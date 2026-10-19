"""AnimationFactory control layer: ONE core for the CLI (af.py) and the MCP adapter (assets_mcp/af_assets_server.py).
Every function takes plain arguments and returns a JSON-able dict: {"status": ok | needs_changes | waiting_approval | error | running | ..., "contract": "af/1", ...}.
Errors are structured: {"code", "scene_id", "shot_id", "field", "message", "next_action"}. Nothing here approves anything (approval is the human gate), nothing
calls a paid API except `render` without `draft`, which refuses to run without the owner's approvals and reports `paid_calls_this_run`.
The commands wrap functions that already exist (capabilities, sbload/sbstore, validate, overview.estimate, build_remotion, produce.py) instead of re-implementing them."""
import contextlib
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import budget  # noqa: E402
import capabilities as CAP  # noqa: E402
import sbload  # noqa: E402
import sbstore  # noqa: E402

P2 = Path(__file__).resolve().parent.parent
CONTRACT = "af/1"
PY = sys.executable


class AfError(Exception):
    def __init__(self, code, message, field=None, next_action=None, status="error", **extra):
        super().__init__(message)
        self.err = {"code": code, "scene_id": None, "shot_id": None, "field": field, "message": message, "next_action": next_action}
        self.err.update(extra)
        self.status = status


def _ok(**kw):
    return {"status": "ok", "contract": CONTRACT, **kw}


def _fail(errors, status="error", **kw):
    return {"status": status, "contract": CONTRACT, "errors": errors, "charged_calls": 0, **kw}


def proj_path(project):
    p = Path(project)
    if not p.is_absolute():
        p = P2 / "projects" / project
    if not (p / "storyboard.json").exists() and not (p / "brief.json").exists():
        raise AfError("UNKNOWN_PROJECT", f"no project {project!r}", "project", "List projects under phase2/projects or create one with project_new.")
    return p


def _hash(p):
    f = p / "storyboard.json"
    return hashlib.sha256(f.read_bytes()).hexdigest() if f.exists() else None


def structure(msg):
    """One validator text line -> structured error. Shot problems carry their own code/field; others are located by scene id."""
    e = {"code": "INVALID_STORYBOARD", "scene_id": None, "shot_id": None, "field": None, "message": msg, "next_action": "Fix the named field and validate again."}
    m = re.match(r"^(s\w+): (.*)$", msg)
    if m:
        e["scene_id"], rest = m.group(1), m.group(2)
        sm = re.match(r"^shot (\S+): ([\w.]+): (.*?) \[([A-Z_]+)\]$", rest)
        if sm:
            e.update(shot_id=sm.group(1) if sm.group(1) != "None" else None, field=sm.group(2), message=sm.group(3), code=sm.group(4))
            e["next_action"] = {"CUE_NOT_IN_VOICE": "Copy an exact run of words from the scene's voice text or use seconds.", "SHOT_OVERLAP": "End the shot before the next one starts or drop `end`.",
                                "SHOTS_NOT_INCREASING": "Order shots by increasing start.", "UNKNOWN_FOCUS": "Use main, cast1.., item:<index|img> or [x, y, w, h].",
                                "UNKNOWN_SHOT_SIZE": "Use wide, medium, close or detail."}.get(e["code"], e["next_action"])
        elif "unknown prop image" in rest or "AI asset" in rest or "held AI asset" in rest:
            e["code"], e["next_action"] = "MISSING_ASSET", "Use a library prop, or an approved AI asset id (ai:<id>); generate and have the owner approve it first."
            am = re.search(r"'([\w:\-]+)'", rest)
            e["field"] = "items.img" if "image" in rest else "holds.prop"
            if am:
                e["asset"] = am.group(1)
        elif "emoji" in rest:
            e["code"] = "EMOJI_IN_TEXT"
        elif "grid" in rest and "cells" in rest:
            e["code"], e["field"] = "GRID_CELL_COUNT", "items.cells"
        elif "appear cue" in rest or "action cue" in rest or "cue" in rest and "does not occur" in rest:
            e["code"], e["next_action"] = "CUE_NOT_IN_VOICE", "Copy an exact run of words from the scene's voice text."
    return e


@contextlib.contextmanager
def _quiet():
    """Library code may print: keep stdout machine-readable by sending any print to stderr."""
    with contextlib.redirect_stdout(sys.stderr):
        yield


# ------------------------------------------------------------------------------------------------------------------ capabilities / project
def capabilities(project=None):
    p = proj_path(project) if project else None
    with _quiet():
        cap = CAP.capabilities(p)
    return _ok(capabilities=cap, commands=[t["name"] for t in TOOLS], renderer="remotion (default); craft = fallback", note="approval is not a command: only the owner approves")


def project_new(name, title, brief=None):
    import new_project
    if re.search(r"[^A-Za-z0-9_\-]", name):
        raise AfError("BAD_PROJECT_NAME", "project name: letters, digits, _ and - only", "name")
    with _quiet():
        d = new_project.create(name, title, brief=brief) if brief else new_project.create(name, title)
    return _ok(project=name, path=str(d), next="project_get / project_put a storyboard, then validate")


def project_get(project, what="storyboard"):
    p = proj_path(project)
    out = {"project": p.name, "hash": _hash(p)}
    if (p / "storyboard.json").exists():
        sb = sbload.load_storyboard(p)
        out.update(version=sb.get("version"), scene_ids=[s["id"] for s in sb["scenes"]])
        if what in ("storyboard", "all"):
            out["storyboard"] = json.loads((p / "storyboard.json").read_text(encoding="utf-8"))
    if what in ("status", "all") and (p / "status.json").exists():
        out["project_status"] = json.loads((p / "status.json").read_text(encoding="utf-8"))      # NOT `status`: that key is the envelope's
    return _ok(**out)


def validate(project, storyboard=None):
    p = proj_path(project)
    sb = storyboard if storyboard is not None else json.loads((p / "storyboard.json").read_text(encoding="utf-8"))
    with _quiet():
        errs, warns = sbstore.validate_obj(p, sb)
    if errs:
        return _fail([structure(e) for e in errs], "needs_changes", warnings=warns)
    return _ok(errors=[], warnings=warns, charged_calls=0)


def project_put(project, storyboard, expect_hash, autolayout=False):
    """Replace the storyboard (compare-and-swap on the file hash). Validates first; a copy of the previous version is kept (versions/)."""
    p = proj_path(project)
    cur = _hash(p)
    if expect_hash != cur:
        return _fail([{"code": "STALE_HASH", "scene_id": None, "shot_id": None, "field": "expect_hash", "message": "the storyboard changed since you read it",
                       "next_action": "Call project_get again, merge your change into the current storyboard and retry with its hash.", "current_hash": cur}], "needs_changes")
    if autolayout:                                                    # content panel + props to free spots (layout.compose / nudge): deterministic, no AI
        import layout
        ai = layout.ai_sizes(p)
        import agy_image as G
        man = G.load_manifest(p)["assets"]
        for sc in storyboard.get("scenes", []):
            for h in sc.get("holds", []):                              # a held AI picture without a size gets one that fits a hand (<= 170 px wide)
                if h.get("prop", "").startswith("ai:") and "scale" not in h and (man.get(h["prop"][3:]) or {}).get("png_size"):
                    h["scale"] = round(min(1.0, 170 / (man[h["prop"][3:]]["png_size"][0] / 2)), 3)
            layout.compose(sc, ai)
            layout.nudge(sc, ai)
    busy = _running_job(p)
    if busy:
        return _fail([{"code": "PROJECT_BUSY", "scene_id": None, "shot_id": None, "field": None, "message": f"job {busy['id']} is running on this project",
                       "next_action": "Wait for it (jobs) before changing the storyboard."}], "needs_changes", job=busy)
    try:
        with _quiet():
            r = sbstore.save(p, storyboard, "af_put")
    except sbstore.SaveError as e:
        return _fail([structure(x) for x in e.errors] or [{"code": "SAVE_REFUSED", "message": str(e), "scene_id": None, "shot_id": None, "field": None, "next_action": "Fix and retry."}],
                     "needs_changes", warnings=e.warnings)
    return _ok(project=p.name, version=r["version"], hash=r["hash"], changed=r["changed"], warnings=r["warnings"])


def estimate(project):
    import overview
    p = proj_path(project)
    sb = sbload.load_storyboard(p)
    return _ok(estimate=overview.estimate(sb), budget={"usage": budget.usage(p), "limits": budget.limits(p)}, charged_calls=0,
               note="an estimate is not an approval: paid steps still need the owner's approval and stay inside the budget limits")


# ------------------------------------------------------------------------------------------------------------------ jobs
def _jobs_dir(p):
    d = p / "logs" / "af_jobs"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _fresh_heartbeat(p, rec):
    """Running = the launcher's heartbeat is younger than 12 s; just spawned (no heartbeat yet) = 25 s of grace."""
    hb = _jobs_dir(p) / f"{rec['id']}.hb"
    if hb.exists():
        return time.time() - hb.stat().st_mtime < 12
    return time.time() - time.mktime(time.strptime(rec["started"], "%Y-%m-%d %H:%M:%S")) < 25


def _job_view(p, rec):
    exitf = _jobs_dir(p) / f"{rec['id']}.exit"
    if exitf.exists():
        code = int(exitf.read_text().strip() or 1)
        rec = {**rec, "state": {0: "succeeded", 2: "waiting_approval"}.get(code, "failed"), "exit_code": code}
    elif _fresh_heartbeat(p, rec):
        rec = {**rec, "state": "running"}
    else:
        rec = {**rec, "state": "interrupted"}                                # never silently re-run: the caller decides
    return rec


def _all_jobs(p):
    return [_job_view(p, json.loads(f.read_text(encoding="utf-8"))) for f in sorted(_jobs_dir(p).glob("*.json"))]


def _running_job(p, request=None):
    for j in _all_jobs(p):
        if j["state"] == "running" and (request is None or j.get("request") == request):
            return j
    return None


def jobs(project, job_id=None):
    p = proj_path(project)
    js = _all_jobs(p)
    if job_id:
        j = next((x for x in js if x["id"] == job_id), None)
        if not j:
            raise AfError("UNKNOWN_JOB", f"no job {job_id!r}", "job_id", "List jobs with jobs(project).")
        tail = Path(j["log"]).read_text(encoding="utf-8", errors="replace").splitlines()[-15:] if Path(j["log"]).exists() else []
        return _ok(job=j, log_tail=tail)
    return _ok(jobs=js)


def _spawn(p, request, argv):
    """Run a command as a recorded job: the same request already running returns that job (no second run, no second paid call)."""
    same = _running_job(p, request)
    if same:
        return same, False
    busy = _running_job(p)
    if busy:
        raise AfError("PROJECT_BUSY", f"job {busy['id']} ({busy['request']['op']}) is running on this project", None, "Wait for it, or poll jobs(project, job_id).", status="needs_changes", job=busy)
    jid = f"{request['op']}-{time.strftime('%Y%m%d%H%M%S')}"
    log = _jobs_dir(p) / f"{jid}.log"
    rec = {"id": jid, "request": request, "started": time.strftime("%Y-%m-%d %H:%M:%S"), "log": str(log), "argv": argv}
    jf = _jobs_dir(p) / f"{jid}.json"
    jf.write_text(json.dumps(rec, ensure_ascii=False, indent=1), encoding="utf-8")
    proc = subprocess.Popen([PY, str(P2 / "tools" / "af.py"), "_run_job", str(jf)], cwd=str(P2), env={**os.environ, "PYTHONIOENCODING": "utf-8"},
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    rec["pid"] = proc.pid
    jf.write_text(json.dumps(rec, ensure_ascii=False, indent=1), encoding="utf-8")
    return _job_view(p, rec), True


def _wait(p, job, timeout):
    t0 = time.time()
    while time.time() - t0 < timeout:
        j = next((x for x in _all_jobs(p) if x["id"] == job["id"]), job)
        if j["state"] != "running":
            return j
        time.sleep(2)
    return next((x for x in _all_jobs(p) if x["id"] == job["id"]), job)


def _usage(p):
    u = budget.usage(p)
    return {k: u.get(k, 0) for k in ("llm_calls", "images", "voice_credits")}


def _delta(a, b):
    return {k: round(b[k] - a[k], 2) for k in a}


# ------------------------------------------------------------------------------------------------------------------ preview / render / artifacts
def preview(project, scenes=None, background=False):
    """A free preview: draft build (stub voice, no paid call) of the given scenes (default: all) + a still per shot + a contact sheet + a low-res clip."""
    p = proj_path(project)
    before = _usage(p)
    req = {"op": "preview", "scenes": scenes or "all"}
    argv = [PY, str(P2 / "tools" / "af.py"), "_preview_worker", str(p)] + (["--scenes", ",".join(scenes)] if scenes else [])
    if background:
        job, fresh = _spawn(p, req, argv)
        return _ok(job=job, started=fresh, paid_calls_this_run=0)
    import build_remotion
    import export_remotion
    v = validate(project)
    if v["status"] != "ok":
        return v
    try:
        with _quiet():
            passed = build_remotion.build(p, draft=True, force=False, scene_ids=scenes, log=lambda m: print(m, file=sys.stderr))
    except export_remotion.ExportError as e:
        return _fail([{"code": "PREVIEW_REFUSED", "scene_id": None, "shot_id": None, "field": None, "message": str(e), "next_action": "Fix the data named in the message (asset, character, voice) and preview again."}], "needs_changes")
    arts = _preview_artifacts(p)
    st = json.loads((p / "status.json").read_text(encoding="utf-8"))["last_build"]
    rep = json.loads((p / "logs" / "build_report.json").read_text(encoding="utf-8"))
    return _ok(project=p.name, checks_passed=passed, checks=rep["checks"], rebuilt_scenes=st["rendered"], reused_scenes=st["reused"], artifacts=arts,
               paid_calls_this_run=0, usage_delta=_delta(before, _usage(p)))


def _preview_artifacts(p):
    work = p / "remotion"
    clip = json.loads((work / "public" / "data" / "clip.json").read_text(encoding="utf-8"))
    out = p / "previews" / "af"
    out.mkdir(parents=True, exist_ok=True)
    video = work / "out" / "clip.mp4"
    stills, arts = [], []
    for sc in clip["scenes"]:
        marks = [(f"{sc['id']}_{s['id']}", sc["start"] + (s["t0"] + s["t1"]) / 2, s["id"], round((s["t0"] + s["t1"]) / 2, 2)) for s in sc.get("shots", [])] or             [(f"{sc['id']}_a", sc["start"] + sc["dur"] * 0.3, None, round(sc["dur"] * 0.3, 2)), (f"{sc['id']}_b", sc["start"] + sc["dur"] * 0.75, None, round(sc["dur"] * 0.75, 2))]
        for name, t, shot_id, scene_t in marks:
            f = out / f"{name}.png"
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{t:.2f}", "-i", str(video), "-frames:v", "1", "-vf", "scale=640:-1", str(f)], check=True)
            stills.append(f)
            arts.append({"kind": "still", "scene": sc["id"], "shot": shot_id, "scene_time_s": scene_t, "note": "taken in the middle of the shot", "path": str(f)})
    from PIL import Image
    ims = [Image.open(f) for f in stills]
    if ims:
        w, h = ims[0].size
        cols = 3
        rows = -(-len(ims) // cols)
        sheet = Image.new("RGB", (w * cols, h * rows), "white")
        for i, im in enumerate(ims):
            sheet.paste(im, ((i % cols) * w, (i // cols) * h))
        sp = out / "contact_sheet.jpg"
        sheet.save(sp, quality=82)
        arts.insert(0, {"kind": "contact_sheet", "path": str(sp)})
    low = out / "preview_low.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(video), "-vf", "scale=640:-2", "-crf", "30", "-preset", "veryfast", str(low)], check=True)
    arts.insert(0, {"kind": "clip", "path": str(low)})
    arts.append({"kind": "report", "path": str(p / "logs" / "build_report.json")})
    return arts


def render(project, draft=False, background=False, timeout=1500):
    """Full production run through produce.py (Remotion). Without `draft` it needs the owner's approvals; it stops at the approval gate (status waiting_approval)."""
    p = proj_path(project)
    v = validate(project)
    if v["status"] != "ok":
        return v
    before = _usage(p)
    req = {"op": "render", "draft": bool(draft)}
    argv = [PY, str(P2 / "tools" / "produce.py"), str(p), "--renderer", "remotion"] + (["--draft"] if draft else [])
    job, fresh = _spawn(p, req, argv)
    if background:
        return {"status": "running", "contract": CONTRACT, "job": job, "started": fresh, "paid_calls_this_run": 0}
    job = _wait(p, job, timeout)
    res = {"job": job, "usage_delta": _delta(before, _usage(p)), "paid_calls_this_run": _delta(before, _usage(p))}
    if job["state"] == "running":
        return {"status": "running", "contract": CONTRACT, **res}
    if job["state"] == "waiting_approval":
        return {"status": "waiting_approval", "contract": CONTRACT, **res, "next_action": "The owner reviews and approves (storyboard.md / UI). The tool never approves for them."}
    if job["state"] == "succeeded":
        return _ok(**res, artifacts=artifacts(project)["artifacts"])
    log = Path(job["log"]).read_text(encoding="utf-8", errors="replace").splitlines()[-12:] if Path(job["log"]).exists() else []
    return _fail([{"code": "RENDER_FAILED", "scene_id": None, "shot_id": None, "field": None, "message": "\n".join(log)[-600:], "next_action": "Read logs/build_report.json and the job log, fix the data, run again."}], **res)


def artifacts(project):
    p = proj_path(project)
    items = []
    for sub, kind in (("output", "video"), ("previews/af", "preview"), ("logs", "report"), ("audio", "audio")):
        d = p / sub
        for f in sorted(d.glob("*")) if d.exists() else []:
            if f.is_file() and (f.suffix in (".mp4", ".png", ".jpg", ".json", ".mp3", ".wav", ".log") and not f.name.endswith(".sig")):
                items.append({"kind": kind, "path": str(f), "bytes": f.stat().st_size, "modified": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(f.stat().st_mtime))})
    return _ok(project=p.name, artifacts=items)


# ------------------------------------------------------------------------------------------------------------------ registry (CLI + MCP read the same table)
def _s(props, required=()):
    return {"type": "object", "additionalProperties": False, "required": list(required), "properties": props}


PROJ = {"type": "string", "description": "project folder name under phase2/projects (or an absolute path)"}
TOOLS = [
    {"name": "capabilities", "fn": capabilities, "description": "Versioned catalog: shot kinds/sizes, actions, poses, props, item types, assets the project may use, contract version. Read it first.", "inputSchema": _s({"project": PROJ})},
    {"name": "project_new", "fn": project_new, "description": "Create a project folder (optionally from a brief dict).", "inputSchema": _s({"name": {"type": "string"}, "title": {"type": "string"}, "brief": {"type": "object"}}, ["name", "title"])},
    {"name": "project_get", "fn": project_get, "description": "Read the storyboard (+ its hash for project_put) and/or status.", "inputSchema": _s({"project": PROJ, "what": {"type": "string", "enum": ["storyboard", "status", "all", "summary"]}}, ["project"])},
    {"name": "project_put", "fn": project_put, "description": "Replace the storyboard. Needs expect_hash from project_get (compare-and-swap). Validates first; returns structured errors with scene/shot/field.", "inputSchema": _s({"project": PROJ, "storyboard": {"type": "object"}, "expect_hash": {"type": "string"}, "autolayout": {"type": "boolean", "description": "arrange content items in the content panel and move props to free spots before saving"}}, ["project", "storyboard", "expect_hash"])},
    {"name": "validate", "fn": validate, "description": "Validate the stored storyboard or a given one. Errors: {code, scene_id, shot_id, field, message, next_action}.", "inputSchema": _s({"project": PROJ, "storyboard": {"type": "object"}}, ["project"])},
    {"name": "estimate", "fn": estimate, "description": "Characters, seconds, voice credits and budget usage. An estimate is not an approval.", "inputSchema": _s({"project": PROJ}, ["project"])},
    {"name": "preview", "fn": preview, "description": "Free draft preview of some/all scenes: still per shot, contact sheet, low-res clip, QA checks. No paid call. Reuses unchanged scenes.", "inputSchema": _s({"project": PROJ, "scenes": {"type": "array", "items": {"type": "string"}}, "background": {"type": "boolean"}}, ["project"])},
    {"name": "render", "fn": render, "description": "Production run (Remotion) through produce.py; stops at approval gates (status waiting_approval). draft=true is free. Returns job + paid_calls/usage_delta.", "inputSchema": _s({"project": PROJ, "draft": {"type": "boolean"}, "background": {"type": "boolean"}}, ["project"])},
    {"name": "jobs", "fn": jobs, "description": "List jobs of a project or read one (state running|succeeded|failed|waiting_approval|interrupted + log tail). Poll this after background runs.", "inputSchema": _s({"project": PROJ, "job_id": {"type": "string"}}, ["project"])},
    {"name": "artifacts", "fn": artifacts, "description": "Files produced for a project: videos, preview stills/clips, reports, audio.", "inputSchema": _s({"project": PROJ}, ["project"])},
]


def call(name, args):
    t = next((x for x in TOOLS if x["name"] == name), None)
    if not t:
        raise KeyError(name)
    try:
        return t["fn"](**(args or {}))
    except AfError as e:
        return _fail([e.err], e.status)
    except sbstore.SaveError as e:
        return _fail([structure(x) for x in e.errors], "needs_changes")
    except TypeError as e:
        return _fail([{"code": "BAD_ARGUMENTS", "scene_id": None, "shot_id": None, "field": None, "message": str(e), "next_action": "Check the inputSchema from capabilities/tools list."}])
