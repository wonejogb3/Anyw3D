@echo off
REM ============================================================
REM  Anyw3D  ·  arranque local (backend + frontend)
REM  Verifica dependencias y levanta ambos servicios.
REM ============================================================
setlocal
cd /d "%~dp0"

echo.
echo === Anyw3D : arranque local ===
echo.

REM --- Comprobaciones basicas ---
where python >nul 2>nul || (echo [X] Python no encontrado. Instala Python 3.10-3.11. & goto :fail)
where node   >nul 2>nul || (echo [X] Node.js no encontrado. Instala Node 18+.        & goto :fail)

REM --- venv del backend ---
if not exist "backend\.venv\Scripts\python.exe" (
  echo [!] No existe el entorno. Ejecutando setup...
  powershell -ExecutionPolicy Bypass -File "scripts\setup.ps1" || goto :fail
)

REM --- deps del frontend ---
if not exist "frontend\node_modules" (
  echo [!] Instalando dependencias del frontend...
  pushd frontend & call npm install & popd
)

REM --- Deteccion de GPU (informativa) ---
where nvidia-smi >nul 2>nul && (echo [OK] GPU NVIDIA detectada ^(CUDA^).) || (echo [i] Sin GPU NVIDIA: se usara CPU.)

echo.
echo Abriendo backend (http://127.0.0.1:8000) y frontend (http://localhost:5173)...
echo Cierra las dos ventanas para detener la app.
echo.

REM --- Backend en su propia ventana ---
start "anyw3d-backend" cmd /k "cd /d "%~dp0backend" && .venv\Scripts\python.exe -m app.main"

REM --- Frontend en su propia ventana ---
start "anyw3d-frontend" cmd /k "cd /d "%~dp0frontend" && npm run dev"

REM --- Abre el navegador ---
timeout /t 4 >nul
start "" http://localhost:5173

goto :eof

:fail
echo.
echo Fallo en el arranque. Revisa los mensajes anteriores.
pause
exit /b 1
