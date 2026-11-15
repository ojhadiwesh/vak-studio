"""NARRATED films: title card -> a story told by a narrator (subtitled, over a soft tanpura bed) -> the chant itself
(the recording, with word-synced captions). One continuous animation covers both parts.

Project fields: "narration" {voice, rate, pitch, lines[{text, tts, pause}]}, "track_from" (second of the recording
where the chant part starts), "animation" (story plan, anchored to narration lines {n}), "mantra_animation"
(plan in recording time; shifted onto the film after the narration)."""
import copy, json, os
from . import anim, edit, narrate
from .util import ffmpeg, key, log

LEAD, GAP = 0.6, 0.8          # narration starts LEAD s after the card; the chant starts GAP s after the narration


def _shift_plan(plan, V):
    """Shift numeric times (seconds of the recording) by V; word/line anchors are resolved on shifted timings."""
    p = copy.deepcopy(plan)
    for sc in p["scenes"]:
        for k in ("from", "to"):
            if isinstance(sc.get(k), (int, float)): sc[k] += V
        for l in sc["layers"]:
            for an in l.get("anim", []):
                for k in ("at", "until"):
                    if isinstance(an.get(k), (int, float)): an[k] += V
                if "keys" in an:
                    an["keys"] = [[k0 + V if isinstance(k0, (int, float)) else k0, v] for k0, v in an["keys"]]
    return p


def run(cache, sb, cfg, rel, out_path):
    card, C = edit.title_card(cache, cfg["card"])
    T0 = round(C - edit.XF, 3)
    wav, lines, ND = narrate.run(cache, cfg["narration"], rel=rel)
    N0 = T0 + LEAD
    narr = [{"text": l["text"], "start": round(l["start"] + N0, 3), "end": round(l["end"] + N0, 3)} for l in lines]
    M0 = round(N0 + ND + GAP, 3)                          # film time where the chant recording starts
    tf = float(cfg.get("track_from", 0.0))
    V = round(M0 - tf, 3)                                 # film time = recording time + V
    total = round(V + sb["audio"]["duration"] + 0.2, 3)
    scene_len = round(total - T0, 3)
    sb["timeline"] = {"card": C, "scene_start": T0, "narration_start": N0, "chant_start": M0, "voice_offset": V, "total": total}
    sb["narration"] = narr
    log(f"narrated: card {C:.1f}s, story {N0:.1f}-{N0 + ND:.1f}s, chant from {M0:.1f}s, total {total:.1f}s")

    # one plan on the film timeline: story scenes, then the chant scenes shifted by V
    story = json.load(open(rel(cfg["animation"]), encoding="utf-8")) if cfg.get("animation") else {"scenes": []}
    mantra = _shift_plan(json.load(open(rel(cfg["mantra_animation"]), encoding="utf-8")), V) if cfg.get("mantra_animation") else {"scenes": []}
    for sc in story["scenes"]:
        if isinstance(sc.get("to"), (int, float)) and sc["to"] > M0: sc["to"] = M0
    plan = {"scenes": story["scenes"] + mantra["scenes"]}
    units = copy.deepcopy(sb["units"])
    for u in units:
        u["start"] += V; u["end"] += V
        for w in u["words"]: w["start"] += V; w["end"] += V
    if cfg.get("storybook"):                              # painted illustrations (vak/storybook.py) instead of code animation
        from . import storybook
        bg = storybook.background(cache, os.path.dirname(rel(cfg["story"])), cfg, narr, T0, M0, total, sb["style"]["id"])
    else:
        bg = anim.render(cache, sb, plan, sb["style"]["id"], T0, scene_len, units=units, narration=narr)

    # overlays: narration subtitles, then the chant's word-synced captions
    subdir, _ = cache.get_or_make("subs", key([l["text"] for l in narr]), "", lambda d: edit.node("subs", _write_json(d + ".json", [l["text"] for l in narr]), d))
    capdir, states = edit.captions(cache, sb, V)
    ov = [(f"{subdir}/sub{i:03d}.png", l["start"] - 0.1, l["end"] + 0.35, True, True) for i, l in enumerate(narr)]
    ov += [(f"{capdir}/st{i:03d}.png", st["from"], st["to"], st.get("first"), st.get("last")) for i, st in enumerate(states)]
    inputs, fc, last = ["-i", bg], ["[0:v]null[v0]"], "v0"
    for i, (png, a, b, first, lastf) in enumerate(ov):
        a, b = a - T0, b - T0
        inputs += ["-loop", 1, "-t", scene_len, "-i", png]
        ch = f"[{i + 1}:v]format=rgba" + (f",fade=t=in:st={a:.3f}:d=0.35:alpha=1" if first else "") + (f",fade=t=out:st={b - .35:.3f}:d=0.35:alpha=1" if lastf else "")
        fc += [ch + f"[c{i}]", f"[{last}][c{i}]overlay=x=0:y=640:enable='between(t,{a:.3f},{b:.3f})'[w{i}]"]
        last = f"w{i}"
    fc.append(f"[{last}]format=yuv420p[v]")
    scene, _ = cache.get_or_make("nscene", key(bg, subdir, capdir, json.dumps(ov)), ".mp4", lambda o: ffmpeg(
        *inputs, "-filter_complex", ";".join(fc), "-map", "[v]", "-t", scene_len, "-c:v", "libx264", "-crf", 17, o))
    log("narrated: picture composited with subtitles and captions")

    # sound: tanpura bed in the chant's key under the story, the narrator, then the chant recording
    bed = edit.score(cache, M0 + 4, sb["audio"]["tonic_hz"], N0, N0 + ND)
    nms, mms = int(N0 * 1000), int(M0 * 1000)
    ffmpeg("-i", card, "-i", scene, "-i", wav, "-i", bed, "-i", sb["audio"]["path"], "-filter_complex",
           f"[0:v]settb=AVTB,fps=24,format=yuv420p[a];[1:v]settb=AVTB,fps=24,format=yuv420p[b];[a][b]xfade=transition=fade:duration={edit.XF}:offset={T0}[v];"
           f"[2:a]aresample=48000,volume=1.6,adelay={nms}|{nms}[n];"
           f"[3:a]aresample=48000,volume=0.45,afade=t=out:st={M0 - 0.5:.2f}:d=3.5[s];"
           f"[4:a]aresample=48000,atrim=start={tf},asetpts=PTS-STARTPTS,afade=t=in:d=1.0,adelay={mms}|{mms}[m];"
           f"[n][s][m]amix=inputs=3:normalize=0:duration=longest,afade=t=out:st={total - 2.5:.2f}:d=2.5,apad,atrim=0:{total},loudnorm=I=-16:TP=-1.5:LRA=11[au]",
           "-map", "[v]", "-map", "[au]", "-t", total, "-c:v", "libx264", "-profile:v", "high", "-pix_fmt", "yuv420p", "-crf", 18,
           "-c:a", "aac", "-b:a", "192k", "-ar", 48000, "-movflags", "+faststart", out_path)
    sb["renders"]["film"] = out_path
    log(f"narrated: film written ({total:.1f}s) -> {out_path}")
    return out_path


def _write_json(path, obj):
    json.dump(obj, open(path, "w", encoding="utf-8"), ensure_ascii=False)
    return path
