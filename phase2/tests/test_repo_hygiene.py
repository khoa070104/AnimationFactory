"""Repo hygiene: the rules that stop the repo from collecting rubbish again. They look at what git TRACKS (so local scratch does not matter).
A failure here means something that should not be committed is about to be: move it (docs/, legacy/) or ignore it (.gitignore)."""
import re
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
TOP_OK = {".editorconfig", ".gitattributes", ".env.example", ".gitignore", ".mcp.json", "README.md", "pyproject.toml", "docs", "legacy", "phase2"}
BAD_EXT = {".mp4", ".wav", ".mp3", ".zip", ".exe", ".mov"}
MD_OK = {"README.md", "phase2/remotion/README.md", "phase2/assets_mcp/README.md", "phase2/style/STYLE_GUIDE.md", "phase2/motion/ACTIONS.md"}    # everything else is under docs/ or legacy/
FIXTURES = {"video1_luong", "video2_quy_khan_cap", "ui_demo"}
MAX_BYTES = 3 * 1024 * 1024


def tracked():
    if not shutil.which("git") or not (ROOT / ".git").exists():
        return None
    r = subprocess.run(["git", "-C", str(ROOT), "ls-files"], capture_output=True, text=True, encoding="utf-8")
    return [l for l in r.stdout.splitlines() if l]


@unittest.skipIf(tracked() is None, "not a git checkout")
class T(unittest.TestCase):
    def test_root_holds_only_known_entries(self):
        extra = {f.split("/")[0] for f in tracked()} - TOP_OK
        self.assertFalse(extra, f"new top-level entries {sorted(extra)}: put them under docs/, legacy/ or phase2/")

    def test_no_media_archives_secrets_or_runtime_state_are_tracked(self):
        bad = [f for f in tracked() if Path(f).suffix.lower() in BAD_EXT or re.search(r"(^|/)\.env$|phase2/config\.json$|llm_cache|/_t_|topic_history\.jsonl$|/\.locks/|telegram_state", f)]
        self.assertFalse(bad, bad[:5])

    def test_markdown_lives_in_docs(self):
        bad = [f for f in tracked() if f.endswith(".md") and not f.startswith(("docs/", "legacy/", "phase2/approved/", "phase2/evidence/", "phase2/projects/")) and f not in MD_OK]    # approved/evidence/projects hold data records, not guides
        self.assertFalse(bad, f"documents belong in docs/: {bad}")

    def test_only_fixture_projects_are_tracked(self):
        names = {f.split("/")[2] for f in tracked() if f.startswith("phase2/projects/") and f.count("/") >= 3}
        self.assertTrue(names <= FIXTURES, f"project data is not source: {sorted(names - FIXTURES)}")

    def test_files_the_code_needs_to_start_are_tracked(self):
        """A clean clone must be able to start: .gitignore must never swallow these (it once swallowed style/tokens.json via a `*token*` rule)."""
        need = ["phase2/style/tokens.json", "phase2/approved/bi_v2.1/tokens.json", "phase2/approved/bi_v2.1/assets/png/head.png", "phase2/remotion/package-lock.json", ".gitattributes"]
        missing = [f for f in need if f not in set(tracked())]
        self.assertFalse(missing, missing)
        ignored = subprocess.run(["git", "-C", str(ROOT), "check-ignore"] + need, capture_output=True, text=True).stdout.split()
        self.assertFalse(ignored, ignored)

    def test_no_big_files(self):
        big = [(f, (ROOT / f).stat().st_size) for f in tracked() if (ROOT / f).exists() and (ROOT / f).stat().st_size > MAX_BYTES]
        self.assertFalse(big, big)

    def test_tools_hard_code_no_machine_paths(self):
        pat = re.compile(r"""["'](?:[A-Za-z]:[\\/]|/mnt/)""")
        bad = []
        for f in tracked():
            if f.startswith("phase2/tools/") and f.endswith(".py") and f != "phase2/tools/toolpaths.py":      # toolpaths.py owns the install-location defaults
                for n, line in enumerate((ROOT / f).read_text(encoding="utf-8", errors="replace").splitlines(), 1):
                    if pat.search(line) and not line.lstrip().startswith("#"):
                        bad.append(f"{f}:{n}")
        self.assertFalse(bad, bad)


if __name__ == "__main__":
    unittest.main()
