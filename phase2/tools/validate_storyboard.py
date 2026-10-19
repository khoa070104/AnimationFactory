"""Validate a project's storyboard BEFORE any paid call: structure, known props/actions/poses/faces, colours, cue phrases that really
occur in the spoken text, subtitle coverage/length, canvas bounds, scene count and duration estimate.
Usage: python validate_storyboard.py PROJECT_DIR      (exit 1 on errors; warnings do not fail)"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import build_storyboard as SBD
import characters as CHR
import sbload
import p2_svg as S

P2 = S.P2
norm = lambda s: re.sub(r"[^\w]+", " ", s.lower()).split()
ITEM_TYPES = {"prop", "text", "notice", "chart", "pills", "pie", "legend", "bill", "grid", "compare", "highlight"}
NUMWORDS = {"một": 1, "hai": 2, "ba": 3, "bốn": 4, "năm": 5, "sáu": 6, "bảy": 7, "tám": 8, "chín": 9, "mười": 10}
PROP_IMGS = {"pen", "basket", "notebook", "phone", "card", "board", "wallet", "calculator", "coin", "jar", "bill", "sweat", "exclaim", "shadow", "sparkle", "pill", "arrow_down"}
TEXT_COLORS = {"dark", "good", "bad", "bi", "white"}
FACES = set(S.FACES)
POSES = set(re.findall(r"^\s{2}(\w+):", (P2 / "lib/bi_motion.jsx").read_text(encoding="utf-8").split("var POSES = {")[1].split("};")[0], re.M))
ACTIONS = set(re.findall(r"^\s{2}(\w+): function \(T, p\)", (P2 / "lib/bi_motion.jsx").read_text(encoding="utf-8").split("var ACTIONS = {")[1], re.M))


def has_phrase(voice, phrase):
    v, p = norm(voice), norm(phrase)
    return any(v[i:i + len(p)] == p for i in range(len(v) - len(p) + 1))


def validate(proj, draft_chars=False):
    sb = sbload.load_storyboard(proj)
    E, W = [], []
    for k in ("project", "title", "version", "voice", "scenes"):
        if k not in sb:
            E.append(f"missing top-level key {k!r}")
    if E:
        return E, W
    for k in ("voice_id", "speed"):
        if k not in sb["voice"]:
            E.append(f"voice.{k} missing")
    ids = [s.get("id") for s in sb["scenes"]]
    if len(set(ids)) != len(ids):
        E.append("duplicate scene ids")
    for sc in sb["scenes"]:
        i = sc.get("id", "?")
        for k in ("id", "title", "voice", "subtitles", "bg", "bi", "items"):
            if k not in sc:
                E.append(f"{i}: missing {k!r}")
        if any(k not in sc for k in ("voice", "subtitles", "bg", "bi", "items")):
            continue
        if str(sc["bg"]).startswith("ai:"):
            status, _ = SBD.ai_asset(proj, sc["bg"][3:])
            if status != "approved":
                E.append(f"{i}: AI background {sc['bg'][3:]!r} is {status!r}; only approved assets can be used in scenes")
        else:
            try:
                SBD.bg_rgb(sc["bg"])
            except SystemExit as e:
                E.append(f"{i}: {e}")
        b = sc["bi"]

        def check_char(who, cid):
            if cid != CHR.BUILTIN:
                stt, why = CHR.state(proj, cid)
                if stt in ("draft", "stale") and draft_chars:
                    W.append(f"{i}: {who} character {cid!r} is {stt!r} (design only: it must be approved before the video is built)")
                elif stt != "approved":
                    E.append(f"{i}: {who} character {cid!r} is {stt!r}{(': ' + why) if why else ''}; only approved characters can be used in scenes")

        def check_actor(who, a_, actions, face_cues):
            if a_.get("face") not in FACES:
                E.append(f"{i}: {who}: unknown face {a_.get('face')!r} (known: {sorted(FACES)})")
            if a_.get("pose") not in POSES:
                E.append(f"{i}: {who}: unknown pose {a_.get('pose')!r} (known: {sorted(POSES)})")
            for k in ("x", "y", "scale"):
                if not isinstance(a_.get(k), (int, float)):
                    E.append(f"{i}: {who}: {k} must be a number")
            for ac in actions:
                if ac["name"] not in ACTIONS:
                    E.append(f"{i}: {who}: unknown action {ac['name']!r} (known: {sorted(ACTIONS)})")
                for cue in ([ac["cue"]] if "cue" in ac else []) + ac.get("cues", []):
                    if not has_phrase(sc["voice"], cue):
                        E.append(f"{i}: {who}: action cue {cue!r} does not occur in the voice text")
                if "cue" not in ac and "cues" not in ac and "at" not in ac:
                    E.append(f"{i}: {who}: action {ac['name']!r} needs `cue`, `cues` or `at`")
            for f in face_cues:
                if f["face"] not in FACES or not has_phrase(sc["voice"], f["cue"]):
                    E.append(f"{i}: {who}: bad face cue {f}")

        check_char("main", b.get("char") or CHR.BUILTIN)
        check_actor("main", b, sc.get("actions", []), sc.get("face_cues", []))
        import shots as SH
        for p_ in SH.problems(sc, has_phrase):                                   # structured (code, shot_id, field) problems, flattened for the text report
            E.append(f"{i}: shot {p_['shot_id']}: {p_['field']}: {p_['message']} [{p_['code']}]")
        for k_, it_ in enumerate(sc.get("items", [])):
            if it_.get("space", "world") not in ("world", "screen"):
                E.append(f"{i}: item #{k_ + 1}: space must be 'world' (follows the camera) or 'screen' (fixed), not {it_.get('space')!r}")
        if len(sc.get("cast", [])) > 3:
            E.append(f"{i}: at most 3 supporting characters per scene")
        for ci, c in enumerate(sc.get("cast", [])):
            check_char(f"cast[{ci}]", c.get("char") or CHR.BUILTIN)
            check_actor(f"cast[{ci}]", c, c.get("actions", []), c.get("face_cues", []))
        if sc.get("rest") and sc["rest"] not in POSES:
            E.append(f"{i}: unknown rest pose {sc['rest']!r}")
        try:
            sbload.resolve_camera(sc.get("camera"))
        except ValueError as e:
            E.append(f"{i}: {e}")
        for h in sc.get("holds", []):
            if h["prop"].startswith("ai:"):
                if SBD.ai_asset(proj, h["prop"][3:])[0] != "approved":
                    E.append(f"{i}: held AI asset {h['prop'][3:]!r} is not approved; only approved assets can be used in scenes")
            elif h["prop"] not in PROP_IMGS:
                E.append(f"{i}: unknown held prop {h['prop']!r}")
            if h.get("side") not in ("L", "R"):
                E.append(f"{i}: hold side must be L or R")
            who = h.get("who", "main")
            if who != "main" and not (re.fullmatch(r"cast[1-3]", who) and int(who[4:]) <= len(sc.get("cast", []))):
                E.append(f"{i}: hold `who` {who!r} names no character of the scene (main, cast1..)")
        for who_, acts_ in [("main", sc.get("actions", []))] + [(f"cast{k + 1}", c_.get("actions", [])) for k, c_ in enumerate(sc.get("cast", []))]:
            held_ = sbload.held_sides(sc, who_)
            for a_ in acts_:
                right_other = any(h_["side"] == "R" and h_["prop"] != "phone" and h_.get("who", "main") == who_ for h_ in sc.get("holds", []))
                if held_ and ((a_["name"] in ("wave", "point", "point_seq") and "R" in held_) or a_["name"] in ("shrug", "cheek") or (a_["name"] == "hold_phone" and right_other)):
                    W.append(f"{i}: {who_} holds a prop in a hand that action {a_['name']!r} also moves: the prop will swing with the arm; choose another action or drop the prop")
        import action_match
        for msg in action_match.check(sc.get("voice", ""), [{x["name"] for x in sc.get("actions", [])}] + [{x["name"] for x in c_.get("actions", [])} for c_ in sc.get("cast", [])], sc.get("accepted_gaps", [])):
            W.append(f"{i}: {msg}")
        txts = [sc.get("voice", ""), sc.get("title", "")]
        for it_ in sc.get("items", []):
            txts += [str(it_.get(k, "")) for k in ("text", "title", "amount", "caption")] + [str(t_) for t_ in it_.get("texts", [])]
            txts += [str(c_.get("text", "")) + str(c_.get("label", "")) for c_ in it_.get("cells", [])] + [str(r_.get("text", "")) for r_ in it_.get("rows", [])]
        if any(sbload.has_emoji(t_) for t_ in txts):
            E.append(f"{i}: emoji in the text: the video font does not draw them (and the voice would not read them); use words, numbers or a prop")
        # items
        def check_color(c, where):
            if c not in TEXT_COLORS and c not in S.A:
                E.append(f"{i}: unknown colour {c!r} in {where}")

        def check_appear(ap, where):
            if isinstance(ap, str) and not has_phrase(sc["voice"], ap):
                E.append(f"{i}: appear cue {ap!r} ({where}) does not occur in the voice text")

        for it in sc["items"]:
            t = it.get("type")
            if t not in ITEM_TYPES:
                E.append(f"{i}: unknown item type {t!r} (known: {sorted(ITEM_TYPES)})")
                continue
            check_appear(it.get("appear"), t)
            if t == "pills" and it.get("marker", "number") not in ("number", "dot", "coin"):
                E.append(f"{i}: pills marker {it.get('marker')!r} must be number, dot or coin")
            if t == "pills" and it.get("marker") == "coin" and not re.search(r"tiền|đồng|chi tiêu|ngân sách|tiết kiệm|đầu tư|nợ|lãi|giá|phí|money|cost|price|budget|saving", " ".join(map(str, it.get("texts", []))), re.I):
                W.append(f"{i}: pills use the coin marker but the list is not about money; use marker 'number'")
            for k in ("x", "y"):
                if k in it and not (-150 <= it[k] <= 2070 if k == "x" else -150 <= it[k] <= 1230):
                    W.append(f"{i}: {t} {k}={it[k]} is far outside the canvas")
            if t == "prop" and it["img"].startswith("ai:"):
                status, _ = SBD.ai_asset(proj, it["img"][3:])
                if status != "approved":
                    E.append(f"{i}: AI asset {it['img'][3:]!r} is {status!r}; only approved assets can be used in scenes")
            elif t == "prop" and it["img"] not in PROP_IMGS:
                E.append(f"{i}: unknown prop image {it['img']!r} (known: {sorted(PROP_IMGS)}, or ai:<id> for an approved AI asset)")
            if t == "compare":
                for side in ("left", "right"):
                    sd = it.get(side) or {}
                    if not isinstance(sd.get("value"), (int, float)) or sd["value"] < 0 or not sd.get("label"):
                        E.append(f"{i}: compare.{side} needs a label and a non-negative number `value`")
                    elif sd.get("color", "blue") not in S.A:
                        E.append(f"{i}: compare.{side}.color {sd.get('color')!r} is not an accent colour")
                    check_appear(sd.get("appear"), t)
            if t == "highlight" and not all(isinstance(it.get(k), (int, float)) and it[k] > 0 for k in ("w", "h")):
                E.append(f"{i}: highlight needs positive w and h")
            if t == "prop" and it.get("img") == "card":
                W.append(f"{i}: the `card` prop is an empty card with a tick: it carries no text; use a notice for text or leave it out")
            if t == "text":
                check_color(it.get("color", "dark"), "text")
                if it["size"] < 40:
                    W.append(f"{i}: text {it['text']!r} is {it['size']} px (style minimum 40)")
            if t == "grid":
                if not it.get("cells") or int(it.get("cols", 0)) < 1:
                    E.append(f"{i}: grid needs cols >= 1 and at least one cell")
                said = re.findall(r"(\d+|một|hai|ba|bốn|năm|sáu|bảy|tám|chín|mười)\s+(?:ô|ngày|mục)\b", sc.get("voice", "").lower())
                if said and len(it.get("cells", [])) != (int(said[0]) if said[0].isdigit() else NUMWORDS[said[0]]):
                    E.append(f"{i}: the text says {said[0]!r} cells/days/items but the grid has {len(it.get('cells', []))}; one cell per item, in the order the text names them (empty cells are fine)")
                for c_ in it.get("cells", []):
                    check_appear(c_.get("appear"), t)
                    if max(len(str(c_.get("text", ""))), len(str(c_.get("label", "")))) > 16:
                        W.append(f"{i}: grid cell text {c_.get('text')!r} is longer than 16 characters and may not fit its cell")
            for x in it.get("bars", []) + it.get("rows", []) + it.get("parts", []):
                if "color" in x:
                    check_color(x["color"], t)
                check_appear(x.get("appear"), t)
            for ap in it.get("appears", []):
                check_appear(ap, t)
        # subtitles: ordered, covering, short
        vt, pos = norm(sc["voice"]), 0
        for seg in sc["subtitles"]:
            st = norm(seg)
            idx = next((j for j in range(pos, len(vt) - len(st) + 1) if vt[j:j + len(st)] == st), None)
            if idx is None:
                E.append(f"{i}: subtitle segment {seg!r} is not the next words of the voice text")
            else:
                if idx != pos:
                    W.append(f"{i}: words skipped before subtitle {seg!r}")
                pos = idx + len(st)
            if len(seg) > 56:
                E.append(f"{i}: subtitle too long ({len(seg)} chars, max 56): {seg!r}")
        if pos < len(vt):
            W.append(f"{i}: the last words of the voice text are not shown in any subtitle")
    import layout
    W += layout.check(sb, proj)                      # partial overlaps / off-canvas items (rough boxes; warnings only)
    st = SBD.stats(sb)
    secs = sum(r["sec"] for r in st)
    tg = sbload.targets(sb)
    if not tg["scenes"][0] <= len(st) <= tg["scenes"][1]:
        W.append(f"{len(st)} scenes (target {tg['scenes'][0]}-{tg['scenes'][1]})")
    if not tg["duration"][0] <= secs <= tg["duration"][1]:
        W.append(f"estimated duration {secs:.0f}s (target {tg['duration'][0]}-{tg['duration'][1]} s)")
    return E, W


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    errs, warns = validate(sys.argv[1], draft_chars="--draft" in sys.argv[2:])    # draft builds may use characters whose pictures the owner has not approved yet (warning)
    for e in errs:
        print("ERROR  ", e)
    for w in warns:
        print("WARNING", w)
    print(f"{len(errs)} error(s), {len(warns)} warning(s)")
    sys.exit(1 if errs else 0)
