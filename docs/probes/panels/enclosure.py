# A small enclosed gantry (a CoreXY-printer-sized cell). +X right, +Y back, +Z up, mm.
# The proof for part.envelope / part.panel on a boxy machine (ADR-635): a sheet-metal
# style lid with folded edges and side covers, each screwed to the extrusion frame,
# clear of the carriage through its whole travel.
p = params(
    size=num(240, unit="mm", min=200, max=320, step=10, label="Frame outside"),
    height=num(220, unit="mm", min=180, max=300, step=10, label="Frame height"),
)
S, H, E = p.size, p.height, 20.0          # frame outside, height, extrusion

def box(x0, x1, y0, y1, z0, z1):
    x0, x1 = sorted((x0, x1)); y0, y1 = sorted((y0, y1)); z0, z1 = sorted((z0, z1))
    return part.box(x1 - x0, y1 - y0, z1 - z0, origin=(x0, y0, z0))

h = S / 2.0
base = box(-h, h, -h, h, -8, 0)
posts = [box(sx * h - (E if sx > 0 else 0), sx * h + (0 if sx > 0 else E),
             sy * h - (E if sy > 0 else 0), sy * h + (0 if sy > 0 else E), 0, H)
         for sx in (-1, 1) for sy in (-1, 1)]
rails = [box(-h, h, -h, -h + E, H - E, H), box(-h, h, h - E, h, H - E, H),
         box(-h, -h + E, -h, h, H - E, H), box(h - E, h, -h, h, H - E, H)]
frame = part.fuse([base] + posts + rails, label="frame")

# The gantry: two rods across X at mid height, a carriage, a motor at the left.
ZG = H - 70.0
rods = [part.cylinder(4.0, S - 2 * E, origin=(-h + E, y, ZG), direction=(1, 0, 0))
        for y in (-25.0, 25.0)]
mounts = [box(-h + E, -h + E + 12, -40, 40, ZG - 12, ZG + 12),
          box(h - E - 12, h - E, -40, 40, ZG - 12, ZG + 12)]
gantry = part.fuse(rods + mounts, label="gantry")
carriage = part.cut(box(-30, 30, -40, 40, ZG - 14, ZG + 14),
                    [part.cylinder(4.2, 80, origin=(-40, y, ZG), direction=(1, 0, 0))
                     for y in (-25.0, 25.0)], label="carriage")
hotend = part.cylinder(11.0, 45, origin=(0, 0, ZG - 59), label="hotend")
head = part.fuse([carriage, hotend], label="head")
bed = box(-90, 90, -90, 90, 60, 66)
TRAVEL = (-h + E + 12 + 30 + 2, h - E - 12 - 30 - 2)   # carriage centre range along X

# ---- the covers --------------------------------------------------------------
# One envelope round the frame and the gantry, the head swept through its travel.
env = part.envelope([frame, gantry, bed], clearance=1.5, radius="hull", resolution=2.0,
                    motion=[{"shape": head, "direction": (1, 0, 0), "range": TRAVEL}])
screw = lib.bolt("m3", 8)
BED = (256, 256, 256)                      # what each piece must print on
# The lid is wider than the bed: one seam down the middle, a lap of frame under it.
lid = part.panel(env, side=(0, 0, 1), max_angle=40, inset=0.4, thickness=1.5,
                 seams=[((1, 0, 0), [0.0])], frame=frame, screw=screw, screws=3,
                 max_piece=BED, label="lid")
sides, done = {}, [lid]
for name, side, seam in (("left", (-1, 0, 0), (0, 1, 0)), ("right", (1, 0, 0), (0, 1, 0)),
                         ("back", (0, 1, 0), (1, 0, 0))):
    sides[name] = part.panel(env, side=side, max_angle=40, inset=0.4, thickness=1.5,
                             seams=[(seam, [0.0])], frame=frame, screw=screw, screws=3,
                             within=((-h - 30, -h - 30, 2), (h + 30, h + 30, H - 2)),
                             # the back takes the power cable through a gland
                             openings=[{"at": (60.0, h, 40.0), "radius": 8.0}]
                             if name == "back" else (),
                             max_piece=BED, avoid=list(done), label=name)
    done.append(sides[name])

result = {}
comps, joints = [], []

def place(name, shape, appearance, **declared):
    result[name] = shape
    c = assembly.component(shape, appearance=appearance, **declared)
    result["c_" + name] = c
    comps.append(c)
    return c

def jcs(comp, pos, axis=(0, 0, 1)):
    return assembly.connector(comp, "origin", offset={"position": list(pos), "axis": list(axis),
                                                      "angle_degrees": 0.0})

def weld(a, b, pos):
    joints.append(assembly.joint("fixed", jcs(a, pos), jcs(b, pos)))

frame_cut = part.cut(frame, [lid.pilots] + [s.pilots for s in sides.values()])
c_frame = place("frame", frame_cut, "mechanism", grounded=True, role="frame")
c_gantry = place("gantry", gantry, "mechanism")
c_bed = place("bed", bed, "mechanism")
c_head = place("head", head, "accent")
weld(c_frame, c_gantry, (0, 0, ZG))
weld(c_frame, c_bed, (0, 0, 60))
# The slider's axis is the connector's Z: turn it onto +X.
along_x = {"position": [0, 0, ZG], "axis": [0, 1, 0], "angle_degrees": 90.0}
j = assembly.joint("slider", assembly.connector(c_gantry, "origin", offset=along_x),
                   assembly.connector(c_head, "origin", offset=along_x),
                   length_limits_mm=TRAVEL)
joints.append(j)
covered = [c_frame, c_gantry, c_head]
for set_name, panel in [("lid", lid)] + list(sides.items()):
    pieces = {}
    for piece_name, body in zip(panel.names, panel.parts):
        c = place(f"{set_name}_{piece_name}", body, "shell", role="panel", covers=covered)
        weld(c_frame, c, (0, 0, 0))
        pieces[piece_name] = c
    k = 0
    for piece_name in panel.names:
        for _boss in panel.mounts[piece_name]:
            c = place(f"{set_name}_screw_{k}", panel.screws[k].body, "mechanism", role="hardware")
            weld(pieces[piece_name], c, (0, 0, 0))       # a screw is held by what it clamps
            k += 1

for i, v in enumerate(joints):
    result["joint_" + str(i)] = v
result["cell"] = assembly.assembly(comps, joints, sweep_step_mm=20.0,
                                   palette={"shell": "#D9D6CF", "mechanism": "#2E3135",
                                            "accent": "#E8A33A"}, label="cell")
result["solve"] = assembly.solve(result["cell"])
