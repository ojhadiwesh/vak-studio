"""The storyboard: one JSON document per chant that every module reads and extends.

Shape (keys are added as modules run):
{
  "title": str, "style": {...}, "timeline": {...},
  "units":   [{id, kind, verse, devanagari, iast, words:[{dev, iast, syl}], english, speaker}],
  "audio":   {path, tonic_hz, segments:[[start,end]], tuned_path},
  "scenes":  [{id, units:[ids], visual:{...}, motion:{...}, technique}],
  "renders": {...}
}"""
import json, os


def new(title, style=None):
    return {"title": title, "style": style or {}, "timeline": {}, "units": [], "audio": {}, "scenes": [], "renders": {}}


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save(sb, path):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(sb, f, ensure_ascii=False, indent=1)
    return path


def unit(sb, uid):
    return next(u for u in sb["units"] if u["id"] == uid)
