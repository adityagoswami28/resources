"""Small hand-drawn icons and app logos for the sketchbook pictures.

Two kinds, all drawn with the same wobbly black pen as the pictures (never an icon font, never brand colors):
  LOGOS   apps and channels a post names (X, Instagram, LinkedIn, YouTube, Notion, Claude, GitHub, blog, newsletter, website)
  ICONS   everyday things (idea, search, write, calendar, chart...)

An icon sits next to the WORD it stands for. It never replaces the word and is never decoration on its own.
Pictures ask for them through resolve(); pen.py draws them beside a label (Pen.text(..., icon="x")).

The set keeps growing: when a needed logo or icon is missing, draw it and add it here.
To add one: write a small function below (it draws inside a 1 x 1 box), add it to LOGOS or ICONS,
and add the words that should find it to LOGO_WORDS or ICON_WORDS. Then:
  python3 sketch.py --icons icons-and-logos.png --theme both               (look at the sheet, day and night)
  python3 sketch.py --icons-web icons.json        (the same drawings for a website)
Full steps: references/pictures.md, "Adding a logo or icon".
"""
import math, re


class G:
    """A tiny drawing board: every number is a share of the icon's size (0 = left/top, 1 = right/bottom)."""

    def __init__(self, P, x, y, s, cls="di"):
        self.P, self.x, self.y, self.s, self.cls = P, x, y, s, cls

    def X(self, v):
        return self.x + v * self.s

    def Y(self, v):
        return self.y + v * self.s

    def j(self):
        return max(self.s * 0.012, 0.5)

    def L(self, x1, y1, x2, y2):
        self.P.path(self.P.r.line(self.X(x1), self.Y(y1), self.X(x2), self.Y(y2), j=self.j() * 0.6, bow=self.P.rnd(-1, 1) * self.s * 0.012, seg=self.s), self.cls)

    def PL(self, pts, close=True):
        n = len(pts)
        d = ""
        for i in range(n if close else n - 1):
            a, b = pts[i], pts[(i + 1) % n]
            d += self.P.r.line(self.X(a[0]), self.Y(a[1]), self.X(b[0]), self.Y(b[1]), j=self.j() * 0.6, bow=self.P.rnd(-1, 1) * self.s * 0.01,
                               over=self.s * 0.015, seg=self.s)
        self.P.path(d, self.cls)

    def CV(self, pts):
        self.P.path(self.P.r.curve([(self.X(a), self.Y(b)) for a, b in pts], j=self.j() * 0.7), self.cls)

    def C(self, cx, cy, rx, ry=None, turn=1.08):
        ry = rx if ry is None else ry
        self.P.path(self.P.r.ellipse(self.X(cx), self.Y(cy), rx * self.s, ry * self.s, j=0.02, turn=turn, n=14, drift=0.03), self.cls)

    def R(self, x, y, w, h):
        self.PL([(x, y), (x + w, y), (x + w, y + h), (x, y + h)])

    def RR(self, x, y, w, h, r):
        """A box with round corners."""
        pts = [(x + w * 0.42, y)]
        for cx, cy, a0 in ((x + w - r, y + r, -90), (x + w - r, y + h - r, 0), (x + r, y + h - r, 90), (x + r, y + r, 180)):
            for k in range(4):
                a = math.radians(a0 + k * 30)
                pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
        pts.append((x + w * 0.5, y + 0.008))
        self.CV(pts)

    def D(self, cx, cy, r):
        self.P.dot(self.X(cx), self.Y(cy), r * self.s)

    def A(self, pts):
        self.P.path(self.P.r.arrow([(self.X(a), self.Y(b)) for a, b in pts], head=self.s * 0.16, j=self.j() * 0.6), self.cls)


# ------------------------------------------------------------------ app and channel logos (hand-drawn, black pen)
def x(g):
    g.PL([(0.12, 0.1), (0.33, 0.1), (0.88, 0.9), (0.67, 0.9)])
    g.L(0.87, 0.1, 0.57, 0.43)
    g.L(0.43, 0.58, 0.14, 0.9)


def instagram(g):
    g.RR(0.09, 0.09, 0.82, 0.82, 0.24)
    g.C(0.5, 0.5, 0.2)
    g.D(0.73, 0.27, 0.05)


def linkedin(g):
    g.RR(0.09, 0.09, 0.82, 0.82, 0.13)
    g.D(0.3, 0.31, 0.055)
    g.L(0.3, 0.45, 0.3, 0.73)
    g.L(0.46, 0.45, 0.46, 0.73)
    g.CV([(0.46, 0.56), (0.52, 0.47), (0.62, 0.46), (0.69, 0.55), (0.7, 0.73)])


def youtube(g):
    g.RR(0.05, 0.2, 0.9, 0.6, 0.17)
    g.PL([(0.41, 0.36), (0.65, 0.5), (0.41, 0.64)])


def notion(g):
    g.PL([(0.16, 0.28), (0.7, 0.28), (0.7, 0.88), (0.16, 0.88)])
    g.PL([(0.16, 0.28), (0.3, 0.13), (0.86, 0.13), (0.7, 0.28)], close=False)
    g.PL([(0.86, 0.13), (0.86, 0.73), (0.7, 0.88)], close=False)
    g.PL([(0.31, 0.76), (0.31, 0.41), (0.56, 0.76), (0.56, 0.41)], close=False)


def claude(g):
    n = 11
    for i in range(n):
        a = -math.pi / 2 + i * 2 * math.pi / n + g.P.rnd(-0.06, 0.06)
        r = g.P.rnd(0.36, 0.45)
        g.L(0.5 + math.cos(a) * 0.09, 0.5 + math.sin(a) * 0.09, 0.5 + math.cos(a) * r, 0.5 + math.sin(a) * r)


def github(g):
    g.C(0.5, 0.5, 0.43)
    g.CV([(0.41, 0.72), (0.3, 0.63), (0.27, 0.47), (0.31, 0.38), (0.3, 0.26), (0.41, 0.33), (0.5, 0.31), (0.59, 0.33), (0.7, 0.26), (0.69, 0.38), (0.73, 0.47), (0.7, 0.63), (0.59, 0.72)])
    g.L(0.41, 0.72, 0.41, 0.9)
    g.L(0.59, 0.72, 0.59, 0.9)
    g.CV([(0.41, 0.8), (0.33, 0.82), (0.25, 0.74)])


def blog(g):
    g.R(0.08, 0.15, 0.84, 0.7)
    g.L(0.08, 0.32, 0.92, 0.32)
    g.D(0.17, 0.235, 0.03)
    g.D(0.26, 0.235, 0.03)
    g.L(0.2, 0.46, 0.8, 0.46)
    g.L(0.2, 0.59, 0.8, 0.59)
    g.L(0.2, 0.72, 0.55, 0.72)


def newsletter(g):
    g.R(0.07, 0.2, 0.86, 0.6)
    g.PL([(0.08, 0.22), (0.5, 0.56), (0.92, 0.22)], close=False)


def website(g):
    g.C(0.5, 0.5, 0.41)
    g.C(0.5, 0.5, 0.17, 0.41, turn=1.02)
    g.L(0.09, 0.5, 0.91, 0.5)
    g.CV([(0.17, 0.28), (0.5, 0.34), (0.83, 0.28)])
    g.CV([(0.17, 0.72), (0.5, 0.66), (0.83, 0.72)])


# ------------------------------------------------------------------ everyday icons
def idea(g):
    g.C(0.5, 0.46, 0.23)
    g.L(0.4, 0.74, 0.6, 0.74)
    g.L(0.42, 0.83, 0.58, 0.83)
    g.L(0.46, 0.92, 0.54, 0.92)
    g.L(0.5, 0.04, 0.5, 0.13)
    g.L(0.15, 0.2, 0.22, 0.26)
    g.L(0.85, 0.2, 0.78, 0.26)


def search(g):
    g.C(0.42, 0.42, 0.27)
    g.L(0.62, 0.62, 0.88, 0.88)


def write(g):
    g.PL([(0.16, 0.84), (0.23, 0.62), (0.7, 0.15), (0.85, 0.3), (0.38, 0.77)])
    g.L(0.23, 0.62, 0.38, 0.77)
    g.L(0.61, 0.24, 0.76, 0.39)


def doc(g):
    g.PL([(0.23, 0.08), (0.61, 0.08), (0.78, 0.25), (0.78, 0.92), (0.23, 0.92)])
    g.PL([(0.61, 0.08), (0.61, 0.25), (0.78, 0.25)], close=False)
    g.L(0.34, 0.46, 0.67, 0.46)
    g.L(0.34, 0.6, 0.67, 0.6)
    g.L(0.34, 0.74, 0.55, 0.74)


def folder(g):
    g.PL([(0.08, 0.24), (0.38, 0.24), (0.46, 0.35), (0.92, 0.35), (0.92, 0.82), (0.08, 0.82)])


def chat(g):
    g.RR(0.08, 0.14, 0.84, 0.56, 0.15)
    g.PL([(0.3, 0.7), (0.25, 0.9), (0.47, 0.7)], close=False)
    for k in (0.35, 0.5, 0.65):
        g.D(k, 0.42, 0.035)


def clock(g):
    g.C(0.5, 0.5, 0.41)
    g.L(0.5, 0.5, 0.5, 0.25)
    g.L(0.5, 0.5, 0.68, 0.6)


def calendar(g):
    g.R(0.11, 0.2, 0.78, 0.7)
    g.L(0.11, 0.39, 0.89, 0.39)
    g.L(0.32, 0.09, 0.32, 0.27)
    g.L(0.68, 0.09, 0.68, 0.27)
    for cx, cy in ((0.32, 0.56), (0.5, 0.56), (0.68, 0.56), (0.32, 0.74), (0.5, 0.74)):
        g.D(cx, cy, 0.035)


def check(g):
    g.C(0.5, 0.5, 0.41)
    g.CV([(0.3, 0.52), (0.44, 0.67), (0.72, 0.3)])


def star(g):
    pts = []
    for i in range(10):
        a = -math.pi / 2 + i * math.pi / 5
        r = 0.44 if i % 2 == 0 else 0.18
        pts.append((0.5 + math.cos(a) * r, 0.54 + math.sin(a) * r))
    g.PL(pts)


def heart(g):
    g.CV([(0.5, 0.86), (0.2, 0.6), (0.1, 0.4), (0.16, 0.22), (0.33, 0.17), (0.5, 0.32), (0.67, 0.17), (0.84, 0.22), (0.9, 0.4), (0.8, 0.6), (0.5, 0.86)])


def rocket(g):
    g.CV([(0.36, 0.64), (0.35, 0.36), (0.5, 0.06), (0.65, 0.36), (0.64, 0.64)])
    g.L(0.36, 0.64, 0.64, 0.64)
    g.C(0.5, 0.36, 0.07)
    g.PL([(0.36, 0.44), (0.19, 0.72), (0.36, 0.64)], close=False)
    g.PL([(0.64, 0.44), (0.81, 0.72), (0.64, 0.64)], close=False)
    g.PL([(0.43, 0.72), (0.5, 0.93), (0.57, 0.72)], close=False)


def target(g):
    g.C(0.5, 0.5, 0.42)
    g.C(0.5, 0.5, 0.24)
    g.D(0.5, 0.5, 0.06)


def spark(g):
    g.PL([(0.4, 0.06), (0.48, 0.36), (0.76, 0.44), (0.48, 0.52), (0.4, 0.82), (0.32, 0.52), (0.04, 0.44), (0.32, 0.36)])
    g.PL([(0.78, 0.6), (0.81, 0.73), (0.94, 0.77), (0.81, 0.81), (0.78, 0.94), (0.75, 0.81), (0.62, 0.77), (0.75, 0.73)])


def gear(g):
    pts = []
    for i in range(8):
        a = i * math.pi / 4
        for da, r in ((-0.15, 0.44), (0.15, 0.44), (0.27, 0.33), (0.515, 0.33)):
            pts.append((0.5 + math.cos(a + da) * r, 0.5 + math.sin(a + da) * r))
    g.PL(pts)
    g.C(0.5, 0.5, 0.14)


def key(g):
    g.C(0.28, 0.5, 0.18)
    g.L(0.46, 0.5, 0.92, 0.5)
    g.L(0.74, 0.5, 0.74, 0.66)
    g.L(0.87, 0.5, 0.87, 0.63)


def lock(g):
    g.R(0.19, 0.44, 0.62, 0.46)
    g.CV([(0.32, 0.44), (0.32, 0.22), (0.5, 0.1), (0.68, 0.22), (0.68, 0.44)])
    g.D(0.5, 0.66, 0.05)


def link(g):
    g.P.push(-40, g.X(0.5), g.Y(0.5))
    g.RR(0.02, 0.37, 0.52, 0.26, 0.13)
    g.RR(0.46, 0.37, 0.52, 0.26, 0.13)
    g.P.pop()


def bolt(g):
    g.PL([(0.58, 0.05), (0.23, 0.55), (0.46, 0.55), (0.4, 0.95), (0.77, 0.42), (0.54, 0.42)])


def chart(g):
    g.PL([(0.13, 0.08), (0.13, 0.88), (0.92, 0.88)], close=False)
    g.R(0.26, 0.56, 0.14, 0.32)
    g.R(0.48, 0.38, 0.14, 0.5)
    g.R(0.7, 0.2, 0.14, 0.68)


def eye(g):
    g.CV([(0.06, 0.5), (0.28, 0.27), (0.5, 0.22), (0.72, 0.27), (0.94, 0.5)])
    g.CV([(0.06, 0.5), (0.28, 0.73), (0.5, 0.78), (0.72, 0.73), (0.94, 0.5)])
    g.C(0.5, 0.5, 0.13)
    g.D(0.5, 0.5, 0.045)


def flag(g):
    g.L(0.22, 0.06, 0.22, 0.94)
    g.PL([(0.22, 0.12), (0.84, 0.3), (0.22, 0.5)], close=False)


def repeat(g):
    g.A([(0.82, 0.42), (0.68, 0.2), (0.4, 0.17), (0.2, 0.36)])
    g.A([(0.18, 0.58), (0.32, 0.8), (0.6, 0.83), (0.8, 0.64)])


def image(g):
    g.R(0.08, 0.17, 0.84, 0.66)
    g.PL([(0.15, 0.76), (0.37, 0.48), (0.52, 0.65), (0.66, 0.5), (0.86, 0.76)], close=False)
    g.C(0.68, 0.34, 0.07)


def save(g):
    g.PL([(0.25, 0.08), (0.75, 0.08), (0.75, 0.92), (0.5, 0.7), (0.25, 0.92)])


def send(g):
    g.PL([(0.06, 0.46), (0.94, 0.08), (0.62, 0.92), (0.44, 0.58)])
    g.L(0.44, 0.58, 0.94, 0.08)


def megaphone(g):
    g.PL([(0.1, 0.4), (0.32, 0.4), (0.72, 0.16), (0.72, 0.84), (0.32, 0.6), (0.1, 0.6)])
    g.L(0.2, 0.6, 0.27, 0.84)
    g.L(0.83, 0.34, 0.93, 0.28)
    g.L(0.84, 0.5, 0.96, 0.5)
    g.L(0.83, 0.66, 0.93, 0.72)


def person(g):
    g.C(0.5, 0.3, 0.17)
    g.CV([(0.16, 0.92), (0.2, 0.68), (0.5, 0.57), (0.8, 0.68), (0.84, 0.92)])


def book(g):
    g.PL([(0.5, 0.24), (0.3, 0.15), (0.07, 0.19), (0.07, 0.8), (0.3, 0.76), (0.5, 0.86)])
    g.PL([(0.5, 0.24), (0.7, 0.15), (0.93, 0.19), (0.93, 0.8), (0.7, 0.76), (0.5, 0.86)], close=False)


def cloud(g):
    g.CV([(0.26, 0.74), (0.12, 0.66), (0.12, 0.5), (0.27, 0.44), (0.36, 0.28), (0.56, 0.25), (0.68, 0.38), (0.84, 0.42), (0.9, 0.58), (0.8, 0.72), (0.26, 0.74)])


def database(g):
    g.C(0.5, 0.23, 0.33, 0.12, turn=1.04)
    g.L(0.17, 0.23, 0.17, 0.77)
    g.L(0.83, 0.23, 0.83, 0.77)
    g.CV([(0.17, 0.5), (0.33, 0.61), (0.5, 0.62), (0.67, 0.61), (0.83, 0.5)])
    g.CV([(0.17, 0.77), (0.33, 0.88), (0.5, 0.89), (0.67, 0.88), (0.83, 0.77)])


def code(g):
    g.PL([(0.33, 0.25), (0.08, 0.5), (0.33, 0.75)], close=False)
    g.PL([(0.67, 0.25), (0.92, 0.5), (0.67, 0.75)], close=False)
    g.L(0.58, 0.14, 0.42, 0.86)


def terminal(g):
    g.R(0.07, 0.15, 0.86, 0.7)
    g.PL([(0.21, 0.37), (0.38, 0.5), (0.21, 0.63)], close=False)
    g.L(0.46, 0.65, 0.68, 0.65)


def phone(g):
    g.RR(0.27, 0.05, 0.46, 0.9, 0.09)
    g.L(0.42, 0.82, 0.58, 0.82)


def laptop(g):
    g.R(0.2, 0.18, 0.6, 0.44)
    g.PL([(0.2, 0.62), (0.06, 0.8), (0.94, 0.8), (0.8, 0.62)], close=False)


def question(g):
    g.CV([(0.31, 0.32), (0.36, 0.16), (0.55, 0.11), (0.69, 0.24), (0.63, 0.42), (0.5, 0.52), (0.5, 0.67)])
    g.D(0.5, 0.84, 0.05)


def warning(g):
    g.PL([(0.5, 0.09), (0.94, 0.86), (0.06, 0.86)])
    g.L(0.5, 0.36, 0.5, 0.62)
    g.D(0.5, 0.74, 0.04)


def checklist(g):
    for k in (0.14, 0.42, 0.7):
        g.R(0.12, k, 0.16, 0.16)
        g.L(0.4, k + 0.08, 0.88, k + 0.08)


def layers(g):
    g.PL([(0.5, 0.1), (0.92, 0.33), (0.5, 0.56), (0.08, 0.33)])
    g.PL([(0.08, 0.52), (0.5, 0.75), (0.92, 0.52)], close=False)
    g.PL([(0.08, 0.7), (0.5, 0.93), (0.92, 0.7)], close=False)


LOGOS = {"x": x, "instagram": instagram, "linkedin": linkedin, "youtube": youtube, "notion": notion, "claude": claude, "github": github,
         "blog": blog, "newsletter": newsletter, "website": website}
ICONS = {"idea": idea, "search": search, "write": write, "doc": doc, "folder": folder, "chat": chat, "clock": clock, "calendar": calendar,
         "check": check, "star": star, "heart": heart, "rocket": rocket, "target": target, "spark": spark, "gear": gear, "key": key,
         "lock": lock, "link": link, "bolt": bolt, "chart": chart, "eye": eye, "flag": flag, "repeat": repeat, "image": image,
         "save": save, "send": send, "megaphone": megaphone, "person": person, "book": book, "cloud": cloud, "database": database,
         "code": code, "terminal": terminal, "phone": phone, "laptop": laptop, "question": question, "warning": warning,
         "checklist": checklist, "layers": layers}
ALL = dict(LOGOS, **ICONS)
NAMES = {"twitter": "x", "tweet": "x", "ig": "instagram", "insta": "instagram", "li": "linkedin", "yt": "youtube", "email": "newsletter", "mail": "newsletter",
         "site": "website", "web": "website", "globe": "website", "lightbulb": "idea", "bulb": "idea", "magnifier": "search", "research": "search",
         "pencil": "write", "pen": "write", "file": "doc", "page": "doc", "note": "doc", "notes": "doc", "bubble": "chat", "prompt": "chat", "time": "clock",
         "schedule": "calendar", "tick": "check", "done": "check", "ai": "spark", "sparkle": "spark", "sparkles": "spark", "agent": "spark", "magic": "spark",
         "skill": "gear", "settings": "gear", "system": "gear", "fast": "bolt", "lightning": "bolt", "results": "chart", "bars": "chart", "numbers": "chart",
         "see": "eye", "loop": "repeat", "refresh": "repeat", "picture": "image", "photo": "image", "bookmark": "save", "share": "send", "plane": "send",
         "post": "megaphone", "announce": "megaphone", "you": "person", "reader": "person", "user": "person", "lesson": "book", "lessons": "book",
         "learn": "book", "memory": "database", "table": "database", "list": "checklist", "stack": "layers", "goal": "target", "launch": "rocket",
         "why": "question", "careful": "warning", "love": "heart"}

# Words in a label that find a logo. Checked first, always on: a named app gets its logo.
LOGO_WORDS = [
    (r"(?<!\d )(?<!\d)\b(x|twitter|tweets?)\b(?! ?\d)", "x"), (r"\b(instagram|insta|ig|reels?)\b", "instagram"), (r"\blinkedin\b", "linkedin"),
    (r"\byoutube\b", "youtube"), (r"\bnotion\b", "notion"), (r"\bclaude\b", "claude"), (r"\bgithub\b", "github"),
    (r"\bblog\b", "blog"), (r"\b(newsletter|e-?mail)\b", "newsletter"), (r"\b(website|web ?site|web page)\b", "website"),
]
# Words that find an everyday icon. Used only when the picture says "icons": "auto", and then only when EVERY item finds one
# (all or none: half a set of icons looks random).
ICON_WORDS = [
    (r"\bideas?\b", "idea"), (r"\b(research\w*|search\w*|find|look up)\b", "search"), (r"\b(writ\w+|drafts?|drafted)\b", "write"),
    (r"\b(briefs?|notes?|docs?|files?)\b", "doc"), (r"\bfolders?\b", "folder"), (r"\b(chats?|prompts?|ask)\b", "chat"),
    (r"\b(schedul\w+|calendar|plan(ned)?)\b", "calendar"), (r"\b(checks?|checked|quality|review\w*|tests?)\b", "check"),
    (r"\b(pictures?|images?|visuals?|drawings?)\b", "image"), (r"\b(results?|numbers?|stats|scores?)\b", "chart"),
    (r"\b(lessons?|learn\w*|rules?)\b", "book"), (r"\b(skills?|systems?|automat\w+|pipeline|setup)\b", "gear"), (r"\b(agents?|ai)\b", "spark"),
    (r"\b(posts?|posted|channels?|publish\w*)\b", "megaphone"), (r"\b(memory|database|tables?)\b", "database"), (r"\bcode\b", "code"),
    (r"\b(fast\w*|quick\w*|speed)\b", "bolt"), (r"\b(goals?|target)\b", "target"), (r"\b(launch\w*|ship\w*)\b", "rocket"),
    (r"\b(readers?|audience|people)\b", "person"), (r"\blinks?\b", "link"), (r"\b(time|hours?|minutes?)\b", "clock"),
]


def name(n):
    """The icon a name points to, or None."""
    n = str(n or "").strip().lower()
    n = NAMES.get(n, n)
    return n if n in ALL else None


def _text(it):
    if isinstance(it, str):
        return it
    return str(it.get("label") or it.get("title") or it.get("name") or it.get("text") or "")


def resolve(items, mode="logos"):
    """One icon name (or None) per item.
    An item can ask: {"label": "...", "icon": "idea"} or refuse: "icon": false.
    Otherwise a named app or channel gets its logo. With mode "auto", everyday icons are guessed from the words too,
    but only when every item finds one.
    mode: "logos" (the default: logos + the icons an item asks for), "auto" (also guess everyday icons, all or none),
    False (none at all, also not the asked ones)."""
    if mode is False or mode == "none":
        return [None] * len(items)
    out, guess = [], []
    for it in items:
        asked = it.get("icon") if isinstance(it, dict) else None
        t = re.sub(r"==|\*\*|~~", "", _text(it)).lower()
        if asked is False:
            out.append(None); guess.append(False); continue
        if asked:
            out.append(name(asked)); guess.append(False); continue
        hit = next((n for rx, n in LOGO_WORDS if re.search(rx, t)), None)
        if hit:
            out.append(hit); guess.append(False); continue
        hit = next((n for rx, n in ICON_WORDS if re.search(rx, t)), None) if mode in (True, "auto", "all") else None
        out.append(hit); guess.append(True)
    if not all(out):                      # all or none for the guessed everyday icons
        out = [None if g else o for o, g in zip(out, guess)]
    return out


def draw(P, n, x, y, s, cls="di"):
    """Draw icon n with its top-left corner at x, y and size s. Returns False when the name is unknown."""
    n = name(n)
    if not n:
        return False
    ALL[n](G(P, x, y, s, cls))
    return True
