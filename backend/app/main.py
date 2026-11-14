"""Punto de entrada del backend FastAPI de Anyw3D.

- /api/...   API REST + SSE
- /files/... resultados generados (png limpio, .glb, .obj) desde storage/
- /          interfaz web compilada (si existe backend/web), para que la app
             funcione con un solo proceso y sin Node (modo portable).

Desarrollo:   python -m app.main      (o uvicorn app.main:app --reload)
Portable:     Anyw3D.exe              (ver launcher.py)
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .api.routes import router
from .config import STORAGE_DIR, WEB_DIR, settings

app = FastAPI(title="Anyw3D", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

# Sirve los resultados: /files/outputs/<job>/model.glb, /files/uploads/..., etc.
app.mount("/files", StaticFiles(directory=str(STORAGE_DIR)), name="files")

if (WEB_DIR / "index.html").exists():
    # Interfaz web compilada. Se monta al final para no tapar /api ni /files.
    app.mount("/", StaticFiles(directory=str(WEB_DIR), html=True), name="web")
else:
    @app.get("/")
    def root():
        return {
            "name": "Anyw3D",
            "docs": "/docs",
            "api": "/api/engines",
            "hint": "Frontend no compilado: usa 'npm run dev' en frontend/ o compila con 'npm run build'.",
        }


def main() -> None:
    import uvicorn
    uvicorn.run(app, host=settings.host, port=settings.port, reload=False)


if __name__ == "__main__":
    main()
