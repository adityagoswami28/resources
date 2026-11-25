"""Paper-shape kit: a Piece is a sheet of card described as vector shapes.
The same shapes are painted by every art style (see styles.py)."""
import math
import numpy as np
import skia
from core import PW, PH, RES, GRES

# colours that every art style knows how to paint
MATS = ['paper', 'ink', 'moon', 'mare', 'rockA', 'rockB', 'rockC', 'leafA', 'leafB', 'leafC', 'trunk', 'water', 'foam',
        'stone', 'stoneD', 'lantern', 'robe1', 'robe2', 'robe3', 'skin', 'hat', 'fur', 'toucan', 'bib', 'beak', 'heron',
        'heronD', 'canoe', 'rope', 'plank', 'bank', 'grass', 'board', 'cover', 'gold', 'tab']
# plain-word names for the same colours
ALIAS = dict(sun='moon', sunspot='mare', rock='rockB', rockFar='rockA', rockNear='rockC', leaf='leafB', leafLight='leafA',
             leafDark='leafC', wood='trunk', woodLight='plank', sand='bank', red='robe1', yellow='robe2', pink='robe3',
             orange='beak', cream='bib', white='heron', navy='toucan', brown='fur', slate='heronD', glow='lantern',
             darkRed='canoe', maroon='stoneD', meadow='grass', tan='stone', straw='hat', black='ink')


def norm_mat(m):
    """Named colour, plain-word alias, or '#rrggbb'."""
    m = ALIAS.get(m, m)
    if m in MATS:
        return m
    if isinstance(m, str) and m.startswith('#') and len(m) == 7:
        int(m[1:], 16)
        return m.lower()
    raise ValueError('unknown colour %r (use a named colour or #rrggbb)' % (m,))


def hex_rgb(m):
    return (int(m[1:3], 16), int(m[3:5], 16), int(m[5:7], 16))


class S:
    __slots__ = ('path', 'mat', 'kind', 'clip', 'tone', 'w')

    def __init__(self, path, mat, kind, clip=None, tone=0.0, w=0.0):
        self.path, self.mat, self.kind, self.clip, self.tone, self.w = path, mat, kind, clip, tone, w


class Piece:
    def __init__(self, name, bbox, y0=0.0, alpha=70.0, side='both', res=RES, lock=0, depth=0.5):
        self.name, self.bbox, self.y0, self.alpha, self.side, self.res = name, bbox, y0, alpha, side, res
        self.lock = lock          # order in which it snaps upright
        self.depth = depth        # 0 far .. 1 near (used for tinting)
        self.shapes, self.anchors, self.flows = [], {}, []
        self.slider = None        # dict(x0, x1, y) for a piece that slides in a slot
        self.flow_axis = None     # centre line of the water, for effects that travel along it

    @property
    def size(self):
        u0, v0, u1, v1 = self.bbox
        return int(round((u1 - u0) * self.res)), int(round((v1 - v0) * self.res))

    def fill(self, path, mat, tone=0.0, clip=None):
        self.shapes.append(S(path, norm_mat(mat), 'fill', clip, tone))
        return path

    def shade(self, path, mat, clip):
        self.shapes.append(S(path, norm_mat(mat), 'shade', clip))

    def hi(self, path, mat, clip=None):
        self.shapes.append(S(path, norm_mat(mat), 'hi', clip))

    def line(self, path, w=0.0020, mat='ink', clip=None):
        self.shapes.append(S(path, norm_mat(mat), 'line', clip, 0.0, w))

    def strip(self, path, mat, w, tone=0.0, cap=skia.Paint.kRound_Cap):
        pa = skia.Paint(Style=skia.Paint.kStroke_Style, StrokeWidth=w, StrokeCap=cap,
                        StrokeJoin=skia.Paint.kRound_Join)
        dst = skia.Path()
        pa.getFillPath(path, dst)
        return self.fill(dst, mat, tone)


# ----------------------------------------------------------------- path helpers
def spline(pts, closed=False, path=None, start=True):
    pts = [np.array(p, float) for p in pts]
    n = len(pts)
    path = path if path is not None else skia.Path()

    def pt(i):
        return pts[i % n] if closed else pts[min(max(i, 0), n - 1)]
    if start:
        path.moveTo(*pts[0])
    else:
        path.lineTo(*pts[0])
    for i in range(n if closed else n - 1):
        p0, p1, p2, p3 = pt(i - 1), pt(i), pt(i + 1), pt(i + 2)
        c1 = p1 + (p2 - p0) / 6
        c2 = p2 - (p3 - p1) / 6
        path.cubicTo(c1[0], c1[1], c2[0], c2[1], p2[0], p2[1])
    if closed:
        path.close()
    return path


def poly(pts, closed=True):
    p = skia.Path()
    p.moveTo(*pts[0])
    for q in pts[1:]:
        p.lineTo(*q)
    if closed:
        p.close()
    return p


def circle(cx, cy, r):
    p = skia.Path()
    p.addCircle(cx, cy, r)
    return p


def oval(cx, cy, rx, ry, rot=0.0):
    p = skia.Path()
    p.addOval(skia.Rect.MakeLTRB(cx - rx, cy - ry, cx + rx, cy + ry))
    if rot:
        m = skia.Matrix()
        m.setRotate(rot, cx, cy)
        p.transform(m)
    return p


def rrect(x0, y0, x1, y1, r):
    p = skia.Path()
    p.addRoundRect(skia.Rect.MakeLTRB(x0, y0, x1, y1), r, r)
    return p


def blob(cx, cy, rx, ry, rng, n=9, jit=0.16):
    pts = []
    for i in range(n):
        a = 2 * math.pi * i / n
        k = 1 + rng.uniform(-jit, jit)
        pts.append((cx + rx * k * math.cos(a), cy + ry * k * math.sin(a)))
    return spline(pts, closed=True)


def scallop(cx, cy, rx, ry, lobes, rng, depth=0.32, jit=0.12):
    """Cloud / foliage outline made of rounded lobes."""
    pts = []
    for i in range(lobes):
        a = 2 * math.pi * (i + rng.uniform(-0.18, 0.18)) / lobes
        k = 1 + rng.uniform(-jit, jit)
        pts.append((a, cx + rx * k * math.cos(a), cy + ry * k * math.sin(a)))
    p = skia.Path()
    p.moveTo(pts[0][1], pts[0][2])
    for i in range(lobes):
        a0 = pts[i][0]
        a1 = pts[(i + 1) % lobes][0] + (2 * math.pi if i == lobes - 1 else 0)
        am = (a0 + a1) / 2
        k = 1 + depth * 1.7
        p.quadTo(cx + rx * k * math.cos(am), cy + ry * k * math.sin(am),
                 pts[(i + 1) % lobes][1], pts[(i + 1) % lobes][2])
    p.close()
    return p


def blade(x, y, ang, ln, wd, bend=0.0):
    """Pointed leaf from base (x, y)."""
    dx, dy = math.cos(ang), math.sin(ang)
    px, py = -dy, dx
    tx, ty = x + dx * ln + px * bend * ln, y + dy * ln + py * bend * ln
    mx, my = x + dx * ln * 0.45, y + dy * ln * 0.45
    p = skia.Path()
    p.moveTo(x, y)
    p.quadTo(mx + px * (wd + bend * ln * 0.4), my + py * (wd + bend * ln * 0.4), tx, ty)
    p.quadTo(mx - px * (wd - bend * ln * 0.4), my - py * (wd - bend * ln * 0.4), x, y)
    p.close()
    return p


def ribbon(pts, widths):
    """Closed band around a centre line with per-point full widths."""
    pts = [np.array(p, float) for p in pts]
    L, R = [], []
    for i, p in enumerate(pts):
        a = pts[max(i - 1, 0)]
        b = pts[min(i + 1, len(pts) - 1)]
        d = b - a
        d /= np.linalg.norm(d) + 1e-9
        nrm = np.array([-d[1], d[0]])
        L.append(p + nrm * widths[i] / 2)
        R.append(p - nrm * widths[i] / 2)
    path = spline(L)
    spline(R[::-1], path=path, start=False)
    path.close()
    return path


def offset_line(pts, off):
    pts = [np.array(p, float) for p in pts]
    out = []
    for i, p in enumerate(pts):
        a = pts[max(i - 1, 0)]
        b = pts[min(i + 1, len(pts) - 1)]
        d = b - a
        d /= np.linalg.norm(d) + 1e-9
        out.append(p + np.array([-d[1], d[0]]) * off)
    return out



# ----------------------------------------------------------------- text
_tf = {}


def typeface(italic=True):
    if italic not in _tf:
        fs = skia.FontStyle.Italic() if italic else skia.FontStyle.Normal()
        tf = None
        for nm in ('Liberation Serif', 'Georgia', 'Times New Roman', 'DejaVu Serif', 'Palatino'):
            t = skia.Typeface.MakeFromName(nm, fs)
            if t is not None and t.getFamilyName() == nm:
                tf = t
                break
        _tf[italic] = tf or skia.Typeface.MakeFromName(None, fs) or skia.Typeface.MakeDefault()
    return _tf[italic]


def text_path(txt, x, y, size, anchor='c', maxw=None, italic=True):
    """Text as a filled outline. (x, y) is the baseline; size is the letter height in units.
    Shrinks to fit maxw. Returns (path, width, size used)."""
    font = skia.Font(typeface(italic), 100)
    gl = font.textToGlyphs(txt)
    ws = font.getWidths(gl)
    tw = sum(ws) or 1.0
    sc = size / 70.0
    if maxw is not None and tw * sc > maxw:
        sc = maxw / tw
    tp = skia.Path()
    xx = 0.0
    for g, w_ in zip(gl, ws):
        gp = font.getPath(g)
        if gp is not None:
            gp.offset(xx, 0)
            tp.addPath(gp)
        xx += w_
    wd = tw * sc
    ox = x - wd / 2 if anchor == 'c' else x - wd if anchor == 'r' else x
    m = skia.Matrix()
    m.setScale(sc, -sc)
    m.postTranslate(ox, y)
    tp.transform(m)
    return tp, wd, sc * 70.0


def wrap_text(txt, n):
    """Split into lines of at most about n characters."""
    words, lines, cur = txt.split(), [], ''
    for w in words:
        if cur and len(cur) + 1 + len(w) > n:
            lines.append(cur)
            cur = w
        else:
            cur = (cur + ' ' + w).strip()
    if cur:
        lines.append(cur)
    return lines


# ----------------------------------------------------------------- shape recipes (the kit for new pieces)
def stroke_path(path, w, cap=skia.Paint.kRound_Cap):
    pa = skia.Paint(Style=skia.Paint.kStroke_Style, StrokeWidth=w, StrokeCap=cap, StrokeJoin=skia.Paint.kRound_Join)
    dst = skia.Path()
    pa.getFillPath(path, dst)
    return dst


def recipe_path(sp, rng):
    """One shape of a recipe, in the piece's own box: x -0.5..0.5, y 0 (base) .. 1 (top)."""
    if 'circle' in sp:
        a = sp['circle']
        return circle(a[0], a[1], a[2])
    if 'oval' in sp:
        a = sp['oval']
        return oval(a[0], a[1], a[2], a[3], a[4] if len(a) > 4 else 0.0)
    if 'rect' in sp:
        a = sp['rect']
        r = a[4] if len(a) > 4 else 0.0
        return rrect(a[0], a[1], a[2], a[3], r) if r else poly([(a[0], a[1]), (a[2], a[1]), (a[2], a[3]), (a[0], a[3])])
    if 'poly' in sp:
        return poly(sp['poly'])
    if 'ngon' in sp:
        a = sp['ngon']                      # cx, cy, r, sides, turn (deg)
        n, rot = int(a[3]), math.radians(a[4] if len(a) > 4 else 0.0)
        return poly([(a[0] + a[2] * math.cos(rot + 2 * math.pi * i / n), a[1] + a[2] * math.sin(rot + 2 * math.pi * i / n)) for i in range(n)])
    if 'curve' in sp:
        return spline(sp['curve'], closed=True)
    if 'blob' in sp:
        a = sp['blob']
        return blob(a[0], a[1], a[2], a[3], rng)
    if 'cloud' in sp:
        a = sp['cloud']
        return scallop(a[0], a[1], a[2], a[3], int(a[4]) if len(a) > 4 else 7, rng)
    if 'leaf' in sp:
        a = sp['leaf']                      # x, y, angle (deg), length, width, bend
        return blade(a[0], a[1], math.radians(a[2]), a[3], a[4], a[5] if len(a) > 5 else 0.0)
    if 'stroke' in sp:
        pts = sp['stroke']
        p = poly(pts, False) if sp.get('sharp') or len(pts) < 3 else spline(pts)
        return stroke_path(p, sp.get('w', 0.04), skia.Paint.kButt_Cap if sp.get('flat') else skia.Paint.kRound_Cap)
    if 'text' in sp:
        a = sp.get('at', [0, 0.5])
        return text_path(sp['text'], a[0], a[1], sp.get('size', 0.12), maxw=sp.get('maxw'), italic=not sp.get('upright'))[0]
    raise ValueError('shape needs one of: circle, oval, rect, poly, ngon, curve, blob, cloud, leaf, stroke, text. Got %s' % sorted(sp))


def draw_recipe(pc, shapes, x, y, s, rng, flip=1, xs=1.0, swap=None):
    """Draw a list of recipe shapes into a piece at base point (x, y), s units tall."""
    m = skia.Matrix()
    m.setScale(s * xs * flip, s)
    m.postTranslate(x, y)
    last = None
    named = {}
    marks = []
    for sp in shapes:
        kind = sp.get('kind', 'fill')
        if 'grid' in sp:                  # repeat a few shapes: [columns, rows, dx, dy, stagger]
            g = sp['grid']
            for j in range(int(g[1])):
                for i in range(int(g[0])):
                    ox = (i + (g[4] if len(g) > 4 and j % 2 else 0.0)) * g[2]
                    marks += draw_recipe(pc, sp['of'], x + ox * s * xs * flip, y + j * g[3] * s, s, rng, flip, xs, swap)
            continue
        if 'line' in sp:                  # a thin drawn line
            pts = sp['line']
            p = poly(pts, False) if sp.get('sharp') or len(pts) < 3 else spline(pts, closed=bool(sp.get('closed')))
            kind = 'line'
        else:
            p = recipe_path(sp, rng)
        p.transform(m)
        mat = sp.get('mat', 'ink')
        if swap and mat in swap:
            mat = swap[mat]
        clip = named.get(sp['in']) if 'in' in sp else (last if kind in ('shade', 'hi') else None)
        if kind == 'fill':
            pc.fill(p, mat, tone=sp.get('tone', 0.0), clip=clip)
            last = p
            if 'id' in sp:
                named[sp['id']] = p
        elif kind == 'shade':
            pc.shade(p, mat, clip)
        elif kind == 'hi':
            pc.hi(p, mat, clip)
        elif kind == 'line':
            pc.line(p, w=max(0.0012, sp.get('w', 0.012) * s) if 'w' in sp else 0.002, mat=mat, clip=clip)
        else:
            raise ValueError('kind must be fill, shade, hi or line')
        b = p.getBounds()
        if 'anchor' in sp:
            pc.anchors[sp['anchor']] = (b.centerX(), b.centerY())
        if sp.get('glow'):
            marks.append(('glow', (b.centerX(), b.centerY())))
        if sp.get('perch'):
            marks.append(('perch', (b.centerX(), b.bottom())))
    return marks
