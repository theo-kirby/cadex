"""Write leo's C3 task bundle: B1's speed-only task carrying retargeted strides (orun18 C3).

usage: pixi run python docs/probes/orun18/c3_bundle.py SPEED_BUNDLE OUT_DIR LABEL CLIP [CLIP ...]

``SPEED_BUNDLE`` is B1's ``speed-task.json``; each ``CLIP`` a
``cadex-gait-clip-v1`` from ``retarget.py``, slowest first. The probe route
(no engine change): a copy of the speed bundle gains what the engine writes
for a speed-scheduled reference (ADR-703, ADR-706, ADR-709, ADR-773), each
part built by the engine's own function over these clips rather than by a
copy of it:

* ``tracking`` from ``CadexDynamics._tracking_records`` over the slowest
  stride, with ``schedule`` from ``_schedule_record`` and ``reset_qpos`` /
  ``reset_qvel`` from ``_reference_start_records`` per stride, in stride
  order;
* ``reference`` (the slowest stride) and ``reference_schedule`` (every
  stride, without poses);
* the speed goal, in the task and in its success spec, narrowed to the
  strides' span, because a command is never extrapolated past them.

The family must keep one footfall order, the check
``_reference_schedule_records`` makes on generated strides (a blend of two
strides at one phase is only a gait when the same foot lands in both); a
family that crosses is refused here as the engine would refuse it.

The reward is D4's (the speed bundle's rows unchanged) plus the clip's three
tracking terms, written as sgt-4's were (``track_pose``, ``track_lift``,
``track_contact``) and no style term (D6). Every expression is compiled
against the bundle's channels and the tracking channels by the engine's
``compile_reward``. The model XML is copied beside the bundle.
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src" / "Mod" / "cadex"))

import mujoco  # noqa: E402

import CadexDynamics as D  # noqa: E402

JOINTS = [("fhaa", "fhaa"), ("scap", "scap"), ("shoulder", "shoulder"), ("elbow", "elbow"),
          ("wrist", "carpus"), ("hhaa", "hhaa"), ("hip", "hip"), ("knee", "knee"),
          ("hock", "ankle")]

# sgt-4's tracking terms, as written (leo 3b0942b, gallop_sg-task.json), weights kept.
TRACK_POSE = "exp(-(" + " + ".join(
    [f"(q_{own}_{side} - q_{ref}_{side}_ref)**2" for side in "lr" for own, ref in JOINTS]
    + ["(q_spine - q_spine_ref)**2"]) + ") / 17100.0)"
TRACK_LIFT = ("exp(-(((pfl_z - 22.0 - ref_lf_lift) / 30)**2 + ((pfr_z - 22.0 - ref_rf_lift) / 30)**2"
              " + ((phl_z - 16.0 - ref_lh_lift) / 30)**2 + ((phr_z - 16.0 - ref_rh_lift) / 30)**2) / 4)")
TRACK_CONTACT = ("((1 - abs(cfl_down - ref_lf_down)) + (1 - abs(cfr_down - ref_rf_down))"
                 " + (1 - abs(chl_down - ref_lh_down)) + (1 - abs(chr_down - ref_rh_down))) / 4")


def footfall_crossings(clips: list[dict]) -> list[str]:
    """The engine's footfall-order check between neighbouring strides."""

    out = []
    for index in range(1, len(clips)):
        before = clips[index - 1]["parameters"]["phase_offsets"]
        after = clips[index]["parameters"]["phase_offsets"]
        out += [f"{clips[index - 1]['label'].split(':')[0]} -> {clips[index]['label'].split(':')[0]}: "
                f"{a} before {b}, then after"
                for a in before for b in before
                if float(before[a]) < float(before[b]) and float(after[a]) > float(after[b])]
    return out


def narrowed(goal: dict, low: float, high: float) -> dict:
    return {**goal, "low": low, "high": high,
            "nominal": [min(max(float(v), low), high) for v in goal["nominal"]]}


def main(argv: list[str]) -> None:
    bundle_path, out_dir, label = Path(argv[0]), Path(argv[1]), argv[2]
    clips = [json.loads(Path(p).read_text()) for p in argv[3:]]
    bundle = json.loads(bundle_path.read_text())
    xml = bundle_path.parent / Path(bundle["model"]["path"]).name
    model = mujoco.MjModel.from_xml_path(str(xml))

    crossed = footfall_crossings(clips)
    if crossed:
        raise SystemExit("refused (schedule_footfall_order): " + "; ".join(crossed))
    widths = {len(row) for clip in clips for row in clip["qpos"]}
    if widths != {model.nq} or len({int(c["samples"]) for c in clips}) != 1:
        raise SystemExit(f"refused: qpos widths {widths} vs nq {model.nq}, or sample counts differ")

    observations = [{**row, "object_name": row["target"]} for row in bundle["observations"]
                    if row["kind"] == "position"]
    episode = bundle["episode"]
    # Every channel the bundle already names: observations, goal, commands,
    # accelerations and scans, the names the engine checks a reference against.
    taken = [c for key in ("observations", "goal", "commands", "accelerations", "scans")
             for row in bundle.get(key) or [] for c in row["channels"]]
    speeds = [1000.0 * float(c["parameters"]["speed_m_s"]) for c in clips]
    goal = [narrowed(bundle["goal"][0], speeds[0], speeds[-1])]

    tracking = D._tracking_records(clips[0], observations, episode, taken=taken, context=label)
    tracking["schedule"] = D._schedule_record(clips, observations, episode, goal,
                                              taken=taken, context=label)
    starts = [D._reference_start_records(mujoco, model, clip) for clip in clips]
    tracking.update(starts[0])
    tracking["reset_qpos"] = [row for start in starts for row in start["reset_qpos"]]
    tracking["reset_qvel"] = [row for start in starts for row in start["reset_qvel"]]

    reward = list(bundle["reward"]) + [
        {"expression": TRACK_POSE, "label": "track_pose", "weight": 1.5},
        {"expression": TRACK_LIFT, "label": "track_lift", "weight": 1.5},
        {"expression": TRACK_CONTACT, "label": "track_contact", "weight": 10.0},
    ]
    names = taken + list(tracking["channels"])
    for row in reward:
        D.compile_reward(row["expression"], names=names, context=f"reward {row['label']!r}")
    for row in bundle["termination"]:
        D.compile_reward(row["expression"], names=names, context=f"termination {row['label']!r}")

    out = {**bundle, "label": label, "goal": goal, "reward": reward,
           "success": {**bundle["success"],
                       "goal": [narrowed(g, speeds[0], speeds[-1]) for g in bundle["success"]["goal"]]},
           "reference": clips[0], "tracking": tracking,
           "reference_schedule": clips}
    out_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(xml, out_dir / xml.name)
    path = out_dir / f"{label}-task.json"
    path.write_text(json.dumps(out, indent=1, sort_keys=True))
    print(f"wrote {path}: strides {[c['label'].split(':')[0] for c in clips]} at "
          f"{[round(v) for v in speeds]} mm/s, cmd {speeds[0]:.0f}-{speeds[-1]:.0f}, "
          f"{len(tracking['channels'])} tracking channels, table "
          f"{len(tracking['table'])}x{len(tracking['table'][0])}, reset rows "
          f"{len(tracking['reset_qpos'])}, reward {[r['label'] for r in reward]}")


if __name__ == "__main__":
    main(sys.argv[1:])
