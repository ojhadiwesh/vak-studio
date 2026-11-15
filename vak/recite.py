"""RECITE: a neural voice recites the chant when no recording is given (a draft until a person records it).

Each unit is voiced separately (Microsoft hi-IN neural voice via edge-tts reads Devanagari; the text is sent to
Microsoft's speech service), joined with pauses, and the exact line timings are returned as the project's manual
`segments`, so alignment needs no guessing. Pronunciation of Sanskrit by a Hindi voice is approximate: a teacher
must review it, and a real recording should replace it before public use."""
import os
from . import narrate
from .util import Cache, duration, ffmpeg, log

VOICE, RATE, GAP, LEAD = "hi-IN-MadhurNeural", "-22%", 0.9, 0.6


def run(units, out_wav, cache_dir, voice=VOICE, rate=RATE):
    """Write out_wav (48 kHz mono) and return segments [[start, end], ...] per unit."""
    cache = Cache(cache_dir)
    clips, segs, t = [], [], LEAD
    for u in units:
        p = narrate._edge_line(cache, u["devanagari"], voice, rate, "+0Hz")
        d = duration(p)
        clips.append((p, t)); segs.append([round(t, 3), round(t + d, 3)])
        t += d + (GAP * 1.6 if u.get("kind") != "verse" or u is units[-1] else GAP)
    total = t + 0.4
    args, fc = [], []
    for i, (p, st) in enumerate(clips):
        args += ["-i", p]; fc.append(f"[{i}:a]aresample=48000,adelay={int(st * 1000)}|{int(st * 1000)}[a{i}]")
    fc.append("".join(f"[a{i}]" for i in range(len(clips))) + f"amix=inputs={len(clips)}:normalize=0,atrim=0:{total:.3f}[o]")
    os.makedirs(os.path.dirname(os.path.abspath(out_wav)), exist_ok=True)
    ffmpeg(*args, "-filter_complex", ";".join(fc), "-map", "[o]", "-ac", 1, "-ar", 48000, out_wav)
    log(f"recite: {len(units)} lines voiced by {voice}, {total:.1f}s -> {out_wav}")
    return segs
