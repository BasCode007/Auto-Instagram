#!/usr/bin/env python3
"""Generate one vertical clip with ComfyUI (Wan 2.2 TI2V-5B) over its HTTP API.

usage: comfy_client.py "prompt" out.mp4 [--seconds 5] [--url http://localhost:8188]
Env: COMFYUI_URL overrides --url.
"""
import argparse, json, os, sys, time, urllib.request, uuid

NEG = ("bright colors, overexposed, static, blurred details, subtitles, text, watermark, "
       "worst quality, low quality, jpeg artifacts, ugly, deformed, extra fingers, cartoon, "
       "painting, still image, walking backwards")

def workflow(prompt, frames, w=704, h=1280, seed=None):
    seed = seed if seed is not None else int.from_bytes(os.urandom(4), "big")
    return {
        "1": {"class_type": "UNETLoader", "inputs": {"unet_name": "wan2.2_ti2v_5B_fp16.safetensors", "weight_dtype": "default"}},
        "2": {"class_type": "CLIPLoader", "inputs": {"clip_name": "umt5_xxl_fp8_e4m3fn_scaled.safetensors", "type": "wan", "device": "default"}},
        "3": {"class_type": "VAELoader", "inputs": {"vae_name": "wan2.2_vae.safetensors"}},
        "4": {"class_type": "ModelSamplingSD3", "inputs": {"model": ["1", 0], "shift": 8.0}},
        "5": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["2", 0], "text": prompt}},
        "6": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["2", 0], "text": NEG}},
        "7": {"class_type": "Wan22ImageToVideoLatent", "inputs": {"vae": ["3", 0], "width": w, "height": h, "length": frames, "batch_size": 1}},
        "8": {"class_type": "KSampler", "inputs": {"model": ["4", 0], "positive": ["5", 0], "negative": ["6", 0], "latent_image": ["7", 0],
               "seed": seed, "steps": 20, "cfg": 5.0, "sampler_name": "uni_pc", "scheduler": "simple", "denoise": 1.0}},
        "9": {"class_type": "VAEDecode", "inputs": {"samples": ["8", 0], "vae": ["3", 0]}},
        "10": {"class_type": "CreateVideo", "inputs": {"images": ["9", 0], "fps": 24}},
        "11": {"class_type": "SaveVideo", "inputs": {"video": ["10", 0], "filename_prefix": "auto_ig/clip", "format": "mp4", "codec": "h264"}},
    }

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("prompt"); ap.add_argument("out")
    ap.add_argument("--seconds", type=float, default=5)
    ap.add_argument("--url", default=os.environ.get("COMFYUI_URL", "http://localhost:8188"))
    ap.add_argument("--timeout", type=int, default=1800)
    a = ap.parse_args()
    frames = int(round(a.seconds * 24 / 4)) * 4 + 1          # Wan wants 4n+1 frames
    body = json.dumps({"prompt": workflow(a.prompt, frames), "client_id": str(uuid.uuid4())}).encode()
    req = urllib.request.Request(a.url + "/prompt", data=body, headers={"Content-Type": "application/json"})
    pid = json.load(urllib.request.urlopen(req, timeout=60))["prompt_id"]
    t0 = time.time()
    while True:
        hist = json.load(urllib.request.urlopen(a.url + "/history/" + pid, timeout=60)).get(pid)
        if hist:
            st = hist.get("status", {})
            if st.get("status_str") == "error":
                sys.exit("ComfyUI error: " + json.dumps(st.get("messages"))[:2000])
            for node in hist.get("outputs", {}).values():
                for key in ("videos", "gifs", "images"):
                    for f in node.get(key, []):
                        q = urllib.parse.urlencode({"filename": f["filename"], "subfolder": f.get("subfolder", ""), "type": f.get("type", "output")})
                        with urllib.request.urlopen(a.url + "/view?" + q, timeout=600) as r, open(a.out, "wb") as o:
                            o.write(r.read())
                        print(json.dumps({"video": a.out, "seconds": frames / 24, "prompt_id": pid}))
                        return
        if time.time() - t0 > a.timeout:
            sys.exit("timed out waiting for ComfyUI")
        time.sleep(5)

if __name__ == "__main__":
    import urllib.parse
    main()
