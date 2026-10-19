"""Who really made a decision. The UI's "approver name" is only a label the person typed; this module classifies it together with HOW the decision arrived,
so test clicks and AI actions are never counted as the owner's approval where it matters (the paid voice step).

  classify(by, via) -> {"type": human | test | ai | system, "via": web | telegram | cli | api, "label": by, "verified": bool}

human     a person: a typed name from the web UI/CLI, or a Telegram account on the configured allow-list (verified = True only for Telegram allow-list ids)
test      a label that says it is a test (tester, "kiểm thử", "test") - Claude or a test clicking buttons
ai        a label naming an AI agent (Claude, Gemini, agy, "AI ")
system    the tool itself (first build, scheduled jobs)
A web/CLI name cannot prove identity (verified False); Telegram callbacks carry the numeric user id, which the allow-list checks."""
import re

TEST_RE = re.compile(r"(kiểm thử|kiem thu|\btest(er|ing)?\b|không phải chủ dự án)", re.I)
AI_RE = re.compile(r"^(claude|gemini|agy|antigravity|gpt|ai\b|bot\b|assistant)", re.I)
SYSTEM = {"tool", "first build", "system"}


def classify(by, via="web", verified=False):
    label = str(by or "").strip()
    if label.lower() in SYSTEM:
        t = "system"
    elif TEST_RE.search(label):
        t = "test"
    elif AI_RE.search(label):
        t = "ai"
    else:
        t = "human"
    return {"type": t, "via": via, "label": label, "verified": bool(verified and t == "human")}


def counts_as_owner(actor):
    """May this decision release a paid step? Only a human. (verified identity is shown, but a web user is accepted as the owner of a local tool.)"""
    return actor.get("type") == "human"
