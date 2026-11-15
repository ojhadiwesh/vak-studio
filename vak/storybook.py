"""STORYBOOK: a narrated story film painted as illustrations.

Claude's storyboard (vak/storyteller.py) gives every scene a style-free picture brief and a character bible. Here:
  1. generate(): each scene is painted on the ComfyUI GPU (Qwen-Image) in the chosen style preset (vak/styles.py);
     a character's first painting becomes the reference for later scenes (Qwen-Image-Edit), so they look the same.
     Paintings go to images/<style>/S01.png … and CH.png (the picture under the chant).
  2. background(): each painting becomes a slow camera move (push in, pull back, pan) lasting exactly its narration
     lines, joined with soft dissolves; the chant painting holds under the chant. vak/narrated.py then adds the title
     card, subtitles, word captions, narrator, tanpura bed and the chant.
Faces stay still (no AI video on faces); deities appear only as light (storyteller rule)."""
import json, os, re
from .util import duration, ffmpeg, key, log

STYLES = ("anime_painted", "animated_3d", "indian_comic", "storybook", "claymation", "ravi_varma", "pahari", "pattachitra",
          "watercolour", "tanjore", "mysore", "art_nouveau", "ink_wash", "persian_miniature", "romantic_oil")
XF = 0.6                       # dissolve between scenes


def shots(story):
    """[(id, picture, [characters seen])] for the story scenes, then the chant picture."""
    names = [c["name"] for c in story.get("characters", [])]
    out = []
    for i, sc in enumerate(story["scenes"]):
        seen = [n for n in names if n in sc.get("picture", "") or any(f["character"] == n for f in sc.get("figures", []))]
        out.append((f"S{i + 1:02d}", sc["picture"], seen))
    out.append(("CH", story.get("chant_picture") or "A seer sits in meditation at dawn by a quiet river, radiant light above.", []))
    return out


def prompt_for(style, picture, seen, story):
    looks = {c["name"]: c["look"] for c in story.get("characters", [])}
    who = " ".join(f"{n}: {looks[n]}." for n in seen if n in looks)
    return f"{style['block']} {picture} {who} Divine presence appears only as radiant light, never as a person. No text, no letters."


def generate(project_dir, story, style_id, url=None, force=False, only=None):
    """Paint every shot that has no image yet. Needs the ComfyUI GPU server (VAK_COMFY_URL)."""
    from . import styles
    from .comfy import Comfy, keyframe_workflow, reference_keyframe_workflow, QWEN, QWEN_EDIT
    from .generate import _seed
    style = styles.resolve(style_id)
    cf = Comfy(url)
    have = cf.check(["EmptySD3LatentImage", "TextEncodeQwenImageEditPlus"])
    missing = [m for m in list(QWEN.values()) + [QWEN_EDIT] if m not in have]
    if missing:
        raise RuntimeError(f"models missing on the GPU server: {missing} (rerun runpod_setup.sh on the pod)")
    folder = os.path.join(project_dir, "images", style_id)
    anchor, done = {}, []
    for sid, picture, seen in shots(story):
        out = os.path.join(folder, f"{sid}.png")
        if only and sid not in only:
            pass
        elif force or not os.path.exists(out):
            p = prompt_for(style, picture, seen, story)
            refs = [anchor[n] for n in seen if n in anchor][:2]
            seed, pre = _seed(sid, style_id, "storybook"), f"vak/{style_id}/{sid}"
            if refs:
                names = " and ".join(n for n in seen if n in anchor)
                wf = reference_keyframe_workflow([cf.upload(r) for r in refs],
                                                 f"Keep {names} from the reference image exactly the same: same face, age, hair, beard, "
                                                 f"ornaments and clothing, in the same painting style. New scene: {p}", style["negative"], seed, prefix=pre)
            else:
                wf = keyframe_workflow(p, style["negative"], seed, prefix=pre)
            _, secs = cf.run(wf, out)
            log(f"storybook: {sid} painted in {style['name']} ({secs:.0f}s){' keeping ' + ', '.join(seen) if refs else ''}")
            done.append(sid)
        for n in seen:                                 # a character's first painting is their reference from now on
            anchor.setdefault(n, out)
    json.dump({sid: prompt_for(style, pic, seen, story) for sid, pic, seen in shots(story)},
              open(os.path.join(folder, "prompts.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return done


def missing(project_dir, story, style_id):
    return [sid for sid, _, _ in shots(story) if not os.path.exists(os.path.join(project_dir, "images", style_id, f"{sid}.png"))]


def move(cache, image, seconds, camera):
    """A slow camera move over a painting, exactly `seconds` long, 1920x1080 at 24 fps (oversampled, so no jitter)."""
    n = max(2, int(round(seconds * 24))); N = n - 1
    z, x, y = {
        "push_in":   (f"1.0+0.12*on/{N}", "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"),
        "pull_back": (f"1.12-0.12*on/{N}", "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"),
        "pan_left":  ("1.12", f"(iw-iw/zoom)*(1-on/{N})", "ih/2-(ih/zoom/2)"),
        "pan_right": ("1.12", f"(iw-iw/zoom)*on/{N}", "ih/2-(ih/zoom/2)"),
        "still":     (f"1.0+0.04*on/{N}", "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"),
    }.get(camera, ("1.0+0.06*on/" + str(N), "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"))
    p, _ = cache.get_or_make("sbmove", key(image, os.path.getsize(image), round(seconds, 3), camera), ".mp4", lambda o: ffmpeg(
        "-loop", 1, "-framerate", 24, "-t", round(n / 24, 3), "-i", image,
        "-vf", f"scale=3840:2160:force_original_aspect_ratio=increase,crop=3840:2160,zoompan=z='{z}':x='{x}':y='{y}':d=1:s=1920x1080:fps=24,format=yuv420p",
        "-frames:v", n, "-c:v", "libx264", "-crf", 16, o))
    return p


def background(cache, project_dir, cfg, narr, T0, M0, total, style_id):
    """The film's picture from T0 to the end: one moving painting per scene (timed to its narration lines), then the
    chant painting, joined by dissolves."""
    story = json.load(open(os.path.join(project_dir, cfg["story"]), encoding="utf-8"))
    gone = missing(project_dir, story, style_id)
    if gone:
        raise SystemExit(f"storybook: paintings missing for {gone} in images/{style_id}/ (generate them on the GPU first)")
    sc = story["scenes"]
    bounds = [T0] + [narr[s["first_line"]]["start"] - 0.3 for s in sc[1:]] + [M0 - 0.3, total]
    cams = [s["camera"] for s in sc] + ["push_in"]
    ids = [f"S{i + 1:02d}" for i in range(len(sc))] + ["CH"]
    clips = []
    for i, sid in enumerate(ids):
        d = bounds[i + 1] - bounds[i] + (XF if i else 0)
        clips.append(move(cache, os.path.join(project_dir, "images", style_id, f"{sid}.png"), max(1.0, d), cams[i]))
    fc, last = [], "0:v"
    for i in range(1, len(clips)):
        off = round(bounds[i] - T0 - XF, 3)
        fc.append(f"[{last}][{i}:v]xfade=transition=fade:duration={XF}:offset={off}[x{i}]"); last = f"x{i}"
    L = round(total - T0, 3)
    out, hit = cache.get_or_make("storybook", key(clips, [round(b, 3) for b in bounds]), ".mp4", lambda o: ffmpeg(
        *sum([["-i", c] for c in clips], []), "-filter_complex", ";".join(fc) + (f";[{last}]format=yuv420p[v]" if fc else "[0:v]format=yuv420p[v]"),
        "-map", "[v]", "-t", L, "-c:v", "libx264", "-crf", 17, o))
    log(f"storybook: {len(clips)} painted shots {'(cached)' if hit else 'joined'} ({L:.1f}s)")
    return out
