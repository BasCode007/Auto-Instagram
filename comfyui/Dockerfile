# ComfyUI as a headless video-generation service. Needs an NVIDIA GPU.
FROM pytorch/pytorch:2.8.0-cuda12.8-cudnn9-runtime
ARG COMFYUI_REF=v0.45.0
ARG MANAGER_REF=main
RUN apt-get update && apt-get install -y --no-install-recommends git ffmpeg libgl1 libglib2.0-0 \
 && rm -rf /var/lib/apt/lists/*
WORKDIR /opt
RUN git clone --depth 1 --branch ${COMFYUI_REF} https://github.com/comfyanonymous/ComfyUI.git comfyui \
 && git clone --depth 1 --branch ${MANAGER_REF} https://github.com/ltdrdata/ComfyUI-Manager.git comfyui/custom_nodes/ComfyUI-Manager
WORKDIR /opt/comfyui
RUN pip install --no-cache-dir -r requirements.txt \
 && pip install --no-cache-dir -r custom_nodes/ComfyUI-Manager/requirements.txt
EXPOSE 8188
VOLUME ["/opt/comfyui/models", "/opt/comfyui/output"]
CMD ["python", "main.py", "--listen", "0.0.0.0", "--port", "8188", "--disable-auto-launch"]
