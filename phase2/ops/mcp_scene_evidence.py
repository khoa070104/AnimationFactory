"""Evidence: assets produced through the MCP (real Antigravity jobs already stored in the project) are used by a scene via scene data only.
Runs on a COPY of the project (approval of the draft assets happens in the copy only; the owner approves in the real project).
Usage: python mcp_scene_evidence.py PROJECT OUT.md"""
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

P2 = Path(__file__).resolve().parent.parent
src = P2 / "projects" / sys.argv[1]
out_md = Path(sys.argv[2])
W = P2.parent / "work" / "mcp_scene_evidence"
shutil.rmtree(W, ignore_errors=True)
proj = W / "proj"
shutil.copytree(src, proj, ignore=shutil.ignore_patterns("logs", "output", "work"))
(proj / "logs").mkdir()
ENV = {**os.environ, "PYTHONIOENCODING": "utf-8"}
T = P2 / "tools"


def run(cmd):
    r = subprocess.run([sys.executable, *map(str, cmd)], capture_output=True, text=True, encoding="utf-8", env=ENV)
    return r.returncode, r.stdout + r.stderr


man = json.loads((proj / "ai_assets/manifest.json").read_text(encoding="utf-8"))["assets"]
lines = ["# Asset Antigravity qua MCP đi vào cảnh (chạy trên bản sao)", ""]
jobs = {j.stem: json.loads(j.read_text(encoding="utf-8")) for j in (proj / "ai_assets/jobs").glob("*.json")}
for aid in ("umbrella_ai", "calm_room_ai"):
    e = man[aid]
    job = next(j for j in jobs.values() if j["asset_id"] == aid)
    a = e["attempts"][-1]
    lines.append(f"- **{aid}** ({e['kind']}): job `{job['job_id']}` state `{job['state']}`; file `{e['file']}` {e['png_size']} sha256 `{e['sha256'][:16]}…`; "
                 f"tool_evidence={a['tool_evidence']}; hội thoại `{e['conversation_id']}`; agent_model `{e['agent_model']}`; image_model `{e['image_model']}` ({e['image_model_note']}); "
                 f"tokens {a['usage'].get('total_tokens')}; trạng thái gốc `{e['status']}`")
    run([T / "agy_image.py", proj, "approve", aid, "--by", "evidence copy only"])
sb = json.loads((proj / "storyboard.json").read_text(encoding="utf-8"))
s1 = sb["scenes"][0]
s1["bg"] = "ai:calm_room_ai"
s1["items"].append({"type": "prop", "img": "ai:umbrella_ai", "x": 1000, "y": 760, "scale": 0.9, "appear": "ví mình"})
(proj / "storyboard.json").write_text(json.dumps(sb, ensure_ascii=False, indent=2), encoding="utf-8")
rc, o = run([T / "validate_storyboard.py", proj])
lines += ["", f"- Dữ liệu cảnh `{s1['id']}` đổi: `bg: ai:calm_room_ai` + prop `ai:umbrella_ai` (không sửa code). Validator: `{o.strip().splitlines()[-1]}`"]
rc, o = run([T / "build_video.py", proj])
rend, reu = re.findall(r"RENDER (\w+)", o), re.findall(r"REUSE (\w+)", o)
lines.append(f"- Dựng: render {rend}, tái sử dụng {len(reu)} cảnh; mã thoát {rc}")
rc, o = run([T / "build_video.py", proj])
rend2 = re.findall(r"RENDER (\w+)", o)
lines.append(f"- Dựng lại không đổi: render {rend2 or 'không cảnh nào'}")
# unapproved asset is refused
run([T / "agy_image.py", proj, "reject", "umbrella_ai", "--note", "evidence: rejected after use"])
rc, o = run([T / "validate_storyboard.py", proj])
lines.append(f"- Sau khi loại `umbrella_ai`, validator: `{[l for l in o.splitlines() if 'umbrella' in l][:1]}`")
shutil.copy(proj / "previews/storyboard_preview.ecproj", W / "keep.ecproj") if (proj / "previews/storyboard_preview.ecproj").exists() else None
rep = json.loads((proj / "logs/build_report.json").read_text(encoding="utf-8"))
st = rep["starts"]
shutil.copy(proj / "ai_assets/source/calm_room_ai.jpg", out_md.parent / "mcp_scene_background_source.jpg")
subprocess.run([r"C:\Program Files\FilmCraft\filmcraft-cli.exe", "--project", str(proj / "render/film.fcproj"), "render", "--seconds", f"{st[0] + 3.0:.2f}", "--out",
                str(out_md.parent / "mcp_scene_frame.png"), "--scale", "0.5"], capture_output=True)
lines += ["", "Khung hình đã dựng của cảnh (xem `mcp_scene_frame.png`); ảnh gốc phông: `mcp_scene_background_source.jpg`."]
out_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
print("\n".join(lines))
shutil.rmtree(W, ignore_errors=True)
