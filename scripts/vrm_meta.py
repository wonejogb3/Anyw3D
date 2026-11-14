"""Corrige los metadatos (nombre, autores y licencia) de un VRM 1.0 sin tocar malla ni texturas.

Al convertir un VRM 0.x con licencia "Other" a VRM 1.0, 3DVtuber elige siempre los términos más
estrictos (modificación prohibida, crédito obligatorio, sin redistribución), aunque el archivo
enlace una página de VRoid Hub que diga otra cosa. Esta herramienta lee esa página
(`meta.otherLicenseUrl`, sus parámetros de consulta) y escribe los mismos términos en los campos
de VRM 1.0: ni más estrictos ni más permisivos. Lo que VRoid Hub no expresa (uso político,
religioso u odioso) se deja como estaba.

Solo se reescribe el bloque JSON del .glb; el bloque binario (malla, texturas) se copia tal cual.

    python scripts/vrm_meta.py entrada.vrm salida.vrm --name "Rabbit" [--author "Nombre"] [--from-vroid]
"""
from __future__ import annotations

import argparse
import json
import struct
import sys
from pathlib import Path
from urllib.parse import parse_qsl, urlsplit


def read_glb(path: Path) -> tuple[dict, bytes]:
    data = path.read_bytes()
    magic, _version, _length = struct.unpack_from("<4sII", data, 0)
    if magic != b"glTF":
        raise ValueError(f"{path} no es un archivo GLB/VRM")
    off, gltf, binary = 12, None, None
    while off < len(data):
        clen, ctype = struct.unpack_from("<I4s", data, off)
        chunk = data[off + 8: off + 8 + clen]
        if ctype == b"JSON":
            gltf = json.loads(chunk.decode("utf-8"))
        elif ctype == b"BIN\x00":
            binary = chunk
        off += 8 + clen
    if gltf is None:
        raise ValueError(f"{path} no tiene bloque JSON")
    return gltf, binary or b""


def write_glb(path: Path, gltf: dict, binary: bytes) -> None:
    js = json.dumps(gltf, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    js += b" " * (-len(js) % 4)                 # el bloque JSON se rellena con espacios
    binary += b"\x00" * (-len(binary) % 4)       # el binario, con ceros
    chunks = struct.pack("<I4s", len(js), b"JSON") + js
    if binary:
        chunks += struct.pack("<I4s", len(binary), b"BIN\x00") + binary
    path.write_bytes(struct.pack("<4sII", b"glTF", 2, 12 + len(chunks)) + chunks)


def vroid_terms(url: str) -> dict | None:
    """Términos de una URL de licencia de VRoid Hub traducidos a campos de VRM 1.0, o None."""
    parts = urlsplit(url)
    if parts.hostname != "hub.vroid.com" or not parts.path.endswith("/license"):
        return None
    q = dict(parse_qsl(parts.query))
    modify = q.get("modification") == "allow"
    redistribute = q.get("redistribution") == "allow"
    if q.get("corporate_commercial_use") == "allow":
        commercial = "corporation"
    elif q.get("personal_commercial_use") in ("profit", "allow"):
        commercial = "personalProfit"
    else:
        commercial = "personalNonProfit"
    users = q.get("allowed_to_use_user")
    return {
        "avatarPermission": {"everyone": "everyone", "author": "onlyAuthor"}.get(users, "onlySeparatelyLicensedPerson"),
        "allowExcessivelyViolentUsage": q.get("violent_expression") == "allow",
        "allowExcessivelySexualUsage": q.get("sexual_expression") == "allow",
        "commercialUsage": commercial,
        "creditNotation": "unnecessary" if q.get("credit") == "unnecessary" else "required",
        "allowRedistribution": redistribute,
        "modification": ("allowModificationRedistribution" if modify and redistribute
                         else "allowModification" if modify else "prohibited"),
    }


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("src", type=Path)
    p.add_argument("dst", type=Path)
    p.add_argument("--name", help="nombre del avatar (meta.name)")
    p.add_argument("--author", action="append", help="autor (repetible); por defecto se mantienen")
    p.add_argument("--from-vroid", action="store_true",
                   help="traducir la licencia de la URL de VRoid Hub (meta.otherLicenseUrl) a VRM 1.0")
    a = p.parse_args(argv)

    gltf, binary = read_glb(a.src)
    vrm = (gltf.get("extensions") or {}).get("VRMC_vrm")
    if not vrm:
        print("error: no es un VRM 1.0 (falta VRMC_vrm)", file=sys.stderr)
        return 1
    meta = vrm.setdefault("meta", {})
    before = dict(meta)

    if a.name:
        meta["name"] = a.name
    if a.author:
        meta["authors"] = a.author
    if a.from_vroid:
        terms = vroid_terms(meta.get("otherLicenseUrl", ""))
        if terms is None:
            print("error: meta.otherLicenseUrl no es una licencia de VRoid Hub", file=sys.stderr)
            return 1
        meta.update(terms)

    write_glb(a.dst, gltf, binary)
    changed = {k: (before.get(k), meta[k]) for k in meta if before.get(k) != meta[k]}
    print(json.dumps({"written": str(a.dst), "changed": changed}, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
