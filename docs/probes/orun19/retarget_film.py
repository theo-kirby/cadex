"""A film of M1's and M2's clips on leo v06: the capture against leo, side on, on the dark floor (orun19 F1).

usage: pixi run python -I docs/probes/orun19/retarget_film.py MODEL_XML OUT_WEBM SAMPLES LOOPS SLOW \
           CAPTURE:FIRST:END:LABEL:CLIP_JSON[:carpus] [...]

orun18's ``retarget_film.py`` drawing, unchanged, for the clips this run trains on.
Each stride is solved again exactly as ``acino_retarget.py`` (an AcinoSet
``fte.pickle``) or ``dog_retarget.py`` (an AI4Animation dog BVH; ``:carpus`` for
M2's fore target) solved it, tail mapped, and the solved clip's sha256 must equal
``CLIP_JSON``'s, the clip the M1 or M2 bundle carries: the film draws the clip that
is trained, or it stops. A film takes one kind of capture.

Each stride plays LOOPS times at real time and once more at 1/SLOW speed, then the
next follows. The capture's skeleton (grey, scaled by the trunk's ``s``, slid so its
girdles' midpoint sits on leo's) is behind leo's leg chains and trunk; left legs
solid, right dashed; a dot on a ball that is down. The floor's ticks stay put. The
film is a drawing of AcinoSet's (D5a) or CC BY-NC material (D5) and is written
outside the repository; it prints one JSON line per clip and the decode check.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import mujoco  # noqa: E402
import numpy as np  # noqa: E402

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE.parent / "orun18"))
sys.path.insert(0, str(ROOT / "src" / "Mod" / "cadex"))
sys.path.insert(0, str(ROOT / "cli"))

import CadexGait as G  # noqa: E402
import acino_retarget as AR  # noqa: E402  (orun18's: cheetah_stride)
import retarget as R  # noqa: E402
from retarget_film import FPS, HALF_WIDTH, TICK_M, frames_for  # noqa: E402
from retarget_sheet import BG, DOG, LEG_COLOUR, LINE, TEXT, TRUNK  # noqa: E402
from cadex_cli.video import ffmpeg  # noqa: E402

_spec = importlib.util.spec_from_file_location("acino_retarget_v06", HERE / "acino_retarget.py")
V06 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(V06)  # orun19's: map_tail, the v06 tail and head

DOG_TAIL = ("Tail", "Tail1_end")  # dog_retarget.TAIL


def solve(model_path: Path, capture: Path, first: int, end: int, label: str, samples: int,
          fore: str) -> tuple[dict, dict, dict]:
    """The clip as acino_retarget.py / dog_retarget.py wrote it, with the stride it came from."""

    cheetah = capture.suffix == ".pickle"
    if cheetah:
        stride = AR.cheetah_stride(capture, first, end, samples)
    else:
        stride = R.dog_stride(capture, first, end, samples)
        if fore == "carpus":
            names = stride["skeleton"]["names"]
            for f, joint in (("LF", "LeftHand"), ("RF", "RightHand")):
                stride["paw"][f] = stride["skeleton"]["points"][:, names.index(joint)].copy()
    clip, measure, dog = R.retarget(model_path, capture, first, end, label, samples, stride=stride)
    clip["label"] = clip["label"].replace("retargeted to leo v05", "retargeted to leo v06")
    if cheetah:
        V06.map_tail(model_path, stride, clip)
    else:
        V06.map_tail(model_path, stride, clip, points=DOG_TAIL)
    return clip, measure, dog


def main(argv: list[str]) -> None:
    model_path, out = Path(argv[0]).expanduser(), Path(argv[1]).expanduser()
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
            parts = spec.split(":")
            capture, first, end, label, stored = Path(parts[0]).expanduser(), *parts[1:5]
            fore = parts[5] if len(parts) > 5 else "paw"
            cheetah = capture.suffix == ".pickle"
            clip, measure, dog = solve(model_path, capture, int(first), int(end), label, samples, fore)
            got = hashlib.sha256(json.dumps(clip).encode()).hexdigest()
            want = hashlib.sha256(Path(stored).expanduser().read_bytes()).hexdigest()
            if got != want:
                raise SystemExit(f"{label}: solved clip {got[:8]} is not the bundle's {want[:8]}")
            credit = ("AcinoSet cheetah (grey, scaled; Joska et al. 2021; paw = wrist/hock)"
                      if cheetah else f"AI4Animation dog (grey, scaled, CC BY-NC 4.0; fore = {fore})")
            skip = ("l_eye", "r_eye", "nose", "tail_mid", "tail_tip") if cheetah else ("Head", "Neck", "Tail")
            s = 0.5 * sum(measure["length_scale"].values())
            names, parents = dog["skeleton"]["names"], dog["skeleton"]["parents"]
            mid_dog = np.mean([dog["pivot"][f][:, 0] for f in R.LEGS], axis=0)
            qpos = np.asarray(clip["qpos"])
            leo = measure["leo"]
            start = count
            for loop, k, rate in frames_for(clip, loops, slow):
                ax.clear()
                ax.set_facecolor(BG)
                data.qpos[:] = qpos[k]
                data.qpos[0] += loop * leo["stride_m"]
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
                ax.text(0.015, 0.03, f"{credit} retargeted to leo v06: fore amber, hind blue; "
                        "left solid, right dashed; dot = ball down",
                        transform=ax.transAxes, color=DOG, fontsize=8.5, va="bottom")
                ax.text(0.985, 0.97, f"sample {k:02d}/{clip['samples']}", transform=ax.transAxes,
                        color=DOG, fontsize=9, va="top", ha="right")
                fig.savefig(Path(work) / f"{count:05d}.png", facecolor=BG)
                count += 1
            print(json.dumps({"clip": label, "clip_sha256": got, "fore_target": None if cheetah else fore,
                              "speed_m_s": leo["speed_m_s"], "froude": leo["froude"],
                              "frames": count - start}))
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
    print(out, out.stat().st_size, "bytes,", count, "frames decoded,", f"{count / FPS:.1f} s")


if __name__ == "__main__":
    main(sys.argv[1:])
