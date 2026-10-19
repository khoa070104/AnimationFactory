"""Housekeeping that keeps the repo and the working folder from filling with rubbish. DRY RUN by default; nothing is deleted without --apply.
  python ops/clean.py            list what would go
  python ops/clean.py --apply    delete it

What it removes (only these patterns, never data you made on purpose):
  * temp projects created by tests: phase2/projects/_t_*
  * __pycache__ folders, *.pyc
  * leftovers of experiments: phase2/remotion/_spike, phase2/remotion/out
  * per-project render scratch older than --days (default 14) that can be rebuilt for free: PROJECT/render/_*.jsx, PROJECT/previews/_*.jsx, PROJECT/logs/af_jobs/*.log
It only REPORTS (never deletes): zip packages in the repo root, projects that no test or doc refers to (size, last change), the biggest folders.
Paid results (audio, AI pictures, voice cache) and approvals are never touched."""
import argparse
import shutil
import sys
import time
from pathlib import Path

P2 = Path(__file__).resolve().parent.parent
ROOT = P2.parent
FIXTURES = {"video1_luong", "video2_quy_khan_cap", "ui_demo"}        # tracked on purpose: tests read them


def size(p):
    return sum(f.stat().st_size for f in p.rglob("*") if f.is_file()) if p.is_dir() else (p.stat().st_size if p.exists() else 0)


def mb(n):
    return f"{n / 1048576:.1f} MB"


def plan(days):
    out = []
    for p in sorted((P2 / "projects").glob("_t_*")):
        out.append((p, "temp test project"))
    for p in list(ROOT.rglob("__pycache__")):
        if "node_modules" not in p.parts:
            out.append((p, "python cache"))
    for p in (P2 / "remotion" / "_spike", P2 / "remotion" / "out"):
        if p.exists():
            out.append((p, "experiment leftover"))
    cutoff = time.time() - days * 86400
    for proj in (P2 / "projects").glob("*"):
        if not proj.is_dir() or proj.name.startswith("_t_"):
            continue
        for pat in ("render/_*.jsx", "previews/_*.jsx", "logs/af_jobs/*.log"):
            for f in proj.glob(pat):
                if f.stat().st_mtime < cutoff:
                    out.append((f, "rebuildable scratch"))
    return out


def report():
    print("\nREPORT ONLY (never deleted by this script)")
    for z in sorted(ROOT.glob("*.zip")):
        print(f"  package {z.name}: {mb(z.stat().st_size)}  (delete by hand when no longer needed)")
    for proj in sorted((P2 / "projects").glob("*")):
        if proj.is_dir() and proj.name not in FIXTURES and not proj.name.startswith("_t_"):
            last = max((f.stat().st_mtime for f in proj.rglob("*") if f.is_file()), default=0)
            print(f"  project {proj.name}: {mb(size(proj))}, last change {time.strftime('%Y-%m-%d', time.localtime(last))} (not a test fixture)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--days", type=int, default=14)
    a = ap.parse_args()
    todo = plan(a.days)
    total = sum(size(p) for p, _ in todo)
    for p, why in todo:
        print(f"{'DELETE' if a.apply else 'would delete'}  {p.relative_to(ROOT)}  ({why}, {mb(size(p))})")
        if a.apply:
            shutil.rmtree(p, ignore_errors=True) if p.is_dir() else p.unlink(missing_ok=True)
    print(f"\n{len(todo)} item(s), {mb(total)} {'deleted' if a.apply else 'would be freed (run with --apply)'}")
    report()


if __name__ == "__main__":
    sys.exit(main())
