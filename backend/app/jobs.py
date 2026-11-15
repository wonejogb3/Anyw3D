"""Gestor de trabajos (jobs) en memoria con progreso en tiempo real.

Cada conversión imagen→3D es un Job con estado y progreso (0–100). El
pipeline reporta avance con `job.update(...)`. El frontend consulta el
estado por polling (GET /api/jobs/{id}) o por stream SSE.

Para una app de un solo usuario en local, un store en memoria es suficiente.
Para multiusuario/persistencia, cambiar por Redis o SQLite.
"""
from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Optional


class JobStatus(str, Enum):
    QUEUED = "queued"
    PREPROCESSING = "preprocessing"
    INFERRING = "inferring"
    POSTPROCESSING = "postprocessing"
    DONE = "done"
    ERROR = "error"


@dataclass
class Job:
    id: str
    engine: str
    status: JobStatus = JobStatus.QUEUED
    progress: int = 0
    stage: str = "En cola"
    error: Optional[str] = None
    # Rutas relativas servidas por /files
    input_path: Optional[str] = None
    preview_path: Optional[str] = None   # imagen ya sin fondo
    glb_path: Optional[str] = None
    obj_path: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    meta: dict = field(default_factory=dict)

    def update(self, *, status: JobStatus | None = None, progress: int | None = None,
               stage: str | None = None, **fields) -> None:
        if status is not None:
            self.status = status
        if progress is not None:
            self.progress = max(0, min(100, int(progress)))
        if stage is not None:
            self.stage = stage
        for k, v in fields.items():
            setattr(self, k, v)
        self.updated_at = time.time()

    def to_dict(self) -> dict:
        d = asdict(self)
        d["status"] = self.status.value
        return d


class JobStore:
    def __init__(self) -> None:
        self._jobs: dict[str, Job] = {}
        self._lock = threading.Lock()

    def create(self, engine: str) -> Job:
        job = Job(id=uuid.uuid4().hex[:12], engine=engine)
        with self._lock:
            self._jobs[job.id] = job
        return job

    def get(self, job_id: str) -> Optional[Job]:
        with self._lock:
            return self._jobs.get(job_id)

    def all(self) -> list[Job]:
        with self._lock:
            return sorted(self._jobs.values(), key=lambda j: j.created_at, reverse=True)


store = JobStore()
