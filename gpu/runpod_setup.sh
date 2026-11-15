#!/usr/bin/env bash
# Vāk GPU worker: ComfyUI + Qwen-Image (keyframes) + Wan 2.2 I2V 14B (clips), all Apache-2.0.
# Run on a RunPod pod with a network volume mounted at /workspace:
#     bash /workspace/runpod_setup.sh          # first time: installs + downloads ~68 GB (15–30 min)
#     bash /workspace/runpod_setup.sh          # later sessions: skips what exists, starts ComfyUI
# ComfyUI then listens on port 8188 (expose it as an HTTP port in the pod settings).
set -euo pipefail
W=/workspace
C=$W/ComfyUI
HF=https://huggingface.co

echo "== GPU"; nvidia-smi --query-gpu=name,memory.total --format=csv,noheader

# --- ComfyUI (kept on the volume so it survives pod restarts) ---
if [ ! -d "$C" ]; then
  git clone --depth 1 https://github.com/comfyanonymous/ComfyUI "$C"
else
  git -C "$C" pull --ff-only || echo "(could not update ComfyUI; using existing copy)"
fi
VENV=$W/venv   # on the volume, so packages survive pod restarts
if [ ! -x "$VENV/bin/python" ]; then python3 -m venv --system-site-packages "$VENV" || rm -rf "$VENV"; fi
if [ -x "$VENV/bin/python" ]; then source "$VENV/bin/activate"; else echo "(no venv support; using system python)"; fi
pip install -q --upgrade pip
# Blackwell cards (RTX PRO 6000, B200) need a CUDA 12.8+ build of torch.
python - <<'EOF' || pip install -q --upgrade torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu128
import torch, sys
ok = torch.cuda.is_available() and torch.zeros(1, device="cuda").add(1).item() == 1
print("torch", torch.__version__, "cuda ok" if ok else "cuda FAILED"); sys.exit(0 if ok else 1)
EOF
# a fresh volume once failed here: "Cannot uninstall typing-extensions ... no RECORD file" (system copy without
# pip metadata); reinstalling it over the top and retrying fixes it
pip install -q -r "$C/requirements.txt" || {
  pip install -q --ignore-installed --no-deps typing-extensions
  pip install -q -r "$C/requirements.txt"
}

# --- models (resumable downloads; skipped when already present) ---
get() {  # get <repo> <path-in-repo> <models-subdir>
  local dst="$C/models/$3/$(basename "$2")"
  mkdir -p "$(dirname "$dst")"
  if [ -s "$dst" ] && [ ! -f "$dst.part" ]; then echo "  have $(basename "$2")"; return; fi
  echo "  downloading $(basename "$2")"
  touch "$dst.part"
  wget -q --show-progress -c -O "$dst" "$HF/$1/resolve/main/$2" && rm -f "$dst.part"
}
echo "== models"
# Keyframes: Qwen-Image 2512 (fp8)
get Comfy-Org/Qwen-Image split_files/diffusion_models/qwen_image_2512_fp8_e4m3fn.safetensors diffusion_models
get Comfy-Org/Qwen-Image split_files/text_encoders/qwen_2.5_vl_7b_fp8_scaled.safetensors      text_encoders
get Comfy-Org/Qwen-Image split_files/vae/qwen_image_vae.safetensors                           vae
# Character consistency: Qwen-Image-Edit 2511 (same text encoder + VAE as Qwen-Image)
get Comfy-Org/Qwen-Image-Edit split_files/diffusion_models/qwen_image_edit_2511_fp8mixed.safetensors diffusion_models
# Clips: Wan 2.2 image-to-video 14B, high- and low-noise experts (fp8) + 4-step draft LoRAs.
# Downloaded in the background after ComfyUI starts, so keyframes can run on a fresh volume ~15 min sooner
# (ComfyUI rescans the model folders, so clips work once /workspace/wan_download.log says "done").
(
set +e
get Comfy-Org/Wan-2.2 split_files/diffusion_models/wan2.2_i2v_high_noise_14B_fp8_scaled.safetensors diffusion_models
get Comfy-Org/Wan-2.2 split_files/diffusion_models/wan2.2_i2v_low_noise_14B_fp8_scaled.safetensors  diffusion_models
get Comfy-Org/Wan-2.2 split_files/text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors             text_encoders
get Comfy-Org/Wan-2.2 split_files/vae/wan_2.1_vae.safetensors                                      vae
get Comfy-Org/Wan-2.2 split_files/loras/wan2.2_i2v_lightx2v_4steps_lora_v1_high_noise.safetensors  loras
get Comfy-Org/Wan-2.2 split_files/loras/wan2.2_i2v_lightx2v_4steps_lora_v1_low_noise.safetensors   loras
df -h "$W" | tail -1
echo "done"
) > "$W/wan_download.log" 2>&1 &

echo "== starting ComfyUI on :8188"
cd "$C"
exec python main.py --listen 0.0.0.0 --port 8188 --preview-method none
