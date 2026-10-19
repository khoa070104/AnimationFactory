"""Export a project (or some of its scenes) as DATA for the Remotion renderer (phase2/remotion): timing, cue-planned actions, primitives, the project's OWN rigs/pictures, fonts.
Everything that decides WHAT happens (storyboard, cues, layout, grid, holds defaults, voice timing) is reused from the existing tools; Remotion only draws it.

  python export_remotion.py PROJECT WORKDIR [--scenes s03,s05] [--draft] [--placeholder ID=RIG@PROJECT ...]

Rules (no silent substitutes):
  * every AI character of the scenes must have its own rig built from its own pictures; production needs them APPROVED, --draft allows draft characters;
  * a character may be drawn with another project's rig ONLY with --placeholder (the clip is then marked draft and the placeholders are listed in clip.json);
  * approved AI assets (backgrounds, props, held props) are copied from PROJECT/ai_assets; an unapproved one is an error, never replaced by a library picture;
  * voice: the real, up-to-date voice when it exists; with --draft the silent stub for scenes that have none. The paid voice API is never called here."""
import argparse
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import build_storyboard as SBD  # noqa: E402
from action_plan import plan_actions  # noqa: E402
import characters as CHR  # noqa: E402
import cues as C  # noqa: E402
import p2_svg as S  # noqa: E402
import sbload  # noqa: E402
import toolpaths  # noqa: E402
import voice_stub  # noqa: E402

P2 = S.P2


class ExportError(Exception):
    problems = None                                                              # structured problems (code, scene_id, shot_id, field, message, next_action) when known


def _aligned(ibox):
    """items_boxes must stay aligned with sc['items'] (item:<index>): an item without a box keeps its slot with an empty box far outside the canvas."""
    return [(a, b if b is not None else (-9999, -9999, -9998, -9998), c) for a, b, c in ibox]


def export(proj, work, scene_ids=None, draft=False, placeholders=None):
    proj, work = Path(proj), Path(work)
    placeholders = placeholders or {}
    pub = work / "public"
    sb = sbload.load_storyboard(proj)
    scenes_sb = [s for s in sb["scenes"] if not scene_ids or s["id"] in scene_ids]
    if not scenes_sb:
        raise ExportError("no such scenes")
    sb_used = {**sb, "scenes": scenes_sb}
    # ---- characters: their own approved rigs (or explicit placeholders) ----
    rigs, rig_dirs, placeheld = {}, {}, []
    for cid in [c for c in CHR.used_ids(sb_used) if c != CHR.BUILTIN]:
        if cid in placeholders:
            src = P2 / "projects" / placeholders[cid]["project"] / "characters" / placeholders[cid]["rig"]
            if not (src / "rig.json").exists():
                raise ExportError(f"placeholder rig {placeholders[cid]} does not exist")
            placeheld.append({"character": cid, **placeholders[cid]})
            rigs[cid], rig_dirs[cid] = json.loads((src / "rig.json").read_text(encoding="utf-8")), src / "png"
            continue
        stt, why = CHR.state(proj, cid)
        if stt == "missing" or not (CHR.cdir(proj, cid) / "rig.json").exists():
            raise ExportError(f"character {cid!r} has no rig built from its own pictures ({why or 'no rig'}); generate and slice its sheets, or pass --placeholder {cid}=RIG@PROJECT for a draft")
        if stt != "approved" and not draft:
            raise ExportError(f"character {cid!r} is {stt!r} ({why}); only approved characters are built into a video (--draft to review early)")
        rigs[cid], rig_dirs[cid] = CHR.load_rig(proj, cid), CHR.cdir(proj, cid) / "png"
    is_draft = bool(draft or placeholders)
    for d in ("assets", "audio", "rigs", "data", "fonts"):
        (pub / d).mkdir(parents=True, exist_ok=True)
    S.make_props(pub / "assets")
    S.make_character(pub / "assets")
    S.ensure_png("arrow_down", S.arrow_down(), pub / "assets")
    for k, v in S.A.items():
        S.ensure_png(f"sw_{k}", S.swatch(v), pub / "assets")
    ids = [s["id"] for s in scenes_sb]
    voice_state = "real"
    if is_draft:
        if voice_stub.run(proj, only=set(ids)) or any(voice_stub.is_stub(proj, i) for i in ids):
            voice_state = "stub"
    else:
        import voice_project as V
        for sc in scenes_sb:
            sg = proj / "audio" / f"{sc['id']}.sig"
            if not (sg.exists() and sg.read_text() == V.sig_of(sb, sc) and (proj / "audio" / f"{sc['id']}.mp3").exists()):
                raise ExportError(f"the real voice of {sc['id']} is missing or out of date: run the voice step first (it needs the owner's approval)")
    tm = sb.get("timing", {})
    lead, word_pad, tail = tm.get("lead", 0.15), tm.get("word_pad", 0.15), tm.get("tail", 0.3)
    scenes, t_cursor = [], 0.0
    for sc in scenes_sb:
        sid = sc["id"]
        wj = proj / "audio" / f"{sid}.words.json"
        words = C.words_of(wj)
        audio_used = round(max(w["end"] for w in words) + word_pad, 3)
        dur = round(lead + audio_used + sc.get("hold_after", tail), 3)
        T = lambda ph, _wj=wj: round(lead + C.cue_time(_wj, ph), 3)
        prims = SBD.expand(sc, pub / "assets", proj)
        for p in prims:
            for k_ in ("appear", "until"):
                if isinstance(p.get(k_), str):
                    p[k_] = T(p[k_])
        shutil.copy(proj / "audio" / f"{sid}.mp3", pub / "audio" / f"{sid}.wav")
        seg = C.segment_times(wj, sc["subtitles"])
        subs = []
        for i, (txt, (s0, s1)) in enumerate(zip(sc["subtitles"], seg)):
            t0 = max(0.05, lead + s0 - 0.05)
            t1 = (lead + seg[i + 1][0] - 0.05) if i + 1 < len(seg) else min(lead + s1 + 0.45, dur)
            subs.append({"text": txt, "t0": round(t0, 3), "t1": round(t1, 3), "w": SBD.sub_bar(pub / "assets", txt)[1]})

        def character(who, c):
            return {"who": who, "id": c.get("char"), "rig": c.get("char") or "bi", "x": c["x"], "y": c["y"], "scale": c.get("scale", 1.0), "flip": bool(c.get("flip")), "face": c.get("face", "neutral"),
                    "pose": c.get("pose", "idle"), "actions": plan_actions(c.get("actions", []), c.get("face", "neutral"), T, sbload.held_sides(sc, who)),
                    "faceCues": [{"t": T(f["cue"]), "face": f["face"]} for f in c.get("face_cues", [])], "rest": c.get("rest")}
        chars = [character("main", {**sc["bi"], "actions": sc.get("actions", []), "face_cues": sc.get("face_cues", []), "rest": sc.get("rest")})]
        chars += [character(f"cast{i + 1}", c) for i, c in enumerate(sc.get("cast", []))]
        import layout as LAY
        import shots as SH
        ai = LAY.ai_sizes(proj)
        ibox = []
        for it_ in sc.get("items", []):
            bx = LAY.item_boxes({"items": [it_]}, ai)
            ibox.append((bx[0][0], bx[0][1], it_) if bx else ("?", None, it_))
        rh = {cid: r_.get("height", 540) for cid, r_ in rigs.items()}
        rh[None] = 420                                                          # Bi, the built-in character
        try:
            res = SH.resolve(sc, dur, T, rh, _aligned(ibox))
        except SH.ShotError as e_:
            err = ExportError(f"{sc['id']}: {e_}")
            err.problems = [{**p_, "scene_id": sc["id"]} for p_ in e_.problems]
            raise err from e_
        for ch_ in chars:
            ch_["looks"] = res["looks"].get(ch_["who"], [])
        hides = {}                                                              # prim item index -> [[t0, t1]] windows where it is hidden (focus isolation)
        pn = sc.get("panel")
        panel_screen = any(p_.get("item") == "panel" and p_.get("space") == "screen" for p_ in prims)
        for s_ in res["shots"]:
            vx0, vy0, vx1, vy1 = s_["view"]
            hit = lambda b: b and not (b[2] <= vx0 or b[0] >= vx1 or b[3] <= vy0 or b[1] >= vy1)
            for n_, (lab_, b_, it_) in enumerate(ibox):
                if s_["id"] in (it_.get("hide_in") or []):                       # the data asks for this item to be hidden in this shot (any kind of item)
                    hides.setdefault(n_, []).append([s_["t0"], s_["t1"]])
                    continue
                if not s_["zoomed"] or it_.get("keep") or it_.get("space", "world") == "screen":      # isolation only touches world items the data did not pin
                    continue
                if it_.get("type") in LAY.CONTENT and n_ != s_["focus_item"] and hit(b_):
                    hides.setdefault(n_, []).append([s_["t0"], s_["t1"]])
            if s_["zoomed"] and pn and not panel_screen and s_["focus_item"] is None and hit(tuple(pn)):
                hides.setdefault("panel", []).append([s_["t0"], s_["t1"]])
        for s_ in res["shots"]:                                                  # a shot about a picture/graphic: characters that would be cut off at its edge are faded out too
            if s_["zoomed"] and s_["focus_item"] is not None:
                vx0, vy0, vx1, vy1 = s_["view"]
                for ch_ in chars:
                    src_ = sc["bi"] if ch_["who"] == "main" else (sc.get("cast") or [{}] * 9)[int(ch_["who"][4:]) - 1]
                    if src_.get("keep"):
                        continue
                    bx = SH.char_box({"x": ch_["x"], "y": ch_["y"], "scale": ch_["scale"]}, rh.get(ch_["id"], 540))
                    if not (bx[2] <= vx0 or bx[0] >= vx1 or bx[3] <= vy0 or bx[1] >= vy1):
                        ch_.setdefault("hide", []).append([s_["t0"], s_["t1"]])
        for p_ in prims:
            if p_.get("item") in hides:
                p_["hide"] = hides[p_["item"]]
        bg_rgb, bg_img = SBD.bg_spec(pub / "assets", sc["bg"], proj)
        holds = [{**h, "prop": SBD.resolve_img(pub / "assets", h["prop"], proj)} for h in sc.get("holds", [])]
        scenes.append({"id": sid, "title": sc["title"], "dur": dur, "start": round(t_cursor, 3), "audio": f"audio/{sid}.wav", "bgRGB": bg_rgb, "bgImage": bg_img, "subs": subs,
                       "subtitleY": sc.get("subtitle_y", 1030), "chars": chars, "holds": holds, "prims": prims, "camera": res["camera"], "shots": res["shots"]})
        t_cursor += dur
    have = {f.stem for f in (pub / "assets" / "png").glob("*.png")}
    missing = sorted({f"{sc['id']}: {n}" for sc in scenes for n in [p["img"] for p in sc["prims"] if p["kind"] == "prop"] + [h["prop"] for h in sc["holds"]] + ([sc["bgImage"]] if sc["bgImage"] else []) if n not in have})
    if missing:                                                  # a picture that would render as a broken-image icon is an error, not a warning
        raise ExportError("pictures missing from the export (would show as broken images): " + ", ".join(missing))
    for cid, rd in rig_dirs.items():
        (pub / "rigs" / cid).mkdir(parents=True, exist_ok=True)
        for f in Path(rd).glob("*.png"):
            shutil.copy(f, pub / "rigs" / cid / f.name)
        lack = [n for n in CHR.rig_images(rigs[cid]) if not (pub / "rigs" / cid / f"{n}.png").exists()]
        if lack:
            raise ExportError(f"rig pictures of {cid!r} are missing: {lack}")
    shutil.copy(toolpaths.font_bold(), pub / "fonts" / "arialbd.ttf")
    from PIL import Image
    sizes = {}
    for f in (pub / "assets" / "png").glob("*.png"):
        with Image.open(f) as im:
            sizes[f.stem] = list(im.size)
    motion = "\n".join((P2 / "lib" / f).read_text(encoding="utf-8") for f in ("bi_rig.jsx", "bi_motion.jsx"))
    data = {"sizes": sizes, "fps": 30, "w": 1920, "h": 1080, "pngScale": S.TOK["pngScale"], "colors": SBD.COLORS, "accent": S.A, "scenes": scenes, "rigs": rigs, "motionSrc": motion,
            "total": round(t_cursor, 3), "voice": voice_state, "draft": is_draft, "placeholders": placeheld, "project": proj.name, "storyboard_version": sb.get("version")}
    (pub / "data" / "clip.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return data


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("project")
    ap.add_argument("work")
    ap.add_argument("--scenes", default="")
    ap.add_argument("--draft", action="store_true")
    ap.add_argument("--placeholder", action="append", default=[])
    a = ap.parse_args()
    ph = {}
    for r in a.placeholder:
        cid, rest = r.split("=")
        rig, pj = rest.split("@")
        ph[cid] = {"rig": rig, "project": pj}
    try:
        d = export(a.project, a.work, a.scenes.split(",") if a.scenes else None, a.draft, ph)
    except ExportError as e:
        sys.exit(f"REFUSED: {e}")
    print(f"exported {len(d['scenes'])} scenes, {d['total']} s, voice: {d['voice']}, draft: {d['draft']}")
