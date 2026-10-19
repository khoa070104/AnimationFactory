"""Review by Telegram: send the built video to the owner's phone, take Duyệt / Yêu cầu sửa / Loại and written feedback back.

Configuration (never the token itself in a file): config.json
  "telegram": {"bot_token_env": "TELEGRAM_BOT_TOKEN", "allowed_user_ids": [123456789], "allowed_chat_ids": [123456789],
               "base_url": "https://api.telegram.org", "max_video_mb": 49}
(AF_TELEGRAM_CONFIG = path of a JSON file merged last, for tests). Nothing is sent and nothing is accepted until a token and an allow-list exist.

Rules
  * only a user id AND a chat id from the allow-list may decide; every other callback/message is refused and logged;
  * a button carries the entry id; the entry remembers the storyboard hash of the video it was sent for - after any change the old buttons are EXPIRED
    ("bản này đã cũ"), so an old approval can never approve a new version;
  * a callback is processed once (its id is stored): a repeated tap cannot approve twice or start a second AI proposal;
  * the outbox is saved BEFORE sending: a crash or a lost reply leaves the entry `unknown` (never silently re-sent; the owner chooses "gửi lại");
  * "Duyệt" is recorded as a delivery approval of THIS video (approvals_history.jsonl kind `video`, actor = the Telegram account, verified) - it does not approve
    scripts/storyboards/assets and never starts a paid step;
  * written feedback is saved to feedback.json; if it starts with a scene id ("s03: ...") an AI revision PROPOSAL is made and shown (before/after) with
    [Áp dụng] [Bỏ] buttons; applying creates a new storyboard version and marks the project "needs rebuild" - rebuilding (and any voice) is decided in the UI.
  python telegram_bot.py send PROJECT        python telegram_bot.py listen"""
import hashlib
import json
import mimetypes
import os
import sys
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import actors  # noqa: E402
import agy_image as G  # noqa: E402

P2 = Path(__file__).resolve().parent.parent
def _state():
    return Path(os.environ.get("AF_TELEGRAM_STATE") or (P2 / "telegram_state"))


class TelegramError(RuntimeError):
    pass


def config():
    cfg = {"bot_token_env": "TELEGRAM_BOT_TOKEN", "allowed_user_ids": [], "allowed_chat_ids": [], "base_url": "https://api.telegram.org", "max_video_mb": 49}
    f = P2 / "config.json"
    if f.exists():
        cfg.update(json.loads(f.read_text(encoding="utf-8")).get("telegram") or {})
    extra = os.environ.get("AF_TELEGRAM_CONFIG")
    if extra and Path(extra).exists():
        d = json.loads(Path(extra).read_text(encoding="utf-8"))
        cfg.update(d.get("telegram", d))
    return cfg


def configured(cfg=None):
    cfg = cfg or config()
    return bool(os.environ.get(cfg["bot_token_env"])) and bool(cfg["allowed_user_ids"]) and bool(cfg["allowed_chat_ids"])


def status():
    cfg = config()
    miss = []
    if not os.environ.get(cfg["bot_token_env"]):
        miss.append(f"biến môi trường {cfg['bot_token_env']} (token bot)")
    if not cfg["allowed_user_ids"] or not cfg["allowed_chat_ids"]:
        miss.append("allowed_user_ids / allowed_chat_ids trong config.json")
    return {"configured": not miss, "missing": miss, "base_url": cfg["base_url"]}


# ------------------------------------------------------------------------------------------------------------------ Bot API
def call(method, params=None, files=None, timeout=40):
    cfg = config()
    token = os.environ.get(cfg["bot_token_env"])
    if not token:
        raise TelegramError(f"no bot token: set the environment variable {cfg['bot_token_env']}")
    url = f"{cfg['base_url'].rstrip('/')}/bot{token}/{method}"
    params = params or {}
    if files:
        boundary = uuid.uuid4().hex
        parts = []
        for k, v in params.items():
            parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v if isinstance(v, str) else json.dumps(v)}\r\n'.encode())
        for k, path in files.items():
            data = Path(path).read_bytes()
            ctype = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
            parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"; filename="{Path(path).name}"\r\nContent-Type: {ctype}\r\n\r\n'.encode() + data + b"\r\n")
        parts.append(f"--{boundary}--\r\n".encode())
        body, ctype = b"".join(parts), f"multipart/form-data; boundary={boundary}"
    else:
        body, ctype = json.dumps(params).encode("utf-8"), "application/json"
    req = urllib.request.Request(url, data=body, method="POST", headers={"Content-Type": ctype})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            res = json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise TelegramError(f"HTTP {e.code}: {e.read().decode('utf-8', 'replace')[:200]}") from e
    except (urllib.error.URLError, OSError, ValueError) as e:
        raise TelegramNetwork(str(e)) from e
    if not res.get("ok"):
        raise TelegramError(f"Telegram refused {method}: {res.get('description')}")
    return res["result"]


class TelegramNetwork(TelegramError):
    """The request may or may not have reached Telegram (timeout, dropped connection)."""


# ------------------------------------------------------------------------------------------------------------------ state
def _jf(name):
    _state().mkdir(parents=True, exist_ok=True)
    return _state() / name


def _load(name, default):
    return G.read_json(_jf(name), default)


def _save(name, obj):
    G.write_json_atomic(_jf(name), obj)


def outbox_file(proj):
    return Path(proj) / "telegram" / "outbox.json"


def outbox(proj):
    return G.read_json(outbox_file(proj), []) or []


def _save_outbox(proj, rows):
    outbox_file(proj).parent.mkdir(exist_ok=True)
    G.write_json_atomic(outbox_file(proj), rows)


def storyboard_hash12(proj):
    return hashlib.sha256((Path(proj) / "storyboard.json").read_bytes()).hexdigest()[:12]


def latest_video(proj):
    outs = sorted((Path(proj) / "output").glob("*.mp4"), key=lambda f: f.stat().st_mtime) if (Path(proj) / "output").exists() else []
    return outs[-1] if outs else None


# ------------------------------------------------------------------------------------------------------------------ sending
def caption(proj):
    import budget
    import sbload
    sb = sbload.load_storyboard(proj)
    st = G.read_json(Path(proj) / "status.json", {}) or {}
    lb = st.get("last_build") or {}
    u = budget.usage(proj)
    flags = []
    if lb.get("draft"):
        flags.append("BẢN NHÁP (giọng im lặng)")
    return (f"{sb.get('title')}\nDự án {Path(proj).name} · storyboard v{sb.get('version')} · {lb.get('seconds', '?')} s · {len(sb['scenes'])} cảnh\n"
            f"Chi phí đã dùng: {u['llm_calls']} lượt AI, {u['images']} lượt ảnh, {u['voice_credits']:g} credit giọng" + ("\n" + " · ".join(flags) if flags else ""))[:1000]


def keyboard(entry_id):
    return {"inline_keyboard": [[{"text": "✅ Duyệt", "callback_data": f"af1|{entry_id}|ok"}, {"text": "✏️ Yêu cầu sửa", "callback_data": f"af1|{entry_id}|fix"},
                                 {"text": "❌ Loại", "callback_data": f"af1|{entry_id}|no"}]]}


def send_review(proj, chat_id=None, force=False, video=None):
    """-> outbox entry. Idempotent per (video file hash, chat): an already sent video is not sent again; an unknown outcome is not retried unless force."""
    proj = Path(proj)
    cfg = config()
    if not configured(cfg):
        raise TelegramError("Telegram is not configured: " + "; ".join(status()["missing"]))
    chat = int(chat_id or cfg["allowed_chat_ids"][0])
    if chat not in [int(x) for x in cfg["allowed_chat_ids"]]:
        raise TelegramError("that chat is not on the allow-list")
    video = Path(video) if video else latest_video(proj)
    if not video or not video.exists():
        raise TelegramError("there is no built video to send")
    vsha = hashlib.sha256(video.read_bytes()).hexdigest()
    rows = outbox(proj)
    for r in rows:
        if r["video_sha"] == vsha and r["chat_id"] == chat and r["kind"] == "video":
            if r["status"] == "sending":                              # the process died while sending: we do not know
                r["status"], r["error"] = "unknown", "the sending process stopped before the answer was recorded"
                _save_outbox(proj, rows)
            if r["status"] in ("sent", "approved", "rejected", "unknown", "blocked_size") and not force:
                return r
    entry = {"id": uuid.uuid4().hex[:8], "kind": "video", "project": proj.name, "hash12": storyboard_hash12(proj), "video": video.name, "video_sha": vsha, "chat_id": chat,
             "status": "sending", "attempts": 1, "created": time.strftime("%Y-%m-%d %H:%M:%S"), "message_id": None, "error": None}
    if video.stat().st_size > int(cfg["max_video_mb"]) * 1024 * 1024:
        entry.update(status="blocked_size", error=f"the video is {video.stat().st_size // 1048576} MB, Telegram bots accept up to {cfg['max_video_mb']} MB; there is no public link to fall back on (the tool is local)")
        _save_outbox(proj, rows + [entry])
        return entry
    _save_outbox(proj, rows + [entry])                                # recorded BEFORE the request
    idx = _load("index.json", {})
    idx[entry["id"]] = {"project": proj.name, "hash12": entry["hash12"]}
    _save("index.json", idx)
    try:
        res = call("sendVideo", {"chat_id": str(chat), "caption": caption(proj), "reply_markup": json.dumps(keyboard(entry["id"])), "supports_streaming": "true"}, files={"video": video}, timeout=120)
        entry.update(status="sent", message_id=res.get("message_id"), sent_at=time.strftime("%Y-%m-%d %H:%M:%S"))
    except TelegramNetwork as e:
        entry.update(status="unknown", error=f"no answer from Telegram ({e}); the video may or may not have arrived")
    except TelegramError as e:
        entry.update(status="failed", error=str(e))
    rows = outbox(proj)
    rows = [entry if r["id"] == entry["id"] else r for r in rows]
    _save_outbox(proj, rows)
    return entry


# ------------------------------------------------------------------------------------------------------------------ receiving
def _allowed(user_id, chat_id):
    cfg = config()
    return int(user_id) in [int(x) for x in cfg["allowed_user_ids"]] and int(chat_id) in [int(x) for x in cfg["allowed_chat_ids"]]


def _find_entry(entry_id):
    ref = _load("index.json", {}).get(entry_id)
    if not ref:
        return None, None
    proj = P2 / "projects" / ref["project"]
    for r in outbox(proj):
        if r["id"] == entry_id:
            return proj, r
    return proj, None


def _update_entry(proj, entry_id, **kw):
    rows = outbox(proj)
    for r in rows:
        if r["id"] == entry_id:
            r.update(kw)
    _save_outbox(proj, rows)


def _history(proj, row):
    with (Path(proj) / "approvals_history.jsonl").open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({"at": time.strftime("%Y-%m-%d %H:%M:%S"), **row}, ensure_ascii=False) + "\n")


def _who(u):
    return f"telegram:{('@' + u['username']) if u.get('username') else u['id']}"


def _answer(cb_id, text, alert=False):
    try:
        call("answerCallbackQuery", {"callback_query_id": cb_id, "text": text[:190], "show_alert": alert})
    except TelegramError:
        pass


def _say(chat_id, text, markup=None):
    p = {"chat_id": str(chat_id), "text": text[:3900]}
    if markup:
        p["reply_markup"] = json.dumps(markup)
    try:
        return call("sendMessage", p)
    except TelegramError:
        return None


def process_update(update):
    """Handle one Telegram update. -> short string describing what was done (for logs/tests)."""
    if "callback_query" in update:
        return _on_callback(update["callback_query"])
    msg = update.get("message") or {}
    if msg.get("text"):
        return _on_text(msg)
    return "ignored"


def _on_callback(cb):
    u, chat = cb["from"], (cb.get("message") or {}).get("chat", {}).get("id")
    if chat is None or not _allowed(u["id"], chat):
        _answer(cb["id"], "Bạn không có quyền duyệt dự án này.", True)
        _log("refused", {"user": u.get("id"), "chat": chat, "data": cb.get("data")})
        return "refused: not on the allow-list"
    handled = _load("handled.json", {})
    if cb["id"] in handled:
        _answer(cb["id"], "Thao tác này đã được xử lý rồi.")
        return "duplicate callback ignored"
    handled[cb["id"]] = time.strftime("%Y-%m-%d %H:%M:%S")
    _save("handled.json", dict(list(handled.items())[-2000:]))
    parts = str(cb.get("data", "")).split("|")
    if len(parts) < 3 or parts[0] != "af1":
        _answer(cb["id"], "Nút không hợp lệ.", True)
        return "bad callback data"
    entry_id, act = parts[1], parts[2]
    proj, entry = _find_entry(entry_id)
    if not entry:
        _answer(cb["id"], "Không tìm thấy bản gửi này.", True)
        return "unknown entry"
    if act in ("pa", "pr"):
        return _on_proposal(cb, proj, entry, act, parts[3] if len(parts) > 3 else "")
    if entry["hash12"] != storyboard_hash12(proj):                    # the content changed after this video was sent
        _answer(cb["id"], "Bản này đã cũ: storyboard đã thay đổi sau khi gửi. Hãy xem bản mới.", True)
        _update_entry(proj, entry_id, status="expired")
        return "expired: storyboard changed since the video was sent"
    actor = actors.classify(_who(u), "telegram", verified=True)
    if act == "ok":
        _history(proj, {"kind": "video", "by": actor["label"], "actor": actor, "entry": entry_id, "video": entry["video"], "video_sha256": entry["video_sha"], "storyboard_hash12": entry["hash12"]})
        _update_entry(proj, entry_id, status="approved", decided_by=actor["label"], decided_at=time.strftime("%Y-%m-%d %H:%M:%S"))
        _answer(cb["id"], "Đã ghi nhận: bạn duyệt video này.")
        _say(chat, "✅ Đã duyệt video (bản storyboard " + entry["hash12"] + ").")
        return "video approved"
    if act == "no":
        _history(proj, {"kind": "video_rejected", "by": actor["label"], "actor": actor, "entry": entry_id, "video_sha256": entry["video_sha"]})
        _update_entry(proj, entry_id, status="rejected", decided_by=actor["label"], decided_at=time.strftime("%Y-%m-%d %H:%M:%S"))
        _answer(cb["id"], "Đã ghi nhận: loại video này.")
        return "video rejected"
    if act == "fix":
        pend = _load("pending.json", {})
        pend[str(chat)] = {"entry": entry_id, "user": u["id"], "at": time.time()}
        _save("pending.json", pend)
        _answer(cb["id"], "Gõ góp ý của bạn.")
        _say(chat, "✏️ Gõ góp ý. Bắt đầu bằng mã cảnh nếu chỉ sửa một cảnh, ví dụ: `s03: rút ngắn lời, mặt vui hơn`. Không có mã cảnh = góp ý chung.")
        return "waiting for feedback text"
    _answer(cb["id"], "Thao tác không biết.", True)
    return "unknown action"


def _on_text(msg):
    u, chat = msg["from"], msg["chat"]["id"]
    if not _allowed(u["id"], chat):
        _log("refused", {"user": u.get("id"), "chat": chat, "text": msg.get("text", "")[:60]})
        return "refused: not on the allow-list"
    pend = _load("pending.json", {})
    p = pend.get(str(chat))
    if not p or p["user"] != u["id"]:
        return "ignored: no feedback was requested"
    del pend[str(chat)]
    _save("pending.json", pend)
    proj, entry = _find_entry(p["entry"])
    if not entry:
        return "unknown entry"
    text = msg["text"].strip()
    import re
    m = re.match(r"^(s\d+\w*|all|chung)\s*:\s*(.+)$", text, re.I | re.S)
    scene, body = (m.group(1).lower(), m.group(2).strip()) if m else ("_all", text)
    scene = "_all" if scene in ("all", "chung") else scene
    if len(body.split()) < 2:
        _say(chat, "Góp ý quá ngắn. Hãy mô tả điều cần sửa (ít nhất vài từ) rồi bấm “Yêu cầu sửa” lại.")
        return "feedback too short: asked again, nothing spent"
    import sbstore
    sb = json.loads((proj / "storyboard.json").read_text(encoding="utf-8"))
    if scene != "_all" and not any(s["id"] == scene for s in sb["scenes"]):
        _say(chat, f"Không có cảnh {scene}. Cảnh hiện có: " + ", ".join(s["id"] for s in sb["scenes"]))
        return "unknown scene"
    fb = G.read_json(proj / "feedback.json", []) or []
    actor = actors.classify(_who(u), "telegram", verified=True)
    fb.append({"id": uuid.uuid4().hex[:8], "scene": scene, "text": body, "storyboard_version": sb.get("version"), "at": time.strftime("%Y-%m-%d %H:%M:%S"), "status": "open", "source": "telegram", "actor": actor})
    G.write_json_atomic(proj / "feedback.json", fb)
    _update_entry(proj, p["entry"], status="changes_requested", feedback_id=fb[-1]["id"])
    if scene == "_all":
        _say(chat, "📝 Đã ghi góp ý chung. Chủ dự án xem ở giao diện.")
        return "general feedback saved"
    import revise
    try:
        prop = revise.propose_scene(proj, scene, body)
    except Exception as e:  # noqa: BLE001 - budget / AI trouble must not lose the feedback
        _say(chat, f"📝 Đã ghi góp ý cho {scene}. AI chưa đề xuất được ({str(e)[:160]}); xem ở giao diện.")
        return f"feedback saved, proposal failed: {e}"
    lines = [f"🤖 Đề xuất sửa {scene}: {prop.get('summary', '')}"] + [f"• {d['path']}: {str(d['before'])[:60]} → {str(d['after'])[:60]}" for d in prop["diff"][:8]]
    if prop["errors"]:
        lines.append("⚠️ Không áp dụng được: " + "; ".join(prop["errors"][:2]))
    mk = None if prop["errors"] else {"inline_keyboard": [[{"text": "Áp dụng", "callback_data": f"af1|{p['entry']}|pa|{prop['id']}"}, {"text": "Bỏ", "callback_data": f"af1|{p['entry']}|pr|{prop['id']}"}]]}
    _say(chat, "\n".join(lines), mk)
    return f"feedback saved, proposal {prop['id']} shown"


def _on_proposal(cb, proj, entry, act, pid):
    import revise
    chat = cb["message"]["chat"]["id"]
    try:
        if act == "pr":
            revise.reject(proj, pid)
            _answer(cb["id"], "Đã bỏ đề xuất.")
            return "proposal rejected"
        res = revise.apply(proj, pid)
    except revise.ReviseError as e:
        _answer(cb["id"], str(e)[:180], True)
        return f"proposal not applied: {e}"
    _update_entry(proj, entry["id"], status="expired", needs_rebuild=True)
    _answer(cb["id"], "Đã áp dụng.")
    _say(chat, f"✅ Đã áp dụng (storyboard v{res['result']['version']}). Video cũ hết hiệu lực; dựng lại trong giao diện (lời đổi thì cần duyệt lại và tạo lại giọng cảnh đó).")
    return "proposal applied"


def _log(kind, row):
    _state().mkdir(parents=True, exist_ok=True)
    with (_state() / "events.jsonl").open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({"at": time.strftime("%Y-%m-%d %H:%M:%S"), "kind": kind, **row}, ensure_ascii=False) + "\n")


def listen(poll_timeout=25, once=False):
    """Long-poll getUpdates and process updates (offset kept on disk, so a restart never replays handled updates)."""
    off = _load("offset.json", {"offset": 0})["offset"]
    while True:
        try:
            ups = call("getUpdates", {"offset": off, "timeout": 0 if once else poll_timeout, "allowed_updates": ["message", "callback_query"]}, timeout=poll_timeout + 15)
        except TelegramNetwork:
            time.sleep(3)
            continue
        for u in ups:
            try:
                r = process_update(u)
                _log("update", {"id": u.get("update_id"), "result": r})
            except Exception as e:  # noqa: BLE001
                _log("error", {"id": u.get("update_id"), "error": str(e)})
            off = u["update_id"] + 1
            _save("offset.json", {"offset": off})
        if once:
            return


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    if len(sys.argv) >= 3 and sys.argv[1] == "send":
        print(json.dumps(send_review(P2 / "projects" / sys.argv[2]), ensure_ascii=False, indent=1))
    elif sys.argv[1:2] == ["listen"]:
        listen()
    else:
        print(json.dumps(status(), ensure_ascii=False, indent=1))
