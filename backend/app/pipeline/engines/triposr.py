"""Adaptador para TripoSR (reconstrucción rápida de una sola imagen).

TripoSR (Stability AI / Tripo) produce una malla desde UNA imagen en segundos.
Es el motor recomendado para prototipos locales.

Integración (ver README, sección "Motores"):
  1. git clone https://github.com/VAST-AI-Research/TripoSR  externals/TripoSR
  2. pip install -r externals/TripoSR/requirements.txt   (+ torch con CUDA)
  3. Los pesos se descargan solos de HuggingFace la primera vez.
  4. Exporta IMG3D_TRIPOSR_DIR si lo clonas en otra ruta.

Este adaptador importa TripoSR de forma perezosa: si no está, el motor
aparece como "no disponible" y la app sigue funcionando con otros motores.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Optional

from .base import Engine, EngineNotAvailable, ProgressCb

_DEFAULT_DIR = Path(__file__).resolve().parents[4] / "externals" / "TripoSR"


def _triposr_dir() -> Path:
    return Path(os.environ.get("IMG3D_TRIPOSR_DIR", str(_DEFAULT_DIR)))


class TripoSREngine(Engine):
    name = "triposr"
    label = "TripoSR (rápido)"
    description = "Reconstrucción desde 1 imagen en segundos. Ideal para prototipos."
    quality = "fast"
    needs_gpu = True

    _model = None  # caché del modelo cargado

    def is_available(self) -> bool:
        d = _triposr_dir()
        return d.exists() and (d / "tsr").exists()

    def _load(self, device: str):
        if self._model is not None:
            return self._model
        d = _triposr_dir()
        if not self.is_available():
            raise EngineNotAvailable(
                f"TripoSR no encontrado en {d}. Clónalo (ver README)."
            )
        sys.path.insert(0, str(d))
        from tsr.system import TSR  # type: ignore

        model = TSR.from_pretrained(
            "stabilityai/TripoSR",
            config_name="config.yaml",
            weight_name="model.ckpt",
        )
        model.renderer.set_chunk_size(8192)
        model.to(device)
        self._model = model
        return model

    def reconstruct(self, image_path: Path, out_dir: Path, *, device: str = "auto",
                    progress: Optional[ProgressCb] = None, **params):
        import numpy as np
        import trimesh
        from PIL import Image

        def rep(p, m):
            if progress:
                progress(p, m)

        dev = self.resolve_device(device)
        rep(15, f"Cargando TripoSR en {dev}…")
        model = self._load(dev)

        rep(45, "Inferencia (TripoSR)…")
        image = Image.open(image_path).convert("RGB")
        with_torch = __import__("torch")
        with with_torch.no_grad():
            scene_codes = model([image], device=dev)
        rep(80, "Extrayendo malla (marching cubes)…")
        resolution = int(params.get("mc_resolution", 256))
        meshes = model.extract_mesh(scene_codes, resolution=resolution)
        mesh = meshes[0]  # trimesh.Trimesh
        # TripoSR entrega la malla en su propio marco; trimesh la maneja igual.
        return mesh
