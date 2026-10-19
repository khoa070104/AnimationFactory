"""Pack ONE project with everything needed to open, edit and rebuild it on this machine (no API key, no API call):
 tools + lib + tokens + the project folder (storyboard, assets, audio, per-scene clips, projects, output, logs, approval, status)
 + REBUILD.bat. Secrets (.env) and other projects are never included.
Usage: python package_project.py PROJECT_DIR OUT.zip"""
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
P2 = ROOT / "phase2"
proj = Path(sys.argv[1]).resolve()
out = Path(sys.argv[2])
name = proj.name
bat = f"""@echo off
chcp 65001 >nul
REM Rebuild the video from the packed data. No API key and no API call: the voice files are inside.
REM   REBUILD.bat          reuse unchanged scene clips   |   REBUILD.bat --force   re-render every scene
cd /d "%~dp0"
python phase2\\tools\\build_video.py phase2\\projects\\{name} %*
if errorlevel 1 ( echo. & echo *** FAILED - see messages above *** ) else ( echo. & echo Done: phase2\\projects\\{name}\\output )
if not defined NOPAUSE pause
"""
n = 0
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
    def add(f, arc):
        global n
        z.write(f, arc)
        n += 1
    for d in (P2 / "tools", P2 / "lib"):
        for f in d.rglob("*"):
            if f.is_file() and "__pycache__" not in f.parts and f.suffix != ".pyc":
                add(f, f.relative_to(ROOT).as_posix())
    add(P2 / "style/tokens.json", "phase2/style/tokens.json")
    for f in (P2 / "cost_model.json", P2 / "HUONG_DAN_PHASE2.md"):
        if f.exists():
            add(f, f.relative_to(ROOT).as_posix())
    for f in (ROOT / "tools").glob("*"):                      # Phase 1 helpers imported by the builders (decode_check, voice...)
        if f.is_file() and f.suffix in (".py", ".jsx"):
            add(f, f.relative_to(ROOT).as_posix())
    for f in proj.rglob("*"):
        if f.is_file() and "__pycache__" not in f.parts:
            rel = f.relative_to(proj)
            if rel.parts[0] == "work" and rel.name != "api_calls.jsonl":
                continue
            add(f, (Path("phase2/projects") / name / rel).as_posix())
    z.writestr("REBUILD.bat", bat)
    n += 1
    z.writestr("README.txt", f"Project {name}. Open phase2\\projects\\{name}\\render\\scenes.ecproj (EffectCraft) and film.fcproj (FilmCraft) "
                              "for reference (they keep the original absolute paths); REBUILD.bat regenerates working projects with paths relative to this folder.\n")
    n += 1
print(f"{n} files -> {out} ({out.stat().st_size // 1024} KB)")
