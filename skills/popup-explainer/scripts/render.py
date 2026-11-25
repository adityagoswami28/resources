"""Frame renderer: paper-fold kinematics, camera, shadows and the 'life' animation.
Each art style plugs in through a small set of hooks (see styles.py).
A Timeline strings the pages together: the film starts on the closed book, the front cover swings open and the first
pop-up rises, each page turns over to the next (the old pop-up folds into the turning leaf while the new one rises
behind it), and at the end the book closes again, cover up."""
import math
import os
import numpy as np
import skia
from core import *
import kit as SC

# ----------------------------------------------------------------- timeline (seconds)
T_START = 1.0                        # the closed book, held before the cover opens
T_OPEN0, T_OPEN1 = 2.75, 4.50
T_LOCK0, T_LOCK_DT = 4.42, 0.085
T_LIFE = 5.0
T_CLOSE = 1.05                       # the book closing after the last page
T_END = 1.1                          # the closed book, held at the very end
T_SAY = 0.7                          # narration starts this long after a page begins to turn
TS, CT, BT = 0.07, 0.016, 0.012      # page stack, cover, board thickness
ZD = -(TS + CT)
TB = TS + CT                         # the block that swings with the front cover: first leaf, pages, cover board
CM = 0.04                            # how far the cover boards stick out past the pages


def lock_time(i):
    return T_LOCK0 + T_LOCK_DT * i


def slide_s(t, t_end):
    return smoother(ramp(t, 5.5, min(9.2, max(t_end - 0.3, 7.0))))


def cam_params(t, t_end, focus=0.0):
    """Camera for one page in its own clock: wide while it opens, then a slow push-in for as long as it is held."""
    push = max(t_end, 8.3)
    fx = 0.30 * focus
    keys = [  # t, target x, y, z, elev, az, dist
        (0.0, 0.0, 0.0, 0.0, 52, -3.0, 5.35),
        (2.7, 0.0, -0.02, 0.0, 49, -2.0, 5.15),
        (4.9, 0.0, -0.22, 0.26, 31, 0.0, 4.75),
        (6.3, fx * 0.3, -0.25, 0.28, 30, 0.8 - focus, 4.6),
        (push, fx, -0.40, 0.36, 24, 2.6 - 3.0 * focus, 3.42),
        (push + 1.0, fx, -0.40, 0.36, 23.7, 3.0 - 3.0 * focus, 3.36),
    ]
    for i in range(len(keys) - 1):
        a, b = keys[i], keys[i + 1]
        if t <= b[0] or i == len(keys) - 2:
            k = smooth(ramp(t, a[0], b[0]))
            return tuple(lerp(a[j], b[j], k) for j in range(1, 7))


class Timeline:
    """Global film time -> which page is showing and where it is in its own choreography.
    Page 0 starts on the closed book and opens with the front cover. Every later page arrives by a page turn:
    while its leaf swings over, the page before it is still on screen, folding away ('prev').
    After the last page the cover swings back and the film ends on the closed book."""

    def __init__(self, says, focus=None):
        """says: seconds of narration for each page."""
        self.pages = []
        g = 0.0
        n = len(says)
        for i, d in enumerate(says):
            last = i == n - 1
            if i == 0:
                g0, tl0, say = 0.0, T_OPEN0 - T_START, T_START + 0.35
                open_done = T_START + (T_OPEN1 - T_OPEN0)
                hold = max(say + d + 0.7 - open_done, 3.6)
            else:
                g0, tl0, say = g, T_OPEN0, g + T_SAY
                hold = max(T_SAY + d + 0.7 - (T_OPEN1 - T_OPEN0), 3.2)
                open_done = g + (T_OPEN1 - T_OPEN0)
            hold_end = open_done + hold + (0.5 if last else 0.0)
            end = hold_end + (T_CLOSE + T_END if last else 0.0)
            self.pages.append(dict(g0=g0, tl0=tl0, say=say, hold_end=hold_end, end=end, last=last,
                                   tl_end=tl0 + hold_end - g0, focus=(focus or [0.0] * n)[i]))
            g = end
        self.total = g

    def at(self, tg):
        i = 0
        while i < len(self.pages) - 1 and tg >= self.pages[i]['end']:
            i += 1
        p = self.pages[i]
        tl = p['tl0'] + tg - p['g0']
        closing = ramp(tg, p['hold_end'], p['hold_end'] + T_CLOSE) if p['last'] else 0.0
        opening = ramp(tl, T_OPEN0, T_OPEN1)
        theta = math.pi * smooth(opening)
        cp = cam_params(min(tl, p['tl_end']), p['tl_end'], p['focus'])
        prev = None
        if i > 0 and tl < T_OPEN1:
            q = self.pages[i - 1]
            prev = dict(page=i - 1, tl=q['tl_end'] + tg - q['hold_end'], tl_end=q['tl_end'], closing=opening)
            was = cam_params(q['tl_end'], q['tl_end'], q['focus'])
            k = smooth(ramp(tl, T_OPEN0, T_OPEN0 + 1.3))
            cp = tuple(lerp(a, b, k) for a, b in zip(was, cp))
        shut = 1 - smooth(ramp(tl, T_OPEN0 - 0.1, T_OPEN1 - 0.25)) if i == 0 else 0.0
        if closing > 0:
            theta = math.pi * (1 - smooth(closing))
            wide = cam_params(T_OPEN0, 99.0)
            k = smooth(ramp(tg, p['hold_end'], p['hold_end'] + T_CLOSE + 0.6))
            cp = tuple(lerp(a, b, k) for a, b in zip(cp, wide))
            shut = smooth(ramp(tg, p['hold_end'] + 0.15, p['hold_end'] + T_CLOSE + 0.45))
        # the closed book lies on the right half: the camera sits over it, and glides to the middle as it opens
        cp = (cp[0] + 0.60 * shut, cp[1], cp[2], cp[3], cp[4], cp[5] - 0.95 * shut)
        return dict(page=i, tl=tl, theta=theta, closing=closing, opening=opening, tl_end=p['tl_end'], prev=prev,
                    cam=Camera(cp[0:3], cp[3], cp[4], cp[5], 30))


class TurnedCam:
    """The same camera, as seen from a frame that has been turned about the spine by ang.
    Lets a whole spread be drawn rotated: its right page becomes the leaf that is swinging over."""

    def __init__(self, cam, ang):
        cs, sn = math.cos(ang), math.sin(ang)
        self.R = np.array([[cs, 0, -sn], [0, 1, 0], [sn, 0, cs]])
        M = np.eye(4)
        M[:3, :3] = self.R
        self.P = cam.P @ M
        self.pos = self.R.T @ cam.pos
        self.fwd = self.R.T @ cam.fwd
        self.fl = cam.fl

    proj = Camera.proj
    plane = Camera.plane


class FlatCam:
    """Looks straight down on one half of the floor, so that half can be painted flat into its own picture
    (art, printed marks and the shadows that fall on it) and then laid onto a bending leaf."""

    def __init__(self, e1, e2, n, x0, y1, res):
        self.P = np.zeros((3, 4))
        self.P[0, :3], self.P[0, 3] = e1 * res, -x0 * res
        self.P[1, :3], self.P[1, 3] = -e2 * res, y1 * res
        self.P[2, 3] = 1.0
        self.pos = n * 50.0
        self.fwd = -n
        self.fl = res

    proj = Camera.proj
    plane = Camera.plane


def reach(sc, right):
    """How far from the spine the standing pieces of a page touch the floor on one side."""
    m = 0.0
    for nm in sc.order:
        pc = sc.pcs[nm]
        if pc.slider:
            if right:
                m = max(m, pc.slider['x1'] + 0.2)
            continue
        sa = math.sin(math.radians(pc.alpha))
        for sh in pc.shapes:
            if sh.kind == 'fill':
                r = sh.path.computeTightBounds()
                m = max(m, (r.right() if right else -r.left()) * sa)
    return m


class Panel:
    def __init__(self, cam, O, U, V, src, T, name=None, light=None, amb=0.7, dif=0.4, texw=None):
        self.O, self.U, self.V, self.src, self.T, self.name = O, U, V, src, T, name
        self.texw = texw if texw is not None else src[2]
        self.Hp = cam.plane(O, U, V)             # plane coords -> screen
        self.M = self.Hp @ T                     # texture px -> screen
        x0, y0, x1, y1 = src
        pts = []
        for (px, py) in ((x0, y0), (x1, y0), (x1, y1), (x0, y1)):
            h = self.M @ np.array([px, py, 1.0])
            pts.append((h[0] / h[2], h[1] / h[2]))
        self.quad = pts
        c = T @ np.array([(x0 + x1) / 2, (y0 + y1) / 2, 1.0])
        self.center = O + U * c[0] + V * c[1]
        n = np.cross(U, V)
        n /= np.linalg.norm(n) + 1e-12
        if n.dot(cam.pos - self.center) < 0:
            n = -n
        self.n = n
        self.b = 1.0
        if light is not None:
            l = light - self.center
            l /= np.linalg.norm(l)
            self.b = min(1.12, amb + dif * max(0.0, n.dot(l)))

    def rect(self):
        return skia.Rect.MakeLTRB(*self.src)

    def quad_path(self):
        p = skia.Path()
        p.moveTo(*self.quad[0])
        for q in self.quad[1:]:
            p.lineTo(*q)
        p.close()
        return p

    def bounds(self, pad=3):
        xs = [q[0] for q in self.quad]
        ys = [q[1] for q in self.quad]
        return [min(xs) - pad, min(ys) - pad, max(xs) + pad, max(ys) + pad]


def union_bounds(panels, pad=3):
    bs = [p.bounds(pad) for p in panels]
    r = skia.Rect.MakeLTRB(max(min(b[0] for b in bs), 0), max(min(b[1] for b in bs), 0),
                           min(max(b[2] for b in bs), W), min(max(b[3] for b in bs), H))
    return r


class Renderer:
    def __init__(self, scenes, style, cache_dir, timeline):
        """scenes: one Scene per page. style: style name or number. Page textures are loaded only while needed."""
        self.scenes, self.style, self.cache_dir, self.tline = scenes, style, cache_dir, timeline
        self.loaded = {}
        self.common = None
        self.cur = None
        self.rel = 1.0
        self.tl_end = 10.0
        self.reaches = {}
        self.bend = None

    def page_style(self, i):
        from styles import get_style
        if i not in self.loaded:
            for k in [k for k in self.loaded if abs(k - i) > 1]:
                del self.loaded[k]
            st = get_style(self.style, self.scenes[i], os.path.join(self.cache_dir, 'page%d.npz' % i),
                           os.path.join(self.cache_dir, 'common.npz'))
            if self.common is None:
                st.load(dict(np.load(st.common)))
                self.common = (dict(st.img), st.bg)
                # one shared page back, so the cut between two pages cannot be seen
                self.common[0]['pageback/art'] = to_image(np.load(os.path.join(self.cache_dir, 'page0.npz'))['pageback/art'])
            data = dict(np.load(st.cache))
            st.load(data)
            # the colour the cover was painted in this look, for the edges of the boards
            cv = data['cover/art']
            h, w = cv.shape[:2]
            st.cover_rgb = tuple(float(x) for x in np.median(cv[h // 3:2 * h // 3, w // 8:3 * w // 8, :3].reshape(-1, 3), axis=0))
            st.img.update(self.common[0])
            st.bg = self.common[1]
            self.loaded[i] = st
        return self.loaded[i]

    def use(self, i):
        if self.cur == i:
            return
        self.cur = i
        self.st = self.page_style(i)
        self.sc = self.scenes[i]
        self.pcs = self.sc.pcs
        rng = np.random.default_rng(11 + i)
        n = max(len(self.sc.order), 1)
        self.mist = [dict(slot=int(rng.integers(0, n)), x=rng.uniform(-0.8, 0.8), z=rng.uniform(0.03, 0.3),
                          w=rng.uniform(0.5, 0.9), ph=rng.uniform(0, 1), k=int(rng.integers(0, 3)),
                          sp=rng.uniform(0.6, 1.2)) for _ in range(13)]
        self.birds = []
        for k, (pn, an) in enumerate(self.sc.birds):
            self.birds.append(dict(piece=pn, anchor=an, t0=5.35 + 0.16 * k + rng.uniform(-0.05, 0.05),
                                   vx=rng.uniform(-0.28, 0.34), vy=rng.uniform(-0.12, 0.06), vz=rng.uniform(0.14, 0.22),
                                   ph=rng.uniform(0, 6.28), f=rng.uniform(3.2, 4.2), s=rng.uniform(0.85, 1.15)))
        self.flies = [dict(x=rng.uniform(-1.05, 1.05), y=rng.uniform(-0.9, -0.1), z0=rng.uniform(0.0, 0.25),
                           t0=5.6 + rng.uniform(0, 2.6), sp=rng.uniform(0.05, 0.12), ph=rng.uniform(0, 6.28),
                           fr=rng.uniform(0.5, 1.3)) for _ in range(46)]

    # ------------------------------------------------------------- kinematics
    def piece_panels(self, cam, pc, theta, t):
        st = self.st
        z, om, dl = st.feel
        dl = math.radians(dl)
        u0, v0, u1, v1 = pc.bbox
        w, h = pc.size
        T = tex_to_plane(u0, v1, pc.res)
        if pc.slider:
            gi = fold_axes(theta, 80)[3]
            g = min(gi, math.pi / 2 - dl) + dl * spring_step(t - lock_time(pc.lock), z, om) * self.rel
            if theta < 1e-6:
                g = 0.0
            c = math.cos(g) * YH + math.sin(g) * ZH
            x = lerp(pc.slider['x0'], pc.slider['x1'], slide_s(t, self.tl_end))
            return [Panel(cam, v3(x, pc.slider['y'], 0), v3(1, 0, 0), c, (0, 0, w, h), T, pc.name, st.lamp, st.amb, st.dif, w)]
        gi = fold_axes(theta, pc.alpha)[3]
        g = min(gi, math.pi / 2 - dl) + dl * spring_step(t - lock_time(pc.lock), z, om) * self.rel
        g_r, g_l, c, _ = fold_axes(theta, pc.alpha, gamma=g)
        O = v3(0, pc.y0, 0)
        out = []
        if pc.side in ('both', 'R') and u1 > 0:
            out.append(Panel(cam, O, g_r, c, ((max(u0, 0) - u0) * pc.res, 0, w, h), T, pc.name, st.lamp, st.amb, st.dif, w))
        if pc.side in ('both', 'L') and u0 < 0:
            out.append(Panel(cam, O, -g_l, c, (0, 0, (min(u1, 0) - u0) * pc.res, h), T, pc.name, st.lamp, st.amb, st.dif, w))
        return out

    # ------------------------------------------------------------- drawing helpers
    def draw_tex_panel(self, c, pn, name, t, shade=True):
        c.save()
        c.concat(skm(pn.M))
        r = pn.rect()
        c.clipRect(r, True)
        self.st.draw_art(c, name, r, t, pn)
        if shade:
            b = pn.b
            if b < 0.995:
                tint = self.st.sh_col
                c.drawRect(r, skia.Paint(Color=skia.Color(tint[0], tint[1], tint[2], int(255 * min(1 - b, 1) )),
                                         BlendMode=skia.BlendMode.kSrcATop))
            elif b > 1.005:
                c.drawRect(r, skia.Paint(Color=skia.Color(255, 250, 235, int(255 * min(b - 1, 1) * 0.8)),
                                         BlendMode=skia.BlendMode.kSrcATop))
        c.restore()

    def cast(self, c, recv, casters, light, alpha, soft=1):
        """Draw shadows of caster panels onto receiver panel (inside the receiver's layer)."""
        if alpha <= 0.003:
            return
        pa = skia.Paint(BlendMode=skia.BlendMode.kSrcATop, Alphaf=alpha)
        rb = recv.bounds(0)
        for cp in casters:
            sh = self.st.shadow(cp.name, soft)
            if sh is None:
                continue
            img, T_sh, (sw, shh) = sh
            # shadow src rect matching the caster panel half
            A = np.linalg.inv(T_sh) @ cp.T
            x0, y0, x1, y1 = cp.src
            sx0 = A[0, 0] * x0 + A[0, 2]
            sx1 = A[0, 0] * x1 + A[0, 2]
            if x0 <= 0.5:
                sx0 = 0
            if x1 >= cp.texw - 0.5:
                sx1 = sw
            # keep only the part of the caster below the light
            vz = cp.V[2]
            sy0 = 0.0
            if vz > 1e-3:
                vmax = (light[2] - 0.04 - cp.O[2]) / vz
                py = (T_sh[1, 2] - vmax) / (-T_sh[1, 1])
                sy0 = max(0.0, py)
            if sy0 >= shh - 1:
                continue
            Hs = shadow_h(light, cp.O, cp.U, cp.V, recv.O, recv.U, recv.V)
            M = recv.Hp @ Hs @ T_sh
            # cull by projected bounds
            xs, ys, ok = [], [], True
            for (px, py) in ((sx0, sy0), (sx1, sy0), (sx1, shh), (sx0, shh)):
                hh = M @ np.array([px, py, 1.0])
                if abs(hh[2]) < 1e-9:
                    ok = False
                    break
                xs.append(hh[0] / hh[2])
                ys.append(hh[1] / hh[2])
            if ok and (max(xs) < rb[0] or min(xs) > rb[2] or max(ys) < rb[1] or min(ys) > rb[3]):
                continue
            c.save()
            c.clipPath(recv.quad_path(), True)
            c.concat(skm(M))
            src = skia.Rect.MakeLTRB(sx0, sy0, sx1, shh)
            c.drawImageRect(img, src, src, SAMP_L, pa)
            c.restore()

    def quad3(self, cam, pts):
        p = skia.Path()
        for i, q in enumerate(pts):
            x, y, _ = cam.proj(np.asarray(q, float))
            if i == 0:
                p.moveTo(x, y)
            else:
                p.lineTo(x, y)
        p.close()
        return p

    def flow(self, c, Hp, flows, t, amt, clip=None, scale=1.0):
        if amt <= 0.01:
            return
        st = self.st
        c.save()
        c.concat(skm(Hp))
        if clip is not None:
            c.clipRect(clip, True)
        for i, f in enumerate(flows):
            pa = skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=f['w'] * st.flow_w * scale,
                            StrokeCap=skia.Paint.kRound_Cap, Color=col(st.flow_col, 255 * st.flow_a * amt))
            if st.flow_blend is not None:
                pa.setBlendMode(st.flow_blend)
            on, off = 0.035 + 0.012 * (i % 3), 0.05 + 0.014 * ((i * 2) % 3)
            pa.setPathEffect(skia.DashPathEffect.Make([on, off], -t * f['sp'] - i * 0.031))
            c.drawPath(SC.spline(f['pts']), pa)
        c.restore()

    # ------------------------------------------------------------- a turning leaf, bending where it is free paper
    def leaf_mesh(self, c, cam, img, res_t, front, base):
        """Lay one face of the turning leaf onto the picture. img: that half of the floor, painted flat.
        front: the face whose normal is +z when the leaf lies on the right (the old page); else the back (the new page).
        base: the leaf's angle in this frame. Out to x_c the leaf is stiff; beyond it the paper lags behind the turn,
        and the near corner peels up first."""
        st = self.st
        x_c, p, phi = self.bend
        d = np.concatenate([np.linspace(0, x_c, 15), np.linspace(x_c, PW, 17)[1:]])
        yy = np.linspace(-PH, PH, 13)
        Dg, Yg = np.meshgrid(d, yy)
        u = np.clip((Dg - x_c) / (PW - x_c), 0, 1)
        yn = Yg / PH
        lag = 1.05 * math.sin(math.pi * p) ** 0.9
        lead = 0.7 * math.sin(math.pi * clamp(p / 0.42)) ** 1.2
        delta = u * u * (lag * (1 + 0.3 * yn) - lead * (1 - yn) / 2)
        a = base + (np.clip(phi - delta, 0.0, math.pi) - phi)
        cx, sz = np.cos(a), np.sin(a)
        dd = np.diff(d)[None, :]
        X = np.zeros_like(a)
        Z = np.zeros_like(a)
        X[:, 1:] = np.cumsum((cx[:, 1:] + cx[:, :-1]) / 2 * dd, axis=1)
        Z[:, 1:] = np.cumsum((sz[:, 1:] + sz[:, :-1]) / 2 * dd, axis=1)
        P3 = np.stack([X, Yg, Z], axis=-1)
        N = np.stack([-sz, np.zeros_like(sz), cx], axis=-1)
        if not front:
            N = -N
        hom = P3 @ cam.P[:, :3].T + cam.P[:, 3]
        scr = hom[..., :2] / hom[..., 2:3]
        facing = (N * (cam.pos - P3)).sum(-1)
        Ld = st.lamp - P3[:, :1]
        Ld = Ld / np.linalg.norm(Ld, axis=-1, keepdims=True)
        ndl = np.maximum((N * Ld).sum(-1), 0.0)
        shade = np.clip(1.0 + st.dif * 1.3 * (ndl - ndl[:, :1]), 0.62, 1.0)
        x0, y0 = scr[..., 0].min() - 4, scr[..., 1].min() - 4
        x1, y1 = scr[..., 0].max() + 4, scr[..., 1].max() + 4
        x0, y0, x1, y1 = max(x0, -400), max(y0, -400), min(x1, W + 400), min(y1, H + 400)
        if x1 - x0 < 2 or y1 - y0 < 2:
            return
        SSF = 2
        surf, arr = new_surface(int((x1 - x0) * SSF) + 2, int((y1 - y0) * SSF) + 2)
        oc = surf.getCanvas()
        depth = hom[..., 2]
        ny, nx = len(yy) - 1, len(d) - 1
        tris = []
        for j in range(ny):
            for i in range(nx):
                for tri in (((j, i), (j, i + 1), (j + 1, i + 1)), ((j, i), (j + 1, i + 1), (j + 1, i))):
                    if sum(facing[q] for q in tri) > 0:
                        tris.append((sum(depth[q] for q in tri), tri))
        if not tris:
            return
        tris.sort(key=lambda q: -q[0])
        tw, th = img.width(), img.height()
        pos, tex, cols = [], [], []
        for _, tri in tris:
            for q in tri:
                pos.append(skia.Point(float((scr[q][0] - x0) * SSF), float((scr[q][1] - y0) * SSF)))
                dq = d[q[1]]
                tex.append(skia.Point(float(min((dq if front else PW - dq) * res_t, tw - 0.5)), float(min((PH - yy[q[0]]) * res_t, th - 0.5))))
                g = int(255 * shade[q])
                cols.append(skia.Color(g, g, g, 255))
        pa = skia.Paint()
        pa.setShader(img.makeShader(skia.TileMode.kClamp, skia.TileMode.kClamp, SAMP_L))
        oc.drawVertices(skia.Vertices(skia.Vertices.kTriangles_VertexMode, pos, tex, cols), pa, skia.BlendMode.kModulate)
        c.save()
        c.translate(x0, y0)
        c.scale(1 / SSF, 1 / SSF)
        c.drawImage(to_image(arr, mip=True), 0, 0, SAMP, skia.Paint())
        c.restore()

    # ------------------------------------------------------------- one frame
    def enter(self, page, t, theta, tl_end, closing, turned=None):
        """Make one page the current one, in its own clock. turned: the frame rotation when it is drawn on a turning leaf."""
        self.use(page)
        st = self.st
        self.theta, self.tl_end = theta, tl_end
        self.rel = 1 - smooth(ramp(closing, 0.0, 0.3))
        st.pace = clamp((tl_end - 5.2) / 3.6, 0.45, 1.0)
        st.tl_end = tl_end
        st.__dict__.pop('lamp', None)
        world = st.lamp
        if turned is not None:
            st.lamp = turned.T @ world                 # the desk lamp, seen from the turned frame
        st.shadow_light = st.lamp
        st.begin(t, theta)
        return st

    def flat_fn(self, cam):
        def flat(name, O, U, V, src=None, bbox=None, res=None):
            st = self.st
            pc = self.pcs.get(name)
            bb = bbox or pc.bbox
            rs = res or pc.res
            if src is None:
                src = (0, 0, int(round((bb[2] - bb[0]) * rs)), int(round((bb[3] - bb[1]) * rs)))
            return Panel(cam, O, U, V, src, tex_to_plane(bb[0], bb[3], rs), name, st.lamp, st.amb, st.dif)
        return flat

    def frame(self, tg):
        stt = self.tline.at(tg)
        prev = stt['prev']
        t, theta, cam = stt['tl'], stt['theta'], stt['cam']
        st = self.enter(stt['page'], t, theta, stt['tl_end'], stt['closing'])
        # the front cover, with the pages stacked on it, lies flat on the left unless the book is opening or closing
        flat_left = prev is not None or theta >= math.pi - 1e-4
        surf, arr = new_surface(W, H)
        c = surf.getCanvas()
        c.clear(col(st.bg))
        lamp = st.lamp
        AA = skia.Paint(AntiAlias=True)
        flat = self.flat_fn(cam)

        X, Y = v3(1, 0, 0), v3(0, 1, 0)
        # ---- desk
        dk = flat('desk', v3(0, 0, ZD), X, Y, bbox=st.desk_bbox, res=st.desk_res)
        c.save()
        c.concat(skm(dk.M))
        st.draw_art(c, 'desk', dk.rect(), t, dk)
        c.restore()
        # ---- cover boards and page stacks that rest on the desk
        m = CM
        xl = -PW - m if flat_left else 0.0
        cv_dark = col(mix(st.cover_rgb, (0, 0, 0), 0.35))
        if st.sh_alpha > 0:
            pa = skia.Paint(AntiAlias=True, Color=col(st.sh_col, 255 * st.sh_alpha * 0.9))
            pa.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 14))
            dx, dy = st.book_shadow
            hi = 0.0 if flat_left else TB * (1 - theta / math.pi)       # a closed book stands taller, so its shadow reaches further
            c.drawPath(self.quad3(cam, [(xl + dx, -PH - m + dy * 0.2, ZD), (PW + m + dx + hi, -PH - m + dy * 0.2, ZD),
                                        (PW + m + dx + hi, PH + m + dy + hi, ZD), (xl + dx, PH + m + dy + hi, ZD)]), pa)
        if not flat_left and cam.pos[0] < 0:
            c.drawPath(self.quad3(cam, [(0, -PH - m, ZD), (0, PH + m, ZD), (0, PH + m, 0), (0, -PH - m, 0)]), skia.Paint(AntiAlias=True, Color=cv_dark))
        c.drawPath(self.quad3(cam, [(xl, -PH - m, ZD), (PW + m, -PH - m, ZD), (PW + m, -PH - m, -TS), (xl, -PH - m, -TS)]),
                   skia.Paint(AntiAlias=True, Color=cv_dark))
        cw, ch = self.pcs['cover'].size
        cv = flat('cover', v3(0, 0, -TS), X, Y, src=None if flat_left else (cw / 2, 0, cw, ch))
        self.draw_tex_panel(c, cv, 'cover', t)
        edge = st.pal_rgb['paper']
        for (xa, xb, zt) in ((-PW, 0, -BT), (0, PW, 0.0)):
            if xa < 0 and not flat_left:
                continue
            q = [(xa, -PH, -TS), (xb, -PH, -TS), (xb, -PH, zt), (xa, -PH, zt)]
            c.drawPath(self.quad3(cam, q), skia.Paint(AntiAlias=True, Color=col(mix(edge, st.sh_col, 0.22))))
            lp = skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=1.0, Color=col(mix(edge, st.sh_col, 0.45), 150))
            for k in range(1, 6):
                zz = lerp(-TS, zt, k / 6)
                a = cam.proj(v3(xa, -PH, zz))
                b = cam.proj(v3(xb, -PH, zz))
                c.drawLine(a[0], a[1], b[0], b[1], lp)
        # ---- pull tab (slides with the piece in the slot)
        if self.sc.slider:
            out = smooth(stt['opening']) * (1 - smooth(stt['closing']))
            self.pull_tab(c, cam, flat, t, out)

        if prev is not None:
            self.turn(c, cam, stt, prev)
            st = self.enter(stt['page'], t, theta, stt['tl_end'], stt['closing'])
            st.post(c, arr, t, cam, self)
            return arr

        self.open_spread(c, cam, theta, t, flat)
        st.post(c, arr, t, cam, self)
        return arr

    def pull_tab(self, c, cam, flat, t, out):
        st = self.st
        m = 0.04
        X, Y = v3(1, 0, 0), v3(0, 1, 0)
        sl = self.pcs[self.sc.slider].slider
        tabx = PW - 0.70 - 0.50 * (1 - out) + (sl['x1'] - sl['x0']) * slide_s(t, self.tl_end) * out
        ty = sl['y']
        tb = flat('tab', v3(tabx, ty, -0.004), X, Y)
        if st.sh_alpha > 0 and tabx + 0.77 > PW + m and isinstance(cam, Camera):
            pa = skia.Paint(AntiAlias=True, Color=col(st.sh_col, 255 * st.sh_alpha * 0.7))
            pa.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 5))
            dx, dy = st.book_shadow
            c.drawPath(self.quad3(cam, [(PW + m, ty - 0.045 + dy * .25, ZD), (tabx + 0.77 + dx * .25, ty - 0.045 + dy * .25, ZD),
                                        (tabx + 0.77 + dx * .25, ty + 0.045 + dy * .25, ZD), (PW + m, ty + 0.045 + dy * .25, ZD)]), pa)
        self.draw_tex_panel(c, tb, 'tab', t)

    # ------------------------------------------------------------- a page turning over to the next one
    def turn(self, c, cam, stt, prev):
        """The leaf between two spreads swings from right to left. Its front carries the right half of the old spread
        (whose pop-up folds flat as the gap closes), its back the left half of the new one (whose pop-up rises).
        The leaf's plane separates the two, so whichever spread lies behind it from the camera is painted first."""
        phi = stt['theta']
        n_out = v3(-math.sin(phi), 0, math.cos(phi))
        old_side = n_out.dot(cam.pos) > 0                # the camera sees the leaf's front (the old page)
        # the leaf is card where pop-ups stand on it, and free paper beyond them: that outer part bends as it turns
        key = (prev['page'], stt['page'])
        if key not in self.reaches:
            self.reaches[key] = clamp(max(reach(self.scenes[key[0]], True), reach(self.scenes[key[1]], False)) + 0.05, 0.6, 1.08)
        self.bend = (self.reaches[key], prev['closing'], phi)

        def new_spread():
            self.enter(stt['page'], stt['tl'], phi, stt['tl_end'], 0.0)
            self.open_spread(c, cam, phi, stt['tl'], self.flat_fn(cam), turn='new')

        def old_spread():
            tc = TurnedCam(cam, phi)
            self.enter(prev['page'], prev['tl'], math.pi - phi, prev['tl_end'], prev['closing'], turned=tc.R)
            flat = self.flat_fn(tc)
            if self.sc.slider and old_side:
                self.pull_tab(c, tc, flat, prev['tl'], 1.0)
            self.open_spread(c, tc, math.pi - phi, prev['tl'], flat, turn='old', fade=1 - smooth(ramp(prev['closing'], 0.45, 0.8)))
            self.st.__dict__.pop('lamp', None)

        if old_side:
            new_spread()
            old_spread()
        else:
            old_spread()
            new_spread()

    def gutter(self, c, cam, O, U, a=0.2):
        Hp = cam.plane(O, U, YH)
        c.save()
        c.concat(skm(Hp))
        sh = skia.GradientShader.MakeLinear([skia.Point(0, 0), skia.Point(0.11, 0)],
                                            [col(self.st.sh_col, 255 * a * self.st.gutter), col(self.st.sh_col, 0)])
        c.drawRect(skia.Rect.MakeLTRB(0, -PH, 0.11, PH), skia.Paint(Shader=sh))
        c.restore()

    # ------------------------------------------------------------- the open pop-up spread
    def open_spread(self, c, cam, theta, t, flat, turn=None, fade=1.0):
        """turn: None for a spread on its own; 'new' / 'old' for the two spreads that share a turning leaf.
        fade: scales the shadows (the old spread's are let go as it folds away)."""
        st = self.st
        lamp = st.lamp
        X, Y = v3(1, 0, 0), v3(0, 1, 0)
        l = v3(math.cos(theta), 0, math.sin(theta))
        n_out = v3(-math.sin(theta), 0, math.cos(theta))
        mw, mh = self.pcs['map'].size
        half = mw / 2
        gr = flat('map', v3(0, 0, 0), X, Y, src=(half, 0, mw, mh))
        gl = flat('map', v3(0, 0, 0), -l, Y, src=(0, 0, half, mh))
        outer_visible = n_out.dot(cam.pos) > 0
        vv = cam.pos - 0.5 * PW * l
        edge_on = abs(n_out.dot(vv)) / np.linalg.norm(vv) < 0.04
        life = ramp(t, T_LIFE, T_LIFE + 0.7)
        shut = theta < 1e-5                              # the book is closed: nothing inside can be seen
        swinging = turn is None and theta < math.pi - 1e-4       # the front cover and its pages are off the desk
        # pieces
        order = [] if shut else self.sc.order
        panels = {}
        for name in order:
            panels[name] = self.piece_panels(cam, self.pcs[name], theta, t)
        fly = self.flyer_panels(cam, t, panels) if theta > math.pi * 0.97 else []
        eff_y = [(self.pcs[nm].slider['y'] if self.pcs[nm].slider else self.pcs[nm].y0 - 0.12) for nm in order]
        sha = st.sh_alpha * fade
        light = st.shadow_light
        swing_shadow = st.board_shadow and turn != 'old'

        def board_shadow_path(z=0.0, cam=cam):
            pts = []
            for (a, y) in ((0, -PH), (PW, -PH), (PW, PH), (0, PH)):
                P = a * l + y * Y
                k = (lamp[2] - z) / max(lamp[2] - P[2], 1e-3)
                Q = lamp + (P - lamp) * k
                pts.append(Q)
            return self.quad3(cam, pts)

        def ground(pn, is_right, c=c, cam=cam):
            c.saveLayer(union_bounds([pn]), None)
            self.draw_tex_panel(c, pn, 'map', t, shade=True)
            # things printed / cut into the page
            if is_right and self.sc.slider:
                sl = self.pcs[self.sc.slider].slider
                c.save()
                c.concat(skm(pn.Hp))
                c.clipRect(skia.Rect.MakeLTRB(0, -PH, PW, PH))
                pa = skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=0.008, StrokeCap=skia.Paint.kRound_Cap,
                                Color=col(st.slot_col, 230), BlendMode=skia.BlendMode.kSrcATop)
                c.drawLine(sl['x0'] - 0.07, sl['y'], sl['x1'] + 0.06, sl['y'], pa)
                c.restore()
            # flowing river
            Hp = cam.plane(v3(0, 0, 0), X if is_right else -l, Y)
            clip = skia.Rect.MakeLTRB(0, -PH + 0.07, PW - 0.07, PH) if is_right else skia.Rect.MakeLTRB(-PW + 0.07, -PH + 0.07, 0, PH)
            st.ground_fx(c, Hp, clip, t, self, is_right)
            self.flow(c, Hp, self.pcs['map'].flows, t, life * st.flow_ground, clip)
            # shadows
            if sha > 0:
                cs = [p for nm in order for p in panels[nm]]
                self.cast(c, pn, cs, light, sha * st.ground_sh, soft=2)
                if is_right and theta < math.pi * 0.985 and swing_shadow:
                    pa = skia.Paint(AntiAlias=True, Color=col(st.sh_col, 255 * sha * 0.9), BlendMode=skia.BlendMode.kSrcATop)
                    pa.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 6 + 30 * math.sin(theta)))
                    c.save()
                    c.clipPath(pn.quad_path(), True)
                    c.drawPath(board_shadow_path(0.0, cam), pa)
                    c.restore()
            self.gutter(c, cam, v3(0, 0, 0), X if is_right else -l, a=0.2)
            c.restore()

        def leaf(is_right):
            """One face of the leaf that is turning: painted flat first, then laid on the bending paper."""
            res_t = 560
            e1 = X if is_right else -l
            fc = FlatCam(e1, Y, ZH if is_right else -n_out, 0.0 if is_right else -PW, PH, res_t)
            mp = self.pcs['map']
            pn = Panel(fc, v3(0, 0, 0), e1, Y, (half, 0, mw, mh) if is_right else (0, 0, half, mh),
                       tex_to_plane(mp.bbox[0], mp.bbox[3], mp.res), 'map', st.lamp, st.amb, st.dif)
            s2, a2 = new_surface(int(PW * res_t), int(2 * PH * res_t))
            ground(pn, is_right, s2.getCanvas(), fc)
            self.leaf_mesh(c, cam, to_image(a2, mip=True), res_t, is_right, 0.0 if is_right else theta)

        def board_edges():
            """The sides of whatever carries the left page."""
            if turn == 'new':
                return                                   # a turning leaf is drawn as thin paper
            if turn == 'old':                            # the leaf turned last time, at rest on the left
                ec = mix(st.pal_rgb['board'], st.sh_col, 0.3)
                for q in ([0 * l - PH * Y, PW * l - PH * Y, PW * l - PH * Y + n_out * BT, -PH * Y + n_out * BT],
                          [PW * l - PH * Y, PW * l + PH * Y, PW * l + PH * Y + n_out * BT, PW * l - PH * Y + n_out * BT]):
                    c.drawPath(self.quad3(cam, q), skia.Paint(AntiAlias=True, Color=col(ec)))
                return
            if not swinging:
                return                                   # flat on the desk: drawn with the rest of the book
            # the block that swings with the front cover: pages, then the cover board sticking out past them
            m = CM
            pap = col(mix(st.pal_rgb['paper'], st.sh_col, 0.22))
            cvd = col(mix(st.cover_rgb, (0, 0, 0), 0.35))
            lp = skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=1.0, Color=col(mix(st.pal_rgb['paper'], st.sh_col, 0.45), 150))

            def P(a, y, h):
                return a * l + y * Y + h * n_out
            if not outer_visible and not edge_on:        # the inside of the cover board, showing as a rim round the pages
                cw, ch = self.pcs['cover'].size
                rim = flat('cover', n_out * TS, -l, Y, src=(0, 0, cw / 2, ch))
                self.draw_tex_panel(c, rim, 'cover', t)
            side = l.dot(cam.pos - PW * l) > 0            # can the camera see the fore-edge?
            if side:
                c.drawPath(self.quad3(cam, [P(PW + m, -PH - m, TS), P(PW + m, PH + m, TS), P(PW + m, PH + m, TB), P(PW + m, -PH - m, TB)]), skia.Paint(AntiAlias=True, Color=cvd))
                c.drawPath(self.quad3(cam, [P(PW, -PH, 0), P(PW, PH, 0), P(PW, PH, TS), P(PW, -PH, TS)]), skia.Paint(AntiAlias=True, Color=pap))
            c.drawPath(self.quad3(cam, [P(0, -PH - m, TS), P(PW + m, -PH - m, TS), P(PW + m, -PH - m, TB), P(0, -PH - m, TB)]), skia.Paint(AntiAlias=True, Color=cvd))
            c.drawPath(self.quad3(cam, [P(0, -PH, 0), P(PW, -PH, 0), P(PW, -PH, TS), P(0, -PH, TS)]), skia.Paint(AntiAlias=True, Color=pap))
            for k in range(1, 6):
                a = cam.proj(P(0, -PH, TS * k / 6))
                b = cam.proj(P(PW, -PH, TS * k / 6))
                c.drawLine(a[0], a[1], b[0], b[1], lp)

        def left_board_inner():
            board_edges()
            if turn == 'new':
                leaf(False)
            elif not edge_on:
                ground(gl, False)

        def left_board_outer():
            board_edges()
            if not edge_on and swinging:
                bo = flat('jacket', n_out * TB, l, Y)     # the front cover, title up
                self.draw_tex_panel(c, bo, 'jacket', t)

        # shadow of the board on the left stack / desk while it swings over
        if turn == 'old':
            leaf(True)
        elif not shut:
            ground(gr, True)
        if not outer_visible:
            if st.sh_alpha > 0 and theta < math.pi * 0.99 and not edge_on and swing_shadow:
                pa = skia.Paint(AntiAlias=True, Color=col(st.sh_col, 255 * sha * 0.8))
                pa.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 4 + 26 * math.sin(theta)))
                c.save()
                if swinging:                             # the cover coming down: its shadow lands on the bare desk
                    c.clipPath(self.quad3(cam, [(-4.4, -2.9, ZD), (0, -2.9, ZD), (0, 5.9, ZD), (-4.4, 5.9, ZD)]), True)
                    c.drawPath(board_shadow_path(ZD), pa)
                else:
                    c.clipPath(self.quad3(cam, [(-PW, -PH, -BT), (0, -PH, -BT), (0, PH, -BT), (-PW, PH, -BT)]), True)
                    c.drawPath(board_shadow_path(-BT), pa)
                c.restore()
            left_board_inner()
        elif turn == 'new':
            leaf(False)                                  # where the paper bends, its back can show early

        # pieces far -> near, with anything that flies slipped in at its own depth
        def flyers_between(far_y, near_y):
            for pn in fly:
                if near_y < pn.O[1] <= far_y:
                    c.saveLayer(skia.Rect.MakeLTRB(*pn.bounds(3)), None)      # own layer, so its shading tints only the piece
                    self.draw_tex_panel(c, pn, pn.name, t)
                    c.restore()
        flyers_between(9.0, eff_y[0] if eff_y else -9.0)
        for i, name in enumerate(order):
            pns = panels[name]
            pc = self.pcs[name]
            if pc.slider and theta < 0.5:
                continue
            # tab struts for the side pieces
            if theta > math.pi * 0.7:                   # folded tighter than this, the struts lie hidden between the sheets
                st.pre_piece(c, name, t, cam, self, panels)
            c.saveLayer(union_bounds(pns), None)
            for pn in pns:
                self.draw_tex_panel(c, pn, name, t)
                # animated water on the panel
                if pc.flows:
                    u0, v0, u1, v1 = pc.bbox
                    right = pn.U[0] > 0 or (abs(theta - math.pi) < 1e-3 and pn is pns[0])
                    is_r = pn is pns[0] and pc.side != 'L'
                    clip = skia.Rect.MakeLTRB(0, 0, u1, v1) if is_r else skia.Rect.MakeLTRB(u0, 0, 0, v1)
                    self.flow(c, pn.Hp, pc.flows, t, life * st.flow_fall, clip)
                st.piece_fx(c, name, pn, t, self)
            if sha > 0:
                cs = [p for nm in order[i + 1:i + 5] if not self.pcs[nm].slider or pc.side in ('L', 'R') for p in panels[nm]]
                for pn in pns:
                    self.cast(c, pn, cs, light, sha * st.piece_sh, soft=1)
            c.restore()
            st.post_piece(c, name, t, cam, self, panels)
            # mist between the layers
            self.draw_mist(c, cam, t, i)
            flyers_between(eff_y[i], eff_y[i + 1] if i + 1 < len(order) else -9.0)
        if outer_visible:
            if turn == 'new':
                board_edges()                            # the old page is painted on the leaf's front afterwards
            else:
                left_board_outer()
        self.draw_birds(c, cam, t, panels)
        st.overlay(c, t, cam, self, panels)

    # ------------------------------------------------------------- life: mist, birds
    def draw_mist(self, c, cam, t, slot):
        st = self.st
        a0 = ramp(t, T_LIFE + 0.1, T_LIFE + 1.8) * st.mist_a * self.rel * (1.0 if self.sc.mist else 0.0)
        if a0 <= 0.003:
            return
        pc = self.pcs[self.sc.order[slot]]
        ys = {slot: (pc.slider['y'] if pc.slider else pc.y0) - 0.06}
        for m in self.mist:
            if m['slot'] != slot:
                continue
            cyc = ((t - T_LIFE) * 0.085 * m['sp'] * st.mist_speed + m['ph']) % 1.0
            z = m['z'] + 0.32 * cyc
            a = a0 * math.sin(math.pi * cyc) ** 0.8
            x = m['x'] + 0.06 * math.sin(t * 0.5 + m['ph'] * 6)
            sx, sy, d = cam.proj(v3(x, ys[slot] - 0.04, z))
            w = m['w'] * cam.fl / d
            img = st.mist_img(m['k'])
            hgt = w * img.height() / img.width()
            pa = skia.Paint(Alphaf=min(1.0, a))
            if st.mist_blend is not None:
                pa.setBlendMode(st.mist_blend)
            c.drawImageRect(img, skia.Rect.MakeWH(img.width(), img.height()),
                            skia.Rect.MakeLTRB(sx - w / 2, sy - hgt / 2, sx + w / 2, sy + hgt / 2), SAMP_L, pa)

    def anchor_world(self, panels, pname, aname):
        u, v = self.pcs[pname].anchors[aname]
        return self.sheet_point(panels, pname, u, v)

    def sheet_point(self, panels, pname, u, v):
        pc = self.pcs[pname]
        pns = panels[pname]
        if pc.slider or len(pns) == 1:
            pn = pns[0]
            return pn.O + pn.U * u + pn.V * v
        pn = None
        for q in pns:
            if (q.U[0] > 0) == (u >= 0) or len(pns) == 1:
                pn = q
        pn = pn or pns[0]
        return pn.O + pn.U * u + pn.V * v

    def draw_birds(self, c, cam, t, panels):
        st = self.st
        if self.theta < math.pi * 0.9:
            return
        for b in self.birds:
            P0 = self.anchor_world(panels, b['piece'], b['anchor'])
            tau = (t - b['t0']) * st.bird_speed
            if tau <= 0:
                # perched: folded paper bird
                sx, sy, d = cam.proj(P0 + v3(0, -0.004, 0.006))
                s = 0.016 * cam.fl / d * b['s']
                p = skia.Path()
                p.moveTo(sx - s, sy)
                p.quadTo(sx - s * 0.2, sy - s * 0.9, sx + s * 0.9, sy - s * 0.25)
                p.quadTo(sx + s * 0.2, sy + s * 0.1, sx - s, sy)
                st.draw_bird(c, p, 1.0)
                continue
            e = 1 - math.exp(-tau * 1.2)
            P = P0 + v3(b['vx'] * (tau + 0.6 * e) + 0.05 * math.sin(tau * 1.3 + b['ph']),
                        b['vy'] * tau - 0.05 * e,
                        b['vz'] * tau + 0.10 * e + 0.02 * math.sin(tau * 2 + b['ph']))
            sx, sy, d = cam.proj(P)
            if d <= 0.2:
                continue
            s = 0.034 * cam.fl / d * b['s'] * (0.55 + 0.45 * min(1, tau * 3))
            fl = math.sin(tau * b['f'] * 2 * math.pi / max(st.bird_speed, 0.3) * 0.5 + b['ph'])
            dirx = 1 if b['vx'] >= 0 else -1
            p = skia.Path()
            wy = -fl * s * 0.75
            p.moveTo(sx - s, sy + wy)
            p.quadTo(sx - s * 0.45, sy + wy * 0.2 - s * 0.28, sx, sy)
            p.quadTo(sx + s * 0.45, sy + wy * 0.2 - s * 0.28, sx + s, sy + wy)
            p.quadTo(sx + s * 0.4, sy + wy * 0.25 + s * 0.05, sx + dirx * s * 0.1, sy + s * 0.22)
            p.quadTo(sx - s * 0.4, sy + wy * 0.25 + s * 0.05, sx - s, sy + wy)
            p.close()
            fade = 1 - ramp(tau, 5.5, 7.5)
            st.draw_bird(c, p, fade)

    # ------------------------------------------------------------- things that fly between two spots
    def spot(self, panels, ref):
        """['mid', 'hive'] = a named thing on a sheet, ['mid', x, y] = a point on a sheet, ['floor', x, y] = on the page."""
        if isinstance(ref[0], str):
            if ref[0] == 'floor':
                return v3(ref[1], ref[2], 0.03)
            if ref[0] in panels and len(ref) == 3:
                return self.sheet_point(panels, ref[0], ref[1], ref[2]) + v3(0, -0.035, 0)
            if ref[0] not in panels or ref[1] not in self.pcs[ref[0]].anchors:
                raise ValueError('nothing called %r on sheet %r' % (ref[1], ref[0]))
            return self.anchor_world(panels, ref[0], ref[1]) + v3(0, -0.035, 0)
        return v3(*ref)

    def flyer_panels(self, cam, t, panels):
        st = self.st
        out = []
        for k, f in enumerate(self.sc.flyers):
            A, B = self.spot(panels, f['src']), self.spot(panels, f['dst'])
            pc = self.pcs[f['piece']]
            w, h = pc.size
            T = tex_to_plane(pc.bbox[0], pc.bbox[3], pc.res)
            for j in range(f['n']):
                tau = t - T_LIFE - f['at'] - j * f['secs'] * (0.37 if f['n'] > 1 else 0.0)
                if tau < 0:
                    continue
                if f['loop']:
                    leg, p = divmod(tau / f['secs'], 1.0)
                    a, b = (A, B) if int(leg) % 2 == 0 else (B, A)
                else:
                    p, a, b = min(tau / f['secs'], 1.0), A, B
                e = smooth(p)
                bob = 0.012 * math.sin(tau * 9.0 + j * 2.1 + k)
                P = a + (b - a) * e + v3(0.02 * math.sin(tau * 3.1 + j), 0, f['arc'] * math.sin(math.pi * e) * (1 + 0.25 * (j % 2)) + bob)
                face = 1.0 if b[0] >= a[0] else -1.0
                O = P - ZH * (pc.bbox[3] * 0.5)
                out.append(Panel(cam, O, v3(face, 0, 0), ZH, (0, 0, w, h), T, pc.name, st.lamp, st.amb, st.dif, w))
        return out
