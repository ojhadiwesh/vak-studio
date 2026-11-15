"""Red-team run: every prompt goes through the same screen the app uses (vak.safety.check).
    python safety/run_redteam.py
Attack prompts (expected crisis/block) + domain prompts that must stay ALLOWED (chants that talk about death,
destruction, protection, healing). Writes safety/redteam_results.csv + redteam_summary.json. Deterministic, offline."""
import csv, json, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from vak import safety  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")
rows = [json.loads(l) for l in open(os.path.join(ROOT, "safety", "redteam_prompts.jsonl"), encoding="utf-8") if l.strip()]
out = []
for r in rows:
    got = safety.check(r["text"])
    out.append({**r, "got": got["action"], "got_category": got["category"], "pass": got["action"] == r["expected"]})
with open(os.path.join(ROOT, "safety", "redteam_results.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(out[0].keys())); w.writeheader(); w.writerows(out)
att = [o for o in out if o["expected"] != "allow"]; ben = [o for o in out if o["expected"] == "allow"]
cr = [o for o in out if o["expected"] == "crisis"]
summary = {"total": len(out), "passed": sum(o["pass"] for o in out),
           "attacks_caught": f"{sum(o['pass'] for o in att)}/{len(att)}",
           "crisis_detected": f"{sum(o['got'] == 'crisis' for o in cr)}/{len(cr)}",
           "benign_allowed": f"{sum(o['pass'] for o in ben)}/{len(ben)}",
           "failures": [{"id": o["id"], "category": o["category"], "expected": o["expected"], "got": o["got"]} for o in out if not o["pass"]]}
print(json.dumps(summary, indent=1, ensure_ascii=False))
json.dump(summary, open(os.path.join(ROOT, "safety", "redteam_summary.json"), "w", encoding="utf-8"), indent=1)
