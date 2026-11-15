"""Añade las 52 formas ARKit ("perfect sync") a un avatar VRM 0.x de VRoid.

Fuente de las formas: los modelos de hinzka (github.com/hinzka/52blendshapes-for-VRoid-face,
uso libre, sin crédito obligatorio), con las 52 formas modeladas sobre la cara base de VRoid.

Cómo se construye cada forma:
- Boca, mandíbula, mejillas, nariz y lengua: se TRANSFIEREN de la cara de hinzka. Las zonas piel
  ("Face"), boca ("FaceMouth") y blanco del ojo ("EyeWhite") comparten malla base con VRoid aunque el
  orden de vértices y el atlas cambien: la correspondencia se recupera por UV + posición, se valida
  por triángulos y se propaga por vecindad. Cada desplazamiento se adapta con un mapa lineal local
  (vecindario de 2 anillos), y los vértices sin correspondencia fiable se rellenan por difusión.
- Ojos y cejas: se construyen con las propias formas Fcl_ del avatar (su geometría de ojos y cejas
  difiere de la base), como hace hinzka con el parpadeo.
- eyeLook*: la mirada la mueven los huesos de los ojos del VRM; las formas quedan neutras.

Salida: el mismo VRM 0.x con 52 formas nuevas en la malla de la cara (nombres ARKit en lowerCamel)
y 52 clips de expresión (UpperCamel: EyeBlinkLeft…), como los modelos perfect sync de VRoid.
Solo se AÑADEN datos: las formas, texturas y huesos originales quedan intactos.

    python scripts/perfect_sync.py avatar.vrm salida.vrm --source hinzka_Female.vrm [--report informe.json]
"""
from __future__ import annotations

import argparse
import json
import struct
import sys
from pathlib import Path

import numpy as np
from scipy.spatial import cKDTree

# ─── formato GLB ────────────────────────────────────────────────────────────────
COMP = {5126: np.float32, 5123: np.uint16, 5125: np.uint32, 5121: np.uint8, 5122: np.int16, 5120: np.int8}
NCOMP = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4}


def read_glb(path: Path):
    data = path.read_bytes()
    if data[:4] != b"glTF":
        raise ValueError(f"{path} no es GLB/VRM")
    off, gltf, binary = 12, None, b""
    while off < len(data):
        clen, ctype = struct.unpack_from("<I4s", data, off)
        chunk = data[off + 8: off + 8 + clen]
        if ctype == b"JSON":
            gltf = json.loads(chunk.decode("utf-8"))
        elif ctype == b"BIN\x00":
            binary = chunk
        off += 8 + clen
    return gltf, bytearray(binary)


def write_glb(path: Path, gltf: dict, binary: bytes) -> None:
    js = json.dumps(gltf, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    js += b" " * (-len(js) % 4)
    binary = bytes(binary) + b"\x00" * (-len(binary) % 4)
    body = struct.pack("<I4s", len(js), b"JSON") + js + struct.pack("<I4s", len(binary), b"BIN\x00") + binary
    path.write_bytes(struct.pack("<4sII", b"glTF", 2, 12 + len(body)) + body)


def accessor(g, b, i):
    a = g["accessors"][i]
    dt, n, count = COMP[a["componentType"]], NCOMP[a["type"]], a["count"]
    if "bufferView" in a:
        bv = g["bufferViews"][a["bufferView"]]
        start = bv.get("byteOffset", 0) + a.get("byteOffset", 0)
        size = np.dtype(dt).itemsize * n
        stride = bv.get("byteStride") or size
        raw = np.frombuffer(bytes(b[start: start + stride * (count - 1) + size]), np.uint8)
        if stride == size:
            out = raw.view(dt).reshape(count, n).copy()
        else:
            out = np.lib.stride_tricks.as_strided(raw, (count, size), (stride, 1)).copy().view(dt).reshape(count, n)
    else:
        out = np.zeros((count, n), dt)
    if "sparse" in a:  # accesores dispersos
        sp = a["sparse"]
        ibv, vbv = g["bufferViews"][sp["indices"]["bufferView"]], g["bufferViews"][sp["values"]["bufferView"]]
        idx = np.frombuffer(bytes(b), COMP[sp["indices"]["componentType"]], sp["count"],
                            ibv.get("byteOffset", 0) + sp["indices"].get("byteOffset", 0))
        val = np.frombuffer(bytes(b), dt, sp["count"] * n,
                            vbv.get("byteOffset", 0) + sp["values"].get("byteOffset", 0)).reshape(-1, n)
        out[idx] = val
    return out


def add_accessor(g, b: bytearray, arr: np.ndarray, with_minmax: bool) -> int:
    arr = np.ascontiguousarray(arr, np.float32)
    while len(b) % 4:
        b.append(0)
    g["bufferViews"].append({"buffer": 0, "byteOffset": len(b), "byteLength": arr.nbytes})
    b.extend(arr.tobytes())
    acc = {"bufferView": len(g["bufferViews"]) - 1, "componentType": 5126, "count": len(arr), "type": "VEC3"}
    if with_minmax:
        acc["min"], acc["max"] = arr.min(0).tolist(), arr.max(0).tolist()
    g["accessors"].append(acc)
    return len(g["accessors"]) - 1


# ─── cara VRoid ─────────────────────────────────────────────────────────────────
ZONES = ("FaceMouth", "EyeIris", "EyeHighlight", "EyeWhite", "FaceBrow", "FaceEyeline", "FaceEyelash", "EyeExtra", "Face")
TRANSFER_ZONES = ("Face", "FaceMouth", "EyeWhite")
ARKIT = """eyeBlinkLeft eyeLookDownLeft eyeLookInLeft eyeLookOutLeft eyeLookUpLeft eyeSquintLeft eyeWideLeft
eyeBlinkRight eyeLookDownRight eyeLookInRight eyeLookOutRight eyeLookUpRight eyeSquintRight eyeWideRight
jawForward jawLeft jawRight jawOpen mouthClose mouthFunnel mouthPucker mouthLeft mouthRight mouthSmileLeft
mouthSmileRight mouthFrownLeft mouthFrownRight mouthDimpleLeft mouthDimpleRight mouthStretchLeft mouthStretchRight
mouthRollLower mouthRollUpper mouthShrugLower mouthShrugUpper mouthPressLeft mouthPressRight mouthLowerDownLeft
mouthLowerDownRight mouthUpperUpLeft mouthUpperUpRight browDownLeft browDownRight browInnerUp browOuterUpLeft
browOuterUpRight cheekPuff cheekSquintLeft cheekSquintRight noseSneerLeft noseSneerRight tongueOut""".split()
# Formas de ojos y cejas: se construyen con las Fcl_ del propio avatar (no se transfieren)
OWN = {"eyeBlink", "eyeSquint", "eyeWide", "eyeLook", "browDown", "browInnerUp", "browOuterUp"}


class Face:
    def __init__(self, g, b):
        self.g, self.b = g, b
        cands = [(i, m) for i, m in enumerate(g["meshes"])
                 if any("Fcl_" in n for n in self._names(m))]
        if not cands:
            raise ValueError("no se encontró la malla de la cara de VRoid (formas Fcl_)")
        self.mesh_index, self.mesh = cands[0]
        self.prims = self.mesh["primitives"]
        if len({p["attributes"]["POSITION"] for p in self.prims}) != 1:
            raise ValueError("la cara no comparte un único arreglo de vértices entre primitivas")
        self.names = self._names(self.mesh)
        self.pos = accessor(g, b, self.prims[0]["attributes"]["POSITION"]).astype(np.float64)
        self.uv = accessor(g, b, self.prims[0]["attributes"]["TEXCOORD_0"]).astype(np.float64)
        n = len(self.pos)
        self.zone = np.full(n, "", object)
        self.zone_tris, tris = {}, []
        for p in self.prims:
            mat = g["materials"][p["material"]]["name"]
            z = next((k for k in ZONES if k in mat), "other")
            t = accessor(g, b, p["indices"]).reshape(-1, 3).astype(np.int64)
            self.zone_tris.setdefault(z, []).append(t)
            tris.append(t)
            self.zone[np.unique(t)] = np.where(self.zone[np.unique(t)] == "", z, self.zone[np.unique(t)])
        self.tris = np.concatenate(tris)
        self.adj = [set() for _ in range(n)]
        for a, c, d in self.tris.tolist():
            self.adj[a] |= {c, d}; self.adj[c] |= {a, d}; self.adj[d] |= {a, c}

    @staticmethod
    def _names(mesh):
        return list((mesh.get("extras") or {}).get("targetNames")
                    or (mesh["primitives"][0].get("extras") or {}).get("targetNames") or [])

    def target(self, name):
        i = self.names.index(name)
        return accessor(self.g, self.b, self.prims[0]["targets"][i]["POSITION"]).astype(np.float64)

    def zone_data(self, z):
        tri = np.concatenate(self.zone_tris[z])
        ids = np.unique(tri)
        remap = np.full(len(self.pos), -1)
        remap[ids] = np.arange(len(ids))
        return {"ids": ids, "uv": self.uv[ids], "pos": self.pos[ids], "tri": remap[tri]}


# ─── correspondencia vértice a vértice ──────────────────────────────────────────
DIHEDRAL = [lambda p: p, lambda p: np.c_[1 - p[:, 0], p[:, 1]], lambda p: np.c_[p[:, 0], 1 - p[:, 1]],
            lambda p: 1 - p, lambda p: p[:, ::-1], lambda p: np.c_[1 - p[:, 1], p[:, 0]],
            lambda p: np.c_[p[:, 1], 1 - p[:, 0]], lambda p: 1 - p[:, ::-1]]


def _norm(a):
    return (a - a.min(0)) / np.maximum(np.ptp(a, 0), 1e-12)


def _tri_set(tri):
    return {tuple(sorted(t)) for t in tri.tolist()}


def _confirmed(perm, u, h_tris):
    good = np.zeros(len(perm), bool)
    for t in u["tri"].tolist():
        img = perm[t]
        if img.min() >= 0 and tuple(sorted(img)) in h_tris:
            good[t] = True
    vals, counts = np.unique(perm[good], return_counts=True)
    dup = set(vals[counts > 1].tolist())
    good &= np.array([p not in dup for p in perm])
    return good


def _affine(src, dst):
    coef, *_ = np.linalg.lstsq(np.c_[src, np.ones(len(src))], dst, rcond=None)
    return lambda x: np.c_[x, np.ones(len(x))] @ coef


def correspond(u, h, w_pos=0.35, rounds=6):
    """Devuelve (M, confirmado): M[i] = vértice local de h para el vértice local i de u."""
    h_tris = _tri_set(h["tri"])
    n, nh = len(u["uv"]), len(h["uv"])
    uv_h, pos_h = _norm(h["uv"]), _norm(h["pos"])
    best = None
    for T in DIHEDRAL:
        fu, fh = np.c_[T(_norm(u["uv"])), _norm(u["pos"]) * w_pos], np.c_[uv_h, pos_h * w_pos]
        perm = cKDTree(fh).query(fu)[1]
        s = _confirmed(perm, u, h_tris).mean()
        if best is None or s > best[0]:
            best = (s, T, perm)
    _, T, perm = best
    uv_u, pos_u = T(_norm(u["uv"])), _norm(u["pos"])
    fu, fh = np.c_[uv_u, pos_u * w_pos], np.c_[uv_h, pos_h * w_pos]
    for _ in range(rounds):
        s = np.where(_confirmed(perm, u, h_tris))[0]
        if len(s) < 12:
            break
        fuv, fpos = _affine(uv_u[s], uv_h[perm[s]]), _affine(pos_u[s], pos_h[perm[s]])
        fu = np.c_[fuv(uv_u), fpos(pos_u) * w_pos]
        perm = cKDTree(fh).query(fu)[1]
    # propagación por vecindad desde las semillas confirmadas
    seeds = _confirmed(perm, u, h_tris)
    M = np.full(n, -1)
    M[seeds] = perm[seeds]
    used = set(M[seeds].tolist())
    au, ah = [set() for _ in range(n)], [set() for _ in range(nh)]
    for a, c, d in u["tri"].tolist():
        au[a] |= {c, d}; au[c] |= {a, d}; au[d] |= {a, c}
    for a, c, d in h["tri"].tolist():
        ah[a] |= {c, d}; ah[c] |= {a, d}; ah[d] |= {a, c}
    changed = True
    while changed:
        changed = False
        for v in np.where(M < 0)[0]:
            nb = [M[w] for w in au[v] if M[w] >= 0]
            if len(nb) < 2:
                continue
            cand = set.intersection(*(ah[x] for x in nb)) - used
            if cand:
                c = min(cand, key=lambda c: float(np.linalg.norm(fh[c] - fu[v])))
                M[v] = c
                used.add(c)
                changed = True
    return M, _confirmed(M, u, h_tris) & (M >= 0)


# ─── transferencia ──────────────────────────────────────────────────────────────
def transfer_setup(user: Face, src: Face):
    """Pares (vértice usuario, vértice fuente) fiables y su mapa lineal local 3x3."""
    pairs = {}
    stats = {}
    for z in TRANSFER_ZONES:
        u, h = user.zone_data(z), src.zone_data(z)
        if len(u["ids"]) != len(h["ids"]):
            raise ValueError(f"zona {z}: {len(u['ids'])} vs {len(h['ids'])} vértices: no es la misma malla base")
        M, ok = correspond(u, h)
        # rechaza pares lejanos tras alinear con los pares confirmados
        s = np.where(ok)[0]
        f = _affine(u["pos"][s], h["pos"][M[s]])
        resid = np.linalg.norm(f(u["pos"][s]) - h["pos"][M[s]], axis=1)
        keep = s[resid <= max(3 * np.median(resid), 0.002)]
        for i in keep:
            pairs.setdefault(int(u["ids"][i]), []).append(int(h["ids"][M[i]]))
        stats[z] = {"vertices": int(len(u["ids"])), "confirmados": int(ok.sum()), "usados": int(len(keep))}
    uv = np.array(sorted(pairs))
    hv = np.array([pairs[v][0] for v in uv])
    # Escala local por vértice: proporción mediana de longitudes de aristas (vecindario de 2 anillos),
    # limitada y suavizada. Ambas caras comparten ejes (VRoid/UniVRM), así que no hace falta rotar:
    # un mapa 3x3 libre se condiciona mal en zonas estrechas (dientes, lengua) y amplifica.
    s0 = float(np.median(np.ptp(user.pos[uv], 0) / np.maximum(np.ptp(src.pos[hv], 0), 1e-9)))
    known = dict(zip(uv.tolist(), hv.tolist()))
    s = np.full(len(uv), s0)
    for k, v in enumerate(uv.tolist()):
        ring = set(user.adj[v])
        for w in list(ring):
            ring |= user.adj[w]
        ring = [w for w in ring if w != v and w in known]
        if len(ring) >= 3:
            lu = np.linalg.norm(user.pos[ring] - user.pos[v], axis=1)
            lh = np.linalg.norm(src.pos[[known[w] for w in ring]] - src.pos[known[v]], axis=1)
            ok = lh > 1e-6
            if ok.sum() >= 3:
                s[k] = np.median(lu[ok] / lh[ok])
    s = np.clip(s, 0.75 * s0, 1.35 * s0)
    pos_index = {v: k for k, v in enumerate(uv.tolist())}
    for _ in range(10):  # suavizado de la escala sobre la malla
        s = np.array([np.mean([s[pos_index[w]] for w in user.adj[v] if w in pos_index] + [s[k]])
                      for k, v in enumerate(uv.tolist())])
    A = s[:, None, None] * np.eye(3)[None]
    stats["escala_global"] = round(s0, 3)
    stats["escala_local_min_max"] = [round(float(s.min()), 3), round(float(s.max()), 3)]
    return uv, hv, A, stats


def front_sign(user: Face) -> float:
    """+1/-1: hacia dónde mira la cara en el eje Z (la punta de la nariz es lo más adelantado)."""
    skin = user.pos[(user.zone == "Face") & (np.abs(user.pos[:, 0]) < 0.004)]
    med = np.median(user.pos[user.zone == "Face", 2])
    return 1.0 if skin[:, 2].max() - med > med - skin[:, 2].min() else -1.0


def poking(user: Face, d, fwd: float, reach=0.002, tolerance=0.0003):
    """(vértices de FaceMouth, máscara de los que quedan delante de la piel, profundidad de la piel)."""
    skin = (user.zone == "Face")
    mouth = np.where(user.zone == "FaceMouth")[0]
    P = user.pos + d
    dist, idx = cKDTree(P[skin][:, :2]).query(P[mouth][:, :2], k=3)
    skin_z = P[skin][idx, 2].mean(1)
    ahead = (dist[:, 0] < reach) & (fwd * (P[mouth, 2] - skin_z) > -tolerance)
    return mouth, ahead, skin_z


def no_poke(user: Face, d, fwd: float, rest_ahead, margin=0.0008):
    """Que dientes y lengua (zona FaceMouth) no atraviesen la piel al deformarse: donde hay piel
    delante, el vértice se deja `margin` por detrás de ella. Los que ya están a ras en reposo
    (`rest_ahead`) no se tocan, para no crear saltos. Devuelve (d corregido, vértices corregidos)."""
    mouth, ahead, skin_z = poking(user, d, fwd)
    fix = ahead & ~rest_ahead
    d = d.copy()
    v = mouth[fix]
    d[v, 2] = (skin_z[fix] - fwd * margin) - user.pos[v, 2]
    return d, int(fix.sum())


def outliers(user: Face, d, thresh_mm=1.5):
    """Vértices que se mueven muy distinto de la media de sus vecinos (posible error de correspondencia)."""
    mag = np.linalg.norm(d, axis=1)
    bad = 0
    for v in np.where(mag > 1e-5)[0]:
        nb = list(user.adj[v])
        if nb:
            dev = np.linalg.norm(d[v] - d[nb].mean(0))
            if dev > thresh_mm / 1000 and dev > 0.5 * max(mag[v], np.linalg.norm(d[nb], axis=1).mean()):
                bad += 1
    return bad


def _diffusion(user: Face, uv):
    """Matriz dispersa que promedia los vecinos de cada vértice sin par fiable (zonas transferidas)."""
    from scipy.sparse import csr_matrix
    zone_ok = np.isin(user.zone, TRANSFER_ZONES)
    fixed = np.zeros(len(user.pos), bool)
    fixed[uv] = True
    todo = np.where(zone_ok & ~fixed)[0]
    rows, cols, vals = [], [], []
    for r, v in enumerate(todo.tolist()):
        nb = [w for w in user.adj[v] if zone_ok[w]] or [v]
        rows += [r] * len(nb)
        cols += nb
        vals += [1.0 / len(nb)] * len(nb)
    return zone_ok, todo, csr_matrix((vals, (rows, cols)), shape=(len(todo), len(user.pos)))


def transfer(user: Face, src: Face, setup, name: str, iters=400):
    uv, hv, A, _ = setup
    if not hasattr(user, "_diff"):
        user._diff = _diffusion(user, uv)
    zone_ok, todo, S = user._diff
    dh = src.target(name)
    d = np.zeros_like(user.pos)
    d[uv] = np.einsum("kij,kj->ki", A, dh[hv])
    for _ in range(iters):          # relleno por difusión (Jacobi) con los pares fiables fijos
        d[todo] = S @ d
    d[~zone_ok] = 0.0
    return d


# ─── formas propias (ojos y cejas) ──────────────────────────────────────────────
def side_weight(user: Face, left_sign: float, width=0.006):
    """Peso 0..1 del lado izquierdo, con transición suave de `width` m en el centro."""
    return np.clip(0.5 + left_sign * user.pos[:, 0] / (2 * width), 0.0, 1.0)[:, None]


def outer_brow_raise(user: Face, left_sign: float, lift=0.007):
    d = np.zeros_like(user.pos)
    brow = user.zone == "FaceBrow"
    out = {}
    for side, sgn in (("Left", left_sign), ("Right", -left_sign)):
        sel = brow & (np.sign(user.pos[:, 0]) == np.sign(sgn))
        ax = np.abs(user.pos[sel, 0])
        t = (ax - ax.min()) / max(np.ptp(ax), 1e-9)
        dd = d.copy()
        dd[sel, 1] = lift * (t * t * (3 - 2 * t))   # smoothstep: el extremo exterior sube más
        out[side] = dd
    return out


def build(user_path: Path, src_path: Path, out_path: Path):
    g, b = read_glb(user_path)
    sg, sb = read_glb(src_path)
    if "VRM" not in g.get("extensions", {}):
        raise ValueError("el avatar debe ser VRM 0.x (de VRoid); conviértelo a 1.0 después")
    user, src = Face(g, b), Face(sg, sb)
    present = [n for n in user.names if n in ARKIT]
    if present:
        raise ValueError(f"el avatar ya tiene formas ARKit: {present[:5]}…")

    # ¿qué lado es "Left"? el de Fcl_EYE_Close_L (como hinzka: EyeBlinkLeft = Fcl_EYE_Close_L)
    mag = np.linalg.norm(user.target("Fcl_EYE_Close_L"), axis=1)
    left_sign = float(np.sign((user.pos[:, 0] * mag).sum()))
    wl = side_weight(user, left_sign)

    setup = transfer_setup(user, src)
    new, report = {}, {"correspondencia": setup[3], "formas": {}}

    # 1) formas transferidas: todo lo que usan los clips ARKit de la fuente salvo ojos/cejas
    src_clips = {c["name"]: c for c in sg["extensions"]["VRM"]["blendShapeMaster"]["blendShapeGroups"]}
    wanted = set()
    for c in src_clips.values():
        base = c["name"][:1].lower() + c["name"][1:]
        if base in ARKIT and not any(base.startswith(o) for o in OWN):
            for bd in c.get("binds", []):
                tname = src.names[bd["index"]]
                if not tname.startswith("Fcl_"):
                    wanted.add(tname)
    fwd = front_sign(user)
    # dientes/lengua ya a ras de la piel en reposo: se respetan (no es cosa de las formas nuevas)
    _, rest_ahead, _ = poking(user, np.zeros_like(user.pos), fwd)
    base_poke = int(rest_ahead.sum())
    for tname in sorted(wanted):
        d = transfer(user, src, setup, tname)
        fixed = 0
        if tname != "tongueOut":     # la lengua fuera SÍ debe asomar
            d, fixed = no_poke(user, d, fwd, rest_ahead)
        new[tname] = d
        ds = np.linalg.norm(src.target(tname), axis=1).max()
        report["formas"][tname] = {"origen": "hinzka", "max_mm": round(float(np.linalg.norm(d, axis=1).max()) * 1000, 2),
                                   "max_fuente_mm": round(float(ds) * 1000, 2), "anomalos": outliers(user, d),
                                   "dientes_corregidos": fixed}
    report["asoman_en_reposo"] = base_poke

    # 2) formas propias (ojos y cejas)
    spread, angry = user.target("Fcl_EYE_Spread"), user.target("Fcl_BRW_Angry")
    own = {
        "eyeBlinkLeft": user.target("Fcl_EYE_Close_L"), "eyeBlinkRight": user.target("Fcl_EYE_Close_R"),
        "eyeSquintLeft": 0.5 * user.target("Fcl_EYE_Joy_L"), "eyeSquintRight": 0.5 * user.target("Fcl_EYE_Joy_R"),
        "eyeWideLeft": 0.5 * spread * wl, "eyeWideRight": 0.5 * spread * (1 - wl),
        "browDownLeft": angry * wl, "browDownRight": angry * (1 - wl),
        "browInnerUp": user.target("Fcl_BRW_Surprised"),
    }
    outer = outer_brow_raise(user, left_sign)
    own["browOuterUpLeft"], own["browOuterUpRight"] = outer["Left"], outer["Right"]
    # eyeLook*: SIN formas en la malla. La mirada la mueven los huesos de los ojos del VRM, y si la
    # malla tuviera formas llamadas eyeLook*, el add-on VRM las tomaría al pasar a VRM 1.0 y cambiaría
    # lookAt de "bone" a "expression": con formas neutras, los ojos dejarían de moverse.
    for k, d in own.items():
        new[k] = d
        report["formas"][k] = {"origen": "propia", "max_mm": round(float(np.linalg.norm(d, axis=1).max()) * 1000, 2)}

    # 3) escribir las formas en la malla de la cara (POSITION + NORMAL nula compartida)
    zero_normal = add_accessor(g, b, np.zeros((len(user.pos), 3)), with_minmax=False)
    index = {}
    for name, d in new.items():
        acc_i = add_accessor(g, b, d, with_minmax=True)
        for p in user.prims:
            p.setdefault("targets", []).append({"POSITION": acc_i, "NORMAL": zero_normal})
        index[name] = len(user.names)
        user.names.append(name)
    user.mesh.setdefault("extras", {})["targetNames"] = user.names
    for p in user.prims:
        if "extras" in p and "targetNames" in p["extras"]:
            p["extras"]["targetNames"] = user.names
    if "weights" in user.mesh:
        user.mesh["weights"] += [0.0] * len(new)
    g["buffers"][0]["byteLength"] = len(b)

    # 4) clips VRM 0.x con nombres ARKit en UpperCamel (convención perfect sync de VRoid)
    groups = g["extensions"]["VRM"]["blendShapeMaster"]["blendShapeGroups"]
    have = {grp["name"] for grp in groups}

    def bind(tname, w):
        return {"mesh": user.mesh_index, "index": index[tname] if tname in index else user.names.index(tname), "weight": w}

    for base in ARKIT:
        clip = base[:1].upper() + base[1:]
        if base.startswith("eyeLook"):
            binds = []          # clip vacío: la mirada va por huesos (ver arriba)
        elif any(base.startswith(o) for o in OWN):
            binds = [bind(base, 100)]
        else:
            sc = src_clips.get(clip)
            binds = [bind(src.names[bd["index"]], bd["weight"]) for bd in (sc or {}).get("binds", [])] or [bind(base, 100)]
            if base.startswith("noseSneer"):   # hinzka también baja la ceja al arrugar la nariz
                binds.append(bind("browDown" + base[len("noseSneer"):], 40))
        if clip in have:
            continue
        groups.append({"name": clip, "presetName": "unknown", "binds": binds, "materialValues": [], "isBinary": False})
    write_glb(out_path, g, b)
    report["lado_izquierdo_x"] = left_sign
    report["formas_nuevas"] = len(new)
    report["clips_arkit"] = sum(1 for grp in groups if grp["name"][:1].lower() + grp["name"][1:] in ARKIT)
    return report


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("avatar", type=Path)
    p.add_argument("salida", type=Path)
    p.add_argument("--source", type=Path, required=True, help="VRM de hinzka con las 52 formas (femenino o masculino)")
    p.add_argument("--report", type=Path)
    a = p.parse_args(argv)
    rep = build(a.avatar, a.source, a.salida)
    text = json.dumps(rep, ensure_ascii=False, indent=1)
    if a.report:
        a.report.write_text(text, encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
