p = params(
    duct_inner_d=num(32.0, unit="mm", min=30.0, max=42.0, label="Duct inner diameter",
                     description="Clear diameter inside each propeller duct"),
    duct_wall=num(1.2, unit="mm", min=1.0, max=2.0, label="Wall thickness"),
    wheelbase=num(65.0, unit="mm", min=55.0, max=85.0, label="Wheelbase",
                  description="Diagonal motor-to-motor distance"),
    motor_hole_d=num(1.5, unit="mm", min=1.0, max=2.5, label="Motor hole diameter"),
    cam_hole_d=num(10.5, unit="mm", min=4.0, max=13.0, label="Camera hole diameter"),
    duct_height=num(15.0, unit="mm", min=12.0, max=20.0, label="Frame height"),
    plate_t=num(1.6, unit="mm", min=1.2, max=2.5, label="Plate thickness"),
    spoke_w=num(2.5, unit="mm", min=1.0, max=2.5, label="Spoke width"),
    mount_h=num(1.0, unit="mm", min=1.0, max=6.0, label="Motor mount height",
                description="Uniform height of motor hubs and spokes"),
    strut_w=num(3.0, unit="mm", min=2.0, max=10.0, label="Strut width",
                description="Width of the four floor struts"),
    strut_h=num(2.0, unit="mm", min=2.0, max=10.0, label="Strut height",
                description="Vertical thickness of the four floor struts"),
    duct_blend=num(2.0, unit="mm", min=0.2, max=4.0, label="Duct blend radius",
                   description="Fillet where the ducts meet the outer walls"),
    notch_fillet=num(1.5, unit="mm", min=0.0, max=3.0, label="Cut corner fillet",
                     description="Rounding of the top corners of the duct wall openings"),
    strut_fillet=num(1.0, unit="mm", min=0.0, max=3.0, label="Strut joint fillet",
                     description="Rounding of the vertical edges where the FC struts meet the ducts"),
    hub_fillet=num(1.0, unit="mm", min=0.0, max=2.0, label="Spoke joint fillet",
                   description="Rounding of the vertical edges where the spokes meet the motor hubs"),
    duct_top_fillet=num(0.5, unit="mm", min=0.0, max=1.5, label="Duct rim fillet",
                        description="Rounding of the upper inner edge of each duct (capped by wall thickness)"),
    vent_gap=num(8.0, unit="mm", min=4.0, max=15.0, label="Vent spacing",
                 description="Center-to-center distance between the wall vents"),
    vent_w=num(4.0, unit="mm", min=1.0, max=6.0, label="Vent width"),
    vent_h=num(10.0, unit="mm", min=3.0, max=14.0, label="Vent height"),
    vent_round=num(0.5, min=0.0, max=1.0, label="Vent roundness",
                   description="0 = square corners, 1 = fully rounded ends"),
    batt_w=num(7.0, unit="mm", min=3.0, max=14.0, label="Battery slot width"),
    batt_h=num(7.0, unit="mm", min=3.0, max=12.0, label="Battery slot depth",
               description="How far the battery-lead slot reaches down from the top"),
    batt_round=num(1.0, min=0.0, max=1.0, label="Battery slot roundness",
                   description="0 = square slot, 1 = fully rounded bottom and top corners"),
    fc_z=num(0.0, unit="mm", min=0.0, max=6.0, label="FC lift",
             description="Extra clearance of the flight controller board above the struts"),
    fc_pattern=num(25.5, unit="mm", min=20.0, max=31.0, label="FC hole pattern",
                   description="Square mounting hole pattern of the flight controller"),
)

r_in = p.duct_inner_d / 2.0
w = p.duct_wall
r_out = r_in + w
s = p.wheelbase * 0.7071067811865476   # duct center spacing (wheelbase / sqrt(2))
c = s / 2.0                        # duct center coordinate
half = c + r_out                   # outer half-size of the frame
H = p.duct_height  # frame height
t = p.plate_t

centers = [(c, c, 45.0), (-c, c, 135.0), (-c, -c, 225.0), (c, -c, 315.0)]

# ---- outer shell: rounded-square wall + bottom plate ----
outer = part.box(2 * half, 2 * half, H, origin=(-half, -half, 0))
outer = part.fillet(outer, r_out, edges={"direction": [0, 0, 1], "expected_count": 4})
inner = part.box(2 * (half - w), 2 * (half - w), H + 2,
                 origin=(-(half - w), -(half - w), -1))
inner = part.fillet(inner, r_out - w, edges={"direction": [0, 0, 1], "expected_count": 4})
body = part.cut(outer, inner)

# ---- wall cutouts (floor is fully open apart from the four struts) ----
cutters = []
oct_r = c - 8.0
peg_y = p.fc_pattern * 0.7071067811865476  # posts on the axes -> 25.5x25.5 square on the 45-deg board

# camera hole in front wall
cutters.append(part.cylinder(p.cam_hole_d / 2.0, w + 2, origin=(0, -half - 1, H / 2.0),
                             direction=(0, 1, 0)))
# slotted diagonal vents in the side walls
sl_w, sl_len = p.vent_w, p.vent_h
slot = part.box(w + 2, sl_w, sl_len, origin=(0, -sl_w / 2.0, -sl_len / 2.0))
vr = 0.499 * min(sl_w, sl_len) * p.vent_round
if vr > 0.05:
    slot = part.fillet(slot, vr, edges={"direction": [1, 0, 0], "expected_count": 4})
slot = part.transform(slot, rotation_axis=(1, 0, 0), rotation_degrees=45.0)
# battery-lead slot: rounded cut dropping from the top of the back wall
bs_w, bs_h = p.batt_w, p.batt_h
batt = part.box(bs_w, w + 2, bs_h + 8, origin=(-bs_w / 2.0, half - w - 1, H - bs_h))
br = 0.499 * min(bs_w, 2.0 * bs_h) * p.batt_round
if br > 0.05:
    batt = part.fillet(batt, br, edges={"direction": [0, 1, 0], "expected_count": 4})
cutters.append(batt)
for vy in (-p.vent_gap, 0.0, p.vent_gap):
    v = part.transform(slot, translation=(half - w - 1, vy, H / 2.0))
    cutters.append(v)
    cutters.append(part.mirror(v, (0, 0, 0), (1, 0, 0)))

# ---- fuse solid duct cylinders, then bore the prop openings through ----
# ---- floor struts: four bridges spanning duct-to-duct, carrying the pegs ----
st_w = p.strut_w
post_h = 3.0
post_top = H - 6.0            # post top face 6 mm below duct top
strut_z = post_top - post_h - p.strut_h
strut = part.box(2 * c, st_w, p.strut_h, origin=(-c, peg_y - st_w / 2.0, strut_z))
struts = [part.transform(strut, rotation_degrees=a) for a in (0.0, 90.0, 180.0, 270.0)]
body = part.fuse([body] + [part.cylinder(r_out, H, origin=(cx, cy, 0))
                           for cx, cy, b in centers])
delta = (r_out * r_out - r_in * r_in) ** 0.5
wall_y = half - w
for sx in (1.0, -1.0):
    for sy in (1.0, -1.0):
        for px, py in ((sx * (c - delta), sy * wall_y),
                       (sx * wall_y, sy * (c - delta))):
            body = part.fillet(body, p.duct_blend,
                               edges={"geometry_type": "Line",
                                      "direction": [0, 0, 1],
                                      "near_point": [px, py, H / 2.0],
                                      "max_distance": 1.0,
                                      "expected_count": 1})
body = part.cut(body, cutters)
# round the top corners where the battery slot meets the wall's top edge
if br > 0.05:
    for bx in (bs_w / 2.0, -bs_w / 2.0):
        body = part.fillet(body, br,
                           edges={"geometry_type": "Line",
                                  "direction": [0, 1, 0],
                                  "near_point": [bx, half - w / 2.0, H],
                                  "max_distance": 0.5,
                                  "expected_count": 1})
body = part.fuse([body] + struts)
body = part.cut(body, [part.cylinder(r_in, H + 2, origin=(cx, cy, -1))
                       for cx, cy, b in centers])

# ---- open the lower inner wall of each duct between its two inward spokes ----
notch_h = strut_z + 1.0
notch = part.cylinder(r_out + 2.0, notch_h, origin=(0, 0, -1), angle=120.0)
notch = part.cut(notch, part.cylinder(r_in - 0.5, notch_h + 2, origin=(0, 0, -2)))
keep = part.box(r_out + 3.0, p.spoke_w, notch_h + 4, origin=(0, -p.spoke_w / 2.0, -2))
notch = part.cut(notch, [keep, part.transform(keep, rotation_degrees=120.0)])
nf = p.notch_fillet
if nf > 0.05:
    rm = (r_in - 0.5 + r_out + 2.0) / 2.0
    zt = notch_h - 1.0
    c120, s120 = -0.5, 0.8660254037844386
    sy = p.spoke_w / 2.0
    for d, pt in (([-1, 0, 0], [rm, sy, zt]),
                  ([-c120, -s120, 0],
                   [rm * c120 + sy * s120, rm * s120 - sy * c120, zt])):
        notch = part.fillet(notch, nf,
                            edges={"geometry_type": "Line",
                                   "direction": d,
                                   "near_point": pt,
                                   "max_distance": 1.0,
                                   "expected_count": 1})
body = part.cut(body, [part.transform(notch,
                                      rotation_degrees=base + 120.0,
                                      translation=(cx, cy, 0))
                       for cx, cy, base in centers])

# ---- fillet the vertical edges where the struts meet the duct outer walls ----
sf = p.strut_fillet
if sf > 0.05:
    zm = strut_z + p.strut_h / 2.0
    pts = []
    for ys in (peg_y - st_w / 2.0, peg_y + st_w / 2.0):
        dxe = (r_out * r_out - (c - ys) ** 2) ** 0.5
        for xe in (c - dxe, -c + dxe):
            pts.append((xe, ys))
    for k in range(4):
        for x0, y0 in pts:
            for _ in range(k):
                x0, y0 = -y0, x0
            body = part.fillet(body, sf,
                               edges={"geometry_type": "Line",
                                      "direction": [0, 0, 1],
                                      "near_point": [x0, y0, zm],
                                      "max_distance": 0.6,
                                      "expected_count": 1})

# ---- fillet the upper inner rim of each duct ----
tf = min(p.duct_top_fillet, w - 0.1)
if tf > 0.05:
    for cx, cy, b in centers:
        body = part.fillet(body, tf,
                           edges={"geometry_type": "Circle",
                                  "radius": r_in,
                                  "near_point": [cx, cy, H],
                                  "max_distance": 1.0,
                                  "expected_count": 1})

# ---- motor hubs with tri-spokes ----
adds = [body]
holes = []
sw = p.spoke_w
mh = p.mount_h
for cx, cy, base in centers:
    adds.append(part.cylinder(4.5, mh, origin=(cx, cy, 0)))
    adds.append(part.cylinder(3.6, mh, origin=(cx, cy, 0)))
    for k in range(3):
        ang = base + 120.0 * k
        spoke = part.box(r_in + 0.8 - 3.8, sw, mh, origin=(cx + 3.8, cy - sw / 2.0, 0))
        adds.append(part.transform(spoke, rotation_degrees=ang, pivot=(cx, cy, 0)))
        hole = part.cylinder(p.motor_hole_d / 2.0, mh + 2, origin=(cx + 3.3, cy, -1))
        holes.append(part.transform(hole, rotation_degrees=ang, pivot=(cx, cy, 0)))
    holes.append(part.cylinder(2.0, mh + 2, origin=(cx, cy, -1)))

# ---- posts on the struts between the ducts ----
for px, py in ((0, peg_y), (0, -peg_y), (peg_y, 0), (-peg_y, 0)):
    adds.append(part.cylinder(1.2, post_h, origin=(px, py, strut_z + t)))

frame_solid = part.fuse(adds)
# fillet the vertical edges where each tri-spoke meets its motor hub
hf = p.hub_fillet
if hf > 0.05:
    for cx, cy, base in centers:
        frame_solid = part.fillet(frame_solid, hf,
                                  edges={"geometry_type": "Line",
                                         "direction": [0, 0, 1],
                                         "near_point": [cx, cy, mh / 2.0],
                                         "max_distance": 4.75,
                                         "expected_count": 6})
frame = part.cut(frame_solid, holes, label="whoop_frame")

# ---- imported flight controller board ----
fc = mesh.import_file("flight-controller.stl", label="Flight controller")
# raw import bottom sits at z = -0.2; seat the board on the strut tops,
# rotated 45 deg so its corner notches wrap the four posts
fc = mesh.transform(fc, rotation_degrees=45.0,
                    translation=(0, 0, strut_z + p.strut_h + 0.2 + p.fc_z))

# ---- imported 1S battery pack ----
fc_top = strut_z + p.strut_h + p.fc_z + 2.5   # top face of the imported board
# raw STL is in mm, lying flat, long axis along y, body bottom at z=-0.33,
# lead wires trailing off the -y end: spin it so the leads face the
# battery slot in the back wall (+y), seat it on the FC top
battery = mesh.import_file("1s-battery.stl", label="battery")
battery = mesh.transform(battery, scale=(1.0, 68.0 / 74.5515, 1.0),
                         rotation_degrees=180.0,
                         translation=(0, 1.5, fc_top + 0.33))

print("oct_r", oct_r, "peg_y", peg_y, "c", c, "half", half)
try:
    print("peg_r", peg_r)
except:
    pass
try:
    print("peg_d", peg_d)
except:
    pass
try:
    print("peg_h", peg_h)
except:
    pass
try:
    print("peg_x", peg_x)
except:
    pass
try:
    print("pegs", pegs)
except:
    pass
try:
    print("post_r", post_r)
except:
    pass
try:
    print("post_h", post_h)
except:
    pass
try:
    print("posts", posts)
except:
    pass
try:
    print("boss_r", boss_r)
except:
    pass
try:
    print("standoff", standoff)
except:
    pass
try:
    print("oct_pts", oct_pts)
except:
    pass
try:
    print("hub_r", hub_r)
except:
    pass
try:
    print("mount_r", mount_r)
except:
    pass
try:
    print("hole_r", hole_r)
except:
    pass
# ---- imported ESP32 module ----
# raw STL is in meters and standing on its long edge: scale x1000,
# tip it flat (rot +90 about X), seat bottom at z=0 and center its footprint
esp32 = mesh.import_file("esp32.stl", label="ESP32")
esp32 = mesh.transform(esp32, scale=1000.0,
                       rotation_axis=(1, 0, 0), rotation_degrees=90.0,
                       translation=(-2.5677, -6.1114, 0.25))
# flip it component-side down and tuck it under the flight controller
fc_bot = strut_z + p.strut_h + p.fc_z    # underside of the FC board
esp32 = mesh.transform(esp32, rotation_axis=(1, 0, 0), rotation_degrees=180.0,
                       translation=(0, 0, fc_bot))

# ---- imported range finder module ----
# raw STL is in meters, standing on its long edge: scale x1000, lay flat,
# seat bottom at z=0 with footprint centered, then slide it into the waist
# between the two +x ducts, long axis along y, beside the ESP32,
# flipped sensor-side down
rangef = mesh.import_file("range-finder.stl", label="Range finder")
rangef = mesh.transform(rangef, scale=1000.0,
                        rotation_axis=(1, 0, 0), rotation_degrees=90.0,
                        translation=(0, 0, 1.0))
rangef = mesh.transform(rangef, rotation_axis=(1, 0, 0), rotation_degrees=180.0)
rangef = mesh.transform(rangef, rotation_degrees=90.0,
                        translation=(c - 4.0, 0, 4.0))

# ---- imported 0702 motors on the four mounts ----
# raw STL is in mm, shaft up, base at z=0 with a small stub below and the
# wire tab pointing +y; seat each base on its hub top (z = mount_h) and spin
# the tab to face the frame center so the wires route inward to the FC
motor_raw = mesh.import_file("0702-motor.stl", label="Motor")
motors = {}
for i, (mx, my, mbase) in enumerate(centers):
    motors["motor_%d" % (i + 1)] = mesh.transform(
        motor_raw, rotation_degrees=mbase + 90.0, translation=(mx, my, mh))

# ---- imported props on the motor shafts ----
# raw STL is a 3-blade prop in mm, hub bore at the origin, axis along +y,
# ~125.5 mm diameter: scale it to fit the duct with ~0.5 mm tip clearance,
# stand it up (axis y -> z), then seat each hub flush with its shaft tip
prop_raw = mesh.import_file("prop.stl", label="Prop")
prop_s = (p.duct_inner_d - 1.0) / 125.5
prop_up = mesh.transform(prop_raw, scale=prop_s,
                         rotation_axis=(1, 0, 0), rotation_degrees=90.0)
shaft_tip = p.mount_h + 12.75          # raw motor shaft tip is 12.75 above its base
prop_z = shaft_tip - 7.557 * prop_s    # hub top (raw y=7.557) flush with shaft tip
props = {}
for i, (mx, my, mbase) in enumerate(centers):
    props["prop_%d" % (i + 1)] = mesh.transform(
        prop_up, rotation_degrees=mbase, translation=(mx, my, prop_z))

# ---- imported camera module ----
# raw STL is in mm: square board on top (z up to 5), lens barrel pointing -z
# (tip at z=-7). Tip it to face forward (-y) and slide the barrel into the
# camera hole in the front wall, lens tip flush with the outer face
camera = mesh.import_file("c03-camera.stl", label="Camera")
camera = mesh.transform(camera, rotation_axis=(1, 0, 0), rotation_degrees=-90.0,
                        translation=(0, -half + 7.0, H / 2.0))

# ---- wiring harness: routed, not authored ----
# Every port is a (point, direction) pair: a place on a component's surface
# and the way the wire leaves it. The points are literals read off the
# imported components' bounding boxes -- a pick resolves to the same pair.
# A cable never lists the two components it lands on, because a port sits on
# their surface and the search would start inside an obstacle. The flight
# controller stays out of every list for a second reason: its board is a
# square turned 45 degrees, so the bounding box a mesh obstacle is tested by
# is half air.
k = 0.7071067811865476
fc_mid = fc_bot + 1.25              # mid-thickness of the imported FC board
fc_edge = 9.0                       # where the 45-degree board edge runs
esp_face, esp_mid = 11.3, 3.8       # the ESP32's +/-x faces, at mid-height
rf_face = c - 9.3                   # the range finder's -x face
mot_face = 5.14                     # motor body inner face, off its axis

wires = {}
wires["wire_batt_fc"] = part.cable(
    ((5.7, 12.0, fc_top + 2.5), (1, 0, 0)),        # battery pack, +x face
    ((fc_edge, fc_edge, fc_mid), (k, k, 0)),       # FC board, +x+y edge
    gauge_mm=0.8, clearance_mm=0.6, avoid=[frame, esp32, rangef],
    label="battery lead")
wires["wire_fc_esc"] = part.cable(
    ((-fc_edge, -fc_edge, fc_mid), (-k, -k, 0)),   # FC board, -x-y edge
    ((-esp_face, -4.0, esp_mid), (-1, 0, 0)),      # ESP32, -x face
    gauge_mm=0.8, clearance_mm=0.6, avoid=[frame, battery, rangef],
    label="FC to ESP32")
wires["wire_esc_rf"] = part.cable(
    ((esp_face, -4.0, esp_mid), (1, 0, 0)),        # ESP32, +x face
    ((rf_face, 6.0, 2.0), (-1, 0, 0)),             # range finder, -x face
    gauge_mm=0.8, clearance_mm=0.6, avoid=[frame, battery, fc],
    label="ESP32 to range finder")

# the four motor leads: out of each hub, in through its duct notch, up to the
# FC board edge facing it
for i, (mx, my, mbase) in enumerate(centers):
    sx, sy = (1.0 if mx > 0 else -1.0), (1.0 if my > 0 else -1.0)
    others = [m for j, m in enumerate(motors.values()) if j != i]
    wires["wire_motor_%d" % (i + 1)] = part.cable(
        ((mx - sx * mot_face, my - sy * 2.5, mh + 1.0), (-sx, 0, 0)),
        ((sx * fc_edge, sy * fc_edge, fc_mid), (sx * k, sy * k, 0)),
        gauge_mm=0.8, clearance_mm=0.6,
        avoid=[frame, battery, esp32, rangef] + others,
        label="motor %d lead" % (i + 1))

result = {"frame": frame, "flight_controller": fc, "battery": battery,
          "camera": camera, "esp32": esp32, "range_finder": rangef,
          **motors, **props, **wires}