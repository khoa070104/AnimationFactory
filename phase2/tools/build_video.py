"""Build the animated preview of a project from data: storyboard.json + audio + word timings.
 - scene length = lead + real audio length + tail; actions / pop-ins / subtitles are placed on spoken-word times;
 - only scenes whose inputs changed are re-rendered (render/sNN.sig); unchanged scenes are reused;
 - scenes are assembled in FilmCraft (video + audio) and checked.
Usage: python build_video.py PROJECT_DIR [--force] [--only s03]"""
import argparse
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import acceptance  # noqa: E402
import approve  # noqa: E402
import build_motion_demo as B  # noqa: E402
import build_storyboard as SBD  # noqa: E402
import characters as CHR  # noqa: E402
import check_motion as CM  # noqa: E402
import cues as C  # noqa: E402
import sbload  # noqa: E402
import toolpaths  # noqa: E402
import decode_check  # noqa: E402
import p2_svg as S  # noqa: E402

FC = toolpaths.filmcraft()
TICKS = 254016000000
PEAK = {"point": 0.45, "cheer": 0.5, "cheek": 0.5, "shrug": 0.3, "hold_phone": 0.5, "nod": 0.0, "wave": 0.4, "enter": 0.0, "write": 0.5, "carry": 0.5}
P2 = S.P2


def motion_parts(text):
    """Split lib/bi_motion.jsx into: shared machinery, one source block per ACTION, one line per POSE."""
    import re
    a0 = text.index("var ACTIONS = {")
    a1 = text.index("\n};\n", a0) + 4
    p0 = text.index("var POSES = {")
    p1 = text.index("\n};\n", p0) + 4
    actions_src, poses_src = text[a0:a1], text[p0:p1]
    machinery = text.replace(actions_src, "").replace(poses_src, "")
    starts = [(m.start(), m.group(1)) for m in re.finditer(r"^  (\w+): function \(T, p\)", actions_src, re.M)]
    actions = {name: actions_src[s:(starts[i + 1][0] if i + 1 < len(starts) else len(actions_src))] for i, (s, name) in enumerate(starts)}
    poses = {m.group(1): m.group(0) for m in re.finditer(r"^  (\w+): \{.*\},?$", poses_src, re.M)}
    return machinery, actions, poses


def motion_hash(text, action_names, rest=None):
    """Cache dependency of a scene on the motion library: shared machinery + ONLY the actions and poses it uses."""
    import re
    machinery, actions, poses = motion_parts(text)
    used_actions = sorted(n for n in set(action_names) if n in actions)
    used_poses = {"idle"} | ({rest} if rest else set())
    for n in used_actions:
        used_poses |= {w for w in re.findall(r'"(\w+)"', actions[n]) if w in poses}
    return sha(machinery, *[actions[n] for n in used_actions], *[poses[n] for n in sorted(used_poses) if n in poses])


def sha(*parts):
    h = hashlib.sha1()
    for p in parts:
        h.update(p if isinstance(p, bytes) else str(p).encode("utf-8"))
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("project")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--only")
    ap.add_argument("--draft", action="store_true", help="draft build with the stub voice (voice_stub.py): no approval gate, output is marked as a draft")
    a = ap.parse_args()
    proj = Path(a.project).resolve()
    (proj / "logs").mkdir(exist_ok=True)
    (proj / "render").mkdir(exist_ok=True)
    (proj / "output").mkdir(exist_ok=True)
    logf = proj / "logs" / f"build_{time.strftime('%Y%m%d_%H%M%S')}.log"
    t_start = time.time()
    report = []

    def log(msg):
        line = f"[{time.strftime('%H:%M:%S')}] {msg}"
        print(line, flush=True)
        with logf.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")

    def check(name, ok, info=""):
        report.append({"name": name, "pass": bool(ok), "info": info})
        log(("PASS " if ok else "FAIL ") + name + (" - " + info if info else ""))

    sb = sbload.load_storyboard(proj)
    st = json.loads((proj / "status.json").read_text(encoding="utf-8"))
    if (proj / "approval.json").exists() and not a.draft:
        vc, _ = approve.changes_since_approval(proj)
        if vc:
            sys.exit(f"REFUSED: voice text changed after approval in {vc}")
    timing = sb.get("timing", {"lead": 0.3, "tail": 0.5})
    lead, tail, word_pad = timing["lead"], timing["tail"], timing.get("word_pad", 0.15)
    vchg, schg = approve.changes_since_approval(proj) if (proj / "approval.json").exists() else ([], [])
    log(f"since approval: voice text changed {vchg or '-'}; scene data/timing changed (flag for re-review) {schg or '-'}")
    assets = SBD.ensure_assets(proj, sb)
    exp_fade = sb.get("export", {}).get("fade_out", 0.4 if sb["scenes"][-1].get("transition") == "fade-out" else 0)   # export option: dissolve at the end
    rig_hash = sha(*[(P2 / "lib" / f).read_bytes() for f in ("bi_rig.jsx", "scene_anim.jsx")], (P2 / "style/tokens.json").read_bytes())
    motion_text = (P2 / "lib/bi_motion.jsx").read_text(encoding="utf-8")

    scenes, sigs = [], {}
    for sc in sb["scenes"]:
        sid = sc["id"]
        mp3, wj, sg = proj / "audio" / f"{sid}.mp3", proj / "audio" / f"{sid}.words.json", proj / "audio" / f"{sid}.sig"
        if not (mp3.exists() and wj.exists() and sg.exists()):
            sys.exit(f"voice for {sid} is missing: run voice_project.py first")
        adur = decode_check.probe_seconds(mp3)
        ws_all = C.words_of(wj)
        last_end = max(w["end"] for w in ws_all)
        audio_used = round(min(adur, last_end + word_pad), 3)          # trailing silence of the TTS file is not placed on the timeline
        hold_after = sc.get("hold_after", tail)
        dur = round(lead + audio_used + hold_after, 3)
        T = lambda ph: round(lead + C.cue_time(wj, ph), 3)
        prims = SBD.expand(sc, assets)
        for p in prims:
            if isinstance(p.get("appear"), str):
                p["appear"] = T(p["appear"])
        def plan_actions(actions, face, who="main"):
            acts_ = []
            held = sbload.held_sides(sc, who)
            for ac in actions:
                params = {k: v for k, v in ac.items() if k not in ("name", "at", "cue", "cues", "stay")}
                params.update(sbload.arm_params(ac["name"], held))
                if ac["name"] == "point":
                    params.setdefault("face", face)
                if ac["name"] == "point_seq":
                    params["times"] = [T(c) for c in ac["cues"]]
                    params.setdefault("face", face)
                    t0 = params["times"][0] - 0.45
                elif "cue" in ac:
                    t0 = max(0.0, T(ac["cue"]) - PEAK.get(ac["name"], 0.0))
                else:
                    t0 = ac.get("at", 0.0)
                acts_.append({"name": ac["name"], "T": round(t0, 3), "params": params, "stay": bool(ac.get("stay"))})
            return acts_

        acts = plan_actions(sc.get("actions", []), sc["bi"]["face"])
        cast = [{**c, "rig": c.get("char"), "actions": plan_actions(c.get("actions", []), c["face"], f"cast{ci + 1}"), "face_cues": [{"t": T(f["cue"]), "face": f["face"]} for f in c.get("face_cues", [])]}
                for ci, c in enumerate(sc.get("cast", []))]
        subs = []
        seg = C.segment_times(wj, sc["subtitles"])
        for i, (txt, (s0, s1)) in enumerate(zip(sc["subtitles"], seg)):
            t0 = max(0.05, lead + s0 - 0.05)
            t1 = (lead + seg[i + 1][0] - 0.05) if i + 1 < len(seg) else min(lead + s1 + 0.45, dur)
            subs.append({"text": txt, "t0": round(t0, 3), "t1": round(t1, 3), "bar": SBD.sub_bar(assets, txt)[0]})
        data = {"id": sid, "dur": dur, "bg": sc["bg"], "bi": {**sc["bi"], "rig": sc["bi"].get("char")}, "cast": cast, "holds": [{**h, "prop": SBD.resolve_img(assets, h["prop"])} for h in sc.get("holds", [])], "rest": sc.get("rest"), "prims": prims, "actions": acts,
                "face_cues": [{"t": T(f["cue"]), "face": f["face"]} for f in sc.get("face_cues", [])], "subs": subs,
                "subtitleY": sc.get("subtitle_y", 1030), "audio_dur": adur, "audio_used": audio_used,
                "first_word": C.words_of(wj)[0]["start"], "last_end": last_end,
                "camera": sbload.resolve_camera(sc.get("camera")), "fade_out": exp_fade if sc is sb["scenes"][-1] else 0, "bgRGB": SBD.bg_spec(assets, sc["bg"])[0], "bgImage": SBD.bg_spec(assets, sc["bg"])[1]}
        scenes.append(data)
    CHAR_PARTS = ["head", "torso", "arm_upper", "arm_lower", "leg", "shadow"] + [f"face_{k}" for k in S.FACES]
    rigs = CHR.rigs_for(proj, sb)
    for cid in rigs:
        stt, why = CHR.state(proj, cid)
        if stt != "approved" and not (a.draft and stt in ("draft", "stale")):
            sys.exit(f"REFUSED: character {cid!r} is {stt!r} ({why}); only approved characters are built into a video (use --draft to review motion early)")

    def scene_assets_hash(sc_data):
        """Hash of exactly the images this scene uses (its characters' parts included), so adding/changing an image elsewhere does not invalidate it."""
        chars = [sc_data["bi"].get("rig")] + [c.get("rig") for c in sc_data.get("cast", [])]
        extra = set()
        for cid in chars:
            if cid in rigs:
                extra |= set(CHR.rig_images(rigs[cid]))
        names = (set(CHAR_PARTS) if any(c is None for c in chars) else set()) | extra | {p["img"] for p in sc_data["prims"] if p["kind"] == "prop"} | {h["prop"] for h in sc_data["holds"]} | {x["bar"] for x in sc_data["subs"]} | ({sc_data["bgImage"]} if sc_data.get("bgImage") else set())
        return sha(*[(assets / "png" / f"{n}.png").read_bytes() for n in sorted(names)])

    for s in scenes:
        sigs[s["id"]] = sha(json.dumps(s, ensure_ascii=False, sort_keys=True), (proj / "audio" / f"{s['id']}.mp3").read_bytes(),
                            (proj / "audio" / f"{s['id']}.words.json").read_bytes(), rig_hash, motion_hash(motion_text, [a['name'] for a in s['actions']], s.get('rest')),
                            scene_assets_hash(s), json.dumps([rigs[c] for c in sorted({s["bi"].get("rig")} | {x.get("rig") for x in s.get("cast", [])} - {None}) if c in rigs], sort_keys=True))
    log(f"scenes resolved: {len(scenes)}; total audio {sum(s['audio_dur'] for s in scenes):.1f}s")

    # ---- EffectCraft: one project with every scene (cheap), render only changed scenes ----
    pr = B.params(proj / "render/scenes.ecproj")
    pr.update({"assets": str(assets).replace("\\", "/"), "scenes": scenes, "colors": {k: v for k, v in SBD.COLORS.items()}, "rigs": rigs})
    jsx = proj / "render/_scenes.jsx"
    jsx.write_text("var P = " + json.dumps(pr, ensure_ascii=False) + ";\n" + B.jsx_text("bi_rig.jsx", "bi_motion.jsx", "scene_anim.jsx"), encoding="utf-8")
    Path(pr["out"]).unlink(missing_ok=True)
    t0 = time.time()
    script_out = B.run_script(jsx)
    cue_rows = []
    for line in script_out.splitlines():
        if line.startswith("CUE "):
            _, lab, name, planned, actual = line.split()
            cue_rows.append({"who": lab, "action": name, "planned": float(planned), "actual": float(actual)})
    (proj / "render" / "cue_report.json").write_text(json.dumps(cue_rows, indent=1), encoding="utf-8")
    log(f"EffectCraft project built ({time.time() - t0:.1f}s)")
    rendered, reused = [], []
    for s in scenes:
        sid = s["id"]
        mp4, sgf = proj / "render" / f"{sid}.mp4", proj / "render" / f"{sid}.sig"
        need = a.force or not mp4.exists() or not sgf.exists() or sgf.read_text() != sigs[sid] or (a.only and a.only == sid)
        if not need:
            reused.append(sid)
            log(f"REUSE {sid}: inputs unchanged, clip not re-rendered")
            continue
        t0 = time.time()
        sgf.unlink(missing_ok=True)
        r = subprocess.run([B.EC, "--project", pr["out"], "render", "--comp", sid, "--out", str(mp4), "--format", "h264", "--audio", "off"], capture_output=True, text=True, encoding="utf-8")
        if r.returncode:
            sys.exit(f"render failed for {sid}: {r.stderr[-500:]}")
        sgf.write_text(sigs[sid])
        rendered.append(sid)
        log(f"RENDER {sid} ({time.time() - t0:.1f}s)")

    # ---- FilmCraft: assemble ----
    film = proj / "render/film.fcproj"
    film.unlink(missing_ok=True)
    mp4s = [proj / "render" / f"{s['id']}.mp4" for s in scenes]
    mp3s = [proj / "audio" / f"{s['id']}.mp3" for s in scenes]

    def fcrun(lines, *opts):
        r = subprocess.run([FC, *opts, "run", "-"], input="\n".join(json.dumps(x) for x in lines), capture_output=True, text=True, encoding="utf-8")
        res = [json.loads(x) for x in r.stdout.splitlines() if x.startswith("{")]
        bad = [x for x in res if not x.get("ok")]
        if bad or r.returncode:
            sys.exit(f"FilmCraft failed: {bad or r.stderr[-400:]}")
        return res

    t0 = time.time()
    res = fcrun([{"id": "file.newSequence", "params": {"name": "Main", "width": 1920, "height": 1080, "fps": 30}},
                 {"id": "file.import", "params": {"paths": [str(p).replace("\\", "/") for p in mp4s + mp3s]}}], "--save-as", str(film))
    ids = res[1]["result"]["items"]
    n = len(scenes)
    vids, auds = ids[:n], ids[n:]
    place, cur, starts = [], 0.0, []
    for s, v, au in zip(scenes, vids, auds):
        clip = decode_check.probe_seconds(proj / "render" / f"{s['id']}.mp4")
        starts.append(cur)
        place.append({"id": "timeline.place", "params": {"item": v, "track": "V1", "seconds": round(cur, 4), "audio": False}})
        place.append({"id": "timeline.place", "params": {"item": au, "audioTrack": "A1", "seconds": round(cur + lead, 4), "video": False, "duration": int(s["audio_used"] * TICKS)}})
        cur += clip
    fcrun(place, "--project", str(film), "--save")
    out = proj / "output" / f"{sb['project']}_v{sb['version']}_{'draft' if a.draft else 'preview'}.mp4"
    r = subprocess.run([FC, "--project", str(film), "export", str(out), "--format", "h264"], capture_output=True, text=True, encoding="utf-8")
    if r.returncode:
        sys.exit(f"export failed: {r.stdout[-300:]} {r.stderr[-300:]}")
    log(f"assembled + exported in {time.time() - t0:.1f}s -> {out}")

    # ---- checks ----
    pj = json.loads(subprocess.run([FC, "probe", str(out), "--compact"], capture_output=True, text=True).stdout)
    secs = pj["duration"] / TICKS
    check("video 1920x1080 with audio", pj["video"] and (pj["video"]["width"], pj["video"]["height"]) == (1920, 1080) and bool(pj["audio_streams"]))
    tg = sbload.targets(sb)
    acceptance.lock(proj, tg, "first build")                      # no criteria locked yet: the ones this build is judged by are fixed now
    crit_problems = acceptance.problems(proj, tg)
    locked = acceptance.load(proj)
    check("pass/fail criteria were fixed before the build (not loosened since)", not crit_problems,
          crit_problems[0] if crit_problems else f"locked {locked['criteria']} by {locked['locked_by']} at {locked['locked_at']}")
    check(f"duration within {tg['duration'][0]}-{tg['duration'][1]} s", tg["duration"][0] <= secs <= tg["duration"][1], f"{secs:.1f}s")
    check(f"scene count within {tg['scenes'][0]}-{tg['scenes'][1]}", tg["scenes"][0] <= len(scenes) <= tg["scenes"][1], f"{len(scenes)} scenes")
    seq = json.loads(subprocess.run([FC, "--project", str(film), "inspect", "sequence", "--compact"], capture_output=True, text=True).stdout)
    nv = sum(len(t["items"]) for t in seq["video"])
    na = sum(len(t["items"]) for t in seq["audio"])
    check("timeline has exactly one video and one audio clip per scene (no duplicates)", (nv, na) == (n, n), f"video {nv}, audio {na}")
    items = sorted((it for t in seq["video"] for it in t["items"]), key=lambda x: x["start"])
    gaps = [(items[i + 1]["start"] - items[i]["end"]) / TICKS for i in range(len(items) - 1)]
    check("video clips are contiguous (no gaps/overlaps)", all(abs(g) < 0.04 for g in gaps), f"max |gap| {max((abs(g) for g in gaps), default=0):.3f}s")
    aud_items = sorted((it for t in seq["audio"] for it in t["items"]), key=lambda x: x["start"])
    ok_a = all(abs((au["start"] - v["start"]) / TICKS - lead) < 0.04 and au["end"] <= v["end"] + 0.04 * TICKS for v, au in zip(items, aud_items))
    check("each voice clip starts `lead` s into its scene and ends inside it", ok_a)
    # silence between the last word of one scene and the first word of the next
    gaps_sp = []
    for i in range(len(scenes) - 1):
        a_end = starts[i] + lead + scenes[i]["last_end"]
        b_start = starts[i + 1] + lead + scenes[i + 1]["first_word"]
        gaps_sp.append(round(b_start - a_end, 2))
    held = {sc["id"] for sc in sb["scenes"] if "hold_after" in sc}
    over = [(scenes[i]["id"], g) for i, g in enumerate(gaps_sp) if g > (1.5 if scenes[i]["id"] in held else 0.85)]
    check("silence between scenes <= 0.85 s (<= 1.5 s after scenes that hold a chart/summary)", not over,
          f"gaps {gaps_sp}" + (f"; too long: {over}" if over else ""))
    trimmed = [s["id"] for s in scenes if s["audio_used"] < s["last_end"] + 0.1 - 1e-6]
    check("no speech trimmed: every voice clip keeps >= 0.1 s after the last word", not trimmed, str(trimmed))
    # subtitles: every segment inside its scene, non-overlapping, narrow enough
    sub_ok, sub_info = True, ""
    for s in scenes:
        prev = 0
        for x in s["subs"]:
            if x["t0"] < prev - 0.001 or x["t1"] > s["dur"] + 0.001 or len(x["text"]) > 56:
                sub_ok, sub_info = False, f"{s['id']}: {x}"
            prev = x["t1"]
    check("subtitles: inside scene, in order, no overlap, <= 56 chars", sub_ok, sub_info)
    # cue times inside scenes
    cue_ok = all(0 <= p["appear"] <= s["dur"] for s in scenes for p in s["prims"] if p.get("appear") is not None) and \
        all(0 <= ac["T"] <= s["dur"] for s in scenes for ac in s["actions"])
    check("all cue-driven actions/appear times fall inside their scene", cue_ok)
    tol = (locked or {}).get("criteria", {}).get("cue_tolerance", acceptance.DEFAULT_CUE_TOLERANCE)
    late = [f"{r['who']} {r['action']} planned {r['planned']:.2f}s starts {r['actual']:.2f}s (+{r['actual'] - r['planned']:.2f})" for r in cue_rows if r["actual"] - r["planned"] > tol + 1e-6]
    check(f"actions start within {tol:g} s of their spoken cue (planned vs actual start, after non-overlap scheduling)", not late, "; ".join(late[:6]) if late else f"{len(cue_rows)} actions, worst shift {max([r['actual'] - r['planned'] for r in cue_rows] or [0]):.2f}s")
    # motion QA: run for every scene that was (re)rendered; a reused scene keeps the verdict stored with its clip (render/sNN.qa.json)
    bad = []
    for s in scenes:
        qaf = proj / "render" / f"{s['id']}.qa.json"
        if s["id"] not in rendered and qaf.exists() and json.loads(qaf.read_text(encoding="utf-8")).get("sig") == sigs[s["id"]]:
            problems = json.loads(qaf.read_text(encoding="utf-8"))["problems"]
        else:
            jsxs = proj / "render/_sample.jsx"
            problems = []
            who = [("", s["bi"].get("rig"))] + [(f"c{i + 1}_", c.get("rig")) for i, c in enumerate(s.get("cast", []))]
            for pfx, cid in who:
                jsxs.write_text("var P = " + json.dumps({"comp": s["id"], "fps": pr["fps"], "prefix": pfx}) + ";\n" + (P2 / "lib/sample_motion.jsx").read_text(encoding="utf-8"), encoding="utf-8")
                rr = subprocess.run([B.EC, "--project", pr["out"], "script", str(jsxs)], capture_output=True, text=True, encoding="utf-8")
                rows = []
                for line in rr.stdout.splitlines():
                    if line.startswith("S "):
                        v = line.split()[1:]
                        rows.append({"f": int(v[0]), "t": float(v[1]), "rootx": float(v[2]), "rooty": float(v[3]), "shL": float(v[4]), "elL": float(v[5]), "shR": float(v[6]),
                                     "elR": float(v[7]), "neck": float(v[8]), "waist": float(v[9]), "hipL": float(v[10]), "hipR": float(v[11]), "held": float(v[12])})
                problems += [f"{(pfx or 'main ')}{name} ({info})" for name, ok, info in CM.row_checks(rows, rigs.get(cid)) if not ok]
            qaf.write_text(json.dumps({"sig": sigs[s["id"]], "problems": problems}, ensure_ascii=False), encoding="utf-8")
        bad += [f"{s['id']}: {x}" for x in problems]
    check("motion QA on all scenes (joint limits, no snaps/flips, arms never through torso)", not bad, "; ".join(bad))
    # status
    st["state"] = "draft_built" if a.draft else "preview_built"
    st["last_build"] = {"draft": bool(a.draft), "output": str(out), "seconds": round(secs, 1), "rendered": rendered, "reused": reused, "built_in_s": round(time.time() - t_start, 1)}
    (proj / "status.json").write_text(json.dumps(st, ensure_ascii=False, indent=2), encoding="utf-8")
    (proj / "logs" / "build_report.json").write_text(json.dumps({"checks": report, "starts": [round(x, 2) for x in starts]}, ensure_ascii=False, indent=2), encoding="utf-8")
    log(f"DONE {out} {secs:.1f}s | rendered {rendered or '-'} | reused {reused or '-'} | log {logf}")
    sys.exit(0 if all(c["pass"] for c in report) else 1)


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    main()
