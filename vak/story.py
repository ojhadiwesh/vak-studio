"""STORY module: links units to scenes, characters and playbook techniques, and writes prompts
for any scene that still needs a visual."""
from .util import log
from . import styles

# Praise-sections playbook: default technique by what a unit contains
PLAYBOOK = {
    "invocation": "title",          # name card over the opening image
    "speaker": "story",
    "narrative": "story",
    "names": "accumulation",        # each name adds an element that stays
    "list": "rhythm",               # one cut per listed item
    "protection": "anchor",         # light accumulates on the devotee
    "blessing": "release",
}


def run(sb, cfg, library=None, style_override=None):
    style = styles.resolve(cfg.get("style"), style_override)
    sb["style"] = style
    library = library if library is not None else cfg.get("characters", {})
    units = sb["units"]
    scenes = []
    for sc in cfg["scenes"]:
        if "units" in sc:                           # 1-based unit positions, for chants of one verse
            ids = [units[i - 1]["id"] for i in sc["units"]]
        else:
            want = sc.get("verses", "all")
            ids = [u["id"] for u in units if want == "all" or u["verse"] in want or (u["verse"] is None and sc.get("include_preamble"))]
        s = {"id": sc["id"], "title": sc.get("title", ""), "units": ids, "technique": sc.get("technique", PLAYBOOK.get(sc.get("kind", "narrative"), "story")),
             "visual": dict(sc.get("visual", {})), "characters": sc.get("characters", []),
             "reference": sc.get("reference", []),           # scene ids whose keyframes carry the same characters
             "start": sc.get("start")}                      # optional explicit start (seconds of the recording)
        chars = " ".join((library or {}).get(c, c) for c in s["characters"])
        # prompts are kept even when a visual exists, so any scene can be regenerated in another style
        s["visual"]["prompt"] = f"{style['block']} {sc.get('description', '')} {chars}".strip()
        s["visual"]["negative"] = style["negative"]
        # Wan I2V: motion first, then one camera move, then what stays still (docs/MODEL_PRACTICES.md)
        cam = sc.get("camera") or styles.DEFAULT_CAMERA
        s["visual"]["motion_prompt"] = f"{sc.get('motion', '')} {cam} {style['motion']}".strip()
        scenes.append(s)
    sb["scenes"] = scenes
    # speaker labels for captions
    for u in units:
        u["label"] = "Invocation" if u["kind"] == "invocation" else (u["speaker"] or "")
        if u["kind"] == "verse" and u["speaker"] and cfg.get("addressee", {}).get(u["speaker"]):
            u["label"] = f"{u['speaker']}, to {cfg['addressee'][u['speaker']]}"
    log(f"story: {len(scenes)} scene(s), style '{style['id']}' ({style['name']})")
    return sb
