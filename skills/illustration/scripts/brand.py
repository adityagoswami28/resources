"""Your brand, read from ONE file: brand.json (in the skill folder, next to SKILL.md).

Everything that makes the pictures yours lives in that file, so the engine never needs editing:
  corner   what sits in the corner of every picture: "name" (your name and handle), "file" (your logo image), "none"
  colors   "notebook" (cream paper, navy, blue pen, peach), "sea", "ink", or your own 4 colors
  paper    "grid", "dots" or "plain" (and paper_color for your own day paper color)

    python3 brand.py            # prints what brand.json says, in plain words
"""
import html, json, os

HERE = os.path.dirname(os.path.abspath(__file__))
FILE = os.environ.get("BRAND_FILE") or os.path.join(HERE, "..", "brand.json")   # BRAND_FILE=other.json for a second brand

# Each palette is 4 colors. The engine works out every other shade (washes, tape, night paper) from these.
#   soft       the big soft wash behind drawings and on paper tape
#   accent     the ONE pen mark to notice (and the pencil's body)
#   highlight  the highlighter on one phrase, and sticky notes
#   deep       titles, the corner name, the pencil's end
#   paper      optional: the day paper (white when left out)
PALETTES = {
    "notebook":   {"soft": "#F5DECB", "accent": "#2B67B8", "highlight": "#FFE27A", "deep": "#1D3557", "paper": "#FAF6EC"},
    "sea":        {"soft": "#D5E7E4", "accent": "#E8603C", "highlight": "#FFE45C", "deep": "#14393B"},
    "ink":        {"soft": "#E6E6E1", "accent": "#D7263D", "highlight": "#FFE45C", "deep": "#1A1A1A"},
}
PAPERS = ("grid", "dots", "plain")
CORNERS = ("name", "file", "none")
DEFAULT = {"setup_done": False, "name": "", "handle": "", "site": "", "handles": {},
           "corner": "name", "logo_file": "", "logo_file_night": "", "colors": "notebook", "paper": "grid", "paper_color": ""}


def load():
    b = dict(DEFAULT)
    if os.path.exists(FILE):
        b.update(json.load(open(FILE)))
    return b


def handles(b):
    """The name shown by the logo for each app. Instagram, X and LinkedIn use your handle; blog and newsletter your site."""
    own = b.get("handles") or {}
    h, s = b.get("handle", ""), b.get("site", "") or b.get("handle", "")
    return {"instagram": own.get("instagram", h), "x": own.get("x", h), "linkedin": own.get("linkedin", h),
            "blog": own.get("blog", s), "newsletter": own.get("newsletter", s)}


# ---------- the corner ----------
CORNER_CSS = """.logo .bname{font-family:'Gochi Hand',cursive;font-size:.86em;line-height:1;color:var(--logo)}
.logo .bimg{display:block;height:1.12em;width:auto}
.logo .bname + .handle,.logo .bimg + .handle{margin-left:.55em}
.logo .handle:first-child{margin-left:0;font-size:.56em}"""


def corner(b, handle, theme="light"):
    """The inside of the corner logo (HTML), or "" for no logo."""
    kind = b.get("corner", "name")
    if kind == "none":
        return ""
    hd = '<span class="handle">%s</span>' % html.escape(handle) if handle else ""
    if kind == "file":
        f = b.get("logo_file_night") if theme == "dark" and b.get("logo_file_night") else b.get("logo_file", "")
        p = f if os.path.isabs(f) else os.path.normpath(os.path.join(HERE, "..", f))
        if f and os.path.exists(p):
            return '<img class="bimg" alt="" src="file://%s">%s' % (p, hd)
        print("  brand.json: logo_file %r not found, writing the name instead" % f)
    name = b.get("name", "")
    return ('<span class="bname">%s</span>' % html.escape(name) if name else "") + hd


# ---------- colors ----------
def _rgb(h):
    h = h.strip().lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _hex(c):
    return "#%02X%02X%02X" % tuple(max(0, min(255, round(v))) for v in c)


def mix(a, b, t):
    """a moved t of the way toward b (t = 0 gives a, 1 gives b)."""
    A, B = _rgb(a), _rgb(b)
    return _hex([x + (y - x) * t for x, y in zip(A, B)])


def rgba(h, a):
    return "rgba(%d,%d,%d,%s)" % (_rgb(h) + (a,))


def _lum(h):
    def ch(v):
        v /= 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = (ch(v) for v in _rgb(h))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a, b):
    la, lb = sorted((_lum(a), _lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def readable(color, paper, need=4.5, toward="#000000"):
    """The color, darkened (or lightened) just enough to read as text on the paper."""
    for i in range(41):
        c = mix(color, toward, i / 40)
        if contrast(c, paper) >= need:
            return c
    return toward


def _ok(v):
    try:
        _rgb(v)
        return True
    except (ValueError, AttributeError):
        return False


def palette(b):
    c = b.get("colors", "notebook")
    if isinstance(c, dict):     # your own: any color left out (or not a color) stays the notebook one
        p = dict(PALETTES["notebook"])
        p.update({k: v for k, v in c.items() if k in ("soft", "accent", "highlight", "deep", "paper") and v and _ok(v)})
        return p
    return dict(PALETTES.get(c, PALETTES["notebook"]))


def color_css(b):
    """CSS that swaps the default colors for the brand's. Empty for the notebook palette (sketch.css already has it)."""
    p = palette(b)
    if p == PALETTES["notebook"]:
        return ""
    soft, acc, hl, deep = p["soft"], p["accent"], p["highlight"], p["deep"]
    W = "#FFFFFF"
    P = p.get("paper", W)          # the day paper (a palette can bring its own, e.g. cream)
    night = mix("#0E0E0E", deep, 0.25)
    day = {
        "--paper": P, "--scrap": mix(P, W, 0.6), "--grid": mix(soft, W, 0.5) if P == W else mix(P, deep, 0.07),
        "--text": mix("#141414", deep, 0.2), "--muted": readable(mix("#3B3B3B", deep, 0.35), P, 7),
        "--pencil": readable(mix("#444444", deep, 0.3), P, 7), "--head": deep, "--forest": deep, "--logo": deep,
        "--sage": soft, "--sage-deep": mix(soft, deep, 0.15), "--tang": acc, "--tang-ink": readable(acc, P, 4.5), "--hl": hl,
        "--card": mix(soft, P, 0.6), "--doodle": mix(soft, deep, 0.1), "--lift": rgba(deep, ".17"),
        "--tape": rgba(mix(soft, deep, 0.12), ".85"), "--tape2": rgba(hl, ".85"),
        "--wa": mix(soft, deep, 0.06), "--wb": mix(hl, P, 0.3), "--wc": mix(acc, P, 0.62),
    }
    dark = {
        "--paper": night, "--grid": mix(night, soft, 0.04), "--ink": mix(soft, W, 0.55), "--edge": mix(soft, night, 0.6),
        "--draw": mix(soft, night, 0.08), "--text": mix(soft, W, 0.45), "--muted": mix(soft, night, 0.18), "--pencil": mix(soft, night, 0.12),
        "--head": mix(soft, W, 0.4), "--sage": mix(soft, night, 0.88), "--sage-deep": mix(soft, night, 0.72),
        "--tang-ink": readable(mix(acc, W, 0.25), night, 4.5, W), "--scrap": mix(night, soft, 0.04), "--card": mix(night, soft, 0.06),
        "--doodle": mix(night, soft, 0.12), "--tape": rgba(mix(soft, night, 0.5), ".72"), "--tape2": rgba(hl, ".6"),
        "--wa": rgba(mix(soft, night, 0.55), ".5"), "--wb": rgba(hl, ".22"), "--wc": rgba(acc, ".3"), "--logo": mix(soft, W, 0.4),
    }
    css = "body{%s}\nbody.dark{%s}\n" % (";".join("%s:%s" % kv for kv in day.items()), ";".join("%s:%s" % kv for kv in dark.items()))
    if P == W:   # email pictures never sit on pure white
        css += "body.fmt-nl-inline:not(.dark){--paper:%s;--grid:%s}\n" % (mix(soft, W, 0.72), mix(soft, W, 0.42))
    css += "body.sage{--paper:%s;--grid:%s;--card:%s;--wa:%s;--doodle:%s}\n" % (soft, mix(soft, deep, 0.05), mix(soft, W, 0.5), mix(soft, deep, 0.12), mix(soft, deep, 0.15))
    css += ".pc-body{fill:%s} .pc-band{fill:%s} .pc-end{fill:%s}\n" % (acc, mix(soft, deep, 0.15), deep)
    return css


# ---------- paper ----------
def paper_css(b):
    kind = b.get("paper", "grid")
    out = ""
    pc = b.get("paper_color", "")
    try:     # your own day paper color; the night paper stays dark
        out += "body:not(.dark){--paper:%s;--grid:%s;--scrap:%s}\n" % (_hex(_rgb(pc)), mix(pc, palette(b)["deep"], 0.07), mix(pc, "#FFFFFF", 0.5)) if pc else ""
    except ValueError:
        pass     # brand.py prints the problem
    if kind == "plain":
        out += "body{background-image:none}\n"
    if kind == "dots":
        out += ("body{background-image:radial-gradient(circle,var(--doodle) calc(2.4px*var(--u)),transparent calc(2.9px*var(--u)));"
                "background-position:calc(-18px*var(--u)) calc(-18px*var(--u))}\n")
    return out


def css(b):
    """Every brand rule for the page, added after sketch.css."""
    return CORNER_CSS + "\n" + color_css(b) + paper_css(b)


def problems(b):
    """Plain-words problems in brand.json, one per line (empty when all is well)."""
    out = []
    if b.get("corner", "name") not in CORNERS:
        out.append("corner must be one of: %s" % ", ".join(CORNERS))
    if b.get("paper", "grid") not in PAPERS:
        out.append("paper must be one of: %s" % ", ".join(PAPERS))
    c = b.get("colors", "notebook")
    if isinstance(c, str) and c not in PALETTES:
        out.append("colors must be one of: notebook, sea, ink, or your own {soft, accent, highlight, deep, paper}")
    if isinstance(c, dict):
        for k, v in c.items():
            try:
                _rgb(v)
            except Exception:
                out.append("colors.%s is not a color like #1F3A2C: %r" % (k, v))
    if b.get("paper_color"):
        try:
            _rgb(b["paper_color"])
        except Exception:
            out.append("paper_color is not a color like #F7F4EC: %r" % b["paper_color"])
    if b.get("corner") == "file" and not b.get("logo_file"):
        out.append("corner is \"file\" but logo_file is empty")
    if b.get("corner", "name") == "name" and not (b.get("name") or b.get("handle") or b.get("site")):
        out.append("corner is \"name\" but name, handle and site are all empty: the corner will be blank")
    return out


if __name__ == "__main__":
    b = load()
    print("setup done:", "yes" if b.get("setup_done") else "no (the skill asks 3 questions first)")
    print("corner:", b.get("corner"), "|", b.get("name") or "-", "|", ", ".join("%s %s" % kv for kv in handles(b).items() if kv[1]) or "no handles")
    print("colors:", b.get("colors") if isinstance(b.get("colors"), str) else "your own", palette(b))
    print("paper:", b.get("paper"))
    for p in problems(b):
        print("PROBLEM:", p)
