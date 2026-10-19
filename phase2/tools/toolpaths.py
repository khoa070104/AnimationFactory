"""Where the three CLIs and the preview font live. Nothing else in the tool hard-codes an install path.
Order: environment variable -> phase2/config.json {"paths": {...}} -> default install location.
  AF_EFFECTCRAFT, AF_FILMCRAFT, AF_VECTORCRAFT, AF_FONT          (python tools/toolpaths.py  shows what is used and whether it exists)"""
import json
import os
import sys
from pathlib import Path

P2 = Path(__file__).resolve().parent.parent
DEFAULTS = {"effectcraft": r"C:\Program Files\EffectCraft\effectcraft-cli.exe", "filmcraft": r"C:\Program Files\FilmCraft\filmcraft-cli.exe",
            "vectorcraft": r"C:\Program Files\VectorCraft\vectorcraft-cli.exe", "font": "C:/Windows/Fonts/arial.ttf"}


def font_bold():
    """Bold variant of the configured font (Arial Bold next to arial.ttf), else the font itself."""
    f = Path(get("font"))
    b = f.with_name(f.stem + "bd" + f.suffix)
    return b if b.exists() else f


def get(name):
    env = os.environ.get("AF_" + name.upper())
    if env:
        return env
    cfg = P2 / "config.json"
    if cfg.exists():
        v = json.loads(cfg.read_text(encoding="utf-8")).get("paths", {}).get(name)
        if v:
            return v
    return DEFAULTS[name]


def effectcraft():
    return get("effectcraft")


def filmcraft():
    return get("filmcraft")


def vectorcraft():
    return get("vectorcraft")


def font():
    return get("font")


if __name__ == "__main__":
    for n in DEFAULTS:
        p = get(n)
        print(f"{n:12s} {'OK     ' if Path(p).exists() else 'MISSING'} {p}")
    sys.exit(0 if all(Path(get(n)).exists() for n in DEFAULTS) else 1)
