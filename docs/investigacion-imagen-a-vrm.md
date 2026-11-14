# Investigación: de PNG/JPG a GLB y VRM con código abierto

*Fecha: 14-nov-2026. Estrellas y fechas consultadas en GitHub ese día (`push` = último envío de código).*

## 0. Punto de partida

- El motor **Demo** de Anyw3D solo "infla" la silueta: de frente sale escalonado y de lado es un
  bulto con los colores estirados. **No sirve para avatares.** Hace falta reconstrucción 3D con IA.
- Un **VRM** no es solo una malla. Necesita esqueleto humanoide, pesos de skinning, expresiones
  (parpadeo, boca), metadatos VRM y materiales MToon. El camino tiene **3 etapas**:
  **imagen → malla 3D texturizada (GLB) → esqueleto + skinning → VRM**.
- **Hardware de esta PC:** Windows 11, **AMD Radeon RX 9060 XT 16 GB** (RDNA4, gfx1200), 32 GB de RAM.
  **No es NVIDIA**, y la mayoría de los modelos de imagen→3D compilan extensiones *solo CUDA*
  (flash-attn, nvdiffrast, spconv, CuMesh, tiny-cuda-nn). Este es el factor que más limita.
- **No existe un proyecto abierto maduro "imagen → VRM" en un solo paso.** Lo que lo hace de una vez
  es comercial (Neural4D, VTubeMe). En código abierto se encadenan piezas.

---

## 1. Etapa 1 — Imagen → malla 3D (GLB)

| Proyecto | ★ | Último push | Licencia | Requisitos | ¿AMD/Windows? | Notas |
|---|---:|---|---|---|---|---|
| [microsoft/TRELLIS.2](https://github.com/microsoft/TRELLIS.2) | 12 897 | 2026-07-10 | MIT | NVIDIA **≥24 GB**, CUDA 12.4, flash-attn, nvdiffrast, CuMesh | ❌ | Máxima fidelidad (4B). Deriva de color en ilustraciones planas. |
| [microsoft/TRELLIS](https://github.com/microsoft/TRELLIS) | 14 264 | 2026-10-27 | MIT | NVIDIA ~16 GB, spconv/kaolin | ❌ | Generación anterior. |
| [Tencent-Hunyuan/Hunyuan3D-2](https://github.com/Tencent-Hunyuan/Hunyuan3D-2) | 15 399 | 2025-10-28 | Tencent Community | 6 GB (forma) / 16 GB (forma+textura) | ⚠️ Windows sí; la textura usa rasterizador CUDA | Variantes `mini`, `mv` (multivista), `turbo`. Hay un [portable para Windows](https://github.com/YanWenKun/Hunyuan3D-2-WinPortable) (NVIDIA). |
| [Tencent-Hunyuan/Hunyuan3D-2.1](https://github.com/Tencent-Hunyuan/Hunyuan3D-2.1) | 4 430 | 2025-10-17 | Tencent Community | ~21 GB, CUDA 12 | ❌ | Texturas **PBR**. Pesos **no licenciados en UE, Reino Unido ni Corea del Sur**. |
| [VAST-AI-Research/TripoSR](https://github.com/VAST-AI-Research/TripoSR) | 7 383 | 2026-06-04 | MIT | PyTorch casi puro | ✅ probable (ROCm o CPU, lento) | Rápido pero de baja fidelidad: forma "blanda", poco útil para personajes. |
| [VAST-AI-Research/TripoSG](https://github.com/VAST-AI-Research/TripoSG) | 1 909 | 2025-04-18 | MIT | CUDA | ❌ | Solo forma (sin textura). |
| [Stability-AI/stable-fast-3d](https://github.com/Stability-AI/stable-fast-3d) | 1 934 | 2025-01-22 | Stability Community | CUDA (texture baker) | ❌ | Rápido, fidelidad menor. |
| [TencentARC/InstantMesh](https://github.com/TencentARC/InstantMesh) | 4 601 | 2025-01-03 | Apache-2.0 | CUDA, nvdiffrast | ❌ | Ya superado por los anteriores. |

### Específicos de personajes / avatares

| Proyecto | ★ | Último push | Licencia | Qué hace | ¿AMD? |
|---|---:|---|---|---|---|
| [hyz317/StdGEN](https://github.com/hyz317/StdGEN) (CVPR 2025) | 409 | 2026-04-17 | Apache-2.0 | Imagen de personaje **anime** → pose A → multivista → malla **separada en cuerpo, pelo y ropa**. **Entrenado con personajes VRoid (VRM).** | ❌ CUDA 11.8 + xformers |
| [zjp-shadow/CharacterGen](https://github.com/zjp-shadow/CharacterGen) (SIGGRAPH'24) | 850 | 2025-04-11 | Apache-2.0 | Imagen → personaje 3D en pose A canónica | ❌ CUDA |
| [aigc3d/LHM](https://github.com/aigc3d/LHM) (ICCV 2025) | 2 698 | 2026-03-17 | Apache-2.0 | Humano **realista** animable desde una foto (gaussianas) | ❌ CUDA |

### Imagen → personaje **ya con esqueleto**

| Proyecto | ★ | Último push | Licencia | Qué hace | ¿AMD? |
|---|---:|---|---|---|---|
| [VAST-AI-Research/AniGen](https://github.com/VAST-AI-Research/AniGen) (SIGGRAPH 2026) | 555 | 2026-07-15 | MIT según README (+ partes de NVIDIA con restricciones) | **Una imagen → GLB texturizado con esqueleto y pesos de skinning**, en un solo modelo | ❌ NVIDIA **≥18 GB**, CUDA (spconv, pytorch3d, nvdiffrast) |

---

## 2. Etapa 2 — Esqueleto y skinning (auto-rigging)

| Proyecto | ★ | Último push | Licencia | Notas | ¿AMD? |
|---|---:|---|---|---|---|
| [VAST-AI-Research/UniRig](https://github.com/VAST-AI-Research/UniRig) (SIGGRAPH 2025) | 2 109 | 2026-06-04 | MIT | Esqueleto + pesos para cualquier malla. Su README remite a **SkinTokens**, el sucesor (98–133 % mejor skinning). | ⚠️ |
| [VAST-AI-Research/SkinTokens](https://github.com/VAST-AI-Research/SkinTokens) | 645 | 2026-05-12 | MIT | Sucesor de UniRig. **PyTorch puro: funciona en AMD (ROCm)** según AssetFurnace. | ✅ |
| [jasongzy/Make-It-Animatable](https://github.com/jasongzy/Make-It-Animatable) (CVPR 2025) | 475 | 2026-09-08 | MIT | Rig humanoide en segundos, integración con Blender | ⚠️ sin verificar |
| [Seed3D/Puppeteer](https://github.com/Seed3D/Puppeteer) (NeurIPS 2025) | 445 | 2025-09-19 | Apache-2.0 | Rigging + animación | ⚠️ sin verificar |

---

## 3. Etapa 3 — GLB/FBX con esqueleto → **VRM**

| Proyecto | ★ | Último push | Licencia | Notas |
|---|---:|---|---|---|
| [saturday06/VRM-Addon-for-Blender](https://github.com/saturday06/VRM-Addon-for-Blender) | 1 741 | 2026-11-14 | MIT | **Estándar de facto**: importa y exporta VRM 0.x/1.0 en Blender 2.93–5.3; scriptable sin interfaz. Lo usan StdGEN y 3DVtuber. |
| [HenriqueDVR/3DVtuber](https://github.com/HenriqueDVR/3DVtuber) | 0 | 2026-11-12 | MIT | **Lo más cercano a lo que buscas:** "personaje de imagen→3D → avatar VRM 1.0 listo para streaming". Esqueleto VRM (usa el de Tripo o pone y pesa uno propio), parpadeo y formas de boca, seguimiento ocular, pelo/ropa con físicas (spring bones), MToon, pintura de textura. Usa Blender 4.2+ en segundo plano. **Probado en Windows, sin GPU (sirve con AMD).** Funciona en Warudo y VNyan; **no en VSeeFace** (exporta VRM 1.0, no 0.x). ⚠️ Muy nuevo (sept-2026), un solo autor, 0 estrellas. |
| [vrm-c/UniVRM](https://github.com/vrm-c/UniVRM) | 3 423 | 2026-10-19 | MIT | Implementación oficial para Unity. |
| [pixiv/three-vrm](https://github.com/pixiv/three-vrm) | 2 290 | 2026-10-22 | MIT | Cargar y mostrar VRM en three.js (para el visor de Anyw3D). |
| [postmelee/rigloom](https://github.com/postmelee/rigloom) | 0 | 2026-10-25 | MIT | Rigging en el navegador + GLB → VRM 1.0. **En desarrollo temprano, sin release.** |
| [shmerz/GLBtoVRM](https://github.com/shmerz/GLBtoVRM) | 1 | 2026-11-02 | GPL-3.0 | GLB ya rigeado con blendshapes → VRM. Muy nuevo. |
| [Ringo3apples/vrm-exporter](https://github.com/Ringo3apples/vrm-exporter) | 5 | 2026-10-22 | sin declarar | Exportar VRM 0.0/1.0 desde three.js + three-vrm. |

---

## 4. Pipelines completos (orquestadores)

| Proyecto | ★ | Último push | Licencia | Qué cubre | ¿Windows + AMD? |
|---|---:|---|---|---|---|
| [Bingeljell/image-to-3dlab](https://github.com/Bingeljell/image-to-3dlab) (**AssetFurnace**) | 1 185 | 2026-11-13 | Apache-2.0 | Texto o imagen → 3D → limpieza → **esqueleto (SkinTokens) + 21 animaciones** → GLB. Varios motores: Pixal3D, TRELLIS.2, Hunyuan3D, SF3D. Registra la licencia de cada asset. | ⚠️ Windows "pruebas limitadas". En **AMD solo vía Linux + ROCm**, con el motor **Pixal3D** (C++/GGML, sin extensiones CUDA). Probado en RX 7900 XTX y Ryzen AI Max+ 395, **no en RX 9060 XT**. Sus autores usan Pixal3D con 16 GB (justo). Usa Blender 4.2+ para el rig. Envía conteos de uso anónimos (desactivables). |
| [hassard0/3D-Model-Builder](https://github.com/hassard0/3D-Model-Builder) | 0 | 2026-04-25 | sin declarar | HunyuanDiT + **AniGen** (imagen → GLB rigeado) + Hunyuan3D-2 | ❌ 4× NVIDIA V100 16 GB, Ubuntu |
| [toxicoder/AvatarStream](https://github.com/toxicoder/AvatarStream) | 7 | 2026-01-13 | MIT | Avatares 3D desde una imagen + tracking por webcam | sin verificar |

---

## 5. Viabilidad en esta PC (AMD RX 9060 XT 16 GB, Windows 11)

- **PyTorch oficial de AMD para Windows** soporta la RX 9060 XT (notas de AMD de enero de 2026), pero
  **sin el stack ROCm completo**: las extensiones CUDA de TRELLIS, Hunyuan, AniGen o StdGEN no compilan.
- **WSL2 + ROCm 7.2.1 soporta oficialmente la RX 9060 XT.** Requiere el driver **Adrenalin 26.1.1 o
  posterior** y Ubuntu 22.04/24.04 en WSL2. El driver instalado ahora es `32.0.31041.1004`: hay que
  comprobar en AMD Software qué versión Adrenalin corresponde. Esto abre la vía Linux + ROCm
  (Pixal3D + SkinTokens) **dentro de Windows**.
- Lo que **sí funciona hoy sin dudas**: la etapa 3 (Blender + VRM Add-on / 3DVtuber), porque no usa GPU.

---

## 6. Rutas recomendadas

### Ruta A — 100 % local con tu AMD (la que encaja con Anyw3D)
1. **WSL2 + Ubuntu 24.04 + ROCm 7.2.1** (verificar Adrenalin ≥ 26.1.1).
2. **AssetFurnace** dentro de WSL (instalador Linux), motor **Pixal3D** (compila HIP una vez, 10–20 min;
   ~8,4 GB de pesos) → GLB texturizado.
3. **Auto-rig** de AssetFurnace (SkinTokens) → GLB con esqueleto.
4. **3DVtuber** en Windows (Blender + VRM Add-on) → **VRM 1.0** con expresiones, mirada y físicas.
- **Riesgo:** nadie lo ha probado en RDNA4 + WSL, y 16 GB va justo para Pixal3D. Puede fallar en el
  paso 2; si pasa, la ruta B sigue siendo válida.

### Ruta B — Híbrida: lo más rápido para ver un buen resultado
1. Generar el 3D en un servicio en línea. Por ejemplo **Tripo** (comercial, con créditos gratis):
   generar en **pose T**, pulsar **Rig → "VRM 1.0 humanoid"** y exportar **FBX**. Es la entrada que
   recomienda 3DVtuber (no usar el GLB rigeado de Tripo, cuyo esqueleto llega roto). Alternativa sin
   rig: demos gratuitas de Hunyuan3D-2 o TRELLIS.2 en Hugging Face; 3DVtuber pone el esqueleto.
2. **3DVtuber** local → **VRM 1.0**.
- **Contra:** la imagen sale de tu equipo en el paso 1 y depende de un tercero.

### Ruta C — Máxima calidad para anime (necesita NVIDIA: GPU alquilada u otra PC)
- **StdGEN** (entrenado con personajes VRoid, partes separadas) o **AniGen** (sale ya rigeado), o
  **Hunyuan3D-2.1 / TRELLIS.2** + **SkinTokens** → **VRM Add-on / 3DVtuber** → VRM.

---

## 7. Cómo preparar la imagen de entrada (afecta mucho al resultado)

- Personaje **de cuerpo entero, de frente**, idealmente en **pose A o T** y con **manos abiertas**,
  sin objetos tapando el cuerpo.
- **Fondo limpio** o transparente, una sola figura.
- Mejor un **render 3D suave o con iluminación difusa** que una ilustración plana: TRELLIS.2 cambia los
  colores de ilustraciones planas, y Pixal3D conserva mejor los colores saturados.

## 8. Encaje con Anyw3D

La arquitectura de motores de Anyw3D (`backend/app/pipeline/engines/`) permite añadir:
- un motor que llame a **AssetFurnace/Pixal3D** (su CLI o servidor) para la etapa 1–2;
- un paso de **exportación VRM** que ejecute **Blender sin interfaz + VRM Add-on** (o los scripts de
  3DVtuber) sobre el GLB rigeado.

Antes de integrar nada conviene **validar la ruta a mano** con tu propia imagen y ver si la calidad sirve.

## 9. Precauciones

- **Repos muy nuevos** (3DVtuber, rigloom, GLBtoVRM; 0–1 estrellas): leer el código antes de ejecutarlo.
  3DVtuber descarga Blender y el add-on (pide permiso primero).
- **AssetFurnace** se instala con `irm … | iex` (script remoto): **leer `install.ps1`/`install.sh` antes**,
  como recomiendan sus autores.
- **Licencias de pesos:** Hunyuan (Tencent Community, excluye UE, Reino Unido y Corea del Sur), SF3D
  (Stability Community) y AniGen (componentes NVIDIA con restricciones). Revisarlas antes de un uso comercial.

## Fuentes
- Repos de GitHub enlazados en las tablas (metadatos vía API de GitHub, 14-nov-2026).
- AMD — PyTorch on Windows 7.2: https://www.amd.com/en/resources/support-articles/release-notes/RN-AMDGPU-WINDOWS-PYTORCH-7-2.html
- AMD ROCm — matriz Windows: https://rocm.docs.amd.com/projects/radeon-ryzen/en/latest/docs/compatibility/compatibilityrad/windows/windows_compatibility.html
- AMD ROCm — matriz WSL: https://rocm.docs.amd.com/projects/radeon-ryzen/en/latest/docs/compatibility/compatibilityrad/wsl/wsl_compatibility.html
- AniGen (página de terceros): https://sonusahani.com/github/anigen
- Servicios comerciales de VRM: https://blog.neural4d.com/anime-art-generation/how-to-make-a-vrchat-avatar/ · https://www.producthunt.com/p/vtubeme
