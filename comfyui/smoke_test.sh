#!/usr/bin/env bash
# Proves the GPU path end to end: container up, GPU visible, one 2-second clip rendered.
# Usage: bash comfyui/smoke_test.sh   (from the repo root, after download_models.sh)
set -euo pipefail
URL="${COMFYUI_URL:-http://localhost:8188}"
echo "1/4 GPU visible to Docker?"
docker run --rm --gpus all nvidia/cuda:12.8.0-base-ubuntu22.04 nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv
echo "2/4 starting comfyui (first build downloads ~6 GB of PyTorch)"
docker compose --profile gpu up -d --build comfyui
for i in $(seq 1 60); do curl -fsS "$URL/system_stats" >/dev/null 2>&1 && break; sleep 5; done
curl -fsS "$URL/system_stats" | python3 -c 'import json,sys; d=json.load(sys.stdin); print("   ComfyUI", d["system"]["comfyui_version"], "|", [ (g["name"], round(g["vram_total"]/2**30),"GB") for g in d["devices"]])'
echo "3/4 models present?"
curl -fsS "$URL/object_info/UNETLoader" | python3 -c 'import json,sys; print("  ", json.load(sys.stdin)["UNETLoader"]["input"]["required"]["unet_name"][0])'
echo "4/4 rendering a 2 s clip (expect 1-3 min on a 16 GB card)"
time python3 pipeline_v2/comfy_client.py "slow cinematic dolly past a matte black supercar in a dark showroom, volumetric light, film grain" comfyui/smoke.mp4 --seconds 2 --url "$URL"
ffprobe -v error -show_entries stream=width,height,r_frame_rate:format=duration -of compact comfyui/smoke.mp4
echo "OK: comfyui/smoke.mp4"
