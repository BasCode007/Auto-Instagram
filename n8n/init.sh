#!/bin/sh
# One-shot setup run by the n8n-init service before n8n starts: import the two
# workflows and publish (activate) them, so there is nothing to click in the UI.
# Runs once per data volume; set FORCE_REIMPORT=1 to re-import after updating
# the workflow files (this resets the "already posted" memory).
set -e
MARK=/home/node/.n8n/.auto-instagram-imported
if [ -f "$MARK" ] && [ "${FORCE_REIMPORT:-0}" != "1" ]; then
  echo "auto-instagram: workflows already imported; nothing to do"
  exit 0
fi
n8n import:workflow --input=/workflows/auto-instagram-errors.json
n8n import:workflow --input=/workflows/auto-instagram-workflow.json
n8n publish:workflow --id=AutoIgErrors0001
n8n publish:workflow --id=AutoIgMain000001
date > "$MARK"
echo "auto-instagram: workflows imported and published"
