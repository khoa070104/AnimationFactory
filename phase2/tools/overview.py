"""One project, seen as the owner needs it: what is waiting for MY decision, what failed and where, what it costs, what the jobs are doing.
Pure reads of the project folder (no AI call, no paid call); used by the UI production/overview pages and by tests.
  todo(proj)        -> [{kind, label, detail, tab}]   decisions the owner has to make
  problems(proj)    -> [{where, message}]             failed steps / jobs, with the step name
  production(proj)  -> steps, todo, problems, costs, jobs, slots"""
import json
import time
from pathlib import Path

import agy_image as G
import agy_slots
import approve
import budget
import prepare as PR
import revise
import sbload


def _jobs(proj):
    import agy_jobs as J
    out = []
    d = Path(proj) / "ai_assets" / "jobs"
    if d.exists():
        for f in sorted(d.glob("*.json"), key=lambda f: f.stat().st_mtime, reverse=True):
            try:
                j = J.check(Path(proj).name, f.stem)
            except Exception as e:  # noqa: BLE001 - a broken record must not hide the others
                out.append({"job_id": f.stem, "state": "unreadable", "error": str(e)})
                continue
            out.append({k: j.get(k) for k in ("job_id", "asset_id", "state", "error", "requested_at", "finished_at", "run", "reused", "kind")})
    return out


def todo(proj):
    proj = Path(proj)
    items = []
    sb = json.loads((proj / "storyboard.json").read_text(encoding="utf-8"))
    ov = PR.overview(proj)
    res = G.read_json(PR.pdir(proj) / "research.json", {}) or {}
    need = [f for f in res.get("facts", []) if f.get("needs_check") and not f.get("decision")]
    if need:
        items.append({"kind": "facts", "tab": "script", "label": f"{len(need)} thông tin chưa có căn cứ — chấp nhận hoặc loại bỏ",
                      "detail": "; ".join(f["claim"][:70] for f in need[:3])})
    scr = G.read_json(PR.pdir(proj) / "script.json", {}) or {}
    if scr.get("claims_to_verify"):
        items.append({"kind": "claims", "tab": "script", "label": f"{len(scr['claims_to_verify'])} điểm AI đánh dấu cần kiểm chứng", "detail": "; ".join(c["text"][:70] for c in scr["claims_to_verify"][:3])})
    if sb.get("scenes"):
        ap = G.read_json(proj / "approval.json")
        if not ap:
            items.append({"kind": "script", "tab": "script", "label": "Duyệt kịch bản (lời đọc)", "detail": "chưa duyệt lần nào; giọng đọc chỉ được tạo sau khi duyệt"})
            items.append({"kind": "storyboard", "tab": "board", "label": "Duyệt storyboard (hình ảnh, hành động)", "detail": "chưa duyệt lần nào"})
        else:
            vc, sc = approve.changes_since_approval(proj)
            if vc:
                items.append({"kind": "script", "tab": "script", "label": "Duyệt lại lời đọc: " + ", ".join(vc), "detail": "lời đọc đã đổi sau lần duyệt — chỉ các cảnh này cần tạo lại giọng"})
            if sc:
                items.append({"kind": "storyboard", "tab": "board", "label": "Duyệt lại hình/hành động: " + ", ".join(sc), "detail": "định nghĩa cảnh đã đổi sau lần duyệt"})
    import actors
    apr = G.read_json(proj / "approval.json") or {}
    for k, cell in (apr.get("kinds") or {}).items():
        act = cell.get("actor") or actors.classify(cell.get("by"))
        if act["type"] in ("test", "ai"):
            items.append({"kind": "owner_approval", "tab": "script" if k == "script" else "board", "label": f"Phần '{k}' đang được duyệt bởi {act['label']!r} ({act['type']}), không phải chủ dự án",
                          "detail": "thao tác thử/AI không mở khóa bước trả phí; chủ dự án cần duyệt lại"})
    for aid, e in G.load_manifest(proj)["assets"].items():
        if e.get("status") == "approved" and e.get("approved_by") and actors.classify(e["approved_by"])["type"] in ("test", "ai"):
            items.append({"kind": "owner_approval", "tab": "assets", "label": f"Ảnh {aid} được duyệt bởi {e['approved_by']!r}, không phải chủ dự án", "detail": "xem lại ảnh và duyệt lại nếu đồng ý"})
    plan = G.read_json(PR.pdir(proj) / "asset_plan.json")
    if plan and plan["assets"] and not ov["plan_approved"]:
        items.append({"kind": "plan", "tab": "assets", "label": f"Duyệt kế hoạch tạo {len([a for a in plan['assets'] if not a.get('reuse')])} asset mới", "detail": "; ".join(a['id'] for a in plan['assets'])})
    drafts = [k for k, e in G.load_manifest(proj)["assets"].items() if e.get("status") == "draft" or G.approval_state(proj, k)[0] == "changed_after_approval"]
    if drafts:
        items.append({"kind": "assets", "tab": "assets", "label": "Duyệt/loại asset: " + ", ".join(drafts), "detail": "asset mới ở trạng thái nháp, chưa dùng được trong cảnh"})
    import sbstore
    rv = sbstore.review_list(proj)
    if rv:
        items.append({"kind": "cues", "tab": "script", "label": "Xem lại mốc hành động gần đúng ở cảnh: " + ", ".join(sorted(rv)),
                      "detail": "lời đổi mà không còn cụm cũ; mốc được thay bằng cụm gần nhất/thời điểm ước lượng — duyệt storyboard là xác nhận"})
    import characters as CHR
    for cid in [c for c in CHR.used_ids(sb) if c != CHR.BUILTIN]:
        stt, why = CHR.state(proj, cid)
        if stt != "approved":
            items.append({"kind": "characters", "tab": "assets", "label": f"Nhân vật {cid}: " + ("duyệt hình + khung xương" if stt == "draft" else stt), "detail": why or "chưa vẽ"})
    if plan:
        st = G.read_json(PR.pdir(proj) / "asset_state.json", {"applied": []})
        ready = [a["id"] for a in plan["assets"] if a["id"] not in st["applied"] and G.approval_state(proj, a["id"])[0] == "approved"]
        if ready:
            items.append({"kind": "apply", "tab": "assets", "label": "Đưa asset đã duyệt vào cảnh: " + ", ".join(ready), "detail": "bấm “Đưa asset vào cảnh” — tạo phiên bản storyboard mới"})
    pend = [p for p in revise.list_all(proj) if p["status"] == "pending"]
    if pend:
        items.append({"kind": "proposals", "tab": "script", "label": f"{len(pend)} đề xuất sửa của AI đang chờ bạn xem", "detail": "; ".join(f"{p['type']} {p['target']}" for p in pend[:4])})
    fb = [f for f in G.read_json(proj / "feedback.json", []) or [] if f.get("status") == "open"]
    if fb:
        items.append({"kind": "feedback", "tab": "board", "label": f"{len(fb)} góp ý chưa xử lý", "detail": "; ".join(f"{f['scene']}: {f['text'][:50]}" for f in fb[:3])})
    return items


def problems(proj):
    proj = Path(proj)
    out = []
    for n, c in PR.overview(proj)["steps"].items():
        if c.get("state") in ("failed", "interrupted"):
            out.append({"where": f"AI · {n}", "message": c.get("error") or "tiến trình dừng giữa chừng — chạy tiếp để hoàn thành (phần đã xong được giữ nguyên)"})
    st = G.read_json(proj / "status.json", {}) or {}
    for n, c in (st.get("steps") or {}).items():
        if c.get("state") == "failed":
            out.append({"where": f"Sản xuất · {n}", "message": c.get("error") or "lỗi"})
    for j in _jobs(proj):
        if j["state"] in ("failed", "timeout", "interrupted", "invalid", "unreadable"):
            out.append({"where": f"Asset {j.get('asset_id') or j['job_id']}", "message": f"{j['state']}: {j.get('error') or ''}".strip()})
    return out


def costs(proj):
    s = budget.summary(proj)
    est = G.read_json(Path(proj) / "estimate.json", {}) or {}
    s["voice_estimate_credits"] = (est.get("total") or {}).get("credits")
    return s


def production(proj):
    proj = Path(proj)
    st = G.read_json(proj / "status.json", {}) or {}
    return {"prepare": PR.overview(proj), "produce_steps": st.get("steps", {}), "state": st.get("state"), "todo": todo(proj), "problems": problems(proj), "costs": costs(proj),
            "jobs": _jobs(proj), "slots": agy_slots.status(), "api_calls": st.get("api_calls", 0), "credits_spent": st.get("credits_spent", 0)}


def scene_seconds(sb):
    import build_storyboard as SBD
    return {r["id"]: r["sec"] for r in SBD.stats(sbload.normalise(json.loads(json.dumps(sb))))}


def estimate(sb):
    """Characters / seconds / voice credits of the current storyboard, computed on the fly (no files needed)."""
    import build_storyboard as SBD
    rows = SBD.stats(sbload.normalise(json.loads(json.dumps(sb))))
    return {"chars": sum(r["chars"] for r in rows), "sec": round(sum(r["sec"] for r in rows), 1), "credits": sum(r["credits"] for r in rows)}
