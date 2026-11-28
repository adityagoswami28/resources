"""The pen: hand-drawn building blocks for sketchbook pictures.

Every picture in pictures.py draws with a Pen into a box of w x h pixels.
Lines wobble (rough.py), fills are marker washes that sit a little off the outline,
words are real text (foreignObject) so they wrap and stay sharp.
Colors come from sketch.css classes, never from here, so the light and dark page both work.
"""
import html, math, re
import icons
from rough import Rough


def mark(s):
    """Escape text and turn the small marks into pen marks:
    ==words== highlighter, **words** colored pen, ~~words~~ crossed out."""
    s = html.escape(str(s or ""))
    s = re.sub(r"==(.+?)==", r'<mark>\1</mark>', s)
    s = re.sub(r"\*\*(.+?)\*\*", r'<b class="pen">\1</b>', s)
    s = re.sub(r"~~(.+?)~~", r'<s>\1</s>', s)
    return s


class Pen:
    def __init__(self, w, h, u=1.0, seed=1):
        self.w, self.h, self.u = w, h, u
        self.r = Rough(seed)
        self.b = []
        self.wide = w / h > 1.35
        self.tall = h / w > 1.15
        self.fs = 44 * u          # normal hand label
        self.small = 36 * u       # smallest text allowed (36px on a 1080 slide: still readable on a phone)
        self.big = 56 * u
        self._clip = 0

    # ---- output ----
    def raw(self, s):
        self.b.append(s)

    def svg(self):
        return "".join(self.b)

    def path(self, d, cls="d"):
        self.b.append('<path class="%s" d="%s"/>' % (cls, d))

    def push(self, rot=0, cx=0, cy=0):
        self.b.append('<g transform="rotate(%.2f %.1f %.1f)">' % (rot, cx, cy))

    def pop(self):
        self.b.append("</g>")

    def J(self, k=1.0):
        return 1.5 * self.u * k

    def rnd(self, a, b):
        return self.r.r.uniform(a, b)

    # ---- lines and shapes ----
    def line(self, x1, y1, x2, y2, cls="d", j=1.0, bow=None, over=0):
        self.path(self.r.line(x1, y1, x2, y2, j=self.J(j), bow=bow, over=over, seg=70 * self.u), cls)

    def box(self, x, y, w, h, cls="d", wash=None, j=1.0):
        if wash:
            self.wash_rect(x, y, w, h, wash)
        self.path(self.r.rect(x, y, w, h, j=self.J(j), over=4 * self.u), cls)

    def circle(self, cx, cy, rx, ry=None, cls="d", wash=None, second=True):
        ry = rx if ry is None else ry
        if wash:
            self.wash_ellipse(cx, cy, rx, ry, wash)
        self.path(self.r.ellipse(cx, cy, rx, ry, j=0.012, turn=1.07, n=20, drift=0.03), cls)
        if second:
            self.path(self.r.ellipse(cx + self.u, cy - self.u, rx - 2 * self.u, ry + self.u, j=0.014, turn=0.55, n=20, drift=0.0), cls + " thin")

    def ring(self, cx, cy, rx, ry, cls="dt"):
        """A quick pen circle around something important."""
        self.path(self.r.ellipse(cx, cy, rx, ry, j=0.025, turn=1.17, start=-2.4, n=18, drift=0.09), cls)

    def poly(self, pts, cls="d", wash=None, close=True):
        if wash:
            ox, oy = self.rnd(-6, 6) * self.u, self.rnd(-5, 5) * self.u
            d = "M%.1f %.1f" % (pts[0][0] + ox, pts[0][1] + oy) + "".join("L%.1f %.1f" % (x + ox, y + oy) for x, y in pts[1:]) + "Z"
            self.path(d, "wash " + wash)
        n = len(pts)
        d = ""
        for i in range(n if close else n - 1):
            a, b = pts[i], pts[(i + 1) % n]
            d += self.r.line(a[0], a[1], b[0], b[1], j=self.J(), over=self.rnd(1, 4) * self.u, seg=70 * self.u)
        self.path(d, cls)

    def curve(self, pts, cls="d", j=1.0):
        self.path(self.r.curve(pts, j=self.J(j)), cls)

    def arrow(self, pts, cls="dp", head=None, j=0.8):
        self.path(self.r.arrow(pts, head=head or 15 * self.u, j=self.J(j)), cls)

    def arrow2(self, a, b, cls="dp", bend=0.12, head=None):
        """Arrow from a to b with a soft bend (bend = how far the middle is pushed sideways)."""
        mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
        dx, dy = b[0] - a[0], b[1] - a[1]
        self.arrow([a, (mx - dy * bend, my + dx * bend), b], cls=cls, head=head)

    def wash_rect(self, x, y, w, h, c="wa"):
        u = self.u
        ox, oy = self.rnd(-6, 6) * u, self.rnd(-5, 5) * u
        k = lambda: self.rnd(-3, 3) * u
        pts = [(x + ox + k(), y + oy + k()), (x + w + ox + k(), y + oy + k()), (x + w + ox + k(), y + h + oy + k()), (x + ox + k(), y + h + oy + k())]
        self.path("M%.1f %.1f" % pts[0] + "".join("L%.1f %.1f" % p for p in pts[1:]) + "Z", "wash " + c)

    def wash_ellipse(self, cx, cy, rx, ry, c="wa"):
        u = self.u
        ox, oy = self.rnd(-6, 6) * u, self.rnd(-5, 5) * u
        self.path(self.r.ellipse(cx + ox, cy + oy, rx - 3 * u, ry - 3 * u, j=0.012, turn=1.0, n=18, drift=0.0) + "Z", "wash " + c)

    def hatch(self, x, y, w, h, cls="dp thin", angle=48, gap=None):
        self._clip += 1
        cid = "c%d_%d" % (id(self) % 99999, self._clip)
        self.b.append('<clipPath id="%s"><rect x="%.1f" y="%.1f" width="%.1f" height="%.1f"/></clipPath>' % (cid, x, y, w, h))
        self.b.append('<path class="%s" clip-path="url(#%s)" d="%s"/>' % (cls, cid, self.r.hatch(x, y, w, h, angle=angle, gap=gap or 15 * self.u, j=self.J(0.7))))
        self.b.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="none" stroke="none"/>' % (x, y, w, h))   # its size, for centering

    def tick(self, x, y, s, cls="dtk"):
        self.path(self.r.tick(x, y, s), cls)

    def cross(self, x, y, s, cls="dtk"):
        self.path(self.r.line(x, y, x + s, y + s, j=self.J(0.5), bow=0) + self.r.line(x + s, y, x, y + s, j=self.J(0.5), bow=0), cls)

    def check(self, x, y, s, ok=True):
        """A drawn checkbox with a tick (ok), a cross (False) or nothing (None)."""
        self.path(self.r.rect(x, y, s, s, j=self.J(0.5), over=2 * self.u), "d")
        if ok is True:
            self.tick(x + s * 0.12, y - s * 0.05, s * 0.95)
        elif ok is False:
            self.cross(x + s * 0.18, y + s * 0.18, s * 0.64)

    def underline(self, x, y, w, cls="dp"):
        self.path(self.r.line(x, y, x + w, y - 1 * self.u, j=self.J(0.8), seg=70 * self.u), cls)
        self.path(self.r.line(x + w * 0.18, y + 8 * self.u, x + w * 0.82, y + 7 * self.u, j=self.J(0.7), seg=70 * self.u), cls + " thin")

    def spark(self, x, y, s=26, cls="dt"):
        """Three short lines: 'look here'."""
        for a in (-0.9, -0.35, 0.2):
            self.line(x + math.cos(a) * s * 0.45 * self.u, y + math.sin(a) * s * 0.45 * self.u,
                      x + math.cos(a) * s * self.u, y + math.sin(a) * s * self.u, cls=cls, j=0.3, bow=0)

    def dot(self, cx, cy, r, cls="dotf"):
        self.b.append('<circle class="%s" cx="%.1f" cy="%.1f" r="%.1f"/>' % (cls, cx, cy, r))

    # ---- words ----
    def text(self, x, y, w, h, s, cls="hand", size=None, align="center", valign="center", rot=0, icon=None, icon_pos="left", icon_size=None):
        """Words in a box. icon = a small drawing from icons.py that sits left of the words (or on top: icon_pos="top")."""
        size = size or self.fs
        if "hand" in cls:
            size *= 1.2   # Gochi Hand draws small for its size
        size = max(size, self.small)
        jc = {"center": "center", "left": "flex-start", "right": "flex-end"}[align]
        ai = {"center": "center", "top": "flex-start", "bottom": "flex-end"}[valign]
        tr = ' transform="rotate(%.2f %.1f %.1f)"' % (rot, x + w / 2, y + h / 2) if rot else ""
        ic, extra, one = "", "", ""
        if icon and icons.name(icon):
            top = icon_pos == "top"
            isz = icon_size or (min(h * 0.44, w * 0.5, 104 * self.u) if top else min(h * 0.54, w * 0.26, 66 * self.u))
            q = Pen(isz, isz, u=self.u, seed=self.r.r.randint(1, 9999))
            icons.draw(q, icon, 0, 0, isz)
            ic = '<svg class="ic" width="%.1f" height="%.1f" viewBox="0 0 %.1f %.1f">%s</svg>' % (isz, isz, isz, isz, q.svg())
            extra = ";gap:%.1fpx" % (isz * (0.14 if top else 0.24))
            if top:
                extra += ";flex-direction:column"
                jc, ai = ai, jc
            elif align == "center":
                align = "left"
            if not top and len(re.sub(r"==|\*\*|~~", "", str(s))) <= 10:
                one = ' style="white-space:nowrap"'      # a short label stays on one line beside its icon
        self.b.append('<foreignObject x="%.1f" y="%.1f" width="%.1f" height="%.1f"%s><div class="t %s" data-min="%.1f" style="font-size:%.1fpx;justify-content:%s;align-items:%s;text-align:%s%s">%s<span%s>%s</span></div></foreignObject>'
                      % (x, y, max(w, 1), max(h, 1), tr, cls, self.small * 0.94, size, jc, ai, align, extra, ic, one, mark(s)))

    def icon(self, name, cx, cy, s, cls="di"):
        """A small drawing from icons.py, centered on cx, cy."""
        return icons.draw(self, name, cx - s / 2, cy - s / 2, s, cls)

    def num(self, cx, cy, n, r=None, cls="dt"):
        """A number in a hand-drawn circle (step numbers). Always a round circle."""
        r = r or 30 * self.u
        self.path(self.r.ellipse(cx, cy, r, r, j=0.02, turn=1.1, n=14, drift=0.04), cls)
        self.text(cx - r, cy - r, 2 * r, 2 * r, str(n), cls="hand pen", size=r * 1.25)

    # ---- paper pieces ----
    def paper(self, x, y, w, h, kind="scrap", tilt=0, tape=1, tape2=False):
        """Start a taped-in piece of paper (scrap, card or sticky). Draw on it, then call pop()."""
        u = self.u
        self.push(tilt, x + w / 2, y + h / 2)
        self.b.append('<rect class="lift" x="%.1f" y="%.1f" width="%.1f" height="%.1f"/>' % (x + 8 * u, y + 9 * u, w, h))
        self.b.append('<rect class="pp %s" x="%.1f" y="%.1f" width="%.1f" height="%.1f"/>' % (kind, x, y, w, h))
        if tape:
            self.tape(x + w / 2 if tape == 1 else x + w * 0.2, y, tape2)

    def tape(self, cx, cy, yellow=False, rot=None, tw=None):
        u = self.u
        tw, th = (tw or 130 * u), 34 * u
        rot = self.rnd(-6, 6) if rot is None else rot
        x, y = cx - tw / 2, cy - th / 2
        e = 4 * u
        pts = [(x + e, y), (x + tw - e, y), (x + tw, y + th * .2), (x + tw - e, y + th * .4), (x + tw, y + th * .6), (x + tw - e, y + th * .8), (x + tw, y + th),
               (x + e, y + th), (x, y + th * .8), (x + e, y + th * .6), (x, y + th * .4), (x + e, y + th * .2)]
        self.b.append('<polygon class="tape%s" transform="rotate(%.1f %.1f %.1f)" points="%s"/>'
                      % (" tape2" if yellow else "", rot, cx, cy, " ".join("%.1f,%.1f" % p for p in pts)))

    def pencil(self, x, y, length=240, angle=-28):
        """The pencil (website mascot): tip at x,y, body going up-right. Its colors follow the palette (accent body, deep end)."""
        r = Rough(12)
        k = length * self.u / 176.0
        b = '<polygon points="1,17 11.5,12.6 11.5,21.4" class="pc-tip"/>'
        b += '<polygon points="11.5,12.6 30,5.5 30,28.5 11.5,21.4" class="pc-wood"/>'
        b += '<rect x="30" y="5.5" width="112" height="23" class="pc-body"/>'
        b += '<rect x="142" y="5.5" width="13" height="23" class="pc-band"/>'
        b += '<path d="M155 5.5 H166 Q173 5.5 173 12 V22 Q173 28.5 166 28.5 H155 Z" class="pc-end"/>'
        d = (r.line(11.5, 12.6, 30, 5.5, j=0.3, bow=0) + r.line(11.5, 21.4, 30, 28.5, j=0.3, bow=0) + r.line(11.5, 12.6, 1, 17, j=0.2, bow=0)
             + r.line(11.5, 21.4, 1, 17, j=0.2, bow=0) + r.line(30, 5.5, 166, 5.5, j=0.5, bow=0) + r.line(30, 28.5, 166, 28.5, j=0.5, bow=0)
             + r.line(30, 5.5, 30, 28.5, j=0.3, bow=0) + r.line(142, 5.5, 142, 28.5, j=0.3, bow=0) + r.line(155, 5.5, 155, 28.5, j=0.3, bow=0)
             + "M166 5.5 Q173 5.5 173 12 V22 Q173 28.5 166 28.5")
        b += '<path class="pc-line" d="%s"/>' % d
        b += '<path class="pc-line thin" d="%s"/>' % (r.line(34, 13.2, 139, 13.2, j=0.4, bow=0) + r.line(34, 21, 139, 21, j=0.4, bow=0))
        self.b.append('<g transform="translate(%.1f %.1f) rotate(%.1f) scale(%.3f) translate(-1 -17)">%s</g>' % (x, y, angle, k, b))


# ---- small geometry helpers ----
def rect_edge(cx, cy, w, h, tx, ty, pad=0):
    """Point on the edge of a box (center cx,cy) on the way to tx,ty."""
    dx, dy = tx - cx, ty - cy
    if dx == 0 and dy == 0:
        return cx, cy
    hw, hh = w / 2 + pad, h / 2 + pad
    k = min(hw / abs(dx) if dx else 1e9, hh / abs(dy) if dy else 1e9)
    return cx + dx * k, cy + dy * k


def ell_edge(cx, cy, rx, ry, tx, ty, pad=0):
    a = math.atan2((ty - cy) / (ry or 1), (tx - cx) / (rx or 1))
    return cx + math.cos(a) * (rx + pad), cy + math.sin(a) * (ry + pad)
