"""Build the Bi v2 motion demo (all actions + chained transitions) and render MP4; optionally a debug project with markers.
Usage: python build_motion_demo.py [--debug] [--out-dir phase2/motion]"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import p2_svg as S

P2 = S.P2
TOK = S.TOK
import toolpaths
EC = toolpaths.effectcraft()
hexrgb = lambda h: [int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)]


def params(out_proj, debug=False, comp=None):
    return {"assets": str(P2 / "assets").replace("\\", "/"), "out": str(out_proj).replace("\\", "/"),
            "w": TOK["canvas"]["w"], "h": TOK["canvas"]["h"], "fps": TOK["canvas"]["fps"], "pngScale": TOK["pngScale"],
            "font": TOK["text"]["font"], "text": TOK["text"], "bg": hexrgb(TOK["bg"]), "bgAlt": hexrgb(TOK["bgAlt"]),
            "colors": {"bi": hexrgb(TOK["bi"])}, "debug": debug, "comp": comp}


def jsx_text(*files):
    return "\n".join((P2 / "lib" / f).read_text(encoding="utf-8") for f in files)


def run_script(path):
    r = subprocess.run([EC, "--empty", "script", str(path)], capture_output=True, text=True, encoding="utf-8")
    if r.returncode:
        sys.exit(f"EffectCraft script failed:\n{r.stdout[-1500:]}\n{r.stderr[-1500:]}")
    return r.stdout


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--debug", action="store_true")
    ap.add_argument("--out-dir", default=str(P2 / "motion"))
    a = ap.parse_args()
    out = Path(a.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    S.make_character()
    S.make_props()
    name = "motion_demo_debug" if a.debug else "motion_demo"
    proj = out / f"{name}.ecproj"
    proj.unlink(missing_ok=True)
    jsx = out / f"_{name}.jsx"
    jsx.write_text("var P = " + json.dumps(params(proj, a.debug), ensure_ascii=False) + ";\n"
                   + jsx_text("bi_rig.jsx", "bi_motion.jsx", "motion_demo.jsx"), encoding="utf-8")
    print(run_script(jsx))
    if not a.debug:
        mp4 = out / "motion_demo.mp4"
        r = subprocess.run([EC, "--project", str(proj), "render", "--comp", "MotionDemo", "--out", str(mp4), "--format", "h264", "--audio", "off"],
                           capture_output=True, text=True, encoding="utf-8")
        print((r.stdout + r.stderr)[-300:])
        r.check_returncode()


if __name__ == "__main__":
    main()
