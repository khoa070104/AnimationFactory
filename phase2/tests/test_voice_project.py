"""Voice generation guard rails (no real API calls): approval gate, per-scene skip, only changed scenes are re-sent."""
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

P2 = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(P2 / "tools"))
import approve  # noqa: E402
import voice_project as V  # noqa: E402


def make_project():
    d = Path(tempfile.mkdtemp()) / "proj"
    d.mkdir()
    sb = json.loads((P2 / "projects/video1_luong/storyboard.json").read_text(encoding="utf-8"))
    sb["scenes"] = sb["scenes"][:3]
    (d / "storyboard.json").write_text(json.dumps(sb, ensure_ascii=False), encoding="utf-8")
    (d / "status.json").write_text(json.dumps({"state": "x"}), encoding="utf-8")
    return d, sb


class FakeTTS:
    def __init__(self):
        self.calls = []

    def __call__(self, text, voice_id, out, speed):
        self.calls.append(text)
        Path(out).write_bytes(b"x")
        Path(out).with_suffix(".words.json").write_text("[]", encoding="utf-8")


OK = lambda *a: (True, "ok", 1.0)


def approve_project(d):
    import subprocess
    r = subprocess.run([sys.executable, str(P2 / "tools/approve.py"), str(d), "--by", "chủ dự án"], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr


class T(unittest.TestCase):
    def setUp(self):
        os.environ["AF_VOICE_CACHE"] = tempfile.mkdtemp()      # isolated shared voice cache per test (never the real one)

    def test_speed_1_vs_1_0_is_not_a_change(self):
        # a browser round-trip of the storyboard JSON turns 1.0 into 1; that must not look like a voice change
        d, sb = make_project()
        sb["voice"]["speed"] = 1.0
        (d / "storyboard.json").write_text(json.dumps(sb, ensure_ascii=False), encoding="utf-8")
        approve_project(d)
        sb["voice"]["speed"] = 1
        (d / "storyboard.json").write_text(json.dumps(sb, ensure_ascii=False), encoding="utf-8")
        self.assertEqual(approve.changes_since_approval(d), ([], []))
        # ...but a real wording change must still be caught by the approval gate
        sb["scenes"][0]["voice"] += " Thêm."
        (d / "storyboard.json").write_text(json.dumps(sb, ensure_ascii=False), encoding="utf-8")
        self.assertEqual(approve.changes_since_approval(d)[0], [sb["scenes"][0]["id"]])
        with self.assertRaises(SystemExit):
            V.run(d, tts_fn=FakeTTS(), verify_fn=OK)

    def test_a_test_or_ai_approval_never_releases_the_paid_voice(self):
        d, sb = make_project()
        import subprocess
        for label in ("tester", "Claude (kiểm thử, không phải chủ dự án)", "Claude"):
            r = subprocess.run([sys.executable, str(P2 / "tools/approve.py"), str(d), "--by", label], capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(r.returncode, 0, r.stderr)
            f = FakeTTS()
            with self.assertRaises(SystemExit) as e:
                V.run(d, tts_fn=f, verify_fn=OK)
            self.assertIn("not the owner's approval", str(e.exception))
            self.assertEqual(f.calls, [], "no paid call")
        approve_project(d)                                         # a person's name does release it
        self.assertEqual(V.run(d, tts_fn=FakeTTS(), verify_fn=OK), 3)

    def test_refuses_without_approval(self):
        d, _ = make_project()
        with self.assertRaises(SystemExit) as e:
            V.run(d, tts_fn=FakeTTS(), verify_fn=OK)
        self.assertIn("no approval", str(e.exception))

    def test_generates_once_then_skips(self):
        d, sb = make_project()
        approve_project(d)
        f = FakeTTS()
        self.assertEqual(V.run(d, tts_fn=f, verify_fn=OK), 3)
        self.assertEqual(V.run(d, tts_fn=f, verify_fn=OK), 0, "unchanged input must not call the API again")
        self.assertEqual(len(f.calls), 3)

    def test_edit_after_approval_is_blocked_then_only_changed_scene_is_regenerated(self):
        d, sb = make_project()
        approve_project(d)
        f = FakeTTS()
        V.run(d, tts_fn=f, verify_fn=OK)
        sb["scenes"][1]["voice"] += " Thêm một câu."
        (d / "storyboard.json").write_text(json.dumps(sb, ensure_ascii=False), encoding="utf-8")
        with self.assertRaises(SystemExit) as e:
            V.run(d, tts_fn=f, verify_fn=OK)
        self.assertIn("s02", str(e.exception))
        self.assertEqual(approve.changes_since_approval(d)[0], ["s02"])
        approve_project(d)                       # user re-approves the new text
        n = len(f.calls)
        self.assertEqual(V.run(d, tts_fn=f, verify_fn=OK), 1, "only the edited scene is regenerated")
        self.assertEqual(len(f.calls), n + 1)

    def test_visual_only_change_needs_no_voice(self):
        d, sb = make_project()
        approve_project(d)
        f = FakeTTS()
        V.run(d, tts_fn=f, verify_fn=OK)
        sb["scenes"][0]["items"][0]["x"] += 10
        (d / "storyboard.json").write_text(json.dumps(sb, ensure_ascii=False), encoding="utf-8")
        voice_changed, scene_changed = approve.changes_since_approval(d)
        self.assertEqual((voice_changed, scene_changed), ([], ["s01"]))
        self.assertEqual(V.run(d, tts_fn=f, verify_fn=OK), 0)

    def test_failed_verification_stops_and_is_not_marked_done(self):
        d, _ = make_project()
        approve_project(d)
        f = FakeTTS()
        with self.assertRaises(SystemExit):
            V.run(d, tts_fn=f, verify_fn=lambda *a: (False, "cut off", 1.0))
        self.assertEqual(len(f.calls), 1, "stops after the first failing scene")
        self.assertFalse((d / "audio/s01.sig").exists())

    def test_other_project_with_same_sentence_reuses_audio_without_api_call(self):
        a, _ = make_project()
        approve_project(a)
        f1 = FakeTTS()
        V.run(a, tts_fn=f1, verify_fn=OK)
        self.assertEqual(len(f1.calls), 3)
        b, sbb = make_project()                                  # a different project with the same sentences (+ one new)
        sbb["scenes"] = sbb["scenes"][:2] + [dict(sbb["scenes"][2], voice="Một câu hoàn toàn mới.", subtitles=["Một câu hoàn toàn mới."], actions=[])]
        (b / "storyboard.json").write_text(json.dumps(sbb, ensure_ascii=False), encoding="utf-8")
        approve_project(b)
        f2 = FakeTTS()
        self.assertEqual(V.run(b, tts_fn=f2, verify_fn=OK), 1, "only the genuinely new sentence calls the API")
        self.assertEqual(f2.calls, ["Một câu hoàn toàn mới."])
        self.assertTrue((b / "audio/s01.mp3").exists())
        self.assertTrue((b / "audio/s01.sig").exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
