"""Topic opportunity research (YouTube first): candidate topics WITH evidence that was actually measured, kept apart from the AI's own judgement.

  run(proj, runner=None, fetcher=None) -> dict   (prepare.py step `opportunity` writes it to PROJECT/prepare/opportunities.json)

Flow (cheap model for everything here, as configured):
  1. candidates: 3 topic ideas for the channel/niche (angle, why now, viewer intent), avoiding the channel's earlier topics (topic_history);
  2. for each candidate a search-enabled call lists existing YouTube videos on it (only accepted if the web-search tool was really used);
  3. this tool opens every video URL ITSELF and reads what the page says: title, channel, views, length, publish date (`measured: true`, with access time);
     a video it cannot read stays `measured: false` and no number is invented;
  4. per-candidate summary from the measured videos only (n, median/max views, newest/oldest date); with no measured video the numbers are null, never 0;
  5. a last call gives the AI's own judgement (fit, difference, risk) from that evidence, marked `source: "AI"`.
Not available and therefore NEVER shown: search volume, Google keyword difficulty (a Google metric, not a YouTube one), subscriber-based forecasts.
`fetcher(url) -> (final_url, status, raw_html)` and `runner` (LLM runner) can be replaced in tests."""
import json
import re
import statistics
import time
import urllib.error
import urllib.request
from pathlib import Path

import llm
import topics

UA = "Mozilla/5.0 (compatible; AnimationFactory/4 research; +local tool)"
CAND_SCHEMA = {"type": "object", "required": ["topics"], "properties": {"topics": {"type": "array", "minItems": 1, "maxItems": 4, "items": {
    "type": "object", "required": ["topic", "angle", "why_now"], "properties": {"topic": {"type": "string"}, "angle": {"type": "string"}, "why_now": {"type": "string"},
                                                                               "viewer_intent": {"type": "string"}, "queries": {"type": "array", "maxItems": 3, "items": {"type": "string"}}}}}}}
VID_SCHEMA = {"type": "object", "required": ["videos"], "properties": {"videos": {"type": "array", "maxItems": 6, "items": {
    "type": "object", "required": ["title", "url"], "properties": {"title": {"type": "string"}, "url": {"type": "string"}, "channel": {"type": "string"}}}}}}
JUDGE_SCHEMA = {"type": "object", "required": ["fit", "difference", "risk"], "properties": {"fit": {"type": "integer"}, "fit_reason": {"type": "string"}, "difference": {"type": "string"}, "risk": {"type": "string"}}}
YT = re.compile(r"^https?://(www\.|m\.)?(youtube\.com/watch|youtu\.be/)", re.I)


def fetch_raw(url, timeout=20):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "vi,en;q=0.7"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.geturl(), r.status, r.read(900_000).decode("utf-8", errors="replace")
    except (urllib.error.URLError, OSError, ValueError):
        return url, 0, ""


def parse_video_page(html):
    """What a YouTube watch page states about its own video. -> dict with only the fields really found."""
    out = {}
    m = re.search(r'"videoDetails":\{(.*?)"isOwnerViewing"', html, re.S) or re.search(r'"videoDetails":\{(.{0,6000})', html, re.S)
    blob = m.group(1) if m else html
    for key, rx, cast in (("title", r'"title":"((?:[^"\\]|\\.)*)"', lambda v: json.loads('"' + v + '"')), ("views", r'"viewCount":"(\d+)"', int), ("length_s", r'"lengthSeconds":"(\d+)"', int),
                          ("channel", r'"author":"((?:[^"\\]|\\.)*)"', lambda v: json.loads('"' + v + '"'))):
        mm = re.search(rx, blob)
        if mm:
            try:
                out[key] = cast(mm.group(1))
            except (ValueError, TypeError):
                pass
    pd = re.search(r'"publishDate":"(\d{4}-\d{2}-\d{2})', html) or re.search(r'itemprop="datePublished" content="(\d{4}-\d{2}-\d{2})', html)
    if pd:
        out["published"] = pd.group(1)
    return out


def summarize(videos):
    ms = [v["measured"] for v in videos if v.get("measured")]
    views = [x["views"] for x in ms if "views" in x]
    dates = sorted(x["published"] for x in ms if "published" in x)
    return {"videos_found": len(videos), "videos_read": len(ms), "median_views": int(statistics.median(views)) if views else None, "max_views": max(views) if views else None,
            "newest": dates[-1] if dates else None, "oldest": dates[0] if dates else None,
            "note": ("số liệu chỉ từ " + str(len(ms)) + " video đọc được; không phải toàn bộ cạnh tranh") if ms else "chưa đọc được video nào: không có số liệu (không suy ra bằng 0)"}


def run(proj, brief, ch, runner=None, fetcher=None, n=3):
    fetcher = fetcher or fetch_raw
    now = lambda: time.strftime("%Y-%m-%d %H:%M:%S")
    past = topics.titles(ch_id := (brief.get("channel") or "default"))
    niche = (brief.get("title") or "").strip()
    cands = llm.call(proj, "opportunity_topics", "cheap",
                     f"Channel: audience {ch['audience']}; tone {ch['tone']}; avoid: {'; '.join(ch.get('avoid', []))}.\nOwner's theme/niche: {niche}\nStory guideline: {brief.get('story_guideline') or '-'}\n"
                     f"Topics this channel already covered (do NOT repeat): {json.dumps(past, ensure_ascii=False)}\n\nSuggest {n} different video topics for YouTube in this niche: topic (a clear video title in Vietnamese), "
                     "angle (what makes it different), why_now (one sentence), viewer_intent (what the viewer wants to know), queries (up to 2 short YouTube search queries). TASK: opportunity_topics",
                     CAND_SCHEMA, runner=runner)["data"]["topics"][:n]
    out = {"created": now(), "platform": "youtube", "niche": niche, "candidates": [], "not_available": ["search volume", "Google keyword difficulty", "subscriber-based forecast"]}
    for c in cands:
        if topics.is_duplicate(c["topic"], past):
            continue
        q = c.get("queries") or [c["topic"]]
        res = llm.call(proj, "opportunity_videos", "cheap",
                       f"Use web search to find existing YouTube videos about: {c['topic']} (queries: {q}). Return up to 5 videos you really found: title, url (the YouTube watch link), channel. Do not invent videos. TASK: opportunity_videos",
                       VID_SCHEMA, search=True, runner=runner)
        searched = (res["meta"].get("searches") or 0) > 0
        vids = []
        for v in res["data"]["videos"][:5] if searched else []:
            final, status, html = fetcher(v["url"])
            rec = {"title": v["title"], "url": v["url"], "final_url": final, "channel_claimed": v.get("channel"), "accessed_at": now(), "measured": None, "status": status}
            if status == 200 and html and YT.match(final):
                m = parse_video_page(html)
                if m.get("views") is not None or m.get("title"):
                    rec["measured"] = m
            vids.append(rec)
        summ = summarize(vids)
        j = llm.call(proj, "opportunity_judge", "cheap",
                     f"Topic: {c['topic']} ({c['angle']}). Evidence measured from YouTube pages: {json.dumps(summ, ensure_ascii=False)}; videos read: "
                     f"{json.dumps([v['measured'] for v in vids if v['measured']], ensure_ascii=False)}. Give your OWN judgement for a small educational channel: fit 0-10 (integer) with a one-line reason, "
                     "difference (how to stand out from those videos), risk. If the evidence is thin say so. Do not output numbers about search volume. TASK: opportunity_judge", JUDGE_SCHEMA, runner=runner)["data"]
        out["candidates"].append({**c, "searched": searched, "videos": vids, "summary": summ, "judgement": {**j, "source": "AI"},
                                  "evidence_state": "measured" if summ["videos_read"] >= 2 else ("partial" if summ["videos_read"] == 1 else "none")})
    return out
