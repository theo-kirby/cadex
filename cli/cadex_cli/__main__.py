# SPDX-License-Identifier: LGPL-2.1-or-later

"""``cadex`` — the command line.

Four subcommands over one project, of which exactly one spends tokens::

    cadex -p "a mounting bracket for a NEMA17, 4 mm wall" --out ./out
    cadex params --set fin_angle=12 --out ./sweep/12
    cadex script --set bracket.py --out ./out
    cadex export --out ./out

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
from contextlib import contextmanager
import os
from pathlib import Path
import signal
import sys
from typing import Any, Iterator, Sequence

from .agent import (
    ClaudeTurn,
    ClaudeUnavailable,
    DEFAULT_MODEL,
    find_claude,
    system_prompt,
)
from .bridge import Bridge, ToolCall
from .client import CadexdClient, CadexdError, open_project
from .engine import Engine, EngineError, resolve_engine
from .export import ExportError, export_outputs, parse_formats
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
    read_script_source,
    read_script_state,
    read_working_revision,
    write_agent_state,
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
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Model for the turn.")
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
    _common(export_parser, inherit=True)

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
    return parser


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
    args: argparse.Namespace, report: RunReport
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
            opened = open_project(client, project_root)
            report.params = params_from_script(opened.get("script"))
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
                system_prompt_text=system_prompt(api),
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

        accepted = bridge.state.last_accepted
        report.revision = bridge.state.revision or report.revision
        if accepted is not None:
            apply_modeling_reply(report, accepted)
        _refresh_script_state(client, report)

        if not result.ok:
            report.error = result.error or "the agent turn failed."
            return EXIT_FAILURE
        if accepted is None:
            report.error = (
                "the turn finished without the engine accepting a script."
            )
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

    with _engine_session(args, report) as (engine, client):
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
        elif command == "script":
            code = command_script(args, report)
        else:  # argparse already refuses anything else
            return EXIT_USAGE
    except (ValueError, ExportError) as exc:
        report.error = str(exc)
        code = EXIT_USAGE if isinstance(exc, ValueError) else EXIT_FAILURE
    except (EngineError, ClaudeUnavailable, ProjectBusy, CadexdError) as exc:
        report.error = str(exc)
        code = EXIT_FAILURE
    except KeyboardInterrupt:
        report.error = "cancelled."
        code = EXIT_FAILURE

    if not (quiet and code == EXIT_OK):
        emit(report, as_json=bool(args.json))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
