"""Endpoints de la API Anyw3D.

POST /api/jobs            crea un job (multipart: image + config) y lo arranca
GET  /api/jobs            lista jobs
GET  /api/jobs/{id}       estado + progreso de un job
GET  /api/jobs/{id}/events  stream SSE con el progreso
GET  /api/engines         motores disponibles
Los archivos (png/glb/obj) se sirven en /files (montado en main.py).
"""
from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

from ..config import UPLOADS_DIR, settings
from ..jobs import JobStatus, store
from ..pipeline import engines
from ..pipeline.runner import run_job

router = APIRouter(prefix="/api")


@router.get("/engines")
def get_engines():
    return {
        "default": settings.default_engine,
        "engines": [e.__dict__ for e in engines.list_engines()],
    }


@router.get("/health")
def health():
    return {"ok": True, "version": "1.0.0"}


@router.post("/jobs")
async def create_job(
    background: BackgroundTasks,
    image: UploadFile = File(...),
    engine: str = Form(None),
    low_poly: bool = Form(False),
    target_faces: int = Form(20000),
    texture_size: int = Form(1024),
    input_size: int = Form(1024),
):
    # Validación de la subida
    if image.content_type not in ("image/png", "image/jpeg", "image/jpg"):
        raise HTTPException(400, "Formato no soportado. Usa PNG o JPG.")
    data = await image.read()
    if len(data) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(413, f"Imagen mayor de {settings.max_upload_mb} MB.")

    engine_name = engine or settings.default_engine
    try:
        engines.get_engine(engine_name)
    except engines.EngineNotAvailable as e:
        raise HTTPException(400, str(e))

    job = store.create(engine_name)
    src = UPLOADS_DIR / f"{job.id}_{image.filename or 'input.png'}"
    src.write_bytes(data)
    job.update(input_path=f"uploads/{src.name}")

    params = {
        "low_poly": low_poly,
        "target_faces": target_faces,
        "texture_size": texture_size,
        "input_size": input_size,
    }
    # Arranca el pipeline en segundo plano; responde al instante con el id.
    background.add_task(run_job, job.id, src, params)
    return job.to_dict()


@router.get("/jobs")
def list_jobs():
    return [j.to_dict() for j in store.all()]


@router.get("/jobs/{job_id}")
def get_job(job_id: str):
    job = store.get(job_id)
    if job is None:
        raise HTTPException(404, "Job no encontrado.")
    return job.to_dict()


@router.get("/jobs/{job_id}/events")
async def job_events(job_id: str):
    """Server-Sent Events: emite el estado hasta que el job termina."""
    if store.get(job_id) is None:
        raise HTTPException(404, "Job no encontrado.")

    async def gen():
        last = None
        while True:
            job = store.get(job_id)
            if job is None:
                break
            snap = job.to_dict()
            if snap != last:
                yield f"data: {json.dumps(snap)}\n\n"
                last = snap
            if job.status in (JobStatus.DONE, JobStatus.ERROR):
                break
            await asyncio.sleep(0.4)

    return StreamingResponse(gen(), media_type="text/event-stream")
