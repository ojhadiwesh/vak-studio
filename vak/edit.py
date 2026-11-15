"""EDIT module: the audio timeline drives everything. Builds the painted title card, word-synced
captions, light motes and a tanpura score in the chant's key, then assembles the film."""
import json, os, shutil, subprocess, numpy as np, scipy.io.wavfile as wavfile
from scipy.signal import fftconvolve, butter, sosfilt
from .util import ASSETS, ffmpeg, duration, key, log, sh
from . import motion, anim

CARD_HOLD, XF, TAIL = 2.6, 1.2, 3.5


def node(*args):
    # shutil.which finds npm.cmd on Windows; a local playwright in assets/node_modules also works.
    env = dict(os.environ, NODE_PATH=sh([shutil.which("npm") or "npm", "root", "-g"]).strip())
    return sh(["node", os.path.join(ASSETS, "render.js"), *map(str, args)], env=env)


# ---------- title card ----------
def title_card(cache, title, seed=11):
    frames, hit = cache.get_or_make("cardframes", key("card", seed, os.path.getmtime(os.path.join(ASSETS, "card.html"))), "", lambda d: node("card", d, seed))
    log(f"edit: painted card {'(cached)' if hit else 'rendered'}")
    txt, _ = cache.get_or_make("title", key(title), ".png", lambda o: node("title", o, json.dumps(title, ensure_ascii=False)))
    n = len([f for f in os.listdir(frames) if f.endswith(".png")])
    paint = n / 8; total = round(paint + CARD_HOLD, 3)
    out, _ = cache.get_or_make("card", key(frames, txt, total), ".mp4", lambda o: ffmpeg(
        "-framerate", 8, "-i", f"{frames}/f%03d.png", "-loop", 1, "-t", total, "-i", txt, "-filter_complex",
        f"[0:v]fps=24,scale=1920:1080:flags=lanczos,tpad=stop_mode=clone:stop_duration={CARD_HOLD}[p];"
        f"[1:v]format=rgba,fade=t=in:st={max(0.5, paint - 1.6):.2f}:d=0.9:alpha=1[t];[p][t]overlay=shortest=1,format=yuv420p",
        "-t", total, "-r", 24, "-c:v", "libx264", "-crf", 18, o))
    return out, total


# ---------- captions ----------
def caption_states(units, offset):
    states = []
    for i, u in enumerate(units):
        if "start" not in u: continue
        nxt = units[i + 1]["start"] if i + 1 < len(units) and "start" in units[i + 1] else u["end"] + 2.2
        show_from, show_to = u["start"] - 0.35 + offset, min(nxt - 0.3, u["end"] + 1.6) + offset
        ws = u["words"]
        for k, w in enumerate(ws):
            a = show_from if k == 0 else w["start"] + offset
            b = ws[k + 1]["start"] + offset if k + 1 < len(ws) else w["end"] + offset
            states.append({"unit": i, "lit": k, "from": round(a, 3), "to": round(b, 3), "first": k == 0})
        states.append({"unit": i, "lit": len(ws), "from": round(ws[-1]["end"] + offset, 3), "to": round(show_to, 3), "last": True})
    return states


def captions(cache, sb, offset):
    data = {"units": sb["units"], "states": caption_states(sb["units"], offset)}
    k = key(json.dumps(data, ensure_ascii=False, sort_keys=True))
    j = cache.path("captions", k, ".json")
    json.dump(data, open(j, "w", encoding="utf-8"), ensure_ascii=False)
    d, hit = cache.get_or_make("captionpng", k, "", lambda o: node("captions", j, o))
    log(f"edit: {len(data['states'])} caption states {'(cached)' if hit else 'rendered'}")
    return d, data["states"]


# ---------- light motes ----------
def motes(cache, seconds):
    def make(o):
        W, H, N = 960, 540, 70
        rng = np.random.default_rng(3)
        x, y = rng.uniform(0, W, N), rng.uniform(0, H, N); vx, vy = rng.normal(0, 4, N), -rng.uniform(6, 18, N)
        r, ph, tw = rng.uniform(1.2, 3.6, N), rng.uniform(0, 6.28, N), rng.uniform(0.6, 1.6, N)
        yy, xx = np.mgrid[0:H, 0:W]
        p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{W}x{H}", "-r", "24", "-i", "-", "-c:v", "qtrle", o], stdin=subprocess.PIPE)
        for f in range(int(seconds * 24)):
            t = f / 24; px = (x + vx * t + 6 * np.sin(t * .5 + ph)) % W; py = (y + vy * t) % H
            a = np.zeros((H, W), np.float32); br = .55 + .45 * np.sin(t * tw + ph)
            for i in range(N):
                s = int(r[i] * 5); xa, xb = max(0, int(px[i]) - s), min(W, int(px[i]) + s + 1); ya, yb = max(0, int(py[i]) - s), min(H, int(py[i]) + s + 1)
                if xa >= xb or ya >= yb: continue
                d2 = (xx[ya:yb, xa:xb] - px[i]) ** 2 + (yy[ya:yb, xa:xb] - py[i]) ** 2
                a[ya:yb, xa:xb] += br[i] * (np.exp(-d2 / (2 * r[i] ** 2)) + .25 * np.exp(-d2 / (2 * (3 * r[i]) ** 2)))
            fr = np.empty((H, W, 4), np.uint8); fr[..., :3] = (255, 214, 140); fr[..., 3] = (np.clip(a, 0, 1) * 255).astype(np.uint8)
            p.stdin.write(fr.tobytes())
        p.stdin.close(); p.wait()
    pth, hit = cache.get_or_make("motes", key(round(seconds, 2)), ".mov", make)
    log(f"edit: light motes {'(cached)' if hit else 'rendered'}")
    return pth


# ---------- score ----------
def score(cache, total, tonic, voice_from, voice_to):
    def make(o):
        sr = 48000; n = int(sr * total); t = np.arange(n) / sr; rng = np.random.default_rng(7)
        SA = tonic; PA, LSA = SA * 0.75, SA / 2
        def pluck(f0, a, dur=5.5):
            m = int(sr * dur); tt = np.arange(m) / sr; y = np.zeros(m)
            for h in range(1, 26):
                env = np.exp(-tt * (.55 + .07 * h)) * (1 + .9 * np.sin(np.pi * np.clip(tt * (.6 + .05 * h), 0, 1)) * (h > 3))
                y += env * np.sin(2 * np.pi * f0 * h * (1 + rng.normal(0, .0007)) * tt + rng.uniform(0, 6.28)) / h ** .9
            return a * y * np.minimum(1, tt / .01)
        def bell(f0, a, dur=7):
            m = int(sr * dur); tt = np.arange(m) / sr; y = np.zeros(m)
            for rr, aa, dd in [(1, 1, .5), (2, .6, .7), (2.76, .5, 1), (4.07, .3, 1.4), (5.4, .25, 1.8), (8.9, .12, 2.6)]:
                y += aa * np.exp(-tt * dd) * np.sin(2 * np.pi * f0 * rr * tt)
            return a * y * np.minimum(1, tt / .003)
        L, R = np.zeros(n), np.zeros(n)
        def place(sig, st, pan=0):
            i = int(st * sr); j = min(n, i + len(sig))
            if i < n: L[i:j] += sig[:j - i] * (1 - pan) / 2 * 1.4; R[i:j] += sig[:j - i] * (1 + pan) / 2 * 1.4
        seq = [(PA, .8, -.3), (SA, .75, .2), (SA, .75, .35), (LSA, 1, -.1)]; tc, k = .8, 0
        while tc < total - 2:
            f, a, pan = seq[k % 4]; place(pluck(f, a * (1 + rng.normal(0, .05))), tc, pan); tc += 1.22 + rng.normal(0, .02); k += 1
        pad = sum(a * np.sin(2 * np.pi * (f + d) * t) * (1 + .25 * np.sin(2 * np.pi * .11 * t + f)) for f, a in [(LSA, .5), (SA, .35), (PA * 2, .2), (SA * 2, .12)] for d in (-.15, .15))
        pad = sosfilt(butter(2, 1200, "low", fs=sr, output="sos"), pad); L += .18 * pad; R += .18 * pad
        for st, a in [(.3, .9), (voice_from - 1.4, .55), (total - 4.1, .7)]:
            place(bell(SA * 4, a), st)
        m = int(sr * 3.2); tt = np.arange(m) / sr
        L = .7 * L + .3 * fftconvolve(L, rng.normal(0, 1, m) * np.exp(-tt * 2.2))[:n] / 40
        R = .7 * R + .3 * fftconvolve(R, rng.normal(0, 1, m) * np.exp(-tt * 2.2))[:n] / 40
        env = np.clip(t / 3, 0, 1) * (1 - .35 * np.clip((t - voice_from + .5) / 1.5, 0, 1) * np.clip((voice_to + .5 - t) / 1.5, 0, 1)) * np.clip((total - t) / 3.5, 0, 1)
        st = np.stack([L * env, R * env], 1); st = st / np.abs(st).max() * .5
        wavfile.write(o, sr, (st * 32767).astype(np.int16))
    pth, hit = cache.get_or_make("score", key(round(total, 2), round(tonic, 2), round(voice_from, 2), round(voice_to, 2)), ".wav", make)
    log(f"edit: tanpura score in {tonic:.1f} Hz {'(cached)' if hit else 'synthesized'}")
    return pth


# ---------- assembly ----------
def run(cache, sb, title, out_path, anim_plan=None):
    card, C = title_card(cache, title)
    T0 = round(C - XF, 3)
    voice_dur = sb["audio"]["duration"]
    track = sb["audio"].get("mode") == "track"      # finished mix: plays from frame 0 under the title card
    V = 0.0 if track else T0                        # film time at which the recording starts
    total = round(voice_dur + 0.2, 3) if track else round(T0 + voice_dur + TAIL, 3)
    scene_len = round(total - T0, 3)
    sb["timeline"] = {"card": C, "scene_start": T0, "voice_offset": V, "total": total}

    if anim_plan:                                   # code-drawn animation: one continuous background, no clips
        bg = anim.render(cache, sb, anim_plan, sb["style"]["id"], T0 - V, scene_len)
    else:
        bg = scene_clips(cache, sb, T0, V, scene_len)
    return compose(cache, sb, card, bg, T0, V, total, scene_len, voice_dur, track, out_path, motes_on=not anim_plan)


def scene_clips(cache, sb, T0, V, scene_len):
    # scenes back to back (one crossfade between neighbours)
    scenes, units = sb["scenes"], {u["id"]: u for u in sb["units"]}
    cuts = [0.0]
    for a, b in zip(scenes, scenes[1:]):            # recording time -> scene timeline (which starts at T0)
        t = b["start"] if b.get("start") is not None else (units[a["units"][-1]]["end"] + units[b["units"][0]]["start"]) / 2
        cuts.append(round(t + V - T0, 3))
    cuts.append(scene_len)
    clips = [motion.scene_footage(cache, s, round(cuts[i + 1] - cuts[i] + (0.8 if i < len(scenes) - 1 else 0), 3)) for i, s in enumerate(scenes)]
    bg = clips[0]
    for i, c in enumerate(clips[1:], 1):
        bg, _ = cache.get_or_make("scenejoin", key(bg, c, cuts[i]), ".mp4", lambda o, bg=bg, c=c, off=cuts[i]: ffmpeg(
            "-i", bg, "-i", c, "-filter_complex", f"[0:v][1:v]xfade=transition=fade:duration=0.8:offset={off:.3f},format=yuv420p", "-c:v", "libx264", "-crf", 16, o))
    return bg


def compose(cache, sb, card, bg, T0, V, total, scene_len, voice_dur, track, out_path, motes_on=True):
    capdir, states = captions(cache, sb, V)
    if motes_on:
        mot = motes(cache, scene_len)
        inputs = ["-i", bg, "-i", mot]
        fc = ["[0:v]eq=brightness='0.018*sin(t*1.1)':eval=frame[b0]", "[1:v]scale=1920:1080,format=rgba,fade=t=in:st=6:d=3:alpha=1[m]", "[b0][m]overlay=0:0[v0]"]
    else:                                           # the animation has its own light; a null input keeps input numbering
        mot = "none"
        inputs = ["-i", bg, "-f", "lavfi", "-i", "color=c=black@0.0:s=16x16:d=1"]
        fc = ["[0:v]null[v0]"]
    last = "v0"
    for i, st in enumerate(states):
        a, b = st["from"] - T0, st["to"] - T0
        inputs += ["-loop", 1, "-t", scene_len, "-i", f"{capdir}/st{i:03d}.png"]
        ch = f"[{i + 2}:v]format=rgba" + (f",fade=t=in:st={a:.3f}:d=0.4:alpha=1" if st.get("first") else "") + (f",fade=t=out:st={b - .4:.3f}:d=0.4:alpha=1" if st.get("last") else "")
        y = f"640+if(lt(t\\,{a + .45:.3f})\\,28*(1-(t-{a:.3f})/0.45)\\,0)" if st.get("first") else "640"
        fc += [ch + f"[c{i}]", f"[{last}][c{i}]overlay=x=0:y='{y}':enable='between(t,{a:.3f},{b:.3f})'[w{i}]"]
        last = f"w{i}"
    fc.append(f"[{last}]format=yuv420p[v]")
    scene, hit = cache.get_or_make("scene", key(bg, mot, capdir, json.dumps(states)), ".mp4", lambda o: ffmpeg(
        *inputs, "-filter_complex", ";".join(fc), "-map", "[v]", "-t", scene_len, "-c:v", "libx264", "-crf", 17, o))
    log(f"edit: scene composited with motes and captions {'(cached)' if hit else ''}")

    if track:
        ffmpeg("-i", card, "-i", scene, "-i", sb["audio"]["path"], "-filter_complex",
               f"[0:v]settb=AVTB,fps=24,format=yuv420p[a];[1:v]settb=AVTB,fps=24,format=yuv420p[b];[a][b]xfade=transition=fade:duration={XF}:offset={T0}[v];"
               f"[2:a]aresample=48000,afade=t=out:st={total - 2.5:.2f}:d=2.5,apad,atrim=0:{total},loudnorm=I=-16:TP=-1.5:LRA=11[au]",
               "-map", "[v]", "-map", "[au]", "-t", total, "-c:v", "libx264", "-profile:v", "high", "-pix_fmt", "yuv420p", "-crf", 18, "-c:a", "aac", "-b:a", "192k", "-ar", 48000, "-movflags", "+faststart", out_path)   # 4:2:0 + 48 kHz: plays everywhere
        sb["renders"]["film"] = out_path
        log(f"edit: film written ({total:.1f}s, track mix) -> {out_path}")
        return out_path
    sc = score(cache, total, sb["audio"]["tonic_hz"], T0, T0 + voice_dur)
    ms = int(T0 * 1000)
    ffmpeg("-i", card, "-i", scene, "-i", sb["audio"]["voice"], "-i", sc, "-filter_complex",
           f"[0:v]settb=AVTB,fps=24,format=yuv420p[a];[1:v]settb=AVTB,fps=24,format=yuv420p[b];[a][b]xfade=transition=fade:duration={XF}:offset={T0}[v];"
           f"[2:a]aresample=48000,acompressor=threshold=-28dB:ratio=3:attack=10:release=200,volume=10dB,aecho=0.85:0.6:70|140:0.16|0.08,adelay={ms}|{ms},apad[vo];"
           f"[3:a]volume=0.3[s];[vo][s]amix=inputs=2:normalize=0:duration=longest,atrim=0:{total},loudnorm=I=-16:TP=-1.5:LRA=11[au]",
           "-map", "[v]", "-map", "[au]", "-t", total, "-c:v", "libx264", "-profile:v", "high", "-pix_fmt", "yuv420p", "-crf", 18, "-c:a", "aac", "-b:a", "192k", "-ar", 48000, "-movflags", "+faststart", out_path)   # 4:2:0 + 48 kHz: plays everywhere
    sb["renders"]["film"] = out_path
    log(f"edit: film written ({total:.1f}s) -> {out_path}")
    return out_path
