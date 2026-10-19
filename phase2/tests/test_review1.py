"""Regression tests for the Chặng 1 review (each test is the case the reviewer reproduced):
 clean clone files, two writers / two job starters at once, shot timing holes, QA failure is a failure, focus isolation limits, JSON errors at the door."""
import copy
import json
import subprocess
import sys
import threading
import time
import unittest
from pathlib import Path

P2 = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(P2 / "tools"))
sys.path.insert(0, str(P2 / "tests"))
import af_core as AF  # noqa: E402
import shots as SH  # noqa: E402
import test_af_control as TAC  # noqa: E402
import test_characters as TC  # noqa: E402

CHILD = r"""
import json, sys, time
sys.path.insert(0, sys.argv[1] + "/tools")
import af_core as AF
proj, hash_, tag, t_go = sys.argv[2], sys.argv[3], sys.argv[4], float(sys.argv[5])
sb = json.load(open(sys.argv[6], encoding="utf-8"))
sb["scenes"][0]["title"] = tag
while time.time() < t_go:
    time.sleep(0.005)
r = AF.call("project_put", {"project": proj, "storyboard": sb, "expect_hash": hash_})
print(json.dumps({"status": r["status"], "code": (r.get("errors") or [{}])[0].get("code"), "version": r.get("version")}))
"""


class T(unittest.TestCase):
    setUp, tearDown, project, with_mai, scene = TC.T.setUp, TC.T.tearDown, TC.T.project, TC.T.with_mai, TC.T.scene
    story = TAC.T.story

    def ready(self):
        d = self.project()
        self.with_mai(d)
        self.story(d)
        return d, AF.call("project_get", {"project": d.name})

    # 2. two writers / two job starters
    def test_two_processes_saving_at_once_one_wins_and_the_other_gets_STALE_HASH(self):
        d, cur = self.ready()
        for rnd in range(3):
            cur = AF.call("project_get", {"project": d.name})
            files = []
            for i in (0, 1):
                f = d / f"_w{i}.json"
                f.write_text(json.dumps(cur["storyboard"], ensure_ascii=False), encoding="utf-8")
                files.append(f)
            go = time.time() + 6
            ps = [subprocess.Popen([sys.executable, "-c", CHILD, str(P2), d.name, cur["hash"], f"w{rnd}{i}", str(go), str(files[i])], stdout=subprocess.PIPE, text=True, encoding="utf-8") for i in (0, 1)]
            res = [json.loads(p.communicate(timeout=120)[0].strip().splitlines()[-1]) for p in ps]
            self.assertEqual(sorted(r["status"] for r in res), ["needs_changes", "ok"], res)
            self.assertEqual([r["code"] for r in res if r["status"] != "ok"], ["STALE_HASH"])
            new = AF.call("project_get", {"project": d.name})
            self.assertEqual(new["storyboard"]["version"], cur["storyboard"]["version"] + 1, "exactly one write happened")

    def test_two_concurrent_job_starts_launch_one_job_with_a_unique_id(self):
        d, _ = self.ready()
        p = AF.proj_path(d.name)
        argv = [sys.executable, "-c", "import time; time.sleep(4)"]
        out = []

        def go(op):
            try:
                out.append(AF._spawn(p, {"op": op}, argv))
            except AF.AfError as e:
                out.append(e)
        ts = [threading.Thread(target=go, args=(f"op{i}",)) for i in range(2)]
        [t.start() for t in ts]
        [t.join() for t in ts]
        started = [o for o in out if isinstance(o, tuple) and o[1]]
        refused = [o for o in out if isinstance(o, AF.AfError)]
        self.assertEqual((len(started), len(refused)), (1, 1), out)
        self.assertEqual(refused[0].err["code"], "PROJECT_BUSY")
        self.assertEqual(len(list((p / "logs" / "af_jobs").glob("*.json"))), 1)
        self.assertRegex(started[0][0]["id"], r"^op\d-\d{14}-[0-9a-f]{6}$")
        same = AF._spawn(p, {"op": started[0][0]["request"]["op"]}, argv)
        self.assertEqual((same[1], same[0]["id"]), (False, started[0][0]["id"]), "the same request returns the running job")
        time.sleep(5)

    # 3. shot timing
    def shots(self, shots, dur=6.0, T=None):
        sc = {"voice": "alpha beta gamma delta epsilon", "bi": {"x": 400, "y": 900, "scale": 1.0}, "cast": [], "items": [], "shots": shots}
        return SH.timing_problems(sc, dur, T or (lambda v: {"beta": 1.0, "delta": 4.0}.get(v, 2.0)))

    def test_timing_holes_are_refused_with_a_code_and_the_shot_id(self):
        codes = lambda sh: [(p["code"], p["shot_id"]) for p in self.shots(sh)]
        self.assertIn(("SHOTS_NOT_INCREASING", "b"), codes([{"id": "a", "start": "delta"}, {"id": "b", "start": "beta"}]))
        self.assertIn(("END_BEFORE_START", "a"), codes([{"id": "a", "start": 2, "end": 1}]))
        self.assertIn(("SHOT_OVERLAP", "a"), codes([{"id": "a", "start": 0, "end": 3}, {"id": "b", "start": 2}]))
        self.assertIn(("EASE_TOO_LONG", "b"), codes([{"id": "a", "start": 0}, {"id": "b", "start": 2, "ease": 2}, {"id": "c", "start": 3}]))
        self.assertIn(("SHOT_AFTER_SCENE_END", "b"), codes([{"id": "a", "start": 0}, {"id": "b", "start": 7}]))
        self.assertEqual(self.shots([{"id": "a", "start": 0}, {"id": "b", "start": 2, "ease": 0.5}, {"id": "c", "start": 3, "cut": True}]), [])
        sc = {"voice": "alpha beta", "bi": {"x": 400, "y": 900}, "shots": [{"id": "a", "start": "delta"}, {"id": "b", "start": "beta"}]}
        with self.assertRaises(SH.ShotError):
            SH.resolve(sc, 6.0, lambda v: {"beta": 1.0, "delta": 4.0}[v])

    def test_structural_shot_errors_unknown_end_phrase_point_focus_and_wrong_types(self):
        has = lambda voice, ph: ph in voice
        base = {"voice": "alpha beta gamma", "bi": {}, "cast": [], "items": []}
        pr = lambda shots: {(p["code"], p["field"]) for p in SH.problems({**base, "shots": shots}, has)}
        self.assertIn(("CUE_NOT_IN_VOICE", "end"), pr([{"id": "a", "start": 0, "end": "không có"}]))
        self.assertIn(("UNKNOWN_FOCUS", "focus"), pr([{"id": "a", "start": 0, "size": "close", "focus": [100, 200]}]))
        self.assertIn(("END_BEFORE_START", "end"), pr([{"id": "a", "start": 2, "end": 1}]))
        self.assertIn(("BAD_FIELD_TYPE", "start"), pr([{"id": "a", "start": [1]}]))
        self.assertIn(("SHOTS_NOT_INCREASING", "start"), pr([{"id": "a", "start": "gamma"}, {"id": "b", "start": "alpha"}]))
        self.assertEqual(pr([{"id": "a", "start": 0, "size": "close", "focus": [100, 200, 300, 200]}]), set())

    def test_preview_reports_a_shot_timing_error_as_structured_data(self):
        d, cur = self.ready()
        sb = copy.deepcopy(cur["storyboard"])
        sb["scenes"][0]["shots"] = [{"id": "sh1", "start": 0}, {"id": "sh2", "start": "mỉm cười"}, {"id": "sh3", "start": 0.4}]
        r = AF.call("project_put", {"project": d.name, "storyboard": sb, "expect_hash": cur["hash"]})
        self.assertEqual(r["status"], "ok", r)                                  # a phrase and seconds can only be compared once the voice timing is known
        pv = AF.call("preview", {"project": d.name})
        self.assertEqual(pv["status"], "needs_changes", pv)
        got = [(e["scene_id"], e["shot_id"], e["field"], e["code"]) for e in pv["errors"]]
        self.assertIn(("s01", "sh3", "start", "SHOTS_NOT_INCREASING"), got)

    # 4. QA failure is a failure
    def test_failed_qa_is_needs_changes_not_ok_and_the_cli_exit_code_follows(self):
        d, _ = self.ready()
        import build_remotion
        real = (build_remotion.build, AF._preview_artifacts, AF.validate)

        def fake_build(p, **kw):
            (p / "logs").mkdir(exist_ok=True)
            (p / "logs" / "build_report.json").write_text(json.dumps({"checks": [{"name": "motion QA", "pass": False, "info": "arm through torso"}, {"name": "x", "pass": True}]}), encoding="utf-8")
            (p / "status.json").write_text(json.dumps({"last_build": {"rendered": ["s01"], "reused": []}}), encoding="utf-8")
            return False
        build_remotion.build, AF._preview_artifacts = fake_build, lambda p: [{"kind": "clip", "path": "x.mp4"}]
        try:
            r = AF.call("preview", {"project": d.name})
        finally:
            build_remotion.build, AF._preview_artifacts, AF.validate = real
        self.assertEqual((r["status"], r["errors"][0]["code"], r["checks_passed"]), ("needs_changes", "QA_FAILED", False))
        self.assertEqual(r["errors"][0]["failed_checks"][0]["name"], "motion QA")
        self.assertTrue(r["artifacts"], "the draft is still returned so the problem can be looked at")
        self.assertIsInstance(r["paid_calls_this_run"], int)

    # 5. focus isolation
    def test_isolation_respects_screen_layer_keep_hide_in_and_the_real_shot_window(self):
        d, cur = self.ready()
        sb = copy.deepcopy(cur["storyboard"])
        sc = sb["scenes"][0]
        near = {"type": "text", "x": 640, "y": 400, "size": 46}
        sc["items"] += [{**near, "text": "world"}, {**near, "text": "pinned", "space": "screen"}, {**near, "text": "kept", "keep": True}, {**near, "text": "forced", "hide_in": ["sh1"], "x": 1500}]
        sc["shots"] = [{"id": "sh1", "start": 0}, {"id": "sh2", "start": 1.0, "kind": "reaction", "size": "close", "focus": "main", "end": 1.6}, {"id": "sh3", "start": 2.2}]
        r = AF.call("project_put", {"project": d.name, "storyboard": sb, "expect_hash": cur["hash"]})
        self.assertEqual(r["status"], "ok", r)
        self.assertEqual(AF.call("preview", {"project": d.name})["status"], "ok")
        clip = json.loads((d / "remotion/public/data/clip.json").read_text(encoding="utf-8"))
        by = {p.get("text"): p for p in clip["scenes"][0]["prims"] if p.get("text")}
        self.assertEqual(by["world"].get("hide"), [[1.0, 1.6]], "hidden only while the close-up lasts (its `end`), not until the next shot starts")
        self.assertFalse(by["pinned"].get("hide"), "a screen-layer item is not part of the world view")
        self.assertFalse(by["kept"].get("hide"), "keep: true pins an item")
        self.assertEqual(by["forced"].get("hide"), [[0.0, 1.0]], "hide_in hides an item in the named shot, whatever it is")

    # 6. JSON contract at the door
    def test_bad_input_returns_json_errors(self):
        code, out, _ = TAC.af("call", "validate", "--json", "{broken")
        self.assertEqual((code, out["status"], out["errors"][0]["code"], out["charged_calls"]), (1, "error", "INVALID_JSON", 0))
        r = AF.call("project_new", {"name": "New-Video", "title": "x"})
        self.assertEqual((r["status"], r["errors"][0]["code"]), ("error", "BAD_PROJECT_NAME"))
        r = AF.call("project_get", {"project": 5})
        self.assertEqual(r["status"], "error")
        self.assertIn("code", r["errors"][0])

    def test_scene_ids_need_not_start_with_s(self):
        e = AF.structure("intro: shot sh1: size: unknown size 'x' [UNKNOWN_SHOT_SIZE]", ["intro", "s2"])
        self.assertEqual((e["scene_id"], e["shot_id"], e["code"], e["field"]), ("intro", "sh1", "UNKNOWN_SHOT_SIZE", "size"))
        e = AF.structure("outro: AI asset 'x' is 'missing'", ["intro", "outro"])
        self.assertEqual((e["scene_id"], e["code"]), ("outro", "MISSING_ASSET"))

    def test_paid_calls_is_always_a_number(self):
        self.assertEqual(AF._paid({"llm_calls": 0, "images": 0, "voice_credits": 0}), 0)
        self.assertEqual(AF._paid({"llm_calls": 1, "images": 2, "voice_credits": 5}), 4)


if __name__ == "__main__":
    unittest.main()
