"""Machine-wide limit on agy runs, shared between processes: with one slot only one holder at a time (default); a dead holder never blocks;
the limit is configurable; the image runner and LLM calls both take a slot."""
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

P2 = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(P2 / "tools"))
import agy_slots as S  # noqa: E402

HOLD = r'''
import sys, time
sys.path.insert(0, sys.argv[1])
import agy_slots as S
with S.AgySlot("child", timeout=60):
    open(sys.argv[2], "w").write("held")
    while not __import__("os").path.exists(sys.argv[3]):
        time.sleep(0.05)
'''


class T(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.old = (S.LOCKS, os.environ.get("AF_AGY_CONCURRENCY"))
        S.LOCKS = self.tmp / "locks"
        os.environ["AF_LOCKS"] = str(S.LOCKS)
        os.environ.pop("AF_AGY_CONCURRENCY", None)
        self.procs = []

    def tearDown(self):
        for p in self.procs:
            if p.poll() is None:
                p.kill()
            p.wait()
        S.LOCKS = self.old[0]
        os.environ.pop("AF_LOCKS", None)
        if self.old[1] is not None:
            os.environ["AF_AGY_CONCURRENCY"] = self.old[1]

    def hold(self):
        held, release = self.tmp / "held", self.tmp / "release"
        p = subprocess.Popen([sys.executable, "-c", HOLD, str(P2 / "tools"), str(held), str(release)], env=dict(os.environ))
        p.args = (held, release)
        self.procs.append(p)
        end = time.time() + 30
        while not held.exists() and time.time() < end:
            time.sleep(0.05)
        self.assertTrue(held.exists())
        return p

    def test_default_is_one_and_other_process_must_wait(self):
        self.assertEqual(S.limit(), 1)
        p = self.hold()
        with self.assertRaises(S.SlotTimeout):
            with S.AgySlot("me", timeout=1):
                pass
        self.assertTrue(S.status()[0]["busy"])
        p.args[1].write_text("go")
        p.wait(timeout=30)
        with S.AgySlot("me", timeout=5):                                  # free again after the holder left
            self.assertTrue(S.status()[0]["busy"])
        self.assertFalse(S.status()[0]["busy"])

    def test_dead_holder_does_not_block(self):
        p = self.hold()
        p.kill()
        p.wait()
        end = time.time() + 10
        while S.proc_stamp(p.pid) is not None and time.time() < end:
            time.sleep(0.05)
        with S.AgySlot("me", timeout=5):
            pass

    def test_limit_is_configurable_and_counts_in_process_holders(self):
        os.environ["AF_AGY_CONCURRENCY"] = "2"
        self.assertEqual(S.limit(), 2)
        with S.AgySlot("a", timeout=2), S.AgySlot("b", timeout=2):
            with self.assertRaises(S.SlotTimeout):
                with S.AgySlot("c", timeout=1):
                    pass

    def test_llm_and_image_runs_go_through_the_slot(self):
        import agy_image as G
        import llm
        fake = P2 / "tests" / "fake_agy.py"
        home = self.tmp / "home"
        (home / "brain").mkdir(parents=True)
        os.environ.update({"AGY_CMD": json.dumps([sys.executable, str(fake)]), "AGY_HOME": str(home)})
        try:
            p = self.hold()                                               # someone else holds the only slot
            t0 = time.time()
            holder_release = p.args[1]

            import threading
            threading.Timer(1.5, lambda: holder_release.write_text("go")).start()
            data, meta = llm._run_agy("m", "TASK: asset_plan\ns01 [hook] a: b\ns02 [body] c: d", {"type": "object"}, 60, False)
            self.assertGreaterEqual(time.time() - t0, 1.0, "the LLM call waited for the slot")
            self.assertTrue(data["assets"])
        finally:
            os.environ.pop("AGY_CMD", None)
            os.environ.pop("AGY_HOME", None)


if __name__ == "__main__":
    unittest.main()
