"""Builds eval/chant_id_dataset.jsonl (run once; the file is committed). 
Task: a person types a chant any way they like -> does Vak recognise the right chant (or correctly say "not in our
knowledge layer") and give the canonical Devanagari?  expected_id = None means it must NOT claim a match."""
import json, os
H = "hand"      # written and labelled by hand (spellings people really type)
G = "variant"   # systematic variant of a canonical text (case, punctuation, script)
rows = []
def add(text, exp, kind, note=""):
    rows.append({"id": f"c{len(rows)+1:03d}", "input": text, "expected_id": exp, "kind": kind, "note": note})

# --- hand-written: real-world spellings, typos, partials (labels checked by hand) ---
for t, e, n in [
 ("om namah shivaya", "panchakshari", "most common spelling"),
 ("Om Namah Shivay", "panchakshari", "Hindi-style dropped final a"),
 ("om namaha shivaaya", "panchakshari", "long vowel doubled"),
 ("aum namah sivaya", "panchakshari", "s for sh"),
 ("OM NAMAH SHIVAYA!!", "panchakshari", "caps + punctuation"),
 ("om nmah shivaya", "panchakshari", "typo: missing vowel"),
 ("om namha shivaya", "panchakshari", "typo: transposed"),
 ("om namo narayanaya", "ashtakshari", ""),
 ("om namo narayana", "ashtakshari", "dropped final syllable"),
 ("Om Namo Naaraayanaaya", "ashtakshari", "doubled vowels"),
 ("om namo narayanay", "ashtakshari", "typo"),
 ("om gam ganapataye namaha", "ganapati", ""),
 ("om gan ganapataye namah", "ganapati", "anusvara as n"),
 ("Om Gam Ganpataye Namah", "ganapati", "Hindi spelling Ganpati"),
 ("om gam ganapatye namah", "ganapati", "typo"),
 ("hare krishna hare krishna krishna krishna hare hare hare rama hare rama rama rama hare hare", "mahamantra", "full"),
 ("Hare Krsna Hare Krsna Krsna Krsna Hare Hare Hare Rama Hare Rama Rama Rama Hare Hare", "mahamantra", "ISKCON spelling krsna"),
 ("hare krishna hare krishna krishna krishna hare hare\nhare ram hare ram ram ram hare hare", "mahamantra", "two lines, Hindi ram"),
 ("lokah samastah sukhino bhavantu", "lokah", ""),
 ("loka samasta sukhino bhavanthu", "lokah", "South Indian th"),
 ("Lokaa Samastaa Sukhino Bhavantu", "lokah", "doubled vowels"),
 ("lokah samasta sukino bhavantu", "lokah", "typo: sukino"),
 ("om shanti shanti shanti", "shanti", ""),
 ("Om Shanti Shanti Shantihi", "shanti", "spoken visarga"),
 ("om shaanti shaanti shaantih", "shanti", "doubled vowels"),
 ("om santi santi santi", "shanti", "s for sh"),
 # negatives: real chants NOT in the knowledge layer -> must not be mislabelled
 ("om bhur bhuvah svah tat savitur varenyam bhargo devasya dhimahi dhiyo yo nah prachodayat", None, "Gayatri: not in chants.json"),
 ("om tryambakam yajamahe sugandhim pushtivardhanam", None, "Mahamrityunjaya: not in chants.json"),
 ("om namo bhagavate vasudevaya", None, "close to ashtakshari but different"),
 ("om namah", None, "too short to identify"),
 ("om shri ganeshaya namah", None, "different Ganesha mantra"),
 ("hare rama hare rama", None, "fragment shared by many bhajans"),
 ("om mani padme hum", None, "Buddhist mantra"),
 ("sarve bhavantu sukhinah sarve santu niramayah", None, "close to lokah but different prayer"),
 ("om sahana vavatu sahanau bhunaktu", None, "shanti mantra, different one"),
 ("I love chanting every morning", None, "ordinary sentence"),
]: add(t, e, H, n)

# --- systematic variants of each canonical chant ---
from indic_transliteration import sanscript as s
KN = json.load(open(os.path.join(os.path.dirname(__file__), "..", "knowledge", "chants.json"), encoding="utf-8"))["chants"]
for c in KN:
    dev = c["text"]; iast = s.transliterate(dev, s.DEVANAGARI, s.IAST)
    base = c["aliases"][0]
    for t, n in [(dev, "canonical Devanagari"), (dev.replace("॥", "").replace("।", "").strip(), "Devanagari, no danda"),
                 (iast, "IAST"), (iast.upper(), "IAST upper case"), (base.title(), "title case"),
                 (base.replace(" ", "  "), "double spaces"), (base + ".", "trailing period"), ("  " + base + "\n", "padding"),
                 (base.replace(" ", "-"), "hyphens"), (base.replace(" ", ""), "no spaces")]:
        add(t, c["id"], G, n)
# negatives in other scripts / noise
for t, n in [("ॐ भूर्भुवः स्वः", "Gayatri vyahrti, Devanagari"), ("ॐ त्र्यम्बकं यजामहे", "Mahamrityunjaya, Devanagari"),
             ("नमस्ते", "greeting"), ("asdf qwer zxcv", "keyboard noise"), ("1234 5678", "numbers"),
             ("hello how are you", "chat"), ("shiva", "single deity name"), ("krishna", "single deity name"),
             ("ram ram", "fragment"), ("om om om", "only Om")]:
    add(t, None, G, n)
with open(os.path.join(os.path.dirname(__file__), "chant_id_dataset.jsonl"), "w", encoding="utf-8") as f:
    for r in rows: f.write(json.dumps(r, ensure_ascii=False) + "\n")
print(len(rows), "examples;", sum(r["kind"] == H for r in rows), "hand-written")
