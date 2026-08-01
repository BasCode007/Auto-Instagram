# n8n + the rendering toolchain the Execute Command nodes need.
# The stock n8n image is Alpine-based and ships none of ffmpeg / ImageMagick /
# fonts, so we add them here. Build via docker-compose (see docker-compose.yml).
FROM n8nio/n8n:latest
USER root
RUN apk add --no-cache \
    ffmpeg \
    imagemagick \
    ttf-dejavu \
    fontconfig \
    bash \
    curl \
    jq \
 && fc-cache -f
USER node
