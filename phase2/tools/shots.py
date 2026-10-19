"""Shots: the level below `scene`. A scene may carry `shots` (absent = one implicit wide shot, so every older storyboard is unchanged):

  "shots": [{"id": "sh1", "purpose": "...", "start": 0 | "spoken phrase", "kind": "wide|action|reaction|prop|compare|graphic",
             "focus": "main" | "cast1" | "item:2" | "item:<img>" | [x, y, w, h],     # what the viewer must look at
             "size": "wide|medium|close|detail", "pad": 0.25, "cut": false, "ease": 0.5, "end": optional seconds | phrase,
             "gaze": [{"who": "main", "at": "cast1" | "item:..." | "left" | "right" | [x, y]}]}]

Timing rules (validated): `start` is seconds from the scene start or a phrase of the scene's voice; starts strictly increase; a shot lasts until the next one starts
(the last until the scene ends); an explicit `end` earlier than the next start returns the camera to the wide frame in between (a gap, by choice); an `end` later than
the next start is an overlap and is refused. The camera is a pure function of scene time and never restarts anyone's pose: characters and held props keep their
state across shots (nothing is re-entered by a cut).

Framing uses the size of what is looked at: the body box of a character comes from its rig height x scale, items from layout.item_boxes; the view is padded, zoomed
(max 2.2: raster pictures get soft beyond that), kept inside the canvas and above the subtitle band. resolve() turns shots into camera keys + gaze schedules in SECONDS;
both are data for the renderer. Remotion applies them; the Craft renderer keeps its old per-scene preset only."""
W, H = 1920, 1080
SUBTITLE_TOP = 985
MAX_ZOOM = 2.2
KINDS = ("wide", "action", "reaction", "prop", "compare", "graphic")
SIZES = {"wide": None, "medium": 0.30, "close": 0.20, "detail": 0.28}          # default padding around the focus box (fraction of its size)
UPPER = {"medium": 1.0, "close": 0.45, "detail": 1.0}                           # part of a character's height kept in frame (from the head down)


def problem(code, shot_id, field, message, next_action):
    return {"code": code, "shot_id": shot_id, "field": field, "message": message, "next_action": next_action}


def problems(sc, has_phrase):
    """Structured problems of a scene's shots (see module doc). has_phrase(voice, phrase) -> bool. -> list of dicts (empty = fine)."""
    out, shots = [], sc.get("shots") or []
    if not isinstance(shots, list):
        return [problem("SHOTS_NOT_A_LIST", None, "shots", "`shots` must be a list", "Make `shots` a list of shot objects.")]
    voice, cast, items = sc.get("voice", ""), sc.get("cast", []) or [], sc.get("items", []) or []
    seen, prev = set(), None
    for k, s in enumerate(shots):
        sid = s.get("id") or f"#{k + 1}"
        if sid in seen:
            out.append(problem("DUPLICATE_SHOT_ID", sid, "id", f"shot id {sid!r} is used twice", "Give each shot its own id."))
        seen.add(sid)
        if s.get("kind", "wide") not in KINDS:
            out.append(problem("UNKNOWN_SHOT_KIND", sid, "kind", f"unknown kind {s.get('kind')!r}", f"Use one of {list(KINDS)}."))
        if s.get("size", "wide") not in SIZES:
            out.append(problem("UNKNOWN_SHOT_SIZE", sid, "size", f"unknown size {s.get('size')!r}", f"Use one of {list(SIZES)}."))
        st = s.get("start", 0)
        if isinstance(st, str) and not has_phrase(voice, st):
            out.append(problem("CUE_NOT_IN_VOICE", sid, "start", f"start phrase {st!r} does not occur in the scene's voice text", "Copy an exact run of words from the voice text, or use seconds."))
        elif isinstance(st, (int, float)) and st < 0:
            out.append(problem("NEGATIVE_START", sid, "start", "start is negative", "Use seconds >= 0."))
        if k == 0 and isinstance(st, (int, float)) and st > 0.5:
            out.append(problem("FIRST_SHOT_LATE", sid, "start", f"the first shot starts at {st}s: nothing frames the scene before it", "Start the first shot at 0 or add an earlier wide shot."))
        if isinstance(st, (int, float)) and isinstance(prev, (int, float)) and st <= prev:
            out.append(problem("SHOTS_NOT_INCREASING", sid, "start", f"start {st}s is not after the previous shot ({prev}s)", "Shots must start in strictly increasing order."))
        prev = st if isinstance(st, (int, float)) else prev
        out += _focus_problems(sid, s, cast, items)
        for g in s.get("gaze", []) or []:
            who = g.get("who", "main")
            if who != "main" and not (who.startswith("cast") and who[4:].isdigit() and 1 <= int(who[4:]) <= len(cast)):
                out.append(problem("UNKNOWN_GAZE_ACTOR", sid, "gaze.who", f"gaze names {who!r}, not a character of the scene", "Use 'main' or 'cast1'..."))
            if _ref_problem(g.get("at"), cast, items, allow_dir=True):
                out.append(problem("UNKNOWN_GAZE_TARGET", sid, "gaze.at", _ref_problem(g.get("at"), cast, items, allow_dir=True), "Use a character, item:<index|img>, left, right or [x, y]."))
        en = s.get("end")
        if isinstance(en, (int, float)) and k + 1 < len(shots) and isinstance(shots[k + 1].get("start", 0), (int, float)) and en > shots[k + 1]["start"] + 1e-6:
            out.append(problem("SHOT_OVERLAP", sid, "end", f"end {en}s is after the next shot starts ({shots[k + 1]['start']}s)", "End the shot before the next one starts, or drop `end`."))
    return out


def _ref_problem(ref, cast, items, allow_dir=False):
    if ref in (None, "scene"):
        return "" if ref == "scene" else "missing target"
    if isinstance(ref, (list, tuple)):
        return "" if len(ref) in (2, 4) and all(isinstance(v, (int, float)) for v in ref) else "a region is [x, y, w, h], a point [x, y]"
    if allow_dir and ref in ("left", "right"):
        return ""
    if ref == "main":
        return ""
    if isinstance(ref, str) and ref.startswith("cast") and ref[4:].isdigit():
        return "" if 1 <= int(ref[4:]) <= len(cast) else f"{ref!r}: the scene has {len(cast)} supporting character(s)"
    if isinstance(ref, str) and ref.startswith("item:"):
        key = ref[5:]
        if key.isdigit():
            return "" if int(key) < len(items) else f"{ref!r}: the scene has {len(items)} item(s)"
        return "" if any(str(i.get("img")) == key or i.get("type") == key for i in items) else f"{ref!r}: no item with that picture/type"
    return f"unknown target {ref!r}"


def _focus_problems(sid, s, cast, items):
    sz = s.get("size", "wide")
    if sz == "wide" and s.get("focus") is None:
        return []
    msg = _ref_problem(s.get("focus"), cast, items)
    return [problem("UNKNOWN_FOCUS", sid, "focus", msg, "Point `focus` at main, cast1.., item:<index|img> or [x, y, w, h].")] if msg else []


# ------------------------------------------------------------------------------------------------------------------ geometry
def char_box(c, rig_height=540):
    """Body box of a character in canvas px: feet at (x, y), height = rig height x scale, width about half of it."""
    s = float(c.get("scale", 1.0))
    h, w = rig_height * s, rig_height * s * 0.5
    return (c["x"] - w / 2, c["y"] - h, c["x"] + w / 2, c["y"])


def _focus_box(ref, chars, boxes, items_boxes, size):
    if isinstance(ref, (list, tuple)) and len(ref) == 4:
        return (ref[0], ref[1], ref[0] + ref[2], ref[1] + ref[3])
    if ref in chars:
        x0, y0, x1, y1 = chars[ref]
        keep = UPPER.get(size, 1.0)
        return (x0, y0, x1, y0 + (y1 - y0) * keep)                              # close-up = head and chest
    if isinstance(ref, str) and ref.startswith("item:"):
        key = ref[5:]
        for k, (lab, b, it) in enumerate(items_boxes):
            if (key.isdigit() and int(key) == k) or (not key.isdigit() and (str(it.get("img")) == key or it.get("type") == key)):
                return b
    return None


def frame(box, size, pad=None):
    """-> (cx, cy, zoom) that shows `box` with padding, inside the canvas and above the subtitle band."""
    if size == "wide" or box is None:
        return (W / 2, H / 2, 1.0)
    p = SIZES.get(size, 0.25) if pad is None else pad
    bw, bh = (box[2] - box[0]) * (1 + 2 * p), (box[3] - box[1]) * (1 + 2 * p)
    z = max(1.0, min(MAX_ZOOM, W / max(bw, 1), H / max(bh, 1)))
    cx, cy = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
    bottom = (box[3] + (box[3] - box[1]) * p - cy) * z + H / 2                    # where the padded box ends on screen
    if bottom > SUBTITLE_TOP - 20:
        cy += (bottom - (SUBTITLE_TOP - 20)) / z
    cx = min(max(cx, W / (2 * z)), W - W / (2 * z))                              # never show outside the canvas
    cy = min(max(cy, H / (2 * z)), H - H / (2 * z))
    return (round(cx, 1), round(cy, 1), round(z, 3))


def resolve(sc, dur, T, rig_heights=None, items_boxes=None):
    """Shots -> {"camera": [{t, cx, cy, z}], "looks": {who: [{t, at: [x, y], dir}]}} in seconds.
    T(phrase) -> seconds; items_boxes: [(label, box, item)] aligned with sc['items']; rig_heights: {char id: rig height}."""
    shots = sc.get("shots") or []
    if not shots:
        return {"camera": [], "looks": {}, "shots": []}
    rig_heights = rig_heights or {}
    chars = {"main": char_box(sc["bi"], rig_heights.get(sc["bi"].get("char"), 540))}
    for k, c in enumerate(sc.get("cast", []) or []):
        chars[f"cast{k + 1}"] = char_box(c, rig_heights.get(c.get("char"), 540))
    items_boxes = items_boxes or []
    tt = lambda v: round(T(v) if isinstance(v, str) else float(v), 3)
    cam, looks = [], {}
    prev = (W / 2, H / 2, 1.0)
    for k, s in enumerate(shots):
        t0 = tt(s.get("start", 0))
        box = _focus_box(s.get("focus"), chars, None, items_boxes, s.get("size", "wide"))
        f = frame(box, s.get("size", "wide"), s.get("pad"))
        ease = 0.0 if s.get("cut") else float(s.get("ease", 0.5))
        if k == 0:
            cam.append({"t": 0.0, "cx": f[0], "cy": f[1], "z": f[2]})
        else:
            cam.append({"t": round(t0 - (0.001 if ease == 0 else 0), 3), "cx": prev[0], "cy": prev[1], "z": prev[2]})      # hold/leave the previous frame (a cut: until 1 ms before)...
            cam.append({"t": round(t0 + ease, 3), "cx": f[0], "cy": f[1], "z": f[2]})   # ...and arrive (a cut: at once)
        prev = f
        en = s.get("end")
        if en is not None and (k + 1 == len(shots) or tt(en) < tt(shots[k + 1].get("start", 0))):
            te = tt(en)
            cam.append({"t": te, "cx": f[0], "cy": f[1], "z": f[2]})
            cam.append({"t": round(te + 0.5, 3), "cx": W / 2, "cy": H / 2, "z": 1.0})      # a gap by choice: back to the wide frame
            prev = (W / 2, H / 2, 1.0)
        for g in s.get("gaze", []) or []:
            who = g.get("who", "main")
            at = g.get("at")
            if at in ("left", "right"):
                looks.setdefault(who, []).append({"t": t0, "dir": at})
            else:
                b = _focus_box(at, chars, None, items_boxes, "wide") if not (isinstance(at, (list, tuple)) and len(at) == 2) else (at[0], at[1], at[0], at[1])
                if b:
                    looks.setdefault(who, []).append({"t": t0, "at": [round((b[0] + b[2]) / 2, 1), round((b[1] + b[3]) / 2, 1)]})
    starts = [tt(s.get("start", 0)) for s in shots]
    meta = []
    for k, s in enumerate(shots):
        box = _focus_box(s.get("focus"), chars, None, items_boxes, s.get("size", "wide"))
        cx, cy, z = frame(box, s.get("size", "wide"), s.get("pad"))
        fi = None
        ref = s.get("focus")
        if isinstance(ref, str) and ref.startswith("item:"):
            key = ref[5:]
            fi = next((n for n, (_l, _b, it) in enumerate(items_boxes) if (key.isdigit() and int(key) == n) or (not key.isdigit() and (str(it.get("img")) == key or it.get("type") == key))), None)
        meta.append({"id": s.get("id"), "kind": s.get("kind", "wide"), "size": s.get("size", "wide"), "purpose": s.get("purpose"), "t0": starts[k],
                     "t1": (starts[k + 1] if k + 1 < len(shots) else round(dur, 3)), "view": [round(cx - W / (2 * z)), round(cy - H / (2 * z)), round(cx + W / (2 * z)), round(cy + H / (2 * z))],
                     "focus_item": fi, "zoomed": s.get("size", "wide") in ("close", "detail")})
    return {"camera": cam, "looks": looks, "shots": meta}


def camera_at(keys, t):
    """Same interpolation as the renderer: eased between consecutive keys; the later of two keys at one time wins (a cut)."""
    if not keys:
        return (W / 2, H / 2, 1.0)
    ks = [k for i, k in enumerate(keys) if i + 1 >= len(keys) or keys[i + 1]["t"] != k["t"]]
    if t <= ks[0]["t"]:
        return (ks[0]["cx"], ks[0]["cy"], ks[0]["z"])
    for a, b in zip(ks, ks[1:]):
        if t < b["t"]:
            p = (t - a["t"]) / (b["t"] - a["t"])
            e = p * p * (3 - 2 * p)
            return tuple(a[k] + (b[k] - a[k]) * e for k in ("cx", "cy", "z"))
    return (ks[-1]["cx"], ks[-1]["cy"], ks[-1]["z"])
