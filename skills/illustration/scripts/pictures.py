"""The 30 sketchbook pictures. Each one is a way to SHOW one kind of idea.

A picture is a function (P, d): P is the Pen (pen.py) with a box of P.w x P.h pixels,
d is the picture's data from the post file ("hero": {"type": "hub", ...}).
Every picture fills its box in wide, square and tall shapes.
One colored pen mark per picture (the thing to notice): pass "pick" where a picture supports it.
PICTURES at the bottom lists all 30 with the idea shape each one fits and sample data.
"""
import math
import icons as IC
from pen import rect_edge, ell_edge


def _pick(d, i):
    return d.get("pick") is not None and int(d["pick"]) == i


def _label(x):
    return x if isinstance(x, str) else x.get("label") or x.get("title") or x.get("text") or ""


def _icons(d, items):
    """The small icon or logo for each item (a name from icons.py, or None).
    A named app or channel gets its logo. An item can ask for an icon: {"label": "ideas", "icon": "idea"}.
    "icons": "auto" on the picture also guesses everyday icons from the words (all items or none). "icons": false turns them off."""
    return IC.resolve(items, d.get("icons", "logos"))


# which list of a picture can carry icons (the other pictures don't draw them)
ICON_LISTS = {"hub": ["items"], "equation": ["parts"], "steps": ["steps"], "loop": ["nodes"], "pipeline": ["steps"], "funnel": ["stages"],
              "layers": ["layers"], "anatomy": ["parts"], "stickies": ["items"], "machine": ["in", "out"], "table": ["cols"]}


def icons_of(d):
    """(icons this picture will draw, icon names its items asked for). Used by the checks."""
    items = [it for k in ICON_LISTS.get(ALIASES.get(d.get("type"), d.get("type")), []) for it in (d.get(k) or [])]
    asked = [it["icon"] for it in items if isinstance(it, dict) and it.get("icon")]
    return _icons(d, items), asked


# 1 ---------------------------------------------------------------- hub
def hub(P, d):
    u, w, h = P.u, P.w, P.h
    items = d["items"][:7]
    n = len(items)
    cx, cy = w / 2, h / 2
    out = d.get("dir", "out") != "in"
    ic = _icons(d, items)
    if n >= 4 and h < 560 * u:                 # a short space: a row of boxes above the middle and a row below
        top = (n + 1) // 2
        bh, cry = min(96 * u, h * 0.23), max(min(h * 0.13, 70 * u), 50 * u)
        crx = min(w * 0.17, 170 * u)
        for i, it in enumerate(items):
            row, k, m = (0, i, top) if i < top else (1, i - top, n - top)
            bw = min((w - (m - 1) * 26 * u) / m, 300 * u)
            x = cx + (k - (m - 1) / 2) * (bw + 26 * u)
            y = bh / 2 + 4 * u if row == 0 else h - bh / 2 - 4 * u
            p1 = ell_edge(cx, cy, crx, cry, x, y, pad=12 * u)
            p2 = rect_edge(x, y, bw, bh, cx, cy, pad=12 * u)
            P.arrow2(p1, p2, bend=0.06) if out else P.arrow2(p2, p1, bend=0.06)
            pk = _pick(d, i)
            P.box(x - bw / 2, y - bh / 2, bw, bh, wash="wc" if pk else None)
            P.text(x - bw / 2 + 8 * u, y - bh / 2 + 4 * u, bw - 16 * u, bh - 8 * u, _label(it), cls="hand pen" if pk else "hand ink", icon=ic[i], size=40 * u if ic[i] else None)
        P.circle(cx, cy, crx, cry, wash="wb")
        P.text(cx - crx * 0.8, cy - cry * 0.75, crx * 1.6, cry * 1.5, _label(d["center"]), cls="serif", size=44 * u)
        return
    crx, cry = min(w * 0.15, 170 * u), min(h * 0.13, 100 * u)
    bw, bh = min(w * (0.31 if n < 5 or (any(ic) and n < 6) else 0.27), 330 * u), (124 if any(ic) else 112) * u
    RX, RY = w / 2 - bw / 2 - 10 * u, min(h / 2 - bh / 2 - 16 * u, w * 0.5)
    a0 = -math.pi / 2 if n % 2 else -math.pi / 2 + math.pi / n
    for i, it in enumerate(items):
        a = a0 + i * 2 * math.pi / n
        x, y = cx + math.cos(a) * RX, cy + math.sin(a) * RY
        if abs(math.cos(a)) > 0.6:                    # side boxes go all the way out, clear of the middle
            x = cx + math.copysign(RX, math.cos(a))
        p1 = ell_edge(cx, cy, crx, cry, x, y, pad=14 * u)
        p2 = rect_edge(x, y, bw, bh, cx, cy, pad=14 * u)
        if math.hypot(p2[0] - p1[0], p2[1] - p1[1]) > 30 * u:
            P.arrow2(p1, p2, bend=0.08) if out else P.arrow2(p2, p1, bend=0.08)
        pk = _pick(d, i)
        P.box(x - bw / 2, y - bh / 2, bw, bh, wash="wc" if pk else None)
        P.text(x - bw / 2 + 8 * u, y - bh / 2 + 4 * u, bw - 16 * u, bh - 8 * u, _label(it), cls="hand pen" if pk else "hand ink", icon=ic[i], size=40 * u if ic[i] else None)
    P.circle(cx, cy, crx, cry, wash="wb")
    P.text(cx - crx * 0.8, cy - cry * 0.75, crx * 1.6, cry * 1.5, _label(d["center"]), cls="serif", size=46 * u)


# 2 ---------------------------------------------------------------- venn
def venn(P, d):
    u, w, h = P.u, P.w, P.h
    sets = d["sets"][:3]
    mid = d.get("middle")
    note = d.get("note")
    cx = w / 2
    if len(sets) == 3:
        R = min(w / 3.34, h / 3.2)
        if note and mid:
            R = min(w / 3.8, h / 3.2)
            cx = max(R * 1.66, w * 0.44)
        cy = h / 2 - 0.04 * R
        C = [(cx - R * 0.62, cy - R * 0.5), (cx + R * 0.62, cy - R * 0.5), (cx, cy + R * 0.58)]
        L = [(C[0][0] - R * 0.86, C[0][1] - R * 0.62, R * 1.1, R * 0.6), (C[1][0] - R * 0.24, C[1][1] - R * 0.62, R * 1.1, R * 0.6),
             (C[2][0] - R * 0.6, C[2][1] + R * 0.2, R * 1.2, R * 0.56)]
        mc = (cx, cy - R * 0.1)
    else:
        R = min(w / 3.5, h / 2.25)
        cy = h / 2 - (0.12 * R if note else 0)
        C = [(cx - R * 0.6, cy), (cx + R * 0.6, cy)]
        L = [(C[0][0] - R * 0.9, cy - R * 0.4, R * 0.95, R * 0.8), (C[1][0] - R * 0.05, cy - R * 0.4, R * 0.95, R * 0.8)]
        mc = (cx, cy)
    for (x, y), c in zip(C, ("wa", "wb", "wc")):
        P.wash_ellipse(x, y, R, R, c)
    for (x, y) in C:
        P.circle(x, y, R)
    for s, (x, y, bw, bh) in zip(sets, L):
        P.text(x, y, bw, bh, _label(s), cls="hand ink", size=46 * u)
    if mid:
        mrx, mry = R * 0.47, R * 0.24
        P.ring(mc[0], mc[1], mrx, mry)
        P.text(mc[0] - mrx * 0.86, mc[1] - mry * 0.8, mrx * 1.72, mry * 1.6, mid, cls="hand pen", size=36 * u)
        if note:
            if len(sets) == 3:
                nx, ny = cx + R + 22 * u, cy + R * 0.86
                nw, nh = w - nx - 2 * u, R * 0.9
                P.arrow([(nx + nw * 0.3, ny - 10 * u), (cx + R * 0.9, cy + R * 0.34), (mc[0] + mrx * 1.02, mc[1] + mry * 0.4)], cls="dt")
                P.text(nx, ny, nw, nh, note, cls="hand pen", size=36 * u, align="left", valign="top")
            else:
                ny = cy + R + 26 * u
                P.arrow([(mc[0], mc[1] + mry + 6 * u), (cx + 14 * u, cy + R * 0.7), (cx, ny - 4 * u)], cls="dt")
                P.text(cx - R * 1.3, ny, R * 2.6, h - ny, note, cls="hand pen", size=38 * u, valign="top")


# 3 ---------------------------------------------------------------- compare
def compare(P, d):
    u, w, h = P.u, P.w, P.h
    gap = 76 * u
    cw = (w - gap) / 2
    sides = [d["left"], d["right"]]
    tw = cw - 76 * u
    fs = 40 * u

    def rows(sd):                             # how many written lines each point needs
        return [max(1, math.ceil(len(str(p)) * fs * 0.5 / (tw - 56 * u))) for p in sd.get("points", [])[:5]] or [1]

    need = max(sum(r * fs * 1.3 + 34 * u for r in rows(sd)) for sd in sides)
    ph = min(h - 44 * u, 200 * u + max(need, 150 * u))
    if 200 * u + need > ph:                   # tight space: smaller writing (never under the smallest size)
        fs = max(P.small, fs * (ph - 200 * u) / need)
    y0 = (h - ph) / 2
    for k, sd in enumerate(sides):
        x0 = k * (cw + gap)
        good = sd.get("good", k == 1)
        P.paper(x0 + 4 * u, y0, cw - 12 * u, ph, kind="card" if good else "scrap", tilt=(-1.2, 1.1)[k], tape=1, tape2=bool(good))
        tx = x0 + 34 * u
        P.text(tx, y0 + 34 * u, tw, 96 * u, sd.get("title", ""), cls="serif", size=44 * u, align="left")
        P.underline(tx, y0 + 138 * u, min(tw * 0.7, 300 * u), cls="dt" if good else "dp")
        pts = sd.get("points", [])[:5]
        rs = rows(sd)
        unit = (ph - 196 * u) / sum(r + 0.7 for r in rs)
        yy = y0 + 166 * u
        for p, r in zip(pts, rs):
            rh = unit * (r + 0.7)
            ms = 36 * u
            if good is True:
                P.tick(tx, yy + rh / 2 - ms * 0.55, ms)
            elif good is False:
                P.cross(tx + 2 * u, yy + rh / 2 - ms * 0.42, ms * 0.8, cls="dp")
            else:
                P.dot(tx + ms / 2, yy + rh / 2, 6 * u)
            P.text(tx + 56 * u, yy, tw - 56 * u, rh, p, cls="body", size=fs, align="left")
            yy += rh
        P.pop()
    vs = d.get("vs", "vs")
    if vs:
        P.dot(w / 2, h / 2, 40 * u, cls="lift")
        P.raw('<circle cx="%.1f" cy="%.1f" r="%.1f" class="pp scrap"/>' % (w / 2, h / 2, 38 * u))
        P.text(w / 2 - 38 * u, h / 2 - 38 * u, 76 * u, 76 * u, vs, cls="hand pen", size=38 * u)


# 4 ---------------------------------------------------------------- fix (first try, crossed out -> better)
def fix(P, d):
    u, w, h = P.u, P.w, P.h
    side = w / h > 1.5
    if side:
        aw = 110 * u
        bw = (w - aw) / 2 - 10 * u
        A = (6 * u, h * 0.14, bw, h * 0.72)
        B = (w - bw - 12 * u, h * 0.1, bw, h * 0.8)
        P.arrow([(A[0] + bw + 18 * u, h / 2 - 6 * u), (w / 2, h / 2 - 22 * u), (B[0] - 20 * u, h / 2 - 4 * u)], cls="dt", head=20 * u)
    else:
        ah = 104 * u
        A = (w * 0.04, 12 * u, w * 0.8, (h - ah) * 0.36)
        B = (w * 0.1, A[1] + A[3] + ah, w * 0.86, h - (A[1] + A[3] + ah) - 22 * u)
        P.arrow([(w * 0.34, A[1] + A[3] + 16 * u), (w * 0.3, A[1] + A[3] + ah * 0.55), (w * 0.38, B[1] - 20 * u)], cls="dt", head=20 * u)
        if d.get("note"):
            P.text(w * 0.42, A[1] + A[3] + 8 * u, w * 0.54, ah - 14 * u, d["note"], cls="hand pen", size=36 * u, align="left")
    x, y, bw, bh = A
    P.paper(x, y, bw, bh, kind="scrap", tilt=-1.6, tape=2)
    P.text(x + 30 * u, y + 20 * u, bw - 60 * u, 50 * u, d.get("before_label", "first try"), cls="hand", size=34 * u, align="left")
    P.text(x + 30 * u, y + 70 * u, bw - 60 * u, bh - 92 * u, "~~" + d["before"] + "~~", cls="hand ink", size=46 * u, align="left")
    P.pop()
    x, y, bw, bh = B
    P.paper(x, y, bw, bh, kind="card", tilt=1.0, tape=1, tape2=True)
    P.text(x + 34 * u, y + 24 * u, bw - 68 * u, 50 * u, d.get("after_label", "better"), cls="hand pen", size=34 * u, align="left")
    P.text(x + 34 * u, y + 76 * u, bw - 68 * u, bh - 100 * u, d["after"], cls="serif", size=52 * u, align="left")
    P.pop()
    if side and d.get("note"):
        P.text(w / 2 - 150 * u, h * 0.9, 300 * u, h * 0.1, d["note"], cls="hand pen", size=34 * u)


# 5 ---------------------------------------------------------------- matrix (2 x 2)
def matrix(P, d):
    u, w, h = P.u, P.w, P.h
    x0, y0 = 84 * u, 14 * u
    gw, gh = w - x0 - 24 * u, h - y0 - 96 * u
    xm, ym = x0 + gw / 2, y0 + gh / 2
    cells = d["cells"][:4]
    quads = [(x0, y0), (xm, y0), (x0, ym), (xm, ym)]
    pk = d.get("pick")
    if pk is not None:
        qx, qy = quads[int(pk)]
        P.wash_rect(qx + 12 * u, qy + 12 * u, gw / 2 - 24 * u, gh / 2 - 24 * u, "wb")
    P.arrow([(x0, y0 + gh), (x0 + 2 * u, ym), (x0, y0 - 4 * u)], cls="d", head=18 * u, j=0.5)
    P.arrow([(x0, y0 + gh), (xm, y0 + gh + 2 * u), (x0 + gw + 8 * u, y0 + gh)], cls="d", head=18 * u, j=0.5)
    P.line(xm, y0 + 10 * u, xm, y0 + gh - 8 * u, cls="dp dash")
    P.line(x0 + 8 * u, ym, x0 + gw - 10 * u, ym, cls="dp dash")
    for i, (c, (qx, qy)) in enumerate(zip(cells, quads)):
        on = pk is not None and int(pk) == i
        P.text(qx + 26 * u, qy + 20 * u, gw / 2 - 52 * u, gh / 2 - 40 * u, _label(c), cls="hand pen" if on else "hand ink", size=(46 if on else 40) * u)
        if on:
            P.spark(qx + gw / 2 - 48 * u, qy + 44 * u, 30)
    P.text(x0, y0 + gh + 16 * u, gw, 70 * u, d.get("x", ""), cls="hand", size=38 * u)
    P.text(-gh / 2 + 36 * u, ym - 36 * u, gh, 72 * u, d.get("y", ""), cls="hand", size=38 * u, rot=-90)


# 6 ---------------------------------------------------------------- spectrum (a scale between two ends)
def spectrum(P, d):
    u, w, h = P.u, P.w, P.h
    marks = d.get("marks", [])
    near, far = 96 * u, min(h * 0.3, 250 * u)
    cy = h / 2 + min(far * 0.45, h * 0.12)
    x0, x1 = 40 * u, w - 40 * u
    P.wash_rect(x0, cy - 13 * u, x1 - x0, 26 * u, "wa")
    P.line(x0, cy, x1, cy, j=0.7)
    for x in (x0, x1):
        P.line(x, cy - 26 * u, x, cy + 26 * u, j=0.4, bow=0)
    lw = min(330 * u, (x1 - x0) / max(len(marks), 1) * 1.9)
    for i, m in enumerate(marks):
        x = x0 + (x1 - x0) * float(m.get("at", 0.5))
        on = _pick(d, i)
        reach = far if i % 2 else near          # labels sit above the line, at two heights, so they never collide
        P.line(x, cy - 16 * u, x, cy - reach + 10 * u, cls="dt" if on else "dp", j=0.5)
        P.dot(x, cy, (12 if on else 9) * u, cls="dott" if on else "dotf")
        bx = min(max(x - lw / 2, 0), w - lw)
        P.text(bx, cy - reach - 110 * u, lw, 110 * u, _label(m), cls="hand pen" if on else "hand ink", size=(44 if on else 40) * u, valign="bottom")
        if on:
            P.ring(x, cy, 30 * u, 26 * u)
    ey = cy + 40 * u
    P.text(x0 - 30 * u, ey, w * 0.44, 120 * u, d.get("left", ""), cls="serif", size=42 * u, align="left", valign="top")
    P.text(w - w * 0.44 - 10 * u, ey, w * 0.44, 120 * u, d.get("right", ""), cls="serif", size=42 * u, align="right", valign="top")


# 7 ---------------------------------------------------------------- equation (A + B = C)
def equation(P, d):
    u, w, h = P.u, P.w, P.h
    parts = d["parts"][:4]
    n = len(parts)
    op = d.get("op", "+")
    opw = 70 * u
    one_row = w / h > 1.7 and n <= 3
    ic = _icons(d, parts)
    if one_row:
        bw = min(320 * u, (w - (n) * opw - 20 * u) / (n + 1))
        bh = min(h * 0.5, 190 * u)
        tot = (n + 1) * bw + n * opw
        x, y = (w - tot) / 2, h / 2 - bh / 2
        for i, p in enumerate(parts):
            P.box(x, y, bw, bh, wash="wa")
            P.text(x + 12 * u, y + 8 * u, bw - 24 * u, bh - 16 * u, _label(p), cls="hand ink", size=42 * u, icon=ic[i], icon_pos="top")
            x += bw
            P.text(x, y, opw, bh, "=" if i == n - 1 else op, cls="serif", size=70 * u)
            x += opw
        rx, ry, rw, rh = x, y - 14 * u, bw, bh + 28 * u
    else:
        bw = min(380 * u, (w - (n - 1) * opw - 20 * u) / n)
        bh = min(h * 0.3, 230 * u)
        tot = n * bw + (n - 1) * opw
        gap = min(110 * u, h * 0.12)
        rh = min(h * 0.36, 280 * u)
        y = (h - (bh + gap + rh)) / 2
        x = (w - tot) / 2
        for i, p in enumerate(parts):
            P.box(x, y, bw, bh, wash="wa")
            P.text(x + 12 * u, y + 8 * u, bw - 24 * u, bh - 16 * u, _label(p), cls="hand ink", size=42 * u, icon=ic[i], icon_pos="top")
            x += bw
            if i < n - 1:
                P.text(x, y, opw, bh, op, cls="serif", size=70 * u)
                x += opw
        rw = min(w * 0.76, 700 * u)
        rx, ry = (w - rw) / 2 + 40 * u, y + bh + gap
        P.text(rx - 130 * u, ry, 110 * u, rh, "=", cls="serif", size=96 * u)
    P.wash_rect(rx + 10 * u, ry + 12 * u, rw - 20 * u, rh - 24 * u, "wb")
    P.ring(rx + rw / 2, ry + rh / 2, rw / 2 + 4 * u, rh / 2 + 2 * u)
    P.text(rx + rw * 0.1, ry + rh * 0.14, rw * 0.8, rh * 0.72, d["result"], cls="serif", size=54 * u)


# 8 ---------------------------------------------------------------- steps
def steps(P, d):
    u, w, h = P.u, P.w, P.h
    st = d["steps"][:5]
    n = len(st)
    pk = d.get("pick")
    ic = _icons(d, st)
    if w / h > 1.5:
        gap = 64 * u
        bw = (w - (n - 1) * gap - 12 * u) / n
        bh = min(h - 110 * u, 330 * u)
        y = (h - bh) / 2 + 30 * u
        for i, s in enumerate(st):
            x = 6 * u + i * (bw + gap)
            on = pk is not None and int(pk) == i
            P.box(x, y, bw, bh, wash="wb" if on else None)
            P.dot(x + 10 * u, y - 4 * u, 34 * u, cls="lift")
            P.raw('<circle cx="%.1f" cy="%.1f" r="%.1f" style="fill:var(--paper)"/>' % (x + 6 * u, y - 8 * u, 33 * u))
            P.num(x + 6 * u, y - 8 * u, i + 1, r=32 * u)
            has = isinstance(s, dict) and s.get("text")
            P.text(x + 16 * u, y + 30 * u, bw - 32 * u, bh * (0.42 if has else 1) - 40 * u, _label(s), cls="serif", size=40 * u, icon=ic[i])
            if has:
                P.text(x + 16 * u, y + bh * 0.44, bw - 32 * u, bh * 0.52, s["text"], cls="body muted", size=30 * u, valign="top")
            if i < n - 1:
                P.arrow([(x + bw + 10 * u, y + bh / 2), (x + bw + gap / 2, y + bh / 2 - 8 * u), (x + bw + gap - 10 * u, y + bh / 2)])
    else:
        gap = 44 * u
        rh = min((h - (n - 1) * gap - 10 * u) / n, 270 * u)
        tot = n * rh + (n - 1) * gap
        y0 = (h - tot) / 2
        nx = 44 * u
        bx = 104 * u
        for i, s in enumerate(st):
            y = y0 + i * (rh + gap)
            on = pk is not None and int(pk) == i
            P.box(bx, y, w - bx - 14 * u, rh, wash="wb" if on else None)
            P.num(nx, y + rh / 2, i + 1, r=34 * u)
            has = isinstance(s, dict) and s.get("text")
            isz = min(rh * 0.5, 92 * u) if any(ic) else 0
            tw = w - bx - 70 * u - (isz + 26 * u if isz else 0)
            if ic[i]:
                P.icon(ic[i], w - 14 * u - 34 * u - isz / 2, y + rh / 2, isz)
            if has:
                P.text(bx + 28 * u, y + 12 * u, tw, rh * 0.44, _label(s), cls="serif", size=48 * u, align="left", valign="bottom")
                P.text(bx + 28 * u, y + rh * 0.52, tw, rh * 0.44, s["text"], cls="body muted", size=38 * u, align="left", valign="top")
            else:
                P.text(bx + 28 * u, y + 8 * u, tw, rh - 16 * u, _label(s), cls="serif", size=42 * u, align="left")
            if i < n - 1:
                P.arrow([(nx, y + rh / 2 + 44 * u), (nx - 8 * u, y + rh + gap / 2), (nx, y + rh + gap + rh / 2 - 44 * u)])


# 9 ---------------------------------------------------------------- loop
def loop(P, d):
    u, w, h = P.u, P.w, P.h
    nodes = d["nodes"][:6]
    n = len(nodes)
    ic = _icons(d, nodes)
    cx, cy = w / 2, h / 2
    bw, bh = min(w * 0.32, 320 * u), 116 * u
    RX, RY = w / 2 - bw / 2 - 10 * u, min(h / 2 - bh / 2 - 14 * u, w * 0.5)
    a0 = -math.pi / 2
    pos = [(cx + math.cos(a0 + i * 2 * math.pi / n) * RX, cy + math.sin(a0 + i * 2 * math.pi / n) * RY) for i in range(n)]
    for i in range(n):
        a, b = pos[i], pos[(i + 1) % n]
        am = a0 + (i + 0.5) * 2 * math.pi / n
        mid = (cx + math.cos(am) * RX * 0.93, cy + math.sin(am) * RY * 0.93)
        p1 = rect_edge(a[0], a[1], bw, bh, mid[0], mid[1], pad=12 * u)
        p2 = rect_edge(b[0], b[1], bw, bh, mid[0], mid[1], pad=14 * u)
        P.arrow([p1, mid, p2], cls="dt" if _pick(d, i) else "dp", head=17 * u)
    for i, (x, y) in enumerate(pos):
        P.box(x - bw / 2, y - bh / 2, bw, bh, wash="wb" if i == 0 and d.get("pick") is None else None)
        P.text(x - bw / 2 + 8 * u, y - bh / 2 + 4 * u, bw - 16 * u, bh - 8 * u, _label(nodes[i]), cls="hand ink", icon=ic[i])
    if d.get("center"):
        cic = _icons(d, [d["center"]])[0]            # the middle names an app ("Notion")? it gets its logo too
        cw, ch = RX * 0.9, RY * (0.9 if cic else 0.7)
        P.text(cx - cw / 2, cy - ch / 2, cw, ch, d["center"], cls="hand pen", size=42 * u, icon=cic, icon_pos="top", icon_size=58 * u if cic else None)


# 10 --------------------------------------------------------------- pipeline (many steps, a check after each)
def pipeline(P, d):
    u, w, h = P.u, P.w, P.h
    st = d["steps"][:12]
    n = len(st)
    ic = _icons(d, st)
    k = 4 if w / h > 1.45 else (2 if n == 4 else 3)   # 4 steps: one row when there is width, else 2 by 2 (never 3 + 1)
    k = min(k, n)
    rows = math.ceil(n / k)
    gx = (58 if k < 4 else 44) * u * (1.6 if k == 2 else 1)
    bw = (w - (k - 1) * gx - 24 * u) / k
    if k == 2:
        bw = min(bw, 400 * u)
    bh = (170 if k == 2 else 118) * u
    x0 = (w - k * bw - (k - 1) * gx) / 2
    note_h = 80 * u
    stack = any(ic) and bw < 215 * u and (h - rows * 156 * u - note_h - 40 * u) / max(rows - 1, 1) > 50 * u   # narrow boxes: icon above the word
    if stack:
        bh = 156 * u
    gy = min(150 * u, (h - rows * bh - note_h - 40 * u) / max(rows - 1, 1))
    tot = rows * bh + (rows - 1) * gy + note_h
    y0 = (h - tot) / 2 + 20 * u
    cells = []
    for i in range(n):
        r, c = divmod(i, k)
        col = c if r % 2 == 0 else k - 1 - c
        cells.append((x0 + col * (bw + gx), y0 + r * (bh + gy)))
    for i, (x, y) in enumerate(cells):
        P.box(x, y, bw, bh)
        P.text(x + 6 * u, y + 4 * u, bw - 12 * u, bh - 8 * u, _label(st[i]), cls="hand ink", size=P.fs * 1.25 if k == 2 else (36 * u if any(ic) else None), icon=ic[i],
               icon_pos="top" if stack else "left")
        if d.get("checks", True):
            P.tick(x + bw - 26 * u, y - 20 * u, 30 * u)
        if i < n - 1:
            nx, ny = cells[i + 1]
            if abs(ny - y) < 1:
                if nx > x:
                    P.arrow([(x + bw + 9 * u, y + bh / 2), (x + bw + gx / 2, y + bh / 2 - 5 * u), (nx - 9 * u, y + bh / 2)])
                else:
                    P.arrow([(x - 9 * u, y + bh / 2), (x - gx / 2, y + bh / 2 + 5 * u), (nx + bw + 9 * u, y + bh / 2)])
            else:
                P.arrow([(x + bw / 2, y + bh + 9 * u), (x + bw / 2 + 5 * u, y + bh + gy / 2), (x + bw / 2, ny - 12 * u)])
    ny = y0 + rows * bh + (rows - 1) * gy + 18 * u
    P.text(x0 - 4 * u, ny, w * 0.5 - x0, note_h, d.get("note", "then learn, and go again"), cls="hand", size=34 * u, align="left")
    if d.get("checks", True):
        P.text(w * 0.5, ny, w * 0.5 - x0, note_h, d.get("check_note", "tick = a quality check"), cls="hand pen", size=34 * u, align="right")


# 11 --------------------------------------------------------------- timeline
def timeline(P, d):
    u, w, h = P.u, P.w, P.h
    ev = d["events"][:6]
    n = len(ev)
    if w / h > 1.3:
        x0, x1, cy = 30 * u, w - 40 * u, h / 2
        P.arrow([(x0, cy), (w / 2, cy + 3 * u), (x1, cy)], cls="d", head=18 * u, j=0.6)
        seg = (x1 - x0 - 60 * u) / n
        for i, e in enumerate(ev):
            x = x0 + seg * (i + 0.5)
            up = i % 2 == 0
            on = _pick(d, i)
            P.dot(x, cy, (13 if on else 10) * u, cls="dott" if on else "dotf")
            if on:
                P.ring(x, cy, 32 * u, 28 * u)
            bw = seg * 1.5
            bx = min(max(x - bw / 2, 0), w - bw)
            reach = h / 2 - 20 * u
            if up:
                P.line(x, cy - 16 * u, x, cy - 56 * u, cls="dp", j=0.4)
                P.text(bx, cy - reach, bw, reach - 124 * u, e["what"], cls="hand ink", size=36 * u, valign="bottom")
                P.text(bx, cy - 122 * u, bw, 62 * u, e["when"], cls="serif" + (" pen" if on else ""), size=40 * u)
            else:
                P.line(x, cy + 16 * u, x, cy + 56 * u, cls="dp", j=0.4)
                P.text(bx, cy + 60 * u, bw, 62 * u, e["when"], cls="serif" + (" pen" if on else ""), size=40 * u)
                P.text(bx, cy + 124 * u, bw, reach - 124 * u, e["what"], cls="hand ink", size=36 * u, valign="top")
    else:
        lx = 60 * u
        P.arrow([(lx, 14 * u), (lx + 3 * u, h / 2), (lx, h - 14 * u)], cls="d", head=18 * u, j=0.6)
        seg = (h - 60 * u) / n
        for i, e in enumerate(ev):
            y = 20 * u + seg * (i + 0.5)
            on = _pick(d, i)
            P.dot(lx, y, (13 if on else 10) * u, cls="dott" if on else "dotf")
            if on:
                P.ring(lx, y, 32 * u, 28 * u)
            P.line(lx + 18 * u, y, lx + 58 * u, y, cls="dp", j=0.4)
            P.text(lx + 74 * u, y - seg * 0.46, w - lx - 90 * u, seg * 0.44, e["when"], cls="serif" + (" pen" if on else ""), size=42 * u, align="left", valign="bottom")
            P.text(lx + 74 * u, y + 2 * u, w - lx - 90 * u, seg * 0.46, e["what"], cls="hand ink", size=38 * u, align="left", valign="top")


# 12 --------------------------------------------------------------- tree (a question, then which way to go)
def tree(P, d):
    u, w, h = P.u, P.w, P.h
    br = d["branches"][:3]
    n = len(br)
    qw, qh = min(w * 0.66, 620 * u), min(h * 0.24, 170 * u)
    qx, qy = (w - qw) / 2, 10 * u
    gap = 40 * u
    bw = (w - (n - 1) * gap - 16 * u) / n
    bh = min(h * 0.34, 240 * u)
    by = h - bh - 16 * u
    mids = [((qx + qw * (j + 1) / (n + 1)) + (8 * u + j * (bw + gap) + bw / 2)) / 2 for j in range(n)]
    for i, b in enumerate(br):
        bx = 8 * u + i * (bw + gap)
        cxb = bx + bw / 2
        sx = qx + qw * (i + 1) / (n + 1)
        good = b.get("good")
        P.arrow([(sx, qy + qh + 10 * u), ((sx + cxb) / 2 + 6 * u, (qy + qh + by) / 2), (cxb, by - 14 * u)], cls="dt" if good else "dp", head=17 * u)
        mx, my = (sx + cxb) / 2, (qy + qh + by) / 2
        lw = 200 * u
        right = cxb >= w / 2
        # a slanted arrow leans into its label lower down: push the label out by the lean
        lean = (cxb - sx) / max(1.0, by - qy - qh) * (1 if right else -1)
        off = 16 * u + max(0.0, lean) * 44 * u
        # keep each label inside the gap to the next arrow, so labels never run into each other (wide pictures)
        if right and i + 1 < n:
            lw = min(lw, mids[i + 1] - mx - off - 24 * u)
        elif not right and i > 0:
            lw = min(lw, mx - mids[i - 1] - off - 24 * u)
        lx = mx + (off if right else -lw - off)
        P.text(lx, my - 44 * u, lw, 88 * u, b.get("when", ""), cls="hand pen", size=48 * u, align="left" if right else "right")
        P.box(bx, by, bw, bh, wash="wb" if good else None)
        P.text(bx + 14 * u, by + 10 * u, bw - 28 * u, bh - 20 * u, b.get("then", ""), cls="hand ink", size=40 * u)
        if good:
            P.tick(bx + bw - 34 * u, by - 22 * u, 34 * u)
    P.box(qx, qy, qw, qh, wash="wa")
    P.text(qx + 18 * u, qy + 8 * u, qw - 36 * u, qh - 16 * u, d["question"], cls="serif", size=44 * u)


# 13 --------------------------------------------------------------- ladder (levels you climb)
def ladder(P, d):
    u, w, h = P.u, P.w, P.h
    lv = d["levels"][:6]
    n = len(lv)
    x0, yb = 10 * u, h - 20 * u
    sw = (w - 30 * u) / n
    pk = d.get("pick")
    flag = pk is None or int(pk) != n - 1
    top_room = (226 if flag else 150) * u
    sh = (h - top_room - 30 * u) / n
    pts = [(x0, yb)]
    for i in range(n):
        y = yb - (i + 1) * sh
        pts += [(x0 + i * sw, y), (x0 + (i + 1) * sw, y)]
    pts.append((x0 + n * sw, yb))
    for i in range(n):
        y = yb - (i + 1) * sh
        P.hatch(x0 + i * sw + 4 * u, y + 4 * u, sw - 4 * u, (i + 1) * sh - 6 * u, gap=34 * u)
    P.poly(pts, close=True)
    for i, l in enumerate(lv):
        y = yb - (i + 1) * sh
        on = pk is not None and int(pk) == i
        P.text(x0 + i * sw + 4 * u, y - 136 * u, sw - (22 * u if i == n - 1 and flag else 8 * u), 126 * u, _label(l), cls="hand pen" if on else "hand ink", size=36 * u, valign="bottom")
        if on:
            P.ring(x0 + (i + 0.5) * sw, y - 62 * u, sw * 0.52, 66 * u)
    fx, fy = x0 + n * sw - 6 * u, yb - n * sh
    if flag:
        P.line(fx, fy, fx, fy - 216 * u, cls="dt", j=0.3, bow=0)
        P.poly([(fx, fy - 216 * u), (fx - 56 * u, fy - 193 * u), (fx, fy - 170 * u)], cls="dt", wash="wc")


# 14 --------------------------------------------------------------- funnel (many go in, few come out)
def funnel(P, d):
    u, w, h = P.u, P.w, P.h
    stg = d["stages"][:5]
    n = len(stg)
    has_val = any(isinstance(s, dict) and s.get("value") for s in stg)
    ic = _icons(d, stg)
    fw = w * (0.72 if has_val else 0.94)
    x0 = 8 * u
    gap = 16 * u
    sh = (h - 20 * u - (n - 1) * gap) / n
    wt, wb_ = fw, fw * 0.34
    for i, s in enumerate(stg):
        y = 10 * u + i * (sh + gap)
        t0, t1 = i / n, (i + 1) / n
        a, b = wt + (wb_ - wt) * t0, wt + (wb_ - wt) * t1
        cxm = x0 + fw / 2
        on = _pick(d, i) or (d.get("pick") is None and i == n - 1)
        P.poly([(cxm - a / 2, y), (cxm + a / 2, y), (cxm + b / 2, y + sh), (cxm - b / 2, y + sh)], wash="wb" if on else ("wa" if i % 2 == 0 else None))
        P.text(cxm - b / 2 + 10 * u, y + 4 * u, b - 20 * u, sh - 8 * u, _label(s), cls="serif" if on else "hand ink", size=40 * u, icon=ic[i])
        if has_val and isinstance(s, dict) and s.get("value"):
            P.line(cxm + (a + b) / 4 + 14 * u, y + sh / 2, x0 + fw + 16 * u, y + sh / 2, cls="dp dash", j=0.3)
            P.text(x0 + fw + 26 * u, y, w - fw - 36 * u, sh, s["value"], cls="hand pen" if on else "hand", size=44 * u, align="left")


# 15 --------------------------------------------------------------- layers (what sits on what)
def layers(P, d):
    u, w, h = P.u, P.w, P.h
    ly = d["layers"][:6]
    n = len(ly)
    has_note = any(isinstance(l, dict) and l.get("note") for l in ly)
    pyramid = d.get("shape") == "pyramid"
    ic = _icons(d, ly)
    sw = w * (0.58 if has_note or pyramid else 0.9)
    x0 = 10 * u
    gap = 0 if pyramid else 18 * u
    sh = (h - 24 * u - (n - 1) * gap) / n
    if not pyramid:
        sh = min(sh, 170 * u)
    y0 = (h - (n * sh + (n - 1) * gap)) / 2
    for i, l in enumerate(ly):
        y = y0 + i * (sh + gap)
        on = _pick(d, i)
        if pyramid:
            cxm = x0 + sw / 2
            a, b = sw * i / n, sw * (i + 1) / n
            P.poly([(cxm - a / 2, y), (cxm + a / 2, y), (cxm + b / 2, y + sh), (cxm - b / 2, y + sh)], wash="wb" if on else ("wa" if i % 2 else None))
            lx = cxm + (a + b) / 4 + 20 * u
            P.line(lx, y + sh / 2, x0 + sw + 20 * u, y + sh / 2, cls="dp dash", j=0.3)
            txt = _label(l) + ((": " + l["note"]) if isinstance(l, dict) and l.get("note") else "")
            P.text(x0 + sw + 32 * u, y, w - sw - 44 * u, sh, txt, cls="hand pen" if on else "hand ink", size=38 * u, align="left")
        else:
            off = (i % 2) * 14 * u
            P.box(x0 + off, y, sw - 14 * u, sh, wash="wb" if on else ("wa" if i % 2 == 0 else None))
            P.text(x0 + off + 20 * u, y + 6 * u, sw - 54 * u, sh - 12 * u, _label(l), cls="serif", size=42 * u, icon=ic[i])
            if has_note and isinstance(l, dict) and l.get("note"):
                P.arrow([(x0 + sw + 110 * u, y + sh / 2 + 4 * u), (x0 + sw + 60 * u, y + sh / 2 - 6 * u), (x0 + sw + 14 * u, y + sh / 2)], cls="dt" if on else "dp", head=13 * u)
                P.text(x0 + sw + 120 * u, y, w - sw - 126 * u, sh, l["note"], cls="hand pen" if on else "hand", size=38 * u, align="left")


# 16 --------------------------------------------------------------- iceberg (the small part you see, the big part you don't)
def iceberg(P, d):
    u, w, h = P.u, P.w, P.h
    wl = h * 0.3
    cx = w * 0.4
    P.wash_rect(0, wl, w, h - wl - 6 * u, "wa")
    tip = [(cx - w * 0.11, wl), (cx - w * 0.06, wl - h * 0.09), (cx + w * 0.0, wl - h * 0.17), (cx + w * 0.07, wl - h * 0.08), (cx + w * 0.12, wl)]
    P.poly(tip, close=False)
    mass = [(cx - w * 0.11, wl), (cx - w * 0.3, wl + h * 0.2), (cx - w * 0.34, wl + h * 0.44), (cx - w * 0.14, wl + h * 0.64), (cx + w * 0.1, wl + h * 0.66),
            (cx + w * 0.31, wl + h * 0.42), (cx + w * 0.27, wl + h * 0.16), (cx + w * 0.12, wl)]
    d_ = "M%.1f %.1f" % mass[0] + "".join("L%.1f %.1f" % p for p in mass[1:]) + "Z"
    P.raw('<path d="%s" style="fill:var(--scrap);stroke:none"/>' % d_)
    P.poly(mass, close=False)
    pts = [(i * w / 8, wl + (6 if i % 2 else -6) * u) for i in range(9)]
    P.curve(pts[:3], cls="dp")
    P.curve(pts[5:], cls="dp")
    above, below = d.get("above", [])[:3], d.get("below", [])[:5]
    ax = cx + w * 0.17
    P.text(ax, 0, w - ax - 6 * u, 54 * u, d.get("top_label", "what people see"), cls="hand pen", size=36 * u, align="left")
    ah = (wl - 62 * u) / max(len(above), 1)
    for i, a in enumerate(above):
        P.text(ax, 56 * u + i * ah, w - ax - 6 * u, ah, _label(a), cls="serif", size=40 * u, align="left")
    P.arrow([(ax - 10 * u, 30 * u), (cx + w * 0.1, 36 * u), (cx + w * 0.03, wl - h * 0.14)], cls="dt", head=14 * u)
    by, bh = wl + h * 0.1, h * 0.5
    bx, bw = cx - w * 0.24, w * 0.48
    rh = bh / max(len(below), 1)
    for i, b in enumerate(below):
        P.text(bx, by + i * rh, bw, rh, _label(b), cls="hand ink", size=38 * u)
    P.text(cx + w * 0.3, wl + h * 0.5, w - (cx + w * 0.3) - 4 * u, h * 0.2, d.get("bottom_label", "what it takes"), cls="hand pen", size=36 * u, align="left")
    P.arrow([(cx + w * 0.34, wl + h * 0.52), (cx + w * 0.3, wl + h * 0.46), (cx + w * 0.22, wl + h * 0.42)], cls="dt", head=14 * u)


# 17 --------------------------------------------------------------- anatomy (one thing, its parts named)
def anatomy(P, d):
    u, w, h = P.u, P.w, P.h
    parts = d["parts"][:6]
    n = len(parts)
    ic = _icons(d, parts)
    tw, th = w * 0.5, min(h * 0.94, 940 * u)
    tx, ty = 8 * u, (h - th) / 2
    P.paper(tx, ty, tw, th, kind="scrap", tilt=0, tape=1)
    head = 96 * u
    P.text(tx + 12 * u, ty + 12 * u, tw - 24 * u, head - 14 * u, _label(d["thing"]), cls="serif", size=42 * u)
    P.line(tx + 14 * u, ty + head, tx + tw - 14 * u, ty + head, cls="dp", j=0.5)
    bh = (th - head - 20 * u) / n
    rx = tx + tw + 96 * u
    for i, p in enumerate(parts):
        y = ty + head + 10 * u + i * bh
        on = _pick(d, i)
        if on:
            P.wash_rect(tx + 14 * u, y + 8 * u, tw - 28 * u, bh - 16 * u, "wb")
        k = 3 if bh > 90 * u else 2
        for j in range(k):
            yy = y + bh * (j + 1) / (k + 1)
            P.line(tx + 28 * u, yy, tx + tw - 28 * u - P.rnd(0, tw * 0.35), yy, cls="dp thin", j=0.6)
        if i < n - 1:
            P.line(tx + 14 * u, y + bh, tx + tw - 14 * u, y + bh, cls="dp dash", j=0.4)
        cy = y + bh / 2
        lh = min(bh * 0.96, 190 * u)
        P.arrow([(rx - 8 * u, cy), (rx - 44 * u, cy - 12 * u), (tx + tw + 10 * u, cy)], cls="dt" if on else "dp", head=17 * u)
        P.text(rx + 6 * u, cy - lh / 2, w - rx - 6 * u, lh, _label(p), cls="hand pen" if on else "hand ink", size=42 * u, align="left", icon=ic[i])
    P.pop()


# 18 --------------------------------------------------------------- screen (a tool or page, one part pointed out)
def screen(P, d):
    u, w, h = P.u, P.w, P.h
    note = d.get("note")
    side = bool(note) and w / h > 1.1          # wide: note beside the screen; tall: note under it
    gut = 84 * u if note and not side else 0   # left gutter for the arrow
    sw = w * 0.62 if side else w * 0.96 - gut
    sh = h * (0.92 if side or not note else 0.72)
    sx, sy = 10 * u + gut, 12 * u
    P.paper(sx, sy, sw, sh, kind="scrap", tilt=-0.8, tape=0)
    bar = 74 * u
    P.line(sx + 4 * u, sy + bar, sx + sw - 4 * u, sy + bar, j=0.5)
    for i in range(3):
        P.path(P.r.ellipse(sx + (36 + i * 34) * u, sy + bar / 2, 10 * u, 10 * u, j=0.03, turn=1.1, n=10), "dp")
    P.text(sx + 150 * u, sy + 6 * u, sw - 180 * u, bar - 10 * u, d.get("title", ""), cls="hand ink", size=36 * u, align="left")
    lines = d.get("lines") or ["", "", ""]
    rows = len(lines) + 1
    rh = (sh - bar - 30 * u) / rows
    hi = int(d.get("at", min(1, len(lines))))
    k = 0
    hy = None
    for r in range(rows):
        y = sy + bar + 16 * u + r * rh
        if r == hi:
            hy = y
            P.wash_rect(sx + 30 * u, y + rh * 0.12, sw - 60 * u, rh * 0.76, "wb")
            P.text(sx + 46 * u, y + rh * 0.1, sw - 92 * u, rh * 0.8, d.get("highlight", ""), cls="body bold", size=36 * u, align="left")
        else:
            t = lines[k] if k < len(lines) else ""
            k += 1
            if t:
                P.text(sx + 40 * u, y, sw - 80 * u, rh, t, cls="body muted", size=31 * u, align="left")
            else:
                P.line(sx + 40 * u, y + rh * 0.36, sx + sw * P.rnd(0.6, 0.9), y + rh * 0.36, cls="dp thin", j=0.6)
                P.line(sx + 40 * u, y + rh * 0.66, sx + sw * P.rnd(0.35, 0.7), y + rh * 0.66, cls="dp thin", j=0.6)
    P.pop()
    if hy is not None:
        P.ring(sx + sw / 2, hy + rh / 2, sw / 2 - 16 * u, rh * 0.52)
        if note:
            if side:
                nx = sx + sw + 34 * u
                ay = hy + rh / 2
                if ay - 84 * u > h - ay - 84 * u:      # more room above
                    P.arrow([(nx + 60 * u, ay - 74 * u), (nx + 26 * u, ay - 30 * u), (sx + sw - 4 * u, ay)], cls="dt", head=16 * u)
                    P.text(nx, 0, w - nx, ay - 84 * u, note, cls="hand pen", size=40 * u, align="left", valign="bottom")
                else:
                    P.arrow([(nx + 60 * u, ay + 74 * u), (nx + 26 * u, ay + 30 * u), (sx + sw - 4 * u, ay)], cls="dt", head=16 * u)
                    P.text(nx, ay + 84 * u, w - nx, h - ay - 88 * u, note, cls="hand pen", size=40 * u, align="left", valign="top")
            else:
                ny = sy + sh + 30 * u
                ay = hy + rh / 2
                P.arrow([(gut + 20 * u, ny + 44 * u), (26 * u, ny - 20 * u), (22 * u, (ny + ay) / 2), (30 * u, ay + 30 * u), (sx - 4 * u, ay)], cls="dt", head=17 * u)
                P.text(gut + 40 * u, ny, w - gut - 44 * u, h - ny - 4 * u, note, cls="hand pen", size=42 * u, align="left", valign="top")


# 19 --------------------------------------------------------------- stickies (a set of equal things)
def stickies(P, d):
    u, w, h = P.u, P.w, P.h
    items = d["items"][:9]
    n = len(items)
    cols = max(1, min(n, round(math.sqrt(n * w / h))))
    rows = math.ceil(n / cols)
    while (rows - 1) * cols >= n and rows > 1:
        rows -= 1
    cw, ch = w / cols, h / rows
    kinds = ["sticky", "card", "scrap", "sagep"]
    ic = _icons(d, items)
    for i, it in enumerate(items):
        r, c = divmod(i, cols)
        in_row = min(cols, n - r * cols)
        xoff = (cols - in_row) * cw / 2
        nw, nh = min(cw * 0.86, ch * 1.5), min(ch * 0.8, cw * 0.86)
        x, y = xoff + c * cw + (cw - nw) / 2, r * ch + (ch - nh) / 2 + 8 * u
        kind = kinds[(i + r) % 4] if not _pick(d, i) else "sticky"
        if d.get("pick") is not None and not _pick(d, i) and kind == "sticky":
            kind = "card"
        P.paper(x, y, nw, nh, kind=kind, tilt=P.rnd(-3.2, 3.2), tape=0 if kind == "sticky" else 1)
        sub = isinstance(it, dict) and it.get("text")
        cls = "hand onhl" if kind == "sticky" else "hand ink"
        if sub:
            P.text(x + 16 * u, y + 24 * u, nw - 32 * u, nh * 0.46, _label(it), cls=cls, size=44 * u, valign="bottom", icon=ic[i])
            P.text(x + 18 * u, y + nh * 0.52 + 14 * u, nw - 36 * u, nh * 0.4, it["text"], cls="body onhl" if kind == "sticky" else "body muted", size=30 * u, valign="top")
        else:
            P.text(x + 16 * u, y + 22 * u, nw - 32 * u, nh - 36 * u, _label(it), cls=cls, size=46 * u, icon=ic[i], icon_pos="top")
        P.pop()


# 20 --------------------------------------------------------------- bars (real numbers side by side)
def bars(P, d):
    u, w, h = P.u, P.w, P.h
    bs = d["bars"][:6]
    n = len(bs)
    unit = d.get("unit", "")
    x0, y0 = 30 * u, 70 * u
    pw, ph = w - x0 - 20 * u, h - y0 - 130 * u
    vmax = max(float(b["value"]) for b in bs) or 1
    slot = pw / n
    bw = slot * 0.56
    P.line(x0, y0 - 40 * u, x0, y0 + ph, j=0.5)
    P.line(x0, y0 + ph, x0 + pw, y0 + ph, j=0.5)
    for i, b in enumerate(bs):
        on = _pick(d, i)
        bh = max(ph * float(b["value"]) / vmax, 8 * u)
        x, y = x0 + i * slot + (slot - bw) / 2, y0 + ph - bh
        if on:
            P.wash_rect(x, y, bw, bh, "wc")
        else:
            P.hatch(x, y, bw, bh, gap=17 * u)
        P.path(P.r.line(x, y0 + ph, x, y, j=P.J(0.6)) + P.r.line(x, y, x + bw, y, j=P.J(0.6), over=3 * u) + P.r.line(x + bw, y, x + bw, y0 + ph, j=P.J(0.6)), "dt" if on else "d")
        val = b.get("show", ("%g" % float(b["value"])) + unit)
        P.text(x - slot * 0.2, y - 74 * u, bw + slot * 0.4, 66 * u, val, cls="serif" + (" pen" if on else ""), size=(48 if on else 40) * u, valign="bottom")
        P.text(x0 + i * slot + 4 * u, y0 + ph + 14 * u, slot - 8 * u, 110 * u, b["label"], cls="hand pen" if on else "hand ink", size=36 * u, valign="top")


# 21 --------------------------------------------------------------- curve (how something changes)
SHAPES = {
    "up": [(0, .1), (.5, .42), (1, .9)], "down": [(0, .9), (.5, .5), (1, .12)], "flat": [(0, .3), (.5, .33), (1, .31)],
    "hype": [(0, .05), (.1, .5), (.2, .93), (.32, .5), (.42, .2), (.62, .36), (.82, .52), (1, .6)],
    "hockey": [(0, .1), (.4, .13), (.66, .22), (.84, .5), (1, .95)],
    "dip": [(0, .62), (.2, .4), (.38, .18), (.56, .3), (.78, .62), (1, .92)],
    "s": [(0, .08), (.28, .14), (.5, .5), (.72, .86), (1, .92)],
    "plateau": [(0, .08), (.25, .5), (.5, .74), (.75, .8), (1, .81)],
}


def _dense(pts, k=14):
    """Extra points along a drawn curve (same smoothing as the pen), so labels can be kept off it."""
    out, n = [], len(pts)
    for i in range(n - 1):
        p0 = pts[i - 1] if i > 0 else pts[i]
        p1, p2 = pts[i], pts[i + 1]
        p3 = pts[i + 2] if i + 2 < n else pts[i + 1]
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
        for t in range(k):
            t /= k
            a, b, c, e = (1 - t) ** 3, 3 * t * (1 - t) ** 2, 3 * t * t * (1 - t), t ** 3
            out.append((a * p1[0] + b * c1[0] + c * c2[0] + e * p2[0], a * p1[1] + b * c1[1] + c * c2[1] + e * p2[1]))
    return out + [pts[-1]]


def _free(cands, ink, taken, box, pad):
    """Pick the first spot (x, y, w, h) that covers no drawn line, no other label and stays in the box."""
    best, low = cands[0], 1e9
    for n, (x, y, bw, bh) in enumerate(cands):
        s = n * 0.01
        if x < box[0] or y < box[1] or x + bw > box[2] or y + bh > box[3]:
            s += 60
        s += sum(1 for (a, b) in ink if x - pad < a < x + bw + pad and y - pad < b < y + bh + pad)
        s += sum(40 for (tx, ty, tw, th) in taken if x < tx + tw + pad and tx < x + bw + pad and y < ty + th + pad and ty < y + bh + pad)
        if s < low:
            best, low = (x, y, bw, bh), s
    return best


def curve(P, d):
    u, w, h = P.u, P.w, P.h
    x0, y0 = 84 * u, 24 * u
    pw, ph = w - x0 - 50 * u, h - y0 - 100 * u
    P.arrow([(x0, y0 + ph), (x0 + 2 * u, y0 + ph / 2), (x0, y0 - 6 * u)], cls="d", head=18 * u, j=0.5)
    P.arrow([(x0, y0 + ph), (x0 + pw / 2, y0 + ph + 2 * u), (x0 + pw + 30 * u, y0 + ph)], cls="d", head=18 * u, j=0.5)
    P.text(x0, y0 + ph + 16 * u, pw, 70 * u, d.get("x", ""), cls="hand", size=38 * u)
    P.text(-ph / 2 + 36 * u, y0 + ph / 2 - 36 * u, ph, 72 * u, d.get("y", ""), cls="hand", size=38 * u, rot=-90)
    px = lambda p: (x0 + 14 * u + p[0] * (pw - 40 * u), y0 + ph - 14 * u - p[1] * (ph - 40 * u))
    lines = d.get("lines", [])[:3]
    fs = (40 if h > 560 * u else 36) * u
    box = (x0 + 12 * u, y0 - 10 * u, w, y0 + ph - 10 * u)

    def size(t, maxw):                       # rough size of a hand-written label
        one = len(t) * fs * 0.56 + 16 * u
        rows = max(1, math.ceil(one / maxw))
        return min(one, maxw) if rows == 1 else maxw, rows * fs * 1.3 + 8 * u

    drawn, ink, last = [], [], None
    for i, ln in enumerate(lines):
        pts = [px(p) for p in (ln.get("points") or SHAPES[ln.get("shape", "up")])]
        main = ln.get("main", i == len(lines) - 1)
        P.curve(pts, cls="dt" if main else "dp dash", j=0.6)
        drawn.append((ln, pts, main))
        ink += _dense(pts)
        if main:
            last = pts[-1]
    pencil = last and d.get("pencil", True)
    if pencil:                                # the pencil lies up and to the left of the line's end
        ink += _dense([last, (last[0] - 111 * u, last[1] - 178 * u)], 8)
    mk = d.get("mark")
    if mk:
        mx, my = px(mk["at"])
        ink += [(mx + a * 34 * u, my + b * 30 * u) for a in (-1, 0, 1) for b in (-1, 0, 1)]
    taken = []
    maxw = min(380 * u, pw * 0.5)

    def line_label(ln, pts, main):
        t = ln.get("label", "")
        if not t:
            return
        bw, bh = size(t, maxw)
        if ln.get("label_at"):               # [x, y] in chart units (0 to 1), the label's middle
            lx, ly = px(ln["label_at"])
            spot = (lx - bw / 2, ly - bh / 2, bw, bh)
        else:
            dense = _dense(pts, 6)
            order = sorted(range(len(dense)), key=lambda k: abs(k / len(dense) - (0.8 if main else 0.5)))
            cands = []
            for g in (30 * u, 70 * u, 120 * u):
                for k in order:
                    x, y = dense[k]
                    cands += [(x - bw / 2, y - bh - g, bw, bh), (x - bw / 2, y + g, bw, bh), (x + g, y - bh / 2, bw, bh), (x - bw - g, y - bh / 2, bw, bh),
                              (x + g, y + g, bw, bh), (x - bw - g, y - bh - g, bw, bh), (x - bw - g, y + g, bw, bh), (x + g, y - bh - g, bw, bh)]
            spot = _free(cands, ink, taken, box, 20 * u)
        taken.append(spot)
        P.text(spot[0], spot[1], spot[2], spot[3], t, cls="hand pen" if main else "hand", size=fs)

    for ln, pts, main in drawn:
        if main:
            line_label(ln, pts, main)
    if mk:
        P.ring(mx, my, 34 * u, 30 * u, cls="d")
        t = mk.get("label", "")
        bw, bh = size(t, min(300 * u, pw * 0.42))
        cands = []
        for g in (60 * u, 100 * u):
            cands += [(mx + g, my - bh - g * 0.6, bw, bh), (mx - bw - g, my - bh - g * 0.6, bw, bh), (mx + g, my + g * 0.6, bw, bh), (mx - bw - g, my + g * 0.6, bw, bh),
                      (mx - bw / 2, my - bh - g * 1.2, bw, bh), (mx - bw / 2, my + g * 1.2, bw, bh), (mx + g * 1.3, my - bh / 2, bw, bh), (mx - bw - g * 1.3, my - bh / 2, bw, bh)]
        sx, sy, bw, bh = _free(cands, ink, taken, box, 16 * u)
        taken.append((sx, sy, bw, bh))
        a = rect_edge(sx + bw / 2, sy + bh / 2, bw, bh, mx, my, pad=6 * u)
        b = ell_edge(mx, my, 34 * u, 30 * u, a[0], a[1], pad=10 * u)
        if math.hypot(a[0] - b[0], a[1] - b[1]) > 24 * u:
            P.arrow2(a, b, cls="dp", bend=0.15)
        P.text(sx, sy, bw, bh, t, cls="hand ink", size=fs * 0.95)
    for ln, pts, main in drawn:
        if not main:
            line_label(ln, pts, main)
    if pencil:
        P.pencil(last[0], last[1], length=210, angle=-122)


# 22 --------------------------------------------------------------- bignumber (one number worth remembering)
def bignumber(P, d):
    u, w, h = P.u, P.w, P.h
    val = str(d["value"])
    dots = d.get("dots")
    note = d.get("note")
    fs = min(h * 0.4, w * 1.5 / max(len(val), 2), 380 * u)
    lab_h = min(h * 0.24, 200 * u)
    dot_h = 90 * u if dots else 0
    tot = fs * 1.05 + lab_h + dot_h
    y = (h - tot) / 2
    nw = min(w * 0.92, fs * 0.62 * len(val) + 80 * u)
    cx = w / 2
    P.wash_rect(cx - nw / 2, y + fs * 0.3, nw, fs * 0.56, "wb")
    P.text(cx - w * 0.48, y, w * 0.96, fs * 1.05, val, cls="serif", size=fs)
    P.underline(cx - nw * 0.42, y + fs * 1.02, nw * 0.84, cls="dt")
    if d.get("pencil", True):
        P.pencil(cx + nw * 0.42, y + fs * 1.02 - 1 * u, length=210, angle=-30)
    P.text(w * 0.06, y + fs * 1.1, w * 0.88, lab_h, d.get("label", ""), cls="body bold", size=42 * u)
    if dots:
        k, n = int(dots[0]), int(dots[1])
        r = min(24 * u, (w * 0.8) / n / 2.6)
        gx = r * 2.7
        sx = cx - (n - 1) * gx / 2
        yy = y + fs * 1.1 + lab_h + dot_h / 2
        for i in range(n):
            if i < k:
                P.dot(sx + i * gx, yy, r, cls="dott")
            P.path(P.r.ellipse(sx + i * gx, yy, r, r, j=0.03, turn=1.08, n=10), "dt" if i < k else "dp")
    if note:
        nx = cx + nw / 2 - 20 * u
        P.text(min(nx, w - 300 * u), max(y - 60 * u, 0), 300 * u, 110 * u, note, cls="hand pen", size=36 * u, rot=-4)


# 23 --------------------------------------------------------------- quote
def quote(P, d):
    u, w, h = P.u, P.w, P.h
    pw, ph = w * 0.9, min(h * 0.86, w * 0.9)
    x, y = (w - pw) / 2, (h - ph) / 2
    P.paper(x, y, pw, ph, kind="scrap", tilt=-1.1, tape=2)
    P.tape(x + pw * 0.82, y, yellow=True)
    P.text(x + 30 * u, y + 6 * u, 180 * u, 190 * u, "“", cls="serif pen", size=230 * u, align="left", valign="top")
    by = 96 * u if d.get("by") else 30 * u
    P.text(x + 60 * u, y + 150 * u, pw - 120 * u, ph - 180 * u - by, d["text"], cls="serif", size=72 * u, align="left")
    if d.get("by"):
        P.text(x + pw * 0.3, y + ph - by - 16 * u, pw * 0.64, by, "— " + d["by"], cls="hand pen", size=40 * u, align="right")
    P.pop()


# 24 --------------------------------------------------------------- checklist
def checklist(P, d):
    u, w, h = P.u, P.w, P.h
    items = d["items"][:7]
    n = len(items)
    title = d.get("title")
    pw = min(w * 0.94, 980 * u)
    head = 124 * u if title else 30 * u
    rh = min(140 * u, (h * 0.94 - head - 30 * u) / n)
    ph = head + n * rh + 34 * u
    x, y = (w - pw) / 2, (h - ph) / 2
    P.paper(x, y, pw, ph, kind="scrap", tilt=0.7, tape=1)
    if title:
        P.text(x + 44 * u, y + 30 * u, pw - 88 * u, 70 * u, title, cls="serif", size=44 * u, align="left")
        P.underline(x + 44 * u, y + 106 * u, min(pw * 0.5, 340 * u))
    for i, it in enumerate(items):
        yy = y + head + i * rh
        ok = it.get("ok", True) if isinstance(it, dict) else True
        s = 46 * u
        P.check(x + 46 * u, yy + rh / 2 - s / 2, s, ok)
        P.text(x + 116 * u, yy, pw - 150 * u, rh, _label(it), cls="body", size=42 * u, align="left")
    P.pop()


# 25 --------------------------------------------------------------- prompt (what you type, what you get)
def prompt(P, d):
    u, w, h = P.u, P.w, P.h
    side = w / h > 1.7
    if side:
        aw = (w - 110 * u) / 2
        A = (6 * u, h * 0.16, aw, h * 0.68)
        B = (w - aw - 12 * u, h * 0.1, aw, h * 0.8)
        P.arrow([(A[0] + aw + 16 * u, h / 2), (w / 2, h / 2 - 14 * u), (B[0] - 18 * u, h / 2)], cls="dt", head=18 * u)
    else:
        gap = 96 * u
        ah = (h - gap - 110 * u) * 0.4
        A = (w * 0.14, 56 * u, w * 0.84, ah)
        B = (8 * u, A[1] + ah + gap + 30 * u, w * 0.88, h - (A[1] + ah + gap + 30 * u) - 16 * u)
        P.arrow([(w * 0.5, A[1] + ah + 22 * u), (w * 0.46, A[1] + ah + gap * 0.5), (w * 0.42, B[1] - 52 * u)], cls="dt", head=18 * u)
    x, y, bw, bh = A
    P.text(x, y - 54 * u, bw, 50 * u, d.get("ask_label", "you type"), cls="hand", size=36 * u, align="right")
    P.paper(x, y, bw, bh, kind="card", tilt=0.8, tape=0)
    P.text(x + 34 * u, y + 16 * u, bw - 68 * u, bh - 32 * u, d["ask"], cls="body bold", size=44 * u, align="left")
    P.pop()
    x, y, bw, bh = B
    P.text(x + 6 * u, y - 54 * u, bw, 50 * u, d.get("answer_label", "you get"), cls="hand pen", size=36 * u, align="left")
    P.paper(x, y, bw, bh, kind="scrap", tilt=-0.7, tape=0)
    ans = d["answer"]
    if isinstance(ans, list):
        rh = (bh - 40 * u) / len(ans)
        for i, a in enumerate(ans):
            P.tick(x + 34 * u, y + 20 * u + i * rh + rh / 2 - 18 * u, 28 * u)
            P.text(x + 88 * u, y + 20 * u + i * rh, bw - 116 * u, rh, a, cls="body", size=42 * u, align="left")
    else:
        P.text(x + 34 * u, y + 16 * u, bw - 68 * u, bh - 32 * u, ans, cls="body", size=36 * u, align="left")
    P.pop()


# 26 --------------------------------------------------------------- machine (things go in, one system works, things come out)
def _cells(n, x, y, w, h, cols, gap, max_h):
    """n boxes laid out in rows inside a space, centered. Returns (x, y, w, h) for each."""
    rows = math.ceil(n / cols)
    bw = (w - (cols - 1) * gap) / cols
    bh = min(max_h, (h - (rows - 1) * gap) / rows)
    y0 = y + (h - rows * bh - (rows - 1) * gap) / 2
    out = []
    for i in range(n):
        r, c = divmod(i, cols)
        m = min(cols, n - r * cols)
        x0 = x + (w - m * bw - (m - 1) * gap) / 2
        out.append((x0 + c * (bw + gap), y0 + r * (bh + gap), bw, bh))
    return out


def machine(P, d):
    u, w, h = P.u, P.w, P.h
    ins, outs = d["in"][:4], d["out"][:4]
    ni, no = len(ins), len(outs)
    side = w / h > 1.05
    ic = _icons(d, list(ins) + list(outs))
    lab = 58 * u
    if side:                                     # in on the left, the machine in the middle, out on the right
        cw = w * 0.285
        mw, mh = w * 0.25, min(h * 0.52, 320 * u)
        A = _cells(ni, 6 * u, lab, cw, h - lab - 10 * u, 1, 24 * u, 112 * u)
        B = _cells(no, w - cw - 6 * u, lab, cw, h - lab - 10 * u, 1, 24 * u, 112 * u)
        mx, my = (w - mw) / 2, lab + (h - lab - 10 * u - mh) / 2
        P.text(6 * u, A[0][1] - lab, cw, lab - 6 * u, d.get("in_label", "goes in"), cls="hand", size=36 * u)
        P.text(w - cw - 6 * u, B[0][1] - lab, cw, lab - 6 * u, d.get("out_label", "comes out"), cls="hand", size=36 * u)
        for i, (x, y, bw, bh) in enumerate(A):
            P.arrow2((x + bw + 10 * u, y + bh / 2), (mx - 14 * u, my + mh * (i + 1) / (ni + 1)), bend=0.05)
        for i, (x, y, bw, bh) in enumerate(B):
            P.arrow2((mx + mw + 12 * u, my + mh * (i + 1) / (no + 1)), (x - 14 * u, y + bh / 2), cls="dt" if _pick(d, i) else "dp", bend=-0.05)
    else:                                        # in on top, the machine in the middle, out below
        gh = h * 0.26
        mw, mh = min(w * 0.62, 560 * u), min(h * 0.2, 220 * u)
        ca, cb = (ni if ni <= 3 else 2), (no if no <= 3 else 2)
        A = _cells(ni, 6 * u, lab, w - 12 * u, gh, ca, 22 * u, 112 * u)
        B = _cells(no, 6 * u, h - gh - 8 * u, w - 12 * u, gh, cb, 22 * u, 112 * u)
        a_bot = max(y + bh for x, y, bw, bh in A)
        b_top = min(y for x, y, bw, bh in B)
        mx, my = (w - mw) / 2, (a_bot + b_top - mh) / 2
        P.text(6 * u, A[0][1] - lab, w * 0.5, lab - 6 * u, d.get("in_label", "goes in"), cls="hand", size=36 * u, align="left")
        P.text(w * 0.5 - 6 * u, B[-1][1] + B[-1][3] + 4 * u, w * 0.5, lab - 6 * u, d.get("out_label", "comes out"), cls="hand", size=36 * u, align="right")
        near = [b for b in A if abs(b[1] + b[3] - a_bot) < 1]
        for k, (x, y, bw, bh) in enumerate(near):
            P.arrow2((x + bw / 2, y + bh + 10 * u), (mx + mw * (k + 1) / (len(near) + 1), my - 16 * u), bend=0.04)
        first = [(i, b) for i, b in enumerate(B) if abs(b[1] - b_top) < 1]
        for k, (i, (x, y, bw, bh)) in enumerate(first):
            P.arrow2((mx + mw * (k + 1) / (len(first) + 1), my + mh + 12 * u), (x + bw / 2, y - 16 * u), cls="dt" if _pick(d, i) else "dp", bend=-0.04)
    for i, ((x, y, bw, bh), it) in enumerate(zip(A, ins)):
        P.box(x, y, bw, bh)
        P.text(x + 10 * u, y + 4 * u, bw - 20 * u, bh - 8 * u, _label(it), cls="hand ink", size=38 * u, icon=ic[i])
    for i, ((x, y, bw, bh), it) in enumerate(zip(B, outs)):
        on = _pick(d, i)
        P.box(x, y, bw, bh, wash="wc" if on else None)
        P.text(x + 10 * u, y + 4 * u, bw - 20 * u, bh - 8 * u, _label(it), cls="hand pen" if on else "hand ink", size=38 * u, icon=ic[ni + i])
    # the machine: a box drawn twice, with three small lights
    P.box(mx, my, mw, mh, wash="wb")
    P.path(P.r.rect(mx + 9 * u, my + 9 * u, mw - 18 * u, mh - 18 * u, j=P.J(0.7), over=2 * u), "d thin")
    P.text(mx + 20 * u, my + 14 * u, mw - 40 * u, mh - 62 * u, _label(d.get("box", "")), cls="serif", size=42 * u)
    for k in range(3):
        P.dot(mx + mw / 2 + (k - 1) * 30 * u, my + mh - 32 * u, 7 * u, cls="dotf" if k == 0 else "dote")


# 27 --------------------------------------------------------------- table (a few options against the same questions)
def table(P, d):
    u, w, h = P.u, P.w, P.h
    cols, rows = d["cols"][:4], d["rows"][:6]
    nc, nr = len(cols), len(rows)
    pk = d.get("pick")
    ic = _icons(d, cols)
    pw = min(w * 0.97, 1000 * u)
    lw = pw * (0.42 if nc <= 2 else (0.3 if any(ic) else 0.36) if nc == 3 else 0.3)   # logos in the heads: the columns get a little more room
    cw = (pw - lw - 22 * u) / nc
    head = (196 if any(ic) else 126) * u
    rh = min(150 * u, (h * 0.95 - head - 26 * u) / nr)
    ph = head + nr * rh + 26 * u
    x, y = (w - pw) / 2, (h - ph) / 2
    P.paper(x, y, pw, ph, kind="scrap", tilt=-0.5, tape=1)
    if pk is not None:
        P.wash_rect(x + lw + int(pk) * cw + 6 * u, y + 16 * u, cw - 12 * u, ph - 32 * u, "wb")
    for j, c in enumerate(cols):
        P.text(x + lw + j * cw + 8 * u, y + 20 * u, cw - 16 * u, head - 30 * u, _label(c), cls="serif pen" if _pick(d, j) else "serif", size=36 * u, icon=ic[j], icon_pos="top")
    P.line(x + 22 * u, y + head, x + pw - 22 * u, y + head, j=0.5)
    P.line(x + lw, y + 24 * u, x + lw, y + ph - 22 * u, cls="dp", j=0.5)
    for i, r in enumerate(rows):
        yy = y + head + i * rh
        if i:
            P.line(x + 22 * u, yy, x + pw - 22 * u, yy, cls="dp dash", j=0.4)
        P.text(x + 30 * u, yy + 4 * u, lw - 44 * u, rh - 8 * u, _label(r), cls="body", size=38 * u, align="left")
        for j, v in enumerate((r.get("cells") or [])[:nc]):
            ccx, ccy = x + lw + j * cw + cw / 2, yy + rh / 2
            on = _pick(d, j)
            sz = min(46 * u, rh * 0.44)
            if v is True:
                P.tick(ccx - sz * 0.45, ccy - sz * 0.62, sz, cls="dtk" if (on or pk is None) else "d")
            elif v is False:
                P.cross(ccx - sz * 0.3, ccy - sz * 0.3, sz * 0.6, cls="dp")
            elif v is not None:
                P.text(ccx - cw / 2 + 8 * u, yy + 4 * u, cw - 16 * u, rh - 8 * u, str(v), cls="hand pen" if on else "hand ink", size=36 * u)
    P.pop()


# 28 --------------------------------------------------------------- donut (shares of one whole)
def donut(P, d):
    u, w, h = P.u, P.w, P.h
    parts = d["parts"][:5]
    vals = [max(float(p["value"]), 0.0) for p in parts]
    tot = sum(vals) or 1.0
    unit = d.get("unit", "")
    R = min(w * (0.2 if w / h > 1.1 else 0.27), h * 0.34, 300 * u)
    r = R * 0.56
    cx, cy = w / 2, h / 2

    def pt(rad, ang):
        return (cx + math.cos(ang) * rad, cy + math.sin(ang) * rad)

    def wedge(a0, a1, ox=0.0, oy=0.0):
        k = max(2, int((a1 - a0) / 0.1))
        ring = [pt(R - 3 * u, a0 + (a1 - a0) * i / k) for i in range(k + 1)] + [pt(r + 3 * u, a1 - (a1 - a0) * i / k) for i in range(k + 1)]
        return "M" + "L".join("%.1f %.1f" % (px + ox, py + oy) for px, py in ring) + "Z"

    a, plain_i, mids = -math.pi / 2, 0, []
    for i, p in enumerate(parts):
        a1 = a + 2 * math.pi * vals[i] / tot          # exact share: the pen wobbles, the angle does not
        if vals[i] > 0:
            if _pick(d, i):
                P.path(wedge(a, a1, P.rnd(-5, 5) * u, P.rnd(-4, 4) * u), "wash wc")
            else:
                if plain_i % 2 == 0:
                    P.path(wedge(a, a1, P.rnd(-5, 5) * u, P.rnd(-4, 4) * u), "wash wa")
                else:
                    P._clip += 1
                    cid = "w%d_%d" % (id(P) % 99999, P._clip)
                    P.raw('<clipPath id="%s"><path d="%s"/></clipPath>' % (cid, wedge(a, a1)))
                    P.raw('<path class="dp thin" clip-path="url(#%s)" d="%s"/>' % (cid, P.r.hatch(cx - R, cy - R, 2 * R, 2 * R, angle=48, gap=16 * u, j=P.J(0.7))))
                plain_i += 1
            if len(parts) > 1:
                P.line(*pt(r, a), *pt(R, a), j=0.3, bow=0)
        mids.append((a + a1) / 2)
        a = a1
    P.circle(cx, cy, R)
    P.circle(cx, cy, r, second=False)
    if d.get("center"):
        P.text(cx - r * 0.82, cy - r * 0.62, r * 1.64, r * 1.24, d["center"], cls="serif", size=38 * u)
    # labels sit beside their slice, joined by a short pencil line
    lh = 132 * u
    for sgn in (1, -1):
        side = sorted([(cy + math.sin(mids[i]) * R * 1.05, i) for i in range(len(parts)) if vals[i] > 0 and (math.cos(mids[i]) >= 0) == (sgn > 0)])
        ys = [min(max(t, lh / 2), h - lh / 2) for t, _ in side]
        for k in range(1, len(ys)):
            ys[k] = max(ys[k], ys[k - 1] + lh)
        for k in range(len(ys) - 1, -1, -1):
            top = h - lh / 2 if k == len(ys) - 1 else ys[k + 1] - lh
            ys[k] = min(ys[k], top)
        for (t, i), yl in zip(side, ys):
            on = _pick(d, i)
            p = parts[i]
            lx = cx + R + 48 * u if sgn > 0 else 4 * u
            lw = (w - lx - 4 * u) if sgn > 0 else (cx - R - 52 * u)
            edge = lx - 12 * u if sgn > 0 else lx + lw + 12 * u
            P.line(*pt(R + 9 * u, mids[i]), edge, yl, cls="dt" if on else "dp", j=0.4)
            al = "left" if sgn > 0 else "right"
            val = p.get("show", ("%g" % float(p["value"])) + unit)
            P.text(lx, yl - lh / 2 + 4 * u, lw, 60 * u, val, cls="serif pen" if on else "serif", size=(48 if on else 42) * u, align=al, valign="bottom")
            P.text(lx, yl - lh / 2 + 64 * u, lw, lh - 68 * u, _label(p), cls="hand pen" if on else "hand ink", size=36 * u, align=al, valign="top")


# 29 --------------------------------------------------------------- folder (what is inside)
def _file_icon(P, x, y, s, is_folder, cls="d"):
    if is_folder:
        P.poly([(x, y + s * 0.2), (x + s * 0.38, y + s * 0.2), (x + s * 0.5, y + s * 0.36), (x + s, y + s * 0.36), (x + s, y + s * 0.92), (x, y + s * 0.92)], cls=cls, wash="wa")
    else:
        fx, fw = x + s * 0.14, s * 0.72
        P.poly([(fx, y + s * 0.04), (fx + fw * 0.64, y + s * 0.04), (fx + fw, y + s * 0.3), (fx + fw, y + s * 0.98), (fx, y + s * 0.98)], cls=cls)
        P.path(P.r.line(fx + fw * 0.64, y + s * 0.04, fx + fw * 0.64, y + s * 0.3, j=P.J(0.3), bow=0)
               + P.r.line(fx + fw * 0.64, y + s * 0.3, fx + fw, y + s * 0.3, j=P.J(0.3), bow=0), cls + " thin")
        for k in (0.52, 0.68, 0.84):
            P.line(fx + fw * 0.2, y + s * k, fx + fw * 0.8, y + s * k, cls="dp thin", j=0.3, bow=0)


def folder(P, d):
    u, w, h = P.u, P.w, P.h
    items = d["items"][:7]
    n = len(items)
    head = 124 * u
    rh = min(136 * u, (h - head - 8 * u) / n)
    y0 = (h - head - n * rh) / 2
    x0 = 10 * u
    rs = 84 * u
    _file_icon(P, x0, y0 + 10 * u, rs, True)
    P.text(x0 + rs + 22 * u, y0, w - x0 - rs - 30 * u, 104 * u, _label(d.get("root", "")), cls="serif", size=46 * u, align="left")
    tx = x0 + rs * 0.5
    s = min(66 * u, rh * 0.6)
    step = 78 * u
    parent, last_y = None, None
    for i, it in enumerate(items):
        name = it if isinstance(it, str) else (it.get("name") or _label(it))
        note = "" if isinstance(it, str) else it.get("note", "")
        deep = (not isinstance(it, str)) and int(it.get("depth", 1)) >= 2 and parent is not None
        yc = y0 + head + i * rh + rh / 2
        ix = tx + 44 * u + (step if deep else 0)
        on = _pick(d, i)
        if deep:
            px, py = parent
            P.path(P.r.line(px, py, px, yc, j=P.J(0.4), bow=0) + P.r.line(px, yc, ix - 8 * u, yc, j=P.J(0.4), bow=0), "dp")
        else:
            P.line(tx, yc, ix - 8 * u, yc, cls="dp", j=0.4, bow=0)
            parent, last_y = (ix + s * 0.5, yc + s * 0.5 + 6 * u), yc
        _file_icon(P, ix, yc - s / 2, s, name.endswith("/"), cls="dt" if on else "d")
        nx = ix + s + 18 * u
        nw = min(w * 0.4, 400 * u) - (step * 0.6 if deep else 0)
        if not note:
            nw = w - nx - 6 * u
        if on:
            P.wash_rect(nx - 8 * u, yc - 32 * u, min(nw, len(name) * 23 * u + 20 * u), 64 * u, "wb")
        P.text(nx, yc - rh / 2 + 4 * u, nw, rh - 8 * u, name, cls="body bold pen" if on else "body bold", size=40 * u, align="left")
        if note:
            P.text(nx + nw + 16 * u, yc - rh / 2 + 4 * u, w - (nx + nw + 16 * u) - 4 * u, rh - 8 * u, note, cls="hand", size=36 * u, align="left")
    if last_y is not None:
        P.line(tx, y0 + 10 * u + rs * 0.92 + 8 * u, tx, last_y, cls="dp", j=0.5, bow=0)


# 30 --------------------------------------------------------------- balance (a trade-off: two sides weighed, one wins)
def balance(P, d):
    u, w, h = P.u, P.w, P.h
    L, Rt = d["left"], d["right"]
    lp, rp = (L.get("points") or [])[:3], (Rt.get("points") or [])[:3]
    heavy = d.get("heavier") or ("right" if len(rp) >= len(lp) else "left")
    ang = 5.5 if heavy == "right" else -5.5
    half = w * 0.47
    lift = math.sin(math.radians(5.5)) * half          # how far the light side rises
    th = min(170 * u, h * 0.22)                         # height of the stand
    title_h = 96 * u
    kmax = max(len(lp), len(rp), 1)
    bh = min(98 * u, (h - th - 30 * u - lift - title_h - 20 * u) / kmax)
    used = th + 30 * u + kmax * bh + title_h + lift
    px, py = w / 2, h - max((h - used) / 2, 0) - 24 * u  # foot of the stand
    by = py - th                                        # the beam sits here
    bw = min(half * 0.84, 430 * u)
    P.poly([(px, by + 8 * u), (px - th * 0.5, py), (px + th * 0.5, py)], wash="wa")
    P.line(px - th * 0.95, py, px + th * 0.95, py, j=0.4)
    if d.get("note"):
        nx = 8 * u if heavy == "right" else px + th * 0.7
        P.text(nx, by + 34 * u, half - th * 0.7, py - by - 34 * u, d["note"], cls="hand", size=36 * u, align="left" if heavy == "right" else "right", valign="bottom")
    P.push(ang, px, by)
    P.line(px - half, by, px + half, by, j=0.4, bow=0)
    P.line(px - half + 6 * u, by + 9 * u, px + half - 6 * u, by + 9 * u, cls="d thin", j=0.4, bow=0)
    for sd, S, pts in (("left", L, lp), ("right", Rt, rp)):
        bx = px - half + 8 * u if sd == "left" else px + half - bw - 8 * u
        on = sd == heavy
        for k, t in enumerate(pts):
            yb = by - (k + 1) * bh - 2 * u
            P.box(bx + P.rnd(-8, 8) * u, yb, bw, bh - 5 * u, wash="wb" if on else None)
            P.text(bx + 12 * u, yb + 2 * u, bw - 24 * u, bh - 10 * u, _label(t), cls="hand ink", size=38 * u)
        ty = by - len(pts) * bh - title_h - 4 * u
        P.text(bx, ty, bw, title_h - 8 * u, _label(S), cls="serif pen" if on else "serif", size=44 * u, valign="bottom")
    P.pop()


# ------------------------------------------------------------------ the list of 30
# shape = the kind of idea it shows. sample = data that works (also the data format).
PICTURES = {
    "hub": dict(fn=hub, group="How things connect", shape="1 thing becomes many, or many feed 1",
                sample={"center": "1 idea", "items": ["X thread", {"label": "carousel", "icon": "instagram"}, "LinkedIn post", "blog post", "newsletter"], "dir": "out"}),
    "venn": dict(fn=venn, group="How things connect", shape="things that overlap; the middle is the point",
                 sample={"sets": ["skills", "agents", "automations"], "middle": "systems", "note": "this middle bit is what I build"}),
    "compare": dict(fn=compare, group="How things connect", shape="A vs B, wrong way vs right way, myth vs fact",
                    sample={"left": {"title": "One giant prompt", "points": ["hard to fix", "breaks quietly", "starts over each time"], "good": False},
                            "right": {"title": "Small skills", "points": ["fix one piece", "a check after each", "reuse them anywhere"], "good": True}}),
    "fix": dict(fn=fix, group="How things connect", shape="first try crossed out, then the better version",
                sample={"before": "Write me a post about AI", "after": "Write for ==builders== who already use AI tools", "note": "say who it's for"}),
    "matrix": dict(fn=matrix, group="How things connect", shape="2 questions at once (a 2 by 2)",
                   sample={"x": "how often you do it →", "y": "how boring it is →", "cells": ["automate later", "automate first", "leave it", "make a template"], "pick": 1}),
    "spectrum": dict(fn=spectrum, group="How things connect", shape="a scale between two ends, and where things sit",
                     sample={"left": "you do it all", "right": "AI does it all", "marks": [{"label": "autocomplete", "at": 0.12}, {"label": "chat", "at": 0.38}, {"label": "skills", "at": 0.64}, {"label": "agents", "at": 0.9}], "pick": 2}),
    "equation": dict(fn=equation, group="How things connect", shape="parts that add up to a result",
                     sample={"parts": ["11 skills", "1 agent", "a check after each step"], "result": "a content pipeline"}),
    "steps": dict(fn=steps, group="How it happens", shape="a how-to in order (2 to 5 steps)",
                  sample={"steps": [{"title": "Write the brief", "text": "who it is for, what it must do"}, {"title": "Let AI draft", "text": "one piece at a time"}, {"title": "Check it", "text": "against a short scorecard"}]}),
    "loop": dict(fn=loop, group="How it happens", shape="something that repeats or feeds itself",
                 sample={"nodes": ["build", "use it", "see what broke", "fix"], "center": "every week"}),
    "pipeline": dict(fn=pipeline, group="How it happens", shape="a long process with a check after each step",
                     sample={"steps": ["idea", "research", "write", "channels", "pictures", "schedule", "results"]}),
    "timeline": dict(fn=timeline, group="How it happens", shape="what happened when",
                     sample={"events": [{"when": "Week 1", "what": "one skill"}, {"when": "Week 2", "what": "five skills"}, {"when": "Week 3", "what": "checks added"}, {"when": "Week 4", "what": "runs end to end"}], "pick": 3}),
    "tree": dict(fn=tree, group="How it happens", shape="a choice: if this, go that way",
                 sample={"question": "Will you do this task again?", "branches": [{"when": "no", "then": "just do it by hand"}, {"when": "yes", "then": "make it a skill", "good": True}]}),
    "ladder": dict(fn=ladder, group="How it happens", shape="levels you climb, one after another",
                   sample={"levels": ["ask a question", "save a prompt", "build a skill", "chain skills", "run a system"], "pick": 2}),
    "funnel": dict(fn=funnel, group="How it happens", shape="many go in, few come out",
                   sample={"stages": [{"label": "ideas", "value": "30"}, {"label": "researched", "value": "10"}, {"label": "drafted", "value": "5"}, {"label": "posted", "value": "1"}]}),
    "layers": dict(fn=layers, group="What it is made of", shape="what sits on top of what",
                   sample={"layers": [{"label": "what you see", "note": "the post"}, {"label": "skills", "note": "one per job"}, {"label": "checks", "note": "after every step"}, {"label": "your notes", "note": "where it all starts"}], "pick": 2}),
    "iceberg": dict(fn=iceberg, group="What it is made of", shape="the small part people see, the big part they don't",
                    sample={"above": ["one finished post"], "below": ["research", "3 drafts", "fact checks", "5 channel versions", "pictures"]}),
    "anatomy": dict(fn=anatomy, group="What it is made of", shape="one thing with its parts named",
                    sample={"thing": "a good skill file", "parts": ["when to use it", "the steps", "an example", "what to check"], "pick": 3}),
    "screen": dict(fn=screen, group="What it is made of", shape="a tool or page, with one part pointed out",
                   sample={"title": "SKILL.md", "lines": ["name: visuals", "", ""], "at": 1, "highlight": "description: when to use this", "note": "this line decides if it runs"}),
    "stickies": dict(fn=stickies, group="What it is made of", shape="a set of equal things, in no order",
                     sample={"items": ["Docs", "Slides", "Sheets", "Whiteboard", "Data", "Design"]}),
    "bars": dict(fn=bars, group="Numbers", shape="a few real numbers side by side",
                 sample={"bars": [{"label": "by hand", "value": 6}, {"label": "one prompt", "value": 3}, {"label": "pipeline", "value": 1}], "unit": "h", "pick": 2}),
    "curve": dict(fn=curve, group="Numbers", shape="how something changes over time",
                  sample={"x": "time →", "y": "how useful it is", "lines": [{"label": "what I expected", "shape": "up", "main": False}, {"label": "what happened", "shape": "dip", "main": True}],
                          "mark": {"at": [0.38, 0.18], "label": "the week it all broke"}}),
    "bignumber": dict(fn=bignumber, group="Numbers", shape="one number worth remembering",
                      sample={"value": "11", "label": "steps, with a check after every one", "dots": [11, 11]}),
    "quote": dict(fn=quote, group="Words", shape="a real, exact quote",
                  sample={"text": "My test: am I still using it a month later?", "by": "page 1 of the sketchbook"}),
    "checklist": dict(fn=checklist, group="Words", shape="rules, do's and don'ts, things to tick off",
                      sample={"title": "Before it goes out", "items": [{"text": "One idea per picture", "ok": True}, {"text": "Reads in 2 seconds", "ok": True}, {"text": "Every fact has a source", "ok": True}, {"text": "Made-up numbers", "ok": False}]}),
    "prompt": dict(fn=prompt, group="Words", shape="what to type and what you get",
                   sample={"ask": "Turn this blog post into a 7-image carousel. One idea per image.", "answer": ["a hook image", "5 idea images", "a save-this recap"]}),
    # 26 to 30 (added 2026-11-21). They keep their numbers; each belongs to the group named here.
    "machine": dict(fn=machine, group="How it happens", shape="things go in, one system works on them, things come out",
                    sample={"in": ["one idea", "my notes", "past lessons"], "box": "the content pipeline", "out": ["5 posts", "the pictures", "a schedule"]}),
    "table": dict(fn=table, group="How things connect", shape="a few options checked against the same questions",
                  sample={"cols": ["by hand", "one prompt", "small skills"], "rows": [{"label": "easy to check", "cells": [True, False, True]}, {"label": "easy to fix", "cells": [True, False, True]},
                                                                                    {"label": "fast", "cells": [False, True, True]}], "pick": 2}),
    "donut": dict(fn=donut, group="Numbers", shape="shares of one whole (real numbers that add up)",
                  sample={"parts": [{"label": "checking", "value": 50}, {"label": "writing", "value": 30}, {"label": "pictures", "value": 20}], "unit": "%", "center": "one post", "pick": 0}),
    "folder": dict(fn=folder, group="What it is made of", shape="what is inside a folder, a file or a kit",
                   sample={"root": "my-skill/", "items": [{"name": "SKILL.md", "note": "when to use it + the steps"}, {"name": "references/", "note": "longer guides"},
                                                          {"name": "scripts/", "note": "code it can run"}, {"name": "learnings.md", "note": "one-line rules"}], "pick": 0}),
    "balance": dict(fn=balance, group="How things connect", shape="a trade-off: two sides weighed, one wins",
                    sample={"left": {"title": "one big prompt", "points": ["quick to write"]}, "right": {"title": "small skills", "points": ["easy to check", "easy to fix", "use them again"]},
                            "note": "more setup, worth it"}),
}

# names used by the older picture templates still work
ALIASES = {"stat": "bignumber", "icons": "stickies", "flow": "steps", "cycle": "loop", "icon": "stickies", "before-after": "fix", "2x2": "matrix",
           "scale": "spectrum", "stack": "layers", "pyramid": "layers", "chart": "bars", "line": "curve", "decision": "tree", "stairs": "ladder",
           "pie": "donut", "share": "donut", "files": "folder", "filetree": "folder", "seesaw": "balance", "tradeoff": "balance", "trade-off": "balance",
           "in-out": "machine", "inout": "machine", "grid": "table"}


def adapt(d):
    """Turn older template data into the new shape so old post files keep working."""
    t = d.get("type")
    d = dict(d)
    if t == "stat":
        d.setdefault("value", d.get("value", ""))
    if t == "icons" or t == "icon":
        d["items"] = [x.get("label", "") if isinstance(x, dict) else x for x in d.get("items", [{"label": d.get("label", "")}])]
    if t == "flow":
        d["steps"] = [{"title": x} if isinstance(x, str) else x for x in d.get("nodes", [])]
    if t == "cycle":
        d["nodes"] = d.get("nodes", [])
    if t == "pyramid":
        d["shape"] = "pyramid"
    if t == "hub":
        d["center"] = _label(d.get("center", ""))
    d["type"] = ALIASES.get(t, t)
    return d


# a headline for each sample (a claim, not a label), used by --sampler
TITLES = {
    "hub": "One idea becomes ==five posts==", "venn": "What I build sits in ==the middle==", "compare": "Small skills beat ==one giant prompt==",
    "fix": "Say ==who it is for==", "matrix": "Automate the ==boring, frequent== jobs first", "spectrum": "Skills sit ==between== chat and agents",
    "equation": "A pipeline is ==three things== added up", "steps": "Brief, draft, ==check==", "loop": "It only gets good ==by repeating==",
    "pipeline": "Seven steps, ==a check after each==", "timeline": "It took ==four weeks== to run end to end", "tree": "Doing it twice? ==Make it a skill==",
    "ladder": "Most people stop at ==step two==", "funnel": "Thirty ideas in, ==one post== out", "layers": "The checks are ==the quiet layer==",
    "iceberg": "A post is ==the small part==", "anatomy": "A skill file has ==four parts==", "screen": "One line decides ==if a skill runs==",
    "stickies": "Claude can make ==six things==", "bars": "Hours per post, ==sample numbers==", "curve": "It got worse ==before it got better==",
    "bignumber": "Every step gets ==checked==", "quote": "The only test ==that counts==", "checklist": "The ==last look== before posting",
    "prompt": "Ask for ==one idea per image==",
    "machine": "Notes in, ==posts out==", "table": "Small skills ==tick every box==", "donut": "Half the work is ==checking==",
    "folder": "What's inside ==a skill folder==", "balance": "More setup, ==worth it==",
}
for _k, _t in TITLES.items():
    PICTURES[_k]["sample_title"] = _t
