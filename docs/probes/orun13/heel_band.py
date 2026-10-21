"""orun13 (O2, O7): where a judged policy's rigid hind feet sit in heel_pitch's band.

usage: pixi run python docs/probes/orun13/heel_band.py EVALUATION_DIR [EVALUATION_DIR ...]

``heel_pitch`` (leo's gallop task) pays the metatarsus's world pitch ``m``
in the clip's hind stance: full at ``m <= 10`` deg, nothing at 45. leo's
sole is flat at ``m = +4.5`` (``hind_flat_target.py``); a lower ``m`` is
the foot rotated toes-up about the heel. So the band pays a toes-up foot in
full. This reads, from a judged evaluation's traces (``judge.py``), where
each hind foot actually sits while it is on the ground, and what the
current band and a flat-only band would pay there.

``m`` per frame is the paw's world pitch (the rigid foot's; from
``component_placements``) offset so that its median over the trace's flat
frames (heel and toes both within the engine's ``STANCE_MM``) reads +4.5.
The sign is set so that a toes-up foot (toes above the heel) reads lower;
the script checks it against the sole tilt (toes minus heel, mm) and
prints the correlation.

A frame is **on the ground** when the heel or the toes are within
``STANCE_MM``; it is then **flat** (both), **toes-up** (heel only) or
**toe** (toes only, the heel up). Per leg it prints the share of on-ground
frames in each, the median ``m`` in each, and the mean pay per on-ground
frame of:

- ``now``: the task's band, ``sat01((45 - m) / 35)``;
- ``flat``: the same with the toes-up side closed, ``min(now,
  sat01((m + 15) / 14))``: full from -1 to +10, nothing at -15 or below;
- ``peak``: ``0.3 exp(-((m - 4.5) / 20)^2) + 0.7 exp(-((m - 4.5) / 3)^2)``:
  full only at the flat sole; 0.93 at 1 deg off (the heel about 1.3 mm
  up), 0.41 at +8.5, 0.30 at +10 (about 7 mm up), with a broad tail so a
  toe stance far off still has a slope towards flat.

The engine's heel is down within ``STANCE_MM`` (1 mm), and on leo's foot
1 deg of pitch about the toes lifts the heel about 1.3 mm, so only
``m`` within about 0.8 deg of +4.5 counts as a heel down with the toes.

Writes nothing. Left and right are given apart (O5).
"""

from __future__ import annotations

import json
import math
import statistics
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src" / "Mod" / "cadex"))
import CadexEvaluation as E  # noqa: E402
from spine_foot import paw_capsules, rot  # noqa: E402

import mujoco  # noqa: E402

FLAT_M = 4.5
LEGS = (("LH", "c_paw_hl"), ("RH", "c_paw_hr"))


def sat01(x):
    return min(max(x, 0.0), 1.0)


def now_band(m):
    return sat01((45.0 - m) / 35.0)


def flat_band(m):
    return min(now_band(m), sat01((m + 15.0) / 14.0))


def peak_band(m):
    d = m - FLAT_M
    return 0.3 * math.exp(-(d / 20.0) ** 2) + 0.7 * math.exp(-(d / 3.0) ** 2)


def pitch(xyzw):
    """The world pitch (deg) of a body's x axis: positive is nose-down about +y."""
    x_axis = rot(xyzw)[:, 0]
    return math.degrees(math.atan2(-x_axis[2], x_axis[0]))


def legs(out: Path, model):
    evaluation = json.loads((out / "evaluation.json").read_text())
    rig = evaluation["rig"]
    floor = rig["floor_mm"]
    paw_geoms = paw_capsules(model)
    acc = {leg: {"m": [], "tilt": [], "kind": []} for leg, _ in LEGS}
    for path in sorted(out.glob("seed-*-trace.json")):
        trace = json.loads(path.read_text())
        frames = [f for f in trace["frames"] if f.get("joint_positions")]
        samples = [(f.get("nominal_time_s") or 0.0, f["component_placements"]) for f in frames]
        late = [i for i, (t, _) in enumerate(samples) if t >= E.SETTLE_S - 1e-9]
        for leg, paw in LEGS:
            toes = E.foot_series(samples, paw, paw_geoms[paw], floor)["height"]
            hb = rig["heels"][paw]
            heel = E.foot_series(samples, hb["body"], hb["geoms"], floor)["height"]
            for i in late:
                t_down, h_down = toes[i] <= E.STANCE_MM, heel[i] <= E.STANCE_MM
                if not (t_down or h_down):
                    continue
                acc[leg]["m"].append(pitch(samples[i][1][paw]["rotation_xyzw"]))
                acc[leg]["tilt"].append(toes[i] - heel[i])
                acc[leg]["kind"].append("flat" if t_down and h_down else "toes_up" if h_down else "toe")
    return acc


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    for arg in argv[1:]:
        out = Path(arg)
        model_xml = sorted(out.parent.parent.glob("runs/*/train/cat_model-model.xml"))
        judged = json.loads((out / "judged-task.json").read_text()) if (out / "judged-task.json").exists() else {}
        xml = judged.get("model", {}).get("path")
        path = Path(xml) if xml and Path(xml).exists() else model_xml[-1]
        model = mujoco.MjModel.from_xml_path(str(path))
        acc = legs(out, model)
        print(f"\n### {out.name}\n")
        print("| leg | on-ground frames | flat / toes-up / toe share | median m flat / toes-up / toe (deg) "
              "| tilt~m corr | pay now | pay flat-only | pay peak | toes-up share of `now` pay |")
        print("|---|---|---|---|---|---|---|---|---|")
        for leg, _ in LEGS:
            a = acc[leg]
            raw = np.asarray(a["m"])
            tilt = np.asarray(a["tilt"])
            flat_idx = [k for k, kind in enumerate(a["kind"]) if kind == "flat"]
            ref = statistics.median(raw[flat_idx]) if flat_idx else statistics.median(raw)
            # toes-up must read lower: pick the sign that makes m fall as the tilt rises
            sign = 1.0 if np.corrcoef(raw, tilt)[0, 1] < 0 else -1.0
            m = FLAT_M + sign * (raw - ref)
            corr = float(np.corrcoef(m, tilt)[0, 1])
            n = len(m)
            share = {k: sum(1 for x in a["kind"] if x == k) / max(n, 1) for k in ("flat", "toes_up", "toe")}
            medk = {k: (statistics.median([m[j] for j, x in enumerate(a["kind"]) if x == k])
                        if any(x == k for x in a["kind"]) else None) for k in ("flat", "toes_up", "toe")}
            pay_now = [now_band(x) for x in m]
            pay_flat = [flat_band(x) for x in m]
            pay_peak = [peak_band(x) for x in m]
            toes_pay = sum(p for p, k in zip(pay_now, a["kind"]) if k == "toes_up")
            f = lambda v: "–" if v is None else "%.1f" % v  # noqa: E731
            print(f"| {leg} | {n} | {share['flat']:.2f} / {share['toes_up']:.2f} / {share['toe']:.2f} "
                  f"| {f(medk['flat'])} / {f(medk['toes_up'])} / {f(medk['toe'])} | {corr:.2f} "
                  f"| {statistics.mean(pay_now):.2f} | {statistics.mean(pay_flat):.2f} | {statistics.mean(pay_peak):.2f} "
                  f"| {toes_pay / max(sum(pay_now), 1e-9):.2f} |")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
