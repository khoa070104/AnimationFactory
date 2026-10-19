"""Per-project AI ledger, usage and budget limits.

Every real AI call (LLM via agy, image via agy, paid voice job) appends a row to PROJECT/logs/ai_ledger.jsonl (cache hits are logged as
`cache: true` and cost nothing). `check(proj, kind, planned)` refuses to START work that would exceed a limit; the message is shown in the UI.
Limits: config.json ai.limits, overridden by brief.json "budget" {llm_calls, llm_tokens, images, voice_credits}. A limit of null/absent = none.
Cost in money is not known unless config ai.price_per_1k_tokens has the model; credits (voice) and tokens are real numbers from the providers."""
import json
import time
from pathlib import Path

import aiconfig

KINDS = {"llm_calls": "lượt gọi AI (LLM)", "llm_tokens": "token LLM", "images": "lượt tạo ảnh", "voice_credits": "credit giọng đọc"}


class BudgetError(RuntimeError):
    pass


def ledger_file(proj):
    return Path(proj) / "logs" / "ai_ledger.jsonl"


def append(proj, row):
    f = ledger_file(proj)
    f.parent.mkdir(parents=True, exist_ok=True)
    row = {"ts": time.strftime("%Y-%m-%d %H:%M:%S"), **row}
    with f.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def rows(proj):
    f = ledger_file(proj)
    out = []
    if f.exists():
        for line in f.read_text(encoding="utf-8").splitlines():
            try:
                out.append(json.loads(line))
            except ValueError:
                pass
    return out


def brief_budget(proj):
    f = Path(proj) / "brief.json"
    if f.exists():
        b = json.loads(f.read_text(encoding="utf-8")).get("budget")
        return b if isinstance(b, dict) else {}
    return {}


def limits(proj):
    lim = dict(aiconfig.get()["limits"])
    for k, v in brief_budget(proj).items():
        if k in KINDS and v not in ("", None):
            lim[k] = float(v) if k == "voice_credits" else int(v)
    return lim


def voice_credits_spent(proj):
    f = Path(proj) / "work" / "api_calls.jsonl"
    total = 0
    if f.exists():
        for line in f.read_text(encoding="utf-8").splitlines():
            try:
                e = json.loads(line)
            except ValueError:
                continue
            total += (e.get("credit_cost") or 0) + (e.get("transcript_cost") or 0)
    return total


def usage(proj):
    r = rows(proj)
    llm = [x for x in r if x.get("kind") == "llm" and not x.get("cache")]
    img = [x for x in r if x.get("kind") == "image" and not x.get("cache")]
    return {"llm_calls": len(llm), "llm_tokens": sum((x.get("tokens") or {}).get("total", 0) for x in llm), "images": len(img),
            "voice_credits": voice_credits_spent(proj)}


def check(proj, kind, planned=1):
    """Raise BudgetError (clear Vietnamese message) if starting `planned` more of `kind` would pass the project limit."""
    lim = limits(proj).get(kind)
    if lim is None:
        return
    used = usage(proj)[kind]
    if used + planned > lim:
        raise BudgetError(f"Vượt hạn mức dự án: {KINDS[kind]} đã dùng {used:g}, cần thêm {planned:g}, hạn mức {lim:g}. "
                          f"Công việc này chưa được bắt đầu; tăng hạn mức trong thông tin dự án (ngân sách) nếu bạn muốn tiếp tục.")


def summary(proj):
    """For the production page: usage vs limit, per model LLM figures, image runs, voice credits, and the money estimate (or 'unknown')."""
    u, lim = usage(proj), limits(proj)
    prices = aiconfig.get().get("price_per_1k_tokens") or {}
    models, est_money, unknown = {}, 0.0, False
    for x in rows(proj):
        if x.get("kind") != "llm" or x.get("cache"):
            continue
        m = models.setdefault(x.get("model_actual") or x.get("model") or "?", {"calls": 0, "tokens": 0, "failed": 0})
        m["calls"] += 1
        m["tokens"] += (x.get("tokens") or {}).get("total", 0)
        m["failed"] += 1 if x.get("status") != "ok" else 0
    for name, m in models.items():
        p = prices.get(name)
        if p:
            est_money += m["tokens"] / 1000 * (p.get("in", 0) + p.get("out", 0)) / 2
        else:
            unknown = True
    cache_hits = sum(1 for x in rows(proj) if x.get("cache"))
    return {"usage": u, "limits": lim, "llm_models": models, "cache_hits": cache_hits, "image_runs": u["images"], "voice_credits": u["voice_credits"],
            "money": None if (unknown or not models) else round(est_money, 4),
            "money_note": ("chưa biết: nhà cung cấp chỉ trả số token (agy không báo tiền); đặt price_per_1k_tokens trong config để ước tính"
                           if (unknown or not models) else "ước tính theo bảng giá trong config")}
