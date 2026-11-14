# Instalación de dependencias (una sola vez).
#   - Crea el venv del backend e instala requirements.
#   - Instala PyTorch (CUDA si hay GPU NVIDIA, CPU si no).
#   - Instala dependencias del frontend (npm install).
# Uso:  powershell -ExecutionPolicy Bypass -File scripts\setup.ps1
$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
Set-Location $root

Write-Host "=== Backend: entorno virtual de Python ===" -ForegroundColor Cyan
if (-not (Test-Path "$root\backend\.venv")) {
  python -m venv "$root\backend\.venv"
}
$py = "$root\backend\.venv\Scripts\python.exe"
& $py -m pip install --upgrade pip

# --- PyTorch: CUDA vs CPU ---
$hasGpu = (Get-Command nvidia-smi -ErrorAction SilentlyContinue) -ne $null
if ($hasGpu) {
  Write-Host "GPU NVIDIA detectada -> instalando PyTorch con CUDA 12.1" -ForegroundColor Green
  & $py -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
} else {
  Write-Host "Sin GPU -> instalando PyTorch CPU" -ForegroundColor Yellow
  & $py -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
}

Write-Host "Instalando requirements del backend…" -ForegroundColor Cyan
& $py -m pip install -r "$root\backend\requirements.txt"

Write-Host "`n=== Frontend: dependencias de Node ===" -ForegroundColor Cyan
Set-Location "$root\frontend"
npm install
Set-Location $root

Write-Host "`nSetup completo. Arranca la app con run_local.bat" -ForegroundColor Green
Write-Host "Motores de IA 3D (opcionales): ver README, sección 'Motores'." -ForegroundColor Yellow
