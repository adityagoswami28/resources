"""Pop-up explainer: storyboard.json -> video.

  python popup.py story.json --preview        one small picture, a still of every page (check this first)
  python popup.py story.json                  the full video (story.mp4 next to the storyboard)

Output is kept to a few lines on purpose."""
import argparse
import hashlib
import json
import math
import os
import subprocess
import sys
import time
from multiprocessing import Pool


def _setup_check():
    """Say plainly what is missing, and the two lines that fix it, instead of a long error."""
    import importlib.util
    import shutil
    miss = [pkg for mod, pkg in (('numpy', 'numpy'), ('scipy', 'scipy'), ('skia', 'skia-python')) if importlib.util.find_spec(mod) is None]
    if miss:
        print('SETUP missing: %s. Fix (a private Python folder, so nothing else on the machine changes):' % ', '.join(miss))
        print('  python3 -m venv ~/.popup-venv && ~/.popup-venv/bin/pip install skia-python numpy scipy kokoro-onnx soundfile')
        print('  then run this with ~/.popup-venv/bin/python instead of python')
        sys.exit(2)
    if shutil.which('ffmpeg') is None:
        print('SETUP missing: ffmpeg (a program, not a Python package). Mac: brew install ffmpeg. Linux: apt install ffmpeg')
        sys.exit(2)


if __name__ == '__main__':
    _setup_check()
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
FPS = 30
LPS = 17.4           # how fast the free voice speaks, in letters per second (measured). Used for estimates only


def load_story(path):
    with open(path) as fh:
        story = json.load(fh)
    story.setdefault('style', 'cut-paper')
    return story


def story_key(story):
    vis = {k: v for k, v in story.items() if k not in ('voice', 'music', 'air')}
    vis['pages'] = [{k: v for k, v in p.items() if k != 'say'} for p in story['pages']]
    h = hashlib.sha1(json.dumps(vis, sort_keys=True).encode())
    here = os.path.dirname(os.path.abspath(__file__))
    for f in ('core.py', 'kit.py', 'catalogue.py', 'book.py', 'styles.py'):   # a changed engine repaints too
        with open(os.path.join(here, f), 'rb') as fh:
            h.update(fh.read())
    return h.hexdigest()[:12]


def scenes_of(story):
    from book import build_scene
    return [build_scene(p, story, i) for i, p in enumerate(story['pages'])]


def say_secs(story, measured=None):
    if measured:
        return measured
    v = story.get('voice')
    speed = float(v.get('speed', 1.0)) if isinstance(v, dict) else 1.0
    return [max(1.5, len(p.get('say', '').strip()) / LPS / speed) if 'secs' not in p else p['secs'] for p in story['pages']]


def timeline_of(story, scenes, measured=None):
    from render import Timeline
    return Timeline(say_secs(story, measured), [sc.focus for sc in scenes])


def _build_page(job):
    story, i, cache = job
    from styles import get_style
    sc = scenes_of(story)[i]
    st = get_style(story['style'], sc, os.path.join(cache, 'page%d.npz' % i), os.path.join(cache, 'common.npz'))
    st.ensure(load=False)
    return i


def textures(story, cache, procs):
    from styles import get_style
    os.makedirs(cache, exist_ok=True)
    sc = scenes_of(story)
    if not os.path.exists(os.path.join(cache, 'common.npz')):
        st = get_style(story['style'], sc[0], os.path.join(cache, 'page0.npz'), os.path.join(cache, 'common.npz'))
        np.savez(st.common, **st.build_common())
    jobs = [(story, i, cache) for i in range(len(sc)) if not os.path.exists(os.path.join(cache, 'page%d.npz' % i))]
    if jobs:
        with Pool(min(procs, len(jobs))) as pool:
            list(pool.imap_unordered(_build_page, jobs))


def _renderer(story, cache, measured=None):
    from render import Renderer
    sc = scenes_of(story)
    return Renderer(sc, story['style'], cache, timeline_of(story, sc, measured))


def _render_chunk(job):
    story, cache, measured, f0, f1, path = job
    from styles import STYLES, NAMES
    R = _renderer(story, cache, measured)
    twos = STYLES[NAMES.get(story['style'], story['style'])].on_twos
    p = subprocess.Popen(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgba', '-s', '1920x1080', '-r', str(FPS),
                          '-i', '-', '-c:v', 'libx264', '-preset', 'fast', '-crf', '14', '-pix_fmt', 'yuv420p', path], stdin=subprocess.PIPE)
    last, last_f = None, None
    for f in range(f0, f1):
        fr = f - (f % 2) if twos else f
        if fr != last_f:
            last = R.frame(fr / FPS).tobytes()
            last_f = fr
        p.stdin.write(last)
    p.stdin.close()
    p.wait()
    return path


def render(story, cache, out_silent, procs, measured=None):
    tl = timeline_of(story, scenes_of(story), measured)
    nf = int(math.ceil(tl.total * FPS))
    n = max(procs * 3, 1)
    edges = [round(nf * k / n) for k in range(n + 1)]
    jobs = [(story, cache, measured, edges[k], edges[k + 1], os.path.join(cache, 'chunk%03d.mp4' % k)) for k in range(n) if edges[k + 1] > edges[k]]
    with Pool(procs) as pool:
        list(pool.imap_unordered(_render_chunk, jobs))
    lst = os.path.join(cache, 'chunks.txt')
    with open(lst, 'w') as fh:
        for j in jobs:
            fh.write("file '%s'\n" % os.path.basename(j[5]))
    subprocess.check_call(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', lst, '-c', 'copy', out_silent])
    for j in jobs:
        os.remove(j[5])
    return nf


def _still(job):
    story, cache, tg = job
    return _renderer(story, cache).frame(tg)


def preview(story, cache, out_png, procs, extra=()):
    """One sheet: the closed book's cover, then a finished still of every page (and any extra moments asked for)."""
    import skia
    sc = scenes_of(story)
    tl = timeline_of(story, sc)
    times = [0.0] + [min(p['hold_end'] - 0.15, p['g0'] + (9.0 - p['tl0'])) for p in tl.pages] + list(extra)   # the cover, then every page
    with Pool(min(procs, len(times))) as pool:
        frames = pool.map(_still, [(story, cache, t) for t in times])
    n = len(frames)
    cols = 2 if n > 1 else 1
    rows = (n + cols - 1) // cols
    tw, th, pad = 800, 450, 8
    surf = skia.Surface(cols * tw + (cols + 1) * pad, rows * th + (rows + 1) * pad)
    c = surf.getCanvas()
    c.clear(skia.Color(20, 20, 24))
    for k, arr in enumerate(frames):
        img = skia.Image.fromarray(arr, colorType=skia.kRGBA_8888_ColorType, alphaType=skia.kPremul_AlphaType)
        x, y = pad + (k % cols) * (tw + pad), pad + (k // cols) * (th + pad)
        c.drawImageRect(img, skia.Rect.MakeXYWH(x, y, tw, th), skia.SamplingOptions(skia.FilterMode.kLinear, skia.MipmapMode.kLinear))
    surf.makeImageSnapshot().save(out_png)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('story')
    ap.add_argument('--preview', action='store_true')
    ap.add_argument('--at', type=float, nargs='*', default=[], help='extra moments (seconds) to add to the preview')
    ap.add_argument('--style')
    ap.add_argument('--out')
    ap.add_argument('--procs', type=int, default=os.cpu_count() or 4)
    ap.add_argument('--silent', action='store_true', help='skip the sound')
    ap.add_argument('--no-voice', action='store_true', help='paper sounds only')
    a = ap.parse_args()
    t0 = time.time()
    story = load_story(a.story)
    if a.style:
        story['style'] = a.style
    base = os.path.splitext(os.path.abspath(a.story))[0]
    cache = os.path.join(os.path.dirname(base), '.popup-cache', '%s-%s' % (story_key(story), story['style']))
    scenes = scenes_of(story)
    warns = [w for i, sc in enumerate(scenes) for w in ['page %d: %s' % (i + 1, x) for x in sc.warnings]]
    tl = timeline_of(story, scenes)
    for w in warns[:12]:
        print('CHECK ' + w)
    fitted = [x for sc in scenes for x in sc.fitted]
    if fitted:
        print('FITTED %d piece%s nudged to stay on the sheet (nothing to do)' % (len(fitted), '' if len(fitted) == 1 else 's'))
    textures(story, cache, a.procs)
    if a.preview:
        out = a.out or base + '-preview.png'
        preview(story, cache, out, a.procs, a.at)
        print('preview %s  (%d pages, about %.0f s of video, %d things to check, %.0f s)' % (out, len(scenes), tl.total, len(warns), time.time() - t0))
        return
    out = a.out or base + '.mp4'
    silent = os.path.join(cache, 'silent.mp4')
    voices = who = measured = None
    if not (a.silent or a.no_voice):
        import voice
        voices, who = voice.narrate(story, os.path.dirname(cache))          # who: e.g. 'free (af_heart)'
        if voices:
            measured = [max(1.5, len(v) / voice.SR) for v in voices]
            tl = timeline_of(story, scenes, measured)
        else:
            print('VOICE none: the video will have paper sounds only')
    nf = render(story, cache, silent, a.procs, measured)
    if a.silent:
        subprocess.check_call(['ffmpeg', '-y', '-loglevel', 'error', '-i', silent, '-c:v', 'libx264', '-preset', 'slow', '-crf', '22',
                               '-pix_fmt', 'yuv420p', '-movflags', '+faststart', out])
    else:
        import audio
        wav = os.path.join(cache, 'sound.wav')
        snd = audio.synth(tl, scenes, story)
        if voices:
            snd = voice.mix(snd, voices, tl)
        audio.write_wav(wav, snd)
        subprocess.check_call(['ffmpeg', '-y', '-loglevel', 'error', '-i', silent, '-i', wav, '-c:v', 'libx264', '-preset', 'slow', '-crf', '22', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '192k',
                               '-movflags', '+faststart', '-shortest', out])
    print('video %s  (%.1f s, %d pages, voice: %s, %.0f s to make)' % (out, nf / FPS, len(scenes), who or 'none', time.time() - t0))


if __name__ == '__main__':
    main()
