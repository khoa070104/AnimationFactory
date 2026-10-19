"""Storyboard builder: storyboard.json -> per-project assets, EffectCraft preview comps, PNG per scene, contact sheet, storyboard.md.
No per-scene code: scenes are data (see phase2/projects/video1_luong/storyboard.json).
Usage: python build_storyboard.py PROJECT_DIR"""
import json
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).parent))
import p2_svg as S
import layout as LAY
import sbload
import toolpaths
import build_motion_demo as B
import agy_image as G

TOK, A = S.TOK, S.A


hexrgb = lambda h: [int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)]


def load_model():
    """Cost/speed model: phase2/cost_model.json (written by calibrate.py from real jobs); defaults come from Phase 1 samples."""
    f = S.P2 / "cost_model.json"
    m = {"chars_per_sec": 12.0, "credits_per_char": 0.725, "basis": "default from 3 Phase 1 Edge jobs (65+8/101, 101+13/157, 25+3/40 credits/chars)"}
    if f.exists():
        m.update(json.loads(f.read_text(encoding="utf-8")))
    return m


MODEL = load_model()
CHARS_PER_SEC, CREDITS_PER_CHAR = MODEL["chars_per_sec"], MODEL["credits_per_char"]


def bg_rgb(name):
    """Scene background: token name (cream | blue) or any #RRGGBB."""
    if name == "cream":
        return hexrgb(TOK["bg"])
    if name == "blue":
        return hexrgb(TOK["bgAlt"])
    if isinstance(name, str) and name.startswith("#") and len(name) == 7:
        return hexrgb(name)
    raise SystemExit(f"unknown background {name!r} (use cream, blue or #RRGGBB)")
hexrgb = lambda h: [int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)]
COLORS = {"dark": TOK["text"]["dark"], "good": TOK["text"]["good"], "bad": TOK["text"]["bad"], "bi": hexrgb(TOK["bi"]), "white": [1, 1, 1]}


def ensure_assets(proj, sb):
    """Per-project asset copy (a project never reads or changes another project's assets). sb['character']['shirt'] recolours Bi."""
    out = proj / "assets"
    S.make_character(out, shirt=(sb.get("character") or {}).get("shirt"))
    S.make_props(out)
    S.ensure_png("arrow_down", S.arrow_down(), out)
    for k, v in A.items():
        S.ensure_png(f"sw_{k}", S.swatch(v), out)
    import characters as CHR
    for cid in CHR.used_ids(sb):                                    # AI characters: their part images live in the project's assets too
        if cid != CHR.BUILTIN:
            CHR.install(proj, cid, out / "png")
    return out


def sub_bar(out, text):
    """Subtitle backing bar sized to the text (fixed 84 px height, so text is always centred with padding)."""
    w = ((len(text) * 24 + 120 + 19) // 20) * 20
    name = f"subbar_{w}"
    S.ensure_png(name, S.subbar(w), out)
    return name, w


def ai_asset(proj, aid):
    """-> (status, png_path or None) for an Antigravity-generated asset registered in PROJECT/ai_assets/manifest.json.
    status is "approved" only when the file on disk is the exact image the owner approved (hash-bound); otherwise the reason
    (missing, draft, rejected, file_missing, changed_after_approval...)."""
    status, png, _why = G.approval_state(proj, aid)
    return status, png


def resolve_img(out, img, proj=None):
    """Prop image reference: a library name, or `ai:<id>` = an APPROVED AI asset (copied into the project's assets as ai_<id>)."""
    if not img.startswith("ai:"):
        return img
    aid = img[3:]
    status, png, why = G.approval_state(proj or out.parent, aid)       # `proj` when `out` is not PROJECT/assets (another renderer's asset folder)
    if status != "approved":
        raise SystemExit(f"AI asset {aid!r} is {status!r}{': ' + why if why else ''}: only approved assets can be used in scenes (agy_image.py approve)")
    dst = out / "png" / f"ai_{aid}.png"
    dst.parent.mkdir(parents=True, exist_ok=True)
    if not dst.exists() or dst.read_bytes() != png.read_bytes():
        dst.write_bytes(png.read_bytes())
    return f"ai_{aid}"


def bg_spec(out, name, proj=None):
    """Scene background -> (rgb, image name or None). `ai:<id>` = an APPROVED AI background (copied into the project assets), drawn over a cream base."""
    if isinstance(name, str) and name.startswith("ai:"):
        return hexrgb(TOK["bg"]), resolve_img(out, name, proj)
    return bg_rgb(name), None


def grid_cell_size(it):
    """Cell size from the content. cols >= 2: two lines (label above text), width from the longest text (~24 px per character at size 40). cols == 1: ONE line per row
    (label on the left, text after it) so a list of 7 rows stays narrow and short; a larger size asked for in the storyboard is kept."""
    cells = it.get("cells", [])
    ml = max([len(str(c.get("label", ""))) for c in cells] + [0])
    mt = max([len(str(c.get("text", ""))) for c in cells] + [0])
    if int(it.get("cols", 2) or 2) == 1:
        return max(int(it.get("cell_w", 0) or 0), 24 * (ml + mt) + 110, 300), max(int(it.get("cell_h", 0) or 0), 74)
    longest = max(ml, mt, 4)
    return max(int(it.get("cell_w", 0) or 0), 24 * longest + 60, 220), max(int(it.get("cell_h", 0) or 0), 120)


def expand(sc, out, proj=None):
    """Items -> primitive props/texts. Every primitive carries `appear` (seconds or a spoken cue phrase) for the animated build."""
    prims = []
    pn = sc.get("panel")
    if pn:                                                              # soft plate behind the content stack (layout.compose), drawn first
        pw, ph = int(pn[2] - pn[0]), int(pn[3] - pn[1])
        S.ensure_png(f"panel_{pw}x{ph}", S.panel(pw, ph), out)
        prims.append({"kind": "prop", "img": f"panel_{pw}x{ph}", "x": (pn[0] + pn[2]) / 2, "y": (pn[1] + pn[3]) / 2, "scale": 1.0, "rot": 0,
                      "appear": next((i.get("appear") for i in sc["items"] if i.get("type") in ("text", "grid", "chart", "legend", "pills", "notice", "bill", "pie")), None)})   # the plate comes with the first content item

    def P(img, x, y, s=1.0, r=0, ap=None):
        prims.append({"kind": "prop", "img": img, "x": x, "y": y, "scale": s, "rot": r, "appear": ap})

    def T(t, x, y, size, c="dark", r=0, ap=None):
        prims.append({"kind": "text", "text": t, "x": x, "y": y, "size": size, "color": c, "rot": r, "appear": ap})
    CONTENT_T = ("text", "grid", "chart", "legend", "pills", "notice", "bill", "pie")
    if pn:
        first = next((i for i in sc["items"] if i.get("type") in CONTENT_T), None)
        prims[0]["space"] = (first or {}).get("space", "world")
        prims[0]["item"] = "panel"
        content_items = [i for i in sc["items"] if i.get("type") in CONTENT_T]
        if len(content_items) == 1 and content_items[0].get("until") is not None:
            prims[0]["until"] = content_items[0]["until"]
    for idx, it in enumerate(sc["items"]):
        n0 = len(prims)
        ty, ap = it["type"], it.get("appear")
        if ty == "prop":
            P(resolve_img(out, it["img"], proj), it["x"], it["y"], it.get("scale", 1.0), it.get("rot", 0), ap)
        elif ty == "text":
            if str(sc.get("bg", "")).startswith("ai:") and not it.get("rot") and not pn:         # a picture background is busy: text gets the same soft plate as the subtitles
                w, h = int((len(it["text"]) * 0.56 * it["size"] + 90 + 19) // 20 * 20), int(it["size"] * 1.5)
                S.ensure_png(f"tbar_{w}x{h}", S.subbar(w, h), out)
                P(f"tbar_{w}x{h}", it["x"], it["y"] - 0.3 * it["size"], 1.0, 0, ap)
            T(it["text"], it["x"], it["y"], it["size"], it.get("color", "dark"), it.get("rot", 0), ap)
        elif ty == "notice":
            icon = it.get("icon", "check")
            nw = LAY.notice_width(it)
            if icon == "check" and nw == 600:
                P("card", it["x"], it["y"], 1.0, 0, ap)
            else:
                S.ensure_png(f"nplate_{icon}_{nw}", S.notice_plate(icon, nw), out)
                P(f"nplate_{icon}_{nw}", it["x"], it["y"], 1.0, 0, ap)
            dx = 68 if icon != "none" else 0
            T(it["amount"], it["x"] + dx, it["y"] - 20, 54, {"check": "good", "warn": "bad"}.get(icon, "dark"), 0, ap)
            T(it["caption"], it["x"] + dx + 4, it["y"] + 38, 40, "dark", 0, ap)
        elif ty == "chart":
            k, x, y = it["scale"], it["x"], it["y"]
            P("board", x, y, k, 0, ap)
            T(it["title"], x, y - 222 * k, 54, "dark", 0, ap)
            base = y + 205 * k
            n = len(it["bars"])
            for i, b in enumerate(it["bars"]):
                cx = x + (i - (n - 1) / 2) * 200
                h = int(b["value"] * it.get("unit_h", 60) + 20)
                name = f"bar_{sc['id']}_{i}"
                S.ensure_png(name, S.bar(A[b["color"]], 120, h), out)
                bap = b.get("appear", ap)
                P(name, cx, base - h / 2, 1.0, 0, bap)
                T(b["text"], cx, base - h - 36, 46, "dark", 0, bap)
                T(b["label"], cx, base + 40, 40, "dark", 0, ap)
        elif ty == "pills":
            # label capsules size themselves to the longest text (coin + left-aligned text), so any wording fits
            size = it.get("size", 50)
            maxlen = max(len(t) for t in it["texts"])
            W = max(560, int(((maxlen * 0.62 * size + 190) + 19) // 20 * 20))
            pname = f"pill_{W}"
            S.ensure_png(pname, S.pill(W), out)
            for i, t in enumerate(it["texts"]):
                y = it["y"] + i * it["gap"]
                pap = (it.get("appears") or [ap] * len(it["texts"]))[i]
                P(pname, it["x"], y, 1.0, 0, pap)
                mk = it.get("marker", "number")                 # list marker: number (default, 1-2-3), dot, or coin (money lists only)
                if mk == "coin":
                    P("coin", it["x"] - W / 2 + 62, y, 0.9, 0, pap)
                else:
                    S.ensure_png("badge", S.badge(), out)
                    P("badge", it["x"] - W / 2 + 62, y, 1.0, 0, pap)
                    if mk == "number":
                        prims.append({"kind": "text", "text": str(i + 1), "x": it["x"] - W / 2 + 62, "y": y + round(0.32 * 44), "size": 44, "color": "dark", "rot": 0, "appear": pap, "align": "center"})
                prims.append({"kind": "text", "text": t, "x": it["x"] - W / 2 + 120, "y": y + round(0.32 * size), "size": size, "color": "dark", "rot": 0, "appear": pap, "align": "left"})
        elif ty == "compare":
            # two bars side by side, height proportional to the value (largest = 300 px); value above, label below, optional caption
            x0, y0 = it["x"], it["y"]
            sides = [it["left"], it["right"]]
            vmax = max(s_["value"] for s_ in sides) or 1
            base = y0 + 170                                          # bars end here; the tallest (280 px) tops out at y0-110, its value sits above it, the title above that
            if it.get("title"):
                T(it["title"], x0, y0 - 205, 42, "dark", 0, ap)
            for k_, sd in enumerate(sides):
                cx = x0 + (-130 if k_ == 0 else 130)
                h_ = max(20, int(280 * sd["value"] / vmax))
                name = f"cmp_{sd.get('color', 'blue')}_{h_}"
                S.ensure_png(name, S.bar(A[sd.get("color", "blue")], 150, h_), out)
                sap = sd.get("appear", ap)
                P(name, cx, base - h_ / 2, 1.0, 0, sap)
                T(f"{sd['value']:g}{it.get('unit', '')}", cx, base - h_ - 24, 46, "dark", 0, sap)
                T(sd["label"], cx, base + 54, 40, "dark", 0, sap)
                if sd.get("text"):
                    T(sd["text"], cx, base + 100, 36, "dark", 0, sap)
        elif ty == "highlight":
            w_, h_ = int(it["w"]), int(it["h"])
            name = f"ring_{it.get('color', 'red')}_{w_}x{h_}"
            S.ensure_png(name, S.ring(w_, h_, A.get(it.get("color", "red"), "#e0584f")), out)
            P(name, it["x"], it["y"], 1.0, 0, ap)
        elif ty == "grid":
            # a table of cells drawn by the tool (so the Vietnamese text is exact); cells fill in one by one at their own cue
            cells = it["cells"]
            cw, chh = grid_cell_size(it)
            cols = max(1, int(it.get("cols", 2)))
            rows = -(-len(cells) // cols)
            gap = 14
            top = it["y"] + (35 if it.get("title") else 0)
            cname = f"cell_{cw}x{chh}"
            S.ensure_png(cname, S.cell(cw, chh), out)
            if it.get("title"):
                T(it["title"], it["x"], top - (rows - 1) / 2 * (chh + gap) - chh / 2 - 28, 48, "dark", 0, ap)
            for i, c in enumerate(cells):
                r_, c_ = divmod(i, cols)
                cx = it["x"] + (c_ - (cols - 1) / 2) * (cw + gap)
                cy = top + (r_ - (rows - 1) / 2) * (chh + gap)
                cap = c.get("appear", ap)
                P(cname, cx, cy, 1.0, 0, ap)
                if cols == 1:                                            # one line: label | text
                    lab_w = 24 * max([len(str(k.get("label", ""))) for k in cells] + [0]) + 24
                    if c.get("label"):
                        prims.append({"kind": "text", "text": c["label"], "x": cx - cw / 2 + 24, "y": cy + 13, "size": 40, "color": "dark", "rot": 0, "appear": ap, "align": "left"})
                    if c.get("text"):
                        prims.append({"kind": "text", "text": c["text"], "x": cx - cw / 2 + 24 + lab_w, "y": cy + 13, "size": 40, "color": "good", "rot": 0, "appear": cap, "align": "left"})
                    continue
                if c.get("label"):
                    T(c["label"], cx, cy - 12, 40, "dark", 0, ap)
                if c.get("text"):
                    T(c["text"], cx, cy + 38, 40, "good", 0, cap)
        elif ty == "pie":
            name = f"pie_{sc['id']}"
            S.ensure_png(name, S.pie([(p["value"], A[p["color"]]) for p in it["parts"]]), out)
            P(name, it["x"], it["y"], it["scale"], 0, ap)
        elif ty == "legend":
            size = it.get("size", 48)
            maxlen = max(len(r["text"]) for r in it["rows"])
            left = it["x"] - maxlen * 0.26 * size      # block roughly centred on x; text is LEFT-aligned, swatches in one column
            for i, r in enumerate(it["rows"]):
                y = it["y"] + i * it["gap"]
                rap = r.get("appear", ap)
                prims.append({"kind": "text", "text": r["text"], "x": left, "y": y + round(0.32 * size), "size": size, "color": "dark", "rot": 0, "appear": rap, "align": "left"})
                P(f"sw_{r['color']}", left - 40 * size / 48, y, 1.0, 0, rap)
        elif ty == "bill":
            k = it["scale"] / 1.55
            x, y, r = it["x"], it["y"], it.get("rot", 0)
            P("bill", x, y, it["scale"], r, ap)
            T(it["head"], x + 10 * k, y - 248 * k, 58 * k, "white", r, ap)
            T(it["title"], x + 2 * k, y - 25 * k, 84 * k, "dark", r, ap)
            T(it["amount"], x + 8 * k, y + 110 * k, 72 * k, "bad", r, ap)
        else:
            raise SystemExit(f"unknown item type {ty!r} in scene {sc['id']}")
        for p_ in prims[n0:]:
            p_["space"] = it.get("space", "world")
            p_["item"] = idx
            if it.get("until") is not None:
                p_["until"] = it["until"]
    for sub in sc["subtitles"]:
        if len(sub) > 56:
            raise SystemExit(f"subtitle too long ({len(sub)} chars, max 56) in {sc['id']}: {sub}")
    return prims


def stats(sb):
    tm = sb.get("timing", {"lead": 0.3, "tail": 0.5})
    rows = []
    for sc in sb["scenes"]:
        c = len(sc["voice"])
        pad = tm["lead"] + tm.get("word_pad", 0.15) + sc.get("hold_after", tm["tail"])
        rows.append({"id": sc["id"], "chars": c, "sec": round(c / CHARS_PER_SEC + pad, 1), "credits": round(c * CREDITS_PER_CHAR)})
    return rows


def main():
    proj = Path(sys.argv[1]).resolve()
    sb = sbload.load_storyboard(proj)
    out = ensure_assets(proj, sb)
    scenes = []
    for sc in sb["scenes"]:
        sub = max(sc["subtitles"], key=len)
        scenes.append({"id": sc["id"], "bg": sc["bg"], "bi": {**sc["bi"], "rig": sc["bi"].get("char")}, "cast": [{**c, "rig": c.get("char")} for c in sc.get("cast", [])], "holds": [{**h, "prop": resolve_img(out, h["prop"])} for h in sc.get("holds", [])], "prims": expand(sc, out),
                       "bgRGB": bg_spec(out, sc["bg"])[0], "bgImage": bg_spec(out, sc["bg"])[1], "subtitle": sub, "subbar": sub_bar(out, sub)[0], "subtitleY": sc.get("subtitle_y", 1030)})
    pr = B.params(proj / "previews/storyboard_preview.ecproj")
    import characters as CHR
    pr.update({"assets": str(out).replace("\\", "/"), "scenes": scenes, "colors": {**{k: v for k, v in COLORS.items()}}, "rigs": CHR.rigs_for(proj, sb)})
    (proj / "previews").mkdir(exist_ok=True)
    jsx = proj / "previews/_scenes.jsx"
    jsx.write_text("var P = " + json.dumps(pr, ensure_ascii=False) + ";\n" + B.jsx_text("bi_rig.jsx", "bi_motion.jsx", "scene_static.jsx"), encoding="utf-8")
    Path(pr["out"]).unlink(missing_ok=True)
    print(B.run_script(jsx))
    tiles = []
    for sc in sb["scenes"]:
        f = proj / f"previews/{sc['id']}.png"
        r = subprocess.run([B.EC, "--project", pr["out"], "render-frame", "--comp", sc["id"], "--time", "0", "--out", str(f)], capture_output=True, text=True)
        if r.returncode:
            sys.exit(r.stderr)
        im = Image.open(f).convert("RGB").resize((640, 360))
        ImageDraw.Draw(im).text((8, 6), f"{sc['id']}  {sc['title']}", fill=(180, 0, 0), font=ImageFont.truetype(toolpaths.font(), 18))
        tiles.append(im)
    cols = 3
    rows = (len(tiles) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * 650 + 10, rows * 370 + 10), (255, 255, 255))
    for i, im in enumerate(tiles):
        sheet.paste(im, (10 + (i % cols) * 650, 10 + (i // cols) * 370))
    sheet.save(proj / "previews/contact_sheet.png")
    st = stats(sb)
    tot = {"chars": sum(r["chars"] for r in st), "sec": round(sum(r["sec"] for r in st), 1), "credits": sum(r["credits"] for r in st)}
    (proj / "estimate.json").write_text(json.dumps({"scenes": st, "total": tot, "assumptions": {
        "chars_per_sec": CHARS_PER_SEC, "credits_per_char": CREDITS_PER_CHAR, "basis": MODEL["basis"],
        "note": "estimate for the Edge voice incl. word timings; other voices/providers may price differently; credits, not money"}},
        ensure_ascii=False, indent=2), encoding="utf-8")
    make_docs(proj, sb, st, tot)
    print("scenes", len(st), "total", tot)


def voice_note(proj):
    f = proj / "status.json"
    if f.exists():
        st = json.loads(f.read_text(encoding="utf-8"))
        if st.get("voice_generated"):
            return f"**Giọng đã tạo:** {st.get('api_calls', 0)} lượt gọi, {st.get('credits_spent', 0)} credit thực tế."
    return "**Chưa gọi API giọng nói.**"


def make_docs(proj, sb, st, tot):
    """storyboard.md (for approval), script_v1.md (voice text only), status.json."""
    sc_by = {r["id"]: r for r in st}
    L = [f"# Storyboard · {sb['title']} (v{sb['version']})", "",
         f"**Trạng thái:** {sb.get('status', '')}. {voice_note(proj)} Đối tượng: {sb.get('audience', '—')}.", "",
         f"**Thông điệp:** {sb.get('message', '')}", "",
         "![Tổng quan](previews/contact_sheet.png)", "",
         "## Tổng hợp",
         f"- {len(st)} cảnh, {tot['chars']} ký tự lời đọc, **ước tính {tot['sec']} giây** (tốc độ đọc ≈ {CHARS_PER_SEC:.1f} ký tự/giây, cộng khoảng nghỉ đầu/cuối cảnh theo cấu hình `timing`/`hold_after`).",
         f"- **Ước tính chi phí giọng đọc: ≈ {tot['credits']} credit** cho lần tạo đầu (giọng Edge `{sb['voice']['voice_id']}`, kèm mốc thời gian từng từ). Cách tính: {CREDITS_PER_CHAR:.3f} credit/ký tự ({MODEL['basis']}). Đây là ước tính, chỉ áp dụng cho giọng Edge, không quy ra tiền; số thật sẽ ghi vào log sau khi chạy.",
         "- Sửa lời một cảnh chỉ tạo lại giọng của cảnh đó (tính theo ký tự cảnh đó); lời, giọng, tốc độ không đổi thì không gọi API.", "",
         "| Cảnh | Tiêu đề | Ký tự | Ước tính (s) | Credit | Chuyển cảnh |", "|---|---|---|---|---|---|"]
    for sc in sb["scenes"]:
        r = sc_by[sc["id"]]
        L.append(f"| {sc['id']} | {sc['title']} | {r['chars']} | {r['sec']} | {r['credits']} | {sc['transition']} |")
    for sc in sb["scenes"]:
        r = sc_by[sc["id"]]
        texts = [it["text"] for it in sc["items"] if it["type"] == "text"]
        props = sorted({it.get("img", it["type"]) for it in sc["items"] if it["type"] != "text"})
        acts = []
        for a in sc.get("actions", []):
            when = f"tại cụm “{a['cue']}”" if "cue" in a else f"lúc {a.get('at', 0)} s"
            acts.append(f"`{a['name']}` {when}")
        faces = [f"“{f['cue']}” → {f['face']}" for f in sc.get("face_cues", [])]
        L += ["", f"## {sc['id']} · {sc['title']}", "", f"![{sc['id']}](previews/{sc['id']}.png)", "",
              f"- **Lời đọc:** {sc['voice']}",
              f"- **Phụ đề (từng đoạn, 1 dòng):** " + " / ".join(sc["subtitles"]),
              f"- **Nhân vật:** Bi, biểu cảm `{sc['bi']['face']}`, tư thế mở đầu `{sc['bi']['pose']}`" + (f", cầm {', '.join(h['prop'] for h in sc['holds'])}" if sc.get("holds") else ""),
              f"- **Hành động:** " + ("; ".join(acts) if acts else "(giữ tư thế)") + (f". Đổi biểu cảm: {'; '.join(faces)}" if faces else ""),
              f"- **Bối cảnh:** nền `{sc['bg']}`",
              f"- **Đạo cụ / hình:** " + (", ".join(props) if props else "-"),
              f"- **Chữ trên màn hình:** " + (" · ".join(texts) if texts else "(chữ nằm trong biểu đồ/hóa đơn)"),
              f"- **Chuyển cảnh:** {sc['transition']}"]
    points = sb.get("review_points") or ["Nội dung và thứ tự các cảnh.", "Lời đọc từng cảnh (đây là văn bản sẽ gửi API).", "Số liệu minh họa nếu có.", "Giọng đọc."]
    L += ["", "## Điểm cần bạn duyệt"] + [f"{i + 1}. {p}" for i, p in enumerate(points)] + \
         ["", "Sau khi bạn duyệt: tôi mới gọi API giọng nói (một lần cho từng cảnh), rồi dựng bản xem thử."]
    (proj / "storyboard.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    (proj / "script_v1.md").write_text(f"# {sb['title']} · kịch bản lời đọc v{sb['version']}\n\n" + "\n\n".join(
        f"**{sc['id']} · {sc['title']}**\n{sc['voice']}" for sc in sb["scenes"]) + "\n", encoding="utf-8")
    if (proj / "status.json").exists():
        return                       # never overwrite approvals / API counters
    status = {"project": sb["project"], "storyboard_version": sb["version"], "state": "storyboard_draft_awaiting_approval",
              "approved": {"script": None, "storyboard": None}, "voice_generated": False,
              "api_calls": 0, "credits_spent": 0, "estimate": tot, "updated": "2026-10-18"}
    (proj / "status.json").write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
