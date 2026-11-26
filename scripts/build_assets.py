"""Generates the SVG artwork used in README.md.

Palette, fonts and motifs (flowers, bee, chunky offset shadows) mirror
https://anxmarks.com.br so the profile and the site feel like one thing.

Fonts are pulled from Google Fonts, subset to the glyphs actually used and
embedded as base64, so the SVGs render the same inside GitHub's <img> tags.

Usage:  pip install fonttools brotli
        python scripts/build_assets.py
"""
from __future__ import annotations

import base64
import io
import re
import urllib.request
from pathlib import Path

from fontTools.subset import Options, Subsetter
from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets"
CACHE = Path(__file__).resolve().parent / ".fonts"

# ---- site palette (css/style.css :root) ----------------------------------
CREAM = "#FDF7E4"
CARD = "#FFFDF2"
YELLOW = "#FBEFB0"
YELLOW_DEEP = "#F9D77E"
PINK = "#F07CB8"
PINK_DEEP = "#D4468C"
PINK_PALE = "#F5A9C0"
PURPLE = "#8E6FC4"
PURPLE_PALE = "#C9A7F0"
BLUE_PALE = "#ADD3F7"
GOLD = "#F5C446"
INK = "#3A2A44"
INK_SOFT = "#6B5878"

FONTS = {
    ("Fredoka", 700): None,
    ("Quicksand", 500): None,
    ("Quicksand", 700): None,
}


# ---- fonts ----------------------------------------------------------------
def load_font(family: str, weight: int) -> TTFont:
    CACHE.mkdir(exist_ok=True)
    path = CACHE / f"{family}-{weight}.ttf"
    if not path.exists():
        css_url = f"https://fonts.googleapis.com/css2?family={family}:wght@{weight}"
        css = urllib.request.urlopen(css_url).read().decode()
        ttf_url = re.search(r"url\((https://[^)]+\.ttf)\)", css).group(1)
        path.write_bytes(urllib.request.urlopen(ttf_url).read())
    return TTFont(path)


def font(family: str, weight: int) -> TTFont:
    key = (family, weight)
    if FONTS.get(key) is None:
        FONTS[key] = load_font(family, weight)
    return FONTS[key]


def text_width(s: str, family: str, weight: int, size: float, spacing: float = 0) -> float:
    f = font(family, weight)
    cmap = f.getBestCmap()
    hmtx = f["hmtx"]
    upm = f["head"].unitsPerEm
    total = 0
    for ch in s:
        g = cmap.get(ord(ch)) or cmap.get(ord("?"))
        total += hmtx[g][0]
    return total * size / upm + spacing * max(len(s) - 1, 0)


def wrap(s: str, family: str, weight: int, size: float, max_w: float) -> list[str]:
    lines, cur = [], ""
    for word in s.split():
        trial = f"{cur} {word}".strip()
        if text_width(trial, family, weight, size) <= max_w:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def font_face(used: dict[tuple[str, int], str]) -> str:
    """@font-face rules with each font subset to the characters it renders."""
    rules = []
    for (family, weight), chars in used.items():
        if not chars:
            continue
        f = TTFont(CACHE / f"{family}-{weight}.ttf")
        opts = Options()
        opts.flavor = "woff2"
        opts.layout_features = ["kern", "liga"]
        sub = Subsetter(opts)
        sub.populate(text=chars)
        sub.subset(f)
        buf = io.BytesIO()
        f.flavor = "woff2"
        f.save(buf)
        b64 = base64.b64encode(buf.getvalue()).decode()
        rules.append(
            f"@font-face{{font-family:'{family}';font-weight:{weight};"
            f"src:url(data:font/woff2;base64,{b64}) format('woff2');}}"
        )
    return "".join(rules)


class Svg:
    """Tiny helper that tracks which glyphs each font needs."""

    def __init__(self, w: int, h: int, title: str):
        self.w, self.h, self.title = w, h, title
        self.parts: list[str] = []
        self.css: list[str] = []
        self.used: dict[tuple[str, int], str] = {}

    def add(self, s: str) -> None:
        self.parts.append(s)

    def text(self, x, y, s, family, weight, size, fill, anchor="start", spacing=0, extra=""):
        font(family, weight)
        self.used[(family, weight)] = self.used.get((family, weight), "") + s
        esc = s.replace("&", "&amp;").replace("<", "&lt;")
        ls = f' letter-spacing="{spacing}"' if spacing else ""
        self.add(
            f'<text x="{x}" y="{y}" font-family="{family}, sans-serif" font-weight="{weight}" '
            f'font-size="{size}" fill="{fill}" text-anchor="{anchor}"{ls} {extra}>{esc}</text>'
        )

    def save(self, name: str) -> None:
        style = font_face(self.used) + "".join(self.css)
        svg = (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}" height="{self.h}" '
            f'viewBox="0 0 {self.w} {self.h}" role="img" aria-label="{self.title}">'
            f"<title>{self.title}</title><style>{style}</style>" + "".join(self.parts) + "</svg>"
        )
        OUT.mkdir(exist_ok=True)
        (OUT / name).write_text(svg, encoding="utf-8")
        print(f"  {name:<28} {len(svg) / 1024:6.1f} KB")


# ---- motifs (ported from js/main.js) ---------------------------------------
def flower(cx, cy, size, petal, center, cls=""):
    s = size / 100
    petals = "".join(
        f'<ellipse cx="50" cy="26" rx="13" ry="22" fill="{petal}" transform="rotate({a} 50 50)"/>'
        for a in range(0, 360, 60)
    )
    c = f' class="{cls}"' if cls else ""
    return (
        f'<g transform="translate({cx - size / 2} {cy - size / 2})"><g{c}>'
        f'<g transform="scale({s})">{petals}<circle cx="50" cy="50" r="13" fill="{center}"/></g>'
        f"</g></g>"
    )


def bee(x, y, scale=1.0, cls="", body=GOLD):
    c = f' class="{cls}"' if cls else ""
    return (
        f'<g transform="translate({x} {y}) scale({scale})"><g{c}>'
        f'<ellipse cx="30" cy="22" rx="12" ry="9" fill="#9FD0F5" opacity=".8"/>'
        f'<ellipse cx="50" cy="22" rx="12" ry="9" fill="#9FD0F5" opacity=".8"/>'
        f'<ellipse cx="40" cy="34" rx="22" ry="15" fill="{body}" stroke="{INK}" stroke-width="2"/>'
        f'<rect x="32" y="21" width="7" height="26" rx="3" fill="{INK}"/>'
        f'<rect x="45" y="23" width="7" height="22" rx="3" fill="{INK}"/>'
        f'<circle cx="62" cy="32" r="3" fill="{INK}"/>'
        f"</g></g>"
    )


def icon(kind, bg, x, y, size=60):
    if kind == "bars":
        shapes = '<rect x="15" y="32" width="7" height="14" rx="3" fill="#fff"/><rect x="26" y="22" width="7" height="24" rx="3" fill="#fff"/><rect x="37" y="27" width="7" height="19" rx="3" fill="#fff"/>'
    elif kind == "db":
        shapes = f'<ellipse cx="30" cy="20" rx="14" ry="5.5" fill="#fff"/><rect x="16" y="20" width="28" height="18" fill="#fff"/><ellipse cx="30" cy="38" rx="14" ry="5.5" fill="#fff"/><ellipse cx="30" cy="28" rx="14" ry="5" fill="{bg}"/>'
    elif kind == "python":
        shapes = '<circle cx="23" cy="24" r="8" fill="#fff"/><circle cx="37" cy="36" r="8" fill="#fff"/><rect x="19" y="20" width="22" height="8" rx="4" fill="#fff"/><rect x="19" y="32" width="22" height="8" rx="4" fill="#fff"/>'
    elif kind == "sheet":
        shapes = f'<rect x="16" y="15" width="28" height="30" rx="5" fill="#fff"/><rect x="20" y="22" width="20" height="3" rx="1.5" fill="{bg}"/><rect x="20" y="29" width="20" height="3" rx="1.5" fill="{bg}"/><rect x="20" y="36" width="12" height="3" rx="1.5" fill="{bg}"/>'
    elif kind == "pie":
        shapes = f'<circle cx="30" cy="30" r="15" fill="#fff"/><path d="M30 30 L30 15 A15 15 0 0 1 45 30 Z" fill="{bg}"/>'
    elif kind == "phone":
        shapes = f'<rect x="20" y="12" width="20" height="36" rx="5" fill="#fff"/><rect x="26" y="42" width="8" height="2.5" rx="1.2" fill="{bg}"/>'
    elif kind == "film":
        shapes = f'<rect x="13" y="18" width="34" height="24" rx="5" fill="#fff"/><path d="M27 24 L36 30 L27 36 Z" fill="{bg}"/>'
    else:  # net
        shapes = '<circle cx="22" cy="24" r="5" fill="#fff"/><circle cx="39" cy="20" r="5" fill="#fff"/><circle cx="34" cy="40" r="5" fill="#fff"/><path d="M22 24 L39 20 M39 20 L34 40 M22 24 L34 40" stroke="#fff" stroke-width="2.5"/>'
    s = size / 60
    return f'<g transform="translate({x} {y}) scale({s})"><rect width="60" height="60" rx="18" fill="{bg}"/>{shapes}</g>'


ANIM = """
@keyframes float{0%,100%{transform:translateY(0) rotate(0)}50%{transform:translateY(-10px) rotate(12deg)}}
@keyframes floatSlow{0%,100%{transform:translateY(0) rotate(-6deg)}50%{transform:translateY(-14px) rotate(8deg)}}
@keyframes buzz{0%{transform:translate(0,0)}25%{transform:translate(26px,-12px)}50%{transform:translate(52px,4px)}75%{transform:translate(22px,-9px)}100%{transform:translate(0,0)}}
@keyframes blink{0%,49%{opacity:1}50%,100%{opacity:0}}
.f1{transform-box:fill-box;transform-origin:center;animation:float 6s ease-in-out infinite}
.f2{transform-box:fill-box;transform-origin:center;animation:floatSlow 7.5s ease-in-out infinite}
.f3{transform-box:fill-box;transform-origin:center;animation:float 6.5s ease-in-out infinite .8s}
.bee{animation:buzz 9s ease-in-out infinite}
.cursor{animation:blink 1.1s step-end infinite}
@media (prefers-reduced-motion:reduce){.f1,.f2,.f3,.bee,.cursor{animation:none}}
"""


# ---- banner ---------------------------------------------------------------
def banner():
    W, H = 1000, 340
    s = Svg(W, H, "Hi! I'm Ana. Data Analyst and Scientist.")
    s.css.append(ANIM)
    s.add(f'<defs><clipPath id="r"><rect width="{W}" height="{H}" rx="28"/></clipPath></defs>')
    s.add('<g clip-path="url(#r)">')
    s.add(f'<rect width="{W}" height="{H}" fill="{YELLOW}"/>')
    s.add(f'<rect width="{W}" height="12" fill="{PURPLE}"/>')
    s.add(f'<rect y="12" width="{W}" height="16" fill="{PINK}"/>')
    # wave at the bottom, like the welcome -> about seam on the site
    s.add(
        f'<path d="M0 290 C 140 250, 260 330, 420 296 S 700 250, 820 292 S 960 310, 1000 280 '
        f'L1000 340 L0 340 Z" fill="{PINK_PALE}"/>'
    )
    s.add(flower(92, 112, 78, PINK, GOLD, "f2"))
    s.add(flower(905, 150, 62, PURPLE_PALE, "#FFF6E0", "f1"))
    s.add(flower(160, 250, 40, BLUE_PALE, "#FFFFFF", "f3"))
    s.add(flower(840, 66, 34, "#BEE55C", "#FFF9B0", "f3"))
    s.add(bee(700, 228, 0.8, "bee"))

    s.text(W / 2, 102, "DATA ANALYST & SCIENTIST", "Quicksand", 700, 15, PINK_DEEP, "middle", 3.5)
    s.text(W / 2, 180, "Hi! I'm Ana", "Fredoka", 700, 74, INK, "middle")
    heart_x = W / 2 + text_width("Hi! I'm Ana", "Fredoka", 700, 74) / 2 + 14
    s.add(
        f'<path transform="translate({heart_x} 130) scale(1.7)" d="M12 21s-7.5-4.6-10-9.3C.3 8.5 2 4 6 4c2.4 0 4 1.5 6 3.6C14 5.5 15.6 4 18 4c4 0 5.7 4.5 4 7.7C19.5 16.4 12 21 12 21z" fill="{PINK}"/>'
    )
    # little terminal-ish pill
    pill = "> python analyse.py --make-it-colourful"
    pw = text_width(pill, "Quicksand", 700, 13) + 44
    s.add(f'<rect x="{W / 2 - pw / 2}" y="214" width="{pw}" height="30" rx="15" fill="{INK}"/>')
    s.text(W / 2 - pw / 2 + 18, 234, pill, "Quicksand", 700, 13, YELLOW)
    s.add(f'<rect class="cursor" x="{W / 2 + pw / 2 - 22}" y="222" width="7" height="14" rx="1.5" fill="{PINK}"/>')
    s.add("</g>")
    s.save("banner.svg")


# ---- skills ---------------------------------------------------------------
SKILLS = [
    ("Python", "pandas, NumPy, matplotlib. My default place to think.", "Daily", "python", PINK),
    ("SQL", "Joins, window functions and queries that finish before lunch.", "Daily", "db", PURPLE),
    ("Power BI & Tableau", "Dashboards stakeholders can actually navigate alone.", "Confident", "bars", "#4FA8E0"),
    ("Statistics", "A/B tests, regression, and knowing when not to trust a p-value.", "Confident", "pie", "#F5A03C"),
    ("Excel", "Pivot tables, Power Query and a worrying love of shortcuts.", "Fluent", "sheet", "#6BC08A"),
    ("Storytelling", "Turning a model into three sentences a manager remembers.", "Favourite", "net", PINK_DEEP),
]


def skills():
    W, pad, gap = 1000, 30, 22
    cols, card_h = 2, 112
    card_w = (W - pad * 2 - gap) / cols
    rows = (len(SKILLS) + cols - 1) // cols
    H = pad * 2 + rows * card_h + (rows - 1) * gap + 8
    s = Svg(W, int(H), "Skills: Python, SQL, Power BI and Tableau, Statistics, Excel, Storytelling")
    s.add(f'<rect width="{W}" height="{H}" rx="28" fill="{BLUE_PALE}"/>')
    for i, (name, blurb, level, kind, color) in enumerate(SKILLS):
        x = pad + (i % cols) * (card_w + gap)
        y = pad + (i // cols) * (card_h + gap)
        s.add(f'<rect x="{x}" y="{y + 7}" width="{card_w}" height="{card_h}" rx="24" fill="#28507A" opacity=".16"/>')
        s.add(f'<rect x="{x}" y="{y}" width="{card_w}" height="{card_h}" rx="24" fill="{CARD}"/>')
        s.add(icon(kind, color, x + 22, y + 26, 60))
        tx = x + 102
        s.text(tx, y + 44, name, "Fredoka", 700, 22, INK)
        lw = text_width(level, "Quicksand", 700, 12) + 22
        s.add(f'<rect x="{x + card_w - lw - 20}" y="{y + 24}" width="{lw}" height="26" rx="13" fill="{YELLOW}"/>')
        s.text(x + card_w - lw / 2 - 20, y + 41.5, level, "Quicksand", 700, 12, "#9A6A1E", "middle")
        for j, line in enumerate(wrap(blurb, "Quicksand", 500, 15, card_w - 126)):
            s.text(tx, y + 70 + j * 20, line, "Quicksand", 500, 15, INK_SOFT)
    s.save("skills.svg")


# ---- project cards ----------------------------------------------------------
PROJECTS = [
    ("nyc-airbnb", "NYC Airbnb Analysis",
     "Exploratory analysis of NYC Airbnb data. Hosts running 10+ listings get 3x fewer reviews and sit idle nearly 3x longer.",
     ["Python", "SQLite", "Power BI"], "bars", PINK),
    ("chocolate-sales", "Chocolate Sales",
     "Python data prep plus an executive Tableau dashboard on revenue, product efficiency and regional sales.",
     ["Python", "Tableau"], "pie", "#F5A03C"),
    ("sweet-cost", "Sweet Cost",
     "Mobile app that helps pastry shops price their products: ingredients, labour, packaging and fixed costs.",
     ["TypeScript", "JavaScript"], "phone", PURPLE),
    ("reel-rate", "ReelRate",
     "A web app for movie lovers to browse a film catalogue, rate titles and leave reviews for the community.",
     ["TypeScript", "JavaScript"], "film", "#4FA8E0"),
]


def project_card(slug, title, blurb, tags, kind, color):
    W, H = 480, 268
    s = Svg(W, H, f"{title}: {blurb}")
    s.add(f'<rect width="{W}" height="{H}" rx="28" fill="{PURPLE_PALE}"/>')
    x, y, w, h = 20, 18, W - 40, H - 48
    s.add(f'<rect x="{x}" y="{y + 10}" width="{w}" height="{h}" rx="22" fill="#5A3282" opacity=".22"/>')
    s.add(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="22" fill="#FFFFFF"/>')
    s.add(icon(kind, color, x + 22, y + 22, 52))
    s.add(f'<circle cx="{x + 92}" cy="{y + 41}" r="6" fill="{PINK}"/>')
    s.text(x + 106, y + 49, title, "Fredoka", 700, 24, INK)
    s.text(x + w - 22, y + 49, "→", "Quicksand", 700, 22, PINK_DEEP, "end")
    for j, line in enumerate(wrap(blurb, "Quicksand", 500, 15, w - 44)):
        s.text(x + 22, y + 104 + j * 21, line, "Quicksand", 500, 15, INK_SOFT)
    tx = x + 22
    for t in tags:
        tw = text_width(t, "Quicksand", 700, 12) + 24
        s.add(f'<rect x="{tx}" y="{y + h - 44}" width="{tw}" height="26" rx="13" fill="{YELLOW}"/>')
        s.text(tx + tw / 2, y + h - 26.5, t, "Quicksand", 700, 12, "#9A6A1E", "middle")
        tx += tw + 8
    s.save(f"project-{slug}.svg")


# ---- footer -----------------------------------------------------------------
def footer():
    W, H = 1000, 100
    s = Svg(W, H, "Made with too many colours")
    s.css.append(ANIM)
    s.add(f'<rect width="{W}" height="{H}" rx="28" fill="{YELLOW}"/>')
    pairs =[("#A8D8FF", "#FFFFFF"), ("#BEE55C", "#FFF9B0"), ("#FFE066", "#FF9EB5"),
             ("#ED82FF", "#FFF3D0"), (PINK, GOLD), ("#9AC8EB", "#FFFFFF"),
             ("#F6E4B9", "#ED82FF"), ("#B8D555", "#FFFFFF"), ("#FFE066", PINK)]
    sizes = [36, 52, 40, 46, 0, 40, 54, 42, 34]
    xs = [60, 140, 215, 290, 0, 710, 785, 860, 940]
    for i, ((p, c), sz, x) in enumerate(zip(pairs, sizes, xs)):
        if i == 4:
            continue  # gap for the text
        s.add(flower(x, 50, sz, p, c, ["f1", "f2", "f3"][i % 3]))
    s.text(W / 2, 46, "made with too many colours", "Fredoka", 700, 20, PINK_DEEP, "middle")
    s.text(W / 2, 70, "anxmarks.com.br", "Quicksand", 700, 14, PURPLE, "middle", 1.5)
    s.add(bee(640, 36, 0.5, "bee"))
    s.save("footer.svg")


if __name__ == "__main__":
    print("building assets/")
    banner()
    skills()
    for p in PROJECTS:
        project_card(*p)
    footer()
