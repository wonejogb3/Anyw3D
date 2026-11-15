# Diagnóstico de entorno para Anyw3D.
# Comprueba Python, Node, npm, Git y GPU NVIDIA/CUDA. No instala nada.
$ErrorActionPreference = "SilentlyContinue"

function Test-Cmd($name) {
  $c = Get-Command $name -ErrorAction SilentlyContinue
  if ($c) { return $c.Source } else { return $null }
}

Write-Host "`n=== Diagnóstico de entorno (Anyw3D) ===`n" -ForegroundColor Cyan

$py = Test-Cmd "python"
if ($py) { Write-Host ("[OK ] Python : " + (python --version 2>&1)) -ForegroundColor Green }
else     { Write-Host "[X  ] Python no encontrado. Instala Python 3.10-3.11." -ForegroundColor Red }

$node = Test-Cmd "node"
if ($node) { Write-Host ("[OK ] Node   : " + (node --version)) -ForegroundColor Green }
else       { Write-Host "[X  ] Node.js no encontrado. Instala Node 18+." -ForegroundColor Red }

$npm = Test-Cmd "npm"
if ($npm) { Write-Host ("[OK ] npm    : " + (npm --version)) -ForegroundColor Green }
else      { Write-Host "[X  ] npm no encontrado." -ForegroundColor Red }

$git = Test-Cmd "git"
if ($git) { Write-Host ("[OK ] Git    : " + (git --version)) -ForegroundColor Green }
else      { Write-Host "[!  ] Git no encontrado (necesario para clonar TripoSR/InstantMesh/TRELLIS)." -ForegroundColor Yellow }

# --- GPU ---
$smi = Test-Cmd "nvidia-smi"
if ($smi) {
  Write-Host "`n[OK ] GPU NVIDIA detectada:" -ForegroundColor Green
  nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader | ForEach-Object {
    Write-Host ("       " + $_)
  }
  Write-Host "       -> Instala PyTorch con CUDA (ver setup.ps1)." -ForegroundColor Yellow
} else {
  Write-Host "`n[!  ] Sin GPU NVIDIA: se usará CPU. Los motores de IA 3D serán lentos;" -ForegroundColor Yellow
  Write-Host "       el motor 'mock' funciona perfectamente en CPU." -ForegroundColor Yellow
}

Write-Host "`nListo. Si todo está [OK], ejecuta scripts\setup.ps1 y luego run_local.bat.`n" -ForegroundColor Cyan
