"""Helpers for Factory asset build scripts (src/assets/<id>/build.py). Contract: forge/CONTRACT.md.

`blender_run.py` resets the scene, puts this module on sys.path, fills in the context below and runs the
asset's build.py, then calls finish() and exports the glb. An asset script only builds geometry and clips:

    import factory as F

    body = F.box('body', (1.0, 0.8, 0.9), (0, 0, 0.45), F.mat('crate', F.C['wood']))
    lid = F.box('lid', (1.04, 0.84, 0.08), (0, 0.42, 0.94), F.mat('lid', F.DOMAIN_COLOR))
    F.socket('socket_in', (0, -0.7, 1.0))
    idle = F.Clip('Idle', 4.0)
    idle.key(lid, 'rotation_euler', 0, (0, 0, 0)); ...

Axes are Blender's own: metres, Z up, and the FRONT (where traffic arrives) is -Y. The exporter writes +Y up,
so Blender -Y becomes three's +Z, which is the contract's front. The origin sits on the floor at the
footprint centre. Keep moving parts as separate, named objects; merge() the static ones.
"""
from __future__ import annotations

import hashlib
import math
import random

import bmesh
import bpy

FPS = 30
FRONT = (0.0, -1.0, 0.0)

# Filled in by blender_run.py before build.py runs.
ID: str = ''
MANIFEST: dict = {}
C: dict[str, str] = {}  # the floor palette, `C` in src/world/Props.tsx
DOMAINS: dict[str, str] = {}  # domain id -> colour, src/domains.ts
DOMAIN: str = ''  # the Factory domain this component stands in
DOMAIN_COLOR: str = '#2563EB'
SEED: int = 0
rng = random.Random(0)
EXPORT: dict = {}  # extra glTF exporter options an asset may set (e.g. {'export_texcoords': True} for an AO map)

_mats: dict[str, bpy.types.Material] = {}
_clips: list['Clip'] = []
_rest: dict[str, tuple] = {}


def _init(ctx: dict) -> None:
    global ID, MANIFEST, C, DOMAINS, DOMAIN, DOMAIN_COLOR, SEED, rng
    ID = ctx['id']
    MANIFEST = ctx['manifest']
    C = dict(ctx.get('palette') or {})
    DOMAINS = dict(ctx.get('domains') or {})
    DOMAIN = ctx.get('domain') or ''
    DOMAIN_COLOR = ctx.get('domain_color') or DOMAIN_COLOR
    SEED = int(hashlib.sha256(ID.encode()).hexdigest()[:8], 16)
    rng = random.Random(SEED)
    _mats.clear()
    _clips.clear()
    _rest.clear()
    EXPORT.clear()


def srgb_to_linear(c: float) -> float:
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def rgba(hex_color: str, alpha: float = 1.0) -> tuple[float, float, float, float]:
    """'#FFD84D' -> linear RGBA, the space Blender's colour inputs (and glTF factors) use. three reads it back as the same hex."""
    h = hex_color.lstrip('#')
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    return (srgb_to_linear(r), srgb_to_linear(g), srgb_to_linear(b), alpha)


def mat(name: str, color: str, rough: float = 0.65, metal: float = 0.0, emit: str | None = None, strength: float = 1.0, alpha: float = 1.0) -> bpy.types.Material:
    """A flat PBR material (cached by name). Contract: roughness 0.5-0.8 on the body, no image textures."""
    if name in _mats:
        return _mats[name]
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes.get('Principled BSDF')
    bsdf.inputs['Base Color'].default_value = rgba(color)
    bsdf.inputs['Roughness'].default_value = rough
    bsdf.inputs['Metallic'].default_value = metal
    if emit:
        bsdf.inputs['Emission Color'].default_value = rgba(emit)
        bsdf.inputs['Emission Strength'].default_value = strength
    if alpha < 1:
        bsdf.inputs['Alpha'].default_value = alpha
        try:
            m.surface_render_method = 'BLENDED'
        except AttributeError:
            m.blend_method = 'BLEND'
    _mats[name] = m
    return m


def _link(obj: bpy.types.Object, parent: bpy.types.Object | None) -> bpy.types.Object:
    bpy.context.scene.collection.objects.link(obj)
    if parent is not None:
        obj.parent = parent
    return obj


def _finish_mesh(name: str, bm: bmesh.types.BMesh, loc, rot, material, parent, smooth: bool) -> bpy.types.Object:
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    if material is not None:
        me.materials.append(material)
    obj = _link(bpy.data.objects.new(name, me), parent)
    obj.location = loc
    obj.rotation_euler = rot
    if smooth:
        # bevelled hard surface: smooth shading with face-area weighted normals keeps big faces flat
        me.shade_smooth()
        wn = obj.modifiers.new('weighted', 'WEIGHTED_NORMAL')
        wn.mode = 'FACE_AREA'
        wn.weight = 100
        wn.keep_sharp = True
    return obj


def box(name: str, size, loc=(0, 0, 0), material=None, bevel: float = 0.04, segments: int = 2, rot=(0, 0, 0), parent=None) -> bpy.types.Object:
    """A bevelled box centred on `loc` (size in metres, Blender axes)."""
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co.x *= size[0]
        v.co.y *= size[1]
        v.co.z *= size[2]
    b = min(bevel, min(size) * 0.45)
    if b > 0:
        bmesh.ops.bevel(bm, geom=list(bm.edges), offset=b, segments=segments, profile=0.5, affect='EDGES', clamp_overlap=True)
    return _finish_mesh(name, bm, loc, rot, material, parent, smooth=b > 0)


def cyl(name: str, radius: float, depth: float, loc=(0, 0, 0), material=None, verts: int = 24, bevel: float = 0.02, rot=(0, 0, 0), parent=None, radius_top: float | None = None) -> bpy.types.Object:
    """A cylinder (or a cone with radius_top) standing on Z, centred on `loc`, with bevelled rims."""
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=verts, radius1=radius, radius2=radius if radius_top is None else radius_top, depth=depth)
    b = min(bevel, depth * 0.4, radius * 0.4)
    if b > 0:
        rims = [e for e in bm.edges if all(abs(abs(v.co.z) - depth / 2) < 1e-5 for v in e.verts) and len(e.link_faces) == 2 and abs(e.link_faces[0].normal.z - e.link_faces[1].normal.z) > 0.5]
        bmesh.ops.bevel(bm, geom=rims, offset=b, segments=2, profile=0.5, affect='EDGES', clamp_overlap=True)
    return _finish_mesh(name, bm, loc, rot, material, parent, smooth=True)


def sphere(name: str, radius: float, loc=(0, 0, 0), material=None, segments: int = 16, rings: int = 10, parent=None) -> bpy.types.Object:
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=segments, v_segments=rings, radius=radius)
    obj = _finish_mesh(name, bm, loc, (0, 0, 0), material, parent, smooth=False)
    obj.data.shade_smooth()
    return obj


def empty(name: str, loc=(0, 0, 0), parent=None, rot=(0, 0, 0)) -> bpy.types.Object:
    """A named pivot: parent moving parts to it to animate them about a hinge."""
    obj = _link(bpy.data.objects.new(name, None), parent)
    obj.empty_display_type = 'PLAIN_AXES'
    obj.empty_display_size = 0.1
    obj.location = loc
    obj.rotation_euler = rot
    return obj


def socket(name: str, loc=(0, 0, 0), parent=None) -> bpy.types.Object:
    """One of the three traffic sockets (socket_in / socket_hold / socket_out): an empty, exported as a named node."""
    if not name.startswith('socket_'):
        raise ValueError(f'socket names start with socket_: {name}')
    return empty(name, loc, parent)


def merge(objs, name: str) -> bpy.types.Object:
    """Join static parts into one mesh (one draw call). Modifiers are applied first, materials kept."""
    objs = [o for o in objs if o is not None and o.type == 'MESH']
    if not objs:
        raise ValueError('merge: nothing to merge')
    dg = bpy.context.evaluated_depsgraph_get()
    for o in objs:
        if o.modifiers:
            me = bpy.data.meshes.new_from_object(o.evaluated_get(dg), preserve_all_data_layers=True, depsgraph=dg)
            o.modifiers.clear()
            o.data = me
    target = objs[0]
    with bpy.context.temp_override(active_object=target, object=target, selected_objects=objs, selected_editable_objects=objs):
        bpy.ops.object.join()
    target.name = name
    target.data.name = name
    return target


class Clip:
    """One glTF animation (Idle / Accept / Work / Emit). Key any object's location / rotation_euler / scale at times in
    seconds; every object keyed in a clip becomes a channel of the same named animation."""

    def __init__(self, name: str, seconds: float):
        self.name = name
        self.seconds = seconds
        self.action = bpy.data.actions.new(name)
        self.action.use_fake_user = True
        self.objs: list[bpy.types.Object] = []
        _clips.append(self)

    def key(self, obj: bpy.types.Object, path: str, t: float, value, interp: str = 'BEZIER') -> 'Clip':
        if obj.name not in _rest:
            _rest[obj.name] = (tuple(obj.location), tuple(obj.rotation_euler), tuple(obj.scale))
        ad = obj.animation_data_create()
        if ad.action is not self.action:
            ad.action = self.action
        if obj not in self.objs:
            self.objs.append(obj)
        bpy.context.preferences.edit.keyframe_new_interpolation_type = interp
        setattr(obj, path, value)
        obj.keyframe_insert(data_path=path, frame=round(t * FPS))
        return self

    def hold(self, obj: bpy.types.Object, path: str, value, interp: str = 'LINEAR') -> 'Clip':
        """The same value at the first and last frame: keeps a part still for the whole clip."""
        return self.key(obj, path, 0, value, interp).key(obj, path, self.seconds, value, interp)


def finish() -> None:
    """Stash each clip on its objects as NLA tracks (so the exporter writes one animation per clip) and restore the rest pose."""
    for clip in _clips:
        for obj in clip.objs:
            ad = obj.animation_data
            slot = ad.action_slot if ad.action is clip.action else None
            if ad.action is not clip.action:
                ad.action = clip.action
                slot = ad.action_slot
            track = ad.nla_tracks.new()
            track.name = clip.name
            strip = track.strips.new(clip.name, 0, clip.action)
            if slot is not None:
                try:
                    strip.action_slot = slot
                except Exception:  # older Blender: no slots
                    pass
            track.mute = True
            ad.action = None
    for name, (loc, rot, scale) in _rest.items():
        obj = bpy.data.objects[name]
        obj.location = loc
        obj.rotation_euler = rot
        obj.scale = scale
    bpy.context.scene.frame_set(0)


def ease_loop(t: float, period: float) -> float:
    """0..1..0 over one period: handy for breathing lights and seamless idle loops."""
    return 0.5 - 0.5 * math.cos(2 * math.pi * t / period)
