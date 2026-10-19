"""Project characters made by AI (cut-out rig from two Antigravity sheets; see char_rig.py) - profile, prompts, generation, approval, installation.

  PROJECT/characters/<cid>/profile.json   who the character is (name, role, description, outfit, references)
  PROJECT/characters/<cid>/rig.json       the measured rig (written by char_rig.build_rig) + the sha256 of the two sheets it was made from
  PROJECT/characters/<cid>/png/           part images (installed into PROJECT/assets/png at build time)
  PROJECT/ai_assets/<cid>_parts.png, <cid>_faces.png   the sheets: ordinary AI assets (job, manifest, hash, approve/reject in the same UI page)

A character is `approved` only when BOTH sheets are approved (hash-bound, see agy_image.approval_state) AND the rig on disk was built from exactly those
approved sheet hashes; otherwise it is `draft` / `stale` and scenes refuse it. `bi` is the built-in hand-drawn character and needs nothing."""
import json
import shutil
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import agy_image as G  # noqa: E402
import char_rig  # noqa: E402

BUILTIN = "bi"
ID_RE = __import__("re").compile(r"^[a-z0-9_]{1,24}$")


class CharacterError(RuntimeError):
    pass


def cdir(proj, cid):
    return Path(proj) / "characters" / cid


def profile_path(proj, cid):
    return cdir(proj, cid) / "profile.json"


def list_ids(proj):
    d = Path(proj) / "characters"
    return sorted(p.name for p in d.iterdir() if (p / "profile.json").exists()) if d.exists() else []


def save_profile(proj, cid, profile):
    if not ID_RE.match(str(cid)) or cid == BUILTIN:
        raise CharacterError("character id: a-z, 0-9, _ (max 24), not 'bi'")
    p = {"id": cid, "name": str(profile.get("name") or cid).strip(), "role": profile.get("role") if profile.get("role") in ("main", "support") else "support",
         "description": str(profile.get("description") or "").strip(), "outfit": str(profile.get("outfit") or "").strip(),
         "personality": str(profile.get("personality") or "").strip(), "refs": [str(x) for x in (profile.get("refs") or [])][:3], "updated": time.strftime("%Y-%m-%d %H:%M:%S")}
    if len(p["description"]) < 15:
        raise CharacterError("describe the character (appearance, clothes, colours) in at least a sentence")
    G.write_json_atomic(profile_path(proj, cid), p)
    return p


def get_profile(proj, cid):
    return G.read_json(profile_path(proj, cid))


def sheet_ids(cid):
    return f"{cid}_parts", f"{cid}_faces"


def subject(profile):
    """The character's look as ONE sentence block, identical in both sheet prompts so the two pictures show the same person."""
    bits = [profile["description"].rstrip(".")]
    if profile.get("outfit"):
        bits.append("outfit: " + profile["outfit"].rstrip("."))
    bits.append("friendly rounded cartoon proportions, simple flat shapes, same character in every piece")
    return "; ".join(bits)


def sheet_requests(proj, cid):
    """The two image requests (parts first; the faces sheet uses the parts sheet as a reference so hair, skin and colours match)."""
    prof = get_profile(proj, cid)
    if not prof:
        raise CharacterError(f"unknown character {cid}")
    pid, fid = sheet_ids(cid)
    refs = sorted(str(f) for f in (Path(proj) / "style_ref").glob("*.png"))          # only pictures the owner put into THIS project; never another project's or a sample's
    parts = {"asset_id": pid, "kind": "parts_sheet", "prompt": subject(prof), "display_width": 1600, "reference_images": refs}
    faces = {"asset_id": fid, "kind": "faces_sheet", "prompt": subject(prof), "display_width": 1600, "reference_images": refs}
    return parts, faces


def sheets_hashes(proj, cid):
    man = G.load_manifest(proj)["assets"]
    out = {}
    for nm, aid in zip(("parts", "faces"), sheet_ids(cid)):
        e = man.get(aid)
        out[nm] = e.get("sha256") if e and e.get("file") and G.file_problem(proj, e) is None else None
    return out


def build(proj, cid):
    """Slice the two sheets (current files) into the rig. Raises CharRigError with the reason. Records the sheet hashes the rig came from."""
    h = sheets_hashes(proj, cid)
    if not all(h.values()):
        raise CharacterError(f"both sheets must exist first ({sheet_ids(cid)})")
    pid, fid = sheet_ids(cid)
    d = cdir(proj, cid)
    if (d / "png").exists():
        shutil.rmtree(d / "png")
    rig = char_rig.build_rig(Path(proj) / "ai_assets" / f"{pid}.png", Path(proj) / "ai_assets" / f"{fid}.png", d, cid)
    rig["sources"] = h
    rig["built"] = time.strftime("%Y-%m-%d %H:%M:%S")
    (d / "rig.json").write_text(json.dumps(rig, ensure_ascii=False, indent=2), encoding="utf-8")
    return rig


def state(proj, cid):
    """-> (status, why). status: builtin | missing | draft | stale | approved."""
    if cid == BUILTIN:
        return "builtin", ""
    if not get_profile(proj, cid):
        return "missing", "no such character"
    rig = G.read_json(cdir(proj, cid) / "rig.json")
    h = sheets_hashes(proj, cid)
    if not rig:
        return "draft", "sheets not sliced into a rig yet"
    if rig.get("sources") != h:
        return "stale", "a sheet changed after the rig was built; rebuild the rig"
    st = [G.approval_state(proj, aid)[0] for aid in sheet_ids(cid)]
    if st != ["approved", "approved"]:
        return "draft", f"sheets {dict(zip(('parts', 'faces'), st))}: the owner must approve both pictures"
    return "approved", ""


def load_rig(proj, cid):
    if cid == BUILTIN:
        return None
    r = G.read_json(cdir(proj, cid) / "rig.json")
    if not r:
        raise CharacterError(f"character {cid} has no rig")
    return r


def rig_images(rig):
    """File stems of every image the rig needs."""
    names = [rig["shadow"]["img"], rig["leg"]["img"], rig["torso"]["img"], rig["armUpper"]["img"], rig["armLower"]["img"]]
    names += [rig["face"]["pattern"].replace("{k}", k) for k in rig["kinds"]]
    if rig.get("head"):
        names.append(rig["head"]["img"])
    return names


def install(proj, cid, assets_png):
    """Copy the rig's part images into the project's assets/png (the builder reads them from there)."""
    rig = load_rig(proj, cid)
    if rig is None:
        return None
    assets_png = Path(assets_png)
    assets_png.mkdir(parents=True, exist_ok=True)
    for n in rig_images(rig):
        src = cdir(proj, cid) / "png" / f"{n}.png"
        if not src.exists():
            raise CharacterError(f"rig image {n}.png is missing; rebuild the character")
        dst = assets_png / f"{n}.png"
        if not dst.exists() or dst.read_bytes() != src.read_bytes():
            shutil.copy(src, dst)
    return rig


def retire_unused(proj, keep):
    """Character folders of earlier plans (ids no longer in the plan) are moved to versions/retired_characters/, so they cannot be drawn or used by accident."""
    import shutil
    root = Path(proj) / "characters"
    for d in list(root.iterdir()) if root.exists() else []:
        if d.is_dir() and d.name not in keep and d.name != BUILTIN:
            dst = Path(proj) / "versions" / "retired_characters"
            dst.mkdir(parents=True, exist_ok=True)
            shutil.move(str(d), str(dst / f"{d.name}_{time.strftime('%Y%m%d_%H%M%S')}"))


def used_ids(sb):
    ids = {sc.get("bi", {}).get("char") or BUILTIN for sc in sb.get("scenes", [])}
    for sc in sb.get("scenes", []):
        ids |= {c.get("char") or BUILTIN for c in sc.get("cast", [])}
    return sorted(ids)


def rigs_for(proj, sb):
    """{char id: rig} for every AI character the storyboard uses (Bi is built in and absent)."""
    out = {}
    for cid in used_ids(sb):
        if cid != BUILTIN:
            out[cid] = load_rig(proj, cid)
    return out


def register_sheet(proj, aid, kind, src_png, prompt="imported by the owner"):
    """Register a picture the owner (or a test) already has as an AI asset in `draft` state: same manifest, hash, approval rules as a generated one."""
    proj = Path(proj)
    out = proj / "ai_assets"
    out.mkdir(parents=True, exist_ok=True)
    dst = out / f"{aid}.png"
    shutil.copy(src_png, dst)
    from PIL import Image
    with Image.open(dst) as im:
        size = list(im.size)
    G.put_asset(proj, aid, {"id": aid, "kind": kind, "status": "draft", "prompt": prompt, "file": f"ai_assets/{aid}.png", "png_size": size, "sha256": G.sha_file(dst),
                            "signature": f"imported:{G.sha_file(dst)[:10]}", "source": "imported", "created": time.strftime("%Y-%m-%d %H:%M:%S"), "approved_by": None,
                            "transparent": True, "agent_model": None, "image_model": None, "image_model_note": "imported file", "attempts": []})
