"""Ready-made paper pieces. Every piece is drawn from the same shape kit as a custom recipe,
so the art styles paint both the same way.

A piece is a function  fn(pc, x, y, s, rng, o, cx):
  pc   the sheet of card it is drawn on        x, y   where its base sits on that sheet
  s    its height in page units                o      the options given in the storyboard
  cx   context: cx.xs (width correction), cx.scene (to register perches, glows, the sun)"""
import math
import numpy as np
import skia
from kit import *

REG = {}
DEFAULT_S = {}


def piece(name, s=0.3):
    def deco(fn):
        REG[name] = fn
        DEFAULT_S[name] = s
        return fn
    return deco


def add_perch(pc, cx, pt):
    n = sum(1 for k in pc.anchors if k.startswith('perch'))
    pc.anchors['perch%d' % n] = pt
    cx.scene.birds.append((pc.name, 'perch%d' % n))


def add_glow(pc, cx, pt, size=1.0):
    nm = 'glow%d' % len(cx.scene.glows)
    pc.anchors[nm] = pt
    cx.scene.glows.append((pc.name, nm, size))


# ----------------------------------------------------------------- building blocks
# ----------------------------------------------------------------- motifs
def foliage(pc, cx, cy, rx, ry, rng, mat='leafB', lobes=7, shade=True):
    fp = scallop(cx, cy, rx, ry, lobes, rng)
    pc.fill(fp, mat, tone=rng.uniform(-0.12, 0.12))
    if shade:
        pc.shade(scallop(cx + rx * 0.28, cy - ry * 0.38, rx * 0.8, ry * 0.75, max(lobes - 1, 4), rng), mat, fp)
        pc.hi(scallop(cx - rx * 0.32, cy + ry * 0.36, rx * 0.34, ry * 0.3, 4, rng), mat, fp)
    return fp


def karst(pc, cx, w, h, rng, mat='rockB', leaf='leafB', lean=0.0, n=7, detail=1.0, cap=True):
    L, R, C = [], [], []
    for i in range(n + 1):
        t = i / n
        hw = 0.5 * w * (1.0 - 0.46 * t ** 2.0) * (1 + rng.uniform(-0.10, 0.10))
        if i == 0:
            hw = 0.5 * w * 1.1
        y = h * 0.92 * t
        x = cx + lean * t * t
        L.append((x - hw, y))
        R.append((x + hw, y))
        C.append((x, y, hw))
    top = (cx + lean, h)
    path = skia.Path()
    path.moveTo(L[0][0], -0.03)
    spline(L + [top] + R[::-1], path=path, start=False)
    path.lineTo(R[0][0], -0.03)
    path.close()
    pc.fill(path, mat, tone=rng.uniform(-0.08, 0.08))
    inner = [(x + hw * (0.05 + 0.3 * rng.random()), y) for (x, y, hw) in C]
    sp = skia.Path()
    sp.moveTo(inner[0][0], -0.03)
    spline(inner + [(top[0] + 0.012, top[1] + 0.02)], path=sp, start=False)
    sp.lineTo(top[0] + w, h + 0.05)
    sp.lineTo(cx + w, -0.03)
    sp.close()
    pc.shade(sp, mat, path)
    # lit edge
    lit = [(x - hw * 0.72, y) for (x, y, hw) in C[1:-1]]
    pc.hi(ribbon(lit, [w * 0.07] * len(lit)), mat, path)
    for _ in range(int(round(4 * detail))):
        t0 = rng.uniform(0.3, 0.92)
        x0 = cx + lean * t0 * t0 + rng.uniform(-0.3, 0.3) * w * (1 - 0.4 * t0)
        y0 = h * 0.92 * t0
        ln = rng.uniform(0.12, 0.3) * h
        pts = [(x0 + rng.uniform(-0.012, 0.012) * w * 2, y0 - ln * j / 3) for j in range(4)]
        pc.line(spline(pts), w=0.0018, clip=path)
    for _ in range(int(round(3 * detail))):
        t0 = rng.uniform(0.1, 0.8)
        y0 = h * 0.92 * t0
        x0 = cx + lean * t0 * t0 + rng.uniform(-0.32, 0.1) * w
        ln = rng.uniform(0.15, 0.35) * w
        pc.line(spline([(x0, y0), (x0 + ln * 0.5, y0 + rng.uniform(-0.008, 0.008)),
                        (x0 + ln, y0 + rng.uniform(-0.012, 0.004))]), w=0.0016, clip=path)
    if cap:
        foliage(pc, top[0] - 0.02 * w, h - 0.02 - 0.03 * w, 0.30 * w, 0.028 + 0.10 * w, rng, leaf, 6)
        for side in (-1, 1):
            if rng.random() < 0.75:
                t0 = rng.uniform(0.3, 0.72)
                i = int(t0 * n)
                x, y, hw = C[i]
                foliage(pc, x + side * hw * 0.92, y, 0.10 * w + 0.012, 0.022 + 0.05 * w, rng, leaf, 5)
        for _ in range(int(round(2 * detail))):
            x0 = top[0] + rng.uniform(-0.2, 0.2) * w
            y0 = h - 0.05
            ln = rng.uniform(0.05, 0.14)
            pc.line(spline([(x0, y0), (x0 + 0.006, y0 - ln * 0.5), (x0 - 0.004, y0 - ln)]), w=0.0018, mat=leaf, clip=path)
    return top


def figure(pc, x, y, h, robe, f=1, staff=True, pack=True, hat=True):
    s = h
    pc.fill(spline([(x - .2 * s, y), (x - .17 * s, y + .35 * s), (x - .13 * s, y + .62 * s), (x + .13 * s, y + .62 * s),
                    (x + .17 * s, y + .35 * s), (x + .2 * s, y)], closed=True), robe)
    if pack:
        pc.fill(rrect(x - f * .30 * s, y + .30 * s, x - f * .12 * s, y + .58 * s, .04 * s), 'trunk')
    pc.fill(circle(x + f * .03 * s, y + .71 * s, .10 * s), 'skin')
    if hat:
        pc.fill(poly([(x - .25 * s, y + .77 * s), (x + .25 * s, y + .77 * s), (x + f * .02 * s, y + 1.0 * s)]), 'hat')
    if staff:
        pc.strip(poly([(x + f * .30 * s, y), (x + f * .26 * s, y + .9 * s)], False), 'trunk', .035 * s)


def lantern(pc, name, x, y, s, hang=0.0, post=0.0):
    if hang:
        pc.strip(poly([(x, y + s * .5), (x, y + s * .5 + hang)], False), 'rope', 0.003)
    if post:
        pc.strip(poly([(x, y - s * .5), (x, y - s * .5 - post)], False), 'trunk', 0.006)
    body = rrect(x - s * .36, y - s * .5, x + s * .36, y + s * .5, s * .26)
    pc.fill(body, 'lantern')
    pc.hi(oval(x - s * .08, y + s * .06, s * .14, s * .26), 'lantern', body)
    pc.fill(rrect(x - s * .24, y + s * .44, x + s * .24, y + s * .62, s * .05), 'stoneD')
    pc.fill(rrect(x - s * .24, y - s * .62, x + s * .24, y - s * .44, s * .05), 'stoneD')
    pc.anchors[name] = (x, y)


def monkey_sit(pc, x, y, s, f=1):
    tail = skia.Path()
    tail.moveTo(x - f * .16 * s, y + .12 * s)
    tail.cubicTo(x - f * .5 * s, y - .1 * s, x - f * .42 * s, y - .75 * s, x - f * .2 * s, y - .62 * s)
    tail.cubicTo(x - f * .08 * s, y - .55 * s, x - f * .16 * s, y - .38 * s, x - f * .26 * s, y - .46 * s)
    pc.strip(tail, 'fur', .07 * s)
    body = oval(x, y + .36 * s, .23 * s, .34 * s, -8 * f)
    pc.fill(body, 'fur')
    pc.shade(oval(x - f * .12 * s, y + .3 * s, .2 * s, .3 * s), 'fur', body)
    pc.strip(spline([(x + f * .08 * s, y + .5 * s), (x + f * .3 * s, y + .3 * s), (x + f * .22 * s, y + .08 * s)]), 'fur', .08 * s)
    pc.strip(spline([(x, y + .12 * s), (x + f * .28 * s, y + .14 * s), (x + f * .3 * s, y - .02 * s)]), 'fur', .09 * s)
    head = circle(x + f * .1 * s, y + .82 * s, .18 * s)
    pc.fill(circle(x - f * .06 * s, y + .9 * s, .07 * s), 'fur')
    pc.fill(head, 'fur')
    pc.fill(oval(x + f * .17 * s, y + .79 * s, .1 * s, .11 * s), 'skin')


def monkey_hang(pc, x, yb, s, f=1):
    pc.strip(spline([(x, yb), (x + f * .04 * s, yb - .3 * s), (x + f * .1 * s, yb - .58 * s)]), 'fur', .075 * s)
    tail = skia.Path()
    tail.moveTo(x + f * .2 * s, yb - 1.12 * s)
    tail.cubicTo(x + f * .5 * s, yb - 1.3 * s, x + f * .62 * s, yb - .85 * s, x + f * .44 * s, yb - .8 * s)
    tail.cubicTo(x + f * .32 * s, yb - .78 * s, x + f * .34 * s, yb - .96 * s, x + f * .44 * s, yb - .94 * s)
    pc.strip(tail, 'fur', .065 * s)
    body = oval(x + f * .12 * s, yb - .86 * s, .21 * s, .32 * s, 10 * f)
    pc.fill(body, 'fur')
    pc.shade(oval(x + f * .22 * s, yb - .92 * s, .18 * s, .3 * s), 'fur', body)
    pc.strip(spline([(x + f * .0 * s, yb - .66 * s), (x - f * .22 * s, yb - .8 * s), (x - f * .3 * s, yb - .62 * s)]), 'fur', .07 * s)
    pc.strip(spline([(x + f * .06 * s, yb - 1.1 * s), (x - f * .08 * s, yb - 1.34 * s), (x + f * .02 * s, yb - 1.5 * s)]), 'fur', .075 * s)
    pc.strip(spline([(x + f * .2 * s, yb - 1.12 * s), (x + f * .24 * s, yb - 1.36 * s), (x + f * .14 * s, yb - 1.46 * s)]), 'fur', .075 * s)
    pc.fill(circle(x - f * .04 * s, yb - .5 * s, .17 * s), 'fur')
    pc.fill(oval(x - f * .1 * s, yb - .53 * s, .1 * s, .105 * s), 'skin')


def toucan(pc, x, y, s, f=1):
    pc.strip(poly([(x - f * .1 * s, y + .2 * s), (x - f * .26 * s, y - .28 * s)], False), 'toucan', .13 * s, cap=skia.Paint.kButt_Cap)
    body = oval(x, y + .4 * s, .2 * s, .36 * s, 14 * f)
    pc.fill(body, 'toucan')
    pc.fill(oval(x + f * .1 * s, y + .56 * s, .12 * s, .17 * s, 10 * f), 'bib')
    head = circle(x + f * .08 * s, y + .82 * s, .16 * s)
    pc.fill(head, 'toucan')
    bk = skia.Path()
    bk.moveTo(x + f * .18 * s, y + .93 * s)
    bk.cubicTo(x + f * .5 * s, y + 1.02 * s, x + f * .8 * s, y + .86 * s, x + f * .86 * s, y + .62 * s)
    bk.cubicTo(x + f * .66 * s, y + .74 * s, x + f * .4 * s, y + .76 * s, x + f * .2 * s, y + .72 * s)
    bk.close()
    pc.fill(bk, 'beak')
    pc.shade(poly([(x + f * .62 * s, y + 1.0 * s), (x + f * .9 * s, y + 1.0 * s), (x + f * .9 * s, y + .55 * s), (x + f * .7 * s, y + .6 * s)]), 'beak', bk)
    pc.fill(circle(x + f * .11 * s, y + .86 * s, .045 * s), 'bib')
    pc.fill(circle(x + f * .115 * s, y + .86 * s, .02 * s), 'toucan')


def heron(pc, x, y, s, f=1):
    pc.strip(spline([(x - f * .02 * s, y), (x - f * .03 * s, y + .2 * s), (x - f * .05 * s, y + .42 * s)]), 'heronD', .022 * s)
    pc.strip(spline([(x + f * .07 * s, y), (x + f * .1 * s, y + .2 * s), (x + f * .02 * s, y + .44 * s)]), 'heronD', .022 * s)
    # tail
    pc.fill(poly([(x - f * .1 * s, y + .56 * s), (x - f * .34 * s, y + .36 * s), (x - f * .14 * s, y + .44 * s)]), 'heronD')
    body = oval(x - f * .03 * s, y + .52 * s, .2 * s, .115 * s, 22 * f)
    neck = skia.Path()
    neck.moveTo(x + f * .11 * s, y + .58 * s)
    neck.cubicTo(x + f * .26 * s, y + .68 * s, x - f * .03 * s, y + .78 * s, x + f * .09 * s, y + .93 * s)
    pc.strip(neck, 'heron', .055 * s)
    pc.fill(body, 'heron')
    wing = oval(x - f * .07 * s, y + .5 * s, .16 * s, .075 * s, 26 * f)
    pc.fill(wing, 'heronD', tone=0.35, clip=body)
    pc.line(spline([(x - f * .2 * s, y + .44 * s), (x - f * .05 * s, y + .49 * s), (x + f * .06 * s, y + .56 * s)]), w=0.0016, clip=body)
    pc.fill(oval(x + f * .11 * s, y + .945 * s, .055 * s, .038 * s), 'heron')
    pc.fill(poly([(x + f * .14 * s, y + .97 * s), (x + f * .38 * s, y + .925 * s), (x + f * .14 * s, y + .92 * s)]), 'beak')
    pc.strip(spline([(x + f * .08 * s, y + .97 * s), (x - f * .06 * s, y + .99 * s), (x - f * .16 * s, y + .93 * s)]), 'heronD', .016 * s)
    pc.fill(circle(x + f * .125 * s, y + .952 * s, .008 * s), 'heronD')



# ----------------------------------------------------------------- the catalogue
@piece('sun', 0.5)
def p_sun(pc, x, y, s, rng, o, cx):
    """Sun or moon disc; y is its centre. Options: mat, rays, plain."""
    r = s / 2
    mat = o.get('mat', 'moon')
    if o.get('rays'):
        for k in range(14):
            a = 2 * math.pi * k / 14
            ln = r * (0.5 if k % 2 else 0.34)
            p = blade(x + math.cos(a) * r * 1.08 * cx.xs, y + math.sin(a) * r * 1.08, a, ln, r * 0.09)
            pc.fill(p, mat, tone=-0.15)
    disc = oval(x, y, r * cx.xs, r)
    pc.fill(disc, mat)
    if not o.get('plain'):
        for (dx, dy, rx, ry) in [(-.4, .36, .3, .21), (.32, .46, .21, .16), (.46, -.07, .18, .21), (-.5, -.28, .18, .14), (0, .07, .12, .1)]:
            pc.fill(blob(x + dx * r, y + dy * r, rx * r, ry * r, rng, 8, .2), 'mare', clip=disc)
    pc.anchors['sun'] = (x, y)
    pc.anchors['sun_r'] = r
    cx.scene.sun = (pc.name, 'sun', r)


@piece('cloud', 0.12)
def p_cloud(pc, x, y, s, rng, o, cx):
    """Cloud; y is its centre, s its height."""
    mat = o.get('mat', 'foam')
    c = scallop(x, y, s * 1.5 * cx.xs, s * 0.5, 8, rng, depth=.3)
    pc.fill(c, mat)
    pc.shade(scallop(x + s * .3, y - s * .25, s * 1.3, s * .4, 7, rng), mat, c)


@piece('hills', 0.2)
def p_hills(pc, x, y, s, rng, o, cx):
    """Rolling hills across the whole sheet: a pale far ridge and a nearer one in front. Options: mat, bumps."""
    u0, _, u1, _ = pc.bbox
    mat = o.get('mat', 'rockA')
    n = int(o.get('bumps', 7))
    tone = o.get('tone', -0.1)
    for (k, top, tn, ph) in ((0, 1.0, tone + 0.2, rng.uniform(0, 6)), (1, 0.74, tone, rng.uniform(0, 6))):
        m = 2 * n + k
        pts = []
        for i in range(m + 1):
            crest = (i + k) % 2 == 0                       # crests and dips take turns, so it reads as hills and not a band
            hgt = rng.uniform(0.8, 0.96) if crest else rng.uniform(0.42, 0.6)
            pts.append((u0 + (u1 - u0) * i / m + (rng.uniform(-.02, .02) if 0 < i < m else 0), y + s * top * hgt))
        p = skia.Path()
        p.moveTo(u0, -0.03)
        spline(pts, path=p, start=False)
        p.lineTo(u1, -0.03)
        p.close()
        pc.fill(p, mat, tone=tn)
        if k:
            for i in range(m + 1):
                if (i + k) % 2 == 0:
                    px, py = pts[i]
                    pc.shade(oval(px + 0.07, py - s * 0.42, 0.085, s * 0.5), mat, p)


@piece('peak', 0.5)
def p_peak(pc, x, y, s, rng, o, cx):
    """Tall rock tower with plants on top. Options: mat, leaf, w, lean."""
    top = karst(pc, x, o.get('w', s * 0.42), s, rng, o.get('mat', 'rockB'), o.get('leaf', 'leafB'), o.get('lean', 0.0),
                detail=o.get('detail', 1.0))
    add_perch(pc, cx, top)


@piece('mountain', 0.5)
def p_mountain(pc, x, y, s, rng, o, cx):
    """Pointed mountain with a snow cap. Options: mat, w, snow."""
    w = o.get('w', s * 1.3)
    mat = o.get('mat', 'rockB')
    pts = [(x - w / 2, -0.03), (x - w * .3, y + s * .38), (x - w * .1, y + s * .8), (x, y + s), (x + w * .12, y + s * .78),
           (x + w * .33, y + s * .36), (x + w / 2, -0.03)]
    m = poly([(px + rng.uniform(-.01, .01) * (0 < i < 6), py) for i, (px, py) in enumerate(pts)])
    pc.fill(m, mat)
    pc.shade(poly([(x + w * .02, y + s * 1.02), (x + w * .6, y + s), (x + w * .6, -0.03), (x + w * .1, -0.03)]), mat, m)
    if o.get('snow', True):
        pc.fill(poly([(x - w * .16, y + s * .68), (x - w * .06, y + s * .74), (x, y + s * .66), (x + w * .07, y + s * .76),
                      (x + w * .17, y + s * .68), (x + w * .2, y + s * 1.05), (x - w * .2, y + s * 1.05)]), 'foam', clip=m)
    add_perch(pc, cx, (x, y + s))


@piece('tree', 0.45)
def p_tree(pc, x, y, s, rng, o, cx):
    """Round leafy tree. Options: mat (leaves), fruit (colour of dots)."""
    mat = o.get('mat', 'leafB')
    tw = s * 0.07
    trunk = poly([(x - tw * 1.5, y - 0.02), (x - tw * .7, y + s * .5), (x + tw * .7, y + s * .5), (x + tw * 1.5, y - 0.02)])
    for (dx, dy) in ((-.2, .62), (.2, .6)):
        pc.strip(spline([(x, y + s * .4), (x + dx * s * .5, y + s * .5), (x + dx * s, y + s * dy)]), 'trunk', tw * .7)
    pc.fill(trunk, 'trunk')
    pc.shade(poly([(x + tw * .15, y + s * .55), (x + tw * 3, y + s * .55), (x + tw * 3, y - .02), (x + tw * .3, y - .02)]), 'trunk', trunk)
    for (dx, dy, rx, ry) in [(-.22, .62, .2, .15), (.22, .6, .2, .15), (0, .78, .26, .17), (0, .62, .2, .13)]:
        foliage(pc, x + dx * s, y + dy * s, rx * s * cx.xs, ry * s, rng, mat, 7)
    if o.get('fruit'):
        for _ in range(7):
            pc.fill(circle(x + rng.uniform(-.34, .34) * s, y + rng.uniform(.52, .86) * s, s * .028), o['fruit'])
    add_perch(pc, cx, (x, y + s * .94))


@piece('pine', 0.45)
def p_pine(pc, x, y, s, rng, o, cx):
    """Pine tree. Options: mat."""
    mat = o.get('mat', 'leafC')
    pc.fill(poly([(x - s * .04, y - .02), (x - s * .03, y + s * .25), (x + s * .03, y + s * .25), (x + s * .04, y - .02)]), 'trunk')
    for i, (yb, yt, w) in enumerate([(.16, .56, .3), (.38, .78, .23), (.6, 1.0, .16)]):
        t = poly([(x - w * s, y + yb * s), (x, y + yt * s), (x + w * s, y + yb * s)])
        pc.fill(t, mat, tone=0.08 * i)
        pc.shade(poly([(x + .02 * s, y + yt * s), (x + w * s, y + yt * s), (x + w * s, y + yb * s), (x + .05 * s, y + yb * s)]), mat, t)
    add_perch(pc, cx, (x, y + s))


@piece('bush', 0.14)
def p_bush(pc, x, y, s, rng, o, cx):
    """Low bush. Options: mat, w."""
    foliage(pc, x, y + s * .45, o.get('w', s * 1.1), s * .5, rng, o.get('mat', 'leafB'), 7)


@piece('grass', 0.12)
def p_grass(pc, x, y, s, rng, o, cx):
    """Strip of ground with tufts of grass along the whole sheet (or from x0 to x1). Options: mat, tufts."""
    u0, _, u1, _ = pc.bbox
    x0, x1 = o.get('x0', u0), o.get('x1', u1)
    mat = o.get('mat', 'grass')
    band = [(x0, -0.03)] + [(u, y + 0.022 + 0.008 * math.sin(u * 23) + 0.004 * math.sin(u * 61)) for u in np.linspace(x0, x1, 41)] + [(x1, -0.03)]
    pc.fill(poly(band), mat, tone=-0.25)
    n = int(o.get('tufts', max(2, round((x1 - x0) / 0.3))))
    for k in range(n):
        bx = x0 + (x1 - x0) * (k + rng.uniform(.2, .8)) / n
        hm = s * rng.uniform(.6, 1.0)
        m = int(rng.integers(4, 8))
        for i in range(m):
            ang = math.pi * (0.14 + 0.72 * (i + rng.uniform(-.25, .25)) / (m - 1))
            ln = hm * (0.55 + 0.45 * math.sin(ang))
            pc.fill(blade(bx + rng.uniform(-.02, .02), y, ang, ln, 0.02, rng.uniform(-.25, .25)),
                    'leafC' if i % 2 else 'leafB', tone=rng.uniform(-.15, .15))


@piece('flower', 0.25)
def p_flower(pc, x, y, s, rng, o, cx):
    """Flower on a stem. Options: mat (petals), centre, petals."""
    mat, cen, n = o.get('mat', 'robe3'), o.get('centre', 'robe2'), int(o.get('petals', 6))
    top = (x + rng.uniform(-.04, .04) * s, y + s * .78)
    pc.strip(spline([(x, y - .01), (x + (top[0] - x) * .3, y + s * .4), top]), 'leafB', s * .04)
    pc.fill(blade(x, y + s * .22, math.radians(40), s * .3, s * .07, .2), 'leafB')
    pc.fill(blade(x, y + s * .32, math.radians(140), s * .28, s * .07, -.2), 'leafC')
    r = s * .2
    for k in range(n):
        a = 2 * math.pi * k / n + 0.3
        pc.fill(oval(top[0] + math.cos(a) * r * .62, top[1] + math.sin(a) * r * .62, r * .5, r * .34, math.degrees(a)), mat,
                tone=0.12 * (k % 2))
    pc.fill(circle(top[0], top[1], r * .36), cen)
    pc.anchors[o.get('id', '_')] = top


@piece('rock', 0.1)
def p_rock(pc, x, y, s, rng, o, cx):
    """Boulder. Options: mat, w."""
    w = o.get('w', s * 1.6)
    mat = o.get('mat', 'rockC')
    b = blob(x, y + s * .3, w / 2, s * .7, rng, 8, .14)
    pc.fill(b, mat, tone=-0.1)
    pc.shade(oval(x + w * .3, y + s * .2, w * .4, s * .65), mat, b)


@piece('house', 0.3)
def p_house(pc, x, y, s, rng, o, cx):
    """Small house with a lit window. Options: mat (walls), roof, w."""
    w = o.get('w', s * 0.9)
    mat, roof = o.get('mat', 'stone'), o.get('roof', 'canoe')
    body = poly([(x - w / 2, y - .02), (x - w / 2, y + s * .58), (x + w / 2, y + s * .58), (x + w / 2, y - .02)])
    pc.fill(poly([(x + w * .2, y + s * .7), (x + w * .2, y + s * .98), (x + w * .32, y + s * .98), (x + w * .32, y + s * .6)]), mat, tone=-0.2)
    pc.fill(body, mat)
    pc.shade(poly([(x + w * .22, y + s * .6), (x + w * .6, y + s * .6), (x + w * .6, y - .02), (x + w * .3, y - .02)]), mat, body)
    rf = poly([(x - w * .6, y + s * .56), (x, y + s), (x + w * .6, y + s * .56)])
    pc.fill(rf, roof)
    pc.shade(poly([(x + w * .05, y + s * 1.02), (x + w * .7, y + s), (x + w * .7, y + s * .5), (x + w * .2, y + s * .56)]), roof, rf)
    pc.fill(rrect(x - w * .1, y - .02, x + w * .1, y + s * .3, w * .03), 'stoneD')
    win = rrect(x - w * .36, y + s * .26, x - w * .18, y + s * .44, w * .02)
    pc.fill(win, 'lantern')
    pc.line(win, w=0.0016)
    if o.get('glow', True):
        add_glow(pc, cx, (x - w * .27, y + s * .35), 0.8)
    add_perch(pc, cx, (x, y + s))


@piece('tower', 0.5)
def p_tower(pc, x, y, s, rng, o, cx):
    """Tall building with rows of windows. Options: mat, w, floors, cols, roof."""
    w = o.get('w', s * 0.4)
    mat = o.get('mat', 'stone')
    floors, cols = int(o.get('floors', max(2, round(s / 0.09)))), int(o.get('cols', 3))
    body = poly([(x - w / 2, y - .02), (x - w / 2, y + s), (x + w / 2, y + s), (x + w / 2, y - .02)])
    pc.fill(body, mat)
    pc.shade(poly([(x + w * .25, y + s * 1.02), (x + w * .6, y + s * 1.02), (x + w * .6, y - .02), (x + w * .3, y - .02)]), mat, body)
    if o.get('roof'):
        pc.fill(poly([(x - w * .58, y + s), (x, y + s * 1.18), (x + w * .58, y + s)]), o['roof'])
    for i in range(floors):
        for j in range(cols):
            wx = x - w / 2 + w * (j + .5) / cols
            wy = y + s * (i + .55) / floors
            lit = rng.random() < 0.45
            pc.fill(rrect(wx - w * .09, wy - s * .2 / floors, wx + w * .09, wy + s * .2 / floors, .003), 'lantern' if lit else 'stoneD')
    add_perch(pc, cx, (x, y + s))


@piece('person', 0.12)
def p_person(pc, x, y, s, rng, o, cx):
    """Small figure in a robe. Options: mat (robe), hat, pack, staff, flip."""
    figure(pc, x, y, s, o.get('mat', 'robe1'), f=-1 if o.get('flip') else 1, staff=bool(o.get('staff')), pack=bool(o.get('pack')),
           hat=o.get('hat', True))


@piece('heron', 0.3)
def p_heron(pc, x, y, s, rng, o, cx):
    """Tall wading bird."""
    heron(pc, x, y, s, f=-1 if o.get('flip') else 1)


@piece('toucan', 0.1)
def p_toucan(pc, x, y, s, rng, o, cx):
    toucan(pc, x, y, s, f=-1 if o.get('flip') else 1)


@piece('monkey', 0.09)
def p_monkey(pc, x, y, s, rng, o, cx):
    monkey_sit(pc, x, y, s, f=-1 if o.get('flip') else 1)


@piece('lantern', 0.05)
def p_lantern(pc, x, y, s, rng, o, cx):
    """Glowing lantern; y is its centre. Options: post, hang (lengths)."""
    lantern(pc, '_lan', x, y, s, hang=o.get('hang', 0.0), post=o.get('post', 0.0))
    add_glow(pc, cx, (x, y), o.get('glow', 1.0))


@piece('boat', 0.1)
def p_boat(pc, x, y, s, rng, o, cx):
    """Canoe with a paddler; s is its height, the hull is about 2.4 times as long."""
    k = s / 0.105
    f = -1 if o.get('flip') else 1
    hull = skia.Path()
    hull.moveTo(x - .125 * k, y + .052 * k)
    hull.cubicTo(x - .09 * k, y + .004 * k, x + .09 * k, y + .004 * k, x + .125 * k, y + .052 * k)
    hull.cubicTo(x + .09 * k, y + .03 * k, x - .09 * k, y + .03 * k, x - .125 * k, y + .052 * k)
    hull.close()
    figure(pc, x - .02 * k * f, y + .024 * k, .07 * k, o.get('rider', 'robe2'), f=f, pack=False, staff=False)
    pc.strip(poly([(x + .035 * k * f, y + .085 * k), (x - .055 * k * f, y + .012 * k)], False), 'trunk', .005 * k)
    mat = o.get('mat', 'canoe')
    pc.fill(hull, mat)
    pc.shade(poly([(x - .13 * k, y + .022 * k), (x + .13 * k, y + .022 * k), (x + .13 * k, y), (x - .13 * k, y)]), mat, hull)


@piece('fall', 0.4)
def p_fall(pc, x, y, s, rng, o, cx):
    """Waterfall that flows once the scene comes alive. Options: w (width at the top)."""
    w = o.get('w', 0.12)
    f = poly([(x - w / 2, y + s), (x + w / 2, y + s), (x + w * .7, -0.03), (x - w * .7, -0.03)])
    pc.fill(f, 'water')
    pc.hi(poly([(x - w * .25, y + s), (x - w * .03, y + s), (x - w * .03, -0.03), (x - w * .33, -0.03)]), 'water', f)
    pc.fill(scallop(x, y + 0.012, w * .9, 0.03, 9, rng, depth=.3), 'foam')
    for k in (-.38, -.14, .1, .34):
        pc.flows.append(dict(pts=[(x + w * k, y + s), (x + w * k * 1.4, y + 0.01)], w=0.007, sp=0.42))


@piece('sign', 0.2)
def p_sign(pc, x, y, s, rng, o, cx):
    """Wooden signpost with a word on it. Options: text, mat (board)."""
    txt = o.get('text', '')
    tp, wd, sz = text_path(txt, x, y + s * .7, s * .26, maxw=o.get('maxw', 0.5))
    pc.strip(poly([(x, y - .02), (x, y + s * .66)], False), 'trunk', s * .07)
    bd = rrect(x - wd / 2 - s * .12, y + s * .58, x + wd / 2 + s * .12, y + s * 1.0, s * .04)
    pc.fill(bd, o.get('mat', 'plank'), tone=0.35)
    pc.line(bd, w=0.002)
    pc.fill(tp, 'ink')


@piece('label', 0.07)
def p_label(pc, x, y, s, rng, o, cx):
    """A word or two; y is the baseline, s the letter height. Options: text, mat, banner (paper strip behind)."""
    tp, wd, sz = text_path(o.get('text', ''), x, y, s, maxw=o.get('maxw'), italic=not o.get('upright'))
    if o.get('banner', True):
        bd = rrect(x - wd / 2 - sz * .5, y - sz * .45, x + wd / 2 + sz * .5, y + sz * 1.15, sz * .3)
        pc.fill(bd, 'paper')
        pc.line(bd, w=0.002)
    pc.fill(tp, o.get('mat', 'ink'))


@piece('arrow', 0.02)
def p_arrow(pc, x, y, s, rng, o, cx):
    """Curved arrow from (x, y) to o['to']; s is the line thickness. Options: mat, bend."""
    tx, ty = o['to']
    mx, my = (x + tx) / 2, (y + ty) / 2
    dx, dy = tx - x, ty - y
    ln = math.hypot(dx, dy) + 1e-6
    nx, ny = -dy / ln, dx / ln
    b = o.get('bend', 0.18) * ln
    mat = o.get('mat', 'robe1')
    body = spline([(x, y), (mx + nx * b, my + ny * b), (tx, ty)])
    pc.strip(body, mat, s)
    ax, ay = tx - (mx + nx * b), ty - (my + ny * b)
    al = math.hypot(ax, ay) + 1e-6
    ax, ay = ax / al, ay / al
    h = s * 3.2
    pc.fill(poly([(tx + ax * h * .9, ty + ay * h * .9), (tx - ay * h * .7, ty + ax * h * .7), (tx + ay * h * .7, ty - ax * h * .7)]), mat)
