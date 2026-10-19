"""Chapter 1 demo builder: creates (or refreshes) a demo project from an example storyboard in phase2/examples through the CONTROL LAYER only
(project_new -> project_get -> project_put(autolayout) -> validate -> preview). Budget is zero: no image, no voice, no LLM call can happen.
  python ops/chang1_demos.py story|explain
Characters and pictures come from the series project (sample_a_thuc_don_tuan) with their approvals (asset_policy: series)."""
import json
import shutil
import sys
from pathlib import Path

P2 = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(P2 / "tools"))
import af_core as AF  # noqa: E402
import agy_image as G  # noqa: E402
import characters as CHR  # noqa: E402
import prepare as PR  # noqa: E402

SERIES = "sample_a_thuc_don_tuan"
DEMOS = {"story": ("story_label.json", ["bg_kitchen", "prop_shopping_bag"]), "explain": ("explain_process.json", [])}


def build(kind, before=False):
    """before=True: the SAME input without shots/until (what the old pipeline did): one fixed wide frame for the whole scene."""
    fn, assets = DEMOS[kind]
    sb = json.loads((P2 / "examples" / fn).read_text(encoding="utf-8"))
    if before:
        sb["project"] += "_before"
        for sc in sb["scenes"]:
            sc.pop("shots", None)
            for it in sc.get("items", []):
                it.pop("until", None)
    name = sb["project"]
    if not (P2 / "projects" / name).exists():
        r = AF.call("project_new", {"name": name, "title": sb["title"], "brief": {"title": sb["title"], "asset_policy": "series", "series_from": SERIES, "character_mode": "ai", "research": "no",
                                                                                   "budget": {"images": 0, "llm_calls": 0, "voice_credits": 0}}})
        assert r["status"] == "ok", r
        proj = P2 / "projects" / name
        PR._copy_series(proj, {"series_from": SERIES})                        # characters with their sheets and approvals (same versions)
        src = P2 / "projects" / SERIES
        for aid in assets:
            e = G.load_manifest(src)["assets"][aid]
            (proj / "ai_assets").mkdir(exist_ok=True)
            shutil.copy(src / e["file"], proj / "ai_assets" / f"{aid}.png")
            G.put_asset(proj, aid, {**e, "reused_from": {"project": SERIES, "asset": aid}})
    cur = AF.call("project_get", {"project": name})
    sb.pop("_about", None)
    put = AF.call("project_put", {"project": name, "storyboard": sb, "expect_hash": cur["hash"], "autolayout": True})
    if put["status"] != "ok":
        return put
    return AF.call("preview", {"project": name})


if __name__ == "__main__":
    res = build(sys.argv[1], before="--before" in sys.argv)
    print(json.dumps({k: v for k, v in res.items() if k != "checks"}, ensure_ascii=False, indent=1)[:3500])
    for c in res.get("checks", []):
        print("PASS" if c["pass"] else "FAIL", c["name"][:90], "-", c["info"][:100])
