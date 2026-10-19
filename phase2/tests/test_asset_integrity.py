"""Asset-job integrity (no Antigravity, no paid API): project-scoped jobs, per-job results, cache that checks its file,
approval bound to the image hash, atomic state files."""
import hashlib
import json
import os
import shutil
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path

import numpy as np
from PIL import Image

P2 = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(P2 / "tools"))
sys.path.insert(0, str(P2 / "tests"))
import agy_image as G  # noqa: E402
import agy_jobs as J  # noqa: E402
import build_storyboard as SBD  # noqa: E402
from imgdouble import ColorAgy, Dispatch, FakeAgyNoTool, RUNNER, wait_state  # noqa: E402,F401


class T(unittest.TestCase):
    def setUp(self):
        home = Path(tempfile.mkdtemp())
        os.environ["AGY_HOME"] = str(home)
        self.brain = home / "brain"
        self.brain.mkdir()
        self.names = []
        self.req = {"asset_id": "coin", "kind": "prop", "prompt": "a gold coin", "display_width": 200}

    def tearDown(self):
        for n in self.names:
            shutil.rmtree(J.PROJECTS / n, ignore_errors=True)

    def project(self, tag):
        name = f"_t_assets_{tag}_{os.getpid()}_{len(self.names)}"
        d = J.PROJECTS / name
        d.mkdir(parents=True)
        (d / "storyboard.json").write_text("{}", encoding="utf-8")
        self.names.append(name)
        return name

    def submit_and_wait(self, name, req=None, **kw):
        j = J.submit(name, req or self.req, runner=RUNNER)
        return wait_state(name, j["job_id"], **kw)

    # 1 ---------------------------------------------------------------------------------------------------------------------
    def test_same_request_in_two_projects_while_running(self):
        a, b = self.project("a"), self.project("b")
        gate = threading.Event()
        Dispatch.impl = ColorAgy(self.brain, gate)
        ja = J.submit(a, self.req, runner=RUNNER)
        jb = J.submit(b, self.req, runner=RUNNER)                       # used to hit `_inflight` of project a (and TypeError on a missing record)
        self.assertEqual(ja["job_id"], jb["job_id"])
        self.assertEqual((ja["project"], jb["project"]), (a, b))
        self.assertIn(J.check(a, ja["job_id"])["state"], ("queued", "running"))
        self.assertIn(J.check(b, jb["job_id"])["state"], ("queued", "running"))
        again_a = J.submit(a, self.req, runner=RUNNER)                   # a repeat in the SAME project is still the same running job
        self.assertIn("already queued/running", again_a["note"])
        gate.set()
        ra, rb = wait_state(a, ja["job_id"]), wait_state(b, jb["job_id"])
        self.assertEqual((ra["state"], rb["state"]), ("succeeded", "succeeded"))
        self.assertEqual((ra["project"], rb["project"]), (a, b))
        for name, r in ((a, ra), (b, rb)):
            self.assertTrue((J.PROJECTS / name / r["result"]["file"]).is_file())
        self.assertEqual(len(Dispatch.impl.calls), 2, "each project is its own asset: two runs")

    # 2 ---------------------------------------------------------------------------------------------------------------------
    def test_old_job_never_returns_the_newer_request_result(self):
        p = self.project("v")
        Dispatch.impl = ColorAgy(self.brain)
        j1 = self.submit_and_wait(p)
        sha1 = j1["result"]["sha256"]
        j2 = self.submit_and_wait(p, {**self.req, "prompt": "a different silver coin"})
        sha2 = j2["result"]["sha256"]
        self.assertNotEqual(sha1, sha2)
        self.assertNotEqual(j1["job_id"], j2["job_id"])
        old = J.check(p, j1["job_id"])
        self.assertEqual(old["state"], "superseded")
        self.assertEqual(old["result"]["sha256"], sha1, "the old job reports what IT produced")
        self.assertNotEqual(old["result"]["sha256"], sha2)
        self.assertIn("not usable", old["use_in_scene"])
        vf = J.PROJECTS / p / old["result"]["file"]                         # and that image is still available, frozen
        self.assertTrue(vf.is_file())
        self.assertEqual(G.sha_file(vf), sha1)
        self.assertEqual(J.check(p, j2["job_id"])["state"], "succeeded")

    # 3 ---------------------------------------------------------------------------------------------------------------------
    def test_cache_does_not_claim_success_for_a_missing_or_changed_file(self):
        p = self.project("c")
        f = ColorAgy(self.brain)
        Dispatch.impl = f
        j = self.submit_and_wait(p)
        png = J.PROJECTS / p / j["result"]["file"]
        again = J.submit(p, self.req, runner=RUNNER)                         # healthy cache: reused, no run
        self.assertTrue(again["reused_now"])
        self.assertEqual(len(f.calls), 1)
        saved = png.read_bytes()
        png.unlink()
        with self.assertRaises(J.JobError) as e:
            J.submit(p, self.req, runner=RUNNER)
        self.assertIn("missing", str(e.exception))
        self.assertEqual(len(f.calls), 1, "no automatic regeneration (no cost)")
        self.assertEqual(J.check(p, j["job_id"])["state"], "invalid")
        png.write_bytes(saved[:-5] + b"xxxxx")                               # damaged/replaced file
        with self.assertRaises(J.JobError) as e:
            J.submit(p, self.req, runner=RUNNER)
        self.assertIn("no longer matches", str(e.exception))
        self.assertEqual(len(f.calls), 1)
        self.assertEqual(J.check(p, j["job_id"])["state"], "invalid")
        regen = J.submit(p, {**self.req, "regenerate": True}, runner=RUNNER)  # only an explicit request creates it again
        self.assertEqual(wait_state(p, regen["job_id"])["state"], "succeeded")
        self.assertEqual(len(f.calls), 2)

    # 4 ---------------------------------------------------------------------------------------------------------------------
    def test_approval_is_bound_to_the_image_hash(self):
        p = self.project("h")
        Dispatch.impl = ColorAgy(self.brain)
        j = self.submit_and_wait(p)
        proj = J.PROJECTS / p
        G.set_status(proj, "coin", "approved", approved_by="owner")
        self.assertEqual(G.approval_state(proj, "coin")[0], "approved")
        self.assertEqual(J.check(p, j["job_id"])["result"]["status"], "approved")
        out = proj / "assets"
        self.assertEqual(SBD.resolve_img(out, "ai:coin"), "ai_coin")
        png = proj / j["result"]["file"]
        Image.new("RGBA", (40, 40), (0, 0, 255, 255)).save(png)               # a different picture under the same name
        status, _, why = G.approval_state(proj, "coin")
        self.assertEqual(status, "changed_after_approval")
        self.assertIn("approve it again", why)
        with self.assertRaises(SystemExit) as e:
            SBD.resolve_img(out, "ai:coin")
        self.assertIn("changed_after_approval", str(e.exception))
        self.assertNotEqual(SBD.ai_asset(proj, "coin")[0], "approved")
        with self.assertRaises(SystemExit):
            G.set_status(proj, "coin", "approved", approved_by="owner")      # cannot approve a file that is not the generated one
        self.assertEqual(J.check(p, j["job_id"])["state"], "invalid")
        # a regenerated image is a new draft: it never inherits the old approval
        regen = J.submit(p, {**self.req, "regenerate": True}, runner=RUNNER)
        wait_state(p, regen["job_id"])
        self.assertEqual(G.approval_state(proj, "coin")[0], "draft")

    def test_old_approval_record_without_approved_hash_is_still_bound_to_manifest_hash(self):
        p = self.project("l")
        Dispatch.impl = ColorAgy(self.brain)
        j = self.submit_and_wait(p)
        proj = J.PROJECTS / p
        m = G.load_manifest(proj)
        m["assets"]["coin"].update(status="approved", approved_by="old")      # approval written before approved_sha256 existed
        m["assets"]["coin"].pop("approved_sha256", None)
        G.save_manifest(proj, m)
        self.assertEqual(G.approval_state(proj, "coin")[0], "approved")
        (proj / j["result"]["file"]).write_bytes(b"not the approved image")
        self.assertEqual(G.approval_state(proj, "coin")[0], "changed_after_approval")

    def test_failed_regeneration_never_destroys_the_good_approved_asset(self):
        p = self.project("f")
        proj = J.PROJECTS / p
        Dispatch.impl = ColorAgy(self.brain)
        j = self.submit_and_wait(p)
        G.set_status(proj, "coin", "approved", approved_by="owner")
        good_sha = G.load_manifest(proj)["assets"]["coin"]["sha256"]
        bad = FakeAgyNoTool(self.brain)
        spec = {"id": "coin", "kind": "prop", "prompt": "a gold coin, but bluer", "refs": [], "display": 200}
        for n in (1, 2):
            with self.assertRaises(RuntimeError):
                G.generate(proj, dict(spec), runner=bad)
            e = G.load_manifest(proj)["assets"]["coin"]
            self.assertEqual((e["status"], e["sha256"]), ("approved", good_sha), "the approved picture and its entry survive a failed run")
            self.assertEqual(G.approval_state(proj, "coin")[0], "approved")
            self.assertEqual(e["last_failure"]["fail_count"], n)
            self.assertEqual(G.sha_file(proj / e["file"]), good_sha)
            self.assertFalse((proj / "ai_assets" / "coin.new.png").exists())
        calls = len(bad.calls)
        with self.assertRaises(RuntimeError) as err:
            G.generate(proj, dict(spec), runner=bad)
        self.assertIn("blocked", str(err.exception))
        self.assertEqual(len(bad.calls), calls, "the failure memo still bounds retries")

    # 5 ---------------------------------------------------------------------------------------------------------------------
    def test_state_files_are_written_atomically(self):
        d = Path(tempfile.mkdtemp())
        f = d / "state.json"
        G.write_json_atomic(f, {"n": 0})
        stop, bad = threading.Event(), []

        def writer():
            try:
                for n in range(1, 400):
                    G.write_json_atomic(f, {"n": n, "pad": "x" * 20000})
            finally:
                stop.set()

        def reader():
            while not stop.is_set():
                try:
                    json.loads(f.read_text(encoding="utf-8"))               # raw read: no retry safety net
                except json.JSONDecodeError as e:
                    bad.append(str(e))
                except (PermissionError, FileNotFoundError):
                    pass                                                       # Windows sharing during replace: not a corrupt file
                time.sleep(0.002)

        ts = [threading.Thread(target=writer)] + [threading.Thread(target=reader) for _ in range(3)]
        [t.start() for t in ts]
        [t.join() for t in ts]
        self.assertEqual(bad, [], "a reader must never see a half-written file")
        self.assertEqual(G.read_json(f)["n"], 399)

    def test_checking_while_a_job_changes_state_never_fails(self):
        p = self.project("s")
        gate = threading.Event()
        Dispatch.impl = ColorAgy(self.brain, gate)
        j = J.submit(p, self.req, runner=RUNNER)
        errors, seen, stop = [], set(), threading.Event()

        def poll():
            while not stop.is_set():
                try:
                    seen.add(J.check(p, j["job_id"])["state"])
                except Exception as e:                                          # noqa: BLE001
                    errors.append(repr(e))

        ts = [threading.Thread(target=poll) for _ in range(3)]
        [t.start() for t in ts]
        time.sleep(0.3)
        gate.set()
        wait_state(p, j["job_id"])
        time.sleep(0.2)
        stop.set()
        [t.join() for t in ts]
        self.assertEqual(errors, [])
        self.assertIn("succeeded", seen)

    def test_manifest_updates_from_two_workers_do_not_lose_each_other(self):
        d = Path(tempfile.mkdtemp())

        def put(prefix):
            for n in range(40):
                G.put_asset(d, f"{prefix}{n}", {"id": f"{prefix}{n}", "status": "draft"})

        ts = [threading.Thread(target=put, args=(c,)) for c in "ab"]
        [t.start() for t in ts]
        [t.join() for t in ts]
        self.assertEqual(len(G.load_manifest(d)["assets"]), 80)


if __name__ == "__main__":
    unittest.main()
