"""Approved Bi v2.1 baseline must not drift.
1) every frozen file still matches MANIFEST.sha256;
2) rebuilding the three style frames with the CURRENT rig/asset code is pixel-identical to approved/bi_v2.1/frames."""
import hashlib
import subprocess
import sys
import unittest
from pathlib import Path

from PIL import Image, ImageChops

P2 = Path(__file__).resolve().parent.parent
BASE = P2 / "approved/bi_v2.1"


class T(unittest.TestCase):
    def test_manifest(self):
        bad = []
        for line in (BASE / "MANIFEST.sha256").read_text(encoding="utf-8").splitlines():
            h, p = line.split("  ", 1)
            if hashlib.sha256((BASE / p).read_bytes()).hexdigest() != h:
                bad.append(p)
        self.assertEqual(bad, [], "frozen baseline files were modified")

    def test_current_code_reproduces_approved_frames(self):
        r = subprocess.run([sys.executable, str(P2 / "tools/build_style_frames.py")], capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(r.returncode, 0, r.stderr[-500:])
        for i in (1, 2, 3):
            a = Image.open(BASE / f"frames/frame0{i}.png").convert("RGB")
            b = Image.open(P2 / f"style/frames/frame0{i}.png").convert("RGB")
            self.assertEqual(a.size, b.size)
            self.assertIsNone(ImageChops.difference(a, b).getbbox(), f"frame0{i} differs from the approved baseline")


if __name__ == "__main__":
    unittest.main(verbosity=2)
