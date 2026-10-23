"""orun16 Q2: re-judge one policy on its own spec with the model's solver settings patched, on the CPU.

usage: CUDA_VISIBLE_DEVICES= pixi run python docs/probes/orun16/rod_solver.py \
           MODEL_XML JUDGED_TASK_JSON POLICY OUT_DIR VARIANT [VARIANT ...]

The front push-rod loops (``j_frodbot_*``) open 3-4 mm against O9's 2 mm.
``orun14/wrist-peak.md`` found every frame over 2 mm is a fore-stance frame
with the wrist drive at peak and the carpus driven past its soft stop
(MuJoCo's default ``solreflimit`` 0.02 s on ``j_carpus_*`` and
``j_wrist_*``). This asks which solver setting closes the loop, without a
build: it patches the model XML's text in memory, plays
``CadexDynamics.evaluate_success`` (the engine's own judge, the call
``cli/cadex_cli/evaluate_runner.py`` makes, minus the runner's digest check
that the patch would fail) on the judged task's seeds, and writes
``OUT_DIR/<variant>/`` with each seed's trace and ``measured.json``. Read
the traces with ``orun14/rod_gap.py`` and ``orun14/wrist_peak.py``.

The policy is the one trained on the unpatched model, so a variant's gait is
that policy's reply to a slightly different plant; a variant that moves
speed or form a lot is a variant the policy would need retraining on.

Variants:
- ``base``: unpatched (must reproduce the engine's evaluation);
- ``carpus4``: ``solreflimit="0.004"`` on ``j_carpus_*`` (two solver steps,
  the hind pins' ``limit_time_constant_s``);
- ``stop4``: the same on ``j_carpus_*`` and ``j_wrist_*``;
- ``iter``: ``iterations="400" tolerance="1e-12"`` on ``<option>`` (does
  the solver converge?);
- ``eq2``: ``refsafe`` off and the four rod loops' ``solref`` at one
  solver step (0.002 s), past the stiffest the engine allows;
- ``dt1``: what a build at ``solver_step_s`` 0.001 would give: the step
  halved, every equality's ``solref`` at its two steps (0.002 s; the
  engine's rule), contacts and the paw pins' stops unchanged at 0.004 s,
  and the task's episode at 20 solver steps an action;
- ``dt1keep``: the step halved with every ``solref`` as built (does the
  policy still gallop on a 1 ms step?);
- ``dt1rod``: the step halved and only the four rod loops at 0.002 s.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src" / "Mod" / "cadex"))

import CadexDynamics as D  # noqa: E402


def limit(xml: str, joints: list[str]) -> str:
    for name in joints:
        xml, n = re.subn(rf'(<joint name="{name}" )', rf'\1solreflimit="0.004" ', xml)
        assert n == 1, name
    return xml


def patch(xml: str, variant: str) -> str:
    if variant == "base":
        return xml
    if variant == "carpus4":
        return limit(xml, ["j_carpus_l", "j_carpus_r"])
    if variant == "stop4":
        return limit(xml, ["j_carpus_l", "j_carpus_r", "j_wrist_l", "j_wrist_r"])
    if variant == "iter":
        out = xml.replace('<option integrator="implicitfast">',
                          '<option integrator="implicitfast" iterations="400" tolerance="1e-12">')
        assert out != xml
        return out
    if variant == "eq2":
        out = xml.replace('<flag island="disable"/>', '<flag island="disable" refsafe="disable"/>')
        out, n = re.subn(r'(<connect name="j_(?:f?rodbot)_[lr]"[^>]*?)solref="0.004"', r'\1solref="0.002"', out)
        assert out != xml and n == 4
        return out
    if variant in ("dt1keep", "dt1rod"):
        out = xml.replace('<option integrator="implicitfast">',
                          '<option integrator="implicitfast" timestep="0.001">')
        if variant == "dt1rod":
            out, n = re.subn(r'(<connect name="j_(?:f?rodbot)_[lr]"[^>]*?)solref="0.004"',
                             r'\1solref="0.002"', out)
            assert n == 4
        return out
    if variant == "dt1":
        out = xml.replace('<option integrator="implicitfast">',
                          '<option integrator="implicitfast" timestep="0.001">')
        start = out.index("<equality>")
        out = out[:start] + out[start:].replace('solref="0.004"', 'solref="0.002"')
        assert out != xml
        return out
    raise SystemExit(f"unknown variant {variant}")


def task_for(task: dict, variant: str) -> dict:
    if not variant.startswith("dt1"):
        return task
    episode = {**task["episode"], "solver_step_s": 0.001,
               "solver_steps_per_action": 2 * int(task["episode"]["solver_steps_per_action"])}
    return {**task, "episode": episode}


def main(argv: list[str]) -> int:
    model_path, task_path, policy_path, out_root = map(Path, argv[1:5])
    xml = model_path.read_text()
    task = json.loads(task_path.read_text())
    container = D.decode_policy(policy_path.read_bytes(), context="rod_solver")
    components = re.findall(r'<body[^>]*name="([^"]+)"', xml)
    for variant in argv[5:]:
        out = out_root / variant
        out.mkdir(parents=True, exist_ok=True)

        def keep(seed: int, document: dict) -> None:
            (out / f"seed-{seed}-trace.json").write_text(json.dumps(document))

        measured = D.evaluate_success(patch(xml, variant).encode(), task_for(task, variant), container,
                                      components=components, on_trace=keep,
                                      context=f"rod_solver {variant}")
        (out / "measured.json").write_text(json.dumps(measured, indent=1, default=str))
        preds = {p["id"]: (p["passed"], round(p["value"]["median"], 3) if p.get("value") else None)
                 for p in measured["summary"]["predicates"]}
        void = measured["summary"].get("void")
        print(variant, "void", void, json.dumps(preds), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
