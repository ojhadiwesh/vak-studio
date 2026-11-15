"""Command line:  python -m vak run project.json [--cache DIR] [--style ID] [--prompts-only]
                python -m vak styles                 (list visual style presets)
                python -m vak generate project.json [--style ID] [--what images|clips|both] ...
                python -m vak art art/library.json --style pattachitra[,madhubani]   (Indian-art pieces for animation)
                python -m vak units chant.txt        (preview how the text is split)
                python -m vak new DIR --chant chant.txt --title T [--style ID] (--audio FILE | --recite)   (new project)"""
import argparse, json
from . import pipeline, text, styles


def main():
    ap = argparse.ArgumentParser(prog="vak", description="Sanskrit chant -> film engine")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run"); r.add_argument("project"); r.add_argument("--cache")
    r.add_argument("--style", help="visual style preset id; see `python -m vak styles`")
    r.add_argument("--prompts-only", action="store_true", help="stop after the story step and write to_generate.json")
    sub.add_parser("styles")
    g = sub.add_parser("generate", help="fill missing images/clips on a ComfyUI GPU server")
    g.add_argument("project"); g.add_argument("--style"); g.add_argument("--comfy", help="ComfyUI URL (or set VAK_COMFY_URL)")
    g.add_argument("--what", choices=["images", "clips", "both"], default="both")
    g.add_argument("--takes", type=int, default=1, help="keyframe candidates per scene")
    g.add_argument("--scenes", help="comma-separated scene ids, e.g. G01,G03")
    g.add_argument("--quality", choices=["draft", "final"], default="final")
    g.add_argument("--steps", type=int, help="final-quality sampling steps (default 20; official repo uses 40)")
    g.add_argument("--shift", type=float, default=8.0, help="Wan sigma shift (5 = closer to keyframe, 8 = more motion)")
    g.add_argument("--tag", default="", help="suffix for clip filenames, for side-by-side tests (e.g. _s5)")
    g.add_argument("--force", action="store_true", help="regenerate even if files exist")
    t = sub.add_parser("art", help="generate the Indian-art piece library (cut-out elements + backgrounds) on a GPU")
    t.add_argument("library"); t.add_argument("--style", default="pattachitra", help="comma-separated: pattachitra,madhubani,kalamkari,gond")
    t.add_argument("--items", help="comma-separated item ids"); t.add_argument("--takes", type=int, default=1)
    t.add_argument("--force", action="store_true"); t.add_argument("--comfy")
    t.add_argument("--cut-only", action="store_true", help="redo cut-outs, index and sheet from existing raw images (no GPU)")
    u = sub.add_parser("units"); u.add_argument("chant")
    n = sub.add_parser("new", help="create a project folder from chant text (rule-based animation plans included)")
    n.add_argument("dest"); n.add_argument("--chant", required=True); n.add_argument("--title", required=True)
    n.add_argument("--style", default="shadow_puppet"); n.add_argument("--translations", help="JSON {devanagari line: english}")
    n.add_argument("--audio"); n.add_argument("--recite", action="store_true", help="no recording: a neural voice recites (draft)")
    a = ap.parse_args()
    if a.cmd == "run":
        pipeline.run(a.project, a.cache, a.style, "story" if a.prompts_only else None)
    elif a.cmd == "generate":
        from . import generate
        generate.run(a.project, a.style, a.what, a.takes, a.scenes.split(",") if a.scenes else None, a.quality, a.force, a.comfy, a.steps, a.shift, a.tag)
    elif a.cmd == "art":
        from . import artgen
        artgen.run(a.library, a.style.split(","), a.items.split(",") if a.items else None, a.takes, a.force, a.comfy, a.cut_only)
    elif a.cmd == "new":
        from . import create
        tr = json.load(open(a.translations, encoding="utf-8")) if a.translations else None
        create.new_project(a.dest, a.title, open(a.chant, encoding="utf-8").read(), a.style, tr, audio=a.audio, recite=a.recite)
    elif a.cmd == "styles":
        for k, v in styles.PRESETS.items():
            print(f"{k:12s} {v['name']}")
    else:
        for x in text.parse(open(a.chant, encoding="utf-8").read()):
            print(x["id"], x["kind"], x["verse"], x["devanagari"], "|", sum(w["syl"] for w in x["words"]), "syl")


if __name__ == "__main__":
    main()
