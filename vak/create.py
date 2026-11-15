"""CREATE: a new chant project from pasted text (used by the web app and `python -m vak new`).

    preview(text, translations)          -> units (+ IAST, English, word meanings) and the planned scenes per style
    new_project(dest, title=..., text=..., style=..., audio=... | recite=True)  -> path of project.json

The project folder then builds like any other: python -m vak run <dest>/project.json --style <id>."""
import json, os, re, shutil
from . import planner, text
from .util import log

ANIM_STYLES = {"yantra": "Yantra + Akshara (figure-free)", "shadow_puppet": "Shadow puppets (tholu bommalata)", "silhouette": "Silhouette paper-cut + sacred geometry"}
STORY_STYLES = ("shadow_puppet", "silhouette")     # figures and scenes: offered only when a chant has a cited story
LIVE_STYLES = {"nada": "Nāda · cymatics", "gold": "Liquid gold", "kana": "Kaṇa · particles of light",
               "agni": "Agni · sacred fire", "dhupa": "Dhūpa · incense smoke", "akasha": "Ākāśa · night sky"}   # drawn in the browser from audio + word timings (web/static/vakfx.js)
CREATE_STYLES = {**LIVE_STYLES, **ANIM_STYLES}


def slug(s):
    s = text.iast(s) if re.search(r"[ऀ-ॿ]", s) else s
    import unicodedata
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()       # ā -> a, ṛ -> r
    s = re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")
    return s[:40] or "chant"


def units_of(chant_text, translations=None, words=None):
    if not re.search(r"[ऀ-ॿ]", chant_text):
        raise ValueError("paste the chant in Devanagari (e.g. ॐ नमः शिवाय ॥); IAST input is not supported yet")
    units = text.parse(chant_text)
    if not units:
        raise ValueError("no chant lines found: use Devanagari, end each verse or line with ॥ (e.g. ... ॥ १ ॥)")
    for u in units:
        u["english"] = (translations or {}).get(u["devanagari"], "")
    tmp = None
    if words:
        tmp = os.path.join(os.environ.get("TEMP", "/tmp"), "vak_words_preview.json")
        json.dump(words, open(tmp, "w", encoding="utf-8"), ensure_ascii=False)
    text.word_meanings(units, tmp)
    return units


def normalise(chant_text):
    """Accept pasted text with or without verse marks: a line with no danda gets ॥ so it becomes one unit."""
    lines = [l.strip() for l in chant_text.replace("\r", "").split("\n") if l.strip()]
    if not any("॥" in l or "।" in l for l in lines):
        lines = [l + " ॥" for l in lines]
    return "\n".join(lines) + "\n"


def preview(chant_text, translations=None, words=None, styles=("yantra", "shadow_puppet", "silhouette")):
    units = units_of(normalise(chant_text), translations, words)
    return {"units": units, "plans": {s: planner.summary(planner.plan(units, s)) for s in styles}}


def new_project(dest, title, chant_text, style="yantra", translations=None, words=None, audio=None,
                audio_mode="voice", segments=None, recite=False, card=None, track_from=None, source=None,
                interpretation=None, deity=None, provenance=None):
    os.makedirs(dest, exist_ok=True)
    chant_text = normalise(chant_text)
    open(os.path.join(dest, "chant.txt"), "w", encoding="utf-8").write(chant_text)
    units = units_of(chant_text, translations, words)
    json.dump({u["devanagari"]: u["english"] for u in units if u["english"]},
              open(os.path.join(dest, "translations.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    if words:
        json.dump(words, open(os.path.join(dest, "words.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    cfg = {"title": title, "chant": "chant.txt", "translations": "translations.json", "style": style,
           "tune": False, "out": f"renders/{slug(title)}.mp4", "audio_mode": audio_mode,
           "card": card or {"kicker": " ".join(u["devanagari"] for u in units[:3])[:36].rsplit(" ", 1)[0], "chapter": "", "title": title,
                            "sub": "Understand what you chant · a Vāk film"},
           "characters": {}, "scenes": [{"id": "M1", "title": title, "verses": "all", "include_preamble": True}],
           "animation": "auto", "source": source or "pasted by a user (not yet identified)"}
    if words:
        cfg["words"] = "words.json"
    if interpretation:                               # Claude's reading of an unknown chant (vak/interpret.py): kept with the project
        json.dump(interpretation, open(os.path.join(dest, "interpretation.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        cfg["interpretation"] = "interpretation.json"
    if deity: cfg["deity"] = deity
    if provenance: cfg["provenance"] = provenance
    if recite == "eleven_music":                     # sung by ElevenLabs Music: melody, tanpura, flute; exact word times
        from . import eleven
        cfg["segments"] = eleven.sing(units, os.path.join(dest, "recitation.wav"), os.path.join(dest, ".vak_cache"))
        cfg["audio"], cfg["audio_mode"], cfg["recited_by"] = "recitation.wav", "track", "ElevenLabs Music"
    elif recite == "eleven":                         # ElevenLabs voice with our pronunciation layer (vak/eleven.py)
        from . import eleven
        cfg["segments"] = eleven.run(units, os.path.join(dest, "recitation.wav"), os.path.join(dest, ".vak_cache"))
        cfg["audio"], cfg["audio_mode"], cfg["recited_by"] = "recitation.wav", "voice", "ElevenLabs"
    elif recite:
        from . import recite as rc
        cfg["segments"] = rc.run(units, os.path.join(dest, "recitation.wav"), os.path.join(dest, ".vak_cache"))
        cfg["audio"], cfg["audio_mode"], cfg["recited_by"] = "recitation.wav", "voice", rc.VOICE
    elif audio:
        name = "recording" + os.path.splitext(audio)[1].lower()
        if os.path.abspath(audio) != os.path.abspath(os.path.join(dest, name)):
            shutil.copyfile(audio, os.path.join(dest, name))
        cfg["audio"] = name
        if segments: cfg["segments"] = segments
    else:
        raise ValueError("give a recording (audio=...) or recite=True")
    for fam in ("yantra", "shadow_puppet", "silhouette"):       # rule-based plans, reviewable and editable before the build
        json.dump(planner.plan(units, fam), open(os.path.join(dest, f"anim_plan_{fam}.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    path = os.path.join(dest, "project.json")
    json.dump(cfg, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    log(f"create: project '{title}' with {len(units)} units -> {path}")
    return path
