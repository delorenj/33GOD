# hook-hub: the receiving dock. Blender (bpy) build for the Factory asset contract (forge/CONTRACT.md).
# Deterministic: no randomness, no timestamps. Blender axes: metres, Z up, FRONT (the receiving door) is -Y,
# the back slot (post-its out, toward the belt) is +Y, the open cutaway side is +X. See NOTES.md.
import math

import factory as F

PI = math.pi
TAU = 2 * PI


def M(name, color, rough=0.65, **kw):
    return F.mat(name, color, rough=rough, **kw)


orange = M('dock', F.C['dock'], 0.6)
blue = M('bloodbank', F.DOMAIN_COLOR, 0.55)
concrete = M('concrete', '#A39C8F', 0.8)
hz_y = M('hazard_yellow', '#F2C230', 0.6)
hz_k = M('hazard_black', '#2A2418', 0.7)
steel = M('steel', F.C['steel'], 0.5, metal=0.3)
steel_dk = M('steel_dark', '#3A4250', 0.55, metal=0.2)
wood = M('wood', F.C['wood'], 0.75)
wood_dk = M('bench_body', '#7A5236', 0.75)
rubber = M('rubber', '#1F1D1A', 0.8)
board = M('board', '#24324A', 0.7)
post_m = M('post', F.C['post'], 0.7)
post_edge = M('post_edge', '#E6C34A', 0.7)
parcel_m = M('parcel', F.C['parcel'], 0.8)
tape = M('tape', '#D97757', 0.7)
paper = M('paper', '#F4EFE6', 0.7)
uniform = M('uniform', F.C['uniform'], 0.7)
skin = M('skin', F.C['skin'], 0.8)
curtain = M('curtain', '#A9BFCC', 0.5)
purple = M('memory', F.DOMAINS.get('memory', '#7C4DBA'), 0.6)
purple_dk = M('memory_dark', '#4C2D7A', 0.6)
amber = M('alert', '#F59E0B', 0.6)
red = M('guard', F.C['clock'], 0.6)
grey = M('card_off', '#8A8F98', 0.75)
dark = M('dark', '#2B2118', 0.7)
printer_m = M('printer', '#C7CCD3', 0.55)
lens = M('lens', '#E08A1E', 0.3)
lamp_green = M('lamp_green', '#22C55E', 0.5, emit='#22C55E', strength=3.0)
lamp_amber = M('lamp_amber', '#FBBF24', 0.5, emit='#F59E0B', strength=6.0)
beam_m = M('beam', '#EF4444', 0.5, emit='#EF4444', strength=4.0)

S = []  # static parts, merged into one mesh at the end


def b(name, size, loc, m, bevel=0.02, seg=1, rot=(0, 0, 0)):
    o = F.box(name, size, loc, m, bevel=bevel, segments=seg, rot=rot)
    S.append(o)
    return o


def c(name, r, depth, loc, m, verts=16, bevel=0.01, rot=(0, 0, 0), top=None):
    o = F.cyl(name, r, depth, loc, m, verts=verts, bevel=bevel, rot=rot, radius_top=top)
    S.append(o)
    return o


ANIM = []   # every animated object: keyed in all four clips
REST = {}


def anim(o):
    ANIM.append(o)
    REST[o.name] = {'location': tuple(o.location), 'rotation_euler': tuple(o.rotation_euler), 'scale': tuple(o.scale)}
    return o


# ------------------------------------------------------------------ platform: concrete, hazard lip, bumpers
b('platform', (3.7, 3.9, 0.3), (0, 0, 0.15), concrete, 0.03)
b('lip_x', (0.02, 3.86, 0.14), (1.86, 0, 0.17), hz_y, 0)
for i in range(13):
    b(f'lip_x{i}', (0.026, 0.14, 0.14), (1.865, -1.8 + i * 0.3, 0.17), hz_k, 0)
b('lip_y', (3.66, 0.02, 0.14), (0, -1.96, 0.17), hz_y, 0)
for i in range(12):
    b(f'lip_y{i}', (0.14, 0.026, 0.14), (-1.7 + i * 0.3, -1.965, 0.17), hz_k, 0)
for x in (-0.55, 1.05):
    b(f'bumper{x}', (0.28, 0.12, 0.22), (x, -2.01, 0.16), rubber, 0.03)

# ------------------------------------------------------------------ walls (z 0.3 - 3.05)
H, ZC = 2.75, 1.675
b('wall_n', (0.2, 3.9, H), (-1.75, 0, ZC), orange)
# front wall: driver's window (x -1.4..-0.8, z 1.1..1.6) and the receiving door (x -0.25..0.75, up to z 2.1)
b('wall_f1', (0.25, 0.2, H), (-1.525, -1.85, ZC), orange)
b('wall_f2', (0.6, 0.2, 0.8), (-1.1, -1.85, 0.7), orange)
b('wall_f3', (0.6, 0.2, 1.45), (-1.1, -1.85, 2.325), orange)
b('wall_f4', (0.55, 0.2, H), (-0.525, -1.85, ZC), orange)
b('wall_f5', (1.0, 0.2, 0.95), (0.25, -1.85, 2.575), orange)
# beside the door the wall drops to a knee wall under a lintel: the open side sees the curtain and the rollers
b('wall_f6', (0.8, 0.2, 0.7), (1.15, -1.85, 0.65), orange)
b('wall_f7', (0.8, 0.2, 0.95), (1.15, -1.85, 2.575), orange)
b('knee_cap', (0.86, 0.26, 0.05), (1.18, -1.85, 1.02), blue)
# back wall: the letterbox slot to the belt (x -0.08..0.58, z 1.0..1.5)
b('wall_b1', (1.57, 0.2, H), (-0.865, 1.85, ZC), orange)
b('wall_b2', (0.66, 0.2, 0.7), (0.25, 1.85, 0.65), orange)
b('wall_b3', (0.66, 0.2, 1.55), (0.25, 1.85, 2.275), orange)
b('wall_b4', (0.97, 0.2, H), (1.065, 1.85, ZC), orange)
# Bloodbank-blue copings, corner posts, door jambs, window head
b('cope_n', (0.3, 4.0, 0.1), (-1.75, 0, 3.1), blue)
b('cope_f', (3.3, 0.3, 0.1), (-0.05, -1.85, 3.1), blue)
b('cope_b', (3.3, 0.3, 0.1), (-0.05, 1.85, 3.1), blue)
c('corner_back', 0.08, 2.85, (1.62, 1.85, 1.725), blue, verts=12)   # the front corner is the sign rail's post
for x in (-0.28, 0.78):
    b(f'jamb{x}', (0.06, 0.26, 1.8), (x, -1.85, 1.2), blue)
b('window_head', (0.66, 0.26, 0.05), (-1.1, -1.85, 1.625), blue)
b('slot_head', (0.72, 0.05, 0.05), (0.25, 1.975, 1.53), blue)
b('slot_sill', (0.72, 0.05, 0.05), (0.25, 1.975, 0.975), blue)
# the sign rail: the floor's RECEIVING sign (Props.tsx SIGNS.dock) hangs just in front of it
for y in (-1.72, 1.72):
    c(f'rail_post{y}', 0.05, 2.62, (2.0, y, 1.31), blue, verts=12)
    b(f'rail_stub{y}', (0.48, 0.08, 0.08), (1.76, y, 2.6), blue)
b('sign_rail', (0.1, 3.54, 0.12), (2.0, 0, 2.6), blue)
# the dock canopy over the receiving door, with two braces
b('canopy', (1.6, 0.5, 0.08), (0.25, -2.15, 2.62), blue, 0.02)
for x in (-0.45, 0.95):
    c(f'brace{x}', 0.03, 0.57, (x, -2.15, 2.4), steel, verts=8, bevel=0, rot=(PI / 4, 0, 0))
# driver's window: sill outside, counter inside; the stopwatch above it; the green OPEN lamp by the door
b('sill', (0.7, 0.3, 0.05), (-1.1, -2.0, 1.085), wood)
b('counter', (0.7, 0.3, 0.05), (-1.1, -1.62, 1.085), wood)
c('watch_rim', 0.135, 0.02, (-1.1, -1.962, 1.88), dark, verts=20, rot=(PI / 2, 0, 0))
c('watch_face', 0.12, 0.02, (-1.1, -1.975, 1.88), paper, verts=20, rot=(PI / 2, 0, 0))
c('watch_crown', 0.025, 0.06, (-1.1, -1.975, 2.03), dark, verts=8, bevel=0)
b('lamp_housing', (0.2, 0.08, 0.2), (1.12, -1.98, 2.35), dark, 0.02)

# ------------------------------------------------------------------ incoming roller conveyor (the courier's conveyor ends here)
CX = 0.25
for dx in (-0.31, 0.31):
    b(f'rail{dx}', (0.06, 1.47, 0.1), (CX + dx, -1.465, 0.9), blue)
    b(f'leg_out{dx}', (0.05, 0.05, 0.86), (CX + dx, -2.1, 0.43), steel, 0.01)
    b(f'leg_in{dx}', (0.05, 0.05, 0.56), (CX + dx, -1.05, 0.58), steel, 0.01)
for i in range(8):
    c(f'roller{i}', 0.04, 0.56, (CX, -2.12 + i * 0.185, 0.905), steel, verts=10, bevel=0, rot=(0, PI / 2, 0))
b('curtain_head', (1.06, 0.08, 0.06), (CX, -1.92, 2.07), steel_dk)

# ------------------------------------------------------------------ the bench, turntable, label reader, stamp, printer
b('bench_top', (1.1, 2.3, 0.08), (0.275, 0.4, 0.91), wood, 0.02)
b('bench_body', (1.0, 2.2, 0.57), (0.275, 0.4, 0.585), wood_dk, 0.02)
c('turntable_base', 0.34, 0.04, (CX, -0.2, 0.97), steel, verts=24)
c('reader_post', 0.04, 0.85, (0.82, -0.2, 1.375), steel, verts=10)
b('reader_arm', (0.66, 0.06, 0.06), (0.5, -0.2, 1.78), steel, 0.01)
c('stamp_post', 0.05, 1.0, (0.82, 0.65, 1.45), steel, verts=10)
b('stamp_arm', (0.62, 0.08, 0.08), (0.52, 0.65, 1.93), steel, 0.015)
b('printer', (0.28, 0.3, 0.2), (0.6, 1.3, 1.05), printer_m, 0.03, 2)
b('printer_slot', (0.03, 0.2, 0.02), (0.745, 1.3, 1.1), dark, 0)
# out-chute outside the back slot
b('chute_bed', (0.6, 0.27, 0.04), (CX, 2.08, 1.09), steel, 0.01)
for dx in (-0.3, 0.3):
    b(f'chute_rail{dx}', (0.04, 0.27, 0.07), (CX + dx, 2.08, 1.15), blue, 0.01)
for y in (2.0, 2.16):
    c(f'chute_roller{y}', 0.03, 0.56, (CX, y, 1.14), steel, verts=8, bevel=0, rot=(0, PI / 2, 0))
# the phone to the lessons library (purple: Memory), on the back wall under the back-room cards
b('phone_body', (0.12, 0.26, 0.36), (-1.59, 0.55, 1.4), purple, 0.03, 2)
b('phone_dial', (0.02, 0.14, 0.14), (-1.525, 0.55, 1.36), paper, 0.01)
# roof icon (the primitive's own picture): a box goes in, a post-it comes out
b('icon_box', (0.36, 0.36, 0.3), (-1.75, -0.55, 3.3), parcel_m, 0.04, 2)
b('icon_tape', (0.37, 0.08, 0.02), (-1.75, -0.55, 3.455), tape, 0)
c('icon_arrow', 0.1, 0.24, (-1.75, 0.02, 3.3), dark, verts=3, bevel=0, rot=(-PI / 2, 0, 0), top=0.0)
b('icon_post', (0.05, 0.4, 0.4), (-1.75, 0.55, 3.35), post_m, 0.02, rot=(0.12, 0, 0))
# the alert beacon's base and lens
c('beacon_base', 0.13, 0.08, (1.25, 1.85, 3.19), dark, verts=16)
S.append(F.sphere('beacon_lens', 0.11, (1.25, 1.85, 3.28), lens, segments=14, rings=8))

# ------------------------------------------------------------------ the job-card wall: 36 cards, one per handlers.toml row (record era)
# families: p = Hindsight / Candystore (remember, recall), a = notify and lights (alert), r = guards, w = other
SYNC = [('skill-reminder', 'w'), ('crank-tag', 'w'), ('hindsight-recall', 'p'), ('hindsight-briefing', 'p'),
        ('candystore-context', 'p'), ('candystore-context-kimi', 'p'), ('codegraph-prompt', 'w'),
        ('code-review-graph-status', 'w'), ('code-review-graph-before-commit', 'w'), ('project-notebook-start', 'w'),
        ('native-clock-guard', 'r'), ('crank-keys-guard', 'r'), ('hub-selftest', 'w'),
        ('automaticai-routing-start', 'w'), ('automaticai-routing-receipt', 'w')]
ASYNC = [('hindsight-turn', 'p'), ('hindsight-retain', 'p'), ('hindsight-session-end', 'p'), ('hindsight-journal', 'p'),
         ('hindsight-jot-flush', 'p'), ('skill-lint', 'w'), ('code-review-graph-update', 'w'),
         ('project-notebook-end', 'w'), ('merge-forward', 'w'), ('claude-notify', 'a'), ('codex-turn-notify', 'a'),
         ('nanoleaf', 'a'), ('zellij-notify', 'a'), ('orca-status', 'w'), ('git-checkpoint', 'w'),
         ('opencode-session-notify', 'a'), ('asm-stale-alert', 'a'), ('asm-log', 'w'), ('asm-blocked-amber', 'off'),
         ('automaticai-routing-final', 'w'), ('bmad-loop-relay', 'w')]
assert len(SYNC) == 15 and len(ASYNC) == 21
FAM = {'p': purple, 'a': amber, 'r': red, 'w': paper, 'off': grey}
b('board_window', (0.04, 1.5, 1.15), (-1.63, -0.98, 2.4), board, 0.01)
b('board_back', (0.04, 1.8, 1.15), (-1.63, 0.78, 2.4), board, 0.01)
ROWS = (2.92, 2.55, 2.18)
CARDS = {}


def card(cid, fam, y, ztop, sync):
    if fam == 'off':  # enabled = false: hangs grey and crooked, never fires
        b(f'card_{cid}', (0.02, 0.2, 0.3), (-1.6, y + 0.04, ztop - 0.15), grey, 0.005, rot=(0.3, 0, 0))
        return
    piv = anim(F.empty(f'card_{cid}', (-1.6, y, ztop)))
    parts = [F.box(f'card_{cid}_face', (0.02, 0.2, 0.3), (0, 0, -0.15), FAM[fam], bevel=0.005, segments=1, parent=piv)]
    if sync:  # window card: a stopwatch dot for its time limit
        parts.append(F.cyl(f'card_{cid}_watch', 0.032, 0.012, (0.012, 0.05, -0.07), red if fam != 'r' else paper, verts=10, bevel=0, rot=(0, PI / 2, 0), parent=piv))
    F.merge(parts, f'card_{cid}_mesh')
    CARDS[cid] = piv


for i, (cid, fam) in enumerate(SYNC):
    card(cid, fam, -1.58 + (i % 5) * 0.3, ROWS[i // 5], True)
for i, (cid, fam) in enumerate(ASYNC):
    card(cid, fam, 0.01 + (i % 7) * 0.257, ROWS[i // 7], False)

F.merge(S, 'dock_body')

# ------------------------------------------------------------------ moving parts
# strip curtain in the receiving door: six PVC strips, hinged at the header
STRIPS = []
for i in range(6):
    piv = anim(F.empty(f'curtain_{i}', (-0.2 + i * 0.18, -1.9, 2.07)))
    F.box(f'curtain_{i}_strip', (0.16, 0.012, 1.07), (0, 0, -0.535), curtain, bevel=0.004, segments=1, parent=piv)
    STRIPS.append(piv)

turntable = anim(F.cyl('turntable', 0.32, 0.04, (CX, -0.2, 0.99), steel_dk, verts=24))
F.merge([turntable, F.box('turntable_mark', (0.08, 0.06, 0.012), (0.27, 0, 0.022), post_m, bevel=0, parent=turntable)], 'turntable')
s_hold = F.socket('socket_hold', (0, 0, 0.2), parent=turntable)

scanner = anim(F.box('label_reader', (0.18, 0.22, 0.1), (CX, -0.2, 1.72), dark, bevel=0.02))
beam = anim(F.empty('label_beam', (0, 0, -0.05), parent=scanner))
F.box('label_beam_ray', (0.025, 0.26, 0.3), (0, 0, -0.15), beam_m, bevel=0, parent=beam)
beam.scale = (1, 1, 0.02)
REST[beam.name]['scale'] = (1, 1, 0.02)

pad = anim(F.empty('post_pad', (CX, 0.65, 0.95)))
F.merge([F.box('post_pad_block', (0.5, 0.5, 0.1), (0, 0, 0.05), post_m, bevel=0.01, segments=1, parent=pad)]
        + [F.box(f'post_pad_sheet{k}', (0.506, 0.506, 0.006), (0, 0, z), post_edge, bevel=0, parent=pad) for k, z in enumerate((0.025, 0.05, 0.075))], 'post_pad_mesh')

stamp = anim(F.empty('house_stamp', (CX, 0.65, 1.45)))
F.merge([F.cyl('stamp_shaft', 0.03, 0.42, (0, 0, 0.21), steel, verts=10, bevel=0, parent=stamp),
         F.box('stamp_head', (0.42, 0.42, 0.12), (0, 0, -0.06), blue, bevel=0.03, segments=2, parent=stamp),
         F.box('stamp_rubber', (0.38, 0.38, 0.02), (0, 0, -0.13), dark, bevel=0, parent=stamp),
         F.sphere('stamp_knob', 0.06, (0, 0, 0.44), blue, segments=10, rings=6, parent=stamp)], 'house_stamp_mesh')

receipt = anim(F.empty('receipt', (0.75, 1.3, 1.11)))
F.box('receipt_paper', (0.3, 0.16, 0.006), (0.15, 0, 0), paper, bevel=0, parent=receipt)
receipt.scale = (0.05, 1, 1)
REST[receipt.name]['scale'] = (0.05, 1, 1)

handset = anim(F.empty('library_handset', (-1.5, 0.55, 1.62)))
F.merge([F.box('handset_bar', (0.07, 0.32, 0.06), (0, 0, 0), purple_dk, bevel=0.02, segments=1, parent=handset),
         F.box('handset_ear', (0.1, 0.08, 0.09), (0, 0.13, -0.03), purple_dk, bevel=0.02, segments=1, parent=handset),
         F.box('handset_mouth', (0.1, 0.08, 0.09), (0, -0.13, -0.03), purple_dk, bevel=0.02, segments=1, parent=handset)], 'library_handset_mesh')

clerk = anim(F.empty('clerk', (-0.75, -0.1, 0.3)))
F.merge([F.cyl('clerk_torso', 0.2, 0.55, (0, 0, 0.55), uniform, verts=16, bevel=0, parent=clerk),
         F.sphere('clerk_hip', 0.2, (0, 0, 0.275), uniform, segments=16, rings=8, parent=clerk),
         F.sphere('clerk_chest', 0.2, (0, 0, 0.825), uniform, segments=16, rings=8, parent=clerk),
         F.sphere('clerk_head', 0.19, (0, 0, 1.18), skin, segments=16, rings=10, parent=clerk),
         F.cyl('clerk_cap', 0.17, 0.08, (0, 0, 1.33), blue, verts=16, bevel=0.01, parent=clerk),
         F.box('clerk_brim', (0.14, 0.24, 0.025), (0.17, 0, 1.3), blue, bevel=0.005, parent=clerk)], 'clerk_mesh')

brief = anim(F.box('briefing_card', (0.22, 0.15, 0.014), (-1.1, -1.62, 1.118), paper, bevel=0.003))
F.box('briefing_stripe', (0.2, 0.03, 0.004), (0, 0.04, 0.008), purple, bevel=0, parent=brief)

needle = anim(F.empty('watch_needle', (-1.1, -1.99, 1.88)))
F.box('watch_needle_bar', (0.016, 0.01, 0.1), (0, 0, 0.045), red, bevel=0, parent=needle)

lamp = anim(F.sphere('open_lamp', 0.07, (1.12, -2.04, 2.35), lamp_green, segments=12, rings=8))
core = anim(F.sphere('beacon_core', 0.135, (1.25, 1.85, 3.28), lamp_amber, segments=14, rings=8))
core.scale = (0.3, 0.3, 0.3)
REST[core.name]['scale'] = (0.3, 0.3, 0.3)

flap = anim(F.empty('back_flap', (CX, 1.965, 1.5)))
F.box('back_flap_plate', (0.66, 0.02, 0.5), (0, 0.01, -0.25), blue, bevel=0.01, parent=flap)

# ------------------------------------------------------------------ sockets
CATCH = (CX, -2.08, 1.13)            # on the incoming rollers, outside the door, parcel centre height
HOLD_W = (CX, -0.2, 1.19)            # socket_hold's world point (turntable top + half a parcel)
PAD = (CX, 0.65, 1.12)               # just above the post-it pad, where the stamp wrote the note
OUT_END = (CX, 2.14, 1.2)            # on the out-chute, beyond the back wall
s_in = anim(F.socket('socket_in', CATCH))
s_out = anim(F.socket('socket_out', PAD))
s_out.rotation_euler = (PI / 2, 0, 0)  # a post-it lies flat, so it slides through the letterbox slot
REST[s_out.name]['rotation_euler'] = (PI / 2, 0, 0)

# ------------------------------------------------------------------ clips
KEYED = set()
PATHS = ('location', 'rotation_euler', 'scale')


def K(clip, obj, path, pts, interp='BEZIER'):
    for t, v in pts:
        clip.key(obj, path, t, tuple(v), interp)
    KEYED.add((clip.name, obj.name, path))


def rest(obj, path):
    return REST[obj.name][path]


def off(obj, d):
    r = rest(obj, 'location')
    return tuple(r[k] + d[k] for k in range(3))


def fire(clip, piv, t0, t1, amp=-0.95):
    """A job card swings out on its hook when its handler runs, stays out while it works, and drops back at t1."""
    pts = [(0, (0, 0, 0)), (t0, (0, 0, 0)), (t0 + 0.12, (0, amp, 0)), (t0 + 0.22, (0, amp * 0.88, 0)), (t1, (0, amp * 0.9, 0)),
           (t1 + 0.15, (0, 0, 0)), (t1 + 0.24, (0, amp * 0.12, 0)), (t1 + 0.32, (0, 0, 0)), (clip.seconds, (0, 0, 0))]
    K(clip, piv, 'rotation_euler', pts)


# Idle (4 s): the OPEN lamp breathes, the clerk shifts, the curtain sways, the reader drifts, two cards stir
idle = F.Clip('Idle', 4.0)
K(idle, lamp, 'scale', [(t / 2, (k, k, k)) for t in range(9) for k in [1 + 0.28 * F.ease_loop(t / 2, 2.0)]])
K(idle, clerk, 'scale', [(t, (1, 1, 1 + 0.02 * F.ease_loop(t, 4.0))) for t in range(5)])
K(idle, clerk, 'rotation_euler', [(t, (0, 0, 0.1 * math.sin(TAU * t / 4))) for t in range(5)])
for i, piv in enumerate(STRIPS):
    K(idle, piv, 'rotation_euler', [(t, (0.05 * math.sin(TAU * t / 4 + i * 0.9), 0, 0)) for t in range(5)])
K(idle, scanner, 'location', [(t, off(scanner, (0, 0.06 * math.sin(TAU * t / 4), 0))) for t in range(5)])
for cid, t0 in (('hindsight-journal', 1.2), ('code-review-graph-status', 2.6)):
    K(idle, CARDS[cid], 'rotation_euler', [(0, (0, 0, 0)), (t0, (0, 0, 0)), (t0 + 0.35, (0, -0.14, 0)), (t0 + 0.8, (0, 0.0, 0)), (t0 + 1.0, (0, -0.04, 0)), (t0 + 1.2, (0, 0, 0)), (4.0, (0, 0, 0))])

# Accept (1.2 s): the parcel is caught on the rollers, the clerk leans in, the curtain parts strip by strip
acc = F.Clip('Accept', 1.2)
K(acc, s_in, 'location', [(0, CATCH), (0.36, CATCH), (0.75, (CX, -0.9, 1.15)), (0.94, (CX, -0.2, 1.26)), (1.06, HOLD_W), (1.2, HOLD_W)])
for i, piv in enumerate(STRIPS):
    a = (0.15, 0.6, 0.9, 0.9, 0.6, 0.15)[i]
    K(acc, piv, 'rotation_euler', [(0, (0, 0, 0)), (0.36, (0, 0, 0)), (0.47, (a, 0, 0)), (0.62, (a * 0.8, 0, 0)), (0.82, (-a * 0.3, 0, 0)), (1.0, (a * 0.1, 0, 0)), (1.2, (0, 0, 0))])
K(acc, clerk, 'rotation_euler', [(0, (0, 0, 0)), (0.2, (0, 0, 0)), (0.5, (0, 0.14, -0.55)), (0.85, (0, 0.1, -0.2)), (1.2, (0, 0, 0))])
K(acc, lamp, 'scale', [(0, (1, 1, 1)), (0.25, (1, 1, 1)), (0.35, (1.4, 1.4, 1.4)), (0.55, (1, 1, 1)), (1.2, (1, 1, 1))])

# Work (2.4 s, loops): read the label, match the cards for a Claude prompt_submit parcel, answer the window, stamp the post-it
work = F.Clip('Work', 2.4)
K(work, turntable, 'rotation_euler', [(0, (0, 0, 0)), (0.1, (0, 0, 0)), (0.9, (0, 0, TAU)), (2.4, (0, 0, TAU))])
K(work, scanner, 'location', [(0, rest(scanner, 'location')), (0.1, rest(scanner, 'location')), (0.35, off(scanner, (0, -0.2, 0))), (0.65, off(scanner, (0, 0.18, 0))), (0.9, rest(scanner, 'location')), (2.4, rest(scanner, 'location'))])
K(work, beam, 'scale', [(0, (1, 1, 0.02)), (0.12, (1, 1, 1)), (0.85, (1, 1, 1)), (0.95, (1, 1, 0.02)), (2.4, (1, 1, 0.02))])
for k, cid in enumerate(('skill-reminder', 'crank-tag', 'hindsight-recall', 'codegraph-prompt', 'hub-selftest')):
    fire(work, CARDS[cid], 0.35 + k * 0.11, 1.25)    # the window cards: the courier waits until all five answer
for k, cid in enumerate(('hindsight-turn', 'nanoleaf', 'orca-status')):
    fire(work, CARDS[cid], 1.15 + k * 0.12, 1.8 + k * 0.05)  # the back-room cards: nobody waits
K(work, needle, 'rotation_euler', [(0, (0, 0, 0)), (0.3, (0, 0, 0)), (1.4, (0, TAU, 0)), (2.4, (0, TAU, 0))])
hs = rest(handset, 'location')
K(work, handset, 'location', [(0, hs), (0.55, hs), (0.72, off(handset, (0.1, 0, 0.2))), (1.3, off(handset, (0.1, 0, 0.2))), (1.45, off(handset, (0, 0, 0.02))), (1.55, hs), (2.4, hs)])
K(work, handset, 'rotation_euler', [(0, (0, 0, 0)), (0.55, (0, 0, 0)), (0.72, (0.2, 0.45, 0)), (0.9, (-0.15, 0.45, 0)), (1.1, (0.12, 0.45, 0)), (1.3, (0, 0.4, 0)), (1.5, (0, 0, 0)), (2.4, (0, 0, 0))])
K(work, clerk, 'rotation_euler', [(0, (0, 0, 0)), (0.4, (0, 0, 0)), (0.7, (0, 0, 0.9)), (1.35, (0, 0, 0.9)), (1.6, (0, 0, 0.1)), (1.8, (0, 0.16, 0)), (2.05, (0, 0.16, 0)), (2.4, (0, 0, 0))])
br = rest(brief, 'location')
K(work, brief, 'location', [(0, br), (0.9, br), (1.2, (-1.1, -2.07, 1.118)), (1.45, (-1.1, -2.07, 1.118)), (1.62, (-1.1, -2.2, 1.32)), (1.66, br), (2.4, br)])
K(work, brief, 'scale', [(0, (1, 1, 1)), (1.45, (1, 1, 1)), (1.62, (0.02, 0.02, 0.02)), (2.0, (0.02, 0.02, 0.02)), (2.3, (1, 1, 1)), (2.4, (1, 1, 1))])
K(work, core, 'scale', [(t, (s, s, s)) for t, s in ((0, 0.3), (1.3, 0.3), (1.4, 1.0), (1.52, 0.35), (1.64, 1.0), (1.76, 0.35), (1.88, 1.0), (2.05, 0.3), (2.4, 0.3))])
st = rest(stamp, 'location')
K(work, stamp, 'location', [(0, st), (1.55, st), (1.64, off(stamp, (0, 0, 0.06))), (1.76, off(stamp, (0, 0, -0.29))), (1.88, off(stamp, (0, 0, -0.29))), (2.15, st), (2.4, st)])
K(work, pad, 'scale', [(0, (1, 1, 1)), (1.75, (1, 1, 1)), (1.79, (1.03, 1.03, 0.85)), (1.9, (1, 1, 0.92)), (2.02, (1, 1, 1)), (2.4, (1, 1, 1))])

# Emit (0.9 s): the flap opens, the post-it slides out of the letterbox slot onto the chute, the receipt prints
emit = F.Clip('Emit', 0.9)
K(emit, s_out, 'location', [(0, PAD), (0.2, (CX, 1.2, 1.28)), (0.45, (CX, 1.86, 1.24)), (0.62, OUT_END), (0.9, OUT_END)])
K(emit, flap, 'rotation_euler', [(0, (0, 0, 0)), (0.08, (0, 0, 0)), (0.3, (1.15, 0, 0)), (0.62, (1.15, 0, 0)), (0.76, (-0.06, 0, 0)), (0.84, (0.03, 0, 0)), (0.9, (0, 0, 0))])
K(emit, receipt, 'scale', [(0, (0.05, 1, 1)), (0.12, (0.05, 1, 1)), (0.5, (1, 1, 1)), (0.66, (1, 1, 1)), (0.72, (0.05, 1, 1)), (0.9, (0.05, 1, 1))])
K(emit, receipt, 'rotation_euler', [(0, (0, 0, 0)), (0.12, (0, 0, 0)), (0.5, (0, 0.35, 0)), (0.66, (0, 0.35, 0)), (0.74, (0, 0, 0)), (0.9, (0, 0, 0))])
K(emit, clerk, 'rotation_euler', [(0, (0, 0, 0)), (0.3, (0, 0.08, -0.25)), (0.7, (0, 0, -0.05)), (0.9, (0, 0, 0))])

# every animated object is keyed on every path in every clip (held at rest where it does not move), so crossfades
# never fall back to a stale pose and Idle stays seamless
for clip in (idle, acc, work, emit):
    for obj in ANIM:
        for path in PATHS:
            if (clip.name, obj.name, path) not in KEYED:
                clip.hold(obj, path, rest(obj, path))
