"""Headless Blender harness for one Factory asset. Run by tools/assets/build.mjs:

    blender -b --factory-startup --python-exit-code 1 -P tools/assets/blender_run.py -- --ctx <ctx.json>

ctx.json: {id, build_py, out, manifest, palette, domains, domain, domain_color}. The harness empties the scene,
makes `import factory` work for the asset script, runs its build.py, stashes the clips, exports the glb with
every clip as a named animation, and prints one line `FACTORY_RESULT {json}`.
"""
import json
import os
import runpy
import sys
import traceback

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import factory  # noqa: E402


def main() -> int:
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    if len(argv) != 2 or argv[0] != '--ctx':
        print('usage: blender ... -P blender_run.py -- --ctx <ctx.json>', file=sys.stderr)
        return 2
    with open(argv[1]) as f:
        ctx = json.load(f)

    # an empty, deterministic scene: no default cube, camera or light; 30 fps, frame 0
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.fps = factory.FPS
    scene.frame_start = 0
    scene.frame_set(0)
    factory._init(ctx)

    build_py = ctx['build_py']
    sys.path.insert(0, os.path.dirname(build_py))
    runpy.run_path(build_py, run_name='__main__')
    factory.finish()

    out = ctx['out']
    os.makedirs(os.path.dirname(out), exist_ok=True)
    opts = dict(
        filepath=out,
        export_format='GLB',
        export_yup=True,
        export_apply=True,
        export_animations=True,
        export_animation_mode='NLA_TRACKS',
        export_force_sampling=True,
        export_optimize_animation_size=True,
        export_anim_slide_to_zero=True,
        export_frame_range=False,
        export_cameras=False,
        export_lights=False,
        export_extras=False,
        export_materials='EXPORT',
        export_texcoords=False,
        export_normals=True,
        export_tangents=False,
    )
    opts.update(factory.EXPORT)
    bpy.ops.export_scene.gltf(**opts)
    print('FACTORY_RESULT ' + json.dumps({'id': factory.ID, 'out': out, 'clips': [c.name for c in factory._clips], 'objects': len(bpy.data.objects)}))
    return 0


if __name__ == '__main__':
    try:
        code = main()
    except Exception:
        traceback.print_exc()
        code = 1
    if code:
        sys.exit(code)
