"""No-cost tests (HTTP mocked): interrupted job is resumed only when text/voice/speed match."""
import sys, json, tempfile, unittest
from pathlib import Path
from unittest import mock
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import voice

class Resp:
    def __init__(self, body=None, content=b"", code=200): self._b, self.content, self.status_code, self.text = body, content, code, "x"
    def json(self): return self._b
    def raise_for_status(self): pass

def make_env(tmp, calls):
    def post(url, **kw):
        calls.append(("POST", kw["files"]["text"][1])); return Resp({"success": True, "task_id": f"task{len(calls)}"})
    def get(url, **kw):
        if "/v1/task/" in url:
            tid = url.rsplit("/", 1)[1]
            return Resp({"status": "done", "credit_cost": 1, "metadata": {"json_url": "http://x/w.json"}, "audio_url": "http://x/a.mp3", "id": tid})
        if url.endswith(".json"): return Resp(content=b"[]")
        return Resp(content=f"AUDIO-FOR-{calls[-1][1]}".encode())
    return mock.patch.object(voice.requests, "post", post), mock.patch.object(voice.requests, "get", get)

class T(unittest.TestCase):
    def run_tts(self, tmp, text, calls, speed=1.0, voice_id="v"):
        p, g = make_env(tmp, calls)
        with p, g, mock.patch.object(voice, "headers", lambda: {}), mock.patch.object(voice, "log_call", lambda e: None), mock.patch.object(voice.time, "sleep", lambda s: None):
            return voice.tts(text, voice_id, tmp / "a.mp3", speed)

    def interrupted(self, tmp, text, calls):
        """first run dies while waiting for the task"""
        p, g = make_env(tmp, calls)
        with p, g, mock.patch.object(voice, "headers", lambda: {}), mock.patch.object(voice, "wait_task", side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt): voice.tts(text, "v", tmp / "a.mp3", 1.0)

    def test_resume_same_script(self):
        tmp = Path(tempfile.mkdtemp()); calls = []
        self.interrupted(tmp, "kich ban A", calls); self.assertEqual(len(calls), 1)
        self.run_tts(tmp, "kich ban A", calls)
        self.assertEqual(len(calls), 1, "same script must resume, not create a new paid job")

    def test_changed_script_not_reused(self):
        tmp = Path(tempfile.mkdtemp()); calls = []
        self.interrupted(tmp, "kich ban A", calls)
        self.run_tts(tmp, "kich ban B", calls)
        self.assertEqual(len(calls), 2, "changed script must create a new job")
        self.assertEqual((tmp / "a.mp3").read_bytes(), b"AUDIO-FOR-kich ban B")

    def test_changed_speed_or_voice_not_reused(self):
        for kw in ({"speed": 1.2}, {"voice_id": "other"}):
            tmp = Path(tempfile.mkdtemp()); calls = []
            self.interrupted(tmp, "kich ban A", calls); self.run_tts(tmp, "kich ban A", calls, **kw)
            self.assertEqual(len(calls), 2, kw)

if __name__ == "__main__": unittest.main(verbosity=2)
