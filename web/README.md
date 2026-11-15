# Vāk web app (buildathon v1, 2026-11-14)

A local web app on top of the `vak` engine: **library + learning player** and **create a chant film** with a
background job queue. Run it with one command from `vak_engine/`:

```
vak_web.cmd                      (or: .venv\Scripts\python -m web [--port 8787] [--no-browser])
```

It opens http://127.0.0.1:8787.

## Interface (rebuilt 2026-11-14 on the "Utsav" design system)
- `/` → `web/static/studio.html`: Vāk Studio. Home has a composer that reads the chant live (preview + Identified/Interpreted), a templates shelf, tools and an Explore gallery with hover-to-play previews. Chant to film (workspace) covers review, editable English, voice (library / upload / recite) and style, then a live render view and the result. The film page has a synced player with tap-a-word, loop line, practice speed, remix and download. There's also a Ctrl K palette and light/dark/auto themes.
- `/static/vak-ds.css`: the design system (tokens + components); reference page `/static/design-system.html`.
- `/legacy`: the first v1 interface (`legacy.html` + `app.js` + `style.css`), kept for reference.
- New API: `POST /api/films/{id}/remix {style}` re-renders a film's project (same chant, recording and line timings) in another free style. Narrated films can't be remixed yet.
- Chants can be typed in Devanagari, IAST or casual English spelling (`vak/romanize.py`). Known chants (`knowledge/chants.json`: Om Namaḥ Śivāya, Om Namo Nārāyaṇāya, Gaṇapati, Hare Kṛṣṇa, Lokāḥ Samastāḥ, Oṃ Śānti, plus the library presets) map to their canonical text, meaning and source. IAST converts exactly. Other English spellings get a best guess marked "Check the spelling". The default voice is neural recitation, so Generate never opens a file picker unless Upload is chosen.
- Placeholders in the UI: meaning narration, Reel maker, 9:16, Recitation and Styles pages, and Pro (GPU) styles show a notice.

## Stack and why
- **FastAPI + uvicorn** in the engine's own venv. It imports the engine directly (`vak.create`, `vak.text`,
  `vak.planner`), so there's no second implementation of text, plan or timing logic, and no extra runtime.
- **Plain HTML/JS/CSS** (`web/static/`), with no build step and no npm for the UI. Fonts are served from the engine's
  `vak/assets/node_modules/@fontsource`, so the demo works offline.
- **Local files** instead of a database: projects and renders live in `chants/`, and jobs, uploads and thumbnails in
  `web/data/`. That's enough for one laptop. Supabase (Postgres + storage) is the obvious next step for accounts
  and sharing.
- **Job runner**: one worker thread and a FIFO queue. Each job (1) creates the project folder with
  `vak.create.new_project`, then (2) runs `python -u -m vak run <project> --style <id> --cache chants/studio/.vak_cache`
  as a subprocess and reads its log for progress (`[anim] frame i/n`, `edit: …`, `done in`). Jobs persist in
  `web/data/jobs.json`. A job that was running when the server stopped runs again on the next start, and the
  engine cache makes the rerun cheap.

## What works
- **Library**: every `chants/**/renders/**/*.mp4` (films, studio films, vertical reels) with posters, style,
  duration and a provenance badge (Identified / Interpreted).
- **Player**: the video plus a learning panel driven by the film's storyboard. It shows the current line in
  Devanagari, IAST and English, with each word sung / current / upcoming. In narrated films, the story line is
  shown before `timeline.chant_start`. Tap a word to get its meaning, the words inside a sandhi form, and
  "▶ Hear it". Tap a line to jump there. Film time = recording time + `timeline.voice_offset`.
- **Create**:
  1. Pick a preset (Gāyatrī, Mahāmṛtyuñjaya) or paste Devanagari.
  2. Review the lines, IAST, word meanings (from `knowledge/glossary.json`) and editable English lines, plus the
     planned scenes.
  3. Choose a voice: the library recording (Gāyatrī music track with manual line timings), an upload (lines found
     from pauses), or neural recitation (draft; hi-IN voice via edge-tts).
  4. Choose a style: `shadow_puppet` or `silhouette`. The free ones run on the laptop in ~3 min; the GPU styles are
     listed as premium, coming soon.
  5. Generate. A job page shows progress, and the film appears in the library with **Watch**.

## Engine additions (in `vak/`)
- `planner.py`: a rule-based stand-in for the Claude Planner. It writes a style-family plan (shadow puppets or
  silhouette + sacred geometry) for any chant: night → dawn → full light, with a seeker at the river, the sun, the
  sung word written in light, a mandala or yantra, and a lotus. Every time is anchored to chant words, so it works
  with any recording. It never invents a story.
- `create.py`: `preview(text)` and `new_project(dest, …)`, also available as `python -m vak new DIR --chant chant.txt --title T (--audio F | --recite)`.
- `recite.py`: neural recitation when there is no recording. It returns exact line timings as `segments`.
- `text.word_meanings`: word glossary (`knowledge/glossary.json` + optional project `words.json`) → `w.meaning`, `w.split`.
- `pipeline.py`:
  - `"animation": "auto"` uses or writes `anim_plan_<family>.json`, and a missing plan is written by the planner.
  - Every film gets `<film>.storyboard.json` next to it, so each film keeps its own timeline.
  - The cache path is made absolute.
- `anim.py` + `util.stream`: the frame progress of the renderer is streamed to the log.

## Left for later
- **Claude Planner**: it will replace `planner.py` once an `ANTHROPIC_API_KEY` is set (structured output in the same
  plan format), along with the Critic (frame sheets → fixes) and `translate: "claude"` for pasted chants.
- **Narrated films from the create flow**: `narrated.py` works for the Viśvāmitra film, but the create flow doesn't
  offer it yet. The next step is "meaning narration" (the narrator explains each line, then the chant), which is
  grounded, with a planner for line-anchored story scenes.
- **Identify step**: corpus matching (GRETIL / Wikisource), viniyoga/dhyāna extraction, and genre → playbook. A human
  review queue for Interpreted chants.
- **Accounts, sharing, payments, hosted storage** (Supabase), and an embed/share page.
- **GPU styles**: start a RunPod pod from a job with cost confirmation; never automatic.
- **Manual line timing in the UI**: for music tracks with uploads, a tap-along to set segments.
- **Teacher review**: of pronunciation (especially neural recitation), translations and glossary meanings before
  public use.

## Sign-in (email + one-time code, Supabase Auth; added 2026-11-15)
- Code: `web/auth.py` (routes `/api/auth/send`, `/verify`, `/me`, `/logout`) and the sign-in dialog in `studio.html`
  (account chip at the bottom of the left rail). No passwords and no JS SDK: the server talks to Supabase Auth and keeps
  the session in httpOnly cookies (`vak_at` access token, `vak_rt` refresh token, 30 days), refreshing it when it expires.
- Env (`.env.local`): `SUPABASE_URL` + `SUPABASE_PUBLISHABLE_KEY` (preferred for Auth) or the existing `SUPABASE_SECRET_KEY`.
  `VAK_REQUIRE_LOGIN=1` makes Generate, Remix, Upload and Share need a signed-in user (off by default, so the demo works
  signed out). Jobs remember their `owner`; it is mirrored to `jobs.user_id` (run the last lines of `supabase/schema.sql`).
- **Email via Resend (preferred, no Supabase dashboard setup):** add `RESEND_API_KEY=re_...` to `.env.local` and
  optionally `VAK_MAIL_FROM=Vāk <login@yourdomain.com>`. The server asks Supabase for an 8-digit code without sending
  (admin `generate_link`, uses the secret key; creates the account on first sign-in) and emails it with Resend.
  Until a domain is verified in Resend, the default sender `onboarding@resend.dev` only reaches the Resend account
  owner's address; others get "Email is in test mode".
- Without `RESEND_API_KEY`, Supabase sends the email itself; then set up in the Supabase dashboard, once:
  1. Authentication → Sign In / Providers → Email: enabled (it is), "Allow new users to sign up" on.
  2. Authentication → Emails → Templates: put the code `{{ .Token }}` in **Magic link** and **Confirm signup**
     (by default they only contain a link). Example body: `<h2>Your Vāk code</h2><p>{{ .Token }}</p><p>It expires in an hour.</p>`
  3. For real users: Authentication → Emails → SMTP settings → custom SMTP (Resend, Postmark, SES, ...). The built-in sender
     only delivers to your project team's addresses and a few emails per hour.
  4. Optional: Authentication → Rate limits, and OTP length/expiry under the Email provider.
- Hosting (Railway, planned 2026-11-15): when `PORT` is set the app listens on `0.0.0.0:$PORT`, opens no browser, trusts
  the proxy's forwarded headers and marks the sign-in cookies `Secure` (HTTPS only). Set the `.env.local` values as
  Railway variables instead (`SUPABASE_URL`, `SUPABASE_SECRET_KEY`, `RESEND_API_KEY`, `VAK_MAIL_FROM`, ...). Job cancel
  kills the job's process group on Linux (`taskkill` on Windows).

## Deploying to Railway (set up 2026-11-15)
Files: `Dockerfile` (Playwright 1.65 noble image + Python venv + ffmpeg + `npm ci` in `vak/assets`), `railway.json`
(Dockerfile build, health check `/api/auth/me`), `web/start.sh` (volume links + first-boot seed), `.railwayignore`/
`.dockerignore` (code only: no `.env.local`, `.venv`, `chants/`, `art/`, media).
- **Library seed**: the films (~460 MB) are too big for `railway up`, so `python -m web.seed push` (run here) packs `chants/`
  (minus studio, work folders, GPU clips/images) + `art/` into 45 MB parts in the private Supabase bucket `seed`; the server
  unpacks it into the volume on first boot (`/data/.seeded` marks it done). Re-run push and delete `/data/.seeded` to refresh;
  `--with-studio` includes your local studio films.
- **Volume** at `/data` holds `chants/`, `art/` and `web/data/` (jobs, uploads) via symlinks, so films survive redeploys.
- **Variables** (Railway → service → Variables, set by you): `SUPABASE_URL`, `SUPABASE_SECRET_KEY`, `RESEND_API_KEY`,
  `ANTHROPIC_API_KEY`, `ELEVENLABS_API_KEY`, optional `VAK_MAIL_FROM`, `VAK_REQUIRE_LOGIN=1`, `VAK_COMFY_URL` (GPU pod).
  Railway sets `PORT`; the app then binds 0.0.0.0, trusts proxy headers and uses Secure cookies.
- Commands (from `vak_engine/`): `railway login` → `railway init -n vak-studio` → `railway up --detach` (creates the
  service) → `railway volume add --mount-path /data` → set variables → `railway up` → `railway domain`.
- **From GitHub (the chosen route):** make `vak_engine/` the repo root (its `.gitignore` keeps secrets, `.venv`,
  `node_modules` and all media out: ~3 MB of code). Railway → New project → Deploy from GitHub repo; it finds
  `railway.json` + `Dockerfile`. If the repo root is a parent folder, set Settings → Root Directory to the `vak_engine`
  path. Then: attach a volume at `/data`, paste the variables, Settings → Networking → Generate domain.
  Don't commit the CLAUDE.md files above `vak_engine/` to a public repo: they hold the password-less ComfyUI pod URL.
