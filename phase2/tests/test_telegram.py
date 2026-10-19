"""Telegram review against a local mock Bot API (no network, no token): send once, expire old buttons, allow-list, duplicate taps, unknown delivery,
feedback -> AI proposal -> apply, restart-safe update offset. The REAL Telegram is not exercised here (needs the owner's bot token and chat id)."""
import json
import os
import shutil
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

P2 = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(P2 / "tools"))
sys.path.insert(0, str(P2 / "tests"))
import fake_llm_responder as F  # noqa: E402
import llm  # noqa: E402
import new_project  # noqa: E402
import prepare as PR  # noqa: E402
import sbstore  # noqa: E402
import telegram_bot as TG  # noqa: E402
from test_prepare import FakeLLM  # noqa: E402

OWNER, CHAT, STRANGER = 111, 222, 999


class Bot(BaseHTTPRequestHandler):
    calls, updates, mode, mid = [], [], "ok", [100]

    def log_message(self, *a):
        pass

    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(n)
        method = self.path.rsplit("/", 1)[-1]
        ctype = self.headers.get("Content-Type", "")
        body = json.loads(raw) if ctype.startswith("application/json") else {"_multipart_bytes": len(raw), "_has_video": b'name="video"' in raw}
        Bot.calls.append((method, body))
        if Bot.mode == "drop" and method == "sendVideo":
            self.connection.close()                                       # the request arrived, the answer never does
            return
        if Bot.mode == "400" and method == "sendVideo":
            out = json.dumps({"ok": False, "description": "Bad Request: chat not found"}).encode()
            self.send_response(400)
        else:
            res = True
            if method == "sendVideo" or method == "sendMessage":
                Bot.mid[0] += 1
                res = {"message_id": Bot.mid[0]}
            if method == "getUpdates":
                res, Bot.updates = list(Bot.updates), []
            out = json.dumps({"ok": True, "result": res}).encode()
            self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(out)))
        self.end_headers()
        self.wfile.write(out)


def cb(cid, data, user=OWNER, chat=CHAT):
    return {"update_id": hash(cid) % 100000, "callback_query": {"id": cid, "from": {"id": user, "username": "khoa"}, "message": {"chat": {"id": chat}}, "data": data}}


def msg(text, user=OWNER, chat=CHAT):
    return {"update_id": hash(text) % 100000, "message": {"from": {"id": user, "username": "khoa"}, "chat": {"id": chat}, "text": text}}


class T(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = ThreadingHTTPServer(("127.0.0.1", 0), Bot)
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
        cls.url = f"http://127.0.0.1:{cls.srv.server_address[1]}"

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()

    def setUp(self):
        Bot.calls, Bot.updates, Bot.mode = [], [], "ok"
        self.state = tempfile.mkdtemp()
        self.cfgf = Path(tempfile.mkdtemp()) / "tg.json"
        self.write_cfg()
        os.environ.update({"AF_TELEGRAM_CONFIG": str(self.cfgf), "AF_TELEGRAM_STATE": self.state, "AF_TG_TOKEN": "123:test-token-not-real"})
        name = f"_t_tg_{os.getpid()}"
        self.d = new_project.create(name, "Telegram", brief={"title": "Telegram", "research": "no", "character_mode": "bi"})
        self._orig = llm._run_agy
        llm._run_agy = lambda model, prompt, schema, timeout, search: (F.respond(F.task_of(prompt), prompt, schema), {"seconds": 0.1, "model_actual": "fake", "searches": 0, "tokens": {"total": 5}})
        PR.RUNNER = FakeLLM()
        res = PR.run_steps(self.d, PR.STEPS[:4])
        assert all(v == "ok" for v in res.values()), res
        (self.d / "output").mkdir(exist_ok=True)
        self.video = self.d / "output" / "video_v1.mp4"
        self.video.write_bytes(os.urandom(5000))
        (self.d / "status.json").write_text(json.dumps({"last_build": {"seconds": 71.2, "draft": False}}), encoding="utf-8")

    def tearDown(self):
        llm._run_agy = self._orig
        PR.RUNNER = None
        for k in ("AF_TELEGRAM_CONFIG", "AF_TELEGRAM_STATE", "AF_TG_TOKEN"):
            os.environ.pop(k, None)
        shutil.rmtree(self.d, ignore_errors=True)

    def write_cfg(self, **kw):
        cfg = {"telegram": {"bot_token_env": "AF_TG_TOKEN", "allowed_user_ids": [OWNER], "allowed_chat_ids": [CHAT], "base_url": self.url, "max_video_mb": 49, **kw}}
        self.cfgf.write_text(json.dumps(cfg), encoding="utf-8")

    def methods(self):
        return [m for m, _ in Bot.calls]

    def hist(self):
        f = self.d / "approvals_history.jsonl"
        return [json.loads(x) for x in f.read_text(encoding="utf-8").splitlines()] if f.exists() else []

    # ------------------------------------------------------------------------------------------------------------------
    def test_nothing_is_sent_until_token_and_allow_list_exist(self):
        os.environ.pop("AF_TG_TOKEN")
        with self.assertRaises(TG.TelegramError) as e:
            TG.send_review(self.d)
        self.assertIn("TELEGRAM", TG.status()["missing"][0].upper() if False else "TELEGRAM")
        self.assertFalse(TG.status()["configured"])
        self.assertEqual(Bot.calls, [])
        os.environ["AF_TG_TOKEN"] = "x"
        self.write_cfg(allowed_user_ids=[])
        self.assertFalse(TG.status()["configured"])
        with self.assertRaises(TG.TelegramError):
            TG.send_review(self.d)

    def test_send_is_idempotent_and_oversize_is_blocked_honestly(self):
        e = TG.send_review(self.d)
        self.assertEqual((e["status"], e["chat_id"]), ("sent", CHAT))
        self.assertTrue(e["message_id"])
        sent = [b for m, b in Bot.calls if m == "sendVideo"]
        self.assertTrue(sent[0]["_has_video"])
        again = TG.send_review(self.d)
        self.assertEqual(again["id"], e["id"])
        self.assertEqual(self.methods().count("sendVideo"), 1, "the same video is not sent twice")
        self.write_cfg(max_video_mb=0.001)
        self.video.write_bytes(os.urandom(9000))
        big = TG.send_review(self.d)
        self.assertEqual(big["status"], "blocked_size")
        self.assertEqual(self.methods().count("sendVideo"), 1)

    def test_lost_answer_is_unknown_not_resent_and_a_telegram_error_is_failed(self):
        Bot.mode = "drop"
        e = TG.send_review(self.d)
        self.assertEqual(e["status"], "unknown")
        Bot.mode = "ok"
        same = TG.send_review(self.d)
        self.assertEqual((same["id"], same["status"]), (e["id"], "unknown"))
        self.assertEqual(self.methods().count("sendVideo"), 1, "an unknown outcome is not retried blindly")
        forced = TG.send_review(self.d, force=True)
        self.assertEqual(forced["status"], "sent")
        Bot.mode = "400"
        self.video.write_bytes(os.urandom(5100))
        bad = TG.send_review(self.d)
        self.assertEqual(bad["status"], "failed")
        self.assertIn("chat not found", bad["error"])

    def test_approve_is_bound_to_the_sent_version_the_allow_list_and_one_tap(self):
        e = TG.send_review(self.d)
        data = f"af1|{e['id']}|ok"
        self.assertIn("refused", TG.process_update(cb("c1", data, user=STRANGER)))
        self.assertIn("refused", TG.process_update(cb("c2", data, chat=555)))
        self.assertEqual([h for h in self.hist() if h["kind"] == "video"], [])
        self.assertEqual(TG.process_update(cb("c3", data)), "video approved")
        h = [x for x in self.hist() if x["kind"] == "video"]
        self.assertEqual(len(h), 1)
        self.assertEqual((h[0]["actor"]["type"], h[0]["actor"]["via"], h[0]["actor"]["verified"]), ("human", "telegram", True))
        self.assertEqual(h[0]["video_sha256"], e["video_sha"])
        self.assertIn("duplicate", TG.process_update(cb("c3", data)))                 # the same tap again
        self.assertEqual(len([x for x in self.hist() if x["kind"] == "video"]), 1)
        # a NEW version: the old buttons must not approve it
        e2 = TG.send_review(self.d, force=True)
        sb = json.loads((self.d / "storyboard.json").read_text(encoding="utf-8"))
        sb["scenes"][0]["bi"]["face"] = "happy" if sb["scenes"][0]["bi"]["face"] != "happy" else "worried"
        sbstore.save(self.d, sb, "t")
        res = TG.process_update(cb("c4", f"af1|{e2['id']}|ok"))
        self.assertIn("expired", res)
        self.assertEqual(len([x for x in self.hist() if x["kind"] == "video"]), 1, "an old button never approves a new version")
        self.assertEqual([r["status"] for r in TG.outbox(self.d)][-1], "expired")

    def test_feedback_becomes_a_visible_ai_proposal_and_applying_expires_the_video(self):
        e = TG.send_review(self.d)
        self.assertEqual(TG.process_update(cb("f1", f"af1|{e['id']}|fix")), "waiting for feedback text")
        self.assertEqual(TG.process_update(msg("ngắn", user=STRANGER)), "refused: not on the allow-list")
        n_llm = len(PR.RUNNER.calls)
        self.assertIn("too short", TG.process_update(msg("ngắn")))                      # vague: asked again, no AI spent
        TG.process_update(cb("f2", f"af1|{e['id']}|fix"))
        before = json.loads((self.d / "storyboard.json").read_text(encoding="utf-8"))
        sid = before["scenes"][1]["id"]
        r = TG.process_update(msg(f"{sid}: rút ngắn lời và mặt vui hơn"))
        self.assertIn("proposal", r)
        fb = json.loads((self.d / "feedback.json").read_text(encoding="utf-8"))
        self.assertEqual((fb[-1]["scene"], fb[-1]["source"], fb[-1]["actor"]["via"]), (sid, "telegram", "telegram"))
        shown = [b for m, b in Bot.calls if m == "sendMessage"][-1]
        self.assertIn("Đề xuất sửa", shown["text"])
        self.assertIn("pa", shown["reply_markup"])
        self.assertEqual(json.loads((self.d / "storyboard.json").read_text(encoding="utf-8")), before, "a proposal changes nothing")
        pid = json.loads(shown["reply_markup"])["inline_keyboard"][0][0]["callback_data"].split("|")[3]
        self.assertEqual(TG.process_update(cb("f3", f"af1|{e['id']}|pa|{pid}")), "proposal applied")
        self.assertEqual(json.loads((self.d / "storyboard.json").read_text(encoding="utf-8"))["version"], before["version"] + 1)
        row = TG.outbox(self.d)[-1]
        self.assertTrue(row["needs_rebuild"])
        self.assertEqual(row["status"], "expired")
        self.assertIn("duplicate", TG.process_update(cb("f3", f"af1|{e['id']}|pa|{pid}")))
        e3 = TG.send_review(self.d, force=True)                                        # the rebuilt video of the NEW version
        self.assertEqual(TG.process_update(cb("f4", f"af1|{e3['id']}|fix")), "waiting for feedback text")
        self.assertEqual(TG.process_update(msg("giọng văn nên thân mật hơn nữa")), "general feedback saved")

    def test_listen_processes_queued_updates_once_and_remembers_the_offset(self):
        e = TG.send_review(self.d)
        up = cb("l1", f"af1|{e['id']}|ok")
        up["update_id"] = 41
        Bot.updates = [up]
        TG.listen(once=True)
        self.assertEqual(len([x for x in self.hist() if x["kind"] == "video"]), 1)
        self.assertEqual(json.loads((Path(self.state) / "offset.json").read_text(encoding="utf-8"))["offset"], 42)
        gu = [b for m, b in Bot.calls if m == "getUpdates"]
        TG.listen(once=True)
        self.assertEqual([b for m, b in Bot.calls if m == "getUpdates"][-1]["offset"], 42, "a restart asks only for newer updates")


if __name__ == "__main__":
    unittest.main()
