"""orun11 M1: the built coupled foot, measured on its exported model.

Usage: pixi run python docs/probes/orun11/foot_static.py MODEL.xml [--png OUT.png] [--side l|r]

Reads the cat's exported MJCF (the training bundle's ``*-model.xml``), where
each hind foot is a closed four-bar: shin -> metatarsus (``j_hock``) -> paw
(``j_pawpin``) -> rod (``j_rodbot``) -> shin (``j_rodtop``), the rod's last pin
an ``equality/connect``. No physics is stepped. For each pose the passive
pins are solved so the connect closes (least squares on its residual, from
the last pose, so the linkage stays on its assembled branch), then:

* **The coupling curve.** Paw pin against hock, the hock's whole range at
  1 deg, the shin at its build pitch.
* **The static check.** The trunk level and the metatarsus level (shin pitch
  + hock = -60 deg, the plantigrade push-off), at shin pitches 0, -12 and -24
  deg. The floor is put under the foot (its lowest collision point), and the
  probe reports the sole's pitch from the floor (the common tangent under the
  paw's pad and toe spheres, positive toes-down) and the hock case's height
  over the floor (the bottom of its 40 mm collision sphere). M1 asks for the
  sole within 8 deg and the case within 10 mm.
* **The link loads.** 3x body weight (the model's own mass) straight up the
  toe sphere's lowest point, the hock case just off the floor: the pin moment,
  the rod's force (moment over the rod's lever about the pin), the bearing
  stress on an M5 pin in double shear, and the Euler margin of the rod.

Positive angles are toes-down about +y for the left leg; the right leg's
joints turn the other way, so its angles are reported with the sign flipped.
"""

from __future__ import annotations

import math
import sys

import mujoco
import numpy as np
from scipy.optimize import least_squares

PIN_M5_MM = 5.0
ROD_ROOT_MM = 4.134          # M5 x 0.8 minor diameter
STEEL_E_MPA = 200e3


def qadr(model, name):
    return model.jnt_qposadr[mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, name)]


def geom(model, name):
    return mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_GEOM, name)


class Leg:
    def __init__(self, model, side):
        self.m, self.d, self.s = model, mujoco.MjData(model), 1.0 if side == "l" else -1.0
        tg = side
        self.hip, self.knee, self.hock = (qadr(model, f"j_{n}_{tg}") for n in ("hip", "knee", "hock"))
        # the pins the tree kept; the one that closes the loop is the connect
        names = [f"j_{n}_{tg}" for n in ("pawpin", "rodtop", "rodbot")]
        kept = [n for n in names if mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, n) >= 0]
        self.passive = [qadr(model, n) for n in kept]
        self.pin = qadr(model, names[0])
        eqs = [i for i in range(model.neq) if model.eq_type[i] == mujoco.mjtEq.mjEQ_CONNECT]
        bodies = {"c_rod_h" + tg, "c_paw_h" + tg, "c_shin_" + tg, "c_meta_h" + tg}
        def body_of(i, obj):     # a closure names two sites (ADR-594), older exports two bodies
            return mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_BODY, int(
                model.site_bodyid[obj] if model.eq_objtype[i] == mujoco.mjtObj.mjOBJ_SITE else obj))
        self.eq = [i for i in eqs if {body_of(i, model.eq_obj1id[i]), body_of(i, model.eq_obj2id[i])} <= bodies]
        if len(self.eq) != 1:
            raise SystemExit(f"expected one connect closing the {tg} foot, found {len(self.eq)}")
        self.pad, self.toe = geom(model, f"c_paw_h{tg}/collision0"), geom(model, f"c_paw_h{tg}/collision1")
        self.case = geom(model, f"c_qdd_hock_{tg}/collision0")
        self.shin_body = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, "c_shin_" + tg)
        self.paw_body = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, "c_paw_h" + tg)
        self.rod_body = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, "c_rod_h" + tg)
        self.guess = np.zeros(len(self.passive))
        mujoco.mj_forward(model, self.d)
        self.shin0 = self.pitch(self.shin_body)
        x0 = self.sole_pitch()
        self.seat = x0              # the sole's pitch at the build pose

    def residual(self, x):
        self.d.qpos[self.passive] = x
        mujoco.mj_kinematics(self.m, self.d)
        i = self.eq[0]
        o1, o2 = self.m.eq_obj1id[i], self.m.eq_obj2id[i]
        if self.m.eq_objtype[i] == mujoco.mjtObj.mjOBJ_SITE:
            p1, p2 = self.d.site_xpos[o1], self.d.site_xpos[o2]
        else:
            a1, a2 = self.m.eq_data[i, 0:3], self.m.eq_data[i, 3:6]
            p1 = self.d.xpos[o1] + self.d.xmat[o1].reshape(3, 3) @ a1
            p2 = self.d.xpos[o2] + self.d.xmat[o2].reshape(3, 3) @ a2
        return (p1 - p2) * 1000.0

    def pose(self, hock_deg, knee_deg=0.0):
        self.d.qpos[:] = self.m.qpos0
        self.d.qpos[self.knee] = math.radians(knee_deg)
        self.d.qpos[self.hock] = math.radians(hock_deg)
        sol = least_squares(self.residual, self.guess, xtol=1e-12, ftol=1e-12)
        self.guess = sol.x
        r = float(np.linalg.norm(self.residual(sol.x)))
        mujoco.mj_kinematics(self.m, self.d)
        return r

    def pitch(self, body):
        R = self.d.xmat[body].reshape(3, 3)
        return math.degrees(math.atan2(-R[2, 0], R[0, 0]))     # rotation about +y, x toward -z

    def sphere(self, g):
        return self.d.geom_xpos[g].copy(), float(self.m.geom_size[g, 0])

    def sole_pitch(self):
        """The common tangent under the pad and toe spheres, deg, toes-down positive."""
        (cp, rp), (ct, rt) = self.sphere(self.pad), self.sphere(self.toe)
        dx, dz = ct[0] - cp[0], ct[2] - cp[2]
        L = math.hypot(dx, dz)
        # a line under both circles at angle a (its upward normal n = (-sin a, cos a)):
        # n . (ct - cp) = rt - rp, i.e. L cos(a + b) = rt - rp with b = atan2(dx, dz)
        b, w = math.atan2(dx, dz), math.acos((rt - rp) / L)
        centre = math.atan2(dz, dx)
        a = min((-b + w, -b - w), key=lambda v: abs(math.remainder(v - centre, 2.0 * math.pi)))
        return -math.degrees(math.remainder(a, 2.0 * math.pi))

    def floor_mm(self):
        """The floor under the paw: its lowest collision point."""
        return min(self.sphere(g)[0][2] - self.sphere(g)[1] for g in (self.pad, self.toe)) * 1000.0

    def case_height_mm(self):
        c, r = self.sphere(self.case)
        return (c[2] - r) * 1000.0 - self.floor_mm()

    def rod_ends(self):
        """The rod's two pin centres: a kept joint's anchor, or the closure's site."""
        ends = []
        for n in ("rodtop", "rodbot"):
            j = mujoco.mj_name2id(self.m, mujoco.mjtObj.mjOBJ_JOINT, self.name(n))
            if j >= 0:
                ends.append(self.d.xanchor[j].copy())
            else:
                ends.append(self.d.site_xpos[self.m.eq_obj1id[self.eq[0]]].copy())
        return ends

    def rod_lever_mm(self):
        """The rod's moment arm about the paw pin, and the rod's length."""
        pin = self.d.xanchor[mujoco.mj_name2id(self.m, mujoco.mjtObj.mjOBJ_JOINT, self.name("pawpin"))].copy()
        top, bot = self.rod_ends()
        u = (top - bot)[[0, 2]]
        Lr = float(np.linalg.norm(u))
        u /= Lr
        v = (pin - bot)[[0, 2]]
        return abs(v[0] * u[1] - v[1] * u[0]) * 1000.0, Lr * 1000.0, pin

    def name(self, n):
        return f"j_{n}_{'l' if self.s > 0 else 'r'}"


def main(argv):
    path = argv[0]
    side = argv[argv.index("--side") + 1] if "--side" in argv else "l"
    m = mujoco.MjModel.from_xml_path(path)
    leg = Leg(m, side)
    s = leg.s
    mass = float(sum(m.body_mass))
    weight = mass * 9.81
    print(f"{path}\n  model mass {mass:.2f} kg, weight {weight:.1f} N; side {side};"
          f" sole at the build pose {leg.seat:+.1f} deg from flat")

    lo, hi = (math.degrees(v) for v in m.jnt_range[mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_JOINT, leg.name("hock"))])
    hocks = np.arange(math.ceil(min(lo, hi)), math.floor(max(lo, hi)) + 1)
    # walk out from the build pose both ways so the solver stays on the assembled branch
    order = [h for h in hocks if h >= 0] + [h for h in sorted(hocks[hocks < 0], reverse=True)]
    curve, worst = {}, 0.0
    leg.guess = np.zeros(len(leg.passive))
    for h in order:
        if h == -1:
            leg.guess = np.zeros(len(leg.passive))
        r = leg.pose(h)
        worst = max(worst, r)
        lever, Lr, _ = leg.rod_lever_mm()
        curve[float(h)] = (math.degrees(leg.d.qpos[leg.pin]), leg.sole_pitch(), lever, Lr)
    hs = sorted(curve)
    print(f"\n  coupling over hock {hs[0] * s:+.0f}..{hs[-1] * s:+.0f} deg (closure residual worst {worst:.4f} mm)")
    print("   hock   pin    sole(shin at build)  rod lever  rod length")
    for h in hs:
        if int(h) % 10 == 0:
            pin, sole, lever, Lr = curve[h]
            print(f"  {h * s:+5.0f}  {pin * s:+6.1f}  {sole:+6.1f}              {lever:5.1f}     {Lr:6.2f}")
    pins = np.array([curve[h][0] for h in hs])
    slope = np.polyfit(np.array(hs), pins, 1)
    print(f"  least-squares line: pin = {slope[1] * s:+.1f} {slope[0]:+.3f} * hock (fit rms"
          f" {float(np.sqrt(np.mean((np.polyval(slope, hs) - pins) ** 2))):.2f} deg)")

    print("\n  static check: trunk level; at each shin pitch the hock lays down (to its stop at most)"
          " until the case meets the floor under the paw")
    rows = []
    for shin in np.arange(0.0, -28.1, -2.0):
        # the knee turns the shin; find the knee angle that pitches it `shin` from build
        def f(k):
            leg.guess = np.zeros(len(leg.passive))
            leg.pose(0.0, k)
            return leg.pitch(leg.shin_body) - leg.shin0 - shin
        k = 0.0
        for _ in range(40):
            e = f(k)
            if abs(e) < 1e-6:
                break
            k -= e / ((f(k + 0.01) - e) / 0.01)
        leg.guess = np.zeros(len(leg.passive))
        best = None
        for h in np.arange(0.0, min(lo, hi) * s - 1e-9 if s > 0 else -max(lo, hi) - 1e-9, -0.25):
            r = leg.pose(h * s, k)
            case = leg.case_height_mm()
            best = (h, leg.sole_pitch(), case, r)
            if case <= 0.0:
                break
        h, sole, case, r = best
        ok = abs(sole) <= 8.0 and case <= 10.0
        rows.append((shin, h, sole, case, ok))
        print(f"   shin {shin:+5.0f}  hock {h:+6.2f}  sole {sole:+5.1f} deg  case {max(case, 0.0):5.1f} mm over the floor"
              f"  closure {r:.4f} mm  {'PASS' if ok else 'FAIL'} (sole <= 8, case <= 10)")

    band = [r[0] for r in rows if r[4]]
    print(f"   passes for shin pitch {max(band):+.0f}..{min(band):+.0f} deg" if band else "   passes at no shin pitch")
    print("\n  link loads, 3x body weight up the toes (the toe sphere's lowest point, or 30 mm ahead of the"
          " pin if that is further), shin at build")
    push = 3.0 * weight
    leg.guess = np.zeros(len(leg.passive))
    for h in (-60.0, -40.0, -20.0, 0.0, 20.0, 40.0):
        hh = h * s
        leg.guess = np.zeros(len(leg.passive))
        for x in np.linspace(0.0, hh, 31):
            leg.pose(x)
        lever, Lr, pin = leg.rod_lever_mm()
        c, r = leg.sphere(leg.toe)
        arm = abs(c[0] - pin[0]) * 1000.0
        arm = max(arm, 30.0)   # never under the study's case: the toe beans' front, 30 mm ahead
        M = push * arm / 1000.0
        F = M * 1000.0 / lever
        shear = F / (2.0 * math.pi * (PIN_M5_MM / 2.0) ** 2)
        euler = math.pi ** 2 * STEEL_E_MPA * (math.pi * ROD_ROOT_MM ** 4 / 64.0) / Lr ** 2
        print(f"   hock {h:+4.0f}: toe {arm:4.1f} mm ahead of the pin, pin moment {M:5.1f} N*m,"
              f" rod lever {lever:4.1f} mm -> rod {F:6.0f} N; M5 pin double shear {shear:4.1f} MPa;"
              f" Euler {euler:5.0f} N ({euler / F:.1f}x)")

    if "--png" in argv:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        bg, fg, grid = "#15171a", "#d7dae0", "#2c3036"
        fig, ax = plt.subplots(figsize=(7.2, 4.2), dpi=100)
        fig.patch.set_facecolor(bg)
        ax.set_facecolor(bg)
        H = np.array(hs) * s
        ax.plot(H, pins * s, color="#5fb3ff", lw=2.0, label="paw pin (built rod, from the build pose)")
        ax.plot(H, np.array([curve[h][1] for h in hs]), color="#ff9f43", lw=1.6,
                label="sole from flat, shin at build (+ toes-down)")
        ax.axhspan(-8.0, 8.0, color="#3a4a3a", alpha=0.5, label="sole within 8 deg")
        ax.set_xlabel("hock, deg (metatarsus against shin)", color=fg)
        ax.set_ylabel("deg", color=fg)
        ax.set_title("orun11 coupled hind foot, as built: paw against hock", color=fg, fontsize=11)
        ax.tick_params(colors=fg)
        for sp in ax.spines.values():
            sp.set_color(grid)
        ax.grid(color=grid, lw=0.6)
        ax.legend(facecolor=bg, edgecolor=grid, labelcolor=fg, fontsize=8)
        fig.tight_layout()
        fig.savefig(argv[argv.index("--png") + 1], facecolor=bg)
    return 0 if any(r[4] for r in rows) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
