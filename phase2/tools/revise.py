"""Fix things from the owner's feedback with AI, but only after the owner has SEEN what would change.

  p = revise.propose_scene(proj, "s03", "rút ngắn lời, mặt vui hơn")     -> proposal (nothing is changed yet): before / after / diff / validation
  p = revise.propose_asset(proj, "plant", "lá xanh hơn, tròn hơn")        -> proposal for a better image prompt (nothing is generated yet)
  revise.apply(proj, p["id"])                                              -> scene: saved as a new storyboard version (voice approval is withdrawn
                                                                              automatically if the text changed); asset: the plan prompt is updated and ONE
                                                                              regeneration job is submitted (counts against the image limit)
  revise.reject(proj, p["id"])
A proposal is stale (refused) if the scene/asset changed after it was proposed. Voice changes are realigned (cues/subtitles) and the whole
storyboard is validated before a proposal is even shown; an invalid result is reported, not offered."""
import json
import secrets
import time
from pathlib import Path

import agy_image as G
import capabilities
import channel as CH
import llm
import prepare as PR
import realign
import sbstore

RUNNER = None


class ReviseError(RuntimeError):
    pass


def _pdir(proj):
    d = PR.pdir(proj) / "proposals"
    d.mkdir(exist_ok=True)
    return d


def _save(proj, p):
    G.write_json_atomic(_pdir(proj) / f"{p['id']}.json", p)


def get(proj, pid):
    p = G.read_json(_pdir(proj) / f"{pid}.json")
    if not p:
        raise ReviseError(f"unknown proposal {pid}")
    return p


def list_all(proj):
    out = [G.read_json(f) for f in sorted(_pdir(proj).glob("*.json"))]
    return sorted([p for p in out if p], key=lambda p: p["created"], reverse=True)


def _scene(sb, sid):
    sc = next((s for s in sb["scenes"] if s["id"] == sid), None)
    if sc is None:
        raise ReviseError(f"unknown scene {sid}")
    return sc


SCENE_SCHEMA = {"type": "object", "required": ["scene", "summary"], "properties": {"scene": capabilities.scene_schema(), "summary": {"type": "string"}}}


def propose_scene(proj, scene_id, instruction):
    proj = Path(proj)
    instruction = str(instruction).strip()
    if len(instruction) < 3:
        raise ReviseError("describe what to change")
    sb = json.loads((proj / "storyboard.json").read_text(encoding="utf-8"))
    sc = _scene(sb, scene_id)
    brief = PR.brief_of(proj)
    ch = PR.channel_of(brief)
    cat = capabilities.capabilities(proj)
    keep = {k: cat[k] for k in ("actions", "poses", "faces", "props", "ai_assets", "backgrounds", "text_colors", "accent_colors", "item_types", "appear_note")}
    prompt = (f"You revise ONE scene of a 2D explainer video according to the owner's feedback. Channel tone: {ch['tone']}. Avoid: {'; '.join(ch.get('avoid', []))}.\n"
              "Change only what the instruction asks; keep everything else identical (id, title, items, layout). You may change the spoken text (`voice`) only if the instruction asks for it; "
              "if you do, keep it spoken-style Vietnamese with numbers written in words. Cue phrases / `appear` phrases must be word runs that occur in the spoken text; use only options from CAPABILITIES.\n\n"
              f"CAPABILITIES: {json.dumps(keep, ensure_ascii=False)}\n\nCURRENT SCENE JSON:\n{json.dumps(sc, ensure_ascii=False)}\n\nINSTRUCTION: {instruction}\n\n"
              "Return the full revised scene and a one-line summary (Vietnamese) of what you changed.\nTASK: revise_scene")
    out = llm.call(proj, "revise_scene", "quality", prompt, SCENE_SCHEMA, runner=RUNNER)
    new = out["data"]["scene"]
    new["id"] = sc["id"]
    if new.get("voice") != sc["voice"]:                                   # text changed: repair cues/subtitles deterministically
        new, changes = realign.realign(new, " ".join(str(new["voice"]).split()))
        new["subtitles"] = "auto"
    else:
        new["subtitles"], changes = sc.get("subtitles", "auto"), []
    for k in ("transition", "camera", "hold_after", "rest", "holds"):
        if k not in new and k in sc:
            new[k] = sc[k]
    cand = json.loads(json.dumps(sb))
    cand["scenes"] = [new if s["id"] == scene_id else s for s in cand["scenes"]]
    errs, warns = sbstore.validate_obj(proj, cand)
    p = {"id": secrets.token_hex(4), "type": "scene", "target": scene_id, "instruction": instruction, "status": "pending", "created": time.strftime("%Y-%m-%d %H:%M:%S"),
         "base_hash": PR.sha(sc), "before": sc, "after": new, "diff": sbstore.scene_diff(sc, new), "realigned": changes, "summary": out["data"].get("summary", ""),
         "voice_changed": new["voice"] != sc["voice"], "errors": errs, "warnings": warns, "model": out["meta"].get("model_actual") or out["meta"].get("model")}
    _save(proj, p)
    return p


def _unwrap(text):
    """Some models answer with the whole JSON object inside the string field; take the real prompt out of it."""
    t = str(text).strip()
    if t.startswith("{"):
        try:
            inner = json.loads(t)
            if isinstance(inner, dict) and isinstance(inner.get("prompt"), str):
                return inner["prompt"].strip()
        except ValueError:
            pass
    return t


def _prompt_problems(new, old):
    low = new.lower().strip()
    probs = []
    if len(low) < 15 or len(low.split()) < 3:
        probs.append("prompt too short to describe a picture")
    if any(w in low for w in ("feedback", "improve", "the prompt", "instruction", "rewrite")):
        probs.append("prompt talks about prompts/feedback instead of describing the picture")
    if low == old.lower().strip():
        probs.append("prompt is identical to the current one")
    return probs


ASSET_SCHEMA = {"type": "object", "required": ["prompt", "explanation"], "properties": {"prompt": {"type": "string"}, "explanation": {"type": "string"}}}


def propose_asset(proj, asset_id, feedback):
    proj = Path(proj)
    e = G.load_manifest(proj)["assets"].get(asset_id)
    plan = G.read_json(PR.pdir(proj) / "asset_plan.json") or {"assets": []}
    pe = next((a for a in plan["assets"] if a["id"] == asset_id), None)
    cur = (pe or {}).get("prompt") or (e or {}).get("prompt")
    if not cur:
        raise ReviseError(f"unknown asset {asset_id}")
    if not str(feedback).strip():
        raise ReviseError("describe what is wrong with the image")
    prompt = ("Improve the prompt of an AI image (flat 2D vector illustration for an explainer video; the tool adds the style rules, white background for props, 16:9 for backgrounds). "
              f"Current subject prompt: {cur!r}\nOwner's feedback on the generated image: {feedback}\nWrite the new subject prompt in English (subject only, one concrete object or scene, no style words) "
              "and a one-line explanation in Vietnamese of what you changed. Example: current 'a gold coin', feedback 'shinier' -> prompt 'a large gold coin with bright shiny highlights'. "
              "The prompt itself must describe the picture (a noun phrase), never talk about prompts, feedback or instructions.\nTASK: asset_prompt")
    out = llm.call(proj, "asset_prompt", "cheap", prompt, ASSET_SCHEMA, runner=RUNNER, validate=lambda d: _prompt_problems(_unwrap(d.get("prompt", "")), cur))
    out["data"]["prompt"] = _unwrap(out["data"]["prompt"])
    p = {"id": secrets.token_hex(4), "type": "asset", "target": asset_id, "instruction": str(feedback).strip(), "status": "pending", "created": time.strftime("%Y-%m-%d %H:%M:%S"),
         "base_hash": PR.sha([cur, (e or {}).get("sha256")]), "before": {"prompt": cur}, "after": {"prompt": out["data"]["prompt"].strip()},
         "diff": [{"path": "prompt", "before": cur, "after": out["data"]["prompt"].strip()}], "summary": out["data"]["explanation"], "errors": [], "warnings": [],
         "model": out["meta"].get("model_actual") or out["meta"].get("model")}
    _save(proj, p)
    return p


def apply(proj, pid):
    proj = Path(proj)
    p = get(proj, pid)
    if p["status"] != "pending":
        raise ReviseError(f"proposal is already {p['status']}")
    if p["errors"]:
        raise ReviseError("this proposal does not pass validation and cannot be applied: " + "; ".join(p["errors"][:3]))
    if p["type"] == "scene":
        sb = json.loads((proj / "storyboard.json").read_text(encoding="utf-8"))
        cur = _scene(sb, p["target"])
        if PR.sha(cur) != p["base_hash"]:
            raise ReviseError("the scene changed after this proposal was made; ask for a new proposal")
        sb["scenes"] = [p["after"] if s["id"] == p["target"] else s for s in sb["scenes"]]
        try:
            res = sbstore.save(proj, sb, f"ai_{p['target']}")
        except sbstore.SaveError as e:
            raise ReviseError(str(e) + ": " + "; ".join(e.errors[:3])) from e
        p.update(status="applied", applied_at=time.strftime("%Y-%m-%d %H:%M:%S"), result={"version": res["version"]})
    else:
        import agy_jobs as J
        e = G.load_manifest(proj)["assets"].get(p["target"])
        if PR.sha([p["before"]["prompt"], (e or {}).get("sha256")]) != p["base_hash"]:
            raise ReviseError("the asset changed after this proposal was made; ask for a new proposal")
        plan = G.read_json(PR.pdir(proj) / "asset_plan.json")
        pe = next((a for a in (plan or {"assets": []})["assets"] if a["id"] == p["target"]), None)
        kind = (pe or e or {}).get("kind")
        refs = (pe or {}).get("refs", [])
        if pe:
            was_approved = PR.plan_approved(proj)
            PR.update_plan_asset(proj, p["target"], prompt=p["after"]["prompt"])
            if was_approved:                                                  # the owner pressed "apply" on a visible diff: that is the approval of the changed plan
                PR.approve_plan(proj, "chủ dự án (áp dụng đề xuất AI đã xem)", f"proposal {p['id']}")
        job = J.submit(Path(proj).name, {"asset_id": p["target"], "kind": kind, "prompt": p["after"]["prompt"], "reference_images": refs, "regenerate": True},
                       **({"runner": PR.IMAGE_RUNNER} if PR.IMAGE_RUNNER else {}))
        p.update(status="applied", applied_at=time.strftime("%Y-%m-%d %H:%M:%S"), result={"job_id": job["job_id"], "state": job["state"]})
    _save(proj, p)
    return p


def reject(proj, pid):
    p = get(proj, pid)
    if p["status"] == "pending":
        p["status"] = "rejected"
        _save(proj, p)
    return p
