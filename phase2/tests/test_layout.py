"""Layout check: nominal sizes match the library images, partial overlaps and off-canvas items are reported, layered items and clean scenes are not."""
import json
import sys
import unittest
from pathlib import Path

from PIL import Image

P2 = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(P2 / "tools"))
import layout  # noqa: E402


class T(unittest.TestCase):
    def test_nominal_sizes_match_the_real_library_images(self):
        png = next((d for d in sorted((P2 / "projects").glob("*/assets/png")) if (d / "bill.png").exists()), None)
        self.assertIsNotNone(png, "no project with library images to measure against")
        for name, (w, h) in layout.PROP_SIZE.items():
            f = png / f"{name}.png"
            if f.exists():
                with Image.open(f) as im:
                    self.assertEqual(tuple(x // 2 for x in im.size), (w, h), name)

    def sc(self, items):
        return {"id": "s1", "bi": {"x": 500, "y": 930, "scale": 1.05}, "items": items}

    def test_partial_overlap_is_reported_layering_is_not(self):
        bad = layout.check_scene(self.sc([{"type": "prop", "img": "bill", "x": 1300, "y": 500, "scale": 1.0}, {"type": "text", "text": "Lãi suất vay = ?", "x": 1300, "y": 330, "size": 60}]))
        self.assertTrue(any("overlap partly" in w for w in bad), bad)
        ok = layout.check_scene(self.sc([{"type": "prop", "img": "board", "x": 1400, "y": 540, "scale": 1.0}, {"type": "text", "text": "Ví dụ", "x": 1400, "y": 320, "size": 56},
                                         {"type": "legend", "x": 1470, "y": 440, "gap": 110, "size": 40, "rows": [{"color": "teal", "text": "Thiết yếu", "appear": 0.5}]}]))
        self.assertEqual(ok, [], "text and a legend placed on a board are intentional layering")

    def test_off_canvas_and_character_overlap(self):
        w = layout.check_scene(self.sc([{"type": "prop", "img": "bill", "x": 1800, "y": 500, "scale": 1.0}]))
        self.assertTrue(any("outside" in x for x in w), w)
        w = layout.check_scene(self.sc([{"type": "prop", "img": "bill", "x": 600, "y": 700, "scale": 1.0}]))
        self.assertTrue(any("Bi" in x for x in w), w)

    def test_applied_asset_is_moved_off_whatever_it_would_overlap(self):
        import tempfile

        import prepare
        sc = self.sc([{"type": "prop", "img": "bill", "x": 1450, "y": 540, "scale": 1.0}])
        item = {"type": "prop", "img": "ai:thing", "x": 1650, "y": 540, "scale": 1.0, "appear": 0.3}
        sc["items"].append(item)
        self.assertTrue(layout.check_scene(sc), "at the planned spot it overlaps the bill")
        self.assertTrue(prepare._free_spot(Path(tempfile.mkdtemp()), sc, item))
        self.assertEqual(layout.check_scene(sc), [])
        self.assertNotEqual((item["x"], item["y"]), (1650, 540))

    def test_hand_made_samples_stay_clean_where_they_were(self):
        for p in ("video2_quy_khan_cap", "ui_demo"):
            sb = json.loads((P2 / "projects" / p / "storyboard.json").read_text(encoding="utf-8"))
            self.assertEqual(layout.check(sb, P2 / "projects" / p), [], p)


if __name__ == "__main__":
    unittest.main()
