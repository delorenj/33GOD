# turn-enricher: the tagging desk. Blender (bpy) build for the Factory asset contract (forge/CONTRACT.md).
# Deterministic: no randomness, no timestamps. Blender axes: metres, Z up, FRONT (toward the floor's sign and the
# belt's side of the room) is -Y. P(x, zf, up) takes the floor's own model axes (x right, zf toward the front, up)
# and returns Blender's, so every number below can be checked against layout.ts and Props.tsx directly.
#
# Right half: the turn-enricher (bloodbank/services/turn-enricher/main.py): an in-tray and a reading lectern (the
# copy of a `turn completed` post-it, main.py:68), a desk phone, Jev's signal gauge with its own "on the line" lamp
# (line 1, main.py:73; red under the 0.5 threshold, green over it, main.py:92), the facts board with its own lamp
# (line 2, Clairic on Cloudflare, main.py:164; action / 4 artifacts / blocker, main.py:96 and 176-193) and a pad of
# post-its with a pen carriage (the `turn annotated` post-it out, main.py:69). No clip wire: main.py reads with a
# core nc.subscribe (no durable, no ack). The desk has no clerk: the service is a program, not a person.
# Left half, on its own plinth: the station's other member, the Candystore enricher, drawn as the primitive
# `Cataloguer` drew it (ochre desk, ochre clerk, green Dapr runner); it never moves.
#
# Clips: Idle / Accept / Work / Emit are the contract's. Work and Work_B are the two turns the waybills recorded
# (codex-ls.waybill.json: signal 0.86, artifacts ["ls"]; claude-readme.waybill.json: signal 0.55, four artifacts;
# blocker null in both); Driver.tsx picks the one that matches a waybill's own turn, else alternates.
# The forge's frames land on 0.1 / 0.5 / 0.9 of each clip (Work: 0.25 s line 1 and the needle rising, 1.25 s line 2
# and the board filling, 2.25 s the pen writing), so the key poses do.
import math

import bmesh

import factory as F

PI = math.pi
TAU = 2 * PI


def P(x, zf, up):
    """the floor's model axes (x right, zf front, up) -> Blender (x, -zf, up)"""
    return (x, -zf, up)


def M(name, color, rough=0.65, **kw):
    return F.mat(name, color, rough=rough, **kw)


purple = M('memory', F.DOMAIN_COLOR or '#7C4DBA', 0.6)          # the Memory zone's purple (SET_DOMAIN.cataloguer)
purple_dk = M('memory_dark', '#55347F', 0.65)
purple_lt = M('memory_light', '#9C7BD0', 0.6)
board_m = M('board', '#8F72C4', 0.7)
top_m = M('worktop', F.C.get('wall', '#EFE6D4'), 0.7)
trim = M('trim', F.C.get('trim', '#C9BBA2'), 0.8)
tin = M('tin', '#D3CBB8', 0.55, metal=0.2)
wood = M('lectern', F.C.get('wood', '#9A6A45'), 0.7)
dark = M('dark', '#2A2418', 0.7)
iron = M('iron', '#45403A', 0.6, metal=0.2)                     # warm dark grey: blue is the belt's alone
face_m = M('dial', '#F4EFE6', 0.6)
red_arc = M('noise_red', '#C2413A', 0.6)
green_arc = M('signal_green', '#2E9E5B', 0.6)
card = M('card', '#FFFFFF', 0.6)
art_m = M('artifact', '#FFF1BF', 0.6)
blocker_m = M('blocker', '#B91C1C', 0.6)
needle_m = M('needle', '#16130E', 0.5)
post_m = M('post', F.C.get('post', '#FFD84D'), 0.8)
bulb_m = M('reading_bulb', '#FFE7A8', 0.4, emit='#FFD27A', strength=3.0)
line_m = M('line_lamp', '#FFB020', 0.4, emit='#FFA000', strength=4.0)
lamp_off = M('lamp_glass', '#6B4A12', 0.4)
ochre = M('enricher', '#A16207', 0.65)                         # Props.tsx Cataloguer: desk and clerk
ochre_lt = M('enricher_top', '#C08A2E', 0.7)
runner_m = M('runner', '#65A30D', 0.65)                        # Props.tsx Cataloguer: the Dapr runner
skin = M('skin', F.C.get('skin', '#E9C9A8'), 0.8)
paper = M('paper', '#F2EBDD', 0.75)

S = []  # static parts, merged into one mesh at the end


def b(name, size, loc, m, bevel=0.015, seg=1, rot=(0, 0, 0)):
    o = F.box(name, size, loc, m, bevel=bevel, segments=seg, rot=rot)
    S.append(o)
    return o


def c(name, r, depth, loc, m, verts=16, bevel=0.008, rot=(0, 0, 0), top=None):
    o = F.cyl(name, r, depth, loc, m, verts=verts, bevel=bevel, rot=rot, radius_top=top)
    S.append(o)
    return o


ANIM = []   # every object a clip moves: keyed on every path in every clip
REST = {}


def anim(o):
    ANIM.append(o)
    REST[o.name] = {'location': tuple(o.location), 'rotation_euler': tuple(o.rotation_euler), 'scale': tuple(o.scale)}
    return o


def open_tube(o):
    """drop a cylinder's caps (hidden inside a capsule's end spheres): big caps bend the smooth side normals dark"""
    bm = bmesh.new()
    bm.from_mesh(o.data)
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if abs(f.normal.z) > 0.9], context='FACES')
    bm.to_mesh(o.data)
    bm.free()
    return o


def person(name, x, zf, m, scale=1.0):
    """Props.tsx Person: a capsule (r 0.2, length 0.55, centre 0.55 up) and a head (r 0.19, 1.18 up)"""
    k = scale
    open_tube(c(f'{name}_body', 0.2 * k, 0.55 * k, P(x, zf, 0.55 * k + 0.08), m, verts=16, bevel=0))
    for dz in (-1, 1):
        S.append(F.sphere(f'{name}_cap{dz}', 0.2 * k, P(x, zf, (0.55 + dz * 0.275) * k + 0.08), m, segments=16, rings=8))
    S.append(F.sphere(f'{name}_head', 0.19 * k, P(x, zf, 1.18 * k + 0.08), skin, segments=16, rings=10))


FLAT = (PI / 2, 0, 0)          # a post-it or copy lying flat
TOP = 0.97                     # the tagging desk's worktop surface
PLINTH = 0.08
HALF_POST = 0.035              # half the thickness of the floor's post-it (Moving.tsx LOOK.post 0.07)

# ------------------------------------------------------------------ two plinths: one desk each
b('plinth_enricher', (1.34, 1.44, PLINTH), (-1.11, 0.23, PLINTH / 2), trim, 0.02)
b('plinth_tagging', (2.0, 1.44, PLINTH), (0.66, 0.23, PLINTH / 2), trim, 0.02)

# ------------------------------------------------------------------ the Candystore enricher's corner (static, as Props.tsx drew it)
EX, EZ = -1.0, -0.1
b('enr_desk', (0.8, 0.72, 0.74), P(EX, EZ, PLINTH + 0.37), ochre, 0.03)
b('enr_top', (0.86, 0.78, 0.05), P(EX, EZ, PLINTH + 0.765), ochre_lt, 0.015)
ENR_TRAY = P(-0.9, 0.02, PLINTH + 0.8)
b('enr_tray', (0.46, 0.4, 0.015), (ENR_TRAY[0], ENR_TRAY[1], ENR_TRAY[2]), paper, 0.004)   # a flat blotter, not an in-tray
for k in range(3):   # the summaries it has written, in a short stack
    b(f'enr_sheet{k}', (0.26, 0.32, 0.012), P(-1.26, -0.24 + 0.01 * k, PLINTH + 0.8 + 0.013 * k), paper, 0.002, rot=(0, 0, 0.08 * k))
person('enr_clerk', EX, -0.72, ochre)
person('enr_runner', -1.58, 0.3, runner_m, 0.85)
RUNNER_OUT = P(-1.58, 0.3, 1.3)   # Driver.tsx hands the enricher's summary to the floor from here

# ------------------------------------------------------------------ the tagging desk (the turn-enricher)
DX0, DX1, DZ0, DZ1 = 0.1, 1.6, -0.58, 0.3
DCX, DCZ = (DX0 + DX1) / 2, (DZ0 + DZ1) / 2
b('desk_kick', (DX1 - DX0 - 0.08, DZ1 - DZ0 - 0.08, 0.1), P(DCX, DCZ, PLINTH + 0.05), purple_dk, 0.01)
b('desk_body', (DX1 - DX0, DZ1 - DZ0, TOP - 0.05 - PLINTH - 0.1), P(DCX, DCZ, (TOP - 0.05 + PLINTH + 0.1) / 2), purple, 0.03)
b('desk_top', (DX1 - DX0 + 0.08, DZ1 - DZ0 + 0.08, 0.05), P(DCX, DCZ, TOP - 0.025), top_m, 0.015)
for k, zc in enumerate((0.73, 0.45)):   # drawer fronts on the right (the left half sits behind the floor's sign)
    b(f'drawer{k}', (0.62, 0.03, 0.22), P(1.2, DZ1 + 0.01, zc), purple_lt, 0.012)
    b(f'drawer_pull{k}', (0.18, 0.03, 0.03), P(1.2, DZ1 + 0.035, zc + 0.04), dark, 0.008)

# the in-tray, front-left: the copy of each `turn completed` post-it lands here (purple lip: this desk's IN)
TRAY = P(0.33, 0.12, TOP + 0.02)
tray = anim(F.empty('in_tray', TRAY))
F.merge([F.box('tray_floor', (0.48, 0.44, 0.02), (0, 0, 0), tin, bevel=0.005, parent=tray),
         F.box('tray_lip', (0.5, 0.03, 0.08), (0, -0.22, 0.035), purple_dk, bevel=0.006, parent=tray),
         F.box('tray_back', (0.5, 0.025, 0.07), (0, 0.22, 0.03), tin, bevel=0.005, parent=tray),
         F.box('tray_side_l', (0.025, 0.44, 0.06), (-0.24, 0, 0.03), tin, bevel=0.004, parent=tray),
         F.box('tray_side_r', (0.025, 0.44, 0.06), (0.24, 0, 0.03), tin, bevel=0.004, parent=tray)], 'in_tray_mesh')

# the reading lectern, centre: a slope 30 degrees toward the front with a lip that holds the copy
LX, LZ, LH, TILT = 0.84, -0.2, 1.13, 0.52
b('lectern_post', (0.14, 0.14, LH - TOP - 0.02), P(LX, LZ - 0.04, (LH + TOP - 0.02) / 2), wood, 0.01)
b('lectern_foot', (0.4, 0.3, 0.03), P(LX, LZ - 0.04, TOP + 0.015), wood, 0.01)
b('lectern_slope', (0.52, 0.44, 0.03), P(LX, LZ, LH), wood, 0.01, rot=(TILT, 0, 0))
lip_zf = LZ + 0.22 * math.cos(TILT)
b('lectern_lip', (0.52, 0.03, 0.05), P(LX, lip_zf + 0.01, LH - 0.22 * math.sin(TILT) + 0.02), dark, 0.006)
HOLD = P(LX, LZ + (0.015 + HALF_POST) * math.sin(TILT), LH + (0.015 + HALF_POST) * math.cos(TILT))
HOLD_ROT = (PI / 2 + TILT, 0, 0)

# the gauge post at the back-left, carrying Jev's signal gauge and the reading lamp's arm
GX, GZ = 0.45, -0.5
POST_TOP = 1.9
c('gauge_post', 0.035, POST_TOP - TOP, P(GX, GZ - 0.07, (POST_TOP + TOP) / 2), iron, verts=12, bevel=0)
c('gauge_post_foot', 0.09, 0.03, P(GX, GZ - 0.07, TOP + 0.015), iron, verts=16)
# the reading lamp: an arm from the post out over the lectern, a shade, and a bulb that breathes
LAMP = P(LX - 0.04, LZ + 0.02, 1.52)
arm_from = P(GX, GZ - 0.07, 1.56)
adx, ady = LAMP[0] - arm_from[0], LAMP[1] - arm_from[1]
alen = math.hypot(adx, ady)
b('lamp_arm', (alen, 0.03, 0.03), ((LAMP[0] + arm_from[0]) / 2, (LAMP[1] + arm_from[1]) / 2, 1.56), iron, 0.006,
  rot=(0, 0, math.atan2(ady, adx)))
c('lamp_shade', 0.13, 0.12, (LAMP[0], LAMP[1], LAMP[2] + 0.02), purple_dk, verts=18, bevel=0.005, top=0.05)
bulb = anim(F.sphere('reading_bulb', 0.06, (LAMP[0], LAMP[1], LAMP[2] - 0.05), bulb_m, segments=12, rings=8))


def line_lamp(name, loc, parent):
    """an 'on the line' lamp: a dark glass dome that a lit bulb swells over while that line's call is open"""
    dome = F.sphere(f'{name}_glass', 0.07, loc, lamp_off, segments=14, rings=8, parent=parent)
    lit = anim(F.sphere(name, 0.08, loc, line_m, segments=14, rings=8, parent=parent))
    lit.scale = (0.01, 0.01, 0.01)
    REST[lit.name]['scale'] = (0.01, 0.01, 0.01)
    return dome, lit


# ---- Jev's signal gauge: a meter in a purple housing, turned a little to the right so the station camera
# (front-left), the overview (front-right) and the forge's clip camera (65 degrees right) all see its face
YAW = 0.25
G = P(GX, GZ, 2.15)
gauge = F.empty('gauge_mount', G, rot=(0, 0, YAW))
GP = []   # gauge parts, parented to the mount (local x right, -y toward the front, z up)


def gp(o):
    GP.append(o)
    return o


gp(F.box('g_housing', (0.98, 0.12, 0.58), (0, 0, 0), purple_dk, bevel=0.03, parent=gauge))
gp(F.box('g_back', (0.9, 0.02, 0.5), (0, 0.065, 0), purple, bevel=0.005, parent=gauge))
gp(F.box('g_face', (0.88, 0.02, 0.48), (0, -0.065, 0), face_m, bevel=0.005, parent=gauge))
gp(F.box('g_hood', (1.02, 0.18, 0.04), (0, -0.03, 0.31), purple_dk, bevel=0.01, parent=gauge))
PIV_Z = -0.18
R_ARC = 0.34
SWEEP = 80 * PI / 180            # value 0 -> -80 deg, 0.5 -> straight up, 1 -> +80 deg


def theta(v):
    return (v - 0.5) * 2 * SWEEP


N_SEG = 14
for k in range(N_SEG):
    v = (k + 0.5) / N_SEG
    a = theta(v)
    gp(F.box(f'g_arc{k}', (0.072, 0.012, 0.06), (R_ARC * math.sin(a), -0.078, PIV_Z + R_ARC * math.cos(a)),
             red_arc if v < 0.5 else green_arc, bevel=0, rot=(0, a, 0), parent=gauge))
for v in (0.0, 0.25, 0.75, 1.0):
    a = theta(v)
    gp(F.box(f'g_tick{v}', (0.014, 0.01, 0.05), ((R_ARC - 0.065) * math.sin(a), -0.08, PIV_Z + (R_ARC - 0.065) * math.cos(a)),
             dark, bevel=0, rot=(0, a, 0), parent=gauge))
gp(F.box('g_threshold', (0.03, 0.014, 0.17), (0, -0.084, PIV_Z + R_ARC - 0.02), dark, bevel=0, parent=gauge))
gp(F.cyl('g_pivot_boss', 0.05, 0.02, (0, -0.08, PIV_Z), dark, verts=14, bevel=0.004, rot=(PI / 2, 0, 0), parent=gauge))
g_dome, lamp_line1 = line_lamp('line_lamp1', (-0.4, -0.02, 0.38), gauge)   # line 1: Jev
GP.append(g_dome)
F.merge(GP, 'gauge_body')

NEEDLE_REST = theta(0.0)
needle = anim(F.empty('needle', (0, -0.095, PIV_Z), parent=gauge, rot=(0, NEEDLE_REST, 0)))
F.merge([F.box('needle_bar', (0.03, 0.012, 0.33), (0, 0, 0.15), needle_m, bevel=0.004, parent=needle),
         F.box('needle_tail', (0.06, 0.012, 0.07), (0, 0, -0.03), needle_m, bevel=0.006, parent=needle),
         F.cyl('needle_cap', 0.032, 0.025, (0, -0.012, 0), iron, verts=12, bevel=0.004, rot=(PI / 2, 0, 0), parent=needle)],
        'needle_mesh')

# ---- the facts board: Clairic's three fields, a row each; light panel, white / cream / red tabs, dark empty slots
BX, BZ, BH, BHALF, BW = 1.34, -0.5, 1.5, 0.45, 0.72
board = F.empty('board_mount', P(BX, BZ, BH), rot=(0, 0, YAW))
BP = []


def bp(o):
    BP.append(o)
    return o


bp(F.box('b_frame', (BW, 0.07, 2 * BHALF), (0, 0, 0), purple_dk, bevel=0.02, parent=board))
bp(F.box('b_panel', (BW - 0.06, 0.02, 2 * BHALF - 0.06), (0, -0.04, 0), board_m, bevel=0.004, parent=board))
leg = BH - BHALF - TOP + 0.02
for sx in (-1, 1):
    bp(F.box(f'b_leg{sx}', (0.06, 0.06, leg), (sx * 0.26, 0.0, -(BHALF + leg / 2) + 0.01), iron, bevel=0.006, parent=board))
ROW_ACTION, ROW_ART, ROW_BLOCK = 0.24, -0.05, -0.33   # hinge heights (local z) of the three rows
for z_, m_ in ((ROW_ACTION, card), (ROW_ART, art_m), (ROW_BLOCK, blocker_m)):
    bp(F.box(f'b_chip{z_}', (0.05, 0.014, 0.16), (-0.295, -0.056, z_ + 0.08), m_, bevel=0.004, parent=board))
    bp(F.box(f'b_rail{z_}', (BW - 0.12, 0.018, 0.02), (0.03, -0.058, z_ - 0.006), purple_dk, bevel=0, parent=board))
b_dome, lamp_line2 = line_lamp('line_lamp2', (-BW / 2 + 0.06, -0.02, BHALF + 0.05), board)   # line 2: Clairic
BP.append(b_dome)
F.merge(BP, 'board_body')

TAB_DOWN = (PI, 0, 0)            # hung below its hinge, dark back to the front: the field is empty
TAB_UP = (0, 0, 0)               # stood up, its face to the front: Clairic gave the field (p_null < 0.5)
TAB_OVER = (-0.08, 0, 0)


def tab(name, u, z_, w, h, face, marks):
    e = anim(F.empty(name, (u, -0.072, z_), parent=board, rot=TAB_DOWN))
    parts = [F.box(f'{name}_face', (w, 0.012, h), (0, -0.007, h / 2), face, bevel=0.005, parent=e),
             F.box(f'{name}_back', (w, 0.006, h), (0, 0.003, h / 2), dark, bevel=0, parent=e)]
    for k, (mz, mw) in enumerate(marks):   # dark strokes: what is written on the card
        parts.append(F.box(f'{name}_mark{k}', (mw, 0.004, 0.03), (0, -0.015, mz), dark, bevel=0, parent=e))
    F.merge(parts, f'{name}_mesh')
    return e


# action: one card (the action Clairic named; one bold stroke, whatever its length)
tab_action = tab('tab_action', 0.03, ROW_ACTION, 0.5, 0.17, card, [(0.085, 0.3)])
# artifacts: four tabs, MAX_ARTIFACTS = 4
tab_art = [tab(f'tab_artifact{i}', -0.18 + i * 0.14, ROW_ART, 0.12, 0.16, art_m, [(0.085, 0.06)]) for i in range(4)]
# blocker: one red tab; neither recorded turn had a blocker, so it only twitches (checked, not accepted)
tab_block = tab('tab_blocker', 0.03, ROW_BLOCK, 0.3, 0.15, blocker_m, [])

# ---- the desk phone, back-left under the gauge: the calls go out on it (the bible's phone line is an HTTPS call)
PH = P(0.3, -0.32, TOP)
b('phone_base', (0.36, 0.28, 0.1), (PH[0], PH[1], TOP + 0.05), dark, 0.025)
b('phone_cradle', (0.3, 0.1, 0.05), (PH[0], PH[1] + 0.04, TOP + 0.12), dark, 0.015)
b('phone_dial', (0.16, 0.012, 0.06), (PH[0], PH[1] - 0.145, TOP + 0.055), tin, 0.004)
handset = anim(F.empty('handset', (PH[0], PH[1] + 0.04, TOP + 0.16)))
F.merge([F.box('hs_bar', (0.34, 0.07, 0.045), (0, 0, 0.02), dark, bevel=0.015, parent=handset),
         F.box('hs_ear', (0.1, 0.11, 0.07), (-0.15, 0, 0.0), dark, bevel=0.025, parent=handset),
         F.box('hs_mouth', (0.1, 0.11, 0.07), (0.15, 0, 0.0), dark, bevel=0.025, parent=handset)], 'handset_mesh')
# the line: a cord off the back of the desk and down to the floor (the call leaves the building)
c('cord_run', 0.014, 0.2, P(PH[0], -0.555, TOP + 0.015), dark, verts=6, bevel=0, rot=(PI / 2, 0, 0))
c('cord_drop', 0.014, TOP - PLINTH, P(PH[0], -0.655, (TOP + PLINTH) / 2), dark, verts=6, bevel=0)

# ---- the pad of post-its, front-right, and the pen carriage that writes on it
PADX, PADZ = 1.38, 0.1
for k in range(6):
    b(f'pad_sheet{k}', (0.52, 0.52, 0.011), P(PADX, PADZ, TOP + 0.006 + 0.011 * k), post_m, 0.002, rot=(0, 0, 0.012 * (k % 3 - 1)))
PAD_TOP = TOP + 0.072
PAD = P(PADX, PADZ, PAD_TOP + HALF_POST)    # the new post-it's centre while it lies on the pad
OUT = P(1.22, 0.42, 1.42)                    # standing at the desk's front-right corner, facing the cameras
OUT_ROT = (0, 0, YAW)

PIVX, PIVZ, PIV_H = 1.58, -0.28, 1.27
c('pen_post', 0.028, PIV_H - TOP, P(PIVX, PIVZ, (PIV_H + TOP) / 2), iron, verts=10, bevel=0)
c('pen_post_foot', 0.07, 0.03, P(PIVX, PIVZ, TOP + 0.015), iron, verts=14)
pv = P(PIVX, PIVZ, PIV_H)
pd = P(PADX, PADZ, PIV_H)
ARM_YAW = math.atan2(pd[1] - pv[1], pd[0] - pv[0])
ARM_LEN = math.hypot(pd[0] - pv[0], pd[1] - pv[1])
pen_mount = F.empty('pen_mount', pv, rot=(0, 0, ARM_YAW))
PEN_REST = (0, -0.3, 0.6)        # tip raised and swung back off the pad
PEN_WIND = (0, -0.38, 0.7)
pen_arm = anim(F.empty('pen_arm', (0, 0, 0), parent=pen_mount, rot=PEN_REST))
F.merge([F.cyl('arm_hub', 0.045, 0.06, (0, 0, 0), purple_dk, verts=12, bevel=0.006, parent=pen_arm),
         F.box('arm_bar', (ARM_LEN + 0.1, 0.035, 0.03), ((ARM_LEN + 0.1) / 2, 0, 0), purple_dk, bevel=0.008, parent=pen_arm)],
        'pen_arm_mesh')
# the pen rides a carriage along the arm (a plotter's pen), so the two lines it writes sit apart
pen = anim(F.empty('pen', (ARM_LEN, 0, 0), parent=pen_arm))
F.merge([F.box('pen_carriage', (0.08, 0.065, 0.06), (0, 0, 0), purple_lt, bevel=0.012, parent=pen),
         F.cyl('pen_body', 0.022, 0.17, (0, 0, -0.08), dark, verts=10, bevel=0.004, parent=pen),
         F.cyl('pen_tip', 0.022, 0.04, (0, 0, -0.185), iron, verts=10, bevel=0, radius_top=0.004, parent=pen)], 'pen_mesh')
PEN_LO = 0.065                   # pitch at which the tip touches the pad's top sheet
PEN_HI = 0.0

# ------------------------------------------------------------------ sockets
CATCH = (TRAY[0], TRAY[1], TRAY[2] + 0.01 + HALF_POST)
s_in = anim(F.socket('socket_in', CATCH))
s_in.rotation_euler = FLAT
REST[s_in.name]['rotation_euler'] = FLAT
s_hold = F.socket('socket_hold', HOLD)
s_hold.rotation_euler = HOLD_ROT
s_out = anim(F.socket('socket_out', PAD))
s_out.rotation_euler = FLAT
REST[s_out.name]['rotation_euler'] = FLAT
# two more empties for the Driver: where the Candystore enricher's copy lands, and where its summary leaves
F.empty('socket_enricher', (ENR_TRAY[0], ENR_TRAY[1], ENR_TRAY[2] + 0.015))
F.empty('socket_runner', RUNNER_OUT)

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


# Idle (4 s): subscribed and waiting. The reading lamp breathes once; the needle trembles on zero (a live meter, four
# trembles); the pen carriage bobs. Keyed every 5 frames, linear, whole cycles only: first key = last key.
idle = clip('Idle', 4.0)
STEPS = 24
tt = [4.0 * i / STEPS for i in range(STEPS + 1)]
K(idle, bulb, 'scale', [(t, S3(1 + 0.4 * F.ease_loop(t, 4.0))) for t in tt], 'LINEAR')
K(idle, needle, 'rotation_euler', [(t, (0, NEEDLE_REST + 0.07 * F.ease_loop(t, 1.0) * (0.5 + 0.5 * F.ease_loop(t, 4.0)), 0)) for t in tt], 'LINEAR')
K(idle, pen_arm, 'rotation_euler', [(t, (0, PEN_REST[1] - 0.06 * F.ease_loop(t, 2.0), PEN_REST[2])) for t in tt], 'LINEAR')

# Accept (1.0 s): the copy lands in the in-tray, the tray gives under it and springs back, then the copy slides up
# onto the lectern. 0.1 s: in the tray; 0.5 s: lifting off it; 0.9 s: on the lectern.
acc = clip('Accept', 1.0)
K(acc, s_in, 'location', [(0, CATCH), (0.4, CATCH), (0.48, off(s_in, (0, 0, 0.03))), (0.66, P(0.58, -0.04, 1.24)), (0.86, HOLD), (1.0, HOLD)])
K(acc, s_in, 'rotation_euler', [(0, FLAT), (0.44, FLAT), (0.86, HOLD_ROT), (1.0, HOLD_ROT)])
K(acc, tray, 'location', [(0, TRAY), (0.3, TRAY), (0.36, off(tray, (0, 0, -0.045))), (0.46, off(tray, (0, 0, 0.015))),
                          (0.55, off(tray, (0, 0, -0.006))), (0.64, TRAY), (1.0, TRAY)])
K(acc, bulb, 'scale', [(0, S3(1)), (0.7, S3(1)), (0.9, S3(1.25)), (1.0, S3(1.25))])


# Work (2.5 s): read, ask Jev (line 1: the gauge's lamp, the needle), ask Clairic (line 2: the board's lamp, the
# tabs), write (the pen). Key poses: 0.25 s line 1 lit and the needle rising; 1.25 s line 2 lit, the needle in the
# green, the action card up; 2.25 s every fact up and the pen on its second line. Board and needle clear at the end,
# so the clip ends where it starts.
def make_work(name, signal, n_art):
    w = clip(name, 2.5)
    K(w, bulb, 'scale', [(0, S3(1.25)), (0.1, S3(1.5)), (2.38, S3(1.5)), (2.5, S3(1.25))])
    hs = rest(handset, 'location')
    up = off(handset, (0.03, -0.02, 0.12))
    UPR = (0.3, -0.25, 0.12)
    K(w, handset, 'location', [(0, hs), (0.03, off(handset, (0, 0, -0.008))), (0.12, off(handset, (0.015, 0, 0.09))), (0.2, up),
                               (0.92, up), (0.96, off(handset, (0.03, -0.02, 0.05))), (1.0, up), (1.86, up), (1.96, hs),
                               (2.0, off(handset, (0, 0, 0.01))), (2.04, hs), (2.5, hs)])
    K(w, handset, 'rotation_euler', [(0, (0, 0, 0)), (0.03, (0, 0, 0)), (0.2, UPR), (1.86, UPR), (1.96, (0, 0, 0)), (2.5, (0, 0, 0))])
    # line 1: Jev's one question, `signal`; the gauge's lamp is lit while the call is open
    K(w, lamp_line1, 'scale', [(0, S3(0.01)), (0.08, S3(0.01)), (0.13, S3(1.15)), (0.2, S3(1)), (0.92, S3(1)), (0.97, S3(0.01)), (2.5, S3(0.01))])
    th = theta(signal)
    K(w, needle, 'rotation_euler', [(0, (0, NEEDLE_REST, 0)), (0.12, (0, NEEDLE_REST, 0)), (0.5, (0, th + 0.1, 0)), (0.6, (0, th - 0.035, 0)),
                                    (0.7, (0, th, 0)), (2.36, (0, th, 0)), (2.48, (0, NEEDLE_REST, 0)), (2.5, (0, NEEDLE_REST, 0))])
    # line 2: Clairic's three fields fill the board; the board's lamp is lit while the call is open
    K(w, lamp_line2, 'scale', [(0, S3(0.01)), (0.98, S3(0.01)), (1.03, S3(1.15)), (1.1, S3(1)), (1.84, S3(1)), (1.89, S3(0.01)), (2.5, S3(0.01))])
    K(w, tab_action, 'rotation_euler', [(0, TAB_DOWN), (1.05, TAB_DOWN), (1.15, TAB_OVER), (1.2, TAB_UP), (2.36, TAB_UP), (2.47, TAB_DOWN), (2.5, TAB_DOWN)])
    for i, t_ in enumerate(tab_art):
        if i < n_art:
            t0 = 1.22 + 0.09 * i
            K(w, t_, 'rotation_euler', [(0, TAB_DOWN), (t0, TAB_DOWN), (t0 + 0.1, TAB_OVER), (t0 + 0.14, TAB_UP), (2.36, TAB_UP), (2.47, TAB_DOWN), (2.5, TAB_DOWN)])
    # the blocker field comes back with p_null >= 0.5: checked, not accepted; the tab twitches and stays down
    K(w, tab_block, 'rotation_euler', [(0, TAB_DOWN), (1.62, TAB_DOWN), (1.68, (PI - 0.4, 0, 0)), (1.76, TAB_DOWN), (2.5, TAB_DOWN)])
    # the pen winds up, swings onto the pad and writes two lines (Driver.tsx reveals them on the new post-it)
    K(w, pen_arm, 'rotation_euler', [(0, PEN_REST), (1.84, PEN_REST), (1.9, PEN_WIND), (2.0, (0, PEN_HI, -0.15)), (2.03, (0, PEN_LO, -0.15)),
                                     (2.13, (0, PEN_LO, 0.13)), (2.15, (0, PEN_HI, 0.13)), (2.18, (0, PEN_HI, -0.15)), (2.2, (0, PEN_LO, -0.15)),
                                     (2.3, (0, PEN_LO, 0.07)), (2.32, (0, PEN_HI, 0.07)), (2.44, PEN_REST), (2.5, PEN_REST)])
    pr = rest(pen, 'location')
    K(w, pen, 'location', [(0, pr), (1.9, pr), (2.0, (ARM_LEN + 0.06, 0, 0)), (2.15, (ARM_LEN + 0.06, 0, 0)), (2.18, (ARM_LEN - 0.05, 0, 0)),
                           (2.32, (ARM_LEN - 0.05, 0, 0)), (2.44, pr), (2.5, pr)])
    return w


work = make_work('Work', 0.86, 1)       # codex-ls.waybill.json: signal 0.86, artifacts ["ls"], blocker null
work_b = make_work('Work_B', 0.55, 4)   # claude-readme.waybill.json: signal 0.55, four artifacts, blocker null

# Emit (1.0 s): the written post-it lifts off the pad, turns upright and stands at the desk's front-right corner,
# facing the cameras; the runtime hands it to the floor at 0.5 s (core nc.publish of
# bloodbank.evt.conversation.turn.annotated). 0.1 s: lifting; 0.5 s: standing; 0.9 s: standing.
emit = clip('Emit', 1.0)
K(emit, s_out, 'location', [(0, PAD), (0.03, P(PADX, PADZ, PAD_TOP + HALF_POST - 0.01)), (0.1, P(PADX, PADZ + 0.02, PAD_TOP + 0.1)),
                            (0.3, P(PADX - 0.04, PADZ + 0.2, 1.36)), (0.44, (OUT[0], OUT[1], OUT[2] + 0.03)), (0.5, OUT), (1.0, OUT)])
K(emit, s_out, 'rotation_euler', [(0, FLAT), (0.06, FLAT), (0.3, (0.35, 0, YAW * 0.8)), (0.5, OUT_ROT), (1.0, OUT_ROT)])
K(emit, bulb, 'scale', [(0, S3(1.25)), (0.4, S3(1.25)), (0.8, S3(1)), (1.0, S3(1))])
K(emit, pen_arm, 'rotation_euler', [(0, PEN_REST), (0.08, (0, PEN_REST[1] - 0.08, PEN_REST[2])), (0.25, PEN_REST), (1.0, PEN_REST)])

# every animated object is keyed on every path in every clip (held at rest where it does not move), so crossfades
# never fall back to a stale pose and Idle stays seamless
for cl in CLIPS:
    for obj in ANIM:
        for path in PATHS:
            if (cl.name, obj.name, path) not in KEYED:
                cl.hold(obj, path, rest(obj, path))

F.merge(S, 'tagging_desk')
