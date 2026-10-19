"""Create a new video project folder (own storyboard, assets, audio, logs, versions, prepare/).
Two ways:
  python new_project.py NAME --title "Tiêu đề video" [--shirt "#F26B21"]           classic: one sample scene to edit by hand
  python new_project.py NAME --title "..." --brief brief.json                       from a brief: an EMPTY storyboard; the AI steps (prepare.py / the UI) fill it
brief.json: {title, goal, message, audience, duration_seconds, references, research (auto|yes|no), script_text, channel, budget{llm_calls,llm_tokens,images,voice_credits}, notes}"""
import argparse
import json
import re
import sys
from pathlib import Path

P2 = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).parent))
TEMPLATE = {
    "project": None, "title": None, "version": 1, "status": "draft - chờ duyệt nội dung", "audience": "", "message": "",
    "voice": {"provider": "edge", "voice_id": "edge_vi-VN-HoaiMyNeural", "speed": 1.0},
    "timing": {"lead": 0.15, "tail": 0.3, "word_pad": 0.15},
    "export": {"fade_out": 0.4},
    "character": {"shirt": "#F26B21"},
    "review_points": ["Nội dung và thứ tự các cảnh.", "Lời đọc từng cảnh (đây là văn bản sẽ gửi API).", "Số liệu minh họa.", "Giọng đọc."],
    "scenes": [{
        "id": "s01", "title": "Cảnh mở đầu",
        "voice": "Đây là câu thoại mẫu của cảnh một.",
        "subtitles": ["Đây là câu thoại mẫu của cảnh một."],
        "bg": "cream", "transition": "cut",
        "bi": {"x": 500, "y": 930, "scale": 1.05, "face": "happy", "pose": "idle"},
        "actions": [{"name": "enter", "at": 0.0}],
        "face_cues": [],
        "items": [{"type": "text", "text": "Chữ trên màn hình", "x": 1380, "y": 500, "size": 64, "color": "dark", "appear": "câu thoại"}]
    }]
}
BRIEF_KEYS = ("renderer", "scene_count", "title", "goal", "message", "audience", "duration_seconds", "references", "research", "script_text", "channel", "budget", "notes",
              "story_guideline", "character_mode", "character_hint", "asset_policy", "series_from", "library_assets")
# asset_policy: new (default for new projects: every picture is made for this project) | series (reuse characters+assets of `series_from`, same versions)
#               | library (only the assets listed in `library_assets`: "project/asset_id", copied as drafts) | legacy (older projects: reuse approved assets freely)
# character_mode: ai (the AI designs the cast, or builds the character you describe in character_hint) | bi (the built-in hand-drawn Bi)
ASSET_POLICIES = ("new", "series", "library", "legacy")


def normalise_brief(b, title="", defaults=None):
    """defaults: values for keys the brief does not have yet (new project: policy new / characters ai; an older brief keeps legacy / bi)."""
    defaults = defaults or {"asset_policy": "new", "character_mode": "ai"}
    out = {k: (b.get(k) if b.get(k) is not None else "") for k in BRIEF_KEYS}      # JSON null = empty
    out["title"] = str(out["title"] or title).strip()
    out["research"] = out["research"] if out["research"] in ("auto", "yes", "no") else "auto"
    out["channel"] = out["channel"] or "default"
    for k, v in defaults.items():
        out[k] = out[k] or v
    if out["asset_policy"] not in ASSET_POLICIES:
        raise ValueError(f"asset_policy must be one of {ASSET_POLICIES}")
    if out["character_mode"] not in ("ai", "bi"):
        raise ValueError("character_mode must be ai or bi")
    if out["asset_policy"] == "series" and not str(out["series_from"]).strip():
        raise ValueError("asset_policy 'series' needs series_from (the project to continue)")
    lib = out["library_assets"]
    out["library_assets"] = [x.strip() for x in (lib.split("\n") if isinstance(lib, str) else lib or []) if str(x).strip()]
    if out["duration_seconds"] in ("", None):
        out["duration_seconds"] = None
    else:
        out["duration_seconds"] = int(out["duration_seconds"])
        if not 20 <= out["duration_seconds"] <= 300:
            raise ValueError("duration_seconds must be 20-300")
    bud = out["budget"] if isinstance(out["budget"], dict) else {}
    out["budget"] = {k: (float(v) if k == "voice_credits" else int(v)) for k, v in bud.items() if k in ("llm_calls", "llm_tokens", "images", "voice_credits") and v not in ("", None)}
    return out


def create(name, title, shirt=None, brief=None):
    if not re.fullmatch(r"[a-z0-9_]+", name):
        raise ValueError("project name: lowercase letters, digits, underscore")
    d = P2 / "projects" / name
    if d.exists():
        raise FileExistsError(f"{d} already exists (not overwritten)")
    for sub in ("assets", "audio", "logs", "versions", "previews", "render", "output", "work", "prepare"):
        (d / sub).mkdir(parents=True)
    sb = json.loads(json.dumps(TEMPLATE))
    sb["project"], sb["title"] = name, title
    if shirt:
        sb["character"]["shirt"] = shirt
    state = "draft"
    if brief is not None:
        import channel as CH
        b = normalise_brief(brief, title)
        ch = CH.get(b["channel"])
        sb.update({"status": "chưa có kịch bản - chờ AI chuẩn bị", "audience": b["audience"] or ch["audience"], "message": b["message"], "scenes": [],
                   "voice": {"provider": "edge", "voice_id": ch["voice"]["voice_id"], "speed": float(ch["voice"]["speed"])},
                   "character": {"shirt": ch["character"]["shirt"]}, "targets": ch["targets"]})
        (d / "brief.json").write_text(json.dumps(b, ensure_ascii=False, indent=2), encoding="utf-8")
        state = "brief"
    (d / "storyboard.json").write_text(json.dumps(sb, ensure_ascii=False, indent=2), encoding="utf-8")
    (d / "status.json").write_text(json.dumps({"project": name, "storyboard_version": 1, "state": state, "approved": {}, "voice_generated": False,
                                                "api_calls": 0, "credits_spent": 0}, indent=2), encoding="utf-8")
    return d


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("name")
    ap.add_argument("--title", required=True)
    ap.add_argument("--shirt")
    ap.add_argument("--brief", help="brief.json: create an empty project for the AI steps")
    a = ap.parse_args()
    try:
        d = create(a.name, a.title, a.shirt, json.loads(Path(a.brief).read_text(encoding="utf-8")) if a.brief else None)
    except (ValueError, FileExistsError) as e:
        sys.exit(str(e))
    print(f"created {d}\nnext: " + ("python tools/prepare.py " + str(d) if a.brief else f"edit storyboard.json, then  python tools/produce.py projects/{a.name} --until storyboard"))
