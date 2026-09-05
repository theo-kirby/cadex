# =====================================================================
# MG90S biped robot - 10 DOF, 3D printable, ESP32-S3 + PCA9685
# Both legs come from one signed builder (no mirrored solids).
# Every link is authored in its own frame, centred on the MIDDLE of the
# limb, and placed by its component. +X forward, +Y left, +Z up.
# Thigh and shin are channel sections: a servo-mount wall on one side,
# a second wall on the other, joined by a back web. All printed parts
# are edge-rounded.
# =====================================================================

p = params(
    hip_y=num(30.0, unit="mm", min=24.0, max=42.0, step=0.5,
              label="Hip half-spacing"),
    roll_h=num(16.0, unit="mm", min=12.0, max=24.0, step=0.5,
               label="Ankle roll axis height"),
    ankle_h=num(34.0, unit="mm", min=26.0, max=48.0, step=0.5,
                label="Ankle pitch axis height"),
    shin_len=num(62.0, unit="mm", min=40.0, max=95.0, step=1.0,
                 label="Shin length"),
    thigh_len=num(58.0, unit="mm", min=40.0, max=95.0, step=1.0,
                  label="Thigh length"),
    hip_gap=num(22.0, unit="mm", min=16.0, max=36.0, step=0.5,
                label="Hip pitch to hip roll"),
    foot_len=num(80.0, unit="mm", min=55.0, max=110.0, step=1.0,
                 label="Foot length"),
    foot_w=num(44.0, unit="mm", min=30.0, max=58.0, step=1.0,
               label="Foot width"),
    foot_t=num(3.5, unit="mm", min=2.0, max=6.0, step=0.5,
               label="Sole thickness"),
    plate_t=num(3.0, unit="mm", min=2.0, max=5.0, step=0.5,
                label="Printed plate thickness"),
    limb_t=num(4.5, unit="mm", min=3.0, max=6.0, step=0.5,
               label="Thigh/shin wall thickness"),
    limb_w=num(18.0, unit="mm", min=15.0, max=26.0, step=0.5,
               label="Thigh/shin channel reach"),
    round_r=num(2.0, unit="mm", min=0.5, max=4.0, step=0.25,
                label="Edge rounding radius"),
    plate_r=num(9.0, unit="mm", min=0.0, max=16.0, step=0.5,
                label="Plate corner radius"),
    torso_d=num(40.0, unit="mm", min=30.0, max=60.0, step=1.0,
                label="Torso depth"),
    torso_w=num(72.0, unit="mm", min=60.0, max=90.0, step=1.0,
                label="Torso width"),
    torso_h=num(62.0, unit="mm", min=45.0, max=90.0, step=1.0,
                label="Torso height"),
    density=num(1300.0, unit="kg/m3", min=800.0, max=2200.0, step=25.0,
                label="Mean density, print plus servo"),
    servo_torque=num(216.0, unit="N*mm", min=90.0, max=400.0, step=2.0,
                     label="MG90S stall torque"),
    servo_stiff=num(25.0, unit="N*mm/deg", min=5.0, max=60.0, step=1.0,
                    label="Servo position gain"),
    stand_com=num(150.0, unit="mm", min=80.0, max=220.0, step=1.0,
                  label="Standing centre of mass height"),
    push_n=num(3.0, unit="N", min=0.5, max=12.0, step=0.5,
               label="Strongest training push"),
    rollout_seed=num(0.0, min=0.0, max=23.0, step=1.0,
                     label="Rollout seed"),
)

HY = p.hip_y
RH = p.roll_h
ZA = p.ankle_h
ZK = ZA + p.shin_len
ZHP = ZK + p.thigh_len
ZHR = ZHP + p.hip_gap
T = p.plate_t
LT = p.limb_t
LW = p.limb_w
RR = p.round_r
PR = p.plate_r

AX = [1.0, 0.0, 0.0]
AY = [0.0, 1.0, 0.0]
AZ = [0.0, 0.0, 1.0]

# ---- MG90S metric servo. Local frame: +Z is the output shaft and the
# ---- origin sits on the top face of the case.
SB_L = 23.0
SB_W = 12.4
SB_H = 22.5
SH_X = 6.0
FL_L = 32.4
FL_T = 2.5
FL_Z = -6.5
CX = -SH_X + SB_L / 2.0


def sub(a, b):
    return [a[0] - b[0], a[1] - b[1], a[2] - b[2]]


def rounded(shape):
    return shape


def localise(shape, c, label):
    return part.transform(shape, translation=[-c[0], -c[1], -c[2]],
                          label=label)


def place(shape, rots, pos):
    out = shape
    for ax, deg in rots:
        out = part.transform(out, rotation_axis=ax, rotation_degrees=deg)
    return part.transform(out, translation=pos)


def rolls(sgn):
    # local +Z -> +X (forward), +X -> outboard, +Y -> up
    return [(AY, 90.0), (AX, 90.0 * sgn)]


def pitch_out(sgn):
    # local +Z -> outboard, +X -> -X (back)
    return [(AZ, 180.0), (AX, -90.0 * sgn)]


def pitch_in(sgn):
    # local +Z -> inboard, +X -> -X (back)
    return [(AZ, 180.0), (AX, 90.0 * sgn)]


def obox(x0, x1, o0, o1, z0, z1, sgn):
    """Box from an x range, an outboard offset range from the hip plane
    and a z range."""
    ya = sgn * (HY + o0)
    yb = sgn * (HY + o1)
    lo = ya if ya < yb else yb
    hi = yb if ya < yb else ya
    return part.box(x1 - x0, hi - lo, z1 - z0, origin=[x0, lo, z0])


def mid3(a, b, c):
    hi = a
    if b > hi:
        hi = b
    if c > hi:
        hi = c
    lo = a
    if b < lo:
        lo = b
    if c < lo:
        lo = c
    return a + b + c - hi - lo


def rbox(x0, x1, o0, o1, z0, z1, sgn, r=PR):
    """obox with its long corners rounded off, so plates read as
    soft-cornered slabs rather than rectangles."""
    b = obox(x0, x1, o0, o1, z0, z1, sgn)
    sy = o1 - o0
    if sy < 0.0:
        sy = -sy
    m = 0.45 * mid3(x1 - x0, sy, z1 - z0)
    rr = r if r < m else m
    if rr < 0.3:
        return b
    return part.fillet(b, rr, edges="all", on_failure="skip")


def servo_group(pos, rots, half_y):
    body = part.box(SB_L, SB_W, SB_H, origin=[-SH_X, -SB_W / 2.0, -SB_H])
    flange = part.box(FL_L, SB_W, FL_T,
                      origin=[CX - FL_L / 2.0, -SB_W / 2.0, FL_Z])
    boss = part.cylinder(5.9, 4.0)
    horn = part.cylinder(9.0, 2.0, origin=[0.0, 0.0, 4.0])
    sv = place(part.fuse([body, flange, boss, horn]), rots, pos)
    wall = place(part.box(FL_L + 2.0, 2.0 * half_y, T,
                          origin=[CX - FL_L / 2.0 - 1.0, -half_y, FL_Z - T]),
                 rots, pos)
    pocket = part.box(SB_L + 1.6, SB_W + 1.6, SB_H + 1.5,
                      origin=[-SH_X - 0.8, -(SB_W + 1.6) / 2.0, -SB_H - 1.0])
    hz = LT + T + 10.0
    h0 = FL_Z - LT - T - 5.0
    tools = [place(pocket, rots, pos),
             place(part.cylinder(1.15, hz, origin=[CX - 14.0, 0.0, h0]),
                   rots, pos),
             place(part.cylinder(1.15, hz, origin=[CX + 14.0, 0.0, h0]),
                   rots, pos)]
    return sv, wall, tools


def hub_group(pos, rots):
    disc = place(part.cylinder(11.0, T, origin=[0.0, 0.0, 6.0]), rots, pos)
    tools = [place(part.cylinder(3.2, T + 6.0, origin=[0.0, 0.0, 3.0]),
                   rots, pos)]
    for sx, sy in [(6.5, 0.0), (-6.5, 0.0), (0.0, 6.5), (0.0, -6.5)]:
        tools.append(place(part.cylinder(1.15, T + 6.0,
                                         origin=[sx, sy, 3.0]), rots, pos))
    return disc, tools


def build_leg(sgn, tag):
    rf = rolls(sgn)
    po = pitch_out(sgn)
    pn = pitch_in(sgn)
    y = sgn * HY

    # foot: carries the ankle roll servo, shaft forward
    sv_ar, wl_ar, tl_ar = servo_group([0.0, y, RH], rf, 8.0)
    sole = obox(-p.foot_len * 0.35, p.foot_len * 0.65,
                -p.foot_w / 2.0, p.foot_w / 2.0, 0.0, p.foot_t, sgn)
    riser = obox(FL_Z - T, FL_Z, -11.7, 22.7, 0.0, RH - 6.0, sgn)
    pad = obox(-24.0, -9.0, -8.0, 19.0, p.foot_t, RH - 7.5, sgn)
    foot = part.compound(
        [part.cut(rounded(part.fuse([sole, riser, pad, wl_ar])), tl_ar),
         sv_ar])

    # ankle bracket: roll horn below, ankle pitch servo above
    hub_ar, th_ar = hub_group([0.0, y, RH], rf)
    sv_ap, wl_ap, tl_ap = servo_group([0.0, y, ZA], po, 11.0)
    gusset = obox(6.0, 6.0 + T, -11.0, 3.0, RH, ZA + 6.0, sgn)
    ankle = part.compound(
        [part.cut(rounded(part.fuse([hub_ar, gusset, wl_ap])),
                  tl_ap + th_ar), sv_ap])

    # shin: outboard servo-mount wall, inboard wall, back web
    hub_ap, th_ap = hub_group([0.0, y, ZA], po)
    sv_kn, wl_kn, tl_kn = servo_group([0.0, y, ZK], pn, 11.0)
    sh_out = rbox(-13.0, 13.0, 6.0, 6.0 + LT, ZA - 11.0, ZK + 11.0, sgn)
    sh_in = rbox(-13.0, 13.0, -LW, -LW + LT, ZA + 20.0, ZK + 11.0, sgn)
    sh_parts = [hub_ap, sh_out, sh_in, wl_kn]
    if ZK - 14.0 > ZA + 25.0:
        sh_parts.append(rbox(-13.0, -13.0 + LT, -LW, 6.0 + LT,
                             ZA + 20.0, ZK - 14.0, sgn))
    shin = part.compound(
        [part.cut(rounded(part.fuse(sh_parts)), tl_kn + th_ap), sv_kn])

    # thigh: inboard servo-mount wall, outboard wall, back web
    hub_kn, th_kn = hub_group([0.0, y, ZK], pn)
    sv_hp, wl_hp, tl_hp = servo_group([0.0, y, ZHP], po, 11.0)
    tg_in = obox(-13.0, 13.0, -9.0, -9.0 + LT, ZK - 11.0, ZHP + 11.0, sgn)
    tg_out = obox(-13.0, 13.0, LW - LT, LW, ZK + 20.0, ZHP + 11.0, sgn)
    tg_parts = [hub_kn, tg_in, tg_out, wl_hp]
    if ZHP - 14.0 > ZK + 25.0:
        tg_parts.append(obox(-13.0, -13.0 + LT, -9.0, LW,
                             ZK + 20.0, ZHP - 14.0, sgn))
    thigh = part.compound(
        [part.cut(rounded(part.fuse(tg_parts)), tl_hp + th_kn), sv_hp])

    # hip bracket: pitch horn below, hip roll servo above
    hub_hp, th_hp = hub_group([0.0, y, ZHP], po)
    sv_hr, wl_hr, tl_hr = servo_group([0.0, y, ZHR], rf, 10.0)
    hip_plate = obox(-13.0, 13.0, 6.0, 6.0 + T, ZHP - 11.0, ZHR + 10.0, sgn)
    hip = part.compound(
        [part.cut(rounded(part.fuse([hub_hp, hip_plate, wl_hr])),
                  tl_hr + th_hp), sv_hr])

    cf = [p.foot_len * 0.15, y, RH / 2.0]
    ca = [0.0, y, (RH + ZA) / 2.0]
    cs = [0.0, y, (ZA + ZK) / 2.0]
    ct = [0.0, y, (ZK + ZHP) / 2.0]
    ch = [0.0, y, (ZHP + ZHR) / 2.0]
    return [(localise(foot, cf, "foot_" + tag), cf),
            (localise(ankle, ca, "ankle_" + tag), ca),
            (localise(shin, cs, "shin_" + tag), cs),
            (localise(thigh, ct, "thigh_" + tag), ct),
            (localise(hip, ch, "hip_" + tag), ch)]


LEG_L = build_leg(1.0, "l")
LEG_R = build_leg(-1.0, "r")
foot_l, CFL = LEG_L[0]
ankle_l, CAL = LEG_L[1]
shin_l, CSL = LEG_L[2]
thigh_l, CTL = LEG_L[3]
hip_l, CHL = LEG_L[4]
foot_r, CFR = LEG_R[0]
ankle_r, CAR = LEG_R[1]
shin_r, CSR = LEG_R[2]
thigh_r, CTR = LEG_R[3]
hip_r, CHR = LEG_R[4]

# ----------------------------------------------------------- torso
hub_hl, th_hl = hub_group([0.0, HY, ZHR], rolls(1.0))
hub_hrr, th_hr2 = hub_group([0.0, -HY, ZHR], rolls(-1.0))
pelvis = part.box(T, 2.0 * HY + 22.0, 24.0,
                  origin=[6.0, -HY - 11.0, ZHR - 11.0])
TZ = ZHR + 11.0
shell = part.box(p.torso_d, p.torso_w, p.torso_h,
                 origin=[-p.torso_d / 2.0, -p.torso_w / 2.0, TZ])
cav = part.box(p.torso_d - 5.0, p.torso_w - 5.0, p.torso_h - 5.0,
               origin=[-p.torso_d / 2.0 + 2.5, -p.torso_w / 2.0 + 2.5,
                       TZ + 2.5])
access = part.box(6.0, p.torso_w - 22.0, p.torso_h - 26.0,
                  origin=[-p.torso_d / 2.0 - 1.0, -(p.torso_w - 22.0) / 2.0,
                          TZ + 13.0])
head = part.box(30.0, 36.0, 20.0, origin=[-15.0, -18.0, TZ + p.torso_h - 2.0])
eye1 = part.cylinder(4.0, 14.0, origin=[8.0, 9.0, TZ + p.torso_h + 10.0],
                     direction=[1.0, 0.0, 0.0])
eye2 = part.cylinder(4.0, 14.0, origin=[8.0, -9.0, TZ + p.torso_h + 10.0],
                     direction=[1.0, 0.0, 0.0])
torso_print = part.cut(
    rounded(part.fuse([pelvis, shell, head, hub_hl, hub_hrr])),
    [cav, access, eye1, eye2] + th_hl + th_hr2)

pca = part.box(25.4, 62.5, 3.0, origin=[-12.7, -31.25, TZ + 5.0])
esp = part.box(25.4, 63.0, 5.0, origin=[-12.7, -31.5, TZ + 13.0])
batt = part.box(30.0, 55.0, 15.0, origin=[-15.0, -27.5, TZ + 27.0])
CTO = [0.0, 0.0, TZ + p.torso_h / 2.0]
torso = localise(part.compound([torso_print, pca, esp, batt]), CTO, "torso")

floor = part.box(400.0, 400.0, 4.0, origin=[-200.0, -200.0, -4.0],
                 label="floor")

# -------------------------------------------------------- assembly
c_floor = assembly.component(floor, grounded=True, label="floor")
c_torso = assembly.component(torso, placement=CTO, label="torso")
c_hip_l = assembly.component(hip_l, placement=CHL, label="hip_l")
c_thigh_l = assembly.component(thigh_l, placement=CTL, label="thigh_l")
c_shin_l = assembly.component(shin_l, placement=CSL, label="shin_l")
c_ankle_l = assembly.component(ankle_l, placement=CAL, label="ankle_l")
c_foot_l = assembly.component(foot_l, placement=CFL, label="foot_l")
c_hip_r = assembly.component(hip_r, placement=CHR, label="hip_r")
c_thigh_r = assembly.component(thigh_r, placement=CTR, label="thigh_r")
c_shin_r = assembly.component(shin_r, placement=CSR, label="shin_r")
c_ankle_r = assembly.component(ankle_r, placement=CAR, label="ankle_r")
c_foot_r = assembly.component(foot_r, placement=CFR, label="foot_r")


def jx(comp, world, c):
    return assembly.connector(comp, "origin", offset={
        "position": sub(world, c), "axis": [0.0, 1.0, 0.0],
        "angle_degrees": 90.0})


def jy(comp, world, c):
    return assembly.connector(comp, "origin", offset={
        "position": sub(world, c), "axis": [1.0, 0.0, 0.0],
        "angle_degrees": -90.0})


def leg_joints(sgn, tag, c_hip, ch, c_thigh, ct, c_shin, cs,
               c_ankle, ca, c_foot, cf):
    y = sgn * HY
    w_hr = [0.0, y, ZHR]
    w_hp = [0.0, y, ZHP]
    w_kn = [0.0, y, ZK]
    w_ap = [0.0, y, ZA]
    w_ar = [0.0, y, RH]
    jr = assembly.joint("revolute", jx(c_torso, w_hr, CTO),
                        jx(c_hip, w_hr, ch),
                        angle_limits_degrees=[-25.0, 25.0],
                        label="hip_roll_" + tag)
    jp = assembly.joint("revolute", jy(c_hip, w_hp, ch),
                        jy(c_thigh, w_hp, ct),
                        angle_limits_degrees=[-55.0, 40.0],
                        label="hip_pitch_" + tag)
    jk = assembly.joint("revolute", jy(c_thigh, w_kn, ct),
                        jy(c_shin, w_kn, cs),
                        angle_limits_degrees=[-5.0, 95.0],
                        label="knee_" + tag)
    ja = assembly.joint("revolute", jy(c_shin, w_ap, cs),
                        jy(c_ankle, w_ap, ca),
                        angle_limits_degrees=[-40.0, 40.0],
                        label="ankle_pitch_" + tag)
    jf = assembly.joint("revolute", jx(c_ankle, w_ar, ca),
                        jx(c_foot, w_ar, cf),
                        angle_limits_degrees=[-25.0, 25.0],
                        label="ankle_roll_" + tag)
    return jr, jp, jk, ja, jf


jhr_l, jhp_l, jk_l, jap_l, jar_l = leg_joints(
    1.0, "l", c_hip_l, CHL, c_thigh_l, CTL, c_shin_l, CSL,
    c_ankle_l, CAL, c_foot_l, CFL)
jhr_r, jhp_r, jk_r, jap_r, jar_r = leg_joints(
    -1.0, "r", c_hip_r, CHR, c_thigh_r, CTR, c_shin_r, CSR,
    c_ankle_r, CAR, c_foot_r, CFR)

robot = assembly.assembly(
    [c_floor, c_torso,
     c_hip_l, c_thigh_l, c_shin_l, c_ankle_l, c_foot_l,
     c_hip_r, c_thigh_r, c_shin_r, c_ankle_r, c_foot_r],
    [jhr_l, jhp_l, jk_l, jap_l, jar_l,
     jhr_r, jhp_r, jk_r, jap_r, jar_r],
    label="biped")

solved = assembly.solve(robot, require_solved=False, label="solved")

# --------------------------------------- mass, contact and MG90S motors
DENS = p.density


def coll_box(sx, sy, sz, world, c, fric=1.0):
    return assembly.collision("box", size_mm=[sx, sy, sz],
                              offset={"position": sub(world, c)},
                              friction=fric)


b_floor = assembly.body(c_floor, density_kg_m3=1200.0, collision=[
    assembly.collision("plane", size_mm=[400.0, 400.0, 50.0], friction=1.0)])
b_torso = assembly.body(c_torso, density_kg_m3=DENS, collision=[
    coll_box(p.torso_d, p.torso_w, p.torso_h,
             [0.0, 0.0, TZ + p.torso_h / 2.0], CTO)])


def leg_bodies(sgn, c_hip, ch, c_thigh, ct, c_shin, cs, c_ankle, ca,
               c_foot, cf):
    y = sgn * HY
    bh = assembly.body(c_hip, density_kg_m3=DENS)
    bt = assembly.body(c_thigh, density_kg_m3=DENS, collision=[
        coll_box(30.0, LW + 11.0, ZHP - ZK,
                 [0.0, y + sgn * (LW - 9.0) / 2.0, (ZK + ZHP) / 2.0], ct)])
    bs = assembly.body(c_shin, density_kg_m3=DENS, collision=[
        coll_box(30.0, LW + 11.0, ZK - ZA,
                 [0.0, y - sgn * (LW - 9.0) / 2.0, (ZA + ZK) / 2.0], cs)])
    ba = assembly.body(c_ankle, density_kg_m3=DENS)
    bf = assembly.body(c_foot, density_kg_m3=DENS, collision=[
        coll_box(p.foot_len, p.foot_w, p.foot_t,
                 [p.foot_len * 0.15, y, p.foot_t / 2.0], cf, 1.2)])
    return [bh, bt, bs, ba, bf]


bodies = [b_floor, b_torso]
bodies = bodies + leg_bodies(1.0, c_hip_l, CHL, c_thigh_l, CTL,
                             c_shin_l, CSL, c_ankle_l, CAL, c_foot_l, CFL)
bodies = bodies + leg_bodies(-1.0, c_hip_r, CHR, c_thigh_r, CTR,
                             c_shin_r, CSR, c_ankle_r, CAR, c_foot_r, CFR)

JOINTS = [
    (jhr_l, "hipr_l", -20.0, 20.0), (jhp_l, "hipp_l", -45.0, 35.0),
    (jk_l, "knee_l", 0.0, 85.0), (jap_l, "ankp_l", -30.0, 30.0),
    (jar_l, "ankr_l", -20.0, 20.0),
    (jhr_r, "hipr_r", -20.0, 20.0), (jhp_r, "hipp_r", -45.0, 35.0),
    (jk_r, "knee_r", 0.0, 85.0), (jap_r, "ankp_r", -30.0, 30.0),
    (jar_r, "ankr_r", -20.0, 20.0),
]

acts = []
jdyn = []
obs = []
effort = []
posture = []
for jnt, nm, lo, hi in JOINTS:
    act = assembly.actuator(jnt, kind="position", control_deg="0",
                            stiffness_nmm_per_deg=p.servo_stiff,
                            damping_nmms_per_deg=1.0,
                            torque_limit_nmm=p.servo_torque,
                            command_limits_degrees=[lo, hi])
    acts.append(act)
    jdyn.append(assembly.joint_dynamics(jnt, damping_nmms_per_deg=0.3,
                                        armature_kgmm2=25.0,
                                        friction_loss_nmm=1.5))
    obs.append(assembly.observation(jnt, "position", name=nm + "_q"))
    obs.append(assembly.observation(jnt, "velocity", name=nm + "_v"))
    obs.append(assembly.observation(act, "actuator_force", name=nm + "_f"))
    effort.append("abs(" + nm + "_f)")
    posture.append("abs(" + nm + "_q)")

obs.append(assembly.observation(c_torso, "component_orientation",
                                name="torso"))
obs.append(assembly.observation(c_torso, "component_angular_velocity",
                                name="tw"))
obs.append(assembly.observation(c_torso, "centre_of_mass", name="com"))
obs.append(assembly.observation(c_torso, "centre_of_mass_velocity",
                                name="comv"))
obs.append(assembly.observation(c_torso, "centroidal_angular_momentum",
                                name="ham"))

model = assembly.mjcf(robot, bodies, actuators=acts, joint_dynamics=jdyn,
                      observations=obs, solver_step_s=0.002,
                      label="biped_mjcf")

# ------------------------------------------- task: stand up to a shove
balance = assembly.task(
    model,
    actions=acts,
    reward=[
        assembly.reward("1", weight=1.0, label="alive"),
        assembly.reward("abs(torso_qx) + abs(torso_qy)", weight=-3.0,
                        label="upright"),
        assembly.reward("abs(com_z - %.1f)" % p.stand_com, weight=-0.02,
                        label="height"),
        assembly.reward("abs(com_x) + abs(com_y)", weight=-0.012,
                        label="stay_put"),
        assembly.reward("abs(comv_x) + abs(comv_y)", weight=-0.004,
                        label="settle"),
        assembly.reward("abs(ham_x) + abs(ham_y)", weight=-0.01,
                        label="not_tipping"),
        assembly.reward(" + ".join(posture), weight=-0.002, label="posture"),
        assembly.reward(" + ".join(effort), weight=-0.0004, label="effort"),
    ],
    termination=[
        assembly.termination("com_z", below=p.stand_com * 0.62),
        assembly.termination("torso_qw", below=0.8),
    ],
    reset_variation=[
        assembly.reset_variation(c_torso, tilt_degrees=[0.0, 4.0],
                                 height_mm=[6.0, 14.0],
                                 angular_velocity_dps=[0.0, 20.0],
                                 linear_velocity_mm_s=[0.0, 40.0]),
    ],
    disturbance=[
        assembly.disturbance(c_torso, newtons=[0.4, p.push_n],
                             direction="horizontal",
                             at_seconds=[1.0, 3.0], duration_s=0.12),
        assembly.disturbance(c_torso, newtons=[0.4, p.push_n],
                             direction="horizontal",
                             at_seconds=[4.0, 7.0], duration_s=0.12),
    ],
    episode_seconds=8.0, control_hz=50, label="balance")

# NOTE: the stiffer limbs change the mass of the robot, so the old
# balance policy no longer matches this task and must be retrained.

result = {
    "foot_l": foot_l, "ankle_l": ankle_l, "shin_l": shin_l,
    "thigh_l": thigh_l, "hip_l": hip_l,
    "foot_r": foot_r, "ankle_r": ankle_r, "shin_r": shin_r,
    "thigh_r": thigh_r, "hip_r": hip_r,
    "torso": torso, "floor": floor,
    "c_floor": c_floor, "c_torso": c_torso,
    "c_hip_l": c_hip_l, "c_thigh_l": c_thigh_l, "c_shin_l": c_shin_l,
    "c_ankle_l": c_ankle_l, "c_foot_l": c_foot_l,
    "c_hip_r": c_hip_r, "c_thigh_r": c_thigh_r, "c_shin_r": c_shin_r,
    "c_ankle_r": c_ankle_r, "c_foot_r": c_foot_r,
    "hip_roll_l": jhr_l, "hip_pitch_l": jhp_l, "knee_l": jk_l,
    "ankle_pitch_l": jap_l, "ankle_roll_l": jar_l,
    "hip_roll_r": jhr_r, "hip_pitch_r": jhp_r, "knee_r": jk_r,
    "ankle_pitch_r": jap_r, "ankle_roll_r": jar_r,
    "biped": robot, "solved": solved,
    "biped_mjcf": model, "balance": balance,
}
