# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""The project as a codebase (ADR-193): the three documents and who writes them.

The pure half needs no engine: scaffold, bounded read, the progress row, the
``DECISION:`` convention. The engine half drives ``main()`` and
``command_prompt`` for real and checks that a first visit scaffolds, an
accepted run lands a row, and a turn's decision lands an ADR entry.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path

import pytest

from cadex_cli.__main__ import _progress_what, command_prompt, main
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
    documentation_status,
    note_lines,
    progress_numbers,
    read_project_docs,
    record_decisions,
    record_notes,
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
    # The convention reaches both a fresh project's docs and its design agent.
    for guidance in (architecture, CLI_OVERLAY):
        normalized = " ".join(guidance.split())
        for fact in (
            "publish each catalog body", "separate assembly components",
            "`assembly.component`", "separate from printed solids",
            "Transformed catalog bodies may also be clearance cutters",
            "a cutter does not imply another purchased part",
            "Review the script alongside placed inventory",
            "cannot identify hardware fused into other solids",
        ):
            assert fact in normalized
    decisions = (root / DECISIONS_NAME).read_text()
    assert "## ADR-001 — Project scaffolded" in decisions
    assert PROGRESS_HEADER in (root / PROGRESS_NAME).read_text()

    # A document that exists is the project's; the scaffold leaves it alone.
    (root / ARCHITECTURE_NAME).write_text("# mine\n")
    assert scaffold_project_docs(root) == []
    assert (root / ARCHITECTURE_NAME).read_text() == "# mine\n"


def test_the_scaffold_states_the_training_mode_and_the_walk_doc_agrees(tmp_path) -> None:
    """ADR-200's three facts reach the project's own docs: which mode trains
    (the venv here, or ``--remote`` on the box), that the artifacts land at
    the same project-relative paths either way, and — since ADR-268 — that a
    warm start travels with the bundle rather than pinning an iterate to
    this machine. The walk's doc and the scaffold are one ticket:
    `docs/CLI.md` must say the scaffold carries the section, so neither
    moves alone."""

    scaffold_project_docs(tmp_path)
    architecture = (tmp_path / ARCHITECTURE_NAME).read_text()
    assert "## Training" in architecture
    for fact in (
        "`cadex train --remote`",
        "training/remote_train.sh",
        "same project-relative paths in both modes",
        "runs/<name>/train/",
        "runs/<name>/review.json",
        "A warm start travels",
        "`--init-from`",
        "(remote)",
    ):
        assert fact in architecture, fact

    walk_doc = (Path(__file__).resolve().parents[2] / "docs" / "CLI.md").read_text()
    assert "`ARCHITECTURE.md` scaffold carries a `## Training` section" in walk_doc
    assert "A warm start travels" in walk_doc
    assert "shared mode artifacts table in `docs/CLI.md`" in architecture
    assert "**Shared mode artifacts**" in walk_doc
    assert "review/section/<accepted-revision>/XZ-<derived-offset>/" in architecture
    assert "Empty cuts" in architecture and "unsupported cuts" in architecture
    for path in ("runs/<name>/train/", "runs/<name>/rollout/",
                 "runs/<name>/review.json", "assets/<name>.cxpolicy", "PROGRESS.md",
                 "review/section/<accepted-revision>/XZ-<derived-offset>/"):
        assert path in walk_doc.split("**Shared mode artifacts**", 1)[1].split(
            "A leg that fails", 1)[0]


def test_the_gui_attached_mode_is_retired_in_the_scaffold_and_the_walk_doc(tmp_path) -> None:
    """ADR-201's GUI-attached walk -- the same commands from a terminal
    beside an open Blender file -- retired with the shell (ADR-495). The
    scaffold a new project receives must not tell it to Rebuild Model or
    reopen a window that no longer exists, and the walk's doc says the mode
    is gone and what replaced it, so neither can drift back alone."""

    scaffold_project_docs(tmp_path)
    architecture = (tmp_path / ARCHITECTURE_NAME).read_text()
    for stale in ("With the GUI attached", "beside the open file",
                  "Rebuild Model", "GUI edit", "the shell's own agent"):
        assert stale not in architecture, stale
    assert "so an iterate has the same shape in either mode." in architecture

    walk_doc = (Path(__file__).resolve().parents[2] / "docs" / "CLI.md").read_text()
    flat = " ".join(walk_doc.split())  # the doc wraps; the sentences do not
    assert "**There is no GUI-attached mode any more** (ADR-495)." in flat
    assert "The review dashboard (`cadex review`, below) is the UI" in flat
    for stale in ("**With the GUI attached", "| Leg | The child command |",
                  "**The shell takes no lock.**", "Rebuild Model or reopen"):
        assert stale not in flat, stale


def test_no_cli_module_reaches_into_the_shell_tree() -> None:
    """The disable commit's contract on this side (ADR-495): nothing the CLI
    or the dashboard runs reads a path under ``shell/`` or imports
    ``mesh_agent``. The tree is deleted (ADR-498); this keeps a revival
    from being wired back in through the front end."""

    package = Path(__file__).resolve().parents[1] / "cadex_cli"
    reaching = []
    for source in sorted(package.rglob("*")):
        if source.suffix not in {".py", ".js", ".html"}:
            continue
        text = source.read_text(encoding="utf-8")
        if re.search(r"""["'/]shell/|/\s*["']shell["']|\bmesh_agent\b|CADEX_BLENDER_EXECUTABLE""", text):
            reaching.append(source.name)
    assert reaching == [], reaching


#: Markdown that may name the deleted shell's paths, and why (ADR-498).
#: Everything else tracked is a live doc and describes the product as it is.
SHELL_HISTORY_DOCS = (
    "docs/DECISIONS.md",       # the ADR log: decisions keep their own words
    "docs/history/",           # superseded docs, by definition
    "docs/probes/",            # frozen run evidence, measured when it was true
    "docs/SHELL-PARITY.md",    # the ledger of the shell, module by module
    "docs/ROADMAP.md",         # phase history; the charter forbids hand edits
    "STATE.md",                # generated from the state graph
    ".hypergraph/",            # the append-only record
    ".ouroboros/",             # run logs
)
SHELL_TOKEN = re.compile(
    r"(?<![\w.-])shell/|\bmesh_agent\b|(?<![\w-])\.blend\b|CADEX_BLENDER_EXECUTABLE")


def test_no_live_doc_names_the_deleted_shell() -> None:
    """Charter S1 (ADR-498): no live doc refers to ``shell/``,
    ``mesh_agent``, a ``.blend`` or ``CADEX_BLENDER_EXECUTABLE``. A doc that
    must tell the shell's history says "the shell" in words; only the
    history kept in :data:`SHELL_HISTORY_DOCS` may name its paths."""

    root = Path(__file__).resolve().parents[2]
    listing = subprocess.run(
        ["git", "ls-files", "-z", "--", "*.md"], cwd=root,
        capture_output=True, text=True, check=False)
    if listing.returncode != 0:
        pytest.skip("not a git checkout")
    docs = [name for name in listing.stdout.split("\0") if name]
    assert "SECURITY.md" in docs and "docs/ARCHITECTURE.md" in docs
    naming = []
    for name in docs:
        if name.startswith(SHELL_HISTORY_DOCS):
            continue
        path = root / name
        if not path.is_file():
            continue
        for number, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            if SHELL_TOKEN.search(line):
                naming.append(f"{name}:{number}")
    assert naming == [], naming


def test_agents_md_describes_the_three_part_product() -> None:
    """ADR-500 (charter R1): the agent contract describes the engine, the
    dashboard and the agent, at no more than half the 432 lines it had when
    orun2 began, and no longer offers a Rust shell as the target."""

    root = Path(__file__).resolve().parents[2]
    text = (root / "AGENTS.md").read_text(encoding="utf-8")
    assert len(text.splitlines()) <= 216, len(text.splitlines())
    flat = " ".join(text.split())
    for part in ("1. **The engine**", "2. **The dashboard**", "3. **The agent**"):
        assert part in flat, part
    vision = " ".join((root / "docs" / "VISION.md").read_text(encoding="utf-8").split())
    for text in (flat, vision):
        assert "wgpu" not in text and "egui" not in text
        assert "Blender-class UX" not in text


def test_claude_code_is_the_only_harness() -> None:
    """ADR-497 (charter A4): the Codex and pi backends went with the shell.
    No CLI module names either harness, and the agent contract says Claude
    Code is the only one rather than offering the other two as a preference."""

    root = Path(__file__).resolve().parents[2]
    package = root / "cli" / "cadex_cli"
    naming = []
    for source in sorted(package.rglob("*")):
        if source.suffix not in {".py", ".js", ".html"}:
            continue
        text = source.read_text(encoding="utf-8")
        if re.search(r"\bcodex\b|\bpi_tools\b|\bPiBackend\b|registerTool", text, re.IGNORECASE):
            naming.append(source.name)
    assert naming == [], naming

    agents = " ".join((root / "AGENTS.md").read_text(encoding="utf-8").split())
    vision = " ".join((root / "docs" / "VISION.md").read_text(encoding="utf-8").split())
    assert "**Claude Code is the only harness** (ADR-497)" in agents
    assert "the only harness (ADR-497" in vision
    for text in (agents, vision):
        assert "OpenAI Codex CLI" not in text
        assert "Claude Code, Codex, or pi" not in text


def test_a_train_row_names_the_mode_it_ran_in() -> None:
    """`PROGRESS.md`'s What column says `(remote)` for a run on the box and
    nothing extra for the venv, so the rows the scaffold promises are
    comparable also say where each number came from."""

    report = RunReport(training={"out": "/p/runs/r/train/r.cxpolicy"})
    local = _progress_what(
        "train", argparse.Namespace(iterations=2, envs=4, out="x", put=True, remote=False), report
    )
    remote = _progress_what(
        "train", argparse.Namespace(iterations=2, envs=4, out="x", put=True, remote=True), report
    )
    assert local == "train 2 it × 4 envs → r.cxpolicy (stored)"
    assert remote == local + " (remote)"


@pytest.mark.parametrize("limit", [4_000, 8_000])
def test_read_keeps_architecture_head_and_recent_history_without_editing(tmp_path, limit) -> None:
    scaffold_project_docs(tmp_path)
    sources = {name: f"old {name}\n" + "x" * 20_000 + f"\nnew {name}"
               for name in PROJECT_DOC_NAMES}
    sources["docs/sensors.md"] = "old sensor\n" + "y" * 3_000 + "\nnew sensor"
    (tmp_path / "docs").mkdir(exist_ok=True)
    for name, source in sources.items():
        (tmp_path / name).write_text(source, encoding="utf-8")

    text = read_project_docs(tmp_path, limit=limit)

    for name, source in sources.items():
        ends = name == ARCHITECTURE_NAME
        bound = 2_000 if name.startswith("docs/") else limit
        omitted = len(source) - bound
        if ends:
            head = bound // 2
            expected = (source[:head]
                        + f"\n[… {omitted} characters omitted …]\n"
                        + source[-(bound - head):])
        else:
            expected = (f"[… {omitted} earlier characters omitted …]\n"
                        + source[-bound:])
        assert f"--- {name} ---\n{expected}" in text
        assert (tmp_path / name).read_bytes() == source.encode("utf-8")


def test_a_scaffold_that_outgrows_the_budget_still_shows_the_project_s_own_lines(
    tmp_path,
) -> None:
    """The guide at the top must never evict what the project wrote below it.

    The architecture scaffold is boilerplate that grows every time the walk
    contract does; the project's own paragraphs are appended under it. Head-
    bounding meant that the moment the scaffold passed the budget — which it
    did at ADR-277, at 8,191 characters — every project's own architecture
    silently stopped reaching the agent's prompt (ADR-279). The check is made
    against the real scaffold rather than a synthetic string so that a future
    guide line cannot break it back without failing here.
    """

    scaffold_project_docs(tmp_path)
    architecture = tmp_path / ARCHITECTURE_NAME
    scaffold = architecture.read_text(encoding="utf-8")
    own = "\n## Own\n\nThe hinge pin is 3 mm; the cable exit stays clear.\n"
    architecture.write_text(scaffold + own, encoding="utf-8")
    # Force the eviction the old bounding suffered even on a short scaffold.
    limit = len(scaffold) - 500

    text = read_project_docs(tmp_path, limit=limit)

    assert "The hinge pin is 3 mm; the cable exit stays clear." in text
    assert scaffold.strip().splitlines()[0] in text  # ...and the guide's head
    assert "characters omitted" in text


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


def test_note_lines_land_one_file_per_subject_and_come_back_next_visit(tmp_path) -> None:
    """A design turn's longer notes reach `docs/` (ADR-245).

    The convention was documented and unreachable: the agent has no file
    tool, and a headless walk has no caller to ask. A closing `NOTE
    <subject>:` line lands the same way a `DECISION:` line does.
    """

    text = (
        "Built the leg.\n"
        "- NOTE actuators: MG90S at 1.8 kg-cm stall; damping = stall / no-load.\n"
        "note Gear Ratios: 4:1, in two stages.\n"
        "NOTE clearance: the review's own report is not a note subject.\n"
        "NOTE: no subject here.\n"
        "NOTE sensors:\n"
        "Nothing to note.\n"
    )
    assert note_lines(text) == [
        ("actuators", "MG90S at 1.8 kg-cm stall; damping = stall / no-load."),
        ("gear-ratios", "4:1, in two stages."),
    ]

    assert record_notes(tmp_path, text) == ["docs/actuators.md", "docs/gear-ratios.md"]
    actuators = (tmp_path / "docs" / "actuators.md").read_text()
    assert actuators.startswith("# actuators\n")
    assert "- (" in actuators and "MG90S at 1.8 kg-cm stall" in actuators
    assert not (tmp_path / "docs" / "clearance.md").exists()

    # A second note on the same subject appends; the first survives.
    assert record_notes(tmp_path, "NOTE actuators: the knee stalls at 40 deg.") == [
        "docs/actuators.md"
    ]
    actuators = (tmp_path / "docs" / "actuators.md").read_text()
    assert "MG90S at 1.8 kg-cm stall" in actuators
    assert "the knee stalls at 40 deg." in actuators
    assert record_notes(tmp_path, "nothing noted") == []

    # ...and the next turn reads them back beside the three documents,
    # while the CLI's own generated reports stay out of the prompt.
    scaffold_project_docs(tmp_path)
    (tmp_path / "docs" / "clearance.md").write_text("| pair | mm |\n", encoding="utf-8")
    prompt_docs = read_project_docs(tmp_path)
    assert "--- docs/actuators.md ---" in prompt_docs
    assert "--- docs/gear-ratios.md ---" in prompt_docs
    assert "--- docs/clearance.md ---" not in prompt_docs
    assert "| pair | mm |" not in prompt_docs
    assert "the knee stalls at 40 deg." in prompt_docs


def test_documentation_status_names_the_subjects_a_project_has_no_note_for(
    tmp_path,
) -> None:
    """The convention is checked, not only offered (ADR-256).

    A walk hands in what the model declares; the status says which of
    those subjects the project documents and which it does not. The
    generated reports never count as a note, and a project with nothing
    declared has nothing missing.
    """

    assert documentation_status(tmp_path) == {
        "notes": [], "expected": [], "missing": []
    }
    assert documentation_status(tmp_path, ["actuators", "sensors"])["missing"] == [
        "actuators", "sensors"
    ]

    record_notes(tmp_path, "NOTE sensors: the hinge angle, in degrees.")
    (tmp_path / "docs" / "clearance.md").write_text("| pair | mm |\n", encoding="utf-8")
    status = documentation_status(tmp_path, ["actuators", "sensors", "sensors", ""])
    assert status["notes"] == ["docs/sensors.md"]
    assert status["expected"] == ["actuators", "sensors"]
    assert status["missing"] == ["actuators"]
    assert documentation_status(tmp_path, ["sensors"])["missing"] == []

    # ...and the guide says which declaration asks for which note.
    walk_doc = " ".join(
        (Path(__file__).resolve().parents[2] / "docs" / "CLI.md").read_text().split()
    )
    assert (
        "an `<actuator>` section with children asks the project for "
        "`docs/actuators.md`" in walk_doc
    )


def test_the_scaffold_and_the_overlay_ask_for_the_notes_the_walk_exercises(tmp_path) -> None:
    """The convention is asked for, not only described (ADR-245).

    `docs/CLI.md`, the `ARCHITECTURE.md` scaffold and the design
    instruction are one ticket: a mechanism with actuators or sensors
    leaves those two notes behind, and the generated reports are not
    note subjects.
    """

    assert "NOTE actuators:" in CLI_OVERLAY
    assert "NOTE sensors:" in CLI_OVERLAY
    assert "docs/inventory.md and docs/clearance.md are the CLI's own reports" in (
        " ".join(CLI_OVERLAY.split())
    )

    scaffold_project_docs(tmp_path)
    architecture = " ".join((tmp_path / ARCHITECTURE_NAME).read_text().split())
    assert "NOTE <subject>: <text>" in architecture
    assert "actuators.md" in architecture and "sensors.md" in architecture

    # ...and it says the walk reads the convention back (ADR-256): which
    # declaration asks for which note, where the finding lands, and that a
    # missing note neither fails the run nor gets written by the CLI.
    assert (
        "an `<actuator>` section with children asks this project for "
        "`docs/actuators.md`, a `<sensor>` section for `docs/sensors.md`"
    ) in architecture
    assert "The `documentation` block in `review.json` and the `PROGRESS.md` row" in (
        architecture
    )
    assert "`docs notes N, none missing` or `docs notes N, no <subjects>`" in architecture
    assert (
        "never a walk failure, and the CLI never writes the note itself" in architecture
    )

    walk_doc = " ".join(
        (Path(__file__).resolve().parents[2] / "docs" / "CLI.md").read_text().split()
    )
    assert "a closing line `NOTE <subject>: <text>` becomes a dated bullet" in walk_doc
    assert "a turn's closing `NOTE <subject>:` lines, or a person" in walk_doc


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

    # ...and the project owns a repository with one commit per accepted run
    # (ADR-194): the row is in its commit, the artifacts are not tracked.
    assert (root / ".git").is_dir()
    assert "committed " + _git(root, "rev-parse", "--short", "HEAD") + "." in envelope["notes"]
    assert _git(root, "log", "--format=%s").splitlines() == [
        "cadex params width=40",
        "cadex script --set plate.py",
    ]
    assert _git(root, "status", "--porcelain") == ""
    tracked = _git(root, "ls-files").splitlines()
    assert PROGRESS_NAME in tracked and "script.py" in tracked
    assert not any(name.startswith("script_artifacts/") for name in tracked)

    # Printing the script is a read, not a run: no row, no commit. (Opening
    # the project re-stages the accepted attempt under a new id, so the
    # engine's script.json is dirty until the next accepted run commits it.)
    assert main(["script", "--project", str(root)]) == EXIT_OK
    capsys.readouterr()
    assert len(
        [l for l in (root / PROGRESS_NAME).read_text().splitlines() if l.startswith("| 20")]
    ) == 2
    assert len(_git(root, "log", "--format=%h").splitlines()) == 2
    assert _git(root, "status", "--porcelain") in ("", "M script.json")


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


# -- the comparison as one row, and the repository (ADR-194) --------------


def test_a_number_a_previous_row_carried_is_written_with_its_change(tmp_path) -> None:
    from cadex_cli.project_docs import previous_numbers

    root = tmp_path / "project"
    assert previous_numbers(root) == {}
    trace = tmp_path / "assembly-simulation-trace.json"

    def exported(reward: float) -> list[ExportedOutput]:
        trace.write_text(json.dumps({"policy": {"total_reward": reward}}))
        return [ExportedOutput(name="sim", kind="trace", files={"json": str(trace)})]

    # The first row has nothing to compare against.
    numbers = progress_numbers(
        training={"reward_per_step": 5.24, "wall_time_s": 22.5, "sha256": "ab" * 32},
        outputs=exported(1729.95),
        previous=previous_numbers(root),
    )
    assert numbers == "total_reward 1730.0, reward/step 5.24, 22.5 s, sha256 abababab"
    append_progress_row(root, run="params", what="policy_on=1", digest="2996fb73" + "0" * 56, numbers=numbers)
    assert previous_numbers(root) == {
        "total_reward": (1730.0, "2996fb73"),
        "reward/step": (5.24, "2996fb73"),
    }

    # The next row carries the change against that row, per number, and a
    # row without a number leaves the last one that had it in force.
    append_progress_row(root, run="export", what="export → out", digest="deadbeef" * 8)
    numbers = progress_numbers(
        training={"reward_per_step": 1.52},
        outputs=exported(127.8),
        previous=previous_numbers(root),
    )
    assert numbers == (
        "total_reward 127.8 (Δ -1602.2 vs 2996fb73 at 1730.0), "
        "reward/step 1.52 (Δ -3.72 vs 2996fb73 at 5.24)"
    )
    row = append_progress_row(root, run="params", what="policy_on=1", digest="369a0dd5" + "1" * 56, numbers=numbers)
    assert "(Δ -1602.2 vs 2996fb73 at 1730.0)" in row
    # ...and the delta text is not mistaken for the row's own value next time.
    assert previous_numbers(root)["total_reward"] == (127.8, "369a0dd5")
    assert previous_numbers(root)["reward/step"] == (1.52, "369a0dd5")


def test_a_walk_row_s_travel_reads_back_off_the_row_on_both_channels(tmp_path) -> None:
    """The unit is in the label, so the figure survives the round trip.

    `motion 103.3 mm` cannot be read back — `_NUMBER_RE` wants
    `<label> <number>` — so before ADR-260 a walk's travel could be
    written and never compared. Four significant figures, not one
    decimal: a rig that moved 0.0004 mm did not stand still.
    """

    from cadex_cli.project_docs import compared_number, previous_numbers

    root = tmp_path / "project"
    first = "; motion {:s} on carriage, {:s} on carriage over 61 solved frame(s)".format(
        compared_number("travel_mm", 103.298, {}),
        compared_number("travel_deg", 0.0, {}),
    )
    assert first.startswith("; motion travel_mm 103.3 on carriage, travel_deg 0 on")
    append_progress_row(root, run="walk", what="walk 5 it × 16 envs → runs/walk-1",
                        digest="4b0a1c2d" + "0" * 56, numbers="clearance unavailable" + first)
    assert previous_numbers(root) == {
        "travel_mm": (103.3, "4b0a1c2d"), "travel_deg": (0.0, "4b0a1c2d")}

    # The iterate walk: the travel held while (elsewhere on the row's own
    # train leg) the reward fell. The row says the first half; it makes no
    # claim about which of the two mattered.
    previous = previous_numbers(root)
    second = compared_number("travel_mm", 103.719, previous)
    assert second == "travel_mm 103.7 (Δ +0.419 vs 4b0a1c2d at 103.3)"
    assert compared_number("travel_deg", 0.0, previous) == (
        "travel_deg 0 (Δ ±0 vs 4b0a1c2d at 0)")
    append_progress_row(root, run="walk", what="walk 5 it × 16 envs → runs/walk-2",
                        digest="9e10f3a4" + "0" * 56, numbers="clearance unavailable; motion "
                        + second + " on carriage over 61 solved frame(s)")
    # The delta text is not mistaken for the next row's own value.
    assert previous_numbers(root)["travel_mm"] == (103.7, "9e10f3a4")


def test_a_walk_row_s_clearance_finding_count_carries_its_delta(tmp_path) -> None:
    """The number an iterate turns, said as a change (ADR-271).

    A walk that answers a clearance finding writes `clearance offending
    0`, which alone is indistinguishable from a rig that never had one.
    The label was always in front of the count, so every row already
    written reads back and the very first row of the new spelling carries
    a real delta.
    """

    from cadex_cli.project_docs import compared_number, previous_numbers

    root = tmp_path / "project"
    # A row in the old spelling: no delta text, and never re-written.
    append_progress_row(
        root, run="walk", what="walk 5 it × 16 envs → runs/before",
        digest="f08ff7ef" + "0" * 56,
        numbers="clearance offending 1; unknown 0; pairs checked 1 "
                "(initial solved pose; 0.1 mm / 1e-06 mm³)",
    )
    assert previous_numbers(root)["clearance offending"] == (1.0, "f08ff7ef")

    previous = previous_numbers(root)
    answered = compared_number("clearance offending", 0.0, previous)
    assert answered == "clearance offending 0 (Δ -1 vs f08ff7ef at 1)"
    append_progress_row(
        root, run="walk", what="walk 5 it × 16 envs → runs/after",
        digest="ef8662ad" + "0" * 56,
        numbers=answered + "; unknown 0; pairs checked 1 "
                "(initial solved pose; 0.1 mm / 1e-06 mm³)",
    )
    # The delta text is not mistaken for the next row's own value, and a
    # walk that finds nothing twice running says so rather than going
    # quiet.
    assert previous_numbers(root)["clearance offending"] == (0.0, "ef8662ad")
    assert compared_number("clearance offending", 0.0, previous_numbers(root)) == (
        "clearance offending 0 (Δ ±0 vs ef8662ad at 0)")


def _git(root: Path, *argv: str) -> str:
    import subprocess

    return subprocess.run(
        ["git", "-C", str(root), *argv], capture_output=True, text=True, check=True
    ).stdout.strip()


@pytest.mark.parametrize("location", ["inside", "outside", "relative", "home"])
def test_walk_records_portable_output_in_row_and_commit(tmp_path, monkeypatch, location) -> None:
    from cadex_cli.__main__ import _commit_run, _record_progress
    from cadex_cli.project_docs import ensure_project_repo

    root = tmp_path / "project"
    scaffold_project_docs(root)
    ensure_project_repo(root)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("HOME", str(tmp_path))
    out = {
        "inside": str(root / "runs" / "repair-2"),
        "outside": str(tmp_path / "external" / "repair-2"),
        "relative": "project/runs/repair-2",
        "home": "~/project/runs/repair-2",
    }[location]
    label = "repair-2" if location == "outside" else "runs/repair-2"
    args = argparse.Namespace(iterations=1, envs=4, out=out)
    report = RunReport(
        project_root=str(root), accepted_revision="r2", digest="a" * 64,
        walk={"review": {"clearance": {"available": False}}},
    )
    _record_progress("walk", args, report)
    _commit_run("walk", args, report)

    progress = _git(root, "show", "HEAD:PROGRESS.md")
    subject = _git(root, "log", "-1", "--format=%s")
    what = f"walk 1 it × 4 envs → {label}"
    assert what in progress
    assert subject == f"cadex {what}"
    assert str(tmp_path) not in progress + subject
    assert _git(root, "status", "--porcelain") == ""


def test_the_project_owns_a_repository_and_a_run_is_a_commit(tmp_path) -> None:
    from cadex_cli.project_docs import GITIGNORE_NAME, commit_project, ensure_project_repo

    root = tmp_path / "project"
    scaffold_project_docs(root)
    (root / "script_artifacts" / "r1").mkdir(parents=True)
    (root / "script_artifacts" / "r1" / "big.brep").write_text("x" * 100)
    (root / ".cadex-cli.lock").write_text("1\n")
    (root / "assets").mkdir()
    (root / "assets" / "walk.cxpolicy").write_bytes(b"\x00" * 16)

    assert ensure_project_repo(root) == "initialised a git repository in the project root."
    assert (root / ".git").is_dir()
    assert (root / GITIGNORE_NAME).is_file()
    assert ensure_project_repo(root) == ""  # idempotent, and silent the second time

    sha = commit_project(root, "cadex script --set plate.py")
    assert sha and _git(root, "rev-parse", "--short", "HEAD") == sha
    assert _git(root, "log", "--format=%s") == "cadex script --set plate.py"
    tracked = _git(root, "ls-files").splitlines()
    assert set(tracked) == {
        GITIGNORE_NAME, "ARCHITECTURE.md", "DECISIONS.md", "PROGRESS.md", "assets/walk.cxpolicy"
    }
    assert _git(root, "status", "--porcelain") == ""

    # Nothing changed: nothing to commit, no error.
    assert commit_project(root, "again") == ""
    # A change is one more commit.
    append_progress_row(root, run="params", what="width=40")
    assert commit_project(root, "cadex params width=40")
    assert len(_git(root, "log", "--format=%h").splitlines()) == 2


def test_a_project_inside_another_work_tree_is_left_alone(tmp_path) -> None:
    from cadex_cli.project_docs import commit_project, ensure_project_repo

    _git(tmp_path, "init", "-q")
    root = tmp_path / "nested"
    scaffold_project_docs(root)

    note = ensure_project_repo(root)

    assert note.startswith("inside an existing git work tree")
    assert not (root / ".git").exists()
    assert commit_project(root, "never") == ""
    assert _git(tmp_path, "status", "--porcelain")  # untouched: still unstaged


def test_walk_retention_uses_git_precedence_and_preserves_history(tmp_path) -> None:
    from cadex_cli.project_docs import commit_project, ensure_project_repo

    root = tmp_path / "project"
    scaffold_project_docs(root)
    ensure_project_repo(root)
    (root / "assets").mkdir()
    (root / "assets/old.cxpolicy").write_text("original")
    assert commit_project(root, "baseline")
    baseline = _git(root, "rev-parse", "HEAD")

    # Quill's root negation outranks its local policy exclusion.
    with (root / ".git/info/exclude").open("a") as stream:
        stream.write("\n/runs/iterate/\n/assets/new.cxpolicy\n")
    policy = root / "assets/new.cxpolicy"
    policy.write_text("new weights")
    assert "!assets/*.cxpolicy" in _git(root, "check-ignore", "-v", str(policy))
    # Explicit overrides belong AFTER that negation in the root ignore file.
    with (root / ".gitignore").open("a") as stream:
        stream.write("\n/assets/new.cxpolicy\n/assets/old.cxpolicy\n")
    generated = ["runs/iterate/train/new.cxpolicy", "runs/iterate/review.json",
                 "review/render/revision/front.svg", "review/section/revision/summary.json"]
    for name in generated:
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("generated")
    (root / "PROGRESS.md").write_text("measured results")
    (root / "docs").mkdir()
    (root / "docs/sensors.md").write_text("sensor rationale")
    (root / "script.py").write_text("# authoritative source")
    (root / "assets/default.cxpolicy").write_text("retained by default")
    # Ignores neither untrack files nor undo explicit user staging.
    (root / "assets/old.cxpolicy").write_text("updated")
    staged = root / "runs/iterate/user-note.txt"
    staged.write_text("staged")
    _git(root, "add", "-f", str(staged))
    staged.write_text("working version")
    assert commit_project(root, "walk train")
    assert commit_project(root, "walk review") == ""
    tree = set(_git(root, "ls-tree", "-r", "--name-only", "HEAD").splitlines())
    assert not (set(generated) | {"assets/new.cxpolicy"}) & tree
    assert {"script.py", "PROGRESS.md", "docs/sensors.md", "assets/default.cxpolicy",
            "assets/old.cxpolicy", "runs/iterate/user-note.txt"} <= tree
    assert _git(root, "show", "HEAD:PROGRESS.md") == "measured results"
    assert _git(root, "show", "HEAD:assets/old.cxpolicy") == "updated"
    assert _git(root, "show", "HEAD:runs/iterate/user-note.txt") == "working version"
    assert _git(root, "show", baseline + ":assets/old.cxpolicy") == "original"
    assert all((root / name).is_file() for name in generated)
    assert policy.read_text() == "new weights"


def test_objective_evidence_ignores_seeds_and_model_but_names_action_changes(tmp_path):
    from cadex_cli.project_docs import task_comparison, comparison_cell, append_progress_row
    import json
    task = {"schema": "task-v1", "observations": [{"unit": "mm"}],
            "reward": [{"expression": "height", "weight": 1}], "termination": [],
            "episode": {"max_steps": 200}, "functions": ["abs"],
            "actions": [{"low": 0, "high": 40, "unit": "mm"}],
            "model": {"sha256": "old"}}
    path = tmp_path / "task.json"
    def evidence(seed):
        path.write_text(json.dumps(task))
        return {**task_comparison(path), "training_seed": seed, "rollout_seed": 7}
    first = evidence(0)
    task["model"]["sha256"] = "new"
    second = evidence(5)
    assert first["objective_id"] == second["objective_id"]
    task["actions"][0]["high"] = 60
    third = evidence(5)
    assert third["objective_id"] == first["objective_id"]
    assert third["actions_id"] != first["actions_id"]
    task["reward"][0]["weight"] = 2
    assert evidence(5)["objective_id"] != first["objective_id"]
    append_progress_row(tmp_path, run="walk", what="legacy", numbers="travel_mm 1")
    cell = comparison_cell(tmp_path, "walk", first)
    assert "training_seed 0; rollout_seed 7" in cell
    assert "unavailable (legacy row)" in cell
    append_progress_row(tmp_path, run="walk", what="new", numbers=cell)
    later = comparison_cell(tmp_path, "walk", second)
    assert "training_seed 5; rollout_seed 7" in later
    assert "previous evidence: objective " + first["objective_id"] in later
    assert "training_seed 0; rollout_seed 7" in later
    path.write_text('{}')
    assert task_comparison(path)["objective_id"] is None


@pytest.mark.parametrize("kind", ["progress", "decision", "note"])
@pytest.mark.parametrize("failure", ["write", "replace"])
def test_failed_document_write_preserves_history_and_retry(
    tmp_path, monkeypatch, kind, failure
):
    scaffold_project_docs(tmp_path)
    record_notes(tmp_path, "NOTE sensors: original sensor rationale")
    path, update = {
        "progress": (tmp_path / PROGRESS_NAME,
                     lambda: append_progress_row(tmp_path, run="walk", what="new result")),
        "decision": (tmp_path / DECISIONS_NAME,
                     lambda: record_decisions(tmp_path, "DECISION: new result")),
        "note": (tmp_path / "docs/sensors.md",
                 lambda: record_notes(tmp_path, "NOTE sensors: new result")),
    }[kind]
    path.chmod(0o640)
    original = path.read_bytes()
    files = set(tmp_path.rglob("*"))
    write_text = Path.write_text

    def interrupted_write(target, text, *args, **kwargs):
        write_text(target, text[:12], *args, **kwargs)
        raise OSError("injected disk write failure")

    with monkeypatch.context() as patch:
        if failure == "write":
            patch.setattr(Path, "write_text", interrupted_write)
        else:
            def refused_replace(*args):
                raise OSError("injected disk write failure")
            patch.setattr("cadex_cli.project_docs.os.replace", refused_replace)
        with pytest.raises(OSError, match="injected disk write failure"):
            update()
    assert path.read_bytes() == original
    assert set(tmp_path.rglob("*")) == files
    update()
    assert path.read_bytes().startswith(original)
    assert path.read_text().count("new result") == (2 if kind == "decision" else 1)
    assert path.stat().st_mode & 0o777 == 0o640
    assert set(tmp_path.rglob("*")) == files
