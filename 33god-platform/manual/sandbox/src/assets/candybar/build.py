# candybar: the clock. Blender (bpy) build for the Factory asset contract (forge/CONTRACT.md).
# Deterministic: no randomness, no timestamps. Blender axes: metres, Z up, FRONT (faces the belt and the planner's
# desk) is -Y, the right side (+X) carries the chore chart and, under it, the dispatcher's punch clock. See NOTES.md.
#
# The floor's two cameras split the story: the overview looks at the FRONT (face, cuckoo door, bell: the heartbeat),
# the station camera (`?at=candybar`, src/content.ts) looks at the RIGHT side (chart and punch clock: the dispatcher).
#
# Clips: Idle / Accept / Work / Emit are the contract's (the dispatcher's cycle). Work_S / Work_H / Work_N are Work
# for a chore on another runner kind (Driver.tsx rotates them in the registry's proportions); Strike is the
# heartbeat's tick, played by Driver.tsx for the sim's `tick fired` visit, its post-it on a fourth empty, socket_tick.
# The pendulum and the face's hands are not keyed in any clip: the Driver runs them on the floor's own time.
# The whole tower stays under 5.8 m: the verifier caps a manifest's height at 6 m.
import math

import factory as F

PI = math.pi
TAU = 2 * PI


def M(name, color, rough=0.65, **kw):
    return F.mat(name, color, rough=rough, **kw)


red = M('clock', F.C.get('clock', '#B23A48'), 0.6)           # the Triggers zone's red (C.clock = domain colour)
red_dk = M('clock_dark', '#7E2733', 0.65)
roof_m = M('roof', '#5E1F28', 0.7)
cream = M('trim', F.C.get('wall', '#EFE6D4'), 0.7)
concrete = M('concrete', '#A39C8F', 0.8)
dark = M('dark', '#2A2418', 0.7)
glass = M('window', '#231C24', 0.5)
brass = M('brass', '#D4A017', 0.45, metal=0.5)
wood = M('door', '#7A5236', 0.75)
steel = M('steel', '#9AA3AF', 0.5, metal=0.4)                 # the ram: light steel, so it reads against the red sleeve
steel_dk = M('steel_dark', '#3A4250', 0.6, metal=0.2)
tin = M('tin', '#D3CBB8', 0.55, metal=0.2)                    # tray and chute: light, so the yellow copy and kraft envelope read
board_m = M('board', '#33302C', 0.75)
paper = M('card', '#F4EFE6', 0.7)
teal = M('hermes', F.C.get('crew', '#2F7F7A'), 0.6)
grey = M('n8n', F.C.get('rules', '#6B7280'), 0.65)
go = M('in_green', '#2E9E5B', 0.6)
lamp_green = M('lamp_green', '#22C55E', 0.5, emit='#22C55E', strength=3.0)
scan_m = M('scanner', '#FBBF24', 0.5, emit='#F59E0B', strength=2.5)
ink = M('ink', '#8E1F2E', 0.6)
body_m = M('punch_body', '#E8DCC2', 0.65)

S = []  # static parts, merged into one mesh at the end


def b(name, size, loc, m, bevel=0.02, seg=1, rot=(0, 0, 0)):
    o = F.box(name, size, loc, m, bevel=bevel, segments=seg, rot=rot)
    S.append(o)
    return o


def c(name, r, depth, loc, m, verts=16, bevel=0.01, rot=(0, 0, 0), top=None):
    o = F.cyl(name, r, depth, loc, m, verts=verts, bevel=bevel, rot=rot, radius_top=top)
    S.append(o)
    return o


ANIM = []   # every object a clip moves: keyed on every path in every clip
REST = {}


def anim(o):
    ANIM.append(o)
    REST[o.name] = {'location': tuple(o.location), 'rotation_euler': tuple(o.rotation_euler), 'scale': tuple(o.scale)}
    return o


FACE_Y = -0.75      # the tower's front wall; the pilasters stand proud to -0.80, the floor's sign hangs at -0.82
FRONT = (PI / 2, 0, 0)  # a disc facing the front
TOWER_TOP = 4.5

# ------------------------------------------------------------------ plinth and tower
b('plinth', (2.1, 2.1, 0.2), (0, 0, 0.1), concrete, 0.03)
b('tower', (1.5, 1.5, TOWER_TOP - 0.2), (0, 0, (TOWER_TOP + 0.2) / 2), red, 0.03)
for sx in (-1, 1):
    for sy in (-1, 1):
        b(f'pilaster{sx}{sy}', (0.2, 0.2, TOWER_TOP - 0.2), (sx * 0.7, sy * 0.7, (TOWER_TOP + 0.2) / 2), red_dk, 0.02)
b('base_course', (1.66, 1.66, 0.18), (0, 0, 0.29), cream, 0.02)
b('band_mid', (1.64, 1.64, 0.08), (0, 0, 2.5), cream, 0.015)
b('cornice', (1.78, 1.78, 0.16), (0, 0, TOWER_TOP + 0.04), cream, 0.02)

# front, bottom to top: the door, (the floor's sign, 1.15-1.65 m), the pendulum window, the face, the cuckoo house
b('door_frame', (0.7, 0.04, 0.92), (0, FACE_Y - 0.005, 0.66), cream, 0.01)
b('door', (0.56, 0.06, 0.82), (0, FACE_Y - 0.02, 0.61), wood, 0.01)
c('door_knob', 0.03, 0.05, (0.19, FACE_Y - 0.06, 0.6), brass, verts=10, rot=FRONT)
b('pend_frame', (0.6, 0.04, 0.78), (0, FACE_Y - 0.005, 2.07), cream, 0.01)
b('pend_glass', (0.48, 0.05, 0.66), (0, FACE_Y - 0.015, 2.07), glass, 0.005)
c('pend_bracket', 0.04, 0.06, (0, FACE_Y - 0.04, 2.36), brass, verts=10, rot=FRONT)

FACE_Z = 3.1
c('face_bezel', 0.56, 0.07, (0, FACE_Y - 0.035, FACE_Z), dark, verts=32, bevel=0.015, rot=FRONT)
c('face_dial', 0.5, 0.03, (0, FACE_Y - 0.075, FACE_Z), cream, verts=32, bevel=0.005, rot=FRONT)
for k in range(12):
    a = k * TAU / 12
    big = k % 3 == 0
    r = 0.41 if big else 0.43
    b(f'face_tick{k}', (0.05 if big else 0.028, 0.012, 0.12 if big else 0.06),
      (r * math.sin(a), FACE_Y - 0.095, FACE_Z + r * math.cos(a)), dark, 0, rot=(0, a, 0))
c('face_cap', 0.04, 0.04, (0, FACE_Y - 0.14, FACE_Z), brass, verts=12, rot=FRONT)

# the cuckoo house: a brass-gabled doorway above the dial (as on a real cuckoo clock), with a brass perch under it
DOOR_Z = 4.05
b('cuckoo_frame', (0.78, 0.05, 0.72), (0, FACE_Y - 0.01, DOOR_Z), cream, 0.01)
b('cuckoo_hole', (0.66, 0.05, 0.62), (0, FACE_Y - 0.02, DOOR_Z), glass, 0.005)
for sx in (-1, 1):
    b(f'gable{sx}', (0.56, 0.12, 0.07), (sx * 0.22, -0.9, 4.56), brass, 0.015, rot=(0, sx * 0.5, 0))
c('gable_knob', 0.05, 0.06, (0, -0.93, 4.71), brass, verts=12, rot=FRONT)
b('perch', (0.62, 0.36, 0.04), (0, FACE_Y - 0.19, 3.7), brass, 0.01)
b('perch_lip', (0.62, 0.03, 0.06), (0, FACE_Y - 0.36, 3.73), brass, 0.008)
for sx in (-1, 1):
    b(f'perch_bracket{sx}', (0.035, 0.24, 0.035), (sx * 0.22, FACE_Y - 0.13, 3.655), brass, 0.006, rot=(-0.35, 0, 0))

# the hands: Driver.tsx turns them from the floor's own clock (hoursNow), like the primitive did.
# Rest pose reads 8:00, the floor's START_HOUR, so a still frame matches the stage.
hour = F.empty('hand_hour', (0, FACE_Y - 0.105, FACE_Z), rot=(0, 8 / 12 * TAU, 0))
F.merge([F.box('hour_bar', (0.075, 0.014, 0.3), (0, 0, 0.12), dark, bevel=0.005, parent=hour)], 'hand_hour_mesh')
minute = F.empty('hand_minute', (0, FACE_Y - 0.125, FACE_Z))
F.merge([F.box('minute_bar', (0.045, 0.014, 0.45), (0, 0, 0.18), dark, bevel=0.005, parent=minute)], 'hand_minute_mesh')

# belfry: posts, yoke, eave, pyramid roof, finial (top of the finial ball 5.79 m)
DECK = TOWER_TOP + 0.12
for sx in (-1, 1):
    for sy in (-1, 1):
        b(f'belfry_post{sx}{sy}', (0.15, 0.15, 0.6), (sx * 0.7, sy * 0.7, DECK + 0.3), red_dk, 0.02)
b('bell_yoke', (0.1, 1.4, 0.08), (0, 0, 5.19), red_dk, 0.015)
b('eave', (1.9, 1.9, 0.08), (0, 0, 5.26), red_dk, 0.02)
c('roof', 1.34, 0.32, (0, 0, 5.46), roof_m, verts=4, bevel=0.01, rot=(0, 0, PI / 4), top=0.0)
c('finial_stem', 0.025, 0.12, (0, 0, 5.67), brass, verts=8)
S.append(F.sphere('finial_ball', 0.05, (0, 0, 5.74), brass, segments=12, rings=8))

# ------------------------------------------------------------------ the chore chart (the registry), right side +X
CX = 0.79
ROWS = (3.84, 3.52, 3.2, 2.88)
COLS = (-0.46, -0.23, 0.0, 0.23, 0.46)
b('chart_frame', (0.05, 1.3, 1.44), (CX, 0, 3.36), cream, 0.01)
b('chart_board', (0.05, 1.18, 1.32), (CX + 0.01, 0, 3.36), board_m, 0.005)
b('chart_header', (0.06, 1.3, 0.1), (CX + 0.005, 0, 4.14), red_dk, 0.01)
for sy in (-1, 1):
    b(f'scan_rail{sy}', (0.03, 0.03, 1.34), (CX + 0.06, sy * 0.62, 3.36), steel_dk, 0.005)

# 20 cards drawn for the registry's 139 jobs, striped by runner kind. The record gives no split; the manifests on disk
# (2026-11-21, deduplicated by name: 57 systemd, 33 exec, 12 hermes, 12 n8n of 114) give 10 / 6 / 2 / 2.
KINDS = 'SESSH' 'SESEN' 'SSESE' 'NSHES'
STRIPE = {'E': red, 'S': dark, 'H': teal, 'N': grey}
assert (KINDS.count('S'), KINDS.count('E'), KINDS.count('H'), KINDS.count('N')) == (10, 6, 2, 2)
# one card per runner kind can come due; E is krebs-tick (exec, */10: the record's first wire), the one Work plays
DUE = {'E': (1, 3), 'S': (2, 0), 'H': (0, 4), 'N': (3, 0)}
for k, (ri, ci) in DUE.items():
    assert KINDS[ri * 5 + ci] == k
CARD = (0.02, 0.21, 0.28)
due_cards = {}
for ri, z in enumerate(ROWS):
    b(f'chart_ledge{ri}', (0.04, 1.16, 0.025), (CX + 0.035, 0, z - 0.155), steel_dk, 0.004)
    for ci, y in enumerate(COLS):
        k = KINDS[ri * 5 + ci]
        if DUE.get(k) == (ri, ci):
            e = anim(F.empty(f'card_due_{k}', (CX + 0.045, y, z)))
            F.merge([F.box(f'due_card_{k}', CARD, (0, 0, 0), paper, bevel=0.004, parent=e),
                     F.box(f'due_stripe_{k}', (0.01, CARD[1], 0.1), (0.013, 0, 0.09), STRIPE[k], bevel=0, parent=e),
                     F.box(f'due_line_{k}', (0.006, 0.14, 0.02), (0.012, 0, -0.04), steel_dk, bevel=0, parent=e)],
                    f'card_due_{k}_mesh')
            due_cards[k] = e
            continue
        b(f'card{ri}{ci}', CARD, (CX + 0.045, y, z), paper, 0.004)
        b(f'stripe{ri}{ci}', (0.01, CARD[1], 0.1), (CX + 0.058, y, z + 0.09), STRIPE[k], 0)
        b(f'line{ri}{ci}', (0.006, 0.14, 0.02), (CX + 0.057, y, z - 0.04), steel_dk, 0)

SCAN_TOP = ROWS[0] + 0.17
SCAN_BOT = ROWS[-1] - 0.17
scanner = anim(F.empty('scanner', (CX + 0.085, 0, SCAN_TOP)))
F.merge([F.box('scan_bar', (0.06, 1.24, 0.07), (0, 0, 0), scan_m, bevel=0.01, parent=scanner),
         F.box('scan_shoe_l', (0.06, 0.06, 0.09), (0, -0.62, 0), steel_dk, bevel=0.01, parent=scanner),
         F.box('scan_shoe_r', (0.06, 0.06, 0.09), (0, 0.62, 0), steel_dk, bevel=0.01, parent=scanner)], 'scanner_mesh')

# ------------------------------------------------------------------ the dispatcher's punch clock, right foot, under the chart
# A big light cabinet with a press on top, so the dispatcher's clips read against the red tower from the station camera
PX, PY = 1.33, -0.15
TOP = 1.45
PW, PD = 0.9, 1.1            # cabinet width (x) and depth (y)
PLATE_Y = PY - 0.1
PF = PY - PD / 2             # the cabinet's front face
b('punch_footing', (PW + 0.12, PD + 0.12, 0.2), (PX, PY, 0.1), concrete, 0.02)
b('punch_body', (PW, PD, TOP - 0.2), (PX, PY, (TOP + 0.2) / 2), body_m, 0.03)
b('punch_band', (PW + 0.02, PD + 0.02, 0.08), (PX, PY, 0.36), red, 0.01)
b('punch_band_top', (PW + 0.02, PD + 0.02, 0.07), (PX, PY, TOP - 0.1), red, 0.01)
b('punch_top', (PW + 0.04, PD + 0.04, 0.04), (PX, PY, TOP + 0.02), steel_dk, 0.01)
b('plate', (0.7, 0.72, 0.025), (PX, PLATE_Y, TOP + 0.05), paper, 0.005)
c('punch_dial_rim', 0.22, 0.02, (PX, PF - 0.01, 0.8), dark, verts=24, bevel=0.004, rot=FRONT)
c('punch_dial', 0.19, 0.03, (PX, PF - 0.02, 0.8), paper, verts=24, bevel=0.005, rot=FRONT)
b('punch_dial_hand', (0.025, 0.01, 0.15), (PX, PF - 0.04, 0.855), red, 0)
b('punch_slot', (0.46, 0.02, 0.035), (PX, PF - 0.005, 1.08), dark, 0)
# the press: two posts at the back, a crossbar, a beam out over the plate and the ram's sleeve; the lamp on top
for sx in (-1, 1):
    b(f'press_post{sx}', (0.1, 0.1, 0.76), (PX + sx * 0.36, PY + 0.45, TOP + 0.42), steel_dk, 0.015)
b('press_cross', (0.84, 0.12, 0.12), (PX, PY + 0.45, TOP + 0.8), steel_dk, 0.02)
b('press_beam', (0.14, 0.6, 0.12), (PX, PY + 0.16, TOP + 0.8), steel_dk, 0.02)
b('press_sleeve', (0.2, 0.2, 0.18), (PX, PLATE_Y, TOP + 0.8), red_dk, 0.02)
c('lamp_base', 0.08, 0.05, (PX, PLATE_Y, TOP + 0.915), dark, verts=12)

# the ram: light steel head smaller than the copy (0.42 m), so the copy shows round it when it comes down
stamp = anim(F.empty('stamp', (PX, PLATE_Y, TOP + 0.5)))
F.merge([F.cyl('stamp_rod', 0.035, 0.42, (0, 0, 0.21), steel, verts=10, bevel=0, parent=stamp),
         F.box('stamp_head', (0.3, 0.3, 0.12), (0, 0, -0.06), steel, bevel=0.025, parent=stamp),
         F.box('stamp_collar', (0.16, 0.16, 0.07), (0, 0, 0.035), red, bevel=0.015, parent=stamp),
         F.box('stamp_pad', (0.24, 0.14, 0.02), (0, 0, -0.13), ink, bevel=0.004, parent=stamp)], 'stamp_mesh')

lamp = anim(F.sphere('lamp', 0.1, (PX, PLATE_Y, TOP + 1.0), lamp_green, segments=14, rings=8))

# the in-tray: hinged at the cabinet's front edge, it dips when the copy lands in it; a green lip says IN
tray = anim(F.empty('in_tray', (PX, PF, TOP - 0.16)))
F.merge([F.box('tray_floor', (0.66, 0.44, 0.025), (0, -0.22, 0), tin, bevel=0.005, parent=tray),
         F.box('tray_lip', (0.68, 0.03, 0.09), (0, -0.43, 0.045), go, bevel=0.006, parent=tray),
         F.box('tray_side_l', (0.025, 0.44, 0.07), (-0.33, -0.22, 0.035), tin, bevel=0.005, parent=tray),
         F.box('tray_side_r', (0.025, 0.44, 0.07), (0.33, -0.22, 0.035), tin, bevel=0.005, parent=tray)], 'in_tray_mesh')
b('tray_bracket', (0.5, 0.05, 0.14), (PX, PF - 0.01, TOP - 0.23), steel_dk, 0.01)

# the envelope chute: a light slide with red rails (OUT) off the plate's right edge, down and out to +X, standing on
# a cream pedestal; a lip at its foot holds the envelope until the floor takes it
CHUTE_TILT = 0.6
CL = 0.6
cx0 = PX + 0.37
cmid = (cx0 + CL / 2 * math.cos(CHUTE_TILT), PLATE_Y, TOP + 0.03 - CL / 2 * math.sin(CHUTE_TILT))
b('chute', (CL, 0.66, 0.03), cmid, tin, 0.006, rot=(0, CHUTE_TILT, 0))
for sy in (-1, 1):
    b(f'chute_rail{sy}', (CL + 0.02, 0.035, 0.12), (cmid[0], cmid[1] + sy * 0.33, cmid[2] + 0.05), red, 0.008, rot=(0, CHUTE_TILT, 0))
cend_x = cx0 + CL * math.cos(CHUTE_TILT)
cend_z = TOP + 0.03 - CL * math.sin(CHUTE_TILT)
b('chute_stop', (0.035, 0.66, 0.1), (cend_x + 0.01, PLATE_Y, cend_z + 0.05), red, 0.008)
b('chute_pedestal', (0.22, 0.5, cend_z - 0.06), (cend_x - 0.1, PLATE_Y, (cend_z - 0.06) / 2), body_m, 0.02)
b('chute_pedestal_band', (0.24, 0.52, 0.07), (cend_x - 0.1, PLATE_Y, 0.36), red, 0.01)

flap = anim(F.empty('out_flap', (PX + 0.36, PLATE_Y, TOP + 0.05)))
F.merge([F.box('flap_plate', (0.03, 0.66, 0.22), (0, 0, 0.11), red_dk, bevel=0.006, parent=flap)], 'out_flap_mesh')

# plain faces get windows: the left (-X) and the back (+Y)
for zc in (2.07, 3.55):
    b(f'win_l_frame{zc}', (0.04, 0.5, 0.66), (-0.755, 0, zc), cream, 0.01)
    b(f'win_l_glass{zc}', (0.05, 0.38, 0.54), (-0.765, 0, zc), glass, 0.005)
    b(f'win_b_frame{zc}', (0.5, 0.04, 0.66), (0, 0.755, zc), cream, 0.01)
    b(f'win_b_glass{zc}', (0.38, 0.05, 0.54), (0, 0.765, zc), glass, 0.005)

# ------------------------------------------------------------------ the heartbeat: bell, hammer, pendulum, cuckoo doors
# The bell and the hammer hang on mounts turned to the front-left diagonal, so the hammer swings across the
# overview and station cameras instead of toward them.
DIAG = (0, 0, -3 * PI / 4)   # a mount's +X points front-left, out of the belfry's open corner
DX, DY = math.cos(DIAG[2]), math.sin(DIAG[2])
bell_mount = F.empty('bell_mount', (0, 0, 5.17), rot=DIAG)
bell = anim(F.empty('bell', (0, 0, 0), parent=bell_mount))
F.merge([F.cyl('bell_crown', 0.06, 0.1, (0, 0, -0.03), brass, verts=10, bevel=0.01, parent=bell),
         F.cyl('bell_body', 0.36, 0.4, (0, 0, -0.26), brass, verts=24, bevel=0.02, radius_top=0.16, parent=bell),
         F.cyl('bell_lip', 0.38, 0.05, (0, 0, -0.46), brass, verts=24, bevel=0.015, parent=bell),
         F.sphere('bell_clapper', 0.06, (0, 0, -0.44), dark, segments=10, rings=6, parent=bell)], 'bell_mesh')

HAM_R = 0.66
hammer_mount = F.empty('hammer_mount', (0, 0, 5.12), rot=DIAG)
hammer = anim(F.empty('hammer', (HAM_R, 0, 0), parent=hammer_mount))
F.merge([F.box('hammer_arm', (0.06, 0.06, 0.36), (0, 0, -0.17), steel_dk, bevel=0.01, parent=hammer),
         F.cyl('hammer_head', 0.11, 0.26, (-0.05, 0, -0.38), steel_dk, verts=16, bevel=0.015, rot=(0, PI / 2, 0), parent=hammer),
         F.cyl('hammer_face', 0.115, 0.03, (-0.19, 0, -0.38), brass, verts=16, bevel=0.006, rot=(0, PI / 2, 0), parent=hammer)],
        'hammer_mesh')
b('hammer_hanger', (0.12, 0.12, 0.1), (HAM_R * DX, HAM_R * DY, 5.15), red_dk, 0.015)
b('hammer_strut', (0.95, 0.08, 0.06), (0.5 * DX, 0.5 * DY, 5.2), red_dk, 0.01, rot=(0, 0, DIAG[2]))

# the pendulum: the heartbeat's sleep-until-the-minute; Driver.tsx swings it on real time (not keyed in any clip)
pend = F.empty('pendulum', (0, FACE_Y - 0.07, 2.36))
F.merge([F.box('pend_rod', (0.025, 0.015, 0.36), (0, 0, -0.18), brass, bevel=0.004, parent=pend),
         F.cyl('pend_bob', 0.1, 0.035, (0, 0, -0.4), brass, verts=20, bevel=0.008, rot=FRONT, parent=pend)], 'pendulum_mesh')

DOOR_Y = FACE_Y - 0.04
door_l = anim(F.empty('cuckoo_door_l', (-0.33, DOOR_Y, DOOR_Z)))
F.merge([F.box('door_l_leaf', (0.33, 0.03, 0.6), (0.165, 0, 0), red_dk, bevel=0.008, parent=door_l),
         F.box('door_l_inlay', (0.21, 0.01, 0.42), (0.165, -0.018, 0), cream, bevel=0.004, parent=door_l)], 'cuckoo_door_l_mesh')
door_r = anim(F.empty('cuckoo_door_r', (0.33, DOOR_Y, DOOR_Z)))
F.merge([F.box('door_r_leaf', (0.33, 0.03, 0.6), (-0.165, 0, 0), red_dk, bevel=0.008, parent=door_r),
         F.box('door_r_inlay', (0.21, 0.01, 0.42), (-0.165, -0.018, 0), cream, bevel=0.004, parent=door_r)], 'cuckoo_door_r_mesh')

# ------------------------------------------------------------------ sockets
FLAT = (PI / 2, 0, 0)                      # a post-it, copy or envelope lying flat
CATCH = (PX, PF - 0.23, TOP - 0.1)         # in the in-tray, in front of the punch clock
HOLD = (PX, PLATE_Y, TOP + 0.1)            # flat on the reading plate, under the ram
CHUTE_END = (cend_x - 0.24, PLATE_Y, cend_z + 0.16)  # resting against the stop at the chute's foot
TICK_IN = (0, FACE_Y + 0.12, 3.99)         # inside the tower, behind the cuckoo doors
TICK_OUT = (0, FACE_Y - 0.24, 3.99)        # standing on the perch, facing front

s_in = anim(F.socket('socket_in', CATCH))
s_in.rotation_euler = FLAT
REST[s_in.name]['rotation_euler'] = FLAT
s_hold = F.socket('socket_hold', HOLD)
s_hold.rotation_euler = FLAT
s_out = anim(F.socket('socket_out', HOLD))
s_out.rotation_euler = FLAT
REST[s_out.name]['rotation_euler'] = FLAT
s_tick = anim(F.socket('socket_tick', TICK_IN))

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


# Idle (4 s): the heartbeat sleeps until the next minute and the dispatcher's durable clip waits on the belt: the lamp
# breathes, the scanner idles at the top row, the bell sways a hair (the pendulum swings, from the Driver)
idle = clip('Idle', 4.0)
K(idle, lamp, 'scale', [(i * 0.5, S3(1 + 0.3 * F.ease_loop(i * 0.5, 2.0))) for i in range(9)])
K(idle, scanner, 'location', [(i * 0.5, off(scanner, (0, 0, 0.035 * math.sin(TAU * i * 0.5 / 4)))) for i in range(9)])
K(idle, bell, 'rotation_euler', [(i * 0.5, (0, 0.04 * math.sin(TAU * i * 0.5 / 4), 0)) for i in range(9)])

# Accept (1.0 s): the planner's tick copy lands in the in-tray (durable candybar-dispatcher-ticks), the tray dips,
# the lamp blinks twice, the copy slides up onto the reading plate under the ram
acc = clip('Accept', 1.0)
K(acc, s_in, 'location', [(0, CATCH), (0.32, CATCH), (0.38, (CATCH[0], CATCH[1], CATCH[2] - 0.04)), (0.5, CATCH),
                          (0.7, (PX, PF - 0.02, TOP + 0.24)), (0.88, HOLD), (1.0, HOLD)])
K(acc, tray, 'rotation_euler', [(0, (0, 0, 0)), (0.32, (0, 0, 0)), (0.39, (0.22, 0, 0)), (0.5, (-0.07, 0, 0)), (0.6, (0.03, 0, 0)), (0.72, (0, 0, 0)), (1.0, (0, 0, 0))])
K(acc, lamp, 'scale', [(0, S3(1)), (0.34, S3(1)), (0.42, S3(1.7)), (0.52, S3(1)), (0.6, S3(1.5)), (0.72, S3(1)), (1.0, S3(1))])


# Work (2.0 s, loops): match this minute against every card on the chart. The scanner sweeps all four rows; the due
# card steps out as the bar crosses it; the press winds up and the ram prints the safe-to-repeat code (candybar id +
# tick minute) on the copy (Driver.tsx draws the mark); the ram lifts, the card goes back, the scanner returns.
SWEEP = (0.05, 0.85)   # the bar's run from the top row to the bottom


def make_work(name, kind):
    w = clip(name, 2.0)
    top_, bot_ = rest(scanner, 'location'), off(scanner, (0, 0, SCAN_BOT - SCAN_TOP))
    K(w, scanner, 'location', [(0, top_), (SWEEP[0], top_), (SWEEP[1], bot_), (1.2, bot_), (1.85, top_), (2.0, top_)], 'LINEAR')
    card = due_cards[kind]
    row = DUE[kind][0]
    t_cross = SWEEP[0] + (SWEEP[1] - SWEEP[0]) * (SCAN_TOP - ROWS[row]) / (SCAN_TOP - SCAN_BOT)
    cd = rest(card, 'location')
    cout = off(card, (0.42, 0, 0.06))
    K(w, card, 'location', [(0, cd), (t_cross, cd), (t_cross + 0.14, cout), (1.5, cout), (1.68, cd), (2.0, cd)])
    K(w, card, 'rotation_euler', [(0, (0, 0, 0)), (t_cross, (0, 0, 0)), (t_cross + 0.14, (0, 0, -0.5)), (1.5, (0, 0, -0.5)), (1.68, (0, 0, 0)), (2.0, (0, 0, 0))])
    st = rest(stamp, 'location')
    K(w, stamp, 'location', [(0, st), (0.82, st), (0.94, off(stamp, (0, 0, 0.08))), (1.02, off(stamp, (0, 0, -0.25))),
                             (1.2, off(stamp, (0, 0, -0.25))), (1.45, st), (2.0, st)])
    K(w, lamp, 'scale', [(0, S3(1)), (1.0, S3(1)), (1.06, S3(1.5)), (1.2, S3(1)), (2.0, S3(1))])
    return w


work = make_work('Work', 'E')
for k in ('S', 'H', 'N'):
    make_work(f'Work_{k}', k)

# Emit (1.0 s): the out flap drops, the envelope (bloodbank.cmd.cron.candybar.invoke) slides off the plate and down
# the chute to its stop; the runtime hands it to the floor at half time, which sticks it on the back belt for the hands
emit = clip('Emit', 1.0)
K(emit, flap, 'rotation_euler', [(0, (0, 0, 0)), (0.06, (0, 0, 0)), (0.2, (0, 1.45, 0)), (0.7, (0, 1.45, 0)), (0.86, (0, -0.06, 0)), (0.94, (0, 0.02, 0)), (1.0, (0, 0, 0))])
TILTED = (PI / 2, CHUTE_TILT, 0)
K(emit, s_out, 'location', [(0, HOLD), (0.08, HOLD), (0.24, (PX + 0.42, PLATE_Y, TOP + 0.08)), (0.46, CHUTE_END),
                            (0.52, (CHUTE_END[0] + 0.02, CHUTE_END[1], CHUTE_END[2] - 0.012)), (1.0, (CHUTE_END[0] + 0.02, CHUTE_END[1], CHUTE_END[2] - 0.012))])
K(emit, s_out, 'rotation_euler', [(0, FLAT), (0.16, FLAT), (0.3, TILTED), (1.0, TILTED)])
K(emit, lamp, 'scale', [(0, S3(1)), (0.45, S3(1)), (0.52, S3(1.5)), (0.65, S3(1)), (1.0, S3(1))])

# Strike (2.2 s, Driver only): the heartbeat publishes bloodbank.evt.cron.tick.fired. The hammer winds back, holds,
# strikes the bell twice, the bell swings away and settles, the cuckoo doors open, the tick post-it rides out onto the
# perch and stands there (Driver hands it to the floor at 1.4 s), the doors close behind it
strike = clip('Strike', 2.2)
K(strike, hammer, 'rotation_euler', [(0, (0, 0, 0)), (0.12, (0, -0.42, 0)), (0.24, (0, -0.42, 0)), (0.32, (0, 0.24, 0)), (0.4, (0, 0.04, 0)),
                                     (0.52, (0, -0.36, 0)), (0.6, (0, 0.24, 0)), (0.7, (0, 0.04, 0)), (0.9, (0, 0, 0)), (2.2, (0, 0, 0))])
K(strike, bell, 'rotation_euler', [(0, (0, 0, 0)), (0.32, (0, 0, 0)), (0.42, (0, 0.15, 0)), (0.54, (0, -0.05, 0)), (0.6, (0, 0.02, 0)), (0.7, (0, 0.16, 0)),
                                   (0.84, (0, -0.12, 0)), (1.0, (0, 0.08, 0)), (1.18, (0, -0.05, 0)), (1.38, (0, 0.025, 0)), (1.6, (0, -0.008, 0)), (2.2, (0, 0, 0))])
K(strike, door_l, 'rotation_euler', [(0, (0, 0, 0)), (0.38, (0, 0, 0)), (0.56, (0, 0, -1.8)), (0.64, (0, 0, -1.65)), (1.6, (0, 0, -1.7)),
                                     (1.85, (0, 0, 0.05)), (1.92, (0, 0, 0)), (2.2, (0, 0, 0))])
K(strike, door_r, 'rotation_euler', [(0, (0, 0, 0)), (0.38, (0, 0, 0)), (0.56, (0, 0, 1.8)), (0.64, (0, 0, 1.65)), (1.6, (0, 0, 1.7)),
                                     (1.85, (0, 0, -0.05)), (1.92, (0, 0, 0)), (2.2, (0, 0, 0))])
K(strike, s_tick, 'location', [(0, TICK_IN), (0.5, TICK_IN), (0.9, TICK_OUT), (0.98, (0, TICK_OUT[1] + 0.025, TICK_OUT[2])), (1.04, TICK_OUT), (2.2, TICK_OUT)])

# every animated object is keyed on every path in every clip (held at rest where it does not move), so crossfades
# never fall back to a stale pose and Idle stays seamless
for cl in CLIPS:
    for obj in ANIM:
        for path in PATHS:
            if (cl.name, obj.name, path) not in KEYED:
                cl.hold(obj, path, rest(obj, path))

F.merge(S, 'clock_tower')
