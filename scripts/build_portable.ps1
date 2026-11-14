# Genera el ejecutable portable de Anyw3D:  dist\Anyw3D\Anyw3D.exe
#
#   powershell -ExecutionPolicy Bypass -File scripts\build_portable.ps1
#
# Pasos: venv de build -> dependencias lite -> compila la web (Vite) ->
#        empaqueta backend + web con PyInstaller (modo carpeta, arranque rapido).
# La carpeta dist\Anyw3D es portable: copiala a cualquier PC con Windows x64
# y ejecuta Anyw3D.exe (no requiere Python ni Node instalados).
$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent

function Invoke-Step($what, [scriptblock]$cmd) {
  Write-Host "`n=== $what ===" -ForegroundColor Cyan
  # PowerShell 5.1 convierte el stderr de programas nativos (pip, npm y
  # PyInstaller escriben su log ahi) en errores; con "Stop" abortaria aunque
  # el comando termine bien. El exito se juzga por el codigo de salida.
  $prev = $ErrorActionPreference
  $ErrorActionPreference = "Continue"
  try { & $cmd } finally { $ErrorActionPreference = $prev }
  if ($LASTEXITCODE -ne 0) { throw "Fallo en: $what (codigo $LASTEXITCODE)" }
}

# 1) Entorno de build aislado
$venv = Join-Path $root ".venv-portable"
$py   = Join-Path $venv "Scripts\python.exe"
if (-not (Test-Path $py)) {
  Invoke-Step "Creando entorno de build (.venv-portable)" { py -3 -m venv $venv }
}
Invoke-Step "Actualizando pip" { & $py -m pip install --upgrade pip --quiet }
Invoke-Step "Instalando dependencias lite" {
  & $py -m pip install -r (Join-Path $root "backend\requirements-portable.txt") --quiet
}

# 2) Interfaz web
Push-Location (Join-Path $root "frontend")
try {
  if (-not (Test-Path "node_modules")) { Invoke-Step "npm install" { npm install --no-audit --no-fund } }
  Invoke-Step "Compilando la interfaz (vite build -> backend\web)" { npm run build }
} finally { Pop-Location }

# 3) Empaquetado
$backend = Join-Path $root "backend"
$web     = Join-Path $backend "web"
Push-Location $backend
try {
  Invoke-Step "Empaquetando con PyInstaller" {
    & $py -m PyInstaller (Join-Path $backend "launcher.py") `
      --name Anyw3D --onedir --console --noconfirm --clean `
      --distpath (Join-Path $root "dist") `
      --workpath (Join-Path $root "build") `
      --specpath (Join-Path $root "build") `
      --paths $backend `
      --add-data "$web;web" `
      --hidden-import app.main `
      --collect-submodules app `
      --collect-submodules uvicorn `
      --collect-data trimesh `
      --exclude-module torch --exclude-module torchvision `
      --exclude-module rembg --exclude-module onnxruntime --exclude-module open3d `
      --exclude-module tkinter --exclude-module matplotlib
  }
} finally { Pop-Location }

$exe = Join-Path $root "dist\Anyw3D\Anyw3D.exe"
if (Test-Path $exe) {
  Write-Host "`nListo: $exe" -ForegroundColor Green
  Write-Host "Carpeta portable: $(Split-Path $exe)" -ForegroundColor Green
} else {
  throw "No se genero $exe"
}
