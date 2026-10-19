"""Helper process for test_job_processes.py: submits an asset job with a test-double runner that counts its calls and waits for a release
file, then stays alive until the job reaches a final state.
Usage: job_proc_a.py PROJECT RELEASE_FILE COUNTER_FILE READY_FILE REQUEST_JSON   (env AGY_HOME = fake agy home)"""
import json
import os
import sys
import time
from pathlib import Path

P2 = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(P2 / "tools"))
sys.path.insert(0, str(P2 / "tests"))
import agy_jobs as J  # noqa: E402
from test_agy_image import FakeAgy  # noqa: E402

project, release, counter, ready = sys.argv[1:5]
req = json.loads(sys.argv[5])
fake = FakeAgy(Path(os.environ["AGY_HOME"]) / "brain")


def runner(prompt, cwd, log_file, timeout=330):
    with open(counter, "a", encoding="utf-8") as f:
        f.write(f"{os.getpid()}\n")
    Path(ready).write_text(str(os.getpid()), encoding="utf-8")
    end = time.time() + 120
    while not Path(release).exists() and time.time() < end:
        time.sleep(0.05)
    return fake(prompt, cwd, log_file, timeout)


job = J.submit(project, req, runner=runner)
print(json.dumps({"pid": os.getpid(), "state": job["state"], "run": job.get("run"), "note": job.get("note")}), flush=True)
while True:
    state = J.check(project, job["job_id"])["state"]
    if state not in ("queued", "running"):
        break
    time.sleep(0.1)
print(state, flush=True)
