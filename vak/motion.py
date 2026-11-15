"""MOTION module: turns each scene's clip or still into moving footage of the right length,
without ping-pong loops: slow-motion playthrough, then a layered 2.5D camera move on the last frame."""
import os, subprocess, numpy as np, cv2
from PIL import Image
from .util import ffmpeg, duration, key, log

ease = lambda u: u * u * (3 - 2 * u)


def slowmo(cache, clip, factor=2):
    def make(o):
        ffmpeg("-i", clip, "-an", "-vf", f"minterpolate=fps={24 * factor}:mi_mode=mci:mc_mode=aobmc:vsbmc=1,setpts={factor}*PTS,fps=24,scale=1920:1080,format=yuv420p",
               "-c:v", "libx264", "-crf", 16, o)
    p, hit = cache.get_or_make("slowmo", key(clip, factor), ".mp4", make)
    log(f"motion: slow-motion clip {'(cached)' if hit else 'rendered'}")
    return p


def last_frame(cache, video):
    p, _ = cache.get_or_make("lastframe", key(video), ".png", lambda o: ffmpeg("-sseof", "-0.5", "-i", video, "-update", 1, o))  # keep overwriting: last decoded frame wins
    return p


def cut_layers(cache, image, box):
    """Foreground figure (RGBA) + background plate with the figure's area filled in."""
    def make(d):
        os.makedirs(d)
        from rembg import remove, new_session
        img = Image.open(image).convert("RGB"); W, H = img.size
        x0, y0, x1, y1 = box
        m = np.asarray(remove(img.crop((x0, y0, x1, y1)), session=new_session("isnet-general-use"), only_mask=True), np.float32) / 255
        n, lab, st, _ = cv2.connectedComponentsWithStats((m > 0.5).astype(np.uint8), 8)
        if n > 1: m = m * (lab == 1 + np.argmax(st[1:, cv2.CC_STAT_AREA]))
        m = cv2.GaussianBlur(m, (0, 0), 1.2)
        mask = np.zeros((H, W), np.float32); mask[y0:y1, x0:x1] = m
        rgb = np.asarray(img)
        Image.fromarray(np.dstack([rgb, (mask * 255).astype(np.uint8)]), "RGBA").save(f"{d}/fg.png")
        hole = cv2.dilate((mask > 0.15).astype(np.uint8), np.ones((31, 31), np.uint8)) * 255
        small = cv2.resize(rgb, (W // 2, H // 2)); hs = cv2.resize(hole, (W // 2, H // 2), interpolation=cv2.INTER_NEAREST)
        fill = cv2.inpaint(cv2.cvtColor(small, cv2.COLOR_RGB2BGR), hs, 25, cv2.INPAINT_TELEA)
        fill = cv2.GaussianBlur(cv2.cvtColor(cv2.resize(fill, (W, H), interpolation=cv2.INTER_CUBIC), cv2.COLOR_BGR2RGB), (0, 0), 3)
        a = cv2.GaussianBlur(hole.astype(np.float32) / 255, (0, 0), 6)[..., None]
        Image.fromarray((rgb * (1 - a) + fill * a).astype(np.uint8)).save(f"{d}/bg.png")
    d, hit = cache.get_or_make("layers", key(image, box), "", make)
    log(f"motion: figure cut-out {'(cached)' if hit else 'made'}")
    return f"{d}/bg.png", f"{d}/fg.png"


def layered_move(cache, bg, fg, seconds, z0=1.1, bg_end=(1.045, -28, -8), fg_end=(1.12, -95, 6)):
    """Two layers moving at different speeds (near layer moves and grows more). Nothing is stretched."""
    def make(o):
        b0 = cv2.cvtColor(cv2.imread(bg), cv2.COLOR_BGR2RGB).astype(np.float32)
        f0 = cv2.cvtColor(cv2.imread(fg, cv2.IMREAD_UNCHANGED), cv2.COLOR_BGRA2RGBA).astype(np.float32)
        H, W = b0.shape[:2]; cx, cy = W / 2, H / 2; n = int(round(seconds * 24))
        p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", "24", "-i", "-",
                              "-c:v", "libx264", "-crf", "16", "-pix_fmt", "yuv420p", o], stdin=subprocess.PIPE)
        def warp(L, z, dx, dy, border):
            M = np.float32([[z, 0, (1 - z) * cx + dx], [0, z, (1 - z) * cy + dy]])
            return cv2.warpAffine(L, M, (W, H), flags=cv2.INTER_CUBIC, borderMode=border)
        for f in range(n):
            u = ease(f / max(1, n - 1))
            b = warp(b0, z0 + (z0 * bg_end[0] - z0) * u, bg_end[1] * u, bg_end[2] * u, cv2.BORDER_REFLECT)
            a = warp(f0, z0 + (z0 * fg_end[0] - z0) * u, fg_end[1] * u, fg_end[2] * u, cv2.BORDER_CONSTANT)
            al = a[..., 3:4] / 255
            p.stdin.write(np.clip(b * (1 - al) + a[..., :3] * al, 0, 255).astype(np.uint8).tobytes())
        p.stdin.close(); p.wait()
    pth, hit = cache.get_or_make("layered", key(bg, fg, round(seconds, 3), z0, bg_end, fg_end), ".mp4", make)
    log(f"motion: layered camera move {'(cached)' if hit else 'rendered'} ({seconds:.1f}s)")
    return pth


def scene_footage(cache, scene, seconds):
    """Footage of exactly `seconds` for a scene: clip played once (slow-mo, easing in to 1.1x),
    then a layered move from its last frame. A still image gets the layered move only."""
    v = scene["visual"]
    if v.get("clip"):
        slow = slowmo(cache, v["clip"], v.get("slow", 2))
        L = duration(slow)
        def make(o):
            ffmpeg("-i", slow, "-vf", f"fps=24,scale=2880:1620,zoompan=z='1+0.10*on/{int(L * 24) - 1}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s=1920x1080:fps=24,format=yuv420p",
                   "-c:v", "libx264", "-crf", 16, o)
        head, _ = cache.get_or_make("easein", key(slow), ".mp4", make)
        still = last_frame(cache, v["clip"])
        rest = seconds - L
    else:
        head, still, rest = None, v["image"], seconds
    tail = None
    if rest > 0.05:
        if v.get("subject_box"):
            bg, fg = cut_layers(cache, still, v["subject_box"])
            tail = layered_move(cache, bg, fg, rest, z0=1.1 if head else 1.0)
        else:
            tail, _ = cache.get_or_make("kenburns", key(still, round(rest, 3)), ".mp4", lambda o: ffmpeg(
                "-loop", 1, "-t", rest, "-i", still, "-vf", f"scale=2880:1620,zoompan=z='1.1+0.06*on/{int(rest * 24)}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s=1920x1080:fps=24,format=yuv420p",
                "-c:v", "libx264", "-crf", 16, o))
    parts = [p for p in (head, tail) if p]
    out, _ = cache.get_or_make("scenefoot", key(parts, round(seconds, 3)), ".mp4", lambda o: ffmpeg(
        *sum([["-i", p] for p in parts], []), "-filter_complex",
        "".join(f"[{i}:v]fps=24,format=yuv420p,setsar=1[v{i}];" for i in range(len(parts))) + "".join(f"[v{i}]" for i in range(len(parts))) + f"concat=n={len(parts)}:v=1:a=0[o]",
        "-map", "[o]", "-t", seconds, "-c:v", "libx264", "-crf", 16, o))
    return out
