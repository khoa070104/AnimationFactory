"""Asset jobs across REAL processes (the UI server and the MCP server are separate processes sharing one project):
a job is owned by the process that runs it; other processes see it as running, never interrupt it, never start it twice;
if the owner dies the job becomes `interrupted` and can be submitted again. Test-double agy only, no paid calls."""
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
import agy_jobs as J  # noqa: E402
from imgdouble import ColorAgy, Dispatch, RUNNER, wait_state  # noqa: E402

HELPER = str(P2 / "tests" / "job_proc_a.py")
REQ = {"asset_id": "coin", "kind": "prop", "prompt": "a gold coin", "display_width": 200}


class T(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        home = self.tmp / "home"
        (home / "brain").mkdir(parents=True)
        os.environ["AGY_HOME"] = str(home)
        self.home = home
        self.name = f"_t_proc_{os.getpid()}_{int(time.time() * 1000) % 100000}"
        self.proj = J.PROJECTS / self.name
        self.proj.mkdir(parents=True)
        (self.proj / "storyboard.json").write_text("{}", encoding="utf-8")
        self.release, self.counter, self.ready = self.tmp / "release", self.tmp / "count.txt", self.tmp / "ready"
        self.procs = []

    def tearDown(self):
        for p in self.procs:
            if p.poll() is None:
                p.kill()
            p.wait()
            p.stdout.close()
        shutil.rmtree(self.proj, ignore_errors=True)

    def start(self, ready=None):
        p = subprocess.Popen([sys.executable, HELPER, self.name, str(self.release), str(self.counter), str(ready or self.ready), json.dumps(REQ)],
                             stdout=subprocess.PIPE, text=True, encoding="utf-8", env=os.environ.copy())
        self.procs.append(p)
        return p

    def wait_for(self, path, secs=30):
        end = time.time() + secs
        while not path.exists():
            if time.time() > end:
                raise AssertionError(f"{path.name} never appeared")
            time.sleep(0.05)

    def calls(self):
        return len(self.counter.read_text(encoding="utf-8").split()) if self.counter.exists() else 0

    def jobfile(self, job_id):
        return json.loads((self.proj / "ai_assets/jobs" / f"{job_id}.json").read_text(encoding="utf-8"))

    # ---------------------------------------------------------------------------------------------------------------------
    def test_other_process_sees_running_and_cannot_interrupt_or_restart(self):
        a = self.start()
        info = json.loads(a.stdout.readline())
        self.wait_for(self.ready)                                         # A's job is running: A's fake agy was called once
        self.assertEqual(self.calls(), 1)
        counting = ColorAgy(self.home / "brain")
        Dispatch.impl = counting                                          # this process = B (e.g. the UI server)
        job_id = f"coin-{J.G.signature(G.normalise({'id': 'coin', **{k: REQ[k] for k in ('kind', 'prompt')}, 'display': 200}), [])[:10]}"
        for _ in range(3):
            j = J.check(self.name, job_id)
            self.assertEqual(j["state"], "running", "B's check must not turn A's running job into `interrupted`")
            self.assertEqual(j["owner"]["pid"], info["pid"])
            time.sleep(0.1)
        again = J.submit(self.name, REQ, runner=RUNNER)                   # B re-submits the same request
        self.assertEqual(again["job_id"], job_id)
        self.assertEqual(again["state"], "running")
        self.assertEqual(again["run"], 1, "no new run")
        self.assertIn(f"process {info['pid']}", again["note"])
        self.assertEqual(self.jobfile(job_id)["state"], "running")
        self.assertEqual(self.jobfile(job_id)["run"], 1)
        self.assertEqual((self.calls(), len(counting.calls)), (1, 0), "the test double must have been called exactly once, by A")
        self.release.write_text("go", encoding="utf-8")
        self.assertEqual(wait_state(self.name, job_id)["state"], "succeeded")
        self.assertEqual(a.stdout.readline().strip(), "succeeded")
        self.assertEqual((self.calls(), len(counting.calls)), (1, 0))
        done = J.submit(self.name, REQ, runner=RUNNER)                    # finished: stored result, still no run
        self.assertTrue(done["reused_now"])
        self.assertEqual((self.calls(), len(counting.calls)), (1, 0))

    def test_two_processes_submitting_at_once_start_one_run(self):
        a = self.start(self.tmp / "ready_a")
        b = self.start(self.tmp / "ready_b")
        first = [json.loads(a.stdout.readline()), json.loads(b.stdout.readline())]
        time.sleep(0.5)
        self.assertEqual(self.calls(), 1, "exactly one of the two processes owns and runs the job")
        self.assertEqual(sorted(x["run"] for x in first), [1, 1])
        self.assertEqual(sum(1 for x in first if x["note"]), 1, "the other one got the existing job back")
        self.release.write_text("go", encoding="utf-8")
        self.assertEqual((a.stdout.readline().strip(), b.stdout.readline().strip()), ("succeeded", "succeeded"))
        self.assertEqual(self.calls(), 1)

    def test_owner_crash_is_detected_and_the_request_can_be_resubmitted(self):
        a = self.start()
        info = json.loads(a.stdout.readline())
        self.wait_for(self.ready)
        job_id = J.check(self.name, f"coin-{next(f.stem.split('-')[1] for f in (self.proj / 'ai_assets/jobs').glob('coin-*.json'))}")["job_id"]
        self.assertEqual(J.check(self.name, job_id)["state"], "running")
        a.kill()                                                           # A dies abnormally, mid-run
        a.wait()
        end = time.time() + 10
        while J.proc_stamp(info["pid"]) is not None and time.time() < end:
            time.sleep(0.05)
        j = J.check(self.name, job_id)
        self.assertEqual(j["state"], "interrupted")
        self.assertIn("stopped", j["error"])
        self.assertEqual(self.jobfile(job_id)["state"], "interrupted")
        counting = ColorAgy(self.home / "brain")
        Dispatch.impl = counting
        again = J.submit(self.name, REQ, runner=RUNNER)                   # recovery: the same request runs again, from this process
        self.assertEqual(again["run"], 2)
        self.assertEqual(again["owner"]["pid"], os.getpid())
        self.assertEqual(wait_state(self.name, job_id)["state"], "succeeded")
        self.assertEqual((self.calls(), len(counting.calls)), (1, 1), "A's double once (it died), B's once")
        self.assertEqual(G.load_manifest(self.proj)["assets"]["coin"]["status"], "draft")

    def test_recycled_pid_is_not_taken_for_the_owner(self):
        a = self.start()
        json.loads(a.stdout.readline())
        self.wait_for(self.ready)
        path = next((self.proj / "ai_assets/jobs").glob("coin-*.json"))
        j = json.loads(path.read_text(encoding="utf-8"))
        j["owner"]["stamp"] = "1:1"                                        # same pid, but a different process incarnation
        G.write_json_atomic(path, j)
        self.assertEqual(J.check(self.name, j["job_id"])["state"], "interrupted")
        self.release.write_text("go", encoding="utf-8")                    # let the helper finish
        a.wait(timeout=60)


if __name__ == "__main__":
    unittest.main()
