"""Shared maths and drawing helpers for the Rio de la Luna pop-up film."""
import math
import numpy as np
import skia
from scipy import ndimage as ndi

W, H, FPS = 1920, 1080, 30
PW = 1.25          # page width (one page)
PH = 0.95          # page half depth (spine runs along y)
RES = 800          # texture pixels per unit for standing pieces
GRES = 720         # texture pixels per unit for flat pages

SAMP = skia.SamplingOptions(skia.FilterMode.kLinear, skia.MipmapMode.kLinear)
SAMP_L = skia.SamplingOptions(skia.FilterMode.kLinear)


def v3(*a):
    return np.array(a, dtype=float)


YH = v3(0, 1, 0)
ZH = v3(0, 0, 1)


def clamp(x, a=0.0, b=1.0):
    return a if x < a else b if x > b else x


def smooth(x):
    x = clamp(x)
    return x * x * (3 - 2 * x)


def smoother(x):
    x = clamp(x)
    return x * x * x * (x * (6 * x - 15) + 10)


def ramp(t, a, b):
    return clamp((t - a) / (b - a))


def lerp(a, b, t):
    return a + (b - a) * t


def spring_step(tau, zeta, omega):
    """Unit step response of a damped spring (0 -> 1)."""
    if tau <= 0:
        return 0.0
    if zeta >= 0.999:
        return 1 - math.exp(-omega * tau) * (1 + omega * tau)
    wd = omega * math.sqrt(1 - zeta * zeta)
    return 1 - math.exp(-zeta * omega * tau) * (
        math.cos(wd * tau) + zeta / math.sqrt(1 - zeta * zeta) * math.sin(wd * tau))


# ----------------------------------------------------------------- camera
class Camera:
    def __init__(self, target, elev, az, dist, fov):
        el, a = math.radians(elev), math.radians(az)
        d = v3(math.sin(a) * math.cos(el), -math.cos(a) * math.cos(el), math.sin(el))
        self.pos = np.asarray(target, float) + d * dist
        f = np.asarray(target, float) - self.pos
        f /= np.linalg.norm(f)
        r = np.cross(f, ZH)
        r /= np.linalg.norm(r)
        u = np.cross(r, f)
        fl = (H / 2) / math.tan(math.radians(fov) / 2)
        R = np.stack([r, -u, f])
        K = np.array([[fl, 0, W / 2], [0, fl, H / 2], [0, 0, 1.0]])
        self.P = K @ np.hstack([R, (-R @ self.pos)[:, None]])
        self.fwd = f
        self.fl = fl

    def proj(self, X):
        h = self.P @ np.append(X, 1.0)
        return h[0] / h[2], h[1] / h[2], h[2]

    def plane(self, O, U, V):
        """Homography taking plane coords (u, v, 1) to screen."""
        return self.P[:, :3] @ np.column_stack([U, V, O]) + np.outer(self.P[:, 3], [0, 0, 1])


def skm(M):
    m = skia.Matrix()
    M = M / M[2, 2] if abs(M[2, 2]) > 1e-12 else M
    m.setAll(*[float(x) for x in M.reshape(9)])
    return m


def tex_to_plane(u0, v1, res):
    """Texture pixel -> plane coords (v up)."""
    return np.array([[1 / res, 0, u0], [0, -1 / res, v1], [0, 0, 1.0]])


def shadow_h(light, cO, cU, cV, rO, rU, rV):
    """Homography: caster plane coords -> receiver plane coords, central projection from light."""
    n = np.cross(rU, rV)
    n /= np.linalg.norm(n)
    d = -n.dot(rO)
    L = np.append(light, 1.0)
    pl = np.append(n, d)
    M = pl.dot(L) * np.eye(4) - np.outer(L, pl)
    A = np.zeros((4, 3))
    A[:3, 0], A[:3, 1], A[:3, 2] = cU, cV, cO
    A[3, 2] = 1
    B = np.linalg.pinv(np.column_stack([rU, rV]))
    Rm = np.zeros((3, 4))
    Rm[:2, :3] = B
    Rm[:2, 3] = -B @ rO
    Rm[2, 3] = 1
    Hm = Rm @ M @ A
    return Hm


# ----------------------------------------------------------------- paper fold kinematics
def fold_axes(theta, alpha_deg, gamma=None):
    """V-fold with glue lines at alpha to the spine, wings toward the viewer.
    Right page is fixed flat, left page is rotated by theta about the spine (0 closed, pi flat).
    Returns glue directions on right and left page, crease direction and the ideal crease angle."""
    a = math.radians(alpha_deg)
    sa, ca = math.sin(a), math.cos(a)
    l = v3(math.cos(theta), 0, math.sin(theta))
    b = v3(math.cos(theta / 2), 0, math.sin(theta / 2))
    g_r = v3(sa, -ca, 0)
    g_l = sa * l - ca * YH
    gam_ideal = math.atan2(ca, sa * max(math.cos(theta / 2), 0.0))
    g = gam_ideal if gamma is None else gamma
    c = math.cos(g) * YH + math.sin(g) * b
    return g_r, g_l, c, gam_ideal


# ----------------------------------------------------------------- numpy <-> skia
def new_surface(w, h):
    arr = np.zeros((h, w, 4), np.uint8)
    info = skia.ImageInfo.Make(w, h, skia.kRGBA_8888_ColorType, skia.kPremul_AlphaType)
    return skia.Surface.MakeRasterDirect(info, arr), arr


def to_image(arr, mip=True):
    """uint8 premultiplied RGBA array -> skia image."""
    img = skia.Image.fromarray(np.ascontiguousarray(arr), colorType=skia.kRGBA_8888_ColorType,
                               alphaType=skia.kPremul_AlphaType, copy=True)
    if mip:
        img = img.withDefaultMipmaps()
    return img


def premul(rgb, a):
    """rgb float 0..1 (h,w,3), a float (h,w) -> uint8 premul RGBA."""
    out = np.empty(rgb.shape[:2] + (4,), np.uint8)
    out[..., :3] = np.clip(rgb * a[..., None] * 255 + 0.5, 0, 255)
    out[..., 3] = np.clip(a * 255 + 0.5, 0, 255)
    return out


def unpremul(arr):
    a = arr[..., 3].astype(np.float32) / 255
    rgb = arr[..., :3].astype(np.float32) / 255
    rgb = rgb / np.maximum(a, 1e-4)[..., None]
    return np.clip(rgb, 0, 1), a


def blur(a, sigma):
    if sigma <= 0:
        return a
    if a.ndim == 3:
        return ndi.gaussian_filter(a, (sigma, sigma, 0), mode='nearest')
    return ndi.gaussian_filter(a, sigma, mode='nearest')


_noise_cache = {}


def fbm(h, w, scale, seed=0, octaves=4, gain=0.5):
    """Smooth fractal noise in 0..1; scale = feature size in px."""
    key = (h, w, scale, seed, octaves)
    if key in _noise_cache:
        return _noise_cache[key]
    rng = np.random.default_rng(seed)
    out = np.zeros((h, w), np.float32)
    amp, tot = 1.0, 0.0
    s = float(scale)
    for _ in range(octaves):
        gh, gw = int(h / s) + 3, int(w / s) + 3
        g = rng.random((gh, gw), dtype=np.float32)
        z = ndi.zoom(g, (h / (gh - 2) + 0.01, w / (gw - 2) + 0.01), order=3, mode='reflect')[:h, :w]
        if z.shape != (h, w):
            z = np.pad(z, ((0, h - z.shape[0]), (0, w - z.shape[1])), mode='edge')
        out += amp * z
        tot += amp
        amp *= gain
        s = max(s / 2, 1.5)
    out /= tot
    out = (out - out.min()) / (out.max() - out.min() + 1e-6)
    if len(_noise_cache) < 40:
        _noise_cache[key] = out
    return out


def white(h, w, seed=0):
    return np.random.default_rng(seed).random((h, w), dtype=np.float32)


def col(c, a=255):
    return skia.Color(int(c[0]), int(c[1]), int(c[2]), int(a))


def mix(c1, c2, t):
    return tuple(c1[i] + (c2[i] - c1[i]) * t for i in range(3))


def tone_col(c, tone):
    """tone -1..1 darkens / lightens."""
    if tone >= 0:
        return mix(c, (255, 255, 255), tone * 0.5)
    return mix(c, (0, 0, 0), -tone * 0.5)
