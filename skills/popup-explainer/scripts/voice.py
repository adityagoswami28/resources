"""Narration for the pop-up film.

Free by default: the open Kokoro voice, run on this machine (first use downloads about 120 MB of voice files).
Premium when set up: if ELEVENLABS_API_KEY is in the environment, ElevenLabs speaks instead.
Fallbacks: the Mac's built-in `say`, then no voice (the film still renders, with page timing estimated).

Only the narration text ever leaves the machine, and only when the premium voice is used.
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.request

import numpy as np
from scipy import signal

SR = 48000
MODEL_URL = 'https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/'
MODEL_FILES = ('kokoro-v1.0.int8.onnx', 'voices-v1.0.bin')
FREE_VOICE = 'af_heart'
PREMIUM_VOICE = '21m00Tcm4TlvDq8ikWAM'
_kokoro = None


def _say(msg):
    print('VOICE ' + msg)
    sys.stdout.flush()


def model_dir():
    return os.environ.get('POPUP_VOICE_DIR') or os.path.join(os.path.expanduser('~'), '.cache', 'popup-explainer', 'voice')


def _fetch_models():
    d = model_dir()
    os.makedirs(d, exist_ok=True)
    for f in MODEL_FILES:
        p = os.path.join(d, f)
        if os.path.exists(p) and os.path.getsize(p) > 1_000_000:
            continue
        _say('downloading %s (one time)' % f)
        tmp = p + '.part'
        with urllib.request.urlopen(MODEL_URL + f, timeout=120) as r, open(tmp, 'wb') as fh:
            shutil.copyfileobj(r, fh, 1 << 20)
        os.replace(tmp, p)
    return [os.path.join(d, f) for f in MODEL_FILES]


def _decode(path):
    """Any audio file -> mono float array at SR, using ffmpeg."""
    raw = subprocess.run(['ffmpeg', '-loglevel', 'error', '-i', path, '-f', 'f32le', '-ac', '1', '-ar', str(SR), '-'],
                         check=True, capture_output=True).stdout
    return np.frombuffer(raw, np.float32).astype(np.float64)


def _free(text, name, speed):
    global _kokoro
    from kokoro_onnx import Kokoro
    if _kokoro is None:
        m, v = _fetch_models()
        _kokoro = Kokoro(m, v)
    x, sr = _kokoro.create(text, voice=name or FREE_VOICE, speed=speed, lang='en-gb' if (name or '').startswith('b') else 'en-us')
    return signal.resample_poly(np.asarray(x, np.float64), SR, sr)


def _premium(text, name, speed):
    key = os.environ['ELEVENLABS_API_KEY']
    body = json.dumps(dict(text=text, model_id='eleven_multilingual_v2', voice_settings=dict(speed=float(np.clip(speed, 0.7, 1.2))))).encode()
    req = urllib.request.Request('https://api.elevenlabs.io/v1/text-to-speech/%s?output_format=mp3_44100_128' % (name or PREMIUM_VOICE),
                                 data=body, headers={'xi-api-key': key, 'Content-Type': 'application/json', 'Accept': 'audio/mpeg'})
    with urllib.request.urlopen(req, timeout=120) as r, tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as fh:
        shutil.copyfileobj(r, fh)
    try:
        return _decode(fh.name)
    finally:
        os.remove(fh.name)


def _mac(text, name, speed):
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, 'v.aiff')
        cmd = ['say', '-o', p, '-r', str(int(175 * speed))]
        if name:
            cmd += ['-v', name]
        subprocess.run(cmd + [text], check=True)
        return _decode(p)


def _tidy(x):
    """Trim silence at both ends, even out the level, soften the edges."""
    if len(x) == 0:
        return x
    env = np.abs(signal.sosfiltfilt(signal.butter(2, 20, 'low', fs=SR, output='sos'), np.abs(x)))
    loud = np.nonzero(env > max(env.max() * 0.03, 1e-4))[0]
    if len(loud) == 0:
        return np.zeros(0)
    a, b = max(loud[0] - int(0.03 * SR), 0), min(loud[-1] + int(0.12 * SR), len(x))
    x = x[a:b].copy()
    rms = np.sqrt(np.mean(x[np.abs(x) > 0.01] ** 2)) if np.any(np.abs(x) > 0.01) else 1.0
    x *= 0.11 / max(rms, 1e-6)
    x = np.tanh(x * 1.4) / 1.4
    n = min(int(0.02 * SR), len(x) // 2)
    x[:n] *= np.linspace(0, 1, n)
    x[-n:] *= np.linspace(1, 0, n)
    return x


def providers(want=None):
    """Order to try. want: 'premium', 'free', 'mac', 'none' or None (best available)."""
    if want == 'none':
        return []
    order = []
    if os.environ.get('ELEVENLABS_API_KEY') and want in (None, 'premium'):
        order.append(('premium', _premium))
    if want in (None, 'premium', 'free'):
        order.append(('free', _free))
    if shutil.which('say'):
        order.append(('mac', _mac))
    return order


def narrate(story, cache):
    """-> (list of mono arrays at SR, one per page; the voice used, e.g. 'free (af_heart)', or None)."""
    opt = story.get('voice') or {}
    if isinstance(opt, str):
        opt = {'provider': opt}
    texts = [(p.get('say') or '').strip() for p in story['pages']]
    order = providers(opt.get('provider'))
    if not order or not any(texts):
        return None, None
    vdir = os.path.join(cache, 'voice')
    os.makedirs(vdir, exist_ok=True)
    speed = float(opt.get('speed', 1.0))
    for k, (pname, fn) in enumerate(order):
        name = opt.get('name') if k == 0 else None       # a named voice belongs to the first choice only
        out = []
        try:
            for t in texts:
                if not t:
                    out.append(np.zeros(0))
                    continue
                key = hashlib.sha1(json.dumps([pname, name, speed, t]).encode()).hexdigest()[:16]
                f = os.path.join(vdir, key + '.npy')
                if os.path.exists(f):
                    out.append(np.load(f))
                    continue
                x = _tidy(fn(t, name, speed))
                np.save(f, x.astype(np.float32))
                out.append(x)
            return out, '%s (%s)' % (pname, name or dict(free=FREE_VOICE, premium=PREMIUM_VOICE, mac='system voice')[pname])
        except Exception as e:                            # try the next voice down
            _say('%s voice not available (%s: %s)' % (pname, type(e).__name__, str(e)[:120]))
    return None, None


def mix(foley, voices, tl):
    """Lay the narration over the paper sounds, turning the sounds down while the voice speaks."""
    n = len(foley)
    v = np.zeros(n)
    for p, x in zip(tl.pages, voices):
        i = int(p['say'] * SR)
        m = min(len(x), n - i)
        if m > 0:
            v[i:i + m] += x[:m]
    act = (np.abs(v) > 1e-3).astype(np.float64)
    k = int(0.35 * SR)
    act = np.minimum(1.0, np.convolve(act, np.ones(k) / k * 4.0, 'same'))
    act = signal.sosfiltfilt(signal.butter(1, 3.0, 'low', fs=SR, output='sos'), act)
    duck = 1.0 - 0.62 * np.clip(act, 0, 1)
    out = foley * duck[:, None] * 0.9 + v[:, None] * 1.9
    peak = np.abs(out).max()
    return out * (0.97 / peak) if peak > 0.97 else out
