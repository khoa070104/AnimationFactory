"""AI characters end to end: sheets (real Antigravity pictures in fixtures) -> rig -> approval state -> scenes animated by the SAME EffectCraft builder as Bi,
mixed with a supporting character, selective rebuild, asset-policy rules, bad sheets regenerated once. Real EffectCraft + FilmCraft; no paid call."""
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image

P2 = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(P2 / "tools"))
sys.path.insert(0, str(P2 / "tests"))
import agy_image as G  # noqa: E402
import approve  # noqa: E402
import budget  # noqa: E402
import char_rig  # noqa: E402
import characters as CHR  # noqa: E402
import new_project  # noqa: E402
import prepare as PR  # noqa: E402
import sbstore  # noqa: E402
from imgdouble import Dispatch, RUNNER as IMG_RUNNER, SheetAgy  # noqa: E402
from test_prepare import FakeLLM  # noqa: E402

FIX = P2 / "tests" / "fixtures"
DESC = "Mai, a young Vietnamese woman with a short black bob and a red hairpin, mustard raincoat, teal trousers, white sneakers"


class Rig(unittest.TestCase):
    def test_sheets_are_sliced_into_a_plausible_rig(self):
        tmp = Path(tempfile.mkdtemp())
        rig = char_rig.build_rig(FIX / "mai_parts_sheet.png", FIX / "mai_faces_sheet.png", tmp, "mai")
        self.assertEqual(set(rig["kinds"]), {"happy", "neutral", "worried", "surprised", "thinking"})
        self.assertEqual(char_rig.rig_problems(rig), [])
        self.assertLessEqual(rig["armScale"], 1.0)
        reach, body = rig["L1"] + rig["L2"], -rig["waistY"]
        self.assertTrue(0.55 * body <= reach <= 1.9 * body, (reach, body))
        for k in rig["kinds"]:
            self.assertTrue((tmp / "png" / f"ch_mai_face_{k}.png").exists())
        with Image.open(tmp / "png" / "ch_mai_torso.png") as im:                    # 2x display size, transparent outside the piece
            self.assertEqual(im.mode, "RGBA")
            self.assertEqual(np.asarray(im)[0, 0, 3], 0)
        shutil.rmtree(tmp, ignore_errors=True)

    def test_wrong_sheets_are_refused_with_a_reason(self):
        with self.assertRaises(char_rig.CharRigError) as e:                       # five heads where four body parts are expected
            char_rig.build_rig(FIX / "mai_faces_sheet.png", FIX / "mai_faces_sheet.png", tempfile.mkdtemp(), "x")
        self.assertIn("found 5 separate pieces, expected 4", str(e.exception))
        with self.assertRaises(char_rig.CharRigError) as e:
            char_rig.build_rig(FIX / "mai_parts_sheet.png", FIX / "mai_parts_sheet.png", tempfile.mkdtemp(), "x")
        self.assertIn("faces sheet", str(e.exception))
        blank = Path(tempfile.mkdtemp()) / "blank.png"
        Image.new("RGBA", (800, 400), (0, 0, 0, 0)).save(blank)
        with self.assertRaises(char_rig.CharRigError):
            char_rig.split_row(blank, 4, "parts sheet")


class T(unittest.TestCase):
    def setUp(self):
        self.names = []
        self.fake = FakeLLM("ok")
        PR.RUNNER = self.fake
        self.home = Path(tempfile.mkdtemp())
        (self.home / "brain").mkdir()
        os.environ["AGY_HOME"] = str(self.home)
        os.environ["AF_VOICE_CACHE"] = tempfile.mkdtemp()

    def tearDown(self):
        PR.RUNNER = PR.IMAGE_RUNNER = None
        os.environ.pop("AF_VOICE_CACHE", None)
        for n in self.names:
            shutil.rmtree(P2 / "projects" / n, ignore_errors=True)

    def project(self, **brief):
        name = f"_t_chr_{os.getpid()}_{len(self.names)}"
        d = new_project.create(name, "Nhân vật", brief={"title": brief.pop("title", "Nhân vật"), "research": "no", **brief})
        self.names.append(name)
        return d

    def with_mai(self, d, approve_it=True):
        CHR.save_profile(d, "mai", {"name": "Mai", "role": "main", "description": DESC})
        CHR.register_sheet(d, "mai_parts", "parts_sheet", FIX / "mai_parts_sheet.png")
        CHR.register_sheet(d, "mai_faces", "faces_sheet", FIX / "mai_faces_sheet.png")
        CHR.build(d, "mai")
        if approve_it:
            for a in ("mai_parts", "mai_faces"):
                G.set_status(d, a, "approved", approved_by="chủ dự án")

    def scene(self, sid, voice, char=None, cast=None):
        bi = {"x": 520, "y": 960, "scale": 1.0, "face": "neutral", "pose": "idle"}
        if char:
            bi["char"] = char
        sc = {"id": sid, "title": sid, "voice": voice, "subtitles": "auto", "bg": "cream", "transition": "cut", "bi": bi, "actions": [{"name": "enter", "at": 0.0}], "face_cues": [], "items": []}
        if cast:
            sc["cast"] = cast
        return sc

    # ------------------------------------------------------------------------------------------------------------------
    def test_character_state_follows_the_approved_pictures(self):
        d = self.project()
        self.with_mai(d, approve_it=False)
        self.assertEqual(CHR.state(d, "mai")[0], "draft")
        sb = json.loads((d / "storyboard.json").read_text(encoding="utf-8"))
        sb["scenes"] = [self.scene("s01", "Mai chào các bạn và bắt đầu câu chuyện.", "mai")]
        errs, warns = sbstore.validate_obj(d, sb, draft_chars=False)
        self.assertTrue(any("only approved characters" in e for e in errs), errs)
        errs, warns = sbstore.validate_obj(d, sb, draft_chars=True)
        self.assertEqual(errs, [])
        self.assertTrue(any("design only" in w for w in warns))
        PR.approve_character(d, "mai", "chủ dự án")
        self.assertEqual(CHR.state(d, "mai")[0], "approved")
        self.assertEqual(sbstore.validate_obj(d, sb, draft_chars=False)[0], [])
        # a different picture under the same name: the character is stale, scenes refuse it
        new = Image.open(FIX / "mai_faces_sheet.png").convert("RGBA")
        new.putpixel((5, 5), (1, 2, 3, 255))
        new.save(d / "ai_assets" / "mai_faces.png")
        self.assertIn(CHR.state(d, "mai")[0], ("draft", "stale"))
        self.assertTrue(sbstore.validate_obj(d, sb, draft_chars=False)[0])
        with self.assertRaises(PR.PrepareError):
            PR.approve_character(d, "mai", "chủ dự án")                               # cannot approve what has no rig built from these pictures
        with self.assertRaises(CHR.CharacterError):
            CHR.save_profile(d, "bi", {"description": DESC})
        self.assertEqual(sbstore.validate_obj(d, {**sb, "scenes": [self.scene("s01", "Chào các bạn nhé.", "ghost")]}, draft_chars=True)[0][0].count("missing") + 1, 2)

    def test_scene_with_ai_character_and_cast_builds_moves_and_rebuilds_selectively(self):
        d = self.project()
        self.with_mai(d)
        sb = json.loads((d / "storyboard.json").read_text(encoding="utf-8"))
        s1 = self.scene("s01", "Mai mở ví ra và thấy tiền vơi nhanh quá. Cô ấy chỉ vào hóa đơn rồi mỉm cười.", "mai",
                        cast=[{"char": "bi", "x": 1500, "y": 960, "scale": 0.9, "face": "neutral", "pose": "idle", "flip": True, "actions": [{"name": "enter", "at": 1.5}, {"name": "nod", "cue": "mỉm cười"}], "face_cues": []}])
        s1["actions"] = [{"name": "enter", "at": 0.0}, {"name": "point", "cue": "chỉ vào hóa đơn", "hold": 0.8}, {"name": "cheer", "cue": "mỉm cười", "hold": 0.6}]
        s1["face_cues"] = [{"cue": "mỉm cười", "face": "happy"}]
        s1["items"] = [{"type": "prop", "img": "wallet", "x": 1000, "y": 700, "scale": 0.9, "appear": "mở ví"}]
        s2 = self.scene("s02", "Còn Bi thì chỉ gật đầu đồng ý với kế hoạch của cả hai người.")
        s2["actions"] = [{"name": "nod", "cue": "gật đầu"}]
        sb["scenes"] = [s1, s2]
        sb["targets"] = {"duration": [5, 40], "scenes": [1, 4]}
        (d / "storyboard.json").write_text(json.dumps(sb, ensure_ascii=False, indent=2), encoding="utf-8")
        import subprocess
        env = dict(os.environ, PYTHONIOENCODING="utf-8")

        def produce(*extra):
            r = subprocess.run([sys.executable, str(P2 / "tools/produce.py"), str(d), "--draft", *extra], capture_output=True, text=True, encoding="utf-8", env=env)
            self.assertEqual(r.returncode, 0, (r.stdout + r.stderr)[-3500:])
            rep = json.loads((d / "logs/build_report.json").read_text(encoding="utf-8"))
            self.assertTrue(all(c["pass"] for c in rep["checks"]), [c for c in rep["checks"] if not c["pass"]])
            return json.loads((d / "status.json").read_text(encoding="utf-8"))["last_build"]

        lb = produce()
        self.assertTrue(lb["draft"])
        self.assertEqual(sorted(lb["rendered"]), ["s01", "s02"])
        self.assertTrue(list((d / "output").glob("*_draft.mp4")))
        # the character really moves: frames of the AI character's arm region differ over time, and its own colours are on screen
        import subprocess as sp
        import toolpaths
        EC = toolpaths.effectcraft()
        frames = {}
        for t in (0.4, 3.6):
            f = Path(tempfile.mkdtemp()) / f"f{t}.png"
            sp.run([EC, "--project", str(d / "render/scenes.ecproj"), "render-frame", "--comp", "s01", "--time", str(t), "--out", str(f)], check=True, capture_output=True)
            frames[t] = np.asarray(Image.open(f).convert("RGB")).astype(int)
        zone = frames[0.4][300:950, 1300:1750]                       # the supporting character enters at 1.5 s: before that nobody stands in her spot
        self.assertLess((np.abs(zone - frames[0.4][5, 5]).sum(axis=2) > 40).sum(), 200, "a character that has not entered yet must be off-screen, not standing at its final place")
        diff = np.abs(frames[0.4] - frames[3.6]).sum(axis=2)
        self.assertGreater((diff > 60).sum(), 4000, "the picture must change as the character walks in, points and cheers")
        mustard = ((abs(frames[3.6][:, :, 0] - 240) < 40) & (abs(frames[3.6][:, :, 1] - 180) < 40) & (frames[3.6][:, :, 2] < 110)).sum()
        self.assertGreater(mustard, 1500, "Mai's yellow raincoat (from the Antigravity picture) is drawn")
        # nothing changed: nothing re-rendered
        self.assertEqual(produce()["rendered"], [])
        # change ONE picture of the character: only the scene that uses her is rebuilt (the Bi-only scene is reused)
        png = d / "characters" / "mai" / "png" / "ch_mai_torso.png"
        im = Image.open(png).convert("RGBA")
        a = np.asarray(im).copy()
        a[:, :, 0] = np.clip(a[:, :, 0].astype(int) + 25, 0, 255)
        Image.fromarray(a, "RGBA").save(png)
        lb = produce()
        self.assertEqual(lb["rendered"], ["s01"])
        self.assertIn("s02", lb["reused"])

    def test_writing_carrying_and_a_table_build_and_pass_motion_qa(self):
        """The owner's Sample A review: the character really writes (pen + notebook in hand), carries a basket, a 7-cell menu is a grid, nobody is a chart of equal bars."""
        d = self.project()
        self.with_mai(d)
        sb = json.loads((d / "storyboard.json").read_text(encoding="utf-8"))
        cast = [{"char": "bi", "x": 1500, "y": 960, "scale": 0.9, "face": "neutral", "pose": "idle", "flip": True,
                 "actions": [{"name": "enter", "at": 0.5}, {"name": "carry", "cue": "xách giỏ", "hold": 1.2}], "face_cues": []}]
        s1 = self.scene("s01", "Mai ngồi viết thực đơn: thứ Hai trứng sốt cà, thứ Ba đậu hũ xào rau. Rồi Bi xách giỏ ra chợ mua đồ.", "mai", cast=cast)
        s1["actions"] = [{"name": "enter", "at": 0.0}, {"name": "write", "cue": "viết thực đơn", "hold": 2.0}]
        s1["holds"] = [{"who": "main", "side": "R", "prop": "pen"}, {"who": "cast1", "side": "L", "prop": "basket"}]
        s1["items"] = [{"type": "grid", "title": "Thực đơn", "x": 1400, "y": 520, "cols": 2, "cells": [
            {"label": "Thứ Hai", "text": "Trứng sốt cà", "appear": "thứ Hai trứng sốt cà"}, {"label": "Thứ Ba", "text": "Đậu hũ xào rau", "appear": "thứ Ba đậu hũ xào rau"},
            {"label": "Thứ Tư"}, {"label": "Thứ Năm"}]}]
        sb["scenes"] = [s1]
        sb["targets"] = {"duration": [3, 40], "scenes": [1, 4]}
        (d / "storyboard.json").write_text(json.dumps(sb, ensure_ascii=False, indent=2), encoding="utf-8")
        import subprocess
        env = dict(os.environ, PYTHONIOENCODING="utf-8")
        r = subprocess.run([sys.executable, str(P2 / "tools/produce.py"), str(d), "--draft"], capture_output=True, text=True, encoding="utf-8", env=env)
        self.assertEqual(r.returncode, 0, (r.stdout + r.stderr)[-3500:])
        cues = json.loads((d / "render/cue_report.json").read_text(encoding="utf-8"))
        self.assertTrue({"write", "carry"} <= {c["action"] for c in cues}, cues)
        rep = json.loads((d / "logs/build_report.json").read_text(encoding="utf-8"))
        self.assertTrue(all(c["pass"] for c in rep["checks"]), [c for c in rep["checks"] if not c["pass"]])

    def test_policy_new_never_reuses_other_projects_assets(self):
        other = self.project(title="Dự án khác")
        CHR.register_sheet(other, "shared_prop", "prop", FIX / "mai_faces_sheet.png")
        G.set_status(other, "shared_prop", "approved", approved_by="chủ dự án")
        names = {"new": [], "legacy": ["shared_prop"]}
        for pol, want in names.items():
            d = self.project(asset_policy=pol, character_mode="bi")
            got = [c["asset"] for c in PR.library_candidates(d) if c["project"] == other.name]
            self.assertEqual(got, want, pol)
        d = self.project(asset_policy="library", library_assets=[f"{other.name}/shared_prop"], character_mode="bi")
        self.assertEqual([c["asset"] for c in PR.library_candidates(d) if c["project"] == other.name], ["shared_prop"])
        d = self.project(asset_policy="series", series_from=other.name, character_mode="bi")
        self.assertEqual({c["project"] for c in PR.library_candidates(d)}, {other.name})
        with self.assertRaises(ValueError):
            new_project.normalise_brief({"title": "x", "asset_policy": "series"})

    def test_ai_pipeline_designs_cast_generates_sheets_bad_sheet_is_regenerated_once(self):
        PR.RUNNER = self.fake = FakeLLM("chars")
        d = self.project(title="Hành trình của Lan", asset_policy="new", character_mode="ai", character_hint="a young woman with a long ponytail, green jacket")
        res = PR.run_steps(d, PR.PLAN_STEPS)
        self.assertTrue(all(v == "ok" for v in res.values()), res)
        plan = PR.characters_plan(d)
        self.assertEqual([c["id"] for c in plan["characters"]], ["lan"])
        self.assertIn("long ponytail", CHR.get_profile(d, "lan")["description"], "the owner's description is kept")
        sb = json.loads((d / "storyboard.json").read_text(encoding="utf-8"))
        self.assertTrue(all(s["bi"].get("char") == "lan" for s in sb["scenes"]))
        self.assertEqual(CHR.state(d, "lan")[0], "draft")
        self.assertEqual([c["id"] for c in PR.plan_characters(d)], ["lan"])
        # nothing is drawn before the plan (which lists the character) is approved
        h = PR.plan_hash(d)
        PR.approve_plan(d, "chủ dự án")
        self.assertTrue(PR.plan_approved(d))
        CHR.save_profile(d, "lan", {**CHR.get_profile(d, "lan"), "description": CHR.get_profile(d, "lan")["description"] + " She wears glasses."})
        self.assertNotEqual(PR.plan_hash(d), h)
        self.assertFalse(PR.plan_approved(d), "editing the character withdraws the plan approval")
        PR.approve_plan(d, "chủ dự án")
        Dispatch.impl = img = SheetAgy(self.home / "brain", broken_parts=1)          # the FIRST parts sheet is a wrong picture
        PR.IMAGE_RUNNER = IMG_RUNNER
        PR.do_assets(d, poll=0.05)
        self.assertEqual(CHR.state(d, "lan")[0], "draft", "rig built from the (regenerated) sheets, waiting for the owner")
        prompts = [c for c in img.calls if "BODY-PARTS sheet" in c]
        self.assertEqual(len(prompts), 2, "wrong sheet regenerated exactly once")
        self.assertIn("rejected", prompts[1])
        rig = G.read_json(CHR.cdir(d, "lan") / "rig.json")
        self.assertEqual(rig["sources"], CHR.sheets_hashes(d, "lan"))
        n_img = len(img.calls)
        PR.approve_character(d, "lan", "chủ dự án")
        self.assertEqual(CHR.state(d, "lan")[0], "approved")
        PR.do_assets(d, poll=0.05)
        self.assertEqual(len(img.calls), n_img, "an approved character is never drawn again")
        self.assertEqual(sbstore.validate_obj(d, json.loads((d / "storyboard.json").read_text(encoding="utf-8")), draft_chars=False)[0], [])
        usage = budget.usage(d)
        self.assertEqual(usage["images"], 4)                                          # parts (bad) + parts (good) + faces + the planned prop


if __name__ == "__main__":
    unittest.main()
