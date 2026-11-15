"""Supabase for Vāk (optional): public share links for films (Storage) and rows for films, jobs and chants (Postgres).

Switched on by two values in vak_engine/.env.local (gitignored, loaded by vak/envfile.py):
  SUPABASE_URL          https://<project-ref>.supabase.co
  SUPABASE_SECRET_KEY   a new-style secret API key "sb_secret_..." (Project Settings -> API Keys). Server only, never sent
                        to the browser; it can be rotated or revoked on its own. The legacy service_role JWT is not used.
Without them the Studio works offline exactly as before. Schema: web/supabase/schema.sql."""
import json, mimetypes, os, threading, urllib.request, urllib.error

BUCKET = "films"


def cfg():
    url, keyv = os.environ.get("SUPABASE_URL", "").rstrip("/"), os.environ.get("SUPABASE_SECRET_KEY", "")
    return (url, keyv) if url and keyv.startswith("sb_secret_") else (None, None)


def enabled():
    return cfg()[0] is not None


def _headers(extra=None):
    _, k = cfg()
    h = {"apikey": k}                                 # new sb_secret keys go in apikey only (they are not JWTs)
    h.update(extra or {})
    return h


def _req(method, path, data=None, headers=None, timeout=120):
    url, _ = cfg()
    r = urllib.request.Request(url + path, data=data, method=method, headers=_headers(headers))
    try:
        with urllib.request.urlopen(r, timeout=timeout) as resp:
            body = resp.read()
            return json.loads(body) if body and resp.headers.get("content-type", "").startswith("application/json") else body
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"Supabase {method} {path} → {e.code}: {e.read()[:300].decode('utf-8', 'replace')}")


def upsert(table, rows):
    rows = rows if isinstance(rows, list) else [rows]
    return _req("POST", f"/rest/v1/{table}", json.dumps(rows, ensure_ascii=False, default=str).encode("utf-8"),
                {"content-type": "application/json", "Prefer": "resolution=merge-duplicates,return=minimal"})


def public_url(path):
    url, _ = cfg()
    return f"{url}/storage/v1/object/public/{BUCKET}/{path}"


def upload(path, local_file, content_type=None):
    ct = content_type or mimetypes.guess_type(local_file)[0] or "application/octet-stream"
    with open(local_file, "rb") as f:
        _req("POST", f"/storage/v1/object/{BUCKET}/{path}", f.read(), {"content-type": ct, "x-upsert": "true", "cache-control": "3600"}, timeout=600)
    return public_url(path)


def check():
    """(ok, message) for the Studio's status: can we reach the project, are the tables and the bucket there?"""
    if not enabled():
        return False, "Supabase not configured (set SUPABASE_URL and SUPABASE_SECRET_KEY=sb_secret_... in .env.local)"
    try:
        _req("GET", "/rest/v1/films?select=id&limit=1", timeout=15)
        _req("GET", f"/storage/v1/bucket/{BUCKET}", timeout=15)
        return True, "connected"
    except Exception as e:
        return False, str(e)[:240]


def background(fn, *a):
    """Fire-and-forget sync (job rows): never slows or breaks a render."""
    if enabled():
        threading.Thread(target=lambda: _quiet(fn, *a), daemon=True).start()


def _quiet(fn, *a):
    try:
        fn(*a)
    except Exception as e:
        print("cloud:", e)
