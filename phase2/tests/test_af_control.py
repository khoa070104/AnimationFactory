"""The control layer for AI CLIs: clean JSON on stdout, structured errors that name scene/shot/field, compare-and-swap on the storyboard, no approve command,
the same core behind the CLI and the MCP adapter, preview artifacts, and an AI loop (error -> fix by data -> success) without touching code."""
import copy
import json
import os
import subprocess
import sys
import time
import unittest
from pathlib import Path

P2 = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(P2 / "tools"))
sys.path.insert(0, str(P2 / "tests"))
import af_core as AF  # noqa: E402
import test_characters as TC  # noqa: E402

ENV = dict(os.environ, PYTHONIOENCODING="utf-8")


def af(*args):
    r = subprocess.run([sys.executable, str(P2 / "tools" / "af.py"), *args], capture_output=True, text=True, encoding="utf-8", env=ENV)
    return r.returncode, json.loads(r.stdout), r.stderr          # stdout must be exactly one JSON document


class T(unittest.TestCase):
    setUp, tearDown, project, with_mai, scene = TC.T.setUp, TC.T.tearDown, TC.T.project, TC.T.with_mai, TC.T.scene

    def story(self, d):
        sb = json.loads((d / "storyboard.json").read_text(encoding="utf-8"))
        s1 = self.scene("s01", "Mai nhìn gói hàng rồi chỉ vào cái nhãn và mỉm cười thật tươi.", "mai")
        s1["actions"] = [{"name": "enter", "at": 0.0}, {"name": "point", "cue": "chỉ vào cái nhãn", "hold": 1.0}]
        s1["items"] = [{"type": "text", "text": "Nhãn", "x": 1300, "y": 400, "size": 46}]
        s1["shots"] = [{"id": "sh1", "start": 0, "kind": "wide"}, {"id": "sh2", "start": "mỉm cười", "kind": "reaction", "size": "close", "focus": "main"}]
        sb["scenes"] = [s1]
        sb["targets"] = {"duration": [3, 40], "scenes": [1, 4]}
        (d / "storyboard.json").write_text(json.dumps(sb, ensure_ascii=False, indent=2), encoding="utf-8")

    def test_cli_stdout_is_one_json_document_with_contract_and_no_approve_command(self):
        code, out, err = af("capabilities")
        self.assertEqual((code, out["status"], out["contract"]), (0, "ok", "af/1"))
        self.assertNotIn("approve", " ".join(out["commands"]).lower())
        self.assertEqual(set(out["commands"]), {t["name"] for t in AF.TOOLS})
        self.assertIn("shots", out["capabilities"])
        code, out, _ = af("project_get", "--project", "no_such_project")
        self.assertEqual((code, out["status"], out["errors"][0]["code"], out["charged_calls"]), (1, "error", "UNKNOWN_PROJECT", 0))

    def test_ai_loop_error_names_the_field_then_a_data_fix_succeeds_without_code_changes(self):
        d = self.project()
        self.with_mai(d)
        self.story(d)
        cur = AF.call("project_get", {"project": d.name})
        self.assertEqual(cur["status"], "ok")
        sb = cur["storyboard"]
        bad = copy.deepcopy(sb)
        bad["scenes"][0]["shots"][1]["start"] = "cụm không có trong lời"
        bad["scenes"][0]["shots"][1]["focus"] = "cast4"
        bad["scenes"][0]["items"].append({"type": "prop", "img": "ai:khong_ton_tai", "x": 1100, "y": 600, "scale": 1})
        r = AF.call("project_put", {"project": d.name, "storyboard": bad, "expect_hash": cur["hash"]})
        self.assertEqual(r["status"], "needs_changes")
        where = {(e["code"], e["scene_id"], e["shot_id"]) for e in r["errors"]}
        self.assertIn(("CUE_NOT_IN_VOICE", "s01", "sh2"), where)
        self.assertIn(("UNKNOWN_FOCUS", "s01", "sh2"), where)
        self.assertTrue(any(e["code"] == "MISSING_ASSET" and e["scene_id"] == "s01" for e in r["errors"]), r["errors"])
        self.assertTrue(all(e["next_action"] for e in r["errors"]))
        self.assertEqual(AF.call("project_get", {"project": d.name})["hash"], cur["hash"], "a refused put changes nothing")
        r = AF.call("project_put", {"project": d.name, "storyboard": sb, "expect_hash": "0" * 64})
        self.assertEqual((r["status"], r["errors"][0]["code"]), ("needs_changes", "STALE_HASH"))
        sb["scenes"][0]["shots"][1]["size"] = "detail"
        r = AF.call("project_put", {"project": d.name, "storyboard": sb, "expect_hash": cur["hash"]})
        self.assertEqual(r["status"], "ok", r)
        self.assertNotEqual(r["hash"], cur["hash"])

    def test_preview_returns_stills_per_shot_a_contact_sheet_and_a_clip_without_paid_calls(self):
        d = self.project()
        self.with_mai(d)
        self.story(d)
        r = AF.call("preview", {"project": d.name})
        self.assertEqual(r["status"], "ok", r)
        kinds = [a["kind"] for a in r["artifacts"]]
        self.assertIn("contact_sheet", kinds)
        self.assertIn("clip", kinds)
        self.assertEqual(sum(1 for a in r["artifacts"] if a["kind"] == "still"), 2, "one still per shot")
        self.assertTrue(all(Path(a["path"]).exists() for a in r["artifacts"]))
        self.assertEqual(r["usage_delta"], {"llm_calls": 0, "images": 0, "voice_credits": 0})
        self.assertEqual(r["paid_calls_this_run"], 0)
        again = AF.call("preview", {"project": d.name})
        self.assertEqual(again["rebuilt_scenes"], [], "unchanged: nothing rebuilt")

    def test_render_without_the_owners_approval_waits_and_a_background_job_can_be_polled(self):
        d = self.project()
        self.with_mai(d)
        self.story(d)
        r = AF.call("render", {"project": d.name, "background": True})
        self.assertEqual(r["status"], "running")
        jid = r["job"]["id"]
        again = AF.call("render", {"project": d.name, "background": True})
        self.assertEqual(again["job"]["id"], jid, "the same request already running returns the same job")
        for _ in range(120):
            j = AF.call("jobs", {"project": d.name, "job_id": jid})
            if j["job"]["state"] != "running":
                break
            time.sleep(2)
        self.assertEqual(j["job"]["state"], "waiting_approval", j)
        self.assertEqual(AF.call("jobs", {"project": d.name})["jobs"][0]["id"], jid)

    def test_changing_the_camera_target_and_a_longer_label_are_data_edits(self):
        d = self.project()
        self.with_mai(d)
        self.story(d)
        AF.call("preview", {"project": d.name})
        clip = lambda: json.loads((d / "remotion/public/data/clip.json").read_text(encoding="utf-8"))
        before = clip()["scenes"][0]["camera"]
        cur = AF.call("project_get", {"project": d.name})
        sb = cur["storyboard"]
        sb["scenes"][0]["shots"][1].update({"size": "close", "focus": [1200, 300, 300, 200]})                  # another target: a region on the right
        r = AF.call("project_put", {"project": d.name, "storyboard": sb, "expect_hash": cur["hash"]})
        self.assertEqual(r["status"], "ok", r)
        pv = AF.call("preview", {"project": d.name})
        self.assertEqual(pv["status"], "ok", pv)
        self.assertEqual(pv["rebuilt_scenes"], ["s01"], "only the scene whose data changed is rebuilt")
        self.assertNotEqual(clip()["scenes"][0]["camera"], before)
        sb["scenes"][0]["items"][0]["text"] = "Một cái nhãn rất dài ghi tên người nhận và cả địa chỉ nhà hàng xóm bên cạnh"
        r = AF.call("project_put", {"project": d.name, "storyboard": sb, "expect_hash": r["hash"], "autolayout": True})
        self.assertEqual(r["status"], "ok")
        self.assertTrue(any("content panel" in w and "s01" in w for w in r["warnings"]), r["warnings"])
        sb["scenes"][0]["items"][0]["text"] = "Nhãn: Văn Minh"
        r = AF.call("project_put", {"project": d.name, "storyboard": sb, "expect_hash": r["hash"], "autolayout": True})
        self.assertFalse([w for w in r["warnings"] if "content panel" in w], r["warnings"])
        self.assertEqual(AF.call("preview", {"project": d.name})["status"], "ok")

    def test_zoomed_shots_hide_content_that_pokes_into_the_view_but_is_not_the_focus(self):
        """Found by the independent acceptance run: a label card's corner showed in reaction close-ups. Content that is not the focus fades out for that shot."""
        d = self.project()
        self.with_mai(d)
        self.story(d)
        sb = AF.call("project_get", {"project": d.name})
        cur = sb["storyboard"]
        cur["scenes"][0]["items"].append({"type": "text", "text": "Ghi chú gần nhân vật", "x": 640, "y": 400, "size": 46})     # right next to Mai: inside her close-up
        r = AF.call("project_put", {"project": d.name, "storyboard": cur, "expect_hash": sb["hash"]})
        self.assertEqual(r["status"], "ok", r)
        self.assertEqual(AF.call("preview", {"project": d.name})["status"], "ok")
        clip = json.loads((d / "remotion/public/data/clip.json").read_text(encoding="utf-8"))
        prims = [p for p in clip["scenes"][0]["prims"] if p.get("text") == "Ghi chú gần nhân vật"]
        close = [s for s in clip["scenes"][0]["shots"] if s["id"] == "sh2"][0]
        self.assertTrue(prims and prims[0].get("hide") == [[close["t0"], close["t1"]]], prims)
        far = [p for p in clip["scenes"][0]["prims"] if p.get("text") == "Nhãn"]
        self.assertTrue(far and not far[0].get("hide"), "an item outside the view is left alone")

    def test_mcp_adapter_serves_the_same_core(self):
        p = subprocess.Popen([sys.executable, str(P2 / "assets_mcp" / "af_assets_server.py")], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8", env=ENV)
        msgs = [{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-06-18"}}, {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
                {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "capabilities", "arguments": {}}}]
        out, _ = p.communicate("\n".join(json.dumps(m) for m in msgs) + "\n", timeout=60)
        res = {json.loads(line)["id"]: json.loads(line) for line in out.splitlines() if line.strip()}
        names = {t["name"] for t in res[2]["result"]["tools"]}
        self.assertTrue({"submit_asset_job", "check_asset_job"} | {t["name"] for t in AF.TOOLS} <= names)
        self.assertEqual(json.loads(res[3]["result"]["content"][0]["text"])["contract"], "af/1")


if __name__ == "__main__":
    unittest.main()
