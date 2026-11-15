"""CAST: characters designed for each chant, from its context, as paper-cut silhouettes (no fixed character list).

Claude reads the story and the character bible (vak/storyteller.py) and draws every human character as SVG paths,
one per body part, each in that part's own pivot frame. The silhouette renderer (assets/anim/silhouette.js, element
"cast") assembles them on the shared skeleton, so every pose, the walk, breathing and rim light work for any character.

Then a render-and-review loop: the engine draws each character in four poses, Claude looks at the sheet and redraws a
character that is broken or doesn't read (a detached limb, an unclear outline, a costume that contradicts the bible).
Gods and goddesses are never designed here: they appear only as light unless a reviewed iconography exists.
Cached in knowledge/cast/<hash>.json; a character once drawn can be reused by later chants."""
import base64, hashlib, json, os, shutil, subprocess, tempfile, time
from typing import List
from pydantic import BaseModel
from .util import ASSETS, log, sh

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, "knowledge", "cast")
MODEL = os.environ.get("VAK_CAST_MODEL", "claude-opus-5-5")
PARTS = ("back", "torso", "head", "upper_arm", "forearm", "held", "thigh", "shin", "lower", "lap")


class Part(BaseModel):
    d: str        # SVG path data (absolute commands M L C Q Z), in this part's own frame; "" = use the default shape
    cut: str      # optional ornament holes (paper-cut lace: eyes of a mala, border pattern), same frame; "" if none


class CharacterArt(BaseModel):
    id: str               # short lowercase id, e.g. "agastya"
    name: str             # as in the story
    design_notes: str     # what makes this figure recognisable in outline (headdress, garment, object, build)
    back: Part
    torso: Part
    head: Part
    upper_arm: Part
    forearm: Part
    held: Part
    thigh: Part
    shin: Part
    lower: Part
    lap: Part


class Cast(BaseModel):
    characters: List[CharacterArt]


class Verdict(BaseModel):
    id: str
    ok: bool
    problems: str          # what to fix, concretely ("" when ok)


class Review(BaseModel):
    characters: List[Verdict]


RIG = """THE RIG (all numbers are canvas units; a standing figure is about 400 tall; the figure FACES RIGHT (+x); y points DOWN).
Every part is drawn as filled SVG path data in ITS OWN frame, with the origin at its pivot joint. Use absolute commands
(M, L, C, Q, Z), closed shapes, integers. Keep within the bounds given so the parts meet at the joints.

- torso   origin = hip joint. From the waist/belt at y=+10 up to the shoulders at about y=-175; x within -50..+50.
          The neck starts at about (6,-175). Include chest garments, upper cloth, sacred thread, beads as part of the outline.
          Default (a bare-chested man): M -30 8 L 30 8 L 25 -40 L 34 -108 L 44 -148 L 26 -166 L 10 -174 L -12 -174 L -30 -164 L -42 -146 L -35 -108 L -26 -40 Z
- head    origin = top of the neck at the head pivot. The neck occupies y 0..+14 below it. The skull spans y about 0..-75,
          the face is on the RIGHT (nose at about x=+34, y=-30; chin at about x=+20, y=0). Hair, topknot, jaṭā, crown or veil
          may rise to y=-170 and fall behind to x=-70; a beard may hang to y=+110.
          Default (a man in profile): M -18 4 L 16 2 L 20 -16 L 36 -26 L 31 -32 L 33 -44 L 22 -64 L -2 -72 L -22 -60 L -26 -30 Z
- upper_arm  origin = shoulder. A limb hanging straight down to the elbow at y=+76, about 20 wide (x -11..+11). Sleeves and
          armlets belong here.
- forearm origin = elbow. Hangs down to the wrist at y=+72, then the HAND to about y=+96 (x -12..+16). Bracelets here.
- held    the object in the near hand; origin = the palm (76 below the elbow, along the forearm); +y continues along the
          forearm. A staff carried upright runs from about y=-220 to y=+120; a water pot (kamaṇḍalu) hangs at y 0..+60;
          a mala, a book of palm leaves, a lotus, a veena... Use "" if the character carries nothing.
- thigh   origin = hip joint; hangs to the knee at y=+104, about 28 wide.
- shin    origin = knee; hangs to the ankle at y=+100, with the FOOT at the end pointing right (toes to about x=+36, y=+111).
- lower   OPTIONAL lower garment drawn over the legs when standing: origin = hip; a dhoti to y≈+110, a long robe or sari
          to y≈+190 (ankles), flaring a little. "" if the legs show.
- lap     the SEATED lower body for meditation poses: origin = hip; folded legs cross-legged in front, x about -60..+120,
          y about -10..+65, including the garment over them.
- back    OPTIONAL shape behind everything, origin = hip: long hair falling down the back, a trailing shawl (x -90..+20,
          y -200..+60). "" if none.

The silhouette is read by OUTLINE ALONE: make each character instantly recognisable from its shape (headdress, beard,
garment, held object, posture, build, age). Avoid tiny details; one or two "cut" ornaments at most."""

SYSTEM = f"""You are a character designer for paper-cut silhouette animation in a devotional learning app.
You design each HUMAN character of a chant's story from its context and the character bible, as body parts that an
existing skeleton animates (stand, walk, point, bow, kneel, meditate...).

{RIG}

Rules:
- Design only the human characters you are given (sages, kings, devotees, attendants). Never design a god or goddess:
  divine figures appear in the film only as light.
- Each character must look different from the others and true to the bible: age and build, hair (jaṭā, topknot, shaven,
  long), beard, headdress, garment (dhoti, robe, bark cloth, sari), ornaments, and what they carry.
- Paths must be valid SVG path data with the coordinates in the frames above."""


def available():
    return bool(os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN"))


def _client():
    import anthropic
    return anthropic.Anthropic()


def _parse(messages, fmt):
    resp = _client().beta.messages.parse(model=MODEL, max_tokens=16000, betas=["server-side-fallback-2026-07-01"], fallbacks="default",
                                         output_config={"effort": "high"}, system=SYSTEM, messages=messages, output_format=fmt)
    if resp.stop_reason == "refusal" or resp.parsed_output is None:
        raise RuntimeError("Claude could not design the cast")
    return resp.parsed_output.model_dump(), resp.model


def _brief(story):
    who = [c for c in story.get("characters", [])]
    scenes = [{"title": s["title"], "picture": s.get("picture", ""), "figures": [{"character": f["character"], "pose": f["pose"], "pose_to": f["pose_to"]}
                                                                                 for f in s.get("figures", [])]} for s in story.get("scenes", [])]
    return {"film": story.get("title"), "characters": who, "scenes": scenes}


def sheet(cast, out_png):
    """Draw every character in four poses (stand, walk, bow, meditate) for review; returns the image path."""
    layers = [{"el": "sky", "mood": "dawn"}, {"el": "ground", "y": .86}]
    chars = list(cast.values())
    poses = [("stand", 0), ("stand", 1), ("bow", 0), ("meditate", 0)]
    n = len(chars) * len(poses)
    for i, c in enumerate(chars):
        for j, (pose, walk) in enumerate(poses):
            k = i * len(poses) + j
            layers.append({"el": "cast", "id": c["id"], "x": round((k + .5) / n, 4), "y": .84, "s": min(1.0, 3.6 / n * 1.4), "dir": 1, "pose": pose, "walk": walk})
    data = {"plan": {"scenes": [{"id": "S", "title": "sheet", "from": 0, "to": 10, "camera": {"from": {"zoom": 1, "x": .5, "y": .5}, "to": {"zoom": 1, "x": .5, "y": .5}},
                                 "layers": layers}], "cast": cast}, "units": [], "narration": []}
    tmp = tempfile.mkdtemp(prefix="vakcast_")
    dj = os.path.join(tmp, "data.json"); json.dump(data, open(dj, "w", encoding="utf-8"), ensure_ascii=False)
    env = dict(os.environ, NODE_PATH=sh([shutil.which("npm") or "npm", "root", "-g"]).strip())
    r = subprocess.run(["node", os.path.join(ASSETS, "anim.js"), "silhouette", dj, tmp, "--stills", "1.3"], env=env, capture_output=True, text=True, encoding="utf-8", errors="replace")
    src = os.path.join(tmp, "t1.30.jpg")
    if r.returncode != 0 or not os.path.exists(src):
        raise RuntimeError("cast sheet failed: " + (r.stderr or r.stdout)[-800:])
    os.makedirs(os.path.dirname(os.path.abspath(out_png)), exist_ok=True)
    shutil.move(src, out_png); shutil.rmtree(tmp, ignore_errors=True)
    return out_png


def _review(cast, story, img):
    b64 = base64.b64encode(open(img, "rb").read()).decode()
    order = ", ".join(f"{c['name']} ({c['id']})" for c in cast.values())
    msg = [{"role": "user", "content": [
        {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": b64}},
        {"type": "text", "text": f"This sheet shows the cast you designed, left to right in groups of four poses (stand, walk, bow, meditate): {order}.\n"
                                 f"Character bible: {json.dumps(story.get('characters', []), ensure_ascii=False)}\n"
                                 "For each character say ok=false only for real problems: parts that don't join at the joints, a shape that "
                                 "is unreadable or ugly in outline, a head or face facing the wrong way, a held object floating, a costume "
                                 "that contradicts the bible, or two characters that look the same. Be concrete about the fix."}]}]
    out, _ = _parse(msg, Review)
    return {v["id"]: v for v in out["characters"]}


def design(story, force=False, review=True):
    """The cast for a story film: {id: CharacterArt dict}. Cached by the story's characters and scenes."""
    brief = _brief(story)
    if not brief["characters"]:
        return {}
    k = hashlib.sha256(json.dumps(brief, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()[:16]
    p = os.path.join(CACHE, k + ".json")
    if not force and os.path.exists(p):
        return json.load(open(p, encoding="utf-8"))["cast"]
    if not available():
        raise RuntimeError("Claude isn't connected: add ANTHROPIC_API_KEY to vak_engine/.env.local")
    t0 = time.time()
    msgs = [{"role": "user", "content": "Design the cast for this film. Brief:\n\n" + json.dumps(brief, ensure_ascii=False, indent=1)}]
    out, model = _parse(msgs, Cast)
    cast = {c["id"]: c for c in out["characters"]}
    log(f"cast: designed {', '.join(c['name'] for c in cast.values())} in {time.time() - t0:.0f}s with {model}")
    notes = {}
    if review:
        img = sheet(cast, os.path.join(CACHE, k + "_v1.jpg"))
        verdicts = _review(cast, story, img)
        bad = {cid: v["problems"] for cid, v in verdicts.items() if not v["ok"] and cid in cast}
        notes["review_v1"] = verdicts
        if bad:                                   # one round of redrawing, with the reviewer's notes
            log(f"cast: redrawing {', '.join(bad)} ({'; '.join(bad.values())[:200]})")
            fix = msgs + [{"role": "assistant", "content": json.dumps(out, ensure_ascii=False)},
                          {"role": "user", "content": "A review of the rendered sheet found problems. Redraw ONLY these characters, fixing: "
                                                      + json.dumps(bad, ensure_ascii=False) + ". Return just those characters."}]
            out2, _ = _parse(fix, Cast)
            for c in out2["characters"]:
                if c["id"] in cast:
                    cast[c["id"]] = c
            sheet(cast, os.path.join(CACHE, k + "_v2.jpg"))
    os.makedirs(CACHE, exist_ok=True)
    json.dump({"cast": cast, "brief": brief, "notes": notes, "_model": model, "_at": time.strftime("%Y-%m-%d %H:%M")},
              open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    log(f"cast: {len(cast)} characters ready in {time.time() - t0:.0f}s -> knowledge/cast/{k}.json")
    return cast
