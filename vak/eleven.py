"""ELEVEN: chant audio from ElevenLabs voices, with our own pronunciation layer.

Each line is generated separately (exact line timings for alignment, like vak/recite.py). The text sent to the voice
is built from the chant, not typed by hand:
  mode "devanagari"  (default) the line as written, with a Hindi language hint, voiced by an Indian devotional voice
  mode "respell"     every word respelled for an English-reading voice: knowledge/pronunciation.json first
                     (fixes found by listening, e.g. समस्ताः → "Sah-mah-staa-ha"), otherwise an automatic respelling from IAST
Uses the official SDK (pip install elevenlabs), which reads ELEVENLABS_API_KEY from the environment; vak loads it
from .env.local (vak/envfile.py). Optional: ELEVENLABS_VOICE_ID, ELEVENLABS_MODEL (default eleven_v4),
ELEVENLABS_MODE, ELEVENLABS_NARRATOR_VOICE_ID (story narration, see vak/narrate.py). The text is sent to ElevenLabs."""
import json, os, re, time
from .util import Cache, duration, ffmpeg, key, log

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PRON = os.path.join(ROOT, "knowledge", "pronunciation.json")
DEFAULT_VOICE = "ovcrTRBELQPup0RNagdO"          # Pranit, soothing devotional Hindi (Voice Library; needs a paid plan, e.g. Starter);
                                                # ELEVENLABS_VOICE_ID picks another. Chosen by listening, 2026-11-15
DEFAULT_MODEL = "eleven_v4"                     # latest, highest quality; ELEVENLABS_MODEL overrides (e.g. eleven_multilingual_v2)
NARRATOR_VOICE = "JBFqnCBsd6RMkjVDRZzb"         # George, a narrative voice; ELEVENLABS_NARRATOR_VOICE_ID picks another
GAP, LEAD = 1.0, 0.6


def available():
    return bool(os.environ.get("ELEVENLABS_API_KEY"))


def lexicon():
    try:
        return {k: v for k, v in json.load(open(PRON, encoding="utf-8")).items() if not k.startswith("_")}
    except Exception:
        return {}


VOWELS = ["ai", "au", "ā", "ī", "ū", "ṝ", "ṛ", "ḷ", "a", "i", "u", "e", "o"]
CONS = ["kh", "gh", "ch", "jh", "ṭh", "ḍh", "th", "dh", "ph", "bh", "k", "g", "ṅ", "c", "j", "ñ", "ṭ", "ḍ", "ṇ", "t", "d", "n",
        "p", "b", "m", "y", "r", "l", "v", "ś", "ṣ", "s", "h"]
V_OUT = {"a": "ah", "ā": "aa", "i": "i", "ī": "ee", "u": "oo", "ū": "oo", "ṛ": "ri", "ṝ": "ree", "ḷ": "li", "e": "ay", "o": "oh", "ai": "ai", "au": "ow"}
C_OUT = {"c": "ch", "ch": "chh", "ś": "sh", "ṣ": "sh", "ṭ": "t", "ṭh": "th", "ḍ": "d", "ḍh": "dh", "ṇ": "n", "ñ": "n", "ṅ": "n"}
ECHO = {"a": "ha", "ā": "ha", "i": "hi", "ī": "hi", "u": "hu", "ū": "hu", "e": "hay", "o": "ho"}


def _phones(w):
    out, i = [], 0
    while i < len(w):
        for tok in ("ṃ", "ḥ", *VOWELS, *CONS):
            if w.startswith(tok, i):
                out.append(tok); i += len(tok); break
        else:
            i += 1                                   # punctuation, apostrophes
    return out


def auto_respell(iast):
    """IAST → syllables an English-reading voice says well: "samastāḥ" → "Sah-mahs-taa-ha" (open short a, long vowels
    doubled, visarga echoed as a soft extra syllable, aspirates kept)."""
    ph = _phones(iast.lower())
    syl, cur, last_v = [], [], None
    for k, p in enumerate(ph):
        if p in VOWELS:
            cur.append(p); last_v = p
            syl.append(cur); cur = []
        elif p == "ṃ" and syl:
            syl[-1].append("m")
        elif p == "ḥ" and syl:
            syl.append(["ḥ", last_v or "a"])
        else:
            cur.append(p)
    if cur and syl:                                  # word-final consonants close the last syllable
        syl[-1].extend(cur)
    for i in range(len(syl) - 1):                    # a consonant cluster splits: first consonant closes the syllable before
        nxt = syl[i + 1]
        onset = []
        for c in nxt:                                # only the consonants before the vowel form the cluster
            if c not in CONS: break
            onset.append(c)
        if len(onset) >= 2 and syl[i][-1] in VOWELS + ["m"]:
            syl[i].append(nxt.pop(0))
    parts = []
    for s in syl:
        if s[0] == "ḥ":
            parts.append(ECHO.get(s[1], "ha")); continue
        parts.append("".join(V_OUT.get(p) or C_OUT.get(p) or p for p in s))
    word = "-".join(parts)
    return word[:1].upper() + word[1:]


def line_text(unit, mode="respell", lex=None):
    if mode == "devanagari":
        return unit["devanagari"].replace("॥", "").replace("।", "").strip() + "।"
    lex = lex if lex is not None else lexicon()
    words = [lex.get(w["dev"]) or auto_respell(w["iast"]) for w in unit["words"]]
    return " ".join(words) + "."


def _client():
    from elevenlabs import ElevenLabs
    return ElevenLabs()                              # reads ELEVENLABS_API_KEY from the environment


def voice_settings(model, stability=0.65, similarity=0.8, style=0.15, speed=None):
    """Eleven v4 takes only stability + similarity_boost; v2/v3 models also take style, speed and speaker boost."""
    s = {"stability": stability, "similarity_boost": similarity}
    if not model.startswith("eleven_v4"):
        s.update(style=style, use_speaker_boost=True)
        if speed:
            s["speed"] = speed
    return s


def speak(cache, text, voice, model, settings, language=None, previous_text=None, next_text=None, tag="eleven"):
    """One line of speech -> cached 48 kHz mono wav. previous/next text stitch neighbouring lines (no tone jumps)."""
    from elevenlabs import VoiceSettings
    from elevenlabs.core.api_error import ApiError

    def make(out):
        mp3 = out + ".mp3"
        extra = {k: v for k, v in (("language_code", language), ("previous_text", previous_text), ("next_text", next_text)) if v}
        client = _client()
        for attempt in range(5):
            try:
                audio = client.text_to_speech.convert(text=text, voice_id=voice, model_id=model, output_format="mp3_44100_128",
                                                      voice_settings=VoiceSettings(**settings), **extra)
                with open(mp3, "wb") as f:
                    for chunk in audio:
                        f.write(chunk)
                break
            except ApiError as e:
                if e.status_code in (429, 500, 502, 503) and attempt < 4:
                    time.sleep(2 + 3 * attempt); continue
                raise RuntimeError(f"ElevenLabs refused the request ({e.status_code}): {str(e.body)[:300]}")
        ffmpeg("-i", mp3, "-ar", 48000, "-ac", 1, out); os.remove(mp3)
    p, hit = cache.get_or_make(tag, key(text, voice, model, json.dumps(settings, sort_keys=True), language, previous_text, next_text), ".wav", make)
    return p


# ---------- sung chant: ElevenLabs Music (music_v2_5) ----------
SING_STYLES = ["Indian devotional Sanskrit chant", "deep calm male vocals", "tanpura drone", "bansuri flute", "soft tabla",
               "meditative", "slow tempo", "temple reverb"]
SING_NEG = ["pop", "drum kit", "electronic", "rap", "english lyrics", "choir", "fast tempo"]


def sing_plan(units, styles=None):
    """Composition plan: a short instrumental intro, one chunk per line (lyrics in Devanagari), an outro."""
    styles = styles or (os.environ.get("ELEVENLABS_SING_STYLES", "").split("|") if os.environ.get("ELEVENLABS_SING_STYLES") else SING_STYLES)
    ch = [{"text": "[Intro]\n{tanpura drone, soft bansuri}", "duration_ms": 6000, "positive_styles": styles,
           "negative_styles": SING_NEG, "context_adherence": "high"}]
    for i, u in enumerate(units):
        syl = sum(w.get("syl", 2) for w in u["words"]) or 4
        line = " ".join(w["dev"] for w in u["words"])
        ch.append({"text": f"[Chant {i + 1}]\n{line}", "duration_ms": int(min(30000, max(4000, syl * 620 + 1600))),
                   "positive_styles": ["solo chant", "sustained notes", "clear pronunciation"], "negative_styles": SING_NEG,
                   "context_adherence": "high"})
    ch.append({"text": "[Outro]\n{tanpura fades}", "duration_ms": 5000, "positive_styles": ["gentle fade out"],
               "negative_styles": SING_NEG, "context_adherence": "high"})
    return {"chunks": ch}


def sing(units, out_wav, cache_dir):
    """Sing the chant with ElevenLabs Music; write out_wav (48 kHz stereo) and return per-line segments
    [[start, end, {"words": [[s, e], ...]}], ...] from the model's word timestamps."""
    if not available():
        raise RuntimeError("ELEVENLABS_API_KEY is not set on this computer")
    cache, plan = Cache(cache_dir), sing_plan(units)
    k = key(json.dumps(plan, ensure_ascii=False, sort_keys=True)); final = cache.path("eleven_sing", k, ".wav")

    def make(out):
        r = _client().music.compose_detailed(composition_plan=plan, model_id="music_v2_5", with_timestamps=True)
        mp3 = out + ".mp3"; open(mp3, "wb").write(r.audio)
        js = r.json if isinstance(r.json, dict) else json.loads(r.json)
        json.dump(js, open(final + ".json", "w", encoding="utf-8"), ensure_ascii=False)     # timestamps beside the cached song
        ffmpeg("-i", mp3, "-ar", 48000, "-ac", 2, out); os.remove(mp3)
    p, hit = cache.get_or_make("eleven_sing", k, ".wav", make)
    meta = json.load(open(p + ".json", encoding="utf-8"))
    sung = [w for w in meta.get("words_timestamps", []) if not w["word"].startswith("{") and not w["word"].endswith("}")]
    clean = lambda s: re.sub(r"[^\u0900-\u097F]", "", s).replace("।", "").replace("॥", "")
    segs, k = [], 0
    for u in units:                                   # walk the sung words in order, matching ours one by one
        wt = []
        for w in u["words"]:
            j = k
            while j < len(sung) and clean(sung[j]["word"]) != clean(w["dev"]) and j < k + 3:
                j += 1
            if j < len(sung) and clean(sung[j]["word"]) == clean(w["dev"]):
                k = j
            if k < len(sung):
                wt.append([sung[k]["start_ms"] / 1000, max(sung[k]["end_ms"], sung[k]["start_ms"] + 200) / 1000]); k += 1
        if len(wt) == len(u["words"]):
            segs.append([round(wt[0][0], 3), round(wt[-1][1], 3), {"words": [[round(a, 3), round(b, 3)] for a, b in wt]}])
        else:                                         # timestamps missing: fall back to the plan's chunk times
            t0 = sum(c["duration_ms"] for c in plan["chunks"][:len(segs) + 1]) / 1000
            segs.append([round(t0, 3), round(t0 + plan["chunks"][len(segs) + 1]["duration_ms"] / 1000 - .5, 3)])
    os.makedirs(os.path.dirname(os.path.abspath(out_wav)), exist_ok=True)
    ffmpeg("-i", p, "-c:a", "pcm_s16le", out_wav)
    log(f"eleven: sung by ElevenLabs Music {'(cached)' if hit else ''}, {len(sung)} words timed, {duration(out_wav):.1f}s -> {out_wav}")
    return segs


def run(units, out_wav, cache_dir, mode=None, voice=None, model=None, speed=0.85, stability=0.65):
    """Voice every line with ElevenLabs; write out_wav (48 kHz mono) and return [[start, end], ...] per unit."""
    if not available():
        raise RuntimeError("ELEVENLABS_API_KEY is not set on this computer")
    cache = Cache(cache_dir)
    mode = mode or os.environ.get("ELEVENLABS_MODE", "devanagari")
    voice = voice or os.environ.get("ELEVENLABS_VOICE_ID") or DEFAULT_VOICE
    model = model or os.environ.get("ELEVENLABS_MODEL", DEFAULT_MODEL)
    settings = voice_settings(model, stability, speed=speed)
    lex = lexicon()
    clips, segs, t = [], [], LEAD
    for u in units:
        txt = line_text(u, mode, lex)
        p = speak(cache, txt, voice, model, settings, language="hi" if mode == "devanagari" else None)
        d = duration(p)
        clips.append((p, t)); segs.append([round(t, 3), round(t + d, 3)])
        log(f"eleven: {u['devanagari']}  ←  \"{txt}\" ({d:.1f}s)")
        t += d + GAP
    total = t + 0.4
    args, fc = [], []
    for i, (p, st) in enumerate(clips):
        args += ["-i", p]; fc.append(f"[{i}:a]aresample=48000,adelay={int(st * 1000)}|{int(st * 1000)}[a{i}]")
    fc.append("".join(f"[a{i}]" for i in range(len(clips))) + f"amix=inputs={len(clips)}:normalize=0,apad,atrim=0:{total:.3f}[o]")
    os.makedirs(os.path.dirname(os.path.abspath(out_wav)), exist_ok=True)
    ffmpeg(*args, "-filter_complex", ";".join(fc), "-map", "[o]", "-ac", 1, "-ar", 48000, out_wav)
    log(f"eleven: {len(units)} lines voiced ({mode}, model {model}), {total:.1f}s -> {out_wav}")
    return segs
