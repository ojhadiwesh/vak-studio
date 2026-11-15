# Vāk — Evaluation report

**What we evaluate:** the first step of the core flow. A person pastes or types a chant however they know it
(Devanagari, IAST, casual English spelling, typos, partial lines). Vāk must either **recognise the right chant**
from its knowledge layer, so it can show the canonical text, meaning and source with an **"Identified"** badge,
or say honestly that it is **not identified** (then it falls back to meaning-based visuals and never invents a story).

**Why this metric fits:** a wrong "Identified" badge is the costly error, because it would attach a false source and
meaning to someone's prayer. So we report **precision of claimed matches** and **false identifications** next to
accuracy and recall. For identified chants we also check that the Devanagari Vāk shows is exactly the canonical text.

## How to run (reproducible, offline, no API key)

```bash
pip install indic-transliteration       # the only dependency
python eval/run_eval.py --baseline      # the matcher before this work
python eval/run_eval.py                 # the current matcher
```

Writes `eval/results.json`, `eval/results_baseline.csv` and `eval/results_current.csv` (every example with
the prediction and whether it was correct). The dataset is `eval/chant_id_dataset.jsonl`; `eval/make_dataset.py`
rebuilds it.

## Dataset: 106 examples

| Slice | n | What it is |
|---|---|---|
| Hand-written (`kind: hand`) | 36 | Spellings people really type: "Om Namah Shivay", "Ganpataye", "Krsna", "bhavanthu", typos, dropped syllables; plus 10 hard negatives: real chants **not** in our knowledge layer that look similar (Om Namo Bhagavate Vāsudevāya vs Om Namo Nārāyaṇāya, Sarve Bhavantu Sukhinaḥ vs Lokāḥ Samastāḥ, Gāyatrī, Mahāmṛtyuñjaya, Om Maṇi Padme Hūṃ) |
| Systematic variants (`kind: variant`) | 60 | For each of the 6 known chants: canonical Devanagari, Devanagari without daṇḍas, IAST, IAST upper case, title case, double spaces, trailing period, padding, hyphens, no spaces |
| Noise negatives | 10 | Devanagari openings of other chants, a greeting, keyboard noise, numbers, single deity names, "om om om" |

Every label was written by hand by the team. The 36 hand-written examples were checked line by line
(column `note` says what each one tests).

## Results: before and after

| Metric | Before (exact key match) | After (`romanize.identify`) |
|---|---|---|
| Accuracy (106) | 0.821 | **1.000** |
| Recall on known chants (76) | 0.779 | **1.000** |
| Precision of claimed matches | 1.000 | **1.000** |
| False identifications | 0 | **0** |
| Devanagari exact on identified | 1.000 | **1.000** |
| Hand-written subset accuracy (36) | 0.806 | **1.000** |

**Failures found by the baseline (19):** every chant typed in **Devanagari** (12: the matcher only looked at Latin
input, so a devotee pasting the real text got "not identified"), dropped final syllables ("Shivay", "narayana"),
Hindi spellings ("Ganpataye"), small typos ("nmah", "ganapatye") and a two-line mahāmantra with "ram".

**What we changed:** `vak/romanize.py::identify` transliterates Devanagari to IAST before matching, folds
spelling variants (krsna/krishna, long vowels, aspirates), and accepts a near-match only when the similarity is
≥ 0.90 and the length is within ~12 %, so close-but-different prayers stay unmatched (hard negatives: 0 false IDs).
The web app now uses it (`to_devanagari`).

## Limits (honest)
- The knowledge layer has 6 short chants, so this measures the matcher, not coverage. The next step is the corpus
  match against GRETIL / Wikisource for long stotras.
- We wrote the dataset and the fix, so there is a risk we fit to our own examples. The threshold was set once,
  before the final run, and the hard negatives were written to resist it. A held-out set typed by devotees we
  haven't met is the next test.
- Unknown chants go to the Claude Interpreter (`vak/interpret.py`), which returns a confidence and a citation or
  "unknown". It isn't in this offline eval because it needs an API key; its output is marked **Interpreted** and
  goes to a human review queue before publishing.
