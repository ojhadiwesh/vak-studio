"""STORYTELLER: from Claude's reading of a chant (vak/interpret.py) to a narrated story film:
narration script → storyboard → animation plan (silhouette paper-cut style) → vak/narrated.py assembles
title card → narrated story with subtitles → the chant with word captions.

Claude writes a *constrained* storyboard (characters mapped to the renderer's figure roles, setting, poses, actions,
camera); Python turns it into the renderer's plan, so every scene uses only elements that exist.
Guardrails: the story comes only from the cited source in the interpretation (mode "story"); without one the narrator
explains the chant instead (mode "meaning") and no legend is invented. Gods never appear as figures: only as light,
rays, a mandala or a yantra. Cached in knowledge/stories/<hash>.json."""
import hashlib, json, os, time
from typing import List, Literal
from pydantic import BaseModel
from .util import log

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, "knowledge", "stories")
MODEL = os.environ.get("VAK_STORY_MODEL", "claude-opus-5-5")

Role = Literal["sage", "robed_sage", "ascetic", "king", "soldier", "woman"]
Pose = Literal["stand", "point", "raise_staff", "shield", "kneel", "bow", "meditate", "meditate_up", "look_back", "dance", "dance2", "lay_down"]
Mood = Literal["sunset", "gold", "storm", "dusk", "night", "dawn", "forest", "cosmos", "noon"]
Prop = Literal["staff", "sword", "spear", "scarf", "crown"]
Land = Literal["mountains", "river", "tree", "palms", "palace", "hut"]
Extra = Literal["cow", "horse", "army", "birds", "rain", "leaves", "rays", "divine_light", "mandala", "yantra", "stars"]


class Figure(BaseModel):
    character: str            # who this is in the story
    role: Role                # how the paper-cut rig draws them
    x: float                  # 0.12–0.88 across the frame
    facing: Literal["left", "right"]
    pose: Pose
    pose_to: Pose             # same as pose when nothing changes
    change_at: float          # 0–1 through the scene when the pose changes
    walk_to: float            # x to walk to during the scene; equal to x to stay
    props: List[Prop]


class CharacterLook(BaseModel):
    name: str                 # as in the story (never a god or goddess)
    look: str                 # one fixed visual description used in every painting: age, build, face, hair/beard,
                              # clothing and colours, ornaments, what they hold (e.g. "elderly sage, long white beard, ...")


class Scene(BaseModel):
    title: str
    first_line: int           # narration lines this scene covers (0-based, inclusive)
    last_line: int
    mood: Mood
    mood_to: Mood             # the sky at the end of the scene (same as mood when unchanged)
    landscape: List[Land]
    celestial: Literal["sun", "moon", "stars", "none"]
    figures: List[Figure]
    extras: List[Extra]
    light_x: float            # where divine light / rays appear (0–1)
    camera: Literal["push_in", "pull_back", "pan_left", "pan_right", "still"]
    picture: str              # the painting for this scene, style-free: composition, who is where doing what (by name),
                              # setting, time of day, light, mood; 40–80 words; no text; divine presence only as light


class NarrationLine(BaseModel):
    text: str                 # subtitle, with IAST names (Mārkaṇḍeya)
    tts: str                  # the same sentence spelled for an English voice (Markandeya), commas for pauses
    pause: float              # seconds of silence after the line (0.4–1.2)


class StoryFilm(BaseModel):
    mode: Literal["story", "meaning"]
    title: str                # film title, e.g. "Mārkaṇḍeya and the Armour of the Goddess"
    kicker: str               # 1–3 words in Devanagari for the title card
    subtitle: str             # one line under the title
    narration: List[NarrationLine]
    characters: List[CharacterLook]
    scenes: List[Scene]
    chant_picture: str        # a calm painting held while the chant is sung (devotee or seer at dawn, the symbol, light)


SYSTEM = """You turn a chant's interpretation into a short narrated film for a devotional learning app.
The film is: a narrator tells the story (or explains the chant), then the chant itself is heard.
It is drawn as layered paper-cut silhouettes against a painted sky.

Narration:
- 7 to 12 lines, each at most 25 words, warm and simple, in English, for families and learners. About 45–80 seconds.
- mode "story" ONLY if the interpretation has a cited story (story.has_story true). Tell only what that source says
  (frame, legend, characters, setting); you may describe scenery and mood, but add no events, dialogue or names that
  the source does not give. Name the source briefly in the narration when natural ("The Mārkaṇḍeya Purāṇa tells…").
- Otherwise mode "meaning": explain who chants this, what it asks or praises and what its key words mean. No legend.
- The last line leads into the chant ("Listen now to the words…").
- text uses IAST for names; tts spells the same sentence for an English text-to-speech voice (no diacritics:
  Markandeya, Brahma, Shiva), with commas where the voice should pause.

Storyboard (scenes):
- Cover every narration line exactly once, in order, without gaps; each scene covers 1–3 lines.
- Use only the listed roles, poses, props, landscape and extras. At most 3 figures per scene; x between 0.12 and 0.88.
- Roles: rishis and sages → "sage" (beard, staff) or "robed_sage"; a renunciant in meditation → "ascetic";
  kings → "king" (prop "crown"); warriors → "soldier"; women devotees → "woman".
- NEVER draw a god or goddess as a figure (no Brahmā, Śiva, Devī, Viṣṇu as people). Show divine presence as
  "divine_light" (with light_x), "rays", "mandala" or "yantra". A sage may face or bow to the light.
- Keep it gentle and reverent: poses change slowly; at most one walk per scene.
- Choose sky moods that follow the story's arc and end in light (dawn, gold) before the chant.

Pictures (the same story may also be painted as illustrations):
- characters: one fixed look per human character, detailed enough that a painter draws the same person every time
  (age, build, face, hair and beard, clothing with colours, ornaments, what they carry). Traditional Indian dress of the period.
- picture: describe each scene's painting without naming an art style: composition and framing (wide, medium, close),
  who is where and doing what (use the character names), setting, time of day, light and mood, 40–80 words.
  Show at most two people clearly; never show a god or goddess as a person: divine presence is radiant light, rays,
  a glowing yantra or lotus. No text or letters in the picture.
- chant_picture: a calm, luminous closing image for the chant itself."""


def available():
    return bool(os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN"))


def write(interp, force=False, prefer="story"):
    """Claude writes the narration and storyboard from an interpretation (cached)."""
    payload = {k: interp.get(k) for k in ("identification", "genre", "deity_name", "meaning_summary", "dhyana", "story")}
    payload["lines"] = [{"devanagari": l["devanagari"], "english": l["english"]} for l in interp.get("lines", [])]
    if prefer == "meaning":
        payload["requested"] = "meaning narration: explain the chant; do not tell the story even if one is cited"
    k = hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()[:16]
    p = os.path.join(CACHE, k + ".json")
    if not force and os.path.exists(p):
        old = json.load(open(p, encoding="utf-8"))
        if old.get("scenes") and "picture" in old["scenes"][0]:      # written before pictures existed: write again
            return old
    if not available():
        raise RuntimeError("Claude isn't connected: add ANTHROPIC_API_KEY to vak_engine/.env.local")
    import anthropic
    t0 = time.time()
    resp = anthropic.Anthropic().beta.messages.parse(
        model=MODEL, max_tokens=16000,
        betas=["server-side-fallback-2026-07-01"], fallbacks="default",
        output_config={"effort": "high"},
        system=SYSTEM,
        messages=[{"role": "user", "content": "Write the film for this chant. Interpretation:\n\n" + json.dumps(payload, ensure_ascii=False, indent=1)}],
        output_format=StoryFilm,
    )
    if resp.stop_reason == "refusal" or resp.parsed_output is None:
        raise RuntimeError("Claude could not write this story")
    out = resp.parsed_output.model_dump()
    out = repair(out)
    out["_model"], out["_at"] = resp.model, time.strftime("%Y-%m-%d %H:%M")
    os.makedirs(CACHE, exist_ok=True)
    json.dump(out, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    log(f"storyteller: '{out['title']}' ({out['mode']}), {len(out['narration'])} lines, {len(out['scenes'])} scenes "
        f"in {time.time() - t0:.0f}s with {resp.model}")
    return out


def repair(s):
    """Make the scenes cover every narration line once, in order (Claude is asked to; this guarantees it)."""
    n = len(s["narration"]); sc = sorted(s["scenes"], key=lambda x: x["first_line"]); out, nxt = [], 0
    for x in sc:
        a, b = max(nxt, min(x["first_line"], n - 1)), min(max(x["last_line"], x["first_line"]), n - 1)
        if a > b or a >= n:
            continue
        x["first_line"], x["last_line"] = a, b; out.append(x); nxt = b + 1
    if out:
        out[0]["first_line"] = 0
        if nxt < n: out[-1]["last_line"] = n - 1
        for i in range(1, len(out)):                    # close gaps
            out[i]["first_line"] = out[i - 1]["last_line"] + 1
    s["scenes"] = [x for x in out if x["first_line"] <= x["last_line"]]
    return s


# ---------- storyboard → renderer plan (silhouette elements, narration-line anchors) ----------
ROLE = {"sage": "sage", "robed_sage": "vasishtha", "ascetic": "ascetic", "king": "king", "soldier": "soldier", "woman": "dancer"}
CAM = {"push_in": ((1.0, .5, .5), (1.08, .5, .48)), "pull_back": ((1.1, .5, .48), (1.0, .5, .5)), "pan_left": ((1.06, .56, .5), (1.06, .44, .5)),
       "pan_right": ((1.06, .44, .5), (1.06, .56, .5)), "still": ((1.0, .5, .5), (1.03, .5, .5))}


def _anchor(first, last, f):
    """A point f (0–1) through lines first..last, as a narration anchor."""
    pos = first + clampf(f, 0, .999) * (last - first + 1); n = int(pos)
    return {"n": min(n, last), "f": round(pos - n, 3)}


def clampf(x, a, b):
    return max(a, min(b, x))


def plan(story, cast=None):
    cast = cast or {}
    byname = {c["name"]: cid for cid, c in cast.items()}
    scenes, nsc = [], len(story["scenes"])
    for i, sc in enumerate(story["scenes"]):
        a, b = sc["first_line"], sc["last_line"]
        c0, c1 = CAM[sc["camera"]]
        L = [{"el": "sky", "mood": sc["mood"]}]
        if sc["mood_to"] != sc["mood"]:
            L[0].update(moodTo=sc["mood_to"], anim=[{"prop": "moodMix", "from": 0, "to": 1, "at": {"n": a, "f": .2}, "until": {"n": b, "e": "end"}}])
        if sc["celestial"] == "sun": L.append({"el": "sun", "x": .76, "y": .58, "r": 80})
        elif sc["celestial"] == "moon": L.append({"el": "moon", "x": .78, "y": .22, "r": 46})
        if sc["celestial"] == "stars" or "stars" in sc["extras"]: L.append({"el": "stars", "n": 160, "a": .8})
        dl = sc["light_x"] if 0 < sc["light_x"] < 1 else .5
        if "mandala" in sc["extras"]:
            L.append({"el": "mandala", "x": dl, "y": .4, "r": 380, "a": .9, "draw": 0, "anim": [{"prop": "draw", "from": 0, "to": 1, "at": {"n": a, "f": .1}, "until": {"n": b, "e": "end"}}]})
        if "yantra" in sc["extras"]:
            L.append({"el": "yantra", "x": dl, "y": .4, "r": 300, "a": .9, "draw": 0, "anim": [{"prop": "draw", "from": 0, "to": 1, "at": {"n": a, "f": .1}, "until": {"n": b, "e": "end"}}]})
        if "rays" in sc["extras"]: L.append({"el": "rays", "x": dl, "y": .3, "n": 18, "len": 700, "a": .5})
        if "mountains" in sc["landscape"]: L.append({"el": "mountains", "y": .66, "h": 170, "depth": .75, "seed": 3 + i})
        if "palace" in sc["landscape"]: L.append({"el": "palace", "x": .66, "y": .72, "s": .9, "depth": .35})
        if "tree" in sc["landscape"]: L.append({"el": "tree", "x": .12 if i % 2 else .88, "y": .88, "s": 1.0, "depth": .2})
        if "palms" in sc["landscape"]: L.append({"el": "palm", "x": .9 if i % 2 else .08, "y": .88, "s": .9, "depth": .25})
        if "river" in sc["landscape"]: L.append({"el": "river", "y": .8})
        if "hut" in sc["landscape"]: L.append({"el": "hut", "x": .74, "y": .86, "s": .8, "depth": .3})
        if "birds" in sc["extras"]: L.append({"el": "birds", "y": .25, "n": 6, "fly": 0, "s": .8, "anim": [{"prop": "fly", "from": 0, "to": 1, "at": {"n": a}, "until": {"n": b, "e": "end"}, "ease": "linear"}]})
        L.append({"el": "ground", "y": .86})
        if "divine_light" in sc["extras"]:
            L.append({"el": "point", "x": dl, "y": .34, "r": 240, "a": 0, "anim": [{"prop": "a", "from": 0, "to": 1, "at": {"n": a, "f": .15}, "until": {"n": a, "f": .7}}]})
            L.append({"el": "beam", "x": dl, "y1": .4, "a": 0, "anim": [{"prop": "a", "from": 0, "to": .6, "at": {"n": a, "f": .3}, "until": {"n": b, "e": "end"}}]})
        if "army" in sc["extras"]:
            L.append({"el": "army", "x": .06, "y": .9, "s": .5, "n": 5, "gap": .055, "walk": 1, "anim": [{"prop": "x", "from": .02, "to": .18, "at": {"n": a}, "until": {"n": b, "e": "end"}, "ease": "linear"}]})
        if "cow" in sc["extras"]: L.append({"el": "cow", "x": .84, "y": .9, "s": .7, "dir": -1})
        if "horse" in sc["extras"]: L.append({"el": "horse", "x": .2, "y": .9, "s": .8, "dir": 1, "rider": "king"})
        for f in sc["figures"][:3]:
            x = clampf(f["x"], .1, .9)
            cid = byname.get(f["character"]) or (f["character"].lower() if f["character"].lower() in cast else None)
            if cid:                                   # this chant's own character, designed by vak/cast.py
                g = {"el": "cast", "id": cid, "x": x, "y": .9, "s": .92, "dir": 1 if f["facing"] == "right" else -1, "pose": f["pose"], "anim": []}
            else:
                g = {"el": "figure", "role": ROLE[f["role"]], "x": x, "y": .9, "s": .92, "dir": 1 if f["facing"] == "right" else -1, "pose": f["pose"], "anim": []}
                for pr in f["props"]:
                    g[pr] = 1
                if f["role"] in ("sage", "robed_sage", "ascetic"): g["beard"] = 1
                if f["role"] == "king" and "crown" not in f["props"]: g["crown"] = 0
            if f["pose_to"] != f["pose"]:
                g["anim"].append({"prop": "pose", "from": f["pose"], "to": f["pose_to"], "at": _anchor(a, b, f["change_at"]), "until": _anchor(a, b, min(.99, f["change_at"] + .12))})
            if abs(f["walk_to"] - x) > .03:
                g["walk"] = 1
                g["anim"].append({"prop": "x", "from": x, "to": clampf(f["walk_to"], .1, .9), "at": {"n": a, "f": .05}, "until": _anchor(a, b, .7), "ease": "linear"})
            if not g["anim"]: g.pop("anim")
            L.append(g)
        if "leaves" in sc["extras"]: L.append({"el": "leaves", "n": 30})
        if "rain" in sc["extras"]: L.append({"el": "rain", "a": .6})
        scenes.append({"id": f"S{i + 1:02d}", "title": sc["title"],
                       "from": 0 if i == 0 else {"n": a, "d": -.3},
                       "to": {"n": b + 1, "d": -.3} if i < nsc - 1 else {"n": b, "e": "end", "d": 1.0},
                       "fade_in": 0 if i == 0 else .4, "fade_out": .4,
                       "camera": {"from": {"zoom": c0[0], "x": c0[1], "y": c0[2]}, "to": {"zoom": c1[0], "x": c1[1], "y": c1[2]}},
                       "layers": L})
    out = {"about": f"Story plan written by Claude ({story.get('_model', '')}) from the chant's interpretation; mode {story['mode']}.", "scenes": scenes}
    if cast:
        out["cast"] = cast
    return out


def mantra_plan(duration, hero="ascetic", cast=None):
    """The chant part (recording time): night sky turning to dawn, a mandala drawing itself, each sung word in light,
    a seer in meditation below. No deity as a figure."""
    d = round(duration + 1.0, 2)
    return {"scenes": [{"id": "M1", "title": "The chant", "from": 0, "to": d, "fade_in": .6, "fade_out": .6,
                        "camera": {"from": {"zoom": 1.0, "x": .5, "y": .5}, "to": {"zoom": 1.06, "x": .5, "y": .48}},
                        "layers": [{"el": "sky", "mood": "cosmos", "moodTo": "dawn", "anim": [{"prop": "moodMix", "from": 0, "to": 1, "at": 0, "until": d}]},
                                   {"el": "stars", "n": 220, "a": .8},
                                   {"el": "mandala", "x": .5, "y": .42, "r": 430, "a": .85, "draw": 0, "anim": [{"prop": "draw", "from": 0, "to": 1, "at": 0, "until": round(d * .6, 2)}]},
                                   {"el": "word", "x": .5, "y": .4, "size": 140},
                                   ({"el": "cast", "id": hero, "x": .5, "y": .97, "s": .75, "dir": 1, "pose": "meditate_up", "headGlow": .8} if cast
                                    else {"el": "figure", "role": hero, "x": .5, "y": .97, "s": .75, "dir": 1, "pose": "meditate_up", "beard": 1, "headGlow": .8})]}],
            **({"cast": cast} if cast else {})}


def narration_cfg(story):
    """Narrator: ElevenLabs (English storyteller voice) when connected, otherwise the free Indian-English neural voice."""
    from . import eleven
    lines = [{"text": l["text"], "tts": l["tts"], "pause": clampf(l.get("pause", .6), .3, 1.4)} for l in story["narration"]]
    if eleven.available():
        return {"engine": "eleven", "lines": lines, "gap": .6}
    return {"engine": "edge", "voice": "en-IN-PrabhatNeural", "rate": "-4%", "pitch": "-2Hz", "lines": lines, "gap": .6}


def apply(project_json, story, duration, style="silhouette", cast=None):
    """Turn a chant project into a narrated story film: silhouette (code-drawn) or a storybook painting style."""
    d = os.path.dirname(project_json); cfg = json.load(open(project_json, encoding="utf-8"))
    json.dump(story, open(os.path.join(d, "story.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    json.dump(plan(story, cast), open(os.path.join(d, "story_plan.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    if cast:                                          # the seer of the closing scene: the character seen most often
        seen = [f["character"] for sc in story["scenes"] for f in sc["figures"]]
        byname = {c["name"]: cid for cid, c in cast.items()}
        hero = max(cast, key=lambda cid: sum(1 for n in seen if byname.get(n) == cid))
    else:
        hero = next((ROLE[f["role"]] for sc in story["scenes"] for f in sc["figures"] if f["role"] in ("sage", "robed_sage", "ascetic")), "ascetic")
    json.dump(mantra_plan(duration, hero, cast), open(os.path.join(d, "mantra_plan.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    cfg.update(style=style, narration=narration_cfg(story), animation="story_plan.json", mantra_animation="mantra_plan.json",
               track_from=0.0, story="story.json")
    if style != "silhouette":
        cfg["storybook"] = True
    cfg["card"] = {"kicker": story["kicker"], "chapter": "", "title": story["title"], "sub": story["subtitle"]}
    json.dump(cfg, open(project_json, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    log(f"storyteller: project set up as a narrated {story['mode']} film ({len(story['scenes'])} scenes) -> {project_json}")
