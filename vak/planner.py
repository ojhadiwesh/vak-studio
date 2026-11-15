"""PLANNER (rule-based stand-in): chant units -> a style's animation plan, with no LLM.

Until the Claude "Planner" is wired in (needs ANTHROPIC_API_KEY; see docs/ANIMATION_ENGINE.md), this writes a
meaning-neutral devotional plan for any chant: night by the river -> dawn -> full light, one scene per group of
units, every time anchored to the chant's words ({u, w, e, d}) so a new recording re-times it automatically.
It never invents a story (guardrail: no purāṇic narrative without a cited source); it shows the practice and its
symbols: a seeker at the river, the rising sun, the sung word written in light, a mandala/yantra, a lotus.

    plan(units, style)            -> {"about", "scenes": [...]}   (style: "shadow_puppet" | "silhouette" | ...)
    summary(plan)                 -> [{id, title, units}] for review screens
"""
import copy

STYLES = ("yantra", "shadow_puppet", "silhouette", "pattachitra_anim")
FAR = 99999.0


def U(u, w=None, e=None, d=0.0, f=None):
    a = {"u": u}
    if w is not None: a["w"] = w
    if e: a["e"] = e
    if f is not None: a["f"] = f
    if d: a["d"] = round(d, 3)
    return a


def _syl(u):
    return sum(w.get("syl", 1) for w in u["words"])


def groups(units, target=6.0, sec_per_syl=0.32):
    """Consecutive 1-based unit indices per scene, ~target seconds each (estimated from syllables, so no timings
    are needed: the plan can be reviewed before the recording is aligned)."""
    if len(units) <= 12:                       # short chants: one scene per chanted line
        return [[i] for i in range(1, len(units) + 1)]
    out, cur, est = [], [], 0.0
    for i, u in enumerate(units, 1):
        cur.append(i); est += _syl(u) * sec_per_syl + 0.6
        nxt = units[i] if i < len(units) else None
        verse_end = nxt is None or nxt.get("verse") != u.get("verse")
        if est >= target or (verse_end and est >= target * 0.6) or nxt is None:
            out.append(cur); cur, est = [], 0.0
    return out


def _word_keys(us, units, lo, hi, last=None):
    """Keyframes that pulse a value on every word of the given units: rise to hi at each word, settle to lo."""
    keys = []
    for ui in us:
        for k in range(len(units[ui - 1]["words"])):
            keys += [[U(ui, k), lo], [U(ui, k, d=0.3), hi]]
    keys.append([U(us[-1], e="end"), last if last is not None else lo])
    return keys


def _title(units, us):
    eng = " ".join(units[i - 1].get("english", "") for i in us).strip()
    iast = " ".join(units[i - 1].get("iast", "") for i in us)
    eng = eng if len(eng) <= 60 else eng[:57].rsplit(" ", 1)[0] + "…"
    iast = iast if len(iast) <= 50 else iast[:47].rsplit(" ", 1)[0] + "…"
    return iast + (": " + eng if eng else "")


def _cam(k, a=1.0, b=1.08):
    return ({"from": {"zoom": a, "x": 0.5, "y": 0.5}, "to": {"zoom": b, "x": 0.48, "y": 0.48}} if k % 2 == 0 else
            {"from": {"zoom": b, "x": 0.5, "y": 0.47}, "to": {"zoom": a, "x": 0.5, "y": 0.5}})


# ---------------------------------------------------------------- shadow puppets
def _sp_open(units):
    return {"title": "Night on the river; the seeker comes to the ghat", "camera": {"from": {"zoom": 1.0, "x": 0.5, "y": 0.5}, "to": {"zoom": 1.08, "x": 0.47, "y": 0.5}},
            "layers": [
                {"el": "screen", "day": 0.0, "anim": [{"prop": "day", "from": 0.0, "to": 0.12, "at": U(1, d=-6), "until": U(1)}]},
                {"el": "stars", "n": 170, "a": 1}, {"el": "moon", "x": 0.8, "y": 0.17, "s": 1},
                {"el": "temple", "x": 0.72, "y": 0.57, "s": 0.55}, {"el": "palm", "x": 0.93, "y": 0.62, "s": 1.1, "dir": -1},
                {"el": "ghat", "x": 0.44, "y": 0.5, "s": 0.9}, {"el": "diya", "x": 0.47, "y": 0.495, "s": 0.8},
                {"el": "sage", "x": 0.3, "y": 0.5, "s": 0.55, "pot": 1, "walk": 0, "pace": 0.9, "pose": "stand", "anim": [
                    {"prop": "x", "from": 0.06, "to": 0.3, "at": U(1, d=-6.5), "until": U(1, d=-1.9), "ease": "linear", "hold_before": 1},
                    {"prop": "walk", "from": 1, "to": 0, "at": U(1, d=-2.3), "until": U(1, d=-1.8), "hold_before": 1},
                    {"prop": "pose", "from": "stand", "to": "pray", "at": U(1, d=-1.8), "until": U(1, d=-0.9)}]},
                {"el": "river", "y": 0.66, "day": 0.0}]}


def _sp_scene(kind, us, units, d0, d1):
    a, b = U(us[0]), U(us[-1], e="end")
    day = {"el": "screen", "day": d0, "anim": [{"prop": "day", "from": d0, "to": d1, "at": a, "until": b}]}
    sx, sy = 0.78 - 0.25 * d1, 0.55 - 0.3 * d1
    if kind == "raise":
        return {"title": "He stands in the river and raises his hands", "layers": [day,
                {"el": "stars", "n": 120, "a": max(0.1, 0.8 - d0), "anim": [{"prop": "a", "from": max(0.1, 0.8 - d0), "to": max(0.0, 0.5 - d1), "at": a, "until": b}]},
                {"el": "sage", "x": 0.5, "y": 0.83, "s": 0.72, "pose": "stand", "anim": [{"prop": "pose", "from": "stand", "to": "raise", "at": U(us[0], d=0.4), "until": U(us[0], d=2.6)}]},
                {"el": "river", "y": 0.63, "day": d0}]}
    if kind == "sunrise":
        return {"title": "The sun rises", "layers": [day, {"el": "hills", "y": 0.64, "color": "#4b6a2a"},
                {"el": "sun", "x": 0.5, "y": 0.78, "s": 1.1, "rays": 0, "glow": 0.4, "anim": [
                    {"prop": "y", "from": 0.78, "to": 0.36, "at": a, "until": b, "ease": "out"},
                    {"prop": "rays", "from": 0, "to": 1, "at": U(us[0], d=0.9), "until": b},
                    {"prop": "glow", "from": 0.4, "to": 1, "at": U(us[0], d=0.5), "until": b}]},
                {"el": "river", "y": 0.66, "day": 0.6, "glitter": 0, "gx": 0.5, "anim": [{"prop": "glitter", "from": 0, "to": 1, "at": U(us[0], d=1.2), "until": b}]},
                {"el": "sage", "x": 0.2, "y": 0.86, "s": 0.4, "pose": "raise", "rods": False}]}
    if kind == "meditate":
        return {"title": "Meditating on the radiance", "layers": [day,
                {"el": "sun", "x": 0.7, "y": 0.3, "s": 1.25, "rays": 1, "glow": 0.6, "anim": [{"prop": "glow", "keys": _word_keys(us, units, 0.65, 1.05, 0.9)}]},
                {"el": "river", "y": 0.7, "day": d1, "glitter": 0.8, "gx": 0.7},
                {"el": "ghat", "x": 0.56, "y": 0.6, "s": 1.0}, {"el": "sage", "x": 0.47, "y": 0.6, "s": 0.68, "pose": "meditate"}]}
    if kind == "offer":
        return {"title": "The water offering to the sun", "layers": [day,
                {"el": "sun", "x": 0.78, "y": 0.27, "s": 1.0, "rays": 1, "glow": 0.9},
                {"el": "sage", "x": 0.42, "y": 0.9, "s": 0.72, "pose": "raise", "pot": 1, "pour": 0, "rods": True, "anim": [
                    {"prop": "pose", "from": "raise", "to": "offer", "at": a, "until": U(us[0], d=1.0)},
                    {"prop": "pour", "from": 0, "to": 1, "at": U(us[0], d=1.2), "until": U(us[0], d=2.4)}]},
                {"el": "river", "y": 0.66, "day": d1, "glitter": 1, "gx": 0.6}]}
    if kind == "lotus":
        lw = len(units[us[-1] - 1]["words"]) - 1
        return {"title": "The lotus opens, the egrets rise", "layers": [day,
                {"el": "sun", "x": 0.82, "y": 0.2, "s": 0.8, "rays": 1, "glow": 0.8},
                {"el": "egrets", "y": 0.3, "n": 6, "fly": 0, "anim": [{"prop": "fly", "from": 0, "to": 1, "at": U(us[0], d=0.4), "until": b, "ease": "linear"}]},
                {"el": "river", "y": 0.62, "day": d1, "glitter": 0.7, "gx": 0.8},
                {"el": "lotus", "x": 0.5, "y": 0.7, "s": 2.0, "open": 0, "rise": 0, "anim": [
                    {"prop": "rise", "from": 0, "to": 1, "at": a, "until": U(us[0], d=1.2)},
                    {"prop": "open", "from": 0, "to": 1, "at": U(us[-1], max(0, lw)), "until": b}]}]}
    if kind == "ghat":
        return {"title": "Prayer at the ghat, the lamp burning", "layers": [day,
                {"el": "sun", "x": sx, "y": sy, "s": 0.9, "rays": 1, "glow": 0.7, "a": min(1, d0 * 2)},
                {"el": "temple", "x": 0.72, "y": 0.57, "s": 0.55}, {"el": "palm", "x": 0.93, "y": 0.62, "s": 1.1, "dir": -1},
                {"el": "ghat", "x": 0.44, "y": 0.5, "s": 0.9}, {"el": "diya", "x": 0.47, "y": 0.495, "s": 0.8},
                {"el": "sage", "x": 0.3, "y": 0.5, "s": 0.55, "pose": "pray"},
                {"el": "river", "y": 0.66, "day": d1, "glitter": d1 * 0.8, "gx": sx}]}
    # closing
    return {"title": "Closing: the whole scene in full light", "layers": [{"el": "screen", "day": 1.0},
            {"el": "sun", "x": 0.5, "y": 0.24, "s": 0.9, "rays": 1, "glow": 1},
            {"el": "temple", "x": 0.8, "y": 0.6, "s": 0.6}, {"el": "palm", "x": 0.08, "y": 0.64, "s": 1.0},
            {"el": "egrets", "y": 0.18, "n": 4, "fly": 0.2, "anim": [{"prop": "fly", "from": 0.2, "to": 0.9, "at": a, "until": U(us[-1], e="end", d=4), "ease": "linear"}]},
            {"el": "sage", "x": 0.5, "y": 0.86, "s": 0.46, "pose": "pray", "rods": False},
            {"el": "river", "y": 0.66, "day": 1.0, "glitter": 0.9, "gx": 0.5}]}


SP_CYCLE = ["sunrise", "meditate", "offer", "lotus", "ghat"]


# ---------------------------------------------------------------- silhouette paper-cut + sacred geometry
SAGE = {"el": "figure", "role": "ascetic", "dir": 1, "beard": 1, "jata": 1.1}


def _si_open(units):
    return {"title": "Night; the seeker sits by the river", "camera": {"from": {"zoom": 1.0, "x": 0.5, "y": 0.5}, "to": {"zoom": 1.06, "x": 0.48, "y": 0.5}},
            "layers": [
                {"el": "sky", "mood": "night", "moodTo": "dawn", "moodMix": 0, "horizon": 0.66, "anim": [{"prop": "moodMix", "from": 0, "to": 0.25, "at": U(1, d=-8), "until": U(1)}]},
                {"el": "stars", "n": 200, "a": 0.9}, {"el": "moon", "x": 0.78, "y": 0.18, "s": 1},
                {"el": "mountains", "y": 0.62, "h": 150, "depth": 0.7, "seed": 4},
                {"el": "river", "y": 0.68},
                {"el": "tree", "x": 0.86, "y": 0.92, "s": 0.9, "depth": 0.1, "seed": 11},
                {"el": "ground", "y": 0.9, "depth": 0},
                dict(SAGE, x=0.3, y=0.92, s=0.62, pose="stand", walk=0, anim=[
                    {"prop": "x", "from": 0.05, "to": 0.3, "at": U(1, d=-7), "until": U(1, d=-2.4), "ease": "linear", "hold_before": 1},
                    {"prop": "walk", "from": 1, "to": 0, "at": U(1, d=-2.8), "until": U(1, d=-2.3), "hold_before": 1},
                    {"prop": "pose", "from": "stand", "to": "meditate", "at": U(1, d=-2.2), "until": U(1, d=-0.8)}])]}


def _si_scene(kind, us, units, d0, d1):
    a, b = U(us[0]), U(us[-1], e="end")
    words = [{"el": "word", "unit": i, "x": 0.5, "y": 0.4 if kind in ("mandala", "pulse") else 0.16, "size": 150 if kind in ("mandala", "pulse") else 110} for i in us]
    sage = dict(SAGE, x=0.5, y=0.97, s=0.75, pose="meditate_up", headGlow=0.6 + 0.4 * d1)
    if kind == "landscape":
        mood = {"el": "sky", "mood": "dawn", "moodTo": "gold", "moodMix": d0, "horizon": 0.66, "anim": [{"prop": "moodMix", "from": d0, "to": d1, "at": a, "until": b}]}
        return {"title": "Dawn over the river; the sung word written in light", "layers": [mood,
                {"el": "stars", "n": 160, "a": max(0, 0.6 - d0), "anim": [{"prop": "a", "from": max(0, 0.6 - d0), "to": 0, "at": a, "until": b}]},
                {"el": "sun", "x": 0.62, "y": 0.66 - 0.2 * d0, "r": 70, "a": 1, "anim": [{"prop": "y", "from": 0.66 - 0.2 * d0, "to": 0.58 - 0.25 * d1, "at": a, "until": b, "ease": "out"}]},
                {"el": "mountains", "y": 0.62, "h": 150, "depth": 0.7, "seed": 4},
                {"el": "river", "y": 0.68},
                {"el": "birds", "y": 0.3, "n": 7, "fly": 0, "anim": [{"prop": "fly", "from": 0, "to": 1, "at": U(us[0], d=0.3), "until": b, "ease": "linear"}]},
                {"el": "tree", "x": 0.86, "y": 0.92, "s": 0.9, "depth": 0.1, "seed": 11},
                {"el": "ground", "y": 0.9, "depth": 0},
                dict(SAGE, x=0.3, y=0.92, s=0.62, pose="meditate_up", headGlow=0.3 + 0.5 * d1), *words]}
    cosmos = {"el": "sky", "mood": "cosmos", "moodTo": "dawn", "moodMix": d0 * 0.5, "anim": [{"prop": "moodMix", "from": d0 * 0.5, "to": d1 * 0.5, "at": a, "until": b}]}
    stars = {"el": "stars", "n": 220, "a": 0.8 - 0.5 * d0}
    if kind == "mandala":
        return {"title": "The mandala unfolds with the chant", "layers": [cosmos, stars,
                {"el": "mandala", "x": 0.5, "y": 0.42, "r": 430, "a": 1, "draw": 0, "pulse": 1, "anim": [
                    {"prop": "draw", "from": 0, "to": 1, "at": a, "until": b, "ease": "linear"},
                    {"prop": "pulse", "keys": _word_keys(us, units, 0.6, 1.4, 1.0)}]}, *words, sage]}
    if kind == "yantra":
        return {"title": "The sun's yantra draws itself", "layers": [cosmos, stars,
                {"el": "rays", "x": 0.5, "y": 0.42, "n": 12, "len": 900, "a": 0, "spin": 0.08, "anim": [{"prop": "a", "from": 0, "to": 1, "at": a, "until": U(us[0], d=2)}]},
                {"el": "yantra", "x": 0.5, "y": 0.42, "r": 300, "draw": 0, "anim": [{"prop": "draw", "from": 0, "to": 1, "at": a, "until": b, "ease": "linear"}]}, *words, sage]}
    if kind == "pulse":
        return {"title": "The radiance pulses on each word", "layers": [cosmos, stars,
                {"el": "rays", "x": 0.5, "y": 0.42, "n": 12, "len": 900, "a": 1, "spin": 0.08},
                {"el": "yantra", "x": 0.5, "y": 0.42, "r": 300, "draw": 1, "pulse": 0, "a": 0.7, "anim": [{"prop": "pulse", "keys": _word_keys(us, units, 0.1, 1.1, 0.6)}]},
                *words, sage]}
    if kind == "beam":
        return {"title": "The light enters the mind; the petals open", "layers": [cosmos, stars,
                {"el": "mandala", "x": 0.5, "y": 0.62, "r": 520, "a": 1, "draw": 0, "anim": [{"prop": "draw", "from": 0, "to": 1, "at": U(us[0], d=0.5), "until": b}]},
                {"el": "beam", "x": 0.5, "y0": -0.1, "y1": 0.58, "a": 0, "anim": [{"prop": "a", "from": 0, "to": 1, "at": a, "until": U(us[0], e="end")}]},
                *[dict(w, y=0.24) for w in words],
                dict(sage, s=1.05, headGlow=0.6, anim=[{"prop": "headGlow", "from": 0.6, "to": 1.6, "at": a, "until": b}])]}
    # closing: all becomes one point of light
    return {"title": "Closing: all becomes one point of light", "layers": [
            {"el": "sky", "mood": "dawn", "moodTo": "gold", "moodMix": 0.6, "anim": [{"prop": "moodMix", "from": 0.6, "to": 1, "at": a, "until": U(us[-1], e="end", d=3)}]},
            {"el": "mandala", "x": 0.5, "y": 0.62, "r": 520, "a": 1, "draw": 1, "anim": [{"prop": "a", "from": 1, "to": 0.2, "at": U(us[-1], e="end"), "until": U(us[-1], e="end", d=3)}]},
            {"el": "sun", "x": 0.5, "y": 0.62, "r": 60, "glow": 1, "a": 1},
            {"el": "point", "x": 0.5, "y": 0.62, "r": 300, "a": 0, "anim": [{"prop": "a", "from": 0, "to": 1, "at": U(us[-1], e="end", d=-0.5), "until": U(us[-1], e="end", d=2.5)}]},
            *[dict(w, y=0.24) for w in words],
            dict(sage, s=1.05, pose="meditate", headGlow=1)]}


SI_CYCLE = ["mandala", "landscape", "yantra", "pulse", "beam"]


def family(style):
    if style == "yantra":
        return "yantra"
    return "silhouette" if style in ("silhouette", "pattachitra_anim") else "shadow_puppet"


# ---------------------------------------------------------------- yantra + akshara (figure-free, for chants without a story)
# deity → yantra kind, symbol set and palette. Detected from the chant's own words; symbols only, never a figure.
DEITIES = [
    ("shiva", ["शिव", "त्र्यम्बक", "रुद्र", "महादेव", "शम्भ", "शङ्कर", "नीलकण्ठ", "पशुपत"], "hex", ["om", "crescent", "trishula", "bilva"], "Śiva"),
    ("devi", ["देव्य", "देवी", "दुर्ग", "चण्डिक", "काल्य", "काली", "लक्ष्म", "सरस्वत", "अम्ब", "भवान", "श्रीं", "ह्रीं"], "shri", ["om", "trishula", "lotus", "flame"], "the Goddess"),
    ("vishnu", ["नारायण", "विष्णु", "कृष्ण", "राम", "हरे", "गोविन्द", "वासुदेव", "माधव", "केशव"], "lotus", ["om", "shankha", "chakra", "lotus"], "Viṣṇu"),
    ("ganesha", ["गण", "गं", "विनायक", "वक्रतुण्ड", "एकदन्त", "लम्बोदर"], "hex", ["om", "bija:गं", "lotus", "flame"], "Gaṇeśa"),
    ("surya", ["सवितु", "सूर्य", "भर्ग", "आदित्य", "भास्कर", "मित्र", "रवि"], "sun", ["om", "sun", "lotus", "flame"], "the Sun"),
]


def deity(units):
    """(key, kind, symbols, label) for the deity the chant addresses; 'peace' when none is named."""
    text = " ".join(u["devanagari"] for u in units)
    best, score = None, 0
    for key, stems, kind, syms, label in DEITIES:
        n = sum(text.count(s) for s in stems)
        if n > score:
            best, score = (key, kind, syms, label), n
    return best or ("peace", "lotus", ["om", "lotus", "flame", "sun"], "peace")


def _yantra_plan(units):
    key, kind, syms, label = deity(units)
    gs = groups(units)
    n = len(gs)
    last = gs[-1][-1]
    end = U(last, e="end", d=3.0)

    def layers(i, a, b, draw0, draw1, mix0, mix1, extra=()):
        return [
            {"el": "field", "pal": key, "mix": mix0, "anim": [{"prop": "mix", "from": mix0, "to": mix1, "at": a, "until": b}]},
            {"el": "embers", "pal": key, "n": 60},
            {"el": "ripples", "pal": key, "x": 0.5, "y": 0.4},
            {"el": "geometry", "pal": key, "kind": kind, "x": 0.5, "y": 0.4, "r": 290, "draw": draw0,
             "anim": [{"prop": "draw", "from": draw0, "to": draw1, "at": a, "until": b, "ease": "linear"}]},
            {"el": "symbols", "pal": key, "set": syms, "x": 0.5, "y": 0.4, "r": 290, "focus": i % len(syms), "show": 1},
            {"el": "word", "pal": key, "x": 0.5, "y": 0.4},
            *extra]

    # the yantra is fully drawn by ~40% of the chant; light grows through it
    prog = lambda k: k / n
    draw = lambda k: min(1.0, 0.15 + 0.85 * prog(k) / 0.4)
    scenes = [{"id": "P0", "title": f"The yantra of {label} begins to draw itself", "units": [],
               "camera": {"from": {"zoom": 1.06, "x": 0.5, "y": 0.47}, "to": {"zoom": 1.0, "x": 0.5, "y": 0.5}},
               "layers": [l for l in layers(0, U(1, d=-14), U(1), 0.0, 0.15, 0.0, 0.0) if l["el"] != "symbols"]
               + [{"el": "symbols", "pal": key, "set": syms, "x": 0.5, "y": 0.4, "r": 290, "focus": 0, "show": 0,
                   "anim": [{"prop": "show", "from": 0, "to": 1, "at": U(1, d=-3), "until": U(1)}]}]}]
    for i, us in enumerate(gs):
        a = U(us[0], d=-0.35)
        b = U(gs[i + 1][0], d=-0.35) if i + 1 < n else end
        extra = []
        if i == n - 1:      # closing: everything gathers into one point of light
            extra = [{"el": "bindu", "pal": key, "x": 0.5, "y": 0.4, "a": 0, "anim": [{"prop": "a", "from": 0, "to": 0.9, "at": U(last, e="end", d=-0.3), "until": U(last, e="end", d=2.4)}]}]
        z0, z1 = 1.0 + 0.06 * prog(i), 1.0 + 0.06 * prog(i + 1)
        scenes.append({"id": f"P{i + 1}", "title": f"Line {i + 1}: {_title(units, us)}", "units": us,
                       "camera": {"from": {"zoom": z0, "x": 0.5, "y": 0.5}, "to": {"zoom": z1, "x": 0.5, "y": 0.5}, "ease": "linear"},
                       "fade_in": 0, "fade_out": 0,
                       "layers": layers(i, a, b, draw(i), draw(i + 1), 0.15 + 0.85 * prog(i), 0.15 + 0.85 * prog(i + 1), extra)})
    for i, sc in enumerate(scenes):
        sc["from"] = -FAR if i == 0 else U(sc["units"][0], d=-0.35)
    for i, sc in enumerate(scenes):
        sc["to"] = scenes[i + 1]["from"] if i + 1 < len(scenes) else FAR
    scenes[0]["fade_in"] = 0.8; scenes[0]["fade_out"] = 0
    return {"about": f"Rule-based Yantra + Akshara plan for {len(units)} units, addressed to {label} (detected from the words); "
                     "figure-free. Times are anchored to chant words {u, w, e, d}.",
            "planner": "rules-v1", "style_family": "yantra", "deity": key, "scenes": scenes}


def plan(units, style):
    """Return an animation plan for `units` (storyboard units, 1-based in anchors) in a code-drawn style."""
    if not units:
        raise ValueError("no units to plan")
    fam = family(style)
    if fam == "yantra":
        return _yantra_plan(units)
    gs = groups(units)
    n = len(gs)
    scenes = [dict(_sp_open(units) if fam == "shadow_puppet" else _si_open(units), id="P0")]
    k = 0
    for i, us in enumerate(gs):
        d0, d1 = 0.12 + 0.88 * i / n, 0.12 + 0.88 * (i + 1) / n
        first_word = units[us[0] - 1]["words"][0]["dev"]
        if i == n - 1 and n > 1:
            kind = "closing"
        elif fam == "shadow_puppet" and i == 0 and first_word == "ॐ":
            kind = "raise"
        else:
            kind = (SP_CYCLE if fam == "shadow_puppet" else SI_CYCLE)[k % 5]; k += 1
        sc = (_sp_scene if fam == "shadow_puppet" else _si_scene)(kind, us, units, d0, d1)
        sc.setdefault("camera", _cam(i))
        sc["id"] = f"P{i + 1}"
        sc["title"] = f"{sc['title']} ({_title(units, us)})"
        sc["units"] = us
        scenes.append(sc)
    # scene boundaries: just before each group's first unit; the first and last scenes cover the whole film
    for i, sc in enumerate(scenes):
        sc["from"] = -FAR if i == 0 else U(sc["units"][0], d=-0.35)
        sc.setdefault("fade_in", 0.5 if i else 0.8); sc.setdefault("fade_out", 0.35)
    for i, sc in enumerate(scenes):
        sc["to"] = scenes[i + 1]["from"] if i + 1 < len(scenes) else FAR
    scenes[-1]["fade_out"] = 0
    return {"about": f"Rule-based plan ({fam} family) written by vak/planner.py for {len(units)} units; replace with the "
                     "Claude Planner's output when an API key is set. Times are anchored to chant words {u, w, e, d}.",
            "planner": "rules-v1", "style_family": fam, "scenes": scenes}


def summary(p):
    return [{"id": s["id"], "title": s.get("title", ""), "units": s.get("units", [])} for s in p["scenes"]]
