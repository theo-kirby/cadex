"""Compare an evaluation's resolved spec with the frozen ot11 contract.

P1 freezes each behaviour's seeds, conditions, predicates and thresholds in
``contract.json``, and changing one is a recorded decision. Until this, the
only check that a stored evaluation was read against that contract, and not
against a reworded predicate, was the actor's eye after each round (REPORT.md,
*Remaining defects*). ``cadex evaluate`` writes the spec it resolved into
``evaluation.json`` as ``spec``; this reads that block and names every way it
differs from the contract. It reports and never refuses: an evaluation that
deviates on purpose (``w2-2`` has no goal to track) keeps its row, and the
deviation is printed beside it.

Which behaviour a spec is for is read from its predicate ids: W walk, Q
reach, B balance.
"""

from __future__ import annotations

import math

PREFIX = {"W": "walk", "Q": "reach", "B": "balance"}

# The product's metric name for each frozen predicate id. The contract states
# a metric in prose; this is the one name the engine computes it under.
METRICS = {
    "W1": "completed", "W2": "max_tilt_deg", "W3": "speed_ratio",
    "W4-lateral": "lateral_ratio", "W4-heading": "max_heading_deg",
    "W5-steps": "steps_min", "W5-share": "step_share_min",
    "W6": "step_clearance_hip_heights_min", "W7": "slip_share_max",
    "W8-low": "duty_factor_min", "W8-high": "duty_factor_max",
    "W9": "step_count_ratio", "W10": "foot_lowest_hip_heights_min",
    "Q1": "completed", "Q2": "final_error_arm_lengths_max",
    "Q3": "time_to_target_s_max", "Q4": "overshoot_ratio_max",
    "B1": "completed", "B2": "max_tilt_deg", "B3": "max_drift_com_heights",
    "B4": "max_heading_deg", "B5": "recovery_s_max",
}

# How a frozen predicate with two metrics splits into the product's ids.
SPLIT = {"W4": ("W4-lateral", "W4-heading"), "W5": ("W5-steps", "W5-share")}


def _single(ids: set[str]) -> str | None:
    """The behaviour every predicate id names, or None if they disagree."""

    return PREFIX.get(next(iter(ids))) if len(ids) == 1 else None


def frozen_predicates(contract_predicates: list[dict]) -> dict[str, tuple]:
    """id -> (metric, min, max) in the product's terms, from the contract."""

    out: dict[str, tuple] = {}
    for predicate in contract_predicates:
        pid = predicate["id"]
        if "rule" in predicate and "metric" not in predicate:
            out[pid] = (METRICS[pid], 1.0, None)  # completes: truncation, no termination
        elif pid in SPLIT:
            for index, sub in enumerate(SPLIT[pid]):
                low = predicate.get("min")
                high = predicate.get("max")
                out[sub] = (METRICS[sub],
                            low[index] if isinstance(low, list) else None,
                            high[index] if isinstance(high, list) else None)
        elif pid == "W8":
            out["W8-low"] = (METRICS["W8-low"], predicate["min"], None)
            out["W8-high"] = (METRICS["W8-high"], None, predicate["max"])
        else:
            high = predicate.get("max", predicate.get("max_s"))
            out[pid] = (METRICS[pid], predicate.get("min"), high)
    return out


def _same(a, b) -> bool:
    if a is None or b is None:
        return a is None and b is None
    return math.isclose(float(a), float(b), rel_tol=1e-9, abs_tol=1e-9)


def _range(label: str, got: tuple, want: list, tol: float, out: list[str]) -> None:
    if not (math.isclose(got[0], want[0], abs_tol=tol) and math.isclose(got[1], want[1], abs_tol=tol)):
        out.append(f"{label} [{got[0]:.6g}, {got[1]:.6g}] != frozen [{want[0]:.6g}, {want[1]:.6g}]")


def deviations(spec: dict, contract: dict) -> list[str]:
    """Every way ``spec`` differs from the frozen contract; empty if it conforms."""

    behaviour = _single({p["id"][:1] for p in spec.get("predicates", [])})
    if behaviour is None:
        return ["behaviour: the predicate ids name no single frozen behaviour"]
    frozen = contract["behaviours"][behaviour]
    out: list[str] = []

    if list(spec.get("seeds", [])) != list(contract["evaluation_seeds"]):
        out.append(f"seeds {spec.get('seeds')} != frozen {contract['evaluation_seeds']}")
    seconds = spec.get("episode", {}).get("episode_seconds")
    if not _same(seconds, frozen["episode_seconds"]):
        out.append(f"episode_seconds {seconds} != frozen {frozen['episode_seconds']}")

    want = frozen_predicates(frozen["predicates"])
    got = {p["id"]: (p["metric"], p.get("min"), p.get("max")) for p in spec["predicates"]}
    for pid in want:
        if pid not in got:
            out.append(f"{pid}: missing")
    for pid, (metric, low, high) in got.items():
        if pid not in want:
            out.append(f"{pid}: not in the contract")
            continue
        w_metric, w_low, w_high = want[pid]
        if metric != w_metric:
            out.append(f"{pid}: metric {metric} != frozen {w_metric}")
        if not _same(low, w_low):
            out.append(f"{pid}: min {low} != frozen {w_low}")
        if not _same(high, w_high):
            out.append(f"{pid}: max {high} != frozen {w_high}")

    conditions = frozen["conditions"]
    resets = spec.get("reset_variation") or []
    if isinstance(conditions["reset_variation"], dict):
        frozen_reset = conditions["reset_variation"]
        if len(resets) != 1:
            out.append(f"reset_variation: {len(resets)} declared, frozen 1")
        else:
            reset = resets[0]
            _range("reset tilt_deg", (math.degrees(reset["tilt_low_rad"]), math.degrees(reset["tilt_high_rad"])),
                   frozen_reset["tilt_deg"], 1e-6, out)
            span = (reset["height_high_m"] - reset["height_low_m"]) * 1000.0
            lift = frozen_reset["lift_above_clearing_mm"]
            if not math.isclose(span, lift[1] - lift[0], abs_tol=1e-6):
                out.append(f"reset lift span {span:.6g} mm != frozen {lift[1] - lift[0]:.6g} mm")
    elif resets:
        out.append(f"reset_variation: {len(resets)} declared, frozen none")

    shoves = spec.get("disturbance") or []
    frozen_shoves = conditions["disturbance"] if isinstance(conditions["disturbance"], list) else []
    weight = (spec.get("scale") or {}).get("weight_n")
    if len(shoves) != len(frozen_shoves):
        out.append(f"disturbance: {len(shoves)} declared, frozen {len(frozen_shoves)}")
    else:
        for index, (shove, want_shove) in enumerate(zip(shoves, frozen_shoves)):
            tag = f"shove {index + 1}"
            if shove.get("direction") != want_shove["direction"]:
                out.append(f"{tag} direction {shove.get('direction')} != frozen {want_shove['direction']}")
            if not _same(shove.get("duration_s"), want_shove["duration_s"]):
                out.append(f"{tag} duration_s {shove.get('duration_s')} != frozen {want_shove['duration_s']}")
            _range(f"{tag} at_s", (shove["at_low_s"], shove["at_high_s"]), want_shove["at_s"], 1e-9, out)
            _range(f"{tag} azimuth_deg", (math.degrees(shove["azimuth_low_rad"]), math.degrees(shove["azimuth_high_rad"])),
                   want_shove["azimuth_deg"], 1e-6, out)
            if not weight:
                out.append(f"{tag}: the spec states no weight to read force_weights against")
            else:
                _range(f"{tag} force_weights", (shove["newtons_low"] / weight, shove["newtons_high"] / weight),
                       want_shove["force_weights"], 1e-9, out)

    goals = spec.get("goal") or []
    if behaviour == "walk":
        scale = (spec.get("scale") or {}).get("hip_height_mm")
        speeds = [g for g in goals if g.get("kind") == "speed"]
        if len(goals) != 1 or len(speeds) != 1:
            out.append(f"goal: {len(goals)} declared, frozen one speed command")
        elif not scale:
            out.append("goal: the spec states no hip height to read the command against")
        else:
            goal = speeds[0]
            _range("goal hip_heights_per_s", (goal["low"] / scale, goal["high"] / scale),
                   conditions["goal"]["forward_hip_heights_per_s"], 1e-9, out)
            if goal.get("resample_steps", 0) != 0 or goal.get("segments", 1) != 1:
                out.append("goal: the frozen command is held for the episode")
    elif behaviour == "reach":
        points = [g for g in goals if g.get("kind") == "point"]
        arm = (spec.get("scale") or {}).get("arm_length_mm")
        if len(goals) != 1 or len(points) != 1:
            out.append(f"goal: {len(goals)} declared, frozen one point target")
        elif not arm:
            out.append("goal: the spec states no arm length to read the target rules against")
        else:
            goal = points[0]
            control_hz = spec.get("episode", {}).get("control_hz")
            switch = conditions["goal"]["switch_at_s"]
            checks = [
                ("segments", goal.get("segments"), 2),
                ("joint_fraction", goal.get("joint_fraction"), 0.8),
                ("attempts", goal.get("attempts"), conditions["goal"]["max_redraws"]),
                ("min_z arm lengths", goal["min_z_m"] * 1000.0 / arm, 0.10),
                ("min_separation arm lengths", goal["min_separation_m"] * 1000.0 / arm, 0.25),
                ("switch_at_s", goal.get("resample_steps", 0) / control_hz if control_hz else None, switch),
            ]
            for name, value, frozen_value in checks:
                if not _same(value, frozen_value):
                    out.append(f"goal {name} {value} != frozen {frozen_value}")
    elif goals:
        out.append(f"goal: {len(goals)} declared, frozen none")
    return out
