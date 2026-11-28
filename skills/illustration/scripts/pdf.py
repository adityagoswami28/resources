#!/usr/bin/env python3
"""Join carousel PNGs into one PDF for a LinkedIn document post (one slide per page, no margins).

  python3 pdf.py OUT/li-portrait --out carousel.pdf

Finds Chrome by itself, like sketch.py (set CHROME to change it). No extra installs.
"""
import argparse, glob, os, shutil, struct, subprocess, sys, tempfile


def chrome():
    """CHROME=/path wins; else the Mac app, the cloud's Chromium, or one on PATH (same as sketch.py)."""
    c = os.environ.get("CHROME")
    if c:
        return c
    for p in ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"] + sorted(glob.glob("/opt/pw-browsers/chromium-*/chrome-linux*/chrome")):
        if os.path.exists(p):
            return p
    for n in ("google-chrome", "chromium", "chromium-browser"):
        if shutil.which(n):
            return shutil.which(n)
    sys.exit("Chrome not found. Set CHROME=/path/to/chrome")


def size(png):
    with open(png, "rb") as f:
        f.read(16)
        return struct.unpack(">II", f.read(8))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("folder", help="folder of numbered slide PNGs (01-..., 02-...)")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    pngs = sorted(glob.glob(os.path.join(a.folder, "*.png")))
    if not pngs:
        raise SystemExit("no PNGs in " + a.folder)
    W, H = size(pngs[0])
    if any(size(p) != (W, H) for p in pngs):
        raise SystemExit("all slides must be the same size (LinkedIn crops mixed sizes)")
    imgs = "".join(f'<img src="file://{os.path.abspath(p)}">' for p in pngs)
    page = (f"<!doctype html><style>@page{{size:{W}px {H}px;margin:0}}html,body{{margin:0}}"
            f"img{{display:block;width:{W}px;height:{H}px;page-break-after:always}}img:last-child{{page-break-after:auto}}</style>{imgs}")
    with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False) as f:
        f.write(page)
    out = os.path.abspath(a.out)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    subprocess.run([chrome(), "--headless=new", "--no-sandbox", "--disable-gpu", "--no-pdf-header-footer", "--allow-file-access-from-files",
                    f"--print-to-pdf={out}", "file://" + f.name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=180)
    os.unlink(f.name)
    print(f"✓ {os.path.relpath(out)} ({len(pngs)} pages, {W}x{H}, {os.path.getsize(out)//1024} KB)")


if __name__ == "__main__":
    main()
