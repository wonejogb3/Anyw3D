"""Adaptador para InstantMesh (alta fidelidad vía multivista).

InstantMesh genera vistas múltiples con un difusor y reconstruye una malla
con un transformer LRM. Más lento y pesado que TripoSR, mejor geometría.

Integración:
  1. git clone https://github.com/TencentARC/InstantMesh externals/InstantMesh
  2. Crear su entorno (ver su README: torch CUDA, xformers, etc.).
  3. Descargar sus pesos (HuggingFace: TencentARC/InstantMesh).
  4. Exportar IMG3D_INSTANTMESH_DIR si usas otra ruta.

Como su ejecución oficial es por script/config, la forma más robusta de
integrarlo en local es invocar su script de inferencia como subproceso y
recoger el .obj/.glb resultante. Aquí queda el punto de integración.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from .base import Engine, EngineNotAvailable, ProgressCb

_DEFAULT_DIR = Path(__file__).resolve().parents[4] / "externals" / "InstantMesh"


def _dir() -> Path:
    return Path(os.environ.get("IMG3D_INSTANTMESH_DIR", str(_DEFAULT_DIR)))


class InstantMeshEngine(Engine):
    name = "instantmesh"
    label = "InstantMesh (alta fidelidad)"
    description = "Multivista + LRM. Mejor geometría; necesita GPU potente."
    quality = "high"
    needs_gpu = True

    def is_available(self) -> bool:
        d = _dir()
        return d.exists() and (d / "run.py").exists()

    def reconstruct(self, image_path: Path, out_dir: Path, *, device: str = "auto",
                    progress: Optional[ProgressCb] = None, **params):
        import subprocess
        import sys
        import trimesh

        d = _dir()
        if not self.is_available():
            raise EngineNotAvailable(
                f"InstantMesh no encontrado en {d}. Clónalo e instala sus pesos (ver README)."
            )
        if progress:
            progress(20, "Lanzando InstantMesh (multivista)…")

        # Ejecuta el script oficial como subproceso con su config por defecto.
        config = params.get("config", "configs/instant-mesh-large.yaml")
        cmd = [sys.executable, "run.py", config, str(image_path),
               "--output_path", str(out_dir), "--export_texmap"]
        proc = subprocess.run(cmd, cwd=str(d), capture_output=True, text=True)
        if proc.returncode != 0:
            raise RuntimeError(f"InstantMesh falló:\n{proc.stderr[-2000:]}")

        if progress:
            progress(85, "Recogiendo malla…")
        produced = sorted(out_dir.rglob("*.obj")) + sorted(out_dir.rglob("*.glb"))
        if not produced:
            raise RuntimeError("InstantMesh no produjo malla.")
        return trimesh.load(produced[0])
