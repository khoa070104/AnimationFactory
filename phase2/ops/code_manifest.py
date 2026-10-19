"""List every code/config file with its sha256 and an overall hash (stands in for a Git commit: no repository is used).
Usage: python code_manifest.py OUT.json"""
import hashlib
import json
import sys
import time
from pathlib import Path

P2 = Path(__file__).resolve().parent.parent
groups = {"tools": "tools/*.py", "lib": "lib/*.jsx", "assets_mcp": "assets_mcp/*", "ui": "ui/**/*", "tests": "tests/*.py", "ops": "ops/*.py",
          "style": "style/tokens.json", "root": "*.json"}
files = {}
for g, pat in groups.items():
    for f in sorted(P2.glob(pat)):
        if f.is_file() and "__pycache__" not in f.parts:
            files[f.relative_to(P2).as_posix()] = hashlib.sha256(f.read_bytes()).hexdigest()
for f in (P2 / "approved/bi_v2.1/MANIFEST.sha256", P2 / "HUONG_DAN_PHASE2.md"):
    if f.exists():
        files[f.relative_to(P2).as_posix()] = hashlib.sha256(f.read_bytes()).hexdigest()
pipeline = [k for k in files if k.startswith(("tools/", "lib/", "style/"))]
overall = hashlib.sha256("".join(f"{k}{files[k]}" for k in sorted(files)).encode()).hexdigest()
pipe = hashlib.sha256("".join(f"{k}{files[k]}" for k in sorted(pipeline)).encode()).hexdigest()
out = {"generated": time.strftime("%Y-%m-%d %H:%M:%S"), "files": len(files), "overall_sha256": overall, "pipeline_sha256": pipe, "hashes": files}
Path(sys.argv[1]).write_text(json.dumps(out, indent=1), encoding="utf-8")
print(len(files), "files; overall", overall[:16], "; pipeline (tools+lib+style)", pipe[:16])
