"""Renderiza la cara de un VRM con cada expresión (por defecto las 52 ARKit) para revisarlas.

Se ejecuta DENTRO de Blender (con el add-on VRM activo):

    blender -b --factory-startup -P externals/3DVtuber/scripts/_startup.py -P scripts/render_expresiones.py -- avatar.vrm carpeta_salida [--size 320] [--all]

Escribe un PNG por expresión (00_neutral.png, JawOpen.png, …) con la misma cámara ortográfica
frontal, encuadrada sobre la malla de la cara. La hoja de contactos se arma aparte
(scripts/hoja_contactos.py).
"""
import argparse
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

ARKIT_PREFIX = ("Eye", "Jaw", "Mouth", "Brow", "Cheek", "Nose", "Tongue")


def args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    p = argparse.ArgumentParser()
    p.add_argument("vrm", type=Path)
    p.add_argument("out", type=Path)
    p.add_argument("--size", type=int, default=320)
    p.add_argument("--all", action="store_true", help="también las expresiones estándar (happy, aa…)")
    p.add_argument("--engine", choices=("workbench", "eevee"), default="workbench",
                   help="eevee respeta la transparencia de MToon (más fiel, más lento)")
    p.add_argument("--only", nargs="*", default=[], help="renderizar solo estas expresiones")
    p.add_argument("--hide", nargs="*", default=[],
                   help="ocultar objetos cuyo nombre contenga estos textos (p. ej. Hair: el render rápido ignora la "
                        "transparencia de MToon y un pelo transparente sale opaco, tapando las cejas)")
    return p.parse_args(argv)


def expressions(armature):
    """[(nombre, [(objeto, forma, peso)])] de las expresiones VRM 1.0 del avatar."""
    ext = armature.data.vrm_addon_extension.vrm1.expressions
    out = []
    for e in ext.custom:
        out.append((e.custom_name, e))
    # nombre VRM 1.0 -> atributo del add-on
    presets = {"happy": "happy", "angry": "angry", "sad": "sad", "relaxed": "relaxed", "surprised": "surprised",
               "aa": "aa", "ih": "ih", "ou": "ou", "ee": "ee", "oh": "oh",
               "blink": "blink", "blinkLeft": "blink_left", "blinkRight": "blink_right"}
    for name, attr in presets.items():
        e = getattr(ext.preset, attr, None)
        if e is not None:
            out.append((name, e))
    res = []
    for name, e in out:
        binds = []
        for b in e.morph_target_binds:
            obj = bpy.data.objects.get(b.node.mesh_object_name)
            if obj and obj.data.shape_keys and b.index in obj.data.shape_keys.key_blocks:
                binds.append((obj, b.index, b.weight))
        res.append((name, binds))
    return res


def reset_keys():
    for obj in bpy.data.objects:
        if obj.type == "MESH" and obj.data.shape_keys:
            for kb in obj.data.shape_keys.key_blocks[1:]:
                kb.value = 0.0


def main():
    a = args()
    a.out.mkdir(parents=True, exist_ok=True)
    # escena vacía (sin read_factory_settings: reiniciaría las preferencias y apagaría el add-on VRM)
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    bpy.ops.import_scene.vrm(filepath=str(a.vrm))
    armature = next(o for o in bpy.data.objects if o.type == "ARMATURE")
    for obj in bpy.data.objects:
        if any(h.lower() in obj.name.lower() for h in a.hide):
            obj.hide_render = True
            print(f"HIDDEN {obj.name}")
    face = next(o for o in bpy.data.objects if o.type == "MESH" and o.data.shape_keys
                and any(k.name.startswith("Fcl_") for k in o.data.shape_keys.key_blocks))

    # encuadre: caja de la cara en el mundo (la parte delantera es -Y en Blender)
    corners = [face.matrix_world @ Vector(c) for c in face.bound_box]
    lo = Vector((min(c.x for c in corners), min(c.y for c in corners), min(c.z for c in corners)))
    hi = Vector((max(c.x for c in corners), max(c.y for c in corners), max(c.z for c in corners)))
    center = (lo + hi) / 2
    cam_data = bpy.data.cameras.new("cam")
    cam_data.type = "ORTHO"
    cam_data.ortho_scale = max(hi.x - lo.x, hi.z - lo.z) * 1.15
    cam = bpy.data.objects.new("cam", cam_data)
    bpy.context.scene.collection.objects.link(cam)
    cam.location = (center.x, lo.y - 1.0, center.z)
    cam.rotation_euler = (math.pi / 2, 0.0, 0.0)          # mira hacia +Y: de frente a la cara
    scene = bpy.context.scene
    scene.camera = cam
    if a.engine == "eevee":
        engines = {e.identifier for e in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items}
        scene.render.engine = "BLENDER_EEVEE_NEXT" if "BLENDER_EEVEE_NEXT" in engines else "BLENDER_EEVEE"
        world = bpy.data.worlds.new("fondo")
        world.use_nodes = True
        world.node_tree.nodes["Background"].inputs[0].default_value = (0.25, 0.25, 0.27, 1)
        world.node_tree.nodes["Background"].inputs[1].default_value = 1.0
        scene.world = world
    else:
        scene.render.engine = "BLENDER_WORKBENCH"
        scene.display.shading.light = "STUDIO"
        scene.display.shading.color_type = "TEXTURE"
    scene.render.resolution_x = scene.render.resolution_y = a.size
    scene.render.film_transparent = False
    scene.render.image_settings.file_format = "PNG"

    items = [("00_neutral", [])] + [(n, b) for n, b in expressions(armature)
                                    if a.all or n.startswith(ARKIT_PREFIX)]
    if a.only:
        items = [it for it in items if it[0] in a.only or it[0] == "00_neutral"]
    for name, binds in items:
        reset_keys()
        for obj, key, weight in binds:
            obj.data.shape_keys.key_blocks[key].value = weight
        scene.render.filepath = str(a.out / f"{name}.png")
        bpy.ops.render.render(write_still=True)
        print(f"RENDER {name} binds={len(binds)}")
    print(f"RENDER_DONE {len(items)}")


main()
