# SPDX-License-Identifier: LGPL-2.1-or-later

"""The whole ``cadex -p`` path, with a scripted model instead of a real one.

``command_prompt`` is driven end to end against a **real engine** and a
**real bridge socket**; only the model is replaced (``mock_backend``). So
what these check is everything between the prompt and the report: the
project lock, the engine's opinion of the script, the revision the bridge
supplies, the export, the session file, and the exit codes a pipeline
branches on.

Also the system prompt, which has no engine in it at all — it is assembled
from a ``describe_api`` reply so that the CLI never becomes a second, staler
copy of the xscript API.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pytest

from cadex_cli.__main__ import command_prompt
from cadex_cli.agent import CLI_OVERLAY, system_prompt
from cadex_cli.report import EXIT_FAILURE, EXIT_OK, EXIT_REJECTED, RunReport
from cadex_cli.session import agent_state_path, read_agent_state

from mock_backend import SESSION_ID, turn_factory

BRACKET = """
p = params(width=num(30.0, unit="mm", min=10.0, max=90.0, step=1.0))
plate = part.box(p.width, 20.0, 6.0)
print("built at", p.width)
result = {"plate": plate}
"""

TALLER = """
p = params(width=num(30.0, unit="mm", min=10.0, max=90.0, step=1.0),
           thickness=num(9.0, unit="mm", min=2.0, max=20.0, step=0.5))
plate = part.box(p.width, 20.0, p.thickness)
result = {"plate": plate}
"""

BROKEN = """
result = {"plate": part.box(-1.0, 0.0, 0.0)}
"""


def _args(tmp_path: Path, **overrides) -> argparse.Namespace:
    values = {
        "prompt": "build a plate",
        "project": str(tmp_path / "project"),
        "out": "",
        "format": "step,stl",
        "engine": "",
        "json": False,
        "wait": False,
        "resume": False,
        "model": "mock",
        "claude": "",
        "command": None,
    }
    values.update(overrides)
    return argparse.Namespace(**values)


# -- the system prompt ---------------------------------------------------


def test_the_system_prompt_carries_the_engines_own_contract() -> None:
    api = {
        "instructions": "One project script is the sole source of truth.",
        "program_schema": "cadex-xscript-project-v9",
        "source_globals": ["part", "params", "num"],
        "result_contract": "Assign result to a dict.",
        "revision_rule": "Guard every mutation.",
        "parameters": {"params": "params(...) declares sliders."},
    }

    text = system_prompt(api)

    assert CLI_OVERLAY in text
    for expected in (
        "cadex-xscript-project-v9",
        "part, params, num",
        "One project script is the sole source of truth.",
        "Assign result to a dict.",
        "params(...) declares sliders.",
    ):
        assert expected in text


def test_the_prompt_states_the_headless_limits_rather_than_leaving_them(
) -> None:
    """The agent is told it cannot see; it should not find out by failing."""

    assert "no screenshot" in CLI_OVERLAY
    assert "MILLIMETRES" in CLI_OVERLAY
    assert "describe_api" in CLI_OVERLAY
    # And that it must not pass the guard the bridge supplies.
    assert "expected_revision" in CLI_OVERLAY


def test_the_prompt_pushes_for_a_parametric_script() -> None:
    """The cheap sweep only exists if the expensive turn made it possible."""

    assert "params(" in CLI_OVERLAY
    assert "cadex params --set" in CLI_OVERLAY


# -- the turn ------------------------------------------------------------


@pytest.mark.usefixtures("engine")
def test_a_scripted_turn_builds_exports_and_reports(tmp_path) -> None:
    factory = turn_factory(
        [
            [
                ("tool", "describe_api", {}),
                ("tool", "write_script", {"source": BRACKET}),
                ("tool", "inspect", {"scope": "output", "target": "plate"}),
                ("done", "Built a 30 mm plate."),
            ]
        ]
    )
    args = _args(tmp_path, out=str(tmp_path / "out"))
    report = RunReport()

    code = command_prompt(args, report, turn_factory=factory)

    assert code == EXIT_OK, report.error
    assert report.ok is True
    assert report.digest and report.accepted_revision
    assert report.params == {"width": 30.0}
    (output,) = report.outputs
    assert output.name == "plate" and output.kind == "brep"
    assert Path(output.files["step"]).is_file()
    assert Path(output.files["stl"]).is_file()
    assert "Built a 30 mm plate." in report.notes

    # The engine's own stdout reached the model, which is the only way it
    # can check its work here.
    turn = factory.made[0]
    assert "built at 30" in turn.last_payload("write_script")["stdout"]


@pytest.mark.usefixtures("engine")
def test_the_bridge_supplies_the_guard_for_a_second_write(tmp_path) -> None:
    """Two writes in one turn, with no ``expected_revision`` from the model."""

    factory = turn_factory(
        [
            [
                ("tool", "write_script", {"source": BRACKET}),
                ("tool", "write_script", {"source": TALLER}),
                ("done", "Two writes."),
            ]
        ]
    )
    report = RunReport()

    assert command_prompt(_args(tmp_path), report, turn_factory=factory) == EXIT_OK
    turn = factory.made[0]
    first, second = (
        json.loads(reply["content"][0]["text"])
        for name, reply in turn.tool_results
        if name == "write_script"
    )
    assert first["expected_revision_used"] == ""  # a project with no script yet
    assert second["expected_revision_used"] == first["revision"]
    assert report.params == {"width": 30.0, "thickness": 9.0}


@pytest.mark.usefixtures("engine")
def test_a_refused_script_can_be_followed_by_an_accepted_one(tmp_path) -> None:
    """A rejection moves the working revision; the retry must still land."""

    factory = turn_factory(
        [
            [
                ("tool", "write_script", {"source": BROKEN}),
                ("tool", "write_script", {"source": BRACKET}),
                ("done", "Fixed it."),
            ]
        ]
    )
    report = RunReport()

    assert command_prompt(_args(tmp_path), report, turn_factory=factory) == EXIT_OK
    turn = factory.made[0]
    payloads = [
        json.loads(reply["content"][0]["text"])
        for name, reply in turn.tool_results
        if name == "write_script"
    ]
    assert payloads[0]["ok"] is False
    assert payloads[1]["ok"] is True
    # The second call was guarded with the revision the *refusal* produced.
    assert payloads[1]["expected_revision_used"] == payloads[0]["model_state"][
        "next_write_expected_revision"
    ]


@pytest.mark.usefixtures("engine")
def test_a_turn_that_never_accepts_a_script_exits_rejected(tmp_path) -> None:
    factory = turn_factory([[("tool", "write_script", {"source": BROKEN}),
                             ("done", "I could not.")]])
    report = RunReport()

    code = command_prompt(_args(tmp_path), report, turn_factory=factory)

    assert code == EXIT_REJECTED
    assert report.ok is False
    assert "without the engine accepting" in report.error


@pytest.mark.usefixtures("engine")
def test_a_failed_turn_exits_one_and_says_why(tmp_path) -> None:
    factory = turn_factory([[("fail", "the model ran out of context")]])
    report = RunReport()

    code = command_prompt(_args(tmp_path), report, turn_factory=factory)

    assert code == EXIT_FAILURE
    assert report.error == "the model ran out of context"


# -- the session file ----------------------------------------------------


@pytest.mark.usefixtures("engine")
def test_the_session_id_is_stored_beside_the_engines_state(tmp_path) -> None:
    factory = turn_factory([[("tool", "write_script", {"source": BRACKET}),
                             ("done", "ok")]])
    report = RunReport()
    args = _args(tmp_path)

    command_prompt(args, report, turn_factory=factory)

    root = Path(report.project_root)
    stored = read_agent_state(root)
    assert stored.session_id == SESSION_ID
    assert stored.model == "mock"
    assert report.session_id == SESSION_ID
    # A CLI-owned sibling; the engine's own state file is untouched by us.
    assert agent_state_path(root).name == "agent.json"
    assert (root / "script.json").is_file()
    payload = json.loads(agent_state_path(root).read_text(encoding="utf-8"))
    assert payload["schema"] == "cadex-cli-agent-v1"


@pytest.mark.usefixtures("engine")
def test_resume_passes_the_stored_session_id_and_default_does_not(tmp_path) -> None:
    script = [[("tool", "write_script", {"source": BRACKET}), ("done", "ok")]]

    first = turn_factory(script)
    command_prompt(_args(tmp_path), RunReport(), turn_factory=first)
    assert first.made[0].session_id == SESSION_ID  # the mock's own id

    resumed = turn_factory([[("done", "ok")]])
    command_prompt(_args(tmp_path, resume=True), RunReport(), turn_factory=resumed)
    # It was *given* the stored id rather than starting from nothing.
    assert resumed.made[0].session_id == SESSION_ID

    fresh = turn_factory([[("done", "ok")]])
    command_prompt(_args(tmp_path, resume=False), RunReport(), turn_factory=fresh)
    assert fresh.made[0].session_id == SESSION_ID  # the mock supplies its own


@pytest.mark.usefixtures("engine")
def test_the_turn_runs_in_the_project_directory(tmp_path) -> None:
    """Claude Code files a conversation under the directory it ran in.

    A scratch cwd per turn makes every ``--resume`` look like an expired
    session, which is indistinguishable from a real one and silently costs
    the whole conversation.
    """

    factory = turn_factory([[("done", "ok")]])
    report = RunReport()
    command_prompt(_args(tmp_path), report, turn_factory=factory)
    assert factory.made[0].cwd == report.project_root
