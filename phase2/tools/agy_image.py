"""agy_image: generate project art (props, backgrounds, characters) with Antigravity's image generator, with a manifest.

  python agy_image.py PROJECT generate --id piggy_ai --kind prop --prompt "a piggy bank" [--ref a.png ...] [--display 300]
                      [--opaque] [--regenerate] [--timeout 330]
  python agy_image.py PROJECT approve piggy_ai --by "owner"      |  reject ID --note "..."  |  list

Rules enforced here (shared by the CLI, the job manager and the MCP server)
  * The art must come from Antigravity's generate_image / `image-generator` sub-agent (checked in the stream-json log). A run where the
    agent drew with code, produced nothing or timed out is a failure, never an asset.
  * The file is taken ONLY from this job's conversations: the sub-agent's transcript (log_uri) and the final response of THIS agy run,
    and it must live under brain/<one of those conversation ids>/. There is no "newest image on the machine" fallback.
  * Same request (kind, prompt, refs, size, transparency) + stored file => no agy call. Only `regenerate` or a changed request calls agy.
    A request that failed twice is blocked until `regenerate` (no retry loops). Attempts per call and time per attempt are bounded.
  * Output PNG is 2x its display size (scale 1.0 in a storyboard = display size). Props/characters get a transparent background (white removed
    by flood fill from the border, fringe softened) unless `transparent=False`; backgrounds are cover-cropped to 16:9.
  * manifest.json stores prompt, full prompt, reference images (sha256), source file, hash, usage, attempts, conversation ids, the agent model
    label read from agy's log (the image model itself is not exposed by agy) and the approval state. New art starts as `draft`.
agy headless cannot ask permissions, so the prompt forbids shell commands; --dangerously-skip-permissions is never used."""
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
from collections import deque
from pathlib import Path
from urllib.parse import unquote, urlparse

import numpy as np
from PIL import Image, ImageFilter

P2 = Path(__file__).resolve().parent.parent
TOK = json.loads((P2 / "style/tokens.json").read_text(encoding="utf-8"))
PROMPT_VERSION = 2
MAX_FAILS = 2
DEFAULT_TIMEOUT = 330
IMAGE_EXT = (".jpg", ".jpeg", ".png", ".webp")
KINDS = {
    "prop": "Subject is ONE single object, centered, filling most of the square frame, on a plain pure white (#FFFFFF) background with nothing else around it. Square image.",
    "character": "Subject is ONE character, full body, front view, centered, on a plain pure white (#FFFFFF) background with nothing else. Square image.",
    "background": "Wide 16:9 landscape scene background, no characters, no text, calm low-contrast flat shapes so characters and charts placed on top stay readable.",
    # character sheets for the cut-out rig (tools/char_rig.py slices them by connected components, so parts must never touch)
    "parts_sheet": ("Character BODY-PARTS sheet for 2D cut-out animation, on a plain pure white (#FFFFFF) background, nothing else. Show EXACTLY FOUR separate parts in ONE horizontal row, "
                    "left to right, each fully separated from the others by wide white gaps (nothing touches or overlaps), all at the same scale and drawn upright and straight: "
                    "(1) TORSO in the character's clothes: from the shoulders down to the waist, front view, NO head, NO arms, NO legs, flat bottom edge; "
                    "(2) UPPER ARM: one straight vertical sleeve piece, same clothes colour, rounded at both ends, about as long as the torso is wide; "
                    "(3) LOWER ARM WITH HAND: one straight vertical piece, rounded elbow end on top, a simple mitten hand (no separate fingers) at the bottom, skin colour; "
                    "(4) LEG WITH SHOE: one straight vertical leg, rounded hip end on top, shoe at the bottom pointing slightly forward. No labels, no text, no shadows."),
    "faces_sheet": ("Character HEADS sheet, on a plain pure white (#FFFFFF) background, nothing else. Show EXACTLY FIVE separate heads in ONE horizontal row, left to right, "
                    "front view, each complete (hair, ears, face, short neck stub), IDENTICAL shape, size, hair and colours - only the facial expression differs: "
                    "1 happy (smile), 2 neutral, 3 worried (brows up, small frown), 4 surprised (round open mouth, wide eyes), 5 thinking (one brow raised, mouth slightly to the side). "
                    "Wide white gaps between heads, nothing touches or overlaps, no labels, no text, no body."),
}
STYLE = (f"Style rules (must follow): flat 2D vector illustration for an adult-audience explainer video; thick near-black outline ({TOK['ink']}, about 8px at 512px); "
         "solid color fills; NO gradients, NO shadows, NO textures, NO 3D; simple geometric shapes; no text or letters anywhere. "
         f"Palette: cream {TOK['bg']}, orange {TOK['bi']}, blue {TOK['accent']['blue']}, yellow {TOK['accent']['yellow']}, teal {TOK['accent']['teal']}, "
         f"red {TOK['accent']['red']}, green {TOK['accent']['green']}.")


def brain_dir():
    return Path(os.environ.get("AGY_HOME") or Path.home() / ".gemini" / "antigravity-cli") / "brain"


def agy_cmd():
    """Command prefix for agy. AGY_CMD (JSON list) overrides it (used to point at another build or a test double)."""
    if os.environ.get("AGY_CMD"):
        return json.loads(os.environ["AGY_CMD"])
    return [shutil.which("agy") or str(Path(os.environ.get("LOCALAPPDATA", "")) / "agy/bin/agy.exe")]


def sha_file(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def build_prompt(kind, subject, ref_names):
    refs = ""
    if ref_names:
        refs = (" Reference image(s) are in the current directory: " + ", ".join(ref_names) +
                ". Open them to match the visual style (line weight, flatness, colours); do not copy their subject unless the subject says so.")
    return ("Call the generate_image tool directly (do NOT run shell commands, do NOT write code or SVG to draw). Generate exactly ONE image. "
            f"{STYLE} {KINDS[kind]} Subject: {subject}.{refs} "
            "When done, reply with one line: the exact file path of the generated image and the tool name you used.")


class AgyTimeout(RuntimeError):
    pass


def run_agy(prompt, cwd, log_file, timeout=DEFAULT_TIMEOUT):
    """Run agy headless. Returns (events, stderr). Raises AgyTimeout when the time limit is hit (the process tree is killed)."""
    cmd = agy_cmd() + ["--print", prompt, "--output-format", "stream-json", "--mode", "accept-edits", "--print-timeout", f"{max(10, timeout - 20)}s",
                       "--log-file", str(log_file)]
    import agy_slots
    try:
        with agy_slots.AgySlot("image"):                                    # at most N agy runs on the machine at once (default 1), across processes
            r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)
    except subprocess.TimeoutExpired as e:
        raise AgyTimeout(f"agy did not finish within {timeout}s") from e
    ev = []
    for line in r.stdout.splitlines():
        line = line.strip()
        if line.startswith("{"):
            try:
                ev.append(json.loads(line))
            except ValueError:
                pass
    return ev, r.stderr


def uri_to_path(uri):
    u = urlparse(uri)
    p = unquote(u.path)
    if re.match(r"^/[A-Za-z]:", p):
        p = p[1:]
    return Path(p)


def analyse(events):
    """-> tool_evidence, conversation ids (this run + its sub-agents), transcripts, response, usage, denied, response_paths."""
    used, conv, resp, usage, denied = False, None, "", {}, []
    subs, transcripts = [], []
    for e in events:
        su = e.get("step_update") or {}
        if su.get("tool_name") == "generate_image":
            used = True
        for s in (su.get("subagent_info") or {}).get("subagents", []):
            if s.get("type_name") == "image-generator":
                used = True
                if s.get("conversation_id") and s["conversation_id"] not in subs:
                    subs.append(s["conversation_id"])
                if s.get("log_uri"):
                    transcripts.append(s["log_uri"])
        if e.get("event") == "result":
            r = e["result"]
            conv, resp, usage, denied = r.get("conversation_id"), r.get("response", ""), r.get("usage", {}), r.get("denied_actions", [])
    paths = re.findall(r"[A-Za-z]:[\\/][^\s\]\)\"'<>]+?\.(?:jpg|jpeg|png|webp)", resp, flags=re.I)
    return {"tool_evidence": used, "conversation_id": conv, "subagent_ids": subs, "transcripts": transcripts, "response": resp, "usage": usage,
            "denied": denied, "response_paths": [Path(p.replace("/", "\\")) for p in paths]}


def transcript_images(uris):
    """Image files recorded by the image-generator sub-agent's own transcript (in order)."""
    out = []
    for u in uris:
        f = uri_to_path(u)
        if not f.exists():
            continue
        for line in f.read_text(encoding="utf-8", errors="replace").splitlines():
            try:
                row = json.loads(line)
            except ValueError:
                continue
            for m in row.get("media") or []:
                if str(m.get("mime_type", "")).startswith("image/") and m.get("uri"):
                    out.append(uri_to_path(m["uri"]))
            for p in re.findall(r"saved at ([A-Za-z]:[\\/][^\s]+?\.(?:jpg|jpeg|png|webp))", str(row.get("content", "")), flags=re.I):
                out.append(Path(p))
    return out


def locate_output(info):
    """The generated file of THIS job: candidates come from this job's transcript / response and must sit under brain/<this job's conversation>/."""
    ids = {i for i in [info["conversation_id"], *info["subagent_ids"]] if i}
    base = brain_dir().resolve()
    cands = transcript_images(info["transcripts"]) + info["response_paths"]
    ok = []
    for p in cands:
        try:
            rp = p.resolve()
        except OSError:
            continue
        if rp.exists() and rp.suffix.lower() in IMAGE_EXT and base in rp.parents and any(i in rp.parts for i in ids) and rp not in ok:
            ok.append(rp)
    return ok[-1] if ok else None                                  # several images in one run: the last one is the final answer


def agent_model(log_file):
    f = Path(log_file)
    if f.exists():
        m = re.search(r'selected model override to backend: label="([^"]+)"', f.read_text(encoding="utf-8", errors="replace"))
        if m:
            return m.group(1)
    return None


def remove_white_background(im, white=232):
    """Flood-fill the near-white background from the image border; soften the fringe. Returns RGBA."""
    a = np.asarray(im.convert("RGB")).astype(np.int16)
    h, w, _ = a.shape
    bg_like = a.min(axis=2) >= white
    seen = np.zeros((h, w), dtype=bool)
    dq = deque()
    for x in range(w):
        for y in (0, h - 1):
            if bg_like[y, x] and not seen[y, x]:
                seen[y, x] = True
                dq.append((y, x))
    for y in range(h):
        for x in (0, w - 1):
            if bg_like[y, x] and not seen[y, x]:
                seen[y, x] = True
                dq.append((y, x))
    while dq:
        y, x = dq.popleft()
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            ny, nx = y + dy, x + dx
            if 0 <= ny < h and 0 <= nx < w and not seen[ny, nx] and bg_like[ny, nx]:
                seen[ny, nx] = True
                dq.append((ny, nx))
    alpha = np.where(seen, 0, 255).astype(np.uint8)
    near = np.asarray(Image.fromarray(seen.astype(np.uint8) * 255).filter(ImageFilter.MaxFilter(5))) > 0
    fringe = near & ~seen
    mn = a.min(axis=2)
    soft = np.clip((255 - mn) / (255 - 90.0), 0, 1) * 255
    alpha = np.where(fringe, np.minimum(alpha, soft).astype(np.uint8), alpha)
    rgb = a.astype(np.uint8).copy()
    gray_fringe = fringe & ((a.max(axis=2) - a.min(axis=2)) < 28)
    rgb[gray_fringe] = np.array([29, 29, 31], dtype=np.uint8)
    return Image.fromarray(np.dstack([rgb, alpha]), "RGBA")


def cover_crop(im, w, h):
    s = max(w / im.width, h / im.height)
    im = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
    l, t = (im.width - w) // 2, (im.height - h) // 2
    return im.crop((l, t, l + w, t + h))


def postprocess(src, dst, kind, display, transparent):
    im = Image.open(src).convert("RGB")
    if kind == "background":
        out = cover_crop(im, display * 2, round(display * 2 * 9 / 16)).convert("RGBA")
    else:
        out = remove_white_background(im) if transparent else im.convert("RGBA")
        if transparent:
            bbox = out.getchannel("A").getbbox()
            if bbox:
                pad = 8
                out = out.crop((max(0, bbox[0] - pad), max(0, bbox[1] - pad), min(out.width, bbox[2] + pad), min(out.height, bbox[3] + pad)))
        s = (display * 2) / max(out.size)
        out = out.resize((max(1, round(out.width * s)), max(1, round(out.height * s))), Image.LANCZOS)
    out.save(dst, "PNG")
    return out.size


def transparency_report(png):
    """Verify a PNG that was supposed to get a transparent background: corners/edges transparent and a sensible opaque subject."""
    a = np.asarray(Image.open(png).convert("RGBA"))[:, :, 3]
    h, w = a.shape
    corners = [int(a[0, 0]), int(a[0, w - 1]), int(a[h - 1, 0]), int(a[h - 1, w - 1])]
    edge = np.concatenate([a[0, :], a[-1, :], a[:, 0], a[:, -1]])
    opaque = float((a > 200).mean())
    edge_clear = float((edge < 10).mean())
    ok = max(corners) < 10 and edge_clear > 0.85 and 0.03 <= opaque <= 0.95
    return {"ok": bool(ok), "corner_alpha": corners, "opaque_fraction": round(opaque, 3), "edge_transparent_fraction": round(edge_clear, 3)}


def normalise(spec):
    s = dict(spec)
    s.setdefault("refs", [])
    s.setdefault("timeout", DEFAULT_TIMEOUT)
    s["display"] = int(s.get("display") or (1920 if s["kind"] == "background" else 300))
    t = s.get("transparent")
    s["transparent"] = (s["kind"] != "background") if t is None else bool(t)
    if s["kind"] == "background":
        s["transparent"] = False
    return s


def signature(spec, refs):
    return hashlib.sha1(json.dumps([PROMPT_VERSION, spec["kind"], spec["prompt"], [r["sha256"] for r in refs], spec["display"], spec["transparent"]],
                                   ensure_ascii=False).encode("utf-8")).hexdigest()


def write_json_atomic(f, obj):
    """Write to a temp file in the same folder, then replace: a reader sees the old or the new file, never half of one."""
    f = Path(f)
    f.parent.mkdir(parents=True, exist_ok=True)
    tmp = f.with_name(f".{f.name}.{os.getpid()}.{threading.get_ident()}.tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
    for k in range(100):
        try:
            os.replace(tmp, f)
            return
        except PermissionError:                                              # Windows: a reader holds the target for a moment
            time.sleep(0.05)
    os.replace(tmp, f)


def read_json(f, default=None):
    """Read a JSON state file written by write_json_atomic (retries a few times on a transient sharing/parse error)."""
    f = Path(f)
    if not f.exists():
        return default
    last = None
    for k in range(40):
        try:
            return json.loads(f.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, PermissionError, FileNotFoundError) as e:
            last = e
            time.sleep(0.05)
    raise last


class manifest_lock:
    """Cross-process lock (lock file created exclusively) for read-modify-write of one project's manifest.
    The MCP server, the UI server and the CLI can all change it; a lock older than 60 s is treated as left behind by a dead process."""

    def __init__(self, proj, timeout=30, name=".manifest.lock"):
        self.f = Path(proj) / "ai_assets" / name
        self.timeout = timeout

    def __enter__(self):
        self.f.parent.mkdir(parents=True, exist_ok=True)
        end = time.time() + self.timeout
        while True:
            try:
                os.close(os.open(self.f, os.O_CREAT | os.O_EXCL | os.O_WRONLY))
                return self
            except FileExistsError:
                try:
                    if time.time() - self.f.stat().st_mtime > 60:
                        self.f.unlink()
                        continue
                except FileNotFoundError:
                    continue
                if time.time() > end:
                    raise RuntimeError("the asset manifest is locked by another process; try again")
                time.sleep(0.05)

    def __exit__(self, *a):
        self.f.unlink(missing_ok=True)


def load_manifest(proj):
    return read_json(Path(proj) / "ai_assets/manifest.json", {"assets": {}})


def save_manifest(proj, m):
    write_json_atomic(Path(proj) / "ai_assets/manifest.json", m)


def put_asset(proj, aid, entry):
    """Replace ONE asset's entry under the lock, re-reading the manifest first (a job runs for minutes; approvals of other assets must survive)."""
    with manifest_lock(proj):
        m = load_manifest(proj)
        m["assets"][aid] = entry
        save_manifest(proj, m)


def file_problem(proj, entry):
    """None if the entry's PNG exists and still has the recorded hash, else a short reason."""
    f = Path(proj) / (entry.get("file") or "")
    if not entry.get("file") or not f.is_file():
        return f"image file {entry.get('file')} is missing"
    if entry.get("sha256") and sha_file(f) != entry["sha256"]:
        return f"image file {entry['file']} no longer matches its recorded hash (it was replaced or damaged)"
    return None


def approval_state(proj, aid):
    """-> (status, png path or None, reason). status is 'approved' only if the owner approved THIS image: the approval stores the file hash
    (approved_sha256; older records fall back to the manifest hash) and the file on disk must still have it."""
    e = load_manifest(proj)["assets"].get(aid)
    if not e:
        return "missing", None, "not in the project's asset manifest"
    png = Path(proj) / (e.get("file") or "_none_")
    if e.get("status") != "approved":
        return e.get("status", "missing"), (png if png.is_file() else None), e.get("error") or ""
    if not png.is_file():
        return "file_missing", None, f"approved image {e.get('file')} is missing"
    want = e.get("approved_sha256") or e.get("sha256")
    if not want or sha_file(png) != want:
        return "changed_after_approval", png, "the image file differs from the one that was approved; approve it again"
    return "approved", png, ""


def record_failure(proj, cur, aid, failed_entry):
    """A failed run replaces the manifest entry ONLY when there was no usable picture before. Otherwise the good asset (and its approval) stays and the
    failure is kept beside it as `last_failure` (so the failure memo still bounds retries)."""
    if cur and cur.get("file") and cur.get("status") in ("draft", "approved") and file_problem(proj, cur) is None:
        keep = dict(cur)
        keep["last_failure"] = {"signature": failed_entry["signature"], "fail_count": failed_entry["fail_count"], "error": failed_entry["error"],
                                "prompt": failed_entry.get("prompt"), "at": time.strftime("%Y-%m-%d %H:%M:%S"), "attempts": failed_entry.get("attempts")}
        put_asset(proj, aid, keep)
    else:
        put_asset(proj, aid, failed_entry)


def generate(proj, spec, runner=run_agy, max_attempts=2):
    """-> (manifest entry, called_agy). Raises RuntimeError (clear reason) on failure/timeout/blocked."""
    proj = Path(proj)
    spec = normalise(spec)
    out_dir = proj / "ai_assets"
    (out_dir / "source").mkdir(parents=True, exist_ok=True)
    (out_dir / "logs").mkdir(exist_ok=True)
    m = load_manifest(proj)
    aid = spec["id"]
    refs = [{"path": str(Path(r).resolve()), "sha256": sha_file(r)} for r in spec["refs"]]
    sig = signature(spec, refs)
    cur = m["assets"].get(aid)
    png = out_dir / f"{aid}.png"
    if cur and cur.get("signature") == sig and not spec.get("regenerate"):
        if cur["status"] not in ("rejected", "failed"):
            bad = file_problem(proj, cur)
            if bad:                                                          # never report a cached success for a file that is gone or changed
                raise RuntimeError(f"stored result for this request is unusable: {bad}. Nothing was generated; use regenerate to create it again (this calls agy)")
            return cur, False                                                # same request, stored result: no agy call
        if cur["status"] == "failed" and cur.get("fail_count", 1) >= MAX_FAILS:
            raise RuntimeError(f"blocked: this exact request already failed {cur['fail_count']} times ({cur.get('error')}); change it or use regenerate")
    lf = (cur or {}).get("last_failure") or {}
    if lf.get("signature") == sig and not spec.get("regenerate") and lf.get("fail_count", 1) >= MAX_FAILS:
        raise RuntimeError(f"blocked: this exact request already failed {lf['fail_count']} times ({lf.get('error')}); change it or use regenerate")
    fails_before = (cur.get("fail_count", 0) if (cur and cur.get("signature") == sig and cur["status"] == "failed") else
                    lf.get("fail_count", 0) if lf.get("signature") == sig else 0)
    work = out_dir / "_work" / aid
    shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True)
    ref_names = []
    for r in spec["refs"]:
        shutil.copy(r, work / Path(r).name)
        ref_names.append(Path(r).name)
    prompt = build_prompt(spec["kind"], spec["prompt"], ref_names)
    attempts, src, info, reason = [], None, None, "no attempt"
    for k in range(max_attempts):
        import budget
        budget.check(proj, "images", 1)                                      # refuse to START a run over the project's image limit
        started = time.time()
        log = out_dir / "logs" / f"{aid}_{time.strftime('%Y%m%d_%H%M%S')}_try{k + 1}"
        att = {"try": k + 1}
        try:
            events, err = runner(prompt, work, str(log) + ".agy.log", spec["timeout"]) if _takes_timeout(runner) else runner(prompt, work, str(log) + ".agy.log")
        except AgyTimeout as e:
            budget.append(proj, {"kind": "image", "task": f"asset {aid}", "attempt": k + 1, "status": "timeout", "seconds": round(time.time() - started, 1)})
            att.update({"seconds": round(time.time() - started, 1), "error": "timeout", "detail": str(e)})
            attempts.append(att)
            reason = f"timeout after {spec['timeout']}s"
            break                                                            # a timed-out run is not retried automatically
        Path(str(log) + ".events.jsonl").write_text("\n".join(json.dumps(e, ensure_ascii=False) for e in events), encoding="utf-8")
        info = analyse(events)
        budget.append(proj, {"kind": "image", "task": f"asset {aid}", "attempt": k + 1, "status": "ok" if info["tool_evidence"] else "no_tool_evidence",
                             "tokens": {"total": (info["usage"] or {}).get("total_tokens", 0)}, "seconds": round(time.time() - started, 1),
                             "conversation_id": info["conversation_id"], "model_actual": agent_model(str(log) + ".agy.log")})
        att.update({"seconds": round(time.time() - started, 1), "usage": info["usage"], "tool_evidence": info["tool_evidence"], "denied": info["denied"],
                    "conversation_id": info["conversation_id"], "subagent_ids": info["subagent_ids"], "events_log": str(log) + ".events.jsonl"})
        attempts.append(att)
        src = locate_output(info) if info["tool_evidence"] else None
        if src is not None:
            att["agent_model"] = agent_model(str(log) + ".agy.log")
            break
        reason = "image generator was not used" if not info["tool_evidence"] else "no generated file found in this job's conversation"
        if k + 1 < max_attempts:
            prompt += " IMPORTANT: your previous attempt produced no image. Use the image generator, do not run commands."
    if src is None:
        record_failure(proj, cur, aid, {"id": aid, "status": "failed", "signature": sig, "attempts": attempts, "fail_count": fails_before + 1, "error": reason,
                                        "kind": spec["kind"], "prompt": spec["prompt"]})
        shutil.rmtree(work, ignore_errors=True)
        raise RuntimeError(reason)
    src_copy = out_dir / "source" / f"{aid}{src.suffix.lower()}"
    shutil.copy(src, src_copy)
    new_png = png.with_name(f"{aid}.new.png")
    size = postprocess(src_copy, new_png, spec["kind"], spec["display"], spec["transparent"])
    tr = transparency_report(new_png) if spec["transparent"] else None
    if tr is not None and not tr["ok"]:
        reason = (f"transparent background requested but the generated image has no plain white background to remove "
                  f"(opaque {tr['opaque_fraction']:.0%}, transparent edge {tr['edge_transparent_fraction']:.0%}); regenerate or use transparent_background=false")
        record_failure(proj, cur, aid, {"id": aid, "status": "failed", "signature": sig, "attempts": attempts, "fail_count": fails_before + 1, "error": reason,
                                        "kind": spec["kind"], "prompt": spec["prompt"], "source": str(src_copy.relative_to(proj)).replace("\\", "/"), "transparency": tr})
        new_png.unlink(missing_ok=True)                                      # the previous good picture (if any) is untouched
        shutil.rmtree(work, ignore_errors=True)
        raise RuntimeError(reason)
    os.replace(new_png, png)
    entry = {"id": aid, "kind": spec["kind"], "status": "draft", "prompt": spec["prompt"], "full_prompt": prompt, "refs": refs, "display": spec["display"],
             "transparent": spec["transparent"], "transparency_check": tr, "file": str(png.relative_to(proj)).replace("\\", "/"), "png_size": list(size), "sha256": sha_file(png),
             "source": str(src_copy.relative_to(proj)).replace("\\", "/"), "source_sha256": sha_file(src_copy), "signature": sig,
             "conversation_id": info["conversation_id"], "subagent_ids": info["subagent_ids"], "generated_file": str(src),
             "agent_model": attempts[-1].get("agent_model"), "image_model": None, "image_model_note": "not exposed by agy",
             "attempts": attempts, "created": time.strftime("%Y-%m-%d %H:%M:%S"), "approved_by": None,
             "history": (cur or {}).get("history", []) + ([cur["sha256"]] if cur and cur.get("sha256") else [])}
    ver = out_dir / "versions" / f"{aid}-{sig[:10]}.png"                     # one frozen copy per request: a job's result stays retrievable after a newer request replaces the asset
    ver.parent.mkdir(exist_ok=True)
    shutil.copy(png, ver)
    entry["version_file"] = str(ver.relative_to(proj)).replace("\\", "/")
    put_asset(proj, aid, entry)
    shutil.rmtree(work, ignore_errors=True)
    return entry, True


def _takes_timeout(fn):
    import inspect
    try:
        return len(inspect.signature(fn).parameters) >= 4
    except (TypeError, ValueError):
        return False


def set_status(proj, aid, status, **kw):
    """Approve / reject. Approval is bound to the image's hash: it fails if the file is missing or differs from the manifest, and a regenerated
    image is a new draft (never inherits an earlier approval)."""
    with manifest_lock(proj):
        m = load_manifest(proj)
        if aid not in m["assets"]:
            sys.exit(f"unknown asset {aid}")
        e = m["assets"][aid]
        if status == "approved":
            bad = file_problem(proj, e)
            if bad:
                sys.exit(f"cannot approve {aid}: {bad}")
            kw["approved_sha256"] = e["sha256"]
        e["status"] = status
        e.update(kw)
        save_manifest(proj, m)
    with (Path(proj) / "approvals_history.jsonl").open("a", encoding="utf-8") as fh:        # who approved / rejected which image (by hash)
        fh.write(json.dumps({"at": time.strftime("%Y-%m-%d %H:%M:%S"), "kind": "asset", "id": aid, "status": status, "by": kw.get("approved_by"),
                             "actor": __import__("actors").classify(kw.get("approved_by"), "web") if kw.get("approved_by") else None,
                             "note": kw.get("note"), "sha256": e.get("sha256")}, ensure_ascii=False) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("project")
    sp = ap.add_subparsers(dest="cmd", required=True)
    g = sp.add_parser("generate")
    g.add_argument("--id", required=True)
    g.add_argument("--kind", choices=sorted(KINDS), required=True)
    g.add_argument("--prompt", required=True)
    g.add_argument("--ref", action="append", default=[])
    g.add_argument("--display", type=int)
    g.add_argument("--opaque", action="store_true", help="keep the white background (no transparency)")
    g.add_argument("--regenerate", action="store_true")
    g.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)
    a1 = sp.add_parser("approve")
    a1.add_argument("id")
    a1.add_argument("--by", required=True)
    r1 = sp.add_parser("reject")
    r1.add_argument("id")
    r1.add_argument("--note", default="")
    sp.add_parser("list")
    a = ap.parse_args()
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    if a.cmd == "generate":
        e, called = generate(a.project, {"id": a.id, "kind": a.kind, "prompt": a.prompt, "refs": a.ref, "display": a.display,
                                         "transparent": False if a.opaque else None, "regenerate": a.regenerate, "timeout": a.timeout})
        print(("GENERATED via Antigravity" if called else "REUSED (no agy call)"), e["file"], e["png_size"], e["status"])
    elif a.cmd == "approve":
        set_status(a.project, a.id, "approved", approved_by=a.by, approved_on=time.strftime("%Y-%m-%d"))
        print("approved", a.id)
    elif a.cmd == "reject":
        set_status(a.project, a.id, "rejected", note=a.note)
        print("rejected", a.id)
    else:
        for k, v in load_manifest(a.project)["assets"].items():
            print(k, v.get("kind"), v["status"], v.get("file"))


if __name__ == "__main__":
    main()
