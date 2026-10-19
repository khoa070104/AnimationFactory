"""Owner's Gate 1 review, turned into shared-component checks: walk-in path, list markers, cast cues realigned on a voice edit."""
import copy
import sys
import tempfile
import unittest
from pathlib import Path

P2 = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(P2 / "tools"))
import layout  # noqa: E402
import realign  # noqa: E402
import validate_storyboard as V  # noqa: E402
import p2_svg  # noqa: E402

SC = {"id": "s1", "voice": "Minh nhìn điện thoại. Chị gọi: thôi để chị chỉ mẹo.", "bi": {"char": "minh", "x": 520, "y": 960, "scale": 1.0},
      "actions": [{"name": "enter", "at": 0}],
      "cast": [{"char": "chi_lan", "x": 1500, "y": 960, "scale": 1.0, "flip": True, "actions": [{"name": "enter", "at": 3.5}, {"name": "cheer", "cue": "chị gọi"}], "face_cues": [{"cue": "chị gọi", "face": "happy"}]}],
      "items": [{"type": "prop", "img": "phone", "x": 1050, "y": 420, "scale": 1.1}]}


class T(unittest.TestCase):
    def test_walk_in_from_the_near_edge_does_not_cross_anyone(self):
        self.assertEqual([w for w in layout.check_scene(SC) if "walk-in" in w], [])

    def test_walk_in_through_another_character_is_reported(self):
        sc = copy.deepcopy(SC)
        sc["cast"][0]["x"] = 900                       # left half: it would walk in from the left, through the main character at x=520
        w = [x for x in layout.check_scene(sc) if "walk-in" in x]
        self.assertEqual(len(w), 1)
        self.assertIn("cast 1", w[0])

    def test_pills_have_a_marker_field_and_a_badge_picture(self):
        import capabilities
        self.assertIn("marker", [f[0] for f in capabilities.ITEM_FIELDS["pills"]])
        self.assertTrue(p2_svg.badge().lstrip().startswith("<svg"))

    def test_cast_cues_follow_a_voice_edit(self):
        new, changes = realign.realign(SC, "Minh nhìn điện thoại. Chị nói: thôi để chị chỉ mẹo.")
        cast = new["cast"][0]
        self.assertTrue(realign.has_phrase(new["voice"], cast["actions"][1]["cue"]))
        self.assertTrue(all(realign.has_phrase(new["voice"], f["cue"]) for f in cast["face_cues"]))
        self.assertTrue(any("cast1" in c["where"] for c in changes))


class Sample(unittest.TestCase):
    def test_emoji_are_rejected_and_stripped_and_holds_get_defaults(self):
        import sbload
        self.assertTrue(sbload.has_emoji("Mua theo cảm hứng 🛒"))
        self.assertEqual(sbload.strip_emoji("Mua 🛒 xong 🗑️"), "Mua xong")
        sb = sbload.normalise({"scenes": [{"id": "s1", "voice": "x", "holds": [{"side": "R", "prop": "pen"}, {"side": "L", "prop": "ai:nb", "who": "cast1"}]}]})
        h = sb["scenes"][0]["holds"]
        self.assertEqual(h[0]["scale"], sbload.HOLD_DEFAULTS["pen"]["scale"])
        self.assertEqual(h[1]["rot"], sbload.HOLD_DEFAULT_AI["rot"])
        for prop in ("phone", "calculator", "pen", "basket", "notebook"):                 # every library prop can be held with only {side, prop}: the picture size must always be known
            self.assertIn("scale", sbload.normalise({"scenes": [{"id": "s", "voice": "x", "holds": [{"side": "R", "prop": prop}]}]})["scenes"][0]["holds"][0], prop)

    def test_grid_takes_space_in_the_layout(self):
        sc = {"id": "s1", "bi": {"x": 520, "y": 960, "scale": 1.0}, "items": [{"type": "grid", "x": 1400, "y": 520, "cols": 2, "cells": [{"text": "a"}] * 7},
                                                                           {"type": "prop", "img": "board", "x": 1700, "y": 520, "scale": 0.6}]}
        self.assertTrue(any("grid" in w and "board" in w for w in layout.check_scene(sc)))


class Nudge(unittest.TestCase):
    def test_overlapping_items_move_to_free_spots_and_characters_never_move(self):
        sc = {"id": "s1", "bi": {"x": 520, "y": 960, "scale": 1.0}, "cast": [{"char": "bi", "x": 1500, "y": 960, "scale": 1.0, "actions": []}],
              "items": [{"type": "grid", "x": 1100, "y": 520, "cols": 2, "cells": [{"text": "a"}] * 4}, {"type": "prop", "img": "board", "x": 1700, "y": 520, "scale": 0.6},
                        {"type": "prop", "img": "coin", "x": 1000, "y": 400, "scale": 1}]}
        self.assertTrue(layout.check_scene(sc))
        chars = (sc["bi"]["x"], sc["cast"][0]["x"])
        self.assertGreater(layout.nudge(sc), 0)
        self.assertEqual(layout.check_scene(sc), [])
        self.assertEqual(chars, (sc["bi"]["x"], sc["cast"][0]["x"]))


class Review2(unittest.TestCase):
    def sb(self, items, voice="Kẻ bảy ô tương ứng bảy ngày, điền từng món.", **kw):
        sc = {"id": "s1", "title": "t", "voice": voice, "subtitles": "auto", "bg": "cream", "transition": "cut", "bi": {"x": 520, "y": 960, "scale": 1.0, "face": "neutral", "pose": "idle"},
              "actions": [], "face_cues": [], "items": items, **kw}
        return {"project": "t", "title": "t", "version": 1, "voice": {"provider": "edge", "voice_id": "x", "speed": 1.0}, "scenes": [sc]}

    def test_a_table_must_have_as_many_cells_as_the_text_counts(self):
        import sbstore
        d = Path(tempfile.mkdtemp())
        cells = lambda n: [{"label": f"Ngày {i}"} for i in range(n)]
        e, _ = sbstore.validate_obj(d, self.sb([{"type": "grid", "x": 1300, "y": 400, "cols": 1, "cells": cells(4)}]))
        self.assertTrue(any("says 'bảy'" in x and "grid has 4" in x for x in e), e)
        e, _ = sbstore.validate_obj(d, self.sb([{"type": "grid", "x": 1300, "y": 400, "cols": 1, "cells": cells(7)}]))
        self.assertFalse([x for x in e if "grid has" in x], e)

    def test_content_goes_into_a_panel_between_the_characters_and_props_stay_out_of_it(self):
        sc = {"id": "s1", "bg": "ai:kitchen", "bi": {"x": 520, "y": 960, "scale": 1.0}, "cast": [{"char": "bi", "x": 1500, "y": 960, "scale": 1.0, "actions": []}],
              "items": [{"type": "text", "text": "Tiêu đề", "x": 300, "y": 900, "size": 46}, {"type": "grid", "x": 1700, "y": 300, "cols": 2, "cells": [{"label": f"d{i}", "text": "món"} for i in range(7)]}]}
        self.assertEqual(layout.compose(sc), 2)
        x0, y0, x1, y1 = layout.zone(sc)
        for _lab, b in layout.item_boxes(sc):
            self.assertTrue(x0 - 5 <= b[0] and b[2] <= x1 + 5 and y0 - 5 <= b[1] and b[3] <= y1 + 5, (b, (x0, y0, x1, y1)))
        self.assertEqual((sc["bi"]["x"], sc["cast"][0]["x"]), (400, 1520))
        self.assertTrue(sc["panel"][0] < sc["items"][1]["x"] < sc["panel"][2])
        titles_first = [b[1] for _l, b in layout.item_boxes(sc)]
        self.assertLess(titles_first[0], titles_first[1], "the heading stays above the table")

    def test_cheer_with_a_busy_hand_raises_only_the_free_arm(self):
        import sbload
        self.assertEqual(sbload.arm_params("cheer", {"L"}), {"free": "R"})
        self.assertEqual(sbload.arm_params("cheer", {"R"}), {"free": "L"})
        self.assertEqual(sbload.arm_params("cheer", set()), {})
        self.assertEqual(sbload.arm_params("nod", {"L"}), {})
        self.assertEqual(sbload.held_sides({"holds": [{"who": "cast1", "side": "L"}, {"side": "R", "who": "main"}]}, "cast1"), {"L"})
        self.assertIn("cheer_r:", (P2 / "lib" / "bi_motion.jsx").read_text(encoding="utf-8"))


class ActionMatch(unittest.TestCase):
    def test_narration_is_matched_against_what_the_scene_can_show(self):
        import action_match as A
        self.assertEqual(A.check("Linh viết thực đơn.", [{"write"}]), [])
        self.assertTrue(any("write" in m for m in A.check("Linh viết thực đơn.", [{"nod"}])), "writing is said but not shown")
        self.assertTrue(any("mở tủ" in m for m in A.check("Tuấn mở tủ lạnh ra.", [{"nod"}])), "opening a fridge cannot be drawn")
        self.assertEqual(A.check("Tuấn mở tủ lạnh ra.", [{"nod"}], ["mở tủ lạnh"]), [], "an accepted gap is not reported again")
        self.assertEqual(A.check("Tủ lạnh nhà Tuấn gọn gàng hẳn.", [set()]), [])
        self.assertTrue(A.check("Về xếp đồ vào tủ.", [{"carry"}]))
        self.assertTrue(A.check("Cả hai ngồi vào bàn.", [set()]))


class Targets(unittest.TestCase):
    def test_scene_count_precedence_owner_then_duration_then_channel(self):
        import prepare
        ch = {"targets": {"duration": [20, 40], "scenes": [2, 3]}}
        t = prepare.targets_of({"duration_seconds": 75, "scene_count": 5}, ch)
        self.assertEqual((t["scenes"], t["scenes_source"]), ([5, 5], "brief"))
        self.assertIn("overriding the channel range [2, 3]", t["note"])
        t = prepare.targets_of({"duration_seconds": 75, "scene_count": [6, 8]}, ch)
        self.assertEqual(t["scenes"], [6, 8])
        t = prepare.targets_of({"duration_seconds": 75, "scene_count": ""}, ch)
        self.assertEqual((t["scenes"], t["scenes_source"]), ([6, 10], "duration"))
        self.assertIn("note", t)
        t = prepare.targets_of({"scene_count": ""}, ch)
        self.assertEqual((t["scenes"], t["scenes_source"]), ([2, 3], "channel"))
        self.assertNotIn("note", t)


if __name__ == "__main__":
    unittest.main()
