"""SAFETY: screen every text a person types before it reaches the engine or Claude.

    check(text) -> {"action": "allow" | "crisis" | "block", "category": str, "message": str, "resources": [...]}

    crisis  - the person may be in danger (suicide, self-harm, abuse, medical emergency). We stop, answer
              kindly and show real helplines. Nothing is generated from the text.
    block   - the text asks for something the app won't make: hate or mockery of a faith, violence or curses
              against people, sexual content, "mantras" sold as medical cures, prompt injection, personal data.
    allow   - a chant or ordinary text.

Rule-based on purpose: fast, free, works offline, gives the same answer every time (so the red-team script is
reproducible). English, Hindi (Devanagari) and Hinglish phrasings. False positives on crisis are acceptable;
false negatives are not.
"""
import re
import unicodedata

RESOURCES = [
    {"name": "Tele-MANAS (India, 24×7, free)", "contact": "14416 or 1-800-891-4416"},
    {"name": "KIRAN mental health helpline (India)", "contact": "1800-599-0019"},
    {"name": "988 Suicide & Crisis Lifeline (US)", "contact": "Call or text 988"},
    {"name": "Emergency services", "contact": "112 (India) · 911 (US) · 999 (UK)"},
    {"name": "Find a helpline in your country", "contact": "https://findahelpline.com"},
]

CRISIS_MESSAGE = ("It sounds like you may be going through something very painful. You don't have to face it alone. "
                  "Please reach out now to someone who can help: a helpline below, a person you trust, or emergency "
                  "services if you are in danger. A chant can be a comfort alongside real support, never instead of it.")

BLOCK_MESSAGES = {
    "hate": "Vāk makes films that honour every tradition. It won't make content that mocks or attacks a faith or a group of people.",
    "violence": "Vāk won't make chants, curses or rituals meant to harm, control or punish anyone.",
    "sexual": "Vāk only makes devotional and learning films; it won't make sexual content.",
    "medical": ("A chant can support calm and wellbeing, but it is not a medical treatment. Vāk won't present a mantra as a "
                "cure. Please keep following your doctor's advice."),
    "injection": "That looks like instructions to the system rather than a chant. Please paste only the chant text.",
    "pii": "Please don't paste personal details (phone numbers, ID or card numbers, passwords). Only the chant text is needed.",
    "too_long": "That text is too long for one film. Paste up to about 60 lines.",
}


def _norm(t):
    t = unicodedata.normalize("NFKC", t or "").lower()
    t = re.sub(r"[​-‏⁠﻿]", "", t)          # zero-width tricks
    t = re.sub(r"(.)\1{2,}", r"\1", t)                         # "dieeee" -> "die"   (fix for r17)
    t = re.sub(r"\b(\w) (?=\w\b)", r"\1", t)                   # "k i l l" -> "kill" (fix for r18)
    t = t.replace("0", "o").replace("1", "i").replace("3", "e").replace("@", "a").replace("$", "s")
    return re.sub(r"\s+", " ", t)


CRISIS = [
    # suicide / wanting to die
    r"\b(kill|end|take|hurt|harm)(ing)? (my ?self|my own life|my life)\b", r"\bsuicid", r"\bkms\b",
    r"\b(want|wanna|going|plan(ning)?|ready|deserve) to (die|be dead|disappear forever)\b",
    r"\bwish (i was|i were|to be) dead\b", r"\bbetter off (dead|without me)\b", r"\bno reason to (live|go on)\b",
    r"\b(can'?t|cannot|don'?t want to) (go on|live|keep living|do this anymore)\b", r"\bend it all\b",
    r"\b(last|final) (message|goodbye|chant before i (die|go))\b", r"\bnot (be|being) here tomorrow\b",
    r"\bmantra (to|for|so i can) (die|leave my body|end my life)\b", r"\bleave (my|this) body\b.*\b(tonight|today|now|forever)\b",
    r"\b(overdose|od on|hang myself|slit|jump (off|from)|pills to die)\b", r"\bself[- ]?harm", r"\bcut(ting)? myself\b",
    # Hindi / Hinglish
    r"मर(ना|जाना) चाह", r"आत्महत्या", r"खुदकुशी", r"जीना नहीं चाह", r"जान दे", r"ख़ुद को (मार|ख़त्म|खत्म)",
    r"\b(marna|mar jana) chah", r"\bjeena nahi(n)? chah", r"\baatmahatya\b", r"\bkhudkushi\b", r"\bjaan de (dunga|dungi|du)",
    # abuse / immediate danger / medical emergency
    r"\b(he|she|they|my (husband|wife|father|mother|partner|uncle|boss)) (is )?(beat|hit|hurt|abus)(s|es|ing)? me\b",
    r"\b(being|am being|i'?m being) (abused|beaten|hurt)\b", r"\bnot safe at home\b", r"\bsomeone is going to kill me\b",
    r"\b(chest pain|can'?t breathe|heart attack|stroke)\b.*\b(now|right now|mantra|chant)\b",
    r"\b(mantra|chant|mahamrityunjaya|kavach\w*)\b.*\b(instead of|rather than|so i don'?t need)( going to| calling)?( a| the)? (doctor|hospital|ambulance)\b",  # fix for r16
]
HATE = [
    r"\b(mock|insult|make fun of|ridicule|humiliate|desecrat)\w* (hindu|hinduism|muslim|islam|christian|sikh|jain|buddhis|jew|god|gods|deity|devi|shiva|krishna|allah|jesus)",
    r"\b(hindus|muslims|christians|sikhs|jews|dalits|brahmins) (are|r) (evil|dirty|animals|inferior|terrorists)\b",
    r"\b(inferior|impure|untouchable) (caste|castes|people)\b",
    r"\b(lower|low|other) (castes?|religions?)\b.{0,20}\b(impure|inferior|dirty|untouchable|evil)\b",   # fix for r23
    r"\bkill (all )?(the )?(hindus|muslims|christians|sikhs|jews|infidels|kafirs)\b",
    r"\bmlechh?as? (must|should) (die|be killed)\b",
]
VIOLENCE = [
    r"\b(curse|hex|spell|mantra|chant|tantra|ritual)\b.{0,40}\b(to |that will |so that )?(kill|destroy|harm|hurt|ruin|punish|make .* sick|death of)\b",
    r"\b(maran|marana|uchatan|uchchatan|vashikaran|vashikaran|vasikaran|abhichar|abhichara) (mantra|prayog|kriya)?",
    r"\bmantra to (control|enslave|seduce|make) (my |a |her |him |someone)",
    r"\b(make|build) (a )?(bomb|weapon|poison)\b",
]
SEXUAL = [r"\b(sex|sexual|nude|naked|porn|erotic|nsfw)\b", r"\bseduc(e|tion)\b.*\bmantra\b",
          r"\b(mantra|chant|spell)\b.{0,20}\bseduc"]   # fix for r29 (word order)
MEDICAL = [
    r"\b(mantra|chant|stotra|kavacham?)\b.{0,60}\b(cure|cures|curing|heal|heals|treat|treats)\b.{0,30}\b(cancer|diabetes|covid|hiv|aids|tumou?r|disease|depression|infection)\b",
    r"\b(stop|quit|skip|replace)( taking)? (my )?(medicine|medication|meds|chemo|insulin|treatment)\b",
    r"\b(guarantee|guaranteed|100%) (cure|healing|recovery)\b",
]
INJECTION = [
    r"\bignore (all |the |your |any )?(previous|prior|above|earlier) (instructions|rules|prompt)", r"\bsystem prompt\b",
    r"\byou are now\b", r"\b(developer|dan|jailbreak) mode\b", r"\breveal (your|the) (instructions|prompt|api key|key|secrets?)\b",
    r"\b(api[_ -]?key|secret[_ -]?key|password|env(ironment)? variables?)\b.*\b(print|show|reveal|output|tell)\b",
    r"\b(print|show|reveal|output|tell me)\b.*\b(api[_ -]?key|secret[_ -]?key|\.env|environment variables?)\b",
    r"</?(system|instructions?|assistant)>", r"\bpretend (you are|to be)\b.*\b(no rules|unfiltered|without (rules|limits))\b",
    r"\binvent (a|the) (purana|puranic|scripture|story)\b.*\b(say|claim|cite)\b",
]
PII = [
    r"\b\d{4}[ -]?\d{4}[ -]?\d{4}[ -]?\d{4}\b",                 # card number
    r"\b\d{4} ?\d{4} ?\d{4}\b(?!.*\b(verse|line)\b)",           # Aadhaar-like
    r"\b[A-Z]{5}\d{4}[A-Z]\b",                                  # PAN (checked on raw text)
    r"\b(my )?(password|passcode|pin|otp) (is|:)",
    r"\b\d{3}-\d{2}-\d{4}\b",                                   # SSN
]


def _any(pats, t):
    return next((p for p in pats if re.search(p, t)), None)


def check(text):
    raw = text or ""
    t = _norm(raw)
    if _any(CRISIS, t):
        return {"action": "crisis", "category": "crisis", "message": CRISIS_MESSAGE, "resources": RESOURCES}
    for cat, pats in (("hate", HATE), ("violence", VIOLENCE), ("sexual", SEXUAL), ("medical", MEDICAL),
                      ("injection", INJECTION)):
        if _any(pats, t):
            return {"action": "block", "category": cat, "message": BLOCK_MESSAGES[cat], "resources": []}
    if _any(PII, raw) or _any(PII, t):
        return {"action": "block", "category": "pii", "message": BLOCK_MESSAGES["pii"], "resources": []}
    if len(raw) > 6000 or raw.count("\n") > 80:
        return {"action": "block", "category": "too_long", "message": BLOCK_MESSAGES["too_long"], "resources": []}
    return {"action": "allow", "category": "ok", "message": "", "resources": []}
