"""One-command pipeline: voice -> assets -> scenes (EffectCraft) -> assembly (FilmCraft) -> checks, with a step log.
Usage: python run_all.py [--shirt "#2E86DE"] [--point-speed 0.3] [--out-dir D:/x] [--name file.mp4] [--redo-voice] [--work-dir D:/w]
Overrides apply to this run only (an effective config is written to <work>/run_config.json);
project/config.json is never modified. Everything else (voice, texts, cues) is in project/config.json."""
import argparse, hashlib, json, os, subprocess, sys, time
from pathlib import Path
T = Path(__file__).resolve().parent; ROOT = T.parent
sys.path.insert(0, str(T)); from common import load_config
cfg = load_config()
ap = argparse.ArgumentParser()
ap.add_argument("--shirt"); ap.add_argument("--point-speed", type=float); ap.add_argument("--out-dir"); ap.add_argument("--name")
ap.add_argument("--work-dir"); ap.add_argument("--redo-voice", action="store_true"); a = ap.parse_args()
if a.shirt: cfg["shirt"] = a.shirt
if a.point_speed is not None: cfg["pointSpeed"] = a.point_speed
if a.out_dir: cfg["outputDir"] = a.out_dir
if a.name: cfg["outputName"] = a.name
W = Path(a.work_dir) if a.work_dir else ROOT/"work"; (W/"audio").mkdir(parents=True, exist_ok=True)
rc = W/"run_config.json"; rc.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
os.environ["AF_CONFIG"] = str(rc); os.environ["AF_WORK"] = str(W)
out = Path(cfg["outputDir"])/cfg["outputName"]; out.parent.mkdir(parents=True, exist_ok=True)
logf = out.parent/"logs"/f"run_{time.strftime('%Y%m%d_%H%M%S')}.log"; logf.parent.mkdir(exist_ok=True)
def log(msg):
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"; print(line, flush=True)
    with logf.open("a", encoding="utf-8") as fh: fh.write(line + "\n")
def sh(label, *cmd):
    t0 = time.time(); log(f"START {label}")
    r = subprocess.run([sys.executable, *cmd], capture_output=True, text=True, encoding="utf-8", errors="replace")
    log(f"{'OK  ' if r.returncode == 0 else 'FAIL'} {label} ({time.time() - t0:.1f}s)")
    if r.returncode:
        log(f"--- stdout ---\n{r.stdout[-1200:]}\n--- stderr ---\n{r.stderr[-1200:]}"); log(f"STEP FAILED: {label}"); sys.exit(1)
    return r.stdout
log(f"config: shirt={cfg['shirt']} pointSpeed={cfg['pointSpeed']} out={out} work={W}")
for i in (1, 2):
    f = W/f"audio/scene{i}.mp3"; h = W/f"audio/scene{i}.hash"
    sig = hashlib.sha1(json.dumps([cfg["voice"], cfg["speed"], cfg[f"scene{i}"]["text"]], ensure_ascii=False).encode()).hexdigest()
    fresh = not (f.exists() and f.with_suffix(".words.json").exists() and h.exists() and h.read_text() == sig) or a.redo_voice
    if fresh:
        sh(f"voice scene{i} (paid API call)", str(T/"voice.py"), "tts", "--voice", cfg["voice"], "--text", cfg[f"scene{i}"]["text"], "--out", str(f), "--speed", str(cfg["speed"]))
        h.write_text(sig)
    else: log(f"SKIP voice scene{i}: text/voice unchanged, reusing audio (no API call)")
try: sh("audio verification (text == speech, not cut off)", str(T/"verify_audio.py"), str(W))
except SystemExit:
    for i in (1, 2): (W/f"audio/scene{i}.hash").unlink(missing_ok=True)      # force regeneration next run
    raise
sh("assets (VectorCraft)", str(T/"make_assets.py")); sh("scenes (EffectCraft)", str(T/"build_scenes.py")); sh("assembly (FilmCraft)", str(T/"build_film.py"))
FC = r"C:\Program Files\FilmCraft\filmcraft-cli.exe"; EC = r"C:\Program Files\EffectCraft\effectcraft-cli.exe"
ok = True
def check(name, cond, info=""):
    global ok; ok &= bool(cond); log(("PASS " if cond else "FAIL ") + name + " " + info)
r = subprocess.run([EC, "--project", str(W/"scenes.ecproj"), "script", str(T/"count_layers.jsx")], capture_output=True, text=True)
for c in [l for l in r.stdout.splitlines() if l.startswith("LAYERS")][0][7:].split(","):
    n, cnt, dup = c.split(":"); check(f"{n}: no duplicate layer names", dup == "0", f"({cnt} layers)")
seq = json.loads(subprocess.run([FC, "--project", str(W/"film.fcproj"), "inspect", "sequence", "--compact"], capture_output=True, text=True).stdout)
vid = sum(len(t["items"]) for t in seq["video"]); aud = sum(len(t["items"]) for t in seq["audio"])
check("timeline has exactly 2 video + 2 audio clips", (vid, aud) == (2, 2), f"(video {vid}, audio {aud})")
pr = json.loads(subprocess.run([FC, "probe", str(out), "--compact"], capture_output=True, text=True).stdout)
secs = pr["duration"] / 254016000000
check("output 1920x1080 with audio", pr["video"] and (pr["video"]["width"], pr["video"]["height"]) == (1920, 1080) and bool(pr["audio_streams"]))
check("duration within 20-30 s", 20 <= secs <= 30, f"({secs:.1f}s)")
log(f"OUTPUT {out} {secs:.1f}s  log: {logf}"); sys.exit(0 if ok else 1)
