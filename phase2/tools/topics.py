"""Topic history per channel (so the AI does not propose, and the owner does not make, the same video twice).
phase2/topic_history.jsonl (AF_TOPIC_HISTORY overrides the path): one line per accepted topic {at, channel, title, project, status}.
`status` = draft (a project was created for it) | published (the owner says it went out). Only accepted topics count; AI candidates are not history."""
import json
import os
import re
import time
from pathlib import Path

P2 = Path(__file__).resolve().parent.parent


def file():
    return Path(os.environ.get("AF_TOPIC_HISTORY") or (P2 / "topic_history.jsonl"))


def _norm(t):
    return " ".join(re.sub(r"[^\w]+", " ", str(t).lower()).split())


def add(channel, title, project, status="draft"):
    f = file()
    f.parent.mkdir(parents=True, exist_ok=True)
    with f.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({"at": time.strftime("%Y-%m-%d %H:%M:%S"), "channel": channel, "title": title, "project": project, "status": status}, ensure_ascii=False) + "\n")


def rows(channel=None):
    f = file()
    out = []
    if f.exists():
        for line in f.read_text(encoding="utf-8").splitlines():
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if channel is None or r.get("channel") == channel:
                out.append(r)
    return out


def titles(channel):
    return sorted({r["title"] for r in rows(channel)})


def is_duplicate(title, past, threshold=0.8):
    """Same video again? exact (normalised) match or word overlap >= threshold with a past title."""
    a = set(_norm(title).split())
    for p in past:
        b = set(_norm(p).split())
        if a and b and (a == b or len(a & b) / max(len(a), len(b)) >= threshold):
            return True
    return False
