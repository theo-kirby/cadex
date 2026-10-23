"""Stills of retarget.py's strides: the capture against leo, side on, on the dark floor (orun18 C2).

usage: pixi run python docs/probes/orun18/retarget_sheet.py MODEL_XML OUT_PNG SAMPLES \
           BVH:FIRST:END:LABEL [BVH:FIRST:END:LABEL ...]

One row per stride, six evenly spaced phases each. The dog's skeleton (grey,
scaled by the trunk's ``s`` and slid along the line so its girdles' midpoint
sits on leo's) is drawn behind leo's (its leg chains joint to joint, the paw's
contact point, and the trunk chest to pelvis): left legs solid, right dashed,
a paw that is down marked with a dot. The floor is the dashboard's ``#141414``
mat with its ``#3a3a3a`` line.
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import mujoco  # noqa: E402
import numpy as np  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src" / "Mod" / "cadex"))

import CadexGait as G  # noqa: E402
import retarget as R  # noqa: E402

BG, LINE, DOG, TEXT = "#141414", "#3a3a3a", "#6b6b6b", "#d8d8d8"
LEG_COLOUR = {"LF": "#e8a33c", "RF": "#e8a33c", "LH": "#4fb3d9", "RH": "#4fb3d9"}
TRUNK = ["j_fhaa_l", "j_spine", "j_spine2", "j_spine_yaw", "j_hhaa_l"]


def main(argv: list[str]) -> None:
    model_path, out_png, samples = Path(argv[0]), Path(argv[1]), int(argv[2])
    strides = [spec.split(":") for spec in argv[3:]]
    model = mujoco.MjModel.from_xml_path(str(model_path))
    data = mujoco.MjData(model)
    structure = G.leg_chains(model, R.LEGS, mujoco=mujoco)
    chains = structure["chains"]
    fig, axes = plt.subplots(len(strides), 6, figsize=(12, 1.9 * len(strides)), facecolor=BG)
    axes = np.atleast_2d(axes)
    for row, (bvh, first, end, label) in enumerate(strides):
        clip, measure, dog = R.retarget(model_path, Path(bvh), int(first), int(end), label, samples)
        n = clip["samples"]
        s = 0.5 * sum(measure["length_scale"].values())
        names = dog["skeleton"]["names"]
        parents = dog["skeleton"]["parents"]
        mid_dog = np.mean([dog["pivot"][f][:, 0] for f in R.LEGS], axis=0)
        data.qpos[:] = model.key_qpos[0]
        mujoco.mj_kinematics(model, data)
        point_local = {f: G._foot_point(model, data, mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, b))
                       for f, b in R.LEGS.items()}
        for col in range(6):
            k = int(round(col * n / 6)) % n
            ax = axes[row, col]
            ax.set_facecolor(BG)
            data.qpos[:] = clip["qpos"][k]
            mujoco.mj_kinematics(model, data)
            pivots = [data.xanchor[mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, R.LEO_PIVOT[f])] for f in R.LEGS]
            centre = float(np.mean([p[0] for p in pivots]))
            pts = dog["skeleton"]["points"][k] * s
            shift = centre - s * mid_dog[k]
            for j, parent in enumerate(parents):
                if parent < 0 or names[j].startswith(("Head", "Neck", "Tail")):
                    continue
                ax.plot([pts[parent, 0] + shift, pts[j, 0] + shift], [pts[parent, 2], pts[j, 2]],
                        color=DOG, lw=1.6, solid_capstyle="round", zorder=1)
            trunk = [data.xanchor[mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, name)] for name in TRUNK]
            ax.plot([p[0] for p in trunk], [p[2] for p in trunk], color=TEXT, lw=2.2, zorder=2)
            for f in ("RF", "RH", "LF", "LH"):
                body = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, R.LEGS[f])
                foot = data.xpos[body] + data.xmat[body].reshape(3, 3) @ point_local[f]
                line = [data.xanchor[j] for j in chains[f]] + [foot]
                ax.plot([p[0] for p in line], [p[2] for p in line], color=LEG_COLOUR[f], lw=2.0,
                        ls="-" if f[0] == "L" else (0, (3, 2)), zorder=3 if f[0] == "L" else 2)
                if clip["contact"][f][k]:
                    ax.plot([foot[0]], [foot[2]], "o", color=LEG_COLOUR[f], ms=4, zorder=4)
            ax.axhline(0.0, color=LINE, lw=1.0, zorder=0)
            ax.set_xlim(centre - 0.62, centre + 0.62)
            ax.set_ylim(-0.03, 0.62)
            ax.set_aspect("equal")
            ax.axis("off")
            ax.set_title(f"{k / n:.2f}", color=TEXT, fontsize=8, pad=1)
        leo = measure["leo"]
        axes[row, 0].text(-0.02, 0.5, f"{label}\n{leo['speed_m_s']:.2f} m/s\nFr {leo['froude']:.2f}",
                          transform=axes[row, 0].transAxes, ha="right", va="center", color=TEXT, fontsize=8)
    fig.suptitle("orun18 C2: AI4Animation dog capture (grey, scaled) retargeted to leo v05 "
                 "(fore amber, hind blue; left solid, right dashed; dot = paw down)",
                 color=TEXT, fontsize=9, y=0.995)
    fig.subplots_adjust(left=0.08, right=0.995, top=0.95, bottom=0.01, wspace=0.02, hspace=0.12)
    fig.savefig(out_png, dpi=110, facecolor=BG)
    print(out_png, out_png.stat().st_size, "bytes")


if __name__ == "__main__":
    main(sys.argv[1:])
