"""Compare LLM providers on the SAME small tasks taken from the tool's own prompts (classification, extraction, asset prompts, cast design, asset plans).
One attempt per task and provider (no retries, no cache, no ledger), measured: usable first time, schema/sanity failures, errors, latency median / P95, tokens.
  python llm_compare.py --providers agy,freellmapi [--n 20] [--out evidence/phase3/llm_compare.md]
`agy` = the configured Antigravity route (models.cheap / models.quality); any other name must exist in config ai.providers (key from its environment variable).
The result is a decision aid: enable a provider per task type (ai.routing) only where its usable rate and latency are better; it is never switched on by this script."""
import argparse
import json
import statistics
import sys
import time
from pathlib import Path

P2 = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(P2 / "tools"))
import aiconfig  # noqa: E402
import llm  # noqa: E402
import prepare as PR  # noqa: E402
import revise  # noqa: E402
import research as R  # noqa: E402

TOPICS = ["Trả nợ sớm hay đầu tư thêm", "Lập ngân sách tháng cho người mới đi làm", "Ba thói quen giúp tập trung học bài", "Vì sao nên có quỹ khẩn cấp",
          "Mua trả góp có thật sự rẻ", "Cách đọc sao kê thẻ tín dụng", "Nên thuê nhà hay mua nhà", "Học ngoại ngữ mười phút mỗi ngày"]
SCENES = [{"id": f"s0{i + 1}", "title": f"Ý {i + 1}", "voice": v, "section": "body", "notes": ""} for i, v in enumerate([
    "Mỗi tháng hãy ghi lại các khoản chi cố định như tiền nhà, điện và nước.", "Ví dụ thu nhập mười triệu thì bốn triệu dành cho chi phí cố định.", "Cuối tháng dành mười lăm phút xem lại từng nhóm chi tiêu."])]


def build_tasks(n):
    ch = PR.CH.DEFAULT
    out = []
    for t in TOPICS:
        out.append({"name": "research_classify", "tier": "cheap", "schema": R.CLASSIFY_SCHEMA, "validate": None,
                    "prompt": f"Topic: {t}\nGoal: người xem hiểu cách làm\nKey message: bắt đầu nhỏ\nAudience: người đi làm trẻ\n\nDecide whether an accurate explainer video on this topic needs facts checked on the web. "
                              "If yes list up to 4 short web search queries. TASK: research_classify"})
    for t in TOPICS[:5]:
        out.append({"name": "asset_prompt", "tier": "cheap", "schema": revise.ASSET_SCHEMA, "validate": lambda d: revise._prompt_problems(revise._unwrap(d.get("prompt", "")), "a small notebook"),
                    "prompt": ("Improve the prompt of an AI image (flat 2D vector illustration). Current subject prompt: 'a small notebook'\nOwner's feedback: " + f"làm cho hợp chủ đề '{t}'" +
                               "\nWrite the new subject prompt in English (subject only) and a one-line explanation in Vietnamese.\nTASK: asset_prompt")})
    brief = {"title": TOPICS[2], "goal": "nhớ ba thói quen", "message": "tập trung là kỹ năng", "story_guideline": "học sinh được chị gái chỉ cách", "character_hint": ""}
    script = {"scenes": [{**s, "voice": s["voice"]} for s in SCENES]}
    for _ in range(4):
        out.append({"name": "characters", "tier": "quality", "schema": PR.CHAR_SCHEMA, "validate": None, "prompt": PR.characters_prompt(brief, ch, script)})
    scenes_txt = "\n".join(f"{s['id']} {s['title']}: {s['voice']} | now: bg=cream, items=[]" for s in SCENES)
    for _ in range(3):
        out.append({"name": "asset_plan", "tier": "cheap", "schema": PR.PLAN_SCHEMA, "validate": None,
                    "prompt": "Plan AI-generated image assets for this video. No earlier asset may be reused: every asset you propose is NEW.\n\nSCENES:\n" + scenes_txt +
                              "\n\nPropose at most 2 assets (id, kind prop|background, prompt in English, scene, mode item|bg, placement). TASK: asset_plan"})
    return out[:n]


def run_one(provider, cfg, task):
    tier = task["tier"]
    if provider == "agy":
        fn = lambda: llm._run_agy(aiconfig.model_for(tier, cfg), task["prompt"], task["schema"], int(cfg["timeout_seconds"]), False)
    else:
        pc = cfg["providers"][provider]
        fn = lambda: llm._run_http(pc, aiconfig.model_for(tier, cfg, provider), task["prompt"], task["schema"], int(cfg["timeout_seconds"]), False)
    t0 = time.time()
    try:
        data, meta = fn()
    except llm.LLMError as e:
        return {"status": "error", "error": str(e)[:160], "seconds": round(time.time() - t0, 1), "tokens": 0}
    problems = ["no structured answer"] if data is None else llm.check_schema(data, task["schema"])
    if not problems and task.get("validate"):
        problems = list(task["validate"](data) or [])
    return {"status": "ok" if not problems else "invalid", "error": "; ".join(problems[:2]), "seconds": round(time.time() - t0, 1), "tokens": (meta.get("tokens") or {}).get("total", 0),
            "model": meta.get("model_actual")}


def summarize(rows):
    secs = sorted(r["seconds"] for r in rows)
    p95 = secs[min(len(secs) - 1, int(round(0.95 * (len(secs) - 1))))] if secs else None
    return {"tasks": len(rows), "usable": sum(1 for r in rows if r["status"] == "ok"), "invalid": sum(1 for r in rows if r["status"] == "invalid"), "errors": sum(1 for r in rows if r["status"] == "error"),
            "median_s": round(statistics.median(secs), 1) if secs else None, "p95_s": p95, "tokens": sum(r["tokens"] for r in rows),
            "models": sorted({r.get("model") for r in rows if r.get("model")})}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--providers", default="agy")
    ap.add_argument("--n", type=int, default=20)
    ap.add_argument("--out")
    a = ap.parse_args()
    cfg = aiconfig.get()
    tasks = build_tasks(a.n)
    result = {}
    for prov in a.providers.split(","):
        rows = []
        for t in tasks:
            r = run_one(prov, cfg, t)
            r["task"] = t["name"]
            rows.append(r)
            print(prov, t["name"], r["status"], r["seconds"], flush=True)
        result[prov] = {"summary": summarize(rows), "rows": rows}
    L = ["# So sánh nhà cung cấp LLM trên cùng một bộ việc", "", f"{len(tasks)} việc lấy từ prompt thật của tool (phân loại nghiên cứu, prompt ảnh, thiết kế nhân vật, kế hoạch asset). Một lượt/việc, không retry, không cache.", "",
         "| Nhà cung cấp | Việc | Dùng được ngay | Sai schema/ý | Lỗi | Trung vị (s) | P95 (s) | Token | Model thực tế |", "|---|---|---|---|---|---|---|---|---|"]
    for prov, v in result.items():
        s = v["summary"]
        L.append(f"| {prov} | {s['tasks']} | {s['usable']} | {s['invalid']} | {s['errors']} | {s['median_s']} | {s['p95_s']} | {s['tokens']} | {', '.join(s['models'])} |")
    L += ["", "Chi phí tiền: nhà cung cấp chỉ báo token; không quy ra tiền nếu chưa khai bảng giá trong config.", ""]
    txt = "\n".join(L)
    print(txt)
    if a.out:
        Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        Path(a.out).write_text(txt, encoding="utf-8")
        Path(a.out).with_suffix(".json").write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
