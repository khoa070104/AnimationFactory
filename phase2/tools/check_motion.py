"""Automatic motion QA for the Bi v2 demo.
 1. samples every frame's joint values from the saved project (valueAtTime);
 2. forward kinematics -> elbow/hand positions per frame;
 3. checks: joint limits, per-frame angular speed (no flips/snaps), elbows/hands never inside the torso body,
    held prop parented to the hand;
 4. pixel verification on a debug build (coloured markers on joints): FK prediction vs rendered marker, and rigidity of the
    held phone relative to the hand (distance and angle stay constant while it moves).
Usage: python check_motion.py   (builds the debug project itself). Exit code 1 if any check fails."""
import json
import math
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
import p2_svg as S
import build_motion_demo as B

P2 = S.P2
EC = B.EC
OUT = P2 / "motion"
FPS = S.TOK["canvas"]["fps"]
results = []


def check(name, ok, info=""):
    results.append((name, bool(ok), info))
    print(("PASS " if ok else "FAIL ") + name + (" - " + info if info else ""), flush=True)


def rot(v, deg):  # clockwise-positive rotation in y-down screen coordinates
    a = math.radians(deg)
    return (v[0] * math.cos(a) - v[1] * math.sin(a), v[0] * math.sin(a) + v[1] * math.cos(a))


BI = {"waistY": -186, "shoulder": {"x": 80, "y": -168}, "L1": 85, "L2": 85, "torso_half": 66, "torso_top": -376}


def geometry(rig=None):
    """Joint geometry used by fk / the torso check: Bi's numbers, or the measured numbers of an AI rig."""
    if not rig:
        return BI
    th = rig["parts"]["torso"][1] * rig["scale"]
    tw = rig["parts"]["torso"][0] * rig["scale"]
    return {"waistY": rig["waistY"], "shoulder": rig["shoulder"], "L1": rig["L1"], "L2": rig["L2"], "torso_half": 0.7 * rig["shoulder"]["x"], "torso_top": rig["waistY"] - 0.92 * th}


def fk(row, rig=None):
    """row: dict of joint values -> positions in comp px (root scale 1)."""
    g = geometry(rig)
    rx, ry = row["rootx"], row["rooty"]
    W = (rx, ry + g["waistY"])
    out = {}
    for side, sx, sh, el in (("L", -g["shoulder"]["x"], row["shL"], row["elL"]), ("R", g["shoulder"]["x"], row["shR"], row["elR"])):
        off = rot((sx, g["shoulder"]["y"]), row["waist"])
        Sx = (W[0] + off[0], W[1] + off[1])
        a1 = row["waist"] + sh
        d1 = rot((0, g["L1"]), a1)
        E = (Sx[0] + d1[0], Sx[1] + d1[1])
        a2 = a1 + el
        d2 = rot((0, g["L2"]), a2)
        H = (E[0] + d2[0], E[1] + d2[1])
        out["sh" + side], out["elbow" + side], out["hand" + side], out["armangle" + side] = Sx, E, H, a2
    return out


def sample(proj):
    jsx = Path(tempfile.mkdtemp()) / "sample.jsx"
    P = {"comp": "MotionDemo", "fps": FPS}
    jsx.write_text("var P = " + json.dumps(P) + ";\n" + (P2 / "lib/sample_motion.jsx").read_text(encoding="utf-8"), encoding="utf-8")
    r = subprocess.run([EC, "--project", str(proj), "script", str(jsx)], capture_output=True, text=True, encoding="utf-8")
    if r.returncode:
        sys.exit(r.stdout[-800:] + r.stderr[-800:])
    rows, parent = [], None
    for line in r.stdout.splitlines():
        if line.startswith("HELDPARENT"):
            parent = line.split(" ", 1)[1].strip()
        elif line.startswith("S "):
            v = line.split()[1:]
            rows.append({"f": int(v[0]), "t": float(v[1]), "rootx": float(v[2]), "rooty": float(v[3]), "shL": float(v[4]), "elL": float(v[5]),
                         "shR": float(v[6]), "elR": float(v[7]), "neck": float(v[8]), "waist": float(v[9]), "hipL": float(v[10]),
                         "hipR": float(v[11]), "held": float(v[12])})
    return rows, parent


def markers(img):
    a = np.asarray(img.convert("RGB")).astype(int)
    targets = {"handR": (255, 0, 255), "handL": (0, 255, 255), "elbowR": (0, 255, 0), "elbowL": (0, 0, 255)}
    res = {}
    for k, c in targets.items():
        m = (abs(a[:, :, 0] - c[0]) < 40) & (abs(a[:, :, 1] - c[1]) < 40) & (abs(a[:, :, 2] - c[2]) < 40)
        ys, xs = np.nonzero(m)
        res[k] = (xs.mean(), ys.mean(), len(xs)) if len(xs) >= 20 else None
    # phone body colour #2B2F3A = (43, 47, 58), the only pixels with this colour in the scene
    m = (abs(a[:, :, 0] - 43) < 6) & (abs(a[:, :, 1] - 47) < 6) & (abs(a[:, :, 2] - 58) < 6)
    ys, xs = np.nonzero(m)
    res["phone"] = (xs.mean(), ys.mean(), len(xs)) if len(xs) >= 300 else None
    return res


def row_checks(rows, rig=None):
    """Pure checks on sampled joint values (unit-testable with synthetic rows). Returns [(name, ok, info)]."""
    out = []
    lim = {"elR": (-175, 175), "elL": (-175, 175), "shL": (-200, 200), "shR": (-200, 200), "neck": (-25, 25), "waist": (-15, 15)}
    bad = [(k, round(min(r[k] for r in rows), 1), round(max(r[k] for r in rows), 1)) for k, (lo, hi) in lim.items()
           if min(r[k] for r in rows) < lo or max(r[k] for r in rows) > hi]
    out.append(("joint limits respected (elbow flexion <= 175 deg, no pass through the folded pose)", not bad,
                str(bad) if bad else "ranges: " + ", ".join(f"{k} {min(r[k] for r in rows):.0f}..{max(r[k] for r in rows):.0f}" for k in ("elR", "elL", "shR", "shL"))))
    worst = (0, "", 0)
    for k in ("shL", "elL", "shR", "elR", "neck", "waist", "hipL", "hipR"):
        for a, b in zip(rows, rows[1:]):
            d = abs(b[k] - a[k])
            if d > worst[0]:
                worst = (d, k, b["t"])
    out.append(("no joint snap/flip (max change per frame <= 30 deg)", worst[0] <= 30, f"max {worst[0]:.1f} deg/frame at {worst[1]} t={worst[2]:.2f}s"))
    flips = sum(1 for k in ("elR", "elL") for a, b in zip(rows, rows[1:]) if (a[k] > 20 and b[k] < -20) or (a[k] < -20 and b[k] > 20))
    out.append(("elbow never flips bend direction between frames", flips == 0, f"{flips} flips"))
    # torso block: Bi: x +-66, y -376..-190 relative to the root; an AI rig: measured from its torso
    g = geometry(rig)
    inside = []
    for r in rows:
        p = fk(r, rig)
        for key in ("elbowL", "elbowR", "handL", "handR"):
            x, y = p[key][0] - r["rootx"], p[key][1] - r["rooty"]
            if abs(x) < g["torso_half"] and g["torso_top"] < y < g["waistY"] + 0.04 * abs(g["waistY"]):
                inside.append((round(r["t"], 2), key, round(x), round(y)))
    out.append(("elbows/hands never pass through the torso", not inside, f"{len(inside)} frames inside, first: {inside[:3]}" if inside else ""))
    return out


def main():
    subprocess.run([sys.executable, str(P2 / "tools/build_motion_demo.py"), "--debug"], check=True, capture_output=True)
    proj = OUT / "motion_demo_debug.ecproj"
    rows, parent = sample(proj)
    check("frames sampled", len(rows) > 600, f"{len(rows)} frames")
    check("held phone is parented to hand_R", parent == "hand_R", f"parent={parent}")

    # --- joint limits (continuous angles, degrees) ---
    for name, ok, info in row_checks(rows):
        check(name, ok, info)

    # --- pixel verification on debug render ---
    times = [0.5, 1.2, 3.4, 5.0, 8.4, 10.6, 12.6, 12.9, 13.2, 13.5, 13.8, 14.1, 14.4, 14.7, 17.8, 19.4, 20.6, 21.3, 22.0, 22.6, 23.4]
    tmp = Path(tempfile.mkdtemp())
    err, phone_vecs, tested = [], [], 0
    for t in times:
        f = tmp / f"{t}.png"
        subprocess.run([EC, "--project", str(proj), "render-frame", "--comp", "MotionDemo", "--time", str(t), "--out", str(f)], check=True, capture_output=True)
        mk = markers(Image.open(f))
        row = min(rows, key=lambda r: abs(r["t"] - t))
        p = fk(row)
        for key in ("handL", "handR", "elbowL", "elbowR"):
            if mk[key] is None:
                continue   # marker hidden behind the head/arm in this frame
            tested += 1
            e = math.hypot(mk[key][0] - p[key][0], mk[key][1] - p[key][1])
            err.append((round(e, 2), key, t))
        if row["held"] > 50 and mk["phone"] and mk["handR"]:
            vx, vy = mk["phone"][0] - mk["handR"][0], mk["phone"][1] - mk["handR"][1]
            phone_vecs.append((t, math.hypot(vx, vy), math.degrees(math.atan2(vy, vx)) - p["armangleR"]))
    worst_e = max(err) if err else (999, "", 0)
    check("FK matches rendered joint markers (<= 4 px, marker centroid tolerance)", tested >= 20 and worst_e[0] <= 4, f"{tested} markers, worst {worst_e[0]} px ({worst_e[1]} t={worst_e[2]})")
    if len(phone_vecs) >= 3:
        lens = [v[1] for v in phone_vecs]
        angs = [((v[2] + 180) % 360) - 180 for v in phone_vecs]
        # angle relative to the forearm must stay constant: compare after wrapping around the mean
        m = sum(angs) / len(angs)
        dev = max(abs(((a - m + 180) % 360) - 180) for a in angs)
        check("held phone rigid on the hand (distance and angle constant)", max(lens) - min(lens) <= 4 and dev <= 4,
              f"{len(phone_vecs)} frames, distance {min(lens):.1f}..{max(lens):.1f}px, angle deviation {dev:.1f} deg")
    else:
        check("held phone rigid on the hand", False, f"only {len(phone_vecs)} usable frames")
    (OUT / "motion_report.json").write_text(json.dumps({"checks": [{"name": n, "pass": ok, "info": i} for n, ok, i in results]}, ensure_ascii=False, indent=2), encoding="utf-8")
    sys.exit(0 if all(ok for _, ok, _ in results) else 1)


if __name__ == "__main__":
    main()
