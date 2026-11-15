# Mejora un avatar VRM con 3DVtuber y deja un VRM 1.0 listo para VTubing.
#
#   powershell -ExecutionPolicy Bypass -File scripts\mejorar_vrm.ps1 -Vrm "C:\ruta\avatar.vrm" -Nombre "Mi avatar"
#
# Pasos:
#   1. 3DVtuber importa el VRM (0.x o 1.0) en Blender 5.2.2 portable + add-on VRM 4.10.5,
#      lo convierte a VRM 1.0, lo pone en poses de prueba, lo exporta y valida el archivo.
#   2. scripts\vrm_meta.py pone el nombre y, si la licencia enlaza a VRoid Hub, traduce
#      esos terminos exactos a VRM 1.0 (3DVtuber deja siempre los mas estrictos).
# Resultado: samples\<Nombre>-vrm1.vrm (o -Salida). Todo ocurre en este PC.
param(
  [Parameter(Mandatory = $true)][string]$Vrm,
  [Parameter(Mandatory = $true)][string]$Nombre,
  [string]$Salida
)
$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
$tv = Join-Path $root "externals\3DVtuber"
$py = Join-Path $tv ".venv\Scripts\python.exe"

if (-not (Test-Path $py)) { throw "Falta 3DVtuber en $tv (ver docs\pipeline-3dvtuber.md)" }
$Vrm = (Resolve-Path $Vrm).Path
$base = ($Nombre -replace '[^A-Za-z0-9_-]', '_')
if (-not $Salida) { $Salida = Join-Path $root "samples\$base-vrm1.vrm" }
# El personaje de 3DVtuber se identifica por nombre + huella del archivo: otro archivo con el mismo
# nombre (una version nueva del avatar) crea otro personaje en vez de recompilar el anterior.
$hash = (Get-FileHash -Algorithm SHA256 $Vrm).Hash.Substring(0, 8).ToLower()
$slug = "${base}_$hash"
$manifest = Join-Path $tv "out\$slug\character.json"

function Invoke-Native([scriptblock]$cmd) {
  # PowerShell 5.1 trata el stderr de programas nativos como error; se juzga por el codigo de salida.
  $prev = $ErrorActionPreference; $ErrorActionPreference = "Continue"
  try { $out = & $cmd 2>$null } finally { $ErrorActionPreference = $prev }
  return @{ code = $LASTEXITCODE; out = ($out | Out-String) }
}

Push-Location $tv
try {
  if (-not (Test-Path $manifest)) {
    Write-Host "== 3DVtuber: creando el personaje '$slug' ==" -ForegroundColor Cyan
    $r = Invoke-Native { & $py -X utf8 -m app init $Vrm --name $slug }
    if ($r.code -ne 0) { throw "init fallo:`n$($r.out)" }
  } else {
    Write-Host "== 3DVtuber: el personaje '$slug' ya existe; se compila de nuevo ==" -ForegroundColor Cyan
  }
  Write-Host "== 3DVtuber: convirtiendo y revisando (1-2 min) ==" -ForegroundColor Cyan
  $r = Invoke-Native { & $py -X utf8 -m app run $manifest }
  $res = $r.out | ConvertFrom-Json
  if ($r.code -ne 0 -or $res.error) { throw "La compilacion fallo:`n$($res.error)" }
  $export = $res.steps | Where-Object { $_.step -eq "export" }
  if (-not $export -or -not (Test-Path $export.vrm)) { throw "3DVtuber no produjo el .vrm" }
} finally { Pop-Location }

Write-Host "== Metadatos: nombre y licencia ==" -ForegroundColor Cyan
New-Item -ItemType Directory -Force (Split-Path $Salida) | Out-Null
$meta = Join-Path $root "scripts\vrm_meta.py"
$r = Invoke-Native { & $py -X utf8 $meta $export.vrm $Salida --name $Nombre --from-vroid }
if ($r.code -ne 0) {
  # Licencia que no es de VRoid Hub: solo se pone el nombre; los terminos quedan como los dejo 3DVtuber.
  $r = Invoke-Native { & $py -X utf8 $meta $export.vrm $Salida --name $Nombre }
  if ($r.code -ne 0) { throw "vrm_meta fallo:`n$($r.out)" }
  Write-Host "  (licencia no reconocida como VRoid Hub: revisa los terminos en el VRM)" -ForegroundColor Yellow
}
Write-Host $r.out

Write-Host "== Revision de 3DVtuber ==" -ForegroundColor Cyan
foreach ($i in $res.verdict.issues) { Write-Host ("  [aviso] " + ($i -join ": ")) -ForegroundColor Yellow }
foreach ($l in $res.verdict.looks) { Write-Host ("  [mirar] " + ($l -join ": ")) -ForegroundColor Yellow }
if ($res.check_failed.Count -eq 0) { Write-Host "  Poses de prueba: sin fallos" -ForegroundColor Green }
Write-Host "`nListo: $Salida" -ForegroundColor Green
