"""Cache-dependency granularity (motion library), auto subtitles, camera data."""
import re
import sys
import unittest
from pathlib import Path

P2 = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(P2 / "tools"))
import build_video as BV  # noqa: E402
import sbload  # noqa: E402

TEXT = (P2 / "lib/bi_motion.jsx").read_text(encoding="utf-8")


class Motion(unittest.TestCase):
    def test_changing_one_action_only_changes_scenes_that_use_it(self):
        edited = TEXT.replace("var hold = (p && p.hold != null) ? p.hold : 1.4;", "var hold = (p && p.hold != null) ? p.hold : 9.9;", 1)
        self.assertNotEqual(edited, TEXT)
        self.assertNotEqual(BV.motion_hash(TEXT, ["hold_phone"]), BV.motion_hash(edited, ["hold_phone"]))
        for other in (["point"], ["cheer", "nod"], ["shrug"], []):
            self.assertEqual(BV.motion_hash(TEXT, other), BV.motion_hash(edited, other), other)

    def test_changing_a_pose_only_changes_scenes_that_reach_it(self):
        edited = re.sub(r"(  phone: \{ rHand: \[)95", r"\g<1>99", TEXT, count=1)
        self.assertNotEqual(edited, TEXT)
        self.assertNotEqual(BV.motion_hash(TEXT, ["hold_phone"]), BV.motion_hash(edited, ["hold_phone"]))
        self.assertNotEqual(BV.motion_hash(TEXT, [], rest="phone"), BV.motion_hash(edited, [], rest="phone"))
        self.assertEqual(BV.motion_hash(TEXT, ["point"]), BV.motion_hash(edited, ["point"]))

    def test_shared_machinery_change_invalidates_every_scene(self):
        edited = TEXT.replace("fk[kind].push([ev[i].t - 0.15,", "fk[kind].push([ev[i].t - 0.30,", 1)
        self.assertNotEqual(edited, TEXT)
        for acts in (["point"], ["nod"], []):
            self.assertNotEqual(BV.motion_hash(TEXT, acts), BV.motion_hash(edited, acts))


class Subtitles(unittest.TestCase):
    def test_auto_segments_are_short_and_lossless(self):
        voice = "Nhưng mới giữa tháng, tài khoản chỉ còn sáu triệu. Tiền đi đâu hết rồi? Mình ngồi xem lại tất cả các khoản chi của mình nhé!"
        segs = sbload.auto_subtitles(voice, 40)
        self.assertTrue(all(len(s) <= 40 for s in segs), segs)
        self.assertEqual(" ".join(segs).split(), voice.split())
        self.assertTrue(any(s.endswith("?") for s in segs) and any(s.endswith(".") for s in segs), "breaks at sentence ends")

    def test_storyboard_without_subtitles_gets_them(self):
        sb = sbload.normalise({"scenes": [{"id": "a", "voice": "Một hai ba bốn năm sáu bảy tám chín mười mười một mười hai."}]})
        self.assertTrue(sb["scenes"][0]["subtitles"])
        self.assertEqual(sb["scenes"][0]["transition"], "cut")


class Camera(unittest.TestCase):
    def test_presets_and_dicts(self):
        self.assertEqual(sbload.resolve_camera("push_in")["zoom"], [1.0, 1.12])
        self.assertIsNone(sbload.resolve_camera(None))
        self.assertEqual(sbload.resolve_camera({"zoom": [1, 1.2]})["pan"], [[0.0, 0.0], [0.0, 0.0]])
        for bad in ("fly_away", {"zoom": [0.1, 1]}, {"zoom": [1, 1], "pan": [[0, 0], [9999, 0]]}):
            with self.assertRaises(ValueError):
                sbload.resolve_camera(bad)


if __name__ == "__main__":
    unittest.main(verbosity=2)
