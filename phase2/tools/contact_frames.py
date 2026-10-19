"""Render frames of a comp at given times and tile them into one image. Usage: python contact_frames.py PROJ COMP OUT.png t1 t2 ..."""
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw

import toolpaths
EC = toolpaths.effectcraft()
proj, comp, out = sys.argv[1:4]
times = [float(t) for t in sys.argv[4:]]
tmp = Path(tempfile.mkdtemp())
tiles = []
for i, t in enumerate(times):
    f = tmp / f"{i}.png"
    subprocess.run([EC, "--project", proj, "render-frame", "--comp", comp, "--time", str(t), "--scale", "0.3", "--out", str(f)], capture_output=True, check=True)
    im = Image.open(f).convert("RGB")
    ImageDraw.Draw(im).text((6, 4), f"t={t:.2f}", fill=(200, 0, 0))
    tiles.append(im)
cols = 4
w, h = tiles[0].size
rows = (len(tiles) + cols - 1) // cols
sheet = Image.new("RGB", (cols * w, rows * h), (255, 255, 255))
for i, im in enumerate(tiles):
    sheet.paste(im, ((i % cols) * w, (i // cols) * h))
sheet.save(out)
print(out, sheet.size)
