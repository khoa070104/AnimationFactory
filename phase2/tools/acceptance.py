"""Acceptance criteria that are FIXED BEFORE a video is built, so a check can never be passed by loosening it afterwards.

  lock(proj, by)                 record the current targets (duration window, scene range) and the cue tolerance in PROJECT/acceptance.json (first lock only; kept)
  problems(proj, targets)        [] when the targets used for a build are the locked ones; otherwise the change is reported unless the OWNER accepted it
  accept_change(proj, by, why)   the owner explicitly accepts the CURRENT (changed) criteria; logged in the file's history

The lock happens automatically when the script is approved (approve.record) and when a build runs without one (first build = the targets it is judged by).
build_video adds a check "criteria were fixed before the build" (pass = unchanged, or changed and accepted by the owner, with the reason shown)."""
import json
import time
from pathlib import Path

import agy_image as G

DEFAULT_CUE_TOLERANCE = 0.7          # seconds an action may start later than the spoken cue (after non-overlap scheduling)


def path(proj):
    return Path(proj) / "acceptance.json"


def load(proj):
    return G.read_json(path(proj))


def current(sb_targets, cue_tol=DEFAULT_CUE_TOLERANCE):
    return {"duration": list(sb_targets["duration"]), "scenes": list(sb_targets["scenes"]), "cue_tolerance": cue_tol}


def lock(proj, targets, by="tool", cue_tol=DEFAULT_CUE_TOLERANCE):
    if load(proj):
        return load(proj)
    rec = {"criteria": current(targets, cue_tol), "locked_by": by, "locked_at": time.strftime("%Y-%m-%d %H:%M:%S"), "history": []}
    G.write_json_atomic(path(proj), rec)
    return rec


def problems(proj, targets):
    rec = load(proj)
    if not rec:
        return []
    now = current(targets, rec["criteria"].get("cue_tolerance", DEFAULT_CUE_TOLERANCE))
    if now == rec["criteria"]:
        return []
    acc = rec.get("accepted")
    if acc and acc.get("criteria") == now:
        return []
    return [f"criteria changed after they were fixed: locked {rec['criteria']} (by {rec['locked_by']}, {rec['locked_at']}) vs now {now}; the owner must accept the change (acceptance.accept_change)"]


def accept_change(proj, by, why, targets):
    rec = load(proj)
    if not rec:
        raise ValueError("no criteria locked yet")
    if not str(why).strip():
        raise ValueError("say why the criteria changed")
    now = current(targets, rec["criteria"].get("cue_tolerance", DEFAULT_CUE_TOLERANCE))
    rec["accepted"] = {"by": by, "why": why, "at": time.strftime("%Y-%m-%d %H:%M:%S"), "criteria": now}
    rec["history"].append({**rec["accepted"], "from": rec["criteria"]})
    G.write_json_atomic(path(proj), rec)
    return rec
