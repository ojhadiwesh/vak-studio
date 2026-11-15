"""art: build a reusable library of Indian-art pieces for the code animator, on a ComfyUI GPU server.

    python -m vak art art/library.json --style pattachitra[,madhubani,...] [--items sun,lotus_open]
                                       [--takes N] [--force] [--comfy URL] [--cut-only]

Each library item is drawn by Qwen-Image 2512 in a folk-art style:
  kind "element"    : one object alone on a plain ground (square) -> cut out with rembg -> transparent PNG,
                      trimmed to its content. These are the layers the animator moves (sun rises, lotus opens...).
  kind "background" : a full-bleed 16:9 scene with nothing that should move on its own (no figures, no birds).
An item with "reference": "<id>" is drawn with Qwen-Image-Edit from that item's image, so a character keeps
its face and costume across poses (draw and approve the anchor first).

Output, per style, under art/<style>/:
  raw/<id>.png        the generated image (takes 2..n in raw/takes/)
  <id>.png            cut-out element with alpha (elements only)
  bg/<id>.png         backgrounds (1664x928)
  index.json          what the animator reads: file, kind, size, anchor point, tags
  sheet.jpg           contact sheet of everything, on a checkerboard, to review by eye

Animating: code moves whole pieces (translate / rotate / scale / fade / reveal masks); faces are never
redrawn, so they stay steady. Pieces that need to bend (a lotus opening) come as separate states
(lotus_bud, lotus_open) that the animator cross-fades."""
import hashlib, json, os
from .comfy import Comfy, keyframe_workflow, reference_keyframe_workflow, QWEN, QWEN_EDIT
from .util import log

# Style blocks written for the library: no "16:9", no borders/frames (borders would be cut into elements).
ART_STYLES = {
    "pattachitra": {
        "name": "Odisha Pattachitra",
        "block": "Painted in the style of traditional Odisha Pattachitra from Raghurajpur on treated cloth (patta): crisp bold "
                 "black outlines drawn with a fine brush, flat opaque colours with no gradients, stylised and graphic, "
                 "two-dimensional, no shading, no perspective",
        # the traditional mineral/organic palette, named the same way in every prompt so all pieces match
        "palette": "Use only this palette: vermilion red (hingula), deep yellow ochre (haritala), indigo blue, "
                   "conch-shell white, lamp-black, leaf green and terracotta brown.",
        # signature details the model only follows when they are named
        "motifs": "Pattachitra pattern details: fine white dotted lines tracing the inside of outlines, tiny repeating leaf, "
                  "petal and creeper patterns filling large surfaces.",
        # only for people and animals: on objects these words made the model paint a woman inside the sun
        "figure_motifs": "Eyes are elongated and almond-shaped in profile; ornaments are drawn as rows of small dots.",
        "ground": "a plain flat light grey background",
        "ground_light": "a plain flat deep indigo background",   # for white or very pale subjects (egret, conch)
    },
    "madhubani": {
        "name": "Madhubani (Mithila)",
        "block": "Madhubani Mithila folk painting, double black outlines filled with fine cross-hatching and dense line "
                 "patterns, flat bright colours: red, yellow, green, blue and black, "
                 "no shading, no perspective",
        "ground": "a plain flat off-white paper background",
    },
    "kalamkari": {
        "name": "Srikalahasti Kalamkari",
        "block": "Srikalahasti Kalamkari hand-painted textile art, pen-drawn black outlines, natural vegetable dye colours: "
                 "madder red, indigo, mustard yellow, olive green, on unbleached cotton, intricate floral fill patterns, "
                 "flat and decorative",
        "ground": "a plain flat unbleached cotton background",
    },
    "gond": {
        "name": "Gond",
        "block": "Gond tribal art, shapes filled with fine repeating dots, dashes and line patterns, bright saturated "
                 "colours, stylised organic forms, lively and decorative, flat, no shading",
        "ground": "a plain flat white background",
    },
}
NEGATIVE = ("text, letters, signature, watermark, logo, border, frame, decorative border, photo, 3d render, "
            "realistic shading, blurry, low quality, extra limbs, extra fingers, deformed hands, distorted face, "
            "modern clothing, cropped, cut off")
# size class -> how much of a big painting the piece would fill; keeps line weight and pattern density
# consistent across pieces that are each drawn alone at the same canvas size
SCALE = {
    "small": "It is a small detail of a larger painting: keep the outline weight and pattern density modest and simple.",
    "medium": "It is a medium-sized motif of a larger painting: normal outline weight and moderate pattern detail.",
    "large": "It is a large main motif of a painting: rich pattern detail, same outline weight as the rest of the painting.",
}
ELEMENT_TAIL = ("A single isolated {what}, centred, the whole subject fully visible with empty space around it, "
                "on {ground}. Nothing else in the picture: no scenery, no ground line, no shadow, no border, no text.")
BG_TAIL = "Full-bleed scene filling the whole picture edge to edge, no border, no frame, no text."
SIZE = {"element": (1328, 1328), "background": (1664, 928)}


def _seed(*parts):
    return int(hashlib.sha1("|".join(map(str, parts)).encode()).hexdigest()[:8], 16)


LIVING = {"figure", "bird", "animal"}
NO_PEOPLE = "It is only the object itself: no person, no face, no figure, no animal."


def _prompt(item, st, chars):
    """Subject first (what the picture is), then style, palette and pattern details, then isolation and scale.
    Style words about eyes/ornaments go only to people and animals, or the model paints a person into objects."""
    who = "".join(f" The {c}: {chars[c]}" for c in item.get("characters", []))
    living = bool(LIVING & set(item.get("tags", [])))
    style = " ".join(x for x in (st["block"] + ".", st.get("palette", ""), st.get("motifs", ""),
                                 st.get("figure_motifs", "") if living else "") if x)
    if item["kind"] == "background":
        room = f" {item['room']}." if item.get("room") else ""
        return f"{item['prompt'][0].upper() + item['prompt'][1:]}.{room}{who} {style} {BG_TAIL}"
    what = item["prompt"] + (f", facing {item['facing']}" if item.get("facing") else "")
    ground = st.get("ground_light", st["ground"]) if item.get("light") else st["ground"]
    guard = "" if living else " " + NO_PEOPLE
    return (ELEMENT_TAIL.format(what=what, ground=ground) + guard + who + f" {style} " + SCALE[item.get("size", "medium")]).strip()


def cut(raw, out, pad=12):
    """Remove the plain ground with rembg (isnet), keep a soft alpha, trim to content + pad. Returns (w, h)."""
    from PIL import Image
    import numpy as np
    from rembg import remove, new_session
    global _SESSION
    try:
        _SESSION
    except NameError:
        _SESSION = new_session("isnet-general-use")
    img = Image.open(raw).convert("RGB")
    a = np.asarray(remove(img, session=_SESSION, only_mask=True), np.float32) / 255
    a[a < 0.04] = 0
    ys, xs = np.nonzero(a > 0.1)
    if not len(xs):
        raise RuntimeError(f"cut-out of {raw} is empty")
    x0, y0 = max(0, xs.min() - pad), max(0, ys.min() - pad)
    x1, y1 = min(img.width, xs.max() + pad + 1), min(img.height, ys.max() + pad + 1)
    rgba = np.dstack([np.asarray(img), (a * 255).astype(np.uint8)])
    Image.fromarray(rgba, "RGBA").crop((x0, y0, x1, y1)).save(out)
    return int(x1 - x0), int(y1 - y0)


def sheet(entries, base, out, cell=300):
    """Contact sheet: every piece on a checkerboard (so the cut-out edges show), with its id."""
    from PIL import Image, ImageDraw
    cols = 6
    rows = (len(entries) + cols - 1) // cols
    S = Image.new("RGB", (cols * cell, rows * (cell + 24)), (40, 40, 40))
    chk = Image.new("RGB", (cell, cell), (205, 205, 205))
    d0 = ImageDraw.Draw(chk)
    for y in range(0, cell, 20):
        for x in range(0, cell, 20):
            if (x + y) // 20 % 2:
                d0.rectangle([x, y, x + 19, y + 19], fill=(240, 240, 240))
    d = ImageDraw.Draw(S)
    for i, (iid, e) in enumerate(entries):
        x, y = i % cols * cell, i // cols * (cell + 24)
        tile = chk.copy()
        im = Image.open(os.path.join(base, e["file"])).convert("RGBA")
        im.thumbnail((cell - 10, cell - 10))
        tile.paste(im, ((cell - im.width) // 2, (cell - im.height) // 2), im)
        S.paste(tile, (x, y))
        d.text((x + 6, y + cell + 5), iid, fill=(235, 235, 235))
    S.save(out, quality=88)


def run(library, styles, items=None, takes=1, force=False, url=None, cut_only=False):
    L = json.load(open(library, encoding="utf-8"))
    root = os.path.join(os.path.dirname(os.path.abspath(library)))
    chars = L.get("characters", {})
    todo = [it for it in L["items"] if not items or it["id"] in items]
    todo.sort(key=lambda it: bool(it.get("reference")))           # anchors before the poses drawn from them
    cf = None
    if not cut_only:
        cf = Comfy(url)
        have = cf.check(["ModelSamplingAuraFlow", "EmptySD3LatentImage", "TextEncodeQwenImageEditPlus", "CFGNorm"])
        missing = [m for m in list(QWEN.values()) + ([QWEN_EDIT] if any(it.get("reference") for it in todo) else []) if m not in have]
        if missing:
            raise SystemExit(f"Models missing on the server: {missing}. Rerun runpod_setup.sh on the pod.")
    for sid in styles:
        st = ART_STYLES[sid]
        base = os.path.join(root, sid)
        idx_path = os.path.join(base, "index.json")
        index = json.load(open(idx_path, encoding="utf-8")) if os.path.exists(idx_path) else {"style": sid, "name": st["name"], "pieces": {}}
        for it in todo:
            iid, kind = it["id"], it["kind"]
            raw = os.path.join(base, "raw", f"{iid}.png")
            if not cut_only and (force or not os.path.exists(raw)):
                w, h = SIZE[kind]
                ref = it.get("reference")
                ref_name = None
                if ref:
                    rp = os.path.join(base, "raw", f"{ref}.png")
                    if not os.path.exists(rp):
                        log(f"art: {sid}/{iid} needs {ref} first; skipped"); continue
                    ref_name = cf.upload(rp)
                for k in range(1, takes + 1):
                    out = raw if k == 1 else os.path.join(base, "raw", "takes", f"{iid}_{k}.png")
                    seed, pre = _seed(iid, sid, k), f"vak/art/{sid}/{iid}"
                    p = _prompt(it, st, chars)
                    if ref_name:
                        who = " and ".join(it.get("characters", [])) or "the figure"
                        p = (f"Keep {who} from the reference image exactly the same: same face, hair, beard, ornaments, clothing "
                             f"colours and the same painting style. New picture: " + p)
                        wf = reference_keyframe_workflow([ref_name], p, NEGATIVE, seed, width=w, height=h, prefix=pre)
                    else:
                        wf = keyframe_workflow(p, NEGATIVE, seed, width=w, height=h, prefix=pre)
                    _, secs = cf.run(wf, out)
                    log(f"art: {sid}/{iid} take {k}{' (from ' + ref + ')' if ref_name else ''} ({secs:.0f}s)")
            if not os.path.exists(raw):
                continue
            if kind == "background":
                os.makedirs(os.path.join(base, "bg"), exist_ok=True)
                f = os.path.join("bg", f"{iid}.png")
                import shutil; shutil.copyfile(raw, os.path.join(base, f))
                size = list(SIZE[kind])
            else:
                f = f"{iid}.png"
                size = list(cut(raw, os.path.join(base, f)))
            index["pieces"][iid] = {"file": f.replace(os.sep, "/"), "kind": kind, "size": size,
                                    "anchor": it.get("anchor", [0.5, 1.0] if it.get("characters") else [0.5, 0.5]),
                                    "tags": it.get("tags", []), "prompt": it["prompt"]}
            json.dump(index, open(idx_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        order = [(i["id"], index["pieces"][i["id"]]) for i in L["items"] if i["id"] in index["pieces"]]
        if order:
            name = "sheet.jpg" if os.path.basename(library) == "library.json" else f"sheet_{os.path.splitext(os.path.basename(library))[0]}.jpg"
            sheet(order, base, os.path.join(base, name))
            log(f"art: {sid}: {len(order)} pieces -> {os.path.relpath(base)} (review {name})")
