# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""Did it walk with real steps? Did it reach? Did it balance in place? One
trace, read against the frozen ot11 contract.

The ot11 contract (``docs/probes/ot11/README.md``, ``contract.json``) states a
success spec for each behaviour as predicates on a rollout trace, none of
which reads the reward. **The reading is the product's** (ADR-455):
``CadexEvaluation`` turns a trace into behaviour metrics and holds predicates
against them, and ``CadexDynamics.evaluation_rig`` reads the model. What is
left here is the contract itself -- which metric each frozen predicate
bounds, and the numbers its definitions fix -- so there is one reader, and
the contract cannot drift from what the product measures. It changes
nothing: no rebuild, no rollout, no training.

    pixi run python docs/probes/ot11/runner/measure.py walk \\
        --model model-model.xml --foot c_foot_fl --foot c_foot_fr ... \\
        --command-mm-s 80 [--off-contract] TRACE.json [TRACE.json ...]
    pixi run python docs/probes/ot11/runner/measure.py balance \\
        --model robin_model-model.xml [--off-contract] TRACE.json [...]
    pixi run python docs/probes/ot11/runner/measure.py reach \\
        --model arm-model.xml --tip c_hand:0,0,40 \\
        --target 0:4:120,0,180 --target 4:8:60,90,140 TRACE.json
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any

SCHEMA = "ot11-measure-v1"
CONTRACT = Path(__file__).resolve().parents[1] / "contract.json"
ENGINE = Path(__file__).resolve().parents[4] / "src/Mod/cadex"


def engine(name: str):
    """One engine module, loaded by path: no built engine is needed to read."""

    spec = importlib.util.spec_from_file_location(f"ot11_{name}", ENGINE / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


evaluation = engine("CadexEvaluation")
load_trace = evaluation.load_trace

# The numbers the contract's definitions fix. They are passed to the product
# reader explicitly, so a product default that moves does not move the
# contract with it.
DEFINITIONS = {"stance_mm": 1.0, "speed_window_s": 0.20, "swing_min_s": 0.10,
               "step_advance_hip_heights": 0.15}
REACH = {"tolerance_arm_lengths": 0.05, "final_window_s": 1.0}

# Which product metric each frozen predicate bounds. Where a predicate states
# two measures its ``min``/``max`` is a pair, in this order. "Every foot",
# "both segments" and "every shove" are the worst one, which the product
# names flat.
BINDING = {
    "walk": {
        "W2": ["max_tilt_deg"], "W3": ["speed_ratio"], "W4": ["lateral_ratio", "max_heading_deg"],
        "W5": ["steps_min", "step_share_min"], "W6": ["step_clearance_hip_heights_min"],
        "W7": ["slip_share_max"], "W8": ["duty_factor_min", "duty_factor_max"],
        "W9": ["step_count_ratio"], "W10": ["foot_lowest_hip_heights_min"],
    },
    "reach": {"Q2": ["final_error_arm_lengths_max"], "Q3": ["time_to_target_s_max"],
              "Q4": ["overshoot_ratio_max"]},
    "balance": {"B2": ["max_tilt_deg"], "B3": ["max_drift_com_heights"], "B4": ["max_heading_deg"],
                "B5": ["recovery_s_max"]},
}


def contract() -> dict[str, Any]:
    return json.loads(CONTRACT.read_text(encoding="utf-8"))


def predicate(behaviour: str, identifier: str) -> dict[str, Any]:
    rows = contract()["behaviours"][behaviour]["predicates"]
    return next(row for row in rows if row["id"] == identifier)


def digest(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def rig(model_path: Path, feet=(), tip=None) -> dict[str, Any]:
    """Everything the predicates need from the model, as plain numbers in mm."""

    dynamics = engine("CadexDynamics")
    try:
        return dynamics.evaluation_rig(dynamics.load_model(Path(model_path).read_bytes()),
                                       feet=list(feet), tip=tip)
    except dynamics.DynamicsError as error:
        raise SystemExit(f"{model_path}: {error}") from error


def spec(behaviour: str, identifier: str) -> list[dict[str, Any]]:
    """One frozen predicate, as the product predicates that state it."""

    frozen = predicate(behaviour, identifier)
    names = BINDING[behaviour][identifier]

    def bound(key: str, index: int):
        value = frozen.get(key, frozen.get(f"{key}_s"))
        return value[index] if isinstance(value, list) else value

    return [{"id": identifier, "metric": name, "min": bound("min", i), "max": bound("max", i)}
            for i, name in enumerate(names)]


def _row(behaviour: str, identifier: str, passed: bool | None, value: Any, why: str = "") -> dict[str, Any]:
    frozen = predicate(behaviour, identifier)
    limit = {k: frozen[k] for k in ("min", "max", "max_s", "rest") if k in frozen}
    return {"id": identifier, "name": frozen["name"], "pass": passed, "value": value, "limit": limit, "why": why}


def _held(behaviour: str, identifier: str, metrics, value: Any, why: str = "") -> dict[str, Any]:
    """One frozen predicate held against the product's metrics."""

    rows = evaluation.check(spec(behaviour, identifier), metrics)
    passed = all(row["pass"] for row in rows)
    return _row(behaviour, identifier, passed, value,
                why or "; ".join(row["why"] for row in rows if row["why"]))


def _completes(behaviour: str, identifier: str, episode, off_contract: bool) -> dict[str, Any]:
    wanted = contract()["behaviours"][behaviour]["episode_seconds"]
    ended = evaluation.episode_metrics(episode)["completed"] == 1.0
    value = {"duration_s": episode["duration_s"], "termination": episode["termination"],
             "truncated": episode["truncated"]}
    if not ended:
        return _row(behaviour, identifier, False, value, f"ended by {episode['termination'] or 'no truncation'}")
    if episode["duration_s"] != wanted:
        if off_contract:
            return _row(behaviour, identifier, None, value,
                        f"ran its own task's {episode['duration_s']} s horizon, not the contract's {wanted} s")
        return _row(behaviour, identifier, False, value, f"ran {episode['duration_s']} s, contract {wanted} s")
    return _row(behaviour, identifier, True, value)


def walk(samples, the_rig, command_mm_s: float, episode, *, off_contract: bool = False) -> dict[str, Any]:
    settle = float(contract()["behaviours"]["walk"]["settle_s"])
    metrics = evaluation.gait_metrics(samples, the_rig, command_mm_s, settle_s=settle, **DEFINITIONS)
    feet, hip = metrics["feet"], metrics["hip_height_mm"]
    # An episode that ends inside the settle has no speed to read; that is a
    # failed predicate with nothing measured, never a number.
    early = "" if metrics["speed_ratio"] is not None else f"the episode ended inside the {settle:g} s settle"

    def per_foot(key):
        return {name: foot[key] for name, foot in feet.items()}

    def held(identifier, value, why=""):
        return _held("walk", identifier, metrics, value, why)

    clear = per_foot("median_step_clearance_hip_heights")
    rows = [
        _completes("walk", "W1", episode, off_contract),
        held("W2", metrics["max_tilt_deg"]),
        held("W3", metrics["speed_ratio"], early),
        held("W4", {"lateral_ratio": metrics["lateral_ratio"], "max_heading_deg": metrics["max_heading_deg"]}, early),
        held("W5", {"steps": per_foot("steps"), "step_share": per_foot("step_share")}),
        held("W6", clear, "" if all(v is not None for v in clear.values())
             else "a foot took no step, so it has no step clearance"),
        held("W7", per_foot("slip_share")),
        held("W8", per_foot("duty_factor"), early),
        held("W9", metrics["step_count_ratio"], "" if metrics["steps_min"] else "a foot took no step"),
        held("W10", per_foot("settled_lowest_height_hip_heights")),
    ]
    return {
        "predicates": rows,
        "metrics": {
            **metrics,
            "step_min_advance_mm": DEFINITIONS["step_advance_hip_heights"] * hip,
            "clearance_min_mm": predicate("walk", "W6")["min"] * hip,
            "sink_limit_mm": predicate("walk", "W10")["min"] * hip,
        },
    }


def balance(samples, the_rig, shoves, episode, *, off_contract: bool = False) -> dict[str, Any]:
    """``shoves`` is ``[(onset_s, duration_s)]``: what the episode applied."""

    rest = predicate("balance", "B5")["rest"]
    metrics = evaluation.balance_metrics(
        samples, the_rig, shoves, speed_window_s=DEFINITIONS["speed_window_s"],
        rest_tilt_deg=rest["tilt_deg_max"], rest_speed_com_heights_per_s=rest["speed_com_heights_per_s_max"],
        rest_hold_s=rest["hold_s"])

    def held(identifier, value, why=""):
        return _held("balance", identifier, metrics, value, why)

    if shoves:
        recovered = held("B5", metrics["recovery_s"], "" if metrics["recovery_s_max"] is not None
                         else "it did not come to rest after a shove")
    else:
        recovered = _row("balance", "B5", None, [], "the episode applied no shove")
    rows = [
        _completes("balance", "B1", episode, off_contract),
        held("B2", metrics["max_tilt_deg"]),
        held("B3", metrics["max_drift_com_heights"]),
        held("B4", metrics["max_heading_deg"]),
        recovered,
    ]
    return {
        "predicates": rows,
        "metrics": {**metrics, "drift_limit_mm": predicate("balance", "B3")["max"] * metrics["com_height_mm"]},
    }


def reach(samples, the_rig, segments, episode, *, off_contract: bool = False) -> dict[str, Any]:
    """``segments`` is ``[{"start_s", "end_s", "target_mm"}]``: the targets the episode held."""

    metrics = evaluation.reach_metrics(samples, the_rig, segments, **REACH)

    def held(identifier, key):
        return _held("reach", identifier, metrics, [segment[key] for segment in metrics["segments"]])

    rows = [
        _completes("reach", "Q1", episode, off_contract),
        held("Q2", "final_error_arm_lengths"),
        held("Q3", "time_to_target_s"),
        held("Q4", "overshoot_ratio"),
    ]
    return {"predicates": rows, "metrics": metrics}


def report(behaviour: str, trace_path: Path, model_path: Path, the_rig, *, off_contract: bool,
           command_mm_s: float | None = None, shoves=(), segments=()) -> dict[str, Any]:
    """One trace's verdict: every predicate, the numbers behind it, and why."""

    trace = load_trace(trace_path)
    episode, digests = trace["episode"], trace["digests"]
    the_contract = contract()
    void: list[str] = []
    model_sha = digest(model_path)
    if digests["mjcf_sha256"] != model_sha:
        void.append(f"the trace ran model {digests['mjcf_sha256']}, not the model read ({model_sha})")
    if not digests["policy_sha256"]:
        void.append("no policy: only a policy rollout is evaluated")
    if episode["steps_per_frame"] != 1 or (episode["control_hz"] or 0) < the_contract["trace"]["min_frame_rate_hz"]:
        void.append("frames are not one per control step at 50 Hz or more")
    if not off_contract and episode["seed"] not in the_contract["evaluation_seeds"]:
        void.append(f"seed {episode['seed']} is not a contract seed")
    if behaviour == "walk":
        measured = walk(trace["samples"], the_rig, float(command_mm_s), episode, off_contract=off_contract)
    elif behaviour == "reach":
        measured = reach(trace["samples"], the_rig, list(segments), episode, off_contract=off_contract)
    else:
        measured = balance(trace["samples"], the_rig, list(shoves), episode, off_contract=off_contract)
    rows = measured["predicates"]
    return {
        "schema": SCHEMA, "behaviour": behaviour, "trace": str(trace_path),
        "conditions": "off-contract: a trace that predates the contract, run under its own task's conditions"
                      if off_contract else "contract",
        "seed": episode["seed"], **digests, "void": void,
        **measured,
        "failing": [row["id"] for row in rows if row["pass"] is False],
        "not_measured": [row["id"] for row in rows if row["pass"] is None],
        "pass": not void and not off_contract and all(row["pass"] is True for row in rows),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("behaviour", choices=("walk", "reach", "balance"))
    parser.add_argument("traces", nargs="+", type=Path)
    parser.add_argument("--model", type=Path, required=True, help="the MJCF the traces ran")
    parser.add_argument("--foot", action="append", default=[], help="a foot body (walk); repeat per foot")
    parser.add_argument("--command-mm-s", type=float, help="the commanded forward speed (walk)")
    parser.add_argument("--shove", action="append", default=[], metavar="ONSET:DURATION",
                        help="a shove the episode applied, in seconds (balance); repeat per shove")
    parser.add_argument("--tip", metavar="BODY[:X,Y,Z]", help="the tip: a body and a point on it, in mm (reach)")
    parser.add_argument("--target", action="append", default=[], metavar="START:END:X,Y,Z",
                        help="a target the episode held, in seconds and world mm (reach); repeat per target")
    parser.add_argument("--off-contract", action="store_true",
                        help="the trace predates the contract; report the predicates, never a pass")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)
    if args.behaviour == "walk" and (not args.foot or args.command_mm_s is None):
        parser.error("walk needs --foot for every foot and --command-mm-s")
    if args.behaviour == "reach" and (not args.tip or not args.target):
        parser.error("reach needs --tip and a --target for every target")
    tip = None
    if args.tip:
        body, _, point = args.tip.partition(":")
        tip = {"body": body, "local_mm": [float(v) for v in point.split(",")] if point else [0.0, 0.0, 0.0]}
    the_rig = rig(args.model, args.foot, tip)
    if args.behaviour != "reach" and the_rig["base"] is None:
        raise SystemExit(f"{args.model} has no floating base; the {args.behaviour} spec reads exactly one")
    shoves = [tuple(float(v) for v in text.split(":")) for text in args.shove]
    segments = []
    for text in args.target:
        start, end, point = text.split(":")
        segments.append({"start_s": float(start), "end_s": float(end),
                         "target_mm": [float(v) for v in point.split(",")]})
    reports = [report(args.behaviour, t, args.model, the_rig, off_contract=args.off_contract,
                      command_mm_s=args.command_mm_s, shoves=shoves, segments=segments) for t in args.traces]
    facts = {k: v for k, v in the_rig.items() if k != "feet"}
    result = {"schema": SCHEMA, "behaviour": args.behaviour, "rig": facts, "traces": reports,
              "pass": bool(reports) and all(r["pass"] for r in reports)}
    text = json.dumps(result, indent=2, sort_keys=True)
    if args.out:
        args.out.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":  # pragma: no cover - exercised through main()
    raise SystemExit(main())
