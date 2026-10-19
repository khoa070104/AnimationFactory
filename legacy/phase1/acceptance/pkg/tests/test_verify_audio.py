"""Audio checker must FAIL on truncated audio and on audio unrelated to the text (needs a finished run in WORK)."""
import json, os, shutil, subprocess, sys, tempfile, unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
WORK = Path(os.environ.get("AF_TEST_WORK", ROOT / "acceptance/work1"))
CFG = WORK / "run_config.json"

def run(work):
    env = dict(os.environ, AF_CONFIG=str(CFG), PYTHONIOENCODING="utf-8")
    r = subprocess.run([sys.executable, str(ROOT/"tools/verify_audio.py"), str(work)], capture_output=True, text=True, env=env, encoding="utf-8")
    return r.returncode, r.stdout

@unittest.skipUnless(CFG.exists(), "needs a finished run")
class T(unittest.TestCase):
    def copy(self):
        t = Path(tempfile.mkdtemp()); shutil.copytree(WORK / "audio", t / "audio"); return t
    def test_good_passes(self):
        self.assertEqual(run(WORK)[0], 0)
    def test_truncated_audio_fails(self):                  # real mp3 cut to ~1 s while words run to ~9-12 s
        t = self.copy(); f = t/"audio/scene1.mp3"; f.write_bytes(f.read_bytes()[:16000])
        code, out = run(t); self.assertEqual(code, 1, out); self.assertIn("CUT OFF", out)
    def test_words_beyond_audio_fails(self):               # timings stretched past the file
        t = self.copy(); j = t/"audio/scene2.words.json"; d = json.loads(j.read_text(encoding="utf-8"))
        for w in d[0]["words"]: w["start"] *= 3; w["end"] *= 3
        j.write_text(json.dumps(d), encoding="utf-8")
        code, out = run(t); self.assertEqual(code, 1, out)
    def test_wrong_text_fails(self):
        t = self.copy(); j = t/"audio/scene1.words.json"; d = json.loads(j.read_text(encoding="utf-8"))
        d[0]["words"][0]["text"] = "Sai"; j.write_text(json.dumps(d), encoding="utf-8")
        self.assertEqual(run(t)[0], 1)
    def test_missing_audio_fails(self):
        t = self.copy(); (t/"audio/scene2.mp3").unlink(); self.assertEqual(run(t)[0], 1)

if __name__ == "__main__": unittest.main(verbosity=2)
