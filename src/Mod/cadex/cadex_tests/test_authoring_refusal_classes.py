# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""The four refusals hex2 and hex3 each learned the API by (ot10 A4).

Both unassisted hexapod runs met the same four refusals in the same order,
and each cost a round-trip or a full 12-14 KB resend
(``docs/probes/hex/hex2-GAPS.md``, ``hex3-GAPS.md``). The inputs below are
the ones the product agent actually sent; the refusal texts they got were:

1. ``lib.servo.horn: style must be one of cross, double_arm, single_arm.``
   for ``s.horn("arm")`` (hex2) and ``s.horn("single")`` (hex3). The library
   listing the agent reads said only ``.horn(style)``.
2. ``There is no project script to edit yet; use write_script.`` for an
   ``edit_script`` sent straight after a refused first ``write_script``
   (hex3), while the engine's own ``revision_rule`` told the agent that "a
   failed candidate becomes the working revision" -- false since ADR-044.
3. ``An Assembly program must return exactly one assembly and one
   solver_diagnostics output.`` for a script that returned its assembly and
   never solved it (hex2 and hex3).
4. ``Every joint listed in api.assembly must be returned exactly once, and no
   unlisted joint output is allowed.`` for joints kept only in a Python list
   (hex3; hex2 met the component twin).

Each class is now prevented where the agent reads (the listing, the
``revision_rule`` and the ``result_contract``), and each refusal names the
fix. These tests pin both halves.
"""

from __future__ import annotations

import pytest

import CadexScriptedRuntime as runtime
import cadex_assembly_worker as worker
from CadexScriptStore import CadexProjectScriptStore
from CadexScriptedRuntime import DomainRuntimeFailure, prepare_project_candidate
from cadex_library_api import LibraryError, library_listing
from test_library import _assembly_api, _servo_lib


# -- 1. the horn style -------------------------------------------------------


@pytest.mark.parametrize(
    "guess, meant",
    [("single", ["'single_arm'"]), ("arm", ["'double_arm'", "'single_arm'"])],
)
def test_a_wrong_horn_style_names_the_style_it_meant(guess, meant) -> None:
    servo = _servo_lib().servo("mg90s")
    with pytest.raises(LibraryError) as caught:
        servo.horn(guess)
    message = str(caught.value)
    assert f"{guess!r} is not a horn style" in message
    assert "Did you mean" in message
    for name in meant:
        assert name in message.split("Did you mean", 1)[1]


def test_an_unrelated_horn_style_still_lists_every_style() -> None:
    with pytest.raises(LibraryError) as caught:
        _servo_lib().servo("mg90s").horn("zzz")
    message = str(caught.value)
    assert "'cross', 'double_arm', 'single_arm'" in message
    assert "Did you mean" not in message


def test_the_library_listing_names_every_horn_style() -> None:
    notes = library_listing()["catalog"]["servos"]["notes"]
    for style in ("'single_arm'", "'double_arm'", "'cross'"):
        assert style in notes


# -- 2. edit_script before an accepted script --------------------------------


def _edit(root) -> DomainRuntimeFailure:
    captured = {
        "tool_name": "xscript.project.edit_script",
        "operation": "edit_script",
        "arguments": {
            "expected_revision": "",
            "replacements": [{"old": 's.horn("single")', "new": 's.horn("single_arm")'}],
        },
        "project_root": str(root),
    }
    with pytest.raises(DomainRuntimeFailure) as caught:
        prepare_project_candidate(captured)
    return caught.value


def _failure_text(failure: DomainRuntimeFailure) -> tuple[str, dict]:
    payload = failure.payload
    return str(payload.get("error") or ""), payload


def test_edit_after_a_refused_first_write_says_it_was_rolled_back(tmp_path) -> None:
    CadexProjectScriptStore(str(tmp_path)).write(
        state_updates={
            "latest_candidate": {
                "status": "failed",
                "revision": "ab" * 32,
                "attempt_id": "a1",
                "failure_code": "DOMAIN_CANDIDATE_FAILED",
                "error": "lib.servo.horn: 'single' is not a horn style",
            }
        }
    )
    error, payload = _failure_text(_edit(tmp_path))
    assert payload["failure_code"] == "NO_PROJECT_SCRIPT"
    assert "refused and rolled back" in error
    assert "Resend the whole corrected source with write_script" in error
    assert payload["retry"]["required_changes"] == [
        {"tool": "write_script", "expected_revision": ""}
    ]


def test_edit_on_an_empty_project_names_write_script(tmp_path) -> None:
    error, payload = _failure_text(_edit(tmp_path))
    assert payload["failure_code"] == "NO_PROJECT_SCRIPT"
    assert "rolled back" not in error
    assert "write_script" in error


def test_the_revision_rule_no_longer_says_a_failed_candidate_is_working() -> None:
    rule = runtime.describe_project_api()["revision_rule"]
    assert "failed candidate becomes the working revision" not in rule
    assert "rolled back" in rule
    assert "never the refused one" in rule


# -- 3 and 4. the assembly's result shape ------------------------------------


def _hexapod_like(api):
    """One grounded body, two legs' worth of components and joints."""

    base = api.component({"document_uid": "d", "object_name": "base"}, grounded=True)
    femur = api.component({"document_uid": "d", "object_name": "femur"})
    tibia = api.component({"document_uid": "d", "object_name": "tibia"})
    hip = api.joint("revolute", api.connector(base), api.connector(femur), label="hip_l1")
    knee = api.joint("revolute", api.connector(femur), api.connector(tibia), label="knee_l1")
    asm = api.assembly([base, femur, tibia], [hip, knee], label="hexapod")
    return base, femur, tibia, hip, knee, asm


def _refusal(raw) -> str:
    with pytest.raises(worker.AssemblyCandidateError) as caught:
        worker._graph_contract(raw)
    return str(caught.value)


def test_an_unsolved_assembly_names_the_solve_line_to_add() -> None:
    api = _assembly_api()
    base, femur, tibia, hip, knee, asm = _hexapod_like(api)
    message = _refusal(
        {"c_base": base, "c_femur": femur, "c_tibia": tibia,
         "hip": hip, "knee": knee, "hexapod": asm}
    )
    assert "exactly one assembly and one solver_diagnostics output" in message
    assert "1 assembly ('hexapod') and 0 solver_diagnostics (none)" in message
    assert "result['solve'] = assembly.solve(hexapod)" in message


def test_two_assemblies_are_told_to_become_one() -> None:
    api = _assembly_api()
    base, femur, tibia, hip, knee, asm = _hexapod_like(api)
    other = api.assembly([base], [], label="other")
    message = _refusal({"a": asm, "b": other, "s": api.solve(asm)})
    assert "2 assembly ('a', 'b')" in message
    assert "single api.assembly" in message


def test_joints_kept_in_a_list_are_named() -> None:
    api = _assembly_api()
    base, femur, tibia, hip, knee, asm = _hexapod_like(api)
    message = _refusal(
        {"c_base": base, "c_femur": femur, "c_tibia": tibia,
         "asm": asm, "solve": api.solve(asm)}
    )
    assert "Every joint listed in api.assembly must be returned exactly once" in message
    assert "2 joint(s) listed in api.assembly are not returned" in message
    assert "'hip_l1', 'knee_l1'" in message
    assert "result['joint_' + str(i)]" in message


def test_components_kept_in_a_list_are_named_by_place() -> None:
    api = _assembly_api()
    base, femur, tibia, hip, knee, asm = _hexapod_like(api)
    message = _refusal({"c_base": base, "hip": hip, "knee": knee,
                        "asm": asm, "solve": api.solve(asm)})
    assert "2 component(s) listed in api.assembly are not returned" in message
    assert "component #1 in api.assembly, component #2 in api.assembly" in message


def test_one_joint_under_two_keys_names_both_keys() -> None:
    api = _assembly_api()
    base, femur, tibia, hip, knee, asm = _hexapod_like(api)
    message = _refusal(
        {"c_base": base, "c_femur": femur, "c_tibia": tibia, "hip": hip,
         "hip_again": hip, "knee": knee, "asm": asm, "solve": api.solve(asm)}
    )
    assert "'hip' and 'hip_again'" in message


def test_a_complete_result_passes_the_contract() -> None:
    api = _assembly_api()
    base, femur, tibia, hip, knee, asm = _hexapod_like(api)
    names = worker._graph_contract(
        {"c_base": base, "c_femur": femur, "c_tibia": tibia, "hip": hip,
         "knee": knee, "asm": asm, "solve": api.solve(asm)}
    )
    assert names[0] == "asm" and names[2] == "solve"


def test_the_result_contract_teaches_the_assembly_shape() -> None:
    contract = runtime.describe_project_api()["result_contract"]
    assert "exactly one assembly.assembly(...) value" in contract
    assert "exactly one assembly.solve(<that assembly>) value" in contract
    assert "kept only in a Python list is not returned" in contract
