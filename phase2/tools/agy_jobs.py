"""Asset job manager on top of agy_image: asynchronous jobs with stable ids, persisted state, one agy run at a time.

  submit(project, request)  -> job record (returns at once; the work runs on a background worker)
  check(project, job_id)    -> job record (+ result summary when it finished)

job_id = <asset_id>-<10 hex of the request signature>: the same request always maps to the same job, so a repeated or retried
submit never starts a second image run (queued/running -> same job; succeeded -> stored result; failed twice -> blocked until `regenerate`).
States: queued, running, succeeded, failed, timeout, interrupted, superseded (a newer request replaced this job's asset), invalid
(the stored image of a finished job is missing or was changed). Every state change is written to PROJECT/ai_assets/jobs/<job_id>.json,
so `check` works after a restart; jobs found `queued/running` at start-up are marked `interrupted` (never silently re-run).
Several processes can share one project (the UI server, the MCP server, a CLI): every queued/running job records its OWNER
(pid + the process' start stamp, so a recycled pid is not mistaken for the owner). Another process that checks or re-submits sees a job
whose owner is alive as simply "running" (never interrupted, never started twice); only a job whose owner is gone becomes `interrupted`.
Submit / interrupt decisions run under a per-project file lock (ai_assets/.jobs.lock).
Time is bounded: per-attempt timeout (default 330 s, max 900) x at most 2 attempts, and a timed-out run is not retried automatically."""
import json
import os
import queue
import re
import threading
import time
from pathlib import Path

import agy_image as G
from agy_slots import proc_stamp  # noqa: F401  (also used by tests)

P2 = G.P2
PROJECTS = P2 / "projects"
ID_RE = re.compile(r"^[a-z0-9_]{1,40}$")
_q = queue.Queue()
_lock = threading.RLock()
_worker = None
_inflight = set()          # {(resolved project path, job_id)}: the same asset request in two projects is two different jobs


class JobError(ValueError):
    """Invalid request (bad project, id, kind, reference...)."""


def resolve_project(name_or_path):
    """Project name under phase2/projects (or an absolute path that resolves INSIDE phase2/projects)."""
    s = str(name_or_path)
    p = (PROJECTS / s) if re.fullmatch(r"[A-Za-z0-9_\-]+", s) else Path(s)
    p = p.resolve()
    root = PROJECTS.resolve()
    if root not in p.parents or not (p / "storyboard.json").exists():
        raise JobError(f"project {s!r} not found under {root}")
    return p


def validate(request):
    r = dict(request)
    if not ID_RE.match(str(r.get("asset_id", ""))):
        raise JobError("asset_id must be 1-40 chars of a-z, 0-9, _")
    if r.get("kind") not in G.KINDS:
        raise JobError(f"kind must be one of {sorted(G.KINDS)}")
    prompt = str(r.get("prompt", "")).strip()
    if not 3 <= len(prompt) <= 2000:
        raise JobError("prompt must be 3-2000 characters")
    refs = [str(x) for x in (r.get("reference_images") or [])]
    if len(refs) > 4:
        raise JobError("at most 4 reference images")
    for x in refs:
        pp = Path(x)
        if not pp.is_file() or pp.suffix.lower() not in G.IMAGE_EXT:
            raise JobError(f"reference image not found or not an image: {x}")
    disp = r.get("display_width")
    if disp is not None and not 64 <= int(disp) <= 4096:
        raise JobError("display_width must be 64-4096")
    to = int(r.get("timeout_seconds") or G.DEFAULT_TIMEOUT)
    if not 30 <= to <= 900:
        raise JobError("timeout_seconds must be 30-900")
    t = r.get("transparent_background")
    if t is not None and not isinstance(t, bool):
        raise JobError("transparent_background must be true/false")
    return {"id": r["asset_id"], "kind": r["kind"], "prompt": prompt, "refs": refs, "display": disp, "transparent": t,
            "timeout": to, "regenerate": bool(r.get("regenerate"))}


def _jobfile(proj, job_id):
    return proj / "ai_assets" / "jobs" / f"{job_id}.json"


def _key(proj, job_id):
    return (str(Path(proj).resolve()), job_id)


def _save(proj, job):
    G.write_json_atomic(_jobfile(proj, job["job_id"]), job)               # atomic: a concurrent `check` never reads half a file


def _load(proj, job_id):
    return G.read_json(_jobfile(proj, job_id))


def _me():
    return {"pid": os.getpid(), "stamp": proc_stamp(os.getpid())}


def _owner_alive(owner, proj, job_id):
    """Is the process that owns this queued/running job still working on it?"""
    if not owner or not owner.get("pid"):
        return _key(proj, job_id) in _inflight                              # record without an owner: only this process can vouch for it
    if owner["pid"] == os.getpid() and owner.get("stamp") == _me()["stamp"]:
        return _key(proj, job_id) in _inflight
    now = proc_stamp(owner["pid"])
    return now is not None and now == owner.get("stamp")


def _jobs_lock(proj):
    return G.manifest_lock(proj, name=".jobs.lock")


def _interrupt_orphans(proj):
    """Caller holds the lock. queued/running jobs whose owner is gone become `interrupted` (never silently re-run)."""
    d = proj / "ai_assets" / "jobs"
    if not d.exists():
        return
    for f in d.glob("*.json"):
        j = G.read_json(f)
        if j and j["state"] in ("queued", "running") and not _owner_alive(j.get("owner"), proj, j["job_id"]):
            j.update(state="interrupted", error="the process that ran this job stopped before it finished; submit again (a finished result is reused)",
                     finished_at=time.strftime("%Y-%m-%d %H:%M:%S"))
            G.write_json_atomic(f, j)


def _mark_interrupted(proj):
    if not (proj / "ai_assets" / "jobs").exists():
        return
    with _lock, _jobs_lock(proj):
        _interrupt_orphans(proj)


SNAP_KEYS = ("file", "version_file", "png_size", "sha256", "transparent", "transparency_check", "source", "conversation_id", "agent_model", "image_model_note", "kind")


def _snapshot(e):
    """What THIS job produced, kept in the job record (the asset entry in the manifest belongs to whichever request ran last)."""
    s = {k: e.get(k) for k in SNAP_KEYS}
    s["tool_evidence"] = bool(e.get("attempts") and e["attempts"][-1].get("tool_evidence"))
    s["usage"] = (e.get("attempts") or [{}])[-1].get("usage")
    return s


def _run(proj, job_id, spec, runner):
    job = _load(proj, job_id)
    job.update(state="running", started_at=time.strftime("%Y-%m-%d %H:%M:%S"))
    _save(proj, job)
    try:
        entry, called = G.generate(proj, spec, runner=runner)
        job.update(state="succeeded", reused=not called, error=None, snapshot=_snapshot(entry))
    except Exception as e:                                           # report clearly, never loop
        msg = str(e)
        entry = G.load_manifest(proj)["assets"].get(spec["id"], {})
        lf = entry.get("last_failure") or {}
        fc = lf["fail_count"] if lf.get("signature") == job["signature"] else entry.get("fail_count", job.get("fail_count", 0) + 1)
        job.update(state="timeout" if msg.startswith("timeout") else "failed", error=msg, reused=False, fail_count=fc)
    job["finished_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
    _save(proj, job)


def _worker_loop(runner):
    while True:
        proj, job_id, spec = _q.get()
        try:
            _run(proj, job_id, spec, runner)
        finally:
            with _lock:
                _inflight.discard(_key(proj, job_id))
            _q.task_done()


def start_worker(runner=G.run_agy):
    global _worker
    with _lock:
        if _worker is None or not _worker.is_alive():
            _worker = threading.Thread(target=_worker_loop, args=(runner,), daemon=True, name="agy-worker")
            _worker.start()


def submit(project, request, runner=G.run_agy):
    proj = resolve_project(project)
    spec = validate(request)
    refs = [{"path": str(Path(r).resolve()), "sha256": G.sha_file(r)} for r in spec["refs"]]
    n = G.normalise(spec)
    sig = G.signature(n, refs)
    job_id = f"{spec['id']}-{sig[:10]}"
    start_worker(runner)
    with _lock, _jobs_lock(proj):
        _interrupt_orphans(proj)
        cur = _load(proj, job_id)
        if cur and cur["state"] in ("queued", "running") and _owner_alive(cur.get("owner"), proj, job_id):
            where = "this process" if (cur.get("owner") or {}).get("pid") == os.getpid() else f"process {(cur.get('owner') or {}).get('pid')}"
            return {**cur, "note": f"same request already queued/running (owned by {where}); not started again"}
        if cur and not spec["regenerate"]:
            ent = G.load_manifest(proj)["assets"].get(spec["id"], {})
            if cur["state"] == "succeeded" and ent.get("signature") == sig:
                bad = G.file_problem(proj, ent)
                if bad:                                                  # a cached success is only reported while its file is really there
                    raise JobError(f"the stored result of this request is unusable: {bad}. Nothing was generated; "
                                   "submit with regenerate=true to create it again (this calls agy)")
                # "reused" in the record describes the original run; "reused_now" says this submit started nothing
                return {**cur, "reused_now": True, "new_generation": False, "note": "same request: stored result is used, no image was generated"}
            if cur["state"] in ("failed", "timeout") and cur.get("fail_count", 1) >= G.MAX_FAILS:
                return {**cur, "note": f"blocked: failed {cur['fail_count']} times; change the request or use regenerate=true"}
        import budget
        try:
            budget.check(proj, "images", 1)                              # a new image run must fit the project's limit; reuse/in-flight returned above
        except budget.BudgetError as e:
            raise JobError(str(e)) from e
        fails = (cur.get("fail_count", 0) if cur and cur["state"] in ("failed", "timeout") and not spec["regenerate"] else 0)
        job = {"job_id": job_id, "asset_id": spec["id"], "project": proj.name, "kind": spec["kind"], "prompt": spec["prompt"], "state": "queued",
               "requested_at": time.strftime("%Y-%m-%d %H:%M:%S"), "signature": sig, "timeout_seconds": spec["timeout"],
               "reference_images": [r["path"] for r in refs], "fail_count": fails, "run": (cur or {}).get("run", 0) + 1, "owner": _me()}
        _save(proj, job)
        _inflight.add(_key(proj, job_id))
    _q.put((proj, job_id, spec))
    return job


def check(project, job_id):
    proj = resolve_project(project)
    if not re.fullmatch(r"[a-z0-9_]{1,40}-[0-9a-f]{10}", str(job_id)):
        raise JobError("bad job_id")
    job = _load(proj, job_id)
    if job is None:
        raise JobError(f"unknown job {job_id!r}")
    if job["state"] in ("queued", "running"):
        if not _owner_alive(job.get("owner"), proj, job_id):
            _mark_interrupted(proj)                                         # only orphans change; a job owned by a live process stays as it is
            job = _load(proj, job_id)
    e = G.load_manifest(proj)["assets"].get(job["asset_id"]) or {}
    current = e.get("signature") == job["signature"]               # the manifest still holds THIS job's request
    if job["state"] in ("failed", "timeout") and current:
        job["fail_count"] = e.get("fail_count", job.get("fail_count", 1))
    if job["state"] == "succeeded":
        snap = job.get("snapshot")
        if snap is None and current:                               # record written before per-job snapshots existed
            snap = _snapshot(e)
        if not current:
            job["state"] = "superseded"
            job["error"] = "a newer request for this asset replaced this job's image; this job's result is not the asset any more"
            if snap:
                vf = snap.get("version_file")
                job["result"] = {**snap, "status": "superseded", "file": vf if vf and (proj / vf).is_file() else None}
            job["use_in_scene"] = "not usable: superseded by a newer request for the same asset id"
        else:
            bad = G.file_problem(proj, e)
            if bad:
                job["state"] = "invalid"
                job["error"] = f"{bad}. Nothing was regenerated; submit with regenerate=true to create it again (this calls agy)"
                job["use_in_scene"] = "not usable: the image file is missing or changed"
            else:
                st = G.approval_state(proj, job["asset_id"])[0]
                job["result"] = {**snap, "status": st}
                job["scene_item"] = ({"type": "prop", "img": f"ai:{job['asset_id']}", "x": 960, "y": 540, "scale": 1.0, "appear": 0.3}
                                     if e.get("kind") != "background" else None)
                job["use_in_scene"] = ("approved: usable in scenes as `ai:<asset_id>`" if st == "approved" else
                                       "changed after approval: approve again" if st == "changed_after_approval" else
                                       "draft: the owner must approve it first (agy_image.py approve <id> --by <name>); scenes refuse unapproved assets")
    job.pop("snapshot", None)
    return job
