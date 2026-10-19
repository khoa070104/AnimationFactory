"""Build the video of a project with the REMOTION renderer (phase2/remotion). Same inputs, gates and report as build_video.py (Craft):
  python build_remotion.py PROJECT [--draft] [--force]
Gates: approved characters (or --draft), the real up-to-date voice (or --draft stub), every AI asset used is approved. Output: PROJECT/output/<name>_v<N>_<preview|draft>.mp4,
PROJECT/remotion/ (public/ = the editable scene data + assets, out/ = per-scene clips), logs/build_report.json, status.json last_build."""
import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import acceptance  # noqa: E402
import check_motion as CM  # noqa: E402
import export_remotion as X  # noqa: E402
import sbload  # noqa: E402
import toolpaths  # noqa: E402

P2 = Path(__file__).resolve().parent.parent
ENGINE = P2 / "remotion"


def node(*args, **kw):
    env = {**os.environ, "NODE_NO_WARNINGS": "1"}
    return subprocess.run(["node", *map(str, args)], capture_output=True, text=True, encoding="utf-8", env=env, **kw)


def build(proj, draft=False, force=False, placeholders=None, scene_ids=None, log=print):
    proj = Path(proj)
    t_start = time.time()
    sb = sbload.load_storyboard(proj)
    work = proj / "remotion"
    log("export scene data")
    data = X.export(proj, work, scene_ids, draft, placeholders)
    log(f"render (incremental) {data['total']:.1f} s, voice {data['voice']}")
    r = node(ENGINE / "render_clip.mjs", work, *(["--force"] if force else []))
    if r.returncode:
        raise X.ExportError("render failed: " + (r.stdout + r.stderr)[-600:])
    rlog = json.loads((work / "out" / "render_log.json").read_text(encoding="utf-8"))
    q = node(ENGINE / "qa.mjs", work)
    if q.returncode:
        raise X.ExportError("QA sampling failed: " + (q.stdout + q.stderr)[-600:])
    qa = json.loads(q.stdout)
    out = proj / "output" / f"{sb['project']}_v{sb['version']}_{'draft' if draft else 'preview'}.mp4"
    out.parent.mkdir(exist_ok=True)
    shutil.copy(work / "out" / "clip.mp4", out)
    report = []

    def check(name, ok, info=""):
        report.append({"name": name, "pass": bool(ok), "info": str(info)})
        log(("PASS " if ok else "FAIL ") + name + (f" - {info}" if info else ""))

    pj = json.loads(subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(out)], capture_output=True, text=True).stdout)
    vs = [s for s in pj["streams"] if s["codec_type"] == "video"]
    secs = float(pj["format"]["duration"])
    check("video 1920x1080 with audio", vs and (vs[0]["width"], vs[0]["height"]) == (1920, 1080) and any(s["codec_type"] == "audio" for s in pj["streams"]))
    tg = sbload.targets(sb)
    n_all = len(sb["scenes"])
    acceptance.lock(proj, tg, "first build")
    crit = acceptance.problems(proj, tg)
    locked = acceptance.load(proj)
    check("pass/fail criteria were fixed before the build (not loosened since)", not crit, crit[0] if crit else f"locked {locked['criteria']}")
    whole = not scene_ids or len(scene_ids) == n_all
    if whole:
        check(f"duration within {tg['duration'][0]}-{tg['duration'][1]} s", tg["duration"][0] <= secs <= tg["duration"][1], f"{secs:.1f}s")
        check(f"scene count within {tg['scenes'][0]}-{tg['scenes'][1]}", tg["scenes"][0] <= len(data["scenes"]) <= tg["scenes"][1], f"{len(data['scenes'])} scenes")
    sub_ok, sub_info = True, ""
    for s in data["scenes"]:
        prev = 0
        for x in s["subs"]:
            if x["t0"] < prev - 0.001 or x["t1"] > s["dur"] + 0.001 or len(x["text"]) > 56:
                sub_ok, sub_info = False, f"{s['id']}: {x}"
            prev = x["t1"]
    check("subtitles: inside scene, in order, no overlap, <= 56 chars", sub_ok, sub_info)
    tol = (locked or {}).get("criteria", {}).get("cue_tolerance", acceptance.DEFAULT_CUE_TOLERANCE)
    late = [f"{c['who']} {c['action']} planned {c['planned']:.2f}s starts {c['actual']:.2f}s" for c in qa["cues"] if c["actual"] - c["planned"] > tol + 1e-6]
    check(f"actions start within {tol:g} s of their spoken cue (planned vs actual start, after non-overlap scheduling)", not late, "; ".join(late[:6]) if late else f"{len(qa['cues'])} actions")
    bad = []
    for who, rec in qa["rows"].items():
        rig = data["rigs"].get(rec["rig"])
        bad += [f"{who}: {name} ({info})" for name, ok, info in CM.row_checks(rec["rows"], rig) if not ok]
    check("motion QA on all characters (joint limits, no snaps/flips, arms never through torso)", not bad, "; ".join(bad[:6]))
    stf = proj / "status.json"
    st = json.loads(stf.read_text(encoding="utf-8")) if stf.exists() else {"project": proj.name}
    st["state"] = "draft_built" if draft else "preview_built"
    st["last_build"] = {"renderer": "remotion", "draft": bool(draft), "output": str(out), "seconds": round(secs, 1), "rendered": rlog["rendered"], "reused": rlog["reused"],
                        "built_in_s": round(time.time() - t_start, 1), "placeholders": data["placeholders"]}
    stf.write_text(json.dumps(st, ensure_ascii=False, indent=2), encoding="utf-8")
    (proj / "logs").mkdir(exist_ok=True)
    (proj / "logs" / "build_report.json").write_text(json.dumps({"checks": report, "renderer": "remotion"}, ensure_ascii=False, indent=2), encoding="utf-8")
    log(f"DONE {out} {secs:.1f}s | rendered {rlog['rendered'] or '-'} | reused {rlog['reused'] or '-'}")
    return all(c["pass"] for c in report)


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    ap = argparse.ArgumentParser()
    ap.add_argument("project")
    ap.add_argument("--draft", action="store_true")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--scenes", default="")
    ap.add_argument("--placeholder", action="append", default=[])
    a = ap.parse_args()
    ph = {}
    for r in a.placeholder:
        cid, rest = r.split("=")
        rig, pj = rest.split("@")
        ph[cid] = {"rig": rig, "project": pj}
    try:
        ok = build(Path(a.project).resolve(), a.draft, a.force, ph, a.scenes.split(",") if a.scenes else None, log=lambda m: print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True))
    except X.ExportError as e:
        sys.exit(f"REFUSED: {e}")
    sys.exit(0 if ok else 1)
