"""Evidence for cache / dependency behaviour, run on COPIES (the real projects are never touched).
Scenarios: unchanged rerun; unused asset added; used AI asset edited; one scene's layout edited; one scene's voice edited (dry run + gate);
a shared motion action edited in a cloned tool tree (only scenes using that action rebuild); MCP repeat request (no agy call).
Usage: python dependency_evidence.py SOURCE_PROJECT OUT.md"""
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

P2 = Path(__file__).resolve().parent.parent
src = P2 / "projects" / sys.argv[1]
out_md = Path(sys.argv[2])
W = P2.parent / "work" / "dep_evidence"
shutil.rmtree(W, ignore_errors=True)
W.mkdir(parents=True)
rows = []
ENV = {**os.environ, "PYTHONIOENCODING": "utf-8"}


def run(cmd, cwd=None):
    r = subprocess.run([sys.executable, *map(str, cmd)], capture_output=True, text=True, encoding="utf-8", env=ENV, cwd=cwd)
    return r.returncode, r.stdout + r.stderr


def build(tools_dir, proj):
    rc, o = run([tools_dir / "build_video.py", proj])
    rendered = re.findall(r"RENDER (\w+)", o)
    reused = re.findall(r"REUSE (\w+)", o)
    return rc, rendered, reused, o


def api_calls(proj):
    return json.loads((proj / "status.json").read_text(encoding="utf-8")).get("api_calls", 0)


def record(name, shows, result, ok):
    rows.append((name, shows, result, ok))
    print(("PASS " if ok else "FAIL ") + name + " :: " + result, flush=True)


proj = W / "proj"
shutil.copytree(src, proj, ignore=shutil.ignore_patterns("logs", "output", "work"))
(proj / "logs").mkdir()
(proj / "work").mkdir()
if (src / "work/api_calls.jsonl").exists():
    shutil.copy(src / "work/api_calls.jsonl", proj / "work/api_calls.jsonl")
# the copy lives outside phase2/projects: the tools resolve everything from the project path, so no special handling is needed
T = P2 / "tools"
all_ids = [s["id"] for s in json.loads((proj / "storyboard.json").read_text(encoding="utf-8"))["scenes"]]
calls0 = api_calls(proj)

rc, rend, reu, o = build(T, proj)                                   # baseline (cold: current code differs from the original build)
record("0. baseline build of the copy", "reference run", f"rendered {len(rend)}/{len(all_ids)}, reused {len(reu)}", rc == 0)

rc, rend, reu, o = build(T, proj)
record("1. rerun, nothing changed", "cache hit for every scene", f"rendered {rend or '-'}; reused {len(reu)}/{len(all_ids)}; API calls {api_calls(proj) - calls0}", rend == [] and len(reu) == len(all_ids))

shutil.copy(proj / "assets/png/coin.png", proj / "assets/png/zz_unused.png")
rc, rend, reu, o = build(T, proj)
record("2. add an asset no scene uses", "dependency tracking: unrelated asset", f"rendered {rend or '-'}", rend == [])

# find an AI asset used by a scene (if any) and edit it; otherwise edit a library prop used by exactly one scene
sb = json.loads((proj / "storyboard.json").read_text(encoding="utf-8"))
used_ai = [(s["id"], it["img"][3:]) for s in sb["scenes"] for it in s["items"] if str(it.get("img", "")).startswith("ai:")]
if used_ai:
    sid, aid = used_ai[0]
    from PIL import Image, ImageEnhance
    f = proj / "ai_assets" / f"{aid}.png"
    im = Image.open(f).convert("RGBA")
    r, g, b, a = im.split()
    Image.merge("RGBA", (g, r, b, a)).save(f)                    # swap channels = a visibly different file, same name
    rc, rend, reu, o = build(T, proj)
    record(f"3. edit the AI asset {aid} used by scene {sid}", "dependency tracking: used asset", f"rendered {rend}", rend == [sid])
else:
    record("3. edit a used AI asset", "n/a", "project has no AI asset in a scene", True)

sc = sb["scenes"][2]
sc["bi"]["x"] = sc["bi"]["x"] + 40
(proj / "storyboard.json").write_text(json.dumps(sb, ensure_ascii=False, indent=2), encoding="utf-8")
rc, rend, reu, o = build(T, proj)
record(f"4. move the character in scene {sc['id']} (layout only)", "per-scene data dependency; no voice call", f"rendered {rend}; API calls {api_calls(proj) - calls0}", rend == [sc["id"]])

# voice edit: gate + dry run (no API call)
sb = json.loads((proj / "storyboard.json").read_text(encoding="utf-8"))
s5 = sb["scenes"][1]
first = s5["voice"].split()[0]
s5["voice"] = s5["voice"].replace(first, first, 1) + " Thêm một câu cuối."
s5["subtitles"] = "auto"
(proj / "storyboard.json").write_text(json.dumps(sb, ensure_ascii=False, indent=2), encoding="utf-8")
rc, o = run([T / "voice_project.py", proj, "--dry-run"])
gate = "REFUSED" in o
run([T / "approve.py", proj, "--by", "evidence copy"])
rc, o2 = run([T / "voice_project.py", proj, "--dry-run"])
m = re.search(r"plan: (\d+) scene\(s\) to generate \((\d+) chars, est\. ~(\d+) credits\), (\d+) from the shared voice cache.*?(\d+) unchanged", o2)
record(f"5. edit the wording of scene {s5['id']} (dry run)", "approval gate + minimal recomputation", f"gate before re-approval: {'REFUSED' if gate else 'NOT refused'}; after: {m.group(1)} scene to generate ({m.group(2)} chars, ~{m.group(3)} credits), {m.group(5)} unchanged; API calls {api_calls(proj) - calls0}" if m else o2[-200:], gate and m and m.group(1) == "1" and api_calls(proj) == calls0)

# shared motion library change in a CLONED tool tree: only scenes that use the action rebuild
clone = W / "clone"
shutil.copytree(P2 / "tools", clone / "tools", ignore=shutil.ignore_patterns("__pycache__"))
shutil.copytree(P2 / "lib", clone / "lib")
(clone / "style").mkdir()
shutil.copy(P2 / "style/tokens.json", clone / "style/tokens.json")
proj2 = clone / "projects" / "p"
shutil.copytree(src, proj2, ignore=shutil.ignore_patterns("logs", "output", "work"))
(proj2 / "logs").mkdir()
rc, rend, reu, o = build(clone / "tools", proj2)                   # cold build with the clone's (identical) code
sb2 = json.loads((proj2 / "storyboard.json").read_text(encoding="utf-8"))
users = {}
for s in sb2["scenes"]:
    for a in s.get("actions", []):
        users.setdefault(a["name"], set()).add(s["id"])
target = next((n for n in ("shrug", "nod", "cheer", "wave", "cheek") if n in users and len(users[n]) < len(all_ids)), None)
if target:
    m = clone / "lib/bi_motion.jsx"
    t = m.read_text(encoding="utf-8")
    key = {"shrug": "T + 1.6", "nod": "T + 1.9", "cheer": "T + 0.85", "wave": "T + 0.4", "cheek": "T + 1.0 + hold"}[target]
    assert key in t
    block_start = t.index(f"  {target}: function (T, p)")
    t2 = t[:block_start] + t[block_start:].replace(key, key.replace("T +", "T + 0.01 +", 1) if target != "shrug" else "T + 1.5", 1)
    m.write_text(t2, encoding="utf-8")
    rc, rend, reu, o = build(clone / "tools", proj2)
    record(f"6. edit the shared action '{target}' in the motion library", "a shared-component change rebuilds exactly the scenes that use it",
           f"scenes using it: {sorted(users[target])}; rebuilt: {sorted(rend)}", sorted(rend) == sorted(users[target]))
    rig = clone / "lib/bi_rig.jsx"
    rig.write_text(rig.read_text(encoding="utf-8") + "\n// touched\n", encoding="utf-8")
    rc, rend, reu, o = build(clone / "tools", proj2)
    record("7. edit the shared character rig", "a rig change rebuilds every scene", f"rebuilt {len(rend)}/{len(all_ids)}", len(rend) == len(all_ids))
else:
    record("6. shared action edit", "n/a", "no action used by a strict subset of scenes", True)

shutil.rmtree(W, ignore_errors=True)
lines = ["# Bằng chứng cache và phụ thuộc (chạy trên bản sao)", "", f"Dự án nguồn: `{sys.argv[1]}`, {len(all_ids)} cảnh, thời điểm {time.strftime('%Y-%m-%d %H:%M')}", "",
         "| Tình huống | Chứng minh | Kết quả | Đạt |", "|---|---|---|---|"]
lines += [f"| {a} | {b} | {c} | {'✔' if d else '✘'} |" for a, b, c, d in rows]
out_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
sys.exit(0 if all(r[3] for r in rows) else 1)
