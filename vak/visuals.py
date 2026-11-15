"""VISUALS module: gets an image or clip for every scene through a model adapter.
Adapters share one interface, so providers can be swapped by configuration."""
import json, os
from .util import log


class Adapter:
    name = "base"
    def image(self, prompt, out): raise NotImplementedError
    def clip(self, image, motion_prompt, seconds, out): raise NotImplementedError


class FileAdapter(Adapter):
    """Uses images/clips already in the project folder (made by hand in OpenArt, Flow, Midjourney...)."""
    name = "file"


class ManualQueue(Adapter):
    """Writes what still needs generating to a to-do list a person works through."""
    name = "manual"
    def __init__(self, todo_path): self.todo = todo_path
    def request(self, scene):
        items = json.load(open(self.todo, encoding="utf-8")) if os.path.exists(self.todo) else {}
        v = scene["visual"]
        items[scene["id"]] = {"title": scene.get("title", ""), "style": v.get("style_id", ""), "prompt": v.get("prompt", ""),
                              "negative": v.get("negative", ""), "motion_prompt": v.get("motion_prompt", ""),
                              "save_image_as": v.get("want_image", ""), "save_clip_as": v.get("want_clip", "")}
        json.dump(items, open(self.todo, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


class APIAdapter(Adapter):
    """Placeholder for hosted models (Seedance, Veo, MiniMax H3, Kling via an API provider).
    Fill in `image`/`clip` with the provider's HTTP calls and an API key from the environment."""
    def __init__(self, provider): self.name = provider


def _find(project_dir, sub, style, sid, exts):
    for e in exts:
        p = os.path.join(project_dir, sub, style, sid + e)
        if os.path.exists(p):
            return p


def run(sb, project_dir, adapter="file"):
    """Explicit visuals in the project win. Otherwise look for clips/<style>/<scene>.(mp4|mov)
    and images/<style>/<scene>.(png|jpg); anything missing goes to to_generate.json."""
    todo_path = os.path.join(project_dir, "to_generate.json")
    if os.path.exists(todo_path):
        os.remove(todo_path)                        # rebuilt each run for the current style
    todo = ManualQueue(todo_path)
    style = sb["style"]["id"]
    ready = 0
    for s in sb["scenes"]:
        v = s["visual"]
        v["style_id"] = style
        for k in ("clip", "image"):
            if v.get(k) and not os.path.isabs(v[k]):
                v[k] = os.path.join(project_dir, v[k])
        if not v.get("clip") and not v.get("image"):
            v["clip"] = _find(project_dir, "clips", style, s["id"], (".mp4", ".mov"))
            v["image"] = _find(project_dir, "images", style, s["id"], (".png", ".jpg", ".jpeg", ".webp"))
            if not v["clip"]: v.pop("clip")
            if not v["image"]: v.pop("image")
        if v.get("clip") or v.get("image"):
            v.pop("status", None)
            ready += 1
        else:
            v["status"] = "needs generation"
            v["want_image"] = f"images/{style}/{s['id']}.png"
            v["want_clip"] = f"clips/{style}/{s['id']}.mp4"
            todo.request(s)
    log(f"visuals: {ready}/{len(sb['scenes'])} scenes have visuals for style '{style}'" + ("" if ready == len(sb["scenes"]) else "; others listed in to_generate.json"))
    return sb
