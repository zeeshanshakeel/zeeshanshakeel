#!/usr/bin/env python3
"""Builds the animated SVGs in ../assets for the GitHub profile README.

Edit the text in the functions below, then run:
    pip install fonttools brotli
    python scripts/build_assets.py

Fonts: Geist Mono + Geist Pixel by Vercel (SIL Open Font License 1.1),
subset and embedded so the SVGs look the same for every visitor.
"""
import base64
import io
import math
import random
from pathlib import Path
from xml.sax.saxutils import escape

from fontTools.subset import Options, Subsetter
from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parent.parent
FONTS = ROOT / "scripts" / "fonts"
OUT = ROOT / "assets"

# ── palette (from zeeshan-shakeel.com) ──────────────────────────────────────
PAPER, PAPER2, INK = "#0e0f11", "#16181b", "#08090a"
BONE, DIM, ACCENT = "#e9ecef", "#808891", "#9fc0d8"
HAIR = "rgba(233,236,239,.12)"
PIX, MONO = "GeistPixel-Square", "GeistMono-Regular"

# ── fonts ───────────────────────────────────────────────────────────────────
CHARSET = "".join(chr(c) for c in range(32, 127)) + "↓→×·∞®—’›↗…"
_cache = {}


def font(name):
    if name not in _cache:
        _cache[name] = TTFont(FONTS / f"{name}.woff2")
    return _cache[name]


def font_face(family, name):
    t = TTFont(FONTS / f"{name}.woff2")
    opts = Options()
    opts.flavor = "woff2"
    opts.layout_features = ["*"]
    s = Subsetter(opts)
    s.populate(text=CHARSET)
    s.subset(t)
    buf = io.BytesIO()
    t.flavor = "woff2"
    t.save(buf)
    b64 = base64.b64encode(buf.getvalue()).decode()
    return f"@font-face{{font-family:'{family}';src:url(data:font/woff2;base64,{b64}) format('woff2');}}"


def text_width(s, name, size):
    t = font(name)
    cm, hm, upm = t.getBestCmap(), t["hmtx"], t["head"].unitsPerEm
    return sum(hm[cm.get(ord(c), cm[ord("?")])][0] for c in s) * size / upm


FACES = None


def faces():
    global FACES
    if FACES is None:
        FACES = (
            font_face("GMono", "GeistMono-Regular")
            + font_face("GPixel", "GeistPixel-Square")
        )
    return FACES


BASE_CSS = f"""
.mono{{font-family:'GMono',ui-monospace,SFMono-Regular,Menlo,monospace}}
.monom{{font-family:'GMonoM','GMono',ui-monospace,monospace}}
.pix{{font-family:'GPixel','GMono',ui-monospace,monospace}}
.bone{{fill:{BONE}}} .dim{{fill:{DIM}}} .acc{{fill:{ACCENT}}}
"""


def svg(w, h, body, css, label):
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
        f'role="img" aria-label="{escape(label)}">\n'
        f"<title>{escape(label)}</title>\n<style>{faces()}{BASE_CSS}{css}</style>\n{body}\n</svg>\n"
    )


def T(x, y, s, cls, size, anchor="start", extra=""):
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" class="{cls}" font-size="{size}" '
        f'text-anchor="{anchor}" {extra}>{escape(s)}</text>'
    )


def frame(w, h, r=14):
    """Card background: paper, grid, glow, hairline border, corner ticks."""
    ticks = []
    L = 14
    for (x, y, dx, dy) in [(10, 10, 1, 1), (w - 10, 10, -1, 1), (10, h - 10, 1, -1), (w - 10, h - 10, -1, -1)]:
        ticks.append(
            f'<path d="M{x} {y + dy * L}V{y}H{x + dx * L}" fill="none" stroke="{ACCENT}" stroke-width="1.5" opacity=".7"/>'
        )
    return f"""
<defs>
  <pattern id="grid" width="28" height="28" patternUnits="userSpaceOnUse">
    <path d="M28 0H0V28" fill="none" stroke="{BONE}" stroke-opacity=".045" stroke-width="1"/>
  </pattern>
  <radialGradient id="vig" cx="50%" cy="40%" r="75%">
    <stop offset="0" stop-color="{ACCENT}" stop-opacity=".07"/>
    <stop offset="1" stop-color="{INK}" stop-opacity="0"/>
  </radialGradient>
  <clipPath id="card"><rect width="{w}" height="{h}" rx="{r}"/></clipPath>
</defs>
<g clip-path="url(#card)">
  <rect width="{w}" height="{h}" fill="{PAPER}"/>
  <rect width="{w}" height="{h}" fill="url(#grid)"/>
  <rect width="{w}" height="{h}" fill="url(#vig)"/>
</g>
<rect x=".5" y=".5" width="{w - 1}" height="{h - 1}" rx="{r}" fill="none" stroke="{HAIR}"/>
{''.join(ticks)}
"""


class KF:
    """Collects @keyframes + class rules for one looping timeline of `total` seconds."""

    def __init__(self, total):
        self.total, self.rules, self.n = total, [], 0

    def pct(self, t):
        return max(0.0, min(100.0, t / self.total * 100))

    def add(self, frames):
        self.n += 1
        name = f"k{self.n}"
        body = "".join(f"{p:.3f}%{{{css}}}" for p, css in frames)
        self.rules.append(
            f"@keyframes {name}{{{body}}}.{name}{{animation:{name} {self.total}s linear infinite;"
            f"transform-box:fill-box;transform-origin:0 50%}}"
        )
        return name

    def show_at(self, t, end=0.965):
        """Hidden until t, visible until the end of the loop."""
        p = self.pct(t)
        return self.add(
            [(0, "opacity:0"), (max(p - 0.01, 0), "opacity:0"), (p, "opacity:1"),
             (end * 100, "opacity:1"), (end * 100 + 1.2, "opacity:0"), (100, "opacity:0")]
        )

    def window(self, t0, t1):
        """Visible only between t0 and t1."""
        a, b = self.pct(t0), self.pct(t1)
        return self.add(
            [(0, "opacity:0"), (max(a - 0.01, 0), "opacity:0"), (a, "opacity:1"),
             (b, "opacity:1"), (min(b + 0.01, 100), "opacity:0"), (100, "opacity:0")]
        )

    def css(self):
        return "\n".join(self.rules)


# ════════════════════════════════════════════════════════════════════════════
# HERO — loader, name decode, typed subtitle, live funnel
# ════════════════════════════════════════════════════════════════════════════
def hero():
    W, H = 900, 340
    rnd = random.Random(7)
    css, body = [], [frame(W, H)]

    # HUD top bar
    body.append(T(34, 38, "ZS® / THE FUNNEL METHOD", "pix dim", 11))
    body.append(T(W / 2 + 8, 38, "PORTFOLIO 2026", "pix dim", 11, "middle"))
    body.append(T(W - 34, 38, "KHI → KUL → LAX", "pix dim", 11, "end"))
    body.append(f'<circle cx="{W / 2 - 52}" cy="34.5" r="3" fill="{ACCENT}" class="blink"/>')
    body.append(f'<line x1="34" y1="52" x2="{W - 34}" y2="52" stroke="{HAIR}"/>')
    css.append("@keyframes blink{0%,49%{opacity:1}50%,100%{opacity:.15}}.blink{animation:blink 1.1s steps(1) infinite}")

    # scanline
    body.append(
        f'<defs><linearGradient id="scan" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{ACCENT}" stop-opacity="0"/>'
        f'<stop offset=".5" stop-color="{ACCENT}" stop-opacity=".07"/><stop offset="1" stop-color="{ACCENT}" stop-opacity="0"/></linearGradient></defs>'
        f'<g clip-path="url(#card)"><rect class="scan" x="0" y="-90" width="{W}" height="90" fill="url(#scan)"/></g>'
    )
    css.append(f"@keyframes scan{{0%{{transform:translateY(0)}}100%{{transform:translateY({H + 90}px)}}}}.scan{{animation:scan 5.5s linear infinite}}")

    # ── loader (plays once) ──
    lx, ly = 48, 150
    loader = [T(lx, ly, "LOADING", "pix dim", 12)]
    vals = [0, 6, 14, 27, 41, 58, 73, 86, 95, 100]
    step = 0.13
    for i, v in enumerate(vals):
        d = 0.15 + i * step
        last = i == len(vals) - 1
        anim = f"animation:on .01s {d:.2f}s forwards" if last else f"animation:flash {step:.2f}s steps(1) {d:.2f}s 1"
        loader.append(T(lx + 70, ly, f"{v:03d}%", "pix bone", 12, extra=f'style="opacity:0;{anim}"'))
    loader.append(f'<rect x="{lx}" y="{ly + 12}" width="220" height="2" fill="{HAIR}"/>')
    loader.append(f'<rect x="{lx}" y="{ly + 12}" width="220" height="2" fill="{ACCENT}" class="lbar"/>')
    body.append(f'<g class="loader">{"".join(loader)}</g>')
    load_end = 0.15 + len(vals) * step + 0.1
    css.append("@keyframes flash{0%,100%{opacity:1}}@keyframes on{to{opacity:1}}@keyframes off{to{opacity:0}}")
    css.append(
        f"@keyframes lbar{{from{{transform:scaleX(0)}}to{{transform:scaleX(1)}}}}"
        f".lbar{{transform-box:fill-box;transform-origin:0 50%;animation:lbar {load_end - 0.25:.2f}s cubic-bezier(.6,.1,.3,1) .15s both}}"
        f".loader{{animation:off .25s {load_end:.2f}s forwards}}"
    )

    # ── name decode (plays once) ──
    glyphs = "ABCDEFGHJKLMNPRSTUVWXYZ0123456789#%&@$/<>"
    size = 58
    start = load_end + 0.15
    gl_layers = []
    k = 0
    for word, y in [("ZEESHAN", 128), ("SHAKEEL", 188)]:
        x = 46
        for ch in word:
            d0 = start + k * 0.055
            for j in range(4):
                g = rnd.choice(glyphs)
                d = d0 + j * 0.06
                body.append(T(x, y, g, "pix acc", size, extra=f'style="opacity:0;animation:flash .06s steps(1) {d:.2f}s 1"'))
            body.append(T(x, y, ch, "pix bone", size, extra=f'style="opacity:0;animation:on .01s {d0 + 0.24:.2f}s forwards"'))
            gl_layers.append(T(x, y, ch, "pix acc", size))
            x += text_width(ch, PIX, size)
            k += 1
    name_done = start + k * 0.055 + 0.3

    # glitch copy of the name, flickers every 7s
    body.append(
        '<defs><clipPath id="sl"><rect x="0" y="86" width="900" height="9"/><rect x="0" y="108" width="900" height="6"/>'
        '<rect x="0" y="150" width="900" height="11"/><rect x="0" y="176" width="900" height="5"/></clipPath></defs>'
        f'<g clip-path="url(#sl)"><g class="glitch">{"".join(gl_layers)}</g></g>'
    )
    css.append(
        "@keyframes glitch{0%,90%{opacity:0;transform:translateX(0)}91%{opacity:.9;transform:translateX(-5px)}"
        "93%{opacity:.9;transform:translateX(6px)}95%{opacity:.7;transform:translateX(-2px)}96%,100%{opacity:0}}"
        f".glitch{{opacity:0;animation:glitch 7s steps(1) {name_done + 1:.2f}s infinite}}"
    )

    # ── subtitle typed ──
    sub = "Digital marketer × AI marketing technologist"
    sx, sy, ss = 48, 228, 15
    n = len(sub)
    cw = 0.6 * ss
    t0 = name_done
    dur = n * 0.03
    for j, ch in enumerate(sub):
        if ch != " ":
            d = t0 + (j + 1) * dur / n
            body.append(T(sx + j * cw, sy, ch, "mono bone", ss, extra=f'style="opacity:0;animation:on .01s {d:.3f}s forwards"'))
    body.append(f'<rect class="typ" x="{sx}" y="{sy - 14}" width="{cw:.1f}" height="18" fill="{ACCENT}" style="opacity:0"/>')
    css.append(
        f"@keyframes typ{{from{{transform:translateX(0)}}to{{transform:translateX({n * cw:.1f}px)}}}}"
        f"@keyframes cur{{0%{{opacity:1}}100%{{opacity:1}}}}"
        f".typ{{animation:typ {dur:.2f}s steps({n}) {t0:.2f}s both,cur {dur + 0.8:.2f}s {t0:.2f}s 1}}"
    )
    tag = "Brand · Content · Growth — marketing myself, top to tip."
    body.append(T(sx, sy + 26, tag, "mono dim", 12.5, extra=f'style="opacity:0;animation:on .6s {t0 + dur + 0.3:.2f}s forwards"'))

    # ── funnel ──
    cx = 728
    levels = [(66, 150), (120, 108), (174, 72), (228, 40), (282, 13)]
    stages = [("01 AWARENESS", "get seen"), ("02 INTEREST", "get felt"), ("03 DESIRE", "get wanted"), ("04 ACTION", "get chosen")]
    cyc = 8.0
    f = []
    for i in range(4):
        (y0, h0), (y1, h1) = levels[i], levels[i + 1]
        f.append(f'<path class="b{i}" d="M{cx - h0} {y0}L{cx + h0} {y0}L{cx + h1} {y1}L{cx - h1} {y1}Z" fill="{ACCENT}" opacity=".03"/>')
        a, b = i * 25, (i + 1) * 25
        css.append(
            f"@keyframes b{i}{{0%{{opacity:.03}}{max(a - 0.1, 0):.1f}%{{opacity:.03}}{a + 3}%{{opacity:.22}}{b - 3}%{{opacity:.12}}"
            f"{min(b + 0.1, 100):.1f}%{{opacity:.03}}100%{{opacity:.03}}}}.b{i}{{animation:b{i} {cyc}s ease-in-out infinite}}"
            f"@keyframes l{i}{{0%{{fill:{DIM}}}{max(a - 0.1, 0):.1f}%{{fill:{DIM}}}{a + 0.2}%{{fill:{ACCENT}}}{b - 0.2}%{{fill:{ACCENT}}}"
            f"{min(b + 0.1, 100):.1f}%{{fill:{DIM}}}100%{{fill:{DIM}}}}}.l{i}{{animation:l{i} {cyc}s steps(1) infinite}}"
        )
        ym = (y0 + y1) / 2
        hm = (h0 + h1) / 2
        f.append(T(cx - hm - 18, ym - 1, stages[i][0], f"pix l{i}", 10.5, "end"))
        f.append(T(cx - hm - 18, ym + 13, stages[i][1], "mono dim", 10.5, "end"))
    for y, h in levels:
        f.append(f'<ellipse cx="{cx}" cy="{y}" rx="{h}" ry="{h * 0.16:.1f}" fill="none" stroke="{BONE}" stroke-opacity=".28"/>')
    for sgn in (-1, 1):
        f.append(
            f'<path d="M{cx + sgn * 150} 66 ' + " ".join(f"L{cx + sgn * h} {y}" for y, h in levels[1:])
            + f'" fill="none" stroke="{BONE}" stroke-opacity=".35"/>'
        )
    f.append(f'<line x1="{cx}" y1="282" x2="{cx}" y2="312" stroke="{ACCENT}" stroke-opacity=".5" stroke-dasharray="2 3"/>')
    body.append("".join(f))

    # particles: strangers fall in, most drop off, a few come out as customers
    def half(y):
        for (y0, h0), (y1, h1) in zip(levels, levels[1:]):
            if y0 <= y <= y1:
                return h0 + (h1 - h0) * (y - y0) / (y1 - y0)
        return 13

    drops = [120] * 10 + [174] * 7 + [228] * 4 + [None] * 4
    pd = 4.6
    parts = []
    for drop in drops:
        r = rnd.uniform(-0.9, 0.9)
        pts = [(cx + r * half(y), y) for y in (60, 120, 174, 228, 282)]
        path = "M" + " L".join(f"{x:.1f} {y}" for x, y in pts) + f" L{cx} 312"
        begin = -rnd.uniform(0, pd)
        if drop is None:
            ft = 0.97
            col = (f'<animate attributeName="fill" values="{BONE};{BONE};{ACCENT};{ACCENT}" keyTimes="0;.8;.86;1" '
                   f'dur="{pd}s" begin="{begin:.2f}s" repeatCount="indefinite"/>')
        else:
            ft = (drop - 60 + rnd.uniform(-20, 10)) / 252 * 0.92
            col = ""
        parts.append(
            f'<circle r="2.1" fill="{BONE}" opacity="0"><animateMotion path="{path}" dur="{pd}s" begin="{begin:.2f}s" repeatCount="indefinite"/>'
            f'<animate attributeName="opacity" values="0;.9;.9;0;0" keyTimes="0;.05;{ft:.3f};{min(ft + 0.03, 0.999):.3f};1" '
            f'dur="{pd}s" begin="{begin:.2f}s" repeatCount="indefinite"/>{col}</circle>'
        )
        if drop is None:
            parts.append(
                f'<circle cx="{cx}" cy="282" r="0" fill="none" stroke="{ACCENT}" stroke-width="1.2" opacity="0">'
                f'<animate attributeName="r" values="0;0;24" keyTimes="0;.86;1" dur="{pd}s" begin="{begin:.2f}s" repeatCount="indefinite"/>'
                f'<animate attributeName="opacity" values="0;0;.9;0" keyTimes="0;.86;.87;1" dur="{pd}s" begin="{begin:.2f}s" repeatCount="indefinite"/></circle>'
            )
    body.append("".join(parts))
    body.append(T(cx + 16, 318, "stranger → customer", "mono dim", 10))

    # bottom HUD
    body.append(f'<line x1="34" y1="290" x2="420" y2="290" stroke="{HAIR}"/>')
    body.append(T(48, 314, "SCROLL TO DESCEND", "pix dim", 10.5))
    body.append(T(48 + text_width("SCROLL TO DESCEND ", PIX, 10.5), 314, "↓", "pix acc bob", 12))
    css.append("@keyframes bob{0%,100%{transform:translateY(-2px)}50%{transform:translateY(3px)}}.bob{animation:bob 1.4s ease-in-out infinite}")
    for i in range(4):
        a, b = i * 25, (i + 1) * 25
        css.append(
            f"@keyframes c{i}{{0%{{opacity:0}}{max(a - 0.1, 0):.1f}%{{opacity:0}}{a}%{{opacity:1}}{b - 0.1}%{{opacity:1}}{b}%{{opacity:0}}100%{{opacity:0}}}}"
            f".c{i}{{opacity:0;animation:c{i} {cyc}s steps(1) infinite}}"
        )
        body.append(T(406, 314, f"STAGE 0{i + 1} / 04", f"pix acc c{i}", 10.5, "end"))

    return svg(W, H, "\n".join(body), "\n".join(css), "Zeeshan Shakeel — digital marketer and AI marketing technologist")


# ════════════════════════════════════════════════════════════════════════════
# TERMINAL — the "coding bio"
# ════════════════════════════════════════════════════════════════════════════
def terminal():
    W = 900
    FS, LH, X0, Y0 = 14, 23, 30, 78
    CW = 0.6 * FS
    TOTAL = 22.0
    k = KF(TOTAL)

    def J(key, val, last=False):
        return ("out", [("  ", "dim"), (f'"{key}"', "acc"), (": ", "dim")] + val + ([] if last else [(",", "dim")]))

    def S(s):
        return [(f'"{s}"', "bone")]

    def arr(items):
        out = [("[", "dim")]
        for i, it in enumerate(items):
            out += [(f'"{it}"', "bone")] + ([(", ", "dim")] if i < len(items) - 1 else [])
        return out + [("]", "dim")]

    script = [
        ("cmd", "whoami"),
        ("out", [("zeeshan shakeel", "bone"), (" — digital marketer & AI marketing technologist", "dim")]),
        ("cmd", "cat about.json"),
        ("out", [("{", "dim")]),
        J("based_in", S("Los Angeles  (Karachi → Kuala Lumpur → LA)")),
        J("studying", S("B.S. Marketing @ CSUN, class of '27")),
        J("stack", arr(["Klaviyo", "GA4", "Meta", "TikTok Shop", "Shopify", "React"])),
        J("builds", S("AI tools that do the marketing grunt work")),
        J("motto", S("Nobody scrolls back for average."), last=True),
        ("out", [("}", "dim")]),
        ("cmd", './run-funnel --brand "you"'),
        ("bar", "awareness", 1.00, "get seen"),
        ("bar", "interest", 0.74, "get felt"),
        ("bar", "desire", 0.52, "get wanted"),
        ("bar", "action", 0.31, "get chosen"),
        ("out", [("› ", "acc"), ("stranger → customer", "bone"), ("  ·  status: ", "dim"), ("open to work", "acc"), (" (marketing × AI)", "dim")]),
        ("prompt",),
    ]
    H = Y0 + len(script) * LH + 14
    body = [frame(W, H, 12)]
    # window chrome
    body.append(f'<path d="M1 41V13A12 12 0 0 1 13 1H{W - 13}A12 12 0 0 1 {W - 1} 13V41Z" fill="{PAPER2}"/>')
    body.append(f'<line x1="1" y1="41" x2="{W - 1}" y2="41" stroke="{HAIR}"/>')
    for i, c in enumerate(["#e9ecef33", "#e9ecef22", ACCENT]):
        body.append(f'<circle cx="{24 + i * 18}" cy="21" r="5.5" fill="{c}"/>')
    body.append(T(W / 2, 25, "zeeshan@funnel: ~/portfolio — zsh", "mono dim", 11.5, "middle"))

    content = []
    t = 0.6
    for i, item in enumerate(script):
        y = Y0 + i * LH
        kind = item[0]
        if kind in ("cmd", "prompt"):
            cls = k.show_at(t)
            content.append(f'<g class="{cls}">' + T(X0, y, "~", "mono acc", FS) + T(X0 + CW * 2, y, "$", "mono bone", FS))
            cx0 = X0 + CW * 4
            if kind == "cmd":
                cmd = item[1]
                n = len(cmd)
                ts = t + 0.45
                te = ts + n * 0.055
                # one character at a time, block cursor riding the leading edge
                for j, ch in enumerate(cmd):
                    if ch != " ":
                        c = k.show_at(ts + (j + 1) * (te - ts) / n)
                        content.append(f'<g class="{c}">' + T(cx0 + j * CW, y, ch, "mono bone", FS) + "</g>")
                mv = k.add([(0, "transform:translateX(0)"),
                            (k.pct(ts), f"transform:translateX(0);animation-timing-function:steps({n},end)"),
                            (k.pct(te), f"transform:translateX({n * CW:.1f}px)"), (100, f"transform:translateX({n * CW:.1f}px)")])
                hide = k.window(0, te + 0.35)
                content.append(
                    f'<g class="{hide}"><rect class="{mv}" x="{cx0}" y="{y - 14}" width="{CW:.1f}" height="18" fill="{ACCENT}"/></g>'
                )
                t = te + 0.4
            else:
                content.append(f'<rect x="{cx0}" y="{y - 14}" width="{CW:.1f}" height="18" fill="{ACCENT}" class="blink"/>')
            content.append("</g>")
        elif kind == "out":
            cls = k.show_at(t)
            spans = "".join(f'<tspan class="{c}">{escape(s)}</tspan>' for s, c in item[1])
            content.append(f'<text x="{X0}" y="{y}" class="mono {cls}" font-size="{FS}" xml:space="preserve">{spans}</text>')
            t += 0.09
        elif kind == "bar":
            _, label, frac, verb = item
            cls = k.show_at(t)
            bx, bw = X0 + CW * 15, 300
            f0, f1 = t + 0.1, t + 1.0
            grow = k.add([(0, "transform:scaleX(0)"),
                          (k.pct(f0), "transform:scaleX(0);animation-timing-function:cubic-bezier(.2,.7,.2,1)"),
                          (k.pct(f1), f"transform:scaleX({frac})"), (100, f"transform:scaleX({frac})")])
            ok = k.show_at(f1)
            content.append(
                f'<g class="{cls}">' + T(X0 + CW * 2, y, "›", "mono acc", FS) + T(X0 + CW * 4, y, label, "mono bone", FS)
                + f'<rect x="{bx:.1f}" y="{y - 10}" width="{bw}" height="8" rx="1" fill="{BONE}" fill-opacity=".08"/>'
                + f'<rect x="{bx:.1f}" y="{y - 10}" width="{bw}" height="8" rx="1" fill="{ACCENT}" class="{grow}"/>'
                + T(bx + bw + 22, y, verb, "mono dim", FS)
                + f'<g class="{ok}">' + T(bx + bw + 22 + CW * 13, y, "[ok]", "mono acc", FS) + "</g>"
                + "</g>"
            )
            t += 0.38
            if script[i + 1][0] != "bar":
                t += 1.4
        if kind == "out" and i + 1 < len(script) and script[i + 1][0] == "cmd":
            t += 0.5

    css = ["@keyframes blink{0%,49%{opacity:1}50%,100%{opacity:0}}.blink{animation:blink 1s steps(1) infinite}", k.css()]
    body.append("\n".join(content))
    return svg(W, H, "\n".join(body), "\n".join(css),
               "Terminal: whoami — Zeeshan Shakeel, digital marketer and AI marketing technologist based in Los Angeles")


# ════════════════════════════════════════════════════════════════════════════
# RECEIPTS — odometer stats with sparklines
# ════════════════════════════════════════════════════════════════════════════
def receipts():
    W, H = 900, 214
    TOTAL = 9.0
    k = KF(TOTAL)
    tiles = [
        ("01 · AWARENESS", "15K+", "organic views", "Delta Sigma Pi · IG video", [3, 4, 4, 7, 6, 9, 12, 11, 15]),
        ("02 · INTEREST", "+145%", "TikTok profile views", "Sonage Skincare", [2, 2, 3, 5, 4, 8, 10, 13, 16]),
        ("03 · DESIRE", "+25%", "content views", "Threadscapes · 5+ creators", [5, 6, 5, 7, 8, 8, 10, 11, 12]),
        ("04 · ACTION", "8", "campaigns shipped", "cross-channel · 3 storefronts", [1, 2, 2, 3, 4, 5, 6, 7, 8]),
    ]
    body = [frame(W, H)]
    defs = []
    gap, pad = 14, 22
    tw = (W - pad * 2 - gap * 3) / 4
    NS, LHD = 40, 46
    for ti, (stage, val, label, src, series) in enumerate(tiles):
        x, y = pad + ti * (tw + gap), 22
        th = H - 44
        body.append(f'<rect x="{x:.1f}" y="{y}" width="{tw:.1f}" height="{th}" rx="10" fill="{PAPER2}" stroke="{HAIR}"/>')
        body.append(T(x + 16, y + 26, stage, "pix acc", 10.5))
        # odometer number
        nx, ny = x + 16, y + 76
        clip_id = f"od{ti}"
        defs.append(f'<clipPath id="{clip_id}"><rect x="{x:.1f}" y="{ny - NS + 2}" width="{tw:.1f}" height="{NS + 8}"/></clipPath>')
        g = []
        cx = nx
        for ci, ch in enumerate(val):
            if ch.isdigit():
                d = int(ch)
                seq = list(range(10)) + list(range(d + 1))
                col = "".join(T(cx, ny + j * LHD, str(s), "pix bone", NS) for j, s in enumerate(seq))
                end = -(len(seq) - 1) * LHD
                t0 = 0.3 + ti * 0.18 + ci * 0.1
                t1 = t0 + 1.3 + ci * 0.15
                roll = k.add([(0, "transform:translateY(0)"),
                              (k.pct(t0), "transform:translateY(0);animation-timing-function:cubic-bezier(.15,.75,.2,1)"),
                              (k.pct(t1), f"transform:translateY({end}px)"), (100, f"transform:translateY({end}px)")])
                g.append(f'<g class="{roll}">{col}</g>')
            else:
                g.append(T(cx, ny, ch, "pix acc", NS))
            cx += text_width(ch, PIX, NS)
        fade = k.add([(0, "opacity:0"), (k.pct(0.25), "opacity:1"), (95, "opacity:1"), (98.5, "opacity:0"), (100, "opacity:0")])
        body.append(f'<g clip-path="url(#{clip_id})"><g class="{fade}">{"".join(g)}</g></g>')
        body.append(T(x + 16, y + 102, label, "mono bone", 12.5))
        body.append(T(x + 16, y + 120, src, "mono dim", 10.5))
        # sparkline
        sx0, sx1, sy0, sy1 = x + 16, x + tw - 16, y + th - 14, y + th - 40
        mx = max(series)
        pts = [(sx0 + (sx1 - sx0) * i / (len(series) - 1), sy0 - (sy0 - sy1) * v / mx) for i, v in enumerate(series)]
        line = "M" + " L".join(f"{a:.1f} {b:.1f}" for a, b in pts)
        area = line + f" L{sx1:.1f} {sy0} L{sx0:.1f} {sy0} Z"
        grad = f"sg{ti}"
        defs.append(f'<linearGradient id="{grad}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{ACCENT}" stop-opacity=".28"/>'
                    f'<stop offset="1" stop-color="{ACCENT}" stop-opacity="0"/></linearGradient>')
        L = 400
        t0 = 0.5 + ti * 0.2
        draw = k.add([(0, f"stroke-dashoffset:{L}"), (k.pct(t0), f"stroke-dashoffset:{L};animation-timing-function:ease-out"),
                      (k.pct(t0 + 1.6), "stroke-dashoffset:0"), (95, "stroke-dashoffset:0;opacity:1"),
                      (98.5, "stroke-dashoffset:0;opacity:0"), (100, f"stroke-dashoffset:{L};opacity:0")])
        afade = k.add([(0, "opacity:0"), (k.pct(t0 + 0.8), "opacity:0"), (k.pct(t0 + 1.8), "opacity:1"),
                       (95, "opacity:1"), (98.5, "opacity:0"), (100, "opacity:0")])
        body.append(f'<path d="{area}" fill="url(#{grad})" class="{afade}"/>')
        body.append(f'<path d="{line}" fill="none" stroke="{ACCENT}" stroke-width="1.6" stroke-linejoin="round" stroke-dasharray="{L}" class="{draw}"/>')
        lx, ly = pts[-1]
        body.append(f'<circle cx="{lx:.1f}" cy="{ly:.1f}" r="2.6" fill="{BONE}" class="{afade}"/>')
        body.append(f'<circle cx="{lx:.1f}" cy="{ly:.1f}" r="2.6" fill="none" stroke="{ACCENT}" class="ping" style="animation-delay:{ti * 0.4:.1f}s"/>')
    css = [
        "@keyframes ping{0%{transform:scale(1);opacity:.9}100%{transform:scale(4);opacity:0}}"
        ".ping{transform-box:fill-box;transform-origin:center;animation:ping 1.8s ease-out infinite}",
        k.css(),
    ]
    return svg(W, H, f"<defs>{''.join(defs)}</defs>" + "\n".join(body), "\n".join(css),
               "Receipts: 15K+ organic views, +145% TikTok profile views, +25% content views, 8 campaigns shipped")


# ════════════════════════════════════════════════════════════════════════════
# SECTION HEADERS
# ════════════════════════════════════════════════════════════════════════════
def header(num, stage, verb, note, idx):
    W, H = 900, 64
    body = [frame(W, H, 10)]
    body.append(T(28, 41, num, "pix acc", 24))
    x = 28 + text_width(num, PIX, 24) + 16
    body.append(T(x, 39, stage, "pix bone", 17))
    x += text_width(stage, PIX, 17) + 14
    body.append(T(x, 38, f"— {verb}", "mono dim", 13))
    body.append(T(W - 28, 38, note, "mono dim", 11.5, "end"))
    body.append(f'<rect x="{W - 28 - text_width(note, MONO, 11.5) - 16:.1f}" y="29" width="6" height="6" fill="{ACCENT}" class="blink"/>')
    body.append(f'<line x1="14" y1="{H - 10}" x2="{W - 14}" y2="{H - 10}" stroke="{HAIR}"/>')
    body.append(f'<rect x="14" y="{H - 11}" width="140" height="2" fill="{ACCENT}" class="sweep"/>')
    css = (
        "@keyframes blink{0%,49%{opacity:1}50%,100%{opacity:.15}}.blink{animation:blink 1.2s steps(1) infinite}"
        f"@keyframes sweep{{0%{{transform:translateX(-160px);opacity:0}}10%{{opacity:1}}90%{{opacity:1}}"
        f"100%{{transform:translateX({W - 140}px);opacity:0}}}}"
        f".sweep{{animation:sweep 3.6s cubic-bezier(.6,0,.4,1) {idx * 0.5:.1f}s infinite}}"
    )
    return svg(W, H, "\n".join(body), css, f"{num} {stage} — {verb}")


# ════════════════════════════════════════════════════════════════════════════
# FOOTER — the funnel never ends ∞
# ════════════════════════════════════════════════════════════════════════════
def footer():
    W, H = 900, 150
    cx, cy, a = W / 2, 58, 62
    pts = []
    for i in range(241):
        t = 2 * math.pi * i / 240
        d = 1 + math.sin(t) ** 2
        pts.append((cx + a * math.cos(t) / d, cy + a * math.sin(t) * math.cos(t) / d))
    path = "M" + " L".join(f"{x:.1f} {y:.1f}" for x, y in pts) + "Z"
    L = 420
    body = [frame(W, H)]
    body.append(f'<path d="{path}" fill="none" stroke="{BONE}" stroke-opacity=".14" stroke-width="1.4"/>')
    body.append(f'<path d="{path}" fill="none" stroke="{ACCENT}" stroke-width="2.4" stroke-linecap="round" stroke-dasharray="70 {L - 70}" class="loop"/>')
    body.append(f'<path d="{path}" fill="none" stroke="{BONE}" stroke-width="1.2" stroke-linecap="round" stroke-dasharray="14 {L - 14}" class="loop2"/>')
    body.append(T(cx, 112, "THE FUNNEL NEVER ENDS", "pix bone", 14, "middle"))
    body.append(T(cx, 132, "©2026 Zeeshan Shakeel · thanks for scrolling this far", "mono dim", 11, "middle"))
    body.append(T(34, 36, "EOF", "pix dim", 10.5))
    body.append(T(W - 34, 36, "∞", "mono acc", 13, "end"))
    css = f"@keyframes loop{{to{{stroke-dashoffset:-{L}}}}}.loop{{animation:loop 3.2s linear infinite}}.loop2{{animation:loop 3.2s linear -1.6s infinite}}"
    return svg(W, H, "\n".join(body), css, "The funnel never ends")


def main():
    OUT.mkdir(exist_ok=True)
    files = {
        "hero.svg": hero(),
        "terminal.svg": terminal(),
        "receipts.svg": receipts(),
        "h-01-awareness.svg": header("01", "AWARENESS", "get seen", "who i am", 0),
        "h-02-interest.svg": header("02", "INTEREST", "get felt", "the receipts", 1),
        "h-03-desire.svg": header("03", "DESIRE", "get wanted", "what i build", 2),
        "h-04-action.svg": header("04", "ACTION", "get chosen", "let's talk", 3),
        "footer.svg": footer(),
    }
    for name, data in files.items():
        (OUT / name).write_text(data, encoding="utf-8")
        print(f"{name:22s} {len(data.encode()) / 1024:6.1f} KB")


if __name__ == "__main__":
    main()
