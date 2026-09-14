# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""``cadex smoke``: the bounded stock-MuJoCo rollout as one command (ADR-352).

Every check has a fixture whose answer is known before it runs: a block
resting on the floor passes; the same block two millimetres into the floor
fails penetration by 2.000 mm at t = 0; a block with no floor never rests;
a hinge with an absurd spring blows up and MuJoCo says so; a task whose own
termination rule fires under zero action fails termination, and holds under
``hold``. The runner tests need ``mujoco`` in this interpreter and no
engine; the command tests need a built engine and skip without one.
"""

from __future__ import annotations

import ast
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import textwrap

import pytest

from cadex_cli import smoke as smoke_module
from cadex_cli.__main__ import main
from cadex_cli.engine import Engine
from cadex_cli.export import ExportedOutput
from cadex_cli.report import EXIT_FAILURE, EXIT_OK, EXIT_REJECTED, EXIT_USAGE
from cadex_cli.smoke import (
    MAXIMUM_TIMEOUT_S,
    SMOKE_SCRIPT,
    SmokeError,
    find_model,
    find_optional_task,
    run_smoke,
    smoke_cell,
    smoke_command,
    smoke_interpreter,
)

HAS_MUJOCO = importlib.util.find_spec("mujoco") is not None
needs_mujoco = pytest.mark.skipif(not HAS_MUJOCO, reason="mujoco is not importable here")

# -- the runner's fixtures ---------------------------------------------------

#: A 50 g block, 20 mm tall, whose keyframe puts its underside exactly on
#: the environment floor. Passes: it settles about 0.1 mm into the soft
#: contact and stays.
RESTING_BLOCK = """<mujoco><option timestep="0.002"/><worldbody>
<geom name="environment/floor" type="plane" size="0 0 0.1" pos="0 0 0"/>
<body name="comp_block" pos="0 0 0.01"><freejoint name="base"/>
<geom name="comp_block/collision0" type="box" size="0.02 0.02 0.01" mass="0.05"/></body>
</worldbody><keyframe><key name="solved" qpos="0 0 0.0100 1 0 0 0"/></keyframe></mujoco>"""

#: The same block, keyframed 2 mm into the floor.
BURIED_BLOCK = RESTING_BLOCK.replace('qpos="0 0 0.0100', 'qpos="0 0 0.0080')

#: The same block with nothing under it: a free base and no floor.
NO_FLOOR = RESTING_BLOCK.replace(
    '<geom name="environment/floor" type="plane" size="0 0 0.1" pos="0 0 0"/>', "")

#: A hinge with a 1e9 N·m/rad spring under explicit Euler at 50 ms: the
#: first step produces a bad acceleration, which MuJoCo reports as a
#: warning and answers by zeroing the state -- so the counter, not the
#: numbers, is what a finite check has to read.
BLOW_UP = """<mujoco><option timestep="0.05" integrator="Euler"/><worldbody>
<body name="comp_base" pos="0 0 0"><geom type="box" size="0.05 0.05 0.01" mass="1"/>
<body name="comp_arm" pos="0 0 0.02"><joint name="j" type="hinge" axis="0 1 0" stiffness="1e9" damping="0"/>
<geom type="capsule" fromto="0 0 0 0.1 0 0" size="0.005" mass="0.01"/></body></body>
</worldbody><keyframe><key name="solved" qpos="0.5"/></keyframe></mujoco>"""

#: A grounded base with a position-servoed arm at 0.5 rad and one joint
#: position sensor, the shape the engine exports (affine bias, gain equal
#: to minus the position bias). Under ``hold`` the servo keeps 0.5 rad;
#: under ``zero`` it drives the arm to 0 rad, which the task below calls a
#: fall.
SERVO_ARM = """<mujoco><option timestep="0.002" integrator="implicitfast"/><worldbody>
<body name="comp_base" pos="0 0 0"><geom name="comp_base/collision0" type="box" size="0.05 0.05 0.01" mass="1"/>
<body name="comp_arm" pos="0 0 0.1"><joint name="j" type="hinge" axis="0 1 0" range="-90 90" damping="0.01"/>
<geom name="comp_arm/collision0" type="capsule" fromto="0 0 0 0.1 0 0" size="0.005" mass="0.01"/></body></body>
</worldbody>
<actuator><general name="j/position" joint="j" biastype="affine" gainprm="5" biasprm="0 -5 -0.2"/></actuator>
<sensor><jointpos joint="j" name="obs/0"/></sensor>
<keyframe><key name="solved" qpos="0.5"/></keyframe></mujoco>"""

SERVO_TASK = {
    "label": "hold",
    "episode": {"reset_keyframe": "solved"},
    "observations": [{"adr": 0, "dim": 1, "scale": 57.29577951308232, "channels": ["q"]}],
    "termination": [{"label": "arm_dropped", "expression": "q", "below": 20.0, "above": None}],
}


def _runner(tmp_path: Path, xml: str, *, task: dict | None = None, **flags) -> dict:
    model = tmp_path / "model-model.xml"
    model.write_text(xml, encoding="utf-8")
    task_path = None
    if task is not None:
        task_path = tmp_path / "job-task.json"
        task_path.write_text(json.dumps(task), encoding="utf-8")
    receipt = tmp_path / "smoke.json"
    options = dict(seconds=2.0, mode="hold", penetration_mm=0.5, rest_speed_mm_s=10.0, fps=50)
    options.update(flags)
    command = smoke_command(sys.executable, model=model, task=task_path, out=receipt, **options)
    return run_smoke(command, receipt=receipt, timeout=60.0)


@needs_mujoco
def test_a_block_resting_on_the_floor_passes_every_check(tmp_path) -> None:
    receipt = _runner(tmp_path, RESTING_BLOCK)
    assert receipt["verdict"] == "pass" and receipt["failing"] == [], receipt
    checks = receipt["checks"]
    assert all(check["pass"] for check in checks.values()), checks
    support = checks["support"]
    assert support["kind"] == "free" and support["base"] == "comp_block"
    assert support["touching_floor_at_end"] is True
    assert support["speed_mm_s"] < 1e-3 and abs(support["drop_mm"]) < 0.2
    # The resting contact is the soft-contact sink, well under tolerance.
    (worst,) = checks["penetration"]["worst"]
    assert {worst["first"], worst["second"]} == {"comp_block", "environment/floor"}
    assert 0.05 < worst["depth_mm"] < 0.3, worst
    assert checks["termination"]["rules"] == 0 and checks["termination"]["note"]
    assert receipt["samples"] == 101 and receipt["steps_per_sample"] == 10
    assert (tmp_path / "smoke.json").is_file()


@needs_mujoco
def test_a_block_two_millimetres_into_the_floor_fails_penetration_at_zero(tmp_path) -> None:
    receipt = _runner(tmp_path, BURIED_BLOCK)
    assert receipt["verdict"] == "fail"
    assert receipt["checks"]["penetration"]["pass"] is False
    assert receipt["checks"]["finite"]["pass"] and receipt["checks"]["support"]["pass"]
    (worst,) = receipt["checks"]["penetration"]["worst"]
    assert worst["depth_mm"] == pytest.approx(2.0, abs=1e-6) and worst["time_s"] == 0.0
    (line,) = receipt["failing"]
    assert line.startswith("penetration: comp_block ∩ environment/floor 2.000 mm at 0.000 s")
    # The tolerance is a declared threshold, not a reinterpretation: at
    # 3 mm the same trace passes.
    assert _runner(tmp_path, BURIED_BLOCK, penetration_mm=3.0)["verdict"] == "pass"


@needs_mujoco
def test_a_free_base_with_no_floor_never_rests(tmp_path) -> None:
    receipt = _runner(tmp_path, NO_FLOOR)
    assert receipt["verdict"] == "fail"
    support = receipt["checks"]["support"]
    assert support["pass"] is False and support["floor"] is None
    assert support["touching_floor_at_end"] is False
    assert support["speed_mm_s"] > 1000.0  # two seconds of free fall
    assert receipt["checks"]["finite"]["pass"] is True
    assert any("no environment floor" in line for line in receipt["failing"])
    assert any("still moving" in line for line in receipt["failing"])


@needs_mujoco
def test_a_blow_up_fails_the_finite_check_through_the_warning_counter(tmp_path) -> None:
    receipt = _runner(tmp_path, BLOW_UP)
    assert receipt["verdict"] == "fail"
    finite = receipt["checks"]["finite"]
    assert finite["pass"] is False
    assert any(item["warning"] == "mjWARN_BADQACC" for item in finite["warnings"]), finite
    assert any(line.startswith("finite: MuJoCo warned mjWARN_BADQACC") for line in receipt["failing"])
    assert receipt["checks"]["support"]["kind"] == "grounded"


@needs_mujoco
def test_hold_keeps_the_servo_pose_and_zero_action_fires_the_declared_termination(tmp_path) -> None:
    held = _runner(tmp_path, SERVO_ARM, task=SERVO_TASK, mode="hold")
    assert held["verdict"] == "pass", held["failing"]
    (actuator,) = held["actuators"]
    assert actuator["kind"] == "position" and actuator["ctrl"] == pytest.approx(0.5)
    assert held["checks"]["termination"] == {
        "pass": True, "rules": 1, "fired": [], "errors": [], "note": None}
    assert held["checks"]["support"] == {
        "kind": "grounded", "pass": True, "grounded": ["comp_base"],
        "note": "grounded bodies are static in the model; they hold by construction"}
    assert held["task"]["label"] == "hold" and held["keyframe"] == "solved"

    dropped = _runner(tmp_path, SERVO_ARM, task=SERVO_TASK, mode="zero")
    assert dropped["verdict"] == "fail"
    (actuator,) = dropped["actuators"]
    assert actuator["ctrl"] == 0.0
    (fired,) = dropped["checks"]["termination"]["fired"]
    assert fired["label"] == "arm_dropped" and fired["value"] < 20.0
    assert 0.0 < fired["at_s"] < 2.0, fired
    (line,) = dropped["failing"]
    assert line.startswith("termination: arm_dropped fired at")


@needs_mujoco
def test_a_missing_keyframe_is_a_failure_with_the_reason(tmp_path) -> None:
    xml = RESTING_BLOCK.replace('name="solved"', 'name="other"')
    with pytest.raises(SmokeError, match="carries no 'solved' keyframe"):
        _runner(tmp_path, xml)


# -- the bound, the interpreter, the model -----------------------------------


def test_the_bound_is_enforced_and_capped_at_five_minutes(tmp_path) -> None:
    receipt = tmp_path / "smoke.json"
    sleeper = [sys.executable, "-c", "import time; time.sleep(30)"]
    with pytest.raises(SmokeError, match="ran past its bound of 0.5 s"):
        run_smoke(sleeper, receipt=receipt, timeout=0.5)
    assert MAXIMUM_TIMEOUT_S == 300.0
    for bad in (0.0, -1.0, 300.001):
        with pytest.raises(SmokeError, match="within"):
            run_smoke(sleeper, receipt=receipt, timeout=bad)


def test_a_child_that_writes_no_receipt_is_a_failure(tmp_path) -> None:
    receipt = tmp_path / "smoke.json"
    with pytest.raises(SmokeError, match="failed: boom"):
        run_smoke([sys.executable, "-c", "import sys; print('boom', file=sys.stderr); sys.exit(1)"],
                  receipt=receipt, timeout=10.0)
    with pytest.raises(SmokeError, match="no readable receipt"):
        run_smoke([sys.executable, "-c", "pass"], receipt=receipt, timeout=10.0)
    receipt.write_text(json.dumps({"verdict": "maybe"}), encoding="utf-8")
    with pytest.raises(SmokeError, match="not a smoke receipt"):
        run_smoke([sys.executable, "-c", "pass"], receipt=receipt, timeout=10.0)


def test_the_interpreter_is_the_engines_own_python_or_this_one(tmp_path) -> None:
    binary = tmp_path / "bin" / "FreeCADCmd"
    binary.parent.mkdir()
    binary.write_text("")
    engine = Engine(binary, tmp_path, "explicit", root=tmp_path)
    assert smoke_interpreter(engine) == Path(sys.executable)
    (tmp_path / "bin" / "python").write_text("")
    assert smoke_interpreter(engine) == tmp_path / "bin" / "python"


def test_the_runner_imports_only_the_standard_library_and_mujoco() -> None:
    """The child runs under the engine's interpreter by path: it may not
    reach back into ``cadex_cli`` or forward into the engine."""

    tree = ast.parse(SMOKE_SCRIPT.read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.add(str(node.module or "").split(".")[0])
    assert imported <= {
        "__future__", "argparse", "hashlib", "json", "math", "pathlib", "sys",
        "time", "typing", "mujoco", "numpy",
    }, imported


def test_the_model_is_the_one_exported_or_the_one_named() -> None:
    model = ExportedOutput(name="model", kind="assembly_mjcf_xml", files={"xml": "/m.xml"})
    other = ExportedOutput(name="other", kind="assembly_mjcf_xml", files={"xml": "/o.xml"})
    task = ExportedOutput(name="job", kind="assembly_training_task_json", files={"json": "/j.json"})
    part = ExportedOutput(name="plate", kind="brep")
    assert find_model([part, model, task]) is model
    assert find_model([model, other], "other") is other
    with pytest.raises(SmokeError, match="exports no MJCF model"):
        find_model([part, task])
    with pytest.raises(SmokeError, match="more than one MJCF model"):
        find_model([model, other])
    with pytest.raises(SmokeError, match="--model nope"):
        find_model([model], "nope")
    assert find_optional_task([model]) is None
    assert find_optional_task([model, task]) is task
    with pytest.raises(SmokeError, match="--task nope"):
        find_optional_task([model, task], "nope")


def test_the_progress_cell_says_the_verdict_and_what_failed() -> None:
    assert smoke_cell({"verdict": "pass", "seconds": 2.0, "mode": "hold"}) == "smoke pass 2 s hold"
    cell = smoke_cell({"verdict": "fail", "seconds": 2.0, "mode": "zero",
                       "failing": ["a", "b", "c", "d", "e"]})
    assert cell == "smoke fail 2 s zero: a; b; c (+2 more)"


# -- the command, against the real engine ------------------------------------

#: A grounded plate with a motor-driven arm exporting a model and a task
#: (the shape ``cadex train`` needs). No collision shapes: the arm touches
#: nothing, the base is static, the smoke passes as "grounded".
GROUNDED_SCRIPT = """
plate = part.box(60, 60, 6)
arm = part.box(80, 8, 8)
base = assembly.component(plate, grounded=True)
swing = assembly.component(arm, placement=[0, 0, 40])
j = assembly.joint("revolute",
                   assembly.connector(base, "origin",
                                      offset={"position": [12, 0, 6],
                                              "axis": [1, 0, 0],
                                              "angle_degrees": 90}),
                   assembly.connector(swing, "origin",
                                      offset={"position": [0, 0, 0],
                                              "axis": [1, 0, 0],
                                              "angle_degrees": 90}))
asm = assembly.assembly([base, swing], [j])
diag = assembly.solve(asm)
motor = assembly.actuator(j, kind="motor", control_nmm="120*sin(2*pi*time)",
                          torque_limit_nmm=400)
model = assembly.mjcf(asm, [
    assembly.body(base, density_kg_m3=2700),
    assembly.body(swing, density_kg_m3=7850),
], gravity_m_s2=[0, 0, 0], actuators=[motor], observations=[
    assembly.observation(j, "position", name="angle"),
    assembly.observation(swing, "centre_of_mass", name="com"),
    assembly.observation(motor, "actuator_force", name="effort"),
])
job = assembly.task(model, actions=[motor],
                    reward=[assembly.reward("-(com_z - 60)^2", weight=1.0e-4,
                                            label="lift")],
                    termination=[assembly.termination("com_z", below=-1000.0,
                                                      label="never")],
                    episode_seconds=1.0, control_hz=50, label="lift")
result = {"plate": plate, "arm": arm, "base": base, "swing": swing,
          "j": j, "asm": asm, "diag": diag, "model": model, "job": job}
"""

#: Nothing grounded: the plate is a free base on the environment floor
#: (ADR-335), its underside at z = {z}. At 0 it rests; at -2 it starts
#: 2 mm into the floor.
FREE_BASE_SCRIPT = """
plate = part.box(60, 60, 6)
arm = part.box(80, 8, 8)
base = assembly.component(plate, placement=[-30, -30, {z}])
swing = assembly.component(arm, placement=[0, 0, 40])
j = assembly.joint("fixed",
                   assembly.connector(base, "origin",
                                      offset={{"position": [12, 0, 6],
                                              "axis": [1, 0, 0],
                                              "angle_degrees": 90}}),
                   assembly.connector(swing, "origin",
                                      offset={{"position": [0, 0, 0],
                                              "axis": [1, 0, 0],
                                              "angle_degrees": 90}}))
asm = assembly.assembly([base, swing], [j])
diag = assembly.solve(asm)
model = assembly.mjcf(asm, [
    assembly.body(base, density_kg_m3=2700,
                  collision=assembly.collision("box", size_mm=[60, 60, 6],
                                               offset=[30, 30, 3])),
    assembly.body(swing, density_kg_m3=7850),
])
result = {{"plate": plate, "arm": arm, "base": base, "swing": swing,
          "j": j, "asm": asm, "diag": diag, "model": model}}
"""

#: A plain assembly with no MJCF output: nothing to smoke.
NO_MODEL_SCRIPT = GROUNDED_SCRIPT.split("motor = ")[0] + """
result = {"plate": plate, "arm": arm, "base": base, "swing": swing,
          "j": j, "asm": asm, "diag": diag}
"""


def _run(capsys, *argv: str) -> tuple[int, dict]:
    code = main([*argv, "--json"])
    return code, json.loads(capsys.readouterr().out)


def _project(engine, tmp_path, capsys, source: str, name: str) -> Path:
    script = tmp_path / f"{name}.py"
    script.write_text(source, encoding="utf-8")
    root = tmp_path / name
    code, envelope = _run(capsys, "script", "--set", str(script), "--project", str(root))
    assert code == EXIT_OK, envelope
    return root


def test_usage_errors_come_before_any_engine(tmp_path, capsys) -> None:
    project = tmp_path / "never"
    for argv, word in (
        ([], "needs --out"),
        (["--out", str(tmp_path / "o"), "--seconds", "0"], "--seconds"),
        (["--out", str(tmp_path / "o"), "--timeout", "301"], "five minutes"),
        (["--out", str(tmp_path / "o"), "--penetration-mm", "-1"], "nonnegative"),
        (["--out", str(tmp_path / "o"), "--fps", "0"], "--fps"),
    ):
        code, envelope = _run(capsys, "smoke", "--project", str(project), *argv)
        assert code == EXIT_USAGE, (argv, envelope)
        assert word in envelope["error"], envelope
    assert not project.exists()


@needs_mujoco
def test_a_grounded_design_smokes_as_one_command(engine, tmp_path, capsys) -> None:
    project = _project(engine, tmp_path, capsys, GROUNDED_SCRIPT, "grounded")
    out = project / "smoke1"
    code, envelope = _run(capsys, "smoke", "--project", str(project), "--out", str(out))
    assert code == EXIT_OK, envelope
    smoke = envelope["smoke"]
    assert smoke["verdict"] == "pass" and smoke["failing"] == [], smoke
    assert smoke["mode"] == "hold" and smoke["seconds"] == 2.0
    assert smoke["checks"]["support"]["kind"] == "grounded"
    assert smoke["checks"]["termination"]["rules"] == 1
    assert smoke["task"]["label"] == "lift"
    # The receipt sits beside the model and the task it names; no BREP was
    # converted, because a smoke reads the model and not the parts.
    assert Path(smoke["receipt"]) == out / "smoke.json"
    assert (out / "model-model.xml").is_file() and (out / "job-task.json").is_file()
    assert smoke["model"]["path"] == "model-model.xml"
    assert not list(out.glob("*.step")) and not list(out.glob("*.stl"))
    assert {row["name"] for row in envelope["outputs"] if row["files"]} == {"model", "job"}
    written = json.loads((out / "smoke.json").read_text(encoding="utf-8"))
    assert written["verdict"] == "pass" and written["checks"] == smoke["checks"]
    assert envelope["digest"] and envelope["accepted_revision"], envelope
    # The run is a recorded row on the project, verdict included.
    progress = (project / "PROGRESS.md").read_text(encoding="utf-8")
    assert "smoke 2 s hold → pass" in progress and "smoke pass 2 s hold" in progress
    assert any(note.startswith("smoke pass: model with task job") for note in envelope["notes"])


@needs_mujoco
def test_a_free_base_rests_on_the_floor_and_a_buried_one_fails(engine, tmp_path, capsys) -> None:
    resting = _project(engine, tmp_path, capsys, FREE_BASE_SCRIPT.format(z=0), "resting")
    code, envelope = _run(capsys, "smoke", "--project", str(resting),
                          "--out", str(resting / "smoke1"), "--mode", "zero")
    assert code == EXIT_OK, envelope
    smoke = envelope["smoke"]
    assert smoke["verdict"] == "pass", smoke["failing"]
    support = smoke["checks"]["support"]
    assert support["kind"] == "free" and support["floor"] == "environment/floor"
    assert support["touching_floor_at_end"] is True and support["speed_mm_s"] < 10.0
    assert abs(support["drop_mm"]) < 0.5, support
    assert smoke["checks"]["termination"]["note"] == "no task exported; nothing declared"
    assert smoke["task"] is None
    assert any(note.startswith("smoke pass: model (no task exported)") for note in envelope["notes"])

    buried = _project(engine, tmp_path, capsys, FREE_BASE_SCRIPT.format(z=-2), "buried")
    code, envelope = _run(capsys, "smoke", "--project", str(buried),
                          "--out", str(buried / "smoke1"), "--mode", "zero")
    # Reported, never refused: the command exits 0 with the verdict, and the
    # row on the project says what failed.
    assert code == EXIT_OK, envelope
    smoke = envelope["smoke"]
    assert smoke["verdict"] == "fail"
    assert smoke["checks"]["penetration"]["pass"] is False
    worst = smoke["checks"]["penetration"]["worst"][0]
    assert "environment/floor" in (worst["first"], worst["second"])
    assert worst["depth_mm"] == pytest.approx(2.0, abs=0.05) and worst["time_s"] == 0.0
    assert smoke["failing"][0].startswith("penetration:")
    progress = (buried / "PROGRESS.md").read_text(encoding="utf-8")
    assert "smoke 2 s zero → fail" in progress and "smoke fail 2 s zero: penetration:" in progress


def test_a_design_without_a_model_is_a_refusal_not_a_rollout(engine, tmp_path, capsys, monkeypatch) -> None:
    project = _project(engine, tmp_path, capsys, NO_MODEL_SCRIPT, "plain")
    calls: list[list[str]] = []

    def never(*args, **kwargs):
        calls.append(list(args[0]))
        raise AssertionError("no rollout may run without a model")

    monkeypatch.setattr(smoke_module.subprocess, "run", never)
    code, envelope = _run(capsys, "smoke", "--project", str(project), "--out", str(project / "s"))
    assert code == EXIT_REJECTED, envelope
    assert "exports no MJCF model" in envelope["error"]
    assert calls == []
    assert not (project / "s" / "smoke.json").exists()


def test_a_rollout_past_the_bound_is_a_failure_with_the_reason(engine, tmp_path, capsys, monkeypatch) -> None:
    project = _project(engine, tmp_path, capsys, GROUNDED_SCRIPT, "slow")
    sleeper = tmp_path / "sleep_runner.py"
    sleeper.write_text("import time; time.sleep(30)\n", encoding="utf-8")
    monkeypatch.setattr(smoke_module, "SMOKE_SCRIPT", sleeper)
    code, envelope = _run(capsys, "smoke", "--project", str(project),
                          "--out", str(project / "s"), "--timeout", "1")
    assert code == EXIT_FAILURE, envelope
    assert "ran past its bound" in envelope["error"]
    assert "smoke" not in envelope
    assert "smoke" not in (project / "PROGRESS.md").read_text(encoding="utf-8")


@needs_mujoco
def test_exact_components_catch_collision_absent_from_the_mjcf(engine, tmp_path, capsys):
    # No collision geoms at all: contact queries cannot see this falling arm.
    source = GROUNDED_SCRIPT.replace('gravity_m_s2=[0, 0, 0], ', '')
    project = _project(engine, tmp_path, capsys, source, "falling")
    code, envelope = _run(capsys, "smoke", "--project", str(project),
                          "--out", str(project / "smoke1"))
    assert code == EXIT_OK, envelope
    smoke = envelope["smoke"]
    assert smoke["verdict"] == "fail"
    assert smoke["checks"]["penetration"]["pass"]  # Floor proxies see nothing.
    geometry = smoke["checks"]["components"]
    assert geometry["initial_pose_agrees"] and geometry["pairs_checked"] == 1
    pair, = geometry["failing"]
    assert {pair["first"], pair["second"]} == {"base", "swing"}
    assert pair["common_volume_mm3"] > 100 and 0 < pair["time_s"] <= 2


@needs_mujoco
def test_smoke_never_restores_or_accepts_an_edited_working_script(engine, tmp_path, capsys):
    project = _project(engine, tmp_path, capsys, GROUNDED_SCRIPT, "retained")
    changed = b'raise RuntimeError("the smoke command must not execute me")\n'
    (project / "script.py").write_bytes(changed)
    before = (project / "script.json").read_bytes()
    code, envelope = _run(capsys, "smoke", "--project", str(project),
                          "--out", str(project / "smoke1"))
    assert code == EXIT_OK and envelope["smoke"]["verdict"] == "pass", envelope
    assert (project / "script.py").read_bytes() == changed
    assert (project / "script.json").read_bytes() == before
    assert envelope["smoke"]["accepted_digest"] == json.loads(before)["accepted_digest"]


@needs_mujoco
def test_actual_solver_time_is_recorded_for_indivisible_frame_rate(tmp_path):
    receipt = _runner(tmp_path, RESTING_BLOCK.replace('timestep="0.002"', 'timestep="0.003"'),
                      seconds=0.11, fps=50)
    trace = json.loads((tmp_path / "smoke-trace.json").read_text())
    assert trace[-1]["time_s"] == pytest.approx(0.111)
    assert receipt["simulated_seconds"] == pytest.approx(0.111)
    assert trace[1]["time_s"] == pytest.approx(0.021)


def test_nonfinite_tolerances_and_excessive_trace_are_usage_errors(tmp_path, capsys):
    for flags in (("--penetration-mm", "nan"), ("--rest-speed-mm-s", "inf"),
                  ("--max-common-volume-mm3", "nan"), ("--seconds", "300", "--fps", "100")):
        code, _ = _run(capsys, "smoke", "--project", str(tmp_path / "never"),
                       "--out", str(tmp_path / "out"), *flags)
        assert code == EXIT_USAGE
    assert not (tmp_path / "never").exists()


def test_retained_model_tampering_is_reported(engine, tmp_path, capsys):
    project = _project(engine, tmp_path, capsys, GROUNDED_SCRIPT, "tampered")
    state = json.loads((project / "script.json").read_text())
    stage = project / state["accepted_attempt"]["staging"]
    (stage / "outputs/model-model.xml").write_text("<mujoco/>")
    code, envelope = _run(capsys, "smoke", "--project", str(project),
                          "--out", str(project / "smoke1"))
    assert code == EXIT_FAILURE and "digest mismatch" in envelope["error"]
    assert not (project / "smoke1/smoke.json").exists()


@needs_mujoco
def test_known_exact_overlap_is_400_cubic_mm_even_without_collision_geoms(engine, tmp_path, capsys):
    source = '''
a = part.box(10, 10, 10)
b = part.box(10, 10, 8)
base = assembly.component(a, grounded=True)
block = assembly.component(b)
j = assembly.joint("fixed", assembly.connector(base, "origin", offset={"position": [5,0,0]}),
                   assembly.connector(block, "origin"))
asm = assembly.assembly([base, block], [j])
solved = assembly.solve(asm)
model = assembly.mjcf(asm, [assembly.body(base, density_kg_m3=1000),
                          assembly.body(block, density_kg_m3=1000)])
result = {"a": a, "b": b, "base": base, "block": block, "j": j,
          "asm": asm, "solved": solved, "model": model}
'''
    project = _project(engine, tmp_path, capsys, source, "overlap")
    code, envelope = _run(capsys, "smoke", "--project", str(project),
                          "--out", str(project / "s"), "--seconds", "0.02")
    assert code == EXIT_OK and envelope["smoke"]["verdict"] == "fail", envelope
    pair, = envelope["smoke"]["checks"]["components"]["failing"]
    assert pair["common_volume_mm3"] == pytest.approx(400, abs=1e-6)
    assert pair["time_s"] == 0
    code, envelope = _run(capsys, "smoke", "--project", str(project),
                          "--out", str(project / "s"), "--seconds", "0.02",
                          "--max-common-volume-mm3", "401")
    assert code == EXIT_OK and envelope["smoke"]["verdict"] == "pass", envelope


def test_no_accepted_attempt_is_a_clean_command_error(engine, tmp_path, capsys):
    code, envelope = _run(capsys, "smoke", "--project", str(tmp_path / "empty"),
                          "--out", str(tmp_path / "out"))
    assert code == EXIT_FAILURE and not envelope["ok"]
    assert "retained" in envelope["error"]


@needs_mujoco
def test_geometry_error_cannot_leave_a_complete_passing_receipt(engine, tmp_path, capsys, monkeypatch):
    from cadex_cli import __main__ as commands
    project = _project(engine, tmp_path, capsys, GROUNDED_SCRIPT, "unmeasured")
    out = project / "smoke1"
    out.mkdir()
    (out / "smoke.json").write_text('{"verdict": "pass"}')

    def interrupted(*args, **kwargs):
        raise SmokeError("exact smoke geometry exceeded the shared wall-time bound")

    monkeypatch.setattr(commands, "check_geometry", interrupted)
    code, envelope = _run(capsys, "smoke", "--project", str(project), "--out", str(out))
    assert code == EXIT_FAILURE and "shared wall-time bound" in envelope["error"]
    assert "smoke" not in envelope
    assert not (out / "smoke.json").exists()
    assert json.loads((out / "smoke-dynamics.json").read_text())["schema"] == "cadex-smoke-dynamics-v1"
