"""The Remotion renderer inside the production flow: gates (own approved rigs, no silent substitutes), the same QA report as the Craft build, produce.py --renderer,
and incremental rendering (nothing changed -> nothing rendered; one scene's data or one cast member's picture changed -> only that scene). Real Remotion; no paid call."""
import json
import os
import shutil
import subprocess
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
import characters as CHR  # noqa: E402
import export_remotion as X  # noqa: E402
import test_characters as TC  # noqa: E402

HAVE = (P2 / "remotion" / "node_modules" / ".bin").exists() and shutil.which("node") and shutil.which("ffmpeg")


@unittest.skipUnless(HAVE, "Remotion is not installed (phase2/remotion: npm install)")
class T(unittest.TestCase):
    setUp, tearDown, project, with_mai, scene = TC.T.setUp, TC.T.tearDown, TC.T.project, TC.T.with_mai, TC.T.scene

    def story(self, d):
        sb = json.loads((d / "storyboard.json").read_text(encoding="utf-8"))
        cast = [{"char": "bi", "x": 1500, "y": 960, "scale": 0.9, "face": "neutral", "pose": "idle", "flip": True,
                 "actions": [{"name": "enter", "at": 0.5}, {"name": "carry", "cue": "xách giỏ", "hold": 1.0}], "face_cues": []}]
        s1 = self.scene("s01", "Mai ngồi viết thực đơn rồi Bi xách giỏ ra chợ mua đồ ăn.", "mai", cast=cast)
        s1["actions"] = [{"name": "enter", "at": 0.0}, {"name": "write", "cue": "viết thực đơn", "hold": 1.5}]
        s1["holds"] = [{"who": "main", "side": "R", "prop": "pen"}, {"who": "main", "side": "L", "prop": "notebook"}, {"who": "cast1", "side": "L", "prop": "basket"}]
        s1["items"] = [{"type": "grid", "title": "Thực đơn", "x": 1100, "y": 520, "cols": 1, "cells": [{"label": "Thứ Hai", "text": "Trứng sốt cà", "appear": "viết thực đơn"}]}]
        s1["items"].append({"type": "legend", "x": 1100, "y": 700, "gap": 70, "size": 40, "rows": [{"text": "Một mục", "color": "blue"}]})   # swatches must be in the export (they were missing: broken-image icons)
        s2 = self.scene("s02", "Còn Bi thì chỉ gật đầu đồng ý với kế hoạch của cả hai người.")
        s2["actions"] = [{"name": "nod", "cue": "gật đầu"}]
        sb["scenes"] = [s1, s2]
        sb["targets"] = {"duration": [5, 40], "scenes": [1, 4]}
        (d / "storyboard.json").write_text(json.dumps(sb, ensure_ascii=False, indent=2), encoding="utf-8")

    def produce(self, d, *extra):
        r = subprocess.run([sys.executable, str(P2 / "tools/produce.py"), str(d), "--draft", "--renderer", "remotion", *extra], capture_output=True, text=True, encoding="utf-8",
                           env=dict(os.environ, PYTHONIOENCODING="utf-8"))
        self.assertEqual(r.returncode, 0, (r.stdout + r.stderr)[-3500:])
        rep = json.loads((d / "logs/build_report.json").read_text(encoding="utf-8"))
        self.assertEqual(rep["renderer"], "remotion")
        self.assertTrue(all(c["pass"] for c in rep["checks"]), [c for c in rep["checks"] if not c["pass"]])
        return json.loads((d / "status.json").read_text(encoding="utf-8"))["last_build"]

    def test_cache_signature_covers_every_input(self):
        """phase2/remotion/tests/sig.test.mjs: cast rig data, fps, size, png scale, colours, font, audio, code... all change the signature; an unused picture does not."""
        r = subprocess.run(["node", "--test", str(P2 / "remotion" / "tests" / "sig.test.mjs"), str(P2 / "remotion" / "tests" / "camera.test.mjs")], capture_output=True, text=True, encoding="utf-8", env=dict(os.environ, NODE_NO_WARNINGS="1"))
        self.assertEqual(r.returncode, 0, (r.stdout + r.stderr)[-2500:])

    def test_shots_move_the_camera_not_the_subtitles_and_characters_keep_their_pose(self):
        """Camera on the world layer: close-up on Mai makes her bigger while the subtitle bar stays where it is; a compare + highlight explain with the data."""
        d = self.project()
        self.with_mai(d)
        sb = json.loads((d / "storyboard.json").read_text(encoding="utf-8"))
        s1 = self.scene("s01", "Mai nhìn bảng so sánh rồi chỉ vào cột cao hơn và mỉm cười thật tươi.", "mai")
        s1["actions"] = [{"name": "enter", "at": 0.0}, {"name": "point", "cue": "chỉ vào cột", "hold": 1.0}]
        s1["items"] = [{"type": "compare", "title": "Hai cách", "x": 1300, "y": 480, "unit": "p", "left": {"label": "Cũ", "value": 40, "color": "red"}, "right": {"label": "Mới", "value": 15, "color": "green"}},
                       {"type": "highlight", "x": 1430, "y": 600, "w": 200, "h": 120, "color": "yellow"}]
        s1["shots"] = [{"id": "sh1", "start": 0, "kind": "wide", "purpose": "show the room and the table"},
                       {"id": "sh2", "start": "mỉm cười", "kind": "reaction", "size": "close", "focus": "main", "purpose": "her reaction", "cut": True}]
        sb["scenes"] = [s1]
        sb["targets"] = {"duration": [3, 40], "scenes": [1, 4]}
        (d / "storyboard.json").write_text(json.dumps(sb, ensure_ascii=False, indent=2), encoding="utf-8")
        lb = self.produce(d)
        clip = json.loads((d / "remotion/public/data/clip.json").read_text(encoding="utf-8"))
        cam = clip["scenes"][0]["camera"]
        self.assertTrue(cam and max(k["z"] for k in cam) > 1.3, cam)
        import subprocess as sp
        out = Path(lb["output"])
        dur = clip["scenes"][0]["dur"]
        frames = {}
        for name, t in (("wide", 1.0), ("close", dur - 0.4)):
            f = Path(tempfile.mkdtemp()) / f"{name}.png"
            sp.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", str(t), "-i", str(out), "-frames:v", "1", str(f)], check=True)
            frames[name] = np.asarray(Image.open(f).convert("RGB")).astype(int)
        mustard = lambda a: ((abs(a[:, :, 0] - 240) < 40) & (abs(a[:, :, 1] - 180) < 40) & (a[:, :, 2] < 110)).sum()
        self.assertGreater(mustard(frames["close"]), 2.2 * mustard(frames["wide"]), "the close-up shows Mai much bigger")
        for k in ("wide", "close"):                                                   # the subtitle bar is on the screen layer: same pixels in both shots
            strip = frames[k][993:999, 930:990]                                   # inside the bar, above the text line
            self.assertGreater(((strip > 225).all(axis=2)).mean(), 0.9, f"subtitle bar present, unmoved, in the {k} frame")

    def test_gates_refuse_silent_substitutes(self):
        d = self.project()
        self.with_mai(d, approve_it=False)
        self.story(d)
        with self.assertRaises(X.ExportError) as e:                                   # draft character, production build
            X.export(d, d / "remotion", draft=False)
        self.assertIn("'draft'", str(e.exception))
        sb = json.loads((d / "storyboard.json").read_text(encoding="utf-8"))
        sb["scenes"][0]["bi"]["char"] = "ghost"                                       # a character without any rig is never replaced by another picture
        (d / "storyboard.json").write_text(json.dumps(sb, ensure_ascii=False), encoding="utf-8")
        with self.assertRaises(X.ExportError) as e:
            X.export(d, d / "remotion", draft=True)
        self.assertIn("no rig built from its own pictures", str(e.exception))
        data = X.export(d, d / "remotion", draft=True, placeholders={"ghost": {"rig": "mai", "project": d.name}})   # only an explicit placeholder, and it is recorded
        self.assertTrue(data["draft"] and data["placeholders"][0]["character"] == "ghost")

    def test_produce_with_remotion_reuses_unchanged_scenes_and_notices_every_cast_change(self):
        d = self.project()
        self.with_mai(d)
        self.story(d)
        lb = self.produce(d)
        self.assertEqual(sorted(lb["rendered"]), ["s01", "s02"])
        self.assertEqual(lb["renderer"], "remotion")
        out = Path(lb["output"])
        self.assertTrue(out.exists() and out.name.endswith("_draft.mp4"))
        self.assertTrue((d / "remotion/public/assets/png/sw_blue.png").exists() and (d / "remotion/public/assets/png/arrow_down.png").exists())
        self.assertEqual(self.produce(d)["rendered"], [], "nothing changed: nothing rendered")
        # the grid cell text of s01 changes (DATA only): only s01 is rendered again
        sb = json.loads((d / "storyboard.json").read_text(encoding="utf-8"))
        sb["scenes"][0]["items"][0]["cells"][0]["text"] = "Canh rau củ"
        (d / "storyboard.json").write_text(json.dumps(sb, ensure_ascii=False), encoding="utf-8")
        self.assertEqual(self.produce(d)["rendered"], ["s01"])
        # a picture of the MAIN character changes: s01 only (s02 uses Bi)
        png = d / "characters" / "mai" / "png" / "ch_mai_torso.png"
        im = np.asarray(Image.open(png).convert("RGBA")).copy()
        im[:, :, 0] = np.clip(im[:, :, 0].astype(int) + 25, 0, 255)
        Image.fromarray(im, "RGBA").save(png)
        self.assertEqual(self.produce(d)["rendered"], ["s01"])


if __name__ == "__main__":
    unittest.main()
