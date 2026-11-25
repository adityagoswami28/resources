"""Make one download zip per resource folder.

    python3 tools/make-zips.py          -> writes downloads/<name>.zip for every folder in skills/
    python3 tools/make-zips.py --check  -> changes nothing, says if a zip is out of date

The zip holds the folder itself (unzip it and you get <name>/ ready to use).
Same files in = the very same zip out (fixed dates and order), so a zip only changes when its folder does.
GitHub runs this on every push (.github/workflows/zips.yml).
"""
import io, os, sys, zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KINDS = ["skills"]                       # add "pipelines", "prompt-guidelines", ... when they hold folders
SKIP = ("__pycache__", ".DS_Store", ".git")


def files_of(folder):
    out = []
    for here, dirs, names in os.walk(folder):
        dirs[:] = sorted(d for d in dirs if d not in SKIP)
        for n in sorted(names):
            if n not in SKIP and not n.endswith(".pyc"):
                out.append(os.path.join(here, n))
    return out


def zip_bytes(folder):
    name = os.path.basename(folder)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for path in files_of(folder):
            rel = os.path.join(name, os.path.relpath(path, folder)).replace(os.sep, "/")
            info = zipfile.ZipInfo(rel, date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            with open(path, "rb") as fh:
                z.writestr(info, fh.read())
    return buf.getvalue()


def main():
    check = "--check" in sys.argv
    os.makedirs(os.path.join(ROOT, "downloads"), exist_ok=True)
    stale = []
    for kind in KINDS:
        base = os.path.join(ROOT, kind)
        if not os.path.isdir(base):
            continue
        for name in sorted(os.listdir(base)):
            folder = os.path.join(base, name)
            if not os.path.isdir(folder):
                continue
            target = os.path.join(ROOT, "downloads", name + ".zip")
            new = zip_bytes(folder)
            old = open(target, "rb").read() if os.path.exists(target) else b""
            if new != old:
                stale.append(name)
                if not check:
                    open(target, "wb").write(new)
                    print("made downloads/%s.zip (%d KB)" % (name, len(new) // 1024))
    if check:
        print("out of date: " + ", ".join(stale) if stale else "every zip is up to date")
        sys.exit(1 if stale else 0)
    if not stale:
        print("every zip is up to date")


if __name__ == "__main__":
    main()
