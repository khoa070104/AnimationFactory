"""Content research for a brief: find sources, keep URL + access time, tie every fact to its source and mark what could not be backed up.

  research.run(proj, brief, channel, mode)  ->  research dict (also written by prepare.py to PROJECT/prepare/research.json)

Flow (cheap model for classification/extraction, as configured):
  1. mode "no" -> nothing. "auto" -> a cheap call decides whether the topic needs facts checked and which searches to run; "yes" -> always.
  2. one search-enabled call returns candidate facts {claim, quote, url}; the run is only accepted as research if the web-search tool was really used;
  3. every url is opened by THIS tool (redirects resolved, access time stored, page text read - nothing is saved as a file) and the fact is
     `verified` only when the page was reachable and the quote (or its numbers) really appears in the page text;
  4. facts that are not verified keep `needs_check: true` with the reason - the owner accepts/removes them in the UI, the script writer may not state them as fact;
  5. reference links the owner put in the brief are read the same way and their excerpts are given to the script writer with their URL and time.
`fetcher(url) -> (final_url, status, text)` and `runner` (LLM runner) can be replaced in tests."""
import html
import re
import time
import urllib.error
import urllib.request
from pathlib import Path

import llm

UA = "Mozilla/5.0 (compatible; AnimationFactory/3 research; +local tool)"
MAX_BYTES = 600_000
URL_RE = re.compile(r"https?://[^\s<>\"')\]]+")

CLASSIFY_SCHEMA = {"type": "object", "required": ["needs_research", "reason", "queries"], "properties": {
    "needs_research": {"type": "boolean"}, "reason": {"type": "string"}, "queries": {"type": "array", "maxItems": 4, "items": {"type": "string"}}}}
FACTS_SCHEMA = {"type": "object", "required": ["facts"], "properties": {"facts": {"type": "array", "maxItems": 10, "items": {
    "type": "object", "required": ["claim", "url"], "properties": {"claim": {"type": "string"}, "quote": {"type": "string"}, "url": {"type": "string"}}}}}}


def fetch_text(url, timeout=20):
    """-> (final_url, status, plain text). Never raises: failures come back as status 0 / text ''. Reads text pages only, nothing is stored."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html,text/plain;q=0.9,*/*;q=0.1"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            ctype = (r.headers.get("Content-Type") or "").lower()
            if "html" not in ctype and "text" not in ctype:
                return r.geturl(), r.status, ""
            raw = r.read(MAX_BYTES)
            m = re.search(r"charset=([\w-]+)", ctype)
            text = raw.decode(m.group(1) if m else "utf-8", errors="replace")
            text = re.sub(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>", " ", text)
            text = html.unescape(re.sub(r"(?s)<[^>]+>", " ", text))
            return r.geturl(), r.status, re.sub(r"\s+", " ", text).strip()
    except (urllib.error.URLError, OSError, ValueError):
        return url, 0, ""


def _norm(s):
    return re.sub(r"[^\w%]+", " ", s.lower()).strip()


def quote_supported(quote, claim, text):
    """True when the page text contains the quote, or (weaker) every number of the claim and most of the quote's words."""
    t = _norm(text)
    q = _norm(quote or "")
    if q and len(q) >= 12 and q in t:
        return True
    nums = re.findall(r"\d+(?:[.,]\d+)?", claim + " " + (quote or ""))
    words = [w for w in q.split() if len(w) > 3]
    if nums and all(n.replace(",", ".") in t.replace(",", ".") for n in nums):
        return not words or sum(1 for w in words if w in t) / len(words) >= 0.6
    return False


def run(proj, brief, channel, mode="auto", fetcher=None, runner=None):
    fetcher = fetcher or fetch_text
    now = lambda: time.strftime("%Y-%m-%d %H:%M:%S")
    out = {"mode": mode, "decision": None, "queries": [], "facts": [], "references": [], "searched": False, "created": now()}
    topic = f"Topic: {brief.get('title', '')}\nGoal: {brief.get('goal', '')}\nKey message: {brief.get('message', '')}\nAudience: {brief.get('audience') or channel.get('audience', '')}"
    # reference links given by the owner
    for u in dict.fromkeys(URL_RE.findall(str(brief.get("references", "")))):
        final, status, text = fetcher(u)
        out["references"].append({"url": u, "final_url": final, "status": status, "accessed_at": now(), "reachable": status == 200 and bool(text),
                                  "excerpt": text[:3000]})
    if mode == "no":
        out["decision"] = {"needs_research": False, "reason": "owner chose no research"}
        return out
    cls = llm.call(proj, "research_classify", "cheap",
                   f"{topic}\n\nDecide whether making an accurate explainer video on this topic needs facts checked on the web (numbers, rules, dates, definitions that can be wrong or change). "
                   "If yes, list up to 4 short web search queries (Vietnamese or English) that would verify the key facts. TASK: research_classify",
                   CLASSIFY_SCHEMA, runner=runner)["data"]
    out["decision"] = {"needs_research": bool(cls["needs_research"]) or mode == "yes", "reason": cls["reason"]}
    out["queries"] = cls["queries"]
    if not out["decision"]["needs_research"]:
        return out
    res = llm.call(proj, "research_facts", "cheap",
                   f"{topic}\n\nUse web search for these queries: {cls['queries'] or [brief.get('title', '')]}. Return up to 8 key facts that a script for this video may rely on. "
                   "For each fact give: claim (one sentence, Vietnamese), quote (a short passage copied from the source that supports it), url (the source page you found in the search results). "
                   "Do not invent facts or urls. TASK: research_facts", FACTS_SCHEMA, search=True, runner=runner)
    out["searched"] = (res["meta"].get("searches") or 0) > 0
    out["model"] = res["meta"].get("model_actual") or res["meta"].get("model")
    deadline = time.time() + 150                                       # total time allowed for opening sources (slow sites must not stall the whole step)
    for i, f in enumerate(res["data"]["facts"], 1):
        final, status, text = fetcher(f["url"]) if time.time() < deadline else (f["url"], 0, "")
        reachable = status == 200 and bool(text)
        supported = reachable and quote_supported(f.get("quote", ""), f["claim"], text)
        reasons = []
        if not out["searched"]:
            reasons.append("the search tool was not used for this answer")
        if not reachable:
            reasons.append("source page could not be opened")
        elif not supported:
            reasons.append("the quote/numbers were not found in the page text")
        out["facts"].append({"id": f"f{i}", "claim": f["claim"], "quote": f.get("quote", ""), "url": f["url"], "final_url": final, "status": status,
                             "accessed_at": now(), "verified": not reasons, "needs_check": bool(reasons), "reasons": reasons, "decision": None})
    return out
