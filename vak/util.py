"""Shared helpers: shelling out, caching, file hashing."""
import hashlib, json, os, shutil, subprocess

ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")


def sh(cmd, **kw):
    """Run a command list; raise with stderr on failure."""
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", **kw)
    if r.returncode != 0:
        raise RuntimeError(f"command failed: {' '.join(map(str, cmd[:6]))} ...\n{r.stderr[-1500:]}")
    return r.stdout


def stream(cmd, prefix="", **kw):
    """Run a command list, echoing its stderr lines as they come (progress for long renders); raise on failure."""
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace", **kw)
    tail = []
    for line in p.stdout:
        line = line.rstrip()
        if line:
            tail = (tail + [line])[-30:]
            print(prefix + line, flush=True)
    if p.wait() != 0:
        raise RuntimeError(f"command failed: {' '.join(map(str, cmd[:6]))} ...\n" + "\n".join(tail))


def ffmpeg(*args):
    return sh(["ffmpeg", "-v", "error", "-y", *map(str, args)])


def duration(path):
    return float(sh(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)]).strip())


def file_hash(path, n=1 << 20):
    h = hashlib.sha1()
    with open(path, "rb") as f:
        h.update(f.read(n))
    h.update(str(os.path.getsize(path)).encode())
    return h.hexdigest()[:12]


def key(*parts):
    """Stable cache key from strings, numbers, dicts and file paths."""
    h = hashlib.sha1()
    for p in parts:
        if isinstance(p, str) and os.path.isfile(p):
            p = "file:" + file_hash(p)
        h.update(json.dumps(p, sort_keys=True, ensure_ascii=False, default=str).encode())
    return h.hexdigest()[:16]


class Cache:
    """Directory cache: a step's output is reused when its inputs have not changed."""

    def __init__(self, root):
        self.root = root
        os.makedirs(root, exist_ok=True)

    def path(self, step, k, ext):
        d = os.path.join(self.root, step)
        os.makedirs(d, exist_ok=True)
        return os.path.join(d, f"{k}{ext}")

    def get_or_make(self, step, k, ext, make):
        p = self.path(step, k, ext)
        if os.path.exists(p) and (os.path.isdir(p) and os.listdir(p) or os.path.isfile(p) and os.path.getsize(p) > 0):
            return p, True
        tmp = p + ".tmp" + (ext if ext and not ext.startswith("/") else "")
        if os.path.isdir(tmp): shutil.rmtree(tmp)
        make(tmp)
        os.replace(tmp, p)
        return p, False


def log(msg):
    print(f"[vak] {msg}", flush=True)
