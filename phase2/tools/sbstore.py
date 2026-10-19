"""Storyboard persistence shared by the UI server, the AI steps and the CLI: validate a storyboard object (without touching the project),
save it as a new version (previous file kept in versions/), and apply a voice edit with automatic cue/subtitle realignment."""
import hashlib
import json
import shutil
import tempfile
import time
from pathlib import Path

import realign


class SaveError(ValueError):
    def __init__(self, msg, errors=(), warnings=()):
        super().__init__(msg)
        self.errors, self.warnings = list(errors), list(warnings)


def sha_file(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def validate_obj(proj, sb, draft_chars=True):
    """-> (errors, warnings) of a storyboard object, with the project's AI assets visible (no file of the project is touched)."""
    import validate_storyboard
    tmp = Path(tempfile.mkdtemp(prefix="af_val_"))
    try:
        (tmp / "storyboard.json").write_text(json.dumps(sb, ensure_ascii=False), encoding="utf-8")
        if (Path(proj) / "ai_assets").exists():
            shutil.copytree(Path(proj) / "ai_assets", tmp / "ai_assets", ignore=shutil.ignore_patterns("source", "logs", "_work", "jobs", "versions"))
        if (Path(proj) / "characters").exists():
            shutil.copytree(Path(proj) / "characters", tmp / "characters", ignore=shutil.ignore_patterns("png"))
        return validate_storyboard.validate(tmp, draft_chars=draft_chars)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def save(proj, sb_obj, note="ui"):
    """Validate; keep the previous file; bump the version when the content changed; write. Raises SaveError with the validator's errors."""
    proj = Path(proj)
    old_text = (proj / "storyboard.json").read_text(encoding="utf-8")
    errors, warnings = validate_obj(proj, sb_obj)
    if errors:
        raise SaveError("storyboard has errors; nothing was saved", errors, warnings)
    old = json.loads(old_text)
    changed = json.dumps(old, sort_keys=True, ensure_ascii=False) != json.dumps(sb_obj, sort_keys=True, ensure_ascii=False)
    if changed:
        (proj / "versions").mkdir(exist_ok=True)
        (proj / "versions" / f"storyboard_v{old.get('version', 0)}_before_{note}_{time.strftime('%Y%m%d_%H%M%S')}.json").write_text(old_text, encoding="utf-8")
        sb_obj["version"] = int(old.get("version", 0)) + 1
        (proj / "storyboard.json").write_text(json.dumps(sb_obj, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"changed": changed, "version": sb_obj.get("version"), "hash": sha_file(proj / "storyboard.json"), "warnings": warnings}


def review_file(proj):
    return Path(proj) / "prepare" / "cue_review.json"


def review_list(proj):
    import agy_image as G
    return G.read_json(review_file(proj), {}) or {}


def review_add(proj, scene_id, changes):
    """Remember realignments that are NOT exact (proposed / approx): the owner has to look at them (todo item) before approving the storyboard."""
    import agy_image as G
    weak = [c for c in changes if c.get("kind") in ("proposed", "approx")]
    if not weak:
        return
    rv = review_list(proj)
    rv[scene_id] = {"at": time.strftime("%Y-%m-%d %H:%M:%S"), "changes": weak}
    review_file(proj).parent.mkdir(exist_ok=True)
    G.write_json_atomic(review_file(proj), rv)


def review_clear(proj, scene_id):
    import agy_image as G
    rv = review_list(proj)
    if scene_id in rv:
        del rv[scene_id]
        G.write_json_atomic(review_file(proj), rv)


def edit_voice(proj, scene_id, text):
    """Replace one scene's spoken text. Cue/appear phrases and subtitles are realigned automatically (realign.py); the result is validated
    and saved as a new version. -> {saved info..., "realigned": [changes]}. Raises SaveError / KeyError."""
    proj = Path(proj)
    sb = json.loads((proj / "storyboard.json").read_text(encoding="utf-8"))
    sc = next((s for s in sb["scenes"] if s["id"] == scene_id), None)
    if sc is None:
        raise KeyError(f"unknown scene {scene_id}")
    text = " ".join(str(text).split())
    if len(text) < 3:
        raise SaveError("voice text is too short")
    new, changes = realign.realign(sc, text)
    new["subtitles"] = "auto"                                         # always re-derived from the new text
    sc.clear()
    sc.update(new)
    out = save(proj, sb, f"voice_{scene_id}")
    review_add(proj, scene_id, changes)
    out["realigned"] = changes
    return out


def scene_diff(before, after, path=""):
    """Human-readable field differences between two scene dicts: [{path, before, after}]."""
    out = []
    if isinstance(before, dict) and isinstance(after, dict):
        for k in sorted(set(before) | set(after)):
            out += scene_diff(before.get(k), after.get(k), f"{path}.{k}" if path else k)
    elif isinstance(before, list) and isinstance(after, list) and len(before) == len(after):
        for i, (x, y) in enumerate(zip(before, after)):
            out += scene_diff(x, y, f"{path}[{i}]")
    elif json.dumps(before, sort_keys=True, ensure_ascii=False) != json.dumps(after, sort_keys=True, ensure_ascii=False):
        out.append({"path": path, "before": before, "after": after})
    return out
