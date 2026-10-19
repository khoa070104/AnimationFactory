"""Calibrate the cost/speed model from REAL jobs in all projects -> phase2/cost_model.json.
credits_per_char = total (voice + transcript credits) / total characters of the jobs logged in projects/*/work/api_calls.jsonl
chars_per_sec    = characters / spoken seconds (first word start -> last word end) over all generated scenes.
Usage: python calibrate.py"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import cues as C

P2 = Path(__file__).resolve().parent.parent
chars = credits = 0
jobs = 0
spoken = spoken_chars = 0.0
for proj in sorted((P2 / "projects").iterdir()):
    log = proj / "work/api_calls.jsonl"
    if log.exists():
        for line in log.read_text(encoding="utf-8").splitlines():
            e = json.loads(line)
            if e.get("credit_cost") is None:
                continue
            jobs += 1
            chars += e["chars"]
            credits += (e["credit_cost"] or 0) + (e.get("transcript_cost") or 0)
    sbf = proj / "storyboard.json"
    if sbf.exists():
        sb = json.loads(sbf.read_text(encoding="utf-8"))
        for sc in sb["scenes"]:
            wj = proj / "audio" / f"{sc['id']}.words.json"
            if wj.exists():
                ws = C.words_of(wj)
                spoken += ws[-1]["end"] - ws[0]["start"]
                spoken_chars += len(sc["voice"])
if not jobs:
    sys.exit("no logged jobs yet; keeping defaults")
model = {"credits_per_char": round(credits / chars, 4), "chars_per_sec": round(spoken_chars / spoken, 2) if spoken else 12.0,
         "basis": f"{jobs} real Edge-voice jobs ({chars} chars, {credits} credits incl. word timings); {spoken_chars:.0f} chars over {spoken:.0f} s of speech",
         "updated": time.strftime("%Y-%m-%d")}
(P2 / "cost_model.json").write_text(json.dumps(model, ensure_ascii=False, indent=2), encoding="utf-8")
print(model)
