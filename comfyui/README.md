# ComfyUI as the video generator

Replaces Higgsfield for AI footage. ComfyUI runs as a container next to n8n
and the renderer; the pipeline talks to it over HTTP (`POST /prompt`,
`GET /history/{id}`, `GET /view`). Model: **Wan 2.2 TI2V-5B** (text or image to
5 s 720p clips), chosen because it is the smallest current model that looks
cinematic and runs on an 8–12 GB consumer GPU.

**Hardware is the constraint.** This needs an NVIDIA GPU on the machine that
runs Docker (RTX 3060 12 GB or better; a 5 s 704×1280 clip takes roughly 2–6
minutes). The cloud session this was built in has no GPU, so the container
and workflow are written from the ComfyUI source and docs but were not
executed here. Without a GPU the options are a rented one (RunPod/Vast,
roughly USD 0.30–0.60 per hour while generating) or staying on stock footage.

## On the RTX 5080 machine (Windows)

The 5080 is a Blackwell card: it needs an NVIDIA driver of 572 or newer and
CUDA 12.8 builds, which is what the Dockerfile pins. 16 GB of VRAM fits the
Wan 2.2 5B model at fp16 with room to spare; the 14B model would need the fp8
files and offloading, so start with 5B.

1. Install Docker Desktop with the WSL 2 backend and the current NVIDIA driver.
   Check the GPU is visible to containers:
   `docker run --rm --gpus all nvidia/cuda:12.8.0-base-ubuntu22.04 nvidia-smi`
2. Clone this repo, then `bash comfyui/smoke_test.sh` (Git Bash or WSL). It
   downloads the models once (~18 GB), builds the container, confirms ComfyUI
   sees the card and renders a 2 s test clip to `comfyui/smoke.mp4`.
3. If the Claude desktop app is on that machine, share the repo folder under
   Settings, Claude Code, Remote Control, and the cloud session can run these
   steps and the first real generations itself.

```bash
bash comfyui/download_models.sh ./comfyui/models     # once, ~18 GB
docker compose --profile gpu up -d --build comfyui
python3 pipeline_v2/comfy_client.py "slow dolly past a matte black supercar in a dark showroom, volumetric light" out.mp4
```

`pipeline_v2/comfy_client.py` holds the workflow graph in API form; edit the
prompt, size (`704x1280` portrait) and length (`121` frames = 5 s at 24 fps).
ComfyUI-Manager is installed for adding nodes from the UI at
http://localhost:8188 if you want to swap models (LTX-Video 2 is the faster
alternative; Wan 2.2 14B the better-looking one on a 24 GB card).
