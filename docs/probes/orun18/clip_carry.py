"""Check that retarget.py's clips are references leo's task can carry (orun18 C2).

usage: pixi run python docs/probes/orun18/clip_carry.py BUNDLE CLIP [CLIP ...]

``BUNDLE`` is leo's speed-only task bundle (``speed-task.json``, B1); each
``CLIP`` a ``cadex-gait-clip-v1`` from ``retarget.py``, slowest first. Each clip
goes through the engine's own builder of a reference's tracking channels,
``CadexDynamics._tracking_records``, over the bundle's joint position
observations (the bundle names a row's joint ``target``; the engine's records,
before the bundle is written, ``object_name``), and the clips together through
``_schedule_record`` (ADR-773) against the bundle's speed goal and against one
narrowed to the strides' span. Prints the channels, the table's size, the
schedule's speeds and turns, and the qpos width against the model's ``nq``:
what a C3 task needs from a clip, read by the engine and not by a copy.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src" / "Mod" / "cadex"))

import mujoco  # noqa: E402

import CadexDynamics as D  # noqa: E402


def main(argv: list[str]) -> None:
    bundle_path, clip_paths = Path(argv[0]), [Path(p) for p in argv[1:]]
    bundle = json.loads(bundle_path.read_text())
    model = mujoco.MjModel.from_xml_path(str(bundle_path.parent / Path(bundle["model"]["path"]).name))
    observations = [{**row, "object_name": row["target"]} for row in bundle["observations"]
                    if row["kind"] == "position"]
    schedule = {"control_interval_s": float(bundle["episode"]["control_interval_s"])}
    taken = [c for row in bundle["observations"] for c in row["channels"]] + [
        c for row in bundle["goal"] for c in row["channels"]]
    clips = [json.loads(p.read_text()) for p in clip_paths]
    for path, clip in zip(clip_paths, clips):
        record = D._tracking_records(clip, observations, schedule, taken=taken, context=path.name)
        widths = {len(row) for row in clip["qpos"]}
        print(f"{path.name}: {len(record['channels'])} channels "
              f"({sum(c.endswith('_ref') for c in record['channels'])} joint refs), "
              f"table {len(record['table'])}x{len(record['table'][0])}, "
              f"period {record['period_s']:.3f} s, turn/step {record['turn_per_step']:.4f}, "
              f"qpos width {widths} vs nq {model.nq}")
    print("joint refs:", [c for c in record["channels"] if c.endswith("_ref")])
    goal = bundle["goal"]
    try:
        D._schedule_record(clips, observations, schedule, goal, taken=taken, context="as trained")
        print("schedule over the bundle's goal: accepted")
    except D.DynamicsError as error:
        print(f"schedule over the bundle's goal ({goal[0]['low']:g}-{goal[0]['high']:g} mm/s): "
              f"refused, {error.reason}")
    speeds = [1000.0 * float(c["parameters"]["speed_m_s"]) for c in clips]
    narrowed = [{**goal[0], "low": speeds[0], "high": speeds[-1],
                 "nominal": [min(max(v, speeds[0]), speeds[-1]) for v in goal[0]["nominal"]]}]
    record = D._schedule_record(clips, observations, schedule, narrowed, taken=taken, context="narrowed")
    print(f"schedule over {speeds[0]:.0f}-{speeds[-1]:.0f} mm/s: accepted; speeds "
          f"{[round(v) for v in record['speeds_mm_s']]}, periods {[round(v, 3) for v in record['periods_s']]}, "
          f"turns/step {[round(v, 4) for v in record['turns_per_step']]}")


if __name__ == "__main__":
    main(sys.argv[1:])
