"""Render a character preview (4 poses + 5 expressions) with the real EffectCraft builder.
  python char_preview.py CHAR_DIR OUT.png          (CHAR_DIR holds rig.json and png/)
The same call is used by the UI ("Xem nhân vật") and by the rig quality check, so what you see is what the scenes will animate."""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import build_motion_demo as B  # noqa: E402
import p2_svg as S  # noqa: E402


def render(char_dir, out_png, bg=None):
    char_dir = Path(char_dir)
    rig = json.loads((char_dir / "rig.json").read_text(encoding="utf-8")) if (char_dir / "rig.json").exists() else None
    tmp = Path(tempfile.mkdtemp(prefix="af_chprev_"))
    assets = tmp / "assets"
    (assets / "png").mkdir(parents=True)
    import shutil
    if rig:
        for f in (char_dir / "png").glob("*.png"):
            shutil.copy(f, assets / "png" / f.name)
    S.make_character(assets)                                       # Bi parts too (shown when no rig is given)
    proj = tmp / "preview.ecproj"
    pr = B.params(proj)
    pr["assets"] = str(assets).replace("\\", "/")
    pr["rig"] = rig
    jsx = tmp / "_preview.jsx"
    jsx.write_text("var P = " + json.dumps(pr, ensure_ascii=False) + ";\n" + B.jsx_text("bi_rig.jsx", "bi_motion.jsx", "char_preview.jsx"), encoding="utf-8")
    B.run_script(jsx)
    r = subprocess.run([B.EC, "--project", str(proj), "render-frame", "--comp", "Preview", "--time", "0", "--out", str(out_png)], capture_output=True, text=True, encoding="utf-8")
    if r.returncode:
        raise RuntimeError(r.stderr[-400:])
    shutil.rmtree(tmp, ignore_errors=True)
    return Path(out_png)


if __name__ == "__main__":
    print(render(sys.argv[1], sys.argv[2]))
