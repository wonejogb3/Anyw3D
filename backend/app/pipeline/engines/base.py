"""Contrato común de todos los motores de reconstrucción 3D."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

# callback de progreso: (porcentaje 0-100, mensaje)
ProgressCb = Callable[[int, str], None]


class EngineNotAvailable(RuntimeError):
    """El motor no está instalado o sus pesos no están disponibles."""


@dataclass
class EngineInfo:
    name: str
    label: str
    description: str
    available: bool
    quality: str           # "fast" | "balanced" | "high"
    needs_gpu: bool


class Engine(ABC):
    name: str = "base"
    label: str = "Base"
    description: str = ""
    quality: str = "balanced"
    needs_gpu: bool = True

    @abstractmethod
    def is_available(self) -> bool:
        """True si se puede ejecutar (dependencias + pesos presentes)."""

    @abstractmethod
    def reconstruct(self, image_path: Path, out_dir: Path,
                    *, device: str = "auto",
                    progress: Optional[ProgressCb] = None, **params):
        """Convierte una imagen RGBA preprocesada en una malla.

        Devuelve un `trimesh.Trimesh` o `trimesh.Scene`.
        Debe reportar avance con `progress(pct, msg)` si se proporciona.
        """

    # Utilidades compartidas -------------------------------------------------
    def info(self) -> EngineInfo:
        return EngineInfo(
            name=self.name, label=self.label, description=self.description,
            available=self._safe_available(), quality=self.quality,
            needs_gpu=self.needs_gpu,
        )

    def _safe_available(self) -> bool:
        try:
            return self.is_available()
        except Exception:
            return False

    @staticmethod
    def resolve_device(device: str) -> str:
        if device != "auto":
            return device
        try:
            import torch
            return "cuda" if torch.cuda.is_available() else "cpu"
        except Exception:
            return "cpu"
