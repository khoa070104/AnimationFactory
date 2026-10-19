"""Channel profile: who the videos are for and how they should sound/look. Stored in phase2/channels/<id>.json, shared by every project
that names it in its brief (brief.json "channel"). The AI steps read it; the storyboard builder takes character colour / voice from it.

Fields: name, audience, tone (giọng văn), visual_style, character {name, shirt}, avoid [list], guiding_message, language, voice {voice_id, speed},
targets {duration:[min,max], scenes:[min,max]}."""
import hashlib
import json
import re
from pathlib import Path

import agy_image as G

CH = Path(__file__).resolve().parent.parent / "channels"
ID_RE = re.compile(r"^[a-z0-9_]{1,40}$")
DEFAULT = {
    "name": "Kênh mẫu", "audience": "người đi làm trẻ, mới bắt đầu quản lý tiền", "tone": "thân thiện, rõ ràng, không giáo điều; câu ngắn, ví dụ đời thường",
    "visual_style": "phẳng, viền đậm, màu kem nền ấm; nhân vật người que Bi", "character": {"name": "Bi", "shirt": "#F26B21"},
    "avoid": ["lời khuyên đầu tư cụ thể", "hứa hẹn lợi nhuận", "so sánh/chê bai thương hiệu"], "guiding_message": "Hiểu tiền của mình để chủ động hơn, không cần giỏi toán.",
    "language": "vi", "voice": {"voice_id": "edge_vi-VN-HoaiMyNeural", "speed": 1.0}, "targets": {"duration": [60, 90], "scenes": [6, 10]},
}


class ChannelError(ValueError):
    pass


def validate(p):
    e = []
    for k in ("name", "audience", "tone", "visual_style", "guiding_message"):
        if not isinstance(p.get(k), str) or not p[k].strip():
            e.append(f"{k} is required")
    if not isinstance(p.get("avoid", []), list) or any(not isinstance(x, str) for x in p.get("avoid", [])):
        e.append("avoid must be a list of strings")
    ch = p.get("character") or {}
    if not re.fullmatch(r"#[0-9A-Fa-f]{6}", str(ch.get("shirt", ""))):
        e.append("character.shirt must be #RRGGBB")
    v = p.get("voice") or {}
    if not v.get("voice_id") or not isinstance(v.get("speed", 1.0), (int, float)) or not 0.5 <= v.get("speed", 1.0) <= 2.0:
        e.append("voice needs voice_id and speed 0.5-2.0")
    t = p.get("targets") or {}
    for k in ("duration", "scenes"):
        a = t.get(k)
        if not (isinstance(a, list) and len(a) == 2 and 0 < a[0] <= a[1]):
            e.append(f"targets.{k} must be [min, max]")
    return e


def ensure_default():
    CH.mkdir(exist_ok=True)
    if not any(CH.glob("*.json")):
        G.write_json_atomic(CH / "default.json", DEFAULT)


def list_all():
    ensure_default()
    return [{"id": f.stem, "name": (G.read_json(f) or {}).get("name", f.stem)} for f in sorted(CH.glob("*.json"))]


def get(cid):
    ensure_default()
    if not ID_RE.match(str(cid or "")):
        raise ChannelError("bad channel id")
    f = CH / f"{cid}.json"
    if not f.exists():
        raise ChannelError(f"unknown channel {cid!r}")
    return G.read_json(f)


def save(cid, profile):
    if not ID_RE.match(str(cid or "")):
        raise ChannelError("channel id: a-z, 0-9, _ (max 40)")
    p = {**DEFAULT, **{k: v for k, v in profile.items() if k in DEFAULT}}
    errs = validate(p)
    if errs:
        raise ChannelError("; ".join(errs))
    CH.mkdir(exist_ok=True)
    G.write_json_atomic(CH / f"{cid}.json", p)
    return p


def fingerprint(profile):
    return hashlib.sha256(json.dumps(profile, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()[:16]
