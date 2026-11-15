# Buildathon checklist (Nov 14–15, 2026)

## Now
- [x] Refine both live styles (Nāda cymatics, Liquid gold) in `web/static/vakfx.js`: deity palettes, tilted bronze plate with
      coloured sand and word ripples, light rays and gold dust in the water
- [x] Film page "Look" switcher: Rendered film / Nāda / Liquid gold, drawn live from the film's audio + word timings, with captions
- [x] Create flow: Nāda / Liquid gold are styles of a new film ("live films": `--style nada|gold` stops after audio and writes
      `renders/<name>_<style>.live.json`; ready in ~3–5 s; Liquid gold is the default style)
- [x] Posters for live films: the player sends a frame it drew (`POST /api/films/{id}/poster`)
- [ ] MP4 export of the live styles (record from the browser, or render on a GPU)
- [x] Live style 3 **Kaṇa · particles of light** (`web/static/vakfx_motion.js`, `--style kana`): 14k grains form ॐ, then each sung word,
      then the deity's symbol; voice makes them shimmer. In Create, the Look switcher and Remix
- [ ] Prototypes in `vakfx_motion.js`, not in the Studio yet: `rekha` (line drawing), `morph` (liquid forms), `akshara` (kinetic type)
- [ ] Live films: a short title intro before the chant; brighter auto-poster (capture later in the chant)

## Later tonight
### Status (2026-11-15, built; waiting for keys to test online)
- [x] `web/cloud.py` (Storage upload, table upserts, status check) + `web/supabase/schema.sql` (chants, films, jobs, RLS, public `films` bucket)
- [x] Share button: records a live film in the browser (visuals + captions + audio → MP4 via `/recording`), then `/share` uploads to
      Supabase Storage and returns the public link; offline it returns a local link. Job rows sync in the background; chants sync at start.
- [x] `vak/eleven.py` + `knowledge/pronunciation.json`: ElevenLabs voice per line, respelled from our guide (auto IAST syllabifier
      for unknown words); "ElevenLabs" voice option in Create (shown as not connected until the key is set)
- [ ] Set keys (user): ~~ELEVENLABS_API_KEY~~ done; ~~SUPABASE_URL~~ done, ~~schema.sql~~ applied to "Vak AI"; SUPABASE_SECRET_KEY (sb_secret_..., not the legacy service_role) in .env.local
- [x] Test: ElevenLabs film end to end (Lokāḥ samastāḥ, Liquid gold); Share → public Supabase URL (rendered MP4) works
- [x] Chant voice chosen by listening: **Pranit** (Voice Library, devotional Hindi) from the Devanagari text with a Hindi hint, eleven_v4;
      the English respelling stays as `ELEVENLABS_MODE=respell`. Story narration stays George (English)
- [x] **Sung chant** voice (approved by ear 2026-11-15): ElevenLabs Music `music_v2_5` sings the Devanagari lines (tanpura, bansuri,
      soft tabla, deep calm male voice); exact word times from its timestamps (`eleven.sing`, `recite="eleven_music"`, "Sung" in Create)
- [ ] Share a live film (browser recording → MP4 → Supabase) and open it on a phone

### Supabase (database + storage)
- [ ] Share links: upload finished films to Supabase Storage, public URL per film, "Share" button uses it
- [ ] Tables: chants, films, jobs (and a teacher-review status per chant/film)
- [ ] Keep the local mode working offline for the stage demo (Supabase optional at runtime)
- [ ] Later: accounts + teacher role, review queue, knowledge layer (chants, glossary, pronunciation) in Postgres

### ElevenLabs voice
- [x] `ELEVENLABS_API_KEY` in `.env.local` via `elevenlabs onboard` (gitignored; loaded by python-dotenv in `vak/envfile.py`);
      chant voice (`vak/eleven.py`) and story narration (`narration.engine: "eleven"` or `VAK_NARRATOR=eleven`) use the SDK
- [ ] `knowledge/pronunciation.json`: per-word respellings that fix pronunciation (e.g. समस्ताः → "Sah-mah-staa-ha",
      भवन्तु → "Bhah-vahn-too"); reused across chants; teacher-reviewable
- [ ] Engine voice adapter: build the ElevenLabs input from the chant (Devanagari where it's right, respelling where not),
      one clip per line so word timing stays exact; two modes: Eleven Music (sung, showcase) and speech v3 (clear, learning)
- [ ] Create flow: "ElevenLabs chant" voice option; label films "AI chant · awaiting teacher review"
- [ ] Generate showcase chants on the paid plan used publicly (free-plan tracks are not commercially licensed later)
- [ ] Pre-generate demo chants; keep live generation only for the "paste any chant" moment

## Interpreter (built 2026-11-15)
- [x] `vak/interpret.py` + `/api/interpret` + workspace context card + film Story tab; job step "Reading the chant with Claude"
- [ ] ANTHROPIC_API_KEY in `.env.local` (user), then test with chants outside the library
- [ ] Next (story-first): cited story → storyboard → narration → animation/video from the interpretation

## Audio sources decided
- Vedic mantras: human recordings. Gāyatrī = Wikimedia CC0 (Rameshvar); Mahāmṛtyuñjaya = Veda Prasara Samiti via
  Vedavani (uploader-marked public domain: ask before public release). See each chant's SOURCES.md.
- Everything else: ElevenLabs with our pronunciation layer. Neural recitation (edge-tts) stays as the free draft fallback.
