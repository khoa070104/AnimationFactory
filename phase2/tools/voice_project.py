"""Generate voice for a project's scenes. Paid API calls happen ONLY here, and only when:
  * the storyboard voice texts match the recorded approval (approval.json), and
  * the scene's (text, voice, speed) differ from what its existing audio was made from.
Unchanged scenes are never re-sent. POSTs are never auto-retried (see tools/voice.py). Every call is logged per project.
Usage: python voice_project.py PROJECT_DIR [--scenes s03,s04] [--dry-run]"""
import argparse
import hashlib
import json
import os
import shutil
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "tools"))
import approve  # noqa: E402
import audio_checks  # noqa: E402
import sbload  # noqa: E402

CREDITS_PER_CHAR = 0.725


def sig_of(sb, sc):
    v = sb["voice"]
    return hashlib.sha1(json.dumps([sc["voice"], v["voice_id"], float(v["speed"])], ensure_ascii=False).encode("utf-8")).hexdigest()


def cache_dir():
    return Path(os.environ.get("AF_VOICE_CACHE") or Path(__file__).resolve().parent.parent / "voice_cache")


def cache_seed():
    """Audio generated in ANY project becomes reusable: index every project's finished scene audio by its signature (default cache only)."""
    if os.environ.get("AF_VOICE_CACHE"):
        return
    c = cache_dir()
    c.mkdir(exist_ok=True)
    for sg in (Path(__file__).resolve().parent.parent / "projects").glob("*/audio/*.sig"):
        sig, mp3, wj = sg.read_text().strip(), sg.with_suffix(".mp3"), sg.with_suffix(".words.json")
        if sig.startswith("stub:"):
            continue                                                  # draft voice (voice_stub.py) is never shared as if it were real
        if mp3.exists() and wj.exists() and not (c / f"{sig}.mp3").exists():
            shutil.copy(mp3, c / f"{sig}.mp3")
            shutil.copy(wj, c / f"{sig}.words.json")


def cache_hit(sig):
    c = cache_dir()
    return (c / f"{sig}.mp3").exists() and (c / f"{sig}.words.json").exists()


def cache_copy_to(sig, f):
    c = cache_dir()
    shutil.copy(c / f"{sig}.mp3", f)
    shutil.copy(c / f"{sig}.words.json", f.with_suffix(".words.json"))


def cache_store(sig, f):
    c = cache_dir()
    c.mkdir(exist_ok=True)
    shutil.copy(f, c / f"{sig}.mp3")
    shutil.copy(f.with_suffix(".words.json"), c / f"{sig}.words.json")


def log_line(proj, msg):
    f = proj / "logs" / f"voice_{time.strftime('%Y%m%d')}.log"
    f.parent.mkdir(exist_ok=True)
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    with f.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def run(proj, only=None, dry=False, tts_fn=None, verify_fn=audio_checks.check_files):
    proj = Path(proj)
    sb = sbload.load_storyboard(proj)
    if not (proj / "approval.json").exists():
        sys.exit("REFUSED: no approval.json - the script has not been approved yet (no voice is generated before approval).")
    import actors
    ap_rec = json.loads((proj / "approval.json").read_text(encoding="utf-8"))
    cell = (ap_rec.get("kinds") or {}).get("script") or {"by": ap_rec.get("approved_by")}
    actor = cell.get("actor") or actors.classify(cell.get("by"))
    if not actors.counts_as_owner(actor):
        sys.exit(f"REFUSED: the script was approved by {actor['label']!r} ({actor['type']}); a test click or an AI label is not the owner's approval - the owner must approve the script before any paid voice call.")
    voice_changed, _ = approve.changes_since_approval(proj)
    if voice_changed:
        sys.exit(f"REFUSED: voice text/settings changed after approval in scenes {voice_changed}; please re-approve (approve.py) before generating.")
    audio = proj / "audio"
    audio.mkdir(exist_ok=True)
    os.environ["AF_WORK"] = str(proj / "work")
    (proj / "work").mkdir(exist_ok=True)
    todo = []
    for sc in sb["scenes"]:
        if only and sc["id"] not in only:
            continue
        f, sg = audio / f"{sc['id']}.mp3", audio / f"{sc['id']}.sig"
        fresh = f.exists() and f.with_suffix(".words.json").exists() and sg.exists() and sg.read_text() == sig_of(sb, sc)
        todo.append((sc, f, sg, fresh))
    cache_seed()
    cached = [t for t in todo if not t[3] and cache_hit(sig_of(sb, t[0]))]
    new_chars = sum(len(sc["voice"]) for sc, _, _, fresh in todo if not fresh and not cache_hit(sig_of(sb, sc)))
    log_line(proj, f"plan: {sum(1 for t in todo if not t[3]) - len(cached)} scene(s) to generate ({new_chars} chars, est. ~{round(new_chars * CREDITS_PER_CHAR)} credits), "
                   f"{len(cached)} from the shared voice cache (no API call), {sum(1 for t in todo if t[3])} unchanged (no API call)")
    if dry:
        return 0
    import budget
    try:
        budget.check(proj, "voice_credits", round(new_chars * CREDITS_PER_CHAR))   # refuse BEFORE the first paid call if the job does not fit the budget
    except budget.BudgetError as e:
        sys.exit(f"REFUSED: {e}")
    if tts_fn is None:
        import voice
        tts_fn = voice.tts
    calls = 0
    for sc, f, sg, fresh in todo:
        if fresh:
            log_line(proj, f"SKIP {sc['id']}: text/voice/speed unchanged, reusing audio (no API call)")
            continue
        sg.unlink(missing_ok=True)
        sig = sig_of(sb, sc)
        if cache_hit(sig):                                           # same text + voice + speed was already generated (this or another project)
            cache_copy_to(sig, f)
            ok, msg, _ = verify_fn(f, f.with_suffix(".words.json"), sc["voice"])
            log_line(proj, f"{'CACHE-HIT' if ok else 'FAIL'} {sc['id']}: reused stored audio, no API call. {msg}")
            if not ok:
                sys.exit(f"cached audio failed verification for {sc['id']}")
            sg.write_text(sig)
            continue
        log_line(proj, f"CALL {sc['id']} ({len(sc['voice'])} chars) -> paid API job")
        t0 = time.time()
        tts_fn(sc["voice"], sb["voice"]["voice_id"], str(f), float(sb["voice"]["speed"]))
        calls += 1
        ok, msg, _ = verify_fn(f, f.with_suffix(".words.json"), sc["voice"])
        log_line(proj, f"{'OK  ' if ok else 'FAIL'} {sc['id']} ({time.time() - t0:.1f}s) {msg}")
        if not ok:
            sys.exit(f"audio verification failed for {sc['id']}; stopped (no further calls). Fix and re-run: the job is not repeated unless the text changes.")
        sg.write_text(sig)
        cache_store(sig, f)
    update_status(proj, sb)
    return calls


def update_status(proj, sb):
    st = json.loads((proj / "status.json").read_text(encoding="utf-8"))
    log = proj / "work" / "api_calls.jsonl"
    entries = [json.loads(x) for x in log.read_text(encoding="utf-8").splitlines()] if log.exists() else []
    st["api_calls"] = len(entries)
    st["credits_spent"] = sum((e.get("credit_cost") or 0) + (e.get("transcript_cost") or 0) for e in entries)
    st["voice_generated"] = all((proj / "audio" / f"{s['id']}.sig").exists() for s in sb["scenes"])
    st["state"] = "voice_ready" if st["voice_generated"] else st.get("state", "content_approved")
    (proj / "status.json").write_text(json.dumps(st, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("project")
    ap.add_argument("--scenes")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    run(a.project, a.scenes.split(",") if a.scenes else None, a.dry_run)
