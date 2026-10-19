"""`ai:<id>` prop references: only APPROVED assets are usable; validator and builder agree."""
import copy
import hashlib
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

P2 = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(P2 / "tools"))
import build_storyboard as SBD  # noqa: E402
import validate_storyboard as V  # noqa: E402
from PIL import Image  # noqa: E402


def make(status):
    d = Path(tempfile.mkdtemp()) / "p"
    (d / "ai_assets").mkdir(parents=True)
    (d / "assets/png").mkdir(parents=True)
    Image.new("RGBA", (40, 30), (255, 0, 0, 255)).save(d / "ai_assets/pig.png")
    (d / "ai_assets/manifest.json").write_text(json.dumps({"assets": {"pig": {"status": status, "file": "ai_assets/pig.png", "sha256": hashlib.sha256((d / "ai_assets/pig.png").read_bytes()).hexdigest()}}}), encoding="utf-8")
    sb = json.loads((P2 / "projects/video2_quy_khan_cap/storyboard.json").read_text(encoding="utf-8"))
    sb = copy.deepcopy(sb)
    for sc in sb["scenes"]:
        if sc["id"] == "s06":
            sc["items"] = [it for it in sc["items"] if it["type"] != "prop"]
            sc["items"].append({"type": "prop", "img": "ai:pig", "x": 1380, "y": 640, "scale": 1.0, "appear": 0.3})
    (d / "storyboard.json").write_text(json.dumps(sb, ensure_ascii=False), encoding="utf-8")
    return d, sb


class T(unittest.TestCase):
    def test_draft_asset_is_refused_by_validator_and_builder(self):
        d, sb = make("draft")
        errs, _ = V.validate(d)
        self.assertTrue(any("only approved" in e for e in errs))
        s06 = [s for s in sb["scenes"] if s["id"] == "s06"][0]
        with self.assertRaises(SystemExit):
            SBD.expand(s06, d / "assets")

    def test_unknown_asset_is_refused(self):
        d, sb = make("approved")
        for sc in sb["scenes"]:
            for it in sc["items"]:
                if it.get("img") == "ai:pig":
                    it["img"] = "ai:nope"
        (d / "storyboard.json").write_text(json.dumps(sb, ensure_ascii=False), encoding="utf-8")
        errs, _ = V.validate(d)
        self.assertTrue(any("missing" in e for e in errs))

    def test_approved_asset_passes_and_is_copied_into_project_assets(self):
        d, sb = make("approved")
        errs, _ = V.validate(d)
        self.assertEqual([e for e in errs if "AI asset" in e], [])
        s06 = [s for s in sb["scenes"] if s["id"] == "s06"][0]
        prims = SBD.expand(s06, d / "assets")
        self.assertTrue(any(p.get("img") == "ai_pig" for p in prims))
        self.assertTrue((d / "assets/png/ai_pig.png").exists())

    def test_ai_background_needs_approval_and_resolves_to_an_image(self):
        for status, ok in (("draft", False), ("approved", True)):
            d, sb = make(status)
            sb["scenes"][0]["bg"] = "ai:pig"
            (d / "storyboard.json").write_text(json.dumps(sb, ensure_ascii=False), encoding="utf-8")
            errs, _ = V.validate(d)
            self.assertEqual(any("AI background" in e for e in errs), not ok)
            if ok:
                rgb, img = SBD.bg_spec(d / "assets", "ai:pig")
                self.assertEqual(img, "ai_pig")
                self.assertEqual(len(rgb), 3)
            else:
                with self.assertRaises(SystemExit):
                    SBD.bg_spec(d / "assets", "ai:pig")

    def test_rejected_asset_is_refused(self):
        d, _ = make("rejected")
        errs, _ = V.validate(d)
        self.assertTrue(any("rejected" in e for e in errs))


if __name__ == "__main__":
    unittest.main(verbosity=2)
