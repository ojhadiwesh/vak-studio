"""Seed archive: the film library and art pieces travel to a hosted Studio through Supabase Storage, because they are too
big for `railway up` (code only) and some films are over Supabase's 50 MB per-file limit.

  python -m web.seed push [--with-studio]   (this laptop) tar of chants/ (library films, projects, recordings) + art/,
                                            split into 45 MB parts, uploaded to the private bucket "seed" with a manifest
  python -m web.seed push --only DIR...     (this laptop) an EXTRA pack with just these folders (e.g. new studio films),
                                            listed in extras.json; servers that already have the base pick it up on boot
  python -m web.seed pull DEST              (the server, every boot via web/start.sh) streams the parts back, checks each
                                            part's sha256 and unpacks into DEST (the volume); packs already applied are
                                            recorded in DEST/.seeded and skipped; existing files are never overwritten

Left out: work folders (_work, master_444, .vak_cache), GPU source clips/ and images/, logs, and chants/studio unless
--with-studio. Needs SUPABASE_URL + SUPABASE_SECRET_KEY (from .env.local here, Railway variables there)."""
import hashlib, io, json, os, re, sys, tarfile, tempfile, time, urllib.request, urllib.error

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
BUCKET, PART = "seed", 45 * 1024 * 1024
SKIP_DIRS = {"_work", "master_444", ".vak_cache", "clips", "images", "__pycache__"}


def _cfg():
    from vak import envfile
    envfile.load()
    url, key = os.environ.get("SUPABASE_URL", "").rstrip("/"), os.environ.get("SUPABASE_SECRET_KEY", "")
    if not url or not key.startswith("sb_secret_"):
        raise SystemExit("seed: set SUPABASE_URL and SUPABASE_SECRET_KEY")
    return url, key


def _req(method, path, data=None, ctype=None, timeout=600, stream=False):
    url, key = _cfg()
    h = {"apikey": key}
    if ctype:
        h["content-type"] = ctype
    if method == "POST" and path.startswith("/storage/v1/object/"):
        h["x-upsert"] = "true"
    r = urllib.request.Request(url + path, data=data, method=method, headers=h)
    for attempt in range(4):
        try:
            resp = urllib.request.urlopen(r, timeout=timeout)
            return resp if stream else resp.read()
        except urllib.error.HTTPError as e:
            body = e.read()[:300].decode("utf-8", "replace")
            if e.code < 500 or attempt == 3:
                raise RuntimeError(f"{method} {path} → {e.code}: {body}")
        except OSError:
            if attempt == 3:
                raise
        time.sleep(2 + 3 * attempt)


def files(with_studio, only=None):
    out = []
    if only:                                               # just these folders (relative to vak_engine/)
        for top in only:
            base = os.path.join(ROOT, top)
            if not os.path.isdir(base):
                raise SystemExit(f"seed: no such folder {top}")
            for d, dirs, fs in os.walk(base):
                rel = os.path.relpath(d, ROOT).replace("\\", "/")
                dirs[:] = [x for x in dirs if x not in SKIP_DIRS]
                out += [f"{rel}/{f}" for f in fs if not f.endswith((".log", ".pyc"))]
        return sorted(out)
    for top in ("chants", "art"):
        base = os.path.join(ROOT, top)
        for d, dirs, fs in os.walk(base):
            rel = os.path.relpath(d, ROOT).replace("\\", "/")
            dirs[:] = [x for x in dirs if x not in SKIP_DIRS and not (rel == "chants" and x == "studio" and not with_studio)]
            out += [f"{rel}/{f}" for f in fs if not f.endswith((".log", ".pyc"))]
    return sorted(out)


class _Parts(io.RawIOBase):
    """Writes a stream into fixed-size parts, uploading each as soon as it is full."""
    def __init__(self, prefix):
        self.prefix, self.buf, self.parts = prefix, bytearray(), []

    def writable(self):
        return True

    def write(self, b):
        self.buf += b
        while len(self.buf) >= PART:
            self._flush(bytes(self.buf[:PART]))
            del self.buf[:PART]
        return len(b)

    def _flush(self, chunk):
        name = f"{self.prefix}/part-{len(self.parts):03d}"
        _req("POST", f"/storage/v1/object/{BUCKET}/{name}", chunk, "application/octet-stream")
        self.parts.append({"name": name, "size": len(chunk), "sha256": hashlib.sha256(chunk).hexdigest()})
        print(f"  uploaded {name} ({len(chunk) / 1e6:.1f} MB)", flush=True)

    def finish(self):
        if self.buf:
            self._flush(bytes(self.buf))
            self.buf = bytearray()


def push(with_studio=False, only=None):
    try:
        _req("POST", "/storage/v1/bucket", json.dumps({"id": BUCKET, "name": BUCKET, "public": False}).encode(), "application/json")
        print("seed: created private bucket 'seed'")
    except RuntimeError as e:
        if "already exists" not in str(e).lower() and "409" not in str(e):
            raise
    fl = files(with_studio, only)
    total = sum(os.path.getsize(os.path.join(ROOT, f)) for f in fl)
    version = time.strftime(("x" if only else "v") + "%Y%m%d-%H%M%S")
    print(f"seed: packing {len(fl)} files ({total / 1e6:.0f} MB) as {version}")
    sink = _Parts(version)
    with tarfile.open(fileobj=sink, mode="w|", format=tarfile.PAX_FORMAT) as tar:
        for f in fl:
            tar.add(os.path.join(ROOT, f), arcname=f, recursive=False)
    sink.finish()
    man = {"version": version, "files": len(fl), "bytes": total, "parts": sink.parts, "created": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    body = json.dumps(man, indent=1).encode()
    _req("POST", f"/storage/v1/object/{BUCKET}/{version}/manifest.json", body, "application/json")
    if only:                                               # an extra pack: added to the list, the base stays the base
        extras = _extras() + [man]
        _req("POST", f"/storage/v1/object/{BUCKET}/extras.json", json.dumps(extras, indent=1).encode(), "application/json")
        print(f"seed: done, {len(sink.parts)} parts. Servers add it on their next boot (redeploy or restart).")
        return
    _req("POST", f"/storage/v1/object/{BUCKET}/manifest.json", body, "application/json")     # "latest" pointer
    print(f"seed: done, {len(sink.parts)} parts. A new server unpacks it on first boot.")


def _extras():
    try:
        return json.loads(_req("GET", f"/storage/v1/object/{BUCKET}/extras.json"))
    except RuntimeError:
        return []


class _Reader(io.RawIOBase):
    """Reads the parts back as one stream, checking each part's sha256 as it goes."""
    def __init__(self, parts):
        self.parts, self.i, self.cur, self.h, self.n = list(parts), -1, None, None, 0

    def readable(self):
        return True

    def _next(self):
        if self.cur is not None:
            p = self.parts[self.i]
            if self.h.hexdigest() != p["sha256"] or self.n != p["size"]:
                raise RuntimeError(f"seed: {p['name']} is corrupt")
            print(f"  ok {p['name']}", flush=True)
        self.i += 1
        if self.i >= len(self.parts):
            self.cur = None
            return False
        self.cur = _req("GET", f"/storage/v1/object/{BUCKET}/{self.parts[self.i]['name']}", stream=True)
        self.h, self.n = hashlib.sha256(), 0
        return True

    def readinto(self, b):
        while True:
            if self.cur is None and not self._next():
                return 0
            data = self.cur.read(len(b))
            if data:
                self.h.update(data)
                self.n += len(data)
                b[:len(data)] = data
                return len(data)
            if not self._next():
                return 0


def pull(dest):
    """Base pack once, then every extra pack not applied yet. DEST/.seeded lists what is applied (an empty file, from
    before extras existed, means the base is in)."""
    dest = os.path.abspath(dest)
    mark = os.path.join(dest, ".seeded")
    done = set(open(mark, encoding="utf-8").read().split()) if os.path.exists(mark) else None
    todo = []
    if done is None:
        todo.append(json.loads(_req("GET", f"/storage/v1/object/{BUCKET}/manifest.json")))
        done = set()
    elif not done:
        done = {"base"}
    todo += [m for m in _extras() if m["version"] not in done]
    if not todo:
        print("seed: up to date", flush=True)
    for man in todo:
        _unpack(man, dest)
        done.add(man["version"])
        open(mark, "w", encoding="utf-8").write("\n".join(sorted(done | {"base"})) + "\n")


def _unpack(man, dest):
    print(f"seed: unpacking {man['version']} ({man['files']} files, {man['bytes'] / 1e6:.0f} MB) into {dest}", flush=True)
    raw = _Reader(man["parts"])
    with tarfile.open(fileobj=io.BufferedReader(raw, 1 << 20), mode="r|") as tar:
        for m in tar:
            target = os.path.abspath(os.path.join(dest, m.name))
            if not target.startswith(dest + os.sep) or not (m.isfile() or m.isdir()) or not re.match(r"^(chants|art)/", m.name):
                continue                                   # only plain files under chants/ and art/
            if os.path.exists(target):
                continue                                   # never overwrite what is already on the volume
            tar.extract(m, dest, filter="data")
    buf = bytearray(1 << 20)
    while raw.readinto(buf):                               # tar stops at its end marker: read the rest so the last part is checked
        pass
    print("seed: done", flush=True)


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "push":
        only = sys.argv[sys.argv.index("--only") + 1:] if "--only" in sys.argv else None
        push("--with-studio" in sys.argv, only)
    elif len(sys.argv) == 3 and sys.argv[1] == "pull":
        pull(sys.argv[2])
    else:
        raise SystemExit(__doc__)
