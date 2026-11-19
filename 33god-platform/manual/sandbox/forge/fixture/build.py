# The pipeline fixture: a bevelled crate with a hinged lid, a stamp and a lamp. It proves the asset pipeline
# (build -> glb -> runtime -> forge hook) and is mounted only with ?fixture (dev or forge). Not a component.
import math

import factory as F

wood = F.mat('crate', F.C['wood'], rough=0.75)
steel = F.mat('steel', F.C['steel'], rough=0.5, metal=0.3)
lid_m = F.mat('lid', F.DOMAIN_COLOR, rough=0.6)
lamp_m = F.mat('lamp', '#FBBF24', rough=0.5, emit='#F59E0B', strength=2.0)

# static body: crate, two steel bands, four feet (merged into one mesh)
parts = [F.box('body', (0.9, 0.8, 0.66), (0, 0, 0.37), wood, bevel=0.05)]
for z in (0.2, 0.55):
    parts.append(F.box(f'band{z}', (0.92, 0.82, 0.06), (0, 0, z), steel, bevel=0.015))
for x in (-0.36, 0.36):
    for y in (-0.31, 0.31):
        parts.append(F.box(f'foot{x}{y}', (0.12, 0.12, 0.05), (x, y, 0.025), steel, bevel=0.015))
F.merge(parts, 'crate')

# the lid swings on a hinge along the back top edge (front is -Y)
hinge = F.empty('lid_hinge', (0, 0.4, 0.7))
F.box('lid', (0.96, 0.86, 0.08), (0, -0.42, 0.04), lid_m, bevel=0.03, parent=hinge)
stamp = F.cyl('stamp', 0.09, 0.22, (0.27, 0.05, 0.98), steel, verts=16)
lamp = F.sphere('lamp', 0.07, (-0.3, 0.2, 1.17), lamp_m)
F.cyl('lamp_post', 0.025, 0.36, (-0.3, 0.2, 0.96), steel, verts=8, bevel=0)

# the sockets: catch at the front, hold inside the crate, leave over the front lip
CATCH, HOLD, OUT = (0, -0.75, 0.95), (0, 0, 0.5), (0, -0.85, 1.05)
s_in = F.socket('socket_in', CATCH)
s_hold = F.socket('socket_hold', HOLD)
s_out = F.socket('socket_out', OUT)
OPEN, SHUT = (-1.9, 0, 0), (0, 0, 0)

idle = F.Clip('Idle', 4.0)  # the lamp breathes, the lid rattles once: alive, never still
for t, k in ((0, 1.0), (1, 1.25), (2, 1.0), (3, 1.25), (4, 1.0)):
    idle.key(lamp, 'scale', t, (k, k, k))
for t, a in ((0, 0.0), (2.6, 0.0), (2.75, -0.06), (2.9, 0.0), (4, 0.0)):
    idle.key(hinge, 'rotation_euler', t, (a, 0, 0))

acc = F.Clip('Accept', 1.0)  # lid opens, the item is caught at the front and lowered in, lid shuts
acc.key(hinge, 'rotation_euler', 0, SHUT).key(hinge, 'rotation_euler', 0.3, OPEN).key(hinge, 'rotation_euler', 0.8, OPEN).key(hinge, 'rotation_euler', 1.0, SHUT)
acc.key(s_in, 'location', 0, CATCH).key(s_in, 'location', 0.45, (0, -0.1, 1.15)).key(s_in, 'location', 0.8, HOLD).key(s_in, 'location', 1.0, HOLD)

work = F.Clip('Work', 1.6)  # the stamp comes down twice; the lid jumps under it; the lamp flashes
for t, z in ((0, 0.98), (0.3, 0.86), (0.45, 0.98), (1.1, 0.86), (1.25, 0.98), (1.6, 0.98)):
    work.key(stamp, 'location', t, (0.27, 0.05, z))
for t, a in ((0, 0.0), (0.3, 0.0), (0.38, -0.08), (0.5, 0.0), (1.1, 0.0), (1.18, -0.08), (1.3, 0.0), (1.6, 0.0)):
    work.key(hinge, 'rotation_euler', t, (a, 0, 0))
for t, k in ((0, 1.0), (0.3, 1.5), (0.6, 1.0), (1.1, 1.5), (1.4, 1.0), (1.6, 1.0)):
    work.key(lamp, 'scale', t, (k, k, k))
work.hold(s_hold, 'location', HOLD)

emit = F.Clip('Emit', 0.8)  # lid flips open, the result pops out over the front lip, lid settles shut
emit.key(hinge, 'rotation_euler', 0, SHUT).key(hinge, 'rotation_euler', 0.2, OPEN).key(hinge, 'rotation_euler', 0.55, OPEN).key(hinge, 'rotation_euler', 0.8, SHUT)
emit.key(s_out, 'location', 0, HOLD).key(s_out, 'location', 0.25, (0, -0.2, 1.3)).key(s_out, 'location', 0.45, OUT).key(s_out, 'location', 0.8, OUT)
emit.key(lamp, 'scale', 0, (1, 1, 1)).key(lamp, 'scale', 0.8, (1, 1, 1))
