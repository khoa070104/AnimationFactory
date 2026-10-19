"""Assemble Scene1/Scene2 clips + voice audio in FilmCraft and export the preview MP4.
Usage: python build_film.py [--out output/preview.mp4]"""
import argparse, json, subprocess
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
FC = r"C:\Program Files\FilmCraft\filmcraft-cli.exe"
TICKS = 254016000000
from common import load_config, work_dir
cfg = load_config()
ap = argparse.ArgumentParser(); ap.add_argument("--out", default=str(Path(cfg["outputDir"])/cfg["outputName"])); a = ap.parse_args()
w = work_dir()
def probe(f):
    r = subprocess.run([FC, "probe", str(f), "--compact"], capture_output=True, text=True, check=True)
    return json.loads(r.stdout)["duration"] / TICKS
v1, v2 = probe(w/"Scene1.mp4"), probe(w/"Scene2.mp4")
proj = w/"film.fcproj"
if proj.exists(): proj.unlink()                  # rebuild from scratch -> no duplicate clips
def run(lines, *opts):
    r = subprocess.run([FC, *opts, "run", "-"], input="\n".join(json.dumps(l) for l in lines), capture_output=True, text=True)
    res = [json.loads(x) for x in r.stdout.splitlines() if x.startswith("{")]
    bad = [x for x in res if not x.get("ok")]
    if bad or r.returncode: raise SystemExit(f"FilmCraft failed: {bad or r.stderr}")
    return res
files = [w/"Scene1.mp4", w/"Scene2.mp4", w/"audio/scene1.mp3", w/"audio/scene2.mp3"]
res = run([{"id": "file.newSequence", "params": {"name": "Main", "width": 1920, "height": 1080, "fps": 30}},
           {"id": "file.import", "params": {"paths": [str(f).replace("\\", "/") for f in files]}}], "--save-as", str(proj))
ids = res[1]["result"]["items"]; print("items", ids)
v1id, v2id, a1id, a2id = ids
t2 = v1   # scene 2 starts when scene 1 ends
place = [{"id": "timeline.place", "params": {"item": v1id, "track": "V1", "seconds": 0, "audio": False}},
         {"id": "timeline.place", "params": {"item": v2id, "track": "V1", "seconds": t2, "audio": False}},
         {"id": "timeline.place", "params": {"item": a1id, "audioTrack": "A1", "seconds": cfg["audioOffset"], "video": False}},
         {"id": "timeline.place", "params": {"item": a2id, "audioTrack": "A1", "seconds": t2 + cfg["audioOffset"], "video": False}}]
run(place, "--project", str(proj), "--save")
Path(a.out).parent.mkdir(parents=True, exist_ok=True)
r = subprocess.run([FC, "--project", str(proj), "export", a.out, "--format", "h264"], capture_output=True, text=True)
print(r.stdout[-300:], r.stderr[-300:]); r.check_returncode()
