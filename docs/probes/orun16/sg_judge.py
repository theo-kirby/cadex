"""Judge one gallop_sg checkpoint on sg_spec at one or more held speed commands (orun16 SG, RL).

usage: CUDA_VISIBLE_DEVICES= PYTHONPATH=cli pixi run python docs/probes/orun16/sg_judge.py \
           PROJECT RUN_TRAIN_DIR POLICY OUT_NAME [--cmd 1000 1700 2400] [--seeds 1001 ...]

``orun11/judge.py`` for the speed-commanded task. The bundle is
``gallop_sg-task.json``; its success spec is ``sg_spec``, ``gallop_spec``'s
predicates with the ``cmd`` goal scripted at 2,400 mm/s
(``sequence=[2400]``, one segment longer than the episode, so the command
is held). For each ``--cmd`` this swaps that sequence for ``[cmd]`` in the
judged copy of the bundle only, and writes
``PROJECT/evaluations/OUT_NAME-<cmd>/`` (``evaluation.json`` with judge.py's
``closure`` block, the seed traces, ``judged-task.json``). The trained
bundle, its digest and the policy are checked as judge.py checks them; the
spec is outside the task's semantic digest, so the swap does not change
what the policy was trained on. ``--seeds`` judges a subset of the spec's
frozen seeds (a quick check; a judged result uses all ten).

The traces then read with the orun12-16 probes as any gallop evaluation
(``legs.py``, ``paw_floor.py``, ``p2_lag.py``, ``pin_rate.py``). Each
evaluation also records ``judged_command_mm_s``.
"""

from __future__ import annotations

import importlib.util
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src" / "Mod" / "cadex"))

import CadexDynamics as D  # noqa: E402
from cadex_cli.engine import resolve_engine  # noqa: E402
from cadex_cli.evaluate import check_out, run_evaluation  # noqa: E402
from cadex_cli.smoke import retained_attempt  # noqa: E402

_spec = importlib.util.spec_from_file_location(
    "orun11_judge", Path(__file__).resolve().parents[1] / "orun11" / "judge.py")
J = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(J)


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
    commands = options(sys.argv, "--cmd") or [1000, 1700, 2400]
    trained_path = train / "gallop_sg-task.json"
    trained = json.loads(trained_path.read_text())
    model = train / Path(trained["model"]["path"]).name
    header = D.decode_policy(policy.read_bytes(), context="judge")["header"]
    assert header["task"]["sha256"] == J.sha(trained_path), "policy was not trained on this bundle"
    assert header["model"]["sha256"] == J.sha(model) == trained["model"]["sha256"], "model mismatch"
    success = trained["success"]
    assert success["label"] == "sg_spec" and success.get("heels"), "not the SG spec"
    goals = [g for g in success["goal"] if g["name"] == "cmd" and g["kind"] == "speed"]
    assert len(goals) == 1 and goals[0]["segments"] == 1, "sg_spec's command is not one held segment"
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
        # The evaluation plays the judged spec's seeds, not the inputs' list.
        judged_task["success"]["seeds"] = seeds
        out = check_out(root, root / "evaluations" / f"{name}-{cmd}")
        out.mkdir(parents=True, exist_ok=True)
        judged = out / "judged-task.json"
        judged.write_text(json.dumps(judged_task))
        inputs = {"accepted_revision": str(state["accepted_revision"]),
                  "accepted_digest": str(state.get("accepted_digest") or ""),
                  "policy_output": "undeclared", "task_output": "gallop_sg", "model_output": "cat_model",
                  "policy": policy.resolve(), "policy_sha256": J.sha(policy), "weights": policy.name,
                  "trained_task_sha256": J.sha(trained_path), "task": judged, "model": model,
                  "components": components, "seeds": seeds}
        report = run_evaluation(resolve_engine(), inputs, out)
        report["judged_spec_task"] = "sg_spec"
        report["judged_command_mm_s"] = cmd
        report["judged_policy"] = str(policy)
        report["closure"] = J.closure(model, out)
        (out / "evaluation.json").write_text(json.dumps(report, indent=2) + "\n")
        print(f"{name}-{cmd}", report["verdict"], len(report["summary"]["passed"]), flush=True)


if __name__ == "__main__":
    main()
