#!/usr/bin/env python3
"""Draw sketchbook pictures (white grid paper, black pen, pencil, marker washes) for any channel.

  python3 sketch.py POST.json --out OUT --format ig-portrait        # every slide, Instagram 4:5
  python3 sketch.py POST.json --out OUT --format inline             # X images 1600x900 (+ x-cover.png from slide 1)
  python3 sketch.py POST.json --out OUT --format blog-inline --theme both   # blog pictures, light + dark (+ blog-cover.png)
  python3 sketch.py POST.json --check                                # word counts and rule warnings, draws nothing
  python3 sketch.py --list                                           # the 30 pictures and the idea each one fits
  python3 sketch.py --sampler OUT [--format ig-square]               # one sample of each of the 30

POST.json: {"slides": [{"hero": {"type": "hub", ...}, "title": "...", "sub": "...", "note": "...", "alt": "..."}]}
Title marks: ==highlighter== (one phrase per picture), **colored pen**, ~~crossed out~~.
Needs: Python 3 and Chrome/Chromium (CHROME=/path, or found automatically). Fonts are bundled; no internet needed.
"""
import argparse, glob, html, json, math, os, re, shutil, subprocess, sys, tempfile, zlib
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from pen import Pen, mark  # noqa: E402
from rough import Rough  # noqa: E402
import pictures as PX  # noqa: E402
import icons as IC  # noqa: E402
import brand as BR  # noqa: E402  (your name, colors and paper: ../brand.json)

# name: (width, height). Each is the size the app shows best.
FORMATS = {
    "ig-portrait": (1080, 1350), "ig-tall": (1080, 1440), "ig-square": (1080, 1080), "ig-story": (1080, 1920),
    "li-portrait": (1080, 1350), "li-square": (1080, 1080), "li-cover": (1920, 1080),
    "inline": (1600, 900), "x-cover": (2000, 800), "x-portrait": (1080, 1350),
    "blog-inline": (1600, 900), "blog-square": (1080, 1080), "blog-cover": (1200, 630), "nl-inline": (1200, 1200),
}
PLATFORM = {"ig-portrait": "instagram", "ig-tall": "instagram", "ig-square": "instagram", "ig-story": "instagram",
            "li-portrait": "linkedin", "li-square": "linkedin", "li-cover": "linkedin", "inline": "x", "x-cover": "x", "x-portrait": "x",
            "blog-inline": "blog", "blog-square": "blog", "blog-cover": "blog", "nl-inline": "newsletter"}
BRAND = BR.load()
HANDLES = BR.handles(BRAND)          # from brand.json; a post can add its own "handles"
COVER_OF = {"inline": "x-cover", "blog-inline": "blog-cover"}       # these also make a cover from slide 1
NO_SWIPE = ("inline", "x-cover", "x-portrait", "li-cover", "blog-inline", "blog-square", "blog-cover", "nl-inline", "ig-story")
WORDS_MAX = {"instagram": 40, "linkedin": 35, "x": 40, "blog": 40, "newsletter": 15}


def chrome():
    c = os.environ.get("CHROME")
    if c:
        return c
    for p in ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"] + sorted(glob.glob("/opt/pw-browsers/chromium-*/chrome-linux*/chrome")):
        if os.path.exists(p):
            return p
    for n in ("google-chrome", "chromium", "chromium-browser"):
        if shutil.which(n):
            return shutil.which(n)
    sys.exit("Chrome not found. Set CHROME=/path/to/chrome")


def plain(s):
    return re.sub(r"==|\*\*|~~", "", str(s or ""))


def est_lines(text, fs, width, k=0.52):
    return max(1, math.ceil(len(plain(text)) * k * fs * 1.1 / max(width, 1)))


def words_in(x):
    if isinstance(x, str):
        return len(plain(x).split())
    if isinstance(x, list):
        return sum(words_in(i) for i in x)
    if isinstance(x, dict):
        return sum(words_in(v) for k, v in x.items() if k not in ("type", "dir", "shape", "pick", "at", "good", "ok", "dots", "main", "label_at", "pencil", "checks", "depth", "heavier", "unit", "icon", "icons"))
    return 0


def check(post, fmt):
    """Warnings from the research rules. Returns a list of plain sentences."""
    out = []
    plat = PLATFORM[fmt]
    sl = post["slides"]
    for i, s in enumerate(sl, 1):
        hero = s.get("hero") or {}
        t = PX.ALIASES.get(hero.get("type"), hero.get("type")) if isinstance(hero, dict) else None
        if t not in PX.PICTURES:
            out.append("image %d: no picture, or an unknown one (%r). Every image needs 1 of the 30 pictures." % (i, hero.get("type") if isinstance(hero, dict) else hero))
        n = words_in(s.get("title")) + words_in(s.get("sub")) + words_in(s.get("note")) + words_in(s.get("facts", [])) + words_in(hero)
        if n > WORDS_MAX[plat]:
            out.append("image %d: %d words, the limit for %s is about %d. Cut words or split the idea." % (i, n, plat, WORDS_MAX[plat]))
        marks = len(re.findall(r"==.+?==", str(s.get("title", "")) + str(s.get("sub", ""))))
        if marks > 1:
            out.append("image %d: %d highlighted phrases. Use the yellow highlighter once." % (i, marks))
        if not s.get("alt") and plat != "linkedin":
            out.append("image %d: no alt text." % i)
        if not s.get("job") and i == 1:
            out.append('image 1: no job. Add "job": "save", "send" or "repost" to the post or the slide.') if not post.get("job") else None
        tw = words_in(s.get("title"))
        if i == 1 and len(sl) > 1 and plat in ("instagram", "linkedin") and not 4 <= tw <= 12:
            out.append("image 1 (cover): the headline has %d words. Aim for 6 to 10, as a statement." % tw)
        if "?" in str(s.get("title", "")) and i == 1 and len(sl) > 1:
            out.append("image 1 (cover): the headline is a question. Statements did better.")
        if plat == "blog" and fmt == "blog-cover" and tw > 6:
            out.append("blog cover: %d words in the title. Keep 3 to 6 words on the picture; the full title lives in the page." % tw)
    with_icons = 0
    for i, s in enumerate(sl, 1):
        hero = s.get("hero") if isinstance(s.get("hero"), dict) else {}
        names, asked = PX.icons_of(PX.adapt(dict(hero)))
        for a in asked:
            if not IC.name(a):
                out.append("image %d: no icon called %r. Run sketch.py --icons sheet.png to see them all." % (i, a))
        if any(n in IC.ICONS for n in names if n):
            with_icons += 1
    if len(sl) >= 3 and with_icons > math.ceil(len(sl) / 3):
        out.append("%d of %d images use everyday icons. Keep it to about 1 in 3 (logos of named apps do not count): icons are a sprinkle." % (with_icons, len(sl)))
    if plat in ("instagram", "linkedin") and fmt not in NO_SWIPE and 1 < len(sl) < 5:
        out.append("%d images: carousels with 2 to 4 images do worst. Use 1 image, or 5 and more." % len(sl))
    if plat == "instagram" and fmt not in NO_SWIPE and len(sl) > 1 and not (sl[1].get("title")):
        out.append("image 2 has no headline. Instagram re-shows a carousel from image 2, so it must work as a second cover.")
    bait = re.compile(r"comment (yes|\w+ (for|to get))|like if|tag (a|3|three) friend|share to unlock|you won.t believe", re.I)
    if bait.search(json.dumps(post)):
        out.append("engagement bait found (comment YES / like if / tag a friend...). Remove it: the apps push these posts down.")
    return out


# ---------- small doodles for the page ----------
def margin_doodle(kind, size, seed=1):
    """One faint doodle in the margin (texture only, kept away from the picture)."""
    r = Rough(100 + kind)
    if kind == 0:
        d = [r.ellipse(18, 22, 9, 9, turn=1.1, n=10), r.ellipse(68, 30, 11, 11, turn=1.1, n=10), r.ellipse(38, 70, 10, 10, turn=1.1, n=10),
             r.line(27, 24, 57, 29), r.line(22, 31, 34, 61), r.line(62, 39, 45, 63)]
    elif kind == 1:
        d = [r.arrow([(70, 30), (56, 14), (34, 14), (18, 30), (16, 52), (32, 70), (54, 72), (70, 58)], head=10)]
    elif kind == 2:
        d = [r.rect(8, 6, 44, 22, over=2), r.arrow([(30, 30), (31, 40), (30, 48)], head=7), "M30 50 L52 64 L30 78 L8 64 Z", r.arrow([(54, 64), (66, 63), (80, 64)], head=7)]
    elif kind == 3:
        d = [r.curve([(12 + i * 6.2, 45 + (22 if i % 2 else -22)) for i in range(12)], j=1.5)]
    else:
        d = [r.rect(10, 28, 44, 44, over=2), r.rect(32, 10, 44, 44, over=2), r.line(10, 28, 32, 10), r.line(54, 28, 76, 10), r.line(10, 72, 32, 54), r.line(54, 72, 76, 54)]
    body = "".join('<path d="%s" fill="none" stroke="var(--doodle)" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"/>' % x for x in d)
    return '<svg viewBox="0 0 90 90" width="%d" height="%d">%s</svg>' % (size, size, body)


def arrow_svg(w, h, seed=9, cls="dp"):
    r = Rough(seed)
    return '<svg viewBox="0 0 56 32" width="%d" height="%d"><path class="%s" style="stroke-width:3.4" d="%s"/></svg>' % (
        w, h, cls, r.arrow([(4, 17), (26, 15), (50, 16)], head=13, j=0.8))


def down_arrow_svg(s, seed=8):
    r = Rough(seed)
    return '<svg viewBox="0 0 40 46" width="%d" height="%d"><path class="dt" style="stroke-width:3.4" d="%s"/></svg>' % (
        s * 0.87, s, r.arrow([(8, 4), (10, 22), (26, 38)], head=11))


FIT_JS = """
async function go(){
  try{await document.fonts.ready}catch(e){}
  document.querySelectorAll('.head').forEach(h=>{const t=h.querySelector('h1');if(!t)return;let fs=parseFloat(getComputedStyle(t).fontSize),n=0;
    while(h.scrollHeight>h.clientHeight+2&&n<40){fs*=.97;t.style.fontSize=fs+'px';n++}});
  document.querySelectorAll('.t').forEach(t=>{const s=t.querySelector(':scope>span');if(!s)return;const min=parseFloat(t.dataset.min||0);
    let fs=parseFloat(t.style.fontSize),n=0;
    const ic=t.querySelector(':scope>svg.ic'),col=t.style.flexDirection==='column';      // a small icon beside (or above) the words
    const isz=ic?parseFloat(ic.getAttribute('height'))+parseFloat(t.style.gap||0):0,ih=col?isz:0,iw=ic&&!col?isz:0;
    const fits=()=>!(s.offsetHeight+ih>t.clientHeight+1||(iw?s.offsetWidth+iw:s.scrollWidth)>t.clientWidth+1);
    while(!fits()&&fs>min&&n<60){fs=Math.max(min,fs*.96);t.style.fontSize=fs+'px';n++}
    while(!fits()&&fs>min*.8&&n<90){fs*=.97;t.style.fontSize=fs+'px';n++}   // last resort: a bit smaller beats words running over each other
    if(s.offsetHeight+ih>t.clientHeight+6||(iw?s.offsetWidth+iw:s.scrollWidth)>t.clientWidth+6)t.dataset.over='1'});
  // center the drawing in its space (measured from what was really drawn, words included)
  document.querySelectorAll('svg.art').forEach(v=>{const g=v.querySelector('.fitg');if(!g)return;g.removeAttribute('transform');
    let a=1e9,b=1e9,c=-1e9,d=-1e9;
    g.querySelectorAll('path,polygon,rect,ellipse,circle,.t span').forEach(e=>{if(e.closest('clipPath')||e.hasAttribute('clip-path'))return;
      const r=e.getBoundingClientRect();if(r.width<1&&r.height<1)return;a=Math.min(a,r.left);b=Math.min(b,r.top);c=Math.max(c,r.right);d=Math.max(d,r.bottom)});
    if(c<a)return;const z=v.getBoundingClientRect();
    const dx=(z.left+z.right)/2-(a+c)/2,dy=(z.top+z.bottom)/2-(b+d)/2;
    g.setAttribute('transform','translate('+dx.toFixed(1)+' '+dy.toFixed(1)+')')});
}
go();setTimeout(go,600);
"""


def build(post, sl, fmt, idx, n, theme="light"):
    W, H = FORMATS[fmt]
    wide = W / H > 1.3
    story = fmt == "ig-story"
    plat = PLATFORM[fmt]
    blog = plat == "blog"
    # u = one "pen unit". Wide pictures are shown small in a feed or a blog column, so their pen is bigger.
    u = H / 620 if wide else W / 1080 * (1.12 if fmt == "nl-inline" else 1.0)   # email shows pictures at half size: bigger pen
    pad = (52 if wide else 76) * u
    swipe = fmt not in NO_SWIPE and n > 1                      # a carousel: next / page number / last-image footer
    cover = idx == 1 and (swipe or fmt in ("x-cover", "blog-cover", "li-cover"))
    last = idx == n
    hs = dict(HANDLES, **post.get("handles", {}))
    title, sub, kick, note = sl.get("title", ""), sl.get("sub", ""), sl.get("kicker", ""), sl.get("note", "")
    facts = sl.get("facts", [])[:2]
    seed = zlib.crc32(("%s-%d" % (json.dumps(sl.get("hero", ""), sort_keys=True), idx)).encode()) % 9973 + 1
    parts = []
    logo_fs = (40 if wide else 60) * u
    inner = BR.corner(BRAND, hs[plat], theme)
    logo = lambda pos: ('<div class="logo" style="%s;font-size:%.1fpx">%s</div>' % (pos, logo_fs, inner)) if inner else ""

    if wide:
        colw = W * 0.34 - pad
        top = pad * 0.8
        if blog:  # blog pictures: logo + site name bottom right
            parts.append(logo("right:%.1fpx;bottom:%.1fpx" % (pad, pad * 0.55)))
            hy, hh = top, H - 2 * top
            ax, ay = W * 0.37, top
            aw, ah = W - pad - ax, H - top - ay - logo_fs * 1.5
        else:
            parts.append(logo("left:%.1fpx;top:%.1fpx" % (pad, top)))
            hy, hh = top + logo_fs * 1.4, H - top * 2 - logo_fs * 1.4
            ax, ay = W * 0.37, top
            aw, ah = W - pad - ax, H - 2 * top
        tfs = (58 if cover else 52) * u
        lines = est_lines(title, tfs, colw)
        if lines > 5:
            tfs *= math.sqrt(5 / lines)
        sfs, kfs, nfs = 30 * u, 36 * u, 36 * u
        head_style = "left:%.1fpx;top:%.1fpx;width:%.1fpx;height:%.1fpx" % (pad, hy, colw, hh)
    else:
        top = 270 if story else 0
        bottom = 380 if story else 0
        if blog:  # blog pictures: logo + site name bottom right, also on the phone-size square
            parts.append(logo("right:%.1fpx;bottom:%.1fpx" % (pad, 40 * u)))
        else:
            parts.append(logo("left:%.1fpx;top:%.1fpx" % (pad, top + 44 * u)))
        colw = W - 2 * pad
        tfs = (96 if cover else 78) * u
        lines = est_lines(title, tfs, colw)
        if lines > 3:
            tfs *= math.sqrt(3 / lines)
            lines = est_lines(title, tfs, colw)
        sfs, kfs, nfs = 38 * u, 46 * u, 46 * u
        hy = top + 60 * u if blog else top + 44 * u + logo_fs + 34 * u
        hh = lines * tfs * 1.12 + (kfs * 1.35 if kick else 0) + (est_lines(sub, sfs, colw, 0.47) * sfs * 1.38 + sfs * 0.45 if sub else 0) + (nfs * 1.7 if note else 0)
        head_style = "left:%.1fpx;top:%.1fpx;width:%.1fpx;height:%.1fpx" % (pad, hy, colw, hh)
        foot = 104 * u if swipe else (logo_fs * 1.25 + 30 * u if blog else 30 * u)
        fh = 176 * u if facts else 0
        ax, ay = pad, hy + hh + 30 * u
        if cover and sl.get("pencil", True):
            rw_ = colw - 150 * u
            rp = Pen(colw, 60 * u, u=u, seed=seed + 3)
            rp.line(0, 30 * u, rw_, 28 * u, j=0.9)
            rp.pencil(rw_ + 4 * u, 28 * u, length=200, angle=-24)
            parts.append('<svg class="rule" style="left:%.1fpx;top:%.1fpx" width="%.1f" height="%.1f" viewBox="0 0 %.1f %.1f">%s</svg>' % (pad, ay - 6 * u, colw, 60 * u, colw, 60 * u, rp.svg()))
            ay += 64 * u
        aw, ah = W - 2 * pad, H - bottom - foot - fh - ay - 26 * u
        if facts:
            cards = "".join('<div class="fact%s" style="font-size:%.1fpx"><b style="font-size:%.1fpx">%s</b>%s</div>' % (
                " hl" if f.get("hl") else "", 36 * u, 38 * u, mark(f.get("label", "")), mark(f.get("text", ""))) for f in facts)
            parts.append('<div class="facts" style="left:%.1fpx;top:%.1fpx;width:%.1fpx;height:%.1fpx">%s</div>' % (pad, ay + ah + 22 * u, aw, fh - 30 * u, cards))
        fy = H - bottom - 76 * u
        if swipe and not last:
            nxt = sl.get("next")
            parts.append('<div class="next" style="left:%.1fpx;top:%.1fpx;font-size:%.1fpx">%s%s</div>' % (
                pad, fy - 4 * u, 44 * u, ("<b>next:</b> %s" % mark(nxt)) if nxt else "swipe", arrow_svg(56 * u, 32 * u, seed)))
        if swipe:
            parts.append('<div class="pager" style="right:%.1fpx;top:%.1fpx;font-size:%.1fpx">%d / %d</div>' % (pad, fy - 4 * u, 44 * u, idx, n))
        more = post.get("more", hs["blog"])
        if last and swipe and more:
            # last image: one place to find more (the app's own handle already sits by the logo)
            parts.append('<div class="follow" style="left:%.1fpx;top:%.1fpx;font-size:%.1fpx;gap:%.1fpx"><b style="font-size:%.1fpx">%s</b><span>%s</span></div>' % (
                pad, fy - 4 * u, 34 * u, 14 * u, 44 * u, html.escape(post.get("more_label", "more at")), html.escape(more)))

    hd = ""
    if kick:
        hd += '<div class="kick" style="font-size:%.1fpx">%s</div>' % (kfs, mark(kick))
    hd += '<h1 style="font-size:%.1fpx">%s</h1>' % (tfs, mark(title))
    if sub:
        hd += '<p class="sub" style="font-size:%.1fpx">%s</p>' % (sfs, mark(sub))
    if note:
        hd += '<div class="note" style="font-size:%.1fpx">%s<span>%s</span></div>' % (nfs, down_arrow_svg(nfs * 1.1, seed), mark(note))
    parts.append('<div class="head" style="%s">%s</div>' % (head_style, hd))

    hero = sl.get("hero") or {}
    if isinstance(hero, str):
        hero = {"type": hero}
    hero = PX.adapt(hero)
    pic = PX.PICTURES.get(hero.get("type"))
    if not pic:
        sys.exit("image %d: unknown picture %r. Run sketch.py --list for the 30." % (idx, hero.get("type")))
    ua = min(u, aw / 720)      # the picture's own pen: big enough to read in a feed, never so big that the drawing gets cramped
    P = Pen(aw, ah, u=ua, seed=seed)
    if fmt == "nl-inline":
        P.small = max(P.small, 48)      # email: no lettering under 48px on the 1200px picture
    pic["fn"](P, hero)
    parts.append('<svg class="art" style="left:%.1fpx;top:%.1fpx;--u:%.4f" width="%.1f" height="%.1f" viewBox="0 0 %.1f %.1f"><g class="fitg">%s</g></svg>' % (ax, ay, ua, aw, ah, aw, ah, P.svg()))

    css = open(os.path.join(HERE, "sketch.css")).read().replace("FONTDIR", "file://" + os.path.join(HERE, "fonts")) + "\n" + BR.css(BRAND)
    cls = " ".join(filter(None, ["wide" if wide else "tall", "fmt-" + fmt, "dark" if theme == "dark" else "", {"soft": "sage"}.get(post.get("paper", ""), post.get("paper", "")) if theme != "dark" else ""]))
    edge = '<div style="position:absolute;inset:0;border:%.1fpx solid var(--doodle);pointer-events:none"></div>' % (3 * u)
    return ('<!doctype html><html><head><meta charset="utf-8"><style>%s\nbody{--W:%dpx;--H:%dpx;--u:%.4f}</style></head>'
            '<body class="%s">%s%s<script>%s</script></body></html>') % (css, W, H, u, cls, "".join(parts), edge, FIT_JS)


def icon_sheet(theme="light"):
    """One page with every small icon and logo, named. For the guides and for checking a new icon."""
    import icons as IC
    u = 1.0
    cols, cw, ch, pad = 10, 164, 172, 60
    groups = [("Logos: apps and channels (a named app gets its logo)", list(IC.LOGOS)), ("Everyday icons (next to the word they stand for)", list(IC.ICONS))]
    W = pad * 2 + cols * cw
    H = pad + sum(70 + math.ceil(len(n) / cols) * ch + 20 for _, n in groups) + 20
    P = Pen(W, H, u=u, seed=7)
    y = pad
    for title, names in groups:
        P.text(pad, y, W - 2 * pad, 56, title, cls="serif", size=34, align="left")
        y += 70
        for i, nm in enumerate(names):
            r, c = divmod(i, cols)
            x0, y0 = pad + c * cw, y + r * ch
            P.icon(nm, x0 + cw / 2, y0 + 56, 84)
            P.text(x0 + 2, y0 + 108, cw - 4, 48, nm, cls="hand", size=24)
        y += math.ceil(len(names) / cols) * ch + 20
    css = open(os.path.join(HERE, "sketch.css")).read().replace("FONTDIR", "file://" + os.path.join(HERE, "fonts")) + "\n" + BR.css(BRAND)
    page = ('<!doctype html><html><head><meta charset="utf-8"><style>%s\nbody{--W:%dpx;--H:%dpx;--u:%.4f}</style></head><body class="%s">'
            '<svg class="art" style="left:0;top:0;--u:1.5;position:absolute" width="%d" height="%d" viewBox="0 0 %d %d">%s</svg><script>%s</script></body></html>') % (
        css, W, H, u, "dark" if theme == "dark" else "", W, H, W, H, P.svg(), FIT_JS)
    return page, W, H


def brand_version():
    """The brand version to stamp on every picture: BRAND_VERSION if set, else brand.json "version" (none = no stamp)."""
    return os.environ.get("BRAND_VERSION", "") or str(BRAND.get("version", ""))


def stamp(png):
    """Write the brand version inside the PNG (a hidden text note), so any picture tells which brand drew it."""
    v = brand_version()
    if not v or not os.path.exists(png):
        return
    data = open(png, "rb").read()
    if data[:8] != b"\x89PNG\r\n\x1a\n" or b"tEXtBrand\x00" in data[:200]:
        return
    body = b"tEXt" + b"Brand\x00" + ("sketchbook v" + v).encode()
    chunk = len(body[4:]).to_bytes(4, "big") + body + (zlib.crc32(body) & 0xFFFFFFFF).to_bytes(4, "big")
    open(png, "wb").write(data[:33] + chunk + data[33:])   # right after the PNG header block


def render(html_text, png, W, H):
    os.makedirs(os.path.dirname(png) or ".", exist_ok=True)
    with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False, dir=os.path.dirname(png) or ".") as f:
        f.write(html_text)
        tmp = f.name
    try:
        for _ in range(3):
            try:
                subprocess.run([chrome(), "--headless=new", "--no-sandbox", "--disable-gpu", "--hide-scrollbars", "--force-device-scale-factor=1",
                                "--allow-file-access-from-files", "--virtual-time-budget=4000", "--window-size=%d,%d" % (W, H), "--screenshot=" + png, "file://" + tmp],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=90)
                if os.path.exists(png):
                    stamp(png)
                    break
            except subprocess.TimeoutExpired:
                print("  retry", os.path.relpath(png))
    finally:
        os.unlink(tmp)
    return png


def jobs_for(post, fmt, out, themes, only=None):
    jobs = []
    sl = post["slides"]
    n = len(sl)
    for i, s in enumerate(sl, 1):
        if only and i not in only:
            continue
        hero = s.get("hero") or {}
        t = hero.get("type", "picture") if isinstance(hero, dict) else str(hero)
        for th in themes:
            suf = "-dark" if th == "dark" else ""
            jobs.append((build(post, s, fmt, i, n, th), os.path.join(out, fmt, "%02d-%s%s.png" % (i, t, suf)), *FORMATS[fmt]))
            if i == 1 and fmt in COVER_OF:
                c = COVER_OF[fmt]
                jobs.append((build(post, s, c, 1, n, th), os.path.join(out, "%s%s.png" % (c, suf)), *FORMATS[c]))
    return jobs


def icons_for_web(box=24, pad=1.5):
    """Every logo and icon as plain pen strokes in a small square, for places that are not pictures (a website).
    One drawing, used everywhere: a website can keep a copy of this file instead of redrawing a logo."""
    import icons as IC
    out = {"box": box, "logos": list(IC.LOGOS), "icons": list(IC.ICONS), "names": dict(IC.NAMES), "draw": {}}
    for i, n in enumerate(IC.ALL):
        P = Pen(box, box, u=1.0, seed=40 + i)
        IC.draw(P, n, pad, pad, box - 2 * pad)
        body = "".join(P.b)
        out["draw"][n] = {"paths": re.findall(r'<path class="[^"]*" d="([^"]+)"', body),
                          "dots": [[float(v) for v in m] for m in re.findall(r'<circle class="[^"]*" cx="([\d.]+)" cy="([\d.]+)" r="([\d.]+)"', body)]}
    return out


def sampler_post():
    return {"slides": [dict(hero=dict(v["sample"], type=k), title=v.get("title", k), alt="sample") for k, v in PX.PICTURES.items()]}


def main():
    ap = argparse.ArgumentParser(description="Draw sketchbook pictures.")
    ap.add_argument("post", nargs="?")
    ap.add_argument("--out", default="out")
    ap.add_argument("--format", "--carousel", dest="format", default="ig-portrait", help="one or more of: " + ", ".join(FORMATS))
    ap.add_argument("--theme", choices=["light", "dark", "both"], default="light", help="dark / both = also the night-page version (blog)")
    ap.add_argument("--only", help="only these image numbers, e.g. 1,3")
    ap.add_argument("--check", action="store_true", help="only print rule warnings")
    ap.add_argument("--html-only", action="store_true")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--sampler", metavar="OUT", help="draw one sample of each of the 30 pictures into OUT")
    ap.add_argument("--icons", metavar="OUT.png", help="draw one sheet with every small icon and logo")
    ap.add_argument("--icons-web", metavar="OUT.json", help="write every icon and logo as pen strokes, for a website")
    a = ap.parse_args()
    if a.icons_web:
        json.dump(icons_for_web(), open(a.icons_web, "w"), separators=(",", ":"))
        print("✓", os.path.relpath(a.icons_web))
        return
    if a.icons:
        for th in (["light", "dark"] if a.theme == "both" else [a.theme]):
            out = a.icons if th == "light" or a.theme == "dark" else a.icons[:-4] + "-dark.png"
            print("✓", os.path.relpath(render(*((icon_sheet(th)[0], out) + icon_sheet(th)[1:]))))
        return
    if a.list:
        g = None
        for i, (k, v) in enumerate(PX.PICTURES.items(), 1):
            if v["group"] != g:
                g = v["group"]
                print("\n" + g)
            print("  %2d. %-10s %s" % (i, k, v["shape"]))
        return
    if a.sampler:
        post, a.out = sampler_post(), a.sampler
        for s in post["slides"]:
            s["title"] = PX.PICTURES[s["hero"]["type"]].get("sample_title", s["hero"]["type"])
        post["slides"] = [dict(s, _single=True) for s in post["slides"]]
    else:
        if not a.post:
            ap.error("give a POST.json, or --list / --sampler")
        post = json.load(open(a.post))
    fmts = a.format.split(",")
    for f in fmts:
        if f not in FORMATS:
            ap.error("unknown format %r" % f)
    warn = []
    for f in fmts:
        for w in ([] if a.sampler else check(post, f)):
            if w and w not in warn:
                warn.append(w)
    for w in warn:
        print("! " + w)
    if a.check:
        print("%d warning(s)." % len(warn))
        return
    themes = ["light", "dark"] if a.theme == "both" else [a.theme]
    only = [int(x) for x in a.only.split(",")] if a.only else None
    jobs = []
    for f in fmts:
        if a.sampler:  # each sample is its own single picture
            for i, s in enumerate(post["slides"], 1):
                for th in themes:
                    jobs.append((build(post, s, f, 1, 1, th), os.path.join(a.out, f, "%02d-%s%s.png" % (i, s["hero"]["type"], "-dark" if th == "dark" else "")), *FORMATS[f]))
        else:
            jobs += jobs_for(post, f, a.out, themes, only)
    if a.html_only:
        for h, png, W, H in jobs:
            os.makedirs(os.path.dirname(png), exist_ok=True)
            open(png[:-4] + ".html", "w").write(h)
        print("wrote %d html files" % len(jobs))
        return
    with ThreadPoolExecutor(5) as ex:
        for p in ex.map(lambda j: render(*j), jobs):
            print("✓", os.path.relpath(p))


if __name__ == "__main__":
    main()
