"""SVG generators for Bi v2 and props (all from style/tokens.json) + SVG->PNG (2x) via VectorCraft."""
import json, math, subprocess
from pathlib import Path
P2 = Path(__file__).resolve().parent.parent
TOK = json.loads((P2 / "style/tokens.json").read_text(encoding="utf-8"))
import toolpaths
VC = toolpaths.vectorcraft()
K, SW = TOK["ink"], TOK["stroke"]
A = TOK["accent"]
LN = f'stroke="{K}" stroke-width="{SW}" stroke-linecap="round" stroke-linejoin="round"'
LN5 = LN.replace(f'stroke-width="{SW}"', 'stroke-width="5"')
LN6 = LN.replace(f'stroke-width="{SW}"', 'stroke-width="6"')


def svg(w, h, body):
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">{body}</svg>'


# ---------- Bi v2 (1x units; pivots documented in STYLE_GUIDE.md and lib/bi_rig.jsx) ----------
def head():
    return svg(220, 220, f'<circle cx="110" cy="105" r="95" fill="{TOK["skin"]}" {LN}/>')


EYE = f'fill="{K}"'


def face(kind):
    b = {
        "happy": f'<circle cx="72" cy="92" r="9" {EYE}/><circle cx="148" cy="92" r="9" {EYE}/><path d="M62 125 Q110 175 158 125 Z" fill="#fff" {LN}/>',
        "neutral": f'<circle cx="72" cy="98" r="9" {EYE}/><circle cx="148" cy="98" r="9" {EYE}/><path d="M82 140 L138 140" fill="none" {LN}/>',
        "worried": f'<circle cx="72" cy="105" r="9" {EYE}/><circle cx="148" cy="105" r="9" {EYE}/><path d="M50 90 L92 72 M170 90 L128 72" fill="none" {LN}/><path d="M78 152 Q110 126 142 152" fill="none" {LN}/>',
        "surprised": f'<circle cx="72" cy="92" r="12" fill="#fff" {LN}/><circle cx="148" cy="92" r="12" fill="#fff" {LN}/><circle cx="72" cy="92" r="4" {EYE}/><circle cx="148" cy="92" r="4" {EYE}/><ellipse cx="110" cy="145" rx="16" ry="22" fill="#fff" {LN}/><path d="M55 62 Q72 50 89 62 M131 62 Q148 50 165 62" fill="none" {LN}/>',
        "thinking": f'<circle cx="72" cy="98" r="9" {EYE}/><circle cx="148" cy="98" r="9" {EYE}/><path d="M84 142 Q110 132 138 144" fill="none" {LN}/><path d="M50 74 L92 80 M128 70 Q148 60 168 70" fill="none" {LN}/>',
    }[kind]
    return svg(220, 220, b)


FACES = ["happy", "neutral", "worried", "surprised", "thinking"]


def torso(shirt):
    """240x210, pivot (120,202). Shoulder caps (circles at x=40/200, y=34, r=22) are unioned with the body (x 52..188) so sleeves
    emerge from them and hanging arms stay outside the body outline.
    Outline trick: wide stroke underlay, then fill-only shapes on top, so only the OUTER outline of the union remains."""
    shapes = (f'<circle cx="40" cy="34" r="22"/><circle cx="200" cy="34" r="22"/>'
              f'<rect x="52" y="8" width="136" height="194" rx="44"/>')
    under = f'<g fill="{K}" stroke="{K}" stroke-width="{SW * 2}" stroke-linejoin="round">{shapes}</g>'
    top = f'<g fill="{shirt}" stroke="none">{shapes}</g>'
    collar = f'<path d="M100 10 Q120 38 140 10" fill="none" {LN}/>'
    return svg(240, 210, under + top + collar)


def arm_upper(shirt):
    return svg(40, 110, f'<path d="M20 15 L20 100" fill="none" {LN}/><rect x="6" y="6" width="28" height="56" rx="14" fill="{shirt}" {LN}/>')


def arm_lower():
    return svg(40, 120, f'<path d="M20 15 L20 88" fill="none" {LN}/><circle cx="20" cy="100" r="15" fill="{TOK["skin"]}" {LN}/>')


def leg():
    return svg(60, 205, f'<rect x="10" y="6" width="40" height="150" rx="16" fill="{TOK["pants"]}" {LN}/><path d="M6 168 Q6 150 30 150 Q54 150 54 168 L58 188 Q58 196 50 196 L12 196 Q4 196 4 188 Z" fill="{TOK["shoe"]}" {LN}/>')


# ---------- props ----------
def phone():
    return svg(300, 520, f'<rect x="10" y="10" width="280" height="500" rx="40" fill="#2B2F3A" {LN}/><rect x="30" y="56" width="240" height="408" rx="14" fill="#F7FBFF"/>')


def card():
    return svg(600, 170, f'<rect x="8" y="8" width="584" height="154" rx="26" fill="#fff" {LN}/><circle cx="84" cy="85" r="36" fill="{A["green"]}" {LN}/><path d="M66 86 L80 100 L104 70" fill="none" stroke="#fff" stroke-width="10" stroke-linecap="round" stroke-linejoin="round"/>')


NOTICE_ICONS = ("check", "warn", "info", "none")


def notice_plate(icon, w=600):
    """The notice card without the baked-in tick: the symbol follows the MEANING of the message (check = confirmed, warn = a problem, info = neutral, none = no symbol)."""
    plate = f'<rect x="8" y="8" width="{w - 16}" height="154" rx="26" fill="#fff" {LN}/>'
    if icon == "check":
        sym = f'<circle cx="84" cy="85" r="36" fill="{A["green"]}" {LN}/><path d="M66 86 L80 100 L104 70" fill="none" stroke="#fff" stroke-width="10" stroke-linecap="round" stroke-linejoin="round"/>'
    elif icon == "warn":
        sym = f'<circle cx="84" cy="85" r="36" fill="{A["red"]}" {LN}/><path d="M84 64 L84 88" stroke="#fff" stroke-width="10" stroke-linecap="round"/><circle cx="84" cy="105" r="6" fill="#fff"/>'
    elif icon == "info":
        sym = f'<circle cx="84" cy="85" r="36" fill="{A["blue"]}" {LN}/><path d="M84 84 L84 106" stroke="#fff" stroke-width="10" stroke-linecap="round"/><circle cx="84" cy="66" r="6" fill="#fff"/>'
    else:
        sym = ""
    return svg(w, 170, plate + sym)


def board(w=820, h=600):
    return svg(w, h, f'<rect x="8" y="8" width="{w - 16}" height="{h - 16}" rx="28" fill="#fff" {LN}/>')


def bar(color, w, h):
    return svg(w, h, f'<path d="M8 {h - 4} L8 22 Q8 8 22 8 L{w - 22} 8 Q{w - 8} 8 {w - 8} 22 L{w - 8} {h - 4} Z" fill="{color}" {LN}/>')


def wallet():
    return svg(240, 170, f'<rect x="8" y="22" width="224" height="140" rx="26" fill="#8B5A2B" {LN}/><rect x="120" y="68" width="112" height="52" rx="22" fill="{A["yellow"]}" {LN}/><circle cx="150" cy="94" r="8" fill="{K}"/>')


def calculator():
    keys = "".join(
        f'<rect x="{26 + c * 50}" y="{118 + r * 46}" width="40" height="34" rx="9" fill="{A["yellow"] if c == 3 else "#fff"}" {LN5}/>'
        for r in range(4) for c in range(4))
    return svg(230, 320, f'<rect x="8" y="8" width="214" height="304" rx="26" fill="{A["blue"]}" {LN}/><rect x="26" y="28" width="178" height="68" rx="12" fill="#EAF6FF" {LN}/>{keys}')


def coin():
    return svg(80, 80, f'<circle cx="40" cy="40" r="32" fill="{A["yellow"]}" {LN}/><path d="M32 32 Q40 24 48 32 Q48 40 40 40 Q32 40 32 48 Q40 56 48 48 M40 22 L40 58" fill="none" stroke="{K}" stroke-width="5" stroke-linecap="round"/>')


def jar():
    coins = "".join(f'<circle cx="{x}" cy="{y}" r="22" fill="{A["yellow"]}" {LN}/>' for x, y in ((70, 262), (125, 268), (98, 226), (150, 224)))
    return svg(220, 300, f'<rect x="38" y="6" width="144" height="30" rx="12" fill="{A["teal"]}" {LN}/><path d="M42 40 L178 40 Q200 60 200 100 L200 262 Q200 292 170 292 L50 292 Q20 292 20 262 L20 100 Q20 60 42 40 Z" fill="#DFF5F2" {LN}/>{coins}')


def bill():
    return svg(380, 480, f'<path d="M12 12 L368 12 L368 450 L330 468 L290 450 L250 468 L210 450 L170 468 L130 450 L90 468 L50 450 L12 468 Z" fill="#fff" {LN}/><rect x="12" y="12" width="356" height="78" fill="{A["red"]}" {LN}/><path d="M44 392 L250 392 M44 424 L180 424" fill="none" stroke="#C9CED6" stroke-width="10" stroke-linecap="round"/>')


def pie(parts):
    cx = cy = 150
    r = 136
    tot = sum(v for v, _ in parts)
    a0 = -math.pi / 2
    out = ""
    for v, c in parts:
        a1 = a0 + 2 * math.pi * v / tot
        large = 1 if a1 - a0 > math.pi else 0
        out += (f'<path d="M{cx} {cy} L{cx + r * math.cos(a0):.1f} {cy + r * math.sin(a0):.1f} '
                f'A{r} {r} 0 {large} 1 {cx + r * math.cos(a1):.1f} {cy + r * math.sin(a1):.1f} Z" fill="{c}" {LN}/>')
        a0 = a1
    return svg(300, 300, out)


def sweat():
    return svg(56, 80, f'<path d="M28 8 Q6 40 6 54 Q6 74 28 74 Q50 74 50 54 Q50 40 28 8 Z" fill="#8FD3FF" {LN6}/>')


def exclaim():
    return svg(70, 170, f'<rect x="14" y="8" width="42" height="108" rx="20" fill="{A["red"]}" {LN}/><circle cx="35" cy="146" r="18" fill="{A["red"]}" {LN}/>')


def shadow():
    return svg(420, 70, '<ellipse cx="210" cy="35" rx="200" ry="26" fill="#000" fill-opacity="0.12"/>')


def sparkle():
    return svg(90, 90, f'<path d="M45 6 L55 35 L84 45 L55 55 L45 84 L35 55 L6 45 L35 35 Z" fill="{A["yellow"]}" {LN5}/>')


def ensure_png(name, svg_text, outdir=None):
    """Write SVG and render PNG at tokens.pngScale. Returns the PNG path."""
    outdir = Path(outdir or P2 / "assets")
    (outdir / "svg").mkdir(parents=True, exist_ok=True)
    (outdir / "png").mkdir(parents=True, exist_ok=True)
    f = outdir / "svg" / f"{name}.svg"
    p = outdir / "png" / f"{name}.png"
    f.write_text(svg_text, encoding="utf-8")
    subprocess.run([VC, "convert", str(f), str(p), "--scale", str(TOK["pngScale"])], check=True, capture_output=True)
    return p


def make_character(outdir=None, shirt=None):
    shirt = shirt or TOK["bi"]
    ensure_png("head", head(), outdir)
    ensure_png("torso", torso(shirt), outdir)
    ensure_png("arm_upper", arm_upper(shirt), outdir)
    ensure_png("arm_lower", arm_lower(), outdir)
    ensure_png("leg", leg(), outdir)
    for k in FACES:
        ensure_png(f"face_{k}", face(k), outdir)


def make_props(outdir=None):
    items = {"pen": pen(), "basket": basket(), "notebook": notebook(), "phone": phone(), "card": card(), "board": board(), "wallet": wallet(), "calculator": calculator(),
             "coin": coin(), "jar": jar(), "bill": bill(), "sweat": sweat(), "exclaim": exclaim(),
             "shadow": shadow(), "sparkle": sparkle(),
             "pie": pie([(45, A["blue"]), (25, A["yellow"]), (20, A["pink"]), (10, A["teal"])])}
    for n, s in items.items():
        ensure_png(n, s, outdir)


if __name__ == "__main__":
    make_character()
    make_props()
    print("assets ok")


def pen():
    return svg(36, 220, f'<rect x="8" y="8" width="20" height="168" rx="6" fill="{A["yellow"]}" {LN}/><path d="M8 176 L18 212 L28 176 Z" fill="#f2d4b0" {LN}/><rect x="8" y="8" width="20" height="34" rx="6" fill="{A["pink"]}" {LN}/>')


def basket():
    return svg(240, 190, f'<path d="M50 84 Q120 -6 190 84" fill="none" stroke="#7a4a1d" stroke-width="12" stroke-linecap="round"/><path d="M20 84 H220 L196 178 H44 Z" fill="#e8a45a" {LN}/><path d="M34 116 H206 M40 148 H200 M92 84 L84 178 M148 84 L156 178" fill="none" stroke="#a8692c" stroke-width="6"/>')


def notebook():
    rows = "".join(f'<path d="M44 {52 + 30 * i} H236" stroke="#9db4d8" stroke-width="5" fill="none"/>' for i in range(5))
    return svg(260, 200, f'<rect x="8" y="8" width="244" height="184" rx="14" fill="#fff" {LN}/><path d="M32 8 V192" stroke="#e0584f" stroke-width="5"/>{rows}'
                         + "".join(f'<circle cx="16" cy="{30 + 34 * i}" r="6" fill="{A["blue"]}" {LN5}/>' for i in range(5)))


def ring(w, h, color):
    return svg(w, h, f'<rect x="8" y="8" width="{w - 16}" height="{h - 16}" rx="28" fill="none" stroke="{color}" stroke-width="10" stroke-dasharray="26 14" stroke-linecap="round"/>')


def panel(w, h):
    return svg(w, h, f'<rect x="4" y="4" width="{w - 8}" height="{h - 8}" rx="40" fill="#fffaf0" fill-opacity="0.93" stroke="#2b2f3a" stroke-opacity="0.35" stroke-width="4"/>')


def cell(w=330, h=120):
    return svg(w, h, f'<rect x="6" y="6" width="{w - 12}" height="{h - 12}" rx="20" fill="#fff" {LN}/>')


def pill(w=560, h=110):
    return svg(w, h, f'<rect x="8" y="8" width="{w - 16}" height="{h - 16}" rx="{(h - 16) // 2}" fill="#fff" {LN}/>')


def badge():
    return svg(80, 80, f'<circle cx="40" cy="40" r="32" fill="{A["yellow"]}" {LN}/>')


def swatch(color):
    return svg(60, 60, f'<rect x="8" y="8" width="44" height="44" rx="12" fill="{color}" {LN}/>')


def arrow_down():
    return svg(90, 130, f'<path d="M45 10 L45 100 M16 74 L45 106 L74 74" fill="none" stroke="{A["green"]}" stroke-width="16" stroke-linecap="round" stroke-linejoin="round"/>')


def subbar(w=1000, h=84):
    return svg(w, h, f'<rect x="0" y="0" width="{w}" height="{h}" rx="{h // 2}" fill="#fff" fill-opacity="0.9"/>')
