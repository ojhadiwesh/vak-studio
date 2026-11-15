"""ComfyUI adapter: talks to a ComfyUI server (a RunPod pod, or any GPU box) over its HTTP API.

Server URL comes from --comfy or the VAK_COMFY_URL environment variable, e.g.
    https://<pod-id>-8188.proxy.runpod.net
Workflows are built here in ComfyUI's API format, so no workflow files need exporting:
    keyframe : Qwen-Image 2512 text-to-image, 1664x928 (16:9)
    keyframe with a reference : Qwen-Image-Edit 2511 — a new scene that keeps the character(s)
               from a reference image (e.g. the same sage across scenes)
    clip     : Wan 2.2 I2V 14B (high-noise + low-noise experts), 1280x720, 81 frames @ 16 fps (~5 s)
               quality "final" = 20 steps, cfg 3.5;  "draft" = lightx2v 4-step LoRAs, cfg 1 (~5x faster)"""
import json, os, time, uuid, urllib.error, urllib.parse, urllib.request
from .util import log

QWEN = {"unet": "qwen_image_2512_fp8_e4m3fn.safetensors", "clip": "qwen_2.5_vl_7b_fp8_scaled.safetensors", "vae": "qwen_image_vae.safetensors"}
QWEN_EDIT = "qwen_image_edit_2511_fp8mixed.safetensors"
WAN = {"high": "wan2.2_i2v_high_noise_14B_fp8_scaled.safetensors", "low": "wan2.2_i2v_low_noise_14B_fp8_scaled.safetensors",
       "clip": "umt5_xxl_fp8_e4m3fn_scaled.safetensors", "vae": "wan_2.1_vae.safetensors",
       "lora_high": "wan2.2_i2v_lightx2v_4steps_lora_v1_high_noise.safetensors",
       "lora_low": "wan2.2_i2v_lightx2v_4steps_lora_v1_low_noise.safetensors"}
# Wan's official default negative, minus 风格/作品/画作/画面 ("style, artwork, painting, picture"), which fight
# painted keyframes, plus our own terms. See docs/MODEL_PRACTICES.md.
VIDEO_NEGATIVE = ("色调艳丽，过曝，静态，细节模糊不清，字幕，静止，整体发灰，最差质量，低质量，JPEG压缩残留，丑陋的，残缺的，"
                  "多余的手指，画得不好的手部，画得不好的脸部，畸形的，毁容的，形态畸形的肢体，手指融合，静止不动的画面，"
                  "杂乱的背景，三条腿，背景人很多，倒着走, morphing face, changing face, flicker, jitter, camera shake, "
                  "fast motion, scene cut, text, hands entering the frame, a person entering the frame")


def keyframe_workflow(prompt, negative, seed, width=1664, height=928, steps=30, cfg=2.5, prefix="vak/key"):
    return {
        "1": {"class_type": "UNETLoader", "inputs": {"unet_name": QWEN["unet"], "weight_dtype": "default"}},
        "2": {"class_type": "CLIPLoader", "inputs": {"clip_name": QWEN["clip"], "type": "qwen_image", "device": "default"}},
        "3": {"class_type": "VAELoader", "inputs": {"vae_name": QWEN["vae"]}},
        "4": {"class_type": "ModelSamplingAuraFlow", "inputs": {"model": ["1", 0], "shift": 3.1}},
        "5": {"class_type": "CLIPTextEncode", "inputs": {"text": prompt, "clip": ["2", 0]}},
        "6": {"class_type": "CLIPTextEncode", "inputs": {"text": negative, "clip": ["2", 0]}},
        "7": {"class_type": "EmptySD3LatentImage", "inputs": {"width": width, "height": height, "batch_size": 1}},
        "8": {"class_type": "KSampler", "inputs": {"model": ["4", 0], "seed": seed, "steps": steps, "cfg": cfg, "sampler_name": "euler",
                                                   "scheduler": "simple", "positive": ["5", 0], "negative": ["6", 0], "latent_image": ["7", 0], "denoise": 1.0}},
        "9": {"class_type": "VAEDecode", "inputs": {"samples": ["8", 0], "vae": ["3", 0]}},
        "10": {"class_type": "SaveImage", "inputs": {"images": ["9", 0], "filename_prefix": prefix}},
    }


def reference_keyframe_workflow(ref_names, prompt, negative, seed, width=1664, height=928, steps=30, cfg=4.0, prefix="vak/key"):
    """Qwen-Image-Edit 2511: generate a new 16:9 scene that keeps the people in 1–3 reference images."""
    wf = {
        "1": {"class_type": "UNETLoader", "inputs": {"unet_name": QWEN_EDIT, "weight_dtype": "default"}},
        "2": {"class_type": "CLIPLoader", "inputs": {"clip_name": QWEN["clip"], "type": "qwen_image", "device": "default"}},
        "3": {"class_type": "VAELoader", "inputs": {"vae_name": QWEN["vae"]}},
        "4": {"class_type": "ModelSamplingAuraFlow", "inputs": {"model": ["1", 0], "shift": 3.1}},
        "5": {"class_type": "CFGNorm", "inputs": {"model": ["4", 0], "strength": 1.0}},
    }
    pos = {"clip": ["2", 0], "prompt": prompt, "vae": ["3", 0]}
    neg = {"clip": ["2", 0], "prompt": negative, "vae": ["3", 0]}
    for i, name in enumerate(ref_names[:3], 1):
        wf[f"2{i}"] = {"class_type": "LoadImage", "inputs": {"image": name}}
        wf[f"3{i}"] = {"class_type": "ImageScaleToTotalPixels", "inputs": {"image": [f"2{i}", 0], "upscale_method": "lanczos", "megapixels": 1.0, "resolution_steps": 1}}
        pos[f"image{i}"] = neg[f"image{i}"] = [f"3{i}", 0]
    wf["6"] = {"class_type": "TextEncodeQwenImageEditPlus", "inputs": pos}
    wf["7"] = {"class_type": "TextEncodeQwenImageEditPlus", "inputs": neg}
    wf["8"] = {"class_type": "FluxKontextMultiReferenceLatentMethod", "inputs": {"conditioning": ["6", 0], "reference_latents_method": "index_timestep_zero"}}
    wf["9"] = {"class_type": "FluxKontextMultiReferenceLatentMethod", "inputs": {"conditioning": ["7", 0], "reference_latents_method": "index_timestep_zero"}}
    wf["10"] = {"class_type": "EmptySD3LatentImage", "inputs": {"width": width, "height": height, "batch_size": 1}}
    wf["11"] = {"class_type": "KSampler", "inputs": {"model": ["5", 0], "seed": seed, "steps": steps, "cfg": cfg, "sampler_name": "euler", "scheduler": "simple",
                                                     "positive": ["8", 0], "negative": ["9", 0], "latent_image": ["10", 0], "denoise": 1.0}}
    wf["12"] = {"class_type": "VAEDecode", "inputs": {"samples": ["11", 0], "vae": ["3", 0]}}
    wf["13"] = {"class_type": "SaveImage", "inputs": {"images": ["12", 0], "filename_prefix": prefix}}
    return wf


def clip_workflow(image_name, prompt, negative, seed, quality="final", width=1280, height=720, frames=81, fps=16, prefix="vak/clip",
                  steps=None, shift=8.0):
    draft = quality == "draft"
    steps, cfg = (4, 1.0) if draft else (steps or 20, 3.5)
    wf = {
        "1": {"class_type": "UNETLoader", "inputs": {"unet_name": WAN["high"], "weight_dtype": "default"}},
        "2": {"class_type": "UNETLoader", "inputs": {"unet_name": WAN["low"], "weight_dtype": "default"}},
        "3": {"class_type": "CLIPLoader", "inputs": {"clip_name": WAN["clip"], "type": "wan", "device": "default"}},
        "4": {"class_type": "VAELoader", "inputs": {"vae_name": WAN["vae"]}},
        "5": {"class_type": "LoadImage", "inputs": {"image": image_name}},
        "6": {"class_type": "CLIPTextEncode", "inputs": {"text": prompt, "clip": ["3", 0]}},
        "7": {"class_type": "CLIPTextEncode", "inputs": {"text": negative, "clip": ["3", 0]}},
        "8": {"class_type": "WanImageToVideo", "inputs": {"positive": ["6", 0], "negative": ["7", 0], "vae": ["4", 0], "start_image": ["5", 0],
                                                          "width": width, "height": height, "length": frames, "batch_size": 1}},
    }
    hi, lo = ["1", 0], ["2", 0]
    if draft:
        wf["9"] = {"class_type": "LoraLoaderModelOnly", "inputs": {"model": hi, "lora_name": WAN["lora_high"], "strength_model": 1.0}}
        wf["10"] = {"class_type": "LoraLoaderModelOnly", "inputs": {"model": lo, "lora_name": WAN["lora_low"], "strength_model": 1.0}}
        hi, lo = ["9", 0], ["10", 0]
    wf["11"] = {"class_type": "ModelSamplingSD3", "inputs": {"model": hi, "shift": shift}}
    wf["12"] = {"class_type": "ModelSamplingSD3", "inputs": {"model": lo, "shift": shift}}
    # hand over high-noise -> low-noise expert where sigma drops below Wan's boundary 0.9 (official config)
    half = steps // 2 if draft else max(1, min(steps - 1, round((1 - 0.9 / (0.1 * shift + 0.9)) * steps)))
    wf["13"] = {"class_type": "KSamplerAdvanced", "inputs": {
        "model": ["11", 0], "add_noise": "enable", "noise_seed": seed, "steps": steps, "cfg": cfg, "sampler_name": "euler", "scheduler": "simple",
        "positive": ["8", 0], "negative": ["8", 1], "latent_image": ["8", 2], "start_at_step": 0, "end_at_step": half, "return_with_leftover_noise": "enable"}}
    wf["14"] = {"class_type": "KSamplerAdvanced", "inputs": {
        "model": ["12", 0], "add_noise": "disable", "noise_seed": seed, "steps": steps, "cfg": cfg, "sampler_name": "euler", "scheduler": "simple",
        "positive": ["8", 0], "negative": ["8", 1], "latent_image": ["13", 0], "start_at_step": half, "end_at_step": 10000, "return_with_leftover_noise": "disable"}}
    wf["15"] = {"class_type": "VAEDecode", "inputs": {"samples": ["14", 0], "vae": ["4", 0]}}
    wf["16"] = {"class_type": "CreateVideo", "inputs": {"images": ["15", 0], "fps": fps}}
    wf["17"] = {"class_type": "SaveVideo", "inputs": {"video": ["16", 0], "filename_prefix": prefix, "format": "mp4", "codec": "h264"}}
    return wf


class Comfy:
    def __init__(self, url=None):
        self.url = (url or os.environ.get("VAK_COMFY_URL", "")).rstrip("/")
        if not self.url:
            raise SystemExit("No ComfyUI server: pass --comfy https://<pod-id>-8188.proxy.runpod.net or set VAK_COMFY_URL")
        self.client = uuid.uuid4().hex

    def _req(self, path, data=None, headers=None, timeout=60):
        r = urllib.request.Request(self.url + path, data=data, headers=headers or {}, method="POST" if data is not None else "GET")
        r.add_header("User-Agent", "vak-engine")
        with urllib.request.urlopen(r, timeout=timeout) as f:
            return f.read()

    def check(self, needed=()):
        """Fail early, with a readable message, if the server is down or a model/node is missing."""
        stats = json.loads(self._req("/system_stats"))
        dev = stats.get("devices", [{}])[0]
        log(f"comfy: connected to {dev.get('name', '?')} ({dev.get('vram_total', 0) / 2**30:.0f} GB)")
        info = json.loads(self._req("/object_info", timeout=120))
        missing = [n for n in needed if n not in info]
        if missing:
            raise SystemExit(f"ComfyUI is missing nodes {missing}; update ComfyUI on the pod (rerun runpod_setup.sh)")
        have = set()
        for node, key in (("UNETLoader", "unet_name"), ("CLIPLoader", "clip_name"), ("VAELoader", "vae_name"), ("LoraLoaderModelOnly", "lora_name")):
            spec = info.get(node, {}).get("input", {}).get("required", {}).get(key)
            if spec and isinstance(spec[0], list):
                have |= set(spec[0])
        return have

    def upload(self, path):
        b = uuid.uuid4().hex
        body = (f"--{b}\r\nContent-Disposition: form-data; name=\"image\"; filename=\"{os.path.basename(path)}\"\r\n"
                f"Content-Type: application/octet-stream\r\n\r\n").encode() + open(path, "rb").read() + \
               f"\r\n--{b}\r\nContent-Disposition: form-data; name=\"overwrite\"\r\n\r\ntrue\r\n--{b}--\r\n".encode()
        return json.loads(self._req("/upload/image", body, {"Content-Type": f"multipart/form-data; boundary={b}"}, timeout=300))["name"]

    def run(self, workflow, out_path, timeout=3600):
        """Queue a workflow, wait for it, download its first output file to out_path."""
        try:
            pid = json.loads(self._req("/prompt", json.dumps({"prompt": workflow, "client_id": self.client}).encode(),
                                       {"Content-Type": "application/json"}))["prompt_id"]
        except urllib.error.HTTPError as e:      # validation errors explain which node/input is wrong
            raise RuntimeError(f"ComfyUI rejected the workflow: {e.read().decode('utf-8', 'replace')[:1500]}") from None
        t0, misses = time.time(), 0
        while True:
            time.sleep(4)
            try:
                h = json.loads(self._req(f"/history/{pid}")).get(pid)
                misses = 0
            except (urllib.error.URLError, OSError, ValueError) as e:   # proxy hiccups (502/524, timeouts) must not kill a long job
                misses += 1
                if misses > 30:
                    raise RuntimeError(f"Lost contact with ComfyUI while waiting for job {pid}: {e}") from None
                continue
            if h:
                st = h.get("status", {})
                if st.get("status_str") == "error":
                    msgs = [m for m in st.get("messages", []) if m[0] == "execution_error"]
                    raise RuntimeError(f"ComfyUI error: {json.dumps(msgs)[:1500]}")
                files = [f for o in h.get("outputs", {}).values() for v in o.values() if isinstance(v, list)
                         for f in v if isinstance(f, dict) and "filename" in f]
                if files:
                    f = files[0]
                    q = urllib.parse.urlencode({"filename": f["filename"], "subfolder": f.get("subfolder", ""), "type": f.get("type", "output")})
                    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
                    with open(out_path, "wb") as o:
                        o.write(self._req(f"/view?{q}", timeout=600))
                    return out_path, time.time() - t0
                if st.get("completed"):
                    raise RuntimeError("ComfyUI finished without an output file")
            if time.time() - t0 > timeout:
                raise TimeoutError(f"ComfyUI job {pid} took longer than {timeout}s")
