"""Preprocesamiento de la imagen de entrada.

1. Carga PNG/JPG (respeta transparencia si ya la trae).
2. Quita el fondo con `rembg` (si está instalado); si no, usa un recorte
   simple por umbral con OpenCV como respaldo.
3. Recorta al bounding box del objeto y centra sobre lienzo cuadrado RGBA.

La salida es un PNG RGBA cuadrado, listo para los modelos de reconstrucción
(TripoSR/InstantMesh esperan objeto centrado con fondo transparente).
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image

try:
    from rembg import remove as _rembg_remove  # type: ignore
    _HAS_REMBG = True
except Exception:  # pragma: no cover - rembg es opcional
    _HAS_REMBG = False


def _remove_background(img: Image.Image) -> Image.Image:
    """Devuelve RGBA con el fondo transparente."""
    if img.mode == "RGBA" and _alpha_is_meaningful(img):
        # La imagen ya viene con transparencia útil.
        return img
    if _HAS_REMBG:
        return _rembg_remove(img.convert("RGBA"))
    # Respaldo sin rembg: umbral sobre fondo claro con OpenCV.
    return _threshold_bg_removal(img)


def _alpha_is_meaningful(img: Image.Image) -> bool:
    a = np.asarray(img.split()[-1])
    transparent_ratio = (a < 10).mean()
    return 0.02 < transparent_ratio < 0.98


def _threshold_bg_removal(img: Image.Image) -> Image.Image:
    import cv2

    rgb = np.asarray(img.convert("RGB"))
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    # GrabCut inicial a partir de un rectángulo centrado (heurística simple).
    mask = np.zeros(gray.shape, np.uint8)
    bgd, fgd = np.zeros((1, 65), np.float64), np.zeros((1, 65), np.float64)
    h, w = gray.shape
    rect = (int(w * 0.05), int(h * 0.05), int(w * 0.9), int(h * 0.9))
    try:
        cv2.grabCut(rgb, mask, rect, bgd, fgd, 5, cv2.GC_INIT_WITH_RECT)
        alpha = np.where((mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD), 255, 0).astype(np.uint8)
    except Exception:
        _, alpha = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    rgba = np.dstack([rgb, alpha])
    return Image.fromarray(rgba, "RGBA")


def _crop_and_center(img: Image.Image, size: int = 1024, pad: float = 0.1) -> Image.Image:
    """Recorta al objeto (según alfa) y lo centra en un cuadrado RGBA."""
    rgba = np.asarray(img.convert("RGBA"))
    alpha = rgba[:, :, 3]
    ys, xs = np.where(alpha > 10)
    if len(xs) == 0:  # nada detectado: devuelve centrado tal cual
        obj = img.convert("RGBA")
    else:
        x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()
        obj = Image.fromarray(rgba[y0:y1 + 1, x0:x1 + 1], "RGBA")

    # Escalar manteniendo proporción dentro de size*(1-pad)
    inner = int(size * (1 - pad))
    ow, oh = obj.size
    scale = min(inner / ow, inner / oh)
    obj = obj.resize((max(1, int(ow * scale)), max(1, int(oh * scale))), Image.LANCZOS)

    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    ox = (size - obj.size[0]) // 2
    oy = (size - obj.size[1]) // 2
    canvas.paste(obj, (ox, oy), obj)
    return canvas


def preprocess_image(src: Path, dst: Path, size: int = 1024) -> Path:
    """Ejecuta todo el preprocesamiento y guarda el PNG RGBA resultante."""
    img = Image.open(src)
    img = _remove_background(img)
    img = _crop_and_center(img, size=size)
    dst.parent.mkdir(parents=True, exist_ok=True)
    img.save(dst, "PNG")
    return dst
