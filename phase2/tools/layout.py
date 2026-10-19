"""Rough layout check for a scene's on-screen items (no rendering): estimates each item's box on the 1920x1080 canvas and reports PARTIAL overlaps
(one item half on top of another), which are almost always mistakes. An item fully inside another (text on a board, chart title in its board) is
intentional layering and is not reported. Box sizes are nominal display sizes of the library images (PNG size / 2 at scale 1.0, measured from the
tool's own assets) and of the text/pill/legend builders in build_storyboard.py; AI assets use their manifest size. Warnings only; the AI storyboard step
uses them to ask for one corrective pass."""
from pathlib import Path

# display size (w, h) of library images at scale 1.0
PROP_SIZE = {"notebook": (260, 200), "pen": (36, 220), "basket": (240, 190), "arrow_down": (90, 130), "bill": (380, 480), "board": (820, 600), "calculator": (230, 320), "card": (600, 170), "coin": (80, 80), "exclaim": (70, 170),
             "jar": (220, 300), "phone": (300, 520), "pie": (300, 300), "pill": (560, 110), "shadow": (420, 70), "sparkle": (90, 90), "sweat": (56, 80), "wallet": (240, 170)}
CANVAS = (1920, 1080)
SUB_ZONE_TOP = 985                    # the subtitle bar sits at y ~ 1030 (84 px high)


def _box(cx, cy, w, h):
    return (cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2)


def item_boxes(sc, ai_size=None):
    """-> [(label, (x0, y0, x1, y1))] for the scene's items (not Bi)."""
    out = []
    for i, it in enumerate(sc.get("items", [])):
        t, x, y = it.get("type"), it.get("x", 0), it.get("y", 0)
        s = float(it.get("scale", 1.0) or 1.0)
        lab = f"{t} #{i + 1}"
        if t == "prop":
            img = str(it.get("img", ""))
            w, h = (ai_size or {}).get(img[3:]) if img.startswith("ai:") and (ai_size or {}).get(img[3:]) else PROP_SIZE.get(img, (200, 200))
            out.append((f"{lab} ({img})", _box(x, y, w * s, h * s)))
        elif t == "text":
            size = float(it.get("size", 56))
            w = len(str(it.get("text", ""))) * 0.55 * size
            out.append((f"{lab} “{str(it.get('text', ''))[:18]}”", _box(x, y - 0.25 * size, w, size * 1.15)))
        elif t == "notice":
            out.append((lab, _box(x, y, 600, 170)))
        elif t == "chart":
            out.append((lab, _box(x, y, 820 * s, 600 * s)))
        elif t == "pie":
            out.append((lab, _box(x, y, 300 * s, 300 * s)))
        elif t == "bill":
            out.append((lab, _box(x, y, 380 * s / 1.0, 480 * s / 1.0)))
        elif t == "grid":
            import build_storyboard as _sb
            cw, ch_ = map(float, _sb.grid_cell_size(it))
            cols = max(1, int(it.get("cols", 2)))
            rows = -(-max(1, len(it.get("cells", []))) // cols)
            gh = rows * ch_ + (rows - 1) * 14
            top = y + (35 if it.get("title") else 0)                      # build_storyboard.expand: rows are centred on `top`, the title sits ~70 px above the first row
            out.append((lab, (x - (cols * cw + (cols - 1) * 14) / 2, top - gh / 2 - (70 if it.get("title") else 0), x + (cols * cw + (cols - 1) * 14) / 2, top + gh / 2)))
        elif t == "pills":
            size = float(it.get("size", 50))
            texts = it.get("texts", [])
            maxlen = max((len(x_) for x_ in texts), default=1)
            w = max(560, int(((maxlen * 0.62 * size + 190) + 19) // 20 * 20))
            n = max(1, len(texts))
            gap = float(it.get("gap", 110))
            out.append((lab, (x - w / 2, y - 55, x + w / 2, y + (n - 1) * gap + 55)))
        elif t == "legend":
            size = float(it.get("size", 48))
            rows = it.get("rows", [])
            maxlen = max((len(r.get("text", "")) for r in rows), default=1)
            left = x - maxlen * 0.26 * size
            gap = float(it.get("gap", 100))
            out.append((lab, (left - 60, y - size * 0.7, left + maxlen * 0.52 * size, y + max(0, len(rows) - 1) * gap + size * 0.7)))
    return out


def _inter(a, b):
    w = min(a[2], b[2]) - max(a[0], b[0])
    h = min(a[3], b[3]) - max(a[1], b[1])
    return max(0.0, w) * max(0.0, h)


def _area(a):
    return max(1.0, (a[2] - a[0]) * (a[3] - a[1]))


def check_scene(sc, ai_size=None):
    """-> list of warning strings for one scene."""
    sid = sc.get("id", "?")
    bi = sc.get("bi") or {}
    s = float(bi.get("scale", 1.05))
    boxes = item_boxes(sc, ai_size)
    named = boxes + [("Bi", (bi.get("x", 500) - 200 * s, bi.get("y", 930) - 600 * s, bi.get("x", 500) + 200 * s, bi.get("y", 930)))]
    for ci, c in enumerate(sc.get("cast", []) or []):                  # supporting characters occupy their own body box
        cs = float(c.get("scale", 1.0))
        named.append((f"cast {ci + 1}", (c.get("x", 1500) - 200 * cs, c.get("y", 930) - 600 * cs, c.get("x", 1500) + 200 * cs, c.get("y", 930))))
    warns = []
    for i in range(len(named)):
        for j in range(i + 1, len(named)):
            (la, a), (lb, b) = named[i], named[j]
            inter = _inter(a, b)
            if not inter:
                continue
            small = min(_area(a), _area(b))
            frac = inter / small
            has_char = any(n.startswith(("Bi", "cast")) for n in (la, lb))
            small_lab, big_lab = (la, lb) if _area(a) < _area(b) else (lb, la)
            layered = any(d in small_lab for d in DECOR) or (small_lab.startswith(("text", "legend", "pills")) and (big_lab.startswith(("chart", "notice", "bill")) or any(k in big_lab for k in ("(board)", "(card)"))))
            if 0.12 < frac < (0.85 if (layered and not has_char) else 1.01):   # decoration, or text/lists written on a board/card/chart, is layering; a prop or table over content or a character is a collision
                warns.append(f"{sid}: layout: {la} and {lb} overlap partly ({int(frac * 100)}% of the smaller one); move or resize one of them")
    chars = [("Bi" if not bi.get("char") else f"main ({bi.get('char')})", bi.get("x", 500), bi.get("y", 930), s, sc.get("actions") or [])]
    for ci, c in enumerate(sc.get("cast", []) or []):
        chars.append((f"cast {ci + 1}", c.get("x", 1500), c.get("y", 930), float(c.get("scale", 1.0)), c.get("actions") or []))
    for ci, (lab, cx, cy, cs, acts) in enumerate(chars):          # the walk-in path must not cross other characters or items (checked as a swept box, not only the end pose)
        if not any(a_.get("name") == "enter" for a_ in acts):
            continue
        sx = cx + (-900 if cx < CANVAS[0] / 2 else 900)
        sweep = (min(cx, sx) - 200 * cs, cy - 600 * cs, max(cx, sx) + 200 * cs, cy)
        for olab, ob in [n for n in named if n[0] != lab and not (ci == 0 and n[0] == "Bi")]:
            if olab.startswith("prop") and ob[3] < cy - 600 * cs:      # a prop that hangs above head height is not in the way
                continue
            inter = _inter(sweep, ob)
            if inter and inter / _area(ob) > 0.12 and _inter((cx - 200 * cs, cy - 600 * cs, cx + 200 * cs, cy), ob) / _area(ob) < 0.12:
                warns.append(f"{sid}: layout: the walk-in of {lab} crosses {olab}; enter from the other side or move it")
    for lab, b in boxes:
        if b[3] > SUB_ZONE_TOP and b[1] < CANVAS[1] and not lab.startswith("prop") and b[2] - b[0] < 1500:
            warns.append(f"{sid}: layout: {lab} runs into the subtitle band (y > {SUB_ZONE_TOP}); move it up")
        if b[0] < -20 or b[1] < -20 or b[2] > CANVAS[0] + 20 or b[3] > CANVAS[1] + 20:
            warns.append(f"{sid}: layout: {lab} extends outside the 1920x1080 canvas")
    return warns


DECOR = ("sparkle", "coin", "exclaim", "sweat", "arrow_down", "shadow", "pill")
CONTENT = {"text", "grid", "chart", "legend", "pills", "notice", "bill", "pie"}        # items that carry the explanation; props are scene dressing


def zone(sc):
    """Content panel (x0, y0, x1, y1): between the two characters when there is a supporting character, else the right-hand side. Subtitles own y > 985."""
    return (640, 170, 1280, 900) if sc.get("cast") else (900, 170, 1800, 900)


def _shrink(it):
    t = it.get("type")
    if t in ("pie", "bill", "prop") and it.get("scale", 1) > 0.4:                # NOT charts: their bars/labels keep a fixed size, a shrunk board would overlap its own text
        it["scale"] = round(it["scale"] * 0.95, 3)
        return True
    if t in ("text", "pills", "legend") and it.get("size", 50) > 40:
        it["size"] = max(40, int(it.get("size", 50) * 0.95))
        return True
    if t == "grid" and int(it.get("cols", 2)) > 1:
        it["cols"] = 1                                                          # a list of rows is narrower than a table of cells
        return True
    return False


def compose(sc, ai_size=None):
    """Reusable layout for explanation scenes: the characters stand at the edges, every content item (title, table, chart, list, notice...) is stacked top to bottom in the
    content panel (shrunk to fit, never over a character), props stay scene dressing for nudge() to place. Deterministic, no AI. -> number of items placed."""
    cast = sc.get("cast") or []
    if cast:
        sc["bi"]["x"] = 400
        cast[0]["x"] = 1520
    x0, y0, x1, y1 = zone(sc)
    big_prop = lambda i: i.get("type") == "prop" and not any(d in str(i.get("img")) for d in DECOR) and item_boxes({"items": [i]}, ai_size)[0][1][2] - item_boxes({"items": [i]}, ai_size)[0][1][0] >= 150
    items = [i for i in sc.get("items", []) if (i.get("type") in CONTENT or big_prop(i)) and "x" in i]      # a big picture (a fridge) takes part in the stack like a table; small props are decoration
    if not items:
        return 0
    box = lambda it: item_boxes({"items": [it]}, ai_size)[0][1]
    gap = 24
    for it in items:
        while box(it)[2] - box(it)[0] > x1 - x0 and _shrink(it):
            pass
    while sum(box(i)[3] - box(i)[1] for i in items) + gap * (len(items) - 1) > y1 - y0:
        if any(_shrink(i) for i in items):
            continue
        pics = [i for i in items if big_prop(i)]
        if not pics:
            break                                                               # still too tall: the layout check will say so
        items.remove(pics[-1])                                                  # a big picture leaves the stack and becomes dressing for nudge()
    cursor, cx = y0, (x0 + x1) / 2
    for it in items:                                                            # in the order the storyboard lists them (the heading comes first)
        b = box(it)
        it["y"] = round(it["y"] + cursor - b[1])
        it["x"] = round(it["x"] + cx - (b[0] + b[2]) / 2)
        cursor += b[3] - b[1] + gap
    sc.pop("panel", None)
    if str(sc.get("bg", "")).startswith("ai:"):                       # a picture background is busy: one soft plate behind the whole content stack keeps every line readable
        bs = [box(i) for i in items]
        sc["panel"] = [max(0, round(min(b[0] for b in bs) - 30)), max(0, round(min(b[1] for b in bs) - 24)), min(1920, round(max(b[2] for b in bs) + 30)), min(1080, round(max(b[3] for b in bs) + 24))]
    return len(items)


def nudge(sc, ai_size=None):
    """Deterministic repair, no AI: an item that overlaps another item or a character moves to the nearest spot (graphics zone x 850-1800, y 280-820) that adds no
    layout warning; characters never move. -> number of items moved."""
    moved = 0
    items = sc.get("items", [])
    for it in items:
        if "x" not in it or "y" not in it:
            continue
        base = len(check_scene(sc, ai_size))
        others = len(check_scene({**sc, "items": [i for i in items if i is not it]}, ai_size))
        if base <= others:
            continue
        ox, oy = it["x"], it["y"]
        spots = sorted(((x, y) for x in range(850, 1801, 50) for y in range(280, 821, 40)), key=lambda p: (p[0] - ox) ** 2 + (p[1] - oy) ** 2)
        done = False
        o_scale = it.get("scale")
        for k in ([1.0] + ([0.85, 0.7, 0.6] if o_scale else [])):               # too big for any free spot: shrink it a little (charts, boards, props) and look again
            if o_scale:
                it["scale"] = round(o_scale * k, 3)
                others = len(check_scene({**sc, "items": [i for i in items if i is not it]}, ai_size))
            for x, y in spots:
                it["x"], it["y"] = x, y
                if len(check_scene(sc, ai_size)) <= others:
                    done = True
                    break
            if done:
                break
        if done:
            moved += 1
        else:
            it["x"], it["y"] = ox, oy
            if o_scale:
                it["scale"] = o_scale
    return moved


def ai_sizes(proj):
    """{asset id: (w, h) in 1x px} of the project's AI pictures, so boxes of AI props are real, not a 200 px guess."""
    out = {}
    if proj:
        import agy_image as G
        for aid, e in G.load_manifest(proj)["assets"].items():
            if e.get("png_size"):
                out[aid] = (e["png_size"][0] / 2, e["png_size"][1] / 2)
    return out


def check(sb, proj=None):
    ai_size = ai_sizes(proj)
    out = []
    for sc in sb.get("scenes", []):
        out += check_scene(sc, ai_size)
    return out
