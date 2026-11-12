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

```bash
bash comfyui/download_models.sh ./comfyui/models     # once, ~17 GB
docker compose --profile gpu up -d --build comfyui
python3 pipeline_v2/comfy_client.py "slow dolly past a matte black supercar in a dark showroom, volumetric light" out.mp4
```

`pipeline_v2/comfy_client.py` holds the workflow graph in API form; edit the
prompt, size (`704x1280` portrait) and length (`121` frames = 5 s at 24 fps).
ComfyUI-Manager is installed for adding nodes from the UI at
http://localhost:8188 if you want to swap models (LTX-Video 2 is the faster
alternative; Wan 2.2 14B the better-looking one on a 24 GB card).
