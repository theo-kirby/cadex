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
    }
    # Cadex runs no agent (ADR-538): nothing in the envelope is a conversation's.
    assert not set(envelope) & {"session_id", "model", "usage", "attachments", "comments"}
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
    """The whole point of the CLI: a sweep with no model anywhere in it."""

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

    def recording(client, root, *, restore=True, **kwargs):
        asked.append(bool(restore))
        return real(client, root, restore=restore, **kwargs)

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


def test_help_is_asked_for_and_a_bare_invocation_is_the_app(capsys) -> None:
    # A bare `cadex` serves the dashboard (cli/tests/test_app.py); help is -h.
    with pytest.raises(SystemExit) as exit_:
        main(["-h"])
    assert exit_.value.code == 0 and "usage: cadex" in capsys.readouterr().out


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


def test_there_is_no_prompt_to_give(capsys) -> None:
    """ADR-538: Cadex has no agent of its own, so ``-p`` and its flags are
    refused as usage rather than quietly ignored."""

    for argv in (["-p", "a bracket"], ["--resume"], ["--model", "m"], ["walk", "--prompt", "x"]):
        with pytest.raises(SystemExit) as exit_:
            main(argv)
        assert exit_.value.code == 2, argv
        capsys.readouterr()


def test_cadex_mcp_serves_a_session_over_stdio_and_lands_its_row(engine, tmp_path) -> None:
    """The product path an agent takes (ADR-538), as a real process on real
    pipes: the guidance and the tools with no engine, a build, the engine let
    go after the idle spell with one row and one commit, and stdout holding
    nothing but the protocol."""

    import os
    import subprocess
    import sys
    import time

    root = tmp_path / "plate"
    cli_dir = Path(__file__).resolve().parents[1]
    env = {**os.environ, "PYTHONPATH": str(cli_dir) + os.pathsep + os.environ.get("PYTHONPATH", "")}
    server = subprocess.Popen(
        [sys.executable, "-m", "cadex_cli", "mcp", "--project", str(root), "--idle", "1"],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)
    sent = 0

    def rpc(method, params=None):
        nonlocal sent
        sent += 1
        server.stdin.write(json.dumps({"jsonrpc": "2.0", "id": sent, "method": method,
                                       "params": params or {}}) + "\n")
        server.stdin.flush()
        reply = json.loads(server.stdout.readline())
        assert reply["id"] == sent, reply
        return reply

    try:
        from cadex_cli.guidance import brief
        init = rpc("initialize", {"protocolVersion": "2025-06-18"})["result"]
        assert init["serverInfo"]["name"] == "cadex" and init["instructions"] == brief(str(root.resolve()))
        names = [tool["name"] for tool in rpc("tools/list")["result"]["tools"]]
        assert names[:2] == ["describe_api", "write_script"] and "leave_note" not in names
        assert not (root / "script.json").exists()  # no engine yet
        built = rpc("tools/call", {"name": "write_script", "arguments": {"source": PLATE}})["result"]
        assert built["isError"] is False, built
        payload = json.loads(built["content"][0]["text"])
        assert payload["ok"] is True
        deadline = time.monotonic() + 60
        while "| mcp |" not in (root / "PROGRESS.md").read_text() and time.monotonic() < deadline:
            time.sleep(0.2)
        progress = (root / "PROGRESS.md").read_text()
        (row,) = [line for line in progress.splitlines() if "| mcp |" in line]
        assert "mcp: write_script" in row
        # Let go: a command that needs the lock gets it without waiting.
        assert main(["revision", "list", "--project", str(root), "--json"]) == EXIT_OK
    finally:
        server.stdin.close()
        assert server.wait(timeout=120) == 0
        stray = server.stdout.read()
        server.stdout.close()
        server.stderr.close()
    assert stray == ""
    log = subprocess.run(["git", "-C", str(root), "log", "--format=%s"],
                         capture_output=True, text=True, check=True).stdout.splitlines()
    assert log[0] == "cadex mcp: write_script"
