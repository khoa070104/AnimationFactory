"""Audio QA for one scene file (same rules as Phase 1 verify_audio, but path-based).
Fails when: spoken words != text sent; decoded audio shorter than the last spoken word (cut off); metadata disagrees with decoded
length; > 1.5 s of silence after the last word; missing files/timings."""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import decode_check  # noqa: E402  (render through FilmCraft, measure the WAV)

TOL_BEFORE_END = 0.15
MAX_TAIL = 1.5
norm = lambda s: re.sub(r"[^\w]+", " ", s.lower()).split()


def check_files(mp3, words_json, text):
    mp3, words_json = Path(mp3), Path(words_json)
    if not mp3.exists() or not words_json.exists():
        return False, "missing audio or word timings", None
    words = json.loads(words_json.read_text(encoding="utf-8"))[0]["words"]
    real = [w for w in words if w["type"] == "word"]
    if not real:
        return False, "no word timings", None
    meta = decode_check.probe_seconds(mp3)
    dur = decode_check.decoded_seconds(mp3)
    last = max(w["end"] for w in real)
    problems = []
    if norm(" ".join(w["text"] for w in real)) != norm(text):
        problems.append("spoken words differ from text sent")
    if abs(dur - meta) > 0.3:
        problems.append(f"metadata {meta:.2f}s vs decoded {dur:.2f}s")
    if last > dur + TOL_BEFORE_END:
        problems.append(f"audio CUT OFF: last word ends {last:.2f}s but audio is {dur:.2f}s")
    if dur - last > MAX_TAIL:
        problems.append(f"{dur - last:.2f}s trailing silence")
    msg = f"{len(norm(text))} words | last word {last:.2f}s, audio {dur:.2f}s" + ("" if not problems else " | FAIL: " + "; ".join(problems))
    return not problems, msg, dur
