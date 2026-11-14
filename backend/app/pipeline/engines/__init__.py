"""Registro de motores 3D.

Cada motor implementa `Engine` (base.py). Se registran por nombre y el
pipeline elige uno en tiempo de ejecución según la petición. Así se puede
añadir un motor nuevo sin tocar el resto del código ("modular").
"""
from __future__ import annotations

from .base import Engine, EngineInfo, EngineNotAvailable
from .mock import MockEngine
from .triposr import TripoSREngine
from .instantmesh import InstantMeshEngine
from .trellis import TrellisEngine

# Instancias registradas (perezosas: no cargan pesos hasta usarlas).
_REGISTRY: dict[str, Engine] = {
    e.name: e for e in (
        MockEngine(),
        TripoSREngine(),
        InstantMeshEngine(),
        TrellisEngine(),
    )
}


def get_engine(name: str) -> Engine:
    engine = _REGISTRY.get(name)
    if engine is None:
        raise EngineNotAvailable(f"Motor desconocido: {name!r}")
    return engine


def list_engines() -> list[EngineInfo]:
    return [e.info() for e in _REGISTRY.values()]


__all__ = ["Engine", "EngineInfo", "EngineNotAvailable", "get_engine", "list_engines"]
