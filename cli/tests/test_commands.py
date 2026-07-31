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
