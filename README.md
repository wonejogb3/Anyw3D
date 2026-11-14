# Anyw3D

**Workspace local para convertir imágenes 2D (PNG/JPG) en modelos 3D** (`.glb`, `.obj`, orientado a
VRM), al estilo de Meshy.ai pero **100 % en tu máquina**.

- **Frontend:** React + Vite + Tailwind + Three.js (`@react-three/fiber`). Arrastrar y soltar,
  configuración, progreso en tiempo real y visor 3D interactivo.
- **Backend:** Python + FastAPI. Quita el fondo, ejecuta el motor 3D, limpia y exporta la malla.
- **Motores modulares:** `mock` (demo sin GPU), **TripoSR** (rápido), **InstantMesh** y **TRELLIS**
  (alta fidelidad).

---

## 1. Probar ya: ejecutable portable

```
dist\Anyw3D\Anyw3D.exe
```

Doble clic: se abre una consola (el servidor) y el navegador en la app. **Cerrar la consola detiene
Anyw3D.** Los resultados se guardan en `dist\Anyw3D\storage\`.

- **Portable:** copia la carpeta `dist\Anyw3D` completa (≈260 MB) a cualquier PC con Windows 10/11
  x64; no necesita Python ni Node. El `.exe` solo funciona junto a su carpeta `_internal\`.
- **Edición "lite":** incluye el motor **Demo (silueta inflada)**, que convierte la silueta en un
  volumen con relieve y los colores de la imagen, sin IA ni GPU, y quita el fondo con OpenCV. Sirve
  para probar todo el flujo. La reconstrucción con IA (TripoSR, etc.) se usa en modo desarrollo
  (sección 3).
- Puerto 8000 por defecto (si está ocupado, usa el siguiente libre; la consola muestra la URL).
- Opciones por entorno o con un `.env` junto al `.exe`: `IMG3D_PORT`, `IMG3D_MAX_UPLOAD_MB`;
  `ANYW3D_NO_BROWSER=1` arranca sin abrir el navegador.
- La primera vez Windows SmartScreen puede avisar (ejecutable sin firmar): *Más información →
  Ejecutar de todas formas*.

### Regenerar el portable
```powershell
powershell -ExecutionPolicy Bypass -File scripts\build_portable.ps1
```
Crea `.venv-portable`, instala `backend\requirements-portable.txt`, compila la web (`vite build` →
`backend\web`) y empaqueta con PyInstaller en `dist\Anyw3D`.

---

## 2. Estructura

```
Anyw3D/
├─ run_local.bat             # modo desarrollo: backend + frontend (Vite) por separado
├─ scripts/
│  ├─ check_env.ps1          # diagnóstico (Python/Node/GPU)
│  ├─ setup.ps1              # entorno de desarrollo: venv, PyTorch (CUDA/CPU), npm install
│  └─ build_portable.ps1     # genera dist\Anyw3D\Anyw3D.exe
├─ backend/
│  ├─ launcher.py            # punto de entrada del .exe (elige puerto, abre navegador)
│  ├─ requirements.txt       # desarrollo completo (IA)
│  ├─ requirements-portable.txt  # build portable "lite"
│  └─ app/
│     ├─ main.py             # FastAPI: /api, /files y la web compilada en /
│     ├─ config.py           # configuración (IMG3D_*), rutas dev/portable
│     ├─ jobs.py             # jobs + progreso
│     ├─ api/routes.py       # REST + SSE
│     └─ pipeline/
│        ├─ preprocess.py    # rembg / OpenCV: quita fondo y centra
│        ├─ postprocess.py   # trimesh: limpia, low-poly, normaliza, exporta glb/obj
│        ├─ runner.py        # preprocess → engine → postprocess
│        └─ engines/         # mock, triposr, instantmesh, trellis
└─ frontend/src/             # App.tsx, api.ts, components/{Dropzone,ConfigPanel,ProgressBar,Viewer3D}
```

---

## 3. Modo desarrollo (con motores de IA)

### 3.1 Programas base (winget)
```powershell
winget install -e --id Python.Python.3.11
winget install -e --id OpenJS.NodeJS.LTS
winget install -e --id Git.Git
```
> Para los motores de IA usa **Python 3.10–3.11**: PyTorch, rembg y open3d no publican paquetes para
> versiones más nuevas de forma fiable. El portable "lite" sí se compila con Python recientes (3.14).

Comprueba el entorno: `powershell -ExecutionPolicy Bypass -File scripts\check_env.ps1`

### 3.2 Instalar y ejecutar
```powershell
powershell -ExecutionPolicy Bypass -File scripts\setup.ps1
```
```bat
run_local.bat
```
Backend en `http://127.0.0.1:8000` (docs en `/docs`), frontend en `http://localhost:5173`.

### 3.3 Motores de IA (clonar en `externals/`, requiere GPU NVIDIA + PyTorch CUDA)
```powershell
# TripoSR: rápido (recomendado para empezar); pesos automáticos desde HuggingFace
git clone https://github.com/VAST-AI-Research/TripoSR externals/TripoSR
backend\.venv\Scripts\pip.exe install -r externals/TripoSR/requirements.txt

# InstantMesh: alta fidelidad (multivista); seguir su README para pesos
git clone https://github.com/TencentARC/InstantMesh externals/InstantMesh

# TRELLIS: máximo detalle, mucha VRAM; seguir su README (kaolin, nvdiffrast)
git clone https://github.com/microsoft/TRELLIS externals/TRELLIS
```
Rutas personalizadas: `IMG3D_TRIPOSR_DIR`, `IMG3D_INSTANTMESH_DIR`, `IMG3D_TRELLIS_DIR`. Un motor
aparece como *no instalado* hasta que existe su carpeta; el resto sigue funcionando.

---

## 4. API

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/api/health` | estado |
| GET | `/api/engines` | motores y disponibilidad |
| POST | `/api/jobs` | crea job (multipart: `image` + `engine`, `low_poly`, `target_faces`, `texture_size`) |
| GET | `/api/jobs/{id}` | estado + progreso |
| GET | `/api/jobs/{id}/events` | progreso en vivo (SSE) |
| GET | `/files/outputs/{id}/model.glb` | resultado (`model.obj`, `input_clean.png`) |

---

## 5. Notas

- **Low-poly:** decimación a N caras (`fast-simplification`) conservando los colores por vértice.
- **VRM:** la salida es `.glb`/`.obj` normalizado (caja unitaria, centrado), base para un avatar; el
  rigging + blendshapes VRM es una fase posterior.
- **Privacidad:** el procesamiento es local; nada sale de tu equipo (los motores de IA descargan sus
  pesos la primera vez).
