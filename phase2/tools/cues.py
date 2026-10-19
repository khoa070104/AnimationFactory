"""Word-level timing helpers on the voice engine's word timestamps (sceneNN.words.json)."""
import json
import re
from pathlib import Path

norm = lambda s: re.sub(r"[^\w]+", " ", s.lower()).split()


def words_of(words_json):
    ws = json.loads(Path(words_json).read_text(encoding="utf-8"))[0]["words"]
    return [w for w in ws if w["type"] == "word"]


def _tok(w):
    t = norm(w["text"])
    return t[0] if t else ""


def find_phrase(ws, phrase, start=0):
    toks = norm(phrase)
    for i in range(start, len(ws) - len(toks) + 1):
        if [_tok(w) for w in ws[i:i + len(toks)]] == toks:
            return i, i + len(toks) - 1
    raise ValueError(f"cue {phrase!r} not found in the spoken words")


def cue_time(words_json, phrase):
    """Start time (s, relative to the audio file) of the first occurrence of the phrase."""
    ws = words_of(words_json)
    i, _ = find_phrase(ws, phrase)
    return ws[i]["start"]


def segment_times(words_json, segments):
    """Sequentially match each subtitle segment to the spoken words -> [(t_start, t_end)] relative to the audio."""
    ws = words_of(words_json)
    out, ptr = [], 0
    for seg in segments:
        i, j = find_phrase(ws, seg, ptr)
        out.append((ws[i]["start"], ws[j]["end"]))
        ptr = j + 1
    return out
