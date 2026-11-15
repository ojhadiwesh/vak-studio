"""run(project) : chant text + recording + visuals -> storyboard.json + film.

project.json
{
  "title": "Devi Kavacham", "chant": "chant.txt", "audio": "recording.m4a",
  "translations": "translations.json",            # or "translate": "claude"
  "addressee": {"Mārkaṇḍeya": "Brahmā"},
  "style": "ravi_varma",                          # preset id (vak/styles.py) or {"preset": id, "block": extra}
  "card": {"kicker": "...", "chapter": "...", "title": "...", "sub": "..."},
  "scenes": [{"id": "S02", "verses": "all", "include_preamble": true,
              "visual": {"clip": "S02.mov", "subject_box": [280, 420, 860, 1080]}}],
  "out": "renders/film.mp4", "tune": true
}"""
import json, os, time
from . import storyboard, text, story, audio, visuals, edit, narrated
from .util import Cache, log


def run(project_path, cache_dir=None, style=None, stop_after=None):
    t0 = time.time()
    P = os.path.dirname(os.path.abspath(project_path))
    cfg = json.load(open(project_path, encoding="utf-8"))
    rel = lambda p: p if os.path.isabs(p) else os.path.join(P, p)
    cache = Cache(os.path.abspath(cache_dir) if cache_dir else os.path.join(P, ".vak_cache"))   # absolute: node opens files by URL

    sb = storyboard.new(cfg["title"])
    sb["units"] = text.parse(open(rel(cfg["chant"]), encoding="utf-8").read())                       # 1 TEXT
    text.translate(sb["units"], cfg.get("translate", "manual"), rel(cfg["translations"]) if cfg.get("translations") else None)
    text.word_meanings(sb["units"], rel(cfg["words"]) if cfg.get("words") else None)
    story.run(sb, cfg, style_override=style)                                                            # 2 STORY
    if stop_after == "story":                       # prompts only: no recording or visuals needed
        visuals.run(sb, P)
        storyboard.save(sb, os.path.join(P, "storyboard.json"))
        log("stopping after story (prompts written to to_generate.json)")
        return sb
    audio.run(sb, rel(cfg["audio"]), cache, tune=cfg.get("tune", True), manual=cfg.get("segments"))     # 3 AUDIO
    sb["audio"]["mode"] = cfg.get("audio_mode", "voice")   # "track": a finished mix that plays from frame 0
    if sb["style"].get("kind") == "live":          # drawn live in the browser from the audio + word timings: no render
        base, _ = os.path.splitext(rel(cfg.get("out", "renders/film.mp4")))
        out = f"{base}_{sb['style']['id']}.live.json"
        os.makedirs(os.path.dirname(out), exist_ok=True)
        sb["timeline"] = {"scene_start": 0.0, "voice_offset": 0.0, "total": sb["audio"]["duration"]}
        sb["live"] = {"style": sb["style"]["id"], "audio": os.path.relpath(rel(cfg["audio"]), os.path.dirname(out)).replace("\\", "/"),
                      "card": cfg.get("card", {})}
        sb["renders"]["film"] = out
        storyboard.save(sb, os.path.join(P, "storyboard.json"))
        storyboard.save(sb, out)
        log(f"live: '{sb['style']['id']}' film ready ({sb['audio']['duration']:.1f}s, drawn in the player) -> {out}")
        log(f"done in {time.time() - t0:.0f}s")
        return sb
    anim_plan = None
    if sb["style"].get("kind") == "animation":     # code-drawn style: the animation plan replaces clips/images
        from . import planner
        anim_plan = cfg.get("animation", "anim_plan.json")       # "auto": the rule-based plan for this style's family
        anim_plan = rel(f"anim_plan_{planner.family(sb['style']['id'])}.json" if anim_plan == "auto" else anim_plan)
        if not os.path.exists(anim_plan) and not cfg.get("narration"):   # no hand-written plan: the rule-based planner
            json.dump(planner.plan(sb["units"], sb["style"]["id"]), open(anim_plan, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
            log(f"planner: rule-based plan written -> {anim_plan}")
        if not os.path.exists(anim_plan):
            raise SystemExit(f"style '{sb['style']['id']}' needs an animation plan: {anim_plan}")
    elif not cfg.get("storybook"):
        visuals.run(sb, P)                                                                              # 4 VISUALS
    if anim_plan is None and not cfg.get("storybook") and any(s["visual"].get("status") == "needs generation" for s in sb["scenes"]):
        storyboard.save(sb, os.path.join(P, "storyboard.json"))
        log("stopping: some scenes still need visuals (see to_generate.json)")
        return sb
    base, ext = os.path.splitext(rel(cfg.get("out", "renders/film.mp4")))
    sid = sb["style"]["id"]
    out = base + ("" if sid == "custom" else f"_{sid}") + ext
    os.makedirs(os.path.dirname(out), exist_ok=True)
    if cfg.get("narration"):                       # story told by a narrator, then the chant
        narrated.run(cache, sb, cfg, rel, out)
    else:
        edit.run(cache, sb, cfg["card"], out, anim_plan=anim_plan)                                          # 5 MOTION + 6 EDIT
    storyboard.save(sb, os.path.join(P, "storyboard.json"))
    storyboard.save(sb, os.path.splitext(out)[0] + ".storyboard.json")   # per-film copy: the player's timeline
    log(f"done in {time.time() - t0:.0f}s")
    return sb
