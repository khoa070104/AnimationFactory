"""agy_image core without Antigravity (in-process fake runner): evidence rule, job-bound file lookup, reuse, bounded retries, timeouts,
failure memo, regeneration scope, approval, background removal / opaque mode / background crop."""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image

P2 = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(P2 / "tools"))
import agy_image as G  # noqa: E402


def fake_art(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    a = np.full((256, 256, 3), 255, dtype=np.uint8)
    yy, xx = np.mgrid[0:256, 0:256]
    d = np.hypot(xx - 128, yy - 128)
    a[d < 70] = (29, 29, 31)
    a[d < 62] = (250, 200, 61)
    a[(abs(xx - 128) < 6) & (abs(yy - 128) < 40)] = (255, 255, 255)       # white detail INSIDE the object must stay opaque
    Image.fromarray(a).save(path, "JPEG", quality=95)


class FakeAgy:
    def __init__(self, brain, use_tool=True, make_file=True, point_outside=False, raise_timeout=False):
        self.calls, self.brain = [], brain
        self.use_tool, self.make_file, self.point_outside, self.raise_timeout = use_tool, make_file, point_outside, raise_timeout

    def __call__(self, prompt, cwd, log_file, timeout=330):
        self.calls.append(prompt)
        if self.raise_timeout:
            raise G.AgyTimeout("hung")
        conv = f"conv{len(self.calls)}"
        out = self.brain / conv / "img.jpg"
        if self.point_outside:
            out = self.brain / "someone-else" / "img.jpg"
        if self.make_file:
            fake_art(out)
        Path(log_file).write_text('x model_config_manager.go:340] Propagating selected model override to backend: label="Fake (High)"\n', encoding="utf-8")
        ev = [{"event": "init"}]
        if self.use_tool:
            ev.append({"event": "step_update", "step_update": {"step_type": "subagent", "tool_name": "invoke_subagent",
                                                               "subagent_info": {"subagents": [{"type_name": "image-generator"}]}}})
        ev.append({"event": "result", "result": {"conversation_id": conv, "status": "SUCCESS", "response": f"[{out}](file:///{out}), tool: generate_image",
                                                 "usage": {"total_tokens": 1000}, "denied_actions": []}})
        return ev, ""


class T(unittest.TestCase):
    def setUp(self):
        self.proj = Path(tempfile.mkdtemp()) / "p"
        self.proj.mkdir()
        home = Path(tempfile.mkdtemp())                     # isolated fake agy home: no file can leak between tests
        os.environ["AGY_HOME"] = str(home)
        self.brain = home / "brain"
        self.brain.mkdir()
        self.spec = {"id": "coin", "kind": "prop", "prompt": "a coin", "refs": [], "display": 200}

    def test_generate_png_transparent_manifest_draft(self):
        f = FakeAgy(self.brain)
        e, called = G.generate(self.proj, dict(self.spec), runner=f)
        self.assertTrue(called)
        im = Image.open(self.proj / e["file"])
        self.assertEqual(im.mode, "RGBA")
        self.assertEqual(max(im.size), 400)                                  # 2x display
        a = np.asarray(im)
        self.assertEqual(a[0, 0, 3], 0, "corner must be transparent")
        self.assertEqual(a[a.shape[0] // 2, a.shape[1] // 2, 3], 255, "object centre must be opaque")
        self.assertEqual(e["status"], "draft")
        self.assertTrue(e["attempts"][0]["tool_evidence"])
        self.assertEqual(e["agent_model"], "Fake (High)")
        self.assertIsNone(e["image_model"])
        self.assertEqual(e["conversation_id"], "conv1")

    def test_reuse_does_not_call_agy_and_regenerate_only_that_asset(self):
        f = FakeAgy(self.brain)
        G.generate(self.proj, dict(self.spec), runner=f)
        G.generate(self.proj, {**self.spec, "id": "wallet", "prompt": "a wallet"}, runner=f)
        n = len(f.calls)
        _, called = G.generate(self.proj, dict(self.spec), runner=f)
        self.assertFalse(called)
        self.assertEqual(len(f.calls), n, "same request must not call agy")
        before = G.load_manifest(self.proj)["assets"]["wallet"]["sha256"]
        G.generate(self.proj, {**self.spec, "regenerate": True}, runner=f)
        self.assertEqual(len(f.calls), n + 1)
        self.assertEqual(G.load_manifest(self.proj)["assets"]["wallet"]["sha256"], before, "other assets untouched")
        _, called = G.generate(self.proj, {**self.spec, "prompt": "a bigger coin"}, runner=f)
        self.assertTrue(called, "changed prompt re-creates")

    def test_art_not_from_image_generator_is_rejected_with_bounded_retries(self):
        f = FakeAgy(self.brain, use_tool=False)
        with self.assertRaises(RuntimeError):
            G.generate(self.proj, dict(self.spec), runner=f, max_attempts=2)
        self.assertEqual(len(f.calls), 2)
        self.assertEqual(G.load_manifest(self.proj)["assets"]["coin"]["status"], "failed")
        self.assertFalse((self.proj / "ai_assets/coin.png").exists())

    def test_file_outside_this_jobs_conversation_is_never_used(self):
        f = FakeAgy(self.brain, point_outside=True)
        with self.assertRaises(RuntimeError) as c:
            G.generate(self.proj, dict(self.spec), runner=f, max_attempts=1)
        self.assertIn("no generated file", str(c.exception))
        self.assertTrue((self.brain / "someone-else" / "img.jpg").exists(), "the decoy exists and is newer, yet it was ignored")

    def test_timeout_is_reported_and_not_retried(self):
        f = FakeAgy(self.brain, raise_timeout=True)
        with self.assertRaises(RuntimeError) as c:
            G.generate(self.proj, dict(self.spec), runner=f, max_attempts=2)
        self.assertTrue(str(c.exception).startswith("timeout"))
        self.assertEqual(len(f.calls), 1, "a timed-out run is not retried")

    def test_failing_request_is_blocked_after_two_failures(self):
        f = FakeAgy(self.brain, make_file=False)
        for _ in range(2):
            with self.assertRaises(RuntimeError):
                G.generate(self.proj, dict(self.spec), runner=f, max_attempts=1)
        n = len(f.calls)
        with self.assertRaises(RuntimeError) as c:
            G.generate(self.proj, dict(self.spec), runner=f, max_attempts=1)
        self.assertIn("blocked", str(c.exception))
        self.assertEqual(len(f.calls), n, "blocked request must not call agy")
        with self.assertRaises(RuntimeError):
            G.generate(self.proj, {**self.spec, "regenerate": True}, runner=f, max_attempts=1)
        self.assertEqual(len(f.calls), n + 1, "regenerate overrides the block")

    def test_approve_background_crop_and_opaque_prop(self):
        G.generate(self.proj, dict(self.spec), runner=FakeAgy(self.brain))
        G.set_status(self.proj, "coin", "approved", approved_by="owner")
        self.assertEqual(G.load_manifest(self.proj)["assets"]["coin"]["status"], "approved")
        e, _ = G.generate(self.proj, {"id": "bg", "kind": "background", "prompt": "office", "refs": [], "display": 480}, runner=FakeAgy(self.brain))
        self.assertEqual(Image.open(self.proj / e["file"]).size, (960, 540))
        e, _ = G.generate(self.proj, {**self.spec, "id": "solid", "transparent": False}, runner=FakeAgy(self.brain))
        self.assertEqual(np.asarray(Image.open(self.proj / e["file"]))[0, 0, 3], 255)
        self.assertFalse(e["transparent"])

    def test_transparent_request_on_art_without_white_background_is_rejected(self):
        class Gray(FakeAgy):
            def __call__(self, prompt, cwd, log_file, timeout=330):
                ev, err = super().__call__(prompt, cwd, log_file, timeout)
                p = self.brain / f"conv{len(self.calls)}" / "img.jpg"
                Image.new("RGB", (256, 256), (120, 120, 130)).save(p, "JPEG")        # full-bleed grey: nothing to remove
                return ev, err
        with self.assertRaises(RuntimeError) as c:
            G.generate(self.proj, dict(self.spec), runner=Gray(self.brain))
        self.assertIn("no plain white background", str(c.exception))
        self.assertFalse((self.proj / "ai_assets/coin.png").exists())
        self.assertEqual(G.load_manifest(self.proj)["assets"]["coin"]["status"], "failed")
        # opaque request on the same art is fine
        e, _ = G.generate(self.proj, {**self.spec, "id": "flat", "transparent": False}, runner=Gray(self.brain))
        self.assertFalse(e["transparent"])

    def test_good_transparency_is_recorded(self):
        e, _ = G.generate(self.proj, dict(self.spec), runner=FakeAgy(self.brain))
        self.assertTrue(e["transparency_check"]["ok"])
        self.assertEqual(e["transparency_check"]["corner_alpha"], [0, 0, 0, 0])

    def test_transcript_media_locates_the_file(self):
        conv, sub = "parent", "child"
        img = self.brain / conv / "x.jpg"
        fake_art(img)
        tr = self.brain / sub / ".system_generated" / "logs" / "transcript.jsonl"
        tr.parent.mkdir(parents=True)
        tr.write_text(json.dumps({"media": [{"mime_type": "image/jpeg", "uri": "file:///" + str(img).replace("\\", "/")}]}) + "\n", encoding="utf-8")
        info = {"conversation_id": conv, "subagent_ids": [sub], "transcripts": ["file:///" + str(tr).replace("\\", "/")], "response_paths": []}
        self.assertEqual(G.locate_output(info), img.resolve())


if __name__ == "__main__":
    unittest.main(verbosity=2)
