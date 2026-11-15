"""ROMANIZE: chants typed in IAST or casual English spelling -> Devanagari.

    to_devanagari(text) -> {"devanagari", "method", "note", "chant"?}
      method "devanagari": already Devanagari, unchanged
             "known":      matched a known chant (knowledge/chants.json) -> its canonical text
             "iast":       IAST diacritics -> exact transliteration
             "guess":      casual spelling ("om namah shivaya") -> best guess; long vowels and retroflex
                           sounds can't be known from plain letters, so the user must check it
"""
import json, os, re
from indic_transliteration import sanscript as s

KNOWN = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "knowledge", "chants.json")
IAST_MARKS = re.compile(r"[āīūṛṝḷṅñṭḍṇśṣṃḥĀĪŪṚṜḶṄÑṬḌṆŚṢṂḤ]")
DEV = re.compile(r"[ऀ-ॿ]")


def known_chants():
    try:
        return json.load(open(KNOWN, encoding="utf-8"))["chants"]
    except Exception:
        return []


def key(t):
    """Loose spelling key: lower case, no diacritics or punctuation, long vowels and aspirates folded."""
    import unicodedata
    t = unicodedata.normalize("NFKD", t.lower()).encode("ascii", "ignore").decode()
    t = re.sub(r"[^a-z]", "", t)
    for a, b in (("aum", "om"), ("aa", "a"), ("ee", "i"), ("ii", "i"), ("oo", "u"), ("uu", "u"), ("sh", "s"), ("w", "v"),
                 ("ri", "r"), ("ru", "r"), ("ksh", "ks"), ("ah", "a"), ("h", "")):
        t = t.replace(a, b)
    return re.sub(r"(.)\1+", r"\1", t)


def match_known(text, extra=()):
    k = key(text)
    if len(k) < 4:
        return None
    for c in [*extra, *known_chants()]:
        keys = [key(a) for a in c.get("aliases", [])] + [key(s.transliterate(c["text"], s.DEVANAGARI, s.IAST))]
        if k in keys:
            return c
    return None


def _guess_line(line):
    words = []
    for w in line.split():
        lw = w.lower()
        if lw in ("om", "aum"):
            words.append("OM"); continue
        lw = re.sub(r"ah$", "aH", lw); lw = re.sub(r"ih$", "iH", lw); lw = re.sub(r"uh$", "uH", lw)   # final visarga
        lw = re.sub(r"aha$", "aH", lw)                                                               # "namaha" -> namaḥ
        words.append(lw)
    return s.transliterate(" ".join(words), s.ITRANS, s.DEVANAGARI).replace("ओम्", "ॐ")


def to_devanagari(text, extra=()):
    """extra: more known chants [{text, name, aliases?...}] (e.g. the app's library presets) to match first."""
    text = text.strip()
    if DEV.search(text):
        c = identify(text, extra)
        if c:
            return {"devanagari": text, "method": "devanagari", "chant": c, "note": f"Recognised as {c['name']}"}
        return {"devanagari": text, "method": "devanagari", "note": ""}
    c = match_known(text, extra) or identify(text, extra)
    if c:
        return {"devanagari": c["text"], "method": "known", "chant": c, "note": f"Recognised as {c['name']}"}
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    if IAST_MARKS.search(text):
        dev = "\n".join(s.transliterate(l, s.IAST, s.DEVANAGARI) for l in lines)
        return {"devanagari": dev, "method": "iast", "note": "Converted from IAST"}
    dev = "\n".join(_guess_line(l) for l in lines)
    return {"devanagari": dev, "method": "guess",
            "note": "Read from English spelling. Long vowels and some sounds can't be known from plain letters: check the Devanagari"}


def identify(text, extra=()):
    """Identify a known chant from Devanagari, IAST or casual spelling, tolerating small typos.
    Stricter than a guess: a wrong "Identified" badge would show a false source, so near-misses must be close."""
    import difflib
    raw = (text or "").strip()
    if not raw:
        return None
    lat = s.transliterate(raw, s.DEVANAGARI, s.IAST) if DEV.search(raw) else raw
    k = key(lat)
    if len(k) < 6:
        return None
    best, score = None, 0.0
    for c in [*extra, *known_chants()]:
        keys = {key(a) for a in c.get("aliases", [])} | {key(s.transliterate(c["text"], s.DEVANAGARI, s.IAST))}
        keys |= {x.replace("krsn", "krisn") for x in keys}
        for kk in keys:
            if k == kk or k.replace("krsn", "krisn") == kk:
                return c
            r = difflib.SequenceMatcher(None, k, kk).ratio()
            if r > score and abs(len(k) - len(kk)) <= max(2, len(kk) // 8):
                best, score = c, r
    return best if score >= 0.9 else None
