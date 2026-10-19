"""Phase 3 acceptance cases, automated with test doubles for the paid/slow parts (LLM, agy images, voice API):
 edit one line (impact shown, only that part re-approved, only that voice regenerated) | unchanged rerun calls nothing | crash of the preparation
 process and recovery without duplicates | cost limits refuse to start | UI/MCP share job state | voice budget refuses before the first paid call."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

P2 = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(P2 / "tools"))
sys.path.insert(0, str(P2 / "tests"))
import agy_image as G  # noqa: E402
import approve  # noqa: E402
import budget  # noqa: E402
import new_project  # noqa: E402
import overview  # noqa: E402
import prepare as PR  # noqa: E402
import sbstore  # noqa: E402
import voice_project as V  # noqa: E402
from imgdouble import ColorAgy, Dispatch, RUNNER as IMG_RUNNER  # noqa: E402
from test_mcp_assets import Client  # noqa: E402
from test_prepare import FakeLLM  # noqa: E402
from test_voice_project import FakeTTS, OK  # noqa: E402

FAKE = P2 / "tests" / "fake_agy.py"


class T(unittest.TestCase):
    def setUp(self):
        self.names = []
        self.fake = FakeLLM()
        PR.RUNNER = self.fake
        os.environ["AF_VOICE_CACHE"] = tempfile.mkdtemp()
        self.home = Path(tempfile.mkdtemp())
        (self.home / "brain").mkdir()

    def tearDown(self):
        PR.RUNNER = PR.IMAGE_RUNNER = None
        os.environ.pop("AF_VOICE_CACHE", None)
        for n in self.names:
            shutil.rmtree(P2 / "projects" / n, ignore_errors=True)

    def project(self, title="Nghiệm thu", **brief):
        name = f"_t_p3_{os.getpid()}_{len(self.names)}"
        d = new_project.create(name, title, brief={"title": title, "research": "no", "character_mode": "bi", **brief})
        self.names.append(name)
        return d

    def prepared(self, **brief):
        d = self.project(**brief)
        res = PR.run_steps(d, PR.PLAN_STEPS)
        self.assertTrue(all(v == "ok" for v in res.values()), res)
        return d

    # ------------------------------------------------------------------------------------------------------------------
    def test_edit_one_line_shows_impact_and_regenerates_only_that_voice(self):
        d = self.prepared()
        approve.record(d, "chủ dự án", "all")
        tts = FakeTTS()
        n = len(json.loads((d / "storyboard.json").read_text(encoding="utf-8"))["scenes"])
        self.assertEqual(V.run(d, tts_fn=tts, verify_fn=OK), n)
        self.assertEqual(overview.todo(d) and [t["kind"] for t in overview.todo(d) if t["kind"] in ("script", "storyboard")], [])
        # the owner edits scene 4's line
        sid = "s04"
        old = next(s for s in json.loads((d / "storyboard.json").read_text(encoding="utf-8"))["scenes"] if s["id"] == sid)["voice"]
        res = sbstore.edit_voice(d, sid, old + " Đây là một câu được thêm vào.")
        self.assertTrue(res["changed"])
        todo = {t["kind"]: t for t in overview.todo(d)}
        self.assertIn(sid, todo["script"]["label"], "the impact on the spoken text is shown")
        self.assertNotIn("s05", todo["script"]["label"])
        self.assertEqual(approve.changes_since_approval(d), ([sid], [sid]), "only this scene's text and visuals need approving again")
        with self.assertRaises(SystemExit) as e:
            V.run(d, tts_fn=tts, verify_fn=OK)
        self.assertIn("REFUSED", str(e.exception))
        approve.record(d, "chủ dự án", "script")
        before = len(tts.calls)
        self.assertEqual(V.run(d, tts_fn=tts, verify_fn=OK), 1, "only the changed scene's voice is generated")
        self.assertEqual(len(tts.calls), before + 1)
        self.assertTrue(tts.calls[-1].endswith("được thêm vào."))
        self.assertEqual(approve.changes_since_approval(d), ([], [sid]), "the visuals of that scene still wait for approval")
        approve.record(d, "chủ dự án", "storyboard")
        self.assertEqual(approve.changes_since_approval(d), ([], []))

    def test_unchanged_rerun_calls_nothing_at_all(self):
        d = self.prepared()
        approve.record(d, "chủ dự án", "all")
        tts = FakeTTS()
        V.run(d, tts_fn=tts, verify_fn=OK)
        llm_calls, voice_calls = len(self.fake.calls), len(tts.calls)
        usage = budget.usage(d)
        res = PR.run_steps(d, PR.PLAN_STEPS)
        self.assertEqual(set(res.values()), {"skipped"})
        self.assertEqual(V.run(d, tts_fn=tts, verify_fn=OK), 0)
        self.assertEqual((len(self.fake.calls), len(tts.calls)), (llm_calls, voice_calls))
        self.assertEqual(budget.usage(d)["llm_calls"], usage["llm_calls"])
        # same LLM request asked again directly: answered from the project cache and logged as a cache hit
        import llm
        r = llm.call(d, "script", "quality", PR.script_prompt(PR.brief_of(d), PR.channel_of(PR.brief_of(d)), [], [], PR.targets_of(PR.brief_of(d), PR.channel_of(PR.brief_of(d))), 8,
                                                              int((sum(PR.targets_of(PR.brief_of(d), PR.channel_of(PR.brief_of(d)))["duration"]) / 2 - 4.8) * PR.chars_per_sec())), PR.SCRIPT_SCHEMA, runner=self.fake)
        self.assertTrue(r["meta"]["cache"])
        self.assertEqual(len(self.fake.calls), llm_calls)

    def test_preparation_process_crash_is_visible_and_recoverable_without_duplicates(self):
        d = self.project("Sập giữa chừng")
        env = dict(os.environ, AGY_CMD=json.dumps([sys.executable, str(FAKE)]), AGY_HOME=str(self.home), FAKE_AGY_COUNT=str(self.home / "count.txt"), FAKE_LLM_MODE="hang",
                   AF_LOCKS=str(self.home / "locks"), PYTHONIOENCODING="utf-8")
        p = subprocess.Popen([sys.executable, str(P2 / "tools/prepare.py"), str(d), "--step", "script"], env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        try:
            end = time.time() + 30
            while time.time() < end:
                st = PR.status(d)["steps"].get("script", {})
                if st.get("state") == "running" and (self.home / "count.txt").exists():
                    break
                time.sleep(0.2)
            self.assertEqual(PR.overview(d)["steps"]["script"]["state"], "running")
            p.kill()                                                      # the preparation process dies abnormally mid-call
            p.wait()
            time.sleep(1.0)
        finally:
            if p.poll() is None:
                p.kill()
            p.stdout.close()
        self.assertEqual(PR.overview(d)["steps"]["script"]["state"], "interrupted")
        self.assertTrue(any(x["where"] == "AI · script" for x in overview.problems(d)))
        self.assertFalse((d / "prepare/script.json").exists(), "nothing half-written")
        self.assertEqual(json.loads((d / "storyboard.json").read_text(encoding="utf-8"))["scenes"], [])
        # recovery: run again with a healthy provider; earlier finished steps are not repeated
        res = PR.run_steps(d, PR.PLAN_STEPS)
        self.assertTrue(all(v == "ok" for v in res.values()), res)
        self.assertEqual(len(self.fake.calls) and len([c for c in self.fake.calls if c[0] == "script"]), 1)
        res = PR.run_steps(d, PR.PLAN_STEPS)
        self.assertEqual(set(res.values()), {"skipped"})

    def test_limits_refuse_to_start_and_say_why(self):
        d = self.prepared(budget={"images": 1, "voice_credits": 5})
        approve.record(d, "chủ dự án", "all")
        tts = FakeTTS()
        with self.assertRaises(SystemExit) as e:
            V.run(d, tts_fn=tts, verify_fn=OK)
        self.assertIn("Vượt hạn mức", str(e.exception))
        self.assertIn("credit giọng đọc", str(e.exception))
        self.assertEqual(tts.calls, [], "refused before the first paid call")
        # images: one allowed, the second job is refused at submit with an explanation
        import agy_jobs as J
        os.environ["AGY_HOME"] = str(self.home)
        Dispatch.impl = ColorAgy(self.home / "brain")
        j = J.submit(d.name, {"asset_id": "one", "kind": "prop", "prompt": "a gold coin"}, runner=IMG_RUNNER)
        end = time.time() + 30
        while J.check(d.name, j["job_id"])["state"] in ("queued", "running") and time.time() < end:
            time.sleep(0.05)
        with self.assertRaises(J.JobError) as e2:
            J.submit(d.name, {"asset_id": "two", "kind": "prop", "prompt": "a silver coin"}, runner=IMG_RUNNER)
        self.assertIn("lượt tạo ảnh", str(e2.exception))
        self.assertEqual(len(Dispatch.impl.calls), 1)

    def test_ui_and_mcp_share_job_state(self):
        import agy_jobs as J
        d = self.prepared()
        os.environ["AGY_HOME"] = str(self.home)
        Dispatch.impl = ColorAgy(self.home / "brain")
        j = J.submit(d.name, {"asset_id": "shared", "kind": "prop", "prompt": "a gold coin", "display_width": 200}, runner=IMG_RUNNER)   # what the UI does
        end = time.time() + 30
        while J.check(d.name, j["job_id"])["state"] in ("queued", "running") and time.time() < end:
            time.sleep(0.05)
        c = Client({"AGY_HOME": str(self.home), "AGY_CMD": json.dumps([sys.executable, str(FAKE)]), "AF_LOCKS": str(self.home / "locks")})
        try:
            err, mj = c.tool("check_asset_job", {"project": d.name, "job_id": j["job_id"]})        # what Claude Code does through MCP
            self.assertFalse(err)
            self.assertEqual((mj["state"], mj["result"]["sha256"]), ("succeeded", J.check(d.name, j["job_id"])["result"]["sha256"]))
            err, again = c.tool("submit_asset_job", {"project": d.name, "asset_id": "shared", "kind": "prop", "prompt": "a gold coin", "display_width": 200})
            self.assertTrue(again["reused_now"] and not again["new_generation"], "the MCP submit reuses the result the UI produced")
        finally:
            c.close()
        self.assertEqual(len(Dispatch.impl.calls), 1)


if __name__ == "__main__":
    unittest.main()
