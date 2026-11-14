"""Orquesta un job completo: preprocess → engine → postprocess.

Se ejecuta en un hilo de fondo (BackgroundTasks de FastAPI). Va actualizando
el Job para que el frontend vea el progreso en tiempo real.
"""
from __future__ import annotations

from pathlib import Path

from ..config import OUTPUTS_DIR, UPLOADS_DIR, settings
from ..jobs import Job, JobStatus, store
from . import engines
from .postprocess import postprocess
from .preprocess import preprocess_image


def _rel(path: Path) -> str:
    """Ruta relativa a storage/, para servirla por /files."""
    from ..config import STORAGE_DIR
    return path.relative_to(STORAGE_DIR).as_posix()


def run_job(job_id: str, src_image: Path, params: dict) -> None:
    job = store.get(job_id)
    if job is None:
        return
    out_dir = OUTPUTS_DIR / job_id
    try:
        engine = engines.get_engine(job.engine)
        if not engine.info().available:
            raise engines.EngineNotAvailable(
                f"El motor '{job.engine}' no está disponible. Instálalo o usa 'mock'."
            )

        # 1) Preprocesamiento --------------------------------------------------
        job.update(status=JobStatus.PREPROCESSING, progress=5, stage="Quitando fondo…")
        clean_png = out_dir / "input_clean.png"
        preprocess_image(src_image, clean_png, size=int(params.get("input_size", 1024)))
        job.update(progress=15, preview_path=_rel(clean_png))

        # 2) Inferencia 3D -----------------------------------------------------
        job.update(status=JobStatus.INFERRING, stage=f"Reconstruyendo ({engine.label})…")

        def on_progress(pct: int, msg: str) -> None:
            # Mapear 0-100 del motor al tramo 15-85 del job.
            job.update(progress=15 + int(pct * 0.70), stage=msg)

        mesh = engine.reconstruct(
            clean_png, out_dir,
            device=settings.device,
            progress=on_progress,
            **{k: v for k, v in params.items() if k not in ("input_size",)},
        )

        # 3) Postprocesamiento + exportación -----------------------------------
        job.update(status=JobStatus.POSTPROCESSING, progress=88, stage="Limpiando y exportando…")
        outputs = postprocess(
            mesh, out_dir, "model",
            low_poly=bool(params.get("low_poly", False)),
            target_faces=int(params.get("target_faces", 20000)),
        )

        job.update(
            status=JobStatus.DONE, progress=100, stage="Listo",
            glb_path=_rel(outputs["glb"]), obj_path=_rel(outputs["obj"]),
        )
    except Exception as exc:  # noqa: BLE001 - se reporta al cliente
        job.update(status=JobStatus.ERROR, stage="Error", error=str(exc))
