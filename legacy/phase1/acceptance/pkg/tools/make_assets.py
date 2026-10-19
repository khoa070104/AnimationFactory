"""Generate character/prop SVGs, then convert each to PNG with vectorcraft-cli.
Usage: python make_assets.py [--shirt "#F26B21"]"""
import argparse, subprocess
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
VC = r"C:\Program Files\VectorCraft\vectorcraft-cli.exe"
from common import load_config
cfg = load_config()
ap = argparse.ArgumentParser(); ap.add_argument("--shirt", default=cfg["shirt"]); a = ap.parse_args()
K, SK = "#1d1d1f", "#FFE3C2"
def svg(w, h, body):
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">{body}</svg>'
ln = f'stroke="{K}" stroke-width="10" stroke-linecap="round" stroke-linejoin="round"'
parts = {
 "head": svg(220,220, f'<circle cx="110" cy="110" r="100" fill="{SK}" {ln}/>'),
 "face_happy": svg(220,220, f'<circle cx="75" cy="95" r="9" fill="{K}"/><circle cx="145" cy="95" r="9" fill="{K}"/><path d="M65 130 Q110 180 155 130 Z" fill="#fff" {ln}/>'),
 "face_worried": svg(220,220, f'<circle cx="75" cy="105" r="9" fill="{K}"/><circle cx="145" cy="105" r="9" fill="{K}"/><path d="M55 95 L95 78 M165 95 L125 78" {ln} fill="none"/><path d="M75 160 Q110 130 145 160" fill="none" {ln}/>'),
 "face_normal": svg(220,220, f'<circle cx="75" cy="100" r="9" fill="{K}"/><circle cx="145" cy="100" r="9" fill="{K}"/><path d="M80 145 L140 145" fill="none" {ln}/>'),
 "torso": svg(170,220, f'<rect x="10" y="10" width="150" height="200" rx="40" fill="{a.shirt}" {ln}/>'),
 "legs": svg(170,200, f'<path d="M60 5 L50 190 M110 5 L120 190" fill="none" {ln}/><path d="M30 190 L55 190 M115 190 L145 190" fill="none" {ln}/>'),
 "arm": svg(50,200, f'<path d="M25 20 L25 165" fill="none" {ln}/><circle cx="25" cy="175" r="14" fill="{SK}" {ln}/>'),
 "phone": svg(300,520, f'<rect x="10" y="10" width="280" height="500" rx="36" fill="#2b2f3a" {ln}/><rect x="30" y="50" width="240" height="420" rx="12" fill="#f7fbff"/>'),
 "coin": svg(80,80, f'<circle cx="40" cy="40" r="32" fill="#ffc83d" {ln}/><text x="40" y="52" font-size="34" text-anchor="middle" fill="{K}" font-family="sans-serif">$</text>'),
}
for n, s in parts.items():
    f = ROOT/"assets/svg"/f"{n}.svg"; f.write_text(s, encoding="utf-8")
    subprocess.run([VC, "convert", str(f), str(ROOT/"assets/png"/f"{n}.png")], check=True, capture_output=True)
print("ok", list(parts))
