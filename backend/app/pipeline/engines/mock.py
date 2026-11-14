"""Motor de prueba (sin IA, sin GPU).

Convierte la silueta de la imagen en un volumen cerrado "inflado": el relieve
crece hacia el centro con un perfil redondeado (raíz de la distancia al borde),
por delante y por detrás, y cada vértice toma el color del píxel. No es
reconstrucción 3D por IA, pero permite probar TODO el pipeline y el visor de
inmediato en cualquier PC, sin pesos ni CUDA. Es el motor por defecto.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import numpy as np
import trimesh

from .base import Engine, ProgressCb

# Resolución de la rejilla (px del lado mayor) y grosor máximo del relieve
# (en unidades del lado de la imagen).
_GRID = 180
_THICKNESS = 0.22


class MockEngine(Engine):
    name = "mock"
    label = "Demo (silueta inflada)"
    description = "Prueba el pipeline completo sin GPU ni pesos. No es IA 3D real."
    quality = "fast"
    needs_gpu = False

    def is_available(self) -> bool:
        return True

    def reconstruct(self, image_path: Path, out_dir: Path, *, device: str = "auto",
                    progress: Optional[ProgressCb] = None, **params):
        import cv2
        from PIL import Image

        def rep(p, m):
            if progress:
                progress(p, m)

        rep(10, "Leyendo silueta…")
        img = Image.open(image_path).convert("RGBA")
        img.thumbnail((_GRID, _GRID), Image.LANCZOS)
        rgba = np.asarray(img)
        alpha = rgba[:, :, 3] > 40
        rgb = rgba[:, :, :3]
        h, w = alpha.shape
        if not alpha.any():
            rep(90, "Imagen vacía: generando primitiva…")
            return trimesh.creation.icosphere(subdivisions=3, radius=0.5)

        rep(35, "Calculando relieve…")
        # Distancia al borde: 1 en el contorno -> relieve 0 (cierra frente y dorso).
        dist = cv2.distanceTransform(alpha.astype(np.uint8), cv2.DIST_L2, 5)
        d = np.clip(dist - 1.0, 0.0, None)
        depth = np.sqrt(d / (d.max() + 1e-6)) * _THICKNESS

        rep(60, "Construyendo malla…")
        ys, xs = np.nonzero(alpha)
        n = len(xs)
        idx = -np.ones((h, w), dtype=np.int64)
        idx[ys, xs] = np.arange(n)

        scale = 1.0 / max(h, w)
        x = (xs - w / 2) * scale
        y = (h / 2 - ys) * scale
        z = depth[ys, xs]
        vertices = np.vstack([np.column_stack([x, y, z]), np.column_stack([x, y, -z])])
        colors = np.vstack([rgb[ys, xs], rgb[ys, xs]])

        # Dos triángulos por cada 2x2 de píxeles del objeto, con normal hacia +Z.
        a, b = idx[:-1, :-1], idx[:-1, 1:]
        c, e = idx[1:, :-1], idx[1:, 1:]
        ok = (a >= 0) & (b >= 0) & (c >= 0) & (e >= 0)
        a, b, c, e = a[ok], b[ok], c[ok], e[ok]
        front = np.vstack([np.column_stack([a, e, b]), np.column_stack([a, c, e])])
        back = front[:, ::-1] + n   # dorso: mismos triángulos, orientación inversa
        faces = np.vstack([front, back])

        rep(85, "Uniendo frente y dorso…")
        mesh = trimesh.Trimesh(
            vertices=vertices,
            faces=faces,
            vertex_colors=np.column_stack([colors, np.full(len(colors), 255, np.uint8)]),
            process=True,   # fusiona los vértices del contorno (z=0) de ambas caras
        )
        rep(95, "Malla lista")
        return mesh
