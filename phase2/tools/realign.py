"""Keep a scene's cue-based timing consistent after its spoken text changed.

Every action cue, face cue and `appear` phrase must be words that occur in the voice text (validate_storyboard enforces it). When the owner edits the
voice text, `realign(scene, new_voice)` returns the scene with those references repaired plus a list of what it did:
  kept      the phrase is still in the text                              (nothing to do)
  matched   a very similar phrase exists in the new text (>= 0.75)       (replaced automatically)
  proposed  a weaker match (0.55-0.75)                                    (replaced, flagged for the owner to check)
  approx    nothing similar: the cue becomes an approximate time from the phrase's relative position in the old text (flagged)
Subtitles that no longer follow the text are reset to "auto". Pure function: no I/O, no AI call, deterministic."""
import copy
import difflib
import re

norm = lambda s: re.sub(r"[^\w]+", " ", str(s).lower()).split()


def has_phrase(voice, phrase):
    v, p = norm(voice), norm(phrase)
    return bool(p) and any(v[i:i + len(p)] == p for i in range(len(v) - len(p) + 1))


def _tokens(voice):
    """-> [(word as written without edge punctuation, normalised word)]"""
    out = []
    for w in voice.split():
        n = norm(w)
        if n:
            out.append((w.strip(".,;:!?\"'()“”"), " ".join(n)))
    return out


def best_phrase(voice, phrase, old_voice=None):
    """-> (score 0-1, phrase text from the voice, start word index) for the most similar run of words in `voice`.
    Score = character similarity, blended with shared whole words, plus a small bonus when the run sits at about the same relative position
    as the phrase did in the old text and shares at least one word (a reworded cue stays where it was)."""
    toks, pw = _tokens(voice), norm(phrase)
    pn = " ".join(pw)
    n = max(1, len(pw))
    rel_old = None
    if old_voice:
        ot = _tokens(old_voice)
        idx = next((i for i, t in enumerate(ot) if pw and t[1].split()[:1] == pw[:1]), None)
        rel_old = None if idx is None else idx / max(1, len(ot))
    best = (0.0, None, 0)
    for size in {max(1, n - 1), n, n + 1}:
        for i in range(0, max(0, len(toks) - size) + 1):
            run = toks[i:i + size]
            if len(run) < size:
                continue
            rn = " ".join(t[1] for t in run)
            ch = difflib.SequenceMatcher(None, pn, rn).ratio()
            shared = len(set(pw) & set(rn.split()))
            sc = max(ch, 0.5 * ch + 0.5 * shared / n)
            if shared and rel_old is not None and abs(i / max(1, len(toks)) - rel_old) < 0.2:
                sc += 0.2
            sc = min(sc + (0.02 if size == n else 0), 1.0)           # same length as the old phrase wins ties
            if sc > best[0]:
                best = (sc, " ".join(t[0] for t in run), i)
    return best


def _fix(voice_old, voice_new, phrase, est_sec_per_word, changes, where, numeric_key=None):
    """-> replacement value for one cue reference: ('cue', text) or ('time', seconds) or None (unchanged)."""
    if has_phrase(voice_new, phrase):
        return None
    sc, text, _ = best_phrase(voice_new, phrase, voice_old)
    if text and sc >= 0.75:
        changes.append({"where": where, "kind": "matched", "old": phrase, "new": text, "score": round(sc, 2)})
        return ("cue", text)
    if text and sc >= 0.55:
        changes.append({"where": where, "kind": "proposed", "old": phrase, "new": text, "score": round(sc, 2)})
        return ("cue", text)
    old_toks = _tokens(voice_old)
    first = norm(phrase)[:1]
    idx = next((i for i, t in enumerate(old_toks) if first and t[1].split()[:1] == first), 0)
    rel = idx / max(1, len(old_toks))
    t = round(0.15 + rel * len(_tokens(voice_new)) * est_sec_per_word, 1)
    changes.append({"where": where, "kind": "approx", "old": phrase, "new": f"~{t}s", "score": round(sc, 2)})
    return ("time", t)


def realign(scene, new_voice, est_sec_per_word=0.4):
    """-> (new_scene, changes). The scene's own voice is replaced by `new_voice`."""
    sc = copy.deepcopy(scene)
    old_voice = sc.get("voice", "")
    sc["voice"] = new_voice
    ch = []
    sid = sc.get("id", "?")
    def fix_actor(obj, who):                       # the scene's main character and every cast member carry their own cues
        for ai, a in enumerate(obj.get("actions", [])):
            if "cue" in a:
                r = _fix(old_voice, new_voice, a["cue"], est_sec_per_word, ch, f"{who}: action {a.get('name')} cue")
                if r and r[0] == "cue":
                    a["cue"] = r[1]
                elif r:
                    a.pop("cue")
                    a["at"] = r[1]
            if "cues" in a:
                new = []
                for c in a["cues"]:
                    r = _fix(old_voice, new_voice, c, est_sec_per_word, ch, f"{who}: action {a.get('name')} cues")
                    new.append(c if r is None else (r[1] if r[0] == "cue" else None))
                    if r and r[0] == "time":
                        ch[-1]["new"] += " (cue removed)"
                a["cues"] = [c for c in new if c]
                if not a["cues"]:
                    a.pop("cues")
                    a.setdefault("at", 0.3)
                    ch.append({"where": f"{who}: action {a.get('name')}", "kind": "approx", "old": "cues", "new": f"~{a['at']}s", "score": 0})
        for f in obj.get("face_cues", []):
            r = _fix(old_voice, new_voice, f["cue"], est_sec_per_word, ch, f"{who}: face cue")
            if r and r[0] == "cue":
                f["cue"] = r[1]
        f2 = []
        for f in obj.get("face_cues", []):
            if has_phrase(new_voice, f["cue"]):
                f2.append(f)
            else:
                ch.append({"where": f"{who}: face cue", "kind": "approx", "old": f["cue"], "new": "(removed)", "score": 0})
        obj["face_cues"] = f2
    fix_actor(sc, sid)
    for ci, c in enumerate(sc.get("cast") or []):
        fix_actor(c, f"{sid}/cast{ci + 1}")

    def fix_appear(obj, key, where):
        v = obj.get(key)
        if isinstance(v, str):
            r = _fix(old_voice, new_voice, v, est_sec_per_word, ch, where)
            if r:
                obj[key] = r[1]

    for it in sc.get("items", []):
        t = it.get("type")
        fix_appear(it, "appear", f"{sid}: {t} appear")
        for sub in it.get("bars", []) + it.get("rows", []) + it.get("parts", []) + it.get("cells", []):
            fix_appear(sub, "appear", f"{sid}: {t} item appear")
        if isinstance(it.get("appears"), list):
            for i, v in enumerate(it["appears"]):
                if isinstance(v, str):
                    r = _fix(old_voice, new_voice, v, est_sec_per_word, ch, f"{sid}: {t} appears[{i}]")
                    if r:
                        it["appears"][i] = r[1]
    subs = sc.get("subtitles")
    if isinstance(subs, list) and subs:
        vt, pos, ok = norm(new_voice), 0, True
        for seg in subs:
            st = norm(seg)
            idx = next((j for j in range(pos, len(vt) - len(st) + 1) if vt[j:j + len(st)] == st), None)
            if idx is None:
                ok = False
                break
            pos = idx + len(st)
        if not ok:
            sc["subtitles"] = "auto"
            ch.append({"where": f"{sid}: subtitles", "kind": "matched", "old": " / ".join(subs), "new": "auto", "score": 1.0})
    return sc, ch
