"""Build the 2-scene EffectCraft project and render each scene to MP4.
Timing comes from the voice's real word timestamps (work/audio/sceneN.words.json) via config cues."""
import argparse, json, subprocess, sys
from pathlib import Path
from common import ROOT, load_config, work_dir, cue_time
EC = r"C:\Program Files\EffectCraft\effectcraft-cli.exe"
FC = r"C:\Program Files\FilmCraft\filmcraft-cli.exe"
cfg = load_config(); W = work_dir()
ap = argparse.ArgumentParser(); ap.add_argument("--point-speed", type=float, default=cfg["pointSpeed"]); a = ap.parse_args()
def dur(f):
    out = subprocess.run([FC, "probe", str(f), "--compact"], capture_output=True, text=True, check=True).stdout
    return json.loads(out)["duration"] / 254016000000
d1, d2 = dur(W/"audio/scene1.mp3"), dur(W/"audio/scene2.mp3")
off = cfg["audioOffset"]; tail = cfg["tailSeconds"]
c1, c2 = cfg["scene1"], cfg["scene2"]
t = lambda n, ph: round(off + cue_time(W/f"audio/scene{n}.words.json", ph), 2)   # audio starts `off` s into the scene
proj = W/"scenes.ecproj"
P = {"assets": str(ROOT/"assets/png").replace("\\", "/"), "out": str(proj).replace("\\", "/"), "pointSpeed": a.point_speed,
     "s1": {"dur": round(off + d1 + tail, 2), "ting": t(1, c1["cues"]["ting"]), "cheer": t(1, c1["cues"]["cheer"]), "caption": c1["caption"]},
     "s2": {"dur": round(off + d2 + tail, 2), "worry": t(2, c2["cues"]["worry"]),
            "point": [t(2, p) for p in c2["cues"]["point"]], "end": t(2, c2["cues"]["end"]),
            "endCard": c2["endCard"], "caption": c2["caption"]}}
jsx = W/"scenes.jsx"
jsx.write_text("var P = " + json.dumps(P, ensure_ascii=False) + ";\n" + (Path(__file__).parent/"scenes_template.jsx").read_text(encoding="utf-8"), encoding="utf-8")
if proj.exists(): proj.unlink()   # always rebuild from empty -> no duplicate layers
r = subprocess.run([EC, "--empty", "script", str(jsx)], capture_output=True, text=True)
print(r.stdout, r.stderr); r.check_returncode()
for c in ("Scene1", "Scene2"):
    r = subprocess.run([EC, "--project", str(proj), "render", "--comp", c, "--out", str(W/f"{c}.mp4"), "--format", "h264", "--audio", "off"], capture_output=True, text=True)
    print(c, r.stdout[-200:], r.stderr[-200:]); r.check_returncode()
print("CUES", json.dumps({"s1": P["s1"], "s2": P["s2"]}, ensure_ascii=False))
