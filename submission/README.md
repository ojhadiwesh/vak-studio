# Vāk — Understand what you chant

**Live app:** https://vak-studio-production.up.railway.app (laptop and phone; demo films are preloaded)
**Repo:** https://github.com/ojhadiwesh/vak-studio

## The problem
Hundreds of millions of people chant Sanskrit every day: the Gāyatrī at sunrise, Mahāmṛtyuñjaya for a sick parent,
Devī Kavacham before Navarātri. Most don't know what the words mean. Learning them needs a teacher, a translation
and a recording in three places, and many online "meanings" have no source. Diaspora families and young people feel
it most: they keep the practice but lose the meaning, and the calm and connection it carries.

**Target user:** a devotee or family who chants daily but doesn't read Sanskrit (start: Art of Living and satsang
communities, diaspora families teaching children), and the teachers and content creators who serve them.

## What Vāk does
Paste any chant (Devanagari, IAST or English spelling) → Vāk recognises it, shows the source, splits every word with
its meaning, gives it a voice (your recording, a neural recitation or a sung version) and animates it into a short
film with word-by-word captions. The learning player lets you tap any word, loop a line and slow it down.

- **Grounded:** a provenance badge on every chant (Verified / Identified / Interpreted); no invented scripture.
- **Crisis-safe:** text that signals suicide, self-harm, abuse or a medical emergency gets a calm panel with real
  helplines (Tele-MANAS 14416, KIRAN, 988, 112/911) and nothing is generated.

## Try it (judges)
1. Open the live URL → **Explore** to play a preloaded film (Gāyatrī, Viśvāmitra), tap a word.
2. Type `om namah shivay` or `lokah samastah sukhino bhavantu` → it's identified with source and meaning → Generate.
3. Type any chant you know, or something unusual, and see what it does.
4. Type `I don't want to live anymore` → the support panel with helplines appears.

## Evaluation and safety (reproducible, offline)
```bash
pip install indic-transliteration
python eval/run_eval.py --baseline   # before: 82.1% accuracy
python eval/run_eval.py              # after: 100% on 106 examples, 0 false identifications
python safety/run_redteam.py         # 60/60: 46/46 attacks caught, 20/20 crises, 14/14 sacred texts allowed
```
Reports: `eval_report.md`, `safety_report.md` (with the data-handling note).

## Run it locally
```bash
python -m venv .venv && .venv/Scripts/pip install -r requirements.txt   # Windows; use .venv/bin on macOS/Linux
cd vak/assets && npm install && npx playwright install chromium && cd ../..
python -m web            # http://127.0.0.1:8787  (ffmpeg must be on PATH)
```
Optional keys in `.env.local`: `ANTHROPIC_API_KEY` (reads unknown chants), `ELEVENLABS_API_KEY` (voice),
`SUPABASE_URL` + `SUPABASE_SECRET_KEY` (sign-in).
