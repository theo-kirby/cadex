"""Judge one checkpoint of leo's speed-only task (B1) on its own speed_spec at held commands.

usage: CUDA_VISIBLE_DEVICES= PYTHONPATH=cli pixi run python docs/probes/orun18/speed_judge.py \
           PROJECT RUN_TRAIN_DIR POLICY OUT_NAME [--cmd 700 1500 2400 5000] [--seeds 1001 ...] \
           [--task speed]

``orun16/sg_judge.py`` for D4's task: the bundle is ``speed-task.json`` and
its spec ``speed_spec`` (``completes``, ``no_fall``, ``upright``,
``straight``, ``top_speed`` 5000, ``hock_down`` reported, ``within_rated``;
C2_SEEDS 1001-1010). Everything else is sg_judge's: for each ``--cmd`` the
``cmd`` goal's held sequence is swapped for ``[cmd]`` in the judged copy of
the bundle only (the spec is outside the task's semantic digest), the policy's
header is checked against the trained bundle and model, and the evaluation
goes to ``PROJECT/evaluations/OUT_NAME-<cmd>/`` with orun11 judge.py's
``closure`` block and ``judged_command_mm_s``. Every command must lie in the
goal's trained range (700-5000 mm/s).

**Footfall without a reference.** The engine reads footfall (touchdown
rates, hind overreach, each pair's lag) only against a task's reference,
for its leg labels, and this task has none (D4). So each seed's
``detail.footfall`` is filled after the evaluation by the engine's own
``CadexEvaluation.footfall_metrics``, over the engine's per-foot detail,
with leo's labels (``LEGS``) and the start heading the engine would use
(``base_series``' first ``forward``); the seed records
``footfall_source``. Nothing is rewarded or judged on it; it lets
``orun17/sg_tables.py`` read B1's evaluations as any SG evaluation
(footfall order, pair lags in ms, flight, heel, U, drives, O9).

**C3 and C4.** ``--task mocap_gallop`` judges a reference bundle built by
``c3_bundle.py`` (the same ``speed_spec``, its ``cmd`` narrowed to the
strides' span). That bundle carries a reference whose legs are ``LEGS``, so
the engine reads its footfall itself and ``add_footfall`` is not applied.
"""

from __future__ import annotations

import importlib.util
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src" / "Mod" / "cadex"))

import CadexDynamics as D  # noqa: E402
import CadexEvaluation as EV  # noqa: E402
from cadex_cli.engine import resolve_engine  # noqa: E402
from cadex_cli.evaluate import check_out, run_evaluation  # noqa: E402
from cadex_cli.smoke import retained_attempt  # noqa: E402

_spec = importlib.util.spec_from_file_location(
    "orun11_judge", Path(__file__).resolve().parents[1] / "orun11" / "judge.py")
J = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(J)

SPEC = "speed_spec"
LEGS = {"LF": "c_paw_fl", "RF": "c_paw_fr", "LH": "c_paw_hl", "RH": "c_paw_hr"}


def add_footfall(report: dict, out: Path) -> None:
    """Each seed's footfall detail and readings, by the engine's function, with LEGS as its labels."""

    labels = {"legs": {label: {"foot_body": body} for label, body in LEGS.items()}}
    for seed in report["seeds"]:
        samples = EV.read_trace(json.loads((out / seed["trace"]["file"]).read_text()))["samples"]
        ahead = EV.base_series(samples, report["rig"])["forward"][0]
        read = EV.footfall_metrics(seed["detail"]["feet"], labels, ahead)
        seed["detail"]["footfall"] = read.pop("footfall")
        seed["metrics"].update(read)
        seed["footfall_source"] = "orun18 speed_judge: CadexEvaluation.footfall_metrics with LEGS, no reference"


def option(argv: list[str], flag: str, default: str) -> str:
    return argv[argv.index(flag) + 1] if flag in argv else default


def options(argv: list[str], flag: str) -> list[int] | None:
    if flag not in argv:
        return None
    values = []
    for token in argv[argv.index(flag) + 1:]:
        if token.startswith("--"):
            break
        values.append(int(token))
    return values


def main() -> None:
    root, train, policy, name = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]), sys.argv[4]
    commands = options(sys.argv, "--cmd") or [700, 1500, 2400, 5000]
    task = option(sys.argv, "--task", "speed")
    trained_path = train / f"{task}-task.json"
    trained = json.loads(trained_path.read_text())
    model = train / Path(trained["model"]["path"]).name
    header = D.decode_policy(policy.read_bytes(), context="judge")["header"]
    assert header["task"]["sha256"] == J.sha(trained_path), "policy was not trained on this bundle"
    assert header["model"]["sha256"] == J.sha(model) == trained["model"]["sha256"], "model mismatch"
    success = trained["success"]
    assert success["label"] == SPEC, f"not {SPEC}"
    goals = [g for g in success["goal"] if g["name"] == "cmd" and g["kind"] == "speed"]
    assert len(goals) == 1 and goals[0]["segments"] == 1, "the spec's command is not one held segment"
    low, high = float(goals[0]["low"]), float(goals[0]["high"])
    seeds = options(sys.argv, "--seeds") or [int(s) for s in success["seeds"]]
    assert set(seeds) <= {int(s) for s in success["seeds"]}, "not the spec's frozen seeds"
    state, _staging, _result = retained_attempt(root)
    run_json = train.parent / "run.json"
    trained_on = json.loads(run_json.read_text()).get("model", {}) if run_json.is_file() else {}
    if trained_on.get("accepted_revision"):
        state = {"accepted_revision": trained_on["accepted_revision"],
                 "accepted_digest": trained_on.get("digest") or state.get("accepted_digest")}
    components = re.findall(r'<body[^>]*name="([^"]+)"', model.read_text())
    for cmd in commands:
        assert low <= cmd <= high, f"command {cmd} outside the goal's {low:g}-{high:g} mm/s"
        judged_task = json.loads(json.dumps(trained))
        for goal in judged_task["success"]["goal"]:
            if goal["name"] == "cmd":
                goal["sequence"] = [float(cmd)]
        judged_task["success"]["seeds"] = seeds
        out = check_out(root, root / "evaluations" / f"{name}-{cmd}")
        out.mkdir(parents=True, exist_ok=True)
        judged = out / "judged-task.json"
        judged.write_text(json.dumps(judged_task))
        inputs = {"accepted_revision": str(state["accepted_revision"]),
                  "accepted_digest": str(state.get("accepted_digest") or ""),
                  "policy_output": "undeclared", "task_output": task, "model_output": "cat_model",
                  "policy": policy.resolve(), "policy_sha256": J.sha(policy), "weights": policy.name,
                  "trained_task_sha256": J.sha(trained_path), "task": judged, "model": model,
                  "components": components, "seeds": seeds}
        report = run_evaluation(resolve_engine(), inputs, out)
        report["judged_spec_task"] = SPEC
        report["judged_command_mm_s"] = cmd
        report["judged_policy"] = str(policy)
        if not (trained.get("reference") or {}).get("legs"):
            add_footfall(report, out)
        report["closure"] = J.closure(model, out)
        (out / "evaluation.json").write_text(json.dumps(report, indent=2) + "\n")
        print(f"{name}-{cmd}", report["verdict"], len(report["summary"]["passed"]), flush=True)


if __name__ == "__main__":
    main()
