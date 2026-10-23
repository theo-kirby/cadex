"""Find AcinoSet's steady cheetah gallop strides, and measure the pose noise (orun18 C4).

usage: pixi run python -I docs/probes/orun18/acino_strides.py ROOT [--cutoff HZ] [--json OUT]

``ROOT`` is ``~/mocap/acinoset/`` (D5a: AcinoSet, Joska et al. ICRA 2021, cited in
SOURCES.md; never committed). Every ``**/fte_pw/fte.pickle`` under it is read: the
FTE baseline's 3D trajectory, 20 points on a 14-body cheetah model (eyes, nose,
neck base, spine, tail base, mid, tip; per leg the girdle point, knee/elbow and
the distal "ankle", the model's end point: it has no paw), in metres, z up.

**Safety.** The files are pickles from outside the repository, so they are read by
an unpickler that refuses every class but numpy's array reconstruction: a pickle
that names anything else stops the read.

**Frame rate.** Read from each file, not assumed: the FTE stores the state ``x``
and its rate ``dx``, so ``dx / diff(x)`` is the rate it was solved at (90 in 2017,
120 in 2019; the 2019 videos' metadata says 119.88).

**Noise and the filter.** The FTE is a smoothed estimate (a kinematic model with
fixed bone lengths, fitted with a motion prior), but frame-to-frame jitter
survives it. Two readings, before and after a zero-phase 4th-order Butterworth
low-pass at ``--cutoff`` (default 12 Hz, about four harmonics of a gallop's
~3 Hz stride):

- the residual: RMS of raw minus filtered position, per point group, in mm; it is
  what the filter removes;
- the share of the raw acceleration's power above the cutoff: how much of the
  signal the filter calls noise.

Run at three cutoffs, these bound the noise from above (all of it above the
cutoff is called noise) and show where the filter starts to cut motion (the
strides it finds change). The distal point's travel over a detected stance is
also reported, raw and filtered; it is **not** a noise reading here: the point is
the wrist or hock, which really moves while the paw is planted, and the filter
leaves it unchanged.

**Footfalls.** A distal point is down when it is within ``CONTACT_M`` of its own
floor (its 5th percentile height over the take) and moving horizontally at under
``CONTACT_SPEED`` of the trunk's speed, on the filtered track, with lifts of up to
``CONTACT_GAP_S`` closed. The distal point is the model's ankle, not the paw, so
it reads stance as "the wrist or hock stops moving", which is late in a fore
stance and early in a hind one; the order of touchdowns is what this probe
claims, not their exact frames.

**Strides.** From one left-hind touchdown to the next. Each gets the trunk
speed (the spine point's horizontal travel over its duration), heading change,
speed change from its first half to its second, each foot's touchdown phase, the
footfall order, the share of frames with no foot down (flight), and duty per
foot. A stride is **steady** when its heading turns under ``STEADY_DEG`` and its
speed changes under ``STEADY_DV`` between halves, and every foot touched down once.
"""

from __future__ import annotations

import argparse
import json
import math
import pickle
from pathlib import Path

import numpy as np
from scipy.signal import butter, filtfilt

POINTS = ["l_eye", "r_eye", "nose", "neck_base", "spine", "tail_base", "tail_mid", "tail_tip",
          "l_shoulder", "l_front_knee", "l_front_ankle", "r_shoulder", "r_front_knee", "r_front_ankle",
          "l_hip", "l_back_knee", "l_back_ankle", "r_hip", "r_back_knee", "r_back_ankle"]
FEET = {"LF": "l_front_ankle", "RF": "r_front_ankle", "LH": "l_back_ankle", "RH": "r_back_ankle"}
GROUPS = {"head": ["l_eye", "r_eye", "nose"], "trunk": ["neck_base", "spine", "tail_base"],
          "tail": ["tail_mid", "tail_tip"], "knees": ["l_front_knee", "r_front_knee", "l_back_knee", "r_back_knee"],
          "distal": list(FEET.values())}
CONTACT_M = 0.04       # within 40 mm of the foot's own floor,
CONTACT_SPEED = 0.35   # and moving at under 0.35 of the trunk's speed, is down
CONTACT_GAP_S = 0.025  # lifts this short are closed (2-3 frames)
STEADY_DEG = 10.0      # heading change over a stride
STEADY_DV = 0.10       # speed change between a stride's halves, as a share
CITATION = ("Joska D., Clark L., Muramatsu N., Jericevich R., Nicolls F., Mathis A., Mathis M.W., "
            "Patel A. 2021. AcinoSet: A 3D Pose Estimation Dataset and Baseline Models for Cheetahs "
            "in the Wild. ICRA 2021, arXiv 2103.13282 (github.com/African-Robotics-Unit/AcinoSet).")


class _Arrays(pickle.Unpickler):
    ALLOWED = {("numpy.core.multiarray", "_reconstruct"), ("numpy._core.multiarray", "_reconstruct"),
               ("numpy.core.multiarray", "scalar"), ("numpy._core.multiarray", "scalar"),
               ("numpy", "ndarray"), ("numpy", "dtype")}

    def find_class(self, module, name):
        if (module, name) not in self.ALLOWED:
            raise pickle.UnpicklingError(f"refused {module}.{name}")
        return super().find_class(module.replace("numpy.core", "numpy._core"), name)


def load(path: Path) -> dict:
    with path.open("rb") as handle:
        data = _Arrays(handle).load()
    pos = np.asarray(data["positions"], dtype=float)
    x, dx = np.asarray(data["x"], dtype=float), np.asarray(data["dx"], dtype=float)
    step = np.diff(x, axis=0)
    ratio = dx[1:][np.abs(step) > 1e-4] / step[np.abs(step) > 1e-4]
    return {"pos": pos, "fps": float(np.round(np.median(ratio), 2)), "start_frame": int(data["start_frame"])}


def lowpass(pos: np.ndarray, fps: float, cutoff: float) -> np.ndarray:
    b, a = butter(4, cutoff / (fps / 2.0))
    return filtfilt(b, a, pos, axis=0, padlen=min(3 * max(len(a), len(b)), len(pos) - 1))


def contacts(pos: np.ndarray, fps: float) -> dict[str, np.ndarray]:
    dt = 1.0 / fps
    trunk = np.linalg.norm(np.gradient(pos[:, POINTS.index("spine"), :2], dt, axis=0), axis=1)
    down = {}
    for leg, point in FEET.items():
        p = pos[:, POINTS.index(point)]
        speed = np.linalg.norm(np.gradient(p[:, :2], dt, axis=0), axis=1)
        d = (p[:, 2] - np.percentile(p[:, 2], 5) < CONTACT_M) & (speed < CONTACT_SPEED * np.maximum(trunk, 0.5))
        gap = int(round(CONTACT_GAP_S * fps))
        idx = np.flatnonzero(d)
        for a, b in zip(idx[:-1], idx[1:]):
            if 1 < b - a <= gap + 1:
                d[a:b] = True
        down[leg] = d
    return down


def stances(d: np.ndarray) -> list[tuple[int, int]]:
    edges = np.diff(np.concatenate([[0], d.astype(int), [0]]))
    return list(zip(np.flatnonzero(edges == 1), np.flatnonzero(edges == -1)))


def hip_height(pos: np.ndarray) -> float:
    """Hind hip over the hind distal points' floor (their 5th percentile): the
    hock stands above the paw, so this is short of the true hip height by the
    planted hock's height."""

    hips = pos[:, [POINTS.index("l_hip"), POINTS.index("r_hip")], 2].mean(1)
    floor = np.percentile(pos[:, [POINTS.index(FEET["LH"]), POINTS.index(FEET["RH"])], 2], 5)
    return round(float(np.median(hips) - floor), 3)


def slip(pos: np.ndarray, down: dict, fps: float) -> dict:
    dt, speeds, travels = 1.0 / fps, [], []
    for leg, point in FEET.items():
        p = pos[:, POINTS.index(point), :2]
        v = np.linalg.norm(np.gradient(p, dt, axis=0), axis=1)
        for a, b in stances(down[leg]):
            if b - a >= 3:
                speeds.append(v[a:b])
                travels.append(float(np.linalg.norm(p[b - 1] - p[a])))
    if not speeds:
        return {"rms_mm_s": None, "travel_mm": None, "stances": 0}
    return {"rms_mm_s": round(1000 * float(np.sqrt(np.mean(np.concatenate(speeds) ** 2))), 1),
            "travel_mm": round(1000 * float(np.median(travels)), 1), "stances": len(travels)}


def strides(pos: np.ndarray, down: dict, fps: float) -> list[dict]:
    spine = pos[:, POINTS.index("spine"), :2]
    touch = {leg: [a for a, _ in stances(d) if a > 0] for leg, d in down.items()}
    out = []
    for f0, f1 in zip(touch["LH"][:-1], touch["LH"][1:]):
        n = f1 - f0
        mid = f0 + n // 2
        v1 = np.linalg.norm(spine[mid] - spine[f0]) / ((mid - f0) / fps)
        v2 = np.linalg.norm(spine[f1] - spine[mid]) / ((f1 - mid) / fps)
        h1 = math.atan2(*(spine[mid] - spine[f0])[::-1])
        h2 = math.atan2(*(spine[f1] - spine[mid])[::-1])
        phases = {leg: [round((t - f0) / n, 2) for t in ts if f0 <= t < f1] for leg, ts in touch.items()}
        once = all(len(v) == 1 for v in phases.values())
        order = "".join(sorted(phases, key=lambda k: phases[k][0] if phases[k] else 9)) if once else "-"
        any_down = np.any([down[leg][f0:f1] for leg in FEET], axis=0)
        turn = abs(math.degrees((h2 - h1 + math.pi) % (2 * math.pi) - math.pi))
        dv = abs(v2 - v1) / max(v1, 1e-6)
        out.append({
            "frames": [int(f0), int(f1)], "period_s": round(n / fps, 3),
            "speed_m_s": round(float(np.linalg.norm(spine[f1] - spine[f0]) / (n / fps)), 2),
            "turn_deg": round(turn, 1), "dv": round(dv, 3),
            "phases": phases, "order": order,
            "gait": _gait(phases),
            "flight": round(float(1.0 - np.mean(any_down)), 2),
            "duty": {leg: round(float(np.mean(down[leg][f0:f1])), 2) for leg in FEET},
            "steady": bool(once and turn < STEADY_DEG and dv < STEADY_DV),
        })
    return out


def _gait(phases: dict) -> str:
    """Rotary when the hind pair's lead (the second of the pair to land, read
    cyclically: the one the other reaches within half a stride) is on the side
    the fore pair's lead is not; transverse when both lead on one side."""

    if not all(len(v) == 1 for v in phases.values()):
        return "-"

    def lead(a, b):
        return b if (phases[b][0] - phases[a][0]) % 1.0 < 0.5 else a

    return "transverse" if lead("LH", "RH")[0] == lead("LF", "RF")[0] else "rotary"


def residual(raw: np.ndarray, filt: np.ndarray) -> dict:
    return {g: round(1000 * float(np.sqrt(np.mean(np.sum((raw[:, [POINTS.index(p) for p in pts]]
                                                           - filt[:, [POINTS.index(p) for p in pts]]) ** 2, axis=-1)))), 1)
            for g, pts in GROUPS.items()}


def high_share(raw: np.ndarray, fps: float, cutoff: float) -> float:
    acc = np.diff(raw, n=2, axis=0) * fps * fps
    spec = np.abs(np.fft.rfft(acc - acc.mean(0), axis=0)) ** 2
    freq = np.fft.rfftfreq(len(acc), 1.0 / fps)
    return round(float(spec[freq > cutoff].sum() / spec.sum()), 3)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("--cutoff", type=float, default=12.0)
    parser.add_argument("--json", type=Path)
    parser.add_argument("--leo-hip", type=float, default=0.396,
                        help="leo v05's hind hip height (froude.py); a stride's leo speed keeps its Froude number")
    args = parser.parse_args()
    takes = []
    for path in sorted(args.root.glob("**/fte_pw/fte.pickle")):
        take = load(path)
        raw, fps = take["pos"], take["fps"]
        if len(raw) < 20:
            continue
        filt = lowpass(raw, fps, args.cutoff)
        down = contacts(filt, fps)
        name = str(path.relative_to(args.root).parent.parent)
        row = {"take": name, "fps": fps, "frames": len(raw),
               "hip_height_m": hip_height(raw),
               "speed_m_s": round(float(np.linalg.norm(raw[-1, 4, :2] - raw[0, 4, :2]) / (len(raw) / fps)), 2),
               "residual_mm": residual(raw, filt), "accel_power_above_cutoff": high_share(raw, fps, args.cutoff),
               "slip_raw": slip(raw, down, fps), "slip_filtered": slip(filt, down, fps),
               "strides": strides(filt, down, fps)}
        takes.append(row)
    steady = [(t["take"], s) for t in takes for s in t["strides"] if s["steady"]]
    hips = {t["take"]: t["hip_height_m"] for t in takes}
    for name, s in steady:
        s["froude"] = round(s["speed_m_s"] ** 2 / (9.81 * hips[name]), 2)
        s["leo_m_s"] = round(math.sqrt(s["froude"] * 9.81 * args.leo_hip), 2)
    print(f"{len(takes)} takes, {sum(len(t['strides']) for t in takes)} LH-to-LH strides, {len(steady)} steady "
          f"(turn < {STEADY_DEG} deg, speed change < {STEADY_DV:.0%}, each foot once); cutoff {args.cutoff} Hz")
    print(f"{'take':34s} {'frames':>9s} {'v':>5s} {'T':>5s} {'order':9s} {'gait':10s} {'flight':>6s} {'hip':>5s} {'Fr':>5s} {'leo':>5s}  phases LF RF LH RH")
    for name, s in sorted(steady, key=lambda r: r[1]["speed_m_s"]):
        ph = " ".join(f"{s['phases'][k][0]:.2f}" for k in ("LF", "RF", "LH", "RH"))
        print(f"{name:34s} {s['frames'][0]:4d}-{s['frames'][1]:<4d} {s['speed_m_s']:5.2f} {s['period_s']:5.3f} "
              f"{s['order']:9s} {s['gait']:10s} {s['flight']:6.2f} {hips[name]:5.2f} {s['froude']:5.1f} {s['leo_m_s']:5.2f}  {ph}")
    def pooled(key, sub):
        vals = [t[key][sub] for t in takes if t[key][sub] is not None]
        return float(np.median(vals)) if vals else float("nan")
    print("\nnoise (median over takes): residual mm " + ", ".join(
        f"{g} {pooled('residual_mm', g):.1f}" for g in GROUPS)
        + f"; accel power above cutoff {np.median([t['accel_power_above_cutoff'] for t in takes]):.2f}")
    print(f"distal point in stance (wrist/hock, real motion, not noise), raw: speed RMS {pooled('slip_raw', 'rms_mm_s'):.0f} mm/s,"
          f" travel {pooled('slip_raw', 'travel_mm'):.0f} mm; filtered: {pooled('slip_filtered', 'rms_mm_s'):.0f} mm/s,"
          f" {pooled('slip_filtered', 'travel_mm'):.0f} mm; hind hip height median {np.median(list(hips.values())):.2f} m")
    if args.json:
        args.json.write_text(json.dumps({"cutoff_hz": args.cutoff, "leo_hip_m": args.leo_hip,
                                         "citation": CITATION, "takes": takes}, indent=1))


if __name__ == "__main__":
    main()
