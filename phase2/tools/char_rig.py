"""AI character -> cut-out rig. Two pictures made by Antigravity (see agy_image KINDS parts_sheet / faces_sheet) become a rig that the SAME EffectCraft
builder animates as the hand-drawn Bi (lib/bi_rig.jsx reads the rig as data):

  parts sheet  : 4 separate pieces left -> right: torso, upper arm, lower arm + hand, leg (+ shoe)
  faces sheet  : 5 complete heads left -> right: happy, neutral, worried, surprised, thinking

  build_rig(parts_png, faces_png, out_dir, char_id, height=540) -> rig dict (also written to out_dir/rig.json, part PNGs to out_dir/png/)

The slicing is by connected components of the picture's alpha (the sheets are made on white, white is removed by agy_image), so the pieces must not touch;
a wrong count / wrong proportions raises CharRigError with a plain reason (the pipeline then regenerates the sheet - bounded). Joint positions are measured
from the pieces (shoulder end of the arm, hip end of the leg, collar of the torso), lengths come from the pieces, nothing from Bi except the pose library's
angles; hand targets of the shared poses are mapped through rig["handK"].
Needs numpy + Pillow; uses OpenCV (cv2) for labelling when available, else a slower pure-numpy labelling."""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

PS = 2                                    # PNGs are written at 2x their display size (same convention as the Bi parts)
KINDS = ["happy", "neutral", "worried", "surprised", "thinking"]
PART_NAMES = ["torso", "arm_upper", "arm_lower", "leg"]


class CharRigError(ValueError):
    pass


def _label(mask):
    try:
        import cv2
        n, lab, stats, _ = cv2.connectedComponentsWithStats(mask.astype(np.uint8), connectivity=8)
        return n - 1, lab, [tuple(int(v) for v in stats[i]) for i in range(1, n)]
    except ImportError:                                           # slow fallback on a 1/4 size mask
        from collections import deque
        small = mask[::4, ::4]
        h, w = small.shape
        lab = np.zeros((h, w), dtype=np.int32)
        n = 0
        for y in range(h):
            for x in range(w):
                if small[y, x] and not lab[y, x]:
                    n += 1
                    dq = deque([(y, x)])
                    lab[y, x] = n
                    while dq:
                        cy, cx = dq.popleft()
                        for dy in (-1, 0, 1):
                            for dx in (-1, 0, 1):
                                ny, nx = cy + dy, cx + dx
                                if 0 <= ny < h and 0 <= nx < w and small[ny, nx] and not lab[ny, nx]:
                                    lab[ny, nx] = n
                                    dq.append((ny, nx))
        full = np.kron(lab, np.ones((4, 4), dtype=np.int32))[:mask.shape[0], :mask.shape[1]]
        full = np.where(mask, full, 0)
        stats = []
        for i in range(1, n + 1):
            ys, xs = np.nonzero(full == i)
            stats.append((int(xs.min()), int(ys.min()), int(xs.max() - xs.min() + 1), int(ys.max() - ys.min() + 1), int(len(xs))))
        return n, full, stats


def split_row(sheet, expected, what):
    """-> list of `expected` RGBA crops (tight bbox, only the pixels of their own component group), sorted left to right."""
    im = Image.open(sheet).convert("RGBA")
    a = np.asarray(im)[:, :, 3]
    n, lab, stats = _label(a > 40)
    if n == 0:
        raise CharRigError(f"{what}: the sheet is empty")
    areas = [s[4] for s in stats]
    big_thr = max(areas) * 0.04
    big = [i for i in range(n) if areas[i] >= big_thr]
    groups = {i: [i] for i in big}
    gap = im.width * 0.03
    for i in range(n):                                            # small pieces (fingers, hair tips) join the nearest big piece if close, else are dropped
        if i in groups:
            continue
        x, y, w, h, _ = stats[i]
        best, bd = None, 1e9
        for j in big:
            X, Y, W, H, _ = stats[j]
            dx = max(X - (x + w), x - (X + W), 0)
            dy = max(Y - (y + h), y - (Y + H), 0)
            d = (dx * dx + dy * dy) ** 0.5
            if d < bd:
                best, bd = j, d
        if best is not None and bd <= gap:
            groups[best].append(i)
    if len(groups) != expected:
        raise CharRigError(f"{what}: found {len(groups)} separate pieces, expected {expected} (pieces must not touch and nothing else may be drawn)")
    order = sorted(groups, key=lambda i: stats[i][0] + stats[i][2] / 2)
    arr = np.asarray(im).copy()
    out = []
    for i in order:
        keep = np.isin(lab, [k + 1 for k in groups[i]])
        piece = arr.copy()
        piece[:, :, 3] = np.where(keep, piece[:, :, 3], 0)
        pim = Image.fromarray(piece, "RGBA")
        bb = pim.getchannel("A").getbbox()
        out.append(pim.crop(bb))
    return out


def _row_width(piece, y0, y1):
    a = np.asarray(piece.getchannel("A")) > 40
    cols = np.nonzero(a[int(y0):max(int(y1), int(y0) + 1)].any(axis=0))[0]
    return (int(cols.min()), int(cols.max())) if len(cols) else (0, piece.width - 1)


def build_rig(parts_png, faces_png, out_dir, char_id, height=540, prefix=None):
    out_dir = Path(out_dir)
    prefix = prefix or f"ch_{char_id}_"
    torso, upper, lower, leg = split_row(parts_png, 4, "parts sheet")
    heads = split_row(faces_png, 5, "faces sheet")
    problems = []
    for nm, p in (("upper arm", upper), ("lower arm", lower), ("leg", leg)):
        if p.height / p.width < 1.7:
            problems.append(f"{nm} is not a long upright piece (height/width {p.height / p.width:.2f}; expected >= 1.7)")
    if torso.height / torso.width < 0.7 or torso.height / torso.width > 2.2:
        problems.append(f"torso proportions look wrong (height/width {torso.height / torso.width:.2f})")
    hs = [h.height / h.width for h in heads]
    if max(hs) / min(hs) > 1.25:
        problems.append("the five heads differ too much in shape/size - they must be the same head with different expressions")
    if problems:
        raise CharRigError("; ".join(problems))
    # common head canvas, bottom-centre aligned (the neck stub sits at the bottom)
    cw, ch = max(h.width for h in heads), max(h.height for h in heads)
    canvases = []
    for h in heads:
        c = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
        c.paste(h, ((cw - h.width) // 2, ch - h.height), h)
        canvases.append(c)
    gw, gh = leg.width, leg.height
    tw, th = torso.width, torso.height
    uw, uh = upper.width, upper.height
    lw, lh = lower.width, lower.height
    # overall scale: leg below the hip + torso + head = `height` (1x px)
    unscaled = 0.86 * gh + 0.92 * th + 0.94 * ch
    s = height / unscaled
    sc = lambda v: v * s
    lo_w0, lo_w1 = _row_width(lower, 0, lh * 0.12)               # width of the elbow end
    up_w0, up_w1 = _row_width(upper, 0, uh * 0.12)
    lw_top = lo_w1 - lo_w0 + 1
    uw_top = up_w1 - up_w0 + 1
    rig = {
        "id": char_id, "kinds": KINDS, "handK": 0, "height": height, "scale": round(s, 5),
        "shadow": None, "leg": None, "torso": None, "armUpper": None, "armLower": None, "head": None, "face": None,
    }

    # AI sheets often draw arms far longer than a body can use: scale both arm pieces (uniformly, so hands keep their shape) until the reach is
    # ~1.15x the shoulder-to-waist distance (Bi: 1.0x), never below 0.4x
    reach0 = (uh - uw_top) + (0.9 * lh - lw_top / 2)
    arm_k = min(1.0, max(0.4, 1.15 * (0.92 - 0.17) * th / reach0))
    rig["armScale"] = round(arm_k, 4)

    def save(piece, name, k=1.0):
        """Resize `piece` so that its display size is the original size x s x k, written at 2x pixels; returns (display_w, display_h)."""
        dw, dh = sc(piece.width) * k, sc(piece.height) * k
        r = piece.resize((max(1, round(dw * PS)), max(1, round(dh * PS))), Image.LANCZOS)
        (out_dir / "png").mkdir(parents=True, exist_ok=True)
        r.save(out_dir / "png" / f"{prefix}{name}.png", "PNG")
        return dw, dh

    save(torso, "torso")
    save(upper, "arm_upper", arm_k)
    save(lower, "arm_lower", arm_k)
    save(leg, "leg")
    for k, c in zip(KINDS, canvases):
        save(c, f"face_{k}")
    # shadow: soft ellipse under the feet, width follows the body
    sw = max(tw, 2 * gw) * s * 1.15
    sh = sw * 0.16
    sh_img = Image.new("RGBA", (round(sw * PS), round(sh * PS)), (0, 0, 0, 0))
    ImageDraw.Draw(sh_img).ellipse((0, 0, sh_img.width - 1, sh_img.height - 1), fill=(29, 29, 31, 46))
    sh_img = sh_img.filter(ImageFilter.GaussianBlur(PS * 2))
    sh_img.save(out_dir / "png" / f"{prefix}shadow.png", "PNG")
    # joints (1x px, root = feet, y up negative)
    leg_len = 0.86 * gh * s
    hip_y = -leg_len
    hip_x = max(0.22 * tw, 0.55 * gw) * s
    top = -0.92 * th * s                                            # top of the torso, relative to the waist
    shoulder_x = 0.43 * tw * s
    shoulder_y = top + 0.17 * th * s
    L1 = max(10.0, (uh - uw_top) * s * arm_k)
    L2 = max(10.0, (0.9 * lh - lw_top / 2) * s * arm_k)
    rig.update({
        "shadow": {"img": f"{prefix}shadow", "pivot": [round(sw / 2, 2), round(sh / 2, 2)]},
        "leg": {"img": f"{prefix}leg", "pivot": [round(gw * s / 2, 2), round(0.14 * gh * s, 2)]},
        "hip": {"x": round(hip_x, 2), "y": round(hip_y, 2)},
        "torso": {"img": f"{prefix}torso", "pivot": [round(tw * s / 2, 2), round(0.92 * th * s, 2)]},
        "waistY": round(hip_y, 2),
        "shoulder": {"x": round(shoulder_x, 2), "y": round(shoulder_y, 2)},
        "L1": round(L1, 2), "L2": round(L2, 2),
        "armUpper": {"img": f"{prefix}arm_upper", "pivot": [round((up_w0 + uw_top / 2) * s * arm_k, 2), round(uw_top / 2 * s * arm_k, 2)]},
        "armLower": {"img": f"{prefix}arm_lower", "pivot": [round((lo_w0 + lw_top / 2) * s * arm_k, 2), round(lw_top / 2 * s * arm_k, 2)]},
        "neck": {"y": round(top + 0.02 * th * s, 2)},
        "head": None,
        "face": {"pattern": prefix + "face_{k}", "pivot": [round(cw * s / 2, 2), round(0.94 * ch * s, 2)]},
        "handK": round((L1 + L2) / 170.0, 4),
        "parts": {"torso": [tw, th], "arm_upper": [uw, uh], "arm_lower": [lw, lh], "leg": [gw, gh], "head": [cw, ch]},
    })
    probs = rig_problems(rig)
    if probs:
        raise CharRigError("; ".join(probs))
    (out_dir).mkdir(parents=True, exist_ok=True)
    (out_dir / "rig.json").write_text(json.dumps(rig, ensure_ascii=False, indent=2), encoding="utf-8")
    return rig


def rig_problems(rig):
    """Sanity limits on the measured rig (so absurd geometry is refused instead of animated)."""
    p = []
    reach = rig["L1"] + rig["L2"]
    body = -rig["waistY"]
    if not 0.55 * body <= reach <= 1.9 * body:
        p.append(f"arm reach {reach:.0f}px vs leg height {body:.0f}px is implausible")
    if rig["hip"]["x"] * 2 > 0.95 * rig["shoulder"]["x"] * 2 * 1.6:
        p.append("legs are much wider apart than the shoulders")
    if rig["shoulder"]["y"] >= 0 or rig["waistY"] >= 0:
        p.append("joints are below the root")
    return p


if __name__ == "__main__":
    r = build_rig(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4])
    print(json.dumps({k: r[k] for k in ("scale", "waistY", "hip", "shoulder", "L1", "L2", "handK")}))
