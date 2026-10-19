"""Hash every file of a project (except logs and render caches' temp files) to prove another project's run did not touch it.
Usage: python snapshot_hashes.py PROJECT_DIR OUT.json            -> write snapshot
       python snapshot_hashes.py PROJECT_DIR --compare OUT.json  -> list added/removed/changed files, exit 1 if any"""
import hashlib
import json
import sys
from pathlib import Path

SKIP = {"logs", "work"}


def snap(proj):
    out = {}
    for f in sorted(Path(proj).rglob("*")):
        if f.is_file() and not (set(f.relative_to(proj).parts) & SKIP):
            out[f.relative_to(proj).as_posix()] = hashlib.sha256(f.read_bytes()).hexdigest()
    return out


if __name__ == "__main__":
    proj = Path(sys.argv[1])
    if sys.argv[2] == "--compare":
        old = json.loads(Path(sys.argv[3]).read_text(encoding="utf-8"))
        new = snap(proj)
        added = sorted(set(new) - set(old))
        removed = sorted(set(old) - set(new))
        changed = sorted(k for k in set(old) & set(new) if old[k] != new[k])
        print(f"{len(old)} files before, {len(new)} after; added {added}; removed {removed}; changed {changed}")
        sys.exit(1 if (added or removed or changed) else 0)
    Path(sys.argv[2]).write_text(json.dumps(snap(proj), indent=0), encoding="utf-8")
    print(f"snapshot of {len(snap(proj))} files -> {sys.argv[2]}")
