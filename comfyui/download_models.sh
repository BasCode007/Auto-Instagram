#!/usr/bin/env bash
# Downloads the Wan 2.2 TI2V-5B set (text+image to video, 720p, fits ~8 GB VRAM
# with offloading). Run once; ~17 GB. Needs curl. Usage: bash comfyui/download_models.sh ./comfyui/models
set -euo pipefail
M="${1:-./comfyui/models}"
HF="https://huggingface.co/Comfy-Org/Wan_2.2_ComfyUI_Repackaged/resolve/main/split_files"
get() { mkdir -p "$M/$1"; [ -s "$M/$1/$2" ] || curl -fL --retry 5 -o "$M/$1/$2" "$HF/$1/$2"; }
get diffusion_models wan2.2_ti2v_5B_fp16.safetensors
get vae wan2.2_vae.safetensors
get text_encoders umt5_xxl_fp8_e4m3fn_scaled.safetensors
echo "models in $M"
