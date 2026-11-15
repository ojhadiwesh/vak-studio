"""NARRATION module: voice the story lines offline (Windows OneCore voice, e.g. "Ravi", en-IN) and lay them
out with pauses. Returns one narration track plus each line's start/end, so scenes and subtitles can be
anchored to "line n". A recorded narration can replace the voice later: same line timings, new audio."""
import json, os, subprocess
from xml.sax.saxutils import escape
from .util import ASSETS, duration, ffmpeg, key, log


def _voice_line(cache, text, voice, rate, pitch):
    ssml = (f'<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="en-IN">'
            f'<prosody rate="{rate}" pitch="{pitch}">{escape(text)}</prosody></speak>')

    def make(out):
        x = out + ".xml"
        open(x, "w", encoding="utf-8").write(ssml)
        r = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
                            os.path.join(ASSETS, "tts_windows.ps1"), x, out, voice], capture_output=True, text=True)
        os.remove(x)
        if r.returncode != 0 or not os.path.exists(out):
            raise RuntimeError(f"narration voice failed: {r.stderr[-800:]}")
    p, _ = cache.get_or_make("tts", key(ssml, voice), ".wav", make)
    return p


def _piper_line(cache, text, model, length_scale, noise):
    """Piper: open-source neural voice, fully offline once the model (.onnx + .onnx.json) is on disk."""
    def make(out):
        import sys
        r = subprocess.run([sys.executable, "-m", "piper", "-m", model, "-f", out, "--length-scale", str(length_scale),
                            "--noise-scale", str(noise), "--sentence-silence", "0.35"], input=text, capture_output=True, text=True, encoding="utf-8")
        if r.returncode != 0 or not os.path.exists(out):
            raise RuntimeError(f"piper failed: {r.stderr[-800:]}")
    p, _ = cache.get_or_make("piper", key(text, model, length_scale, noise), ".wav", make)
    return p


def _edge_line(cache, text, voice, rate, pitch):
    """Microsoft neural voice via edge-tts (free; the line's text is sent to Microsoft's speech service)."""
    def make(out):
        import sys
        import time
        mp3 = out + ".mp3"
        for attempt in range(4):                  # the free service drops a request now and then: retry
            r = subprocess.run([sys.executable, "-m", "edge_tts", "--voice", voice, f"--rate={rate}", f"--pitch={pitch}",
                                "--text", text, "--write-media", mp3], capture_output=True, text=True, encoding="utf-8")
            if r.returncode == 0 and os.path.exists(mp3) and os.path.getsize(mp3) > 0:
                break
            time.sleep(2 + 3 * attempt)
        if r.returncode != 0 or not os.path.exists(mp3):
            raise RuntimeError(f"edge-tts failed: {r.stderr[-800:]}")
        ffmpeg("-i", mp3, "-ar", 48000, "-ac", 1, out); os.remove(mp3)
    p, _ = cache.get_or_make("edge", key(text, voice, rate, pitch), ".wav", make)
    return p


def run(cache, cfg, lead=0.0, rel=lambda p: p):
    """Voice every line; returns (narration.wav at 48 kHz, [{text, start, end}], total seconds).
    cfg["engine"]: "eleven" (ElevenLabs; voice id in cfg["eleven_voice"] or ELEVENLABS_NARRATOR_VOICE_ID), "edge",
    "piper" (model path in cfg["model"]) or "windows" (OneCore voice name in cfg["voice"]).
    VAK_NARRATOR=eleven switches every narrated film to ElevenLabs without editing the projects."""
    from . import eleven
    engine = os.environ.get("VAK_NARRATOR") or cfg.get("engine", "windows")
    if engine == "eleven" and not eleven.available():
        log("narrate: ELEVENLABS_API_KEY not set, falling back to the project's own voice")
        engine = cfg.get("engine", "windows") if cfg.get("engine") != "eleven" else "edge"
    voice, rate, pitch = cfg.get("voice", "Ravi"), cfg.get("rate", "-6%"), cfg.get("pitch", "-3%")
    if engine == "edge" and voice == "Ravi":
        voice = "en-IN-PrabhatNeural"
    texts = [ln.get("tts", ln["text"]) for ln in cfg["lines"]]
    if engine == "eleven":
        e_voice = cfg.get("eleven_voice") or os.environ.get("ELEVENLABS_NARRATOR_VOICE_ID") or eleven.NARRATOR_VOICE
        e_model = cfg.get("eleven_model") or os.environ.get("ELEVENLABS_NARRATOR_MODEL") or eleven.DEFAULT_MODEL
        e_set = eleven.voice_settings(e_model, cfg.get("stability", 0.55), style=0.25, speed=cfg.get("speed", 0.95))
        voice = f"ElevenLabs {e_voice}"
    clips, timings, t = [], [], lead
    for i, ln in enumerate(cfg["lines"]):
        txt = texts[i]
        if engine == "eleven":                  # neighbouring lines passed along so the voice stays even across lines
            p = eleven.speak(cache, txt, e_voice, e_model, e_set, previous_text=texts[i - 1] if i else None,
                             next_text=texts[i + 1] if i + 1 < len(texts) else None, tag="eleven_narr")
        elif engine == "edge":
            p = _edge_line(cache, txt, voice, rate, cfg.get("pitch", "+0Hz"))
        elif engine == "piper":
            p = _piper_line(cache, txt, rel(cfg["model"]), cfg.get("length_scale", 1.12), cfg.get("noise_scale", 0.6))
            voice = os.path.basename(cfg["model"]).replace(".onnx", "")
        else:
            p = _voice_line(cache, txt, voice, rate, pitch)
        d = duration(p)
        clips.append((p, t))
        timings.append({"text": ln["text"], "start": round(t, 3), "end": round(t + d, 3)})
        t += d + ln.get("pause", cfg.get("gap", 0.6))
    total = round(t, 3)

    def make(out):
        args, fc = [], []
        for i, (p, st) in enumerate(clips):
            args += ["-i", p]
            fc.append(f"[{i}:a]aresample=48000,adelay={int(st * 1000)}|{int(st * 1000)}[a{i}]")
        fc.append("".join(f"[a{i}]" for i in range(len(clips))) + f"amix=inputs={len(clips)}:normalize=0,atrim=0:{total},"
                  "highpass=f=70,acompressor=threshold=-24dB:ratio=2.5:attack=8:release=180[o]")
        ffmpeg(*args, "-filter_complex", ";".join(fc), "-map", "[o]", "-ac", 2, "-ar", 48000, out)
    wav, hit = cache.get_or_make("narration", key([c[0] for c in clips], [c[1] for c in clips], total), ".wav", make)
    log(f"narrate: {len(timings)} lines, {total:.1f}s with voice '{voice}' {'(cached)' if hit else ''}")
    return wav, timings, total
