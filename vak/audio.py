"""AUDIO module: recording -> tonic, optional pitch correction, chanted segments aligned to units,
and per-word timings. (Generated recitation comes from the TTS adapter; see adapters.py.)"""
import numpy as np, soundfile as sf
from .util import ffmpeg, log, key


def load_mono(path, sr, out):
    ffmpeg("-i", path, "-ac", 1, "-ar", sr, out)
    x, _ = sf.read(out)
    return x


def tonic(x, sr):
    """Most common sung note (Hz), from autocorrelation pitch over voiced frames."""
    N, H, f0 = 2048, 512, []
    for i in range(0, len(x) - N, H):
        fr = x[i:i + N] * np.hanning(N)
        if np.sqrt((fr ** 2).mean()) < 0.01: continue
        ac = np.correlate(fr, fr, "full")[N - 1:]; ac /= ac[0] + 1e-12
        lo, hi = int(sr / 400), int(sr / 75); k = lo + np.argmax(ac[lo:hi])
        if ac[k] > 0.5: f0.append(sr / k)
    if not f0: return 146.83
    midi = np.round(12 * np.log2(np.array(f0) / 440) + 69).astype(int)
    m = np.bincount(midi).argmax()
    return float(440 * 2 ** ((m - 69) / 12))


def segments(x, sr, min_sil=0.6, min_seg=0.2):
    """Chanted phrases separated by pauses: [[start, end], ...] in seconds."""
    hop = int(sr * 0.02)
    rms = np.sqrt(np.convolve(x ** 2, np.ones(hop) / hop, "same")[::hop] + 1e-12)
    db = 20 * np.log10(rms)
    on = db > db.max() - 18
    segs, start, quiet = [], None, 0
    for i, v in enumerate(on):
        t = i * 0.02
        if v:
            if start is None: start = t
            quiet = 0
        elif start is not None:
            quiet += 0.02
            if quiet >= min_sil:
                end = t - quiet + 0.02
                if end - start >= min_seg: segs.append([round(start, 3), round(end, 3)])
                start, quiet = None, 0
    if start is not None: segs.append([round(start, 3), round(len(on) * 0.02, 3)])
    return segs


def align(segs, units):
    """Make the number of audio segments equal to the number of units: merge the closest pauses
    when there are too many segments, split the longest segment by syllables when too few."""
    segs = [list(s) for s in segs]
    while len(segs) > len(units):
        gaps = [segs[i + 1][0] - segs[i][1] for i in range(len(segs) - 1)]
        i = int(np.argmin(gaps)); segs[i] = [segs[i][0], segs[i + 1][1]]; del segs[i + 1]
    while len(segs) < len(units):
        i = int(np.argmax([b - a for a, b in segs])); a, b = segs[i]
        segs[i:i + 1] = [[a, (a + b) / 2], [(a + b) / 2, b]]
    for u, (a, b) in zip(units, segs):
        u["start"], u["end"] = round(a, 3), round(b, 3)
        tot, t = sum(w["syl"] for w in u["words"]), a
        for w in u["words"]:
            d = (b - a) * w["syl"] / tot
            w["start"], w["end"] = round(t, 3), round(t + d, 3); t += d
    return units


def autotune(src, dst, tonic_hz, strength=0.85, retune_ms=60):
    """Gentle pitch correction toward the nearest note of a scale built on the tonic (WORLD vocoder)."""
    import pyworld as pw
    from scipy.ndimage import uniform_filter1d
    x, sr = sf.read(src); x = (x.mean(1) if x.ndim > 1 else x).astype(np.float64)
    f0, t = pw.harvest(x, sr, f0_floor=70, f0_ceil=400, frame_period=5.0)
    sp, ap = pw.cheaptrick(x, f0, t, sr), pw.d4c(x, f0, t, sr)
    scale = np.array([-1, 0, 2, 4, 7, 9]); notes = np.concatenate([scale + 12 * o for o in (-2, -1, 0, 1)])
    v = f0 > 0; semi = np.zeros_like(f0); semi[v] = 12 * np.log2(f0[v] / tonic_hz)
    tgt = semi.copy(); tgt[v] = notes[np.abs(semi[v][:, None] - notes[None]).argmin(1)]
    corr = uniform_filter1d(np.where(v, tgt - semi, 0.0), max(1, int(retune_ms / 5)))
    f0n = np.where(v, tonic_hz * 2 ** ((semi + strength * corr) / 12), 0.0)
    y = pw.synthesize(f0n, sp, ap, sr, frame_period=5.0)
    y = np.pad(y, (0, max(0, len(x) - len(y))))[:len(x)]
    y *= np.abs(x).max() / max(1e-9, np.abs(y).max())
    sf.write(dst, y.astype(np.float32), sr)


def run(sb, rec, cache, tune=True, manual=None):
    """manual: optional [[start, end] or [start, end, {"first_word_until": t}], ...] per unit, in seconds of
    the recording, for tracks where lines run together (music under the voice, no pauses)."""
    wav, _ = cache.get_or_make("audio48", key(rec), ".wav", lambda o: ffmpeg("-i", rec, "-ac", 1, "-ar", 48000, o))
    x, sr = sf.read(wav)
    ana = cache.path("audio22", key(rec), ".wav"); y = load_mono(rec, 22050, ana)
    f0 = tonic(y, 22050)
    if manual:
        segs = [[m[0], m[1]] for m in manual]
        log(f"audio: tonic {f0:.1f} Hz, {len(segs)} line timings from the project for {len(sb['units'])} units")
    else:
        segs = segments(x, sr)
        log(f"audio: tonic {f0:.1f} Hz, {len(segs)} chanted segments for {len(sb['units'])} units")
    align(segs, sb["units"])
    for u, m in zip(sb["units"], manual or []):          # exact word times from the source (e.g. ElevenLabs Music timestamps)
        wt = m[2].get("words") if len(m) > 2 else None
        if wt and len(wt) == len(u["words"]):
            for w, (a, b) in zip(u["words"], wt):
                w["start"], w["end"] = round(a, 3), round(b, 3)
    for u, m in zip(sb["units"], manual or []):          # a held first word (e.g. a long Om) keeps its own span
        hold = m[2].get("first_word_until") if len(m) > 2 else None
        if hold and len(u["words"]) > 1:
            ws = u["words"]; ws[0]["end"] = hold; rest = sum(w["syl"] for w in ws[1:]); t = hold
            for w in ws[1:]:
                d = (u["end"] - hold) * w["syl"] / rest; w["start"], w["end"] = round(t, 3), round(t + d, 3); t += d
    voice = wav
    if tune:
        voice, hit = cache.get_or_make("autotune", key(wav, round(f0, 2), 0.85, 60), ".wav", lambda o: autotune(wav, o, f0))
        log("audio: pitch correction " + ("(cached)" if hit else "applied"))
    sb["audio"] = {"path": rec, "voice": voice, "duration": round(len(x) / sr, 3), "tonic_hz": round(f0, 2), "segments": segs}
    return sb
