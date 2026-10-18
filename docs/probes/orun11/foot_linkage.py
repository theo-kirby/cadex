"""orun11 M1: three coupled hind-foot linkages, sketched and compared.

Usage: pixi run python docs/probes/orun11/foot_linkage.py [--png OUT.png]

Planar study in the sagittal plane of ``orun11-cat``'s hind leg (build pose,
mm, x forward, z up): the hock axis A (-262, 135) on the shin, the paw pin B
(-222, 52) at the foot of the metatarsus, the paw seated PAW_SEAT = -36 deg
(toes up) about B. Angles are about +y, positive toes-down, as the left
leg's hinges; ``hock`` is the metatarsus against the shin and ``pin`` the paw
against the metatarsus, both from the build pose, so the sole is flat when
``shin + hock + pin = 36`` (shin = the shin's own pitch, 0 at build).

The target coupling: with the shin at its build pitch,
  * plantigrade at the hock's -60 stop: the metatarsus level, so the hock
    axis is 40 mm over the floor and the AK60's case (r 39.5) touches it,
    and the paw flat, pin +96 (the charter's figure);
  * on the toes at toe-off, the hock at 0..+20: the sole 15..45 deg
    toes-down of flat.
A straight line through both, pin = 60 - 0.6 * hock, keeps the sole within
8 deg of flat from hock -60 to -40 and puts it 24 deg on its toes at hock 0
and 36 at +20. Every candidate is scored against that line.

Candidates (each a real part; packaging from the cat's hind leg):
  A  rod from the shank: a rod end on a lug on the shin plate 60-110 mm up
     the shin from A, a long rod down to a horn on the paw (four-bar
     shin - metatarsus - paw - rod).
  B  four-bar off the hock housing: a rod end on a lug at the AK60
     housing's rim (r 44-55 from A), a short rod to the paw horn.
  C  tendon: a cable from a sector on the hock housing (r >= 44, it must
     clear the case) to a pulley on the paw (r <= 28, the paw is 46 mm
     long), with a return spring; the ratio is r_h / r_p, exactly linear.
The rod runs inboard of the metatarsus plate, in the plane of the drive
case, so along its whole length it keeps 42 mm from A (case r 39.5 + 2.5)
or is below the case; the paw horn sits inside the paw's outline over the
sole (z above the pad's top at 46 in the paw frame minus the pad, r 15-32
from B).

Load case: 3x body weight (3 x 307 N, the t2-g5 model's weight) on the toes
(30 mm ahead of B, the toe beans' front), the hock case just off the floor:
the pin moment the link holds is 922 N x 30 mm = 27.7 N*m, and the link
force is that moment over the link's lever about B at the pose.
"""

from __future__ import annotations

import math
import sys

import numpy as np
from scipy.optimize import minimize

A = np.array([-262.0, 135.0])
B = np.array([-222.0, 52.0])
SEAT = -36.0
WEIGHT_N = 307.3                     # t2-g5 model (evaluation rig)
PUSH_N = 3.0 * WEIGHT_N
TOE_LEVER_MM = 30.0
CASE_CLEAR_MM = 42.0
HOCK = np.linspace(-60.0, 40.0, 101)


def target(h):
    return 60.0 - 0.6 * np.asarray(h)


def rot(v, deg, about):
    """Rotate point v about `about` by deg about +y (x toward -z)."""
    a = math.radians(deg)
    d = np.asarray(v) - about
    return about + np.array([d[0] * math.cos(a) + d[1] * math.sin(a),
                             -d[0] * math.sin(a) + d[1] * math.cos(a)])


def meta_frame(point_on_shin, hock):
    """A shin-fixed point seen from the metatarsus: the shin turns by -hock about A."""
    return rot(point_on_shin, -hock, A)


def solve_pin(S0, P0, L, hock, guess):
    """Pin angle that puts paw point P0 (build pose) at distance L from the shin point.

    |B + R(x) d - S| = L with d = P0 - B, e = S - B gives e . R(x) d = c: two
    roots, of which the one nearer the previous pose (the assembly branch).
    """
    S = meta_frame(S0, hock)
    d, e = np.asarray(P0) - B, S - B
    c = (d @ d + e @ e - L * L) / 2.0
    # R(x) d = (dx cos + dz sin, -dx sin + dz cos); e . R d = a cos x + b sin x
    a = e[0] * d[0] + e[1] * d[1]
    b = e[0] * d[1] - e[1] * d[0]
    rho = math.hypot(a, b)
    if rho < 1e-9 or abs(c) > rho:
        return None
    phi, w = math.atan2(b, a), math.acos(c / rho)
    roots = [math.degrees(phi + w), math.degrees(phi - w)]
    roots = [r + 360.0 * round((guess - r) / 360.0) for r in roots]
    return min(roots, key=lambda r: abs(r - guess))


def seg_dist(p, a, b):
    ab = b - a
    t = np.clip(np.dot(p - a, ab) / np.dot(ab, ab), 0.0, 1.0)
    return float(np.linalg.norm(a + t * ab - p))


def four_bar(S0, P0, L=None, in_case_plane=True):
    """The pin curve, transmission angle and rod clearance over the hock range."""
    if L is None:   # rod length that puts the plantigrade pose on the target
        L = float(np.linalg.norm(rot(P0, target(-60.0), B) - meta_frame(S0, -60.0)))
    pins, trans, clear, lever = [], [], [], []
    guess = float(target(-60.0))
    for h in HOCK:
        x = solve_pin(S0, P0, L, h, guess)
        if x is None or abs(x - guess) > 10.0:   # past a toggle, or the branch jumped
            return None
        guess = x
        S, P = meta_frame(S0, h), rot(P0, x, B)
        rod, horn = S - P, P - B
        c = abs(np.dot(rod, horn)) / (np.linalg.norm(rod) * np.linalg.norm(horn))
        trans.append(math.degrees(math.acos(min(1.0, c))))
        # the rod is in the drive case's plane: its nearest approach to A, unless
        # it is wholly below the case (the case reaches z = A_z - 39.5)
        below = max(S[1], P[1]) < A[1] - 39.5
        clear.append(seg_dist(A, S, P) if in_case_plane and not below else 1e3)
        u = rod / np.linalg.norm(rod)
        lever.append(abs(horn[0] * u[1] - horn[1] * u[0]))   # moment arm of the rod about B
        pins.append(x)
    return {"pin": np.array(pins), "trans": np.array(trans), "clear": np.array(clear),
            "lever": np.array(lever), "L": L}


def score(curve):
    if curve is None:
        return 1e6
    e = curve["pin"] - target(HOCK)
    s = float(np.mean(e ** 2))
    s += 50.0 * max(0.0, abs(e[0]) - 2.0) ** 2                    # plantigrade
    s += 5.0 * float(np.sum(np.maximum(0.0, 60.0 - curve["trans"]) ** 2))
    s += 5.0 * float(np.sum(np.maximum(0.0, CASE_CLEAR_MM - curve["clear"]) ** 2))
    return s


def shin_dir():
    """Unit vector up the shin, from the hock to the knee (-180, 252)."""
    d = np.array([-180.0, 252.0]) - A
    return d / np.linalg.norm(d)


def place(params, family):
    rS, aS, rP, aP = params
    # A: a lug on the shin plate's inboard face; B: a lug on the housing rim
    S0 = A + rS * np.array([math.cos(math.radians(aS)), math.sin(math.radians(aS))])
    P0 = B + rP * np.array([math.cos(math.radians(aP)), math.sin(math.radians(aP))])
    return S0, P0


BOUNDS = {"A": [(10.0, 30.0), (-180.0, 180.0), (15.0, 32.0), (-180.0, 180.0)],
          "B": [(44.0, 55.0), (-180.0, 180.0), (15.0, 32.0), (-180.0, 180.0)]}


def fit(family, seed=0):
    rng = np.random.default_rng(seed)
    bounds = BOUNDS[family]

    def f(x):
        x = [min(max(v, lo), hi) for v, (lo, hi) in zip(x, bounds)]
        return score(four_bar(*place(x, family), in_case_plane=family == "B"))

    best = None
    for _ in range(400):
        x0 = [rng.uniform(lo, hi) for lo, hi in bounds]
        s = f(x0)
        if best is None or s < best[0]:
            best = (s, x0)
    starts = [best[1]] + [[rng.uniform(lo, hi) for lo, hi in bounds] for _ in range(12)]
    out = None
    for x0 in starts:
        r = minimize(f, x0, method="Nelder-Mead", options={"maxiter": 3000, "xatol": 1e-3, "fatol": 1e-4})
        if out is None or r.fun < out.fun:
            out = r
    x = [min(max(v, lo), hi) for v, (lo, hi) in zip(out.x, bounds)]
    return x, four_bar(*place(x, family), in_case_plane=family == "B")


def tendon(r_h, r_p):
    """A cable from a sector fixed to the shin, about A, to a pulley on the paw."""
    k = r_h / r_p
    return {"pin": 96.0 - k * (HOCK + 60.0), "r_h": r_h, "r_p": r_p, "k": k}


def sole_from_flat(h, pin, shin=0.0):
    return shin + h + pin - 36.0


def report(name, curve, extra=""):
    pin = curve["pin"]
    i = {h: int(round(h - HOCK[0])) for h in (-60, -40, 0, 20, 40)}
    e = pin - target(HOCK)
    flat = HOCK[np.abs(sole_from_flat(HOCK, pin)) <= 8.0]
    print(f"\n{name} {extra}")
    print("  hock  " + "  ".join(f"{h:+5d}" for h in i))
    print("  pin   " + "  ".join(f"{pin[j]:5.1f}" for j in i.values()))
    print("  sole  " + "  ".join(f"{sole_from_flat(HOCK[j], pin[j]):+5.1f}" for j in i.values())
          + "   (deg toes-down of flat, shin at build)")
    print(f"  rms off the target {math.sqrt(float(np.mean(e ** 2))):.1f} deg, worst {float(np.max(np.abs(e))):.1f}")
    print(f"  sole within 8 deg of flat for hock {flat.min():+.0f}..{flat.max():+.0f}" if flat.size else
          "  sole never within 8 deg of flat")
    if "trans" in curve:
        print(f"  rod {curve['L']:.1f} mm; transmission {curve['trans'].min():.0f}..{curve['trans'].max():.0f} deg;"
              f" nearest the case axis {min(curve['clear'].min(), 999):.0f} mm")
        lever = curve["lever"]
        M = PUSH_N * TOE_LEVER_MM
        print(f"  3x BW on the toes: pin moment {M / 1000:.1f} N*m; rod force {M / lever[0]:.0f} N at plantigrade,"
              f" {M / lever.min():.0f} N worst over the range (lever {lever.min():.1f}-{lever.max():.1f} mm)")
    else:
        M = PUSH_N * TOE_LEVER_MM
        print(f"  3x BW on the toes: cable tension {M / curve['r_p']:.0f} N (r_p {curve['r_p']:.0f} mm)")


def plot(curves, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    bg, fg, grid = "#15171a", "#d7dae0", "#2c3036"
    fig, ax = plt.subplots(figsize=(7.2, 4.4), dpi=100)
    fig.patch.set_facecolor(bg)
    ax.set_facecolor(bg)
    ax.fill_between(HOCK, 36.0 - HOCK - 8.0, 36.0 - HOCK + 8.0, color="#3a4a3a", alpha=0.6,
                    label="sole within 8 deg of flat (shin at build)")
    ax.fill_between(HOCK[60:], 36.0 - HOCK[60:] + 15.0, 36.0 - HOCK[60:] + 45.0, color="#4a3f2a", alpha=0.6,
                    label="on the toes, 15-45 deg (toe-off)")
    ax.plot(HOCK, target(HOCK), color=fg, lw=1.2, ls="--", label="target 60 - 0.6 hock")
    for (name, c), col in zip(curves.items(), ("#5fb3ff", "#ff9f43", "#c77dff", "#7ee08a")):
        ax.plot(HOCK, c["pin"], color=col, lw=2.0, ls=":" if name.startswith("C tendon inboard") else "-", label=name)
    ax.scatter([-60.0], [96.0], color="#ffffff", zorder=5, s=24)
    ax.annotate("plantigrade: hock -60, pin +96", (-60.0, 96.0), (-52.0, 104.0), color=fg, fontsize=8)
    ax.set_xlabel("hock (metatarsus against shin), deg", color=fg)
    ax.set_ylabel("paw pin (paw against metatarsus), deg", color=fg)
    ax.set_title("orun11 coupled hind foot: paw against hock", color=fg, fontsize=11)
    ax.tick_params(colors=fg)
    for s in ax.spines.values():
        s.set_color(grid)
    ax.grid(color=grid, lw=0.6)
    ax.set_ylim(-20.0, 130.0)
    ax.legend(facecolor=bg, edgecolor=grid, labelcolor=fg, fontsize=7.5, loc="lower left")
    fig.tight_layout()
    fig.savefig(path, facecolor=bg)


def main(argv):
    curves = {}
    for fam, name in (("A", "A rod from the shank"), ("B", "B four-bar off the hock housing")):
        x, c = fit(fam)
        S0, P0 = place(x, fam)
        report(name, c, f"S ({S0[0]:.1f}, {S0[1]:.1f}) P ({P0[0]:.1f}, {P0[1]:.1f}) at build"
                        f" [r_S {x[0]:.1f}, r_P {x[2]:.1f} mm]")
        curves[name] = c
    for r_h, r_p, where in ((44.0, 28.0, "on the housing rim"), (15.0, 25.0, "inboard of the shin plate")):
        t = tendon(r_h, r_p)
        report(f"C tendon, sector {where}", t, f"r_h {r_h:.0f} / r_p {r_p:.0f} = {t['k']:.2f}")
        curves[f"C tendon {where} ({r_h:.0f}/{r_p:.0f})"] = t
    if "--png" in argv:
        plot(curves, argv[argv.index("--png") + 1])


if __name__ == "__main__":
    main(sys.argv[1:])
