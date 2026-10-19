"""Shared test doubles for asset jobs. ONE module instance, whichever way the test files are loaded (path style or discover): the job worker thread is
process-wide and keeps the runner it started with, so every test must swap the implementation on the SAME Dispatch class."""
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image

P2 = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(P2 / "tools"))
sys.path.insert(0, str(P2 / "tests"))
import agy_jobs as J  # noqa: E402
from test_agy_image import FakeAgy  # noqa: E402

class ColorAgy(FakeAgy):
    """FakeAgy whose art differs per call (so two requests give two different files); optional gate to hold a run open."""

    def __init__(self, brain, gate=None):
        super().__init__(brain)
        self.gate = gate

    def __call__(self, prompt, cwd, log_file, timeout=330):
        if self.gate is not None:
            self.gate.wait(30)
        ev, err = super().__call__(prompt, cwd, log_file, timeout)
        f = self.brain / f"conv{len(self.calls)}" / "img.jpg"
        a = np.asarray(Image.open(f).convert("RGB")).copy()
        a[(a[:, :, 0] > 200) & (a[:, :, 2] < 120)] = (40 * len(self.calls) % 256, 120, 200)
        Image.fromarray(a).save(f, "JPEG", quality=95)
        return ev, err


class FakeAgyNoTool(FakeAgy):
    def __init__(self, brain):
        super().__init__(brain, use_tool=False)


class Dispatch:
    """The job worker thread is process-wide and keeps the runner it started with; tests swap what it forwards to."""
    impl = None

    def __call__(self, prompt, cwd, log_file, timeout=330):
        return Dispatch.impl(prompt, cwd, log_file, timeout)


RUNNER = Dispatch()


def wait_state(project, job_id, states=("succeeded", "failed", "timeout", "interrupted"), secs=40):
    end = time.time() + secs
    while time.time() < end:
        j = J.check(project, job_id)
        if j["state"] in states:
            return j
        time.sleep(0.05)
    raise AssertionError(f"job {job_id} stayed {j['state']}")




FIX = Path(__file__).resolve().parent / "fixtures"


class SheetAgy(FakeAgy):
    """Image double that answers character-sheet requests with the real Antigravity sheets kept in tests/fixtures (flattened on white like agy's JPEG),
    and any other request with the plain FakeAgy art. `broken` = answer the parts request with a picture that is not 4 separate pieces (first N times)."""

    def __init__(self, brain, broken_parts=0):
        super().__init__(brain)
        self.broken_parts = broken_parts

    def __call__(self, prompt, cwd, log_file, timeout=330):
        ev, err = super().__call__(prompt, cwd, log_file, timeout)
        f = self.brain / f"conv{len(self.calls)}" / "img.jpg"
        src = None
        if "BODY-PARTS sheet" in prompt:
            src = "mai_parts_sheet.png"
            if self.broken_parts > 0:
                self.broken_parts -= 1
                src = "mai_faces_sheet.png"                           # five heads where four parts were asked for
        elif "HEADS sheet" in prompt:
            src = "mai_faces_sheet.png"
        if src:
            im = Image.open(FIX / src).convert("RGBA")
            white = Image.new("RGB", im.size, (255, 255, 255))
            white.paste(im, (0, 0), im)
            pad = Image.new("RGB", (im.width + 160, im.height + 160), (255, 255, 255))
            pad.paste(white, (80, 80))
            pad.save(f, "JPEG", quality=95)
        return ev, err
