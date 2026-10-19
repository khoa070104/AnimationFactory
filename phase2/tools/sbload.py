"""Load a storyboard with defaults applied, so authors only write what matters.
 * `subtitles` may be omitted (or "auto"): the voice text is split into one-line segments (<= subtitle_max_chars, default 40) at punctuation / word boundaries;
 * missing `actions`, `face_cues`, `holds`, `items`, `transition` default to empty / "cut".
Every tool reads storyboards through load_storyboard(), so validation, previews, voice and video all see the same normalised data."""
import json
import re
from pathlib import Path


def auto_subtitles(voice, max_chars=40):
    """Greedy packing of words into segments: never longer than max_chars; prefer a break after . ! ? : ; and (once >= 18 chars) after a comma."""
    segs, cur = [], ""
    for w in voice.split():
        if cur and len(cur) + 1 + len(w) > max_chars:
            segs.append(cur)
            cur = ""
        cur = (cur + " " + w) if cur else w
        end = w[-1] if w else ""
        if end in ".!?:;" or (end == "," and len(cur) >= 18):
            segs.append(cur)
            cur = ""
    if cur:
        segs.append(cur)
    return _no_orphans(segs, max_chars)


def _no_orphans(segs, max_chars, min_words=3, min_chars=14):
    """A segment of one or two words / under 14 characters ("xóm.") that only exists because the line before it was cut for length is joined with it,
    and the pair is split again near its middle (a short segment after a full stop is a real short sentence and stays)."""
    out = []
    for seg in segs:
        short = len(seg.split()) < min_words or len(seg) < min_chars
        if short and out and out[-1][-1] not in ".!?:;,":
            words = (out.pop() + " " + seg).split()
            joined = " ".join(words)
            if len(joined) <= max_chars:
                out.append(joined)
                continue
            best = None
            for k in range(1, len(words)):
                x, y = " ".join(words[:k]), " ".join(words[k:])
                if len(x) <= max_chars and len(y) <= max_chars and (best is None or abs(len(x) - len(y)) < best[0]):
                    best = (abs(len(x) - len(y)), x, y)
            out += [best[1], best[2]] if best else [" ".join(words[:-len(seg.split())]), seg]
        else:
            out.append(seg)
    return out


CAMERA_PRESETS = {"push_in": {"zoom": [1.0, 1.12], "pan": [[0, 0], [0, 0]]}, "pull_out": {"zoom": [1.12, 1.0], "pan": [[0, 0], [0, 0]]},
                  "pan_left": {"zoom": [1.06, 1.06], "pan": [[40, 0], [-40, 0]]}, "pan_right": {"zoom": [1.06, 1.06], "pan": [[-40, 0], [40, 0]]}}


def resolve_camera(c):
    """Scene camera: a preset name (push_in | pull_out | pan_left | pan_right) or {"zoom": [from, to], "pan": [[x0, y0], [x1, y1]]}. -> dict or None."""
    if not c:
        return None
    if isinstance(c, str):
        if c not in CAMERA_PRESETS:
            raise ValueError(f"unknown camera preset {c!r} (known: {sorted(CAMERA_PRESETS)})")
        return json.loads(json.dumps(CAMERA_PRESETS[c]))
    z = c.get("zoom", [1.0, 1.0])
    pan = c.get("pan", [[0, 0], [0, 0]])
    if len(z) != 2 or not all(0.5 <= float(v) <= 2.0 for v in z):
        raise ValueError("camera.zoom must be [from, to] within 0.5..2.0")
    if len(pan) != 2 or any(len(p) != 2 or abs(float(p[0])) > 600 or abs(float(p[1])) > 400 for p in pan):
        raise ValueError("camera.pan must be [[x0, y0], [x1, y1]] within +-600 / +-400 px")
    return {"zoom": [float(z[0]), float(z[1])], "pan": [[float(p[0]), float(p[1])] for p in pan]}


DEFAULT_TARGETS = {"duration": [60, 90], "scenes": [6, 10]}


def targets(sb):
    """Acceptance targets of a project (storyboard `targets`: {"duration": [min_s, max_s], "scenes": [min, max]}); defaults 60-90 s, 6-10 scenes."""
    t = dict(DEFAULT_TARGETS)
    t.update(sb.get("targets") or {})
    return t


# held props: scale / pivot (1x px of the picture) / offset from the hand / rotation
HOLD_DEFAULTS = {"notebook": {"scale": 0.8, "rot": 40, "off": [40, 15]},
                 "pen": {"scale": 0.55, "pivot": [18, 160], "rot": -35, "off": [4, 6]},
                 "basket": {"scale": 0.7, "pivot": [120, 16], "rot": 0, "off": [0, 8]},
                 "phone": {"scale": 0.34, "pivot": [150, 470], "rot": 0, "off": [0, 0]},          # grip at the bottom of the phone (lib/motion_demo.jsx)
                 "calculator": {"scale": 0.55, "pivot": [115, 305]}}
HOLD_DEFAULT_AI = {"scale": 0.6, "rot": 40, "off": [40, 15]}          # rot cancels the forearm tilt of the writing/holding pose so a notebook stays upright


_EMOJI = re.compile("[\U0001F000-\U0001FAFF\u2190-\u21FF\u2300-\u23FF\u2600-\u27BF\u2B00-\u2BFF\uFE0F\u200D]")


def has_emoji(s):
    return bool(_EMOJI.search(str(s)))


def strip_emoji(s):
    return " ".join(_EMOJI.sub("", str(s)).split())


def held_sides(sc, who):
    """Hands (L/R) that hold a prop for character `who` (main, cast1, ...) in scene `sc`."""
    return {h["side"] for h in sc.get("holds", []) if h.get("who", "main") == who}


def arm_params(name, held):
    """Extra action parameters when a hand is busy: cheer raises only the free arm."""
    if name == "cheer" and len(held) == 1:
        return {"free": "R" if "L" in held else "L"}
    return {}


def normalise(sb):
    mc = int(sb.get("subtitle_max_chars", 40))
    for sc in sb.get("scenes", []):
        if not sc.get("subtitles") or sc.get("subtitles") == "auto":
            sc["subtitles"] = auto_subtitles(sc.get("voice", ""), mc)
        sc.setdefault("actions", [])
        sc.setdefault("face_cues", [])
        sc.setdefault("holds", [])
        for h in sc["holds"]:                                            # what the AI picks is only prop + hand; size / grip point / rotation come from the prop's defaults
            d = HOLD_DEFAULTS.get(h.get("prop"), HOLD_DEFAULT_AI if str(h.get("prop", "")).startswith("ai:") else {})
            for k, v in d.items():
                h.setdefault(k, v)
        sc.setdefault("items", [])
        sc.setdefault("transition", "cut")
        sc.setdefault("cast", [])
        for c in sc["cast"]:
            c.setdefault("actions", [])
            c.setdefault("face_cues", [])
    return sb


def load_storyboard(path):
    p = Path(path)
    if p.is_dir():
        p = p / "storyboard.json"
    return normalise(json.loads(p.read_text(encoding="utf-8")))
