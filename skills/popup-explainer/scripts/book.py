"""Turns one page of a storyboard into a pop-up spread: sheets of card in fixed slots that are known to fold flat."""
import hashlib
import math
import numpy as np
import skia
from core import PW, PH, RES, GRES
from kit import *
import catalogue as CAT

# Standing sheets, far to near. Each is a V-fold glued across the spine at angle alpha, or a side sheet on tabs.
SLOTS = dict(
    far=dict(bbox=(-0.96, 0, 0.96, 0.91), y0=0.05, alpha=78, side='both', depth=0.0),
    back=dict(bbox=(-1.0, 0, 1.0, 0.74), y0=-0.10, alpha=70, side='both', depth=0.3),
    mid=dict(bbox=(-1.0, 0, 1.0, 0.66), y0=-0.26, alpha=74, side='both', depth=0.55),
    left=dict(bbox=(-1.02, 0, -0.10, 0.88), y0=-0.42, alpha=74, side='L', depth=0.75),
    right=dict(bbox=(0.10, 0, 1.02, 0.88), y0=-0.42, alpha=74, side='R', depth=0.75),
    front=dict(bbox=(-1.0, 0, 1.0, 0.34), y0=-0.80, alpha=82, side='both', depth=1.0))
LAYERS = ['far', 'back', 'mid', 'left', 'right', 'front']
SLOT_Y = -0.72
PAGE_PIECES = ['map', 'jacket', 'cover', 'tab']


class Ctx:
    def __init__(self, scene, xs):
        self.scene, self.xs = scene, xs


class Scene:
    def __init__(self):
        self.pcs = {}
        self.order = []          # standing pieces, far to near
        self.birds = []          # (piece, anchor)
        self.glows = []          # (piece, anchor, size)
        self.tabs = []           # (piece, parent, [(u, v)])
        self.sun = None          # (piece, anchor, radius)
        self.slider = None       # piece name
        self.flyers = []         # dicts
        self.warnings = []
        self.fitted = []         # things the engine nudged by itself
        self.mist = True
        self.n_birds = 6
        self.focus = 0.0


def _extent(shapes, clipped=False):
    """Box round the solid shapes (its top is .bottom() in skia terms)."""
    b = None
    for sh in shapes:
        if sh.kind != 'fill' or (sh.clip is not None and not clipped):
            continue
        r = sh.path.computeTightBounds()
        b = r if b is None else skia.Rect.MakeLTRB(min(b.left(), r.left()), min(b.top(), r.top()), max(b.right(), r.right()), max(b.bottom(), r.bottom()))
    return b


def _place(scene, pc, items, recipes, rng, xs):
    """Draw each item on the sheet. An item that pokes past the sheet is slid back in (or made a little smaller)
    and that is noted, so a first draft rarely needs its positions fixed by hand."""
    cx = Ctx(scene, xs)
    u0, v0, u1, v1 = pc.bbox
    for it in items:
        if isinstance(it, str):
            it = {'use': it}
        name = it.get('use')
        if name not in recipes and name not in CAT.REG:
            raise ValueError('no piece called %r. Ready-made: %s. Custom: %s' % (name, ', '.join(sorted(CAT.REG)), ', '.join(sorted(recipes)) or 'none'))
        x = x_in = it.get('x', (u0 + u1) / 2)
        y = y_in = it.get('y', 0.0)
        s = s_in = it.get('s', 0.3 if name in recipes else CAT.DEFAULT_S[name])
        n0 = len(pc.shapes)
        keep = (dict(pc.anchors), len(pc.flows), len(scene.birds), len(scene.glows), scene.sun)
        for attempt in range(4):
            if name in recipes:
                marks = draw_recipe(pc, recipes[name], x, y, s, rng, flip=-1 if it.get('flip') else 1, xs=xs, swap=it.get('swap'))
                for kind, pt in marks or []:
                    if kind == 'glow':
                        CAT.add_glow(pc, cx, pt)
                    else:
                        CAT.add_perch(pc, cx, pt)
            else:
                CAT.REG[name](pc, x, y, s, rng, it, cx)
            r = _extent(pc.shapes[n0:])
            if r is None or not (r.left() < u0 - 0.02 or r.right() > u1 + 0.02 or r.bottom() > v1 + 0.01):
                break
            if attempt == 3:
                scene.warnings.append('%s: "%s" at x %.2f does not fit its sheet (sheet is x %.2f..%.2f, up to %.2f high). Make it smaller'
                                      % (pc.name, name, x_in, u0, u1, v1))
                break
            # slide it back onto the sheet; shrink only when it is simply too big
            if r.width() > (u1 - u0):
                s *= (u1 - u0) / r.width() * 0.97
            elif r.left() < u0:
                x += u0 - r.left() + 0.005
            elif r.right() > u1:
                x -= r.right() - u1 + 0.005
            if r.bottom() > v1:
                over = r.bottom() - v1 + 0.005
                drop = min(over, max(r.top(), 0.0))            # lower it, but never push its foot under the floor
                y -= drop
                hgt = max(r.bottom() - (y + drop), 1e-3)
                if over - drop > 1e-4:
                    s *= max(0.3, (hgt - (over - drop)) / hgt)
            del pc.shapes[n0:]
            pc.anchors.clear()
            pc.anchors.update(keep[0])
            del pc.flows[keep[1]:]
            del scene.birds[keep[2]:]
            del scene.glows[keep[3]:]
            scene.sun = keep[4]
        if (x, y, s) != (x_in, y_in, s_in):
            ch = []
            if abs(x - x_in) > 1e-4:
                ch.append('x %.2f to %.2f' % (x_in, x))
            if abs(y - y_in) > 1e-4:
                ch.append('y %.2f to %.2f' % (y_in, y))
            if abs(s - s_in) > 1e-4:
                ch.append('s %.2f to %.2f' % (s_in, s))
            scene.fitted.append('%s: "%s" moved to fit its sheet (%s)' % (pc.name, name, ', '.join(ch)))
        if 'id' in it and it['id'] not in pc.anchors:
            b = _extent(pc.shapes[n0:], clipped=True)
            pc.anchors[it['id']] = (b.centerX(), b.centerY()) if b is not None else (x, y + s * 0.5)


def build_floor(spec, rng, title=None, slot=False):
    """The flat page: an atlas plate that is also the floor of the pop-up."""
    spec = spec or {}
    p = Piece('map', (-PW, -PH, PW, PH), res=GRES)
    p.fill(poly([(-PW, -PH), (PW, -PH), (PW, PH), (-PW, PH)]), 'paper')
    fx, fy = PW - 0.07, PH - 0.07
    frame = poly([(-fx, -fy), (fx, -fy), (fx, fy), (-fx, fy)])
    ground = spec.get('ground', 'grass')
    p.fill(frame, ground, tone=0.25)
    for _ in range(9):
        p.fill(blob(rng.uniform(-1.0, 1.0), rng.uniform(-0.8, 0.8), rng.uniform(.18, .34), rng.uniform(.12, .22), rng, 9, .2),
               ground, tone=rng.uniform(-0.05, 0.12), clip=frame)
    waters = []
    rivers = spec.get('river')
    rivers = [rivers] if isinstance(rivers, dict) else (rivers or [])
    paths = spec.get('path')
    paths = [paths] if isinstance(paths, dict) else (paths or [])
    keep = [q for r in rivers + paths for q in r['pts']]
    dots = spec.get('dots', 'leafA')
    if dots:
        for _ in range(int(spec.get('n_dots', 40))):
            cx, cy = rng.uniform(-1.08, 1.08), rng.uniform(-0.8, 0.8)
            if keep and min(np.hypot(cx - a, cy - b) for (a, b) in keep) < 0.16:
                continue
            p.fill(scallop(cx, cy, rng.uniform(.03, .05), rng.uniform(.022, .034), 6, rng), dots, tone=rng.uniform(-.1, .15), clip=frame)
    for r in paths:
        w = r.get('w', 0.08)
        ws = w if isinstance(w, list) else [w] * len(r['pts'])
        p.fill(ribbon(r['pts'], ws), r.get('mat', 'bank'), clip=frame)
    for r in rivers:
        pts = [tuple(q) for q in r['pts']]
        w = r.get('w', 0.14)
        ws = w if isinstance(w, list) else [w] * len(pts)
        p.fill(ribbon(pts, [a + 0.045 for a in ws]), r.get('bank', 'bank'), clip=frame)
        rv = ribbon(pts, ws)
        p.fill(rv, r.get('mat', 'water'), clip=frame)
        waters.append(rv)
        ol = offset_line(pts, 1)
        for off in (-0.3, 0.3):
            ln = [(pts[i][0] + (ol[i][0] - pts[i][0]) * off * ws[i], pts[i][1] + (ol[i][1] - pts[i][1]) * off * ws[i]) for i in range(len(pts))]
            p.hi(ribbon(ln, [0.012] * len(ln)), 'water', skia.Op(rv, frame, skia.kIntersect_PathOp))
        if r.get('mat', 'water') == 'water':
            for off in (-0.32, -0.12, 0.1, 0.3):
                ln = [(pts[i][0] + (ol[i][0] - pts[i][0]) * off * ws[i], pts[i][1] + (ol[i][1] - pts[i][1]) * off * ws[i]) for i in range(len(pts))]
                p.flows.append(dict(pts=ln, w=0.006, sp=0.22))
            if p.flow_axis is None:
                p.flow_axis = pts
    for pd in spec.get('ponds', []):
        b = blob(pd[0], pd[1], pd[2], pd[3], rng, 10, .1)
        p.fill(blob(pd[0], pd[1], pd[2] + .04, pd[3] + .025, rng, 10, .12), 'bank', clip=frame)
        p.fill(b, 'water', tone=0.15, clip=frame)
    # printed marks and words
    for mk in spec.get('marks', []):
        x, y = mk['at']
        r = mk.get('r', 0.05)
        c = circle(x, y, r)
        p.fill(c, mk.get('mat', 'stone'), clip=frame)
        p.line(c, w=0.0024)
    for lb in spec.get('labels', []):
        x, y = lb['at']
        tp, wd, sz = text_path(lb['text'], x, y, lb.get('size', 0.05), maxw=lb.get('maxw', 0.7))
        p.fill(tp, 'ink')
    if slot:
        pass                         # the slot is drawn by the renderer so every style can colour it
    # compass rose
    cx, cy, R = -0.93, 0.62, 0.13
    p.line(circle(cx, cy, R * 0.72), w=0.0018)
    p.line(circle(cx, cy, R * 0.78), w=0.0012)
    for k in range(8):
        a = math.pi / 2 + 2 * math.pi * k / 8
        ln = R if k % 2 == 0 else R * 0.6
        wd = 0.2 if k % 2 == 0 else 0.16
        tip = (cx + ln * math.cos(a), cy + ln * math.sin(a))
        l = (cx + ln * wd * math.cos(a + math.pi / 2), cy + ln * wd * math.sin(a + math.pi / 2))
        r = (cx + ln * wd * math.cos(a - math.pi / 2), cy + ln * wd * math.sin(a - math.pi / 2))
        p.fill(poly([(cx, cy), l, tip]), 'gold')
        p.fill(poly([(cx, cy), r, tip]), 'stoneD')
        p.line(poly([l, tip, r], False), w=0.0014)
    # cartouche with the title
    if title:
        lines = wrap_text(title, 22)[:2]
        x0, x1 = 0.44, 1.08
        y1 = 0.79
        y0 = y1 - 0.075 - 0.075 * len(lines)
        cart = rrect(x0, y0, x1, y1, 0.03)
        p.fill(cart, 'paper')
        p.line(cart, w=0.003)
        p.line(rrect(x0 + .014, y0 + .014, x1 - .014, y1 - .014, 0.02), w=0.0014)
        for i, ln in enumerate(lines):
            tp, wd, sz = text_path(ln, (x0 + x1) / 2, y1 - 0.085 - 0.075 * i, 0.058, maxw=x1 - x0 - 0.09)
            p.fill(tp, 'ink')
    # frame lines and ticks
    p.line(frame, w=0.004)
    p.line(poly([(-fx - .02, -fy - .02), (fx + .02, -fy - .02), (fx + .02, fy + .02), (-fx - .02, fy + .02)]), w=0.0016)
    for k in range(1, 24):
        x = -fx + 2 * fx * k / 24
        for yy, s in ((fy, 1), (-fy, -1)):
            p.line(poly([(x, yy), (x, yy + s * (0.02 if k % 2 else 0.012))], False), w=0.0014)
    for k in range(1, 18):
        y = -fy + 2 * fy * k / 18
        for xx_, s in ((fx, 1), (-fx, -1)):
            p.line(poly([(xx_, y), (xx_ + s * (0.02 if k % 2 else 0.012), y)], False), w=0.0014)
    return p


COVERS = ['#22505f', '#7a2e2e', '#2f5d3a', '#b7791f', '#5b3a6e', '#1f3a68', '#a4502a', '#46525e']


def cover_of(story):
    """-> (cover colour, picture on the cover or None). No colour given: one is picked from the title, so books differ."""
    cv = story.get('cover') or {}
    if isinstance(cv, str):
        cv = {'colour': cv}
    colr = cv.get('colour') or cv.get('color')
    if not colr:
        colr = COVERS[int(hashlib.sha1((story.get('title') or '').encode()).hexdigest(), 16) % len(COVERS)]
    return norm_mat(colr), cv.get('piece')


def build_front(rng, title, story=None):
    """The front cover, seen while the book is closed: cloth board, gilt frame, a picture and a pasted paper label with the title."""
    m = 0.04
    colr, emblem = cover_of(story or {})
    p = Piece('jacket', (0, -PH - m, PW + m, PH + m), res=GRES)
    p.fill(rrect(0, -PH - m, PW + m, PH + m, 0.02), colr)
    p.line(rrect(0.075, -PH - m + 0.075, PW + m - 0.075, PH + m - 0.075, 0.03), w=0.006, mat='gold')
    p.line(rrect(0.105, -PH - m + 0.105, PW + m - 0.105, PH + m - 0.105, 0.02), w=0.0022, mat='gold')
    p.line(poly([(0.035, -PH - m + 0.02), (0.035, PH + m - 0.02)], False), w=0.004, mat='gold')
    cx = (PW + m) / 2
    lines = wrap_text(title or '', 16)[:3]
    n = max(len(lines), 1)
    sy, r = 0.50, 0.17
    if emblem:
        # a picture from the story itself, pasted on the cover
        it = dict(emblem) if isinstance(emblem, dict) else {'use': emblem}
        probe = Piece('probe', (-9, -9, 9, 9), res=8)
        it.update(x=0.0, y=0.0, s=1.0)
        it.pop('id', None)
        _place(Scene(), probe, [it], (story or {}).get('pieces', {}), np.random.default_rng(3), 1.0)
        r = _extent(probe.shapes)
        if r is not None:                                  # as big as fits the space above the label
            es = min(0.78 / max(r.width(), 1e-3), 0.50 / max(r.height(), 1e-3))
            it.update(x=cx - es * r.centerX(), y=sy + 0.02 - es * r.centerY(), s=es)
            _place(Scene(), p, [it], (story or {}).get('pieces', {}), np.random.default_rng(3), 1.0)
    else:
        # a plain gilt sun
        for k in range(16):
            a = 2 * math.pi * k / 16
            r0, r1 = r * 1.16, r * (1.36 if k % 2 else 1.56)
            p.line(poly([(cx + r0 * math.cos(a), sy + r0 * math.sin(a)), (cx + r1 * math.cos(a), sy + r1 * math.sin(a))], False), w=0.007, mat='gold')
        disc = circle(cx, sy, r)
        p.fill(disc, 'gold')
        p.fill(blob(cx - .05, sy + .05, .055, .04, rng, 8, .2), 'moon', clip=disc)
        p.fill(blob(cx + .06, sy - .04, .035, .045, rng, 8, .2), 'moon', clip=disc)
    # the label
    hh = 0.085 + 0.065 * n
    ly = -0.16
    plate = rrect(cx - 0.47, ly - hh, cx + 0.47, ly + hh, 0.03)
    p.fill(plate, 'paper')
    p.line(rrect(cx - 0.445, ly - hh + 0.025, cx + 0.445, ly + hh - 0.025, 0.02), w=0.0018)
    for i, ln in enumerate(lines):
        tp, wd, sz = text_path(ln, cx, ly + 0.13 * (n - 1) / 2 - 0.13 * i - 0.034, 0.105, maxw=0.80)
        p.fill(tp, 'ink')
    for k in range(2):
        w = 0.16 + 0.07 * k
        yy = ly - hh - 0.11 - 0.05 * k
        p.line(spline([(cx - w, yy), (cx - w / 2, yy + .012), (cx, yy), (cx + w / 2, yy - .012), (cx + w, yy)]), w=0.004, mat='gold')
    return p


def build_cover(story=None):
    m = 0.04
    p = Piece('cover', (-PW - m, -PH - m, PW + m, PH + m), res=GRES // 2)
    p.fill(rrect(-PW - m, -PH - m, PW + m, PH + m, 0.02), cover_of(story or {})[0])
    p.line(rrect(-PW - m + .012, -PH - m + .012, PW + m - .012, PH + m - .012, 0.012), w=0.004, mat='gold')
    return p


def build_tab():
    p = Piece('tab', (0, -0.055, 0.78, 0.055), res=GRES)
    body = rrect(-0.1, -0.045, 0.77, 0.045, 0.03)
    p.fill(body, 'tab')
    p.fill(poly([(0.72, 0.0), (0.68, 0.022), (0.68, 0.009), (0.6, 0.009), (0.6, -0.009), (0.68, -0.009), (0.68, -0.022)]), 'water')
    for x0 in (0.52, 0.545, 0.57):
        p.line(poly([(x0, -0.022), (x0, 0.022)], False), w=0.003)
    p.line(rrect(-0.1, -0.035, 0.76, 0.035, 0.022), w=0.0016)
    return p


def build_scene(page, story, index=0):
    """page: one entry of story['pages']. Returns a Scene."""
    rng = np.random.default_rng(story.get('seed', 7) * 101 + index)
    recipes = story.get('pieces', {})
    sc = Scene()
    life = page.get('life', {})
    sc.mist = life.get('mist', True)
    sc.n_birds = int(life.get('birds', 6))
    sc.focus = {'left': -1.0, 'right': 1.0, 'centre': 0.0, 'center': 0.0}.get(page.get('focus', 'centre'), 0.0)
    lock = 0
    for nm in LAYERS:
        items = page.get(nm)
        if not items:
            continue
        sl = SLOTS[nm]
        pc = Piece(nm, sl['bbox'], y0=sl['y0'], alpha=sl['alpha'], side=sl['side'], lock=lock, depth=sl['depth'])
        lock += 1
        _place(sc, pc, items, recipes, rng, 1.0 / math.sin(math.radians(sl['alpha'])))
        if not any(s.kind == 'fill' for s in pc.shapes):
            continue
        sc.pcs[nm] = pc
        sc.order.append(nm)
    # side sheets are held parallel by a paper tab to the sheet behind them
    for nm in ('left', 'right'):
        if nm in sc.pcs:
            par = 'mid' if 'mid' in sc.pcs else 'back' if 'back' in sc.pcs else None
            if par:
                pc = sc.pcs[nm]
                best = None
                for it in page.get(nm):
                    if isinstance(it, dict) and 'x' in it and (best is None or it.get('s', 0.3) > best.get('s', 0.3)):
                        best = it
                u = best['x'] if best else (pc.bbox[0] + pc.bbox[2]) / 2
                sc.tabs.append((nm, par, [(u, 0.035)]))
    sl = page.get('slider')
    if sl:
        s = sl.get('s', 0.11)
        pc = Piece('slider', (-0.17, 0, 0.17, max(0.125, s * 1.25)), lock=lock, depth=0.9)
        it = dict(sl)
        it['x'], it['y'] = 0.0, 0.012
        _place(sc, pc, [it], recipes, rng, 1.0)
        pc.slider = dict(x0=sl.get('from', 0.17), x1=sl.get('to', 0.60), y=SLOT_Y)
        sc.pcs['slider'] = pc
        sc.slider = 'slider'
        if 'front' in sc.order:
            sc.order.insert(sc.order.index('front'), 'slider')
        else:
            sc.order.append('slider')
    for k, fl in enumerate(page.get('fly', [])):
        s = fl.get('s', 0.06)
        pc = Piece('fly%d' % k, (-s * 0.9, 0, s * 0.9, s * 1.3), depth=0.9)
        it = dict(fl)
        it['x'], it['y'], it['s'] = 0.0, s * 0.1, s
        _place(sc, pc, [it], recipes, rng, 1.0)
        sc.pcs[pc.name] = pc
        sc.flyers.append(dict(piece=pc.name, src=fl['from'], dst=fl['to'], at=fl.get('at', 0.6), secs=fl.get('secs', 2.5),
                              n=int(fl.get('n', 1)), arc=fl.get('arc', 0.12), loop=fl.get('loop', True)))
    # does the page look full? (the camera frames the whole sheet, so small pieces leave it empty)
    best = 0.0
    for nm in sc.order:
        pc = sc.pcs[nm]
        if pc.slider:
            continue
        top = max((sh.path.computeTightBounds().bottom() for sh in pc.shapes if sh.kind == 'fill'), default=0.0)
        best = max(best, top)
    if sc.order and best < 0.7:
        sc.warnings.append('page looks empty: nothing stands taller than %.2f. Put the main piece on far, left or right and make it 0.7 to 0.85 tall' % best)
    for fl in page.get('fly', []):
        if fl.get('s', 0.06) < 0.09:
            sc.warnings.append('flying "%s" is tiny (s %.2f). Use 0.1 or more so it can be seen' % (fl.get('use'), fl.get('s', 0.06)))
    ground = norm_mat((page.get('floor') or {}).get('ground', 'grass'))
    for nm in ('far', 'back'):
        for it in page.get(nm) or []:
            if isinstance(it, dict) and it.get('use') == 'hills' and norm_mat(it.get('mat', 'rockA')) in (ground, norm_mat('leafLight') if ground == 'grass' else ground):
                sc.warnings.append('%s: hills are the same colour as the floor and will not show. Pick a different colour' % nm)
    title = story.get('title')
    sc.pcs['map'] = build_floor(page.get('floor'), rng, page.get('caption'), slot=bool(sl))
    sc.pcs['jacket'] = build_front(np.random.default_rng(3), title, story)
    sc.pcs['cover'] = build_cover(story)
    sc.pcs['tab'] = build_tab()
    sc.birds = sc.birds[:sc.n_birds]
    return sc
