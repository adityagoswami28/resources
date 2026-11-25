"""A small tune for every video, made up on the spot.

The mood sets the feel (speed, scale, instrument). The title sets the notes (key, chords, melody),
so two topics never get the same tune. Nothing is downloaded: every note is built from sine waves."""
import hashlib
import numpy as np
from scipy import signal

SR = 48000

SCALES = dict(major=[0, 2, 4, 5, 7, 9, 11], minor=[0, 2, 3, 5, 7, 8, 10], dorian=[0, 2, 3, 5, 7, 9, 10])
# notes a melody may rest on (scale steps): the five that never clash
PENTA = dict(major=[0, 1, 2, 4, 5], minor=[0, 2, 3, 4, 6], dorian=[0, 2, 3, 4, 6])
# chord loops, as scale steps (0 = home chord)
PROGS = dict(major=[[0, 5, 3, 4], [0, 3, 5, 4], [0, 4, 5, 3], [0, 3, 0, 4]],
             minor=[[0, 5, 2, 6], [0, 5, 3, 4], [0, 3, 5, 6], [0, 6, 5, 6]],
             dorian=[[0, 3, 0, 6], [0, 2, 3, 0], [0, 3, 6, 0], [0, 6, 3, 3]])
MOODS = dict(
    gentle=dict(bpm=78, scale='major', arp='box', lead='box', grid=2, pad=1.0, lift=0),
    bright=dict(bpm=108, scale='major', arp='marimba', lead='marimba', grid=2, pad=0.6, lift=0),
    curious=dict(bpm=92, scale='dorian', arp='pluck', lead='box', grid=2, pad=0.7, lift=0),
    dreamy=dict(bpm=66, scale='major', arp='bell', lead='bell', grid=1, pad=1.6, lift=0),
    stately=dict(bpm=72, scale='minor', arp='harp', lead='harp', grid=2, pad=1.0, lift=-12))
LOOK_MOOD = {'cut-paper': 'gentle', 'risograph': 'bright', 'field-atlas': 'curious', 'night-lantern': 'dreamy',
             'gilded-engraving': 'stately'}
# an instrument is a handful of sine waves: (pitch multiple, loudness, how fast it dies away)
INST = dict(
    box=([(1, 1.0, 3.2), (2, 0.32, 5.0), (3, 0.10, 8.0), (5.4, 0.05, 14.0)], 2.2),
    marimba=([(1, 1.0, 7.0), (4, 0.20, 16.0), (9.2, 0.04, 30.0)], 1.0),
    pluck=([(k, 1.0 / k ** 1.1, 5.5 + 2.5 * k) for k in range(1, 7)], 1.0),
    bell=([(1, 1.0, 1.7), (2.0, 0.38, 2.5), (2.76, 0.16, 3.6), (4.1, 0.07, 5.0)], 3.0),
    harp=([(k, 1.0 / k ** 1.4, 2.3 + 1.1 * k) for k in range(1, 8)], 2.4))
ARPS = [[0, 2, 1, 2, 3, 2, 1, 2], [0, 1, 2, 3, 2, 1, 2, 1], [0, 2, 3, 2, 4, 2, 3, 2], [0, 1, 2, 1, 3, 1, 2, 1]]
RESTS = [[1, 1, 0, 1, 1, 0, 1, 0], [1, 0, 1, 1, 0, 1, 1, 0], [1, 1, 1, 0, 1, 0, 1, 1]]       # 'curious' leaves gaps
RHYTHMS = [[0, 1, 2, 3], [0, 1.5, 2, 3], [0, 2, 3], [0, 1.5, 3], [0, 2], [0, 1, 2.5], [1, 2, 3]]
_notes = {}


def hz(midi):
    return 440.0 * 2 ** ((midi - 69) / 12.0)


def note(inst, midi):
    key = (inst, int(midi))
    if key not in _notes:
        parts, dur = INST[inst]
        n = int(SR * dur)
        t = np.arange(n) / SR
        f = hz(midi)
        x = np.zeros(n)
        for ratio, amp, dec in parts:
            if f * ratio < 9000:
                x += amp * np.sin(2 * np.pi * f * ratio * t) * np.exp(-dec * t)
        x *= np.minimum(1.0, t / 0.004)
        k = int(SR * 0.05)
        x[-k:] *= np.linspace(1, 0, k)
        _notes[key] = x * min(1.0, (hz(72) / f) ** 0.35)          # high notes a touch softer
    return _notes[key]


def put(buf, x, t, gain, pan=0.0):
    i = int(t * SR)
    if i < 0 or i >= len(buf):
        return
    n = min(len(x), len(buf) - i)
    l, r = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
    buf[i:i + n, 0] += x[:n] * gain * l * 1.414
    buf[i:i + n, 1] += x[:n] * gain * r * 1.414


def mood_of(story):
    m = story.get('music')
    if m in ('none', False):
        return None
    if m in MOODS:
        return m
    return LOOK_MOOD.get(story.get('style'), 'gentle')


def synth(story, total, t_first=0.35, t_last=None):
    """-> stereo float array, `total` seconds long, or None for no music.
    t_last: when the book starts to close; the tune comes home to its last chord there."""
    mood = mood_of(story)
    if mood is None:
        return None
    m = MOODS[mood]
    seed = int(hashlib.sha1(('%s|%s' % (story.get('title', ''), mood)).encode()).hexdigest()[:8], 16)
    rng = np.random.default_rng(seed)
    N = int(total * SR)
    buf = np.zeros((N, 2))
    t_last = min(t_last if t_last is not None else total - 2.0, total - 0.8)
    # the bars are stretched a hair so that the last one ends exactly as the book closes
    bar = 4 * 60.0 / m['bpm']
    nbars = max(2, int(round((t_last - t_first) / bar)))
    bar = (t_last - t_first) / nbars
    beat = bar / 4
    root = 48 + int(rng.choice([0, 2, 3, 5, 7, 9, 10]))                        # the key
    sc, penta = SCALES[m['scale']], PENTA[m['scale']]
    prog = PROGS[m['scale']][int(rng.integers(4))]
    arp = ARPS[int(rng.integers(len(ARPS)))]
    rests = RESTS[int(rng.integers(len(RESTS)))] if mood == 'curious' else [1] * 8

    def deg(d, octave=0):
        return root + 12 * octave + sc[d % 7] + 12 * (d // 7)

    def chord_of(b):
        if b == nbars - 1 and nbars > 2:
            c = 4 if m['scale'] == 'major' else 6          # the bar before the end leans toward home
        else:
            c = prog[b % 4]
        return c - 7 if c >= 4 else c                      # keep the chords close together

    # ---- a melody: four bars, then again with a new ending, then something new, then home
    def phrase(r):
        out, pos = [], 7 + int(r.choice([0, 2, 4]))
        for b in range(4):
            c = prog[b]
            for k, on in enumerate(RHYTHMS[int(r.integers(len(RHYTHMS)))]):
                if k == 0:                                 # the first note of a bar belongs to its chord
                    tones = [c + j + 7 * o for j in (0, 2, 4) for o in (0, 1, 2)]
                    pos = min(tones, key=lambda d: (abs(d - pos), d))
                else:
                    step = int(r.choice([-2, -1, -1, 1, 1, 2]))
                    if pos > 12:
                        step = -abs(step)
                    if pos < 5:
                        step = abs(step)
                    pos += step
                    while pos % 7 not in penta:
                        pos += 1 if step > 0 else -1
                out.append((b, on, pos))
        return out
    A = phrase(np.random.default_rng(seed + 1))
    B = phrase(np.random.default_rng(seed + 2))
    A2 = [x for x in A if x[0] < 3] + [x for x in phrase(np.random.default_rng(seed + 3)) if x[0] == 3]
    form = [A, A2, B, A]

    lead_oct = 1 + m['lift'] // 12
    step_len = bar / (4 * m['grid'])
    for b in range(nbars):
        t0 = t_first + b * bar
        c = chord_of(b)
        tones = [c, c + 2, c + 4, c + 7, c + 9]
        # bass
        bass = deg(c, -1)
        put(buf, note('harp', bass), t0, 0.07)
        put(buf, note('box', bass + 12), t0, 0.018)
        if mood == 'bright':
            put(buf, note('harp', deg(c + 4, -1)), t0 + 2 * beat, 0.05)
        # broken chord
        for k in range(4 * m['grid']):
            idx = arp[(k * (2 // m['grid'])) % 8]
            if not rests[(k * (2 // m['grid'])) % 8]:
                continue
            g = 0.05 * (1.25 if k % (2 * m['grid']) == 0 else 0.85 if k % m['grid'] == 0 else 0.65)
            put(buf, note(m['arp'], deg(tones[idx], 1 + m['lift'] // 12)), t0 + k * step_len, g, 0.28 * (1 if k % 2 else -1))
        # melody (waits one bar, so the tune has an opening)
        if b >= 1:
            for (pb, on, pos) in form[(b // 4) % 4]:
                if pb == b % 4:
                    if b == nbars - 1 and on == 0 and nbars > 2:           # the ending bar has its own chord: start on it
                        pos = min([c + j + 7 * o for j in (0, 2, 4) for o in (1, 2)], key=lambda d: abs(d - pos))
                    put(buf, note(m['lead'], deg(pos, lead_oct)), t0 + on * beat, 0.075, 0.1)
    # ---- soft held chords under it all
    tt = np.arange(N) / SR
    pad = np.zeros((N, 2))
    for b in range(nbars + 1):
        t0 = t_first + b * bar
        c = chord_of(b) if b < nbars else 0
        i0, i1 = max(int((t0 - 0.5) * SR), 0), min(int((t0 + bar + 0.6) * SR), N)
        if i1 <= i0:
            continue
        t = tt[i0:i1] - t0
        end = bar if b < nbars else (total - t0)
        env = np.clip((t + 0.5) / 0.9, 0, 1) * np.clip((end + 0.6 - t) / 1.1, 0, 1)
        for d in (c, c + 2, c + 4):
            f = hz(deg(d, 1 + m['lift'] // 12))
            for ch, det in ((0, 0.9985), (1, 1.0015)):
                pad[i0:i1, ch] += (np.sin(2 * np.pi * f * det * t) + 0.18 * np.sin(4 * np.pi * f * det * t)) * env
    buf += pad * 0.007 * m['pad']
    # ---- the last chord, rolled upward as the cover comes down
    for k, d in enumerate((0, 2, 4, 7, 9)):
        put(buf, note(m['lead'], deg(d, 1 + m['lift'] // 12)), t_last + 0.085 * k, 0.07 * (1 - 0.08 * k), 0.2 * (k - 2) / 2)
    put(buf, note('harp', deg(0, -1)), t_last, 0.085)
    # ---- a little air around the notes, then set the level
    n = int(SR * 1.3)
    r2 = np.random.default_rng(5)
    ir = r2.standard_normal((n, 2)) * np.exp(-np.arange(n) / SR * 3.4)[:, None]
    ir[:int(SR * 0.012)] = 0
    sos = signal.butter(2, [300, 4200], btype='band', fs=SR, output='sos')
    wet = np.stack([signal.sosfilt(sos, signal.fftconvolve(buf[:, c], ir[:, c])[:N]) for c in range(2)], 1)
    wet *= 0.22 * np.sqrt((buf ** 2).mean() / max((wet ** 2).mean(), 1e-12))
    buf = buf + wet
    body = buf[int(t_first * SR):int(t_last * SR)]
    buf *= 0.024 / max(np.sqrt((body ** 2).mean()), 1e-9)
    k = int(SR * 0.9)
    buf[-k:] *= np.linspace(1, 0, k)[:, None] ** 1.5
    return buf
