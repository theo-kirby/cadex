# Robot leopard -- QDD creature. +X forward, +Y left, +Z up, mm.
p = params(
    hip_spacing=num(480, unit="mm", min=440, max=560, step=5, label="Hip spacing (front-rear pitch axes)"),
    hip_height=num(380, unit="mm", min=350, max=420, step=5, label="Hip axis height"),
    roll_y=num(50, unit="mm", min=48, max=70, step=1, label="Hip-roll axis offset from centreline"),
    thigh=num(200, unit="mm", min=180, max=240, step=5, label="Thigh / humerus length"),
    fore_shin=num(200, unit="mm", min=180, max=240, step=5, label="Forearm (radius) length"),
    hind_shin=num(220, unit="mm", min=190, max=260, step=5, label="Tibia length"),
    meta=num(95, unit="mm", min=75, max=120, step=5, label="Hind metatarsus length"),
    crank=num(40, unit="mm", min=32, max=50, step=1, label="Knee crank / lever radius"),
    neck_len=num(130, unit="mm", min=110, max=170, step=5, label="Neck length (root to head pivot)"),
    tail1=num(200, unit="mm", min=160, max=240, step=5, label="Tail segment 1 length"),
    tail2=num(240, unit="mm", min=180, max=320, step=5, label="Tail segment 2 length"),
    wall=num(2.5, unit="mm", min=2.0, max=4.0, step=0.5, label="Housing wall"),
)

HX = p.hip_spacing / 2.0
ZH = p.hip_height
PAD_H = 8.0
ANKLE_Z = 40.0
AK70, AK80, AK45 = "cubemars-ak70-10", "cubemars-ak80-9-v3", "cubemars-ak45-10-v3"
L70, L80, L45 = 50.25, 38.5, 45.2
PLATE = 4.5           # housing seat plate
ROLL_OUT = 66.0       # roll output face, inboard of the hip-pitch axis
SPINE_Z = ZH + 20.0

# y stations of the leg stack (left side; the right is its mirror)
Y_PITCH_REAR = p.roll_y + 6.0
Y_PITCH_OUT = Y_PITCH_REAR + L80
Y_KNEE_REAR = Y_PITCH_OUT + 6.0 + PLATE   # 6 mm thigh disc + knee housing plate
YB = Y_KNEE_REAR + L80                    # knee-drive output face

def ik2(hx, hz, fx, fz, l1, l2, knee_forward):
    dx, dz = fx - hx, fz - hz
    d = math.hypot(dx, dz)
    a = (l1 * l1 - l2 * l2 + d * d) / (2.0 * d)
    h = math.sqrt(max(l1 * l1 - a * a, 0.0))
    ux, uz = dx / d, dz / d
    nx, nz = -uz, ux
    if (nx > 0) != knee_forward:
        nx, nz = -nx, -nz
    return (hx + a * ux + h * nx, hz + a * uz + h * nz)

def unit2(a, b):
    dx, dz = b[0] - a[0], b[1] - a[1]
    d = math.hypot(dx, dz)
    return (dx / d, dz / d)

def cyl_y(x, z, y0, y1, r):
    lo, hi = sorted((y0, y1))
    return part.cylinder(r, hi - lo, origin=(x, lo, z), direction=(0, 1, 0))

def box(x0, x1, y0, y1, z0, z1):
    x0, x1 = sorted((x0, x1)); y0, y1 = sorted((y0, y1)); z0, z1 = sorted((z0, z1))
    return part.box(x1 - x0, y1 - y0, z1 - z0, origin=(x0, y0, z0))

def link_y(p0, p1, r0, r1, y0, y1):
    # a tapered link in the XZ plane, round at both ends, extruded across y0..y1
    lo, hi = sorted((y0, y1))
    ux, uz = unit2(p0, p1)
    nx, nz = -uz, ux
    w0, w1 = 0.8 * r0, 0.8 * r1
    pts = [(p0[0] + nx * w0, lo, p0[1] + nz * w0), (p1[0] + nx * w1, lo, p1[1] + nz * w1),
           (p1[0] - nx * w1, lo, p1[1] - nz * w1), (p0[0] - nx * w0, lo, p0[1] - nz * w0)]
    prism = part.extrude(part.face(part.wire(pts, closed=True)), (0, hi - lo, 0))
    return part.fuse([cyl_y(p0[0], p0[1], lo, hi, r0), prism, cyl_y(p1[0], p1[1], lo, hi, r1)])

def zrot_to(d):
    dx, dy, dz = d
    s = math.hypot(dx, dy)
    if s < 1e-9:
        return [1.0, 0.0, 0.0], (0.0 if dz > 0 else 180.0)
    return [-dy / s, dx / s, 0.0], math.degrees(math.atan2(s, dz))

def jcs(comp, pos, d):
    ax, ang = zrot_to(d)
    return assembly.connector(comp, "origin", offset={"position": [float(v) for v in pos], "axis": ax, "angle_degrees": ang})

result = {}
comps = []
joints = []
contacts = []
regions = []

def place(name, shape, appearance, **declared):
    result[name] = shape
    c = assembly.component(shape, appearance=appearance, **declared)
    result["c_" + name] = c
    comps.append(c)
    return c

def weld(name, a, b, pos):
    j = assembly.joint("fixed", jcs(a, pos, (0, 0, 1)), jcs(b, pos, (0, 0, 1)))
    result["w_" + name] = j
    joints.append(j)
    return j

def hinge(name, a, b, pos, axis, limits=None):
    j = assembly.joint("revolute", jcs(a, pos, axis), jcs(b, pos, axis), angle_limits_degrees=limits)
    result["j_" + name] = j
    joints.append(j)
    return j

def bolts(name, screws, holder_c, drive_c):
    # each screw is its own catalog component, welded to the part it clamps, in contact with the part it threads into
    for i, b in enumerate(screws):
        c = place(name + "_" + str(i), b.body, "mechanism")
        weld(name + "_" + str(i), holder_c, c, (0, 0, 0))
        if drive_c is not None:
            contacts.append((c, drive_c))

def cut_all(shape, housings, extra=()):
    tools = []
    for h in housings:
        tools.append(h.cavity)
        tools.extend(h.holes)
    tools.extend(extra)
    return part.cut(shape, tools)

# ---------------- torso: rear half (free base) and front half ----------------
spine = lib.qdd(AK70, origin=(0, L70 / 2.0, SPINE_Z), direction=(0, 1, 0), label="spine")
h_spine = lib.housing(spine, wall=p.wall, plate=PLATE)

NECK_ROOT = (HX + 60.0, ZH + 75.0)
neck_drive = lib.qdd(AK45, origin=(NECK_ROOT[0], L45 / 2.0, NECK_ROOT[1]), direction=(0, 1, 0), label="neck")
h_neck = lib.housing(neck_drive, wall=p.wall, plate=PLATE)

TAIL_PITCH = (-HX - 75.0, ZH + 45.0)
tail_pitch = lib.qdd(AK45, origin=(TAIL_PITCH[0], L45 / 2.0, TAIL_PITCH[1]), direction=(0, 1, 0), label="tail_pitch")
h_tailp = lib.housing(tail_pitch, wall=p.wall, plate=PLATE)

legs = {}
roll_h = {"f": [], "r": []}
for front in (True, False):
    tag = "f" if front else "r"
    s = 1.0 if front else -1.0
    hx = s * HX
    if front:
        A = (hx - 5.0, ANKLE_Z)
        K = ik2(hx, ZH, A[0], A[1], p.thigh, p.fore_shin, knee_forward=False)
        H2 = None
        shin_end = A
    else:
        A = (hx - 15.0, ANKLE_Z)
        t = math.radians(20.0)
        H2 = (A[0] - p.meta * math.sin(t), A[1] + p.meta * math.cos(t))
        K = ik2(hx, ZH, H2[0], H2[1], p.thigh, p.hind_shin, knee_forward=True)
        shin_end = H2
    lev = unit2(shin_end, K)                       # lever and crank point back up the shin's line
    for side, sy in (("l", 1.0), ("r", -1.0)):
        k = tag + side
        roll = lib.qdd(AK70, origin=(hx - s * ROLL_OUT, sy * p.roll_y, ZH), direction=(s, 0, 0), label="roll_" + k)
        hr = lib.housing(roll, wall=p.wall, plate=PLATE)
        roll_h[tag].append(hr)
        legs[k] = {"tag": tag, "s": s, "sy": sy, "hx": hx, "K": K, "A": A, "H2": H2, "lev": lev, "roll": roll, "h_roll": hr}

# rear frame: spine housing, rear roll housings, tail-pitch housing, keel, electronics deck
rk = [box(-172.0, -40.0, -22, 22, ZH, ZH + 47.0),
      box(-HX - 60.0, -50.0, -22, 22, ZH + 40.0, ZH + 52.0),
      box(-HX, -80.0, -27.5, 27.5, ZH + 47.0, ZH + 52.0)]
pi = lib.board("pi-5", origin=(-HX + 5.0, -28.0, ZH + 55.0), label="pi5")
imu = lib.board("bno085-adafruit-4754", origin=(-110.0, -11.43, ZH + 55.0), label="imu")
pi_m = pi.mounting(3.0)
imu_m = imu.mounting(3.0)
rear = part.fuse([h_spine.body, h_tailp.body] + [h.body for h in roll_h["r"]] + rk)
rear = cut_all(rear, [h_spine, h_tailp] + roll_h["r"], [spine.bay(), tail_pitch.bay(), pi.bay(), imu.bay()] + [legs[k]["roll"].bay() for k in ("rl", "rr")])
rear = part.cut(part.fuse([rear] + list(pi_m.standoffs) + list(imu_m.standoffs)), list(pi_m.holes) + list(imu_m.holes))
# ---- panels (ADR-635): each cut from the envelope of what it covers, screwed to its frame
M25 = lib.bolt("m2.5", 8)
rear_env = part.envelope([pi.body, imu.body] + rk, clearance=2.0, radius=30.0)
rear_cover = part.panel(rear_env, side=(0, 0, 1), max_angle=60, thickness=2.0, frame=rear,
                        screw=M25, screws=2, flange="frame",
                        # between the tail drive and the spine drive, both of which show;
                        # split where it comes apart for the electronics, and for the bed
                        within=((-262.0, -200, -2000), (-50.0, 200, 2000)),
                        seams=[((1, 0, 0), [-150.0])], label="rear_cover")
rear = part.cut(rear, rear_cover.pilots)
c_rear = place("torso_rear", rear, "mechanism")

def place_panel(tag, panel, holder, covers):
    pieces = {}
    for name, body in zip(panel.names, panel.parts):
        c = place(tag + "_" + name, body, "shell", role="panel", covers=covers)
        weld(tag + "_" + name, holder, c, (0, 0, 0))
        pieces[name] = c
    k = 0
    for name in panel.names:
        for _boss in panel.mounts[name]:
            c = place(tag + "_screw_" + str(k), panel.screws[k].body, "mechanism")
            weld(tag + "_screw_" + str(k), pieces[name], c, (0, 0, 0))
            contacts.append((c, holder))
            k += 1

# front frame: front roll housings, neck housing, keel, spine output arm
fk = [box(55.0, 172.0, -22, 22, ZH, ZH + 60.0),
      box(55.0, NECK_ROOT[0], -22, 22, ZH + 40.0, ZH + 65.0),
      box(50.0, 90.0, -22, L70 / 2.0 + 6.0, ZH - 5.0, ZH + 50.0),
      box(30.0, 60.0, L70 / 2.0, L70 / 2.0 + 6.0, ZH - 5.0, ZH + 45.0),
      cyl_y(0.0, SPINE_Z, L70 / 2.0, L70 / 2.0 + 6.0, 40.0)]
spine_out = spine.mounting(output_wall=6.0).output
front_frame = part.fuse([h_neck.body] + [h.body for h in roll_h["f"]] + fk)
front_frame = cut_all(front_frame, [h_neck] + roll_h["f"], [neck_drive.bay()] + [legs[k]["roll"].bay() for k in ("fl", "fr")] + list(spine_out.holes))
front_env = part.envelope(fk[:2], clearance=2.0, radius=30.0)
front_cover = part.panel(front_env, side=(0, 0, 1), max_angle=60, thickness=2.0,
                         frame=front_frame, screw=M25, screws=3, flange=30.0,
                         # ends behind the neck housing: the drive shows, the neck swings free
                         within=((0.0, -200, -2000), (NECK_ROOT[0] - 40.0, 200, 2000)),
                         label="front_cover")
front_frame = part.cut(front_frame, front_cover.pilots)
c_front = place("torso_front", front_frame, "mechanism")

c_spine = place("spine_drive", spine.body, "mechanism")
c_neckd = place("neck_drive", neck_drive.body, "mechanism")
c_tailpd = place("tail_pitch_drive", tail_pitch.body, "mechanism")
c_pi = place("pi5", pi.body, "mechanism")
c_imu = place("imu", imu.body, "mechanism")
weld("spine_drive", c_rear, c_spine, (0, 0, SPINE_Z))
weld("neck_drive", c_front, c_neckd, (NECK_ROOT[0], 0, NECK_ROOT[1]))
weld("tail_pitch_drive", c_rear, c_tailpd, (TAIL_PITCH[0], 0, TAIL_PITCH[1]))
weld("pi5", c_rear, c_pi, (-HX + 40.0, 0, ZH + 55.0))
weld("imu", c_rear, c_imu, (-100.0, 0, ZH + 55.0))
bolts("bolt_pi", pi_m.screws, c_rear, c_pi)
bolts("bolt_imu", imu_m.screws, c_rear, c_imu)
place_panel("rear_cover", rear_cover, c_rear, [c_pi, c_imu, c_rear])
place_panel("front_cover", front_cover, c_front, [c_front])
hinge("spine", c_rear, c_front, (0, 0, SPINE_Z), (0, 1, 0), (-20, 20))
contacts.append((c_front, c_spine))

# ---------------- legs ----------------
leg_comps = {}
for k in ("fl", "fr", "rl", "rr"):
    L = legs[k]
    s, sy, hx, K, A, H2, lev = L["s"], L["sy"], L["hx"], L["K"], L["A"], L["H2"], L["lev"]
    frame_c = c_front if L["tag"] == "f" else c_rear
    roll = L["roll"]
    pitch = lib.qdd(AK80, origin=(hx, sy * Y_PITCH_OUT, ZH), direction=(0, sy, 0), label="pitch_" + k)
    knee = lib.qdd(AK80, origin=(hx, sy * YB, ZH), direction=(0, sy, 0), label="knee_" + k)
    h_p = lib.housing(pitch, wall=p.wall, plate=PLATE)
    h_k = lib.housing(knee, wall=p.wall, plate=PLATE)

    # yoke: flange on the roll output, web to the hip-pitch housing
    xf = hx - s * ROLL_OUT
    flange = part.cylinder(24.0, 6.0, origin=(xf, sy * p.roll_y, ZH), direction=(s, 0, 0))
    web = box(xf, hx, sy * 30.0, sy * Y_PITCH_REAR, ZH - 22.0, ZH + 22.0)
    roll_out = roll.mounting(output_wall=6.0).output
    pitch_out = pitch.mounting(output_wall=6.0).output
    knee_out = knee.mounting(output_wall=6.0).output
    yoke = part.cut(h_p.fuse(flange, web), [pitch.bay()] + list(roll_out.holes))

    # thigh: disc on the hip-pitch output, knee-drive housing, beam to the knee
    disc = cyl_y(hx, ZH, sy * Y_PITCH_OUT, sy * (Y_PITCH_OUT + 6.0), 39.5)
    beam = link_y((hx, ZH), K, 30.0, 18.0, sy * (Y_PITCH_OUT + 6.0), sy * (YB - 3.0))
    thigh = part.cut(h_k.fuse(disc, beam), [knee.bay(lead_room=0.0)] + list(pitch_out.holes))

    # crank on the knee-drive output; rod; shin with its lever
    hip = (hx, ZH)
    ctip = (hx + p.crank * lev[0], ZH + p.crank * lev[1])
    ltip = (K[0] + p.crank * lev[0], K[1] + p.crank * lev[1])
    crank = part.cut(part.fuse([cyl_y(hx, ZH, sy * YB, sy * (YB + 6.0), 26.0), link_y(hip, ctip, 14.0, 10.0, sy * YB, sy * (YB + 6.0))]), list(knee_out.holes))
    rod = link_y(ctip, ltip, 9.0, 9.0, sy * (YB + 9.0), sy * (YB + 15.0))
    sy0, sy1 = sy * (YB - 2.0), sy * (YB + 8.0)
    shin_parts = [link_y(K, ltip, 18.0, 10.0, sy0, sy1)]
    if H2 is None:
        shin_parts.append(link_y(K, A, 18.0, 13.0, sy0, sy1))
    else:
        shin_parts.append(link_y(K, H2, 18.0, 13.0, sy0, sy1))
        shin_parts.append(link_y(H2, A, 13.0, 12.0, sy0, sy1))
    shin = part.fuse(shin_parts)

    # paw: a compact printed block on the shin's end, the rubber pad screwed under it
    pad_x = A[0] + (10.0 if L["tag"] == "f" else 5.0)
    pad = lib.foot_pad("essentra-462178", origin=(pad_x, sy * (YB + 3.0), PAD_H), direction=(0, 0, -1), label="pad_" + k)
    paw = box(pad_x - 22.0, pad_x + 18.0, sy * (YB - 12.0), sy * (YB + 18.0), PAD_H, A[1] - 12.0)
    paw = part.cut(paw, [pad.bay(), shin])

    c_roll = place("roll_" + k, roll.body, "mechanism")
    c_pitch = place("pitch_" + k, pitch.body, "mechanism")
    c_knee = place("knee_" + k, knee.body, "mechanism")
    c_yoke = place("yoke_" + k, yoke, "mechanism")
    c_thigh = place("thigh_" + k, thigh, "mechanism")
    c_crank = place("crank_" + k, crank, "mechanism")
    c_rod = place("rod_" + k, rod, "mechanism")
    c_shin = place("shin_" + k, shin, "mechanism")
    c_paw = place("paw_" + k, paw, "mechanism")
    c_pad = place("pad_" + k, pad.body, "accent")

    weld("roll_" + k, frame_c, c_roll, (xf, sy * p.roll_y, ZH))
    weld("pitch_" + k, c_yoke, c_pitch, (hx, sy * Y_PITCH_OUT, ZH))
    weld("knee_" + k, c_thigh, c_knee, (hx, sy * YB, ZH))
    weld("paw_" + k, c_shin, c_paw, (A[0], sy * (YB + 3.0), A[1]))
    weld("pad_" + k, c_paw, c_pad, (pad_x, sy * (YB + 3.0), PAD_H))
    hinge("hip_roll_" + k, frame_c, c_yoke, (xf, sy * p.roll_y, ZH), (s, 0, 0), (-25, 25))
    hinge("hip_pitch_" + k, c_yoke, c_thigh, (hx, 0, ZH), (0, sy, 0), (-60, 60))
    hinge("knee_drive_" + k, c_thigh, c_crank, (hx, 0, ZH), (0, sy, 0), (-45, 45))
    hinge("knee_" + k, c_thigh, c_shin, (K[0], 0, K[1]), (0, sy, 0))
    hinge("rod_a_" + k, c_crank, c_rod, (ctip[0], 0, ctip[1]), (0, sy, 0))
    hinge("rod_b_" + k, c_rod, c_shin, (ltip[0], 0, ltip[1]), (0, sy, 0))
    contacts.extend([(c_yoke, c_roll), (c_thigh, c_pitch), (c_crank, c_knee)])
    regions.append(assembly.anatomy("leg_" + k, [c_yoke, c_thigh, c_crank, c_rod, c_shin]))
    leg_comps[k] = c_paw

regions.append(assembly.anatomy("paws", [leg_comps[k] for k in ("fl", "fr", "rl", "rr")],
    reason="An AK45-10 (262 g, the smallest catalog QDD) at the ankle, 200-220 mm below the knee, adds about 0.262 x 0.21^2 = 0.0116 kg m^2 to the lower leg's swing inertia, over three times the printed shin and paw it would move; the hock and paw stay fixed at the leopard's standing angle."))

# ---------------- neck, head, jaw ----------------
na = math.radians(25.0)
HEAD = (NECK_ROOT[0] + p.neck_len * math.cos(na), NECK_ROOT[1] + p.neck_len * math.sin(na))
JAW = (HEAD[0] + 55.0, HEAD[1] - 45.0)
head_drive = lib.qdd(AK45, origin=(HEAD[0], -L45 / 2.0, HEAD[1]), direction=(0, -1, 0), label="head")
h_head = lib.housing(head_drive, wall=p.wall, plate=PLATE)
neck_link = h_head.fuse(cyl_y(NECK_ROOT[0], NECK_ROOT[1], L45 / 2.0, L45 / 2.0 + 6.0, 22.0),
                        link_y(NECK_ROOT, HEAD, 20.0, 20.0, L45 / 2.0, L45 / 2.0 + 6.0))
neck_link = part.cut(neck_link, [head_drive.bay()] + list(neck_drive.mounting(output_wall=6.0).output.holes))
c_neck = place("neck_link", neck_link, "mechanism")
c_headd = place("head_drive", head_drive.body, "mechanism")
weld("head_drive", c_neck, c_headd, (HEAD[0], 0, HEAD[1]))
hinge("neck", c_front, c_neck, (NECK_ROOT[0], 0, NECK_ROOT[1]), (0, 1, 0), (-30, 30))
contacts.append((c_neck, c_neckd))

jaw_drive = lib.qdd(AK45, origin=(JAW[0], L45 / 2.0, JAW[1]), direction=(0, 1, 0), label="jaw")
h_jaw = lib.housing(jaw_drive, wall=p.wall, plate=PLATE)
CAM_X = HEAD[0] + 128.0
cam = lib.board("rpi-camera-module-3", origin=(CAM_X, -12.5, HEAD[1] - 20.0), direction=(1, 0, 0), roll_degrees=90.0, label="camera")
skull = [cyl_y(HEAD[0], HEAD[1], -L45 / 2.0 - 6.0, -L45 / 2.0, 22.0),
         link_y(HEAD, JAW, 20.0, 20.0, -L45 / 2.0 - 6.0, -L45 / 2.0),
         box(HEAD[0] + 32.0, HEAD[0] + 120.0, -21.0, 21.0, HEAD[1] - 35.0, HEAD[1] + 18.0)]
cam_m = cam.mounting(8.0)
head = h_jaw.fuse(*skull)
head = part.cut(head, [cam.bay(), jaw_drive.bay()] + list(head_drive.mounting(output_wall=6.0).output.holes))
head = part.cut(part.fuse([head] + list(cam_m.standoffs)), list(cam_m.holes))
head_env = part.envelope([skull[2], cam.body], clearance=2.0, radius=20.0)
head_cover = part.panel(head_env, side=(0, 0, 1), max_angle=65, thickness=2.0, frame=head,
                        screw=M25, screws=2, flange=14.0,
                        # clear of the neck link as the head nods through its range
                        openings=[{"around": neck_link, "clearance": 3.0,
                                   "motion": {"origin": (HEAD[0], 0.0, HEAD[1]),
                                              "axis": (0, -1, 0), "range": (-35, 35)}}],
                        # the cover ends behind the camera, which looks out over its nose
                        within=((HEAD[0] - 200, -200, -2000), (CAM_X - 1.0, 200, 2000)),
                        label="head_cover")
head = part.cut(head, head_cover.pilots)
c_head = place("head", head, "mechanism")
c_jawd = place("jaw_drive", jaw_drive.body, "mechanism")
c_cam = place("camera", cam.body, "accent")
place_panel("head_cover", head_cover, c_head, [c_head, c_cam])
weld("jaw_drive", c_head, c_jawd, (JAW[0], 0, JAW[1]))
weld("camera", c_head, c_cam, (CAM_X, 0, HEAD[1] - 10.0))
hinge("head", c_neck, c_head, (HEAD[0], 0, HEAD[1]), (0, -1, 0), (-35, 35))
contacts.append((c_head, c_headd))

CHIN = (JAW[0] + 80.0, JAW[1] - 8.0)
jaw = part.fuse([cyl_y(JAW[0], JAW[1], L45 / 2.0, L45 / 2.0 + 6.0, 22.0),
                 link_y(JAW, CHIN, 18.0, 12.0, L45 / 2.0, L45 / 2.0 + 6.0),
                 box(CHIN[0] - 14.0, CHIN[0] + 6.0, -21.0, L45 / 2.0 + 6.0, CHIN[1] - 10.0, CHIN[1] + 6.0)])
jaw = part.cut(jaw, list(jaw_drive.mounting(output_wall=6.0).output.holes))
c_jaw = place("jaw", jaw, "mechanism")
hinge("jaw", c_head, c_jaw, (JAW[0], 0, JAW[1]), (0, 1, 0), (0, 30))
contacts.append((c_jaw, c_jawd))

regions.append(assembly.anatomy("neck", [c_neck]))
regions.append(assembly.anatomy("head", [c_head]))
regions.append(assembly.anatomy("jaw", [c_jaw]))

# ---------------- tail ----------------
TAIL_YAW = (TAIL_PITCH[0] - 70.0, TAIL_PITCH[1])
tail_yaw = lib.qdd(AK45, origin=(TAIL_YAW[0], 0.0, TAIL_YAW[1] - L45 / 2.0), direction=(0, 0, -1), label="tail_yaw")
h_ty = lib.housing(tail_yaw, wall=p.wall, plate=PLATE)
bracket = h_ty.fuse(cyl_y(TAIL_PITCH[0], TAIL_PITCH[1], L45 / 2.0, L45 / 2.0 + 6.0, 22.0),
                    link_y(TAIL_PITCH, TAIL_YAW, 20.0, 20.0, L45 / 2.0, L45 / 2.0 + 6.0))
bracket = part.cut(bracket, [tail_yaw.bay()] + list(tail_pitch.mounting(output_wall=6.0).output.holes))
c_bracket = place("tail_root", bracket, "mechanism")
c_tyd = place("tail_yaw_drive", tail_yaw.body, "mechanism")
weld("tail_yaw_drive", c_bracket, c_tyd, (TAIL_YAW[0], 0, TAIL_YAW[1]))
hinge("tail_pitch", c_rear, c_bracket, (TAIL_PITCH[0], 0, TAIL_PITCH[1]), (0, 1, 0), (-30, 30))
contacts.append((c_bracket, c_tailpd))

ZY_OUT = TAIL_YAW[1] - L45 / 2.0          # yaw output face, facing down
t1 = math.radians(-30.0)
TAIL_MID = (TAIL_YAW[0] - p.tail1 * math.cos(t1), ZY_OUT - 20.0 + p.tail1 * math.sin(t1))
tail_mid = lib.qdd(AK45, origin=(TAIL_MID[0], L45 / 2.0, TAIL_MID[1]), direction=(0, 1, 0), label="tail_mid")
h_tm = lib.housing(tail_mid, wall=p.wall, plate=PLATE)
seg1 = h_tm.fuse(part.cylinder(22.0, 6.0, origin=(TAIL_YAW[0], 0, ZY_OUT - 6.0)),
                 link_y((TAIL_YAW[0], ZY_OUT - 22.0), TAIL_MID, 16.0, 16.0, -12.0, 12.0),
                 box(TAIL_YAW[0] - 16.0, TAIL_YAW[0] + 16.0, -12.0, 12.0, ZY_OUT - 22.0, ZY_OUT - 4.0))
seg1 = part.cut(seg1, [tail_mid.bay()] + list(tail_yaw.mounting(output_wall=6.0).output.holes))
c_seg1 = place("tail_1", seg1, "mechanism")
c_tmd = place("tail_mid_drive", tail_mid.body, "mechanism")
weld("tail_mid_drive", c_seg1, c_tmd, (TAIL_MID[0], 0, TAIL_MID[1]))
hinge("tail_yaw", c_bracket, c_seg1, (TAIL_YAW[0], 0, ZY_OUT), (0, 0, -1), (-40, 40))
contacts.append((c_seg1, c_tyd))

t2 = math.radians(-35.0)
TAIL_TIP = (TAIL_MID[0] - p.tail2 * math.cos(t2), TAIL_MID[1] + p.tail2 * math.sin(t2))
r_start = (TAIL_MID[0] - 54.0 * math.cos(t2), TAIL_MID[1] + 54.0 * math.sin(t2))
seg2 = part.fuse([cyl_y(TAIL_MID[0], TAIL_MID[1], L45 / 2.0, L45 / 2.0 + 6.0, 22.0),
                  link_y(TAIL_MID, r_start, 18.0, 16.0, L45 / 2.0, L45 / 2.0 + 6.0),
                  link_y(r_start, TAIL_TIP, 16.0, 8.0, -12.0, L45 / 2.0 + 6.0)])
seg2 = part.cut(seg2, list(tail_mid.mounting(output_wall=6.0).output.holes))
c_seg2 = place("tail_2", seg2, "mechanism")
hinge("tail_mid", c_seg1, c_seg2, (TAIL_MID[0], 0, TAIL_MID[1]), (0, 1, 0), (-45, 45))
contacts.append((c_seg2, c_tmd))
regions.append(assembly.anatomy("tail", [c_bracket, c_seg1, c_seg2]))
regions.append(assembly.anatomy("spine", [c_rear, c_front]))

print("knee f", [round(v, 1) for v in legs["fl"]["K"]], "knee r", [round(v, 1) for v in legs["rl"]["K"]], "hock", legs["rl"]["H2"])
print("head", HEAD, "jaw", JAW, "tail mid", TAIL_MID, "tip", TAIL_TIP)

result["leopard"] = assembly.assembly(
    comps, joints, contacts=contacts, sweep_step_degrees=10.0, anatomy=regions,
    palette={"shell": "#E4D9C4", "mechanism": "#2E3135", "accent": "#E8A33A"}, label="leopard")
result["solve"] = assembly.solve(result["leopard"])
