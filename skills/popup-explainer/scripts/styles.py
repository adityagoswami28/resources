"""The five art styles. Each one paints the same vector scene into textures
and supplies its own lighting, 'life' effects and animation feel."""
import math
import os
import numpy as np
import skia
from core import *
import kit as SC
from kit import MATS, hex_rgb
from book import PAGE_PIECES


class Pal(dict):
    """A colour table that also answers '#rrggbb', worked out the way each style needs it."""

    def __init__(self, base, derive):
        super().__init__(base)
        self.derive = derive

    def __missing__(self, k):
        if isinstance(k, str) and k.startswith('#'):
            v = self.derive(hex_rgb(k))
            self[k] = v
            return v
        raise KeyError(k)

    def get(self, k, d=None):
        if dict.__contains__(self, k) or (isinstance(k, str) and k.startswith('#')):
            return self[k]
        return d


def _lum(c):
    return (0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2]) / 255.0

SH_DIV = 4            # shadow textures are 1/4 resolution
SH_PAD = 0.06         # padding around the piece, in units


def setup(c, pc):
    c.scale(pc.res, -pc.res)
    c.translate(-pc.bbox[0], -pc.bbox[3])


def raster(pc, fn, clear=None):
    w, h = pc.size
    surf, arr = new_surface(w, h)
    c = surf.getCanvas()
    if clear is not None:
        c.clear(clear)
    setup(c, pc)
    fn(c)
    surf.flushAndSubmit()
    return arr


def silhouette(pc):
    def fn(c):
        pa = skia.Paint(AntiAlias=True, Color=0xFFFFFFFF)
        for s in pc.shapes:
            if s.kind != 'fill':
                continue
            c.save()
            if s.clip is not None:
                c.clipPath(s.clip, True)
            c.drawPath(s.path, pa)
            c.restore()
    return raster(pc, fn)[..., 3].astype(np.float32) / 255


_fib = {}


def fibre(h, w, seed=3, strength=1.0):
    """Multiplicative paper-fibre texture around 1.0."""
    key = (seed,)
    if key not in _fib:
        n_h, n_w = 1700, 2100
        base = 0.10 * (fbm(n_h, n_w, 2.0, seed, 2) - 0.5) + 0.07 * (fbm(n_h, n_w, 60, seed + 1, 3) - 0.5)
        surf, arr = new_surface(n_w, n_h)
        c = surf.getCanvas()
        c.clear(skia.Color(128, 128, 128, 255))
        rng = np.random.default_rng(seed)
        for _ in range(9000):
            x, y = rng.uniform(0, n_w), rng.uniform(0, n_h)
            a = rng.uniform(0, math.pi)
            ln = rng.uniform(8, 34)
            bend = rng.uniform(-6, 6)
            p = skia.Path()
            p.moveTo(x, y)
            p.quadTo(x + math.cos(a) * ln / 2 - math.sin(a) * bend, y + math.sin(a) * ln / 2 + math.cos(a) * bend,
                     x + math.cos(a) * ln, y + math.sin(a) * ln)
            v = 255 if rng.random() < 0.55 else 0
            c.drawPath(p, skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=rng.uniform(0.6, 1.3),
                                     Color=skia.Color(v, v, v, int(rng.uniform(14, 44)))))
        f = arr[..., 0].astype(np.float32) / 255 - 0.5
        _fib[key] = (1 + base + 0.5 * f).astype(np.float32)
    t = _fib[key]
    rng = np.random.default_rng(h * 7919 + w)
    oy = int(rng.integers(0, max(1, t.shape[0] - h))) if h < t.shape[0] else 0
    ox = int(rng.integers(0, max(1, t.shape[1] - w))) if w < t.shape[1] else 0
    out = t[oy:oy + h, ox:ox + w]
    if out.shape != (h, w):
        out = np.tile(t, (h // t.shape[0] + 1, w // t.shape[1] + 1))[:h, :w]
    return 1 + (out - 1) * strength


class Style:
    idx = 0
    name = 'base'
    feel = (0.3, 26.0, 14.0)            # spring zeta, omega, snap angle (deg)
    on_twos = False
    lamp = v3(-2.6, -1.5, 2.7)
    amb, dif = 0.74, 0.42
    sh_col = (38, 24, 20)
    sh_alpha = 0.42
    ground_sh, piece_sh = 1.0, 0.85
    board_shadow = True
    book_shadow = (0.10, 0.10)
    gutter = 1.0
    bg = (24, 16, 12)
    desk_bbox = (-4.5, -3.0, 4.5, 6.0)
    desk_res = 300
    slot_col = (40, 30, 26)
    flow_col, flow_a, flow_w, flow_blend = (255, 255, 255), 0.8, 1.0, None
    flow_ground, flow_fall = 1.0, 1.0
    mist_col, mist_a, mist_speed, mist_blend = (255, 255, 255), 0.5, 1.0, None
    bird_col, bird_speed = (250, 246, 236), 1.0
    lantern_col, lantern_a = (255, 190, 90), 0.5
    lantern_t0, lantern_dt = 5.2, 0.1
    vignette = 0.5
    grain = 0.05
    pal = {}

    def __init__(self, scene, cache=None, common=None):
        self.sc = scene
        self.pcs = scene.pcs
        self.cache, self.common = cache, common
        self.theta = math.pi
        self.pace = 1.0
        self.shadow_light = self.lamp
        self.img = {}
        self.meta = {}
        self.pal_rgb = self.pal

    # ------------------------------------------------------------- build (numpy) / load (skia)
    def build(self):
        data = {}
        for name in self.sc.order + [f['piece'] for f in self.sc.flyers] + PAGE_PIECES:
            pc = self.pcs[name]
            out = self.paint_piece(pc)
            for k, v in out.items():
                data['%s/%s' % (name, k)] = v
            if name in self.sc.order:
                a = out['art'][..., 3].astype(np.float32) / 255
                pad = int(SH_PAD * pc.res)
                a = np.pad(a, pad)
                small = ndi.zoom(a, 1 / SH_DIV, order=1)
                for k, sg in ((1, 1.6), (2, 3.6)):
                    b = np.clip(blur(small, sg), 0, 1)
                    data['%s/sh%d' % (name, k)] = premul(np.ones(b.shape + (3,), np.float32) * (np.array(self.sh_col) / 255), b)
        m = data['map/art']
        hw = m.shape[1] // 2
        right = m[:, hw:, :3].astype(np.float32) / 255
        paper = np.array(self.pal_rgb['paper'], np.float32) / 255
        back = self.page_back(right, paper)
        back8 = np.concatenate([np.clip(back * 255, 0, 255).astype(np.uint8), np.full(back.shape[:2] + (1,), 255, np.uint8)], -1)
        data['pageback/art'] = back8
        data['atlas'] = np.concatenate([m[:, hw:], back8], axis=1)
        self.extra_build(data)
        return data

    def build_common(self):
        """Textures every page shares: the desk, the mist and the film grain."""
        data = {'desk/art': self.paint_desk()}
        data['bgcol'] = data['desk/art'][2:6, :, :3].reshape(-1, 3).mean(0)
        for k in range(3):
            data['mist%d' % k] = self.paint_mist(k)
        data['grain'] = self.paint_grain()
        return data

    def page_back(self, right, paper):
        ghost = blur(right, 2.0)
        return paper * 0.97 * (1 - 0.10) + ghost * 0.10

    def extra_build(self, data):
        pass

    def ensure(self, rebuild=False, load=True):
        for path, fn in ((self.common, self.build_common), (self.cache, self.build)):
            if rebuild or not os.path.exists(path):
                os.makedirs(os.path.dirname(path), exist_ok=True)
                data = fn()
                np.savez(path, **data)
            elif not load:
                continue
            else:
                data = dict(np.load(path))
            if load:
                self.load(data)

    def load(self, data):
        if 'bgcol' in data:
            self.bg = tuple(float(x) for x in data['bgcol'])
        for k, v in data.items():
            if v.ndim == 3 and v.shape[2] == 4:
                self.img[k] = to_image(v, mip=not k.startswith('desk'))
        for name in self.sc.order:
            if '%s/sh1' % name not in data:
                continue
            pc = self.pcs[name]
            sh = data['%s/sh1' % name]
            self.meta[name] = (tex_to_plane(pc.bbox[0] - SH_PAD, pc.bbox[3] + SH_PAD, pc.res / SH_DIV), (sh.shape[1], sh.shape[0]))

    # ------------------------------------------------------------- per-style painters (override)
    def paint_piece(self, pc):
        raise NotImplementedError

    def paint_desk(self):
        raise NotImplementedError

    def paint_mist(self, k):
        h, w = 150, 400
        n = fbm(h, w, 60, 100 + k, 4)
        yy, xx = np.mgrid[0:h, 0:w]
        fall = np.clip(1 - ((xx - w / 2) / (w / 2)) ** 2 - ((yy - h / 2) / (h / 2)) ** 2, 0, 1)
        a = np.clip((n - 0.25) * 1.6, 0, 1) * fall ** 1.2
        a = blur(a, 4)
        return premul(np.ones((h, w, 3), np.float32) * (np.array(self.mist_col) / 255), a.astype(np.float32))

    def paint_grain(self):
        g = white(540, 960, 5)
        g = blur(g, 0.7)
        g = (g - g.mean()) / (g.std() + 1e-6)
        v = np.clip(0.5 + g * 0.18, 0, 1)
        return premul(np.stack([v, v, v], -1), np.ones_like(v))

    # ------------------------------------------------------------- runtime hooks
    def begin(self, t, theta=math.pi):
        self.now = t
        self.theta = theta

    def draw_art(self, c, name, r, t, pn):
        c.drawImageRect(self.img[name + '/art'], r, r, SAMP, skia.Paint())

    def shadow(self, name, soft):
        key = '%s/sh%d' % (name, soft)
        if key not in self.img:
            return None
        T, wh = self.meta[name]
        return self.img[key], T, wh

    def page_atlas(self):
        im = self.img['atlas']
        return im, (im.width(), im.height())

    def mist_img(self, k):
        return self.img['mist%d' % k]

    def ground_fx(self, c, Hp, clip, t, R, is_right):
        pass

    def pre_piece(self, c, name, t, cam, R, panels):
        # paper tabs holding the side sheets to the sheet behind them
        tabs = [tb for tb in self.sc.tabs if tb[0] == name]
        if not tabs or not panels[name] or tabs[0][1] not in panels:
            return
        pn = panels[name][0]
        ppn = [q for q in panels[tabs[0][1]] if (q.U[0] > 0) == (pn.U[0] > 0)]
        if not ppn:
            return
        ppn = ppn[0]
        for (u, v) in tabs[0][2]:
            a0 = pn.O + pn.U * u + pn.V * v
            b0 = ppn.O + ppn.U * u + ppn.V * v
            dv = 0.03
            q = [a0 - pn.U * dv, b0 - ppn.U * dv, b0 + ppn.U * dv, a0 + pn.U * dv]
            l = self.lamp - a0
            l /= np.linalg.norm(l)
            b = self.amb * 0.8
            c.drawPath(R.quad3(cam, q), skia.Paint(AntiAlias=True, Color=col(mix(self.tab_col(), self.sh_col, 1 - min(b, 1)))))

    def tab_col(self):
        return self.pal_rgb['paper']

    def piece_fx(self, c, name, pn, t, R):
        pass

    def post_piece(self, c, name, t, cam, R, panels):
        pass

    def lantern_level(self, i, t):
        return smooth(ramp(t, self.lantern_t0 + self.lantern_dt * i, self.lantern_t0 + self.lantern_dt * i + 0.5))

    def overlay(self, c, t, cam, R, panels):
        """Lantern glows (all styles)."""
        if self.theta < math.pi * 0.97:
            return
        for i, (pn, an, size) in enumerate(self.sc.glows):
            lv = self.lantern_level(i, t)
            if lv <= 0.01 or not panels.get(pn):
                continue
            P = R.anchor_world(panels, pn, an)
            sx, sy, d = cam.proj(P + v3(0, -0.01, 0))
            fl = 0.9 + 0.1 * math.sin(t * 7.0 + i * 2.1) * math.sin(t * 3.1 + i)
            r = 0.085 * cam.fl / d * size
            a = self.lantern_a * lv * fl * (0.6 if size < 0.5 else 1.0)
            sh = skia.GradientShader.MakeRadial(skia.Point(sx, sy), r,
                                                [col(self.lantern_col, 255 * a), col(self.lantern_col, 90 * a), col(self.lantern_col, 0)],
                                                [0.0, 0.35, 1.0])
            c.drawCircle(sx, sy, r, skia.Paint(Shader=sh, BlendMode=skia.BlendMode.kPlus))

    def draw_bird(self, c, path, fade):
        if self.sh_alpha > 0:
            c.save()
            c.translate(3, 5)
            pa = skia.Paint(AntiAlias=True, Color=col(self.sh_col, 60 * fade))
            pa.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 2.5))
            c.drawPath(path, pa)
            c.restore()
        c.drawPath(path, skia.Paint(AntiAlias=True, Color=col(self.bird_col, 255 * fade)))

    def post(self, c, arr, t, cam, R):
        if self.vignette > 0:
            sh = skia.GradientShader.MakeRadial(skia.Point(W / 2, H * 0.52), W * 0.72,
                                                [col((0, 0, 0), 0), col((0, 0, 0), 0), col(self.sh_col, 255 * self.vignette)],
                                                [0, 0.5, 1.0])
            c.drawRect(skia.Rect.MakeWH(W, H), skia.Paint(Shader=sh))
        if self.grain > 0:
            g = self.img['grain']
            k = int(t * (15 if self.on_twos else 30) + 0.5)
            ox, oy = (k * 173) % 400, (k * 97) % 300
            pa = skia.Paint(Alphaf=self.grain, BlendMode=skia.BlendMode.kOverlay)
            c.drawImageRect(g, skia.Rect.MakeXYWH(ox / 4.0, oy / 4.0, 480, 270) if False else skia.Rect.MakeWH(960, 540),
                            skia.Rect.MakeXYWH(-ox, -oy, W + 400, H + 300), SAMP_L, pa)


# =====================================================================================================
# 1. Cut-paper diorama under a warm desk lamp
# =====================================================================================================
PAL_PAPER = dict(
    paper=(246, 238, 222), ink=(60, 44, 38), moon=(255, 245, 208), mare=(250, 226, 168), rockA=(152, 200, 198),
    rockB=(84, 154, 152), rockC=(36, 104, 114), leafA=(142, 198, 128), leafB=(56, 152, 96), leafC=(16, 100, 80),
    trunk=(130, 86, 60), water=(56, 182, 208), foam=(240, 252, 250), stone=(228, 172, 110), stoneD=(110, 62, 56),
    lantern=(255, 178, 56), robe1=(238, 86, 54), robe2=(252, 204, 62), robe3=(238, 98, 142), skin=(232, 186, 150),
    hat=(242, 216, 150), fur=(98, 62, 48), toucan=(34, 38, 54), bib=(252, 238, 164), beak=(255, 146, 34),
    heron=(242, 244, 240), heronD=(72, 90, 110), canoe=(172, 58, 48), rope=(198, 158, 106), plank=(150, 104, 70),
    bank=(240, 218, 162), grass=(150, 202, 128), board=(234, 222, 198), cover=(34, 80, 96), gold=(228, 178, 72),
    tab=(246, 238, 222))
PAL_PAPER = Pal(PAL_PAPER, lambda c: c)


class PaperStyle(Style):
    idx, name = 1, 'cut-paper'
    feel = (0.22, 30.0, 16.0)
    pal = PAL_PAPER
    bg = (30, 18, 12)
    sh_col = (44, 24, 16)
    sh_alpha = 0.46
    flow_col, flow_a = (244, 252, 250), 0.9
    mist_col, mist_a = (255, 250, 240), 0.42
    bird_col = (252, 248, 236)
    lantern_a = 0.55
    vignette = 0.62
    grain = 0.06

    def paint_piece(self, pc):
        pal = self.pal
        flatp = pc.name in PAGE_PIECES

        def fn(c):
            for s in pc.shapes:
                c.save()
                if s.clip is not None:
                    c.clipPath(s.clip, True)
                if s.kind == 'line':
                    pa = skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=s.w * 1.15,
                                    StrokeCap=skia.Paint.kRound_Cap, Color=col((50, 34, 28) if s.mat == 'ink' else tone_col(pal[s.mat], -0.5), 96))
                    c.drawPath(s.path, pa)
                    pa.setColor(skia.Color(255, 255, 255, 58))
                    c.translate(0.0013, -0.0013)
                    c.drawPath(s.path, pa)
                else:
                    tone = s.tone + (-0.34 if s.kind == 'shade' else 0.30 if s.kind == 'hi' else 0.0)
                    colr = tone_col(pal[s.mat], tone)
                    k = 0.6 if s.kind != 'fill' else 1.0
                    sh = skia.Paint(AntiAlias=True, Color=skia.Color(30, 16, 10, int(105 * k)))
                    sh.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 0.0026 * k))
                    c.save()
                    c.translate(0.0022 * k, -0.0032 * k)
                    c.drawPath(s.path, sh)
                    c.restore()
                    c.drawPath(s.path, skia.Paint(AntiAlias=True, Color=col(colr)))
                    # cut edge: lit on the top-left, dark on the bottom-right
                    c.save()
                    c.clipPath(s.path, True)
                    e = skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=0.0030, Color=skia.Color(255, 255, 255, 70))
                    c.save()
                    c.translate(0.0011, -0.0011)
                    c.drawPath(s.path, e)
                    c.restore()
                    e.setColor(skia.Color(20, 10, 6, 46))
                    c.translate(-0.0011, 0.0011)
                    c.drawPath(s.path, e)
                    c.restore()
                c.restore()
        arr = raster(pc, fn)
        rgb, a = unpremul(arr)
        sil = silhouette(pc)
        h, w = sil.shape
        rgb = rgb * fibre(h, w, 3 + len(pc.name), 1.0)[..., None]
        if not flatp:
            hi = np.clip(sil - np.roll(np.roll(sil, 2, 0), 2, 1), 0, 1)
            lo = np.clip(sil - np.roll(np.roll(sil, -2, 0), -2, 1), 0, 1)
            rgb = rgb + 0.16 * hi[..., None] - 0.14 * lo[..., None]
        return {'art': premul(np.clip(rgb, 0, 1), np.minimum(a, sil) if not flatp else sil)}

    def paint_desk(self):
        x0, y0, x1, y1 = self.desk_bbox
        res = self.desk_res
        w, h = int((x1 - x0) * res), int((y1 - y0) * res)
        g1 = ndi.zoom(fbm(h, w // 12, 5, 21, 4), (1, 12.01), order=1)[:, :w]
        g2 = ndi.zoom(fbm(h, w // 30, 2.2, 22, 2), (1, 30.01), order=1)[:, :w]
        g = 0.55 * g1 + 0.45 * g2
        base = np.array([150, 96, 58], np.float32) / 255
        dark = np.array([92, 52, 30], np.float32) / 255
        rgb = dark + (base - dark) * g[..., None]
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        X = x0 + xx / res
        Y = y1 - yy / res
        plank = np.abs(((Y + 0.3) / 1.45) % 1.0 - 0.5)
        rgb *= (1 - 0.35 * np.clip(1 - plank * 110, 0, 1))[..., None]
        r2 = ((X + 0.5) / 2.9) ** 2 + ((Y + 0.2) / 2.5) ** 2
        light = 0.10 + 1.12 / (1 + r2) ** 1.5
        rgb = rgb * light[..., None] * np.array([1.06, 0.98, 0.86], np.float32)
        bgc = np.array(self.bg, np.float32) / 255
        edge = np.clip(np.minimum.reduce([X - x0, x1 - X, Y - y0, y1 - Y]) / 1.5, 0, 1)[..., None]
        rgb = bgc + (rgb - bgc) * edge
        return premul(np.clip(rgb, 0, 1), np.ones((h, w), np.float32))




def ink_over(rgb, ink_rgb, a):
    return rgb * (1 - a[..., None]) + np.array(ink_rgb, np.float32) / 255 * a[..., None]


def flat_desk(style, base, far, noise=0.05, seed=31):
    x0, y0, x1, y1 = style.desk_bbox
    res = style.desk_res
    w, h = int((x1 - x0) * res), int((y1 - y0) * res)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    X = x0 + xx / res
    Y = y1 - yy / res
    k = np.clip((Y + 1.5) / 6.5, 0, 1)[..., None]
    rgb = np.array(base, np.float32) / 255 * (1 - k) + np.array(far, np.float32) / 255 * k
    rgb = rgb * (1 + noise * (fbm(h, w, 90, seed, 3) - 0.5) * 2)[..., None]
    return rgb, X, Y


# =====================================================================================================
# 2. Risograph: three spot inks, printed one pass at a time, stop-motion on twos
# =====================================================================================================
INKS = [(255, 232, 0), (255, 72, 176), (0, 120, 191)]
RISO_PAPER = (247, 242, 230)
DENS = dict(
    paper=(0, 0, 0), ink=(0, 0, 1), moon=(.55, 0, 0), mare=(.6, .3, 0), rockA=(0, .12, .26), rockB=(0, .3, .55),
    rockC=(0, .45, .95), leafA=(.75, 0, .2), leafB=(1, 0, .5), leafC=(1, .15, .9), trunk=(.5, .7, .45), water=(0, .04, .42),
    foam=(0, 0, 0), stone=(.55, .46, 0), stoneD=(.3, .9, .5), lantern=(1, .45, 0), robe1=(.2, 1, 0), robe2=(1, .15, 0),
    robe3=(0, .3, .9), skin=(.3, .3, 0), hat=(.6, .1, 0), fur=(.4, .7, .6), toucan=(0, .4, 1), bib=(.7, 0, 0),
    beak=(1, .7, 0), heron=(0, .08, .08), heronD=(0, .3, .8), canoe=(.3, 1, .1), rope=(.4, .4, .2), plank=(.5, .6, .3),
    bank=(.3, .12, 0), grass=(.5, 0, .12), board=(.14, .04, 0), cover=(0, .95, .12), gold=(1, .35, 0), tab=(0, 0, 0))


def fit_dens(rgb):
    """The three ink densities that print closest to a colour."""
    g = np.linspace(0, 1, 13)
    D = np.stack(np.meshgrid(g, g, g, indexing='ij'), -1).reshape(-1, 3)
    c = np.ones((len(D), 3)) * (np.array(RISO_PAPER) / 255.0)
    for k in range(3):
        c = c * (1 - D[:, k:k + 1] * (1 - np.array(INKS[k]) / 255.0))
    err = ((c * 255 - np.array(rgb)) ** 2).sum(1) + 40 * D.sum(1)
    return tuple(float(x) for x in D[err.argmin()])


DENS = Pal(DENS, fit_dens)


def riso_rgb(d):
    c = np.array(RISO_PAPER, np.float32) / 255
    for k in range(3):
        c = c * (1 - d[k] * (1 - np.array(INKS[k], np.float32) / 255))
    return tuple(c * 255)


class RisoStyle(Style):
    idx, name = 2, 'risograph'
    on_twos = True
    feel = (0.3, 24.0, 15.0)
    pal = DENS
    bg = (196, 208, 226)
    sh_col = (24, 44, 96)
    sh_alpha = 0.30
    amb, dif = 0.86, 0.22
    flow_col, flow_a = RISO_PAPER, 0.95
    mist_col, mist_a = RISO_PAPER, 0.75
    bird_col = (255, 72, 176)
    lantern_col, lantern_a = (255, 240, 120), 0.28
    vignette = 0.22
    grain = 0.10
    PASS = [(3.95, 4.75), (4.95, 5.75), (5.95, 6.75)]

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.pal_rgb = {m: riso_rgb(DENS[m]) for m in list(DENS)}

    def paint_piece(self, pc):
        sil = silhouette(pc)
        h, w = sil.shape
        flatp = pc.name in PAGE_PIECES
        plates = []
        for k in range(3):
            def fn(c, k=k):
                for s in pc.shapes:
                    c.save()
                    if s.clip is not None:
                        c.clipPath(s.clip, True)
                    d = DENS[s.mat][k]
                    if s.kind == 'line':
                        if k == 2 or (s.mat != 'ink' and d > 0.3):
                            c.drawPath(s.path, skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=s.w * 1.2,
                                                          StrokeCap=skia.Paint.kRound_Cap, Color=skia.Color(255, 255, 255, 235)))
                    else:
                        d = d * (1 - 0.4 * s.tone)
                        if s.kind == 'shade':
                            if k == 0:
                                c.restore()
                                continue
                            d = d + (0.36 if k == 2 else 0.12)
                        elif s.kind == 'hi':
                            d = d * 0.5
                        d = clamp(d)
                        b = s.path.getBounds()
                        sh = skia.GradientShader.MakeLinear([skia.Point(0, b.bottom()), skia.Point(0, b.top())],
                                                            [skia.Color(255, 255, 255, int(255 * d * 0.78)), skia.Color(255, 255, 255, int(255 * d))])
                        pa = skia.Paint(AntiAlias=True, BlendMode=skia.BlendMode.kSrc)
                        pa.setShader(sh)
                        c.drawPath(s.path, pa)
                    c.restore()
            plates.append(raster(pc, fn)[..., 3].astype(np.float32) / 255)
        paper = np.array(RISO_PAPER, np.float32) / 255 * fibre(h, w, 9, 0.35)[..., None]
        out = {'paper': premul(np.clip(paper, 0, 1), sil)}
        rgb = paper.copy()
        shifts = [(2, -1), (-2, 2), (0, 0)]
        for k in range(3):
            D = plates[k]
            D = np.roll(np.roll(D, shifts[k][0], 1), shifts[k][1], 0)
            n = blur(white(h, w, 40 + k + len(pc.name)), 0.65)
            n = (n - n.mean()) / (n.std() + 1e-6)
            u = 0.5 * (1 + np.tanh(n * 0.9))
            D2 = D * (0.88 + 0.24 * fbm(h, w, 70, 50 + k, 3))
            a = np.clip(D2, 0, 1) ** 0.9 * (0.74 + 0.26 * np.clip((1.15 - u) * 2.2, 0, 1)) * (1 - 0.55 * (u > 0.965))
            a = np.clip(a * 1.06, 0, 1) * sil * 0.97
            ink = np.ones((h, w, 3), np.float32) * (np.array(INKS[k], np.float32) / 255)
            out['ink%d' % k] = premul(ink, a.astype(np.float32))
            rgb = rgb * (1 - a[..., None] * (1 - np.array(INKS[k], np.float32) / 255))
        out['art'] = premul(np.clip(rgb, 0, 1), sil)
        return out

    def paint_desk(self):
        rgb, X, Y = flat_desk(self, (232, 222, 226), (176, 196, 226), 0.03)
        h, w = rgb.shape[:2]
        return premul(np.clip(rgb, 0, 1), np.ones((h, w), np.float32))

    def paint_mist(self, k):
        h, w = 150, 400
        n = fbm(h, w, 60, 100 + k, 4)
        yy, xx = np.mgrid[0:h, 0:w]
        fall = np.clip(1 - ((xx - w / 2) / (w / 2)) ** 2 - ((yy - h / 2) / (h / 2)) ** 2, 0, 1)
        a = np.clip((n - 0.25) * 1.6, 0, 1) * fall ** 1.2
        p = 7.0
        xr, yr = (xx + yy) / 1.414, (xx - yy) / 1.414
        dots = 0.5 + 0.25 * (np.cos(2 * np.pi * xr / p) + np.cos(2 * np.pi * yr / p))
        a = np.clip((a * 1.15 - dots) * 3 + 0.5, 0, 1).astype(np.float32)
        return premul(np.ones((h, w, 3), np.float32) * (np.array(self.mist_col, np.float32) / 255), a)

    def draw_art(self, c, name, r, t, pn):
        # the three ink passes finish well before a short page closes
        t0 = self.PASS[0][0]
        k_ = clamp((4.5 + 0.4 * (getattr(self, 'tl_end', 99.0) - 4.5) - t0) / (self.PASS[2][1] - t0), 0.45, 1.0)
        PASS = [(t0 + (a - t0) * k_, t0 + (b - t0) * k_) for a, b in self.PASS]
        if t < 0 or name not in self.sc.order + ['map'] or t >= PASS[2][1]:
            c.drawImageRect(self.img[name + '/art'], r, r, SAMP, skia.Paint())
            return
        c.drawImageRect(self.img[name + '/paper'], r, r, SAMP, skia.Paint())
        for k in range(3):
            p = ramp(t, *PASS[k])
            if p <= 0:
                continue
            Xw = lerp(-1.4, 1.4, p)
            c.save()
            if p < 1:
                ux = pn.U[0]
                if abs(ux) > 1e-3:
                    ulim = (Xw - pn.O[0]) / ux
                    px = (ulim - pn.T[0, 2]) / pn.T[0, 0]
                    if ux > 0:
                        c.clipRect(skia.Rect.MakeLTRB(-1e5, -1e5, px, 1e5))
                    else:
                        c.clipRect(skia.Rect.MakeLTRB(px, -1e5, 1e5, 1e5))
            c.drawImageRect(self.img['%s/ink%d' % (name, k)], r, r, SAMP, skia.Paint(BlendMode=skia.BlendMode.kMultiply))
            c.restore()

    def post(self, c, arr, t, cam, R):
        k = int(t * 15 + 0.5)
        f = ((k * 7919) % 13) / 13.0 - 0.5
        c.drawRect(skia.Rect.MakeWH(W, H), skia.Paint(Color=skia.Color(255, 255, 255, int(10 + 10 * f)) if f > 0 else skia.Color(0, 0, 30, int(-14 * f))))
        super().post(c, arr, t, cam, R)


# =====================================================================================================
# 3. Naturalist's field atlas: pen and pencil first, watercolour floods in from back to front
# =====================================================================================================
PAL_FIELD = dict(
    paper=(244, 237, 221), ink=(70, 52, 44), moon=(250, 236, 186), mare=(232, 206, 146), rockA=(176, 196, 206),
    rockB=(126, 160, 168), rockC=(88, 124, 132), leafA=(156, 192, 120), leafB=(96, 154, 90), leafC=(54, 114, 80),
    trunk=(158, 118, 86), water=(104, 178, 208), foam=(250, 250, 246), stone=(214, 176, 126), stoneD=(120, 82, 70),
    lantern=(246, 158, 54), robe1=(208, 76, 54), robe2=(234, 184, 66), robe3=(198, 100, 140), skin=(226, 186, 156),
    hat=(226, 204, 150), fur=(122, 84, 62), toucan=(52, 54, 68), bib=(246, 232, 160), beak=(240, 140, 44),
    heron=(238, 240, 238), heronD=(96, 114, 134), canoe=(166, 70, 54), rope=(190, 160, 120), plank=(160, 120, 90),
    bank=(234, 216, 170), grass=(182, 210, 142), board=(238, 228, 206), cover=(92, 104, 80), gold=(216, 170, 76),
    tab=(244, 237, 221))
PAL_FIELD = Pal(PAL_FIELD, lambda c: mix(c, (244, 237, 221), 0.14))


class FieldStyle(Style):
    idx, name = 3, 'field-atlas'
    feel = (0.62, 13.0, 12.0)
    pal = PAL_FIELD
    bg = (150, 142, 128)
    lamp = v3(-3.0, -0.9, 3.0)
    sh_col = (58, 62, 82)
    sh_alpha = 0.30
    amb, dif = 0.80, 0.30
    flow_col, flow_a = (255, 255, 255), 0.8
    mist_col, mist_a = (255, 255, 252), 0.5
    bird_col = (64, 54, 50)
    lantern_a = 0.4
    vignette = 0.28
    grain = 0.05
    BLOOM0, BLOOM_STEP, BLOOM_DUR = 4.85, 0.36, 1.5

    def paint_piece(self, pc):
        pal = self.pal
        sil = silhouette(pc)
        h, w = sil.shape
        flatp = pc.name in PAGE_PIECES
        far = pc.depth < 0.2 and not flatp
        pen = (112, 106, 108) if far else (70, 52, 44)
        papc = col(pal['paper'])

        def lines(c):
            for s in pc.shapes:
                c.save()
                if s.clip is not None:
                    c.clipPath(s.clip, True)
                if s.kind == 'fill':
                    c.drawPath(s.path, skia.Paint(AntiAlias=True, Color=papc))
                    if not (pc.name == 'map' and s.mat in ('grass', 'paper')):
                        pa = skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=0.0021 if not far else 0.0017,
                                        StrokeJoin=skia.Paint.kRound_Join, Color=col(pen, 225))
                        pa.setPathEffect(skia.DiscretePathEffect.Make(0.035, 0.0011, 3))
                        c.drawPath(s.path, pa)
                        if s.mat == 'ink':
                            c.drawPath(s.path, skia.Paint(AntiAlias=True, Color=col(pen, 235)))
                elif s.kind == 'shade':
                    c.clipPath(s.path, True)
                    b = s.path.getBounds()
                    pa = skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=0.0014, Color=col((92, 90, 98), 120))
                    pa.setPathEffect(skia.DiscretePathEffect.Make(0.03, 0.0012, 7))
                    step = 0.0085
                    n = int((b.width() + b.height()) / step) + 2
                    for i in range(n):
                        x = b.left() - b.height() + i * step
                        c.drawLine(x, b.top(), x + b.height() * 0.8, b.bottom(), pa)
                elif s.kind == 'line':
                    pa = skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=s.w, StrokeCap=skia.Paint.kRound_Cap,
                                    Color=col(pen if s.mat == 'ink' else tone_col(pal[s.mat], -0.5), 190))
                    pa.setPathEffect(skia.DiscretePathEffect.Make(0.03, 0.0008, 5))
                    c.drawPath(s.path, pa)
                c.restore()
        la = raster(pc, lines)
        lrgb, _ = unpremul(la)
        tex = fibre(h, w, 5, 0.55) * (1 + 0.05 * (fbm(h, w, 3.0, 61, 2) - 0.5))
        lrgb = lrgb * tex[..., None]

        def wash(c):
            for s in pc.shapes:
                if s.kind == 'line' or s.mat in ('paper', 'tab', 'ink'):
                    continue
                c.save()
                if s.clip is not None:
                    c.clipPath(s.clip, True)
                if s.kind == 'fill':
                    c.drawPath(s.path, skia.Paint(AntiAlias=True, Color=col(tone_col(pal[s.mat], s.tone * 0.8)), BlendMode=skia.BlendMode.kSrc))
                elif s.kind == 'shade':
                    c.drawPath(s.path, skia.Paint(AntiAlias=True, Color=col(tone_col(pal[s.mat], -0.55), 120)))
                else:
                    c.drawPath(s.path, skia.Paint(AntiAlias=True, Color=col(pal['paper'], 120)))
                c.restore()
        wa = raster(pc, wash)
        wrgb, a = unpremul(wa)
        wp = blur(wa.astype(np.float32) / 255, 1.5)
        a = wp[..., 3]
        wrgb = wp[..., :3] / np.maximum(a, 1e-3)[..., None]
        paper = np.array(pal['paper'], np.float32) / 255
        low = fbm(h, w, 110, 71, 3)
        gran = fbm(h, w, 4.0, 72, 3)
        wrgb = wrgb + (paper - wrgb) * (0.26 * low ** 1.5)[..., None]
        wrgb = np.clip((wrgb - wrgb.mean(-1, keepdims=True)) * 1.18 + wrgb.mean(-1, keepdims=True), 0, 1)
        wrgb = wrgb * (1 - 0.16 * (gran - 0.5))[..., None]
        L = wrgb.mean(-1) * a + (1 - a)
        e = np.abs(L - blur(L, 2.5))
        wrgb = wrgb * (1 - np.clip(e * 3.0, 0, 0.28))[..., None]
        gap = np.clip((blur(sil, 3.0) - 0.42 + 0.5 * (fbm(h, w, 16, 73, 3) - 0.5)) * 6, 0, 1)
        if flatp:
            gap = np.ones_like(sil)
        a = np.clip(a * gap * 0.94, 0, 1) * sil
        wrgb = np.clip(wrgb, 0, 1)
        art = lrgb * (1 - a[..., None] * (1 - wrgb))
        # bloom order map
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        if pc.name == 'map':
            B = yy / h * 0.85
        else:
            rng = np.random.default_rng(len(pc.name) * 13)
            ys, xs = np.nonzero(sil[::8, ::8] > 0.5)
            B = np.full((h, w), 1e9, np.float32)
            for _ in range(3):
                i = int(rng.integers(0, len(ys)))
                B = np.minimum(B, np.hypot(xx - xs[i] * 8, yy - ys[i] * 8))
            B = B / (B[sil > 0.5].max() + 1e-6) * 0.8
        B = np.clip(B + 0.3 * fbm(h, w, 80, 74, 3) + 0.05 * fbm(h, w, 9, 75, 2), 0, 1.2) / 1.2
        bl = np.zeros((h, w, 4), np.uint8)
        bl[..., 3] = np.clip(B * 255, 0, 255)
        return {'art': premul(np.clip(art, 0, 1), sil), 'line': premul(np.clip(lrgb, 0, 1), sil),
                'wash': premul(wrgb, a.astype(np.float32)), 'bloom': bl}

    def paint_desk(self):
        rgb, X, Y = flat_desk(self, (234, 224, 204), (196, 186, 170), 0.04)
        h, w = rgb.shape[:2]
        weave = 0.5 + 0.25 * (np.sin(X * 520) + np.sin(Y * 520))
        rgb = rgb * (0.97 + 0.05 * weave)[..., None]
        light = 0.72 + 0.4 / (1 + ((X + 1.2) / 3.5) ** 2 + ((Y + 0.2) / 3.2) ** 2)
        rgb = rgb * light[..., None]
        arr = premul(np.clip(rgb, 0, 1), np.ones((h, w), np.float32))
        surf = skia.Surface(arr)
        c = surf.getCanvas()
        x0, y0, x1, y1 = self.desk_bbox
        c.scale(self.desk_res, -self.desk_res)
        c.translate(-x0, -y1)
        # a pencil and a brush resting by the atlas
        for (px, py, ang, ln, body, tip) in [(1.9, -0.55, 74, 1.05, (196, 70, 52), (60, 50, 46)), (2.12, -0.35, 82, 0.95, (70, 60, 52), (88, 132, 150))]:
            c.save()
            c.translate(px, py)
            c.rotate(ang)
            sh = skia.Paint(AntiAlias=True, Color=col(self.sh_col, 90))
            sh.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 0.012))
            c.drawRect(skia.Rect.MakeLTRB(0.01, -0.035, ln, 0.0), sh)
            c.drawRect(skia.Rect.MakeLTRB(0, -0.016, ln * 0.86, 0.016), skia.Paint(AntiAlias=True, Color=col(body)))
            c.drawRect(skia.Rect.MakeLTRB(0, 0.004, ln * 0.86, 0.016), skia.Paint(AntiAlias=True, Color=col(mix(body, (255, 255, 255), 0.25))))
            c.drawPath(SC.poly([(ln * 0.86, -0.016), (ln, 0), (ln * 0.86, 0.016)]), skia.Paint(AntiAlias=True, Color=col((226, 200, 160))))
            c.drawPath(SC.poly([(ln * 0.95, -0.006), (ln, 0), (ln * 0.95, 0.006)]), skia.Paint(AntiAlias=True, Color=col(tip)))
            c.restore()
        return arr

    def bloom_p(self, name, t):
        if name == 'map':
            return ramp(t, self.BLOOM0, self.BLOOM0 + 2.7 * self.pace)
        i = self.pcs[name].lock
        a = self.BLOOM0 + self.BLOOM_STEP * i * self.pace
        return ramp(t, a, a + self.BLOOM_DUR * self.pace)

    def draw_art(self, c, name, r, t, pn):
        if t < 0 or name not in self.sc.order + ['map']:
            c.drawImageRect(self.img[name + '/art'], r, r, SAMP, skia.Paint())
            return
        p = self.bloom_p(name, t)
        if p >= 1:
            c.drawImageRect(self.img[name + '/art'], r, r, SAMP, skia.Paint())
            return
        c.drawImageRect(self.img[name + '/line'], r, r, SAMP, skia.Paint())
        if p <= 0:
            return
        k = 4.0
        pe = p * (1 + 1 / k) * 1.02
        c.saveLayer(r, skia.Paint(BlendMode=skia.BlendMode.kMultiply))
        c.drawImageRect(self.img[name + '/wash'], r, r, SAMP, skia.Paint())
        cf = skia.ColorFilters.Matrix([0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, -k, k * pe])
        c.drawImageRect(self.img[name + '/bloom'], r, r, SAMP, skia.Paint(ColorFilter=cf, BlendMode=skia.BlendMode.kDstIn))
        c.restore()

    def draw_bird(self, c, path, fade):
        pa = skia.Paint(AntiAlias=True, Color=col(self.bird_col, 235 * fade))
        c.drawPath(path, pa)


# =====================================================================================================
# 4. Night lantern atlas: luminous inks on indigo paper, lit by the moon
# =====================================================================================================
LUM = dict(
    paper=(120, 140, 220), ink=(150, 170, 255), moon=(255, 244, 204), mare=(170, 130, 70), rockA=(110, 150, 255),
    rockB=(120, 172, 255), rockC=(130, 192, 255), leafA=(80, 230, 170), leafB=(90, 255, 180), leafC=(110, 255, 170),
    trunk=(255, 180, 120), water=(90, 230, 255), foam=(220, 250, 255), stone=(255, 190, 110), stoneD=(200, 110, 60),
    lantern=(255, 170, 70), robe1=(255, 110, 150), robe2=(255, 220, 120), robe3=(200, 150, 255), skin=(255, 210, 180),
    hat=(255, 230, 160), fur=(255, 170, 120), toucan=(150, 170, 255), bib=(255, 240, 170), beak=(255, 170, 60),
    heron=(225, 240, 255), heronD=(150, 180, 255), canoe=(255, 130, 110), rope=(230, 200, 150), plank=(230, 190, 140),
    bank=(150, 170, 230), grass=(70, 180, 150), board=(120, 140, 220), cover=(90, 100, 180), gold=(255, 210, 120),
    tab=(150, 170, 255))
def _lum_col(c):
    m = max(max(c), 1)
    return mix(tuple(x * 255.0 / m for x in c), (255, 255, 255), 0.15)


def _lum_fill(c):
    mx, mn = max(c) / 255.0, min(c) / 255.0
    sat = (mx - mn) / max(mx, 1e-3)
    return int(10 + 190 * clamp((sat * mx - 0.35) / 0.5) + 120 * clamp((mn - 0.75) / 0.25))


LUM = Pal(LUM, _lum_col)
LUM_FILL = dict(moon=140, mare=150, lantern=255, foam=170, robe1=190, robe2=190, robe3=190, beak=220, bib=200, heron=150,
                hat=150, skin=110, canoe=120, water=38, gold=220, stone=26, leafA=16, leafB=16, leafC=16, plank=90, rope=120,
                heronD=40, toucan=30, fur=40, trunk=22, rockA=10, rockB=10, rockC=10)
LUM_FILL = Pal(LUM_FILL, _lum_fill)


class NightStyle(Style):
    idx, name = 4, 'night-lantern'
    feel = (0.30, 9.0, 16.0)
    pal = LUM
    bg = (4, 4, 12)
    amb, dif = 0.86, 0.16
    sh_col = (3, 3, 16)
    board_shadow = False
    gutter = 1.6
    slot_col = (4, 4, 14)
    flow_col, flow_a, flow_blend = (190, 248, 255), 0.95, skia.BlendMode.kPlus
    mist_col, mist_a, mist_blend, mist_speed = (120, 160, 255), 0.42, skia.BlendMode.kPlus, 0.7
    bird_col, bird_speed = (214, 236, 255), 0.7
    lantern_col, lantern_a = (255, 170, 70), 1.0
    lantern_t0, lantern_dt = 5.7, 0.2
    vignette = 0.75
    grain = 0.05

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.pal_rgb = dict(paper=(40, 42, 90), cover=(16, 18, 48), board=(30, 32, 74))
        sun = self.sc.sun
        self.sun_piece = sun[0] if sun else None
        self.sun_uv = self.pcs[sun[0]].anchors[sun[1]] if sun else (0.0, 0.62)
        self.moon_light = v3(self.sun_uv[0] * 0.97, 0.32, self.sun_uv[1] + 0.365)

    def moon_level(self, t):
        return 0.12 + 0.88 * smooth(ramp(t, 4.45, 5.5))

    def begin(self, t, theta=math.pi):
        self.now = t
        self.theta = theta
        if theta > 1e-5:
            self.shadow_light = self.moon_light
            self.sh_alpha = 0.62 * self.moon_level(t)
            self.ground_sh, self.piece_sh = 1.0, 0.0
        else:
            self.shadow_light = self.lamp
            self.sh_alpha = 0.3
        self.flow_fall = ramp(t, 5.25, 5.9)
        self.flow_ground = ramp(t, 6.0, 7.0)

    def paint_piece(self, pc):
        sil = silhouette(pc)
        h, w = sil.shape
        flatp = pc.name in PAGE_PIECES
        far_i, near_i = (50, 56, 116), (20, 20, 54)
        base_i = mix(far_i, near_i, pc.depth) if not flatp else (30, 32, 76)
        board = pc.name in ('jacket', 'cover')

        def base(c):
            for s in pc.shapes:
                if s.kind == 'line':
                    continue
                c.save()
                if s.clip is not None:
                    c.clipPath(s.clip, True)
                if s.kind == 'fill':
                    k = 0.14 if s.mat not in ('moon', 'mare') else 0.22
                    colr = mix(base_i, LUM[s.mat], k)
                    colr = tone_col(colr, s.tone * 0.5)
                    if s.mat == 'cover':
                        colr = (16, 18, 48)
                    elif board and s is pc.shapes[0]:      # the cover cloth: nearly black, with a breath of its own colour
                        colr = mix((16, 18, 48), LUM[s.mat], 0.2)
                    c.drawPath(s.path, skia.Paint(AntiAlias=True, Color=col(colr)))
                elif s.kind == 'shade':
                    c.drawPath(s.path, skia.Paint(AntiAlias=True, Color=skia.Color(4, 4, 20, 70)))
                c.restore()
        ba = raster(pc, base)
        brgb, _ = unpremul(ba)
        brgb = brgb * fibre(h, w, 13, 0.7)[..., None]

        def lum(c, water=False):
            last = 'paper'
            for s in pc.shapes:
                iw = s.mat in ('water', 'foam')
                if s.kind == 'fill':
                    last = s.mat
                c.save()
                if s.clip is not None:
                    c.clipPath(s.clip, True)
                lc = LUM[s.mat if s.mat != 'ink' else last] if s.kind == 'line' else LUM[s.mat]
                if water:
                    if iw and s.kind == 'fill':
                        c.drawPath(s.path, skia.Paint(AntiAlias=True, Color=col(lc, 95 if s.mat == 'water' else 220)))
                    elif iw and s.kind == 'hi':
                        c.drawPath(s.path, skia.Paint(AntiAlias=True, Color=col((225, 252, 255), 235)))
                    elif s.kind == 'fill':
                        c.drawPath(s.path, skia.Paint(AntiAlias=True, BlendMode=skia.BlendMode.kClear))
                    c.restore()
                    continue
                if s.kind == 'fill':
                    fa = LUM_FILL.get(s.mat, 0)
                    if board and s is pc.shapes[0]:
                        fa = 0
                    if fa and s.mat not in ('moon', 'mare', 'lantern'):
                        # big glowing areas wash out to white, so the larger the shape the dimmer its fill
                        bb = s.path.computeTightBounds()
                        fa = int(fa * max(0.3, min(1.0, (0.012 / max(bb.width() * bb.height(), 1e-6)) ** 0.5)))
                    c.drawPath(s.path, skia.Paint(AntiAlias=True, BlendMode=skia.BlendMode.kClear))
                    if fa:
                        c.drawPath(s.path, skia.Paint(AntiAlias=True, Color=col(lc, fa)))
                    if not (pc.name == 'map' and s.mat in ('grass', 'paper')) and s.mat not in ('moon',):
                        pa = skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=0.0021,
                                        StrokeJoin=skia.Paint.kRound_Join, Color=col(lc, 235))
                        c.drawPath(s.path, pa)
                    if s.mat == 'ink':
                        c.drawPath(s.path, skia.Paint(AntiAlias=True, Color=col(lc, 240)))
                elif s.kind == 'hi':
                    c.drawPath(s.path, skia.Paint(AntiAlias=True, Color=col(lc, 46)))
                elif s.kind == 'line':
                    pa = skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=s.w, StrokeCap=skia.Paint.kRound_Cap,
                                    Color=col(lc, 150))
                    c.drawPath(s.path, pa)
                c.restore()
        la = raster(pc, lum).astype(np.float32) / 255
        la *= sil[..., None]
        # a soft halo baked around the bright ink
        halo = blur(la, 5.0) * 0.55 * sil[..., None]
        lumo = np.clip(la + halo, 0, 1)
        out = {'lum': np.clip(lumo * 255, 0, 255).astype(np.uint8)}
        # dim, unlit appearance
        dim = brgb * 0.9 + lumo[..., :3] * 0.22
        out['art'] = premul(np.clip(dim, 0, 1), sil)
        has_water = any(s.mat in ('water', 'foam') for s in pc.shapes)
        if has_water and (pc.flows or pc.name == 'map'):
            wl = raster(pc, lambda c: lum(c, True)).astype(np.float32) / 255
            wl *= sil[..., None]
            wl = np.clip(wl + blur(wl, 4.0) * 0.5, 0, 1)
            out['wlum'] = np.clip(wl * 255, 0, 255).astype(np.uint8)
            yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
            if pc.name == 'map' and pc.flow_axis is not None:
                # distance along the river
                pts = np.array(pc.flow_axis, np.float32)
                seg = np.linspace(0, len(pts) - 1, 160)
                samp = np.stack([np.interp(seg, np.arange(len(pts)), pts[:, 0]), np.interp(seg, np.arange(len(pts)), pts[:, 1])], 1)
                sx = (samp[:, 0] - pc.bbox[0]) * pc.res
                sy = (pc.bbox[3] - samp[:, 1]) * pc.res
                xs, ys = xx[::6, ::6], yy[::6, ::6]
                d = (xs[..., None] - sx) ** 2 + (ys[..., None] - sy) ** 2
                B = d.argmin(-1).astype(np.float32) / 159
                B = ndi.zoom(B, 6.02, order=1)[:h, :w]
            else:
                B = yy / h
            bl = np.zeros((h, w, 4), np.uint8)
            bl[..., 3] = np.clip(B * 255, 0, 255)
            out['wmap'] = bl
        if pc.name in self.sc.order and pc.name != self.sun_piece:
            # rim light on the edges that face the moon
            sb = blur(sil, 1.6)
            gy, gx = np.gradient(sb)
            yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
            mu, mv = self.sun_uv if pc.slider is None else (-0.5, 0.6)
            dx = (mu - pc.bbox[0]) * pc.res - xx
            dy = (pc.bbox[3] - mv) * pc.res - yy
            dn = np.hypot(dx, dy) + 1e-3
            rim = np.clip(-(gx * dx + gy * dy) / dn * 3.2, 0, 1) * sil
            rim = np.clip(rim + blur(rim, 2.5) * 0.6, 0, 1).astype(np.float32)
            out['rim'] = premul(np.ones((h, w, 3), np.float32) * (np.array([186, 214, 255], np.float32) / 255), rim * 0.9)
        return out

    def page_back(self, right, paper):
        return np.ones_like(right) * (np.array([34, 36, 82], np.float32) / 255) * 0.9 + blur(right, 2.0) * 0.12

    def paint_desk(self):
        rgb, X, Y = flat_desk(self, (16, 17, 36), (6, 6, 16), 0.12)
        h, w = rgb.shape[:2]
        g = ndi.zoom(fbm(h, w // 12, 5, 21, 4), (1, 12.01), order=1)[:, :w]
        rgb = rgb * (0.8 + 0.4 * g)[..., None]
        light = 0.5 + 0.9 / (1 + (X / 3.0) ** 2 + ((Y + 0.2) / 2.6) ** 2)
        rgb = rgb * light[..., None]
        return premul(np.clip(rgb, 0, 1), np.ones((h, w), np.float32))

    def draw_art(self, c, name, r, t, pn):
        img = self.img
        c.drawImageRect(img[name + '/art'], r, r, SAMP, skia.Paint())
        if name + '/lum' not in img:
            return
        pop = t >= 0 and name in self.sc.order + ['map']
        m = self.moon_level(t) if pop else 0.5
        c.drawImageRect(img[name + '/lum'], r, r, SAMP, skia.Paint(BlendMode=skia.BlendMode.kPlus, Alphaf=(0.2 + 0.8 * m) * (0.5 if name == self.sun_piece else 1.0)))
        if not pop:
            return
        if name + '/rim' in img:
            c.drawImageRect(img[name + '/rim'], r, r, SAMP, skia.Paint(BlendMode=skia.BlendMode.kPlus, Alphaf=m))
        if name + '/wlum' in img:
            a = 5.0 + 0.4 * self.pcs[name].lock
            a, b = (5.85, 7.0) if name == 'map' else (a, a + 0.55)
            p = ramp(t, a, b)
            if p > 0:
                c.saveLayer(r, skia.Paint(BlendMode=skia.BlendMode.kPlus))
                c.drawImageRect(img[name + '/wlum'], r, r, SAMP, skia.Paint())
                if p < 1:
                    k = 9.0
                    cf = skia.ColorFilters.Matrix([0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, -k, k * p * (1 + 1 / k)])
                    c.drawImageRect(img[name + '/wmap'], r, r, SAMP, skia.Paint(ColorFilter=cf, BlendMode=skia.BlendMode.kDstIn))
                c.restore()

    def ground_fx(self, c, Hp, clip, t, R, is_right):
        m = self.moon_level(t)
        c.save()
        c.concat(skm(Hp))
        sh = skia.GradientShader.MakeRadial(skia.Point(0, 0.02), 1.5, [col((150, 176, 255), 86 * m), col((110, 140, 255), 34 * m), col((90, 120, 255), 0)], [0, 0.5, 1])
        c.drawRect(skia.Rect.MakeLTRB(-PW, -PH, PW, PH), skia.Paint(Shader=sh, BlendMode=skia.BlendMode.kSrcATop))
        c.restore()

    def piece_fx(self, c, name, pn, t, R):
        # warm pools of lantern light on the paper itself
        pc = self.pcs[name]
        for i, (pnm, an, size) in enumerate(self.sc.glows):
            if pnm != name:
                continue
            lv = self.lantern_level(i, t)
            if lv <= 0.01:
                continue
            u, v = pc.anchors[an]
            rad = 0.2 if size >= 1 else 0.12
            c.save()
            c.concat(skm(pn.Hp))
            sh = skia.GradientShader.MakeRadial(skia.Point(u, v), rad, [col((255, 176, 84), 120 * lv), col((255, 150, 70), 0)])
            c.drawCircle(u, v, rad, skia.Paint(Shader=sh, BlendMode=skia.BlendMode.kSrcATop))
            c.restore()

    def post_piece(self, c, name, t, cam, R, panels):
        if name != self.sun_piece or not panels.get(name):
            return
        m = self.moon_level(t)
        P = R.anchor_world(panels, name, self.sc.sun[1])
        sx, sy, d = cam.proj(P)
        r = self.sc.sun[2] * cam.fl / d
        for (k, colr, a) in ((2.4, (255, 236, 190), 80), (6.0, (120, 150, 255), 56)):
            sh = skia.GradientShader.MakeRadial(skia.Point(sx, sy), r * k, [col(colr, 0), col(colr, 0), col(colr, a * m), col(colr, a * m * 0.3), col(colr, 0)],
                                                [0, 0.9 / k, 1.02 / k, 0.25 + 0.75 / k, 1])
            c.drawCircle(sx, sy, r * k, skia.Paint(Shader=sh, BlendMode=skia.BlendMode.kPlus))

    def overlay(self, c, t, cam, R, panels):
        super().overlay(c, t, cam, R, panels)
        for f in R.flies:
            tau = t - f['t0']
            if tau <= 0:
                continue
            P = v3(f['x'] + 0.05 * math.sin(tau * f['fr'] + f['ph']), f['y'] + 0.03 * math.cos(tau * f['fr'] * 0.7 + f['ph']),
                   f['z0'] + f['sp'] * tau)
            sx, sy, d = cam.proj(P)
            a = smooth(ramp(tau, 0, 0.8)) * (0.55 + 0.45 * math.sin(tau * 3.1 * f['fr'] + f['ph'] * 3)) * (1 - ramp(P[2], 0.75, 1.1)) * R.rel
            if a <= 0.02:
                continue
            r = 0.02 * cam.fl / d
            sh = skia.GradientShader.MakeRadial(skia.Point(sx, sy), r, [col((225, 255, 150), 255 * a), col((170, 255, 110), 80 * a), col((120, 255, 90), 0)], [0, 0.25, 1])
            c.drawCircle(sx, sy, r, skia.Paint(Shader=sh, BlendMode=skia.BlendMode.kPlus))

    def draw_bird(self, c, path, fade):
        c.drawPath(path, skia.Paint(AntiAlias=True, Color=col(self.bird_col, 230 * fade)))

    def post(self, c, arr, t, cam, R):
        # bloom
        small = skia.Surface(W // 4, H // 4)
        sc = small.getCanvas()
        img = skia.Image.fromarray(arr, colorType=skia.kRGBA_8888_ColorType, alphaType=skia.kPremul_AlphaType, copy=False)
        cf = skia.ColorFilters.Matrix([1.5, 0, 0, 0, -0.42, 0, 1.5, 0, 0, -0.42, 0, 0, 1.5, 0, -0.42, 0, 0, 0, 0, 1])
        sc.drawImageRect(img, skia.Rect.MakeWH(W, H), skia.Rect.MakeWH(W // 4, H // 4), SAMP_L, skia.Paint(ColorFilter=cf))
        bl = small.makeImageSnapshot()
        pa = skia.Paint(BlendMode=skia.BlendMode.kPlus, Alphaf=0.36)
        pa.setImageFilter(skia.ImageFilters.Blur(7, 7))
        c.save()
        c.scale(4, 4)
        c.drawImage(bl, 0, 0, SAMP_L, pa)
        c.restore()
        super().post(c, arr, t, cam, R)


# =====================================================================================================
# 5. Gilded engraver's atlas: hand-coloured copperplate, gold leaf, oxblood leather
# =====================================================================================================
PAL_ENGR = dict(
    paper=(236, 224, 196), ink=(46, 32, 26), moon=(216, 174, 82), mare=(178, 134, 56), rockA=(178, 162, 200),
    rockB=(92, 118, 176), rockC=(54, 74, 142), leafA=(122, 178, 128), leafB=(24, 136, 94), leafC=(10, 100, 78),
    trunk=(130, 86, 56), water=(38, 152, 180), foam=(242, 246, 238), stone=(228, 160, 68), stoneD=(122, 40, 44),
    lantern=(222, 178, 80), robe1=(178, 30, 48), robe2=(224, 170, 50), robe3=(134, 70, 162), skin=(226, 190, 160),
    hat=(220, 196, 140), fur=(114, 72, 52), toucan=(44, 38, 46), bib=(240, 226, 160), beak=(228, 120, 40),
    heron=(238, 238, 230), heronD=(82, 98, 130), canoe=(152, 40, 44), rope=(180, 150, 110), plank=(140, 100, 70),
    bank=(234, 214, 162), grass=(190, 208, 150), board=(232, 220, 190), cover=(104, 24, 28), gold=(216, 174, 82),
    tab=(236, 224, 196))
PAL_ENGR = Pal(PAL_ENGR, lambda c: mix(c, (0, 0, 0), 0.06))
ENGR_TONE = dict(paper=1.0, ink=1.0, moon=1.0, mare=1.0, gold=1.0, lantern=1.0, rockA=0.74, rockB=0.6, rockC=0.5, leafA=0.72,
                 leafB=0.6, leafC=0.5, trunk=0.55, water=0.72, foam=0.98, stone=0.72, stoneD=0.2, grass=0.93, bank=0.95,
                 board=0.97, cover=0.62, tab=1.0, heron=0.92, bib=0.95, skin=0.9, hat=0.85)
ENGR_ANG = dict(rockA=80, rockB=82, rockC=78, leafA=28, leafB=32, leafC=24, trunk=86, water=0, stone=2, stoneD=45,
                grass=14, cover=40, board=20)
ENGR_TONE = Pal(ENGR_TONE, lambda c: clamp(0.25 + 0.75 * _lum(c), 0.2, 0.98))
ENGR_ANG = Pal(ENGR_ANG, lambda c: (20, 45, 70, 110, 135, 160)[(c[0] * 3 + c[1] * 5 + c[2] * 7) % 6])
GOLD_MATS = ('moon', 'mare', 'gold', 'lantern')


class EngraverStyle(Style):
    idx, name = 5, 'gilded-engraving'
    feel = (1.0, 11.0, 12.0)
    pal = PAL_ENGR
    bg = (14, 10, 8)
    sh_col = (36, 18, 12)
    sh_alpha = 0.44
    flow_col, flow_a, flow_w = (250, 244, 226), 0.85, 0.7
    mist_col, mist_a, mist_speed = (244, 236, 214), 0.34, 0.6
    bird_col, bird_speed = (40, 28, 24), 0.75
    lantern_col, lantern_a = (255, 200, 110), 0.5
    vignette = 0.66
    grain = 0.05

    def paint_piece(self, pc):
        pal = self.pal
        sil = silhouette(pc)
        h, w = sil.shape
        flatp = pc.name in PAGE_PIECES
        skip_outline = lambda s: pc.name == 'map' and s.mat in ('grass', 'paper')

        def wash(c):
            for s in pc.shapes:
                if s.kind == 'line' or s.mat == 'ink' or (s.mat in ('paper', 'tab') and pc.name != 'jacket'):
                    continue
                c.save()
                if s.clip is not None:
                    c.clipPath(s.clip, True)
                if s.kind == 'fill':
                    c.drawPath(s.path, skia.Paint(AntiAlias=True, Color=col(tone_col(pal[s.mat], s.tone * 0.6)), BlendMode=skia.BlendMode.kSrc))
                elif s.kind == 'shade' and s.mat not in GOLD_MATS:
                    c.drawPath(s.path, skia.Paint(AntiAlias=True, Color=col(tone_col(pal[s.mat], -0.5), 90)))
                c.restore()

        def tone(c):
            for s in pc.shapes:
                if s.kind == 'line':
                    continue
                c.save()
                if s.clip is not None:
                    c.clipPath(s.clip, True)
                if s.kind == 'fill':
                    t0 = ENGR_TONE.get(s.mat, 0.66) + 0.1 * s.tone
                    b = s.path.getBounds()
                    if t0 < 0.97:
                        a, bb = clamp(t0 + 0.15), clamp(t0 - 0.17)
                        sh = skia.GradientShader.MakeLinear([skia.Point(b.left(), b.bottom()), skia.Point(b.right(), b.top())],
                                                            [skia.Color(int(255 * a), int(255 * a), int(255 * a)), skia.Color(int(255 * bb), int(255 * bb), int(255 * bb))])
                        pa = skia.Paint(AntiAlias=True)
                        pa.setShader(sh)
                    else:
                        pa = skia.Paint(AntiAlias=True, Color=skia.Color(255, 255, 255))
                    c.drawPath(s.path, pa)
                elif s.kind == 'shade' and s.mat not in GOLD_MATS:
                    c.drawPath(s.path, skia.Paint(AntiAlias=True, Color=skia.Color(0, 0, 0, 92)))
                elif s.kind == 'hi':
                    c.drawPath(s.path, skia.Paint(AntiAlias=True, Color=skia.Color(255, 255, 255, 150)))
                c.restore()

        def angle(c):
            for s in pc.shapes:
                if s.kind != 'fill':
                    continue
                c.save()
                if s.clip is not None:
                    c.clipPath(s.clip, False)
                a = ENGR_ANG.get(s.mat, 45)
                c.drawPath(s.path, skia.Paint(AntiAlias=False, Color=skia.Color(int(a) + 1, 200 if s.mat in ('water',) else 0, 0, 255)))
                c.restore()

        def ink(c):
            for s in pc.shapes:
                c.save()
                if s.clip is not None:
                    c.clipPath(s.clip, True)
                if s.kind == 'fill':
                    c.drawPath(s.path, skia.Paint(AntiAlias=True, BlendMode=skia.BlendMode.kClear))
                    if s.mat == 'ink':
                        c.drawPath(s.path, skia.Paint(AntiAlias=True, Color=0xFFFFFFFF))
                    elif not skip_outline(s):
                        c.drawPath(s.path, skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=0.0023,
                                                      StrokeJoin=skia.Paint.kRound_Join, Color=0xFFFFFFFF))
                elif s.kind == 'line':
                    c.drawPath(s.path, skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=s.w * 0.9,
                                                  StrokeCap=skia.Paint.kRound_Cap, Color=skia.Color(255, 255, 255, 225)))
                c.restore()

        def gold(c):
            for s in pc.shapes:
                if s.kind != 'fill':
                    continue
                c.save()
                if s.clip is not None:
                    c.clipPath(s.clip, True)
                is_g = s.mat in GOLD_MATS or (s.kind == 'line' and s.mat == 'gold')
                c.drawPath(s.path, skia.Paint(AntiAlias=True, Color=0xFFFFFFFF if is_g else 0, BlendMode=skia.BlendMode.kSrc))
                c.restore()
            for s in pc.shapes:
                if s.kind == 'line' and s.mat == 'gold':
                    c.drawPath(s.path, skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=s.w * 1.4, Color=0xFFFFFFFF))

        wa = raster(pc, wash).astype(np.float32) / 255
        wa = blur(wa, 1.1)
        a = wa[..., 3]
        wrgb = wa[..., :3] / np.maximum(a, 1e-3)[..., None]
        tn = raster(pc, tone, clear=0xFFFFFFFF)[..., 0].astype(np.float32) / 255
        tn = blur(tn, 0.8) + 0.10 * (fbm(h, w, 70, 81, 3) - 0.5)
        an = raster(pc, angle)
        ang = np.radians(an[..., 0].astype(np.float32) - 1)
        wavy = an[..., 1] > 100
        lin = raster(pc, ink)[..., 3].astype(np.float32) / 255
        gm = raster(pc, gold)[..., 3].astype(np.float32) / 255
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        wob = 2.2 * (fbm(h, w, 130, 82, 2) - 0.5) * 4
        phi = -xx * np.sin(ang) + yy * np.cos(ang) + wob
        phi = np.where(wavy, yy + 3.0 * np.sin(xx / 15.0 + yy / 40.0) + wob, phi)
        per = 6.4
        tri = np.abs((phi / per) % 1.0 - 0.5) * 2
        dark = np.clip(1 - tn, 0, 1)
        ink1 = np.clip((dark * 1.12 - tri) * 2.6 + 0.5, 0, 1) * (dark > 0.09)
        phi2 = xx * np.cos(ang + 0.35) + yy * np.sin(ang + 0.35) + wob
        tri2 = np.abs((phi2 / per) % 1.0 - 0.5) * 2
        ink2 = np.clip(((dark - 0.5) * 1.9 - tri2) * 2.6 + 0.5, 0, 1) * (dark > 0.5)
        scr = np.maximum(ink1, ink2) * (an[..., 3] > 0) * (1 - gm)
        ink_a = np.clip(np.maximum(scr * 0.92, lin), 0, 1) * sil
        # paper: cream laid
        paper = np.array(pal['paper'], np.float32) / 255
        laid = 1 + 0.018 * np.sin(yy * 2 * np.pi / 5.0) + 0.02 * (np.abs((xx / 150.0) % 1 - 0.5) < 0.01)
        prgb = paper * (fibre(h, w, 17, 0.5) * laid)[..., None]
        mott = 0.72 + 0.28 * fbm(h, w, 60, 83, 3)
        wa_a = np.clip(a * 0.86 * mott, 0, 1)
        rgb = prgb * (1 - wa_a[..., None] * (1 - wrgb))
        # gold leaf
        gcell = (np.floor(xx / 74) * 7 + np.floor(yy / 74) * 13) % 5 / 5.0
        leaf = 0.9 + 0.12 * gcell + 0.16 * (fbm(h, w, 5, 84, 3) - 0.5)
        crack = ((xx % 74) < 1.2) | ((yy % 74) < 1.2)
        gcol = wrgb * leaf[..., None] * (1 - 0.14 * crack)[..., None]
        grad = (0.86 + 0.28 * (1 - yy / h))[..., None]
        rgb = rgb * (1 - gm[..., None]) + gcol * grad * gm[..., None]
        rgb = ink_over(rgb, pal['ink'], ink_a * 0.95)
        out = {'art': premul(np.clip(rgb, 0, 1), sil)}
        if gm.max() > 0.5:
            g = np.clip(gm * sil * (1 - ink_a * 0.8), 0, 1).astype(np.float32)
            out['gold'] = premul(np.ones((h, w, 3), np.float32), g)
        return out

    def paint_desk(self):
        rgb, X, Y = flat_desk(self, (30, 62, 50), (12, 26, 22), 0.10)
        h, w = rgb.shape[:2]
        rgb = rgb * (0.92 + 0.16 * fbm(h, w, 6, 86, 3))[..., None]
        r2 = ((X + 0.6) / 2.8) ** 2 + ((Y + 0.2) / 2.4) ** 2
        light = 0.16 + 1.05 / (1 + r2) ** 1.4
        rgb = rgb * light[..., None] * np.array([1.08, 0.98, 0.84], np.float32)
        bgc = np.array(self.bg, np.float32) / 255
        x0, y0, x1, y1 = self.desk_bbox
        edge = np.clip(np.minimum.reduce([X - x0, x1 - X, Y - y0, y1 - Y]) / 1.5, 0, 1)[..., None]
        rgb = bgc + (rgb - bgc) * edge
        return premul(np.clip(rgb, 0, 1), np.ones((h, w), np.float32))

    def draw_art(self, c, name, r, t, pn):
        c.drawImageRect(self.img[name + '/art'], r, r, SAMP, skia.Paint())
        key = name + '/gold'
        if key not in self.img:
            return
        g = self.img[key]
        wd = float(g.width())
        tt = self.now
        pos = ((tt * 0.16 + 0.35 * pn.n[0] + 0.2 * pn.n[2]) % 1.0) * 2.6 - 0.8
        x = pos * wd
        bw = max(wd * 0.22, 120)
        sh = skia.GradientShader.MakeLinear([skia.Point(x - bw, 0), skia.Point(x + bw, bw * 0.7)],
                                            [skia.Color(255, 240, 190, 0), skia.Color(255, 244, 204, 150), skia.Color(255, 240, 190, 0)])
        c.saveLayer(r, skia.Paint(BlendMode=skia.BlendMode.kPlus))
        c.drawImageRect(g, r, r, SAMP, skia.Paint())
        c.drawRect(r, skia.Paint(Shader=sh, BlendMode=skia.BlendMode.kSrcIn))
        c.restore()

    def draw_bird(self, c, path, fade):
        c.drawPath(path, skia.Paint(AntiAlias=True, Color=col(self.bird_col, 235 * fade)))


STYLES = {1: PaperStyle, 2: RisoStyle, 3: FieldStyle, 4: NightStyle, 5: EngraverStyle}


NAMES = {'cut-paper': 1, 'risograph': 2, 'field-atlas': 3, 'night-lantern': 4, 'gilded-engraving': 5}


def get_style(idx, scene, cache=None, common=None):
    return STYLES[NAMES.get(idx, idx)](scene, cache, common)
