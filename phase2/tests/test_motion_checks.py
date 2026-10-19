"""The motion checker must catch the faults it claims to catch (synthetic joint data, no rendering)."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import check_motion as C

GOOD = {"rootx": 700.0, "rooty": 975.0, "shL": 12.0, "elL": 4.0, "shR": -12.0, "elR": -4.0, "neck": 0.0, "waist": 0.0, "hipL": 0.0, "hipR": 0.0, "held": 0.0}


def rows(n=30, **over):
    out = []
    for i in range(n):
        r = dict(GOOD, f=i, t=i / 30)
        for k, fn in over.items():
            r[k] = fn(i) if callable(fn) else fn
        out.append(r)
    return out


def failed(rs):
    return [n for n, ok, _ in C.row_checks(rs) if not ok]


class T(unittest.TestCase):
    def test_idle_passes(self):
        self.assertEqual(failed(rows()), [])

    def test_snap_detected(self):
        self.assertTrue(any("snap" in n for n in failed(rows(shR=lambda i: -12.0 if i < 15 else 120.0))))

    def test_elbow_hyperextension_detected(self):
        self.assertTrue(any("joint limits" in n for n in failed(rows(elR=-200.0))))

    def test_elbow_flip_detected(self):
        self.assertTrue(any("flips" in n for n in failed(rows(elR=lambda i: -60.0 if i < 15 else 60.0))))

    def test_arm_through_torso_detected(self):
        # shoulder swung across the body so the hand ends up inside the torso block
        self.assertTrue(any("torso" in n for n in failed(rows(shR=-150.0, elR=-5.0, shL=90.0, elL=0.0)) + failed(rows(shR=60.0, elR=-5.0))))


if __name__ == "__main__":
    unittest.main(verbosity=2)
