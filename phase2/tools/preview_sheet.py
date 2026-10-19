"""Contact sheet of the assembled preview: for each scene, frames at given fractions of the scene. Usage: python preview_sheet.py PROJECT_DIR OUT.png 0.35 0.8"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

import toolpaths
FC = toolpaths.filmcraft()
proj, out = Path(sys.argv[1]), sys.argv[2]
fr = [float(x) for x in sys.argv[3:]] or [0.35, 0.8]
rep = json.loads((proj / "logs/build_report.json").read_text(encoding="utf-8"))
starts = rep["starts"]
sb = json.loads((proj / "storyboard.json").read_text(encoding="utf-8"))
film = proj / "render/film.fcproj"
tmp = Path(tempfile.mkdtemp())
font = ImageFont.truetype(toolpaths.font(), 18)
tiles = []
for i, sc in enumerate(sb["scenes"]):
    end = starts[i + 1] if i + 1 < len(starts) else None
    dur = (end - starts[i]) if end else 8
    for f in fr:
        t = starts[i] + dur * f
        p = tmp / f"{i}_{f}.png"
        r = subprocess.run([FC, "--project", str(film), "render", "--seconds", f"{t:.3f}", "--out", str(p), "--scale", "0.33"], capture_output=True)
        im = Image.open(p).convert("RGB")
        ImageDraw.Draw(im).text((6, 4), f"{sc['id']} t={t:.1f}s", fill=(200, 0, 0), font=font)
        tiles.append(im)
cols = len(fr) * 2 if len(fr) == 2 else 3
cols = 4 if len(fr) == 2 else 3
w, h = tiles[0].size
rows = (len(tiles) + cols - 1) // cols
sheet = Image.new("RGB", (cols * w, rows * h), (255, 255, 255))
for i, im in enumerate(tiles):
    sheet.paste(im, ((i % cols) * w, (i // cols) * h))
sheet.save(out)
print(out, sheet.size)
