# inbox-watcher: the memo desk. Blender (bpy) build for the Factory asset contract (forge/CONTRACT.md).
# Deterministic: no randomness, no timestamps. Blender axes: metres, Z up, FRONT is -Y. P(x, zf, up) takes the model's
# own axes (x right, zf toward the front, up) and returns Blender's.
#
# The anchor (anchors.ts STATION_BODY.control) turns the model by pi: model +zf faces the belt (world north, the
# visitor's window), model -x is world east (MinIO, Transcription, Candystore, Vox all stand east), model -zf is world
# south (where the floor's station and overview cameras stand). So the floor cameras see the back-left and the forge's
# clip camera (65 degrees right of the front) sees the front-right. Nothing tall stands on the right half in front of
# the desk: Holocene's wall is short and pushed to the back-right corner.
#
# The memo desk (holocene/services/inbox-watcher, iw = inbox_watcher.py, mc = memo_common.py), left to right:
#   riser from MinIO's inbox/ shelf (mc ls / mc cp; the original never moves, the desk downloads a copy into a temp
#     dir, iw:1712, and sweeps it the moment transcription ends, shutil.rmtree iw:1759)
#   watch lamp (main loop TICK_S = 1, iw:372) and the brass wake bell (POST :8697/wake from the pad's upload proxy)
#   the player: the copy spins on its cradle, a level needle on its face (measure_levels on every memo, iw:1726), a
#     pink line lamp, and the pink speaking tube to Wren (transcribe CLI / warm Whisper, iw:1784); the typed
#     transcript comes up out of it as a white slip
#   the post-it pad (bb-emit --strict facts bloodbank.audio.memo.<stage>, iw:1060)
#   the envelope pad, the --strict stamp and the stack of blank envelopes (bb-emit --strict --kind command
#     bloodbank.cmd.agent.invocation.invoke, iw:2566)
#   the registry card file (registry_route(), mc:204), the status board (status/<date>/<memo_id>.json, mc:150, seven
#     car stages, iw:843), the hatch lamp at the window slot (jsz consumer check before dispatch, mc:830) and the
#     reply horn above the window (vox /synthesize-url, minutes later; static here)
# Around it, the station's other members as the primitive ControlRoom drew them (static): the deck on four posts,
# the visitor's window, Holocene's screen and operator, its red notebook, the stairs.
#
# The forge's frames land on 0.1 / 0.5 / 0.9 of each clip, so the key poses do.
import math

import bmesh

import factory as F

PI = math.pi
TAU = 2 * PI


def P(x, zf, up):
    """model axes (x right, zf front, up) -> Blender (x, -zf, up)"""
    return (x, -zf, up)


def M(name, color, rough=0.65, **kw):
    return F.mat(name, color, rough=rough, **kw)


slate = M('holocene', F.DOMAIN_COLOR or '#475569', 0.65)       # the Holocene zone's slate (SET_DOMAIN.control)
slate_lt = M('deck_top', '#6B7686', 0.75)
steel = M('steel', F.C.get('steel', '#5B6573'), 0.6, metal=0.2)
orange = M('memo_desk', '#C2410C', 0.6)                          # Priya's own colour (tour/script.ts CAST.priya)
orange_dk = M('memo_desk_dark', '#8A2E08', 0.65)
top_m = M('worktop', F.C.get('wall', '#EFE6D4'), 0.7)
dark = M('dark', '#2A2418', 0.7)
iron = M('iron', '#45403A', 0.6, metal=0.2)
reel_m = M('reel', '#111827', 0.5, metal=0.3)                    # TourWorld.tsx: a recording is a dark reel...
hub_m = M('reel_hub', '#F59E0B', 0.55)                           # ...with an amber hub
pink = M('voice_tube', '#C0307A', 0.6)                           # the Voice zone's pink (#DB2777), toned down
pink_hi = M('voice_bead', '#FF5DB1', 0.45, emit='#FF2E93', strength=2.0)
paper = M('slip', '#F5F0E6', 0.75)
kraft = M('envelope', '#D8B07A', 0.8)                            # Moving.tsx LOOK.env
post_m = M('post', F.C.get('post', '#FFD84D'), 0.8)
brass = M('bell', '#C9A23A', 0.45, metal=0.5)
glass_m = M('glass', '#CFE6EF', 0.3, alpha=0.22)
screen_m = M('screen', '#111827', 0.5, emit='#1F2937', strength=0.6)
event_m = M('screen_event', '#FFD84D', 0.6, emit='#FFD84D', strength=1.2)
note_m = M('notebook', '#F43F5E', 0.65)                          # Props.tsx ControlRoom: "its own notebook"
skin = M('skin', F.C.get('skin', '#E9C9A8'), 0.8)
amber_on = M('lamp_amber', '#FFB020', 0.4, emit='#FFA000', strength=4.0)
pink_on = M('lamp_pink', '#FF4FA3', 0.4, emit='#FF2E93', strength=4.0)
green_on = M('lamp_green', '#4ADE80', 0.4, emit='#22C55E', strength=4.0)
bulb_m = M('watch_bulb', '#FFE7A8', 0.4, emit='#FFD27A', strength=3.5)
glass_off = M('lamp_glass', '#3A2A12', 0.45)
red_off = M('lamp_failed', '#5A1A1A', 0.45)

S = []  # static parts, merged into one mesh at the end


def b(name, size, loc, m, bevel=0.015, seg=1, rot=(0, 0, 0)):
    o = F.box(name, size, loc, m, bevel=bevel, segments=seg, rot=rot)
    S.append(o)
    return o


def c(name, r, depth, loc, m, verts=16, bevel=0.008, rot=(0, 0, 0), top=None):
    o = F.cyl(name, r, depth, loc, m, verts=verts, bevel=bevel, rot=rot, radius_top=top)
    S.append(o)
    return o


def sph(name, r, loc, m, seg=12, rings=8):
    o = F.sphere(name, r, loc, m, segments=seg, rings=rings)
    S.append(o)
    return o


ANIM = []
REST = {}


def anim(o):
    ANIM.append(o)
    REST[o.name] = {'location': tuple(o.location), 'rotation_euler': tuple(o.rotation_euler), 'scale': tuple(o.scale)}
    return o


def set_rest(o, path, v):
    setattr(o, path, v)
    REST[o.name][path] = tuple(v)


def open_tube(o):
    bm = bmesh.new()
    bm.from_mesh(o.data)
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if abs(f.normal.z) > 0.9], context='FACES')
    bm.to_mesh(o.data)
    bm.free()
    return o


def rod(name, a, b_, r, m, verts=10):
    """a cylinder from Blender point a to b"""
    dx, dy, dz = b_[0] - a[0], b_[1] - a[1], b_[2] - a[2]
    L = math.sqrt(dx * dx + dy * dy + dz * dz)
    rx = math.acos(max(-1, min(1, dz / L)))
    rz = math.atan2(dx, -dy) if (abs(dx) + abs(dy)) > 1e-9 else 0
    return c(name, r, L, ((a[0] + b_[0]) / 2, (a[1] + b_[1]) / 2, (a[2] + b_[2]) / 2), m, verts=verts, bevel=0, rot=(rx, 0, rz))


def person(name, x, zf, base, m):
    """Props.tsx Person: a capsule (r 0.2, length 0.55, centre 0.55 up) and a head (r 0.19, 1.18 up)"""
    open_tube(c(f'{name}_body', 0.2, 0.55, P(x, zf, base + 0.55), m, verts=14, bevel=0))
    for dz in (-1, 1):
        sph(f'{name}_cap{dz}', 0.2, P(x, zf, base + 0.55 + dz * 0.275), m, 14, 7)
    sph(f'{name}_head', 0.19, P(x, zf, base + 1.18), skin, 14, 9)


def lamp(name, loc, on_m, r=0.07):
    """a dark glass dome that a lit bulb swells over (scale 0.01 = off, 1 = lit)"""
    sph(f'{name}_glass', r, loc, glass_off, 12, 8)
    lit = anim(F.sphere(name, r * 1.15, loc, on_m, segments=12, rings=8))
    set_rest(lit, 'scale', (0.01, 0.01, 0.01))
    return lit


FLAT = (PI / 2, 0, 0)    # an item lying flat (its thin axis up)
DECK = 2.8               # the mezzanine's floor (the primitive's was 3.4; lower so the desk is the frame, not the legs)
TOP = DECK + 0.97        # the memo desk's worktop surface

# ------------------------------------------------------------------ the mezzanine (static; the primitive's, redrawn)
DX0, DX1, DZ0, DZ1 = -1.75, 1.75, -1.5, 1.9
b('deck_slab', (DX1 - DX0, DZ1 - DZ0, 0.2), P(0, (DZ0 + DZ1) / 2, DECK - 0.1), slate, 0.03)
b('deck_plate', (DX1 - DX0 - 0.1, DZ1 - DZ0 - 0.1, 0.02), P(0, (DZ0 + DZ1) / 2, DECK + 0.005), slate_lt, 0.005)
for px, pz in ((-1.6, -1.35), (1.6, -1.35), (-1.6, 1.75), (1.6, 1.75)):
    b(f'post{px}{pz}', (0.14, 0.14, DECK - 0.2), P(px, pz, (DECK - 0.2) / 2), steel, 0.02)
    b(f'post_foot{px}{pz}', (0.3, 0.3, 0.05), P(px, pz, 0.025), steel, 0.01)
# railings on the two open sides (back and left), low and thin so the cameras see over them
RH = DECK + 0.95
for x in (-1.7, -0.55, 0.6):
    b(f'rail_post_b{x}', (0.06, 0.06, 0.95), P(x, -1.45, DECK + 0.475), steel, 0.01)
b('rail_top_b', (3.4, 0.06, 0.05), P(0.0, -1.45, RH), slate, 0.01)
b('rail_mid_b', (3.4, 0.03, 0.03), P(0.0, -1.45, DECK + 0.5), steel, 0.005)
for z in (-0.2, 0.75):
    b(f'rail_post_l{z}', (0.06, 0.06, 0.95), P(-1.7, z, DECK + 0.475), steel, 0.01)
b('rail_top_l', (0.06, 3.3, 0.05), P(-1.7, 0.2, RH), slate, 0.01)
b('rail_mid_l', (0.03, 3.3, 0.03), P(-1.7, 0.2, DECK + 0.5), steel, 0.005)

# the visitor's window, facing the belt (model +zf), with a dispatch slot the envelopes and post-its leave by
WZ = 1.85
WTOP = DECK + 1.75
b('win_post_l', (0.1, 0.1, 1.75), P(-1.7, WZ, DECK + 0.875), slate, 0.02)
b('win_post_r', (0.1, 0.1, 1.75), P(1.7, WZ, DECK + 0.875), slate, 0.02)
b('win_head', (3.5, 0.12, 0.1), P(0, WZ, WTOP - 0.03), slate, 0.02)
b('win_sill', (3.5, 0.16, 0.1), P(0, WZ, DECK + 0.08), slate, 0.02)
SLOT_LO, SLOT_HI, SLOT_X = DECK + 1.1, DECK + 1.3, 0.6
SLOT_Z = (SLOT_LO + SLOT_HI) / 2
b('glass_lo', (3.3, 0.02, SLOT_LO - DECK - 0.13), P(0, WZ, (SLOT_LO + DECK + 0.13) / 2), glass_m, 0)
b('glass_hi', (3.3, 0.02, WTOP - 0.08 - SLOT_HI), P(0, WZ, (WTOP - 0.08 + SLOT_HI) / 2), glass_m, 0)
for sx in (-1, 1):
    w_ = 1.65 - SLOT_X
    b(f'glass_side{sx}', (w_, 0.02, SLOT_HI - SLOT_LO), P(sx * (SLOT_X + w_ / 2), WZ, SLOT_Z), glass_m, 0)
    b(f'slot_cheek{sx}', (0.05, 0.16, SLOT_HI - SLOT_LO + 0.06), P(sx * (SLOT_X + 0.025), WZ, SLOT_Z), orange, 0.01)
b('slot_lip_lo', (2 * SLOT_X + 0.1, 0.18, 0.04), P(0, WZ, SLOT_LO - 0.02), orange, 0.01)
b('slot_lip_hi', (2 * SLOT_X + 0.1, 0.18, 0.04), P(0, WZ, SLOT_HI + 0.02), orange, 0.01)
# the hatch lamp beside the slot: a puller on the lane's consumer (jsz), checked before every envelope goes
HATCH = P(SLOT_X + 0.17, WZ - 0.02, SLOT_Z)
b('hatch_lamp_box', (0.18, 0.12, 0.22), (HATCH[0], HATCH[1] + 0.05, HATCH[2]), orange_dk, 0.02)
hatch_lit = lamp('hatch_lamp', (HATCH[0], HATCH[1] - 0.02, HATCH[2]), green_on, 0.075)
# the reply horn over the window, left: once the agent answers (minutes later) the desk has Vox speak the reply
# (POST /synthesize-url) and posts it back to the pad. Static: no clip plays that far.
HORN = (-1.15, WZ - 0.02, WTOP + 0.16)
b('horn_bracket', (0.06, 0.06, 0.16), P(HORN[0], HORN[1] - 0.05, WTOP + 0.06), iron, 0.008)
c('horn_bell', 0.17, 0.3, P(HORN[0], HORN[1] + 0.1, HORN[2]), pink, verts=18, bevel=0.01, rot=(-PI / 2, 0, 0), top=0.05)
c('horn_throat', 0.05, 0.12, P(HORN[0], HORN[1] - 0.1, HORN[2]), iron, verts=10, bevel=0.005, rot=(PI / 2, 0, 0))
c('horn_mouth', 0.15, 0.012, P(HORN[0], HORN[1] - 0.045 + 0.1 + 0.15, HORN[2]), dark, verts=18, bevel=0, rot=(PI / 2, 0, 0))

# Holocene's side: a short wall in the back-right corner with its screen, its operator watching it, its red notebook
HX = 1.7
b('holo_wall', (0.1, 0.95, 1.3), P(HX, -1.0, DECK + 0.65), slate, 0.02)
b('screen0', (0.05, 0.74, 0.5), P(HX - 0.07, -1.0, DECK + 1.0), screen_m, 0.015)
for j in range(4):
    w_ = (0.5, 0.36, 0.44, 0.28)[j]
    b(f'screen0_ev{j}', (0.012, w_, 0.05), P(HX - 0.1, -1.0 - (0.6 - w_) / 2 + 0.02, DECK + 1.17 - 0.11 * j), event_m, 0)
person('holo_op', 1.12, -1.0, DECK, slate)
b('note_ledge', (0.2, 0.42, 0.04), P(HX - 0.14, -0.72, DECK + 0.8), slate, 0.01)
b('notebook', (0.16, 0.24, 0.05), P(HX - 0.14, -0.72, DECK + 0.845), note_m, 0.01, rot=(0, 0, 0.25))
# the stairs, outside the right edge, arriving at the gap between the wall and the window
NSTEP = 7
RISE = DECK / (NSTEP + 1)
for i in range(NSTEP):
    zc = 0.95 - 0.36 * (NSTEP - 1 - i)
    b(f'step{i}', (0.7, 0.34, 0.1), P(2.16, zc, RISE * (i + 1) - 0.05), steel, 0.015)
st_a, st_b = P(2.55, 0.95 - 0.36 * NSTEP, 0.0), P(2.55, 1.12, DECK)
rod('stair_stringer', st_a, st_b, 0.04, steel, 8)
# no handrail: from the clip camera it cut across the desk front

# ------------------------------------------------------------------ the memo desk (the inbox-watcher)
KX0, KX1, KZ0, KZ1 = -1.5, 0.9, -0.3, 0.55
KCX, KCZ = (KX0 + KX1) / 2, (KZ0 + KZ1) / 2
b('desk_kick', (KX1 - KX0 - 0.1, KZ1 - KZ0 - 0.1, 0.1), P(KCX, KCZ, DECK + 0.05), orange_dk, 0.01)
b('desk_body', (KX1 - KX0, KZ1 - KZ0, TOP - 0.05 - DECK - 0.1), P(KCX, KCZ, (TOP - 0.05 + DECK + 0.1) / 2), orange, 0.03)
b('desk_top', (KX1 - KX0 + 0.08, KZ1 - KZ0 + 0.08, 0.05), P(KCX, KCZ, TOP - 0.025), top_m, 0.015)
for zf_side in (KZ0 - 0.005, KZ1 + 0.005):   # drawer fronts on both long faces (each camera sees one)
    for k, xc in enumerate((-1.05, 0.45)):
        b(f'drawer{zf_side}{k}', (0.62, 0.03, 0.26), P(xc, zf_side, TOP - 0.27), top_m, 0.012)
        b(f'drawer_pull{zf_side}{k}', (0.2, 0.04, 0.035), P(xc, zf_side, TOP - 0.23), dark, 0.008)
b('desk_band_b', (KX1 - KX0, 0.02, 0.06), P(KCX, KZ0 - 0.01, TOP - 0.1), slate, 0)
b('desk_band_f', (KX1 - KX0, 0.02, 0.06), P(KCX, KZ1 + 0.01, TOP - 0.1), slate, 0)

# ---- the riser from MinIO's inbox/ shelf: up from the floor at the desk's left (world east), over, an open mouth
RX, RZ, RTOP, RR = -2.0, 0.08, DECK + 1.45, 0.2
c('riser', RR, RTOP, P(RX, RZ, RTOP / 2), steel, verts=20, bevel=0)
c('riser_foot', RR + 0.08, 0.08, P(RX, RZ, 0.04), steel, verts=20, bevel=0.01)
for k, h in enumerate((0.9, DECK - 0.4)):
    c(f'riser_band{k}', RR + 0.02, 0.12, P(RX, RZ, h), orange, verts=20, bevel=0.005)
sph('riser_elbow', RR, P(RX, RZ, RTOP), steel, 20, 10)
STUB_X1 = -1.78
open_tube(c('riser_stub', RR, STUB_X1 - RX, P((RX + STUB_X1) / 2, RZ, RTOP), steel, verts=20, bevel=0, rot=(0, PI / 2, 0)))
c('riser_dark', RR - 0.01, 0.01, P(RX + 0.08, RZ, RTOP), dark, verts=20, bevel=0, rot=(0, PI / 2, 0))
open_tube(c('riser_lip', RR + 0.035, 0.05, P(STUB_X1, RZ, RTOP), orange, verts=20, bevel=0, rot=(0, PI / 2, 0)))
# the trough: from the riser's mouth down onto the player's cradle
REEL_R, REEL_T = 0.18, 0.07
T0X, T1X = STUB_X1, -1.24
T0F, T1F = RTOP - RR + 0.02, TOP + 0.26          # trough floor heights at its two ends
TL = math.hypot(T1X - T0X, T1F - T0F)
TA = math.atan2(T0F - T1F, T1X - T0X)            # slope, falling toward +x
tmid = ((T0X + T1X) / 2, (T0F + T1F) / 2)
b('trough_floor', (TL, 0.16, 0.02), P(tmid[0], RZ, tmid[1] - 0.01), steel, 0.004, rot=(0, TA, 0))
for sz in (-1, 1):
    b(f'trough_side{sz}', (TL, 0.015, 0.08), P(tmid[0], RZ + sz * 0.085, tmid[1] + 0.03), steel, 0.004, rot=(0, TA, 0))
b('trough_strut', (0.04, 0.04, T1F - TOP), P(-1.4, RZ, (T1F + TOP) / 2), iron, 0.006)

# ---- the player: a box with a cradle fork on top; the copy of the tape spins there while the line to Wren is open
PLX, PLZ = -1.0, 0.05
PL_TOP = TOP + 0.2
b('player', (0.42, 0.4, 0.2), P(PLX, PLZ, TOP + 0.1), dark, 0.03)
b('player_face', (0.14, 0.02, 0.12), P(PLX - 0.12, PLZ + 0.2, TOP + 0.1), iron, 0.006)
b('player_slot', (0.3, 0.03, 0.012), P(PLX + 0.05, 0.2, PL_TOP + 0.003), iron, 0.002)
AXLE = P(PLX, PLZ, PL_TOP + REEL_R + 0.02)
for sz in (-1, 1):
    b(f'fork{sz}', (0.05, 0.025, REEL_R + 0.06), P(PLX, PLZ + sz * 0.065, PL_TOP + (REEL_R + 0.06) / 2), iron, 0.006)
c('axle', 0.018, 0.16, AXLE, iron, verts=8, bevel=0, rot=(PI / 2, 0, 0))
# the level meter on the player's face: measure_levels (ffmpeg dBFS) runs on every memo; the needle rests left
DIAL = P(PLX + 0.09, PLZ + 0.215, TOP + 0.09)
b('dial', (0.2, 0.012, 0.14), DIAL, top_m, 0.006)
b('dial_red', (0.05, 0.014, 0.025), (DIAL[0] + 0.065, DIAL[1], DIAL[2] + 0.045), M('dial_red', '#DC2626', 0.6), 0.002)
NEEDLE_REST = (0, -0.7, 0)
needle = anim(F.empty('level_needle', (DIAL[0], DIAL[1] - 0.01, DIAL[2] - 0.05), rot=NEEDLE_REST))
F.merge([F.box('needle_bar', (0.008, 0.006, 0.1), (0, 0, 0.05), dark, bevel=0, parent=needle)], 'needle_mesh')
# the pink speaking tube to Wren (the Transcription kiosk by the sound wing, world east): off the player's back,
# down to the deck, along to the left edge, and down to the floor
TUBE_R = 0.05
TUBE = [P(PLX, PLZ - 0.2, TOP + 0.1), P(PLX, -0.58, TOP + 0.1), P(PLX, -0.58, DECK + 0.08),
        P(-1.95, -0.58, DECK + 0.08), P(-1.95, -0.58, 0.05)]
for k in range(4):
    rod(f'tube{k}', TUBE[k], TUBE[k + 1], TUBE_R, pink, 12)
for k in (1, 2, 3):
    sph(f'tube_elbow{k}', TUBE_R, TUBE[k], pink, 10, 6)
c('tube_horn', 0.1, 0.12, P(PLX, -0.21, TOP + 0.1), pink, verts=14, bevel=0.005, rot=(-PI / 2, 0, 0), top=TUBE_R)
c('tube_foot', 0.1, 0.06, P(-1.95, -0.58, 0.03), pink, verts=12, bevel=0.005)
# a bead of sound down the tube to Wren, and the words back up
bead = anim(F.sphere('tube_bead', 0.08, TUBE[0], pink_hi, segments=12, rings=8))
set_rest(bead, 'scale', (0.01, 0.01, 0.01))
# the line lamp on the player: lit while the desk is on the line to Wren
line_lit = lamp('line_lamp', P(PLX - 0.13, PLZ - 0.12, PL_TOP + 0.06), pink_on, 0.06)
b('line_lamp_seat', (0.1, 0.1, 0.03), P(PLX - 0.13, PLZ - 0.12, PL_TOP + 0.015), iron, 0.006)

# the transcript slip: rests inside the player, rises out of its slot, then goes into the envelope
SLIP_REST = P(PLX + 0.05, 0.2, TOP - 0.06)
slip = anim(F.empty('slip', SLIP_REST))
F.merge([F.box('slip_sheet', (0.3, 0.006, 0.4), (0, 0, 0), paper, bevel=0.002, parent=slip)] +
        [F.box(f'slip_line{k}', (w_, 0.004, 0.02), (-0.12 + w_ / 2, -0.005, 0.13 - 0.06 * k), dark, bevel=0, parent=slip)
         for k, w_ in enumerate((0.24, 0.2, 0.24, 0.14, 0.2))], 'slip_mesh')

# ---- the tape (a copy of the memo): a dark reel with an amber hub, facing the long sides; hidden in the riser mouth
TAPE_HIDE = P(STUB_X1 - 0.08, RZ, RTOP)
tape = anim(F.empty('tape', TAPE_HIDE))
set_rest(tape, 'scale', (0.01, 0.01, 0.01))
F.merge([F.cyl('reel_disc', REEL_R, REEL_T, (0, 0, 0), reel_m, verts=24, bevel=0.01, rot=(PI / 2, 0, 0), parent=tape),
         F.cyl('reel_hub', 0.06, REEL_T + 0.02, (0, 0, 0), hub_m, verts=14, bevel=0.005, rot=(PI / 2, 0, 0), parent=tape),
         F.box('reel_window', (0.06, REEL_T + 0.012, 0.08), (0, 0, 0.115), hub_m, bevel=0.004, parent=tape)], 'tape_mesh')

# ---- the watch lamp: a gooseneck at the back-left corner, its head over the trough; ticks every second
WLX, WLZ, WLH = -1.38, -0.18, DECK + 1.82
b('watch_base', (0.2, 0.2, 0.04), P(WLX, WLZ, TOP + 0.02), orange_dk, 0.01)
c('watch_post', 0.025, WLH - TOP, P(WLX, WLZ, (WLH + TOP) / 2), iron, verts=8, bevel=0)
WATCH_YAW = math.atan2(-(RZ + 0.05 - WLZ), -(WLX - (-1.68)))   # arm toward the trough's top end
watch = anim(F.empty('watch_head', P(WLX, WLZ, WLH), rot=(0, 0, WATCH_YAW)))
F.merge([F.box('watch_arm', (0.36, 0.035, 0.035), (-0.18, 0, 0), orange_dk, bevel=0.008, parent=watch),
         F.cyl('watch_shade', 0.15, 0.16, (-0.36, 0, -0.07), orange, verts=16, bevel=0.006, radius_top=0.06, parent=watch),
         F.sphere('watch_joint', 0.035, (0, 0, 0), iron, segments=10, rings=6, parent=watch)], 'watch_mesh')
watch_bulb = anim(F.sphere('watch_bulb', 0.075, (-0.36, 0, -0.15), bulb_m, segments=12, rings=8, parent=watch))

# ---- the wake bell: a brass desk bell, front-left; the pad's upload proxy rings it (POST /wake)
BLX, BLZ = -1.28, 0.36
c('bell_base', 0.17, 0.04, P(BLX, BLZ, TOP + 0.02), dark, verts=18, bevel=0.008)
bell = anim(F.empty('bell', P(BLX, BLZ, TOP + 0.04)))
dome = F.sphere('bell_dome', 0.16, (0, 0, 0), brass, segments=18, rings=10, parent=bell)
dome.scale = (1, 1, 0.8)
F.merge([dome, F.cyl('bell_neck', 0.016, 0.1, (0, 0, 0.16), iron, verts=8, bevel=0, parent=bell)], 'bell_mesh')
plunger = anim(F.empty('bell_plunger', P(BLX, BLZ, TOP + 0.04 + 0.22)))
F.merge([F.cyl('plunger_cap', 0.04, 0.03, (0, 0, 0), dark, verts=12, bevel=0.006, parent=plunger)], 'plunger_mesh')

# ---- the post-it pad: a sheet leaves for the belt at each step the clips play (received, transcribed, dispatched)
PPX, PPZ = -0.72, 0.38
for k in range(4):
    b(f'pp_sheet{k}', (0.32, 0.32, 0.012), P(PPX, PPZ, TOP + 0.006 + 0.012 * k), post_m, 0.002, rot=(0, 0, 0.02 * (k % 3 - 1)))
PP_TOP = TOP + 0.054
sheet = anim(F.empty('post_sheet', P(PPX, PPZ, PP_TOP)))
F.merge([F.box('sheet_mesh_b', (0.32, 0.32, 0.012), (0, 0, 0), post_m, bevel=0.002, parent=sheet)], 'sheet_mesh')

# ---- the envelope pad (socket_hold) and the stack of blank envelopes (socket_in)
EPX, EPZ = -0.3, 0.22
b('env_pad', (0.66, 0.48, 0.02), P(EPX, EPZ, TOP + 0.01), slate_lt, 0.004)
HOLD = P(EPX, EPZ, TOP + 0.02 + 0.015)
ESX, ESZ = 0.38, 0.27
b('stack_tray', (0.68, 0.5, 0.03), P(ESX, ESZ, TOP + 0.015), orange_dk, 0.006)
for k in range(5):
    b(f'stack_env{k}', (0.58, 0.4, 0.03), P(ESX, ESZ, TOP + 0.045 + 0.03 * k), kraft, 0.004, rot=(0, 0, 0.015 * (k % 3 - 1)))
STACK = P(ESX, ESZ, TOP + 0.03 + 0.03 * 5 + 0.015 + 0.002)

# ---- the stamp: bb-emit runs --strict (the envelope is checked against its schema before it goes); an arm on a post
# behind the envelope pad comes down on the envelope
SPX, SPZ, SPH = EPX, -0.22, TOP + 0.34
b('stamp_post', (0.06, 0.06, SPH - TOP), P(SPX, SPZ, (SPH + TOP) / 2), iron, 0.008)
b('stamp_post_foot', (0.16, 0.16, 0.03), P(SPX, SPZ, TOP + 0.015), iron, 0.006)
STAMP_UP = (-0.75, 0, 0)
STAMP_DOWN = (0.0, 0, 0)
stamp = anim(F.empty('stamp_arm', P(SPX, SPZ, SPH), rot=STAMP_UP))
ARM = EPZ - SPZ
F.merge([F.cyl('stamp_hinge', 0.04, 0.1, (0, 0, 0), iron, verts=10, bevel=0.005, rot=(0, PI / 2, 0), parent=stamp),
         F.box('stamp_bar', (0.05, ARM + 0.04, 0.05), (0, -(ARM + 0.04) / 2, 0), orange_dk, bevel=0.01, parent=stamp),
         F.cyl('stamp_knob', 0.06, 0.08, (0, -ARM, 0.06), orange, verts=14, bevel=0.01, parent=stamp),
         F.box('stamp_shank', (0.05, 0.05, 0.22), (0, -ARM, -0.13), iron, bevel=0.008, parent=stamp),
         F.box('stamp_head', (0.24, 0.17, 0.07), (0, -ARM, -SPH + TOP + 0.02 + 0.03 + 0.035 + 0.003), dark, bevel=0.012, parent=stamp),
         F.box('stamp_ink', (0.2, 0.13, 0.01), (0, -ARM, -SPH + TOP + 0.02 + 0.03 + 0.003), orange, bevel=0.002, parent=stamp)],
        'stamp_mesh')

# ---- the registry card file: a drum of cards on a stand; on receive it turns to the worker on the tape's address
RDX, RDZ, RDH = 0.5, -0.12, TOP + 0.31
for sx in (-1, 1):
    b(f'rolo_cheek{sx}', (0.025, 0.2, 0.34), P(RDX + sx * 0.19, RDZ, TOP + 0.17), orange_dk, 0.008)
b('rolo_foot', (0.42, 0.24, 0.03), P(RDX, RDZ, TOP + 0.015), orange_dk, 0.006)
rolo = anim(F.empty('rolodex', P(RDX, RDZ, RDH)))
RP = [F.cyl('rolo_drum', 0.07, 0.34, (0, 0, 0), dark, verts=14, bevel=0.005, rot=(0, PI / 2, 0), parent=rolo)]
for k in range(10):
    a_ = TAU * k / 10
    RP.append(F.box(f'rolo_card{k}', (0.3, 0.012, 0.17), (0, -0.155 * math.sin(a_), 0.155 * math.cos(a_)),
                    top_m if k else post_m, bevel=0.003, rot=(a_, 0, 0), parent=rolo))
F.merge(RP, 'rolodex_mesh')

# ---- the status board: status/<date>/<memo_id>.json is rewritten at every stage. The car's seven stages (iw:843):
# left column received, transcribing, heard, working (the clips light these); right column replying, done (minutes
# later, after the agent answers; dark here) and failed (red, dark).
SBX, SBZ = 0.8, -0.2
b('status_post', (0.05, 0.05, 0.18), P(SBX, SBZ, TOP + 0.09), iron, 0.008)
b('status_board', (0.38, 0.06, 0.86), P(SBX, SBZ, TOP + 0.18 + 0.43), slate, 0.02)
b('status_cap', (0.42, 0.1, 0.04), P(SBX, SBZ, TOP + 0.18 + 0.88), orange, 0.01)
status = [lamp(f'status_lamp{k}', P(SBX - 0.09, SBZ, TOP + 0.18 + 0.75 - 0.2 * k), amber_on, 0.07) for k in range(4)]
for k in range(2):
    sph(f'status_later{k}', 0.07, P(SBX + 0.09, SBZ, TOP + 0.18 + 0.75 - 0.2 * k), glass_off, 12, 8)
sph('status_failed', 0.07, P(SBX + 0.09, SBZ, TOP + 0.18 + 0.15), red_off, 12, 8)

# ------------------------------------------------------------------ sockets
s_in = anim(F.socket('socket_in', STACK))
set_rest(s_in, 'rotation_euler', FLAT)
s_hold = F.socket('socket_hold', HOLD)
s_hold.rotation_euler = FLAT
s_out = anim(F.socket('socket_out', HOLD))
set_rest(s_out, 'rotation_euler', FLAT)

# ------------------------------------------------------------------ clips
KEYED = set()
PATHS = ('location', 'rotation_euler', 'scale')
CLIPS = []


def K(clip, obj, path, pts, interp='BEZIER'):
    for t, v in pts:
        clip.key(obj, path, t, tuple(v), interp)
    KEYED.add((clip.name, obj.name, path))


def rest(obj, path):
    return REST[obj.name][path]


def off(obj, d):
    r = rest(obj, 'location')
    return tuple(r[k] + d[k] for k in range(3))


def S3(k):
    return (k, k, k)


def clip(name, seconds):
    c_ = F.Clip(name, seconds)
    CLIPS.append(c_)
    return c_


OFF, ON = S3(0.01), S3(1.0)


def lamp_keys(cl, lit, t_on=None, t_off=None, start_on=False):
    """a lamp swells on at t_on (and goes off at t_off)"""
    pts = [(0, ON if start_on else OFF)]
    if t_on is not None:
        pts += [(t_on - 0.04, OFF), (t_on, S3(1.2)), (t_on + 0.07, ON)]
    if t_off is not None:
        pts += [(t_off - 0.05, ON), (t_off, OFF)]
    lit_at_end = (start_on or t_on is not None) and t_off is None
    pts.append((cl.seconds, ON if lit_at_end else OFF))
    if start_on and t_on is None and t_off is None:
        # lit the whole clip: the exporter drops a constant channel and three falls back to the rest pose (off), so
        # the lamp breathes a little to stay in the glb
        pts.append((cl.seconds / 2, S3(1.06)))
    K(cl, lit, 'scale', sorted(pts, key=lambda p: p[0]))


def sheet_flight(cl, t0):
    """one post-it leaves the pad for the belt: lifts, flies out of the window slot at t0+0.32 at full size, shrinks
    away just past it; the next sheet is on the pad by t0+0.46"""
    pad = rest(sheet, 'location')
    sx, sy = pad[0], pad[1]
    K(cl, sheet, 'location', [(0, pad), (t0, pad), (t0 + 0.08, (sx, sy, pad[2] + 0.12)), (t0 + 0.2, P(-0.45, 1.0, SLOT_Z + 0.05)),
                              (t0 + 0.32, P(-0.25, WZ, SLOT_Z)), (t0 + 0.35, P(-0.22, WZ + 0.22, SLOT_Z + 0.02)),
                              (t0 + 0.39, pad), (cl.seconds, pad)])
    K(cl, sheet, 'scale', [(0, ON), (t0 + 0.32, ON), (t0 + 0.35, S3(0.5)), (t0 + 0.39, S3(0.01)), (t0 + 0.42, S3(1.06)),
                           (t0 + 0.46, ON), (cl.seconds, ON)])
    K(cl, sheet, 'rotation_euler', [(0, (0, 0, 0)), (t0 + 0.06, (0, 0, 0)), (t0 + 0.2, (0, 0, 0.3)), (t0 + 0.35, (0, 0, 0.1)),
                                    (t0 + 0.39, (0, 0, 0)), (cl.seconds, (0, 0, 0))])


# Idle (4 s): the desk is waiting with the bell live. The watch lamp's bulb ticks once a second (TICK_S = 1) and its
# head sweeps the riser's mouth and the trough. Keyed every 5 frames, whole cycles: first key = last key.
idle = clip('Idle', 4.0)
STEPS = 24
tt = [4.0 * i / STEPS for i in range(STEPS + 1)]
K(idle, watch, 'rotation_euler', [(t, (0, 0, WATCH_YAW + 0.5 * math.sin(TAU * t / 4.0))) for t in tt], 'LINEAR')
K(idle, watch_bulb, 'scale', [(t, S3(1 + 1.1 * F.ease_loop(t, 1.0) ** 3)) for t in tt], 'LINEAR')

# Accept (1.2 s): the pad's ring (POST /wake); "received": the card file turns to the worker on the tape's address
# (registry_route), the R lamp lights and a post-it leaves; the T lamp follows at once (done_stage received ->
# transcribe, iw:1687); a copy of the tape comes out of the riser (mc cp) and rolls down onto the cradle; a blank
# envelope is lifted from the stack onto the pad. 0.12 s: plunger down, bell ringing; 0.6 s: post-it at the slot,
# tape in the trough; 1.08 s: tape on the cradle, envelope on the pad.
acc = clip('Accept', 1.2)
pr = rest(plunger, 'location')
K(acc, plunger, 'location', [(0, pr), (0.05, pr), (0.09, off(plunger, (0, 0, -0.05))), (0.15, pr), (0.22, pr),
                             (0.25, off(plunger, (0, 0, -0.04))), (0.3, pr), (1.2, pr)])
K(acc, bell, 'rotation_euler', [(0, (0, 0, 0)), (0.08, (0, 0, 0)), (0.12, (0.15, 0.06, 0)), (0.18, (-0.12, -0.05, 0)),
                                (0.24, (0.09, 0.03, 0)), (0.3, (-0.05, 0, 0)), (0.38, (0.02, 0, 0)), (0.46, (0, 0, 0)), (1.2, (0, 0, 0))])
K(acc, watch_bulb, 'scale', [(0, ON), (0.1, ON), (0.2, S3(1.8)), (0.95, S3(1.8)), (1.2, ON)])
K(acc, rolo, 'rotation_euler', [(0, (0, 0, 0)), (0.14, (0, 0, 0)), (0.58, (TAU, 0, 0)), (1.2, (TAU, 0, 0))])
lamp_keys(acc, status[0], 0.4)
lamp_keys(acc, status[1], 0.5)
sheet_flight(acc, 0.28)
tr = rest(tape, 'location')
mouth = P(STUB_X1 + 0.06, RZ, RTOP - RR + REEL_R + 0.02)
trough_end = P(T1X, RZ, T1F + REEL_R)
K(acc, tape, 'location', [(0, tr), (0.3, tr), (0.42, mouth), (0.6, P((STUB_X1 + T1X) / 2, RZ, (T0F + T1F) / 2 + REEL_R)),
                          (0.8, trough_end), (0.9, (AXLE[0] - 0.06, AXLE[1], AXLE[2] + 0.05)), (0.97, AXLE),
                          (1.02, (AXLE[0], AXLE[1], AXLE[2] + 0.015)), (1.08, AXLE), (1.2, AXLE)])
K(acc, tape, 'scale', [(0, OFF), (0.3, OFF), (0.4, ON), (1.2, ON)])
K(acc, tape, 'rotation_euler', [(0, (0, 0, 0)), (0.4, (0, 0, 0)), (0.97, (0, TAU, 0)), (1.2, (0, TAU, 0))])
K(acc, s_in, 'location', [(0, STACK), (0.72, STACK), (0.8, (STACK[0], STACK[1], STACK[2] + 0.12)),
                          (0.9, (HOLD[0] + 0.12, HOLD[1], STACK[2] + 0.12)), (1.0, (HOLD[0], HOLD[1], HOLD[2] + 0.03)),
                          (1.06, HOLD), (1.2, HOLD)])
K(acc, s_in, 'rotation_euler', [(0, FLAT), (0.8, FLAT), (0.9, (PI / 2, 0.06, 0)), (1.03, FLAT), (1.2, FLAT)])


# Work (3.0 s): the tape spins on the cradle with the pink line lamp lit, a bead of sound goes down the tube to Wren
# and back, the level needle reads the recording (measure_levels); transcription ends, the temp copy is swept
# (rmtree) and the slip comes up; "heard": H lamp; "transcribed": a post-it; the slip goes into the envelope; the
# hatch lamp lights (a puller on the lane, jsz); the --strict stamp comes down. 0.3 s: spinning, bead in the tube;
# 1.5 s: slip up, post-it flying; 2.7 s: stamp on the envelope, hatch lamp lit.
work = clip('Work', 3.0)
T_SWEEP = 1.18
spin = [(0, (0, TAU, 0))]
for i in range(1, 34):
    t = T_SWEEP * i / 34
    u = t / T_SWEEP
    turns = 4 * (u * u / 0.234375 if u < 0.125 else (u - 0.0625) / 0.9375)   # ease in over 1/8, then constant speed
    spin.append((t, (0, TAU + TAU * turns, 0)))
spin.append((T_SWEEP, (0, 5 * TAU, 0)))
spin.append((3.0, (0, 5 * TAU, 0)))
K(work, tape, 'rotation_euler', spin)
K(work, tape, 'location', [(0, AXLE), (T_SWEEP, AXLE), (T_SWEEP + 0.08, (AXLE[0], AXLE[1], AXLE[2] + 0.08)),
                           (T_SWEEP + 0.16, (AXLE[0], AXLE[1], AXLE[2] + 0.1)), (3.0, (AXLE[0], AXLE[1], AXLE[2] + 0.1))])
K(work, tape, 'scale', [(0, ON), (T_SWEEP, ON), (T_SWEEP + 0.06, S3(1.1)), (T_SWEEP + 0.16, OFF), (3.0, OFF)])
lamp_keys(work, line_lit, 0.08, T_SWEEP)
K(work, bead, 'location', [(0, TUBE[0]), (0.1, TUBE[0]), (0.22, TUBE[1]), (0.32, TUBE[2]), (0.46, TUBE[3]), (0.62, TUBE[4]),
                           (0.7, TUBE[4]), (0.84, TUBE[3]), (0.96, TUBE[2]), (1.04, TUBE[1]), (1.12, TUBE[0]), (3.0, TUBE[0])])
K(work, bead, 'scale', [(0, OFF), (0.06, OFF), (0.12, ON), (0.6, ON), (0.64, S3(0.6)), (0.68, S3(0.6)), (0.72, ON),
                        (1.1, ON), (1.16, OFF), (3.0, OFF)])
ndl = [(0, NEEDLE_REST), (0.1, NEEDLE_REST)]
for i, a_ in enumerate((0.1, -0.25, 0.35, -0.05, 0.5, 0.0, 0.3, -0.2, 0.42, 0.05, 0.25)):
    ndl.append((0.18 + 0.085 * i, (0, a_, 0)))
ndl += [(T_SWEEP + 0.05, NEEDLE_REST), (3.0, NEEDLE_REST)]
K(work, needle, 'rotation_euler', ndl)
lamp_keys(work, status[0], start_on=True)
lamp_keys(work, status[1], start_on=True)
lamp_keys(work, status[2], 1.42)
lamp_keys(work, hatch_lit, 2.12)
sl = rest(slip, 'location')
slip_up = (sl[0], sl[1], PL_TOP + 0.24)
on_env = (HOLD[0], HOLD[1], HOLD[2] + 0.03)
K(work, slip, 'location', [(0, sl), (1.22, sl), (1.4, (slip_up[0], slip_up[1], slip_up[2] + 0.02)), (1.46, slip_up),
                           (1.72, slip_up), (1.88, ((sl[0] + on_env[0]) / 2, (sl[1] + on_env[1]) / 2, slip_up[2] + 0.06)),
                           (2.0, on_env), (2.12, on_env), (2.16, sl), (3.0, sl)])
K(work, slip, 'rotation_euler', [(0, (0, 0, 0)), (1.72, (0, 0, 0)), (1.98, (PI / 2, 0, 0)), (2.12, (PI / 2, 0, 0)),
                                 (2.16, (0, 0, 0)), (3.0, (0, 0, 0))])
K(work, slip, 'scale', [(0, ON), (1.98, ON), (2.12, S3(0.01)), (2.4, S3(0.01)), (2.45, ON), (3.0, ON)])
sheet_flight(work, 1.22)
K(work, stamp, 'rotation_euler', [(0, STAMP_UP), (2.3, STAMP_UP), (2.38, (STAMP_UP[0] - 0.08, 0, 0)), (2.52, (STAMP_DOWN[0] + 0.02, 0, 0)),
                                  (2.56, STAMP_DOWN), (2.62, (STAMP_DOWN[0] - 0.04, 0, 0)), (2.67, STAMP_DOWN), (2.8, STAMP_DOWN),
                                  (2.96, STAMP_UP), (3.0, STAMP_UP)])

# Emit (1.2 s): the envelope lifts off the pad and goes out of the window slot toward the back belt (bb-emit
# command bloodbank.cmd.agent.invocation.invoke); once it is through, the W lamp lights ("working": the agent has
# it) and the hatch lamp goes out; a "dispatched" post-it follows (published after bb-emit returns, iw:2616); the
# board clears for the next memo while this one waits minutes for its agent. 0.12 s: lifting; 0.6 s: in the slot
# (the runtime releases it here); 1.08 s: the post-it at the slot, W lamp lit.
emit = clip('Emit', 1.2)
K(emit, s_out, 'location', [(0, HOLD), (0.12, (HOLD[0], HOLD[1], HOLD[2] + 0.14)), (0.35, P(-0.08, 1.2, SLOT_Z + 0.05)),
                            (0.52, P(0.0, WZ - 0.05, SLOT_Z)), (0.6, P(0.0, WZ + 0.08, SLOT_Z)), (1.08, P(0.0, WZ + 0.6, SLOT_Z + 0.06)),
                            (1.15, P(0.0, WZ + 0.62, SLOT_Z + 0.06)), (1.2, HOLD)])
K(emit, s_out, 'rotation_euler', [(0, FLAT), (1.2, FLAT)])
lamp_keys(emit, hatch_lit, None, 0.66, start_on=True)
lamp_keys(emit, status[3], 0.64, 1.17)
for k in range(3):
    lamp_keys(emit, status[k], None, 1.12 - 0.02 * (2 - k), start_on=True)
sheet_flight(emit, 0.74)

# every animated object is keyed on every path in every clip (held at rest where it does not move), so crossfades
# never fall back to a stale pose and Idle stays seamless
for cl in CLIPS:
    for obj in ANIM:
        for path in PATHS:
            if (cl.name, obj.name, path) not in KEYED:
                cl.hold(obj, path, rest(obj, path))

F.merge(S, 'memo_desk')
