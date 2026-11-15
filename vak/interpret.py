"""INTERPRET: Claude reads a pasted chant that is not in our library and returns what the platform needs, as checked JSON:
identification (name, source with citation, confidence), genre, deity, a faithful English line by line, every word's
sandhi split and meaning, the viniyoga / dhyāna details when present, and the chant's story context (speaker frame,
legend, characters, setting) for the story → storyboard → narration → video pipeline.

Guardrails (CLAUDE.md "Any chant → context"): never invent a purāṇic story without a cited source; every field carries a
confidence or "unknown"; low confidence → provenance "Interpreted" and a teacher's review before publishing.
Results are cached in knowledge/interpreted/<hash>.json (the growing knowledge layer); a cached chant costs nothing.
Needs ANTHROPIC_API_KEY (loaded from .env.local by vak/envfile.py). Model: VAK_INTERPRET_MODEL (default claude-opus-5-5)."""
import hashlib, json, os, re, time
from typing import List, Literal
from pydantic import BaseModel
from .util import log

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, "knowledge", "interpreted")
MODEL = os.environ.get("VAK_INTERPRET_MODEL", "claude-opus-5-5")
Conf = Literal["high", "medium", "low", "unknown"]


class Word(BaseModel):
    dev: str                 # exactly as given
    split: str               # the words inside the sandhi form, IAST (e.g. "tat savituḥ vareṇyam")
    meaning: str             # short English gloss in context


class Line(BaseModel):
    devanagari: str          # exactly as given
    english: str             # faithful translation of the line
    words: List[Word]


class Identification(BaseModel):
    name: str                # e.g. "Śiva Pañcākṣara Stotram, verse 1", or "" if unknown
    source: str              # text + chapter/verse, e.g. "Ṛgveda 3.62.10"; "" if unknown
    tradition: str           # e.g. "attributed to Ādi Śaṅkarācārya"; "" if unknown
    confidence: Conf
    notes: str               # how it was recognised, doubts, variant readings


class Story(BaseModel):
    has_story: bool          # true only if a story is attested in a cited source
    speaker: str             # who recites / speaks in the text ("" if none)
    listener: str
    frame: str               # the narrative frame in one or two sentences (e.g. "Mārkaṇḍeya asks Brahmā for the most secret protection")
    legend: str              # the attested story behind the chant, 3–8 sentences, only from the cited source
    characters: List[str]
    setting: str             # place / time of the story
    source: str              # citation for the story; "" if none
    confidence: Conf


class Interpretation(BaseModel):
    identification: Identification
    genre: Literal["mantra", "stotra", "kavacham", "namavali", "dhyana", "suktam", "narrative", "other"]
    deity: Literal["shiva", "devi", "vishnu", "ganesha", "surya", "peace"]   # visual palette family
    deity_name: str          # as named in the text, e.g. "Śiva", "Durgā", "Savitṛ"
    dhyana: str              # the deity's form if the text describes it (for an anchor image); "" if not
    viniyoga: str            # ṛṣi / chandas / devatā / purpose if stated; "" if not
    meaning_summary: str     # what the chant asks or praises, 1–3 sentences
    story: Story             # the chant's cited story context (for story → storyboard → narration → video)
    lines: List[Line]
    translation_confidence: Conf
    caution: str             # anything a teacher should check (pronunciation, corrupt text, uncertain words)


SYSTEM = """You are a careful Sanskrit scholar helping a devotional learning app explain chants to people who chant them.
You receive a chant already split into lines and words by the app. Interpret it faithfully.

Rules:
- Return one entry in `lines` per given line, in order, with `devanagari` copied exactly; in each, one entry in `words` per given word, in order, with `dev` copied exactly. Never merge, split, reorder or drop lines or words.
- Translate faithfully and plainly; keep devotional names (Śiva, Devī, Savitṛ) in IAST. Do not embellish.
- Identification: name the chant and cite its source (text, book/chapter, verse) only when you actually recognise it. Otherwise leave name/source empty and set confidence "unknown". Never guess a citation.
- Story: set has_story true only when a story about this chant is attested in a text you can cite (e.g. the frame dialogue of a kavacham, a purāṇic account). Write only what that source says. If there is none, has_story false and leave legend empty — the app must never invent a story.
- Confidence: "high" only when certain; prefer "medium"/"low" over false certainty.
- deity: choose the palette family from the deity addressed (shiva, devi, vishnu incl. Rāma/Kṛṣṇa, ganesha, surya incl. Savitṛ); use "peace" for chants without a single deity (śānti mantras, universal prayers).
- caution: note anything a teacher should check."""


def available():
    return bool(os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN"))


def _key(units):
    norm = "\n".join(" ".join(w["dev"] for w in u["words"]) for u in units)
    return hashlib.sha256(norm.encode("utf-8")).hexdigest()[:16]


def cached(units):
    p = os.path.join(CACHE, _key(units) + ".json")
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else None


def run(units, force=False):
    """Interpret the chant (cached by its words). Returns the Interpretation as a dict, plus "_model" and "_at"."""
    p = os.path.join(CACHE, _key(units) + ".json")
    if not force and os.path.exists(p):
        return json.load(open(p, encoding="utf-8"))
    if not available():
        raise RuntimeError("Claude isn't connected: add ANTHROPIC_API_KEY to vak_engine/.env.local and restart the Studio")
    import anthropic
    given = [{"devanagari": u["devanagari"], "iast": u.get("iast", ""), "words": [{"dev": w["dev"], "iast": w.get("iast", "")} for w in u["words"]]}
             for u in units]
    client = anthropic.Anthropic()
    t0 = time.time()
    resp = client.beta.messages.parse(
        model=MODEL, max_tokens=16000,
        betas=["server-side-fallback-2026-07-01"], fallbacks="default",     # a declined request is re-run on a fallback model
        output_config={"effort": "high"},
        system=SYSTEM,
        messages=[{"role": "user", "content": "Interpret this chant. Lines and words as split by the app:\n\n"
                   + json.dumps(given, ensure_ascii=False, indent=1)}],
        output_format=Interpretation,
    )
    if resp.stop_reason == "refusal" or resp.parsed_output is None:
        raise RuntimeError("Claude could not interpret this text" + (f" ({resp.stop_details.category})" if getattr(resp, "stop_details", None) else ""))
    out = resp.parsed_output.model_dump()
    out["_model"], out["_at"] = resp.model, time.strftime("%Y-%m-%d %H:%M")
    os.makedirs(CACHE, exist_ok=True)
    json.dump(out, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    log(f"interpret: {out['identification']['name'] or 'not identified'} ({out['identification']['confidence']}), "
        f"{out['genre']}, deity {out['deity']}, {len(out['lines'])} lines in {time.time() - t0:.0f}s with {resp.model}")
    return out


def provenance(interp):
    """Identified only when Claude recognises the chant with a citation and high/medium confidence; otherwise Interpreted."""
    i = interp["identification"]
    if i["source"] and i["confidence"] in ("high", "medium"):
        return "Identified"
    return "Interpreted"


def source_text(interp):
    i = interp["identification"]
    if i["source"]:
        return f"{i['name'] or 'Identified'} · {i['source']} (identified by Claude, {i['confidence']} confidence; awaiting a teacher's review)"
    return "pasted by a user (not yet identified; interpreted by Claude, awaiting a teacher's review)"


def tables(units, interp):
    """translations {line: english} and words {dev: {meaning, split}} in the shapes create.units_of() takes.
    Lines are matched by position (the model was told to keep them), with a text check."""
    tr, words = {}, {}
    norm = lambda s: re.sub(r"[\s।॥०-९]", "", s)
    for u, L in zip(units, interp.get("lines", [])):
        if norm(L["devanagari"]) != norm(u["devanagari"]):
            continue
        if L["english"]:
            tr[u["devanagari"]] = L["english"]
        for w, W in zip(u["words"], L["words"]):
            if norm(W["dev"]) == norm(w["dev"]) and W["meaning"]:
                words.setdefault(w["dev"], {"meaning": W["meaning"], "split": W["split"]})
    return tr, words
