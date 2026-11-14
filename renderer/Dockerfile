# Render worker: ffmpeg + ImageMagick + fonts + the repo's render scripts,
# behind a small HTTP API. Build context is the repository root.
FROM python:3.12-slim
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      ffmpeg imagemagick fonts-inter fonts-dejavu-core fontconfig curl jq ca-certificates \
 && rm -rf /var/lib/apt/lists/* \
 && fc-cache -f
WORKDIR /app
COPY scripts/ /app/scripts/
COPY renderer/server.py /app/renderer/server.py
COPY pipeline_v2/comfy_client.py /app/pipeline_v2/comfy_client.py
RUN chmod +x /app/scripts/*.sh /app/scripts/*.py \
 && useradd --create-home --uid 10001 render
USER render
ENV SCRIPTS_DIR=/app/scripts PORT=8080
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD curl -fsS http://127.0.0.1:8080/healthz || exit 1
CMD ["python3", "/app/renderer/server.py"]
