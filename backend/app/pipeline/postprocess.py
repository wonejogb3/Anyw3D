"""Postprocesamiento de la malla y exportación.

- Limpieza con trimesh: quita duplicados, componentes sueltos pequeños,
  caras degeneradas; recalcula normales.
- (Opcional) decimación a low-poly.
- Normaliza a una caja unitaria y centra en el origen (bueno para visor/VRM).
- Exporta a .glb (web) y .obj.
"""
from __future__ import annotations

import logging
from pathlib import Path

import trimesh

log = logging.getLogger("anyw3d.postprocess")


def _as_single_mesh(obj) -> trimesh.Trimesh:
    if isinstance(obj, trimesh.Scene):
        geoms = [g for g in obj.geometry.values() if isinstance(g, trimesh.Trimesh)]
        if not geoms:
            raise ValueError("La escena no contiene mallas.")
        return trimesh.util.concatenate(geoms)
    return obj


def clean_mesh(mesh: trimesh.Trimesh, drop_small_ratio: float = 0.02) -> trimesh.Trimesh:
    mesh = mesh.copy()
    mesh.merge_vertices()
    # trimesh 4.x: remove_duplicate_faces/remove_degenerate_faces están
    # obsoletas; se usa update_faces(...) y se cae a la API antigua si hace falta.
    if hasattr(mesh, "unique_faces"):
        mesh.update_faces(mesh.unique_faces())
    elif hasattr(mesh, "remove_duplicate_faces"):
        mesh.remove_duplicate_faces()
    if hasattr(mesh, "nondegenerate_faces"):
        mesh.update_faces(mesh.nondegenerate_faces())
    elif hasattr(mesh, "remove_degenerate_faces"):
        mesh.remove_degenerate_faces()
    mesh.remove_unreferenced_vertices()

    # Quitar islas pequeñas (ruido), conservando las de tamaño relevante.
    # Pasos opcionales: si fallan (dependencia de grafos ausente, malla rara),
    # se conserva la malla tal cual en vez de abortar la exportación.
    try:
        comps = mesh.split(only_watertight=False)
        if len(comps) > 1:
            biggest = max(len(c.faces) for c in comps)
            keep = [c for c in comps if len(c.faces) >= biggest * drop_small_ratio]
            if keep:
                mesh = trimesh.util.concatenate(keep)
    except Exception as exc:  # noqa: BLE001
        log.warning("Sin separar componentes: %s", exc)

    try:
        mesh.fix_normals()
    except Exception as exc:  # noqa: BLE001
        log.warning("Sin reorientar normales: %s", exc)
    return mesh


def _transfer_vertex_colors(src: trimesh.Trimesh, dst: trimesh.Trimesh) -> trimesh.Trimesh:
    """La decimación descarta el color por vértice: se recupera tomando, para cada
    vértice nuevo, el color del vértice original más cercano."""
    if getattr(src.visual, "kind", None) != "vertex":
        return dst
    try:
        _, nearest = src.kdtree.query(dst.vertices)
        dst.visual = trimesh.visual.ColorVisuals(
            dst, vertex_colors=src.visual.vertex_colors[nearest]
        )
    except Exception as exc:  # noqa: BLE001
        log.warning("No se pudieron transferir los colores: %s", exc)
    return dst


def decimate(mesh: trimesh.Trimesh, target_faces: int) -> trimesh.Trimesh:
    if target_faces <= 0 or len(mesh.faces) <= target_faces:
        return mesh
    try:
        # trimesh >= 4: el 1er argumento posicional es un PORCENTAJE; el número de
        # caras va en face_count. Requiere el paquete fast-simplification.
        reduced = mesh.simplify_quadric_decimation(face_count=int(target_faces))
    except TypeError:
        reduced = mesh.simplify_quadric_decimation(int(target_faces))  # trimesh 3.x
    except Exception as exc:  # noqa: BLE001
        log.warning("Decimación no disponible (%s); se exporta sin reducir.", exc)
        return mesh
    return _transfer_vertex_colors(mesh, reduced)


def normalize(mesh: trimesh.Trimesh) -> trimesh.Trimesh:
    mesh = mesh.copy()
    mesh.apply_translation(-mesh.bounding_box.centroid)
    scale = float(mesh.bounding_box.extents.max())
    if scale > 0:
        mesh.apply_scale(1.0 / scale)
    return mesh


def export(mesh: trimesh.Trimesh, out_dir: Path, name: str) -> dict[str, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    glb = out_dir / f"{name}.glb"
    obj = out_dir / f"{name}.obj"
    mesh.export(glb)
    mesh.export(obj)
    return {"glb": glb, "obj": obj}


def postprocess(mesh_or_scene, out_dir: Path, name: str, *,
                low_poly: bool = False, target_faces: int = 20000) -> dict[str, Path]:
    mesh = _as_single_mesh(mesh_or_scene)
    mesh = clean_mesh(mesh)
    if low_poly:
        mesh = decimate(mesh, target_faces)
    mesh = normalize(mesh)
    return export(mesh, out_dir, name)
