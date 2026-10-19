"""ai33.pro v3 voice client: list voices, text-to-speech (with word timings), save audio.
Usage:
  python voice.py voices --provider edge [--language Vietnamese] [--gender Female]
  python voice.py tts --voice edge_vi-VN-HoaiMyNeural --text "Xin chào" --out out.mp3 [--speed 1]
Key: AI33_API_KEY in AnimationFactory/.env or the environment (never printed or logged).

Safety against duplicate paid jobs: the POST that creates a job is NEVER retried automatically.
The task_id + a fingerprint of (text, voice, speed) is written to <out>.task as soon as it is known; if a run dies
while waiting, the next run resumes that task only if the fingerprint still matches, otherwise it discards it. Only idempotent GETs are retried.
Task polling uses GET /v1/task/{task_id}: found by trial, not in the supplied docs (see HUONG_DAN.md)."""
import argparse, hashlib, json, os, sys, time
from pathlib import Path
import requests

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass
ROOT = Path(__file__).resolve().parents[2]            # repo root: holds .env (keys) and work/ (call log)

def load_env():
    f = ROOT / ".env"
    if f.exists():
        for line in f.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1); os.environ.setdefault(k.strip(), v.strip())
load_env()
BASE = os.environ.get("AI33_BASE_URL", "https://api.ai33.pro").rstrip("/")
TASK_PATH = os.environ.get("AI33_TASK_PATH", "/v1/task/{task_id}")
HTTP_TIMEOUT = 60          # seconds per HTTP call
TASK_TIMEOUT = 600         # max seconds waiting for one job
GET_RETRIES = 3

def headers():
    key = os.environ.get("AI33_API_KEY", "")
    if not key: sys.exit("Missing AI33_API_KEY: put it in AnimationFactory/.env")
    return {"xi-api-key": key}

def log_call(entry):
    f = Path(os.environ.get("AF_WORK") or ROOT / "work") / "api_calls.jsonl"; f.parent.mkdir(exist_ok=True)
    entry["ts"] = time.strftime("%Y-%m-%d %H:%M:%S")
    with f.open("a", encoding="utf-8") as fh: fh.write(json.dumps(entry, ensure_ascii=False) + "\n")

def _check(r, what):
    if r.status_code >= 400: raise RuntimeError(f"{what} -> HTTP {r.status_code}: {r.text[:300]}")
    return r.json()

def get(path, **kw):
    for i in range(GET_RETRIES):
        try:
            r = requests.get(BASE + path, headers=headers(), timeout=HTTP_TIMEOUT, **kw)
            if r.status_code >= 500 and i < GET_RETRIES - 1: time.sleep(2 ** i); continue
            return _check(r, f"GET {path}")
        except (requests.ConnectionError, requests.Timeout):
            if i == GET_RETRIES - 1: raise
            time.sleep(2 ** i)

def list_voices(provider, **filters):
    return get("/v3/voices", params={"provider": provider, **{k: v for k, v in filters.items() if v}})["data"]

def find_url(obj):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(v, str) and v.startswith("http") and k.lower() == "audio_url": return v
        for v in obj.values():
            u = find_url(v)
            if u: return u
    elif isinstance(obj, list):
        for v in obj:
            u = find_url(v)
            if u: return u

def wait_task(task_id):
    t0 = time.time()
    while time.time() - t0 < TASK_TIMEOUT:
        res = get(TASK_PATH.format(task_id=task_id))
        status = str(res.get("status", "")).lower()
        if status == "done": return res
        if status in ("error", "failed", "fail"): raise RuntimeError(f"Task {task_id} failed: {json.dumps(res, ensure_ascii=False)[:400]}")
        time.sleep(2)
    raise TimeoutError(f"Task {task_id} not done after {TASK_TIMEOUT}s (resume by re-running; no new job is created)")

def tts(text, voice_id, out, speed=1.0):
    out = Path(out); out.parent.mkdir(parents=True, exist_ok=True)
    pend = out.with_suffix(out.suffix + ".task")
    sig = hashlib.sha1(json.dumps([text, voice_id, float(speed)], ensure_ascii=False).encode("utf-8")).hexdigest()
    task_id, resumed = None, False
    if pend.exists():
        try: saved = json.loads(pend.read_text(encoding="utf-8"))
        except ValueError: saved = {}
        if saved.get("sig") == sig and saved.get("task_id"):      # same text+voice+speed: resume, don't pay twice
            task_id, resumed = saved["task_id"], True
        else:                                                      # interrupted job belongs to a different script/voice
            print(f"WARNING: discarding interrupted job {saved.get('task_id')} (text/voice/speed changed); a new paid job is created", file=sys.stderr)
            pend.unlink()
    if task_id is None:
        for stale in (out, out.with_suffix(".words.json")): stale.unlink(missing_ok=True)   # never leave old audio next to a new job
        data = {"text": text, "voice_id": voice_id, "speed": str(speed), "with_transcript": "true"}
        try:
            r = requests.post(BASE + "/v3/text-to-speech", headers=headers(), timeout=HTTP_TIMEOUT,
                              files={k: (None, v) for k, v in data.items()})
        except (requests.ConnectionError, requests.Timeout) as e:
            raise RuntimeError("POST outcome unknown (no response). NOT retrying to avoid a duplicate paid job; "
                               "check the ai33 dashboard, then re-run.") from e
        body = _check(r, "POST /v3/text-to-speech")
        if not body.get("success"): raise RuntimeError(f"TTS rejected: {body}")
        task_id = body["task_id"]; pend.write_text(json.dumps({"task_id": task_id, "sig": sig}), encoding="utf-8")
    res = wait_task(task_id)
    url = find_url(res)
    if not url: raise RuntimeError(f"No audio_url in task result for {task_id}")
    audio = requests.get(url, timeout=120); audio.raise_for_status()
    out.write_bytes(audio.content)
    jurl = (res.get("metadata") or {}).get("json_url")
    words = out.with_suffix(".words.json")
    if jurl:
        w = requests.get(jurl, timeout=60); w.raise_for_status(); words.write_bytes(w.content)
    pend.unlink(missing_ok=True)
    log_call({"task_id": task_id, "chars": len(text), "credit_cost": res.get("credit_cost"),
              "transcript_cost": (res.get("metadata") or {}).get("transcript_credit_cost"), "resumed": resumed, "file": str(out)})
    return {"task_id": task_id, "file": str(out), "bytes": len(audio.content)}

def main():
    ap = argparse.ArgumentParser(); sp = ap.add_subparsers(dest="cmd", required=True)
    v = sp.add_parser("voices"); v.add_argument("--provider", required=True)
    v.add_argument("--language"); v.add_argument("--gender"); v.add_argument("--search")
    t = sp.add_parser("tts"); t.add_argument("--voice", required=True)
    t.add_argument("--text"); t.add_argument("--text-file"); t.add_argument("--out", required=True)
    t.add_argument("--speed", type=float, default=1.0)
    a = ap.parse_args()
    if a.cmd == "voices":
        for x in list_voices(a.provider, language=a.language, gender=a.gender, search=a.search):
            print(x["voice_id"], "|", x.get("name"), "|", x.get("language"), "|", x.get("gender"))
    else:
        text = a.text or Path(a.text_file).read_text(encoding="utf-8")
        print(json.dumps(tts(text, a.voice, a.out, a.speed), ensure_ascii=False))

if __name__ == "__main__":
    main()
