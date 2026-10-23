"""A film of retarget.py's strides: the capture against leo, side on, on the dark floor (orun18 F1).

usage: pixi run python docs/probes/orun18/retarget_film.py MODEL_XML OUT_WEBM SAMPLES LOOPS SLOW \
           CAPTURE:FIRST:END:LABEL [CAPTURE:FIRST:END:LABEL ...]

``CAPTURE`` is an AI4Animation dog BVH, or an AcinoSet ``fte.pickle`` (a path
ending ``.pickle``), whose stride is read by ``acino_retarget.cheetah_stride``
exactly as that probe retargets it (C4). A film takes one kind of capture.

Each stride plays LOOPS times at real time and once more at 1/SLOW speed,
then the next stride follows. It is retarget_sheet.py's drawing, moving: the
dog's skeleton (grey, scaled by the trunk's ``s`` and slid along the line so
its girdles' midpoint sits on leo's) behind leo's leg chains and trunk, left
legs solid, right dashed, a dot on a paw that is down. Leo travels by the
clip's own root (one stride length per loop) and the window follows it; the
floor's tick marks stay put, so a paw held still on the ground reads as
still. Frames are 60 a second; each picks the clip sample nearest its time,
so nothing is interpolated. The film is a drawing of CC BY-NC material (D5),
or of AcinoSet's (D5a), and is written outside the repository.

The cheetah has no paw (acino_retarget.py): its legs end at the wrist and hock,
which leo's paws follow, and each girdle's points stand over their own distal
floor, so its skeleton's fore and hind halves sit on the floor separately.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import mujoco  # noqa: E402
import numpy as np  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src" / "Mod" / "cadex"))
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "cli"))

import CadexGait as G  # noqa: E402
import acino_retarget as AR  # noqa: E402
import retarget as R  # noqa: E402
from retarget_sheet import BG, DOG, LEG_COLOUR, LINE, TEXT, TRUNK  # noqa: E402
from cadex_cli.video import ffmpeg  # noqa: E402

FPS = 60
HALF_WIDTH = 0.75
TICK_M = 0.25


def frames_for(clip: dict, loops: int, slow: int) -> list[tuple[int, int, float]]:
    """(loop, sample, time shown) per frame: LOOPS at real time, then one at 1/SLOW."""
    n, dt = clip["samples"], clip["sample_dt_s"]
    period = n * dt
    out = []
    for loop in range(loops + 1):
        rate = 1.0 if loop < loops else 1.0 / slow
        count = int(round(period / rate * FPS))
        for f in range(count):
            t = f / FPS * rate
            out.append((loop, int(round(t / dt)) % n, rate))
    return out


def main(argv: list[str]) -> None:
    model_path, out = Path(argv[0]), Path(argv[1])
    samples, loops, slow = int(argv[2]), int(argv[3]), int(argv[4])
    model = mujoco.MjModel.from_xml_path(str(model_path))
    data = mujoco.MjData(model)
    chains = G.leg_chains(model, R.LEGS, mujoco=mujoco)["chains"]
    data.qpos[:] = model.key_qpos[0]
    mujoco.mj_kinematics(model, data)
    point_local = {f: G._foot_point(model, data, mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, b))
                   for f, b in R.LEGS.items()}
    pivot_ids = [mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, R.LEO_PIVOT[f]) for f in R.LEGS]
    trunk_ids = [mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, name) for name in TRUNK]
    fig, ax = plt.subplots(figsize=(9.6, 4.8), dpi=100, facecolor=BG)
    fig.subplots_adjust(0, 0, 1, 1)
    count = 0
    with tempfile.TemporaryDirectory() as work:
        for spec in argv[5:]:
            capture, first, end, label = spec.split(":")
            cheetah = capture.endswith(".pickle")
            stride = AR.cheetah_stride(Path(capture), int(first), int(end), samples) if cheetah else None
            clip, measure, dog = R.retarget(model_path, Path(capture), int(first), int(end), label, samples,
                                            stride=stride)
            credit = ("AcinoSet cheetah (grey, scaled; Joska et al. 2021; paw = wrist/hock) retargeted"
                      if cheetah else "AI4Animation dog (grey, scaled, CC BY-NC 4.0) retargeted")
            skip = ("l_eye", "r_eye", "nose", "tail_mid", "tail_tip") if cheetah else ("Head", "Neck", "Tail")
            s = 0.5 * sum(measure["length_scale"].values())
            names, parents = dog["skeleton"]["names"], dog["skeleton"]["parents"]
            mid_dog = np.mean([dog["pivot"][f][:, 0] for f in R.LEGS], axis=0)
            qpos = np.asarray(clip["qpos"])
            stride = measure["leo"]["stride_m"]
            leo = measure["leo"]
            for loop, k, rate in frames_for(clip, loops, slow):
                ax.clear()
                ax.set_facecolor(BG)
                data.qpos[:] = qpos[k]
                data.qpos[0] += loop * stride
                mujoco.mj_kinematics(model, data)
                centre = float(np.mean([data.xanchor[j][0] for j in pivot_ids]))
                pts = dog["skeleton"]["points"][k] * s
                shift = centre - s * mid_dog[k]
                for j, parent in enumerate(parents):
                    if parent < 0 or names[j].startswith(skip):
                        continue
                    ax.plot([pts[parent, 0] + shift, pts[j, 0] + shift], [pts[parent, 2], pts[j, 2]],
                            color=DOG, lw=2.4, solid_capstyle="round", zorder=1)
                trunk = [data.xanchor[j] for j in trunk_ids]
                ax.plot([p[0] for p in trunk], [p[2] for p in trunk], color=TEXT, lw=3.2, zorder=2)
                for f in ("RF", "RH", "LF", "LH"):
                    body = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, R.LEGS[f])
                    foot = data.xpos[body] + data.xmat[body].reshape(3, 3) @ point_local[f]
                    line = [data.xanchor[j] for j in chains[f]] + [foot]
                    ax.plot([p[0] for p in line], [p[2] for p in line], color=LEG_COLOUR[f], lw=3.0,
                            ls="-" if f[0] == "L" else (0, (3, 2)), zorder=3 if f[0] == "L" else 2)
                    if clip["contact"][f][k]:
                        ax.plot([foot[0]], [foot[2]], "o", color=LEG_COLOUR[f], ms=6, zorder=4)
                ax.axhline(0.0, color=LINE, lw=1.2, zorder=0)
                lo = centre - HALF_WIDTH
                for x in np.arange(np.floor(lo / TICK_M) * TICK_M, centre + HALF_WIDTH, TICK_M):
                    ax.plot([x, x], [-0.02, 0.0], color=LINE, lw=1.2, zorder=0)
                ax.set_xlim(lo, centre + HALF_WIDTH)
                ax.set_ylim(-0.08, 0.67)
                ax.set_aspect("equal")
                ax.axis("off")
                speed = "real time" if rate == 1.0 else f"1/{slow} speed"
                ax.text(0.015, 0.97, f"{label}  {leo['speed_m_s']:.2f} m/s  Fr {leo['froude']:.2f}  "
                        f"period {leo['period_s']:.3f} s  ({speed})", transform=ax.transAxes,
                        color=TEXT, fontsize=11, va="top")
                ax.text(0.015, 0.03, f"{credit} to leo v05: fore amber, hind blue; "
                        "left solid, right dashed; dot = paw down",
                        transform=ax.transAxes, color=DOG, fontsize=8.5, va="bottom")
                ax.text(0.985, 0.97, f"sample {k:02d}/{clip['samples']}", transform=ax.transAxes,
                        color=DOG, fontsize=9, va="top", ha="right")
                fig.savefig(Path(work) / f"{count:05d}.png", facecolor=BG)
                count += 1
        encoder = ffmpeg()
        result = subprocess.run([encoder, "-v", "error", "-nostdin", "-y", "-framerate", str(FPS),
                                 "-i", str(Path(work) / "%05d.png"), "-an", "-c:v", "libvpx-vp9",
                                 "-b:v", "0", "-crf", "34", "-pix_fmt", "yuv420p", str(out)],
                                capture_output=True, timeout=600)
        if result.returncode != 0:
            raise SystemExit(result.stderr.decode())
    check = subprocess.run([encoder, "-v", "error", "-nostdin", "-i", str(out), "-f", "framemd5", "-"],
                           capture_output=True, timeout=300)
    decoded = sum(1 for line in check.stdout.decode().splitlines() if line and not line.startswith("#"))
    if check.returncode != 0 or decoded != count:
        raise SystemExit(f"decode check failed: {decoded} of {count} frames")
    print(out, out.stat().st_size, "bytes,", count, "frames decoded")


if __name__ == "__main__":
    main(sys.argv[1:])
