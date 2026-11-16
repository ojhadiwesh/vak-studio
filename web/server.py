"""Vāk web app: library + learning player + "create a chant film", on top of the vak engine.

Run (from vak_engine/):   .venv\\Scripts\\python -m web          -> http://127.0.0.1:8787
The engine stays the single source of truth: text/plan previews call vak.create, films are built by a job runner
that runs `python -m vak run <project> --style <id>` as a subprocess, one job at a time, and reads its log for
progress. Everything is local files: chants/ (projects and renders), web/data/ (jobs, uploads, thumbnails)."""
import json, os, re, subprocess, sys, threading, time, uuid, shutil, queue
from fastapi import FastAPI, HTTPException, UploadFile, File, Request, Response
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))          # vak_engine/
sys.path.insert(0, ROOT)
from vak import create, styles as vstyles, text as vtext, planner, romanize, eleven, interpret, storyteller, storybook, cast as vcast   # noqa: E402
from vak.util import duration as audio_duration   # noqa: E402
from vak import safety   # noqa: E402
from web import cloud, auth                                                          # noqa: E402

CHANTS = os.path.join(ROOT, "chants")
STUDIO = os.path.join(CHANTS, "studio")
STUDIO_CACHE = os.path.join(STUDIO, ".vak_cache")
DATA = os.path.join(ROOT, "web", "data")
UPLOADS, THUMBS = os.path.join(DATA, "uploads"), os.path.join(DATA, "thumbs")
JOBS_FILE = os.path.join(DATA, "jobs.json")
STATIC = os.path.join(ROOT, "web", "static")
for d in (STUDIO, STUDIO_CACHE, UPLOADS, THUMBS):
    os.makedirs(d, exist_ok=True)

ENV = dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8")
SKIP_DIRS = {"_work", "master_444", ".vak_cache"}

# Presets: curated chants with cited sources (provenance "Identified": source cited, teacher review pending)
PRESETS = {
    "gayatri": {"name": "Gāyatrī Mantra", "dir": "gayatri", "source": "Ṛgveda 3.62.10",
                "recording": {"file": "audio/pixabay_399098.wav", "label": "Gāyatrī with Om chant (Pixabay 399098, music track, AI-generated voice)"}},
    "mahamrityunjaya": {"name": "Mahāmṛtyuñjaya Mantra", "dir": "mahamrityunjaya", "source": "Ṛgveda 7.59.12", "recording": None},
}


def rel_chants(p):
    return os.path.relpath(p, CHANTS).replace("\\", "/")


def jload(p, default=None):
    try:
        return json.load(open(p, encoding="utf-8"))
    except Exception:
        return default


def jsave(p, obj):
    tmp = p + ".tmp"
    json.dump(obj, open(tmp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    os.replace(tmp, p)


# ------------------------------------------------------------------ library
def project_dir_of(mp4):
    d = os.path.dirname(mp4)
    while os.path.basename(d) in ("renders", "reels") and d != CHANTS:
        d = os.path.dirname(d)
    return d


LIVE_EXT = ".live.json"          # a live film: storyboard + audio, drawn in the viewer's browser (no video file)
is_live = lambda p: p.endswith(LIVE_EXT)
base_of = lambda p: p[:-len(LIVE_EXT)] if is_live(p) else os.path.splitext(p)[0]


def storyboard_for(mp4):
    side = mp4 if is_live(mp4) else os.path.splitext(mp4)[0] + ".storyboard.json"
    sb = jload(side) or jload(os.path.join(project_dir_of(mp4), "storyboard.json"))
    if sb:   # older storyboards have no word meanings: fill them from the knowledge glossary (+ project words.json)
        pd = project_dir_of(mp4); cfg = jload(os.path.join(pd, "project.json"), {}) or {}
        vtext.word_meanings(sb.get("units", []), os.path.join(pd, cfg["words"]) if cfg.get("words") else None)
    return sb


_dur = {}


def duration(p):
    k = (p, os.path.getmtime(p))
    if k not in _dur:
        try:
            _dur[k] = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", p],
                                           capture_output=True, text=True).stdout.strip())
        except Exception:
            _dur[k] = 0.0
    return _dur[k]


def film_id(mp4):
    return rel_chants(mp4).replace("/", "~")


def film_path(fid):
    p = os.path.normpath(os.path.join(CHANTS, fid.replace("~", "/")))
    if not p.startswith(CHANTS) or not (p.endswith(".mp4") or is_live(p)) or not os.path.exists(p):
        raise HTTPException(404, "no such film")
    return p


def context_of(pd, cfg):
    """Claude's reading kept with the project (identification, genre, meaning, cited story) for the film page."""
    if not (cfg or {}).get("interpretation"):
        return None
    it = jload(os.path.join(pd, cfg["interpretation"]), {})
    return {k: it.get(k) for k in ("identification", "genre", "deity_name", "meaning_summary", "dhyana", "viniyoga", "story", "caution", "translation_confidence")} if it else None


def provenance(pd, cfg):
    src = (cfg or {}).get("source", "")
    if (cfg or {}).get("interpretation"):                  # read by Claude (vak/interpret.py)
        it = jload(os.path.join(pd, cfg["interpretation"]), {}) if pd else {}
        name = ((it or {}).get("identification") or {}).get("name")
        if cfg.get("provenance") == "Identified":
            return {"level": "Identified", "note": f"{src}"}
        return {"level": "Interpreted", "note": (f"Recognised by Claude as {name}, but its source isn't verified. " if name else "Context not identified. ")
                + "Translation and meanings are Claude's drafts; a teacher must review before publishing."}
    if "pasted" in src or "not yet identified" in src:
        return {"level": "Interpreted", "note": "Context not identified. Translation and meanings are drafts; a teacher must review before publishing."}
    return {"level": "Identified", "note": f"Source: {src or 'cited in the project (SOURCES.md)'}. Pronunciation and translation await a teacher's review."}


def live_info(p):
    """A live film: audio + word timings + style, drawn in the player by web/static/vakfx.js."""
    pd = project_dir_of(p)
    cfg = jload(os.path.join(pd, "project.json"), {}) or {}
    sb = jload(p, {}) or {}
    lv = sb.get("live", {}); style = lv.get("style", "gold")
    audio = os.path.normpath(os.path.join(os.path.dirname(p), lv.get("audio", "")))
    poster = base_of(p) + ".poster.jpg"
    return {"id": film_id(p), "title": (cfg.get("card") or {}).get("title") or sb.get("title") or os.path.basename(base_of(p)),
            "file": os.path.basename(base_of(p)), "kind": "studio", "live": True, "style": style,
            "style_name": vstyles.PRESETS.get(style, {}).get("name", style), "narrated": False,
            "duration": round((sb.get("audio") or {}).get("duration", 0), 1), "chant": rel_chants(pd).split("/")[0], "dev": first_words(sb),
            "video": f"/media/{rel_chants(audio)}", "has_poster": os.path.exists(poster),
            "poster": f"/media/{rel_chants(poster)}" if os.path.exists(poster) else f"/static/proto/{style}.jpg",
            "mtime": os.path.getmtime(p), "provenance": provenance(pd, cfg), "synced": True,
            "has_export": os.path.exists(base_of(p) + ".export.mp4"), "share_url": SHARES().get(film_id(p)),
            "voice": cfg.get("recited_by") or "Recording", "deity": cfg.get("deity"), "context": context_of(pd, cfg)}


REEL_TITLES = {"reel1_the_kings_army": "The King's Army", "reel2_the_crown_laid_down": "The Crown Laid Down",
               "reel3_the_gayatri_in_light": "The Gāyatrī in Light"}


def first_words(sb):
    """The chant's opening words in Devanagari, for the film card."""
    u = (sb or {}).get("units") or []
    return " ".join(re.sub(r"[।॥०-९]", "", u[0].get("devanagari", "")).split()[:2]) if u else ""


def film_info(mp4):
    if is_live(mp4):
        return live_info(mp4)
    pd = project_dir_of(mp4)
    cfg = jload(os.path.join(pd, "project.json"), {}) or {}
    sb = jload(os.path.splitext(mp4)[0] + ".storyboard.json") or jload(os.path.join(pd, "storyboard.json"), {}) or {}
    name = os.path.splitext(os.path.basename(mp4))[0]
    kind = "reel" if os.path.basename(os.path.dirname(mp4)) == "reels" else ("studio" if rel_chants(mp4).startswith("studio/") else "film")
    style = next((k for k in sorted(vstyles.PRESETS, key=len, reverse=True) if name.endswith("_" + k)), None)
    if kind == "film" and not cfg.get("source"):
        preset = next((p for p in PRESETS.values() if rel_chants(pd).split("/")[0] == p["dir"]), None)
        cfg = dict(cfg, source=preset["source"] if preset else "")
    title = (REEL_TITLES.get(name) or re.sub(r"^reel\d+_", "", name).replace("_", " ").capitalize()) if kind == "reel" else (cfg.get("card", {}).get("title") or sb.get("title") or name)
    return {"id": film_id(mp4), "title": title, "file": name, "kind": kind, "style": style,
            "style_name": vstyles.PRESETS.get(style, {}).get("name", style or ""), "narrated": bool(cfg.get("narration")) and kind != "reel",
            "duration": round(duration(mp4), 1), "chant": rel_chants(pd).split("/")[0], "dev": first_words(sb), "video": f"/media/{rel_chants(mp4)}",
            "poster": f"/api/thumb/{film_id(mp4)}", "mtime": os.path.getmtime(mp4), "provenance": provenance(pd, cfg),
            "synced": kind != "reel", "share_url": SHARES().get(film_id(mp4)), "voice": cfg.get("recited_by") or "Recording", "deity": cfg.get("deity"), "context": context_of(pd, cfg)}


def all_films():
    out = []
    for dp, dns, fns in os.walk(CHANTS):
        dns[:] = [d for d in dns if d not in SKIP_DIRS and not d.startswith("_")]
        if "renders" not in dp.replace("\\", "/").split("/"):
            continue
        for f in fns:
            if (f.endswith(".mp4") and not f.endswith(".export.mp4")) or is_live(f):
                try:
                    out.append(film_info(os.path.join(dp, f)))
                except Exception as e:   # one broken film must not hide the library
                    print("library: skipped", f, e)
    if os.environ.get("VAK_SHOW_ALL") != "1":     # story first: community films without a narrated story stay hidden
        out = [f for f in out if f["kind"] != "studio" or f.get("narrated")]
    order = {"studio": 0, "film": 1, "reel": 2}
    return sorted(out, key=lambda x: (order[x["kind"]], -x["mtime"]))


# ------------------------------------------------------------------ jobs
JOBS, LOCK, Q = {}, threading.Lock(), queue.Queue()
STAGES = [("create:", 4, "Preparing the project"), ("recite:", 6, "Reciting the chant"), ("text:", 8, "Reading the chant"),
          ("story:", 10, "Planning scenes"), ("audio:", 13, "Aligning the recording to the words"),
          ("planner:", 15, "Writing the animation plan"), ("edit: painted card", 18, "Painting the title card"),
          ("anim:", 80, "Animation rendered"), ("caption states", 84, "Rendering word-synced captions"),
          ("scene composited", 92, "Compositing captions"), ("tanpura score", 94, "Tuning the tanpura"),
          ("film written", 98, "Mixing and exporting"), ("done in", 100, "Done")]


def save_jobs():
    with LOCK:
        jsave(JOBS_FILE, JOBS)


def update(job, **kw):
    with LOCK:
        job.update(kw, updated=time.time())
    save_jobs()
    if "status" in kw:                                   # job rows mirror to Supabase when the status changes (best effort)
        row = {k: job.get(k) for k in ("id", "title", "style", "status", "progress", "stage", "seconds")}
        if job.get("owner"):
            row["user_id"] = job["owner"]["id"]
        row.update(film_id=job.get("film"), created_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(job.get("created", time.time()))))
        cloud.background(cloud.upsert, "jobs", row)


def run_job(job):
    t0 = time.time()
    os.makedirs(job["dir"], exist_ok=True)
    log_path = os.path.join(job["dir"], "job.log")
    logf = open(log_path, "a", encoding="utf-8")

    def note(line):
        logf.write(line + "\n"); logf.flush()
        tail = (job.get("log", []) + [line])[-14:]
        prog, stage = job["progress"], job["stage"]
        for key, p, label in STAGES:
            if key in line and p >= prog:
                prog, stage = p, label
        m = re.search(r"\[anim\] frame (\d+)/(\d+)", line)
        if m and int(m.group(2)):
            i, n = int(m.group(1)), int(m.group(2))
            a = job.get("_anim") or [time.time(), n, 0, time.time()]
            a[2], a[3] = i, time.time()                   # [start, frames, last frame reported, when]: public() interpolates between reports
            job["_anim"] = a
            prog, stage = 20 + 58 * i / n, f"Animating frame {i} of {n}"
        elif job.get("_anim") and "anim:" in line:
            job["_anim"] = None
        update(job, log=tail, progress=round(prog, 1), stage=stage)

    try:
        update(job, status="running", started=time.time(), stage="Preparing the project", progress=2)
        spec = dict(job["spec"])
        proj = os.path.join(job["dir"], "project.json")
        if not os.path.exists(proj):                                         # 1. project folder (engine API)
            import contextlib, io
            if spec.pop("_interpret", False):                                # 0. an unknown chant: Claude's reading
                update(job, stage="Reading the chant with Claude", progress=3)
                try:
                    with contextlib.redirect_stdout(io.StringIO()):
                        units = create.preview(spec["chant_text"])["units"]
                    it = interpret.run(units)
                    tr, words = interpret.tables(units, it)
                    spec["translations"] = dict(tr, **(spec.get("translations") or {}))
                    spec.update(words=words, interpretation=it, deity=it["deity"])
                    if not spec.get("source"):                              # a library chant keeps its own cited source
                        spec.update(provenance=interpret.provenance(it), source=interpret.source_text(it))
                    if it["identification"]["name"] and not spec.get("card"):
                        spec["card"] = {"kicker": spec["chant_text"].split("॥")[0].split("।")[0].strip()[:40], "chapter": "",
                                        "title": spec["title"], "sub": it["identification"]["name"] + " · understand what you chant"}
                    note(f"interpret: {it['identification']['name'] or 'not identified'} · {it['genre']} · {it['deity']}")
                except Exception as e:
                    note(f"interpret: skipped ({str(e)[:200]})")
            want_story, story_style = spec.pop("_story", None), spec.pop("_story_style", "silhouette")
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                create.new_project(job["dir"], **spec)
            for line in buf.getvalue().splitlines():
                note(line)
            if want_story:                                                   # 2. Claude writes the story film
                if not spec.get("interpretation"):
                    raise RuntimeError("the chant couldn't be read, so no story can be written")
                update(job, stage="Writing the story with Claude", progress=6)
                st = storyteller.write(spec["interpretation"], prefer=want_story)
                pcfg = json.load(open(proj, encoding="utf-8"))
                cast = None
                if story_style == "silhouette" and st.get("characters"):            # characters designed for this chant
                    update(job, stage="Designing the characters with Claude", progress=8)
                    try:
                        with contextlib.redirect_stdout(buf):
                            cast = vcast.design(st)
                        note(f"cast: {', '.join(c['name'] for c in cast.values())}")
                    except Exception as e:
                        note(f"cast: skipped, using the stock figures ({str(e)[:160]})")
                storyteller.apply(proj, st, audio_duration(os.path.join(job["dir"], pcfg["audio"])), style=story_style, cast=cast)
                note(f"story: '{st['title']}' ({st['mode']}), {len(st['narration'])} narration lines, {len(st['scenes'])} scenes")
                if story_style != "silhouette":                              # 3. paint the scenes on the GPU
                    n = len(storybook.missing(job["dir"], st, story_style))
                    update(job, stage=f"Painting {n} scenes on the GPU", progress=10)
                    with contextlib.redirect_stdout(buf):
                        storybook.generate(job["dir"], st, story_style)
                    for line in buf.getvalue().splitlines()[-n:]:
                        note(line)
        cmd = [sys.executable, "-u", "-m", "vak", "run", proj, "--style", job["style"], "--cache", STUDIO_CACHE]
        note("$ python -m vak run " + rel_chants(proj) + " --style " + job["style"])
        p = subprocess.Popen(cmd, cwd=ROOT, env=ENV, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace", start_new_session=os.name != "nt")   # own process group on Linux, so cancel stops its children too
        job["_pid"] = p.pid
        for line in p.stdout:                                                # 2. engine run, progress from its log
            if line.strip():
                note(line.rstrip())
        if p.wait() != 0:
            if job.get("_cancel"):
                note("Cancelled by the user"); update(job, status="cancelled", stage="Cancelled", seconds=round(time.time() - t0)); return
            raise RuntimeError("the engine stopped with an error (see the log)")
        cfg = jload(proj)
        base, ext = os.path.splitext(os.path.join(job["dir"], cfg["out"]))
        mp4 = base + "_" + job["style"] + (LIVE_EXT if job["style"] in create.LIVE_STYLES else ext)
        update(job, status="done", progress=100, stage="Done", film=film_id(mp4), seconds=round(time.time() - t0))
    except Exception as e:
        note(f"ERROR: {e}")
        update(job, status="failed", stage=str(e)[:300], seconds=round(time.time() - t0))
    finally:
        logf.close()


def worker():
    while True:
        jid = Q.get()
        job = JOBS.get(jid)
        if job and job["status"] == "queued":
            try:
                run_job(job)
            except Exception as e:          # never let the worker thread die
                update(job, status="failed", stage=f"internal error: {e}")


def load_jobs():
    for jid, j in (jload(JOBS_FILE, {}) or {}).items():
        if j["status"] in ("queued", "running"):        # the server restarted mid-job: run it again (engine cache makes it cheap)
            j.update(status="queued", stage="Waiting (server restarted)", progress=0)
        JOBS[jid] = j
    for jid, j in sorted(JOBS.items(), key=lambda kv: kv[1]["created"]):
        if j["status"] == "queued":
            Q.put(jid)


# ------------------------------------------------------------------ API
app = FastAPI(title="Vāk")
app.include_router(auth.router)          # email + one-time code sign-in (Supabase Auth): web/auth.py


SHARES_FILE = os.path.join(DATA, "shares.json")
SHARES = lambda: jload(SHARES_FILE, {}) or {}


@app.on_event("startup")
def _start():
    load_jobs()
    threading.Thread(target=worker, daemon=True).start()
    cloud.background(sync_chants)


def sync_chants():
    cloud.upsert("chants", [{"id": c["id"], "name": c["name"], "source": c["source"], "devanagari": c["text"],
                             "translations": c.get("translations", {}), "provenance": "Identified"} for c in library()])


class SafetyIn(BaseModel):
    text: str


@app.post("/api/safety")
def api_safety(body: SafetyIn):
    """The same screen every chant passes through (used by the red-team script)."""
    return safety.check(body.text)


@app.get("/api/capabilities")
def api_capabilities():
    ok, msg = cloud.check() if cloud.enabled() else (False, "not configured")
    return {"eleven": eleven.available(), "cloud": ok, "cloud_status": msg, "interpret": interpret.available(),
            "gpu": bool(os.environ.get("VAK_COMFY_URL")), "auth": auth.enabled(), "auth_required": auth.required(), "storybook_styles": list(storybook.STYLES)}


@app.post("/api/films/{fid}/recording")
async def api_recording(fid: str, request: Request, response: Response, file: UploadFile = File(...)):
    auth.need_user(request, response)
    """A live film recorded in the player (canvas + captions + audio, WebM) → an MP4 next to it, for download and sharing."""
    p = film_path(fid)
    if not is_live(p):
        raise HTTPException(400, "only live films are recorded in the player")
    webm, mp4 = base_of(p) + ".webm", base_of(p) + ".export.mp4"
    with open(webm, "wb") as f:
        shutil.copyfileobj(file.file, f)
    r = subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", webm, "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", "-preset", "veryfast",
                        "-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-movflags", "+faststart", mp4], capture_output=True, text=True)
    if r.returncode != 0:
        raise HTTPException(500, "could not convert the recording: " + r.stderr[-300:])
    return {"export": f"/media/{rel_chants(mp4)}", "duration": round(duration(mp4), 1)}


@app.post("/api/films/{fid}/share")
def api_share(fid: str, request: Request, response: Response):
    """Publish a film: upload its MP4 (and poster) to Supabase Storage, record it in the films table, return the public link.
    Without Supabase, return the local link (works on this computer only)."""
    auth.need_user(request, response)
    p = film_path(fid)
    info = film_info(p)
    video = (base_of(p) + ".export.mp4") if is_live(p) else p
    if not os.path.exists(video):
        raise HTTPException(409, "record the live film first")
    if not cloud.enabled():
        return {"cloud": False, "url": f"/media/{rel_chants(video)}"}
    safe = re.sub(r"[^A-Za-z0-9_.-]", "_", re.sub(r"(\.live\.json|\.mp4)$", "", fid))
    url = cloud.upload(f"{safe}.mp4", video, "video/mp4")
    poster = None
    pfile = base_of(p) + ".poster.jpg" if is_live(p) else os.path.join(THUMBS, fid.replace("~", "_") + ".jpg")
    if not is_live(p) and not os.path.exists(pfile):
        api_thumb(fid)
    if os.path.exists(pfile):
        poster = cloud.upload(f"{safe}.jpg", pfile, "image/jpeg")
    cloud.upsert("films", {"id": fid, "title": info["title"], "chant": info.get("chant"), "style": info.get("style"), "live": bool(info.get("live")),
                           "duration": info.get("duration"), "provenance": info["provenance"]["level"], "voice": info.get("voice"),
                           "video_url": url, "poster_url": poster})
    sh = SHARES(); sh[fid] = url; jsave(SHARES_FILE, sh)
    return {"cloud": True, "url": url, "poster_url": poster}


@app.get("/api/films")
def api_films():
    return all_films()


@app.get("/api/films/{fid}")
def api_film(fid: str):
    mp4 = film_path(fid)
    info = film_info(mp4)
    sb = storyboard_for(mp4) or {}
    info["storyboard"] = {k: sb.get(k) for k in ("title", "units", "timeline", "narration")}
    info["storyboard"]["style"] = (sb.get("style") or {}).get("id")
    return info


class PosterIn(BaseModel):
    image: str                       # data:image/jpeg;base64,...


@app.post("/api/films/{fid}/poster")
def api_poster(fid: str, body: PosterIn):
    """A live film's poster: the player sends one frame it drew (there is no video file to take it from)."""
    import base64
    p = film_path(fid)
    if not is_live(p):
        raise HTTPException(400, "only live films take a poster from the player")
    if not body.image.startswith("data:image/jpeg;base64,") or len(body.image) > 3_000_000:
        raise HTTPException(400, "send one JPEG frame")
    out = base_of(p) + ".poster.jpg"
    open(out, "wb").write(base64.b64decode(body.image.split(",", 1)[1]))
    return {"poster": f"/media/{rel_chants(out)}"}


@app.get("/api/thumb/{fid}")
def api_thumb(fid: str):
    mp4 = film_path(fid)
    if is_live(mp4):
        poster = base_of(mp4) + ".poster.jpg"
        return FileResponse(poster if os.path.exists(poster) else os.path.join(STATIC, "proto", f"{live_info(mp4)['style']}.jpg"), media_type="image/jpeg")
    out = os.path.join(THUMBS, fid.replace("~", "_") + ".jpg")
    if not os.path.exists(out) or os.path.getmtime(out) < os.path.getmtime(mp4):
        d = duration(mp4)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{max(0.0, d * 0.62):.2f}", "-i", mp4, "-frames:v", "1",
                        "-vf", "scale=640:-2", "-q:v", "4", out], capture_output=True)
    if not os.path.exists(out):
        raise HTTPException(404)
    return FileResponse(out, media_type="image/jpeg")


@app.get("/media/{path:path}")
def media(path: str):
    p = os.path.normpath(os.path.join(CHANTS, path))
    if not p.startswith(CHANTS) or not os.path.isfile(p):
        raise HTTPException(404)
    return FileResponse(p)            # Range requests supported: the player can seek


@app.get("/api/styles")
def api_styles():
    out = [{"id": k, "name": v["name"], "tier": "free", "available": True, "story": False, "live": True,
            "eta": "ready in seconds · drawn live from the voice"} for k, v in vstyles.PRESETS.items() if v.get("kind") == "live"]
    for k, v in vstyles.PRESETS.items():
        if v.get("kind") == "live":
            continue
        if v.get("kind") == "animation":
            if k not in create.ANIM_STYLES:
                continue
            story = k in create.STORY_STYLES      # figures and scenes: only for chants with a cited story
            out.append({"id": k, "name": v["name"], "tier": "free", "available": True, "story": story,
                        "eta": "for story films" if story else "about 1–4 minutes on this laptop, no GPU"})
        else:
            out.append({"id": k, "name": v["name"], "tier": "premium", "available": False, "eta": "AI video on a rented GPU (coming soon)"})
    return out


def library():
    """Library presets (with project folders, maybe a recording) + known short chants from knowledge/chants.json."""
    out = []
    for pid, p in PRESETS.items():
        d = os.path.join(CHANTS, p["dir"])
        cfg = jload(os.path.join(d, "project.json"), {})
        out.append({"id": pid, "name": p["name"], "source": p["source"], "title": cfg.get("card", {}).get("title", p["name"]),
                    "text": open(os.path.join(d, "chant.txt"), encoding="utf-8").read().strip(),
                    "translations": jload(os.path.join(d, "translations.json"), {}),
                    "recording": p["recording"]["label"] if p["recording"] else None, "aliases": []})
    for c in romanize.known_chants():
        out.append({"id": "k:" + c["id"], "name": c["name"], "source": c["source"], "title": c.get("title", c["name"]),
                    "text": c["text"].strip(), "translations": c.get("translations", {}), "recording": None, "aliases": c.get("aliases", [])})
    return out


def library_entry(pid):
    return next((p for p in library() if p["id"] == pid), None) if pid else None


@app.get("/api/presets")
def api_presets():
    return library()


class PreviewIn(BaseModel):
    text: str
    translations: dict = {}


def to_devanagari(text):
    lib = library()
    r = romanize.to_devanagari(text, extra=lib)
    if r["method"] == "devanagari":         # typed in Devanagari: still tell the client which library chant it is
        norm = lambda t: re.sub(r"[\s।॥०-९0-9]", "", t)
        m = next((p for p in lib if norm(p["text"]) == norm(text)), None)
        if m: r["chant"] = m
    return r


@app.post("/api/preview")
def api_preview(body: PreviewIn):
    sf = safety.check(body.text)
    if sf["action"] != "allow":
        return {"safety": sf}
    conv = to_devanagari(body.text)
    c = conv.get("chant")
    tr = dict(c.get("translations", {}), **body.translations) if c else body.translations
    try:
        import contextlib, io
        with contextlib.redirect_stdout(io.StringIO()):
            pv = create.preview(conv["devanagari"], tr)
    except Exception as e:
        raise HTTPException(400, str(e))
    for u in pv["units"]:
        u.pop("label", None)
    pv["converted"] = {"devanagari": conv["devanagari"], "method": conv["method"], "note": conv["note"]}
    pv["match"] = {k: c[k] for k in ("id", "name", "source", "title", "recording") if k in c} if c and c.get("id") else None
    return pv


class InterpretIn(BaseModel):
    text: str
    force: bool = False


@app.post("/api/interpret")
def api_interpret(body: InterpretIn):
    """Claude's reading of a chant that isn't in the library: identification, translation, word meanings, story context."""
    sf = safety.check(body.text)
    if sf["action"] != "allow":
        raise HTTPException(422, {"safety": sf})
    conv = to_devanagari(body.text)
    if conv.get("chant", {}).get("id"):
        return {"known": True, "match": {k: conv["chant"][k] for k in ("id", "name", "source") if k in conv["chant"]}}
    try:
        import contextlib, io
        with contextlib.redirect_stdout(io.StringIO()):
            units = create.preview(conv["devanagari"])["units"]
    except Exception as e:
        raise HTTPException(400, str(e))
    try:
        it = interpret.run(units, force=body.force)
    except RuntimeError as e:
        raise HTTPException(503, str(e))
    except Exception as e:
        raise HTTPException(502, f"Claude couldn't read this chant: {str(e)[:300]}")
    tr, words = interpret.tables(units, it)
    return {"known": False, "interpretation": it, "translations": tr, "words": words,
            "provenance": interpret.provenance(it), "source": interpret.source_text(it)}


@app.post("/api/upload")
async def api_upload(request: Request, response: Response, file: UploadFile = File(...)):
    auth.need_user(request, response)
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in (".wav", ".mp3", ".m4a", ".aac", ".ogg", ".flac", ".webm", ".opus"):
        raise HTTPException(400, "upload an audio file (wav, mp3, m4a, ogg, flac, webm)")
    uid = uuid.uuid4().hex[:10] + ext
    with open(os.path.join(UPLOADS, uid), "wb") as f:
        shutil.copyfileobj(file.file, f)
    return {"id": uid, "name": file.filename}


class JobIn(BaseModel):
    title: str
    text: str
    translations: dict = {}
    style: str = "shadow_puppet"
    audio: dict                      # {"kind": "preset", "preset": "gayatri"} | {"kind": "upload", "id": ...} | {"kind": "recite"}
    preset: str | None = None
    narration: str = "none"          # "none" | "story" (cited story, else meaning) | "meaning"


@app.post("/api/jobs")
def api_create_job(body: JobIn, request: Request, response: Response):
    user = auth.need_user(request, response)
    story_style = body.narration in ("story", "meaning") and body.style in storybook.STYLES
    if body.style not in create.CREATE_STYLES and not story_style:
        raise HTTPException(400, "this style needs a GPU (premium, coming soon); pick a code-animation style")
    if story_style and not os.environ.get("VAK_COMFY_URL"):
        raise HTTPException(400, "Painted storybook films need the GPU: start the RunPod pod and set VAK_COMFY_URL, or pick Silhouette")
    if not body.text.strip():
        raise HTTPException(400, "paste a chant first")
    sf = safety.check(body.text + "\n" + body.title)
    if sf["action"] != "allow":
        raise HTTPException(422, {"safety": sf})
    jid = time.strftime("%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:4]
    dest = os.path.join(STUDIO, f"{create.slug(body.title)}_{jid}")
    conv = to_devanagari(body.text)                       # romanised input becomes Devanagari here too
    known = conv.get("chant") if conv.get("chant", {}).get("id") else library_entry(body.preset)
    spec = {"title": body.title.strip() or "Untitled chant", "chant_text": conv["devanagari"], "style": body.style,
            "translations": dict((known or {}).get("translations", {}), **{k: v for k, v in body.translations.items() if v})}
    preset = PRESETS.get((known or {}).get("id") or body.preset or "")
    if preset:
        pcfg = jload(os.path.join(CHANTS, preset["dir"], "project.json"), {})
        spec["source"] = preset["source"]
        spec["card"] = dict(pcfg.get("card", {}), title=spec["title"]) if pcfg.get("card") else None
    elif known:
        spec["source"] = known["source"]
        spec["card"] = {"kicker": known["text"].split("॥")[0].split("।")[0].strip()[:40], "chapter": "", "title": spec["title"],
                        "sub": known["name"] + " · understand what you chant"}
    if not known and interpret.available():               # unknown chant: Claude reads it in the background job (cached if already read)
        spec["_interpret"] = True
    if body.narration in ("story", "meaning"):             # a narrated film: Claude's reading → story → storyboard → narration
        if not interpret.available():
            raise HTTPException(400, "Narrated films need Claude: add ANTHROPIC_API_KEY to .env.local and restart the Studio")
        spec["_interpret"], spec["_story"] = True, body.narration
        if body.style not in storybook.STYLES:
            body.style = "silhouette"                      # code-drawn story renderer; painted styles use the storybook
        spec["_story_style"] = body.style
    a = body.audio or {}
    if a.get("kind") == "preset":
        p = PRESETS.get(a.get("preset", ""))
        if not p or not p["recording"]:
            raise HTTPException(400, "that preset has no recording")
        pcfg = jload(os.path.join(CHANTS, p["dir"], "project.json"), {})
        spec.update(audio=os.path.join(CHANTS, p["dir"], p["recording"]["file"]), audio_mode=pcfg.get("audio_mode", "voice"),
                    segments=pcfg.get("segments"))
    elif a.get("kind") == "upload":
        f = os.path.join(UPLOADS, os.path.basename(a.get("id", "")))
        if not os.path.exists(f):
            raise HTTPException(400, "upload not found")
        spec["audio"] = f
    elif a.get("kind") == "recite":
        spec["recite"] = True
    elif a.get("kind") == "eleven_music":
        if not eleven.available():
            raise HTTPException(400, "ElevenLabs isn't connected: set ELEVENLABS_API_KEY on this computer and restart the Studio")
        spec["recite"] = "eleven_music"
    elif a.get("kind") == "eleven":
        if not eleven.available():
            raise HTTPException(400, "ElevenLabs isn't connected: set ELEVENLABS_API_KEY on this computer and restart the Studio")
        spec["recite"] = "eleven"
    else:
        raise HTTPException(400, "choose a recording: preset, upload or neural recitation")
    return queue_job(jid, dest, spec, body.style, a.get("kind"), {"owner": user} if user else None)


def signature(spec, style):
    keep = {k: spec.get(k) for k in ("chant_text", "translations", "audio", "segments", "recite", "audio_mode", "_story", "_story_style")}
    return json.dumps([style, keep], sort_keys=True, ensure_ascii=False, default=str)


def queue_job(jid, dest, spec, style, audio_kind, extra=None):
    sig = signature(spec, style)
    with LOCK:                                            # the same film already queued or rendering: reuse that job
        dup = next((j for j in JOBS.values() if j["status"] in ("queued", "running") and j.get("sig") == sig), None)
    if dup:
        return public(dup) | {"duplicate": True}
    job = {"sig": sig,"id": jid, "title": spec["title"], "style": style, "dir": dest, "spec": spec, "status": "queued",
           "progress": 0, "stage": "Waiting in the queue", "log": [], "created": time.time(), "audio": audio_kind, **(extra or {})}
    with LOCK:
        JOBS[jid] = job
    save_jobs()
    Q.put(jid)
    return public(job)


@app.delete("/api/films/{fid}")
def api_delete_film(fid: str, request: Request):
    """Admin only (header X-Admin-Token = VAK_ADMIN_TOKEN): remove a film made in the Studio, with its project folder.
    Library films (chants/<preset>/...) can't be deleted here."""
    tok = os.environ.get("VAK_ADMIN_TOKEN", "")
    if not tok or request.headers.get("x-admin-token", "") != tok:
        raise HTTPException(403, "admin only")
    p = film_path(fid)
    rel = rel_chants(p)
    if not rel.startswith("studio/") or not os.path.exists(p):
        raise HTTPException(400, "only films made in the Studio can be deleted")
    proj = os.path.join(STUDIO, rel.split("/")[1])
    shutil.rmtree(proj, ignore_errors=True)
    return {"deleted": fid, "project": rel.split("/")[1]}


class RemixIn(BaseModel):
    style: str


@app.post("/api/films/{fid}/remix")
def api_remix(fid: str, body: RemixIn, request: Request, response: Response):
    user = auth.need_user(request, response)
    """Same chant, same recording and line timings, another code-animation style: a new studio project."""
    if body.style not in create.CREATE_STYLES:
        raise HTTPException(400, "pick a free code-animation style")
    mp4 = film_path(fid)
    pd = project_dir_of(mp4)
    cfg = jload(os.path.join(pd, "project.json"), {}) or {}
    if cfg.get("narration"):
        raise HTTPException(400, "narrated films can't be remixed yet; remix the chant-only film instead")
    if not cfg.get("chant") or not cfg.get("audio") or not os.path.exists(os.path.join(pd, cfg["audio"])):
        raise HTTPException(400, "this film has no source project with a recording to remix")
    preset = next((p for p in PRESETS.values() if rel_chants(pd).split("/")[0] == p["dir"]), None)
    title = (cfg.get("card") or {}).get("title") or cfg.get("title") or "Remix"
    spec = {"title": title, "chant_text": open(os.path.join(pd, cfg["chant"]), encoding="utf-8").read(), "style": body.style,
            "translations": jload(os.path.join(pd, cfg["translations"]), {}) if cfg.get("translations") else {},
            "audio": os.path.join(pd, cfg["audio"]), "audio_mode": cfg.get("audio_mode", "voice"), "segments": cfg.get("segments"),
            "source": cfg.get("source") or (preset["source"] if preset else None), "card": cfg.get("card")}
    jid = time.strftime("%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:4]
    return queue_job(jid, os.path.join(STUDIO, f"{create.slug(title)}_{jid}"), spec, body.style, "remix", {"remix_of": fid} | ({"owner": user} if user else {}))


def public(j):
    out = {k: v for k, v in j.items() if k not in ("spec", "sig", "owner") and not k.startswith("_")} | {"dir": rel_chants(j["dir"])}
    if j["status"] == "queued":                          # say where it is in line and what it waits for
        with LOCK:
            active = sorted((x for x in JOBS.values() if x["status"] in ("queued", "running")), key=lambda x: (x["status"] != "running", x["created"]))
        pos = next((i for i, x in enumerate(active) if x["id"] == j["id"]), 0)
        run = next((x for x in active if x["status"] == "running"), None)
        out["queue_pos"] = pos
        out["stage"] = (f"Waiting: {pos} {'film' if pos == 1 else 'films'} ahead" + (f" · now rendering {run['title']} ({run['style'].replace('_', ' ')}, {round(run['progress'])}%)" if run else "")) if pos else "Starting…"
    a = j.get("_anim")
    if j["status"] == "running" and a:                   # the renderer reports every 240 frames: interpolate in between
        t0, n, i, ti = a
        spf = (ti - t0) / i if i else 0.12
        est = min(n - 1, i + (time.time() - ti) / max(spf, 0.02))
        out["progress"] = round(20 + 58 * est / n, 1)
        left = (n - est) * max(spf, 0.02)
        out["stage"] = f"Animating frame {int(est)} of {n}" + (f" · about {int(left // 60)}:{int(left % 60):02d} left" if i else "")
    return out


@app.get("/api/jobs")
def api_jobs():
    return sorted((public(j) for j in JOBS.values()), key=lambda j: -j["created"])


@app.post("/api/jobs/{jid}/cancel")
def api_cancel(jid: str):
    job = JOBS.get(jid)
    if not job:
        raise HTTPException(404)
    if job["status"] == "queued":
        update(job, status="cancelled", stage="Cancelled")
    elif job["status"] == "running":
        job["_cancel"] = True
        if job.get("_pid"):                    # stop the engine and its renderer (node, ffmpeg) together
            if os.name == "nt":
                subprocess.run(["taskkill", "/PID", str(job["_pid"]), "/T", "/F"], capture_output=True)
            else:                              # hosted on Linux (Railway): kill the job's whole process group
                import signal
                try:
                    os.killpg(job["_pid"], signal.SIGKILL)
                except (ProcessLookupError, PermissionError):
                    pass
    return public(job)


@app.get("/api/jobs/{jid}")
def api_job(jid: str):
    if jid not in JOBS:
        raise HTTPException(404)
    return public(JOBS[jid])


@app.get("/")
def index():
    return FileResponse(os.path.join(STATIC, "studio.html"))      # Vāk Studio (design system "Utsav")


@app.get("/legacy")
def legacy():
    return FileResponse(os.path.join(STATIC, "legacy.html"))      # first v1 interface, kept for reference


app.mount("/static", StaticFiles(directory=STATIC), name="static")
app.mount("/fonts", StaticFiles(directory=os.path.join(ROOT, "vak", "assets", "node_modules", "@fontsource")), name="fonts")   # offline fonts
