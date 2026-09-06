# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""The project as a codebase (ADR-193): the three documents and who writes them.

The pure half needs no engine: scaffold, bounded read, the progress row, the
``DECISION:`` convention. The engine half drives ``main()`` and
``command_prompt`` for real and checks that a first visit scaffolds, an
accepted run lands a row, and a turn's decision lands an ADR entry.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from cadex_cli.__main__ import command_prompt, main
from cadex_cli.agent import CLI_OVERLAY, system_prompt
from cadex_cli.export import ExportedOutput
from cadex_cli.project_docs import (
    ARCHITECTURE_NAME,
    DECISIONS_NAME,
    PROGRESS_HEADER,
    PROGRESS_NAME,
    PROJECT_DOC_NAMES,
    append_progress_row,
    decision_lines,
    progress_numbers,
    read_project_docs,
    record_decisions,
    scaffold_project_docs,
)
from cadex_cli.report import EXIT_OK, RunReport

from mock_backend import turn_factory
from test_turn_loop import BRACKET, _args

PLATE = """
p = params(width=num(30.0, unit="mm", min=10.0, max=90.0, step=1.0))
result = {"plate": part.box(p.width, 20.0, 6.0)}
"""


# -- scaffold ------------------------------------------------------------


def test_scaffold_creates_the_three_and_never_overwrites(tmp_path) -> None:
    root = tmp_path / "actuator"
    created = scaffold_project_docs(root)

    assert created == list(PROJECT_DOC_NAMES)
    for name in PROJECT_DOC_NAMES:
        assert (root / name).is_file()
    architecture = (root / ARCHITECTURE_NAME).read_text()
    assert "# actuator — Architecture" in architecture
    assert "docs/gear-ratios.md" in architecture
    decisions = (root / DECISIONS_NAME).read_text()
    assert "## ADR-001 — Project scaffolded" in decisions
    assert PROGRESS_HEADER in (root / PROGRESS_NAME).read_text()

    # A document that exists is the project's; the scaffold leaves it alone.
    (root / ARCHITECTURE_NAME).write_text("# mine\n")
    assert scaffold_project_docs(root) == []
    assert (root / ARCHITECTURE_NAME).read_text() == "# mine\n"


def test_read_is_bounded_and_keeps_the_tail_of_progress(tmp_path) -> None:
    scaffold_project_docs(tmp_path)
    for index in range(400):
        append_progress_row(tmp_path, run="params", what=f"row {index}")
    (tmp_path / DECISIONS_NAME).write_text("# D\n" + "x" * 20_000)

    text = read_project_docs(tmp_path, limit=4_000)

    assert f"--- {ARCHITECTURE_NAME} ---" in text
    assert "row 399" in text and "row 0 |" not in text  # tail for the log
    assert "earlier characters omitted" in text
    assert "more characters omitted" in text  # head for the ADR log


def test_read_says_nothing_for_a_project_with_no_docs(tmp_path) -> None:
    assert read_project_docs(tmp_path) == ""


# -- the progress row ----------------------------------------------------


def test_a_row_is_one_line_with_escaped_pipes_and_short_hashes(tmp_path) -> None:
    row = append_progress_row(
        tmp_path,
        run="prompt",
        what="a | b\nmulti-line",
        revision="0123456789abcdef",
        digest="fedcba9876543210",
        numbers="total_reward 1729.9",
    )

    assert "\n" not in row
    assert "a \\| b multi-line" in row
    assert "| 01234567 | fedcba98 |" in row
    assert (tmp_path / PROGRESS_NAME).read_text().rstrip().endswith(row)


def test_numbers_come_from_the_trace_and_the_receipt(tmp_path) -> None:
    trace = tmp_path / "assembly-simulation-trace.json"
    trace.write_text(json.dumps({"policy": {"total_reward": 127.84}}))
    outputs = [
        ExportedOutput(name="plate", kind="brep", files={"step": "x.step"}),
        ExportedOutput(name="run", kind="json", files={"json": str(trace)}),
    ]
    training = {"reward_per_step": 1.5234, "wall_time_s": 17.8, "sha256": "4f2d62b1ff"}

    assert progress_numbers(training=training, outputs=outputs) == (
        "total_reward 127.8, reward/step 1.523, 17.8 s, sha256 4f2d62b1"
    )
    assert progress_numbers(training={}, outputs=outputs[:1]) == ""


# -- the DECISION: convention --------------------------------------------


def test_decision_lines_are_found_and_land_as_numbered_entries(tmp_path) -> None:
    text = (
        "Built the bracket.\n"
        "- DECISION: two-stage reduction. One stage needed a 90 mm gear.\n"
        "decision: keep the bore at 6 mm\n"
        "Not a decision.\n"
    )
    assert decision_lines(text) == [
        "two-stage reduction. One stage needed a 90 mm gear.",
        "keep the bore at 6 mm",
    ]

    assert record_decisions(tmp_path, text) == ["ADR-002", "ADR-003"]
    decisions = (tmp_path / DECISIONS_NAME).read_text()
    assert "## ADR-001 — Project scaffolded" in decisions
    assert "## ADR-002 — two-stage reduction (" in decisions
    assert "## ADR-003 — keep the bore at 6 mm (" in decisions
    assert record_decisions(tmp_path, "nothing decided") == []
    assert record_decisions(tmp_path, "DECISION: one more") == ["ADR-004"]


def test_the_overlay_names_the_convention_and_the_prompt_carries_the_docs() -> None:
    assert "ARCHITECTURE.md" in CLI_OVERLAY
    assert "DECISION:" in CLI_OVERLAY
    assert "docs/gear-ratios.md" in CLI_OVERLAY
    api = {"program_schema": "cadex-xscript-project-v9"}
    with_docs = system_prompt(api, project_docs="--- PROGRESS.md ---\n| row |")
    assert "THIS PROJECT'S OWN DOCS" in with_docs
    assert "| row |" in with_docs
    assert with_docs.index("| row |") < with_docs.index("cadex-xscript-project-v9")
    assert "THIS PROJECT'S OWN DOCS" not in system_prompt(api)


# -- with the engine -----------------------------------------------------


def _run(capsys, *argv: str) -> tuple[int, dict]:
    code = main([*argv, "--json"])
    return code, json.loads(capsys.readouterr().out)


@pytest.mark.usefixtures("engine")
def test_a_first_visit_scaffolds_and_an_accepted_run_lands_a_row(
    tmp_path, capsys
) -> None:
    source = tmp_path / "plate.py"
    source.write_text(PLATE, encoding="utf-8")
    root = tmp_path / "project"

    code, envelope = _run(
        capsys, "script", "--set", str(source), "--project", str(root)
    )
    assert code == EXIT_OK, envelope
    assert any(note.startswith("scaffolded ") for note in envelope["notes"])
    for name in PROJECT_DOC_NAMES:
        assert (root / name).is_file()
    progress = (root / PROGRESS_NAME).read_text()
    (row,) = [line for line in progress.splitlines() if "| script |" in line]
    assert "script --set plate.py" in row
    assert envelope["accepted_revision"][:8] in row
    assert envelope["digest"][:8] in row

    # A second visit scaffolds nothing and appends one more row.
    code, envelope = _run(
        capsys, "params", "--set", "width=40", "--project", str(root)
    )
    assert code == EXIT_OK, envelope
    assert not any(
        note.startswith("scaffolded ") for note in envelope.get("notes", [])
    )
    rows = [
        line for line in (root / PROGRESS_NAME).read_text().splitlines()
        if line.startswith("| 20")
    ]
    assert len(rows) == 2
    assert "params width=40" in rows[-1]

    # Printing the script is a read, not a run: no row.
    assert main(["script", "--project", str(root)]) == EXIT_OK
    capsys.readouterr()
    assert len(
        [l for l in (root / PROGRESS_NAME).read_text().splitlines() if l.startswith("| 20")]
    ) == 2


@pytest.mark.usefixtures("engine")
def test_a_turn_reads_the_docs_and_its_decision_lands(tmp_path) -> None:
    root = Path(_args(tmp_path).project)
    scaffold_project_docs(root)
    (root / ARCHITECTURE_NAME).write_text(
        "# project — Architecture\n\nA plate for the sensor mount.\n"
    )
    factory = turn_factory(
        [
            [
                ("tool", "describe_api", {}),
                ("tool", "write_script", {"source": BRACKET}),
                ("done", "Built a 30 mm plate.\nDECISION: width is the one parameter."),
            ]
        ]
    )
    report = RunReport()

    code = command_prompt(_args(tmp_path), report, turn_factory=factory)

    assert code == EXIT_OK, report.error
    turn = factory.made[0]
    assert "THIS PROJECT'S OWN DOCS" in turn.system_prompt_text
    assert "A plate for the sensor mount." in turn.system_prompt_text
    decisions = (root / DECISIONS_NAME).read_text()
    assert "## ADR-002 — width is the one parameter (" in decisions
    assert "recorded ADR-002 in DECISIONS.md." in report.notes
