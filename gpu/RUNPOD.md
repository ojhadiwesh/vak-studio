# Generating visuals on RunPod

One GPU pod runs ComfyUI with **Qwen-Image 2512** (keyframes) and **Wan 2.2 I2V 14B** (clips).
Both are Apache-2.0. Your laptop runs the engine and sends jobs to the pod.

## One-time setup (you, in the RunPod website)
1. Create an account at runpod.io and add credit — **$15–20** is plenty for Gāyatrī.
2. **Storage → New Network Volume**: 100 GB (models are ~68 GB). Pick a data centre that lists
   **RTX PRO 6000** (or H100) as available. Costs about $7/month while it exists; delete it after the event.
3. **Pods → Deploy**, choose that data centre and the volume, then:
   - GPU: **RTX PRO 6000** (96 GB). H100 80 GB also works.
   - Template: **RunPod PyTorch** (2.8 / CUDA 12.8 or newer).
   - Edit template → *Expose HTTP ports*: add **8188** (keep 8888 for Jupyter).
   - Container disk 30 GB is fine (models live on the volume).
4. When the pod is running, open **Connect → Jupyter Lab**, upload `gpu/runpod_setup.sh`
   into `/workspace`, open a Terminal there and run:
   ```
   nohup bash /workspace/runpod_setup.sh > /workspace/comfy.log 2>&1 &
   tail -f /workspace/comfy.log
   ```
   The first run downloads the models (about 15–30 min). It is ready when the log says
   `To see the GUI go to: http://0.0.0.0:8188`.
5. **Connect → HTTP Service 8188** opens ComfyUI. Copy that address — it looks like
   `https://<pod-id>-8188.proxy.runpod.net`.

## Every session (laptop)
```
cd vak_engine
set VAK_COMFY_URL=https://<pod-id>-8188.proxy.runpod.net        (PowerShell: $env:VAK_COMFY_URL="...")
.venv\Scripts\python -m vak generate chants\gayatri\project.json --what images --takes 3
```
Look at `chants/gayatri/images/ravi_varma/` (and `takes/`). Copy the best take over `G0x.png`, then:
```
.venv\Scripts\python -m vak generate chants\gayatri\project.json --what clips --quality draft
.venv\Scripts\python -m vak run chants\gayatri\project.json
```
When the drafts look right, make the final clips (slower, higher quality) and rebuild the film:
```
.venv\Scripts\python -m vak generate chants\gayatri\project.json --what clips --quality final --force
.venv\Scripts\python -m vak run chants\gayatri\project.json
```
Another style: add `--style pahari` (or pattachitra, tanjore, mysore, watercolour) to both commands.
A film can be built from keyframes alone (no clips) — the engine gives them a slow camera move.

## Rough timings on an RTX PRO 6000 (estimates — check the log)
- keyframe 1664×928, 30 steps: under a minute
- clip 1280×720, 81 frames (~5 s): draft (4 steps) a couple of minutes; final (20 steps) roughly 10–15 min
- Gāyatrī = 4 scenes → about 1 h of GPU for 3 takes + drafts + finals, plus the first model download.

## Cost and safety
- **Stop the pod** when you finish (Pods → Stop). A stopped pod costs nothing per hour; the
  volume keeps ComfyUI and the models, so the next start takes a few minutes.
- The 8188 address has **no password**: anyone who learns it can use your GPU while the pod runs.
  Don't share it, and stop the pod when idle.
