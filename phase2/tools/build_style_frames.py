"""Build the 3 style frames with the Bi v2 rig in EffectCraft and render 1920x1080 PNGs.
Usage: python build_style_frames.py"""
import json, subprocess, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import p2_svg as S
P2 = S.P2; TOK = S.TOK
import toolpaths
EC = toolpaths.effectcraft()
out = P2 / "style"; out.mkdir(exist_ok=True); (out / "frames").mkdir(exist_ok=True)

S.make_character(); S.make_props()
# data-driven props: bars sized from values (60 px per million)
data = [("Nhà", "5tr", 5.0, S.A["blue"]), ("Ăn uống", "3tr", 3.0, S.A["yellow"]), ("Mua sắm", "2,5tr", 2.5, S.A["pink"]), ("Khác", "1,5tr", 1.5, S.A["teal"])]
bars = []
for i, (lab, val, v, col) in enumerate(data):
    h = int(v * 60 + 20)
    S.ensure_png(f"bar_{i}", S.bar(col, 120, h))
    bars.append({"label": lab, "value": val, "h": h})
hexrgb = lambda h: [int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)]
params = {"assets": str(P2 / "assets").replace("\\", "/"), "out": str(out / "style_frames.ecproj").replace("\\", "/"),
          "w": TOK["canvas"]["w"], "h": TOK["canvas"]["h"], "fps": TOK["canvas"]["fps"], "pngScale": TOK["pngScale"],
          "font": TOK["text"]["font"], "text": TOK["text"], "bg": hexrgb(TOK["bg"]), "bgAlt": hexrgb(TOK["bgAlt"]),
          "colors": {"bi": hexrgb(TOK["bi"])}, "bars": bars}
jsx = P2 / "style/_build.jsx"
jsx.write_text("var P = " + json.dumps(params, ensure_ascii=False) + ";\n" + (P2 / "lib/bi_rig.jsx").read_text(encoding="utf-8") + "\n"
               + (P2 / "lib/style_frames.jsx").read_text(encoding="utf-8"), encoding="utf-8")
proj = out / "style_frames.ecproj"
proj.unlink(missing_ok=True)
r = subprocess.run([EC, "--empty", "script", str(jsx)], capture_output=True, text=True)
print(r.stdout, r.stderr[-800:])
r.check_returncode()
for i in (1, 2, 3):
    r = subprocess.run([EC, "--project", str(proj), "render-frame", "--comp", f"Frame0{i}", "--time", "0", "--out", str(out / f"frames/frame0{i}.png")], capture_output=True, text=True)
    print(r.stderr.strip()[-120:]); r.check_returncode()
