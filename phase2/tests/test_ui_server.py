"""UI server: security, channel profile, project from a brief, storyboard form editing (validate / version / realign), approvals by kind + history,
AI preparation through the real subprocess path (fake agy), AI revision proposals, asset review, budget refusal, export. No paid call."""
import json
import os
import shutil
import sys
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

P2 = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(P2 / "ui"))
import server as S  # noqa: E402

FAKE = str(P2 / "tests" / "fake_agy.py")


class T(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.home = Path(tempfile.mkdtemp())
        (cls.home / "brain").mkdir()
        cls.env = {"AGY_CMD": json.dumps([sys.executable, FAKE]), "AGY_HOME": str(cls.home), "FAKE_AGY_COUNT": str(cls.home / "count.txt"), "AF_LOCKS": str(cls.home / "locks")}
        cls.old = {k: os.environ.get(k) for k in cls.env}
        os.environ.update(cls.env)
        cls.srv = S.make_server(0)
        cls.port = cls.srv.server_address[1]
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
        cls.names = []
        cls.chans = []
        cls.base = f"http://127.0.0.1:{cls.port}"

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        for n in cls.names:
            shutil.rmtree(P2 / "projects" / n, ignore_errors=True)
        for c in cls.chans:
            (S.CH.CH / f"{c}.json").unlink(missing_ok=True)
        for k, v in cls.old.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    def call(self, method, path, body=None, token=True, host=None, raw=False):
        req = urllib.request.Request(self.base + path, method=method, data=(json.dumps(body).encode() if body is not None else None))
        if token:
            req.add_header("X-AF-Token", S.TOKEN)
        req.add_header("Content-Type", "application/json")
        if host:
            req.add_header("Host", host)
        try:
            with urllib.request.urlopen(req, timeout=90) as r:
                data = r.read()
                return r.status, (data if raw else json.loads(data))
        except urllib.error.HTTPError as e:
            data = e.read()
            return e.code, (data if raw else json.loads(data))

    def new(self, title, **kw):
        c, r = self.call("POST", "/api/projects", {"title": title, "research": "no", "character_mode": "bi", **kw})
        self.assertEqual(c, 200, r)
        self.names.append(r["created"])
        return r["created"]

    def wait_idle(self, name, timeout=180):
        t0 = time.time()
        while time.time() - t0 < timeout:
            _, v = self.call("GET", f"/api/project/{name}")
            if not v["running"]:
                return v
            time.sleep(0.5)
        self.fail("run did not finish")

    def prepare(self, name, step="all", force=()):
        c, r = self.call("POST", f"/api/project/{name}/run", {"kind": "prepare", "step": step, "force": list(force)})
        self.assertEqual(c, 200, r)
        self.wait_idle(name)
        return self.call("GET", f"/api/project/{name}/prepare")[1]

    def test_01_security(self):
        self.assertEqual(self.call("GET", "/api/projects", token=False)[0], 403)
        self.assertEqual(self.call("GET", "/api/projects", host="evil.example.com")[0], 403)
        code, html = self.call("GET", "/", token=False, raw=True)
        self.assertEqual(code, 200)
        self.assertIn(S.TOKEN.encode(), html)

    def test_02_channel_profile_is_saved_and_validated(self):
        cid = f"t_chan_{os.getpid()}"
        self.chans.append(cid)
        c, r = self.call("GET", "/api/channel/default")
        self.assertEqual(c, 200)
        prof = dict(r["profile"], name="Kênh thử UI", tone="ấm áp")
        self.assertEqual(self.call("PUT", f"/api/channel/{cid}", {"profile": prof})[0], 200)
        self.assertIn(cid, [x["id"] for x in self.call("GET", "/api/channels")[1]["channels"]])
        self.assertEqual(self.call("GET", f"/api/channel/{cid}")[1]["profile"]["tone"], "ấm áp")
        bad = dict(prof, character={"name": "Bi", "shirt": "orange"})
        self.assertEqual(self.call("PUT", f"/api/channel/{cid}", {"profile": bad})[0], 400)
        self.assertEqual(self.call("PUT", "/api/channel/Bad%20Id", {"profile": prof})[0], 400)

    def test_03_project_from_brief_form_edit_version_realign_feedback(self):
        n = self.new("Thử giao diện nhập liệu", goal="mục tiêu", message="thông điệp", duration_seconds=70, budget={"llm_calls": 30})
        _, v = self.call("GET", f"/api/project/{n}")
        self.assertEqual((v["has_storyboard"], v["scenes"], v["status"]["state"]), (False, [], "brief"))
        self.assertEqual(v["brief"]["duration_seconds"], 70)
        self.assertEqual(self.call("POST", "/api/projects", {"title": ""})[0], 400)
        c, r = self.call("POST", f"/api/project/{n}/scenes", {})
        self.assertEqual((c, r["scene"]), (200, "s01"))
        _, sc = self.call("GET", f"/api/project/{n}/scenes")
        scene = sc["scenes"][0]
        scene["voice"] = "Một câu thoại mẫu để thử các mốc hành động và phụ đề."
        scene["actions"] = [{"name": "nod", "cue": "câu thoại mẫu"}]
        scene["items"] = [{"type": "text", "text": "Chữ", "x": 1400, "y": 500, "size": 64, "color": "dark", "appear": "mốc hành động"}]
        c, r = self.call("PUT", f"/api/project/{n}/scene/s01", {"scene": scene})
        self.assertEqual(c, 200, r)
        bad = json.loads(json.dumps(scene))
        bad["actions"] = [{"name": "moonwalk", "at": 0}]
        h0 = self.call("GET", f"/api/project/{n}/scenes")[1]["hash"]
        c, r = self.call("PUT", f"/api/project/{n}/scene/s01", {"scene": bad})
        self.assertEqual(c, 422)
        self.assertTrue(any("moonwalk" in e for e in r["errors"]))
        self.assertEqual(self.call("GET", f"/api/project/{n}/scenes")[1]["hash"], h0)
        self.assertTrue(list((P2 / "projects" / n / "versions").glob("storyboard_v*_before_*.json")))
        c, r = self.call("PUT", f"/api/project/{n}/scene/s01/voice", {"text": "Một lời đọc khác hẳn, không còn cụm cũ nào cả."})
        self.assertEqual(c, 200, r)
        self.assertTrue(r["realigned"])
        _, v = self.call("GET", f"/api/project/{n}")
        self.assertEqual(" ".join(v["scenes"][0]["subtitles"]), "Một lời đọc khác hẳn, không còn cụm cũ nào cả.")
        c, r = self.call("POST", f"/api/project/{n}/scenes", {"after": "s01"})
        self.assertEqual(r["scene"], "s02")
        self.assertEqual(self.call("POST", f"/api/project/{n}/scene/s02/move", {"dir": "up"})[0], 200)
        self.assertEqual([s["id"] for s in self.call("GET", f"/api/project/{n}")[1]["scenes"]], ["s02", "s01"])
        self.assertEqual(self.call("POST", f"/api/project/{n}/scene/s02/delete", {})[0], 200)
        self.assertEqual(self.call("POST", f"/api/project/{n}/scene/s01/delete", {})[0], 400, "the last scene cannot be deleted")
        c, r = self.call("POST", f"/api/project/{n}/feedback", {"scene": "s01", "text": "cảnh này chậm"})
        self.assertEqual(c, 200)
        self.assertEqual(self.call("POST", f"/api/project/{n}/feedback", {"scene": "_all", "text": "giọng văn thân mật hơn"})[0], 200)
        self.assertEqual(self.call("POST", f"/api/project/{n}/feedback", {"scene": "zz", "text": "x"})[0], 400)
        _, v = self.call("GET", f"/api/project/{n}")
        self.assertEqual(len(v["feedback"]), 2)
        self.call("POST", f"/api/project/{n}/feedback/{r['feedback']['id']}/done", {})
        _, v2 = self.call("GET", f"/api/project/{n}")
        self.assertEqual([f["status"] for f in v2["feedback"]], ["done", "open"])
        self.assertEqual(v2["scenes"][0]["voice"], "Một lời đọc khác hẳn, không còn cụm cũ nào cả.")

    def test_04_approvals_by_kind_are_bound_and_logged(self):
        n = self.new("Duyệt theo loại")
        self.call("POST", f"/api/project/{n}/scenes", {})
        _, v = self.call("GET", f"/api/project/{n}")
        c, _ = self.call("POST", f"/api/project/{n}/approve", {"by": "tester", "kind": "script", "expect_hash": "0" * 64})
        self.assertEqual(c, 409)
        self.assertEqual(self.call("POST", f"/api/project/{n}/approve", {"by": "", "kind": "script", "expect_hash": v["storyboard_hash"]})[0], 400)
        self.assertEqual(self.call("POST", f"/api/project/{n}/approve", {"by": "t", "kind": "zzz", "expect_hash": v["storyboard_hash"]})[0], 400)
        self.assertEqual(self.call("POST", f"/api/project/{n}/approve", {"by": "tester", "kind": "script", "expect_hash": v["storyboard_hash"]})[0], 200)
        _, a = self.call("GET", f"/api/project/{n}")
        self.assertEqual(sorted(a["approval"]["kinds"]), ["script"])
        self.assertEqual(a["changes_since_approval"], {"voice": [], "scene": ["s01"]}, "the script is approved, the storyboard is not")
        self.assertEqual(self.call("POST", f"/api/project/{n}/approve", {"by": "tester", "kind": "storyboard", "expect_hash": v["storyboard_hash"]})[0], 200)
        _, a = self.call("GET", f"/api/project/{n}")
        self.assertEqual(a["changes_since_approval"], {"voice": [], "scene": []})
        _, sc = self.call("GET", f"/api/project/{n}/scenes")
        s = sc["scenes"][0]
        s["bi"]["face"] = "happy"
        self.call("PUT", f"/api/project/{n}/scene/s01", {"scene": s})
        _, a = self.call("GET", f"/api/project/{n}")
        self.assertEqual(a["changes_since_approval"]["scene"], ["s01"])
        self.assertEqual(a["changes_since_approval"]["voice"], [])
        h = self.call("GET", f"/api/project/{n}/history")[1]["history"]
        self.assertEqual([x["kind"] for x in h], ["script", "storyboard"])
        self.assertTrue(all(x["by"] == "tester" for x in h))

    def test_05_runs_are_real_and_voice_waits_for_approval(self):
        n = self.new("Chạy thật")
        self.call("POST", f"/api/project/{n}/scenes", {})
        c, r = self.call("POST", f"/api/project/{n}/run", {"kind": "storyboard"})
        self.assertEqual(c, 200, r)
        self.assertEqual(self.call("POST", f"/api/project/{n}/run", {"kind": "storyboard"})[0], 409, "one run at a time")
        v = self.wait_idle(n)
        self.assertEqual(v["status"]["steps"]["storyboard"]["state"], "ok", v["log"])
        self.assertTrue(v["scenes"][0]["preview"])
        self.call("POST", f"/api/project/{n}/run", {"kind": "all"})
        v = self.wait_idle(n)
        self.assertEqual(v["status"]["steps"]["voice"]["state"], "waiting", "no approval -> no voice, no paid call")
        self.assertEqual(self.call("POST", f"/api/project/{n}/run", {"kind": "nope"})[0], 400)

    def test_06_files_are_served_safely_with_range(self):
        n = self.new("Tệp")
        c, _ = self.call("GET", f"/files/{n}/../../tools/build_video.py", token=False, raw=True)
        self.assertIn(c, (403, 404))
        c, _ = self.call("GET", f"/files/{n}/storyboard.json", token=False, raw=True)
        self.assertEqual(c, 200)
        (P2 / "projects" / n / ".env").write_text("SECRET=1", encoding="utf-8")
        self.assertEqual(self.call("GET", f"/files/{n}/.env", token=False, raw=True)[0], 404)

    def test_07_ai_preparation_through_the_ui_subprocess_path_persists_and_is_bounded(self):
        n = self.new("Chuẩn bị bằng AI", goal="hiểu cơ bản", message="bắt đầu nhỏ", budget={"llm_calls": 40})
        prep = self.prepare(n)
        steps = prep["overview"]["steps"]
        self.assertEqual([steps[k]["state"] for k in ("research", "script", "storyboard", "assetplan")], ["ok"] * 4, steps)
        self.assertTrue(6 <= len(prep["script"]["scenes"]) <= 10)
        self.assertEqual(self.call("GET", f"/api/project/{n}")[1]["has_storyboard"], True)
        _, prod = self.call("GET", f"/api/project/{n}/production")
        kinds = {t["kind"] for t in prod["todo"]}
        self.assertTrue({"script", "storyboard", "plan"} <= kinds, kinds)
        self.assertEqual(prod["problems"], [])
        self.assertGreater(prod["costs"]["usage"]["llm_calls"], 2)
        calls_before = prod["costs"]["usage"]["llm_calls"]
        prep2 = self.prepare(n)
        self.assertEqual({k: v["state"] for k, v in prep2["overview"]["steps"].items() if k in ("research", "script", "storyboard", "assetplan")}, {k: "ok" for k in ("research", "script", "storyboard", "assetplan")})
        self.assertEqual(self.call("GET", f"/api/project/{n}/production")[1]["costs"]["usage"]["llm_calls"], calls_before, "unchanged rerun: zero new AI calls")
        plan = prep["plan"]
        self.assertTrue(plan["assets"])
        self.assertEqual(self.call("POST", f"/api/project/{n}/prepare/plan/approve", {"by": ""})[0], 400)
        self.call("POST", f"/api/project/{n}/run", {"kind": "prepare", "step": "assets"})
        self.wait_idle(n)
        _, prod = self.call("GET", f"/api/project/{n}/production")
        self.assertEqual(prod["costs"]["usage"]["images"], 0, "no image before the plan is approved")
        self.assertEqual(self.call("POST", f"/api/project/{n}/prepare/plan/approve", {"by": "tester", "expect_hash": "bad"})[0], 409)
        self.assertEqual(self.call("POST", f"/api/project/{n}/prepare/plan/approve", {"by": "tester", "expect_hash": prep["overview"]["plan_hash"]})[0], 200)
        prep = self.prepare(n, "assets")
        self.assertEqual(prep["overview"]["steps"]["assets"]["state"], "ok", prep["overview"]["steps"]["assets"])
        v = self.call("GET", f"/api/project/{n}")[1]
        self.assertEqual([a["status"] for a in v["ai_assets"]], ["draft"])
        aid = v["ai_assets"][0]["id"]
        self.assertEqual(self.call("POST", f"/api/project/{n}/asset/{aid}/approve", {"by": ""})[0], 400)
        c, r = self.call("GET", f"/api/project/{n}/asset/{aid}/composite")
        self.assertEqual(c, 200, r)
        self.assertEqual(self.call("GET", r["url"], token=False, raw=True)[0], 200)
        self.assertEqual(self.call("POST", f"/api/project/{n}/asset/{aid}/approve", {"by": "tester"})[0], 200)
        self.assertTrue(any(j["state"] == "succeeded" for j in self.call("GET", f"/api/project/{n}/production")[1]["jobs"]))
        png = P2 / "projects" / n / "ai_assets" / f"{aid}.png"
        from PIL import Image
        Image.new("RGBA", (20, 20), (0, 0, 255, 255)).save(png)
        self.assertEqual(self.call("GET", f"/api/project/{n}")[1]["ai_assets"][0]["status"], "changed_after_approval")
        _, prod = self.call("GET", f"/api/project/{n}/production")
        self.assertEqual(prod["costs"]["usage"]["images"], 1)
        self.assertTrue(any(j["state"] == "invalid" for j in prod["jobs"]), "a job whose image was replaced is reported, not trusted")
        self.assertTrue(any("Asset" in p["where"] for p in prod["problems"]))

    def test_08_budget_refusal_is_explained_and_resume_continues(self):
        n = self.new("Hạn mức thấp", budget={"llm_calls": 1})
        prep = self.prepare(n)
        st = prep["overview"]["steps"]
        self.assertEqual(st["script"]["state"], "ok")
        self.assertEqual(st["storyboard"]["state"], "failed")
        self.assertIn("Vượt hạn mức", st["storyboard"]["error"])
        _, prod = self.call("GET", f"/api/project/{n}/production")
        self.assertTrue(any("Vượt hạn mức" in p["message"] for p in prod["problems"]))
        c, _ = self.call("PUT", f"/api/project/{n}/brief", {"budget": {"llm_calls": 20}})
        self.assertEqual(c, 200)
        before = Path(os.environ["FAKE_AGY_COUNT"]).read_text(encoding="utf-8").count("llm script")
        prep = self.prepare(n)
        self.assertEqual([prep["overview"]["steps"][k]["state"] for k in ("script", "storyboard")], ["ok", "ok"])
        after = Path(os.environ["FAKE_AGY_COUNT"]).read_text(encoding="utf-8").count("llm script")
        self.assertEqual(after, before, "the finished script was not asked for again")

    def test_09_ai_revision_is_a_proposal_then_applied(self):
        n = self.new("Sửa bằng AI")
        self.prepare(n, "all")
        v = self.call("GET", f"/api/project/{n}")[1]
        sid = v["scenes"][1]["id"]
        c, p = self.call("POST", f"/api/project/{n}/ai/revise", {"type": "scene", "target": sid, "instruction": "mặt vui hơn"})
        self.assertEqual(c, 200, p)
        self.assertEqual(self.call("GET", f"/api/project/{n}")[1]["version"], v["version"], "proposal changes nothing")
        c, r = self.call("POST", f"/api/project/{n}/ai/proposal/{p['id']}/apply", {})
        self.assertEqual(c, 200, r)
        v2 = self.call("GET", f"/api/project/{n}")[1]
        self.assertEqual(v2["version"], v["version"] + 1)
        self.assertEqual(self.call("POST", f"/api/project/{n}/ai/proposal/{p['id']}/apply", {})[0], 400, "applied once")
        self.assertEqual(self.call("POST", f"/api/project/{n}/ai/revise", {"type": "scene", "target": sid, "instruction": ""})[0], 400)

    def test_10_export_has_everything_and_no_secrets(self):
        n = self.new("Bàn giao")
        self.prepare(n, "all")
        c, r = self.call("POST", f"/api/project/{n}/export", {})
        self.assertEqual(c, 200, r)
        code, data = self.call("GET", r["url"], token=False, raw=True)
        self.assertEqual(code, 200)
        z = zipfile.ZipFile(P2 / "projects" / n / "export" / r["file"])
        names = z.namelist()
        for must in ("storyboard.json", "prepare/script.json", "logs/ai_ledger.jsonl", "COST_SUMMARY.json", "HANDOVER.txt", "brief.json"):
            self.assertIn(f"{n}/{must}", names)
        self.assertFalse([x for x in names if x.endswith(".env")])

    def test_11_a_restarted_server_shows_the_same_saved_state(self):
        n = self.new("Khởi động lại")
        self.prepare(n, "all")
        before = {"v": self.call("GET", f"/api/project/{n}")[1], "p": self.call("GET", f"/api/project/{n}/prepare")[1], "prod": self.call("GET", f"/api/project/{n}/production")[1]}
        srv2 = S.make_server(0)                                       # a second, fresh server process-equivalent reading only the project folders
        threading.Thread(target=srv2.serve_forever, daemon=True).start()
        try:
            def get(path):
                req = urllib.request.Request(f"http://127.0.0.1:{srv2.server_address[1]}{path}", headers={"X-AF-Token": S.TOKEN})
                return json.loads(urllib.request.urlopen(req, timeout=30).read())
            self.assertEqual(get(f"/api/project/{n}")["storyboard_hash"], before["v"]["storyboard_hash"])
            self.assertEqual(get(f"/api/project/{n}/prepare")["overview"]["steps"], before["p"]["overview"]["steps"])
            self.assertEqual(get(f"/api/project/{n}/production")["costs"]["usage"], before["prod"]["costs"]["usage"])
        finally:
            srv2.shutdown()


if __name__ == "__main__":
    unittest.main()
