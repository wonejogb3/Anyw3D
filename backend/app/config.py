"""Configuración central del backend de Anyw3D.

Funciona igual en desarrollo y empaquetado como .exe portable (PyInstaller):
- Desarrollo:  APP_HOME = carpeta backend/
- Portable:    APP_HOME = carpeta donde está Anyw3D.exe (escribible; ahí se
               crean storage/ y se lee .env). Los recursos internos (la web
               compilada) se leen de BUNDLE_DIR (sys._MEIPASS).

Se puede sobreescribir con variables de entorno (prefijo IMG3D_) o un .env
junto al ejecutable. Ej: IMG3D_DEFAULT_ENGINE=triposr
"""
from __future__ import annotations

import sys
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

FROZEN = bool(getattr(sys, "frozen", False))

if FROZEN:
    APP_HOME = Path(sys.executable).resolve().parent
    BUNDLE_DIR = Path(getattr(sys, "_MEIPASS", APP_HOME))
else:
    APP_HOME = Path(__file__).resolve().parent.parent  # .../backend
    BUNDLE_DIR = APP_HOME

# Compatibilidad con módulos que usan BACKEND_ROOT
BACKEND_ROOT = APP_HOME
STORAGE_DIR = APP_HOME / "storage"
UPLOADS_DIR = STORAGE_DIR / "uploads"
OUTPUTS_DIR = STORAGE_DIR / "outputs"
# Frontend compilado (vite build -> backend/web). Si existe, el backend lo sirve en "/".
WEB_DIR = BUNDLE_DIR / "web"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="IMG3D_", env_file=str(APP_HOME / ".env"), extra="ignore"
    )

    # Red
    host: str = "127.0.0.1"
    port: int = 8000
    # Orígenes permitidos para el frontend en modo desarrollo (Vite en 5173)
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    # Motor 3D por defecto: "mock" | "triposr" | "instantmesh" | "trellis"
    # "mock" genera una malla de prueba y permite usar toda la app sin GPU.
    default_engine: str = "mock"

    # Límites de subida
    max_upload_mb: int = 25

    # Dispositivo preferido para inferencia: "auto" | "cuda" | "cpu"
    device: str = "auto"

    def ensure_dirs(self) -> None:
        for d in (STORAGE_DIR, UPLOADS_DIR, OUTPUTS_DIR):
            d.mkdir(parents=True, exist_ok=True)


settings = Settings()
settings.ensure_dirs()
