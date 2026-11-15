# vak: Sanskrit chant → film engine

Give it a chant's text, a recording and a visual per scene; it produces a film with a painted
title card, word-synced Sanskrit / transliteration / English captions, a tanpura score in the
chanter's key, gentle pitch correction, and a layered 2.5D camera move.

```
python -m vak units chant.txt          # preview how the text splits into chanted units
python -m vak run project.json         # build storyboard.json + the film
```

## Pipeline (all modules read and extend one `storyboard.json`)

| Module | File | Does |
|---|---|---|
| Text | `vak/text.py` | Parses verses and speaker lines, splits half-verses into pādas by syllable count, transliterates (IAST), counts syllables per word, fills translations (manual table or LLM) |
| Story | `vak/story.py` | Builds scenes from the project, applies the praise-sections playbook, writes prompts for scenes without visuals, derives speaker labels |
| Audio | `vak/audio.py` | Finds the tonic, detects chanted phrases from pauses, aligns them to units (merge/split when counts differ), times each word by syllables, optional pitch correction |
| Visuals | `vak/visuals.py` | Model adapters (file, manual queue, API placeholder); lists missing visuals in `to_generate.json` |
| Motion | `vak/motion.py` | Slow-motion playthrough (no ping-pong), figure cut-out + background fill, layered camera move, Ken Burns fallback |
| Edit | `vak/edit.py` | p5.brush watercolour title card, caption states, light motes, tanpura score, assembly and mix |

Every expensive step is cached in `.vak_cache/` by its inputs, so changing a translation only
re-renders the captions and the final mix.

## Setup
```
pip install -r requirements.txt        # includes elevenlabs (key in .env.local via `npx @elevenlabs/cli onboard init`)
cd vak/assets && npm install          # p5, p5.brush, fonts
npm install -g playwright && npx playwright install chromium
# ffmpeg on PATH; rembg downloads its cut-out model on first use
```

## Example
`examples/verse1/` rebuilds Devi Kavacham verse 1 from `chant.txt`, `translations.json`,
`recording.m4a` and the scene clip `S02.mov`.

## Next
- API adapters for image/video models (MiniMax H3, Seedance, Veo) in `visuals.py`
- TTS adapter (Indic Parler-TTS) so a recording becomes optional
- Automatic subject box for the cut-out; more playbook techniques (accumulation, mandala)
- Knowledge library (characters, story arcs, context) feeding `story.py`
