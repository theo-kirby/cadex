# SPDX-FileCopyrightText: 2026 Cadex Authors
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


def test_the_prompt_teaches_the_two_policy_strings_as_inline_literals() -> None:
    """The one exception to the parametric rule, taught before it is hit.

    nt3's first walk from a prompt stopped at exit 3 because the design
    turn factored ``weights`` and ``sha256`` into module constants, which
    ``cadex walk``'s literal rewrite refuses (docs/CLI.md §2, leg 4). The
    overlay taught the ``policy_on`` switch and said nothing about the
    literals; it now says both.
    """

    assert 'weights="walk.cxpolicy"' in CLI_OVERLAY
    assert "INLINE STRING LITERALS" in CLI_OVERLAY
    # ...and names the mistake, so the model can recognise its own habit.
    assert "weights=WEIGHTS" in CLI_OVERLAY


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
    # The reason, not just the outcome: what the engine last refused, and
    # what the agent said on its way out. A `cadex walk` design leg copies
    # this string into its own envelope, so it is the only place a run with
    # no human watching can learn why the script never landed.
    assert "the engine last refused write_script" in report.error
    assert "the agent's closing words: I could not." in report.error


@pytest.mark.usefixtures("engine")
def test_a_turn_that_offers_no_script_says_the_engine_refused_nothing(
    tmp_path,
) -> None:
    """The other way to reach exit 3, and it used to read the same.

    Seen inside `cadex walk --prompt`: the design turn read the authoring
    contract, said nothing more, and the envelope claimed the engine had
    not accepted a script — with no hint that the engine had never been
    offered one.
    """

    factory = turn_factory([[("tool", "describe_api", {}),
                             ("done", "I need more information.")]])
    report = RunReport()

    code = command_prompt(_args(tmp_path), report, turn_factory=factory)

    assert code == EXIT_REJECTED
    assert "the engine refused nothing" in report.error
    assert "describe_api" in report.error
    assert "never offered a script" in report.error
    assert "the agent's closing words: I need more information." in report.error


def test_a_rejection_reason_survives_a_silent_turn_with_no_calls() -> None:
    """No calls and no closing words is still a distinguishable reason."""

    from cadex_cli.__main__ import _rejection_reason

    reason = _rejection_reason("", [])

    assert "no tool call" in reason
    assert "closing words" not in reason


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
@pytest.mark.parametrize("resume", [False, True])
def test_resumed_turn_reads_current_project_history_and_appends_notes(tmp_path, resume):
    """Resume must reload project knowledge, not rely on conversation memory."""
    first = RunReport()
    assert command_prompt(_args(tmp_path), first, turn_factory=turn_factory([[
        ("tool", "write_script", {"source": BRACKET}),
        ("done", "Built the mount.\nDECISION: retain the sensor footprint.\n"
         "NOTE sensors: encoder measures the hinge angle.\n"
         "NOTE gear-ratios: rejected 4:1 because it fouled the mount."),
    ]])) == EXIT_OK
    root = Path(first.project_root)
    # Knowledge can change between visits, independently of Claude's session.
    architecture = root / "ARCHITECTURE.md"
    architecture.write_text(architecture.read_text() + "\nKeep the cable exit clear.\n")
    sensors = root / "docs/sensors.md"
    sensors.write_text(sensors.read_text() + "\nEncoder offset measured at 0.25 rad.\n")
    decisions = root / "DECISIONS.md"
    decisions.write_text(decisions.read_text() + "\n" + "old rationale " * 800
                         + "\n## ADR-002 — retain the sensor footprint.\nNewest constraint: keep 3 mm cable clearance.\n")
    decisions_before = decisions.read_text()
    sensors_before = sensors.read_text()
    progress = root / "PROGRESS.md"
    progress.write_text(progress.read_text() + "\nPrevious clearance: 2.5 mm.\n")
    progress_before = progress.read_text()
    resumed = turn_factory([[
        ("tool", "write_script", {"source": TALLER}),
        ("done", "Thickened the mount.\nDECISION: keep width while increasing thickness.\n"
         "NOTE sensors: preserve the measured offset after thickening."),
    ]])

    def resume_with_history(**kwargs):
        # Check the input before MockTurn supplies any fallback session id.
        assert kwargs["session_id"] == (SESSION_ID if resume else "")
        assert kwargs["cwd"] == str(root)
        prompt = kwargs["system_prompt_text"]
        for expected in (
            "Newest constraint: keep 3 mm cable clearance.",
            "earlier characters omitted",
            "Keep the cable exit clear.",
            "retain the sensor footprint.",
            "encoder measures the hinge angle.",
            "Encoder offset measured at 0.25 rad.",
            "rejected 4:1 because it fouled the mount.",
            "Previous clearance: 2.5 mm.",
        ):
            assert expected in prompt
        return resumed(**kwargs)

    report = RunReport()
    assert command_prompt(
        _args(tmp_path, resume=resume, prompt="thicken the mount using its recorded constraints"),
        report, turn_factory=resume_with_history,
    ) == EXIT_OK, report.error
    assert report.digest != first.digest
    assert (root / "DECISIONS.md").read_text().startswith(decisions_before)
    assert "keep width while increasing thickness." in (root / "DECISIONS.md").read_text()
    assert sensors.read_text().startswith(sensors_before)
    assert "preserve the measured offset after thickening." in sensors.read_text()
    assert (root / "PROGRESS.md").read_text().startswith(progress_before)


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


@pytest.mark.usefixtures("engine")
@pytest.mark.parametrize("model", ["mock", "changed-model"])
def test_successful_resumed_edit_preserves_or_updates_session_identity(tmp_path, model):
    args = _args(tmp_path)
    first = RunReport()
    assert command_prompt(args, first, turn_factory=turn_factory([[
        ("tool", "write_script", {"source": BRACKET}), ("done", "ok")
    ]])) == EXIT_OK
    root = Path(first.project_root)
    path = agent_state_path(root)
    payload = json.loads(path.read_text())
    payload["updated_at"] = "2000-01-01T00:00:00Z"
    path.write_text(json.dumps(payload))
    before = path.read_bytes()
    report = RunReport()
    assert command_prompt(_args(tmp_path, resume=True, model=model), report,
                          turn_factory=turn_factory([[
        ("tool", "write_script", {"source": TALLER}), ("done", "accepted edit")
    ]])) == EXIT_OK
    assert report.accepted_revision != first.accepted_revision
    assert report.digest != first.digest
    assert (root / "script.py").read_text() == TALLER
    stored = read_agent_state(root)
    assert (stored.session_id, stored.model) == (SESSION_ID, model)
    if model == "mock":
        assert path.read_bytes() == before
    else:
        assert stored.updated_at != payload["updated_at"]


# -- the one follow-up ---------------------------------------------------


@pytest.mark.usefixtures("engine")
def test_a_turn_that_calls_nothing_is_asked_once_more(tmp_path) -> None:
    """The failure that cost three live walks in one evening.

    A design turn that ends without a single tool call has done nothing:
    it reasoned, it wrote a paragraph to stderr, and the project is
    byte-for-byte what it was. The engine, the bridge and the model's
    reading of the project are all still standing at that moment, so the
    run asks once more in the same conversation rather than exiting 3 on a
    turn that never started.
    """

    factory = turn_factory(
        [
            [("text", "Let me think about which finding to take.")],
            [("tool", "write_script", {"source": BRACKET}),
             ("done", "Taken. DECISION: built the plate.")],
        ]
    )
    report = RunReport()

    code = command_prompt(_args(tmp_path), report, turn_factory=factory)

    assert code == EXIT_OK, report.error
    turn = factory.made[0]
    assert len(turn.prompts) == 2
    assert "one follow-up" in turn.prompts[1]
    # Both turns' prose survives, so a closing DECISION: line from either
    # reaches the project's ADR log.
    assert "Let me think" in report.notes[0] or any(
        "Let me think" in note for note in report.notes
    )
    assert any("asked once more" in note for note in report.notes)


@pytest.mark.usefixtures("engine")
def test_the_follow_up_is_not_offered_to_a_turn_the_engine_refused(
    tmp_path,
) -> None:
    """Narrow by construction: a refused turn was told why and stopped.

    Asking that one again is how a loop starts, so the follow-up fires only
    when the model reached the engine not once.
    """

    factory = turn_factory([[("tool", "write_script", {"source": BROKEN}),
                             ("done", "I could not.")]])
    report = RunReport()

    code = command_prompt(_args(tmp_path), report, turn_factory=factory)

    assert code == EXIT_REJECTED
    assert factory.made[0].turns == 1
    assert not any("asked once more" in note for note in report.notes)


@pytest.mark.usefixtures("engine")
def test_a_follow_up_that_still_offers_nothing_exits_rejected(tmp_path) -> None:
    """One follow-up, not a retry loop: the second silence is the answer."""

    factory = turn_factory(
        [
            [("text", "Thinking.")],
            [("done", "NO CHANGE: the recorded findings do not justify one.")],
        ]
    )
    report = RunReport()

    code = command_prompt(_args(tmp_path), report, turn_factory=factory)

    assert code == EXIT_REJECTED
    assert factory.made[0].turns == 2
    assert "no tool call" in report.error
    assert "NO CHANGE" in report.error
