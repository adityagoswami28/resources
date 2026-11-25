"""All sound is synthesised here: the air of the place, paper rustle, board creak, lock snaps, river, and the tune (music.py)."""
import numpy as np
from scipy import signal
from render import T_OPEN0, T_OPEN1, T_LIFE, T_CLOSE, lock_time, slide_s

SR = 48000


def bp(x, lo, hi, order=2):
    sos = signal.butter(order, [lo, hi], btype='band', fs=SR, output='sos')
    return signal.sosfilt(sos, x)


def lp(x, f, order=2):
    return signal.sosfilt(signal.butter(order, f, btype='low', fs=SR, output='sos'), x)


def hp(x, f, order=2):
    return signal.sosfilt(signal.butter(order, f, btype='high', fs=SR, output='sos'), x)


def smooth_env(g, ms=25):
    n = int(SR * ms / 1000)
    return np.convolve(g, np.hanning(n) / np.hanning(n).sum(), mode='same')


def ramp(t, a, b):
    return np.clip((t - a) / (b - a), 0, 1)


def bump(t, a, b, p=1.0):
    x = np.clip((t - a) / (b - a), 0, 1)
    return np.sin(np.pi * x) ** p


def place(buf, snd, t, gain=1.0, pan=0.0):
    i = int(t * SR)
    if i < 0 or i >= buf.shape[0]:
        return
    n = min(len(snd), buf.shape[0] - i)
    l, r = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
    buf[i:i + n, 0] += snd[:n] * gain * l * 1.414
    buf[i:i + n, 1] += snd[:n] * gain * r * 1.414


def snap(rng, pitch=1.0, hard=1.0):
    """A small crisp paper snap: a click, a short papery burst and a tiny card resonance."""
    n = int(SR * 0.09)
    t = np.arange(n) / SR
    burst = bp(rng.standard_normal(n), 1800 * pitch, 7500) * np.exp(-t * 95)
    card = np.sin(2 * np.pi * 620 * pitch * t) * np.exp(-t * 70) * 0.5 + np.sin(2 * np.pi * 1480 * pitch * t) * np.exp(-t * 120) * 0.3
    click = np.zeros(n)
    click[:40] = np.hanning(80)[40:] * 1.2
    flut = bp(rng.standard_normal(n), 900, 3000) * np.exp(-t * 30) * (0.5 + 0.5 * np.sin(2 * np.pi * 55 * t)) * 0.35
    return (burst * 1.0 + card * 0.55 + hp(click, 800) + flut) * hard


def thud(rng, f=95, dur=0.22):
    n = int(SR * dur)
    t = np.arange(n) / SR
    body = np.sin(2 * np.pi * (f * (1 + 0.5 * np.exp(-t * 40))) * t) * np.exp(-t * 26)
    air = lp(rng.standard_normal(n), 900) * np.exp(-t * 34) * 0.6
    pap = bp(rng.standard_normal(n), 2000, 6000) * np.exp(-t * 60) * 0.25
    return body * 0.9 + air + pap


def chirp(rng, f0, f1, dur, vib=0.0):
    n = int(SR * dur)
    t = np.arange(n) / SR
    f = f0 + (f1 - f0) * (t / dur) + vib * np.sin(2 * np.pi * 28 * t)
    ph = 2 * np.pi * np.cumsum(f) / SR
    return np.sin(ph) * np.hanning(n) * (1 + 0.3 * np.sin(2 * ph)) * 0.5


def flutter(rng, dur=0.7, rate=13):
    n = int(SR * dur)
    t = np.arange(n) / SR
    x = bp(rng.standard_normal(n), 500, 3200) * (np.clip(np.sin(2 * np.pi * rate * t), 0, 1) ** 2) * np.hanning(n)
    return x


def grains(rng, n, density, lo=2500, hi=9000, dec=600):
    """Crackly paper texture: many tiny random ticks."""
    x = np.zeros(n)
    k = int(n / SR * density)
    idx = rng.integers(0, n, k)
    x[idx] = rng.standard_normal(k) * rng.random(k) ** 2
    ker = np.exp(-np.arange(int(SR * 0.004)) / SR * dec)
    x = signal.fftconvolve(x, ker)[:n]
    return bp(x, lo, hi)


def synth(tl, scenes, story, seed=1):
    """Paper foley and ambience that follow the film's timeline. Returns a stereo float array."""
    from styles import NAMES
    style = NAMES.get(story.get('style'), story.get('style'))
    segments = [(i, p['tl0'] * 30.0, (p['tl0'] + p['end'] - p['g0']) * 30.0) for i, p in enumerate(tl.pages)]
    relay_from = None
    rng = np.random.default_rng(seed)
    total = sum(b - a for _, a, b in segments) / 30.0
    N = int(total * SR) + SR // 2
    out = np.zeros((N, 2))
    ts = np.zeros(N)                      # style time for every sample
    seg_m0 = []
    m = 0.0
    for (st, a, b) in segments:
        i0, i1 = int(m * SR), int((m + (b - a) / 30.0) * SR)
        ts[i0:i1] = a / 30.0 + (np.arange(i1 - i0) / SR)
        seg_m0.append(m)
        m += (b - a) / 30.0
    ts[int(m * SR):] = segments[-1][2] / 30.0
    tm = np.arange(N) / SR

    # ---------------- the air of the place: 'quiet' (a room), 'birds' (outdoors by day) or 'night' (crickets and frogs)
    air_kind = story.get('air') or ('night' if story.get('style') == 'night-lantern' else 'quiet')
    for ch in range(2):
        air = lp(rng.standard_normal(N), 700) * (0.035 if air_kind == 'quiet' else 0.06) * (0.8 + 0.2 * np.sin(2 * np.pi * 0.07 * tm + ch))
        hiss = bp(rng.standard_normal(N), 2500, 6000, 1) * 0.008
        # crickets: pulsed narrow bands
        cr = np.zeros(N)
        for (f, rate, lvl, ph) in ((4300, 21.0, 0.016, 0.0), (5200, 17.5, 0.012, 1.3), (6100, 26.0, 0.008, 2.1)) if air_kind == 'night' else ():
            car = np.sin(2 * np.pi * f * tm + ch * 0.7 + ph)
            pulse = np.clip(np.sin(2 * np.pi * rate * tm + ph + ch * 0.4), 0, 1) ** 3
            swell = 0.5 + 0.5 * np.sin(2 * np.pi * (0.11 + 0.03 * ph) * tm + ph * 2 + ch)
            cr += car * pulse * swell * lvl
        out[:, ch] += air + hiss + cr
    # far-off birds and frogs
    t = 0.6 if air_kind != 'quiet' else total
    while t < total - 0.5:
        kind = rng.random() * 0.8 if air_kind == 'birds' else 0.8 + rng.random() * 0.2
        pan = rng.uniform(-0.8, 0.8)
        if kind < 0.55:
            f = rng.uniform(1800, 3400)
            for k in range(int(rng.integers(2, 5))):
                place(out, chirp(rng, f * rng.uniform(0.95, 1.1), f * rng.uniform(1.1, 1.5), rng.uniform(0.06, 0.12), 60), t + k * rng.uniform(0.11, 0.16), 0.05, pan)
        elif kind < 0.8:
            place(out, chirp(rng, rng.uniform(900, 1300), rng.uniform(700, 900), rng.uniform(0.25, 0.4), 25), t, 0.045, pan)
        else:
            for k in range(3):
                place(out, chirp(rng, 420, 300, 0.07), t + k * 0.19, 0.035, pan)
        t += rng.uniform(1.1, 2.6) * (1.0 if air_kind == 'birds' else 1.8)

    # ---------------- continuous foley driven by the animation time
    # board opening: soft whoosh and unfolding crackle
    g = bump(ts, T_OPEN0, T_OPEN1 + 0.1, 0.7) * (ts > T_OPEN0) * (ts < T_OPEN1 + 0.1)
    g2 = ramp(ts, 3.5, 4.45) * (ts < 4.6) * (ts > 3.5)
    g, g2 = smooth_env(g), smooth_env(g2)
    for ch in range(2):
        who = bp(rng.standard_normal(N), 180, 1100) * 0.05
        out[:, ch] += who * g + grains(rng, N, 1500, 1800, 8000) * 0.10 * g2 ** 2 + bp(rng.standard_normal(N), 2000, 7000) * 0.02 * g2
    # which page each sample belongs to
    page_of = np.zeros(N, int)
    for k, m0 in enumerate(seg_m0):
        page_of[int(m0 * SR):] = k
    wet_page = np.array([1.0 if any(scenes[k].pcs[nm].flows for nm in scenes[k].order + ['map']) else 0.0 for k in range(len(scenes))])
    # river and falls once life switches on (only on pages that have running water)
    g = smooth_env(ramp(ts, T_LIFE, T_LIFE + 1.2) * wet_page[page_of], 60)
    for ch in range(2):
        w = bp(rng.standard_normal(N), 350, 2600) * (0.6 + 0.4 * lp(rng.standard_normal(N), 9) * 6)
        w2 = bp(rng.standard_normal(N), 2500, 8000, 1) * 0.25
        out[:, ch] += (w * 0.05 + w2 * 0.035) * g
    # pull-tab sliding
    sp = np.zeros(N)
    for k, p in enumerate(tl.pages):
        if scenes[k].slider:
            grid = np.linspace(0, 30.0, 6001)
            cs = np.array([slide_s(x, p['tl_end']) for x in grid])
            sp += np.interp(ts, grid, np.gradient(cs, 0.005)) * (page_of == k)
    g = smooth_env(np.clip(sp / (np.abs(sp).max() + 1e-6), 0, 1), 60)
    slide_g = g
    # a page turning over to the next: paper rustle on top of the opening whoosh (every page after the first)
    g = bump(ts, T_OPEN0 - 0.05, T_OPEN1, 0.8) * (ts < T_OPEN1) * (page_of > 0)
    if g.max() > 0:
        g = smooth_env(g)
        for ch in range(2):
            body = bp(rng.standard_normal(N), 1400, 8500) * (0.35 + 0.65 * smooth_env(rng.random(N) ** 6 * 3, 8))
            out[:, ch] += (body * 0.07 + grains(rng, N, 800) * 0.10 + lp(rng.standard_normal(N), 450) * 0.05) * g
    # the book closing at the very end: a soft falling whoosh, then the board landing
    p = tl.pages[-1]
    i0, i1 = int(p['hold_end'] * SR), min(int((p['hold_end'] + T_CLOSE) * SR), N)
    n = i1 - i0
    if n > 0:
        env = np.hanning(n) ** 0.7
        for ch in range(2):
            out[i0:i1, ch] += bp(rng.standard_normal(n), 160, 1300) * 0.06 * env + grains(rng, n, 1100, 1800, 8000) * 0.05 * env
        place(out, thud(rng, 90, 0.24), p['hold_end'] + T_CLOSE - 0.05, 0.12, 0.3)
    g = slide_g
    for ch in range(2):
        out[:, ch] += bp(rng.standard_normal(N), 900, 3800) * 0.018 * g * (0.7 + 0.3 * np.sin(2 * np.pi * 31 * tm))

    # ---------------- one-shots, placed wherever a segment contains them
    for (st, a, b), m0 in zip(segments, seg_m0):
        t0, t1 = a / 30.0, b / 30.0

        def at(te):
            return m0 + te - t0 if t0 <= te < t1 else None
        q = at(T_OPEN1 - 0.03)
        if q is not None:
            place(out, thud(rng, 82, 0.26), q, 0.15, -0.3)
        sc = scenes[st]
        for i, nm in enumerate(sc.order[:7]):
            q = at(lock_time(i) + 0.02)
            if q is not None:
                r2 = np.random.default_rng(100 + i)
                side = sc.pcs[nm].side
                pan = -0.6 if side == 'L' else 0.6 if side == 'R' else 0.0
                place(out, snap(r2, pitch=[0.8, 0.9, 1.0, 1.12, 1.2, 1.32, 1.6][i], hard=0.6 if sc.pcs[nm].slider else 1.0), q, 0.14, pan)
        for k in range(min(5, len(sc.birds))):
            q = at(5.4 + 0.2 * k)
            if q is not None:
                r2 = np.random.default_rng(200 + k)
                place(out, flutter(r2, 0.6, 12 + k), q, 0.07, r2.uniform(-0.7, 0.7))
                place(out, chirp(r2, 2600 + 300 * k, 3400 + 200 * k, 0.09, 80), q + 0.1, 0.05, r2.uniform(-0.7, 0.7))
        if style == 2:
            for (pa, pb) in ((3.95, 4.75), (4.95, 5.75), (5.95, 6.75)):
                q = at(pa)
                if q is not None:
                    n = int(SR * (pb - pa))
                    tt = np.arange(n) / SR
                    sw = bp(np.random.default_rng(7).standard_normal(n), 700, 4200) * np.hanning(n) * (0.75 + 0.25 * np.sin(2 * np.pi * 15 * tt))
                    l = np.linspace(1, 0, n)
                    i = int(q * SR)
                    nn = min(n, N - i)
                    out[i:i + nn, 0] += sw[:nn] * 0.035 * l[:nn] * 1.4
                    out[i:i + nn, 1] += sw[:nn] * 0.035 * (1 - l[:nn]) * 1.4
    # soft taps on the relay cuts
    if relay_from is not None:
        m = seg_m0[relay_from]
        for k, (st, a, b) in enumerate(segments[relay_from:]):
            if k > 0:
                r2 = np.random.default_rng(300 + k)
                place(out, snap(r2, pitch=0.7 + 0.04 * (k % 5), hard=0.5), m, 0.09, 0.0)
            m += (b - a) / 30.0

    # ---------------- the tune
    import music
    tune = music.synth(story, total, 0.35, tl.pages[-1]['hold_end'] + 0.1)
    if tune is not None:
        out[:len(tune)] += tune

    # ---------------- a little room, then master
    n = int(SR * 0.5)
    ir = rng.standard_normal((n, 2)) * np.exp(-np.arange(n) / SR * 11)[:, None]
    ir[:int(SR * 0.008)] = 0
    wet = np.stack([signal.fftconvolve(out[:, c], ir[:, c])[:N] for c in range(2)], 1)
    wet = np.stack([lp(wet[:, c], 5000) for c in range(2)], 1)
    out = out + wet * 0.012
    out = np.stack([hp(out[:, c], 45) for c in range(2)], 1)
    n_end = int(total * SR)
    out = out[:n_end]
    fade = np.ones(n_end)
    k = int(SR * 0.5)
    fade[:k // 2] = np.linspace(0, 1, k // 2)
    fade[-k:] = np.linspace(1, 0, k)
    out *= fade[:, None]
    out = np.tanh(out * 2.4) / 2.4 * 2.2
    pk = np.abs(out).max()
    if pk > 0.95:
        out *= 0.95 / pk
    return out


def write_wav(path, x):
    import wave
    d = (np.clip(x, -1, 1) * 32767).astype('<i2')
    with wave.open(path, 'wb') as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(d.tobytes())
