import json, os, re
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
def config_path():
    return Path(os.environ.get("AF_CONFIG") or ROOT / "project/config.json")
def load_config():
    return json.loads(config_path().read_text(encoding="utf-8"))
def work_dir():
    return Path(os.environ.get("AF_WORK") or ROOT / "work")
def _norm(s): return re.sub(r"[^\w]", "", s.lower())
def cue_time(words_file, phrase):
    """Start time (s) of the first occurrence of phrase in the voice's word timings."""
    ws = [w for w in json.loads(Path(words_file).read_text(encoding="utf-8"))[0]["words"] if w["type"] == "word"]
    toks = [_norm(t) for t in phrase.split()]
    for i in range(len(ws) - len(toks) + 1):
        if [_norm(w["text"]) for w in ws[i:i + len(toks)]] == toks:
            return ws[i]["start"]
    raise ValueError(f"cue {phrase!r} not found in {words_file}")
