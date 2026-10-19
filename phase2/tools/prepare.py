"""AI preparation of a project: brief + channel profile -> research -> script -> storyboard -> asset plan -> assets.
Everything lands as data in PROJECT/prepare/ and in storyboard.json; the owner approves in the UI; nothing paid is started without that.

  python prepare.py PROJECT [--step research|script|storyboard|assetplan|assets|apply_assets|all] [--force STEP]
  `all` runs research, script, storyboard, assetplan and stops at the owner's approval of the asset plan.

Rules
  * resumable: every step records its inputs hash; a step whose inputs did not change and that already succeeded is SKIPPED (no AI call);
    a failed step keeps all earlier results and can simply be run again;
  * the AI only chooses from capabilities.py; the result must pass validate_storyboard (deterministic cue repair first, then at most 2 AI repair
    rounds); the spoken text of the storyboard is always the approved script text, the AI only designs the visuals;
  * an AI step never overwrites work the owner has already edited or approved unless it is forced (the previous storyboard is kept in versions/);
  * limits (calls / tokens / images) are checked before every AI call (budget.py)."""
import argparse
import hashlib
import json
import os
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import agy_image as G
import agy_slots
import budget
import capabilities
import channel as CH
import characters as CHR
import llm
import realign
import research as R
import sbload
import sbstore

P2 = Path(__file__).resolve().parent.parent
STEPS = ["research", "script", "characters", "storyboard", "assetplan", "assets"]
OPTIONAL = ["opportunity", "chargen"]   # steps the owner starts on purpose (topic research; drawing the cast), not part of "AI chuẩn bị"
ASSET_CAP = 6                       # most AI assets planned per video (the image budget still caps it)
PLAN_STEPS = STEPS[:5]          # what "AI chuẩn bị" runs; `assets` waits for the owner's approval of the plan
RUNNER = None                  # test hooks: replace the LLM runner / the page fetcher / the image runner
FETCHER = None
FETCHER_RAW = None                # raw-page fetcher for opportunity research (tests replace it)
IMAGE_RUNNER = None
ID_RE = re.compile(r"^[a-z0-9_]{1,40}$")


class PrepareError(RuntimeError):
    pass


# ------------------------------------------------------------------------------------------------------------------ plumbing
def pdir(proj):
    d = Path(proj) / "prepare"
    d.mkdir(exist_ok=True)
    return d


def sha(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()[:16]


def jget(f, default=None):
    return G.read_json(f, default)


def brief_of(proj):
    b = jget(Path(proj) / "brief.json", {}) or {}
    b.setdefault("channel", "default")
    b.setdefault("research", "auto")
    b.setdefault("asset_policy", "legacy")          # briefs written before Phase 4 keep the old behaviour
    b.setdefault("character_mode", "bi")
    return b


def channel_of(brief):
    return CH.get(brief.get("channel") or "default")


def status_file(proj):
    return pdir(proj) / "status.json"


def status(proj):
    return jget(status_file(proj), {"steps": {}})


def _set(proj, name, **kw):
    st = status(proj)
    cell = st["steps"].setdefault(name, {})
    cell.update(kw)
    st["updated"] = time.strftime("%Y-%m-%d %H:%M:%S")
    G.write_json_atomic(status_file(proj), st)
    return cell


def effective_state(cell):
    """A step recorded as running whose process is gone is shown as `interrupted`."""
    if cell.get("state") == "running":
        o = cell.get("owner") or {}
        if not (o.get("pid") and agy_slots.proc_stamp(o["pid"]) == o.get("stamp")):
            return "interrupted"
    return cell.get("state", "pending")


class step_run:
    def __init__(self, proj, name, inputs):
        self.proj, self.name, self.inputs = proj, name, inputs

    def __enter__(self):
        _set(self.proj, self.name, state="running", inputs=self.inputs, error=None, started=time.strftime("%H:%M:%S"),
             owner={"pid": os.getpid(), "stamp": agy_slots.proc_stamp(os.getpid())}, calls_before=budget.usage(self.proj)["llm_calls"])
        return self

    def __exit__(self, et, ev, tb):
        used = budget.usage(self.proj)["llm_calls"] - (status(self.proj)["steps"][self.name].get("calls_before") or 0)
        if ev is None:
            _set(self.proj, self.name, state="ok", finished=time.strftime("%H:%M:%S"), llm_calls=used, owner=None)
        else:
            _set(self.proj, self.name, state="failed", error=str(ev), finished=time.strftime("%H:%M:%S"), llm_calls=used, owner=None)
        return False


def fresh(proj, name, inputs):
    cell = status(proj)["steps"].get(name) or {}
    return cell.get("state") == "ok" and cell.get("inputs") == inputs


def chars_per_sec():
    import build_storyboard as SBD
    return SBD.CHARS_PER_SEC


def targets_of(brief, ch):
    t = dict(ch.get("targets") or {"duration": [60, 90], "scenes": [6, 10]})
    d = brief.get("duration_seconds")
    if d:
        d = int(d)
        t["duration"] = [max(20, d - 15), d + 15]                 # the asked length is a wish, +-15 s is the acceptance window
    chan = list(t["scenes"])
    n = brief.get("scene_count")
    if isinstance(n, (int, float)) and not isinstance(n, bool) and n >= 1:           # 1. the owner's explicit scene count always wins
        t["scenes"], t["scenes_source"] = [int(n), int(n)], "brief"
    elif isinstance(n, list) and len(n) == 2 and all(isinstance(x, (int, float)) for x in n):
        t["scenes"], t["scenes_source"] = [int(n[0]), int(n[1])], "brief"
    elif d:                                                                           # 2. else it follows the asked length (a 75 s video is not 3 long scenes)
        lo = max(2, round(int(d) / 13))
        t["scenes"], t["scenes_source"] = [lo, max(lo + 1, min(10, round(int(d) / 7.5)))], "duration"
    else:
        t["scenes_source"] = "channel"                                                # 3. else the channel's own range
    if t["scenes"] != chan and t["scenes_source"] != "channel":
        t["note"] = f"scene count {t['scenes']} comes from the {'owner brief' if t['scenes_source'] == 'brief' else 'asked duration'}, overriding the channel range {chan}"
    return t


# ------------------------------------------------------------------------------------------------------------------ research
def do_research(proj, force=False):
    brief, ch = brief_of(proj), None
    ch = channel_of(brief)
    inputs = sha([{k: brief.get(k) for k in ("title", "goal", "message", "audience", "references", "research")}, CH.fingerprint(ch)])
    if fresh(proj, "research", inputs) and not force:
        return "skipped"
    with step_run(proj, "research", inputs):
        res = R.run(proj, brief, ch, brief.get("research", "auto"), fetcher=FETCHER, runner=RUNNER)
        G.write_json_atomic(pdir(proj) / "research.json", res)
    return "ok"


def research_facts(proj):
    """Facts the script may rely on: verified, or accepted by the owner. Never the ones marked needs_check and not accepted."""
    r = jget(pdir(proj) / "research.json", {}) or {}
    return [f for f in r.get("facts", []) if (f.get("verified") or f.get("decision") == "accept") and f.get("decision") != "remove"]


def set_fact_decision(proj, fact_id, decision):
    if decision not in ("accept", "remove", None):
        raise PrepareError("decision must be accept | remove")
    f = pdir(proj) / "research.json"
    r = jget(f, {})
    hit = [x for x in r.get("facts", []) if x["id"] == fact_id]
    if not hit:
        raise PrepareError(f"unknown fact {fact_id}")
    hit[0]["decision"] = decision
    G.write_json_atomic(f, r)


# ------------------------------------------------------------------------------------------------------------------ script
SCRIPT_SCHEMA = {"type": "object", "required": ["title", "scenes"], "properties": {
    "title": {"type": "string"},
    "scenes": {"type": "array", "minItems": 3, "maxItems": 14, "items": {"type": "object", "required": ["title", "section", "voice"], "properties": {
        "title": {"type": "string"}, "section": {"type": "string", "enum": ["hook", "body", "end"]}, "voice": {"type": "string"},
        "notes": {"type": "string"}, "fact_ids": {"type": "array", "items": {"type": "string"}}}}},
    "claims_to_verify": {"type": "array", "items": {"type": "object", "required": ["text"], "properties": {"text": {"type": "string"}, "reason": {"type": "string"}}}}}}


def split_user_script(text, targets):
    """Owner-supplied script -> scenes: paragraphs are scenes; too few -> split long ones by sentence; too many -> merge neighbours."""
    paras = [re.sub(r"\s+", " ", p).strip() for p in re.split(r"\n\s*\n", text.strip()) if p.strip()]
    lo, hi = targets["scenes"]
    while len(paras) < lo:
        i = max(range(len(paras)), key=lambda k: len(paras[k]))
        sents = re.split(r"(?<=[.!?])\s+", paras[i])
        if len(sents) < 2:
            break
        h = len(sents) // 2
        paras[i:i + 1] = [" ".join(sents[:h]), " ".join(sents[h:])]
    while len(paras) > hi:
        i = min(range(len(paras) - 1), key=lambda k: len(paras[k]) + len(paras[k + 1]))
        paras[i:i + 2] = [paras[i] + " " + paras[i + 1]]
    scenes = []
    for k, p in enumerate(paras):
        scenes.append({"title": " ".join(p.split()[:5]).rstrip(".,;:"), "section": "hook" if k == 0 else ("end" if k == len(paras) - 1 else "body"), "voice": p, "notes": "", "fact_ids": []})
    return scenes


def script_stats(scenes, brief, ch):
    tm = {"lead": 0.15, "word_pad": 0.15, "tail": 0.3}
    cps = chars_per_sec()
    chars = sum(len(s["voice"]) for s in scenes)
    return {"scenes": len(scenes), "chars": chars, "est_seconds": round(chars / cps + len(scenes) * (tm["lead"] + tm["word_pad"] + tm["tail"]), 1)}


def script_prompt(brief, ch, facts, refs, tg, n_target, chars_target, extra=""):
    fl = "\n".join(f"- [{f['id']}] {f['claim']} (source: {f.get('final_url') or f['url']})" for f in facts) or "(none: do not state specific statistics, laws or dates as fact)"
    rl = "\n".join(f"- {r['url']}: {r['excerpt'][:700]}" for r in refs if r.get("reachable")) or "(none)"
    return (f"Write the voice-over script of a short explainer video in {ch.get('language', 'vi')} (Vietnamese unless the profile says otherwise).\n\n"
            f"CHANNEL PROFILE\n- audience: {ch['audience']}\n- tone: {ch['tone']}\n- visual style (for context): {ch['visual_style']}\n- avoid: {'; '.join(ch.get('avoid', [])) or '-'}\n"
            f"- guiding message of the channel: {ch['guiding_message']}\n\nBRIEF\n- topic: {brief.get('title', '')}\n- goal: {brief.get('goal', '')}\n- key message: {brief.get('message', '')}\n"
            f"- audience for this video: {brief.get('audience') or ch['audience']}\n- notes: {brief.get('notes', '')}\n- story guideline from the owner: {brief.get('story_guideline') or '(none)'}\n- main character the owner described (if any): {brief.get('character_hint') or '(none)'}\n\nVERIFIED FACTS YOU MAY USE (cite their ids in fact_ids)\n{fl}\n\n"
            f"OWNER REFERENCES\n{rl}\n\nREQUIREMENTS\n- No emoji and no absolute promises ('never', '0 đồng', 'không bỏ phí'): say 'hạn chế', 'giảm', 'bớt'.\n- {tg['scenes'][0]}-{tg['scenes'][1]} scenes (aim for {n_target}); scene 1 section 'hook', last scene section 'end', others 'body'.\n"
            f"- total spoken text about {chars_target} characters (each scene 90-260 characters), so the video lasts {tg['duration'][0]}-{tg['duration'][1]} seconds.\n"
            "- spoken language: short sentences, write every number in words (e.g. 'hai triệu', 'ba đến sáu tháng'), no emoji, no markdown, no brand names, no stage directions in `voice`.\n"
            "- if the guideline or character asks for a story with people (a student, a sister, a mentor...), tell it as a narrator who names them in the third person, so they can be drawn on screen and speak through the narration; otherwise address the viewer.\n"
            "- clear arc: opening with a relatable situation, development with one idea per scene, a closing takeaway.\n"
            "- never present a statistic/legal rule/date as fact unless it comes from the verified facts; anything else you are unsure of goes to claims_to_verify instead of the voice text.\n"
            f"- notes = one line for the storyboard designer about what should be seen on screen.\n{extra}\nTASK: script")


def do_script(proj, force=False):
    brief = brief_of(proj)
    ch = channel_of(brief)
    tg = targets_of(brief, ch)
    facts, r = research_facts(proj), jget(pdir(proj) / "research.json", {}) or {}
    inputs = sha([{k: brief.get(k) for k in ("title", "goal", "message", "audience", "notes", "script_text", "duration_seconds", "story_guideline", "character_hint")}, CH.fingerprint(ch), [f["id"] + str(f.get("decision")) for f in facts]])
    if fresh(proj, "script", inputs) and not force:
        return "skipped"
    sbf = Path(proj) / "storyboard.json"
    sb = jget(sbf, {}) or {}
    if (sb.get("scenes") and (Path(proj) / "approval.json").exists()) and not force:
        raise PrepareError("the script/storyboard was already approved; rewriting it needs an explicit 'force' (the current version is kept in versions/)")
    with step_run(proj, "script", inputs):
        if str(brief.get("script_text") or "").strip():
            scenes, claims, model, source = split_user_script(brief["script_text"], tg), [], None, "user"
            title = brief.get("title") or "Video"
        else:
            n = (tg["scenes"][0] + tg["scenes"][1]) // 2
            mid = sum(tg["duration"]) / 2
            chars_target = int((mid - 0.6 * n) * chars_per_sec())
            out = llm.call(proj, "script", "quality", script_prompt(brief, ch, facts, r.get("references", []), tg, n, chars_target), SCRIPT_SCHEMA, runner=RUNNER)
            d = out["data"]
            scenes, claims, title, model, source = d["scenes"], d.get("claims_to_verify", []), d["title"], out["meta"].get("model_actual") or out["meta"].get("model"), "ai"
            st = script_stats(scenes, brief, ch)
            lo, hi = tg["duration"]
            if not lo <= st["est_seconds"] <= hi or not tg["scenes"][0] <= st["scenes"] <= tg["scenes"][1]:        # one corrective call, not a loop
                fix = (f"\n\nYOUR PREVIOUS DRAFT was {st['est_seconds']} s and {st['scenes']} scenes, outside the target. Rewrite it to fit {tg['duration']} seconds and "
                       f"{tg['scenes']} scenes, keeping the same ideas. Previous draft voice texts:\n" + "\n".join(f"{i + 1}. {s['voice']}" for i, s in enumerate(scenes)))
                out2 = llm.call(proj, "script_fit", "quality", script_prompt(brief, ch, facts, r.get("references", []), tg, n, chars_target, fix), SCRIPT_SCHEMA, runner=RUNNER)
                d2 = out2["data"]
                if abs(script_stats(d2["scenes"], brief, ch)["est_seconds"] - mid) < abs(st["est_seconds"] - mid):
                    scenes, claims, title = d2["scenes"], d2.get("claims_to_verify", claims), d2["title"]
        for i, s in enumerate(scenes, 1):
            s["id"] = f"s{i:02d}"
            s.setdefault("notes", "")
            s.setdefault("fact_ids", [])
        G.write_json_atomic(pdir(proj) / "script.json", {"title": title, "source": source, "model": model, "scenes": scenes, "claims_to_verify": claims,
                                                         "stats": script_stats(scenes, brief, ch), "created": time.strftime("%Y-%m-%d %H:%M:%S")})
    return "ok"


# ------------------------------------------------------------------------------------------------------------------ characters
CHAR_SCHEMA = {"type": "object", "required": ["characters"], "properties": {"rationale": {"type": "string"}, "characters": {"type": "array", "minItems": 1, "maxItems": 2, "items": {
    "type": "object", "required": ["id", "name", "role", "description"], "properties": {
        "id": {"type": "string"}, "name": {"type": "string"}, "role": {"type": "string", "enum": ["main", "support"]}, "description": {"type": "string"},
        "outfit": {"type": "string"}, "personality": {"type": "string"}}}}}}


def clean_id(raw, taken):
    import re as _re
    base = _re.sub(r"[^a-z0-9]+", "_", str(raw).lower()).strip("_")[:16] or "nhanvat"
    if base == CHR.BUILTIN:
        base = "nv_bi"
    cid, k = base, 2
    while cid in taken:
        cid = f"{base[:13]}_{k}"
        k += 1
    return cid


def characters_plan(proj):
    return jget(pdir(proj) / "characters_plan.json", {"mode": "bi", "characters": []}) or {"mode": "bi", "characters": []}


def main_character(proj):
    for c in characters_plan(proj).get("characters", []):
        if c.get("role") == "main":
            return c["id"]
    cs = characters_plan(proj).get("characters", [])
    return cs[0]["id"] if cs else None


def characters_prompt(brief, ch, script):
    story = "\n".join(f"{s['id']} [{s['section']}] {s['title']}: {s['voice']}" for s in script["scenes"])
    hint = str(brief.get("character_hint") or "").strip()
    return ("Design the CAST of a short 2D explainer/story video. The characters will be drawn by an image model as a flat cut-out cartoon (outline, flat colours) and animated "
            "(arms, legs, head, expressions), so describe them concretely and simply.\n\n"
            f"CHANNEL: audience {ch['audience']}; visual style {ch['visual_style']}; avoid: {'; '.join(ch.get('avoid', [])) or '-'}.\n"
            f"STORY GUIDELINE from the owner: {brief.get('story_guideline') or '(none)'}\n"
            + (f"THE OWNER'S MAIN CHARACTER (keep exactly this look, you only add details such as colours): {hint}\n" if hint else "") +
            f"\nSCRIPT (voice-over by scene):\n{story}\n\n"
            "Return ONE main character (the viewer follows them) and, only if the story clearly needs a second person, ONE supporting character. For each: id (lowercase letters/digits/_, max 16), "
            "name (a short, easy-to-say Vietnamese-friendly name), role main|support, description (face shape, hair, skin tone, build, typical expression), outfit (clothes WITH colours, "
            "accessories), personality (one line). Characters must look clearly different from each other, be adult-audience friendly, and have NO text or logos on clothes.\nTASK: characters")


def _copy_series(proj, brief):
    """asset_policy 'series': take the characters (profile, rig, part images, both sheets with their approvals) of the series project, same versions."""
    import shutil
    src = P2 / "projects" / str(brief.get("series_from"))
    if not (src / "storyboard.json").exists():
        raise PrepareError(f"series project {brief.get('series_from')!r} not found")
    ids = CHR.list_ids(src)
    if not ids:
        raise PrepareError(f"series project {brief.get('series_from')!r} has no AI characters to continue")
    out = []
    for cid in ids:
        dst = CHR.cdir(proj, cid)
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(CHR.cdir(src, cid), dst)
        for aid in CHR.sheet_ids(cid):
            e = G.load_manifest(src)["assets"].get(aid)
            if not e or not e.get("file"):
                raise PrepareError(f"series character {cid}: sheet {aid} is missing in {src.name}")
            (Path(proj) / "ai_assets").mkdir(parents=True, exist_ok=True)
            shutil.copy(src / e["file"], Path(proj) / "ai_assets" / f"{aid}.png")
            ne = dict(e)
            ne["reused_from"] = {"project": src.name, "asset": aid}
            G.put_asset(proj, aid, ne)
        out.append(CHR.get_profile(proj, cid))
    return {"mode": "series", "from": src.name, "characters": out}


def do_characters(proj, force=False):
    brief = brief_of(proj)
    ch = channel_of(brief)
    script = jget(pdir(proj) / "script.json")
    if not script:
        raise PrepareError("no script yet: run the script step first")
    mode, policy = brief.get("character_mode", "bi"), brief.get("asset_policy", "legacy")
    inputs = sha([mode, policy, brief.get("series_from"), brief.get("character_hint"), brief.get("story_guideline"), [(x["id"], x["voice"]) for x in script["scenes"]], CH.fingerprint(ch)])
    if fresh(proj, "characters", inputs) and not force:
        return "skipped"
    existing = [c for c in CHR.list_ids(proj) if (CHR.cdir(proj, c) / "rig.json").exists() or CHR.state(proj, c)[0] == "approved"]
    if existing and mode == "ai" and policy != "series" and not force:
        raise PrepareError(f"characters {existing} already have a rig or approval; redesigning the cast needs an explicit 'force' (their files are kept)")
    with step_run(proj, "characters", inputs):
        if mode == "bi":
            plan = {"mode": "bi", "characters": []}
        elif policy == "series":
            plan = _copy_series(proj, brief)
        else:
            out = llm.call(proj, "characters", "quality", characters_prompt(brief, ch, script), CHAR_SCHEMA, runner=RUNNER)
            taken, chars = set(), []
            for c in out["data"]["characters"][:2]:
                cid = clean_id(c.get("id") or c["name"], taken)
                taken.add(cid)
                chars.append({**c, "id": cid})
            if not any(c["role"] == "main" for c in chars):
                chars[0]["role"] = "main"
            for c in chars:
                CHR.save_profile(proj, c["id"], c)
            CHR.retire_unused(proj, {c["id"] for c in chars})
            plan = {"mode": "ai", "characters": chars, "rationale": out["data"].get("rationale", ""), "model": out["meta"].get("model_actual") or out["meta"].get("model")}
        G.write_json_atomic(pdir(proj) / "characters_plan.json", plan)
    return "ok"


def generate_characters(proj, poll=2.0, max_wait=1800, rounds=2):
    """Make the sheets of every AI character the storyboard USES (parts first, then faces with the parts sheet as reference), slice them into the rig.
    A bad sheet (wrong piece count / proportions) is regenerated once with the reason in the prompt; the image limit applies to every run."""
    import agy_jobs as J
    name = Path(proj).name
    kw = {"runner": IMAGE_RUNNER} if IMAGE_RUNNER else {}
    sb = jget(Path(proj) / "storyboard.json", {}) or {}
    problems = []
    for cid in [c for c in CHR.used_ids(sb) if c != CHR.BUILTIN]:
        if CHR.state(proj, cid)[0] == "approved":
            continue
        prof = CHR.get_profile(proj, cid)
        if not prof:
            problems.append(f"{cid}: no profile")
            continue
        extra = {}
        for attempt in range(rounds):
            parts_req, faces_req = CHR.sheet_requests(proj, cid)
            for nm, req in (("parts", parts_req), ("faces", faces_req)):
                aid = req["asset_id"]
                if extra.get(nm):
                    req = {**req, "prompt": req["prompt"] + " " + extra[nm], "regenerate": True}
                if nm == "faces":
                    pe = G.load_manifest(proj)["assets"].get(parts_req["asset_id"])
                    if pe and pe.get("file"):
                        req = {**req, "reference_images": [str(Path(proj) / pe["file"])] + req.get("reference_images", [])[:1]}
                cur = G.load_manifest(proj)["assets"].get(aid)
                if cur and cur.get("status") in ("draft", "approved") and not extra.get(nm) and G.file_problem(proj, cur) is None:
                    continue
                j = J.submit(name, req, **kw)
                end = time.time() + max_wait
                while True:
                    st = J.check(name, j["job_id"])
                    if st["state"] == "succeeded":
                        break
                    if st["state"] in ("failed", "timeout", "interrupted", "superseded", "invalid") or time.time() > end:
                        problems.append(f"{cid}/{nm}: {st['state']} {st.get('error') or ''}".strip())
                        break
                    time.sleep(poll)
                if problems and problems[-1].startswith(f"{cid}/{nm}"):
                    break
            if problems and problems[-1].startswith(f"{cid}/"):
                break
            try:
                CHR.build(proj, cid)
                break
            except char_rig_error() as e:
                msg = str(e)
                if attempt + 1 >= rounds:
                    problems.append(f"{cid}: {msg}")
                    break
                which = "faces" if msg.startswith("faces sheet") else "parts"
                extra = {which: f"IMPORTANT: the previous picture was rejected ({msg}). Follow the layout exactly: separate pieces in one row with wide white gaps."}
    if problems:
        raise PrepareError("characters incomplete: " + "; ".join(problems))


def char_rig_error():
    import char_rig
    return char_rig.CharRigError


def approve_character(proj, cid, by, note=""):
    """The owner approves the character = both sheets, hash-bound; refused unless the rig was built from exactly these sheets."""
    stt, why = CHR.state(proj, cid)
    if stt == "approved":
        return stt
    rig = G.read_json(CHR.cdir(proj, cid) / "rig.json")
    if not rig or rig.get("sources") != CHR.sheets_hashes(proj, cid):
        raise PrepareError(f"character {cid} has no rig built from its current sheets ({why}); build the rig first")
    for aid in CHR.sheet_ids(cid):
        G.set_status(proj, aid, "approved", approved_by=by, approved_on=time.strftime("%Y-%m-%d"))
    with (Path(proj) / "approvals_history.jsonl").open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({"at": time.strftime("%Y-%m-%d %H:%M:%S"), "kind": "character", "id": cid, "by": by, "note": note, "rig_sha": sha(rig)}, ensure_ascii=False) + "\n")
    return CHR.state(proj, cid)[0]


# ------------------------------------------------------------------------------------------------------------------ storyboard
def visual_schema():
    s = json.loads(json.dumps(capabilities.scene_schema()))
    s["required"] = ["id", "bg", "bi", "items"]
    s["properties"].pop("voice", None)
    s["properties"].pop("title", None)
    return {"type": "object", "required": ["scenes"], "properties": {"scenes": {"type": "array", "items": s}}}


def storyboard_prompt(proj, brief, ch, script):
    cat = capabilities.capabilities(proj)
    ex = jget(P2 / "style" / "storyboard_examples.json")
    keep = {k: cat[k] for k in ("canvas", "actions", "poses", "faces", "props", "ai_assets", "backgrounds", "text_colors", "accent_colors", "camera_presets", "item_types", "sub_fields", "appear_note", "rules")}
    sc = "\n".join(f"{s['id']} [{s['section']}] {s['title']}: {s['voice']}\n   screen note: {s.get('notes', '')}" for s in script["scenes"])
    cp = characters_plan(proj)
    cast_txt = ""
    if cp.get("characters"):
        cast_txt = ("\nCHARACTERS of this video (besides the built-in 'bi', do not use bi): " + json.dumps([{k: c.get(k) for k in ("id", "name", "role", "description")} for c in cp["characters"]], ensure_ascii=False) +
                    "\n- Set bi.char to the character who acts in the scene (normally the MAIN one, id above); bi stays the left-hand actor (x≈520, y≈960, scale 1.0, pose/face/actions as before).\n"
                    "- EVERY listed character must appear in at least one scene: the supporting character goes into `cast` in the scenes where the script involves another person (a mentor, sibling, friend...), "
                    "so use `cast` in at least a third of the scenes when a supporting character exists. Cast entries: {char, x≈1500, y≈960, scale 1.0, flip true (faces left), face, pose, actions, face_cues} with their own actions/cues. "
                    "When a scene has cast, keep graphics in the middle band x 850-1250.\n")
    return ("Design the visuals of every scene of a 2D explainer video made by a tool. You may ONLY use what the CAPABILITIES list offers (action, pose, face, prop, item type, colour names). "
            "You do not write or change the spoken text; you choose, per scene: background, the character's starting face/pose, actions (with cues), face changes, and the on-screen items.\n\n"
            f"CHANNEL visual style: {ch['visual_style']}. Default character: {ch['character']['name']} (a stick figure, always on the left, x≈500, y≈930, scale 1.05).{cast_txt}\n\n"
            f"CAPABILITIES (JSON):\n{json.dumps(keep, ensure_ascii=False)}\n\nEXAMPLES OF VALID SCENES (illustration of the format only; do not copy their content):\n{json.dumps(ex['scenes'], ensure_ascii=False)}\n\n"
            f"SCENES TO DESIGN (id [section] title: spoken text):\n{sc}\n\n"
            "RULES\n- Return one entry per scene with the same id.\n- Every action cue, face cue and `appear` phrase must be an exact consecutive word run copied from THAT scene's spoken text "
            "(so graphics appear when the words are spoken); alternatively use seconds.\n- Put graphics on the right half (x 1000-1800, y 250-800); text size >= 40; keep each scene's items readable (max 4 items).\n"
            "- Use a chart when the text compares or counts numbers, pills for lists of 3, a bill/notice for a payment, a prop for an object. Vary layouts; do not repeat the same layout in a row.\n"
            "- Pills get a marker: leave it as the default numbers (1-2-3) or 'dot'; use 'coin' ONLY for a list about money.\n"
            "- A weekly menu or any table/list with named cells is a `grid` item (cells {label, text, appear}; ONE cell per item the text counts - 'bảy ngày' = 7 cells Thứ Hai..Chủ nhật, cols 1 for more than 4 cells; each text <= 16 characters; cells fill one by one on their cue, empty cells stay blank); never a chart with equal bars. A shopping list is a grid too (cols 1, one ingredient per cell). Write the real contents the text names.\n"
            "- NO emoji anywhere (the font cannot draw them). Do not claim absolutes such as '0 đồng' that the spoken text does not say.\n"
            "- To show someone writing: action `write` plus holds [{who, side:'R', prop:'pen'}] (and a notebook held in the other hand when an asset exists); to show shopping: action `carry` plus holds [{who, side:'L', prop:'basket'}]; phone: hold_phone. `who` is 'main' or 'cast1'. "
            "If the text describes an action the actions list cannot show (e.g. opening a fridge door), choose the closest action AND list the gap in the scene's `action_gaps` (one short sentence each) instead of silently replacing it.\n"
            "- When the spoken text describes a place or a physical activity, design the scene to SHOW it (character pose/action, props, hand-held props), not only graphics; the asset planner will draw the place and the objects, so describe them in the scene title (e.g. 'Minh studies at a desk').\n"
            "- Choose a first pose and an action that match the meaning (cheer for good news, cheek for worry, shrug for doubt, point/point_seq when pointing at graphics, nod to agree). "
            "The first scene should start with action 'enter'.\n- Do not use ai:<id> assets unless they are listed as usable. Use camera presets sparingly.\nTASK: storyboard")


def template_storyboard(proj, brief, ch, script, tg):
    d = int(brief.get("duration_seconds") or 0)
    return {"project": Path(proj).name, "title": script["title"], "version": 1, "status": "bản nháp do AI soạn - chờ duyệt", "audience": brief.get("audience") or ch["audience"],
            "message": brief.get("message", ""), "voice": {"provider": "edge", "voice_id": ch["voice"]["voice_id"], "speed": float(ch["voice"]["speed"])},
            "timing": {"lead": 0.15, "tail": 0.3, "word_pad": 0.15}, "export": {"fade_out": 0.4}, "character": {"shirt": ch["character"]["shirt"]},
            "targets": {k: v for k, v in tg.items() if k in ("duration", "scenes", "scenes_source", "note")},
            "review_points": ["Mạch kể và thứ tự các cảnh.", "Lời đọc từng cảnh (đây là văn bản sẽ gửi API giọng đọc).", "Thông tin cần kiểm chứng (nếu có).", "Hình ảnh, hành động từng cảnh."],
            "scenes": []}


def merge_scenes(script, visuals, main_char=None, known=()):
    vs = {v["id"]: v for v in visuals}
    scenes = []
    for i, s in enumerate(script["scenes"]):
        v = json.loads(json.dumps(vs.get(s["id"]) or {}))
        for it in v.get("items", []):                                       # the video font draws no emoji
            for k, x in list(it.items()):
                if isinstance(x, str):
                    it[k] = sbload.strip_emoji(x)
                elif isinstance(x, list):
                    it[k] = [sbload.strip_emoji(y) if isinstance(y, str) else ({kk: (sbload.strip_emoji(vv) if isinstance(vv, str) and kk in ("text", "label") else vv) for kk, vv in y.items()} if isinstance(y, dict) else y) for y in x]
        sc = {"id": s["id"], "title": s["title"], "voice": s["voice"], "subtitles": "auto", "bg": v.get("bg") or "cream",
              "transition": "fade-out" if i == len(script["scenes"]) - 1 else "cut",
              "bi": dict(v.get("bi") or {"x": 500, "y": 930, "scale": 1.05, "face": "neutral", "pose": "idle"}),
              "actions": v.get("actions", []), "face_cues": v.get("face_cues", []), "items": v.get("items", [])}
        if main_char and (sc["bi"].get("char") not in known):
            sc["bi"]["char"] = main_char                                    # the AI designer forgot / invented an id: the main character acts
        if sc["bi"].get("char") in (None, "", CHR.BUILTIN):
            sc["bi"].pop("char", None)
        cast = [dict(c) for c in v.get("cast", []) if c.get("char") in known][:3]
        if cast:
            sc["cast"] = cast
        for k in ("camera", "hold_after", "holds", "action_gaps", "shots"):
            if v.get(k):
                sc[k] = v[k]
        scenes.append(sc)
    return scenes


validate_obj = sbstore.validate_obj


def error_scene(e):
    m = re.match(r"^(s\d+\w*):", e)
    return m.group(1) if m else None


def _ai_fix(proj, sb, problems, what):
    """One cheap AI call that corrects the scenes named in `problems` (validator errors or layout warnings); merges the visual fields back."""
    bad = sorted({error_scene(e) for e in problems if error_scene(e)})
    sub = {"type": "object", "required": ["scenes"], "properties": {"scenes": visual_schema()["properties"]["scenes"]}}
    cat = capabilities.capabilities(proj)
    prompt = (f"Fix these storyboard scenes: {what}. Keep the idea; change only what the problems require (for overlaps move/resize items so nothing is half on top of "
              "another; graphics belong in the right half x 1000-1800 and must not touch the character on the left). Return the corrected scenes (same ids)."+"\n\nPROBLEMS:\n" +
              "\n".join(problems[:20]) + "\n\nSCENES (voice text is fixed):\n" +
              json.dumps([{k: v for k, v in sc.items() if k not in ("subtitles", "transition")} for sc in sb["scenes"] if sc["id"] in bad], ensure_ascii=False) +
              f"\n\nALLOWED: actions {[a['name'] for a in cat['actions']]}; faces {cat['faces']}; poses {cat['poses']}; props {cat['props']}; text colours {cat['text_colors']}; "
              f"accent colours {cat['accent_colors']}; backgrounds cream|blue|#RRGGBB.\nTASK: storyboard_repair")
    out = llm.call(proj, "storyboard_repair", "cheap", prompt, sub, runner=RUNNER)["data"]["scenes"]
    by = {v["id"]: v for v in out}
    for sc in sb["scenes"]:
        if sc["id"] in by:
            v = by[sc["id"]]
            for k in ("bg", "bi", "actions", "face_cues", "items", "camera", "hold_after", "shots"):
                if k in v:
                    sc[k] = v[k]


def repair_storyboard(proj, sb, brief, ch):
    """1) deterministic cue repair (no AI); 2) up to 2 AI rounds on validator errors; 3) ONE AI pass for layout overlaps (kept only if it stays valid).
    -> (errors, warnings)."""
    errs, warns = validate_obj(proj, sb)
    if errs:
        bad = {error_scene(e) for e in errs if error_scene(e)}
        for sc in sb["scenes"]:
            if sc["id"] in bad:
                new, _ = realign.realign(sc, sc["voice"])
                sc.update(new)
        errs, warns = validate_obj(proj, sb)
    for _ in range(2):
        if not errs:
            break
        _ai_fix(proj, sb, errs, "they fail validation")
        errs, warns = validate_obj(proj, sb)
    lay = [w for w in warns if ": layout:" in w]
    if not errs and lay:
        import layout as _lay
        ai = _lay.ai_sizes(proj)
        for sc in sb["scenes"]:
            _lay.compose(sc, ai)                                                 # content in its own panel, characters at the edges (reusable layout)
            _lay.nudge(sc, ai)                                                   # then props to free spots: deterministic, no AI call
        if True:
            errs, warns = validate_obj(proj, sb)
            lay = [w for w in warns if ": layout:" in w]
    if not errs and lay:
        keep = json.loads(json.dumps(sb))
        _ai_fix(proj, sb, lay, "they have overlapping or off-canvas items")
        e2, w2 = validate_obj(proj, sb)
        if e2 or len([w for w in w2 if ": layout:" in w]) > len(lay):             # the pass made things worse: keep the earlier version
            sb.clear()
            sb.update(keep)
        else:
            errs, warns = e2, w2
    return errs, warns


def do_storyboard(proj, force=False):
    brief = brief_of(proj)
    ch = channel_of(brief)
    tg = targets_of(brief, ch)
    script = jget(pdir(proj) / "script.json")
    if not script:
        raise PrepareError("no script yet: run the script step first")
    inputs = sha([script, CH.fingerprint(ch), characters_plan(proj)])                       # targets only label the storyboard; they never justify rewriting it
    if fresh(proj, "storyboard", inputs) and not force:
        return "skipped"
    sbf = Path(proj) / "storyboard.json"
    old = jget(sbf, {}) or {}
    meta = jget(pdir(proj) / "storyboard_meta.json", {}) or {}
    if old.get("scenes") and not force and ((Path(proj) / "approval.json").exists() or meta.get("scenes_sha") != sha(old["scenes"])):
        raise PrepareError("the storyboard was edited or approved after the AI wrote it; replacing it needs an explicit 'force' (the current version is kept in versions/)")
    with step_run(proj, "storyboard", inputs):
        out = llm.call(proj, "storyboard", "quality", storyboard_prompt(proj, brief, ch, script), visual_schema(), runner=RUNNER)
        sb = template_storyboard(proj, brief, ch, script, tg)
        cp = characters_plan(proj)
        sb["scenes"] = merge_scenes(script, out["data"]["scenes"], main_character(proj), {c["id"] for c in cp.get("characters", [])})
        errs, warns = repair_storyboard(proj, sb, brief, ch)
        if errs:
            G.write_json_atomic(pdir(proj) / "storyboard_rejected.json", {"errors": errs, "storyboard": sb})
            raise PrepareError("the AI storyboard still has validation errors after the allowed repairs (kept in prepare/storyboard_rejected.json): " + "; ".join(errs[:4]))
        if old.get("scenes"):
            (Path(proj) / "versions").mkdir(exist_ok=True)
            (Path(proj) / "versions" / f"storyboard_v{old.get('version', 0)}_before_ai_{time.strftime('%Y%m%d_%H%M%S')}.json").write_text(json.dumps(old, ensure_ascii=False, indent=2), encoding="utf-8")
            sb["version"] = int(old.get("version", 0)) + 1
        sb["origin"] = "ai"
        sbf.write_text(json.dumps(sb, ensure_ascii=False, indent=2), encoding="utf-8")
        G.write_json_atomic(pdir(proj) / "storyboard_meta.json", {"scenes_sha": sha(sb["scenes"]), "warnings": warns, "model": out["meta"].get("model_actual") or out["meta"].get("model"), "created": time.strftime("%Y-%m-%d %H:%M:%S")})
    return "ok"


# ------------------------------------------------------------------------------------------------------------------ asset plan
PLAN_SCHEMA = {"type": "object", "required": ["assets"], "properties": {"assets": {"type": "array", "maxItems": 6, "items": {
    "type": "object", "required": ["id", "kind", "prompt", "scene", "mode"], "properties": {
        "id": {"type": "string"}, "kind": {"type": "string", "enum": ["prop", "background"]}, "prompt": {"type": "string"}, "rationale": {"type": "string"},
        "scene": {"type": "string"}, "scenes": {"type": "array", "items": {"type": "string"}}, "who": {"type": "string"}, "side": {"type": "string", "enum": ["L", "R"]}, "mode": {"type": "string", "enum": ["item", "bg", "hold"]}, "x": {"type": "number"}, "y": {"type": "number"}, "scale": {"type": "number"},
        "appear": {"type": ["string", "number"]},
        "reuse_project": {"type": "string"}, "reuse_asset": {"type": "string"}}}}}}


def library_candidates(proj):
    """Approved AI assets a project may reuse instead of paying for a new image - decided by the brief's asset_policy:
    new -> none (every picture is made for this project) | series -> only the series project | library -> only the listed ones | legacy -> any approved asset."""
    brief = brief_of(proj)
    pol = brief.get("asset_policy", "legacy")
    if pol == "new":
        return []
    wanted = None
    if pol == "library":
        wanted = {tuple(x.split("/", 1)) for x in brief.get("library_assets", []) if "/" in str(x)}
    out = []
    for d in sorted((P2 / "projects").iterdir()):
        if not d.is_dir() or not (d / "ai_assets" / "manifest.json").exists():
            continue
        if pol == "series" and d.name != brief.get("series_from"):
            continue
        for aid, e in G.load_manifest(d)["assets"].items():
            if wanted is not None and (d.name, aid) not in wanted:
                continue
            if aid.endswith(("_parts", "_faces")):
                continue                                                   # character sheets travel with their character, not as props
            if G.approval_state(d, aid)[0] == "approved":
                out.append({"project": d.name, "asset": aid, "kind": e.get("kind"), "prompt": e.get("prompt"), "own": d.resolve() == Path(proj).resolve()})
    return out


def do_assetplan(proj, force=False):
    brief = brief_of(proj)
    ch = channel_of(brief)
    sb = jget(Path(proj) / "storyboard.json", {}) or {}
    if not sb.get("scenes"):
        raise PrepareError("no storyboard yet: run the storyboard step first")
    lib = library_candidates(proj)
    lim = budget.limits(proj).get("images")
    remaining = None if lim is None else max(0, int(lim) - budget.usage(proj)["images"])
    scr = jget(pdir(proj) / "script.json", {}) or {}
    inputs = sha([[(s["id"], s["voice"]) for s in scr.get("scenes", [])], CH.fingerprint(ch)])        # the AI script, not later hand edits
    if fresh(proj, "assetplan", inputs) and not force:
        return "skipped"
    if (pdir(proj) / "plan_approval.json").exists() and not force:
        raise PrepareError("the asset plan was already approved; planning again needs an explicit 'force' (the previous plan is kept in prepare/history/)")
    cap = ASSET_CAP if remaining is None else min(ASSET_CAP, remaining)
    with step_run(proj, "assetplan", inputs):
        plan_assets = []
        if cap > 0:
            sc = "\n".join(f"{s['id']} {s['title']}: {s['voice']} | now: bg={s['bg']}, items={[i.get('img') or i.get('type') for i in s['items']]}" for s in sb["scenes"])
            reuse_txt = ("Approved assets that can be REUSED for free (set reuse_project and reuse_asset instead of making a new one): " + json.dumps(lib, ensure_ascii=False)
                         if lib else "No earlier asset may be reused in this project: every asset you propose is NEW (the tool draws it for this story).")
            prompt = (f"Plan AI-generated image assets (flat 2D illustration; the tool adds the style rules) for this video. Visual style: {ch['visual_style']}.\n"
                      f"Library props already available (no cost): {capabilities.capabilities(proj)['props']}.\n"
                      f"{reuse_txt}\n\nSCENES:\n{sc}\n\n"
                      f"First read each scene's spoken text and note WHERE it happens (room, desk, street...) and WHAT the character does or handles (studying, holding a phone, writing...). "
                      f"Then propose at most {cap} assets that make those places and actions visible: a background for every distinct place the text names (a scene in a named place must not stay on an empty plain background), "
                      "and props for the objects that are handled or needed to show the action (books, desk lamp, notebook...) that the library does not have. Do not spend assets on abstract scenes (lists, numbers). "
                      "Each: id (a-z, 0-9, _), kind prop|background, prompt (English, describe ONLY the subject; props are one object on white; backgrounds are a calm 16:9 scene without people; never plan characters/people here, they are designed separately), "
                      "scene (id) + scenes (EVERY scene id that uses it: one background is shared by all the scenes in the same place, so it is drawn once; keep the places few and consistent) + mode item|bg|hold (hold = the character holds it: also who main|cast1.. and side L|R; use it for a notebook the character writes in), placement (x,y,scale for items: right half x 1000-1800, y 300-800, scale about 1; appear = a phrase from that scene's text or seconds), "
                      "rationale (one sentence). Backgrounds leave free space at the sides/bottom for characters and props. Where the story needs a before/after state of one object (a messy and a tidy fridge) plan two props. If nothing is needed return an empty list.\nTASK: asset_plan")
            plan_assets = llm.call(proj, "asset_plan", "cheap", prompt, PLAN_SCHEMA, runner=RUNNER)["data"]["assets"][:cap]
        ids, clean = set(), []
        scenes = {s["id"]: s for s in sb["scenes"]}
        for a in plan_assets:
            if not ID_RE.match(a["id"]) or a["id"] in ids or a["scene"] not in scenes:
                continue
            ids.add(a["id"])
            ap = a.get("appear", 0.3)
            if isinstance(ap, str) and not realign.has_phrase(scenes[a["scene"]]["voice"], ap):
                ap = 0.3
            used = [a["scene"]] + [x for x in a.get("scenes", []) if x in scenes and x != a["scene"]]
            entry = {"id": a["id"], "kind": a["kind"], "prompt": a["prompt"].strip(), "rationale": a.get("rationale", ""), "scenes": used,
                     "placement": {"scene": a["scene"], "mode": a["mode"], "x": a.get("x", 1400), "y": a.get("y", 560), "scale": a.get("scale", 1.0), "appear": ap,
                                   **({"who": a.get("who", "main"), "side": a.get("side", "L")} if a["mode"] == "hold" else {})},
                     "refs": [], "reuse": None}                                # no picture of another project/sample is ever a reference
            if a.get("reuse_project") and a.get("reuse_asset") and any(c["project"] == a["reuse_project"] and c["asset"] == a["reuse_asset"] for c in lib):
                entry["reuse"] = {"project": a["reuse_project"], "asset": a["reuse_asset"]}
            clean.append(entry)
        old_plan = pdir(proj) / "asset_plan.json"
        if old_plan.exists():
            hd = pdir(proj) / "history"
            hd.mkdir(exist_ok=True)
            shutil_copy(old_plan, hd / f"asset_plan_{time.strftime('%Y%m%d_%H%M%S')}.json")
        G.write_json_atomic(pdir(proj) / "asset_plan.json", {"assets": clean, "created": time.strftime("%Y-%m-%d %H:%M:%S"), "images_remaining_at_planning": remaining})
        (pdir(proj) / "plan_approval.json").unlink(missing_ok=True)       # a new plan needs a new approval
    return "ok"


def shutil_copy(a, b):
    import shutil
    shutil.copy(a, b)


def plan_characters(proj):
    """The AI characters the storyboard uses (what the plan asks the owner to approve): id, name, role, description, outfit."""
    sb = jget(Path(proj) / "storyboard.json", {}) or {}
    out = []
    for cid in [c for c in CHR.used_ids(sb) if c != CHR.BUILTIN]:
        pf = CHR.get_profile(proj, cid) or {}
        out.append({k: pf.get(k) for k in ("id", "name", "role", "description", "outfit")})
    return out


def plan_hash(proj):
    p = jget(pdir(proj) / "asset_plan.json")
    return sha([p["assets"], plan_characters(proj)]) if p else None


def approve_plan(proj, by, note=""):
    h = plan_hash(proj)
    if not h:
        raise PrepareError("there is no asset plan to approve")
    rec = {"by": by, "note": note, "plan_hash": h, "at": time.strftime("%Y-%m-%d %H:%M:%S")}
    G.write_json_atomic(pdir(proj) / "plan_approval.json", rec)
    with (Path(proj) / "approvals_history.jsonl").open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({"at": rec["at"], "kind": "asset_plan", "by": by, "note": note, "plan_hash": h}, ensure_ascii=False) + "\n")
    return rec


def plan_approved(proj):
    a = jget(pdir(proj) / "plan_approval.json")
    return bool(a and a.get("plan_hash") == plan_hash(proj))


def update_plan_asset(proj, aid, **fields):
    """Owner edits one planned asset (prompt / placement) -> the plan hash changes, so its approval is withdrawn."""
    f = pdir(proj) / "asset_plan.json"
    p = jget(f)
    hit = [a for a in p["assets"] if a["id"] == aid]
    if not hit:
        raise PrepareError(f"unknown planned asset {aid}")
    for k in ("prompt", "kind", "rationale"):
        if k in fields and fields[k] is not None:
            hit[0][k] = str(fields[k])
    if fields.get("placement"):
        hit[0]["placement"].update(fields["placement"])
    if fields.get("reuse") == "none":                                      # owner prefers a NEW image over reusing an earlier approved one
        hit[0]["reuse"] = None
    G.write_json_atomic(f, p)
    return hit[0]


def remove_plan_asset(proj, aid):
    f = pdir(proj) / "asset_plan.json"
    p = jget(f)
    p["assets"] = [a for a in p["assets"] if a["id"] != aid]
    G.write_json_atomic(f, p)


def copy_reused(proj, entry):
    src = P2 / "projects" / entry["reuse"]["project"]
    e = G.load_manifest(src)["assets"][entry["reuse"]["asset"]]
    import shutil
    dst = Path(proj) / "ai_assets"
    (dst / "source").mkdir(parents=True, exist_ok=True)
    shutil.copy(src / e["file"], dst / f"{entry['id']}.png")
    new = {k: e.get(k) for k in ("kind", "prompt", "display", "transparent", "transparency_check", "png_size", "sha256", "agent_model", "image_model", "image_model_note")}
    new.update({"id": entry["id"], "status": "draft", "file": f"ai_assets/{entry['id']}.png", "signature": f"reused:{entry['reuse']['project']}:{entry['reuse']['asset']}:{e.get('sha256', '')[:10]}",
                "reused_from": entry["reuse"], "approved_by": None, "created": time.strftime("%Y-%m-%d %H:%M:%S"), "attempts": []})
    G.put_asset(proj, entry["id"], new)


def do_assets(proj, force=False, wait=True, poll=2.0, max_wait=1800):
    """Run the approved plan: reuse copies, submit new image jobs through the shared job manager (limits + one-at-a-time slot apply)."""
    import agy_jobs as J
    plan = jget(pdir(proj) / "asset_plan.json")
    if not plan:
        raise PrepareError("no asset plan: run the plan step first")
    if not plan_approved(proj):
        _set(proj, "assets", state="waiting", error=None)
        raise PrepareError("the asset plan has not been approved (or was changed after approval); approve it first - no image is generated before that")
    with step_run(proj, "assets", plan_hash(proj)):
        jobs = {}
        for a in plan["assets"]:
            cur = G.load_manifest(proj)["assets"].get(a["id"])
            if a.get("reuse"):
                if not cur:
                    copy_reused(proj, a)
                continue
            if cur and cur.get("status") in ("draft", "approved") and cur.get("prompt") == a["prompt"]:
                continue                                                  # already produced for this plan entry: nothing is called again
            j = J.submit(Path(proj).name, {"asset_id": a["id"], "kind": a["kind"], "prompt": a["prompt"], "reference_images": a.get("refs", [])}, **({"runner": IMAGE_RUNNER} if IMAGE_RUNNER else {}))
            jobs[a["id"]] = j["job_id"]
        end = time.time() + max_wait
        failed = []
        while wait and jobs:
            for aid, jid in list(jobs.items()):
                st = J.check(Path(proj).name, jid)
                if st["state"] in ("succeeded",):
                    jobs.pop(aid)
                elif st["state"] in ("failed", "timeout", "interrupted", "superseded", "invalid"):
                    jobs.pop(aid)
                    failed.append(f"{aid}: {st['state']} {st.get('error') or ''}".strip())
            if jobs and time.time() > end:
                failed += [f"{aid}: still running after {max_wait}s" for aid in jobs]
                break
            if jobs:
                time.sleep(poll)
        if failed:
            raise PrepareError("asset step incomplete: " + "; ".join(failed))
        if wait:
            generate_characters(proj, poll=poll, max_wait=max_wait)
    return "ok"


def _free_spot(proj, sc, item):
    """Try the item's own position first, then a grid in the right-hand zone; keep the first spot that adds no layout warning. -> True/None."""
    import layout
    ai = {aid: (e["png_size"][0] / 2, e["png_size"][1] / 2) for aid, e in G.load_manifest(proj)["assets"].items() if e.get("png_size")}
    base = len(layout.check_scene(sc, ai))
    others = len(layout.check_scene({**sc, "items": [i for i in sc["items"] if i is not item]}, ai))
    if base <= others:
        return True
    ox, oy = item["x"], item["y"]
    spots = [(x, y) for y in (450, 600, 350, 700, 550, 650) for x in (1450, 1250, 1650, 1100, 1750)]
    for x, y in spots:
        item["x"], item["y"] = x, y
        if len(layout.check_scene(sc, ai)) <= others:
            return True
    item["x"], item["y"] = ox, oy
    return None


def apply_assets(proj):
    """Insert the APPROVED planned assets into their scenes (data only). Returns the list of applied asset ids; saves a new storyboard version."""
    plan = jget(pdir(proj) / "asset_plan.json")
    if not plan:
        raise PrepareError("no asset plan")
    stf = pdir(proj) / "asset_state.json"
    st = jget(stf, {"applied": []})
    sbf = Path(proj) / "storyboard.json"
    sb = json.loads(sbf.read_text(encoding="utf-8"))
    applied, notes = [], []
    for a in plan["assets"]:
        if a["id"] in st["applied"] or G.approval_state(proj, a["id"])[0] != "approved":
            continue
        p = a["placement"]
        targets = [s for s in sb["scenes"] if s["id"] in (a.get("scenes") or [p["scene"]])]
        for sc in targets:
            if p["mode"] == "bg":
                sc["bg"] = f"ai:{a['id']}"
            elif p["mode"] == "hold":
                png = (G.load_manifest(proj)["assets"].get(a["id"]) or {}).get("png_size") or [400, 400]
                hold = {"who": p.get("who", "main"), "side": p.get("side", "L"), "prop": f"ai:{a['id']}", "scale": round(min(1.0, 170 / (png[0] / 2)), 3)}
                if not any(h["prop"] == hold["prop"] for h in sc.setdefault("holds", [])):
                    sc["holds"].append(hold)
            else:
                ap = p.get("appear", 0.3)
                if sc["id"] != p["scene"] and isinstance(ap, str):
                    ap = 0.3                                               # the cue phrase belongs to the first scene only
                item = {"type": "prop", "img": f"ai:{a['id']}", "x": p["x"], "y": p["y"], "scale": p["scale"], "appear": ap}
                sc.setdefault("items", []).append(item)
                moved = _free_spot(proj, sc, item)                           # keep the planned spot unless it lands half on top of something
                if moved is None:
                    notes.append(f"{sc['id']}: {a['id']} could not be placed without overlapping something; move it in the storyboard form")
        if not targets:
            continue
        applied.append(a["id"])
    if applied:
        errs, _ = validate_obj(proj, sb)
        if errs:
            raise PrepareError("applying the assets would make the storyboard invalid: " + "; ".join(errs[:3]))
        (Path(proj) / "versions").mkdir(exist_ok=True)
        old = sbf.read_text(encoding="utf-8")
        (Path(proj) / "versions" / f"storyboard_v{sb.get('version', 0)}_before_assets_{time.strftime('%Y%m%d_%H%M%S')}.json").write_text(old, encoding="utf-8")
        sb["version"] = int(sb.get("version", 0)) + 1
        sbf.write_text(json.dumps(sb, ensure_ascii=False, indent=2), encoding="utf-8")
        st["applied"] += applied
        st["notes"] = notes
        G.write_json_atomic(stf, st)
    return applied


# ------------------------------------------------------------------------------------------------------------------ overview for the UI / CLI
def overview(proj):
    st = status(proj)
    steps = {}
    for n in STEPS + OPTIONAL:
        c = dict(st["steps"].get(n) or {})
        c["state"] = effective_state(c) if c else "pending"
        steps[n] = c
    return {"steps": steps, "plan_approved": plan_approved(proj), "plan_hash": plan_hash(proj), "updated": st.get("updated")}


def do_opportunity(proj, force=False):
    """Topic opportunity research for the brief's theme: measured YouTube evidence kept apart from the AI's judgement (opportunity.py)."""
    import opportunity
    brief = brief_of(proj)
    ch = channel_of(brief)
    import topics
    inputs = sha([brief.get("title"), brief.get("story_guideline"), CH.fingerprint(ch), topics.titles(brief.get("channel") or "default")])
    if fresh(proj, "opportunity", inputs) and not force:
        return "skipped"
    with step_run(proj, "opportunity", inputs):
        res = opportunity.run(proj, brief, ch, runner=RUNNER, fetcher=FETCHER_RAW)
        G.write_json_atomic(pdir(proj) / "opportunities.json", res)
    return "ok"


def do_chargen(proj, force=False):
    """Make (or rebuild) the sheets + rig of the characters the storyboard uses. Same gate as `assets`: the owner approved the plan that lists them."""
    if not plan_approved(proj):
        raise PrepareError("the asset plan (which lists the characters to draw) has not been approved; approve it first - no image is generated before that")
    with step_run(proj, "chargen", plan_hash(proj)):
        generate_characters(proj)
    return "ok"


RUNNERS = {"opportunity": do_opportunity, "chargen": do_chargen, "research": do_research, "script": do_script, "characters": do_characters, "storyboard": do_storyboard, "assetplan": do_assetplan, "assets": do_assets}


def run_steps(proj, names, force=()):
    results = {}
    for n in names:
        try:
            results[n] = RUNNERS[n](proj, force=n in force)
        except (PrepareError, llm.LLMError, budget.BudgetError, CH.ChannelError) as e:
            results[n] = f"failed: {e}"
            break
    return results


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("project")
    ap.add_argument("--step", default="all", choices=STEPS + OPTIONAL + ["all", "apply_assets"])
    ap.add_argument("--force", action="append", default=[])
    a = ap.parse_args()
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    proj = Path(a.project).resolve()
    if a.step == "apply_assets":
        print("applied:", apply_assets(proj))
        return 0
    names = PLAN_STEPS if a.step == "all" else [a.step]
    res = run_steps(proj, names, a.force)
    for k, v in res.items():
        print(f"{k}: {v}")
    return 1 if any(str(v).startswith("failed") for v in res.values()) else 0


if __name__ == "__main__":
    sys.exit(main())
