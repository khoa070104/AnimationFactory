"""(1) the validator must catch authoring mistakes BEFORE any paid call;
(2) shared tool code must not contain video-specific content (every phrase of every project's storyboard is searched in the tools)."""
import copy
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

P2 = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(P2 / "tools"))
import sbload  # noqa: E402
import validate_storyboard as V  # noqa: E402

BASE = json.loads((P2 / "projects/video2_quy_khan_cap/storyboard.json").read_text(encoding="utf-8"))


def errors_for(mut):
    sb = copy.deepcopy(BASE)
    mut(sb)
    d = Path(tempfile.mkdtemp())
    (d / "storyboard.json").write_text(json.dumps(sb, ensure_ascii=False), encoding="utf-8")
    src = P2 / "projects/video2_quy_khan_cap/ai_assets"                      # the fixture's AI assets (manifest + PNGs) travel with it
    if src.exists():
        (d / "ai_assets").mkdir()
        for f in [src / "manifest.json", *src.glob("*.png")]:
            shutil.copy(f, d / "ai_assets" / f.name)
    return V.validate(d)


class Validator(unittest.TestCase):
    def test_clean_project_passes(self):
        e, _ = errors_for(lambda sb: None)
        self.assertEqual(e, [])

    def test_cue_not_in_voice_text(self):
        e, _ = errors_for(lambda sb: sb["scenes"][0]["actions"][0].update(cue="không có trong lời"))
        self.assertTrue(any("does not occur" in x for x in e))

    def test_unknown_action_pose_face_prop_colour_bg(self):
        def mut(sb):
            s = sb["scenes"][0]
            s["actions"][0]["name"] = "moonwalk"
            s["bi"]["pose"] = "flying"
            s["bi"]["face"] = "angry"
            s["items"][2]["img"] = "rocket"
            s["bg"] = "purple"
        e, _ = errors_for(mut)
        for word in ("moonwalk", "flying", "angry", "rocket", "purple"):
            self.assertTrue(any(word in x for x in e), word)

    def test_subtitle_must_follow_voice_text_and_be_short(self):
        e, _ = errors_for(lambda sb: sb["scenes"][0]["subtitles"].__setitem__(1, "một câu khác hẳn"))
        self.assertTrue(any("not the next words" in x for x in e))
        e, _ = errors_for(lambda sb: sb["scenes"][0].update(subtitles=[sb["scenes"][0]["voice"]]))
        self.assertTrue(any("too long" in x for x in e))

    def test_duplicate_scene_ids_and_unknown_item_type(self):
        e, _ = errors_for(lambda sb: sb["scenes"][1].update(id="s01"))
        self.assertTrue(any("duplicate" in x for x in e))
        e, _ = errors_for(lambda sb: sb["scenes"][0]["items"].append({"type": "hologram"}))
        self.assertTrue(any("hologram" in x for x in e))


class MinimalStoryboard(unittest.TestCase):
    def test_docs_do_not_require_optional_metadata(self):
        import build_storyboard as SBD
        sb = {"project": "m", "title": "T", "version": 1, "voice": {"voice_id": "v", "speed": 1.0},
              "scenes": [{"id": "s01", "title": "A", "voice": "Một câu.", "bg": "cream", "bi": {"x": 1, "y": 1, "scale": 1, "face": "happy", "pose": "idle"}, "items": []}]}
        import sbload
        sb = sbload.normalise(sb)
        d = Path(tempfile.mkdtemp())
        SBD.make_docs(d, sb, SBD.stats(sb), {"chars": 8, "sec": 1.0, "credits": 6})
        self.assertTrue((d / "storyboard.md").exists())


class Generality(unittest.TestCase):
    def test_no_project_content_in_shared_code(self):
        phrases = set()
        for sbf in (P2 / "projects").glob("*/storyboard.json"):
            sb = sbload.load_storyboard(sbf)
            for sc in sb["scenes"]:
                phrases.add(sc["voice"][:30])
                phrases.update(sc["subtitles"])
                phrases.add(sc["title"])
                for it in sc["items"]:
                    for k in ("text", "title", "caption", "amount", "head"):
                        if isinstance(it.get(k), str):
                            phrases.add(it[k])
                    for r in it.get("rows", []) + it.get("bars", []):
                        phrases.add(r.get("text", ""))
                    phrases.update(it.get("texts", []))
        phrases = {p for p in phrases if len(p) >= 8}
        shared = [f for f in (P2 / "tools").glob("*.py") if f.name not in ("build_style_frames.py", "build_motion_demo.py", "new_project.py")] + \
                 [P2 / "assets_mcp/af_assets_server.py"] + \
                 [P2 / "lib" / n for n in ("bi_rig.jsx", "bi_motion.jsx", "scene_static.jsx", "scene_anim.jsx", "sample_motion.jsx")]
        hits = [(f.name, p) for f in shared for p in phrases if p in f.read_text(encoding="utf-8")]
        self.assertEqual(hits, [], "video-specific text found in shared code")


if __name__ == "__main__":
    unittest.main(verbosity=2)
