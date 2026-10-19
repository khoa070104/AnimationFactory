"""Package the whole Phase 2 deliverable (code, projects, evidence, docs) for acceptance. Never includes .env, keys, tokens, work/, caches.
Per-scene clips (render/*.mp4) are left out (rebuilt by REBUILD.bat in ~2 minutes); final MP4s, audio, assets, storyboards, approvals and logs are included.
Usage: python package_all.py OUT.zip"""
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
P2 = ROOT / "phase2"
out = Path(sys.argv[1])
SKIP_DIRS = {"node_modules", ".remotion", "out", "__pycache__", "work", "_work", "jobs", "previews_tmp", "llm_cache", "export", ".locks"}
n = 0
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
    def add(f, arc):
        global n
        z.write(f, arc)
        n += 1
    for base in ("tools", "lib", "remotion", "assets_mcp", "ui", "tests", "ops", "evidence", "approved", "style", "channels"):
        d = P2 / base
        for f in sorted(d.rglob("*")):
            if f.is_file() and not (set(f.parts) & SKIP_DIRS) and f.suffix != ".pyc":
                if base == "style" and f.parent.name == "frames":
                    pass
                add(f, f.relative_to(ROOT).as_posix())
    for f in sorted((ROOT / "docs").rglob("*.md")):
        add(f, f.relative_to(ROOT).as_posix())
    for f in P2.glob("*"):
        if f.is_file() and f.suffix in (".md", ".json") and f.name != "config.json":
            add(f, f.relative_to(ROOT).as_posix())
    for f in (P2 / "voice_cache").glob("*") if (P2 / "voice_cache").exists() else []:
        add(f, f.relative_to(ROOT).as_posix())
    for proj in sorted((P2 / "projects").iterdir()):
        if not proj.is_dir() or proj.name.startswith("_"):
            continue
        for f in sorted(proj.rglob("*")):
            rel = f.relative_to(proj)
            if not f.is_file() or (set(rel.parts) & SKIP_DIRS):
                continue
            if rel.parts[0] == "render" and f.suffix == ".mp4":
                continue
            if f.suffix == ".pyc":
                continue
            add(f, f.relative_to(ROOT).as_posix())
    # the .env with the API key is NOT included
    add(ROOT / ".env.example", ".env.example")
    z.writestr("REBUILD.bat", "@echo off\r\nchcp 65001 >nul\r\nREM Rebuild a project's video from the packed data (no API key, no API call):  REBUILD.bat <project> [--force]\r\n"
                              "cd /d \"%~dp0\"\r\npython phase2\\tools\\build_video.py phase2\\projects\\%*\r\nif not defined NOPAUSE pause\r\n")
    n += 1
    z.writestr("README.txt", "Animation Factory - Phase 2 acceptance package. Start with docs/README.md (index), then docs/acceptance/.\r\n"
                              "No .env / API key / token is included. Python 3.12 + Pillow + numpy; EffectCraft, FilmCraft, VectorCraft installed (paths: phase2/tools/toolpaths.py).\r\n")
    n += 2
print(f"{n} files -> {out} ({out.stat().st_size // (1024 * 1024)} MB)")
