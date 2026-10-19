"""Editing with consequences: voice edits realign cues/subtitles automatically; AI revisions are proposals with a visible diff, validated,
stale-protected and only then applied; asset feedback becomes a prompt proposal and one regeneration."""
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

P2 = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(P2 / "tools"))
sys.path.insert(0, str(P2 / "tests"))
import agy_image as G  # noqa: E402
import approve  # noqa: E402
import budget  # noqa: E402
import new_project  # noqa: E402
import prepare as PR  # noqa: E402
import realign  # noqa: E402
import revise  # noqa: E402
import sbstore  # noqa: E402
from imgdouble import ColorAgy, Dispatch, RUNNER as IMG_RUNNER  # noqa: E402
from test_prepare import FakeLLM  # noqa: E402


class RealignUnit(unittest.TestCase):
    SC = {"id": "s1", "voice": "Khung tham khảo là chi tiêu thiết yếu của ba đến sáu tháng. Thu nhập không ổn định thì nên giữ nhiều hơn.",
          "subtitles": ["Khung tham khảo là chi tiêu thiết yếu", "của ba đến sáu tháng."], "actions": [{"name": "point_seq", "cues": ["ba đến", "sáu tháng"]}, {"name": "nod", "cue": "nhiều hơn"}],
          "face_cues": [{"cue": "không ổn định", "face": "worried"}],
          "items": [{"type": "chart", "bars": [{"appear": "ba đến"}, {"appear": "sáu tháng"}], "appear": 0.3}, {"type": "text", "text": "x", "appear": "thiết yếu"}]}

    def test_unchanged_phrases_are_kept(self):
        new, ch = realign.realign(self.SC, self.SC["voice"] + " Thêm một câu cuối.")
        self.assertEqual(ch, [])
        self.assertEqual(new["subtitles"], self.SC["subtitles"])

    def test_reworded_cue_is_matched_and_far_edit_becomes_approximate_time(self):
        voice = "Khung tham khảo là chi tiêu cần thiết của ba tới sáu tháng. Nếu thu nhập bấp bênh thì nên giữ nhiều hơn nữa."
        new, ch = realign.realign(self.SC, voice)
        kinds = {c["old"]: c["kind"] for c in ch}
        self.assertIn(kinds.get("ba đến"), ("matched", "proposed"))
        self.assertEqual(new["actions"][0]["cues"][0], "ba tới")
        self.assertIn(kinds.get("không ổn định"), ("matched", "proposed", "approx"))
        self.assertEqual(new["subtitles"], "auto", "subtitles that no longer follow the text are re-derived")
        for a in new["actions"]:
            for c in ([a["cue"]] if "cue" in a else []) + a.get("cues", []):
                self.assertTrue(realign.has_phrase(voice, c), c)
        voice2 = "Hoàn toàn khác. Chúng ta nói về một chủ đề không liên quan nào cả."
        new2, ch2 = realign.realign(self.SC, voice2)
        self.assertTrue(any(c["kind"] == "approx" for c in ch2))
        self.assertTrue(all(isinstance(i.get("appear", 0.3), (int, float)) for i in new2["items"]))
        self.assertTrue(all(isinstance(b.get("appear", 0.3), (int, float)) for b in new2["items"][0]["bars"]))


class T(unittest.TestCase):
    def setUp(self):
        self.names = []
        self.fake = FakeLLM()
        PR.RUNNER = revise.RUNNER = self.fake
        d = new_project.create(f"_t_rev_{os.getpid()}", "Chỉnh sửa", brief={"title": "Chỉnh sửa theo góp ý", "research": "no", "character_mode": "bi"})
        self.names.append(d.name)
        self.d = d
        res = PR.run_steps(d, PR.PLAN_STEPS)
        assert all(v == "ok" for v in res.values()), res

    def tearDown(self):
        PR.RUNNER = revise.RUNNER = PR.IMAGE_RUNNER = None
        for n in self.names:
            shutil.rmtree(PR.P2 / "projects" / n, ignore_errors=True)

    def sb(self):
        return json.loads((self.d / "storyboard.json").read_text(encoding="utf-8"))

    def test_voice_edit_realigns_validates_and_withdraws_only_that_scenes_approval(self):
        approve.record(self.d, "chủ dự án", "all")
        sb = self.sb()
        sc = sb["scenes"][2]
        old = sc["voice"]
        res = sbstore.edit_voice(self.d, sc["id"], old.replace("Bước", "Việc").replace("bước", "việc") + " Thêm ý nhỏ ở cuối.")
        self.assertTrue(res["changed"])
        sb2 = self.sb()
        self.assertEqual(sb2["version"], sb["version"] + 1)
        self.assertEqual(sbstore.validate_obj(self.d, sb2)[0], [])
        self.assertEqual(approve.changes_since_approval(self.d)[0], [sc["id"]], "only the edited scene needs its text approved again")
        self.assertEqual(sb2["scenes"][2]["subtitles"], "auto")
        with self.assertRaises(sbstore.SaveError):
            sbstore.edit_voice(self.d, sc["id"], "ab")

    def test_ai_scene_revision_is_a_proposal_with_diff_then_applied(self):
        sb = self.sb()
        sid = sb["scenes"][1]["id"]
        p = revise.propose_scene(self.d, sid, "rút ngắn lời và mặt vui hơn")
        self.assertEqual(p["status"], "pending")
        self.assertTrue(p["voice_changed"] and p["errors"] == [])
        paths = {x["path"] for x in p["diff"]}
        self.assertIn("voice", paths)
        self.assertIn("bi.face", paths)
        self.assertEqual(self.sb(), sb, "a proposal changes nothing")
        approve.record(self.d, "chủ dự án", "all")
        done = revise.apply(self.d, p["id"])
        self.assertEqual(done["status"], "applied")
        sb2 = self.sb()
        self.assertEqual(sb2["version"], sb["version"] + 1)
        self.assertEqual(sb2["scenes"][1]["bi"]["face"], "happy")
        self.assertEqual(approve.changes_since_approval(self.d)[0], [sid])
        with self.assertRaises(revise.ReviseError):
            revise.apply(self.d, p["id"])                                       # already applied

    def test_stale_and_invalid_proposals_cannot_be_applied(self):
        sid = self.sb()["scenes"][1]["id"]
        p1 = revise.propose_scene(self.d, sid, "mặt vui hơn")
        sbstore.edit_voice(self.d, sid, self.sb()["scenes"][1]["voice"] + " Một câu mới.")      # the scene changes after the proposal
        with self.assertRaises(revise.ReviseError) as e:
            revise.apply(self.d, p1["id"])
        self.assertIn("changed after", str(e.exception))

        def bad_face(model, prompt, schema, timeout, search):
            sc = json.loads(prompt.split("CURRENT SCENE JSON:\n")[1].split("\n")[0])
            sc["items"].append({"type": "prop", "img": "no_such_prop", "x": 1, "y": 1})
            return {"scene": sc, "summary": "x"}, {"seconds": 0, "tokens": {"total": 1}}
        revise.RUNNER = bad_face
        p2 = revise.propose_scene(self.d, sid, "thêm một hình lạ")
        self.assertTrue(p2["errors"])
        with self.assertRaises(revise.ReviseError):
            revise.apply(self.d, p2["id"])
        revise.reject(self.d, p2["id"])
        self.assertEqual(revise.get(self.d, p2["id"])["status"], "rejected")

    def test_asset_prompt_that_echoes_the_instructions_is_rejected_and_asked_again(self):
        PR.approve_plan(self.d, "chủ dự án")
        a = json.loads((self.d / "prepare/asset_plan.json").read_text(encoding="utf-8"))["assets"][0]
        answers = iter(["Improve the image subject prompt based on user feedback.", '{"prompt": "a small potted plant on coins, rounder leaves", "explanation": "x"}'])
        seen = []

        def runner(model, prompt, schema, timeout, search):
            seen.append(prompt)
            return {"prompt": next(answers), "explanation": "x"}, {"seconds": 0, "tokens": {"total": 1}}
        revise.RUNNER = runner
        p = revise.propose_asset(self.d, a["id"], "lá tròn hơn")
        self.assertEqual(p["after"]["prompt"], "a small potted plant on coins, rounder leaves")
        self.assertEqual(len(seen), 2)
        self.assertIn("rejected", seen[1])

    def test_asset_feedback_becomes_a_prompt_proposal_and_one_regeneration(self):
        PR.approve_plan(self.d, "chủ dự án")
        a = json.loads((self.d / "prepare/asset_plan.json").read_text(encoding="utf-8"))["assets"][0]
        home = Path(tempfile.mkdtemp())
        os.environ["AGY_HOME"] = str(home)
        (home / "brain").mkdir()
        Dispatch.impl = img = ColorAgy(home / "brain")
        PR.IMAGE_RUNNER = IMG_RUNNER
        PR.do_assets(self.d, poll=0.05)
        self.assertEqual(len(img.calls), 1)
        sha1 = G.load_manifest(self.d)["assets"][a["id"]]["sha256"]
        p = revise.propose_asset(self.d, a["id"], "lá xanh hơn, tròn hơn")
        self.assertNotEqual(p["after"]["prompt"], p["before"]["prompt"])
        self.assertEqual(len(img.calls), 1, "a proposal generates nothing")
        done = revise.apply(self.d, p["id"])
        import agy_jobs as J
        j = J.check(self.d.name, done["result"]["job_id"])
        end = __import__("time").time() + 30
        while j["state"] in ("queued", "running") and __import__("time").time() < end:
            __import__("time").sleep(0.05)
            j = J.check(self.d.name, done["result"]["job_id"])
        self.assertEqual(j["state"], "succeeded")
        self.assertEqual(len(img.calls), 2)
        e = G.load_manifest(self.d)["assets"][a["id"]]
        self.assertNotEqual(e["sha256"], sha1)
        self.assertEqual(e["status"], "draft")
        self.assertEqual(e["prompt"], p["after"]["prompt"])
        self.assertTrue(PR.plan_approved(self.d), "the owner applied a visible diff: the changed plan stays approved")
        self.assertEqual(budget.usage(self.d)["images"], 2)


if __name__ == "__main__":
    unittest.main()
