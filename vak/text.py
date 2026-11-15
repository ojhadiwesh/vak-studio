"""TEXT module: chant text -> chanting units (one per pāda / spoken line), with transliteration,
word syllable counts, speakers and translations."""
import json, os, re
from indic_transliteration import sanscript as s
from .util import log

CONS = set("कखगघङचछजझञटठडढणतथदधनपफबभमयरलवशषसहळ")
INDEP = set("अआइईउऊऋॠऌएऐओऔ")
DIGITS = "०१२३४५६७८९"


def syllables(word):
    if word == "ॐ":
        return 2
    n = 0
    for i, ch in enumerate(word):
        nxt = word[i + 1] if i + 1 < len(word) else ""
        if (ch in CONS and nxt != "्") or ch in INDEP:
            n += 1
    return max(n, 1)


def iast(t):
    return s.transliterate(t, s.DEVANAGARI, s.IAST)


def _words(text):
    return [w for w in re.sub(r"[।॥|0-9०-९]", " ", text).split() if w]


def _split_padas(words):
    """Split a half-verse into two pādas at the word boundary nearest half its syllables."""
    syl = [syllables(w) for w in words]
    tot, best, acc = sum(syl), 1, 0
    if len(words) < 2 or tot < 12:
        return [words]
    for i in range(1, len(words)):
        acc += syl[i - 1]
        if abs(acc - tot / 2) < abs(sum(syl[:best]) - tot / 2):
            best = i
    return [words[:best], words[best:]]


def parse(text):
    """Return units from Devanagari chant text. Lines ending in उवाच are speaker lines;
    a verse is two half-lines, the second ending ॥ n ॥. Pasted verses are often unnumbered: a half-line ending
    in a plain ॥ closes the verse too, and so does the end of the text (a verse pasted without its final ॥)."""
    units, speaker, verse_lines, last = [], None, [], 0
    lines = [l.strip() for l in text.splitlines() if l.strip()]

    def add(kind, words, verse=None):
        dev = " ".join(words)
        units.append({"id": f"u{len(units) + 1:03d}", "kind": kind, "verse": verse, "devanagari": dev, "iast": iast(dev),
                      "words": [{"dev": w, "iast": iast(w), "syl": syllables(w)} for w in words],
                      "speaker": speaker if kind == "verse" else None, "english": ""})

    def close_verse(num):
        nonlocal verse_lines
        for half in verse_lines:
            words = _words(half)
            if words and words[0] == "ॐ" and len(words) > 1:   # a leading ॐ is chanted on its own
                add("verse", ["ॐ"], num); words = words[1:]
            for pada in _split_padas(words):
                if pada:
                    add("verse", pada, num)
        verse_lines = []

    for line in lines:
        m = re.search(r"॥\s*([०-९0-9]+)\s*॥\s*$", line)
        if "उवाच" in line and not verse_lines:                 # speaker line, e.g. मार्कण्डेय उवाच
            words = _words(line)
            add("speaker", words)
            speaker = iast(words[0]).capitalize()
        elif m:                                               # last half-line of a numbered verse
            verse_lines.append(line)
            last = int("".join(str(DIGITS.index(c)) if c in DIGITS else c for c in m.group(1)))
            close_verse(last)
        elif line.rstrip().endswith("॥") and not verse_lines:  # invocation, e.g. ॐ नमश्चण्डिकायै ॥
            add("invocation", _words(line))
        elif line.rstrip().endswith("॥"):                     # last half-line of an unnumbered verse
            verse_lines.append(line)
            last += 1
            close_verse(last)
        else:
            verse_lines.append(line)
    if verse_lines:                                           # the text stops before the verse's closing ॥
        last += 1
        close_verse(last)
    log(f"text: {len(units)} units from {sum(1 for l in lines if '॥' in l)} lines")
    return units


def translate(units, provider="manual", glossary=None):
    """Fill unit['english']. 'manual' reads {devanagari: english} from a JSON file;
    'claude' asks the Anthropic API (needs ANTHROPIC_API_KEY) for faithful pāda-level translations."""
    if provider == "manual":
        table = json.load(open(glossary, encoding="utf-8")) if glossary else {}
        for u in units:
            u["english"] = table.get(u["devanagari"], u["english"])
    elif provider == "claude":
        import urllib.request
        prompt = ("Translate each Sanskrit line below into short, faithful, reverent English. "
                  "Translate only what the line says; no commentary. Return a JSON object mapping each line exactly to its translation.\n\n"
                  + "\n".join(u["devanagari"] for u in units))
        req = urllib.request.Request("https://api.anthropic.com/v1/messages", method="POST",
            headers={"x-api-key": os.environ["ANTHROPIC_API_KEY"], "anthropic-version": "2023-06-01", "content-type": "application/json"},
            data=json.dumps({"model": os.environ.get("VAK_LLM", "claude-opus-5-5"), "max_tokens": 4000,
                             "messages": [{"role": "user", "content": prompt}]}).encode())
        txt = json.loads(urllib.request.urlopen(req).read())["content"][0]["text"]
        table = json.loads(txt[txt.find("{"): txt.rfind("}") + 1])
        for u in units:
            u["english"] = table.get(u["devanagari"], u["english"])
    missing = [u["id"] for u in units if not u["english"]]
    if missing:
        log(f"text: {len(missing)} units still need a translation (review step)")
    return units


KNOWLEDGE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "knowledge", "glossary.json")


def load_glossary(*paths):
    """Merge word glossaries {devanagari word: meaning | {meaning, split}}; later files win."""
    table = {}
    for p in (KNOWLEDGE, *paths):
        if p and os.path.exists(p):
            for k, v in json.load(open(p, encoding="utf-8")).items():
                if not k.startswith("_"):
                    table[k] = v if isinstance(v, dict) else {"meaning": v}
    return table


def word_meanings(units, *paths):
    """Attach w["meaning"] (and w["split"], the words inside a sandhi form) from the glossaries, for tap-a-word."""
    table, n = load_glossary(*paths), 0
    for u in units:
        for w in u["words"]:
            e = table.get(w["dev"])
            if e:
                w["meaning"] = e.get("meaning", ""); n += 1
                if e.get("split"): w["split"] = e["split"]
    tot = sum(len(u["words"]) for u in units)
    log(f"text: word meanings for {n}/{tot} words" + ("" if n == tot else " (the rest need the glossary or a teacher)"))
    return units
