"""generate: fill missing visuals for one style on a ComfyUI GPU server.

    python -m vak generate project.json [--style ID] [--what images|clips|both] [--takes N]
                                        [--scenes G01,G03] [--quality draft|final] [--force] [--comfy URL]

Keyframes go to images/<style>/<scene>.png (extra takes in images/<style>/takes/), clips to
clips/<style>/<scene>.mp4. Existing files are kept unless --force, so reruns only fill gaps.
To pick a different take, copy it over images/<style>/<scene>.png and rerun with --what clips --force.

A scene with "reference": ["G03"] is drawn with Qwen-Image-Edit from that scene's chosen keyframe,
so characters look the same; such scenes are generated after the scenes they reference.
Approve the reference keyframe first (generate it alone with --scenes G03), then the rest."""
import hashlib, json, os, shutil
from . import pipeline
from .comfy import Comfy, keyframe_workflow, reference_keyframe_workflow, clip_workflow, VIDEO_NEGATIVE, QWEN, QWEN_EDIT, WAN
from .util import log


def _seed(*parts):
    return int(hashlib.sha1("|".join(map(str, parts)).encode()).hexdigest()[:8], 16)


def run(project, style=None, what="both", takes=1, scenes=None, quality="final", force=False, url=None,
        steps=None, shift=8.0, tag=""):
    P = os.path.dirname(os.path.abspath(project))
    sb = pipeline.run(project, style=style, stop_after="story")
    sid = sb["style"]["id"]
    todo = [s for s in sb["scenes"] if not scenes or s["id"] in scenes]
    todo.sort(key=lambda s: bool(s.get("reference")))     # referenced scenes first
    cf = Comfy(url)
    have = cf.check(["WanImageToVideo", "CreateVideo", "SaveVideo", "ModelSamplingAuraFlow", "EmptySD3LatentImage",
                     "TextEncodeQwenImageEditPlus", "FluxKontextMultiReferenceLatentMethod", "CFGNorm"])
    need = (list(QWEN.values()) if what != "clips" else []) + ([v for k, v in WAN.items() if quality == "draft" or not k.startswith("lora")] if what != "images" else [])
    if what != "clips" and any(s.get("reference") for s in todo):
        need.append(QWEN_EDIT)
    missing = [m for m in need if m not in have]
    if missing:
        raise SystemExit(f"Models missing on the server: {missing}. Rerun runpod_setup.sh on the pod.")

    for s in todo:
        v = s["visual"]
        explicit = v.get("clip") and not v["clip"].startswith(os.path.join(P, "clips"))
        if explicit:
            log(f"generate: {s['id']} uses a hand-made clip; skipped"); continue
        img = os.path.join(P, "images", sid, f"{s['id']}.png")
        if what in ("images", "both") and (force or not os.path.exists(img)):
            refs = [os.path.join(P, "images", sid, f"{r}.png") for r in s.get("reference", [])]
            if any(not os.path.exists(r) for r in refs):
                log(f"generate: {s['id']} needs reference keyframe(s) {s['reference']} first; skipped"); continue
            ref_names = [cf.upload(r) for r in refs]
            for k in range(1, takes + 1):
                out = img if k == 1 else os.path.join(P, "images", sid, "takes", f"{s['id']}_{k}.png")
                seed, pre = _seed(s["id"], sid, k), f"vak/{sid}/{s['id']}"
                if ref_names:
                    who = " and ".join(s.get("characters", [])) or "the people"
                    prompt = (f"Keep {who} from the reference image exactly the same: same face, age, beard, hair, ornaments and clothing, "
                              f"in the same painting style. New scene: {v['prompt']}")
                    wf = reference_keyframe_workflow(ref_names, prompt, v["negative"], seed, prefix=pre)
                else:
                    wf = keyframe_workflow(v["prompt"], v["negative"], seed, prefix=pre)
                _, secs = cf.run(wf, out)
                log(f"generate: {s['id']} keyframe take {k}{' (from ' + ','.join(s['reference']) + ')' if ref_names else ''} ({secs:.0f}s) -> {os.path.relpath(out, P)}")
        clip = os.path.join(P, "clips", sid, f"{s['id']}{tag}.mp4")
        if what in ("clips", "both") and (force or not os.path.exists(clip)):
            if not os.path.exists(img):
                log(f"generate: {s['id']} has no keyframe yet; run with --what images first"); continue
            name = cf.upload(img)
            # video prompt = motion + camera only; the image negative (style terms) is not reused for video
            _, secs = cf.run(clip_workflow(name, v["motion_prompt"], VIDEO_NEGATIVE, _seed(s["id"], sid, "clip"),
                                           quality, prefix=f"vak/{sid}/{s['id']}", steps=steps, shift=shift), clip)
            log(f"generate: {s['id']} clip ({quality}, {secs:.0f}s) -> {os.path.relpath(clip, P)}")
    log(f"generate: done for style '{sid}'. Build the film with: python -m vak run {os.path.relpath(project)} --style {sid}")
