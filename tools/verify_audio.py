"""Audio checks per scene. Fails (exit 1) when:
  - the words the voice engine spoke differ from the text sent;
  - the DECODED audio (not file metadata) is shorter than its last spoken word (audio cut off / truncated) or word timings are missing;
  - more than 1.5 s of trailing silence follows the last word (wrong or padded file).
Usage: python verify_audio.py WORKDIR   (uses AF_CONFIG or project/config.json)"""
import json, re, subprocess, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent)); from common import load_config
from decode_check import decoded_seconds
FC = r"C:\Program Files\FilmCraft\filmcraft-cli.exe"; TICKS = 254016000000
norm = lambda s: re.sub(r"[^\w]+", " ", s.lower()).split()
TOL_BEFORE_END = 0.15      # a word may end at most this far past the audio's end (container rounding)
MAX_TAIL = 1.5             # max silence after the last word

def check_scene(work, cfg, i):
    mp3 = work/f"audio/scene{i}.mp3"; wj = work/f"audio/scene{i}.words.json"
    if not mp3.exists() or not wj.exists(): return False, f"scene{i}: missing audio or word timings"
    words = json.loads(wj.read_text(encoding="utf-8"))[0]["words"]
    real = [w for w in words if w["type"] == "word"]
    if not real: return False, f"scene{i}: no word timings"
    spoken, sent = norm(" ".join(w["text"] for w in real)), norm(cfg[f"scene{i}"]["text"])
    pr = json.loads(subprocess.run([FC, "probe", str(mp3), "--compact"], capture_output=True, text=True).stdout)
    meta = pr["duration"] / TICKS
    dur = decoded_seconds(mp3)                      # authoritative: length after actually decoding the audio
    last = max(w["end"] for w in real)
    problems = []
    if abs(dur - meta) > 0.3: problems.append(f"file metadata says {meta:.2f}s but decoded audio is {dur:.2f}s")
    if spoken != sent: problems.append("spoken words differ from text sent")
    if last > dur + TOL_BEFORE_END: problems.append(f"audio CUT OFF: last word ends {last:.2f}s but file is {dur:.2f}s")
    if dur - last > MAX_TAIL: problems.append(f"{dur - last:.2f}s of trailing silence after last word")
    msg = f"scene{i}: {len(sent)} words | last word ends {last:.2f}s, file {dur:.2f}s"
    return not problems, msg + ("" if not problems else " | FAIL: " + "; ".join(problems))

def main(work):
    cfg = load_config(); ok = True
    for i in (1, 2):
        good, msg = check_scene(Path(work), cfg, i); ok &= good; print(("PASS " if good else "FAIL ") + msg)
    print("ALL AUDIO CHECKS PASS" if ok else "AUDIO CHECK FAILED"); return 0 if ok else 1

if __name__ == "__main__":
    try: sys.stdout.reconfigure(encoding="utf-8")
    except Exception: pass
    sys.exit(main(sys.argv[1]))
