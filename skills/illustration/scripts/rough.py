"""Tiny hand-drawn path generator. Wobble is baked into the paths (no SVG filters needed)."""
import math, random


class Rough:
    def __init__(self, seed=1):
        self.r = random.Random(seed)

    # ---- core -------------------------------------------------------
    def smooth(self, pts):
        d = "M%.1f %.1f" % pts[0]
        n = len(pts)
        for i in range(n - 1):
            p0 = pts[i - 1] if i > 0 else pts[i]
            p1, p2 = pts[i], pts[i + 1]
            p3 = pts[i + 2] if i + 2 < n else pts[i + 1]
            c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
            c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
            d += "C%.1f %.1f %.1f %.1f %.1f %.1f" % (c1[0], c1[1], c2[0], c2[1], p2[0], p2[1])
        return d

    def line_pts(self, x1, y1, x2, y2, j=1.4, bow=None, over=0.0, seg=55):
        L = math.hypot(x2 - x1, y2 - y1) or 1
        ux, uy = (x2 - x1) / L, (y2 - y1) / L
        nx, ny = -uy, ux
        x1 -= ux * over; y1 -= uy * over; L += 2 * over
        n = max(2, int(L / seg) + 1)
        if bow is None:
            bow = self.r.uniform(-1, 1) * min(5, L * 0.018)
        pts = []
        for i in range(n + 1):
            t = i / n
            jj = self.r.uniform(-j, j) * (0.4 if i in (0, n) else 1)
            off = math.sin(t * math.pi) * bow + jj
            pts.append((x1 + ux * L * t + nx * off, y1 + uy * L * t + ny * off))
        return pts

    def line(self, x1, y1, x2, y2, **k):
        return self.smooth(self.line_pts(x1, y1, x2, y2, **k))

    def rect(self, x, y, w, h, j=1.3, over=3.0):
        o = lambda: self.r.uniform(0.3, 1) * over
        return "".join([
            self.line(x, y, x + w, y, j=j, over=o()),
            self.line(x + w, y, x + w, y + h, j=j, over=o()),
            self.line(x + w, y + h, x, y + h, j=j, over=o()),
            self.line(x, y + h, x, y, j=j, over=o()),
        ])

    def ellipse(self, cx, cy, rx, ry, j=0.03, turn=1.1, start=None, n=16, drift=None):
        a0 = self.r.uniform(0, 2 * math.pi) if start is None else start
        steps = int(n * turn)
        drift = self.r.uniform(0.03, 0.08) * self.r.choice([-1, 1]) if drift is None else drift
        pts = []
        for i in range(steps + 1):
            t = i / steps
            a = a0 + 2 * math.pi * turn * t
            k = 1 + drift * (t - 0.5) + self.r.uniform(-j, j)
            pts.append((cx + math.cos(a) * rx * k, cy + math.sin(a) * ry * k))
        return self.smooth(pts)

    def curve(self, pts, j=1.2):
        """Smooth curve through the given points with a little jitter on the inner ones."""
        out = []
        for i, (x, y) in enumerate(pts):
            if 0 < i < len(pts) - 1:
                x += self.r.uniform(-j, j); y += self.r.uniform(-j, j)
            out.append((x, y))
        return self.smooth(out)

    def arrow(self, pts, head=11, spread=0.5, j=1.2):
        d = self.curve(pts, j=j)
        (x1, y1), (x2, y2) = pts[-2], pts[-1]
        a = math.atan2(y2 - y1, x2 - x1)
        for s in (-1, 1):
            b = a + math.pi + s * spread + self.r.uniform(-0.08, 0.08)
            hx, hy = x2 + math.cos(b) * head, y2 + math.sin(b) * head
            d += "M%.1f %.1f L%.1f %.1f" % (hx, hy, x2, y2)
        return d

    def zigzag(self, x1, y1, x2, y2, amp=7, n=6):
        pts = []
        for i in range(n + 1):
            t = i / n
            s = -1 if i % 2 else 1
            pts.append((x1 + (x2 - x1) * t + self.r.uniform(-2, 2), y1 + (y2 - y1) * t + s * amp + self.r.uniform(-1.5, 1.5)))
        return self.smooth(pts)

    def hatch(self, x, y, w, h, angle=45, gap=11, j=1.0):
        """Hatching lines covering the box (clip them with a clipPath)."""
        a = math.radians(angle)
        ux, uy = math.cos(a), math.sin(a)
        nx, ny = -uy, ux
        cx, cy = x + w / 2, y + h / 2
        R = math.hypot(w, h) / 2
        d = ""
        k = -R
        while k <= R:
            g = k + self.r.uniform(-1.5, 1.5)
            ax, ay = cx + nx * g - ux * R, cy + ny * g - uy * R
            bx, by = cx + nx * g + ux * R, cy + ny * g + uy * R
            d += self.line(ax, ay, bx, by, j=j, bow=self.r.uniform(-2, 2), seg=140)
            k += gap * self.r.uniform(0.85, 1.2)
        return d

    def tick(self, x, y, s=14):
        return self.curve([(x, y + s * 0.5), (x + s * 0.35, y + s * 0.85), (x + s * 1.05, y - s * 0.1)], j=0.6)
