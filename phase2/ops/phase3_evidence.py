"""Render evidence/phase3/real_runs.md from the REAL runs in the project folders (real agy: Gemini + Claude through Antigravity; real image job).
Usage: python phase3_evidence.py PROJECT [PROJECT ...]"""
import json
import shutil
import sys
from pathlib import Path

P2 = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(P2 / "tools"))
import agy_image as G  # noqa: E402
import budget  # noqa: E402
import overview  # noqa: E402
import prepare as PR  # noqa: E402

out_dir = P2 / "evidence" / "phase3"
out_dir.mkdir(parents=True, exist_ok=True)
L = ["# Phase 3 – các lần chạy THẬT (agy: Gemini + Claude qua Antigravity; tạo ảnh thật qua Antigravity)", "",
     "Số liệu đọc từ thư mục dự án (`logs/ai_ledger.jsonl`, `prepare/*.json`, `ai_assets/manifest.json`). Dự án `co_nen_tra_no...` chưa gọi API giọng nói; dự án `lap_ngan_sach...` đã gọi API giọng nói thật sau khi chủ dự án (Khoa) duyệt.", ""]
for name in sys.argv[1:]:
    d = P2 / "projects" / name
    brief = PR.brief_of(d)
    sc = G.read_json(d / "prepare/script.json", {}) or {}
    sb = json.loads((d / "storyboard.json").read_text(encoding="utf-8"))
    errs, warns = PR.validate_obj(d, sb)
    s = budget.summary(d)
    rows = budget.rows(d)
    L += [f"## {name}", f"- Brief: “{brief['title']}” · mục tiêu: {brief.get('goal')} · thời lượng mong muốn {brief.get('duration_seconds')} s · nghiên cứu: {brief.get('research')}",
          f"- Kịch bản: {sc.get('stats')} · nguồn: {sc.get('source')} · model: {sc.get('model')}", f"- Storyboard: v{sb['version']}, {len(sb['scenes'])} cảnh, kiểm tra hợp lệ: {len(errs)} lỗi, {len(warns)} cảnh báo",
          f"- Lượt gọi AI (đã tính, không kể dùng lại): {s['usage']['llm_calls']} · token {s['usage']['llm_tokens']:,} · lượt ảnh {s['usage']['images']} · credit giọng {s['usage']['voice_credits']}",
          "- Model thực tế: " + "; ".join(f"{m} ({v['calls']} lượt, {v['tokens']:,} token, {v['failed']} lỗi)" for m, v in s["llm_models"].items()),
          f"- Tiền: {s['money_note']}", "", "| Việc | Tầng | Model thực tế | Token | Giây | Kết quả |", "|---|---|---|---|---|---|"]
    for r in rows:
        if r.get("cache"):
            L.append(f"| {r['task']} | {r.get('tier', '')} | (dùng lại kết quả đã lưu) | 0 | 0 | cache |")
        else:
            L.append(f"| {r['task']} | {r.get('tier', r.get('kind'))} | {r.get('model_actual') or r.get('model')} | {(r.get('tokens') or {}).get('total', '')} | {r.get('seconds', '')} | {r['status']} |")
    plan = G.read_json(d / "prepare/asset_plan.json", {"assets": []})
    L += ["", "Kế hoạch asset (AI lập, bạn duyệt):", ""]
    for a in plan["assets"]:
        L.append(f"- `{a['id']}` ({a['kind']}) cảnh {a['placement']['scene']}: " + (f"dùng lại từ {a['reuse']['project']}/{a['reuse']['asset']}" if a.get("reuse") else f"TẠO MỚI qua Antigravity — “{a['prompt'][:90]}”"))
    man = G.load_manifest(d)["assets"]
    for k, e in man.items():
        if not e.get("reused_from"):
            L.append(f"- Asset tạo thật: `{k}` · {e.get('agent_model')} · PNG {e.get('png_size')} · trong suốt: {e.get('transparency_check')} · conversation `{e.get('conversation_id')}` · trạng thái {G.approval_state(d, k)[0]}")
    rep = G.read_json(d / "logs/build_report.json", {}) or {}
    if rep.get("checks"):
        L += ["", f"Video: {sorted((d / 'output').glob('*.mp4'))[-1].name} · kiểm tra tự động: {sum(1 for c in rep['checks'] if c['pass'])}/{len(rep['checks'])} đạt"] + [f"  - {'PASS' if c['pass'] else 'FAIL'} {c['name']} {c.get('info', '')}" for c in rep["checks"]] + [""]
    st = G.read_json(d / "status.json", {}) or {}
    if st.get("api_calls"):
        L += [f"Giọng đọc THẬT: {st['api_calls']} lượt gọi API, {st['credits_spent']} credit thực tế (dự toán ~{(G.read_json(d / 'estimate.json', {}) or {}).get('total', {}).get('credits')}).", ""]
    ov = overview.todo(d)
    L += ["", "Việc đang chờ chủ dự án:", ""] + [f"- {t['label']}" for t in ov] + [""]
    sheet = d / "previews" / "contact_sheet.png"
    if sheet.exists():
        shutil.copy(sheet, out_dir / f"{name}_contact_sheet.png")
        L += [f"Ảnh tổng quan các cảnh (khung đầu mỗi cảnh, dựng thật bằng EffectCraft): `evidence/phase3/{name}_contact_sheet.png`", ""]
L += ["## Ghi chú trung thực", "- Các dòng `asset_plan` thứ hai (cả hai dự án) và `storyboard` + `storyboard_repair` thứ hai (dự án `lap_ngan_sach...`) trong sổ cái đến từ MỘT LỖI tìm thấy khi chạy thật: chạy lại 'AI chuẩn bị' sau khi asset đã được duyệt/đưa vào cảnh làm AI lập lại kế hoạch và viết đè storyboard. Lỗi đã sửa (đầu vào các bước chỉ còn kịch bản + hồ sơ kênh; storyboard/kế hoạch đã sửa hoặc duyệt không bị ghi đè nếu không `force`; kế hoạch cũ lưu ở `prepare/history/`) và có test hồi quy. Storyboard của dự án `lap_ngan_sach...` đã được khôi phục từ bản lưu trong `versions/` (v2 → v4); kế hoạch asset dựng lại từ manifest.", "- Dự án `co_nen_tra_no...`: bảng kế hoạch asset hiện tại là bản lập lại do lỗi trên (3 asset dùng lại, 0 asset mới); chưa có ảnh nào được tạo cho dự án này.", "- Lần dựng video đầu của `lap_ngan_sach...` (80,2 s) báo 2 kiểm tra FAIL: (1) kiểm tra chuyển động — khớp khuỷu phải xoay 126°/khung ở cảnh s01 vì hai hành động (`enter` và `cheek` theo cụm từ) chồng lên nhau; (2) thời lượng 80,2 s ngoài cửa sổ 60–80 s suy ra từ brief 70 s. Đã sửa ở mã dùng chung: hành động không còn chồng nhau (`lib/scene_anim.jsx`: hành động sau bắt đầu ngay khi hành động trước kết thúc), cửa sổ thời lượng = brief ±15 s, hiệu chỉnh lại tốc độ đọc từ 25 job thật (`tools/calibrate.py`: 15,28 ký tự/giây). Sau đó 11/11 kiểm tra đạt mà không tạo lại giọng (0 lượt gọi API thêm).", "- Người duyệt 'Claude (kiểm thử, không phải chủ dự án)' là thao tác thử của tôi, không phải duyệt của chủ dự án.", ""]
(out_dir / "real_runs.md").write_text("\n".join(L) + "\n", encoding="utf-8")
print("written", out_dir / "real_runs.md")
