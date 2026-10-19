"""ONE command from approved data to MP4:  validate -> storyboard (previews, estimate, docs) -> voice (gated, paid) -> video.
  python produce.py PROJECT_DIR                 run everything that is allowed (stops at the approval gate before any paid call)
  python produce.py PROJECT_DIR --until storyboard    stop after previews/estimate (what you review before approving)
  python produce.py PROJECT_DIR --dry-run       show what would be sent to the voice API
Progress and the failing step are written to PROJECT/status.json ("steps") and PROJECT/logs/produce_*.log.
Approval is never given by this script: record it with approve.py after the owner approves."""
import argparse
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

T = Path(__file__).resolve().parent
P2 = T.parent
STEPS = ["validate", "storyboard", "voice", "video"]


def code_hash():
    h = hashlib.sha256()
    for f in sorted(list((P2 / "tools").glob("*.py")) + list((P2 / "lib").glob("*.jsx"))):
        h.update(f.name.encode() + f.read_bytes())
    return h.hexdigest()[:16]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("project")
    ap.add_argument("--until", choices=STEPS, default="video")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--draft", action="store_true", help="build a DRAFT with stub (silent) voice: no approval needed, no paid call, output marked as draft")
    ap.add_argument("--force", action="store_true", help="re-render every scene (no cache)")
    ap.add_argument("--renderer", choices=["craft", "remotion"], default=None, help="video renderer (default: the project brief's `renderer`, else craft)")
    ap.add_argument("--freeze-code", action="store_true", help="record the current tool-code hash in the project status")
    a = ap.parse_args()
    proj = Path(a.project).resolve()
    try:
        _brief = json.loads((proj / "brief.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        _brief = {}
    renderer = a.renderer or _brief.get("renderer") or "craft"
    VIDEO_TOOL = T / ("build_remotion.py" if renderer == "remotion" else "build_video.py")
    (proj / "logs").mkdir(exist_ok=True)
    logf = proj / "logs" / f"produce_{time.strftime('%Y%m%d_%H%M%S')}.log"
    stf = proj / "status.json"
    st = json.loads(stf.read_text(encoding="utf-8")) if stf.exists() else {"project": proj.name}
    st["steps"] = {s: {"state": "pending"} for s in STEPS}
    st["code_hash"] = code_hash()
    if a.freeze_code:                      # evidence that a project was produced WITHOUT touching the tool code
        st["frozen_code_hash"] = st["code_hash"]
        st["code_changed_since_freeze"] = False
    elif st.get("frozen_code_hash") and st["frozen_code_hash"] != st["code_hash"]:
        st["code_changed_since_freeze"] = True

    def save():
        stf.write_text(json.dumps(st, ensure_ascii=False, indent=2), encoding="utf-8")

    def log(m):
        line = f"[{time.strftime('%H:%M:%S')}] {m}"
        print(line, flush=True)
        with logf.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")

    def run(step, *cmd, ok_codes=(0,)):
        st["steps"][step] = {"state": "running"}
        save()
        t0 = time.time()
        r = subprocess.run([sys.executable, *map(str, cmd)], capture_output=True, text=True, encoding="utf-8", errors="replace")
        for k, v in json.loads(stf.read_text(encoding="utf-8")).items():       # keep what the step itself recorded (credits, last_build...)
            if k != "steps":
                st[k] = v
        out = (r.stdout + r.stderr).strip()
        for line in out.splitlines()[-12:]:
            log("   " + line)
        ok = r.returncode in ok_codes
        st["steps"][step] = {"state": "ok" if ok else "failed", "seconds": round(time.time() - t0, 1)}
        if not ok:
            st["steps"][step]["error"] = "\n".join(out.splitlines()[-6:])
            st["state"] = f"failed_at_{step}"
        save()
        log(f"{'OK  ' if ok else 'FAIL'} {step} ({time.time() - t0:.1f}s)")
        return ok

    log(f"produce {proj.name} until={a.until} code_hash={st['code_hash']}")
    if not run("validate", T / "validate_storyboard.py", proj, *(["--draft"] if a.draft else [])):
        return 1
    if not run("storyboard", T / "build_storyboard.py", proj):
        return 1
    if a.draft:                            # review motion/layout/timing for free; the paid voice step never runs in this mode
        import voice_stub
        log(f"draft voice (no paid call) for: {voice_stub.run(proj) or 'nothing (already stubbed or real)'}")
        if not run("video", VIDEO_TOOL, proj, "--draft", *(["--force"] if a.force else [])):
            return 1
        st["state"] = "draft_built"
        save()
        log("DONE (draft: stub voice)")
        return 0
    est = json.loads((proj / "estimate.json").read_text(encoding="utf-8"))["total"]
    log(f"estimate: {est['chars']} chars, ~{est['sec']} s, ~{est['credits']} credits")
    if STEPS.index(a.until) <= STEPS.index("storyboard"):
        st["state"] = "storyboard_ready"
        save()
        return 0
    if not (proj / "approval.json").exists():
        st["steps"]["voice"] = {"state": "waiting", "reason": "no approval.json: the owner has not approved this version"}
        st["state"] = "awaiting_approval"
        save()
        log("STOP: waiting for the owner's approval (no paid call made). Review storyboard.md, then record it with approve.py")
        return 2
    if not run("voice", T / "voice_project.py", proj, *(["--dry-run"] if a.dry_run else [])):
        return 1
    if a.dry_run:
        return 0
    import approve
    _, scene_changed = approve.changes_since_approval(proj)
    if scene_changed:                      # the visuals of these scenes were never approved, or changed after approval: no video until the owner approves them
        st["steps"]["video"] = {"state": "waiting", "reason": f"storyboard (hình/hành động) chưa duyệt hoặc đã đổi sau khi duyệt: {', '.join(scene_changed)}"}
        st["state"] = "awaiting_storyboard_approval"
        save()
        log(f"STOP: waiting for the owner's approval of the storyboard for scenes {scene_changed} (voice is ready; no video built)")
        return 2
    if not run("video", VIDEO_TOOL, proj, *(["--force"] if a.force else [])):
        return 1
    st["state"] = "preview_built"
    save()
    log("DONE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
