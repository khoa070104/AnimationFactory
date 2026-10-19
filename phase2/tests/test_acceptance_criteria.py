"""Pass/fail criteria are fixed BEFORE a build: loosening them afterwards cannot make a check pass; cue sync is measured (planned vs actual start);
flagged (approximate) cue changes wait for the owner. Real EffectCraft/FilmCraft draft builds (Bi, no agy, no paid call)."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

P2 = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(P2 / "tools"))
import acceptance  # noqa: E402
import approve  # noqa: E402
import new_project  # noqa: E402
import overview  # noqa: E402
import sbstore  # noqa: E402


class Unit(unittest.TestCase):
    def test_lock_keeps_the_first_criteria_and_reports_changes_until_the_owner_accepts(self):
        d = Path(tempfile.mkdtemp())
        t = {"duration": [60, 80], "scenes": [6, 10]}
        acceptance.lock(d, t, "tool")
        acceptance.lock(d, {"duration": [10, 200], "scenes": [1, 20]}, "someone")          # a second lock never replaces the first
        self.assertEqual(acceptance.load(d)["criteria"]["duration"], [60, 80])
        self.assertEqual(acceptance.problems(d, t), [])
        loose = {"duration": [60, 90], "scenes": [6, 10]}
        self.assertTrue(acceptance.problems(d, loose), "a wider window is a change, not a pass")
        with self.assertRaises(ValueError):
            acceptance.accept_change(d, "chủ dự án", "", loose)
        acceptance.accept_change(d, "chủ dự án", "video dài hơn theo ý chủ", loose)
        self.assertEqual(acceptance.problems(d, loose), [])
        self.assertTrue(acceptance.problems(d, {"duration": [30, 40], "scenes": [6, 10]}), "accepting one change does not accept every change")
        self.assertEqual(acceptance.load(d)["history"][0]["by"], "chủ dự án")


class Build(unittest.TestCase):
    def setUp(self):
        name = f"_t_acc_{os.getpid()}"
        self.d = new_project.create(name, "Tiêu chí", brief={"title": "Tiêu chí", "research": "no", "character_mode": "bi"})
        self.name = name
        sb = json.loads((self.d / "storyboard.json").read_text(encoding="utf-8"))
        sb["scenes"] = [{"id": "s01", "title": "Chào", "voice": "Xin chào các bạn, hôm nay chúng ta học một điều mới và rất thú vị.", "subtitles": "auto", "bg": "cream", "transition": "cut",
                         "bi": {"x": 520, "y": 960, "scale": 1.0, "face": "neutral", "pose": "idle"},
                         "actions": [{"name": "enter", "at": 0.0}, {"name": "cheek", "cue": "xin chào", "hold": 0.6}], "face_cues": [], "items": []}]
        sb["targets"] = {"duration": [4, 20], "scenes": [1, 2]}
        (self.d / "storyboard.json").write_text(json.dumps(sb, ensure_ascii=False, indent=2), encoding="utf-8")
        self.env = dict(os.environ, PYTHONIOENCODING="utf-8")

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def produce(self):
        r = subprocess.run([sys.executable, str(P2 / "tools/produce.py"), str(self.d), "--draft"], capture_output=True, text=True, encoding="utf-8", env=self.env)
        rep = json.loads((self.d / "logs/build_report.json").read_text(encoding="utf-8"))
        return r.returncode, {c["name"]: c for c in rep["checks"]}

    def edit(self, fn):
        sb = json.loads((self.d / "storyboard.json").read_text(encoding="utf-8"))
        fn(sb)
        (self.d / "storyboard.json").write_text(json.dumps(sb, ensure_ascii=False, indent=2), encoding="utf-8")

    def test_late_action_fails_the_build_until_fixed_and_criteria_cannot_be_loosened_to_pass(self):
        rc, checks = self.produce()
        cue = next(c for n, c in checks.items() if n.startswith("actions start within"))
        self.assertEqual(rc, 1)
        self.assertFalse(cue["pass"])
        self.assertIn("cheek", cue["info"])
        self.assertTrue(checks["pass/fail criteria were fixed before the build (not loosened since)"]["pass"])
        locked = acceptance.load(self.d)["criteria"]
        self.assertEqual(locked["cue_tolerance"], 0.7)
        # the owner's honest fix: move the action so it does not wait for the walk-in
        self.edit(lambda sb: sb["scenes"][0].update(actions=[{"name": "cheek", "cue": "xin chào", "hold": 0.6}]))
        rc, checks = self.produce()
        self.assertEqual(rc, 0, [c for c in checks.values() if not c["pass"]])
        # loosening the window afterwards is caught
        self.edit(lambda sb: sb.update(targets={"duration": [1, 200], "scenes": [1, 20]}))
        rc, checks = self.produce()
        self.assertEqual(rc, 1)
        self.assertFalse(checks["pass/fail criteria were fixed before the build (not loosened since)"]["pass"])
        self.assertIn("criteria changed after they were fixed", checks["pass/fail criteria were fixed before the build (not loosened since)"]["info"])
        sbj = json.loads((self.d / "storyboard.json").read_text(encoding="utf-8"))
        acceptance.accept_change(self.d, "chủ dự án", "bài ngắn hơn dự kiến", sbj["targets"])
        rc, checks = self.produce()
        self.assertEqual(rc, 0)

    def test_approximate_cue_changes_wait_for_the_owner_and_approval_clears_them(self):
        self.edit(lambda sb: sb["scenes"][0].update(actions=[{"name": "cheek", "cue": "xin chào", "hold": 0.6}]))
        approve.record(self.d, "chủ dự án", "all")
        self.assertTrue((self.d / "acceptance.json").exists(), "approval fixes the criteria")
        res = sbstore.edit_voice(self.d, "s01", "Một lời đọc hoàn toàn khác, không còn cụm cũ nào cả trong câu này.")
        self.assertTrue(any(c["kind"] == "approx" for c in res["realigned"]))
        self.assertIn("s01", sbstore.review_list(self.d))
        self.assertTrue(any(t["kind"] == "cues" for t in overview.todo(self.d)))
        approve.record(self.d, "chủ dự án", "storyboard")
        self.assertEqual(sbstore.review_list(self.d), {})
        self.assertFalse(any(t["kind"] == "cues" for t in overview.todo(self.d)))


if __name__ == "__main__":
    unittest.main()
