"""Reproducible eval: chant identification from free-form input.

    python eval/run_eval.py            # current matcher (vak.romanize)
    python eval/run_eval.py --baseline # the original exact-key matcher, for the before/after table

Metrics: accuracy (right chant or right "not known"), precision of claimed matches (a wrong "Identified" badge is
the costly error: it would show a false source), recall on known chants, Devanagari exact-match on identified chants.
Writes eval/results.json and eval/results_<mode>.csv. Deterministic, offline, no API key."""
import csv, json, os, re, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from vak import romanize  # noqa: E402

DEV = re.compile(r"[ऀ-ॿ]")


def baseline(text):
    """The matcher as it was before this eval (exact loose key, Latin input only)."""
    if DEV.search(text):
        return None
    k = romanize.key(text)
    if len(k) < 4:
        return None
    for c in romanize.known_chants():
        keys = [romanize.key(a) for a in c.get("aliases", [])] + [romanize.key(romanize.s.transliterate(c["text"], romanize.s.DEVANAGARI, romanize.s.IAST))]
        if k in keys:
            return c
    return None


def current(text):
    return romanize.identify(text)


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    mode = "baseline" if "--baseline" in sys.argv else "current"
    fn = baseline if mode == "baseline" else current
    rows = [json.loads(l) for l in open(os.path.join(ROOT, "eval", "chant_id_dataset.jsonl"), encoding="utf-8")]
    canon = {c["id"]: c["text"] for c in romanize.known_chants()}
    out, tp, fp, fn_, tn, dev_ok = [], 0, 0, 0, 0, 0
    for r in rows:
        c = fn(r["input"]); got = c["id"] if c else None; exp = r["expected_id"]
        ok = got == exp
        if exp and got == exp: tp += 1; dev_ok += c["text"] == canon[exp]
        elif got and got != exp: fp += 1
        elif exp and not got: fn_ += 1
        else: tn += 1
        out.append({**r, "predicted_id": got, "correct": ok})
    n = len(rows); known = sum(1 for r in rows if r["expected_id"])
    hand = [o for o in out if o["kind"] == "hand"]
    res = {"mode": mode, "n": n, "accuracy": round(sum(o["correct"] for o in out) / n, 3),
           "precision_of_matches": round(tp / (tp + fp), 3) if tp + fp else None,
           "recall_on_known": round(tp / known, 3), "false_identifications": fp,
           "devanagari_exact_on_identified": round(dev_ok / tp, 3) if tp else None,
           "hand_subset_accuracy": round(sum(o["correct"] for o in hand) / len(hand), 3), "hand_n": len(hand),
           "failures": [{k: o[k] for k in ("id", "input", "expected_id", "predicted_id", "note")} for o in out if not o["correct"]]}
    with open(os.path.join(ROOT, "eval", f"results_{mode}.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0].keys())); w.writeheader(); w.writerows(out)
    allres = {}
    p = os.path.join(ROOT, "eval", "results.json")
    if os.path.exists(p):
        allres = json.load(open(p, encoding="utf-8"))
    allres[mode] = res
    json.dump(allres, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({k: v for k, v in res.items() if k != "failures"}, indent=1))
    print(f"{len(res['failures'])} failures:")
    for x in res["failures"]:
        print("  ", x["id"], repr(x["input"][:60]), "expected", x["expected_id"], "got", x["predicted_id"])


if __name__ == "__main__":
    main()
