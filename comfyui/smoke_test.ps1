# One-click GPU smoke test for Windows + Docker Desktop. Needs nothing else installed.
# Run RUN_ME.bat (same folder). Writes smoke_report.txt and smoke.mp4 next to it.
$ErrorActionPreference = "Continue"
Set-Location $PSScriptRoot
function Step($n, $msg) { Write-Host ""; Write-Host "== $n  $msg" -ForegroundColor Cyan }

Step 1 "Docker Desktop running?"
docker info --format '{{.ServerVersion}} {{.OSType}}'
if ($LASTEXITCODE -ne 0) { Write-Host "Docker is not running. Start Docker Desktop and run this again."; exit 1 }

Step 2 "GPU visible to containers?"
docker run --rm --gpus all nvidia/cuda:12.8.0-base-ubuntu22.04 nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv
if ($LASTEXITCODE -ne 0) { Write-Host "Docker cannot see the GPU. Update the NVIDIA driver (572+) and enable WSL 2 in Docker Desktop settings."; exit 1 }

if (!(Test-Path ".env")) { Copy-Item ".env.example" ".env" }

Step 3 "Build ComfyUI image (first time: ~6 GB of PyTorch, 5-15 min)"
docker compose --profile gpu build comfyui
if ($LASTEXITCODE -ne 0) { Write-Host "Image build failed (see above)."; exit 1 }

Step 4 "Download Wan 2.2 models (first time: ~18 GB into comfyui\models)"
New-Item -ItemType Directory -Force -Path "comfyui\models" | Out-Null
docker compose --profile gpu run --rm --no-deps --entrypoint bash comfyui /opt/kit/comfyui/download_models.sh /opt/comfyui/models
if ($LASTEXITCODE -ne 0) { Write-Host "Model download failed; run this script again to resume."; exit 1 }

Step 5 "Start ComfyUI"
docker compose --profile gpu up -d comfyui
$ok = $false
for ($i = 0; $i -lt 90; $i++) {
  try { $s = Invoke-RestMethod -Uri "http://localhost:8188/system_stats" -TimeoutSec 5; $ok = $true; break } catch { Start-Sleep -Seconds 5 }
}
if (-not $ok) { Write-Host "ComfyUI did not come up. Logs:"; docker compose --profile gpu logs --tail 60 comfyui; exit 1 }
Write-Host ("ComfyUI " + $s.system.comfyui_version + " | " + (($s.devices | ForEach-Object { $_.name + " " + [math]::Round($_.vram_total/1GB) + " GB" }) -join ", "))

Step 6 "Render a 2-second test clip (1-3 min on a 16 GB card)"
$t0 = Get-Date
docker compose --profile gpu exec -T comfyui python3 /opt/kit/pipeline_v2/comfy_client.py "slow cinematic dolly past a matte black supercar in a dark showroom, volumetric light, film grain, photoreal, 9:16" /opt/comfyui/output/smoke.mp4 --seconds 2 --url http://localhost:8188 --timeout 1500
if ($LASTEXITCODE -ne 0) { Write-Host "Generation failed. Logs:"; docker compose --profile gpu logs --tail 80 comfyui; exit 1 }
docker compose --profile gpu cp comfyui:/opt/comfyui/output/smoke.mp4 .\smoke.mp4
Write-Host ("Rendered in " + [int]((Get-Date) - $t0).TotalSeconds + " s -> " + (Resolve-Path .\smoke.mp4))
Write-Host ""
Write-Host "DONE. Drop smoke_report.txt and smoke.mp4 into the chat." -ForegroundColor Green
