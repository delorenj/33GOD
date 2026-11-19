#!/usr/bin/env python3
"""Independent glb validator for Factory assets (CONTRACT sections 2-4). Stdlib only.

    glbcheck.py <model.glb> [--asset asset.json] [--json]

Reads the glb header, the JSON chunk and the BIN chunk itself, so it does not trust the exporter, the
agent or the runtime. With --asset it checks the file against the manifest: the four clips and their
lengths, the three sockets, the triangle and size budget, the footprint and height, the origin on the
floor, a seamless Idle, and no texture larger than 512 px. Exit 0 when every check passes.
"""
from __future__ import annotations

import argparse
import json
import math
import struct
import sys
from pathlib import Path

CLIP_LEN = {"idle": (2.0, 6.0), "accept": (0.6, 1.5), "work": (0.8, 3.0), "emit": (0.5, 1.2)}  # CONTRACT section 4
KIOSK_SLOT = (1.4, 1.3)
TOL = 1.25            # footprint / height may exceed the manifest by 25% before it is a fault
SEAM_EPS = 1e-3       # Idle's first and last key must match this closely, or it pops on loop
COMPONENTS = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT4": 16}
CT_FMT = {5120: "b", 5121: "B", 5122: "h", 5123: "H", 5125: "I", 5126: "f"}


class Glb:
    def __init__(self, path: Path):
        data = Path(path).read_bytes()
        self.size = len(data)
        if len(data) < 20 or data[:4] != b"glTF":
            raise ValueError("not a glb (bad magic)")
        version, length = struct.unpack_from("<II", data, 4)
        if version != 2:
            raise ValueError(f"glb version {version}, want 2")
        if length != len(data):
            raise ValueError(f"glb header length {length} != file size {len(data)}")
        off, self.json, self.bin = 12, None, b""
        while off + 8 <= len(data):
            clen, ctype = struct.unpack_from("<II", data, off)
            body = data[off + 8: off + 8 + clen]
            if ctype == 0x4E4F534A:
                self.json = json.loads(body.decode("utf-8"))
            elif ctype == 0x004E4942 and not self.bin:
                self.bin = body
            off += 8 + clen
        if self.json is None:
            raise ValueError("glb has no JSON chunk")
        self.g = self.json

    # accessors ------------------------------------------------------------------------------------
    def accessor(self, i: int) -> list[tuple]:
        a = self.g["accessors"][i]
        if "sparse" in a:
            raise ValueError("sparse accessors are not supported by this validator")
        n, nc = a["count"], COMPONENTS[a["type"]]
        fmt = CT_FMT[a["componentType"]]
        size = struct.calcsize(fmt)
        if "bufferView" not in a:
            return [tuple([0] * nc) for _ in range(n)]
        bv = self.g["bufferViews"][a["bufferView"]]
        base = bv.get("byteOffset", 0) + a.get("byteOffset", 0)
        stride = bv.get("byteStride") or size * nc
        out = []
        for k in range(n):
            out.append(struct.unpack_from("<" + fmt * nc, self.bin, base + k * stride))
        return out


def _mat(t, r, s):
    x, y, z, w = r
    xx, yy, zz, xy, xz, yz, wx, wy, wz = x*x, y*y, z*z, x*y, x*z, y*z, w*x, w*y, w*z
    return [
        [(1 - 2*(yy + zz))*s[0], (2*(xy - wz))*s[1], (2*(xz + wy))*s[2], t[0]],
        [(2*(xy + wz))*s[0], (1 - 2*(xx + zz))*s[1], (2*(yz - wx))*s[2], t[1]],
        [(2*(xz - wy))*s[0], (2*(yz + wx))*s[1], (1 - 2*(xx + yy))*s[2], t[2]],
        [0, 0, 0, 1],
    ]


def _mul(a, b):
    return [[sum(a[i][k] * b[k][j] for k in range(4)) for j in range(4)] for i in range(4)]


def _local(node):
    if "matrix" in node:
        m = node["matrix"]  # column-major
        return [[m[c * 4 + r] for c in range(4)] for r in range(4)]
    return _mat(node.get("translation", [0, 0, 0]), node.get("rotation", [0, 0, 0, 1]), node.get("scale", [1, 1, 1]))


def walk(g):
    """Yield (node index, node, world matrix) for every node in the default scene."""
    nodes = g.get("nodes", [])
    scenes = g.get("scenes", [])
    roots = scenes[g.get("scene", 0)].get("nodes", []) if scenes else []
    ident = [[1 if i == j else 0 for j in range(4)] for i in range(4)]
    stack = [(r, ident) for r in roots]
    while stack:
        i, parent = stack.pop()
        node = nodes[i]
        world = _mul(parent, _local(node))
        yield i, node, world
        for c in node.get("children", []):
            stack.append((c, world))


def stats(glb: Glb) -> dict:
    g = glb.g
    tris, lo, hi = 0, [math.inf] * 3, [-math.inf] * 3
    for _, node, world in walk(g):
        if "mesh" not in node:
            continue
        for p in g["meshes"][node["mesh"]]["primitives"]:
            if p.get("mode", 4) != 4:
                continue
            pos = g["accessors"][p["attributes"]["POSITION"]]
            tris += (g["accessors"][p["indices"]]["count"] if "indices" in p else pos["count"]) // 3
            mn, mx = pos.get("min"), pos.get("max")
            if not mn or not mx:
                continue
            for cx in (mn[0], mx[0]):
                for cy in (mn[1], mx[1]):
                    for cz in (mn[2], mx[2]):
                        v = [sum(world[r][c] * q for c, q in enumerate((cx, cy, cz, 1))) for r in range(3)]
                        for k in range(3):
                            lo[k], hi[k] = min(lo[k], v[k]), max(hi[k], v[k])
    return {"tris": tris, "min": lo, "max": hi,
            "size": [hi[k] - lo[k] for k in range(3)] if tris else [0, 0, 0],
            "kb": round(glb.size / 1024, 1)}


def clips(glb: Glb) -> dict:
    """name -> {duration, seam (max |first - last| over every channel), channels}"""
    g, out = glb.g, {}
    for anim in g.get("animations", []):
        dur, seam, ch = 0.0, 0.0, 0
        for c in anim.get("channels", []):
            s = anim["samplers"][c["sampler"]]
            tin = g["accessors"][s["input"]]
            dur = max(dur, (tin.get("max") or [0])[0])
            vals = glb.accessor(s["output"])
            if s.get("interpolation") == "CUBICSPLINE":
                vals = vals[1::3]
            if len(vals) < 2:
                continue
            a, b = vals[0], vals[-1]
            if c["target"].get("path") == "rotation":   # q and -q are the same turn
                if sum(x * y for x, y in zip(a, b)) < 0:
                    b = tuple(-x for x in b)
            seam = max(seam, max(abs(x - y) for x, y in zip(a, b)))
            ch += 1
        out[anim.get("name", "")] = {"duration": round(dur, 3), "seam": round(seam, 5), "channels": ch}
    return out


def _png_wh(data: bytes):
    return struct.unpack(">II", data[16:24]) if data[:8] == b"\x89PNG\r\n\x1a\n" else None


def check(path: Path, asset: dict | None = None) -> list[tuple[str, bool, str]]:
    res: list[tuple[str, bool, str]] = []
    ok = lambda n, c, d="": res.append((n, bool(c), d))   # noqa: E731
    try:
        glb = Glb(path)
    except Exception as e:  # noqa: BLE001
        return [("glb-parse", False, str(e))]
    g = glb.g
    ok("glb-parse", True, f"{glb.size / 1024:.1f} KB")
    st, cl = stats(glb), clips(glb)
    names = {n.get("name") for n in g.get("nodes", [])}
    ok("glb-has-geometry", st["tris"] > 0, f"{st['tris']} tris")
    if not asset:
        return res
    b = asset.get("budget", {})
    ok("glb-tris", st["tris"] <= min(b.get("tris", 15000), 15000), f"{st['tris']} <= {min(b.get('tris', 15000), 15000)}")
    ok("glb-size", st["kb"] <= min(b.get("glbKB", 600), 600), f"{st['kb']} KB <= {min(b.get('glbKB', 600), 600)}")
    want = asset.get("clips", {})
    for key, (lo, hi) in CLIP_LEN.items():
        nm = want.get(key)
        c = cl.get(nm)
        if c is None:
            ok(f"clip-{key}", False, f"animation {nm!r} missing (have {sorted(cl)})")
            continue
        ok(f"clip-{key}", lo <= c["duration"] <= hi and c["channels"] > 0, f"{c['duration']} s, {c['channels']} channels, want {lo}-{hi} s")
    idle = cl.get(want.get("idle"))
    if idle:
        ok("idle-seamless", idle["seam"] <= SEAM_EPS, f"first/last key differ by {idle['seam']} (max {SEAM_EPS})")
    for key, nm in asset.get("sockets", {}).items():
        ok(f"socket-{key}", nm in names, f"node {nm!r}")
    for key in ("in", "hold", "out"):
        ok(f"socket-{key}-declared", key in asset.get("sockets", {}))
    if st["tris"]:
        fx, fz = asset.get("footprint", [0, 0])
        sc = asset.get("scale", 1) or 1
        sx, sy, sz = st["size"]
        ok("fits-footprint", sx <= fx * TOL and sz <= fz * TOL, f"model {sx:.2f} x {sz:.2f} m vs footprint {fx} x {fz}")
        ok("fits-height", sy <= asset.get("height", 0) * TOL, f"model {sy:.2f} m vs height {asset.get('height')}")
        ok("origin-on-floor", abs(st["min"][1]) <= 0.1, f"lowest point y = {st['min'][1]:.3f}")
        cx, cz = (st["min"][0] + st["max"][0]) / 2, (st["min"][2] + st["max"][2]) / 2
        ok("origin-centred", abs(cx) <= max(0.25 * fx, 0.15) and abs(cz) <= max(0.25 * fz, 0.15), f"centre ({cx:.2f}, {cz:.2f})")
        if asset.get("placement") == "kiosk":
            ok("kiosk-slot", fx <= KIOSK_SLOT[0] and fz <= KIOSK_SLOT[1], f"footprint {fx} x {fz} vs slot {KIOSK_SLOT[0]} x {KIOSK_SLOT[1]}")
    big = []
    for im in g.get("images", []):
        if "bufferView" in im:
            bv = g["bufferViews"][im["bufferView"]]
            wh = _png_wh(glb.bin[bv.get("byteOffset", 0): bv.get("byteOffset", 0) + 32])
            if wh is None or max(wh) > 512:
                big.append(wh or "non-png")
        else:
            big.append("external uri")
    ok("textures-small", not big, f"{len(g.get('images', []))} image(s), offenders: {big}" if big else f"{len(g.get('images', []))} image(s)")
    return res


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("glb")
    ap.add_argument("--asset", help="asset.json to check against")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    asset = json.loads(Path(a.asset).read_text()) if a.asset else None
    res = check(Path(a.glb), asset)
    if a.json:
        print(json.dumps([{"name": n, "ok": o, "detail": d} for n, o, d in res], indent=1))
    else:
        for n, o, d in res:
            print(("ok   " if o else "FAIL ") + n + (f"  {d}" if d else ""))
    return 0 if all(o for _, o, _ in res) else 1


if __name__ == "__main__":
    sys.exit(main())
