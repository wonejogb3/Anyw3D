"""Lanzador de Anyw3D (punto de entrada del .exe portable).

1. Busca un puerto libre (8000 por defecto).
2. Arranca el servidor FastAPI (API + interfaz web) en 127.0.0.1.
3. Abre el navegador en la app.
Cerrar esta ventana detiene la aplicación.

Si algo falla al arrancar, la ventana NO se cierra: muestra el error, guarda una
copia en anyw3d_error.log (junto al .exe) y espera a que el usuario pulse Enter.
"""
from __future__ import annotations

import multiprocessing
import os
import socket
import sys
import threading
import traceback
import webbrowser
from datetime import datetime
from pathlib import Path


def _app_dir() -> Path:
    """Carpeta del .exe (o de este script en desarrollo). No depende de app.*,
    para poder informar incluso si falla la importación de la aplicación."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def _pause() -> None:
    """Mantiene abierta la consola (doble clic) hasta que el usuario pulse Enter."""
    try:
        if sys.stdin is not None and sys.stdin.isatty():
            input("\nPulsa Enter para cerrar esta ventana...")
    except (EOFError, OSError):
        pass


def _report_failure(title: str, detail: str) -> None:
    log_path = _app_dir() / "anyw3d_error.log"
    try:
        log_path.write_text(
            f"{datetime.now():%Y-%m-%d %H:%M:%S}  {title}\n\n{detail}\n", encoding="utf-8"
        )
        saved = str(log_path)
    except OSError:
        saved = "(no se pudo escribir el archivo de log)"
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)
    print(detail)
    print(f"  Copia del error: {saved}")
    _pause()


def _pick_port(preferred: int) -> int:
    for port in (preferred, *range(preferred + 1, preferred + 20)):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    # Último recurso: puerto libre asignado por el sistema
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def main() -> None:
    import uvicorn

    from app.config import APP_HOME, STORAGE_DIR, WEB_DIR, settings
    from app.main import app

    port = _pick_port(settings.port)
    url = f"http://127.0.0.1:{port}"

    print("=" * 60)
    print("  Anyw3D  -  Imagen 2D -> modelo 3D (local)")
    print("=" * 60)
    print(f"  App:        {url}")
    print(f"  Resultados: {STORAGE_DIR}")
    print(f"  Interfaz:   {'OK' if (WEB_DIR / 'index.html').exists() else 'NO COMPILADA'}")
    print(f"  Carpeta:    {APP_HOME}")
    print("  Cierra esta ventana para detener Anyw3D.")
    print("=" * 60)

    # ANYW3D_NO_BROWSER=1 arranca sin abrir el navegador (pruebas / uso remoto).
    if os.environ.get("ANYW3D_NO_BROWSER") != "1":
        threading.Timer(1.5, lambda: webbrowser.open(url)).start()
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="info")


def run() -> int:
    # Nunca fallar por imprimir caracteres que la consola no pueda mostrar.
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors="replace")  # type: ignore[union-attr]
        except Exception:  # noqa: BLE001
            pass
    try:
        main()
        return 0
    except KeyboardInterrupt:
        return 0
    except SystemExit as exc:
        # uvicorn termina con sys.exit(1) si no puede abrir el puerto, etc.;
        # el motivo ya está impreso arriba en la consola.
        code = exc.code if isinstance(exc.code, int) else 1
        if code != 0:
            _report_failure(
                f"Anyw3D se detuvo (código {code})",
                "Revisa los mensajes de arriba para ver el motivo.",
            )
        return code
    except Exception:  # noqa: BLE001
        _report_failure("Anyw3D no pudo arrancar. Detalle del error:", traceback.format_exc())
        return 1


if __name__ == "__main__":
    multiprocessing.freeze_support()
    sys.exit(run())
