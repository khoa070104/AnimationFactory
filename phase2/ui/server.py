"""AnimationFactory local UI server (stdlib only). Binds to 127.0.0.1; every API call needs the per-run token; Host header is checked.
  python phase2\\ui\\server.py [--port 8765]     then open the printed URL.
All buttons call the real pipeline (new_project, prepare, sbstore, revise, approve, produce / build_video, agy_jobs, export_project); the UI never edits tool code.
State lives in the project folders (never in the page), so reloading the page or restarting the server loses nothing."""
import argparse
import hashlib
import json
import mimetypes
import os
import re
import secrets
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

HERE = Path(__file__).resolve().parent
P2 = HERE.parent
TOOLS = P2 / "tools"
sys.path.insert(0, str(TOOLS))
import agy_image  # noqa: E402
import agy_jobs  # noqa: E402
import approve  # noqa: E402
import budget  # noqa: E402
import capabilities  # noqa: E402
import characters as CHR  # noqa: E402
import char_preview  # noqa: E402
import channel as CH  # noqa: E402
import export_project  # noqa: E402
import llm  # noqa: E402
import new_project  # noqa: E402
import overview  # noqa: E402
import prepare as PR  # noqa: E402
import revise  # noqa: E402
import sbload  # noqa: E402
import sbstore  # noqa: E402
import telegram_bot as TG  # noqa: E402

PROJECTS = P2 / "projects"
TOKEN = secrets.token_urlsafe(18)
NAME_RE = re.compile(r"^[a-z0-9_]{1,40}$")
RUNNING = {}                      # project -> {"proc", "kind", "started", "log"}
LISTENER = {"proc": None}         # the Telegram listener process (one per server)
LOCK = threading.Lock()
SERVED_EXT = {".png", ".jpg", ".jpeg", ".mp4", ".json", ".md", ".log", ".txt", ".zip", ".jsonl"}


def proj_dir(name):
    if not NAME_RE.match(name or ""):
        raise KeyError("bad project name")
    p = PROJECTS / name
    if not (p / "storyboard.json").exists():
        raise KeyError(f"unknown project {name}")
    return p


def sha_file(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def jread(p, default=None):
    p = Path(p)
    return agy_image.read_json(p, default) if p.exists() else default


def running_info(name):
    with LOCK:
        r = RUNNING.get(name)
        if r and r["proc"].poll() is None:
            return {"kind": r["kind"], "started": r["started"], "scene": r.get("scene")}
        if r:
            r["rc"] = r["proc"].returncode
    return None


def last_log_tail(proj, n=60):
    logs = sorted((proj / "logs").glob("*.log"), key=lambda f: f.stat().st_mtime) if (proj / "logs").exists() else []
    ui = sorted((proj / "logs").glob("ui_run_*.log"), key=lambda f: f.stat().st_mtime) if (proj / "logs").exists() else []
    f = ui[-1] if ui else (logs[-1] if logs else None)
    if not f:
        return {"file": None, "lines": []}
    return {"file": f.name, "lines": f.read_text(encoding="utf-8", errors="replace").splitlines()[-n:]}


class ApiError(Exception):
    def __init__(self, code, msg, extra=None):
        self.code, self.msg, self.extra = code, msg, extra or {}


def project_view(name):
    proj = proj_dir(name)
    sb = sbload.load_storyboard(proj)
    raw_hash = sha_file(proj / "storyboard.json")
    status = jread(proj / "status.json", {})
    est = jread(proj / "estimate.json", {})
    appr = jread(proj / "approval.json")
    changes = {"voice": [], "scene": []}
    if appr and sb["scenes"]:
        vc, sc = approve.changes_since_approval(proj)
        changes = {"voice": vc, "scene": sc}
    fb = jread(proj / "feedback.json", [])
    secs = overview.scene_seconds(sb) if sb["scenes"] else {}
    script = jread(proj / "prepare" / "script.json", {}) or {}
    smeta = {s["id"]: s for s in script.get("scenes", [])}
    scenes = []
    for sc in sb["scenes"]:
        sid = sc["id"]
        prev = proj / "previews" / f"{sid}.png"
        sig = proj / "audio" / f"{sid}.mp3"
        scenes.append({"id": sid, "title": sc.get("title", ""), "voice": sc["voice"], "subtitles": sc["subtitles"], "bg": sc.get("bg"),
                       "bi": sc.get("bi"), "actions": [a.get("name") for a in sc.get("actions", [])], "items": [i.get("type") for i in sc.get("items", [])],
                       "chars": len(sc["voice"]), "est_seconds": secs.get(sid), "section": (smeta.get(sid) or {}).get("section"), "notes": (smeta.get(sid) or {}).get("notes"),
                       "preview": (f"/files/{name}/previews/{sid}.png?v={int(prev.stat().st_mtime)}" if prev.exists() else None),
                       "audio_ready": (proj / "audio" / f"{sid}.sig").exists(), "clip_ready": (proj / "render" / f"{sid}.mp4").exists(),
                       "voice_changed": sid in changes["voice"], "scene_changed": sid in changes["scene"],
                       "feedback": [f for f in fb if f["scene"] == sid]})
    outputs = sorted((proj / "output").glob("*.mp4"), key=lambda f: f.stat().st_mtime, reverse=True) if (proj / "output").exists() else []
    assets = jread(proj / "ai_assets" / "manifest.json", {"assets": {}})["assets"]
    report = jread(proj / "logs" / "build_report.json", {})
    kinds = (appr or {}).get("kinds") or ({k: {"version": appr["storyboard_version"], "by": appr["approved_by"], "on": appr["approved_on"]} for k in ("script", "storyboard")} if appr else {})
    return {"name": name, "title": sb.get("title"), "audience": sb.get("audience"), "message": sb.get("message"), "version": sb.get("version"),
            "storyboard_hash": raw_hash, "voice": sb.get("voice"), "brief": jread(proj / "brief.json", {}), "status": status, "estimate": (overview.estimate(sb) if sb["scenes"] else est.get("total")),
            "estimate_assumptions": est.get("assumptions"),
            "approval": ({"by": appr["approved_by"], "on": appr["approved_on"], "version": appr["storyboard_version"], "kinds": kinds} if appr else None),
            "changes_since_approval": changes, "scenes": scenes, "feedback": fb, "has_storyboard": bool(sb["scenes"]), "targets": sbload.targets(sb),
            "outputs": [{"name": f.name, "url": f"/files/{name}/output/{f.name}?v={int(f.stat().st_mtime)}", "size": f.stat().st_size,
                         "mtime": time.strftime("%Y-%m-%d %H:%M", time.localtime(f.stat().st_mtime))} for f in outputs],
            "project_files": [str(p.relative_to(proj)).replace("\\", "/") for p in (proj / "render").glob("*.?cproj")] if (proj / "render").exists() else [],
            "checks": report.get("checks", []), "running": running_info(name), "log": last_log_tail(proj),
            "ai_assets": [{"id": k, "kind": v.get("kind"), "status": agy_image.approval_state(proj, k)[0] if v.get("status") == "approved" else v.get("status"),
                           "error": v.get("error") or agy_image.approval_state(proj, k)[2] or None, "prompt": v.get("prompt"), "reused_from": v.get("reused_from"),
                           "approved_by": v.get("approved_by"), "model": v.get("agent_model"),
                           "url": (f"/files/{name}/{v['file']}?v={(v.get('sha256') or '')[:8]}" if v.get("file") else None)} for k, v in assets.items()]}


def character_view(proj, name, cid):
    prof = CHR.get_profile(proj, cid) or {}
    stt, why = CHR.state(proj, cid)
    man = agy_image.load_manifest(proj)["assets"]
    sheets = {}
    for nm, aid in zip(("parts", "faces"), CHR.sheet_ids(cid)):
        e = man.get(aid) or {}
        sheets[nm] = {"id": aid, "status": agy_image.approval_state(proj, aid)[0] if e else "missing", "url": f"/files/{name}/{e['file']}?v={(e.get('sha256') or '')[:8]}" if e.get("file") else None}
    rig = jread(CHR.cdir(proj, cid) / "rig.json")
    return {"id": cid, "profile": prof, "state": stt, "why": why, "sheets": sheets, "rig": ({k: rig[k] for k in ("L1", "L2", "armScale", "height", "built")} if rig else None),
            "used": cid in CHR.used_ids(sbload.load_storyboard(proj))}


def character_preview(proj, name, cid):
    rig = jread(CHR.cdir(proj, cid) / "rig.json")
    if not rig:
        raise ApiError(404, "this character has no rig yet")
    out = proj / "prepare" / "char_previews"
    out.mkdir(parents=True, exist_ok=True)
    f = out / f"{cid}_{hashlib.sha256(json.dumps(rig, sort_keys=True).encode()).hexdigest()[:10]}.png"
    if not f.exists():
        char_preview.render(CHR.cdir(proj, cid), f)
    return f"/files/{name}/prepare/char_previews/{f.name}"


def list_projects():
    out = []
    for d in sorted(PROJECTS.iterdir()):
        if d.is_dir() and NAME_RE.match(d.name) and (d / "storyboard.json").exists():
            try:
                sb = sbload.load_storyboard(d)
                st = jread(d / "status.json", {})
                out.append({"name": d.name, "title": sb.get("title"), "version": sb.get("version"), "state": st.get("state"), "scenes": len(sb["scenes"])})
            except (ValueError, KeyError, OSError):
                continue                                               # a damaged project folder must not hide the others
    return out


def slug(title):
    s = re.sub(r"[^a-z0-9]+", "_", re.sub(r"[đĐ]", "d", __import__("unicodedata").normalize("NFKD", title.lower())).encode("ascii", "ignore").decode()).strip("_")
    return (s or "video")[:30]


def save_storyboard(proj, sb_obj, note="ui"):
    try:
        return sbstore.save(proj, sb_obj, note)
    except sbstore.SaveError as e:
        raise ApiError(422, str(e), {"errors": e.errors, "warnings": e.warnings})


def start_run(name, kind, scene=None, step=None, force=()):
    proj = proj_dir(name)
    with LOCK:
        r = RUNNING.get(name)
        if r and r["proc"].poll() is None:
            raise ApiError(409, "a run is already in progress for this project")
        (proj / "logs").mkdir(exist_ok=True)
        log = proj / "logs" / f"ui_run_{time.strftime('%Y%m%d_%H%M%S')}.log"
        py = sys.executable
        if kind == "storyboard":
            cmd = [py, str(TOOLS / "produce.py"), str(proj), "--until", "storyboard"]
        elif kind == "all":
            cmd = [py, str(TOOLS / "produce.py"), str(proj)]
        elif kind == "scene":
            if not scene or not re.match(r"^[A-Za-z0-9_]{1,12}$", scene):
                raise ApiError(400, "scene id required")
            cmd = [py, str(TOOLS / "build_video.py"), str(proj), "--only", scene]
        elif kind == "draft":
            cmd = [py, str(TOOLS / "produce.py"), str(proj), "--draft"]
        elif kind == "prepare":
            if step not in PR.STEPS + PR.OPTIONAL + ["all", "apply_assets"]:
                raise ApiError(400, "unknown prepare step")
            cmd = [py, str(TOOLS / "prepare.py"), str(proj), "--step", step] + [x for f in force if f in PR.STEPS for x in ("--force", f)]
        else:
            raise ApiError(400, "kind must be storyboard | all | scene | draft | prepare")
        fh = open(log, "w", encoding="utf-8")
        proc = subprocess.Popen(cmd, stdout=fh, stderr=subprocess.STDOUT, cwd=str(P2), env={**os.environ, "PYTHONIOENCODING": "utf-8"})
        fh.close()                                   # the child keeps its own handle; do not leak ours
        RUNNING[name] = {"proc": proc, "kind": kind if kind != "prepare" else f"prepare:{step}", "started": time.strftime("%H:%M:%S"), "log": str(log), "scene": scene}
    return {"started": kind, "step": step, "log": log.name}


def composite(proj, aid):
    """Where an asset would sit in its scene: the planned placement drawn on the cream stage (no character) - an honest mock, not a render."""
    from PIL import Image
    plan = jread(proj / "prepare" / "asset_plan.json", {"assets": []}) or {"assets": []}
    e = jread(proj / "ai_assets" / "manifest.json", {"assets": {}})["assets"].get(aid)
    if not e or not e.get("file"):
        raise KeyError("asset has no image")
    pe = next((a for a in plan["assets"] if a["id"] == aid), None)
    stage = Image.new("RGB", (1920, 1080), (255, 246, 229))
    im = Image.open(proj / e["file"]).convert("RGBA")
    pl = (pe or {}).get("placement") or {"mode": "bg" if e.get("kind") == "background" else "item", "x": 1400, "y": 560, "scale": 1.0}
    if pl["mode"] == "bg":
        stage.paste(im.resize((1920, 1080)).convert("RGB"), (0, 0))
    else:
        k = 0.5 * float(pl.get("scale", 1.0))                       # the PNG is 2x its display size; scale 1.0 = display size
        w, h = max(1, int(im.size[0] * k)), max(1, int(im.size[1] * k))
        im2 = im.resize((w, h))
        stage.paste(im2, (int(pl["x"] - w / 2), int(pl["y"] - h / 2)), im2)
    out = proj / "prepare" / "composites"
    out.mkdir(parents=True, exist_ok=True)
    f = out / f"{aid}_{(e.get('sha256') or '')[:8]}.png"
    stage.save(f)
    return f


class Handler(BaseHTTPRequestHandler):
    server_version = "AFUI/2.0"

    def log_message(self, fmt, *args):
        pass

    def handle(self):
        try:
            super().handle()
        except (ConnectionAbortedError, ConnectionResetError, BrokenPipeError):
            pass                                             # browser dropped the connection (e.g. paused video range request)

    # ---- plumbing ----
    def _host_ok(self):
        h = (self.headers.get("Host") or "").split(":")[0]
        return h in ("127.0.0.1", "localhost")

    def _json(self, code, obj):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _body(self):
        n = int(self.headers.get("Content-Length") or 0)
        if n > 5_000_000:
            raise ApiError(413, "body too large")
        return json.loads(self.rfile.read(n).decode("utf-8")) if n else {}

    def _dispatch(self, method):
        if not self._host_ok():
            return self._json(403, {"error": "bad host"})
        u = urlparse(self.path)
        path = unquote(u.path)
        try:
            if method == "GET" and path == "/":
                return self._index()
            if method == "GET" and path.startswith("/files/"):
                return self._file(path)
            if not path.startswith("/api/"):
                return self._json(404, {"error": "not found"})
            if self.headers.get("X-AF-Token") != TOKEN:
                return self._json(403, {"error": "missing or wrong token"})
            body = self._body() if method in ("POST", "PUT") else {}
            res = self._api(method, path, parse_qs(u.query), body)
            return self._json(200, res)
        except ApiError as e:
            return self._json(e.code, {"error": e.msg, **e.extra})
        except KeyError as e:
            return self._json(404, {"error": str(e).strip("'\"")})
        except budget.BudgetError as e:
            return self._json(429, {"error": str(e), "budget": True})
        except (agy_jobs.JobError, CH.ChannelError, PR.PrepareError, revise.ReviseError, llm.LLMError) as e:
            return self._json(400, {"error": str(e)})
        except (ValueError, TypeError) as e:
            return self._json(400, {"error": f"bad request: {e}"})
        except Exception as e:  # never kill the server
            import traceback
            traceback.print_exc()
            return self._json(500, {"error": f"internal error: {e}"})

    def do_GET(self):
        self._dispatch("GET")

    def do_POST(self):
        self._dispatch("POST")

    def do_PUT(self):
        self._dispatch("PUT")

    # ---- static ----
    def _index(self):
        html = (HERE / "static" / "index.html").read_text(encoding="utf-8").replace("__TOKEN__", TOKEN).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(html)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(html)

    def _file(self, path):
        parts = path.split("/", 3)                                          # ['', 'files', name, rel]
        if len(parts) < 4:
            return self._json(404, {"error": "not found"})
        try:
            proj = proj_dir(parts[2])
        except KeyError:
            return self._json(404, {"error": "unknown project"})
        f = (proj / parts[3]).resolve()
        if proj.resolve() not in f.parents or f.suffix.lower() not in SERVED_EXT or not f.is_file() or ".env" in f.name:
            return self._json(404, {"error": "not found"})
        size = f.stat().st_size
        ctype = mimetypes.guess_type(str(f))[0] or "application/octet-stream"
        rng = self.headers.get("Range")
        start, end, code = 0, size - 1, 200
        if rng and rng.startswith("bytes="):
            a, _, b = rng[6:].partition("-")
            start = int(a) if a else max(0, size - int(b))
            end = int(b) if (a and b) else size - 1
            end = min(end, size - 1)
            code = 206
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Length", str(end - start + 1))
        if f.suffix.lower() == ".zip":
            self.send_header("Content-Disposition", f'attachment; filename="{f.name}"')
        if code == 206:
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.end_headers()
        with open(f, "rb") as fh:
            fh.seek(start)
            left = end - start + 1
            while left > 0:
                chunk = fh.read(min(65536, left))
                if not chunk:
                    break
                try:
                    self.wfile.write(chunk)
                except (BrokenPipeError, ConnectionResetError):
                    break
                left -= len(chunk)

    # ---- API ----
    def _api(self, method, path, q, body):
        seg = [s for s in path.split("/") if s][1:]                         # after 'api'
        if seg == ["projects"] and method == "GET":
            return {"projects": list_projects()}
        if seg == ["projects"] and method == "POST":
            return self._create_project(body)
        if seg == ["channels"] and method == "GET":
            return {"channels": CH.list_all()}
        if len(seg) == 2 and seg[0] == "channel":
            if method == "GET":
                return {"id": seg[1], "profile": CH.get(seg[1]) if (CH.CH / f"{seg[1]}.json").exists() else CH.DEFAULT}
            if method == "PUT":
                return {"id": seg[1], "profile": CH.save(seg[1], body.get("profile") or {})}
        if seg == ["telegram"] and method == "GET":
            pr = LISTENER["proc"]
            return {**TG.status(), "listening": bool(pr and pr.poll() is None)}
        if seg == ["telegram", "listen"] and method == "POST":
            if not TG.configured():
                raise ApiError(409, "Telegram is not configured: " + "; ".join(TG.status()["missing"]))
            pr = LISTENER["proc"]
            if body.get("on") and not (pr and pr.poll() is None):
                LISTENER["proc"] = subprocess.Popen([sys.executable, str(TOOLS / "telegram_bot.py"), "listen"], cwd=str(P2), env={**os.environ, "PYTHONIOENCODING": "utf-8"},
                                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if not body.get("on") and pr and pr.poll() is None:
                pr.terminate()
            pr = LISTENER["proc"]
            return {"listening": bool(pr and pr.poll() is None)}
        if seg == ["capabilities"] and method == "GET":
            n = (q.get("project") or [None])[0]
            return capabilities.capabilities(proj_dir(n) if n else None)
        if len(seg) >= 2 and seg[0] == "project":
            return self._project_api(seg[1], seg[2:], method, q, body)
        raise ApiError(404, "unknown endpoint")

    def _create_project(self, body):
        title = str(body.get("title", "")).strip()
        if not title:
            raise ApiError(400, "title is required")
        name = str(body.get("name", "")).strip() or slug(title)
        if not NAME_RE.match(name):
            raise ApiError(400, "name: lowercase letters, digits, underscore (max 40)")
        base, k = name, 2
        while (PROJECTS / name).exists():
            if str(body.get("name", "")).strip():
                raise ApiError(409, "project already exists")
            name = f"{base[:36]}_{k}"
            k += 1
        brief = {k2: body.get(k2) for k2 in new_project.BRIEF_KEYS}
        brief["title"] = title
        try:
            new_project.create(name, title, brief=brief)
        except ValueError as e:
            raise ApiError(400, str(e))
        import topics
        topics.add(brief.get("channel") or "default", title, name)           # the channel remembers which topics already became projects
        return {"created": name}

    def _project_api(self, name, rest, method, q, body):
        proj = proj_dir(name)
        if not rest and method == "GET":
            return project_view(name)
        if rest == ["brief"] and method == "PUT":
            cur = jread(proj / "brief.json", {}) or {}
            b = new_project.normalise_brief({**cur, **body}, cur.get("title", ""), defaults={"asset_policy": "legacy", "character_mode": "bi"})
            CH.get(b["channel"])
            agy_image.write_json_atomic(proj / "brief.json", b)
            return {"saved": True, "brief": b}
        if rest == ["storyboard"] and method == "GET":
            return {"text": (proj / "storyboard.json").read_text(encoding="utf-8"), "hash": sha_file(proj / "storyboard.json")}
        if rest == ["storyboard"] and method == "PUT":
            if body.get("expect_hash") and body["expect_hash"] != sha_file(proj / "storyboard.json"):
                raise ApiError(409, "storyboard changed since you opened it; reload before saving")
            obj = body["storyboard"] if isinstance(body.get("storyboard"), dict) else json.loads(body.get("text", ""))
            return save_storyboard(proj, obj, "editor")
        if rest == ["validate"] and method == "POST":
            obj = body["storyboard"] if isinstance(body.get("storyboard"), dict) else json.loads(body.get("text", ""))
            errors, warnings = sbstore.validate_obj(proj, obj)
            return {"errors": errors, "warnings": warnings}
        # ---- scenes (form editor) ----
        if rest == ["scenes"] and method == "GET":
            sb = json.loads((proj / "storyboard.json").read_text(encoding="utf-8"))
            return {"scenes": sb["scenes"], "hash": sha_file(proj / "storyboard.json"), "version": sb.get("version")}
        if len(rest) == 3 and rest[0] == "scene" and rest[2] == "voice" and method == "PUT":
            try:
                res = sbstore.edit_voice(proj, rest[1], body.get("text", ""))
            except sbstore.SaveError as e:
                raise ApiError(422, str(e), {"errors": e.errors, "warnings": e.warnings})
            return res
        if len(rest) == 2 and rest[0] == "scene" and method == "PUT":
            sb = json.loads((proj / "storyboard.json").read_text(encoding="utf-8"))
            idx = next((i for i, s in enumerate(sb["scenes"]) if s["id"] == rest[1]), None)
            if idx is None:
                raise KeyError("unknown scene")
            new = body.get("scene")
            if not isinstance(new, dict):
                raise ApiError(400, "scene object required")
            new["id"] = rest[1]
            changes = []
            if new.get("voice") != sb["scenes"][idx]["voice"]:
                import realign
                new, changes = realign.realign(new, " ".join(str(new.get("voice", "")).split()))
                new["subtitles"] = "auto"
            sb["scenes"][idx] = new
            res = save_storyboard(proj, sb, f"form_{rest[1]}")
            res["realigned"] = changes
            return res
        if rest == ["scenes"] and method == "POST":
            sb = json.loads((proj / "storyboard.json").read_text(encoding="utf-8"))
            n = 1
            ids = {s["id"] for s in sb["scenes"]}
            while f"s{n:02d}" in ids:
                n += 1
            sc = {"id": f"s{n:02d}", "title": str(body.get("title") or "Cảnh mới"), "voice": str(body.get("voice") or "Lời đọc của cảnh mới."), "subtitles": "auto", "bg": "cream",
                  "transition": "cut", "bi": {"x": 500, "y": 930, "scale": 1.05, "face": "neutral", "pose": "idle"}, "actions": [], "face_cues": [], "items": []}
            after = body.get("after")
            pos = next((i + 1 for i, s in enumerate(sb["scenes"]) if s["id"] == after), len(sb["scenes"]))
            sb["scenes"].insert(pos, sc)
            res = save_storyboard(proj, sb, "add_scene")
            res["scene"] = sc["id"]
            return res
        if len(rest) == 3 and rest[0] == "scene" and rest[2] in ("delete", "move") and method == "POST":
            sb = json.loads((proj / "storyboard.json").read_text(encoding="utf-8"))
            idx = next((i for i, s in enumerate(sb["scenes"]) if s["id"] == rest[1]), None)
            if idx is None:
                raise KeyError("unknown scene")
            if rest[2] == "delete":
                if len(sb["scenes"]) <= 1:
                    raise ApiError(400, "a storyboard needs at least one scene")
                sb["scenes"].pop(idx)
            else:
                j = idx + (-1 if body.get("dir") == "up" else 1)
                if not 0 <= j < len(sb["scenes"]):
                    raise ApiError(400, "cannot move further")
                sb["scenes"][idx], sb["scenes"][j] = sb["scenes"][j], sb["scenes"][idx]
            return save_storyboard(proj, sb, f"{rest[2]}_{rest[1]}")
        # ---- feedback ----
        if rest == ["feedback"] and method == "POST":
            fb = jread(proj / "feedback.json", [])
            text = str(body.get("text", "")).strip()
            if not text or not body.get("scene"):
                raise ApiError(400, "scene and text are required")
            sb = json.loads((proj / "storyboard.json").read_text(encoding="utf-8"))
            if body["scene"] != "_all" and not any(s["id"] == body["scene"] for s in sb["scenes"]):
                raise ApiError(400, "unknown scene")
            fb.append({"id": secrets.token_hex(4), "scene": str(body["scene"]), "text": text, "storyboard_version": sb.get("version"),
                       "at": time.strftime("%Y-%m-%d %H:%M:%S"), "status": "open"})
            agy_image.write_json_atomic(proj / "feedback.json", fb)
            return {"feedback": fb[-1]}
        if len(rest) == 3 and rest[0] == "feedback" and rest[2] == "done" and method == "POST":
            fb = jread(proj / "feedback.json", [])
            for f in fb:
                if f["id"] == rest[1]:
                    f["status"] = "done"
            agy_image.write_json_atomic(proj / "feedback.json", fb)
            return {"ok": True}
        # ---- approvals ----
        if rest == ["approve"] and method == "POST":
            by = str(body.get("by", "")).strip()
            if not by:
                raise ApiError(400, "approver name is required")
            if body.get("expect_hash") != sha_file(proj / "storyboard.json"):
                raise ApiError(409, "the content changed after this page was loaded; review the changes and approve again")
            kind = str(body.get("kind") or "all")
            if kind not in approve.KINDS:
                raise ApiError(400, "kind must be script | storyboard | all")
            try:
                approve.record(proj, by, kind, str(body.get("note", "")), via="web")
            except ValueError as e:
                raise ApiError(400, str(e))
            sb = json.loads((proj / "storyboard.json").read_text(encoding="utf-8"))
            (proj / "versions").mkdir(exist_ok=True)
            import shutil
            shutil.copy(proj / "storyboard.json", proj / "versions" / f"storyboard_v{sb.get('version')}_approved_{kind}.json")
            return {"approved": True, "kind": kind, "version": sb.get("version")}
        if rest == ["history"] and method == "GET":
            return {"history": approve.history(proj)}
        # ---- runs ----
        if rest == ["run"] and method == "POST":
            return start_run(name, str(body.get("kind", "")), body.get("scene"), body.get("step"), body.get("force") or ())
        if rest == ["log"] and method == "GET":
            return {"running": running_info(name), "log": last_log_tail(proj, int((q.get("lines") or ["80"])[0])), "status": jread(proj / "status.json", {})}
        if rest == ["production"] and method == "GET":
            return {**overview.production(proj), "running": running_info(name), "log": last_log_tail(proj, 40)}
        if rest == ["telegram"] and method == "GET":
            return {"status": TG.status(), "outbox": TG.outbox(proj), "current_hash12": TG.storyboard_hash12(proj), "video": (TG.latest_video(proj) or Path("")).name or None}
        if rest == ["telegram", "send"] and method == "POST":
            try:
                return TG.send_review(proj, force=bool(body.get("force")))
            except TG.TelegramError as e:
                raise ApiError(409, str(e))
        if rest == ["export"] and method == "POST":
            f, n = export_project.make(proj)
            return {"file": f.name, "files": n, "url": f"/files/{name}/export/{f.name}", "size": f.stat().st_size}
        # ---- AI preparation ----
        if rest == ["prepare"] and method == "GET":
            return {"overview": PR.overview(proj), "research": jread(proj / "prepare" / "research.json"), "script": jread(proj / "prepare" / "script.json"),
                    "plan": jread(proj / "prepare" / "asset_plan.json"), "asset_state": jread(proj / "prepare" / "asset_state.json", {"applied": []}),
                    "proposals": revise.list_all(proj), "meta": jread(proj / "prepare" / "storyboard_meta.json"), "opportunities": jread(proj / "prepare" / "opportunities.json"), "rejected": jread(proj / "prepare" / "storyboard_rejected.json")}
        if len(rest) == 3 and rest[:2] == ["prepare", "fact"] and method == "POST":
            PR.set_fact_decision(proj, rest[2], body.get("decision"))
            return {"ok": True}
        if rest == ["prepare", "plan", "approve"] and method == "POST":
            by = str(body.get("by", "")).strip()
            if not by:
                raise ApiError(400, "approver name is required")
            if body.get("expect_hash") and body["expect_hash"] != PR.plan_hash(proj):
                raise ApiError(409, "the plan changed after this page was loaded; review it and approve again")
            return PR.approve_plan(proj, by, str(body.get("note", "")))
        if len(rest) == 4 and rest[:3] == ["prepare", "plan", "asset"] and method == "PUT":
            return PR.update_plan_asset(proj, rest[3], prompt=body.get("prompt"), kind=body.get("kind"), rationale=body.get("rationale"), placement=body.get("placement"), reuse=body.get("reuse"))
        if len(rest) == 5 and rest[:3] == ["prepare", "plan", "asset"] and rest[4] == "remove" and method == "POST":
            PR.remove_plan_asset(proj, rest[3])
            return {"ok": True}
        # ---- AI revise (proposal -> diff -> apply) ----
        if rest == ["ai", "revise"] and method == "POST":
            if body.get("type") == "asset":
                return revise.propose_asset(proj, str(body.get("target", "")), body.get("instruction", ""))
            return revise.propose_scene(proj, str(body.get("target", "")), body.get("instruction", ""))
        if rest == ["ai", "proposals"] and method == "GET":
            return {"proposals": revise.list_all(proj)}
        if len(rest) == 4 and rest[:2] == ["ai", "proposal"] and method == "POST" and rest[3] in ("apply", "reject"):
            return revise.apply(proj, rest[2]) if rest[3] == "apply" else revise.reject(proj, rest[2])
        # ---- characters (AI cast: sheets -> rig -> approval) ----
        if rest == ["characters"] and method == "GET":
            return {"characters": [character_view(proj, name, cid) for cid in CHR.list_ids(proj)], "plan": PR.characters_plan(proj)}
        if len(rest) == 2 and rest[0] == "character" and method == "PUT":
            prof = CHR.get_profile(proj, rest[1]) or {}
            CHR.save_profile(proj, rest[1], {**prof, **{k: body.get(k) for k in ("name", "role", "description", "outfit", "personality") if body.get(k) is not None}})
            return character_view(proj, name, rest[1])
        if len(rest) == 3 and rest[0] == "character" and rest[2] == "build" and method == "POST":
            try:
                CHR.build(proj, rest[1])
            except (CHR.CharacterError, __import__("char_rig").CharRigError) as e:
                raise ApiError(422, str(e))
            return character_view(proj, name, rest[1])
        if len(rest) == 3 and rest[0] == "character" and rest[2] == "approve" and method == "POST":
            by = str(body.get("by", "")).strip()
            if not by:
                raise ApiError(400, "approver name is required")
            PR.approve_character(proj, rest[1], by, str(body.get("note", "")))
            return character_view(proj, name, rest[1])
        if len(rest) == 3 and rest[0] == "character" and rest[2] == "preview" and method == "GET":
            return {"url": character_preview(proj, name, rest[1])}
        # ---- assets ----
        if len(rest) == 3 and rest[0] == "asset" and method == "POST" and rest[2] in ("approve", "reject"):
            try:
                if rest[2] == "approve":
                    if not str(body.get("by", "")).strip():
                        raise ApiError(400, "approver name is required")
                    agy_image.set_status(proj, rest[1], "approved", approved_by=str(body["by"]), approved_on=time.strftime("%Y-%m-%d"))
                else:
                    agy_image.set_status(proj, rest[1], "rejected", note=str(body.get("note", "")))
            except SystemExit as e:                                  # set_status refuses unknown assets / missing or changed files
                raise ApiError(409, str(e))
            return {"ok": True}
        if len(rest) == 3 and rest[0] == "asset" and rest[2] == "composite" and method == "GET":
            f = composite(proj, rest[1])
            return {"url": f"/files/{name}/prepare/composites/{f.name}"}
        if rest == ["ai_job"] and method == "POST":
            return agy_jobs.submit(name, {"asset_id": body.get("asset_id"), "kind": body.get("kind"), "prompt": body.get("prompt"),
                                          "reference_images": body.get("reference_images") or [], "transparent_background": body.get("transparent_background"),
                                          "display_width": body.get("display_width"), "regenerate": bool(body.get("regenerate"))})
        if len(rest) == 2 and rest[0] == "ai_job" and method == "GET":
            return agy_jobs.check(name, rest[1])
        raise ApiError(404, "unknown endpoint")


class _Server(ThreadingHTTPServer):
    allow_reuse_address = False          # on Windows SO_REUSEADDR lets a second server share the port and answer with stale code


def make_server(port=0):
    return _Server(("127.0.0.1", port), Handler)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8765)
    a = ap.parse_args()
    srv = make_server(a.port)
    print(f"AnimationFactory UI: http://127.0.0.1:{srv.server_address[1]}/   (Ctrl+C to stop)", flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
