"""What the tool really supports, as data: used by the UI forms (only real options are offered) and by the AI steps (the LLM may only choose
from this catalog; its output is then checked by validate_storyboard). Everything is derived from the same sources the validator and the
builders use (lib/bi_motion.jsx, p2_svg, validate_storyboard, sbload), so it cannot drift from the code; tests enforce that.
  python capabilities.py          print the catalog"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import p2_svg as S
import sbload
import shots as SH
import validate_storyboard as V

P2 = S.P2

ACTION_INFO = {
    "enter": {"label": "Bước vào khung hình", "params": ["at"], "note": "dùng ở cảnh đầu hoặc khi nhân vật mới xuất hiện"},
    "point": {"label": "Chỉ tay vào hình bên phải", "params": ["cue|at", "hold"], "note": "một lần chỉ"},
    "point_seq": {"label": "Chỉ lần lượt nhiều mục", "params": ["cues", "hold"], "note": "mỗi cụm trong cues là một lần chỉ; cần ít nhất 2"},
    "cheer": {"label": "Giơ hai tay ăn mừng", "params": ["cue|at", "hold"], "note": "kết quả tích cực"},
    "wave": {"label": "Vẫy tay", "params": ["cue|at"], "note": "chào / tạm biệt"},
    "cheek": {"label": "Tay đỡ má, lo lắng", "params": ["cue|at", "hold"], "note": "vấn đề, băn khoăn"},
    "hold_phone": {"label": "Cầm điện thoại", "params": ["cue|at", "hold"], "note": "nhắc đến điện thoại / ứng dụng"},
    "shrug": {"label": "Nhún vai", "params": ["cue|at"], "note": "không chắc, không biết"},
    "write": {"label": "Viết (tay phải viết, tay trái giữ sổ)", "params": ["cue|at", "hold"], "note": "chỉ đẹp khi cảnh có holds: sổ ở tay trái (side L) và bút ở tay phải (side R)"},
    "carry": {"label": "Xách đồ bằng một tay", "params": ["cue|at", "hold"], "note": "dùng với holds: giỏ/túi ở tay trái (side L)"},
    "nod": {"label": "Gật đầu", "params": ["cue|at"], "note": "đồng ý, khẳng định"},
}

NUM = "number"
ITEM_FIELDS = {
    "prop": [("img", "prop_img", True), ("x", NUM, True), ("y", NUM, True), ("scale", NUM, False), ("rot", NUM, False), ("appear", "appear", False)],
    "text": [("text", "string", True), ("x", NUM, True), ("y", NUM, True), ("size", NUM, True), ("color", "text_color", False), ("rot", NUM, False), ("appear", "appear", False)],
    "notice": [("amount", "string", True), ("caption", "string", True), ("x", NUM, True), ("y", NUM, True), ("appear", "appear", False)],
    "chart": [("title", "string", True), ("x", NUM, True), ("y", NUM, True), ("scale", NUM, True), ("unit_h", NUM, False), ("appear", "appear", False),
              ("bars", "list:bar", True)],
    "pills": [("texts", "list:string", True), ("x", NUM, True), ("y", NUM, True), ("gap", NUM, True), ("size", NUM, False), ("appears", "list:appear", False), ("marker", "string", False)],
    "grid": [("title", "string", False), ("x", NUM, True), ("y", NUM, True), ("cols", NUM, True), ("cell_w", NUM, False), ("cell_h", NUM, False), ("cells", "list:cell", True), ("appear", "appear", False)],
    "compare": [("title", "string", False), ("x", NUM, True), ("y", NUM, True), ("left", "object", True), ("right", "object", True), ("unit", "string", False), ("appear", "appear", False)],
    "highlight": [("x", NUM, True), ("y", NUM, True), ("w", NUM, True), ("h", NUM, True), ("color", "string", False), ("appear", "appear", False)],
    "pie": [("x", NUM, True), ("y", NUM, True), ("scale", NUM, True), ("appear", "appear", False), ("parts", "list:part", True)],
    "legend": [("x", NUM, True), ("y", NUM, True), ("gap", NUM, True), ("size", NUM, False), ("appear", "appear", False), ("rows", "list:row", True)],
    "bill": [("head", "string", True), ("title", "string", True), ("amount", "string", True), ("x", NUM, True), ("y", NUM, True), ("scale", NUM, True), ("rot", NUM, False),
             ("appear", "appear", False)],
}
for _f in ITEM_FIELDS.values():                                              # every item can live in the camera's world (default) or on the fixed screen layer
    _f.append(("space", "string", False))
    _f.append(("until", "appear", False))
SUB_FIELDS = {
    "bar": [("label", "string", True), ("value", NUM, True), ("text", "string", True), ("color", "accent", True), ("appear", "appear", False)],
    "part": [("value", NUM, True), ("color", "accent", True)],
    "row": [("text", "string", True), ("color", "accent", True), ("appear", "appear", False)],
    "cell": [("label", "string", False), ("text", "string", False), ("appear", "appear", False)],
}
ITEM_HINT = {
    "prop": "một hình đạo cụ trong thư viện hoặc ảnh AI đã duyệt (ai:<id>)", "text": "dòng chữ trên màn hình (cỡ chữ ≥ 40)",
    "notice": "thẻ thông báo có số tiền và chú thích", "grid": "bảng ô (lịch tuần, danh sách): cells = [{label, text, appear}], mỗi ô tối đa 14 ký tự chữ, điền lần lượt theo lời đọc", "compare": "so sánh hai phía: left/right = {label, value, color, text?, appear?}; chiều cao cột theo tỷ lệ giá trị", "highlight": "khung nét đứt khoanh một vùng (x,y là tâm, w,h) để nhấn", "chart": "biểu đồ cột (mỗi cột có giá trị, nhãn, màu)", "pills": "danh sách nhãn viên thuốc, tự co theo chữ",
    "pie": "biểu đồ tròn", "legend": "chú giải màu + chữ, căn trái", "bill": "hóa đơn (đầu, tiêu đề, số tiền)",
}


def capabilities(proj=None):
    """The catalog. With a project: also its AI assets that scenes may use (approved, hash-bound)."""
    ai, chars = [], [{"id": "bi", "name": "Bi", "role": "built-in", "status": "builtin", "description": "người que cam có sẵn"}]
    if proj:
        import agy_image as G
        import characters as CHR
        for cid in CHR.list_ids(proj):
            prof = CHR.get_profile(proj, cid)
            chars.append({"id": cid, "name": prof["name"], "role": prof["role"], "status": CHR.state(proj, cid)[0], "description": prof["description"]})
        for aid, e in G.load_manifest(proj)["assets"].items():
            st = G.approval_state(proj, aid)[0]
            ai.append({"id": aid, "kind": e.get("kind"), "status": st, "usable": st == "approved"})
    return {
        "canvas": {"w": 1920, "h": 1080, "character_zone": "nhân vật Bi đứng bên trái (x≈500, y≈930); đồ họa nên đặt nửa phải x≈1000-1800, y≈250-800; phụ đề ở dưới (y≈1030)"},
        "actions": [{"name": n, **ACTION_INFO[n]} for n in sorted(V.ACTIONS)],
        "poses": sorted(V.POSES), "faces": sorted(V.FACES), "props": sorted(V.PROP_IMGS), "ai_assets": ai, "characters": chars,
        "character_note": "nhân vật chính = bi.char; nhân vật phụ (tối đa 3) = cast[]; mỗi nhân vật có actions/face_cues riêng; mọi nhân vật dùng cùng thư viện hành động",
        "shots": {"note": "scene.shots (optional; absent = one implicit wide shot). Remotion renderer only. Camera frames `focus` at `size`; starts increase; end earlier than the next start = gap (wide), later = overlap (refused); characters keep their pose across cuts.",
                  "kinds": list(SH.KINDS), "sizes": list(SH.SIZES), "focus": "main | cast1.. | item:<index|img> | [x, y, w, h]", "gaze": "[{who, at}] at = cast1 | item:.. | left | right | [x, y]",
                  "max_zoom": SH.MAX_ZOOM, "item_space": "item.space = world (follows the camera, default) | screen (fixed); subtitles are always screen"},
        "backgrounds": ["cream", "blue", "#RRGGBB", "ai:<id>"], "text_colors": sorted(V.TEXT_COLORS), "accent_colors": sorted(S.A),
        "camera_presets": sorted(sbload.CAMERA_PRESETS), "transitions": ["cut", "fade-out"],
        "transition_note": "chỉ có cắt thẳng và mờ dần ở cảnh cuối; các nhãn khác được coi là cắt thẳng",
        "item_types": {t: {"hint": ITEM_HINT[t], "fields": [{"name": n, "type": ty, "required": r} for n, ty, r in f]} for t, f in ITEM_FIELDS.items()},
        "sub_fields": {k: [{"name": n, "type": ty, "required": r} for n, ty, r in f] for k, f in SUB_FIELDS.items()},
        "appear_note": "appear = số giây từ đầu cảnh, hoặc một cụm từ NẰM TRONG lời đọc của cảnh (hình hiện đúng lúc đọc đến cụm đó)",
        "rules": {"subtitle_max_chars": 56, "subtitles": "để 'auto' (tool tự chia theo lời đọc, ≤40 ký tự mỗi dòng)",
                  "holds": "nhân vật cầm đạo cụ: {who:'main'|'cast1'.., side:'L'|'R', prop: tên thư viện (pen, basket, phone, calculator) hoặc ai:<id>}; kích thước/điểm cầm có mặc định; kết hợp với action write/carry/hold_phone",
                  "scene_target": [6, 10], "duration_target": [60, 90]},
    }


def scene_schema():
    """JSON schema (the subset agy/our checker understands) for one storyboard scene; items are one flat object type with `type` required."""
    item_props = {"type": {"type": "string", "enum": sorted(ITEM_FIELDS)}}
    for t, f in ITEM_FIELDS.items():
        for n, ty, _ in f:
            if n in item_props:
                continue
            if ty == NUM:
                item_props[n] = {"type": "number"}
            elif ty == "object":
                item_props[n] = {"type": "object", "properties": {"label": {"type": "string"}, "value": {"type": "number"}, "color": {"type": "string"}, "text": {"type": "string"}, "appear": {"type": ["string", "number"]}}}
            elif ty.startswith("list:"):
                sub = ty[5:]
                item_props[n] = {"type": "array", "items": ({"type": "string"} if sub == "string" else {"type": ["string", "number"]} if sub == "appear" else
                                                           {"type": "object", "properties": {sn: ({"type": "number"} if sty == NUM else {"type": "string"}) for sn, sty, _ in SUB_FIELDS[sub]},
                                                            "required": [sn for sn, _, r in SUB_FIELDS[sub] if r]})}
            else:
                item_props[n] = {"type": "string"} if n != "appear" else {"type": ["string", "number"]}
    return {"type": "object", "required": ["id", "title", "voice", "bg", "bi", "items"], "properties": {
        "id": {"type": "string"}, "title": {"type": "string"}, "voice": {"type": "string"}, "bg": {"type": "string"}, "transition": {"type": "string"},
        "bi": {"type": "object", "required": ["x", "y", "scale", "face", "pose"], "properties": {"x": {"type": "number"}, "y": {"type": "number"}, "scale": {"type": "number"},
                                                                                              "face": {"type": "string", "enum": sorted(V.FACES)}, "pose": {"type": "string", "enum": sorted(V.POSES)},
                                                                                              "char": {"type": "string"}, "flip": {"type": "boolean"}}},
        "cast": {"type": "array", "maxItems": 3, "items": {"type": "object", "required": ["char", "x", "y", "scale", "face", "pose"], "properties": {
            "char": {"type": "string"}, "x": {"type": "number"}, "y": {"type": "number"}, "scale": {"type": "number"}, "flip": {"type": "boolean"},
            "face": {"type": "string", "enum": sorted(V.FACES)}, "pose": {"type": "string", "enum": sorted(V.POSES)},
            "actions": {"type": "array", "items": {"type": "object", "required": ["name"], "properties": {"name": {"type": "string", "enum": sorted(V.ACTIONS)}, "cue": {"type": "string"},
                                                                                                       "cues": {"type": "array", "items": {"type": "string"}}, "at": {"type": "number"}, "hold": {"type": "number"}}}},
            "face_cues": {"type": "array", "items": {"type": "object", "required": ["cue", "face"], "properties": {"cue": {"type": "string"}, "face": {"type": "string", "enum": sorted(V.FACES)}}}}}}},
        "actions": {"type": "array", "items": {"type": "object", "required": ["name"], "properties": {
            "name": {"type": "string", "enum": sorted(V.ACTIONS)}, "cue": {"type": "string"}, "cues": {"type": "array", "items": {"type": "string"}},
            "at": {"type": "number"}, "hold": {"type": "number"}}}},
        "face_cues": {"type": "array", "items": {"type": "object", "required": ["cue", "face"], "properties": {"cue": {"type": "string"}, "face": {"type": "string", "enum": sorted(V.FACES)}}}},
        "holds": {"type": "array", "items": {"type": "object", "required": ["side", "prop"], "properties": {"who": {"type": "string"}, "side": {"type": "string", "enum": ["L", "R"]}, "prop": {"type": "string"}}}},
        "action_gaps": {"type": "array", "items": {"type": "string"}},
        "items": {"type": "array", "items": {"type": "object", "required": ["type"], "properties": item_props}},
        "camera": {"type": "string"}, "hold_after": {"type": "number"},
        "shots": {"type": "array", "items": {"type": "object", "required": ["id"], "properties": {
            "id": {"type": "string"}, "purpose": {"type": "string"}, "start": {"type": ["string", "number"]}, "end": {"type": ["string", "number"]},
            "kind": {"type": "string", "enum": list(SH.KINDS)}, "size": {"type": "string", "enum": list(SH.SIZES)}, "focus": {"type": ["string", "array"]},
            "pad": {"type": "number"}, "cut": {"type": "boolean"}, "ease": {"type": "number"},
            "gaze": {"type": "array", "items": {"type": "object", "required": ["at"], "properties": {"who": {"type": "string"}, "at": {"type": ["string", "array"]}}}}}}}}}


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    print(json.dumps(capabilities(sys.argv[1] if len(sys.argv) > 1 else None), ensure_ascii=False, indent=1))
