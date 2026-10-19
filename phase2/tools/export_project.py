"""Hand-over package of ONE project, from the UI ("Xuất gói bàn giao") or the command line:
the video(s), the editable EffectCraft/FilmCraft project files, storyboard (+ versions), script and research with sources, asset images + manifest,
voice audio, approval history, feedback, run logs, the AI/voice ledger and a cost summary. Never includes .env, API keys, work/ or clip caches.
  python export_project.py PROJECT_DIR     -> PROJECT/export/<name>_<time>.zip"""
import json
import sys
import time
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import budget  # noqa: E402

SKIP_DIRS = {"work", "_work", "llm_cache", "export", "__pycache__", "jobs", "versions_tmp"}


def make(proj):
    proj = Path(proj)
    out_dir = proj / "export"
    out_dir.mkdir(exist_ok=True)
    out = out_dir / f"{proj.name}_{time.strftime('%Y%m%d_%H%M%S')}.zip"
    n = 0
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(proj.rglob("*")):
            rel = f.relative_to(proj)
            if not f.is_file() or set(rel.parts) & SKIP_DIRS or f.suffix in (".pyc", ".lock", ".tmp"):
                continue
            if rel.parts[0] == "render" and f.suffix == ".mp4":
                continue                                           # per-scene clip cache: rebuilt from the project files
            if rel.parts[0] == "output" and f.suffix != ".mp4":
                continue
            if rel.name == ".env" or f.name.endswith(".env"):
                continue
            z.write(f, f"{proj.name}/{rel.as_posix()}")
            n += 1
        z.writestr(f"{proj.name}/COST_SUMMARY.json", json.dumps(budget.summary(proj), ensure_ascii=False, indent=2))
        z.writestr(f"{proj.name}/HANDOVER.txt", (
            f"Gói bàn giao dự án {proj.name} ({time.strftime('%Y-%m-%d %H:%M')}).\r\n"
            "output/*.mp4 video; render/*.ecproj, *.fcproj project chỉnh sửa được; storyboard.json (+ versions/); prepare/ kịch bản, nghiên cứu (nguồn + thời điểm truy cập), kế hoạch asset;\r\n"
            "ai_assets/ ảnh + manifest (trạng thái duyệt, mã băm, nguồn tạo); audio/ giọng đọc; approval.json + approvals_history.jsonl lịch sử duyệt; feedback.json góp ý;\r\n"
            "logs/ nhật ký chạy + ai_ledger.jsonl (mỗi lượt gọi AI/ảnh); COST_SUMMARY.json chi phí và hạn mức.\r\n"
            "Không có khóa API/.env trong gói."))
    return out, n + 2


if __name__ == "__main__":
    p, n = make(sys.argv[1])
    print(f"{n} files -> {p} ({p.stat().st_size // 1024} KB)")
