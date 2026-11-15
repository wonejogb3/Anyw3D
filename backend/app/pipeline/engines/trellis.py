"""Adaptador para Microsoft TRELLIS (alta fidelidad, representación latente).

TRELLIS produce 3D de alta calidad (malla + gaussianas/radiance) desde imagen.
Pesado en VRAM; excelente detalle.

Integración:
  1. git clone https://github.com/microsoft/TRELLIS externals/TRELLIS
  2. Seguir su instalación (torch CUDA, kaolin, nvdiffrast, etc.).
  3. Pesos: microsoft/TRELLIS-image-large (HuggingFace).
  4. Exportar IMG3D_TRELLIS_DIR si usas otra ruta.

TRELLIS expone un pipeline Python (`TrellisImageTo3DPipeline`). Aquí queda el
punto de integración; se importa de forma perezosa.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Optional

from .base import Engine, EngineNotAvailable, ProgressCb

_DEFAULT_DIR = Path(__file__).resolve().parents[4] / "externals" / "TRELLIS"


def _dir() -> Path:
    return Path(os.environ.get("IMG3D_TRELLIS_DIR", str(_DEFAULT_DIR)))


class TrellisEngine(Engine):
    name = "trellis"
    label = "TRELLIS (máximo detalle)"
    description = "Representación latente estructurada. Máxima calidad; mucha VRAM."
    quality = "high"
    needs_gpu = True

    _pipe = None

    def is_available(self) -> bool:
        d = _dir()
        return d.exists() and (d / "trellis").exists()

    def _load(self, device: str):
        if self._pipe is not None:
            return self._pipe
        d = _dir()
        if not self.is_available():
            raise EngineNotAvailable(f"TRELLIS no encontrado en {d}. Instálalo (ver README).")
        sys.path.insert(0, str(d))
        from trellis.pipelines import TrellisImageTo3DPipeline  # type: ignore

        pipe = TrellisImageTo3DPipeline.from_pretrained("microsoft/TRELLIS-image-large")
        pipe.to(device)
        self._pipe = pipe
        return pipe

    def reconstruct(self, image_path: Path, out_dir: Path, *, device: str = "auto",
                    progress: Optional[ProgressCb] = None, **params):
        from PIL import Image
        from trellis.utils import postprocessing_utils  # type: ignore

        dev = self.resolve_device(device)
        if progress:
            progress(15, f"Cargando TRELLIS en {dev}…")
        pipe = self._load(dev)

        if progress:
            progress(50, "Inferencia (TRELLIS)…")
        image = Image.open(image_path).convert("RGB")
        outputs = pipe.run(image, seed=int(params.get("seed", 1)))

        if progress:
            progress(85, "Convirtiendo a malla GLB…")
        glb = postprocessing_utils.to_glb(
            outputs["gaussian"][0], outputs["mesh"][0],
            simplify=float(params.get("simplify", 0.95)),
            texture_size=int(params.get("texture_size", 1024)),
        )
        out_dir.mkdir(parents=True, exist_ok=True)
        tmp = out_dir / "trellis_raw.glb"
        glb.export(str(tmp))
        import trimesh
        return trimesh.load(tmp)
