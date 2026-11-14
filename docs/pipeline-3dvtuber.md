# Pipeline VRM con 3DVtuber (primera versión)

Convierte un avatar **VRM 0.x o 1.0** (por ejemplo, exportado de VRoid Studio) en un **VRM 1.0**
revisado y listo para VTubing en Warudo o VNyan. Todo ocurre en este PC; no se envía nada.

## Uso

```powershell
powershell -ExecutionPolicy Bypass -File scripts\mejorar_vrm.ps1 -Vrm "C:\ruta\avatar.vrm" -Nombre "Mi avatar"
```

Resultado: `samples\<Nombre>-vrm1.vrm` (`samples\` no se sube a GitHub).

## Qué hace

1. **3DVtuber** ([HenriqueDVR/3DVtuber](https://github.com/HenriqueDVR/3DVtuber), commit `e5314c4`, MIT)
   importa el VRM en **Blender 5.2.2 portable + add-on VRM 4.10.5**, lo convierte a VRM 1.0 (esqueleto,
   expresiones, físicas, materiales MToon), lo pone en poses de prueba, lo exporta y valida el archivo.
   Con un VRM ya terminado **conserva** su pelo, físicas, formas faciales, dedos y pose de reposo.
2. **`scripts/vrm_meta.py`** pone el nombre del avatar y, si la licencia enlaza a VRoid Hub, copia
   esos términos exactos a VRM 1.0. 3DVtuber convierte una licencia "Other" en la más estricta
   (modificación prohibida, crédito obligatorio). Solo reescribe los metadatos; malla y texturas
   quedan idénticas.

## Primera versión: Rabbit sin gorra

- Entrada: `Rabbit sin gorra 01.vrm` (VRM 0.x de VRoid, 15,6 MB).
- Salida: `samples\vrm_v1\Rabbit sin gorra v1.vrm` (VRM 1.0, 13,5 MB).
- Verificado con un visor three-vrm: **54 huesos**, **18 expresiones** (las 14 originales con nombres
  VRM 1.0 + 4 de mirada), **control de mirada**, **5 articulaciones con físicas**, 14 materiales MToon y
  las 22 texturas distintas. Poses de prueba sin fallos. La expresión "happy" usa la misma forma
  facial que la "Joy" original (`Fcl_ALL_Joy`).
- Licencia: la de VRoid Hub del original (se permite modificar y redistribuir, sin crédito obligatorio,
  sin uso comercial).
- Avisos de 3DVtuber: "23 imágenes de 24" es un duplicado del original, sin pérdida real. "Se ve el
  interior de la cabeza de lado por la abertura del pelo" viene de la malla original, que no cambió.

## Segunda versión: perfect sync (52 formas ARKit)

- Salida VRM 1.0: `samples\vrm_v2\Rabbit sin gorra v2.vrm` (Warudo, VNyan).
- Salida VRM 0.x: `samples\vrm_v2\Rabbit sin gorra v2 perfect sync (VRM0).vrm`. Los clips siguen la
  convención perfect sync de VRoid (`EyeBlinkLeft`, `JawOpen`…). Debería servir en VSeeFace, pero
  no se ha probado ahí.
- Referencia visual: `samples\vrm_v2\hoja_expresiones_v2.png` (las 52 formas renderizadas).
- **Origen de las formas** ([hinzka/52blendshapes-for-VRoid-face](https://github.com/hinzka/52blendshapes-for-VRoid-face),
  uso libre, sin crédito obligatorio):
  - **Boca, mandíbula, mejillas, nariz y lengua** se transfieren de la cara base de hinzka. Las zonas de
    piel, boca y blanco del ojo comparten malla con VRoid; la correspondencia se recupera por UV y
    posición, con una escala local acotada.
  - **Ojos y cejas** se construyen con las formas `Fcl_` del propio avatar: parpadeo = `Fcl_EYE_Close_L/R`,
    entrecerrar = 50 % de `Fcl_EYE_Joy`, abrir = 50 % de `Fcl_EYE_Spread` por lado, bajar cejas =
    `Fcl_BRW_Angry` por lado, subir el interior = `Fcl_BRW_Surprised`. Subir el exterior se genera
    (7 mm hacia el extremo).
  - **`EyeLook*`**: clips vacíos. La mirada la mueven los huesos de los ojos.
- Dientes y lengua no atraviesan la piel en ninguna forma, salvo `TongueOut`.

```powershell
# 1) Añadir las 52 formas al VRM 0.x de VRoid (necesita numpy y scipy: .venv-portable)
.venv-portable\Scripts\python.exe scripts\perfect_sync.py "samples\Rabbit sin gorra 01.vrm" "samples\vrm_v2\Rabbit sin gorra v2 perfect sync (VRM0).vrm" --source externals\hinzka-52blendshapes\VRoid_V110_Female_v1.1.3.vrm --report samples\vrm_v2\informe_perfect_sync.json
# 2) Convertir a VRM 1.0 (3DVtuber + licencia)
powershell -ExecutionPolicy Bypass -File scripts\mejorar_vrm.ps1 -Vrm "samples\vrm_v2\Rabbit sin gorra v2 perfect sync (VRM0).vrm" -Nombre "Rabbit sin gorra" -Salida "samples\vrm_v2\Rabbit sin gorra v2.vrm"
# 3) Revisar: una imagen por expresión + hoja de contactos
externals\3DVtuber\tools\blender\blender-5.2.2-windows-x64\blender.exe -b --factory-startup -P externals\3DVtuber\scripts\_startup.py -P scripts\render_expresiones.py -- "samples\vrm_v2\Rabbit sin gorra v2.vrm" renders --engine eevee
.venv-portable\Scripts\python.exe scripts\hoja_contactos.py renders hoja.png --cols 9
```

Para la otra PC, además de 3DVtuber:
`git clone https://github.com/hinzka/52blendshapes-for-VRoid-face externals\hinzka-52blendshapes`.

**Lecciones de la v2:**
- **No crear formas `eyeLook*` en la malla.** Al pasar a VRM 1.0, el add-on VRM las detecta, cambia
  `lookAt` de `bone` a `expression` y, si las formas son neutras, los ojos dejan de moverse.
  3DVtuber lo avisa: "the eyes no longer follow the gaze".
- **Un mapa lineal 3×3 libre por vértice amplifica** las formas en zonas estrechas (dientes, lengua):
  con él `jawLeft` salía 4,2 veces mayor. Una escala local acotada (0,75–1,35× la global) lo resuelve.
- **El render rápido (Workbench) ignora la transparencia de MToon:** el pelo transparente sale opaco y
  tapa las cejas. Para revisar, usar `--engine eevee` o `--hide Hair`.

## Limitaciones

- **VSeeFace solo lee VRM 0.x**: para VSeeFace usa el original; el VRM 1.0 es para Warudo, VNyan y
  aplicaciones modernas.
- En modo "mejorar", 3DVtuber **no añade** las 52 formas ARKit ni colisionadores; las formas las añade
  `scripts/perfect_sync.py` (v2). El avatar sigue con **0 colisionadores**: el pelo y las orejas pueden
  atravesar el cuerpo.
- Perfect sync v2: `MouthClose` solo tiene sentido junto con `JawOpen` (así lo envían los
  rastreadores). `BrowDown` hereda un pequeño quiebro de la ceja del propio `Fcl_BRW_Angry`. No se ha
  probado aún con seguimiento en vivo (iPhone o MediaPipe) en Warudo, VNyan ni VSeeFace.
- 3DVtuber es muy nuevo (un autor, 0 estrellas). Su código se revisó: los reportes solo salen si
  pulsas "Enviar"; las actualizaciones solo con el botón Update.

## Instalar en otra PC

`externals/` no se sube a git. En la PC nueva, desde `D:\Anyw3D`:

```powershell
git clone https://github.com/HenriqueDVR/3DVtuber externals\3DVtuber
git -C externals\3DVtuber checkout e5314c4
py -3 -m venv externals\3DVtuber\.venv
externals\3DVtuber\.venv\Scripts\python.exe -m pip install pillow
cd externals\3DVtuber
.venv\Scripts\python.exe -c "from app import engine; engine.install_blender()"
```

El último comando descarga **Blender 5.2.2 portable** de blender.org (404 MB, verificado con SHA-256,
~0,9 GB en disco) dentro de `externals\3DVtuber\tools\` y le instala el add-on VRM. No toca ningún
Blender instalado.

> **Importante:** el add-on VRM debe ser **v4.5.0 o superior**. Con versiones anteriores (por ejemplo,
> 3.14.1) la conversión 0.x → 1.0 deja los huesos, las expresiones y las físicas vacíos, y la
> exportación falla con "Required VRM Human Bone … is not assigned".
