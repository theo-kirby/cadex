# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""The command line itself: flags, exit codes, and the ``--json`` envelope.

These run ``main()`` against a real engine, because the interface a pipeline
branches on is the process — its exit status and its stdout — and not the
functions behind it.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from cadex_cli import CLI_SCHEMA
from cadex_cli.__main__ import main
from cadex_cli.report import EXIT_FAILURE, EXIT_OK, EXIT_REJECTED, EXIT_USAGE

PLATE = """
p = params(width=num(30.0, unit="mm", min=10.0, max=90.0, step=1.0),
           thickness=num(6.0, unit="mm", min=2.0, max=20.0, step=0.5))
plate = part.box(p.width, 20.0, p.thickness)
result = {"plate": plate}
"""

BROKEN = "result = {'plate': part.box(0.0, 0.0, 0.0)}\n"


@pytest.fixture
def project(engine, tmp_path, capsys):
    """A project with ``PLATE`` accepted, and the envelope that produced it."""

    source = tmp_path / "plate.py"
    source.write_text(PLATE, encoding="utf-8")
    root = tmp_path / "project"
    code = main(
        [
            "script",
            "--set",
            str(source),
            "--project",
            str(root),
            "--out",
            str(tmp_path / "out"),
            "--json",
        ]
    )
    assert code == EXIT_OK, capsys.readouterr()
    envelope = json.loads(capsys.readouterr().out)
    return {"root": root, "envelope": envelope}


def _envelope(capsys) -> dict:
    return json.loads(capsys.readouterr().out)


# -- the envelope --------------------------------------------------------


def test_the_json_envelope_carries_what_a_pipeline_needs(project) -> None:
    envelope = project["envelope"]

    assert envelope["schema"] == CLI_SCHEMA
    assert envelope["ok"] is True
    assert set(envelope) >= {
        "schema",
        "ok",
        "project_root",
        "revision",
        "accepted_revision",
        "digest",
        "params",
        "outputs",
        "session_id",
    }
    assert envelope["params"] == {"width": 30.0, "thickness": 6.0}
    (output,) = envelope["outputs"]
    assert output["name"] == "plate" and output["kind"] == "brep"
    assert Path(output["files"]["step"]).is_file()
    assert envelope["engine"]["source"] in {"dev-tree", "payload", "explicit"}


def test_json_goes_to_stdout_and_progress_does_not(project, capsys, tmp_path) -> None:
    """``--json`` has to be safe to pipe, or none of this composes."""

    code = main(
        ["export", "--project", str(project["root"]), "--out", str(tmp_path / "e"), "--json"]
    )
    captured = capsys.readouterr()

    assert code == EXIT_OK
    json.loads(captured.out)  # nothing but the envelope
    assert "rebuild" in captured.err


# -- params: the cheap loop ----------------------------------------------


def test_params_changes_geometry_with_no_model_in_the_loop(
    project, capsys, tmp_path, monkeypatch
) -> None:
    """The whole point of the CLI: a sweep that never spawns ``claude``.

    ``find_claude`` is made to explode, so a run that reached for a model
    would fail loudly rather than pass quietly.
    """

    import cadex_cli.__main__ as entry

    monkeypatch.setattr(
        entry, "find_claude", lambda *_a, **_k: pytest.fail("spawned a model")
    )

    code = main(
        [
            "params",
            "--project",
            str(project["root"]),
            "--set",
            "width=55",
            "--set",
            "thickness=8.5",
            "--out",
            str(tmp_path / "sweep"),
            "--json",
        ]
    )
    envelope = _envelope(capsys)

    assert code == EXIT_OK, envelope
    assert envelope["params"] == {"width": 55.0, "thickness": 8.5}
    # The geometry moved, and the digest is how a pipeline knows.
    assert envelope["digest"] != project["envelope"]["digest"]
    assert Path(envelope["outputs"][0]["files"]["stl"]).is_file()


def test_params_needs_a_number_and_says_so(project, capsys) -> None:
    code = main(
        ["params", "--project", str(project["root"]), "--set", "width=thick", "--json"]
    )
    assert code == EXIT_USAGE
    assert "is not a number" in _envelope(capsys)["error"]


def test_params_with_no_assignment_is_a_usage_error(project, capsys) -> None:
    code = main(["params", "--project", str(project["root"]), "--json"])
    assert code == EXIT_USAGE
    assert "at least one --set" in _envelope(capsys)["error"]


def test_setting_a_parameter_that_is_not_declared_is_rejected(
    project, capsys
) -> None:
    code = main(
        ["params", "--project", str(project["root"]), "--set", "nonesuch=3", "--json"]
    )
    assert code == EXIT_REJECTED
    assert _envelope(capsys)["ok"] is False


# -- script --------------------------------------------------------------


def test_script_prints_the_source_and_nothing_else(project, capsys) -> None:
    """So ``cadex script > model.py`` is a working command."""

    code = main(["script", "--project", str(project["root"])])
    captured = capsys.readouterr()

    assert code == EXIT_OK
    assert captured.out == PLATE
    assert captured.err == ""


def test_a_long_script_and_a_wide_parameter_set_are_read_whole(
    engine, tmp_path, capsys
) -> None:
    """`inspect` is bounded by design; the CLI must page it to the end.

    Any value over 1 KiB comes back as a stub naming the path to fetch it
    from, and a mapping comes back 50 keys at a time. A short script and a
    handful of parameters slip under both, so this reads a script well over
    the string cap with more parameters than one page holds — which is
    exactly the case that turned `cadex script` into a printout of
    `{"type": "string", "characters": 1574, ...}`.
    """

    names = [f"slot_{index:02d}" for index in range(60)]
    declarations = ",\n    ".join(
        f"{name}=num({index + 1}.0, unit='mm', min=0.5, max=200.0, step=0.5)"
        for index, name in enumerate(names)
    )
    padding = "\n".join(f"# {'filler ' * 12}" for _ in range(40))
    source = (
        f"p = params(\n    {declarations},\n)\n"
        f"{padding}\n"
        "plate = part.box(p.slot_00 + 20.0, p.slot_01 + 20.0, p.slot_02 + 5.0)\n"
        'result = {"plate": plate}\n'
    )
    assert len(source) > 4096, len(source)
    script_file = tmp_path / "wide.py"
    script_file.write_text(source, encoding="utf-8")
    root = tmp_path / "project"

    assert main(["script", "--set", str(script_file), "--project", str(root),
                 "--json"]) == EXIT_OK, capsys.readouterr()
    envelope = _envelope(capsys)
    assert set(envelope["params"]) == set(names)

    assert main(["script", "--project", str(root)]) == EXIT_OK
    assert capsys.readouterr().out == source


def test_a_script_the_engine_refuses_exits_three(engine, tmp_path, capsys) -> None:
    """Exit 3 is 'the engine said no', which a pipeline handles differently."""

    source = tmp_path / "broken.py"
    source.write_text(BROKEN, encoding="utf-8")

    code = main(
        ["script", "--set", str(source), "--project", str(tmp_path / "p"), "--json"]
    )

    assert code == EXIT_REJECTED
    assert _envelope(capsys)["ok"] is False


def test_a_missing_script_file_is_a_usage_error(tmp_path, capsys) -> None:
    code = main(
        ["script", "--set", str(tmp_path / "nope.py"), "--project", str(tmp_path / "p"),
         "--json"]
    )
    assert code == EXIT_USAGE
    assert "no such file" in _envelope(capsys)["error"]


def test_neither_form_of_script_asks_for_the_restore_pass(
    project, tmp_path, monkeypatch, capsys
) -> None:
    """Reading and rewriting a script must survive a store that will not replay.

    The walk's digest edit lands on a project whose stored script has just
    stopped re-running: ``train --put`` overwrote the asset the accepted
    script declares by sha256 (ADR-272). Measured on ot4-swing2, where the
    open's restore pass failed and took both legs with it, so the two
    commands whose whole job is to rewrite that literal could not run.
    Neither form needs the replay — the read reads the stored source, the
    write replaces it — so neither may ask for it.
    """

    from cadex_cli import __main__ as main_module

    asked: list[bool] = []
    real = main_module.open_project

    def recording(client, root, *, restore=True):
        asked.append(bool(restore))
        return real(client, root, restore=restore)

    monkeypatch.setattr(main_module, "open_project", recording)

    assert main(["script", "--project", str(project["root"])]) == EXIT_OK
    source = tmp_path / "again.py"
    source.write_text(PLATE, encoding="utf-8")
    assert main(
        ["script", "--set", str(source), "--project", str(project["root"]), "--json"]
    ) == EXIT_OK, capsys.readouterr()

    assert asked == [False, False]


# -- flags ---------------------------------------------------------------


def test_a_global_flag_means_the_same_on_either_side_of_the_subcommand(
    project, capsys, tmp_path
) -> None:
    """A subparser default must not overwrite what was already read."""

    code = main(
        ["--project", str(project["root"]), "--json", "export", "--out", str(tmp_path / "x")]
    )
    envelope = _envelope(capsys)
    assert code == EXIT_OK
    assert envelope["project_root"] == str(project["root"])


def test_an_unknown_export_format_is_refused_before_the_engine_runs(
    project, capsys, tmp_path
) -> None:
    code = main(
        ["export", "--project", str(project["root"]), "--out", str(tmp_path / "x"),
         "--format", "dwg", "--json"]
    )
    assert code == EXIT_FAILURE
    assert "Unknown export format" in _envelope(capsys)["error"]


def test_export_without_out_is_a_usage_error(project, capsys) -> None:
    assert main(["export", "--project", str(project["root"]), "--json"]) == EXIT_USAGE
    assert "needs --out" in _envelope(capsys)["error"]


def test_a_bare_invocation_prints_help_and_exits_two(capsys) -> None:
    assert main([]) == EXIT_USAGE
    assert "usage: cadex" in capsys.readouterr().err


def test_an_engine_that_does_not_exist_is_reported_not_traced(
    tmp_path, capsys
) -> None:
    code = main(
        ["export", "--project", str(tmp_path / "p"), "--out", str(tmp_path / "o"),
         "--engine", str(tmp_path / "nowhere"), "--json"]
    )
    assert code == EXIT_FAILURE
    assert "staged engine payload root" in _envelope(capsys)["error"]


def test_the_human_summary_names_the_files_and_the_next_guard(
    project, capsys, tmp_path
) -> None:
    code = main(["export", "--project", str(project["root"]), "--out", str(tmp_path / "h")])
    captured = capsys.readouterr()

    assert code == EXIT_OK
    assert "wrote  plate" in captured.out
    assert "params thickness=6, width=30" in captured.out
    assert "next   expected_revision" in captured.out


@pytest.mark.parametrize("session_id,model", [
    ("offline-session", "sonnet"),
    ("new-session", "sonnet"),
    ("offline-session", "opus"),
])
def test_refused_walk_preserves_session_unless_identity_changes(
    project, tmp_path, capsys, session_id, model
):
    """Ordinary walk, real restore, offline Claude executable; no provider."""
    import subprocess
    from cadex_cli.session import write_agent_state

    root = project["root"]
    write_agent_state(root, session_id="offline-session", model="sonnet")
    agent = root / "agent.json"
    payload = json.loads(agent.read_text())
    payload["updated_at"] = "2000-01-01T00:00:00Z"
    agent.write_text(json.dumps(payload))
    before_agent = agent.read_bytes()
    before_stat = agent.stat()
    # Keep existing user edits, including edits to a tracked document.
    decisions = root / "DECISIONS.md"
    decisions.write_text(decisions.read_text() + "\nUser's pending decision.\n")
    (root / "user-note.txt").write_text("untracked user work\n")
    preserved = {name: (root / name).read_bytes() for name in (
        "script.py", "PROGRESS.md", "ARCHITECTURE.md", "DECISIONS.md", "user-note.txt"
    )}
    def head():
        return subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"])
    before_head = head()
    before = json.loads((root / "script.json").read_text())
    refusal = "Controlled offline usage-credit refusal"
    fake = tmp_path / "refuse"
    fake.write_text(
        "#!/usr/bin/env python3\nimport json,sys\n"
        + "print(" + repr(json.dumps({"type": "assistant", "message": {
            "content": [{"type": "text", "text": refusal}]}})) + ")\n"
        + "print(" + repr(json.dumps({"type": "result", "is_error": True,
            "session_id": session_id, "result": refusal})) + ")\nsys.exit(1)\n"
    )
    fake.chmod(0o755)
    code = main(["walk", "--resume", "--prompt", "offline refusal",
                 "--project", str(root), "--out", str(root / "runs/refused"),
                 "--claude", str(fake), "--model", model, "--json"])
    report = _envelope(capsys)
    assert code == EXIT_FAILURE
    assert refusal in report["error"]
    assert head() == before_head
    for name, content in preserved.items():
        assert (root / name).read_bytes() == content
    after = json.loads((root / "script.json").read_text())
    for key in ("accepted_revision", "accepted_digest", "param_values"):
        assert after[key] == before[key]
    assert after["accepted_attempt"]["attempt_id"] != before["accepted_attempt"]["attempt_id"]
    assert (root / after["accepted_attempt"]["staging"] / "outputs").is_dir()
    assert after["latest_candidate"]["attempt_id"] == after["accepted_attempt"]["attempt_id"]
    stored = json.loads(agent.read_text())
    assert (stored["session_id"], stored["model"]) == (session_id, model)
    if (session_id, model) == ("offline-session", "sonnet"):
        assert agent.read_bytes() == before_agent
        assert agent.stat().st_ino == before_stat.st_ino
        assert agent.stat().st_mtime_ns == before_stat.st_mtime_ns
    else:
        assert stored["updated_at"] != payload["updated_at"]


def test_the_machine_can_name_the_turn_model_once(monkeypatch) -> None:
    """``$CADEX_MODEL`` is the machine's answer; ``--model`` still wins.

    A box whose default model is unavailable -- out of usage credit, not
    enabled on the account -- otherwise cannot run ``cadex walk`` without a
    person putting ``--model`` on every command, and a lifecycle walk is not
    allowed to need a person.
    """

    from cadex_cli.agent import DEFAULT_MODEL, MODEL_ENV, default_model
    from cadex_cli.__main__ import build_parser

    monkeypatch.delenv(MODEL_ENV, raising=False)
    assert default_model() == DEFAULT_MODEL
    assert build_parser().parse_args(["walk"]).model == DEFAULT_MODEL

    monkeypatch.setenv(MODEL_ENV, "  a-model-with-credit  ")
    assert default_model() == "a-model-with-credit"
    for argv, expected in (
        (["walk"], "a-model-with-credit"),
        (["walk", "--model", "explicit"], "explicit"),
        (["-p", "hello"], "a-model-with-credit"),
        (["--model", "explicit", "-p", "hello"], "explicit"),
    ):
        assert build_parser().parse_args(argv).model == expected, argv

    monkeypatch.setenv(MODEL_ENV, "   ")
    assert default_model() == DEFAULT_MODEL
