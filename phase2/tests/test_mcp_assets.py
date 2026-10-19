"""End-to-end MCP tests over stdio with a test double for agy (AGY_CMD -> tests/fake_agy.py): protocol, async jobs, reuse, failure/timeouts,
bounded retries, job-bound file lookup, project scoping, persistence across restarts. No Antigravity call, no credit."""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

import numpy as np
from PIL import Image

P2 = Path(__file__).resolve().parent.parent
SERVER = P2 / "assets_mcp/af_assets_server.py"
FAKE = P2 / "tests/fake_agy.py"


class Client:
    def __init__(self, env_extra):
        env = dict(os.environ, PYTHONIOENCODING="utf-8", **env_extra)
        self.p = subprocess.Popen([sys.executable, str(SERVER)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8", env=env)
        self.n = 0
        self.rpc("initialize", {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "test", "version": "0"}})
        self.p.stdin.write(json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}) + "\n")
        self.p.stdin.flush()

    def rpc(self, method, params=None):
        self.n += 1
        self.p.stdin.write(json.dumps({"jsonrpc": "2.0", "id": self.n, "method": method, "params": params or {}}) + "\n")
        self.p.stdin.flush()
        while True:
            line = self.p.stdout.readline()
            if not line:
                raise RuntimeError("server closed: " + self.p.stderr.read()[-500:])
            msg = json.loads(line)
            if msg.get("id") == self.n:
                return msg

    def tool(self, name, args):
        r = self.rpc("tools/call", {"name": name, "arguments": args})["result"]
        text = r["content"][0]["text"]
        return r["isError"], (json.loads(text) if not r["isError"] else text)

    def wait(self, project, job_id, timeout=60):
        t0 = time.time()
        while time.time() - t0 < timeout:
            err, job = self.tool("check_asset_job", {"project": project, "job_id": job_id})
            assert not err, job
            if job["state"] not in ("queued", "running"):
                return job
            time.sleep(0.4)
        raise AssertionError("job did not finish in time")

    def close(self):
        try:
            self.p.stdin.close()
            self.p.wait(timeout=10)
        except Exception:
            self.p.kill()


class T(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.name = f"_t_mcp_{os.getpid()}"
        cls.proj = P2 / "projects" / cls.name
        cls.proj.mkdir(parents=True)
        (cls.proj / "storyboard.json").write_text("{}", encoding="utf-8")
        (cls.proj / "brief.json").write_text('{"budget": {"images": 100}}', encoding="utf-8")      # this class runs many test-double jobs in one project
        cls.home = Path(tempfile.mkdtemp())
        (cls.home / "brain").mkdir()
        cls.count = cls.home / "count.txt"
        cls.ref = cls.home / "ref.png"
        Image.new("RGB", (64, 64), (200, 30, 30)).save(cls.ref)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.proj, ignore_errors=True)

    def env(self, mode="ok"):
        return {"AGY_HOME": str(self.home), "AGY_CMD": json.dumps([sys.executable, str(FAKE)]), "FAKE_AGY_MODE": mode, "FAKE_AGY_COUNT": str(self.count)}

    def calls(self):
        return len(self.count.read_text().splitlines()) if self.count.exists() else 0

    def test_1_protocol_and_two_tools(self):
        c = Client(self.env())
        try:
            tools = c.rpc("tools/list")["result"]["tools"]
            self.assertEqual({t["name"] for t in tools}, {"submit_asset_job", "check_asset_job"})
            sub = [t for t in tools if t["name"] == "submit_asset_job"][0]["inputSchema"]
            self.assertEqual(set(sub["required"]), {"project", "asset_id", "kind", "prompt"})
            for k in ("reference_images", "transparent_background", "kind"):
                self.assertIn(k, sub["properties"])
            self.assertEqual(c.rpc("ping")["result"], {})
            self.assertEqual(c.rpc("nope/x")["error"]["code"], -32601)
        finally:
            c.close()

    def test_2_job_lifecycle_result_reuse_and_isolation(self):
        c = Client(self.env())
        try:
            before = self.calls()
            err, job = c.tool("submit_asset_job", {"project": self.name, "asset_id": "coin", "kind": "prop", "prompt": "a coin", "display_width": 200, "reference_images": [str(self.ref)]})
            self.assertFalse(err)
            self.assertIn(job["state"], ("queued", "running"))
            done = c.wait(self.name, job["job_id"])
            self.assertEqual(done["state"], "succeeded", done)
            r = done["result"]
            png = self.proj / r["file"]                                         # inside THIS project's ai_assets
            self.assertEqual(png.parent, self.proj / "ai_assets")
            im = Image.open(png)
            self.assertEqual(im.mode, "RGBA")
            self.assertEqual(np.asarray(im)[0, 0, 3], 0)
            self.assertEqual(r["sha256"], hashlib.sha256(png.read_bytes()).hexdigest())
            self.assertTrue(r["tool_evidence"])
            self.assertEqual(r["status"], "draft")
            self.assertEqual(r["conversation_id"] is not None, True)
            self.assertEqual(r["usage"]["total_tokens"], 1234)
            self.assertIn("owner must approve", done["use_in_scene"])
            self.assertEqual(done["scene_item"]["img"], "ai:coin")
            m = json.loads((self.proj / "ai_assets/manifest.json").read_text(encoding="utf-8"))["assets"]["coin"]
            self.assertEqual(m["agent_model"], "Fake Model (High)")
            self.assertEqual(m["refs"][0]["sha256"], hashlib.sha256(self.ref.read_bytes()).hexdigest())
            self.assertIn("ref.png", m["full_prompt"])
            self.assertEqual(self.calls(), before + 1)
            # same request again -> same job, stored result, no new agy run
            err, again = c.tool("submit_asset_job", {"project": self.name, "asset_id": "coin", "kind": "prop", "prompt": "a coin", "display_width": 200, "reference_images": [str(self.ref)]})
            self.assertEqual(again["job_id"], job["job_id"])
            self.assertIn("stored result", again["note"])
            self.assertTrue(again["reused_now"])
            self.assertFalse(again["new_generation"])
            self.assertEqual(self.calls(), before + 1)
            # result survives a server restart
            c.close()
            c2 = Client(self.env())
            try:
                err, job2 = c2.tool("check_asset_job", {"project": self.name, "job_id": job["job_id"]})
                self.assertEqual(job2["state"], "succeeded")
            finally:
                c2.close()
        finally:
            c.close()

    def test_3_failure_is_reported_retries_are_bounded_then_blocked(self):
        c = Client(self.env("notool"))
        try:
            before = self.calls()
            args = {"project": self.name, "asset_id": "drawn_by_code", "kind": "prop", "prompt": "a drawing"}
            _, j = c.tool("submit_asset_job", args)
            done = c.wait(self.name, j["job_id"])
            self.assertEqual(done["state"], "failed")
            self.assertIn("image generator was not used", done["error"])
            self.assertEqual(self.calls(), before + 2, "at most 2 attempts per run")
            _, j2 = c.tool("submit_asset_job", args)                              # one more run allowed (fail_count 1 < 2)
            c.wait(self.name, j2["job_id"])
            n = self.calls()
            _, j3 = c.tool("submit_asset_job", args)                              # now blocked: no agy call at all
            self.assertIn("blocked", j3["note"])
            time.sleep(1.0)
            self.assertEqual(self.calls(), n)
            self.assertFalse((self.proj / "ai_assets/drawn_by_code.png").exists())
        finally:
            c.close()

    def test_4_timeout_is_clear_and_bounded(self):
        c = Client(self.env("hang"))
        try:
            before = self.calls()
            t0 = time.time()
            _, j = c.tool("submit_asset_job", {"project": self.name, "asset_id": "slow", "kind": "prop", "prompt": "never finishes", "timeout_seconds": 30})
            done = c.wait(self.name, j["job_id"], timeout=70)
            self.assertEqual(done["state"], "timeout")
            self.assertIn("timeout after 30s", done["error"])
            self.assertLess(time.time() - t0, 60)
            self.assertEqual(self.calls(), before + 1, "no automatic retry after a timeout")
        finally:
            c.close()

    def test_5_file_comes_from_the_jobs_own_conversation(self):
        c = Client(self.env("decoy_newer"))
        try:
            _, j = c.tool("submit_asset_job", {"project": self.name, "asset_id": "own", "kind": "prop", "prompt": "own image"})
            done = c.wait(self.name, j["job_id"])
            self.assertEqual(done["state"], "succeeded")
            m = json.loads((self.proj / "ai_assets/manifest.json").read_text(encoding="utf-8"))["assets"]["own"]
            self.assertNotIn("other-conversation", m["generated_file"])
            self.assertIn(m["conversation_id"], m["generated_file"] + "".join(m["subagent_ids"]))
        finally:
            c.close()
        c = Client(self.env("decoy_response"))
        try:
            _, j = c.tool("submit_asset_job", {"project": self.name, "asset_id": "wrongfile", "kind": "prop", "prompt": "points elsewhere"})
            done = c.wait(self.name, j["job_id"])
            self.assertEqual(done["state"], "failed")
            self.assertIn("no generated file", done["error"])
        finally:
            c.close()

    def test_6_invalid_requests_are_rejected_clearly(self):
        c = Client(self.env())
        try:
            for args in ({"project": "../../etc", "asset_id": "x", "kind": "prop", "prompt": "abc"},
                         {"project": self.name, "asset_id": "Bad Id", "kind": "prop", "prompt": "abc"},
                         {"project": self.name, "asset_id": "ok", "kind": "video", "prompt": "abc"},
                         {"project": self.name, "asset_id": "ok", "kind": "prop", "prompt": "abc", "reference_images": ["Z:/nope.png"]},
                         {"project": self.name, "asset_id": "ok", "kind": "prop", "prompt": "abc", "timeout_seconds": 100000},
                         {"project": "nonexistent_project", "asset_id": "ok", "kind": "prop", "prompt": "abc"}):
                err, text = c.tool("submit_asset_job", args)
                self.assertTrue(err, args)
                self.assertIn("invalid request", text)
            err, text = c.tool("check_asset_job", {"project": self.name, "job_id": "does_not_exist-0000000000"})
            self.assertTrue(err)
        finally:
            c.close()

    def test_7_interrupted_job_is_flagged_not_silently_rerun(self):
        c = Client(self.env())
        try:
            jobs = self.proj / "ai_assets/jobs"
            jobs.mkdir(parents=True, exist_ok=True)
            jid = "ghost-abcdef0123"
            (jobs / f"{jid}.json").write_text(json.dumps({"job_id": jid, "asset_id": "ghost", "state": "running", "signature": "x"}), encoding="utf-8")
            before = self.calls()
            _, job = c.tool("check_asset_job", {"project": self.name, "job_id": jid})
            self.assertEqual(job["state"], "interrupted")
            self.assertEqual(self.calls(), before)
        finally:
            c.close()


if __name__ == "__main__":
    unittest.main(verbosity=2)
