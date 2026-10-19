"""Record an approval bound to the exact version approved (per-scene hashes), by KIND.
  script      the spoken text + voice settings of every scene (what is sent to the paid voice API)
  storyboard  the visual definition of every scene (layout, character, actions, items, background, timing)
  all         both (default; what the older one-button approval did)
Later edits show up as 'changed since approval' for exactly the affected scenes and part (voice / scene) and block the paid step that depends on it.
Every approval is also appended to PROJECT/approvals_history.jsonl (who, when, what version, which hashes).
Usage: python approve.py PROJECT_DIR --by "chủ dự án" [--kind script|storyboard|all] --note "..." """
import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

KINDS = ("script", "storyboard", "all")


def voice_hash(sb, sc):
    v = sb["voice"]
    return hashlib.sha256(json.dumps([sc["voice"], v["voice_id"], float(v["speed"])], ensure_ascii=False).encode("utf-8")).hexdigest()


def scene_hash(sc):
    return hashlib.sha256(json.dumps(sc, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


def history_file(proj):
    return Path(proj) / "approvals_history.jsonl"


def log_history(proj, row):
    with history_file(proj).open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({"at": time.strftime("%Y-%m-%d %H:%M:%S"), **row}, ensure_ascii=False) + "\n")


def history(proj):
    f = history_file(proj)
    out = []
    if f.exists():
        for line in f.read_text(encoding="utf-8").splitlines():
            try:
                out.append(json.loads(line))
            except ValueError:
                pass
    return out


def changes_since_approval(proj):
    """-> (voice_changed_scene_ids, visual_changed_scene_ids); a part that was never approved counts as changed."""
    proj = Path(proj)
    sb = json.loads((proj / "storyboard.json").read_text(encoding="utf-8"))
    ap = json.loads((proj / "approval.json").read_text(encoding="utf-8"))
    vc, sc_ch = [], []
    for sc in sb["scenes"]:
        a = ap["scenes"].get(sc["id"]) or {}
        if a.get("voice_sha256") != voice_hash(sb, sc):
            vc.append(sc["id"])
        if a.get("scene_sha256") != scene_hash(sc):
            sc_ch.append(sc["id"])
    for sid in ap["scenes"]:
        if sid not in [s["id"] for s in sb["scenes"]]:
            vc.append(sid)
    return vc, sc_ch


def record(proj, by, kind="all", note="", via="cli", verified=False):
    """Write the approval of `kind` for the CURRENT storyboard. Returns the approval record."""
    proj = Path(proj)
    if kind not in KINDS:
        raise ValueError(f"kind must be one of {KINDS}")
    sb = json.loads((proj / "storyboard.json").read_text(encoding="utf-8"))
    if not sb.get("scenes"):
        raise ValueError("there is no storyboard to approve yet")
    f = proj / "approval.json"
    ap = json.loads(f.read_text(encoding="utf-8")) if f.exists() else {"scenes": {}, "kinds": {}}
    ap.setdefault("kinds", {})
    ap["scenes"] = {sid: v for sid, v in ap["scenes"].items() if sid in [s["id"] for s in sb["scenes"]]}
    now = time.strftime("%Y-%m-%d")
    import actors
    actor = actors.classify(by, via, verified)
    for sc in sb["scenes"]:
        cell = ap["scenes"].setdefault(sc["id"], {})
        if kind in ("script", "all"):
            cell["voice_sha256"] = voice_hash(sb, sc)
        if kind in ("storyboard", "all"):
            cell["scene_sha256"] = scene_hash(sc)
    for k in (("script", "storyboard") if kind == "all" else (kind,)):
        ap["kinds"][k] = {"version": sb["version"], "by": by, "on": now, "note": note, "actor": actor}
    ap.update({"project": sb["project"], "storyboard_version": sb["version"], "approved_by": by, "approved_on": now, "note": note,
               "recorded_by": "ghi nhận qua công cụ theo người duyệt",
               "scope": "nội dung (lời đọc, cảnh, số liệu) và giọng đọc/tốc độ; chưa gồm chuyển động và video"})
    f.write_text(json.dumps(ap, ensure_ascii=False, indent=2), encoding="utf-8")
    import acceptance
    import sbload
    acceptance.lock(proj, sbload.targets(sb), by)                   # the pass/fail criteria are fixed no later than the first approval
    if kind in ("storyboard", "all"):
        import sbstore
        for sc in sb["scenes"]:
            sbstore.review_clear(proj, sc["id"])                    # approving the storyboard = the owner looked at flagged cue changes
    st_f = proj / "status.json"
    st = json.loads(st_f.read_text(encoding="utf-8")) if st_f.exists() else {}
    st.setdefault("approved", {})
    st["approved"]["content"] = {"version": sb["version"], "by": by, "on": now}
    for k in (("script", "storyboard") if kind == "all" else (kind,)):
        st["approved"][k] = {"version": sb["version"], "by": by, "on": now}
    st["storyboard_version"] = sb["version"]
    st["state"] = "content_approved"
    st_f.write_text(json.dumps(st, ensure_ascii=False, indent=2), encoding="utf-8")
    log_history(proj, {"kind": kind, "by": by, "actor": actor, "note": note, "version": sb["version"],
                       "storyboard_sha256": hashlib.sha256((proj / "storyboard.json").read_bytes()).hexdigest(),
                       "scenes": {sc["id"]: {"voice": voice_hash(sb, sc)[:12], "scene": scene_hash(sc)[:12]} for sc in sb["scenes"]}})
    return ap


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("project")
    ap.add_argument("--by", required=True)
    ap.add_argument("--kind", choices=KINDS, default="all")
    ap.add_argument("--note", default="")
    ap.add_argument("--via", default="cli")
    a = ap.parse_args()
    rec = record(Path(a.project), a.by, a.kind, a.note, a.via)
    print("approved", rec["project"], a.kind, "v", rec["storyboard_version"], len(rec["scenes"]), "scenes")


if __name__ == "__main__":
    sys.exit(main())
