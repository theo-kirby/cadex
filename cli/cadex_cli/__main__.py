# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""``cadex`` — the command line.

Six subcommands over one project, of which exactly one spends tokens::

    cadex -p "a mounting bracket for a NEMA17, 4 mm wall" --out ./out
    cadex params --set fin_angle=12 --out ./sweep/12
    cadex script --set bracket.py --out ./out
    cadex export --out ./out
    cadex link --from ../sensorA --output sensor
    cadex asset --put walk.cxpolicy --put walk-task.json

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
from .export import ExportError, export_blueprints, export_outputs, parse_formats
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
    resolve_trainer_python,
    run_trainer,
    trainer_command,
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
    export_parser.add_argument(
        "--blueprints",
        action="store_true",
        default=False,
        help="Also copy the project's stored blueprint sheets into --out "
        "(the shell renders them; this only reads the store).",
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
    train_parser.add_argument("--seed", type=int, default=0, help="RNG seed (0).")
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
    if args.iterations < 1 or args.envs < 1:
        report.error = "--iterations and --envs must be at least 1."
        return EXIT_USAGE
    policy_name = str(args.policy_name or "")
    if policy_name and not policy_name.endswith(".cxpolicy"):
        report.error = "--name must end in .cxpolicy."
        return EXIT_USAGE
    python = resolve_trainer_python(args.trainer_python or None)

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
    command = trainer_command(
        python,
        task.files["json"],
        policy_path,
        iterations=args.iterations,
        envs=args.envs,
        seed=args.seed,
        label=args.label,
        init_from=args.init_from,
    )
    _progress(
        f" · train  {task.name}  {args.iterations} it × {args.envs} envs"
        f"  ({python})"
    )
    report.training = run_trainer(command, timeout=args.timeout)
    report.training.setdefault("out", str(policy_path))
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
        elif command == "link":
            code = command_link(args, report)
        elif command == "asset":
            code = command_asset(args, report)
        elif command == "train":
            code = command_train(args, report)
        else:  # argparse already refuses anything else
            return EXIT_USAGE
    except (ValueError, ExportError, TrainError) as exc:
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
