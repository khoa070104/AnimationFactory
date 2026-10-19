"""Deterministic stand-in for the LLM, used by tests (in-process runner hook and, through fake_agy.py, as a fake `agy --json-schema`).
It reads the real prompts the tool sends (so it also proves that the prompts carry the data they must) and answers with schema-valid data:
  script      N scenes about the brief's topic (different topics -> different texts)       storyboard   visuals designed per scene found in the prompt
  asset_plan  one prop asset                                                              research_*   facts for a fixed topic
Modes (env FAKE_LLM_MODE or the `mode` argument): ok | invalid (answers that break the schema) | badcue (storyboard uses cues that are not in the text)."""
import json
import re

NUMS = ["một", "hai", "ba", "bốn", "năm", "sáu", "bảy", "tám", "chín", "mười"]


def _topic(prompt):
    m = re.search(r"- topic: (.*)", prompt)
    return (m.group(1).strip() if m else "chủ đề") or "chủ đề"


def _script(prompt):
    topic = _topic(prompt)
    m = re.search(r"aim for (\d+)", prompt)
    n = int(m.group(1)) if m else 8
    m2 = re.search(r"about (\d+) characters", prompt)
    per = max(100, int(m2.group(1)) // n) if m2 else 160
    base = [f"Hôm nay chúng ta nói về {topic.lower()}, một chuyện ai cũng gặp.",
            "Nhiều người thấy việc này khó, nhưng thật ra chỉ cần hiểu từng bước nhỏ.",
            "Bước đầu tiên là nhìn rõ số tiền mình có và số tiền mình cần mỗi tháng.",
            "Bước tiếp theo là chia khoản tiền đó thành ba phần rõ ràng cho từng mục đích.",
            "Ví dụ nếu thu nhập là mười triệu, ta có thể giữ lại hai triệu cho kế hoạch dài hạn.",
            "Quan trọng là bắt đầu nhỏ và đều đặn, thay vì chờ đến lúc thật nhiều.",
            "Mỗi tháng hãy xem lại một lần để biết mình đang đi đúng hướng hay chưa.",
            "Tóm lại, hiểu rõ tiền của mình giúp bạn chủ động hơn trong mọi quyết định."]
    scenes = []
    for i in range(n):
        voice = base[i % len(base)]
        while len(voice) < per:
            voice += " " + base[(i + len(voice)) % len(base)]
        voice = voice[: max(per, 90)].rsplit(" ", 1)[0].rstrip(",;") + "."
        scenes.append({"title": f"Ý {i + 1}", "section": "hook" if i == 0 else ("end" if i == n - 1 else "body"), "voice": voice, "notes": "minh họa ý chính", "fact_ids": []})
    msg = re.search(r"- key message: (.*)", prompt)
    note = re.search(r"- notes: (.*)", prompt)
    extra = " ".join(x.group(1).strip() for x in (msg, note) if x and x.group(1).strip())
    if extra:
        scenes[-1]["voice"] += " " + extra
    return {"title": topic[:60], "scenes": scenes, "claims_to_verify": ([{"text": "Số liệu minh họa cần kiểm chứng", "reason": "không có nguồn"}] if "kiểm chứng" in prompt else [])}


def _phrase(voice, k, size=2):
    toks = [w.strip(".,;:!?") for w in voice.split() if w.strip(".,;:!?")]
    k = min(k, max(0, len(toks) - size))
    return " ".join(toks[k:k + size])


def _main(prompt):
    m = re.search(r'"id": "(\w+)", "name": "[^"]*", "role": "main"', prompt)
    return m.group(1) if m else None


def _storyboard(prompt, mode):
    scenes = []
    for m in re.finditer(r"^(s\d+\w*) \[(\w+)\] (.*?): (.*)$", prompt, re.M):
        sid, sec, title, voice = m.groups()
        i = len(scenes)
        layout = i % 4
        cue = _phrase(voice, 2) if mode != "badcue" else "cụm không có trong lời"
        v = {"id": sid, "bg": "blue" if layout == 3 else "cream", "bi": {**({"char": _main(prompt)} if (mode == "chars" and _main(prompt)) else {}), "x": 500, "y": 930, "scale": 1.05, "face": ["happy", "neutral", "worried", "thinking"][i % 4], "pose": "idle"},
             "actions": ([{"name": "enter", "at": 0.0}] if i == 0 else [{"name": ["point", "cheek", "nod", "shrug"][i % 4], "cue": cue, "hold": 0.8}]),
             "face_cues": [], "items": []}
        a, b = _phrase(voice, 1, 1), _phrase(voice, 4, 1)
        if layout == 0:
            v["items"] = [{"type": "prop", "img": "wallet", "x": 1400, "y": 560, "scale": 1.0, "appear": cue}, {"type": "text", "text": title, "x": 1400, "y": 330, "size": 60, "color": "dark", "appear": 0.4}]
        elif layout == 1:
            v["items"] = [{"type": "chart", "x": 1340, "y": 520, "scale": 1.0, "title": title, "unit_h": 30, "appear": 0.3,
                           "bars": [{"label": "A", "value": 3, "text": "3", "color": "teal", "appear": a}, {"label": "B", "value": 6, "text": "6", "color": "blue", "appear": b}]}]
        elif layout == 2:
            v["items"] = [{"type": "pills", "x": 1380, "y": 430, "gap": 130, "size": 50, "texts": ["Bước một", "Bước hai", "Bước ba"], "appears": [0.5, 1.5, 2.5]}]
        else:
            v["items"] = [{"type": "notice", "x": 1250, "y": 520, "amount": "+2.000.000đ", "caption": title, "appear": 0.4}]
        scenes.append(v)
    return {"scenes": scenes}


def _plan(prompt):
    sid = (re.findall(r"^(s\d+\w*) ", prompt, re.M) or ["s02"])
    sid = sid[1] if len(sid) > 1 else sid[0]
    return {"assets": [{"id": "goal_prop", "kind": "prop", "prompt": "a small potted plant growing out of a stack of coins", "rationale": "visual metaphor for steady growth",
                        "scene": sid, "mode": "item", "x": 1450, "y": 600, "scale": 1.0, "appear": 0.5}]}


def respond(task, prompt, schema, mode="ok"):
    if mode == "invalid" and task in ("script", "storyboard", "asset_plan"):
        return {"wrong": True}
    if task in ("script", "script_fit"):
        return _script(prompt)
    if task == "storyboard":
        return _storyboard(prompt, mode)
    if task == "storyboard_repair":
        return _storyboard_repair(prompt)
    if task == "opportunity_topics":
        return {"topics": [{"topic": "Quỹ khẩn cấp là gì và nên có bao nhiêu", "angle": "ví dụ số cụ thể", "why_now": "nhiều người vừa bị cắt giảm thu nhập", "viewer_intent": "muốn biết con số", "queries": ["quỹ khẩn cấp"]},
                           {"topic": "Cách đọc sao kê thẻ tín dụng", "angle": "từng dòng một", "why_now": "mùa mua sắm", "viewer_intent": "tránh phí", "queries": ["sao kê thẻ"]},
                           {"topic": "Trả nợ sớm hay đầu tư thêm", "angle": "so sánh lãi", "why_now": "lãi suất đổi", "viewer_intent": "quyết định", "queries": ["trả nợ sớm"]}]}
    if task == "opportunity_videos":
        t = re.search(r"about: (.*?) \(queries", prompt)
        slug = re.sub(r"\W+", "-", (t.group(1) if t else "x").lower())[:20]
        return {"videos": [{"title": f"Video A về {slug}", "url": f"https://www.youtube.com/watch?v=aaa{slug}", "channel": "Kênh A"},
                           {"title": f"Video B về {slug}", "url": f"https://www.youtube.com/watch?v=bbb{slug}", "channel": "Kênh B"},
                           {"title": "Video không đọc được", "url": "https://example.test/not-youtube", "channel": "?"}]}
    if task == "opportunity_judge":
        return {"fit": 7, "fit_reason": "phù hợp người xem trẻ", "difference": "dùng ví dụ số cụ thể", "risk": "chủ đề đã có nhiều video"}
    if task == "characters":
        return _characters(prompt)
    if task == "asset_plan":
        return _plan(prompt)
    if task == "research_classify":
        need = "lãi suất" in prompt.lower() or "kiểm chứng" in prompt.lower()
        return {"needs_research": need, "reason": "có số liệu cần kiểm chứng" if need else "kiến thức phổ thông", "queries": ["lãi suất tiết kiệm 12 tháng"] if need else []}
    if task == "research_facts":
        return {"facts": [{"claim": "Lãi suất tiết kiệm 12 tháng ở nhóm ngân hàng lớn khoảng 5,9% một năm.", "quote": "lãi suất 12 tháng 5,9% một năm", "url": "https://example.test/rates"},
                          {"claim": "Mọi ngân hàng đều trả đúng 20% một năm.", "quote": "20% một năm", "url": "https://example.test/rates"}]}
    if task.startswith("revise_scene"):
        return _revise(prompt)
    if task == "asset_prompt":
        return {"prompt": "a small potted plant on a stack of coins, rounder shapes, brighter green leaves", "explanation": "tròn hơn, xanh hơn theo góp ý"}
    raise KeyError(task)


def _characters(prompt):
    hint = re.search(r"MAIN CHARACTER \(keep exactly this look[^)]*\): (.*)", prompt)
    main = {"id": "lan", "name": "Lan", "role": "main", "description": (hint.group(1) if hint else "Lan, a young woman with long dark hair in a ponytail, round face, warm skin, calm expression"),
            "outfit": "green jacket, grey trousers, white sneakers", "personality": "careful and curious"}
    return {"characters": [main], "rationale": "one person the viewer follows"}


def _storyboard_repair(prompt):
    out = []
    for m in re.finditer(r'"id": "(s\d+\w*)"', prompt):
        out.append({"id": m.group(1), "bg": "cream", "bi": {"x": 500, "y": 930, "scale": 1.05, "face": "neutral", "pose": "idle"}, "actions": [], "face_cues": [],
                    "items": [{"type": "text", "text": "Ý chính", "x": 1400, "y": 400, "size": 60, "color": "dark", "appear": 0.4}]})
    return {"scenes": out}


def _revise(prompt):
    m = re.search(r"CURRENT SCENE JSON:\n(\{.*\})\n", prompt)
    sc = json.loads(m.group(1)) if m else {}
    ins = (re.search(r"INSTRUCTION: (.*)", prompt) or [None, ""])[1]
    if "ngắn" in ins:
        sc["voice"] = sc["voice"].split(".")[0] + "."
    if "vui" in ins:
        sc["bi"]["face"] = "happy"
    return {"scene": sc, "summary": "đã chỉnh theo yêu cầu: " + ins[:60]}


def task_of(prompt):
    m = re.findall(r"TASK: (\w+)", prompt)
    return m[-1] if m else None
