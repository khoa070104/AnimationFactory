"""Write MANIFEST.sha256 for an approved baseline folder. Usage: python freeze_baseline.py approved/bi_v2.1"""
import hashlib
import sys
from pathlib import Path

root = Path(sys.argv[1])
rows = []
for f in sorted(root.rglob("*")):
    if f.is_file() and f.name != "MANIFEST.sha256":
        rows.append(f"{hashlib.sha256(f.read_bytes()).hexdigest()}  {f.relative_to(root).as_posix()}")
(root / "MANIFEST.sha256").write_text("\n".join(rows) + "\n", encoding="utf-8")
print(len(rows), "files frozen in", root)
