"""ANIMATION module (option B): render a style-agnostic animation plan in one code-drawn style.

The plan (anim_plan.json) says what is on screen, how it moves and when (anchored to words of the chant or to
narration lines); a style renderer in assets/anim/<style>.js decides how it looks. Output: the scene background
video that edit.run would otherwise build from clips, from the end of the title card to the end of the film."""
import base64, io, json, os, re, shutil
from .util import ASSETS, key, log, sh, stream

ART = os.path.join(os.path.dirname(os.path.dirname(ASSETS)), "art")


def art_pieces(art_style, max_side=1000):
    """Painted cut-out pieces from `python -m vak art` (art/<style>/index.json) as {id: {src, w, h}}, downscaled
    and inlined as data URLs so the canvas stays untainted (file:// images would block toDataURL)."""
    idx = os.path.join(ART, art_style, "index.json")
    if not os.path.exists(idx):
        raise SystemExit(f"no art library for '{art_style}': run python -m vak art art/library.json --style {art_style}")
    from PIL import Image
    out = {}
    for pid, e in json.load(open(idx, encoding="utf-8"))["pieces"].items():
        if e["kind"] != "element":
            continue
        im = Image.open(os.path.join(ART, art_style, e["file"])).convert("RGBA")
        im.thumbnail((max_side, max_side))
        b = io.BytesIO(); im.save(b, "WEBP", quality=90)
        out[pid] = {"src": "data:image/webp;base64," + base64.b64encode(b.getvalue()).decode(), "w": im.width, "h": im.height,
                    "tags": e.get("tags", [])}
    return out


def render(cache, sb, plan, style, t_start, seconds, units=None, narration=None):
    """plan: a path or a dict. units/narration: timings on the same timeline as the plan (default: sb units)."""
    if isinstance(plan, str):
        plan = json.load(open(plan, encoding="utf-8"))
    data = {"plan": plan, "units": units if units is not None else sb["units"], "narration": narration or []}
    style_js = os.path.join(ASSETS, "anim", f"{style}.js")
    if not os.path.exists(style_js):
        raise SystemExit(f"no renderer for animation style '{style}' (expected {style_js})")
    src = open(style_js, encoding="utf-8").read()
    files = ["core.js", f"{style}.js", "stage.html"]
    m = re.search(r"STYLE_BASE\s*=\s*['\"](\w+)['\"]", src)
    if m:
        files.append(f"{m.group(1)}.js")
    m = re.search(r"STYLE_ART\s*=\s*['\"](\w+)['\"]", src)
    if m:
        data["art"] = art_pieces(m.group(1))
    code = [open(os.path.join(ASSETS, "anim", n), encoding="utf-8").read() for n in files]
    code.append(open(os.path.join(ASSETS, "anim.js"), encoding="utf-8").read())
    k = key(json.dumps(data, ensure_ascii=False, sort_keys=True), code, style, round(t_start, 3), round(seconds, 3))

    def make(out):
        dj = out + ".data.json"
        json.dump(data, open(dj, "w", encoding="utf-8"), ensure_ascii=False)
        env = dict(os.environ, NODE_PATH=sh([shutil.which("npm") or "npm", "root", "-g"]).strip())
        stream(["node", os.path.join(ASSETS, "anim.js"), style, dj, out, f"{t_start:.3f}", f"{seconds:.3f}"], env=env)
        os.remove(dj)

    p, hit = cache.get_or_make("anim", k, ".mp4", make)
    log(f"anim: '{style}' rendered {seconds:.1f}s {'(cached)' if hit else ''}")
    return p
