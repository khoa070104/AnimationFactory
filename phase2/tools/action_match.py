"""Does the narration ask for something the scene can show? A small shared lexicon (Vietnamese) of what a sentence can ask a character to DO:
  SUPPORTED   verb pattern -> the action(s) that show it (any character of the scene may perform it);
  UNSUPPORTED depictions the tool cannot draw yet (no animation exists): the sentence should say what the picture shows instead, or the owner accepts the gap
              by listing the phrase in the scene's `accepted_gaps`.
Used by validate_storyboard (warnings) and the storyboard prompt; add a verb here once an action exists for it."""
import re

SUPPORTED = [
    (r"\bviết\b|\bghi (?:lại|chép)\b|\bkẻ\b|\bđiền\b", {"write"}),
    (r"nhún vai", {"shrug"}),
    (r"\bchỉ (?:vào|tay|cho|ra)\b|\bnhìn vào bảng\b", {"point", "point_seq"}),
    (r"\bvẫy\b|\bchào\b", {"wave"}),
    (r"\bgật\b", {"nod"}),
    (r"cầm điện thoại|nhìn điện thoại|lướt điện thoại|bấm điện thoại", {"hold_phone"}),
    (r"\bxách\b|cầm giỏ|cầm túi|\bgiỏ\b", {"carry"}),
    (r"ăn mừng|hoan hô|reo lên|giơ tay", {"cheer"}),
    (r"đỡ má|chống cằm|lo lắng", {"cheek"}),
]
UNSUPPORTED = [
    (r"mở (?:cửa )?tủ", "mở tủ"),
    (r"xếp [^.,;:!?]{0,25}(?:vào|lên)", "xếp đồ"),
    (r"\bngồi\b", "ngồi"),
    (r"\bnấu ăn\b|\bnấu (?:cơm|bữa|món)\b|\bnêm\b|\bxào\b(?! rau)", "nấu"),
    (r"\brửa\b|\bgọt\b|\bthái\b", "sơ chế"),
    (r"\bthưởng thức\b|\băn (?:cơm|bữa|tối)\b", "ăn"),
    (r"\bvứt\b|\bném\b", "vứt"),
    (r"\bđổ (?:vào|ra|đi)\b", "đổ"),
]


def check(voice, actions_by_char, accepted=()):
    """-> list of problem strings. `actions_by_char`: iterable of action-name sets (main, cast...)."""
    have = set().union(*actions_by_char) if actions_by_char else set()
    low = voice.lower()
    out = []
    for rx, acts in SUPPORTED:
        m = re.search(rx, low)
        if m and not (acts & have):
            out.append(f"the text says {m.group(0)!r} but no {'/'.join(sorted(acts))} action shows it")
    for rx, name in UNSUPPORTED:
        m = re.search(rx, low)
        if m and not any(a.lower() in m.group(0) or m.group(0) in a.lower() for a in accepted):
            out.append(f"the text describes {m.group(0)!r} ({name}), which the tool cannot show yet: say what the picture shows instead, or list the phrase in `accepted_gaps`")
    return out
