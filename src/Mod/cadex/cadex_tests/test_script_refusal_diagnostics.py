# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""What a refused build tells its author, and what the sandbox lets them write.

Six audited design sessions (cbase-*, 2026-10-09) lost their time to the
same handful of things: a kernel refusal that named the operation but not
the call ("api.fuse: declared solid but OpenCascade produced Compound
containing 2 solids", in a script with forty fuses), a fillet that killed
the worker and came back as "exited without a result", a ``solver_error``
whose diagnosis was buried, a sandbox without ``math`` (Taylor series by
hand) or ``getattr``, a library section that never listed what a lib part
can do, and prints that vanished with the refusal. ADR-615 to ADR-620.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import CadexScriptedDomains as domains
import cadex_domain_api
import cadex_domain_worker
import cadex_project_worker
from cadex_domain_api import create_domain_api


def _part_api():
    pack = domains.get_xscript_pack("PartWorkbench")
    assert pack is not None
    return create_domain_api(pack.domain, pack.api_exports, pack.output_types)


def _run(source: str, **globals_by_name):
    return cadex_project_worker._execute_project_source(
        source=source,
        document_name="Fixture",
        document_objects=[],
        inputs={},
        globals_by_name=globals_by_name,
        max_operations=10_000,
        max_seconds=5.0,
    )


# -- ADR-615: math ----------------------------------------------------------


def test_math_is_provided_and_deterministic() -> None:
    result, _stdout, _budget = _run(
        "a = math.sin(math.pi / 6)\n"
        "b = math.atan2(1.0, 1.0)\n"
        "c = math.hypot(3, 4)\n"
        "d = math.degrees(math.radians(30.0))\n"
        "result = {'a': a, 'b': b, 'c': c, 'd': d, 'tau': math.tau}\n"
    )
    import math

    assert result == {
        "a": math.sin(math.pi / 6),
        "b": math.atan2(1.0, 1.0),
        "c": 5.0,
        "d": math.degrees(math.radians(30.0)),
        "tau": math.tau,
    }


def test_math_is_read_only_and_only_the_whitelist() -> None:
    sandbox_math = cadex_domain_worker.SANDBOX_MATH
    assert dir(sandbox_math) == sorted(
        name for name in cadex_domain_worker.SANDBOX_MATH_NAMES
        if hasattr(__import__("math"), name)
    )
    with pytest.raises(TypeError, match="read-only"):
        _run("math.pi = 3\nresult = {}")
    with pytest.raises(AttributeError, match="not available"):
        _run("x = math.factorial(5)\nresult = {}")
    # No route to the module object's machinery: the AST policy refuses
    # math.__spec__, and a computed getattr refuses it too.
    with pytest.raises(ValueError, match="private, dunder"):
        _run("x = getattr(math, '__spec__')\nresult = {}")


def test_import_math_is_refused_with_the_fix() -> None:
    for source in ("import math\nresult = {}", "from math import sin\nresult = {}"):
        with pytest.raises(ValueError, match="`math` is already provided"):
            domains.validate_program_source(source)
    with pytest.raises(ValueError, match="imports are not allowed$"):
        domains.validate_program_source("import os\nresult = {}")


# -- ADR-616: introspection ---------------------------------------------------


def test_safe_introspection_works_on_public_names() -> None:
    part = _part_api()
    result, _stdout, _budget = _run(
        "box = getattr(part, 'box')\n"
        "missing = getattr(part, 'no_such_call', None)\n"
        "names = dir(part)\n"
        "here = dir()\n"
        "result = {\n"
        "  'has_box': hasattr(part, 'box'), 'has_nothing': hasattr(part, 'nothing'),\n"
        "  'callable': callable(box), 'missing': missing,\n"
        "  'int': type(3) is int, 'isinstance': isinstance(2.5, float),\n"
        "  'public': all(not n.startswith('_') for n in names), 'fillet': 'fillet' in names,\n"
        "  'here': 'part' in here and 'names' in here,\n"
        "}\n",
        part=part,
    )
    assert result == {
        "has_box": True, "has_nothing": False, "callable": True, "missing": None,
        "int": True, "isinstance": True, "public": True, "fillet": True, "here": True,
    }


@pytest.mark.parametrize(
    "source",
    [
        "x = getattr(part, '_domain')",
        "x = getattr(part, '__class__')",
        "x = hasattr(part, '__dict__')",
        "g = (i for i in [1])\nx = getattr(g, 'gi_frame')",
    ],
)
def test_introspection_refuses_private_dunder_and_frame_names(source: str) -> None:
    with pytest.raises(ValueError, match="private, dunder and frame attributes"):
        _run(source + "\nresult = {}", part=_part_api())


def test_type_is_one_argument_and_frames_are_refused_by_the_policy() -> None:
    with pytest.raises(TypeError, match="one argument"):
        _run("T = type('T', (), {})\nresult = {}")
    with pytest.raises(ValueError, match="frame attribute 'gi_frame'"):
        domains.validate_program_source("g = (i for i in [1])\nf = g.gi_frame\nresult = {}")


def test_the_two_frame_attribute_lists_are_one_list() -> None:
    assert domains._BLOCKED_ATTRIBUTES == cadex_domain_worker.SANDBOX_BLOCKED_ATTRIBUTES


# -- ADR-617: the failing call, named ------------------------------------------


def test_creation_lines_ride_beside_the_payload_not_in_it() -> None:
    cadex_domain_api.track_creation_sites(True)
    try:
        part = _part_api()
        result, _stdout, _budget = _run(
            "a = part.box(10, 10, 10)\n"
            "\n"
            "b = part.cylinder(2, 30)\n"
            "u = part.fuse([a, b])\n"
            "result = {'u': u}\n",
            part=part,
        )
        payload = result["u"].to_payload()
        assert "line" not in json.dumps(payload)
        assert cadex_domain_api.creation_lines(payload) == [4]
        assert cadex_domain_api.creation_lines(payload["arguments"][0][1]) == [3]
    finally:
        cadex_domain_api.track_creation_sites(False)


def test_a_kernel_refusal_names_the_call_its_output_and_operands() -> None:
    from cadex_part_worker import PartOperationError, _note_failure_site

    cadex_project_worker._reset_script_run()
    try:
        part = _part_api()
        result, _stdout, _budget = _run(
            "hip_l = part.box(10, 10, 10)\n"
            "hip_r = part.box(10, 10, 10, origin=[50, 0, 0])\n"
            "pelvis = part.fuse([hip_l, hip_r])\n"
            "result = {'pelvis': pelvis}\n",
            part=part,
        )
        cadex_project_worker._SCRIPT_RUN["output"] = "pelvis"
        error = PartOperationError(
            "api.fuse: declared solid but OpenCascade produced Compound "
            "containing 2 solids",
            stage="part_output_type",
            operation="fuse",
        )
        _note_failure_site(error, result["pelvis"].to_payload())
        site, sentence = cadex_project_worker.failure_site(error)
    finally:
        cadex_domain_api.track_creation_sites(False)
    assert site["output"] == "pelvis"
    assert site["call"] == "part.fuse" and site["lines"] == [3]
    assert "pelvis" in site["names"]
    assert [item["names"][0] for item in site["operands"]] == ["hip_l", "hip_r"]
    assert [item["lines"] for item in site["operands"]] == [[1], [2]]
    assert sentence == (
        "Failing call: result['pelvis'], pelvis = part.fuse (script line 3), "
        "while building output 'pelvis'; operands: argument 0[0]: hip_l = "
        "part.box (script line 1); argument 0[1]: hip_r = part.box (script line 2)."
    )


def test_an_enclosing_call_is_named_as_the_nesting() -> None:
    from cadex_part_worker import PartOperationError, _note_failure_site

    error = PartOperationError("api.fillet: boom", operation="fillet")
    _note_failure_site(error, {"domain": "part", "operation": "fillet", "arguments": [], "properties": {}})
    _note_failure_site(error, {"domain": "part", "operation": "cut", "arguments": [], "properties": {}})
    cadex_project_worker._SCRIPT_RUN.clear()
    site, sentence = cadex_project_worker.failure_site(error)
    assert site["call"] == "part.fillet" and site["inside"] == ["cut"]
    assert "nested in part.cut" in sentence


def test_a_script_exception_names_its_line() -> None:
    try:
        _run("a = 1\nb = undefined_name\nresult = {}")
    except NameError as exc:
        site, sentence = cadex_project_worker.failure_site(exc)
    assert site == {"script_line": 2}
    assert sentence == "Raised at script line 2."


def test_a_worker_crash_inside_a_fillet_is_named(tmp_path: Path, monkeypatch) -> None:
    """The cbase-heron-a segfault, as the refusal now reads."""

    import CadexScriptedProcess
    import CadexScriptedRuntime as runtime

    assert runtime._KERNEL_BREADCRUMB_NAME == cadex_domain_worker.KERNEL_BREADCRUMB_NAME
    (tmp_path / "kernel.json").write_text(json.dumps({"in_flight": [
        {"operation": "cut", "lines": [40], "stage": "output femur_l", "scalars": {}},
        {"operation": "fillet", "lines": [57], "stage": "output femur_l",
         "scalars": {"arg1": 2.0}},
    ]}))
    monkeypatch.setattr(
        CadexScriptedProcess, "run_process",
        lambda *a, **k: {"started": True, "returncode": -11, "stderr": "", "stdout": ""},
    )
    failure = runtime.execute_candidate(
        {
            "bundle_dir": str(tmp_path), "entry_module": "cadex_project_worker.py",
            "freecadcmd_executable": "FreeCADCmd", "staging": str(tmp_path),
            "timeout_seconds": 10.0, "memory_limit_bytes": 1 << 30,
            "tool_name": "xscript.project.write_script",
        },
        cancellation_check=None,
    )
    assert failure["failure_code"] == "DOMAIN_WORKER_NO_RESULT"
    assert failure["domain_failure_stage"] == "kernel_crash"
    assert failure["error"].startswith(
        "The isolated domain worker crashed (SIGSEGV) inside OpenCascade while "
        "running part.fillet made at script line 57 (arg1=2.0), during "
        "'output femur_l'."
    )
    assert failure["observed"]["kernel_operation"]["inside"] == ["cut"]
    assert "smaller radius" in failure["retry"]["required_changes"][0]


def test_the_breadcrumb_is_written_in_flight_and_cleared(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv(cadex_domain_worker.PROGRESS_ENV, str(tmp_path / "progress.json"))
    crumb = tmp_path / cadex_domain_worker.KERNEL_BREADCRUMB_NAME
    payload = {"domain": "part", "operation": "fillet", "arguments": [{}, 1.5],
               "properties": {"edges": "all"}}
    with cadex_domain_worker.kernel_operation(payload):
        in_flight = json.loads(crumb.read_text())["in_flight"]
        assert in_flight[0]["operation"] == "fillet"
        assert in_flight[0]["scalars"] == {"arg1": 1.5}
    assert json.loads(crumb.read_text()) == {"in_flight": []}


# -- ADR-618: the solver's own diagnosis --------------------------------------


def test_solver_refusal_names_the_message_and_the_joints_by_output() -> None:
    import cadex_assembly_worker as worker

    class Joint:
        def __init__(self, name: str) -> None:
            self.Name = name

    native = {
        "available": True,
        "solver_message": "Singular Jacobian at newton iteration 3",
        "remaining_degrees_of_freedom": 2,
        "conflicting_joints": ["CandidateJoint1"],
        "redundant_joints": ["CandidateJoint2"],
        "joints": [
            {"joint": "CandidateJoint0", "status": "satisfied"},
            {"joint": "CandidateJoint1", "status": "conflicting", "constraint_count": 5,
             "redundant_constraint_count": 0, "removed_degrees_of_freedom": 5,
             "maximum_absolute_residual": 3.2},
        ],
    }
    joints = {"hip_l": Joint("CandidateJoint0"), "knee_l": Joint("CandidateJoint1"),
              "knee_rod_l": Joint("CandidateJoint2")}
    sentence, implicated = worker._solver_failure_summary(native, joints)
    assert sentence == (
        " The solver said: 'Singular Jacobian at newton iteration 3'."
        " Joints it implicated: knee_l (conflicting), knee_rod_l (redundant)."
        " Remaining degrees of freedom: 2."
    )
    assert [row["joint"] for row in implicated] == ["knee_l", "knee_rod_l"]
    assert implicated[0]["maximum_absolute_residual"] == 3.2


def test_a_silent_solver_failure_says_what_that_usually_means() -> None:
    import cadex_assembly_worker as worker

    sentence, implicated = worker._solver_failure_summary({"available": True}, {})
    assert implicated == []
    assert "not connected to the grounded component" in sentence


# -- ADR-619: what a lib part can do -------------------------------------------


def test_describe_api_lists_every_lib_part_method() -> None:
    import CadexScriptedRuntime as runtime

    classes = {
        item["name"]: item for item in runtime.describe_project_api()["library"]["part_classes"]
    }
    methods = {name: {m["name"]: m for m in item["methods"]} for name, item in classes.items()}
    assert {"actuator", "joint_dynamics", "bay"} <= set(methods["QddPart"])
    assert {"horn", "actuator", "bay"} <= set(methods["ServoPart"])
    assert "mounting" in methods["BoardPart"]
    assert classes["QddPart"]["returned_by"] == ["lib.qdd"]
    assert "ServoPart.horn" in classes["LibraryPart"]["returned_by"]
    assert {"standoffs", "holes", "screws"} <= set(classes["BoardMounting"]["attributes"])
    horn = methods["ServoPart"]["horn"]
    assert not horn["signature"].startswith("(self")
    assert horn["description"]
    assert "LibraryAPI" not in classes and "LibraryError" not in classes


# -- ADR-620: prints survive a refusal ------------------------------------------


def test_prints_survive_a_script_that_raises() -> None:
    cadex_project_worker._SCRIPT_RUN.clear()
    with pytest.raises(ValueError):
        _run("print('leg length', 42)\nraise ValueError('nope')\nresult = {}")
    assert cadex_project_worker._SCRIPT_RUN["stdout"] == "leg length 42\n"


def test_the_worker_failure_report_carries_stdout_and_the_site(
    tmp_path: Path, monkeypatch
) -> None:
    request = tmp_path / "request.json"
    request.write_text(json.dumps({"schema": "x"}))
    report = tmp_path / "result.json"
    monkeypatch.setenv(cadex_project_worker.REQUEST_ENV, str(request))
    monkeypatch.setenv(cadex_project_worker.RESULT_ENV, str(report))
    monkeypatch.setattr(cadex_project_worker, "_resource_limits", lambda _request: None)

    def run(_request, _root):
        _run("print('built the frame')\nx = 1\ny = x / 0\nresult = {}")

    monkeypatch.setattr(cadex_project_worker, "_run", run)
    assert cadex_project_worker.main() == 1
    payload = json.loads(report.read_text())
    assert payload["ok"] is False
    assert payload["stdout"] == "built the frame\n"
    assert payload["error"] == "division by zero. Raised at script line 3."
    assert payload["details"]["failure_site"] == {"script_line": 3}
