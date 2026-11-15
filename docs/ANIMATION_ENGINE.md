# Animation engine (option B): storyboard → plan → style renderer → film

Decided 2026-11-13. A code-animation path beside the AI-video path: cheap (~$1 of Claude per film), fast
(minutes), deterministic, and no face problems. **Styles are built one at a time**: one renderer is finished and
approved before the next one starts.

## Pipeline

```
storyboard (project.json + audio timings from audio.py)
  → Claude Opus 5.5 "Planner" (structured output) → plan.json   (style-agnostic: what, how it moves, when)
  → validator (elements exist in the library, times inside the audio)
  → style renderer (TypeScript, headless browser via Playwright, frames piped to ffmpeg)
  → existing edit.py (title card, captions, audio, export 4:2:0 / 48 kHz)
  → Claude "Critic": 4-frame sheet per shot vs storyboard intent → small JSON fixes (max 2 rounds)
```

## Plan format (per shot)

- `start`/`end` and every event time anchored to `{unit, syllable}` (re-timed automatically by new audio).
- `camera`: push_in / pull_back / pan / crane / fixed, with easing.
- `layers`: library elements with position (0–1 frame coords), scale, pose, attachments (`attach`, `wrap`).
- `events`: semantic actions (light_burst, dissolve_to_embers, draw_on, bloom, fall, walk_to, particles…).
- No style words in the plan. The renderer decides how "light_burst" looks.

## Symbol library (built once, reused for every chant)

Sacred (liṅga, diya, Om from the font, yantra, fire altar, bilva…), nature (sun, moon, stars, river, ghat,
mountains, banyan, lotus bud→open, clouds, birds, cucumber on vine), places (hut, shrine, temple, courtyard),
figures as puppet rigs with ~8 poses (stand, walk, sit, pray, offer water, embrace, bow, run), forces
(horned shadow, buffalo, noose, light column, embers, smoke, petals). Iconography is fixed in the library and
reviewed once by a person; deities appear only as light, symbol or shadow.

## Styles (build order: one at a time)

| # | Style | Notes |
|---|---|---|
| 1 | Shadow puppets (tholu bommalata) | Backlit leather, jointed figures; suits legends; no faces |
| 2 | Kolam / rangoli line art | Self-drawing white lines on dark ground |
| 3 | Sacred geometry | Yantras, mandalas, light; no figures |
| 4 | Pattachitra | Bold borders, flat fills, patterns |
| 5 | Gold temple line-work | Gold strokes on black/deep red |
| 6 | Ink wash | Brush bleed, empty space |
| 7 | Watercolour (p5.brush) | Light scenes only (slow) |
| 8 | Stained glass | Lead lines, light through cells |
| 9 | Devanagari kinetic typography | Letters of the mantra build the picture |
| 10 | Low-poly 3D (Three.js) | Real camera moves |

Each style is "done" when: the Gāyatrī renders end to end, every shot passes the frame-sheet check,
the user approves it, and its look is documented here (palette, line, fill, light, motion feel, transition).

## Claude's jobs

Planner (once per film), Critic (frame sheets → fixes), optional hero-moment code (sandboxed, with
fallback), drafting new library SVGs for human approval.

## Cost and time

Planner ~$0.50 + Critic ~$0.20 per style (Claude Opus 5.5). Rendering 90 s @ 24 fps ≈ 2–4 min per style on a
laptop.

## Risks

Puppet/library art quality decides premium vs cheap; Claude's spatial layout (use layout helpers + Critic);
p5.brush speed.

## Status

- **Style 1, shadow puppets: first version done (2026-11-14), awaiting approval.** `python -m vak run chants/gayatri/project.json --style shadow_puppet`
  → `renders/gayatri_shadow_puppet.mp4` (49 s, built in ~3 min on the laptop, no GPU). Files: `vak/anim.py`,
  `vak/assets/anim.js` (frame driver → ffmpeg), `vak/assets/anim/core.js` (shared), `vak/assets/anim/shadow_puppet.js`
  (style), `chants/gayatri/anim_plan.json` (8 scenes, hand-written in the Planner's format; no Anthropic API key on this laptop yet).
- Quick checks without a full render: `node vak/assets/anim.js shadow_puppet <data.json> <dir> --stills 9,25.5,40`
  (data.json = {plan, units from storyboard.json}).
- Elements so far: screen, stars, moon, sun, river, ghat, temple, palm, hills, clouds, worlds, diya, lotus, egrets, sage (5 poses + walk).
- **Style 2, silhouette paper-cut + sacred-geometry finale: first version done (2026-11-14).** Narrated film
  `chants/gayatri/vishvamitra/` (`python -m vak run chants/gayatri/vishvamitra/project.json`) → `renders/vishvamitra_silhouette.mp4`
  (2:13, built in ~15 min incl. a new title card). Narration: offline Windows voice "Ravi" (en-IN) via `vak/narrate.py` +
  `assets/tts_windows.ps1`; a recorded voice can replace it with the same line timings. Assembly: `vak/narrated.py`
  (card → story with subtitles over a tanpura bed → the chant recording from `track_from`, with word captions).
  Plans: `story_plan.json` (anchored to narration lines `{n}`) + `mantra_plan.json` (recording time, shifted onto the film).
- What Claude-made animation does best (decided 2026-11-14): silhouettes/paper-cut, sacred geometry and light,
  Devanagari kinetic type, self-drawing line art, puppets. Weak: detailed painted figures (Pattachitra etc.) — for those,
  "AI paints the parts, Claude rigs and animates" is the planned hybrid.

## GPU-drawn Indian-art library (started 2026-11-14)

Pieces the animator can move as cut-out layers, drawn by Qwen-Image on the RunPod pod:
`python -m vak art art/library.json --style pattachitra [--items a,b] [--takes 3] [--force] [--cut-only]` (`vak/artgen.py`).
Elements are drawn alone on a plain ground (square), cut out with rembg isnet and trimmed → `art/<style>/<id>.png`;
backgrounds → `art/<style>/bg/`; `index.json` (file, size, anchor, tags) for the animator; `sheet.jpg` to review.
Library rules: side views face right; moving parts are separate pieces (diya + flame, sun + rays ring, egret wings
up/down, lotus bud/half/open); size class sets line weight; white subjects drawn on indigo for a clean cut;
backgrounds leave empty sky/water and contain nothing the animator adds. Styles in `ART_STYLES` (pattachitra tuned;
madhubani, kalamkari, gond drafted). ~37 s per element, ~66 s per referenced sage pose.
Prompt lessons: **subject first**, then style. Style words about eyes/ornaments only for people and animals — on
objects "almond-shaped eyes … jewellery" painted a woman inside the sun. Objects get "no person, no face, no figure".
Pattachitra first pass (31 pieces): objects, plants, animals good; sage poses drift in costume and skin colour
(Qwen-Image-Edit reference not enough) → retake with `--takes 3` and pick; star came out 5-pointed; banyan greyish.
- **Style 2 approved (2026-11-14), version 3:** narrator = Microsoft neural voice `en-IN-PrabhatNeural` via edge-tts
  (`"engine": "edge"` in the project's narration; free, text is sent to Microsoft; retries built in). Piper
  (`en_US-ryan-high`, offline, in `models/piper/`) is kept as an alternative but mispronounces Sanskrit names.
  Lessons: no canvas `filter: blur` (renders 20x slower without a GPU); the shoulder scarf read as a cape, so it is
  opt-in (`"scarf": 1`); riders sit with their hip on the horse's back (`horse` element seats them).

## Rule-based planner (2026-11-14, stand-in for the Claude Planner)
`vak/planner.py` writes a plan for any chant in the shadow-puppet or silhouette family (night by the river → dawn →
full light; sung word in light, mandala/yantra, lotus, egrets), one scene per line for short chants, ~6 s groups for
long ones, every time anchored to chant words. Projects with `"animation": "auto"` use `anim_plan_<family>.json`
(written on demand). Used by the web app's create flow (`web/README.md`). Replace with the Claude Planner's output
when an API key is set; same format.

## Style 3: Yantra + Akshara (figure-free; the default for chants without a story; 2026-11-14)
`--style yantra` → `vak/assets/anim/yantra.js`, plans from `planner._yantra_plan`. The planner detects the deity from the chant's own
words (`planner.DEITIES`: Śiva, the Goddess, Viṣṇu, Gaṇeśa, the Sun; otherwise "peace"). That sets the palette (Śiva indigo, Sun gold, peace teal...),
the yantra (hexagram, Śrī-style triangles, lotus, sun star; always inside a square bhūpura gate with petal rings) and four line-art
symbols (crescent, trident, bilva / conch, discus, lotus / gaṃ / sun, diya; Om for all). Each sung word is written in light at the centre
(outline drawn by a dash animation, then fill and glow), every word start sends a pulse and a ripple, the geometry finishes drawing by
about 40% of the chant, light grows toward the end, and it closes on a bindu. No people, faces or deity images.
Decided with the user: shadow puppets and silhouette are offered only for chants with a cited story; the web app hides them otherwise.
Renders: Oṃ Namaḥ Śivāya 39 s, Gāyatrī (49 s) 4:15, Lokāḥ Samastāḥ 44 s.
