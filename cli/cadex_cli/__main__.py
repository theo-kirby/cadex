# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""``cadex`` — the command line.

Nine subcommands over one project, of which exactly two spend tokens::

    cadex -p "a mounting bracket for a NEMA17, 4 mm wall" --out ./out
    cadex params --set fin_angle=12 --out ./sweep/12
    cadex script --set bracket.py --out ./out
    cadex export --out ./out
    cadex inventory
    cadex clearance
    cadex link --from ../sensorA --output sensor
    cadex asset --put walk.cxpolicy --put walk-task.json
    cadex train --out ./run --iterations 200 --envs 64 --put

That asymmetry is the whole design. An expensive turn authors a *parametric*
script once; after that a sweep is ``set_params`` and a re-export, with no
model in the loop at all, and an external simulator can feed its results back
into the next turn only when the shape itself has to change.

Exit codes are part of the interface, so a pipeline can branch on the reason
rather than on stderr: ``0`` fine, ``1`` the engine or the agent failed,
``2`` the command was wrong, ``3`` the engine refused the script. Progress
goes to stderr and the report goes to stdout, so ``--json`` is always safe to
pipe.
"""

from __future__ import annotations

import argparse
import json
from contextlib import contextmanager
import math
import os
from pathlib import Path
import signal
import sys
import time
from typing import Any, Iterator, Mapping, Sequence

from .agent import (
    ClaudeTurn,
    ClaudeUnavailable,
    DEFAULT_MODEL,
    default_model,
    find_claude,
    system_prompt,
)
from .bridge import Bridge, ToolCall
from .client import CadexdClient, CadexdError, open_project
from .engine import Engine, EngineError, resolve_engine, source_comparison
from .export import ExportError, export_blueprints, export_outputs, parse_formats
from .inventory import InventoryError, write_inventory
from .render import acquire_snapshot, write_render
from .section import write_section
from .clearance import (
    MAXIMUM_COMMON_VOLUME_MM3,
    MINIMUM_CLEARANCE_MM,
    bounds_agreement,
    write_clearance,
)
from .project_docs import (
    append_progress_row,
    commit_project,
    compared_number,
    documentation_status,
    ensure_project_repo,
    previous_numbers,
    task_comparison,
    comparison_cell,
    progress_numbers,
    read_project_docs,
    record_decisions,
    record_notes,
    scaffold_project_docs,
)
from .report import (
    EXIT_FAILURE,
    EXIT_OK,
    EXIT_REJECTED,
    EXIT_USAGE,
    RunReport,
    apply_modeling_reply,
    emit,
    params_from_script,
)
from .session import (
    ProjectBusy,
    project_lock,
    read_agent_state,
    read_project_assets,
    read_script_source,
    read_script_state,
    read_working_revision,
    write_agent_state,
)
from .train import (
    TrainError,
    find_task,
    remote_trainer_command,
    training_plan,
    resolve_trainer_python,
    verify_returned_policy,
    run_trainer,
    trainer_command,
)
from .walk import (
    DEFAULT_LEG_TIMEOUT_S,
    POLICY_SWITCH,
    ROLLOUT_DIRNAME,
    SCRIPT_FILENAME,
    SWEEP_DIRNAME,
    TRAIN_DIRNAME,
    WalkError,
    declare_policy,
    declared_note_subjects,
    review_from_outputs,
    run_leg,
    train_leg_timeout,
    write_review,
)

#: Where a run works when ``--project`` is not given. Hidden, and beside
#: whatever the caller is doing, so `cadex -p ... --out ./out` in an empty
#: directory is a complete command.
DEFAULT_PROJECT_DIRNAME = ".cadex"


def _progress(message: str) -> None:
    """Progress goes to stderr; stdout belongs to the report."""

    sys.stderr.write(message + "\n")
    sys.stderr.flush()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cadex",
        description="Cadex, headless. One parametric project script, driven "
        "by an AI turn or by parameters alone.",
    )
    _common(parser)
    parser.add_argument(
        "-p",
        "--prompt",
        default=None,
        help="What to build or change, in words. Spends tokens.",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Continue this project's stored conversation instead of "
        "starting a fresh one.",
    )
    parser.add_argument(
        "--model",
        default=default_model(),
        help=f"Model for the turn. Default: $CADEX_MODEL, then {DEFAULT_MODEL}.",
    )
    parser.add_argument(
        "--claude", default="", help="Path to the claude CLI, if it is not on PATH."
    )

    subparsers = parser.add_subparsers(dest="command")

    params_parser = subparsers.add_parser(
        "params", help="Set declared parameters and rebuild. No AI, no tokens."
    )
    _common(params_parser, inherit=True)
    params_parser.add_argument(
        "--set",
        dest="assignments",
        action="append",
        default=[],
        metavar="NAME=VALUE",
        help="Repeatable. Values are clamped to each parameter's range.",
    )

    export_parser = subparsers.add_parser(
        "export", help="Rebuild the accepted script and write its outputs."
    )
    export_parser.add_argument(
        "--blueprints",
        action="store_true",
        default=False,
        help="Also copy the project's stored blueprint sheets into --out "
        "(the shell renders them; this only reads the store).",
    )
    _common(export_parser, inherit=True)

    inventory_parser = subparsers.add_parser(
        "inventory",
        help="List the parts of the accepted assembly with catalog ids. "
        "No AI, no tokens.",
    )
    _common(inventory_parser, inherit=True)
    inventory_parser.add_argument(
        "--assembly",
        default="",
        metavar="OUTPUT",
        help="The assembly output to inventory. A project publishes at most "
        "one, so this is only ever a check that you are looking at it.",
    )

    render_parser = subparsers.add_parser(
        "render", help="Write accepted front/top/right/iso views to review/render/.")
    _common(render_parser, inherit=True)
    section_parser = subparsers.add_parser("section", help="Cut accepted geometry through a named world plane.")
    _common(section_parser, inherit=True)
    section_parser.add_argument("--plane", choices=("XY", "XZ", "YZ"), required=True)
    section_parser.add_argument("--offset-mm", type=float, default=0.0)

    clearance_parser = subparsers.add_parser(
        "clearance", help="Check accepted assembly pairs; write docs/clearance.md.",
    )
    _common(clearance_parser, inherit=True)
    clearance_parser.add_argument("--assembly", default="", metavar="OUTPUT")
    clearance_parser.add_argument("--min-clearance-mm", type=float, default=MINIMUM_CLEARANCE_MM)
    clearance_parser.add_argument("--max-common-volume-mm3", type=float, default=MAXIMUM_COMMON_VOLUME_MM3)

    script_parser = subparsers.add_parser(
        "script", help="Print the project script, or replace it from a file."
    )
    _common(script_parser, inherit=True)
    script_parser.add_argument(
        "--set",
        dest="source_file",
        default="",
        metavar="FILE",
        help="Replace the script with this file ('-' for stdin) and rebuild.",
    )
    script_parser.add_argument(
        "--replace",
        action="store_true",
        help="Allow the new script to drop outputs the accepted revision "
        "declares.",
    )

    link_parser = subparsers.add_parser(
        "link",
        help="Bring a part in from another project, or refresh one. No AI, "
        "no tokens.",
    )
    _common(link_parser, inherit=True)
    link_parser.add_argument(
        "--from",
        dest="source_project",
        default="",
        metavar="DIR",
        help="The other project's root. It is read, never opened or changed.",
    )
    link_parser.add_argument(
        "--output",
        default="",
        metavar="NAME",
        help="Which of its declared outputs to pull. Omit to be told what it "
        "declares.",
    )
    link_parser.add_argument(
        "--name",
        dest="asset_name",
        default="",
        metavar="FILE",
        help="Store it under this name. Defaults to <output>.cxpart; re-using "
        "a name is how a part is refreshed.",
    )

    asset_parser = subparsers.add_parser(
        "asset",
        help="Copy a file into the project store, or list what is there. "
        "No AI, no tokens.",
    )
    _common(asset_parser, inherit=True)
    asset_parser.add_argument(
        "--put",
        dest="put_files",
        action="append",
        default=[],
        metavar="FILE",
        help="Repeatable. A .cxpolicy, its .json/.xml provenance, a mesh "
        "(.stl/.obj/.ply) or a .cxpart. Re-using a stored name replaces it.",
    )
    asset_parser.add_argument(
        "--name",
        dest="asset_name",
        default="",
        metavar="NAME",
        help="Store the one --put file under this name (same suffix). "
        "Defaults to the file's own name.",
    )

    train_parser = subparsers.add_parser(
        "train",
        help="Export the accepted script's training bundle into --out and "
        "run the offboard trainer on it. No AI, no tokens; needs the "
        "training venv (training/SETUP.md).",
    )
    _common(train_parser, inherit=True)
    train_parser.add_argument(
        "--iterations", type=int, default=200, help="PPO iterations (200)."
    )
    train_parser.add_argument(
        "--envs", type=int, default=256, help="Parallel environments (256)."
    )
    train_parser.add_argument("--seed", type=int, default=0, help="Training RNG seed, 0..4294967295 (default 0); rollout seed stays in the script.")
    train_parser.add_argument(
        "--label", default="", help="A label written into the policy header."
    )
    train_parser.add_argument(
        "--init-from",
        dest="init_from",
        default="",
        metavar="POLICY",
        help="Warm-start the actor from this .cxpolicy (same task digest).",
    )
    train_parser.add_argument(
        "--init-from-parent-task",
        dest="init_from_parent_task",
        default="",
        metavar="BUNDLE",
        help="The task .json --init-from's policy was trained on; needed "
        "beside --init-from-task-change.",
    )
    train_parser.add_argument(
        "--init-from-task-change",
        dest="init_from_task_change",
        default="",
        metavar="REASON",
        help="Warm-start across a task change (a curriculum step: reward, "
        "disturbance, episode length...) and say why in one line. Needs "
        "--init-from and --init-from-parent-task.",
    )
    train_parser.add_argument(
        "--task",
        dest="task_name",
        default="",
        metavar="NAME",
        help="Which declared training task, when the script exports more "
        "than one.",
    )
    train_parser.add_argument(
        "--name",
        dest="policy_name",
        default="",
        metavar="NAME.cxpolicy",
        help="The policy's filename in --out, and its stored name with "
        "--put. Defaults to <task>.cxpolicy.",
    )
    train_parser.add_argument(
        "--put",
        action="store_true",
        default=False,
        help="After training, copy the policy into the project store and "
        "report its sha256 (the digest assembly.policy names).",
    )
    train_parser.add_argument(
        "--timeout",
        type=float,
        default=0.0,
        metavar="SECONDS",
        help="Stop the trainer after this long; 0 is no limit.",
    )
    train_parser.add_argument(
        "--trainer-python",
        dest="trainer_python",
        default="",
        metavar="PATH",
        help="The training venv's interpreter. Default: $CADEX_TRAIN_PYTHON, "
        "then <repo>/.venv, then ~/cadex-train-venv.",
    )
    train_parser.add_argument(
        "--dry-run",
        dest="dry_run",
        action="store_true",
        default=False,
        help="Rebuild and export the bundle, then report the plan instead "
        "of training: the files the leg would touch and the steps it would "
        "take, here or on the box. Runs no trainer, reaches no box, stores "
        "nothing. The preflight for `walk --remote`.",
    )
    _remote_flags(train_parser)
    walk_parser = subparsers.add_parser(
        "walk",
        help="The lifecycle walk as one command: optional design turns, an "
        "optional parameter change, train, re-declare the policy, verify "
        "and roll out, review. Each leg is a child cadex command. Spends "
        "tokens only for --prompt.",
    )
    _common(walk_parser, inherit=True)
    walk_parser.add_argument(
        "--prompt",
        dest="prompts",
        action="append",
        default=[],
        metavar="TEXT",
        help="Repeatable, in order: design turns before training. The first "
        "starts a conversation (or continues one with --resume); the rest "
        "continue it.",
    )
    walk_parser.add_argument(
        "--resume",
        action="store_true",
        default=False,
        help="Continue the project's stored conversation for the first --prompt.",
    )
    walk_parser.add_argument(
        "--model",
        default=default_model(),
        help=f"Model for the turns. Default: $CADEX_MODEL, then {DEFAULT_MODEL}.",
    )
    walk_parser.add_argument(
        "--claude", default="", help="Path to the claude CLI, if it is not on PATH."
    )
    walk_parser.add_argument(
        "--set",
        dest="assignments",
        action="append",
        default=[],
        metavar="NAME=VALUE",
        help="Repeatable: the iterate step. Blanks the policy switch, applies "
        "the change, and exports the new bundle before training.",
    )
    walk_parser.add_argument(
        "--iterations", type=int, default=200, help="PPO iterations (200)."
    )
    walk_parser.add_argument(
        "--envs", type=int, default=256, help="Parallel environments (256)."
    )
    walk_parser.add_argument("--seed", type=int, default=0, help="Training RNG seed, 0..4294967295 (default 0); rollout seed stays in the script.")
    walk_parser.add_argument(
        "--label", default="", help="A label written into the policy header."
    )
    walk_parser.add_argument(
        "--init-from", dest="init_from", default="", metavar="POLICY",
        help="Warm-start the actor from this .cxpolicy (same task digest).",
    )
    walk_parser.add_argument(
        "--init-from-parent-task", dest="init_from_parent_task", default="",
        metavar="BUNDLE",
        help="The task .json --init-from's policy was trained on; needed "
        "beside --init-from-task-change.",
    )
    walk_parser.add_argument(
        "--init-from-task-change", dest="init_from_task_change", default="",
        metavar="REASON",
        help="Warm-start across a task change, and say why in one line.",
    )
    walk_parser.add_argument(
        "--task", dest="task_name", default="", metavar="NAME",
        help="Which exported training task, if the script declares more than one.",
    )
    walk_parser.add_argument(
        "--name", dest="policy_name", default="", metavar="NAME.cxpolicy",
        help="The policy's filename (default <task>.cxpolicy).",
    )
    walk_parser.add_argument(
        "--timeout", type=float, default=0.0,
        help="Stop the TRAINER after this many seconds (0: no limit). It "
        "bounds the trainer inside the train leg and nothing else; "
        "--leg-timeout bounds the legs themselves.",
    )
    walk_parser.add_argument(
        "--leg-timeout", dest="leg_timeout", type=float,
        default=DEFAULT_LEG_TIMEOUT_S, metavar="SECONDS",
        help="Stop any one leg after this many seconds and fail the walk "
        "there, killing the leg and everything under it (0: no limit). "
        "The train leg is never bounded below --timeout plus a margin. "
        "Default: %(default)g.",
    )
    walk_parser.add_argument(
        "--trainer-python", dest="trainer_python", default="", metavar="PATH",
        help="The training venv's interpreter, if not where training/SETUP.md "
        "puts it.",
    )
    _remote_flags(walk_parser)
    return parser


def _remote_flags(parser: argparse.ArgumentParser) -> None:
    """``--remote`` and ``--allow-cpu``, the same on ``train`` and ``walk``
    (ADR-200): the trainer runs on the box ``training/.remote.env`` names,
    through ``training/remote_train.sh``; the artifacts do not move."""

    parser.add_argument(
        "--remote",
        action="store_true",
        default=False,
        help="Train on the remote box through training/remote_train.sh "
        "(configured by training/.remote.env; run its `check` first). The "
        "bundle goes out from --out and the policy comes back to it; every "
        "later step is unchanged. A warm start travels too (ADR-268): its "
        "two files go out beside the bundle.",
    )
    parser.add_argument(
        "--allow-cpu",
        dest="allow_cpu",
        action="store_true",
        default=False,
        help="With --remote: accept a run the box reports as device 'cpu' "
        "instead of failing it (remote_train.sh --allow-cpu).",
    )


def _common(parser: argparse.ArgumentParser, *, inherit: bool = False) -> None:
    """The flags every subcommand shares.

    A subparser's *defaults* would otherwise overwrite what the top-level
    parser already read, so ``cadex --project foo params`` would silently
    work on ``./.cadex``. ``SUPPRESS`` makes an unmentioned flag leave the
    namespace alone, so the flag means the same thing on either side of the
    subcommand.
    """

    def default(value: Any) -> Any:
        return argparse.SUPPRESS if inherit else value

    parser.add_argument(
        "--project",
        default=default(os.environ.get("CADEX_PROJECT", "") or DEFAULT_PROJECT_DIRNAME),
        help=f"Project root (created if absent). Default: ./{DEFAULT_PROJECT_DIRNAME}",
    )
    parser.add_argument(
        "--out",
        default=default(""),
        help="Directory to write exported files into.",
    )
    parser.add_argument(
        "--format",
        default=default("step,stl"),
        help="Comma-separated export formats: step, stl, brep.",
    )
    parser.add_argument(
        "--engine",
        default=default(""),
        help="A staged engine payload root. Defaults to CADEX_ENGINE_ROOT, "
        "then the development tree.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        default=default(False),
        help="Emit the machine-readable envelope.",
    )
    parser.add_argument(
        "--wait",
        action="store_true",
        default=default(False),
        help="Block for the project lock instead of failing when another run "
        "holds it.",
    )


@contextmanager
def _engine_session(
    args: argparse.Namespace, report: RunReport, *, restore: bool = True
) -> Iterator[tuple[Engine, CadexdClient]]:
    """Resolve, lock, spawn, open — and unwind all four in order."""

    engine = resolve_engine(args.engine or None)
    report.engine = engine.describe()
    project_root = Path(args.project).expanduser()
    with project_lock(project_root, wait=bool(args.wait)):
        project_root = project_root.resolve()
        report.project_root = str(project_root)
        client = CadexdClient(engine)
        try:
            client.start()
            opened = open_project(client, project_root, restore=restore)
            report.params = params_from_script(opened.get("script"))
            # The project as a codebase (ADR-193): its three documents
            # exist from the first visit on. Plain files beside
            # script.json, like agent.json; the engine never reads them.
            created = scaffold_project_docs(project_root)
            if created:
                report.notes.append(
                    "scaffolded " + ", ".join(created) + " in the project root."
                )
            # ...and a git repository it owns (ADR-194): one commit per
            # accepted run, made in main() after the PROGRESS.md row.
            repo_note = ensure_project_repo(project_root)
            if repo_note:
                report.notes.append(repo_note)
            _install_cancel(client)
            yield engine, client
        finally:
            client.shutdown()


def _install_cancel(client: CadexdClient) -> None:
    """Ctrl-C asks the engine to abandon the run before it kills us.

    A cancelled run leaves the store consistent; a killed engine mid-write
    is what ``open_project``'s restore pass has to clean up afterwards.
    """

    def handler(_signum: int, _frame: Any) -> None:
        _progress("cancelling…")
        client.cancel()
        raise KeyboardInterrupt

    try:
        signal.signal(signal.SIGINT, handler)
    except ValueError:
        pass  # not the main thread; the default handler is fine


def _finish(
    args: argparse.Namespace,
    report: RunReport,
    engine: Engine,
    display: dict[str, Any] | None,
) -> None:
    """Export, if asked, and record what was written."""

    if not args.out:
        return
    if not display:
        report.notes.append(
            "nothing to export: the accepted revision declares no geometry."
        )
        return
    report.out_dir = str(Path(args.out).expanduser())
    report.outputs = export_outputs(
        engine, display, report.out_dir, parse_formats(args.format)
    )


def _refresh_script_state(client: CadexdClient, report: RunReport) -> None:
    """Re-read the parameters after a change, so the report is current."""

    report.params = params_from_script(read_script_state(client))


#: How much of the agent's closing words and of an engine refusal reach the
#: envelope. Long enough to name a cause, short enough that a walk's
#: ``error`` line stays one readable paragraph.
REASON_CHARS = 400


def _clip(text: str, limit: int = REASON_CHARS) -> str:
    text = " ".join(str(text).split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _rejection_reason(text: str, calls: Sequence[ToolCall]) -> str:
    """Why a turn ended with no accepted script, in one line.

    The bare sentence — "the turn finished without the engine accepting a
    script" — is true of two quite different runs, and only the parent can
    tell them apart: a turn that *offered* a script and had it refused, and
    a turn that never offered one at all. Both were seen inside ``cadex
    walk`` in one afternoon, and the envelope said the same thing for each,
    so the record could not name the cause. So carry the two facts the
    parent already has: the last thing the engine refused, and the agent's
    own closing words. Nothing here retries and nothing here guesses — this
    is the reason, written down.
    """

    parts = ["the turn finished without the engine accepting a script."]
    refused = next((call for call in reversed(calls) if not call.ok), None)
    if refused is not None:
        detail = _clip(refused.summary) or refused.failure_code or "failed"
        code = f" [{refused.failure_code}]" if refused.failure_code else ""
        parts.append(f"the engine last refused {refused.op}{code}: {detail}")
    else:
        offered = ", ".join(dict.fromkeys(call.op for call in calls))
        parts.append(
            "the engine refused nothing: the agent made "
            + (f"{len(calls)} tool call(s) ({_clip(offered, 120)})" if calls
               else "no tool call")
            + " and never offered a script."
        )
    if text.strip():
        parts.append(f"the agent's closing words: {_clip(text)}")
    return " ".join(parts)


# -- commands ------------------------------------------------------------


def command_prompt(
    args: argparse.Namespace,
    report: RunReport,
    *,
    turn_factory: Any = ClaudeTurn,
) -> int:
    """One AI turn against this project.

    ``turn_factory`` is the seam the suite drives: a mock that replays a
    scripted tool sequence through the *real* bridge socket exercises this
    whole function — revision injection, progress, report assembly, export —
    without spending a token. See ``cli/tests/mock_backend.py``.
    """

    claude_path = find_claude(args.claude) if turn_factory is ClaudeTurn else ""
    stored = read_agent_state(Path(args.project).expanduser())
    session_id = stored.session_id if args.resume else ""
    report.model = args.model

    with _engine_session(args, report) as (engine, client):
        api = client.request("describe_api")
        if api.get("ok") is not True:
            report.error = f"describe_api failed: {api.get('error')}"
            return EXIT_FAILURE

        # The revision the bridge starts from is the engine's own working
        # revision, so the first write of a resumed project is guarded
        # correctly without the model being told what it is.
        revision = read_working_revision(client)

        def on_call(call: ToolCall) -> None:
            mark = "·" if call.ok else "✗"
            _progress(f" {mark} {call.op}  {call.summary}")

        def on_text(text: str) -> None:
            """The model's prose is narration, so it goes to stderr too."""

            sys.stderr.write(text)

        with Bridge(client, on_call=on_call, initial_revision=revision) as bridge:
            turn = turn_factory(
                claude_path=claude_path,
                model=args.model,
                system_prompt_text=system_prompt(
                    api, project_docs=read_project_docs(report.project_root)
                ),
                socket_path=str(bridge.socket_path),
                token=bridge.token,
                session_id=session_id,
                on_text=on_text,
                cwd=report.project_root,
            )
            try:
                result = turn.run(args.prompt)
            finally:
                turn.cleanup()
            sys.stderr.write("\n")
            sys.stderr.flush()

        if result.session_id:
            write_agent_state(
                report.project_root,
                session_id=result.session_id,
                model=args.model,
            )
        report.session_id = result.session_id
        if result.resume_failed:
            report.notes.append(
                "the stored session id could not be resumed; ran a fresh "
                "conversation."
            )
        if result.text.strip():
            report.notes.append(result.text.strip())
        # What the agent decided lands in the project's own ADR log
        # (ADR-193): a closing line that starts `DECISION:`. A convention,
        # not a tool, because the agent has no file access here.
        landed = record_decisions(report.project_root, result.text)
        if landed:
            report.notes.append(
                "recorded " + ", ".join(landed) + " in DECISIONS.md."
            )
        # ...and its longer notes land beside them, one file per subject
        # (ADR-245): a closing line `NOTE <subject>:`. The same convention
        # rather than a second mechanism, and read back on the next visit.
        noted = record_notes(report.project_root, result.text)
        if noted:
            report.notes.append("wrote " + ", ".join(noted) + ".")

        accepted = bridge.state.last_accepted
        report.revision = bridge.state.revision or report.revision
        if accepted is not None:
            apply_modeling_reply(report, accepted)
        _refresh_script_state(client, report)

        if not result.ok:
            report.error = result.error or "the agent turn failed."
            return EXIT_FAILURE
        if accepted is None:
            report.error = _rejection_reason(result.text, bridge.state.calls)
            return EXIT_REJECTED

        _finish(args, report, engine, accepted.get("display"))
        report.ok = True
        return EXIT_OK


def _parse_assignments(raw: Sequence[str]) -> dict[str, Any]:
    values: dict[str, Any] = {}
    for item in raw:
        if "=" not in item:
            raise ValueError(f"--set expects NAME=VALUE, got {item!r}.")
        name, _, text = item.partition("=")
        name = name.strip()
        text = text.strip()
        if not name:
            raise ValueError(f"--set expects NAME=VALUE, got {item!r}.")
        try:
            values[name] = float(text) if "." in text or "e" in text.lower() else int(text)
        except ValueError as exc:
            raise ValueError(
                f"--set {name}: {text!r} is not a number. Parameters are "
                "numeric (num(...))."
            ) from exc
    if not values:
        raise ValueError("params needs at least one --set NAME=VALUE.")
    return values


def command_params(args: argparse.Namespace, report: RunReport) -> int:
    """Change declared parameter values. No model is spawned at all."""

    values = _parse_assignments(args.assignments)
    with _engine_session(args, report) as (engine, client):
        revision = read_working_revision(client)
        _progress(f" · set_params  {', '.join(sorted(values))}")
        reply = client.request(
            "set_params", {"values": values, "expected_revision": revision}
        )
        apply_modeling_reply(report, reply)
        if reply.get("ok") is not True:
            report.error = str(
                reply.get("error") or reply.get("failure_code") or "set_params failed"
            )
            _refresh_script_state(client, report)
            return EXIT_REJECTED
        _refresh_script_state(client, report)
        _finish(args, report, engine, reply.get("display"))
        report.ok = True
        return EXIT_OK


def command_export(args: argparse.Namespace, report: RunReport) -> int:
    """Rebuild the accepted script and write its outputs."""

    if not args.out:
        report.error = "export needs --out."
        return EXIT_USAGE
    with _engine_session(args, report) as (engine, client):
        _progress(" · rebuild")
        reply = client.request("rebuild")
        apply_modeling_reply(report, reply)
        if reply.get("ok") is not True:
            report.error = str(
                reply.get("error") or reply.get("failure_code") or "rebuild failed"
            )
            return EXIT_REJECTED
        _finish(args, report, engine, reply.get("display"))
        if getattr(args, "blueprints", False):
            copied = export_blueprints(client, args.out)
            report.notes.append(
                "blueprints: copied {:d} sheet(s) into {:s}.".format(
                    len(copied), str(Path(args.out).expanduser()))
                if copied else
                "blueprints: the project has none stored."
            )
        report.ok = True
        return EXIT_OK


def command_render(args: argparse.Namespace, report: RunReport) -> int:
    with _engine_session(args, report) as (_engine, client):
        path, value = write_render(client, report.project_root)
        report.revision = report.accepted_revision = value["revision"]
        report.digest = value["digest"] or ""
        report.notes.append(f"render: {value['triangles']} triangles, four views; {path}.")
        report.ok = True
        return EXIT_OK


def command_section(args: argparse.Namespace, report: RunReport) -> int:
    with _engine_session(args, report) as (_engine, client):
        path, value = write_section(client, report.project_root, plane=args.plane, offset=args.offset_mm)
        report.revision = report.accepted_revision = value["revision"]
        report.digest = value["digest"] or ""
        report.notes.append(f"section: {value['status']}; {path}.")
        report.ok = True
        return EXIT_OK


def command_clearance(args: argparse.Namespace, report: RunReport) -> int:
    with _engine_session(args, report, restore=False) as (_engine, client):
        path, value = write_clearance(
            client, report.project_root, target=args.assembly,
            minimum=args.min_clearance_mm, maximum_volume=args.max_common_volume_mm3,
        )
        report.notes.append(f"clearance: {len(value['pairs'])} pair(s), written to {path}.")
        report.ok = True
        return EXIT_OK


def command_inventory(args: argparse.Namespace, report: RunReport) -> int:
    """What the accepted assembly is made of, as a file in the project.

    The first headless review call (ADR-233): no rebuild, no tokens, no
    geometry recomputed — it reads the pinned accepted attempt through
    ``inspect scope="inventory"`` and lands ``docs/inventory.md`` in the
    project, where the next visit's agent will read it.
    """

    with _engine_session(args, report) as (_engine, client):
        _progress(" · inspect scope=inventory")
        path, value = write_inventory(
            client, report.project_root, target=str(args.assembly or "")
        )
        report.notes.append(
            "inventory: {:d} component(s), {:d} catalogued, written to {:s}.".format(
                int(value.get("component_count") or 0),
                sum(int(count) for count in dict(value.get("catalog_counts") or {}).values()),
                str(path),
            )
        )
        report.ok = True
        return EXIT_OK


def command_script(args: argparse.Namespace, report: RunReport) -> int:
    """Print the project script, or replace it wholesale from a file."""

    source: str | None = None
    if args.source_file:
        if args.source_file == "-":
            source = sys.stdin.read()
        else:
            path = Path(args.source_file).expanduser()
            if not path.is_file():
                report.error = f"no such file: {path}"
                return EXIT_USAGE
            source = path.read_text(encoding="utf-8")

    # Neither form needs the restore pass, and the moment it is needed most is
    # the moment restore fails (ADR-272). Reading is a read of the stored
    # source, not of the model; writing replaces that source outright and
    # re-accepts, so replaying the old one first is at best wasted work. The
    # walk's digest edit (ADR-199) lands exactly there: ``train --put``
    # overwrites the asset the accepted script declares by sha256, so the
    # stored script no longer re-runs, and the two legs whose whole job is to
    # rewrite that literal used to fail with the project they were fixing.
    with _engine_session(args, report, restore=False) as (engine, client):
        if source is None:
            sys.stdout.write(read_script_source(client))
            sys.stdout.flush()
            report.ok = True
            # Printing the script IS the output; an envelope after it would
            # corrupt what the caller just redirected into a file.
            return EXIT_OK

        revision = read_working_revision(client)
        _progress(" · write_script")
        request: dict[str, Any] = {"source": source, "expected_revision": revision}
        if args.replace:
            request["replace"] = True
        reply = client.request("write_script", request)
        apply_modeling_reply(report, reply)
        if reply.get("ok") is not True:
            report.error = str(
                reply.get("error") or reply.get("failure_code") or "write_script failed"
            )
            _refresh_script_state(client, report)
            return EXIT_REJECTED
        _refresh_script_state(client, report)
        _finish(args, report, engine, reply.get("display"))
        report.ok = True
        return EXIT_OK


def command_link(args: argparse.Namespace, report: RunReport) -> int:
    """Bring a part in from another project — and refresh one, identically.

    There is no separate refresh command, because there is no separate
    operation: ``link_part`` overwrites the stored container, and overwriting
    an asset is re-import (ADR-138). Running this command again is the whole
    of refreshing, and the engine's ``changed`` is what says whether the other
    project actually moved.

    A change that moved is followed by a rebuild here, so the new geometry
    lands as one normal accepted revision. A change that moved *nothing*
    rebuilds nothing: a no-op that re-accepted the model would put a
    meaningless revision in the history every time somebody checked.
    """

    if not args.source_project:
        report.error = "link needs --from DIR, the other project's root."
        return EXIT_USAGE

    request: dict[str, Any] = {
        "source_project": str(Path(args.source_project).expanduser())
    }
    if args.output:
        request["output"] = args.output
    if args.asset_name:
        request["name"] = args.asset_name

    with _engine_session(args, report) as (engine, client):
        _progress(f" · link_part  {args.output or '?'}")
        reply = client.request("link_part", request)
        if reply.get("ok") is not True:
            report.error = str(
                reply.get("error") or reply.get("failure_code") or "link_part failed"
            )
            candidates = [str(item) for item in reply.get("candidates") or []]
            if candidates:
                report.notes.append(
                    "that project declares: " + ", ".join(candidates)
                )
            return EXIT_REJECTED

        name = str(reply.get("name") or "")
        revision = str(reply.get("source_revision") or "")[:16]
        if not reply.get("changed"):
            report.notes.append(
                f"{name} is already at {revision}; nothing moved, so nothing "
                "was rebuilt."
            )
            _refresh_script_state(client, report)
            report.ok = True
            return EXIT_OK

        previous = str(reply.get("previous_revision") or "")
        report.notes.append(
            f"{name} moved from {previous[:16]} to {revision}."
            if previous
            else f"{name} linked at {revision}. Use it with "
            f'part.import_part("{name}").'
        )

        # A first pull has nothing to rebuild *into* yet: no script names the
        # container. A refresh does, and that rebuild is what makes it real.
        if not read_script_source(client).strip():
            _refresh_script_state(client, report)
            report.ok = True
            return EXIT_OK

        _progress(" · rebuild")
        rebuilt = client.request("rebuild")
        apply_modeling_reply(report, rebuilt)
        if rebuilt.get("ok") is not True:
            report.error = str(
                rebuilt.get("error")
                or rebuilt.get("failure_code")
                or "rebuild failed"
            )
            report.notes.append(
                "the part was updated, but this project no longer builds "
                "against it; the refusal above names what broke."
            )
            _refresh_script_state(client, report)
            return EXIT_REJECTED
        _refresh_script_state(client, report)
        _finish(args, report, engine, rebuilt.get("display"))
        report.ok = True
        return EXIT_OK


def command_asset(args: argparse.Namespace, report: RunReport) -> int:
    """Bring a file into the project store, or list the store. No model.

    This is how a trained policy comes home headlessly (ADR-190): the
    trainer's ``.cxpolicy`` and the receipt it travels with go in through
    ``put_asset`` — the path a mesh already travels, and the one write to
    the store that is not the script's — and the envelope's ``assets`` row
    carries the sha256 ``assembly.policy(sha256=...)`` then requires. It
    never rebuilds: a stored file changes nothing until a script names it,
    and that change is ``cadex script --set`` or a turn's ``edit_script``.

    With no ``--put`` it lists the store, which is what a pipeline reads to
    learn a digest it did not store itself.
    """

    files = [str(item) for item in args.put_files]
    if args.asset_name and len(files) != 1:
        report.error = "--name applies to exactly one --put FILE."
        return EXIT_USAGE
    paths: list[Path] = []
    for item in files:
        path = Path(item).expanduser()
        if not path.is_file():
            report.error = f"no such file: {path}"
            return EXIT_USAGE
        paths.append(path.resolve())

    with _engine_session(args, report) as (_engine, client):
        if not paths:
            report.assets = read_project_assets(client)
            if not report.assets:
                report.notes.append("the project store holds no assets.")
            report.ok = True
            return EXIT_OK

        for path in paths:
            request: dict[str, Any] = {"source_path": str(path)}
            if args.asset_name:
                request["name"] = args.asset_name
            _progress(f" · put_asset  {path.name}")
            reply = client.request("put_asset", request)
            if reply.get("ok") is not True:
                report.error = str(
                    reply.get("error") or reply.get("failure_code") or "put_asset failed"
                )
                report.assets = [
                    dict(item)
                    for item in (reply.get("observed") or {}).get("assets") or []
                ]
                return EXIT_REJECTED
            report.notes.append(
                "stored {:s} ({:d} bytes, sha256 {:s}).".format(
                    str(reply.get("name") or ""),
                    int(reply.get("bytes") or 0),
                    str(reply.get("sha256") or ""),
                )
            )
            report.assets = [dict(item) for item in reply.get("assets") or []]
        report.ok = True
        return EXIT_OK


def command_train(args: argparse.Namespace, report: RunReport) -> int:
    """Rebuild, export the bundle, train offboard, and bring the policy home.

    The training leg of the lifecycle walk (ADR-191, ``docs/MUJOCO.md``
    §7c row 4), as one command instead of a person's three: ``cadex
    export`` for the bundle, the venv's trainer with flags looked up by
    hand, ``cadex asset --put`` for the result. Training itself stays
    offboard (ADR-084) — this spawns ``training/cadex_train.py`` under the
    venv's interpreter and reads its receipt; the engine is never in the
    room while it runs. The project lock is held for the rebuild and again
    for the ``put``, and released in between, because a fifteen-minute
    training run is not a modelling operation.

    It never rebuilds *after* training: the policy is real when a script
    names it with the sha256 this run reports, which is ``cadex script
    --set`` or a turn's ``edit_script``, the same as ``cadex asset``.
    """

    if not args.out:
        report.error = "train needs --out: the bundle and the policy land there."
        return EXIT_USAGE
    if not 0 <= args.seed <= 4294967295:
        report.error = "--seed must be between 0 and 4294967295."
        return EXIT_USAGE
    if args.iterations < 1 or args.envs < 1:
        report.error = "--iterations and --envs must be at least 1."
        return EXIT_USAGE
    policy_name = str(args.policy_name or "")
    if policy_name and not policy_name.endswith(".cxpolicy"):
        report.error = "--name must end in .cxpolicy."
        return EXIT_USAGE
    if (args.init_from_task_change or args.init_from_parent_task) and not (
        args.init_from and args.init_from_parent_task and args.init_from_task_change
    ):
        # The trainer refuses these apart too, but after the rebuild and
        # the export; a usage error costs nothing.
        report.error = (
            "--init-from-task-change needs --init-from POLICY and "
            "--init-from-parent-task BUNDLE beside it (the bundle that "
            "policy was trained on)."
        )
        return EXIT_USAGE
    remote_error = _remote_usage_error(args)
    if remote_error:
        report.error = remote_error
        return EXIT_USAGE
    python = None if args.remote else resolve_trainer_python(args.trainer_python or None)

    with _engine_session(args, report) as (engine, client):
        _progress(" · rebuild")
        reply = client.request("rebuild")
        apply_modeling_reply(report, reply)
        if reply.get("ok") is not True:
            report.error = str(
                reply.get("error") or reply.get("failure_code") or "rebuild failed"
            )
            return EXIT_REJECTED
        _finish(args, report, engine, reply.get("display"))
        _refresh_script_state(client, report)
    try:
        task = find_task(report.outputs, args.task_name)
    except TrainError as exc:
        report.error = str(exc)
        return EXIT_REJECTED

    out_dir = Path(report.out_dir)
    policy_path = out_dir / (policy_name or f"{task.name}.cxpolicy")
    flags = dict(
        iterations=args.iterations,
        envs=args.envs,
        seed=args.seed,
        label=args.label,
        init_from=args.init_from,
        init_from_parent_task=args.init_from_parent_task,
        init_from_task_change=args.init_from_task_change,
    )
    if args.remote:
        # The same leg on the box (ADR-200): the bundle and the model go
        # out from --out, the policy comes back to policy_path, and the
        # receipt is the same last JSON line. Nothing after this branch
        # knows where the trainer ran.
        command = remote_trainer_command(
            task.files["json"], policy_path, allow_cpu=args.allow_cpu, **flags
        )
        where = f"remote, {Path(command[0]).name}"
    else:
        command = trainer_command(python, task.files["json"], policy_path, **flags)
        where = str(python)
    if args.dry_run:
        # The export above was real -- the bundle and the model are on
        # disk, and the plan names them by the path a dispatch would read.
        # Everything after this point is what the plan describes instead of
        # doing (ADR-255).
        report.training_plan = training_plan(
            command,
            bundle=task.files["json"],
            out=policy_path,
            remote=bool(args.remote),
            allow_cpu=bool(args.allow_cpu),
            store_as=policy_path.name if args.put else "",
        )
        _progress(f" · plan   {task.name}  ({where}, not run)")
        report.notes.append(
            "dry run: the {:s} leg would {:s}. Nothing was trained{:s}.".format(
                str(report.training_plan["mode"]),
                " -> ".join(
                    str(step["step"]) for step in report.training_plan["steps"]
                ),
                " or stored" if args.put else "",
            )
        )
        report.ok = True
        return EXIT_OK
    _progress(
        f" · train  {task.name}  {args.iterations} it × {args.envs} envs"
        f"  ({where})"
    )
    report.training = run_trainer(command, timeout=args.timeout)
    verify_returned_policy(policy_path, report.training)
    report.training["comparison"] = {**task_comparison(task.files["json"]),
                                     "training_seed": args.seed}
    report.notes.append(
        "trained {:s}: {:s} ({:s} bytes, sha256 {:s}) in {:.1f} s on {:s}.".format(
            task.name,
            str(report.training.get("out") or policy_path),
            str(report.training.get("bytes") or "?"),
            str(report.training.get("sha256") or ""),
            float(report.training.get("wall_time_s") or 0.0),
            str(report.training.get("device") or "?"),
        )
    )
    if not args.put:
        report.ok = True
        return EXIT_OK

    with _engine_session(args, report) as (_engine, client):
        _progress(f" · put_asset  {policy_path.name}")
        reply = client.request("put_asset", {"source_path": str(policy_path)})
        if reply.get("ok") is not True:
            report.error = str(
                reply.get("error") or reply.get("failure_code") or "put_asset failed"
            )
            return EXIT_REJECTED
        report.assets = [dict(item) for item in reply.get("assets") or []]
        report.notes.append(
            "stored {:s} ({:d} bytes, sha256 {:s}).".format(
                str(reply.get("name") or ""),
                int(reply.get("bytes") or 0),
                str(reply.get("sha256") or ""),
            )
        )
    report.ok = True
    return EXIT_OK


def _remote_usage_error(args: argparse.Namespace) -> str:
    """What is wrong with ``--remote``'s company, or nothing (ADR-200).

    Shared by ``train`` and ``walk`` so the walk refuses before its first
    leg rather than after a design turn spent tokens. ``--trainer-python``
    names a venv on this machine and the box has its own
    (``CADEX_TRAIN_VENV``); ``--allow-cpu`` is the dispatcher's flag and
    means nothing locally. A warm start is no longer refused here: since
    ADR-268 the dispatcher carries its two files out and re-points the
    flags, so an iterate has the same shape in both modes.
    """

    if not args.remote:
        if args.allow_cpu:
            return "--allow-cpu is remote_train.sh's flag; it needs --remote."
        return ""
    if args.trainer_python:
        return (
            "--trainer-python names a venv on this machine; with --remote the "
            "box's CADEX_TRAIN_VENV trains (training/remote.env.example)."
        )
    return ""


def _walk_common(args: argparse.Namespace) -> list[str]:
    common = ["--project", str(Path(args.project).expanduser())]
    if getattr(args, "engine", ""):
        common += ["--engine", str(args.engine)]
    if getattr(args, "wait", False):
        common.append("--wait")
    return common


def command_walk(args: argparse.Namespace, report: RunReport) -> int:
    """The lifecycle walk as one command (ADR-199).

    Design turns (``--prompt``, repeatable), the iterate change (``--set``,
    which blanks the policy switch and exports the bundle at the new
    digest), ``cadex train --put``, the digest edit — the one leg that was
    a person's — as a rewrite of the script's one ``assembly.policy``
    call followed by ``cadex script --set``, ``cadex params --set
    policy_on=1`` for the verified rollout, and the review read off the
    exported trace and accepted inventory. Each child ``cadex`` leg lands
    its own ``PROGRESS.md`` row and commit; the walk commits the review
    and render/section/inventory/clearance reports together. ``--remote`` (ADR-200) goes to
    the train leg and nowhere else: the trainer runs on the box, the
    artifacts and every later leg are unchanged.
    """

    walk_started = time.monotonic()
    if not args.out:
        report.error = "walk needs --out: the bundle, the policy and the rollout land there."
        return EXIT_USAGE
    if not 0 <= args.seed <= 4294967295:
        report.error = "--seed must be between 0 and 4294967295."
        return EXIT_USAGE
    if args.iterations < 1 or args.envs < 1:
        report.error = "--iterations and --envs must be at least 1."
        return EXIT_USAGE
    if args.policy_name and not str(args.policy_name).endswith(".cxpolicy"):
        report.error = "--name must end in .cxpolicy."
        return EXIT_USAGE
    if not math.isfinite(args.leg_timeout) or args.leg_timeout < 0:
        report.error = "--leg-timeout must be a nonnegative number of seconds (0: no limit)."
        return EXIT_USAGE
    if (args.init_from_task_change or args.init_from_parent_task) and not (
        args.init_from and args.init_from_parent_task and args.init_from_task_change
    ):
        report.error = (
            "--init-from-task-change needs --init-from POLICY and "
            "--init-from-parent-task BUNDLE beside it."
        )
        return EXIT_USAGE
    remote_error = _remote_usage_error(args)
    if remote_error:
        report.error = remote_error
        return EXIT_USAGE
    assignments = _parse_assignments(args.assignments) if args.assignments else {}
    if POLICY_SWITCH in assignments:
        report.error = f"--set {POLICY_SWITCH}: the walk owns the switch; set the change only."
        return EXIT_USAGE

    out_dir = Path(args.out).expanduser()
    out_dir.mkdir(parents=True, exist_ok=True)
    report.out_dir = str(out_dir)
    common = _walk_common(args)
    legs: list[dict[str, Any]] = []
    # The walk's own wall-clock bound, in the envelope beside the legs it
    # bounds: a run that was stopped and a run that finished are told apart
    # by the leg's exit code, and by this number saying what it was measured
    # against. The train leg carries its own, never under ``--timeout``.
    leg_timeout = float(args.leg_timeout)
    train_timeout = train_leg_timeout(leg_timeout, float(args.timeout))
    report.walk = {
        "legs": legs, "review": {},
        "leg_timeout_s": leg_timeout, "train_leg_timeout_s": train_timeout,
    }

    try:
        engine = resolve_engine(args.engine or None)
        report.engine = engine.describe()
        comparison = source_comparison(engine)
    except EngineError as exc:
        comparison = {"status": "unavailable", "reason": str(exc)}
    report.walk["engine_source_comparison"] = comparison
    _progress(" · walk engine/source comparison: " + json.dumps(comparison, sort_keys=True))

    def failed(leg: Any, what: str) -> int:
        legs.append(leg.to_json())
        report.error = "{:s} (leg {:s}, exit {:d}): {:s}".format(
            what, leg.name, leg.code, str(leg.envelope.get("error") or "no envelope")
        )
        return leg.code if leg.code in (EXIT_USAGE, EXIT_REJECTED) else EXIT_FAILURE

    # Design: the model turns, in order.
    for index, prompt in enumerate(args.prompts):
        argv = [*common, "-p", prompt, "--json", "--model", args.model]
        if index > 0 or args.resume:
            argv.append("--resume")
        if args.claude:
            argv += ["--claude", args.claude]
        _progress(f" · walk  design turn {index + 1}/{len(args.prompts)}")
        leg = run_leg("design", argv, timeout=leg_timeout)
        if leg.code != EXIT_OK:
            return failed(leg, "the design turn was not accepted")
        legs.append(leg.to_json())

    # Iterate: blank the switch and apply the change; the bundle is exported
    # at its new digest (ADR-192).
    if assignments:
        argv = [*common, "params", "--set", f"{POLICY_SWITCH}=0"]
        for name, value in sorted(assignments.items()):
            argv += ["--set", f"{name}={value}"]
        argv += ["--out", str(out_dir / SWEEP_DIRNAME), "--json"]
        _progress(" · walk  sweep")
        leg = run_leg("sweep", argv, timeout=leg_timeout)
        if leg.code != EXIT_OK:
            return failed(leg, "the change was refused")
        legs.append(leg.to_json())

    # Train, and bring the policy home.
    argv = [
        *common, "train", "--out", str(out_dir / TRAIN_DIRNAME), "--put",
        "--iterations", str(int(args.iterations)), "--envs", str(int(args.envs)),
        "--seed", str(int(args.seed)), "--timeout", str(float(args.timeout)),
        "--json",
    ]
    for flag, value in (
        ("--label", args.label), ("--name", args.policy_name),
        ("--task", args.task_name), ("--trainer-python", args.trainer_python),
        ("--init-from", args.init_from),
        ("--init-from-parent-task", args.init_from_parent_task),
        ("--init-from-task-change", args.init_from_task_change),
    ):
        if value:
            argv += [flag, str(value)]
    for flag, on in (("--remote", args.remote), ("--allow-cpu", args.allow_cpu)):
        if on:
            argv.append(flag)
    _progress(" · walk  train" + (" (remote)" if args.remote else ""))
    leg = run_leg("train", argv, timeout=train_timeout)
    if leg.code != EXIT_OK:
        return failed(leg, "training did not produce a policy")
    legs.append(leg.to_json())
    training = leg.envelope.get("training") or {}
    stored = [row for row in leg.envelope.get("assets") or []
              if row.get("sha256") == training.get("sha256")]
    if not training.get("sha256") or not stored:
        report.error = "train reported no stored policy sha256; nothing to declare."
        return EXIT_FAILURE
    report.training = dict(training)
    report.assets = [dict(row) for row in leg.envelope.get("assets") or []]
    weights = str(stored[0].get("name") or Path(str(training.get("out"))).name)
    sha256 = str(training["sha256"])

    # Declare: the digest edit, then the script write.
    _progress(" · walk  declare")
    leg = run_leg("script", [*common, "script"], capture=False, timeout=leg_timeout)
    if leg.code != EXIT_OK:
        return failed(leg, "the script could not be read")
    try:
        source = declare_policy(str(leg.envelope.get("text") or ""), weights, sha256)
    except WalkError as exc:
        legs.append(leg.to_json())
        report.error = str(exc)
        return EXIT_REJECTED
    script_path = out_dir / SCRIPT_FILENAME
    script_path.write_text(source, encoding="utf-8")
    leg = run_leg("declare", [*common, "script", "--set", str(script_path), "--json"],
                  timeout=leg_timeout)
    if leg.code != EXIT_OK:
        return failed(leg, "the re-declared script was refused")
    legs.append(leg.to_json())

    # Verify and roll out: the switch on, the trace exported.
    _progress(" · walk  rollout")
    leg = run_leg("rollout", [
        *common, "params", "--set", f"{POLICY_SWITCH}=1",
        "--out", str(out_dir / ROLLOUT_DIRNAME), "--json",
    ], timeout=leg_timeout)
    if leg.code != EXIT_OK:
        return failed(leg, "the policy did not verify")
    legs.append(leg.to_json())
    report.params = dict(leg.envelope.get("params") or {})
    report.accepted_revision = str(leg.envelope.get("accepted_revision") or "")
    report.digest = str(leg.envelope.get("digest") or "")
    report.revision = str(leg.envelope.get("revision") or "")

    # Review: the trace's numbers, in the envelope and as a file beside the
    # rollout, plus the accepted assembly inventory in the project docs.
    review = review_from_outputs(leg.envelope.get("outputs") or [])
    review["comparison"] = dict(report.training.get("comparison") or {})
    if "rollout_seed" in review:
        review["comparison"]["rollout_seed"] = review["rollout_seed"]
    review["weights"] = weights
    review["sha256"] = sha256
    # No trace at all is a motion answer too, and the same one write_review
    # would fall back to; setting it here keeps the note and the file equal.
    review.setdefault("motion", {"available": False,
                                 "reason": "no trace was exported."})
    with _engine_session(args, RunReport(), restore=False) as (_engine, client):
        accepted_snapshot = acquire_snapshot(client)
        if accepted_snapshot[1]["digest"] != report.digest:
            raise InventoryError("review: accepted digest differs from rollout")
        render_path, rendering = write_render(
            client, report.project_root, expected_revision=report.accepted_revision,
            accepted_snapshot=accepted_snapshot,
        )
        # The offset is derived from the accepted bounds rather than fixed:
        # a constant misses whatever is not on it, and reports `ok` while
        # doing so (ADR-267). `cadex section` keeps the explicit surface.
        section_path, section = write_section(
            client, report.project_root, plane="XZ",
            expected_revision=report.accepted_revision, accepted_snapshot=accepted_snapshot,
        )
        path, inventory = write_inventory(client, report.project_root)
        clearance_path, clearance = write_clearance(client, report.project_root)
    if clearance["revision"] != rendering["revision"]:
        raise InventoryError("review: clearance revision differs from rendered rollout")
    review["render"] = {
        "available": True, **rendering,
        "path": render_path.relative_to(Path(report.project_root)).as_posix(),
    }
    review["section"] = {
        **section, "summary_path": section_path.relative_to(Path(report.project_root)).as_posix(),
    }
    # What the mechanism declares, against what the project documents:
    # a driven joint asks for docs/actuators.md and an observed one for
    # docs/sensors.md (ADR-245's convention, ADR-256's check). The notes
    # are the design turn's to write, so a gap is reported, never filled.
    subjects, model_path = declared_note_subjects(out_dir / TRAIN_DIRNAME)
    documentation = documentation_status(report.project_root, subjects)
    if model_path is not None:
        documentation["model"] = str(model_path)
    review["documentation"] = documentation
    review["walk_seconds"] = time.monotonic() - walk_started
    review["inventory"] = {
        "available": bool(inventory.get("assembly")),
        "component_count": inventory["component_count"],
        "catalogued_count": sum(inventory.get("catalog_counts", {}).values()),
        "path": path.relative_to(Path(report.project_root)).as_posix(),
    }
    pairs = clearance["pairs"]
    available = bool(clearance.get("available"))
    offending = [row for row in pairs if row["status"] in ("intersection", "below clearance")]
    unknown = [row for row in pairs if row["status"] == "unknown"]
    review["clearance"] = {
        "available": available,
        "scope": "initial solved pose",
        "revision": clearance["revision"],
        "minimum_clearance_mm": MINIMUM_CLEARANCE_MM,
        "maximum_common_volume_mm3": MAXIMUM_COMMON_VOLUME_MM3,
        "pairs_checked": len(pairs) if available else None,
        "offending_pair_count": len(offending) if available else None,
        "offending_pairs": offending,
        "unknown_pair_count": len(unknown) if available else None,
        "unknown_pairs": unknown,
        "bounds_check": bounds_agreement(pairs, rendering.get("objects")),
        "path": clearance_path.relative_to(Path(report.project_root)).as_posix(),
    }
    # A disagreement here is the review lying about itself, not a design
    # finding, so it is said loudly and does not throw away the run's work.
    check = review["clearance"]["bounds_check"]
    report.notes.append(
        "clearance bounds check: {:s}, {:d} comparison(s) over {:d} pair(s){:s}.".format(
            str(check["status"]), int(check["comparisons"]),
            int(check.get("pairs_compared") or 0),
            "" if check["status"] != "fail"
            else ", {:d} FAILURE(S)".format(int(check["failure_count"])),
        )
    )
    # Whether the mechanism moved at all, on both channels, so a reader of
    # the run does not have to open review.json to find out that a revolute
    # rig travelled 0 mm because all of its motion was rotation. One
    # spelling for the note and the row (ADR-260): the note carries the
    # same delta the row does, off the same read of PROGRESS.md, so a
    # reader of the run never has to reconcile two wordings of one figure.
    report.notes.append(
        "motion: "
        + _motion_cell(
            review["motion"], previous_numbers(report.project_root)
        ).removeprefix("; motion ")
        + "."
    )
    # A model that declares nothing asks the project for nothing, and the
    # run says nothing rather than reporting an empty check.
    if documentation["expected"]:
        report.notes.append(
            "documentation: {:d} domain note(s) for {:d} declared subject(s); {:s}.".format(
                len(documentation["notes"]), len(documentation["expected"]),
                "none missing" if not documentation["missing"]
                else "no note for " + ", ".join(documentation["missing"]),
            )
        )
    report.walk["review"] = review
    review_path = write_review(
        out_dir, review=review, legs=legs, training=report.training,
        params=report.params,
    )
    report.walk["review_file"] = str(review_path)
    if review.get("total_reward") is None:
        report.notes.append(
            "the rollout exported no trace with a policy block; the walk "
            "verified the policy but has no number to review."
        )
    else:
        report.notes.append(
            "walk: {:s} ({:s}) verified; total_reward {:.6g} over {:d} legs.".format(
                weights, sha256[:12], float(review["total_reward"]), len(legs)
            )
        )
    report.ok = True
    return EXIT_OK


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    command = args.command or "prompt"
    if command == "prompt" and not args.prompt:
        parser.print_help(sys.stderr)
        return EXIT_USAGE

    report = RunReport(project_root=str(Path(args.project).expanduser()))
    quiet = command == "script" and not getattr(args, "source_file", "")
    try:
        if command == "prompt":
            code = command_prompt(args, report)
        elif command == "params":
            code = command_params(args, report)
        elif command == "export":
            code = command_export(args, report)
        elif command == "section":
            code = command_section(args, report)
        elif command == "render":
            code = command_render(args, report)
        elif command == "clearance":
            code = command_clearance(args, report)
        elif command == "inventory":
            code = command_inventory(args, report)
        elif command == "script":
            code = command_script(args, report)
        elif command == "link":
            code = command_link(args, report)
        elif command == "asset":
            code = command_asset(args, report)
        elif command == "train":
            code = command_train(args, report)
        elif command == "walk":
            code = command_walk(args, report)
        else:  # argparse already refuses anything else
            return EXIT_USAGE
    except (ValueError, ExportError, InventoryError, TrainError, WalkError) as exc:
        report.error = str(exc)
        code = EXIT_USAGE if isinstance(exc, ValueError) else EXIT_FAILURE
    except (EngineError, ClaudeUnavailable, ProjectBusy, CadexdError) as exc:
        report.error = str(exc)
        code = EXIT_FAILURE
    except KeyboardInterrupt:
        report.error = "cancelled."
        code = EXIT_FAILURE

    if code == EXIT_OK and report.ok and not quiet:
        _record_progress(command, args, report)
        _commit_run(command, args, report)
    if not (quiet and code == EXIT_OK):
        emit(report, as_json=bool(args.json))
    return code


#: Notes the CLI adds about the project's own housekeeping (ADR-193,
#: ADR-194), never what a turn said it did.
_HOUSEKEEPING_NOTES = (
    "scaffolded ",
    "recorded ",
    "nothing to",
    "initialised ",
    "inside an existing",
    "no git on",
    "git init",
    "committed ",
)


def _progress_what(command: str, args: argparse.Namespace, report: RunReport) -> str:
    """What this run did, in the words a person would use for the row."""

    if command == "prompt":
        said = ""
        for note in report.notes:
            if note and not note.startswith(_HOUSEKEEPING_NOTES):
                said = note.strip().splitlines()[0]
                break
        return f"prompt: {args.prompt}" + (f" → {said}" if said else "")
    if command == "params":
        return "params " + ", ".join(
            f"{name}={value}" for name, value in sorted(
                _parse_assignments(args.assignments).items()
            )
        )
    if command == "script":
        return f"script --set {Path(args.source_file).name}"
    if command == "export":
        return f"export → {args.out}"
    if command == "section":
        return f"section → review/section/ ({args.plane}, {args.offset_mm:g} mm)"
    if command == "render":
        return "render → review/render/ (front, top, right, iso)"
    if command == "clearance":
        return "clearance → docs/clearance.md"
    if command == "inventory":
        return "inventory → docs/inventory.md"
    if command == "link":
        return "link {:s} from {:s}".format(
            str(getattr(args, "output", "") or "?"), str(args.source_project)
        )
    if command == "asset":
        return "asset --put " + ", ".join(
            Path(str(item)).name for item in args.put_files
        )
    if command == "walk":
        out = Path(args.out).expanduser()
        try:
            label = str(out.resolve().relative_to(Path(report.project_root).resolve()))
        except (ValueError, OSError):
            label = out.name
        return "walk {:d} it × {:d} envs → {:s}".format(
            int(args.iterations), int(args.envs), label
        )
    if command == "train":
        # The mode is part of what happened: a row trained on the box says
        # so, and the project's ARCHITECTURE.md scaffold names the marker.
        return "train {:d} it × {:d} envs → {:s}{:s}{:s}".format(
            int(args.iterations),
            int(args.envs),
            str(Path(str(report.training.get("out") or args.out)).name),
            " (stored)" if args.put else "",
            " (remote)" if getattr(args, "remote", False) else "",
        )
    return command


def _documentation_cell(documentation: dict[str, Any]) -> str:
    """The walk row's documentation half: notes kept, subjects missing.

    Empty when the run read no model declaration at all, so a row only
    claims a documentation finding where there was something to check.
    """

    if not documentation.get("expected"):
        return ""
    missing = list(documentation.get("missing") or [])
    return "; docs notes {:d}, {:s}".format(
        len(documentation.get("notes") or []),
        "none missing" if not missing else "no " + ", ".join(missing),
    )


def _clearance_cell(
    clearance: Mapping[str, Any], previous: Mapping[str, tuple[float, str]]
) -> str:
    """The walk row's clearance half: how many pairs the check found, and
    how that compares with the last walk of this project (ADR-271).

    The offending count is the number a geometry iterate exists to turn.
    `ot4-quill` reported the same 960 mm³ housing/quill intersection on
    every walk row for a day; the design turn that answered it wrote a
    row saying `clearance offending 0`, which on its own is
    indistinguishable from a rig that never had a finding. The count
    carries its delta now, spelled by the same machinery as the travel
    figures, and reads back off the older rows unchanged because the
    label was always in front of the number.

    `unknown` and `pairs checked` stay plain: they say what the check
    could reach, not what it found, and a delta on either without the
    other would read as a claim about the mechanism.
    """

    if not clearance.get("available"):
        return "clearance unavailable"
    return "{:s}; unknown {:d}; pairs checked {:d} (initial solved pose; {:g} mm / {:g} mm³)".format(
        compared_number(
            "clearance offending", float(clearance["offending_pair_count"]), previous
        ),
        int(clearance["unknown_pair_count"]),
        int(clearance["pairs_checked"]),
        float(clearance["minimum_clearance_mm"]),
        float(clearance["maximum_common_volume_mm3"]),
    )


def _motion_cell(
    motion: dict[str, Any], previous: Mapping[str, tuple[float, str]]
) -> str:
    """The walk row's motion half: did the mechanism move, and how — and
    how that compares with the last walk of this project (ADR-260).

    Both channels every time. A row that carried millimetres alone would
    report the repository's own hinged-arm example — a working revolute
    rig — as having gone nowhere, because it travels 0.0000 mm and rotates
    178.8334°. Neither figure is a score and they are not ranked against
    each other, so the row names the largest mover on each channel and
    says over how many frames.

    Spelled `travel_mm N`/`travel_deg N` rather than `N mm`/`N°`, because
    that is what :data:`COMPARED_NUMBERS` can read back off a row: the
    unit moved into the label so a later walk can carry a delta. The
    review JSON keeps `millimetres` and `degrees` under their own keys and
    is unaffected; the run note is this same cell, so there is one
    spelling to learn. Neither delta is a verdict: the carriage iterate
    held its travel at 103 mm while its reward fell, and the row can now
    say both without saying which mattered.
    """

    if not motion.get("available"):
        return "; motion unavailable"
    translation = motion.get("largest_translation") or {}
    rotation = motion.get("largest_rotation") or {}
    return "; motion {:s} on {:s}, {:s} on {:s} over {:d} solved frame(s)".format(
        compared_number(
            "travel_mm", float(translation.get("millimetres") or 0.0), previous
        ),
        str(translation.get("component") or "?"),
        compared_number("travel_deg", float(rotation.get("degrees") or 0.0), previous),
        str(rotation.get("component") or "?"),
        int(motion.get("frames_counted") or 0),
    )


def _record_progress(command: str, args: argparse.Namespace, report: RunReport) -> None:
    """One `PROGRESS.md` row per accepted run (ADR-193).

    Written after the command, from the report, so the row says what
    actually happened. A store listing (`asset` with no `--put`) changes
    nothing and gets no row. Never fatal: a row that cannot be written is a
    note, not a failed run.
    """

    if command == "asset" and not getattr(args, "put_files", None):
        return
    # Read once, before the row is appended: both branches compare against
    # the last row that carried each number, and the walk branch is why
    # travel figures are comparable at all (ADR-260).
    previous = previous_numbers(report.project_root)
    try:
        append_progress_row(
            report.project_root,
            run=command,
            what=_progress_what(command, args, report),
            revision=report.accepted_revision,
            digest=report.digest,
            numbers=((
                _clearance_cell(report.walk["review"]["clearance"], previous)
                + _motion_cell(report.walk["review"].get("motion") or {}, previous)
                + _documentation_cell(report.walk["review"].get("documentation") or {})
            ) if command == "walk" else progress_numbers(
                training=report.training,
                outputs=report.outputs,
                previous=previous,
            )) + (comparison_cell(
                report.project_root, command,
                report.walk.get("review", {}).get("comparison", {})
                if command == "walk" else report.training.get("comparison", {}),
            ) if command in ("walk", "train") else ""),
        )
    except OSError as exc:
        report.notes.append(f"PROGRESS.md not written: {exc}")


def _commit_run(command: str, args: argparse.Namespace, report: RunReport) -> None:
    """One commit per accepted run in the project's own repository (ADR-194).

    After the row, so the row is in the commit; the message is the row's
    words. A listing changes nothing and commits nothing; a project that
    is not its own repository (inside another work tree, or no git) gets
    no commit and said so on its first visit. Never fatal.
    """

    if command == "asset" and not getattr(args, "put_files", None):
        return
    # A walk's legs each committed; what is left is its review.json, when
    # --out lies under the project, plus generated project review artifacts.
    try:
        sha = commit_project(
            report.project_root, f"cadex {_progress_what(command, args, report)}"
        )
    except OSError:
        return
    if sha:
        report.notes.append(f"committed {sha}.")


if __name__ == "__main__":
    raise SystemExit(main())
