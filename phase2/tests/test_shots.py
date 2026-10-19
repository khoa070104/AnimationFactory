"""Shots: timing rules, structured problems (code / shot_id / field), framing from the size of what is looked at, camera continuity, gaze."""
import sys
import unittest
from pathlib import Path

P2 = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(P2 / "tools"))
import cues  # noqa: E402
import shots as SH  # noqa: E402

VOICE = "Linh cười: lập thực đơn tuần đấy. Mười phút thôi."
SC = {"id": "s1", "voice": VOICE, "bi": {"x": 400, "y": 960, "scale": 1.0}, "cast": [{"char": "linh", "x": 1520, "y": 960, "scale": 1.0}],
      "items": [{"type": "prop", "img": "board", "x": 960, "y": 400, "scale": 0.6}, {"type": "text", "text": "Mẹo", "x": 960, "y": 200, "size": 46}]}
has = lambda v, p: p.lower() in v.lower()
T = lambda ph: 2.0 if ph == "lập thực đơn" else 4.0


def codes(shots):
    return [(p["code"], p["shot_id"], p["field"]) for p in SH.problems({**SC, "shots": shots}, has)]


class T1(unittest.TestCase):
    def test_timing_rules_are_machine_readable_and_point_at_the_field(self):
        self.assertEqual(codes([{"id": "a", "start": 0}, {"id": "b", "start": "lập thực đơn"}]), [])
        self.assertIn(("CUE_NOT_IN_VOICE", "b", "start"), codes([{"id": "a", "start": 0}, {"id": "b", "start": "một cụm không có"}]))
        self.assertIn(("SHOTS_NOT_INCREASING", "b", "start"), codes([{"id": "a", "start": 3}, {"id": "b", "start": 2}]))
        self.assertIn(("SHOT_OVERLAP", "a", "end"), codes([{"id": "a", "start": 0, "end": 5}, {"id": "b", "start": 3}]))
        self.assertIn(("DUPLICATE_SHOT_ID", "a", "id"), codes([{"id": "a", "start": 0}, {"id": "a", "start": 1}]))
        self.assertIn(("UNKNOWN_FOCUS", "a", "focus"), codes([{"id": "a", "start": 0, "size": "close", "focus": "cast3"}]))
        self.assertIn(("UNKNOWN_SHOT_SIZE", "a", "size"), codes([{"id": "a", "start": 0, "size": "huge"}]))
        self.assertIn(("FIRST_SHOT_LATE", "a", "start"), codes([{"id": "a", "start": 4}]))
        p = SH.problems({**SC, "shots": [{"id": "a", "start": 0, "size": "close", "focus": "cast3"}]}, has)[0]
        self.assertTrue(p["message"] and p["next_action"])

    def test_framing_follows_the_size_of_the_target(self):
        base = SH.frame(SH.char_box({"x": 1520, "y": 960, "scale": 1.0}), "close")
        tall = SH.frame(SH.char_box({"x": 1520, "y": 960, "scale": 1.3}), "close")
        self.assertGreater(base[2], 1.0)
        self.assertLessEqual(base[2], SH.MAX_ZOOM)
        self.assertLess(tall[2], base[2], "a bigger character is framed from further away")
        for cx, cy, z in (base, tall, SH.frame(SH.char_box({"x": 60, "y": 960, "scale": 1.0}), "close")):
            self.assertGreaterEqual(cx - SH.W / (2 * z), -0.5)                    # never shows outside the canvas
            self.assertLessEqual(cx + SH.W / (2 * z), SH.W + 0.5)
            self.assertGreaterEqual(cy - SH.H / (2 * z), -0.5)
            self.assertLessEqual(cy + SH.H / (2 * z), SH.H + 0.5)
        self.assertEqual(SH.frame(None, "close"), (SH.W / 2, SH.H / 2, 1.0))
        self.assertEqual(SH.frame((0, 0, 10, 10), "wide"), (SH.W / 2, SH.H / 2, 1.0))

    def test_camera_is_continuous_across_an_eased_shot_and_jumps_only_on_a_cut(self):
        shots = [{"id": "a", "start": 0}, {"id": "b", "start": "lập thực đơn", "size": "close", "focus": "cast1", "ease": 0.5},
                 {"id": "c", "start": 3.5, "size": "detail", "focus": "item:board", "cut": True}]
        r = SH.resolve({**SC, "shots": shots}, 6.0, T, {"linh": 540, None: 420}, [("p", (700, 300, 1200, 600), SC["items"][0]), ("t", (900, 160, 1020, 220), SC["items"][1])])
        cam = r["camera"]
        pos = lambda t: SH.camera_at(cam, t)
        self.assertEqual(pos(1.9), (960.0, 540.0, 1.0))
        mid = pos(2.25)
        self.assertTrue(1.0 < mid[2] < pos(2.6)[2], "eased: zoom grows smoothly during the move")
        jump_before, jump_after = pos(3.499), pos(3.51)
        self.assertGreater(abs(jump_after[2] - jump_before[2]) + abs(jump_after[0] - jump_before[0]), 100, "a cut changes the frame at once")
        steps = [pos(2.0 + i * 0.02) for i in range(26)]
        self.assertTrue(all(abs(b[2] - a[2]) < 0.1 for a, b in zip(steps, steps[1:])), "no jump inside an eased move")

    def test_an_end_before_the_next_shot_returns_to_the_wide_frame_and_gaze_is_scheduled(self):
        shots = [{"id": "a", "start": 0, "size": "close", "focus": "main", "end": 2.0, "gaze": [{"who": "main", "at": "cast1"}]}, {"id": "b", "start": 4.0}]
        r = SH.resolve({**SC, "shots": shots}, 6.0, T, {None: 420, "linh": 540}, [])
        self.assertEqual(SH.camera_at(r["camera"], 3.0), (960.0, 540.0, 1.0))
        self.assertGreater(SH.camera_at(r["camera"], 1.9)[2], 1.0)
        self.assertEqual(r["looks"]["main"][0]["t"], 0.0)
        self.assertGreater(r["looks"]["main"][0]["at"][0], 1000, "the main character looks towards the supporting character on the right")

    def test_no_shots_means_no_camera(self):
        self.assertEqual(SH.resolve(SC, 5.0, T), {"camera": [], "looks": {}})


if __name__ == "__main__":
    unittest.main()
