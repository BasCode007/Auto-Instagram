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

Step 7 "Voice service (VoiceStudio): start, install models once (~3 GB), speak a test line"
$envText = Get-Content .env -Raw
if ($envText -match "VOICE_API_KEY=change-me") {
  $key = -join ((48..57 + 97..122) | Get-Random -Count 40 | ForEach-Object { [char]$_ })
  ($envText -replace "VOICE_API_KEY=change-me[^\r\n]*", "VOICE_API_KEY=$key") | Set-Content .env -NoNewline
}
$key = ((Get-Content .env) | Where-Object { $_ -match "^VOICE_API_KEY=" }) -replace "^VOICE_API_KEY=", ""
docker compose --profile gpu up -d voice
docker compose --profile gpu exec -T -e VOICE_BASE_URL=http://localhost:3900 voice bash /opt/kit/voice/setup_models.sh
if ($LASTEXITCODE -ne 0) { Write-Host "Voice models did not install; see above. The video part is fine."; exit 1 }
$hdr = @{ Authorization = "Bearer $key"; "Content-Type" = "application/json" }
$body = @{ model = "omnivoice"; input = "The wealthy don't save money. They buy time."; voice = "default"; response_format = "mp3";
           instruct = "Deep, calm, authoritative male narrator in his forties, neutral accent, unhurried documentary pace." } | ConvertTo-Json
$t1 = Get-Date
Invoke-WebRequest -Uri "http://localhost:3900/v1/audio/speech" -Method Post -Headers $hdr -Body $body -OutFile .\voice_test.mp3 -TimeoutSec 900
Write-Host ("Spoke the test line in " + [int]((Get-Date) - $t1).TotalSeconds + " s -> " + (Resolve-Path .\voice_test.mp3))
& curl.exe -sS -X POST "http://localhost:3900/v1/audio/transcriptions" -H "Authorization: Bearer $key" -F "file=@voice_test.mp3" -F "model=whisper-1" -F "response_format=verbose_json" -F "timestamp_granularities[]=word" -o voice_words.json
Write-Host ("Word timings: " + (Get-Content voice_words.json -Raw).Substring(0, [Math]::Min(300, (Get-Content voice_words.json -Raw).Length)))
Write-Host ""
Write-Host "DONE. Drop smoke_report.txt, smoke.mp4 and voice_test.mp3 into the chat." -ForegroundColor Green
