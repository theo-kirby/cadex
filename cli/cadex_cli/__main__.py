# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""``cadex`` — the command line.

Cadex has no agent of its own (ADR-538). The agent is the person's --
Claude Code, Codex, Pi -- and it drives a project two ways: through
``cadex mcp``'s tools, and through these commands, none of which spends a
token::

    cadex mcp --project ./bracket          # the tools, over MCP stdio
    cadex guidance                         # the text an agent is given
    cadex params --set fin_angle=12 --out ./sweep/12
    cadex script --set bracket.py --out ./out
    cadex export --out ./out
    cadex inventory
    cadex clearance
    cadex link --from ../sensorA --output sensor
    cadex asset --put walk.cxpolicy --put walk-task.json
    cadex train --out ./run --iterations 200 --envs 64 --put
    cadex smoke --out ./smoke
    cadex app                              # the dashboard, read-only

The agent authors a *parametric* script once; after that a sweep is
``set_params`` and a re-export, with no model in the loop at all.

Exit codes are part of the interface, so a pipeline can branch on the reason
rather than on stderr: ``0`` fine, ``1`` the engine failed, ``2`` the
command was wrong, ``3`` the engine refused the script. Progress goes to
stderr and the report goes to stdout, so ``--json`` is always safe to pipe.
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
import threading
import time
from typing import Any, Iterator, Mapping, Sequence

from contextlib import ExitStack

from .bridge import MODELLING_OPS, Bridge, ToolCall
from .client import CadexdClient, CadexdError, open_project
from .engine import Engine, EngineError, resolve_engine, source_comparison
from .export import ExportedOutput, ExportError, export_blueprints, export_outputs, parse_formats
from .inventory import InventoryError, read_inventory, write_inventory
from .render import acquire_snapshot, describe_proxies, write_render
from .section import write_section
from .revisions import (
    previous as previous_revision,
    read_history as read_revision_history,
    read_source as read_revision_source,
    select as select_revision,
)
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
    BUDGET_KEYS,
    ProjectBusy,
    effective_budgets,
    project_lock,
    read_agent_state,
    read_project_assets,
    read_script_source,
    read_script_state,
    read_working_revision,
    write_agent_budgets,
)
from .train import (
    TrainError,
    find_task,
    ungrounded_channels,
    remote_trainer_command,
    training_plan,
    resolve_trainer_python,
    verify_returned_policy,
    resolve_bundle_model,
    run_trainer,
    trainer_command,
)
from .checkpoints import CheckpointRollouts
from .evaluate import (
    DEFAULT_TIMEOUT_S as EVALUATE_TIMEOUT_S,
    MAXIMUM_TIMEOUT_S as EVALUATE_MAXIMUM_TIMEOUT_S,
    REPORT_NAME as EVALUATION_NAME,
    EvaluateError,
    EvaluateRefused,
    add_film,
    check_out,
    default_out,
    evaluation_cell,
    failing_predicates,
    read_report,
    retained_inputs,
    run_evaluation,
)
from .loop import SLOT_BUSY, LoopError, lock_held, machine_lock_path, machine_slot
from .review_record import manifest_identity, read_accepted_identity, write_run_record
from .review_server import serve as serve_review, serve_projects
from .smoke import (
    DEFAULT_FPS,
    DEFAULT_MAX_TILT_DEGREES,
    DEFAULT_MODE,
    DEFAULT_PENETRATION_MM,
    DEFAULT_REST_SPEED_MM_S,
    DEFAULT_SECONDS,
    DEFAULT_TIMEOUT_S,
    MAXIMUM_TIMEOUT_S,
    RECEIPT_NAME,
    SmokeError,
    find_model,
    find_optional_task,
    run_smoke,
    retained_bundle,
    check_geometry,
    smoke_cell,
    smoke_command,
    smoke_interpreter,
)
from .guidance import brief as guidance_brief, instructions as guidance_text
from .mcp import serve as serve_mcp
from .tools import STANDARD_DISPLAY, tool_definitions
from .walk import (
    DEFAULT_LEG_TIMEOUT_S,
    PROGRESS_FILENAME,
    POLICY_SWITCH,
    ROLLOUT_DIRNAME,
    SCRIPT_FILENAME,
    SWEEP_DIRNAME,
    TRAIN_DIRNAME,
    WalkError,
    collect_detached,
    declare_policy,
    declared_note_subjects,
    behaviour_authority,
    floating_bases,
    gait_from_trace,
    read_json,
    read_pending,
    review_from_outputs,
    run_leg,
    task_bundle,
    train_leg_timeout,
    write_pending,
    write_review,
)

#: Where a run works when ``--project`` is not given. Hidden, and beside
#: whatever the caller is doing, so `cadex script --set s.py --out ./out` in
#: an empty directory is a complete command.
DEFAULT_PROJECT_DIRNAME = ".cadex"
#: Where `cadex app` (and a bare `cadex`) looks for projects when neither
#: ``--projects`` nor ``CADEX_PROJECTS`` names a directory: under home.
DEFAULT_PROJECTS_DIRNAME = "cadex-projects"


def _progress(message: str) -> None:
    """Progress goes to stderr; stdout belongs to the report."""

    sys.stderr.write(message + "\n")
    sys.stderr.flush()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cadex",
        description="Cadex, headless. One parametric project script, driven "
        "by your own agent (cadex mcp) or by parameters alone. A bare `cadex` "
        "serves the dashboard.",
    )
    _common(parser)
    subparsers = parser.add_subparsers(dest="command")

    mcp_parser = subparsers.add_parser(
        "mcp",
        help="Serve this project's tools to an agent over MCP stdio (ADR-538): "
        "register `cadex mcp --project DIR` with Claude Code, Codex or any "
        "MCP client. The engine opens on the first tool call and closes after "
        "--idle quiet seconds, landing a PROGRESS.md row and a project commit "
        "when the session changed the design.",
    )
    _common(mcp_parser, inherit=True)
    mcp_parser.add_argument(
        "--idle", type=float, default=30.0, metavar="SECONDS",
        help="Close the engine, and release the project, after this many "
        "seconds without a call (default 30; 0 holds it until the client "
        "goes). The next call reopens it.",
    )

    subparsers.add_parser(
        "guidance",
        help="Print the whole guidance an agent driving Cadex follows; "
        "`cadex mcp`'s instructions are a short brief that tells the agent "
        "to run this. No engine.",
    )

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
    section_parser.add_argument(
        "--offset-mm",
        type=float,
        default=None,
        metavar="N",
        help="Where along the plane normal to cut. Omitted, the offset is "
        "derived from the accepted bounds the way the walk derives it "
        "(ADR-273): every candidate is cut and the one covering the most "
        "objects wins.",
    )

    clearance_parser = subparsers.add_parser(
        "clearance", help="Check accepted assembly pairs; write docs/clearance.md.",
    )
    _common(clearance_parser, inherit=True)
    clearance_parser.add_argument("--sweep", action="store_true",
                                  help="Read published joint sweeps into docs/clearance-sweep.md; never rebuild.")
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
    train_parser.add_argument(
        "--detach", action="store_true",
        help="With --remote: launch and return a pending run receipt in --out. "
        "Does not verify or store a policy; --out must be inside the project.",
    )
    _remote_flags(train_parser)
    _grounding_flag(train_parser)
    _checkpoint_flag(train_parser)
    train_parser.add_argument(
        "--stop-on-collapse", dest="stop_on_collapse", action="store_true",
        default=False,
        help="Stop training, with the reason, once the mean episode has "
        "collapsed: the policy is ending its own episodes (ADR-410). "
        "`cadex walk` always passes it.",
    )

    smoke_parser = subparsers.add_parser(
        "smoke",
        help="Read the accepted artifacts into --out and "
        "run a short bounded stock-MuJoCo rollout of it: hold the solved "
        "pose (or apply zero action) and report whether the state stayed "
        "finite, exact components did not overlap beyond tolerance, the design rests "
        "on the environment floor or holds its grounded base, and no "
        "declared termination fired. No AI, no tokens, no trainer.",
    )
    _common(smoke_parser, inherit=True)
    smoke_parser.add_argument(
        "--seconds", type=float, default=DEFAULT_SECONDS,
        help="Simulated duration (default %(default)g s).",
    )
    smoke_parser.add_argument(
        "--mode", choices=("hold", "zero"), default=DEFAULT_MODE,
        help="hold: position actuators hold the solved pose; zero: every "
        "actuator gets zero command (default %(default)s).",
    )
    smoke_parser.add_argument(
        "--penetration-mm", dest="penetration_mm", type=float,
        default=DEFAULT_PENETRATION_MM,
        help="Deepest floor-proxy penetration of the environment floor (default %(default)g mm).",
    )
    smoke_parser.add_argument("--max-common-volume-mm3", type=float, default=1e-6,
                              help="Maximum exact component common volume (default %(default)g mm³).")
    smoke_parser.add_argument(
        "--rest-speed-mm-s", dest="rest_speed_mm_s", type=float,
        default=DEFAULT_REST_SPEED_MM_S,
        help="A free base moving slower than this at the end is at rest "
        "(default %(default)g mm/s).",
    )
    smoke_parser.add_argument(
        "--max-tilt-degrees", dest="max_tilt_degrees", type=float,
        default=DEFAULT_MAX_TILT_DEGREES,
        help="A free base that has turned further than this from its accepted "
        "pose by the end has fallen over (default %(default)g°).",
    )
    smoke_parser.add_argument(
        "--fps", type=int, default=DEFAULT_FPS,
        help="Samples per simulated second at which the checks look "
        "(default %(default)d).",
    )
    smoke_parser.add_argument(
        "--timeout", type=float, default=DEFAULT_TIMEOUT_S, metavar="SECONDS",
        help="Kill the rollout after this much wall time and fail; at most "
        f"{MAXIMUM_TIMEOUT_S:g} (default %(default)g).",
    )
    smoke_parser.add_argument(
        "--model", dest="model_name", default="", metavar="NAME",
        help="Which exported MJCF model, when the script exports more than one.",
    )
    smoke_parser.add_argument(
        "--task", dest="task_name", default="", metavar="NAME",
        help="Which exported task supplies the termination rules, when the "
        "script exports more than one.",
    )
    evaluate_parser = subparsers.add_parser(
        "evaluate",
        help="Hold the accepted policy against its task's success spec "
        "(assembly.success): one rollout per frozen seed under the spec's "
        "conditions, then pass or fail per seed and per predicate, the "
        "behaviour metrics, the reward by term and how each episode ended, "
        "written to evaluation.json in the project, with a filmstrip and a "
        "video of what the seeds did on the dark prototype floor. Reads the "
        "accepted artifacts; never rebuilds. No AI, no tokens, no trainer.",
    )
    _common(evaluate_parser, inherit=True)
    evaluate_parser.add_argument(
        "--policy", dest="policy_name", default="", metavar="NAME",
        help="Which declared policy output, when the script declares more than one.",
    )
    evaluate_parser.add_argument(
        "--task", dest="task_name", default="", metavar="NAME",
        help="Pick the policy declared against this task output.",
    )
    evaluate_parser.add_argument(
        "--timeout", type=float, default=EVALUATE_TIMEOUT_S, metavar="SECONDS",
        help="Kill the evaluation after this much wall time and fail; at most "
        f"{EVALUATE_MAXIMUM_TIMEOUT_S:g} (default %(default)g).",
    )
    evaluate_parser.add_argument(
        "--film", default="auto", metavar="SEEDS",
        help="Which seeds to draw as a filmstrip on the dark prototype floor: "
        "auto (the first failing seed, or the first seed of a pass), all, none, "
        "or seed numbers separated by commas. The first one is also drawn as "
        "a video (default %(default)s).",
    )
    evaluate_parser.add_argument(
        "--no-video", action="store_true", default=False,
        help="Draw the filmstrips and no video.",
    )
    evaluate_parser.add_argument(
        "--detail-start", type=float, default=None, metavar="SECONDS",
        help="Where each filmstrip's detail sheet begins (default: the seed's "
        "first disturbance, or the middle of an episode that has none).",
    )
    evaluate_parser.add_argument(
        "--detail-step", type=float, default=None, metavar="SECONDS",
        help="The time between the detail sheet's frames (default 0.2).",
    )
    evaluate_parser.add_argument(
        "--film-only", action="store_true", default=False,
        help="Measure nothing: draw the film of the evaluation already in "
        "--out (or the default directory) from the traces it kept.",
    )
    walk_parser = subparsers.add_parser(
        "walk",
        help="The lifecycle walk as one command: an optional parameter "
        "change, train, re-declare the policy, verify and roll out, review. "
        "Each leg is a child cadex command. No tokens.",
    )
    _common(walk_parser, inherit=True)
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
    _checkpoint_flag(walk_parser)
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
    walk_parser.add_argument(
        "--detach",
        action="store_true",
        default=False,
        help="With --remote: launch training on the box and stop at pending. "
        "The walk writes walk-pending.json under --out with the run locator "
        "and the two commands that finish the run; no policy is verified, "
        "stored, declared or rolled out.",
    )
    walk_parser.add_argument(
        "--complete",
        action="store_true",
        default=False,
        help="Finish a detached walk: read walk-pending.json under --out, "
        "take the policy the dispatcher brought home, and run the remaining "
        "legs (store, declare, verify and roll out, review). Runs no "
        "trainer.",
    )
    _remote_flags(walk_parser)
    _grounding_flag(walk_parser)

    review_parser = subparsers.add_parser(
        "review",
        help="Serve this project's review dashboard, read-only, to a browser "
        "on the private network (ADR-286). No engine, no tokens.",
    )
    _common(review_parser, inherit=True)
    review_parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Address to bind. Default 127.0.0.1 (this machine only); give "
        "the machine's Tailscale or LAN address to reach it from another "
        "device, or 0.0.0.0 for every interface.",
    )
    review_parser.add_argument(
        "--port",
        type=int,
        default=8765,
        help="TCP port. Default 8765; 0 takes a free port and reports it.",
    )

    budgets_parser = subparsers.add_parser(
        "budgets",
        help="Show or store the project's engine budgets (ADR-517): the "
        "seconds and megabytes one engine script run may spend. Every later "
        "run opens with them; --engine-timeout / --engine-memory override "
        "them for one call. No engine, no tokens.",
    )
    _common(budgets_parser, inherit=True)
    budgets_parser.add_argument(
        "--set",
        dest="budget_assignments",
        action="append",
        default=[],
        metavar="NAME=VALUE",
        help="Repeatable. timeout_seconds=SECONDS or memory_limit_mb=MB; 0 "
        "unsets one, leaving the engine's default in force.",
    )

    revision_parser = subparsers.add_parser(
        "revision",
        help="Review the accepted revisions (ADR-506): list the trail, reject "
        "the current one (put back the one before), or restore any stored one.",
    )
    _common(revision_parser, inherit=True)
    revision_parser.add_argument(
        "action", choices=("list", "reject", "restore"),
        help="list: the stored trail. reject: put back the revision accepted "
        "before it. restore: put back the named one.",
    )
    revision_parser.add_argument(
        "selector", nargs="?", default="",
        help="An ordinal or a revision prefix. restore needs one; reject "
        "takes one only to check it is the accepted revision.",
    )

    app_parser = subparsers.add_parser(
        "app",
        help="Serve the dashboard over a directory of projects, read-only: "
        "an index of every project in it, each project's review page under "
        "/p/<name>/. What a bare `cadex` does. No engine, no tokens.",
    )
    _common(app_parser, inherit=True)
    app_parser.add_argument(
        "--projects",
        default=None,
        help=f"The projects directory (created if absent). Default: "
        f"CADEX_PROJECTS, then ~/{DEFAULT_PROJECTS_DIRNAME}.",
    )
    app_parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Address to bind. Default 127.0.0.1 (this machine only); put "
        "`tailscale serve` in front of it to view it from another device.",
    )
    app_parser.add_argument(
        "--port",
        type=int,
        default=8765,
        help="TCP port. Default 8765; 0 takes a free port and reports it.",
    )
    return parser


def _grounding_flag(parser: argparse.ArgumentParser) -> None:
    """``--allow-ungrounded``, the same on ``train`` and ``walk`` (ADR-408)."""

    parser.add_argument(
        "--allow-ungrounded",
        dest="allow_ungrounded",
        action="store_true",
        default=False,
        help="Train even though a policy channel names no onboard sensor that "
        "measures it. Without this the leg refuses: the policy would learn "
        "from an input the robot it deploys to cannot read.",
    )


def _checkpoint_flag(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--checkpoint-every", dest="checkpoint_every", type=int, default=0,
        metavar="N",
        help="Write a checkpoint every N iterations (0: none). A local run "
        "rolls each one out through the engine on the CPU while it trains, "
        "and leaves its trace beside it (ADR-544).",
    )


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
        "--engine-timeout",
        dest="engine_timeout",
        type=float,
        default=default(0.0),
        metavar="SECONDS",
        help="Wall-clock budget for one engine script run, this call only. "
        "Default: the project's stored budget (`cadex budgets`), then the "
        "engine's own.",
    )
    parser.add_argument(
        "--engine-memory",
        dest="engine_memory",
        type=int,
        default=default(0),
        metavar="MB",
        help="Memory ceiling for one engine script run, this call only. "
        "Default: the project's stored budget, then the engine's own.",
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
        # The project's engine budgets, each overridden for this call by its
        # flag (ADR-517); a bad flag is refused before an engine starts.
        stored = read_agent_state(project_root).budgets
        overrides = _budget_overrides(args)
        budgets = effective_budgets(stored, overrides)
        client = CadexdClient(engine)
        try:
            client.start()
            opened = open_project(client, project_root, restore=restore, budgets=budgets)
            report.params = params_from_script(opened.get("script"))
            report.budgets = _budgets_report(stored, overrides, opened.get("budgets"))
            stale = stale_policy_note(opened)
            if stale:
                report.notes.append(stale)
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


def stale_policy_note(opened: Mapping[str, Any]) -> str:
    """The envelope's note when the open skipped a restore for a stale policy.

    ``open_project`` opens such a project unrestored rather than locking it
    (ADR-520); the note says which output, why, and the two ways out, so a
    pipeline reading only the notes still learns it.
    """

    restore = opened.get("restore")
    stale = restore.get("stale_policy") if isinstance(restore, Mapping) else None
    if not isinstance(stale, Mapping):
        return ""
    return (
        f"policy output {stale.get('output')!r} is stale ({stale.get('reason')}): "
        "it was trained on a task this engine no longer builds, so the project "
        "opened without its restore pass (ADR-520). Retrain it, or set the "
        "policy aside, before the next rebuild."
    )


def _budget_overrides(args: argparse.Namespace) -> dict[str, Any]:
    """``--engine-timeout`` / ``--engine-memory``, the ones this call gives."""

    overrides = {"timeout_seconds": float(getattr(args, "engine_timeout", 0.0) or 0.0),
                 "memory_limit_mb": int(getattr(args, "engine_memory", 0) or 0)}
    return {key: value for key, value in overrides.items() if value}


def _budgets_report(stored: Mapping[str, Any], overrides: Mapping[str, Any],
                    in_force: Any) -> dict[str, Any]:
    """The envelope's ``budgets``: what is in force and where each came from."""

    return {"in_force": dict(in_force) if isinstance(in_force, Mapping) else {},
            "stored": dict(stored),
            "source": {key: "override" if key in overrides else "project" if key in stored
                       else "engine" for key in BUDGET_KEYS}}


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


def command_budgets(args: argparse.Namespace, report: RunReport) -> int:
    """``cadex budgets [--set NAME=VALUE ...]``: the project's engine budgets (ADR-517).

    Stored in the project's ``agent.json`` beside the conversation, read by
    every later run's ``open_project``. With no ``--set`` it only reports.
    It touches no engine, so what it reports is what is *stored*; a run's
    own envelope says what was in force.
    """

    root = Path(args.project).expanduser()
    if not root.is_dir():
        raise ValueError(f"no project at {root}.")
    changes: dict[str, Any] = {}
    for assignment in args.budget_assignments:
        name, sep, value = str(assignment).partition("=")
        if not sep:
            raise ValueError(f"--set wants NAME=VALUE, not {assignment!r}.")
        changes[name.strip()] = value.strip()
    if changes:
        stored = write_agent_budgets(root, changes).budgets
        report.notes.append("stored " + ", ".join(
            f"{key}={stored[key]:g}" if key in stored else f"{key} unset" for key in changes) + ".")
    else:
        stored = read_agent_state(root).budgets
    report.budgets = {"stored": dict(stored)}
    report.ok = True
    return EXIT_OK


def command_revision(args: argparse.Namespace, report: RunReport) -> int:
    """``cadex revision list|reject|restore``: going back through the trail (ADR-506).

    ``list`` touches no engine: the trail is a file the engine keeps.
    ``reject`` and ``restore`` put a
    stored version back through the engine's ordinary ``write_script`` —
    with ``replace``, since going back may drop outputs on purpose — and
    then its recorded values through ``set_params``, so the project lands
    on the revision named, and say so in ``exact`` when it cannot.
    """

    root = Path(args.project).expanduser()
    if not root.is_dir():
        raise ValueError(f"no project at {root}.")
    action = args.action
    if action == "list":
        report.revisions = {"history": read_revision_history(root)}
        identity = read_accepted_identity(root)
        report.accepted_revision = identity.get("revision", "") if identity.get("available") else ""
        report.ok = True
        return EXIT_OK
    want = str(args.selector or "").strip().lower()
    with _engine_session(args, report, restore=False) as (engine, client):
        identity = read_accepted_identity(root)
        current = identity.get("revision", "") if identity.get("available") else ""
        entries = read_revision_history(root)
        if action == "reject":
            if not current:
                raise ValueError("there is no accepted revision to reject.")
            if want and not current.startswith(want):
                raise ValueError(f"only the accepted revision ({current[:12]}) can be rejected; "
                                 "restore an older one instead.")
            target = previous_revision(entries, current)
        else:
            target = select_revision(entries, want)
        goal = str(target.get("revision") or "")
        report.revisions = {"action": action, "target": goal, "ordinal": target.get("ordinal"),
                            "from": current}
        if goal == current or (target.get("digest") and identity.get("available")
                               and target.get("digest") == identity.get("digest")
                               and action == "restore"):
            report.accepted_revision = current
            report.revisions.update(accepted=current, exact=True)
            report.notes.append(f"nothing to {action}: revision {goal[:12]}"
                                + (" is already accepted." if goal == current else
                                   "'s geometry is already accepted."))
            report.ok = True
            return EXIT_OK
        source = read_revision_source(root, target)

        def write(op: str, request: dict[str, Any]) -> dict[str, Any] | None:
            _progress(f" · {op}")
            request.update(expected_revision=read_working_revision(client),
                           display=dict(STANDARD_DISPLAY))
            reply = client.request(op, request)
            apply_modeling_reply(report, reply)
            if reply.get("ok") is not True:
                report.error = str(reply.get("error") or reply.get("failure_code") or f"{op} failed")
                _refresh_script_state(client, report)
                return None
            return reply

        reply = write("write_script", {"source": source, "replace": True})
        if reply is None:
            return EXIT_REJECTED
        values = target.get("values")
        if report.accepted_revision != goal and isinstance(values, dict):
            # The source came back with today's values; put the revision's own
            # back too. A parameter it did not store was at its default, and a
            # stored value cannot be unset, so it is set to the default: the
            # same model, under a revision that says the value explicitly.
            # Rows are sent only when it had some, since an empty list is a
            # table to clear, not a value to keep.
            state = read_script_state(client)["params"]
            recorded = dict(values.get("params") or {})
            patch: dict[str, Any] = {}
            for spec in state.get("specs") or []:
                name = str(spec.get("name") or "") if isinstance(spec, dict) else ""
                if not name:
                    continue
                want_value = recorded.get(name, spec.get("default"))
                if want_value is not None and \
                        (state.get("values") or {}).get(name, spec.get("default")) != want_value:
                    patch[name] = want_value
            request: dict[str, Any] = {"values": patch}
            for key in ("nets", "boards", "mounts", "cages"):
                if values.get(key):
                    request[key] = list(values[key])
            if patch or len(request) > 1:
                reply = write("set_params", request)
                if reply is None:
                    return EXIT_REJECTED
        _refresh_script_state(client, report)
        exact = report.accepted_revision == goal
        same = bool(target.get("digest")) and report.digest == target.get("digest")
        report.revisions.update(accepted=report.accepted_revision, exact=exact,
                                same_geometry=exact or same,
                                values_recorded=isinstance(values, dict))
        if not exact:
            report.notes.append(
                f"restored revision {goal[:12]} as {report.accepted_revision[:12]}: "
                + ("the same geometry, with a value it left at its default now set explicitly."
                   if same else
                   "its values were not recorded (accepted before ADR-506), so today's are kept."
                   if not isinstance(values, dict) else
                   "its recorded values did not reproduce it.")
            )
        _finish(args, report, engine, reply.get("display"))
        report.ok = True
        return EXIT_OK


def command_params(args: argparse.Namespace, report: RunReport) -> int:
    """Change declared parameter values. No model is spawned at all."""

    values = _parse_assignments(args.assignments)
    with _engine_session(args, report) as (engine, client):
        revision = read_working_revision(client)
        _progress(f" · set_params  {', '.join(sorted(values))}")
        # Retain triangles in this accepted attempt so a following walk can
        # freeze its assembled training view without rebuilding the revision.
        reply = client.request(
            "set_params", {"values": values, "expected_revision": revision,
                           "display": {"quality": "standard", "edges": False}}
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
        report.notes.append(f"render: {value['triangles']} triangles, four views and a hero; {path}.")
        report.notes.append("measures: " + describe_proxies(value["proxies"]) + ".")
        report.ok = True
        return EXIT_OK


def command_section(args: argparse.Namespace, report: RunReport) -> int:
    """Cut the accepted geometry, at a given offset or at a derived one.

    ``--offset-mm`` is optional, and omitting it is the ordinary way to call
    this: the walk has derived its offset since ADR-267, but the flag used to
    default to the constant 0.0, so a person or agent calling the eye by hand
    got exactly the fixed plane that derivation exists to replace -- on
    ``ot4-swing2`` a plane that cuts none of the ten parts. The note says
    which offset was cut and whether it was asked for or derived, because a
    section is a claim about what was *not* on the page as much as what was.
    """

    with _engine_session(args, report) as (_engine, client):
        path, value = write_section(client, report.project_root, plane=args.plane, offset=args.offset_mm)
        report.revision = report.accepted_revision = value["revision"]
        report.digest = value["digest"] or ""
        report.notes.append(
            "section: {:s} {:g} mm ({:s}); {:s}; {:d}/{:d} objects cut; {:s}.".format(
                str(value["plane"]), float(value["offset_mm"]),
                str(value.get("offset_source") or "explicit"),
                str(value["status"]), int(value["objects_cut"]),
                len(value.get("objects") or {}), str(path),
            )
        )
        report.ok = True
        return EXIT_OK


def command_clearance(args: argparse.Namespace, report: RunReport) -> int:
    with _engine_session(args, report, restore=False) as (_engine, client):
        path, value = write_clearance(
            client, report.project_root, target=args.assembly,
            minimum=args.min_clearance_mm, maximum_volume=args.max_common_volume_mm3,
            sweep=args.sweep,
        )
        coverage = f" sweep coverage={value['clearance_sweep'].get('status', 'unavailable')}" if args.sweep else ""
        report.notes.append(f"clearance{coverage}: {len(value['pairs'])} static pair(s), written to {path}.")
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
        # The same tessellation request the agent's writes carry (ADR-312):
        # the accepted attempt is what the review dashboard draws.
        request: dict[str, Any] = {
            "source": source,
            "expected_revision": revision,
            "display": dict(STANDARD_DISPLAY),
        }
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
    and that change is ``cadex script --set`` or the agent's ``edit_script``.

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
    --set`` or the agent's ``edit_script``, the same as ``cadex asset``.
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
    if args.checkpoint_every < 0:
        report.error = "--checkpoint-every must be 0 (none) or a number of iterations."
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
    if args.detach:
        if args.dry_run:
            report.error = "--detach cannot be combined with --dry-run."
            return EXIT_USAGE
        if not Path(args.out).expanduser().resolve().is_relative_to(
            Path(args.project).expanduser().resolve()
        ):
            report.error = "--detach needs --out inside the project for its run receipt."
            return EXIT_USAGE
    python = None if args.remote else resolve_trainer_python(args.trainer_python or None)
    if not args.remote and not args.dry_run and lock_held(machine_lock_path()):
        # Refused before the rebuild; the slot itself is taken around the
        # trainer below (ADR-543).
        report.error = f"{SLOT_BUSY}; wait for it to end."
        return EXIT_REJECTED

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
        # A walk froze this input before launching the train leg. A design
        # accepted in between must not train under the earlier run's identity.
        retained_view = Path(args.out).expanduser().parent / "training-view.json"
        if retained_view.is_file():
            retained = json.loads(retained_view.read_text())["identity"]
            if retained.get("available") and (
                retained["revision"] != report.accepted_revision
                or retained["digest"] != report.digest
            ):
                report.error = "design changed after review inputs were retained; start a new walk"
                return EXIT_REJECTED
    try:
        task = find_task(report.outputs, args.task_name)
        ungrounded = ungrounded_channels(task.files["json"])
    except TrainError as exc:
        report.error = str(exc)
        return EXIT_REJECTED
    if ungrounded and not getattr(args, "allow_ungrounded", False):
        # ADR-408: the refusal bites here, at training, and not at the build
        # -- a task written before it still builds and its policies still
        # verify, but nothing new trains on inputs the robot cannot read.
        report.error = (
            f"{len(ungrounded)} policy channel(s) name no onboard sensor that "
            f"measures them: {', '.join(ungrounded[:8])}"
            + (" ..." if len(ungrounded) > 8 else "")
            + ". Declare api.sensor(...) for what the robot really carries and "
            "pass it as observation(..., sensor=...), or mark a simulation-only "
            "channel role='privileged' so only the reward and the critic read "
            "it. --allow-ungrounded trains anyway."
        )
        return EXIT_REJECTED
    if ungrounded:
        report.notes.append(
            "trained with --allow-ungrounded: the policy reads "
            + ", ".join(ungrounded[:8]) + (" ..." if len(ungrounded) > 8 else "")
            + ", which no declared onboard sensor measures."
        )

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
        stop_on_collapse=args.stop_on_collapse,
        checkpoint_every=args.checkpoint_every,
    )
    if args.remote:
        # Blocking dispatch returns a policy; detached dispatch returns
        # the same remote run identity used by watch/pull (ADR-278).
        command = remote_trainer_command(
            task.files["json"], policy_path, allow_cpu=args.allow_cpu,
            detach=args.detach, **flags
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
    if args.remote:
        report.training = run_trainer(command, timeout=args.timeout)
    else:
        # Each checkpoint is rolled out through the engine on the CPU while
        # the trainer runs, and the stragglers after it (ADR-544).
        rollouts = None
        if args.checkpoint_every > 0:
            bundle = Path(task.files["json"])
            rollouts = CheckpointRollouts(
                out_dir, output=policy_path.stem, bundle=bundle,
                model=resolve_bundle_model(bundle), python=smoke_interpreter(engine),
                module_dir=engine.module_dir)
        # A local trainer is this machine's one training run while it lives,
        # the same slot `train_start`'s supervisor holds (ADR-543).
        try:
            with machine_slot():
                report.training = run_trainer(
                    command, timeout=args.timeout,
                    on_poll=rollouts.poll if rollouts else None)
        except LoopError as exc:
            report.error = str(exc)
            return EXIT_REJECTED
        finally:
            if rollouts is not None:
                rollouts.drain()
                summary = rollouts.summary()
                report.notes.append(
                    "rolled out {:d} checkpoint(s) beside them{:s}{:s}.".format(
                        summary["written"],
                        f", {summary['failed']} failed with a reason" if summary["failed"] else "",
                        f"; {summary['error']}" if summary.get("error") else ""))
    if args.detach:
        if report.training.get("state") != "pending" or not all(
            report.training.get(key) for key in ("run_id", "target", "remote_dir", "pid")
        ):
            raise TrainError("detached launch returned no pending run locator.")
        receipt_path = out_dir / "training-receipt.json"
        report.training["destination"] = str(out_dir)
        report.training["receipt_path"] = str(receipt_path)
        receipt_path.write_text(
            json.dumps(report.training, indent=2) + "\n", encoding="utf-8"
        )
        report.notes.append(
            f"pending remote run {report.training['run_id']}; locator: {receipt_path}. "
            "No policy verified or stored. Use remote_train.sh watch/pull with this "
            "run ID and a fresh destination; --put has not run."
        )
        report.ok = True
        return EXIT_OK
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


def command_smoke(args: argparse.Namespace, report: RunReport) -> int:
    """Simulate retained accepted artifacts, then measure exact posed solids.

    Exit zero means a complete measurement; read the verdict for its result.
    The command never restores, rebuilds or accepts a project script.
    """

    if not args.out:
        report.error = "smoke needs --out: the model and the receipt land there."
        return EXIT_USAGE
    if not (0.0 < float(args.seconds) <= MAXIMUM_TIMEOUT_S):
        report.error = f"--seconds must be within (0, {MAXIMUM_TIMEOUT_S:g}]."
        return EXIT_USAGE
    if not (0.0 < float(args.timeout) <= MAXIMUM_TIMEOUT_S):
        report.error = (
            f"--timeout must be within (0, {MAXIMUM_TIMEOUT_S:g}] seconds: a "
            "smoke rollout is bounded to five minutes."
        )
        return EXIT_USAGE
    if float(args.penetration_mm) < 0.0 or float(args.rest_speed_mm_s) < 0.0:
        report.error = "--penetration-mm and --rest-speed-mm-s must be nonnegative."
        return EXIT_USAGE
    if not (0.0 <= float(args.max_tilt_degrees) <= 180.0):
        report.error = "--max-tilt-degrees must be within [0, 180]."
        return EXIT_USAGE
    if int(args.fps) < 1 or args.seconds * args.fps > 15000:
        report.error = "--fps must be at least 1 and --seconds × --fps at most 15000."
        return EXIT_USAGE

    import time
    import math
    if any(not math.isfinite(v) or v < 0 for v in
           (args.penetration_mm, args.rest_speed_mm_s, args.max_common_volume_mm3,
            args.max_tilt_degrees)):
        report.error = "smoke tolerances must be finite and nonnegative."
        return EXIT_USAGE
    deadline = time.monotonic() + float(args.timeout)
    with _engine_session(args, report, restore=False) as (engine, client):
        report.out_dir = str(Path(args.out).expanduser().resolve())
        state, items, display = retained_bundle(Path(report.project_root), Path(report.out_dir))
        report.accepted_revision = report.revision = state["accepted_revision"]
        report.digest = state["accepted_digest"]
        report.outputs = [
            ExportedOutput(name=name, kind=entry["artifact_kind"],
                           files={Path(entry["artifact_path"]).suffix.lstrip("."): entry["artifact_path"]})
            for name, entry in display.items() if entry["artifact_kind"] != "brep"
        ]
        try:
            model = find_model(report.outputs, args.model_name)
            task = find_optional_task(report.outputs, args.task_name)
        except SmokeError as exc:
            report.error = str(exc)
            return EXIT_REJECTED
        python = smoke_interpreter(engine)
        receipt_path = Path(report.out_dir) / RECEIPT_NAME
        dynamics_path = receipt_path.with_name("smoke-dynamics.json")
        command = smoke_command(
            python, model=model.files["xml"], task=task.files["json"] if task else None,
            out=dynamics_path, seconds=float(args.seconds), mode=str(args.mode),
            penetration_mm=float(args.penetration_mm),
            rest_speed_mm_s=float(args.rest_speed_mm_s),
            max_tilt_degrees=float(args.max_tilt_degrees), fps=int(args.fps),
        )
        _progress(f" · smoke  {model.name}  {float(args.seconds):g} s {args.mode}  ({python})")
        receipt_path.unlink(missing_ok=True)
        for filename in ("smoke-trace.json", "smoke-geometry.json"):
            (Path(report.out_dir) / filename).unlink(missing_ok=True)
        dynamics = run_smoke(command, receipt=dynamics_path, timeout=max(0.001, deadline - time.monotonic()))
        geometry = check_geometry(
            engine, items=items, display=display, model_name=model.name,
            out=Path(report.out_dir), timeout=deadline - time.monotonic(),
            maximum_volume=args.max_common_volume_mm3,
        )
        report.smoke = dynamics
        report.smoke["schema"] = "cadex-smoke-v1"
        report.smoke["checks"]["components"] = geometry
        report.smoke["accepted_revision"] = report.accepted_revision
        report.smoke["accepted_digest"] = report.digest
        for pair in geometry["failing"]:
            report.smoke["failing"].append(
                f"components: {pair['first']} ∩ {pair['second']} "
                f"{pair['common_volume_mm3']:.6g} mm³ at {pair['time_s']:.3f} s")
        if not geometry["pass"]:
            report.smoke["verdict"] = "fail"
        receipt_path.write_text(json.dumps(report.smoke, indent=2, allow_nan=False) + "\n")
        report.smoke["receipt"] = str(receipt_path)
        report.notes.append(
            "smoke {:s}: {:s}{:s}; {:s}.".format(
                str(report.smoke["verdict"]), model.name,
                f" with task {task.name}" if task else " (no task exported)",
                str(receipt_path),
            )
        )
        report.ok = True
        return EXIT_OK


def command_evaluate(args: argparse.Namespace, report: RunReport) -> int:
    """Hold the accepted policy against its task's success spec (ADR-457).

    Exit zero means a complete measurement on every frozen seed; read the
    verdict for its result. Like ``smoke`` it reads what the accepted
    revision retained and never restores, rebuilds or accepts a script, so
    the policy evaluated is the one the engine verified. ``--out`` defaults
    to ``evaluations/<revision>-<policy>`` in the project. The film of the
    chosen seeds is drawn after the measurement is on disk (ADR-459); a film
    that could not be drawn is a failure that leaves the measurement.
    """

    if not (0.0 < float(args.timeout) <= EVALUATE_MAXIMUM_TIMEOUT_S):
        report.error = f"--timeout must be within (0, {EVALUATE_MAXIMUM_TIMEOUT_S:g}] seconds."
        return EXIT_USAGE
    for flag, value, least in (("--detail-start", args.detail_start, 0.0),
                               ("--detail-step", args.detail_step, None)):
        if value is not None and not (math.isfinite(value) and (value > 0 or value == least)):
            report.error = f"{flag} must be a {'time' if least == 0.0 else 'positive step'} in seconds."
            return EXIT_USAGE
    with _engine_session(args, report, restore=False) as (engine, _client):
        root = Path(report.project_root)
        try:
            inputs = retained_inputs(root, task_name=args.task_name, policy_name=args.policy_name)
        except EvaluateRefused as exc:
            report.error = str(exc)
            return EXIT_REJECTED
        report.accepted_revision = report.revision = inputs["accepted_revision"]
        report.digest = inputs["accepted_digest"]
        out = check_out(root, Path(args.out) if args.out else default_out(root, inputs))
        report.out_dir = str(out)
        _progress(
            " · evaluate  {:s} on {:s}  {:d} seed(s)".format(
                inputs["policy_output"], inputs["task_output"], len(inputs["seeds"]))
        )
        try:
            measured = (read_report(out, inputs) if args.film_only else
                        run_evaluation(engine, inputs, out, timeout=float(args.timeout)))
        except EvaluateRefused as exc:
            report.error = str(exc)
            return EXIT_REJECTED
        # What each part is made of, for the film: read from the pinned
        # accepted attempt, no rebuild. Without it the film is drawn in one
        # material and says so.
        try:
            inventory = read_inventory(_client)
        except (InventoryError, CadexdError, ValueError, OSError):
            inventory = None
        measured = add_film(
            root, out, measured, choice=args.film, inventory=inventory,
            start=args.detail_start, step=args.detail_step, video=not args.no_video,
            progress=_progress)
        path = out / EVALUATION_NAME
        report.evaluation = {
            key: measured[key] for key in (
                "schema", "verdict", "policy_output", "task_output", "model_output",
                "policy_sha256", "task_sha256", "model_sha256", "label", "summary")
        }
        report.evaluation["report"] = str(path)
        film = measured["film"]
        report.evaluation["film"] = {
            "state": film["state"], "error": film["error"],
            "seeds": [{"seed": row["seed"],
                       **{key: str(out / row[key]["file"]) for key in ("overview", "detail", "video")
                          if row.get(key)}} for row in film["seeds"]]}
        failing = failing_predicates(measured)
        report.notes.append(
            "evaluation {:s}: {:d} of {:d} seeds pass{:s}; {:s}.".format(
                measured["verdict"], len(measured["summary"]["passed"]),
                measured["summary"]["seeds"],
                (", failing " + ", ".join(failing)) if failing else "", str(path))
        )
        if film["state"] == "failed":
            # The measurement is complete and on disk; what was asked for
            # beside it was not made.
            report.error = "the evaluation was measured, and its film could not be drawn: " + str(
                film["error"])
            return EXIT_FAILURE
        report.ok = True
        return EXIT_OK


def _remote_usage_error(args: argparse.Namespace) -> str:
    """What is wrong with ``--remote``'s company, or nothing (ADR-200).

    Shared by ``train`` and ``walk`` so the walk refuses before its first
    leg rather than after a leg has spent time. ``--trainer-python``
    names a venv on this machine and the box has its own
    (``CADEX_TRAIN_VENV``); ``--allow-cpu`` is the dispatcher's flag and
    means nothing locally. A warm start is no longer refused here: since
    ADR-268 the dispatcher carries its two files out and re-points the
    flags, so an iterate has the same shape in both modes.
    """

    if getattr(args, "detach", False) and not args.remote:
        return "--detach needs --remote."
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
    if getattr(args, "engine_timeout", 0.0):
        common += ["--engine-timeout", repr(float(args.engine_timeout))]
    if getattr(args, "engine_memory", 0):
        common += ["--engine-memory", str(int(args.engine_memory))]
    return common


class McpSession:
    """``cadex mcp``'s tool host: one project's engine behind the bridge (ADR-538).

    The engine is opened on the first tool call that needs it -- the tool
    list and the guidance need none -- and closed after a quiet spell
    (:func:`cadex_cli.mcp.serve` calls :meth:`idle`). Closing releases the
    project lock, so the agent's own ``cadex render --wait`` or ``cadex
    train --wait`` on the same project runs between bursts of tool calls
    instead of queueing behind a server that holds the project for the
    whole conversation. Opening waits for that lock in turn.

    A session that accepted a build lands what a CLI run lands, before it
    lets go: a ``PROGRESS.md`` row and a commit in the project's own
    repository, naming the calls that changed the design.
    """

    def __init__(self, args: argparse.Namespace) -> None:
        self.args = args
        self.engine = resolve_engine(args.engine or None)
        self._stack: ExitStack | None = None
        self._bridge: Bridge | None = None
        self._client: CadexdClient | None = None
        self._report: RunReport | None = None

    def instructions(self) -> str:
        return guidance_brief(str(Path(self.args.project).expanduser().resolve()))

    def tools(self) -> list[dict[str, Any]]:
        return tool_definitions(self.engine.protocol)

    def call(self, tool: str, arguments: dict[str, Any]) -> dict[str, Any]:
        return self._open().call(tool, arguments)

    def idle(self) -> None:
        self.close()

    def _open(self) -> Bridge:
        if self._bridge is not None:
            return self._bridge
        report = RunReport(project_root=str(Path(self.args.project).expanduser()))
        stack = ExitStack()
        try:
            _engine, client = stack.enter_context(_engine_session(self.args, report))
            revision = read_working_revision(client)
        except BaseException:
            stack.close()
            raise
        for note in report.notes:
            _progress(f"mcp: {note}")

        def on_call(call: ToolCall) -> None:
            _progress(f" {'·' if call.ok else '✗'} {call.op}  {call.summary}")

        self._stack, self._client, self._report = stack, client, report
        self._bridge = Bridge(client, on_call=on_call, initial_revision=revision,
                              project_root=report.project_root)
        _progress(f"mcp: opened {report.project_root} at revision {revision[:12] or 'none'}")
        return self._bridge

    def close(self) -> None:
        """Land the session's row and commit, then shut the engine and release the project."""

        bridge, stack, client, report = self._bridge, self._stack, self._client, self._report
        if bridge is None or stack is None or client is None or report is None:
            return
        self._bridge = self._stack = self._client = self._report = None
        try:
            accepted = bridge.state.last_accepted
            if accepted is not None:
                apply_modeling_reply(report, accepted)
                if bridge.state.last_fit is not None:
                    report.fit = dict(bridge.state.last_fit)
                if bridge.state.last_inventory is not None:
                    report.inventory = dict(bridge.state.last_inventory)
                _refresh_script_state(client, report)
                changed = [call.op for call in bridge.state.calls if call.ok and call.op in MODELLING_OPS]
                self.args.mcp_summary = ", ".join(
                    op if changed.count(op) == 1 else f"{op} ×{changed.count(op)}"
                    for op in dict.fromkeys(changed))
                report.ok = True
                _record_progress("mcp", self.args, report)
                _commit_run("mcp", self.args, report)
        finally:
            stack.close()
        _progress(f"mcp: closed {report.project_root}"
                  + (f" at revision {report.accepted_revision[:12]}" if report.ok else ""))


def command_mcp(args: argparse.Namespace, report: RunReport) -> int:
    """Serve the project's tools over MCP stdio until the client goes (ADR-538).

    The protocol owns stdout: the server writes its messages to a private
    copy of the descriptor and points descriptor 1 at stderr, so nothing
    else in the process -- an engine child, a stray print -- can corrupt it.
    """

    if args.idle < 0:
        raise ValueError(f"mcp: --idle must be 0 or more seconds, not {args.idle:g}.")
    # A tool call waits for a CLI command on the same project, never fails on it.
    args.wait = True
    session = McpSession(args)
    out = os.fdopen(os.dup(sys.stdout.fileno()), "w", encoding="utf-8")
    sys.stdout.flush()
    os.dup2(sys.stderr.fileno(), sys.stdout.fileno())
    _progress(f"mcp: serving {Path(args.project).expanduser()} on stdio")
    try:
        serve_mcp(session, sys.stdin.buffer, out, idle_seconds=float(args.idle))
    finally:
        session.close()
        out.close()
    report.ok = True
    return EXIT_OK


def command_review(args: argparse.Namespace, report: RunReport) -> int:
    """Serve one project's review dashboard until interrupted (ADR-286).

    The server reads the project's manifest, records and retained
    artifacts on every request and writes nothing (ADR-537). So stopping it
    — Ctrl-C, SIGTERM — changes nothing about the project, and a walk or a
    training run in progress is neither stopped nor duplicated by starting
    or restarting it. The URL is printed on stderr as soon as the socket is
    bound, which is what a pipeline (or a test) waits for.
    """

    root = Path(args.project).expanduser()
    if not root.is_dir():
        raise ValueError(f"review: project directory not found: {root}")
    port = int(args.port)
    if port < 0 or port > 65535:
        raise ValueError(f"review: --port must be 0..65535, not {port}")
    try:
        server, thread = serve_review(root, str(args.host), port)
    except OSError as exc:
        raise ValueError(f"review: cannot bind {args.host}:{port}: {exc}") from exc
    _progress(f"review: serving {root.name} at {server.url} (read-only; Ctrl-C to stop)")
    _serve_until_stopped(server, thread)
    report.ok = True
    report.notes.append(f"review: served {server.url}; stopped")
    return EXIT_OK


def _serve_until_stopped(server: Any, thread: threading.Thread) -> None:
    """Block until Ctrl-C or SIGTERM, then stop and close ``server``."""

    stop = threading.Event()

    def _stop(_signum: int, _frame: Any) -> None:
        stop.set()

    previous = {sig: signal.signal(sig, _stop) for sig in (signal.SIGINT, signal.SIGTERM)}
    try:
        while not stop.is_set() and thread.is_alive():
            stop.wait(0.5)
    finally:
        for sig, handler in previous.items():
            signal.signal(sig, handler)
        server.shutdown()
        server.server_close()


def projects_directory(args: argparse.Namespace) -> Path:
    """``--projects``, then ``CADEX_PROJECTS``, then ``~/cadex-projects``."""

    chosen = getattr(args, "projects", None) or os.environ.get("CADEX_PROJECTS", "")
    return Path(chosen or Path.home() / DEFAULT_PROJECTS_DIRNAME).expanduser()


def command_app(args: argparse.Namespace, report: RunReport) -> int:
    """Serve the dashboard over a directory of projects until interrupted.

    The same review pages as ``cadex review``, one per project
    under ``/p/<name>/``, behind an index that lists every project in the
    directory anew on each request. The directory is created if absent, so
    a fresh clone reaches a first page without having made a project. The
    URL is printed on stderr as soon as the socket is bound.
    """

    root = projects_directory(args)
    if root.exists() and not root.is_dir():
        raise ValueError(f"app: not a directory: {root}")
    root.mkdir(parents=True, exist_ok=True)
    host = str(getattr(args, "host", "127.0.0.1"))
    port = int(getattr(args, "port", 8765))
    if port < 0 or port > 65535:
        raise ValueError(f"app: --port must be 0..65535, not {port}")
    try:
        server, thread = serve_projects(root, host, port)
    except OSError as exc:
        raise ValueError(f"app: cannot bind {host}:{port}: {exc}") from exc
    _progress(f"app: serving {root} at {server.url} (read-only; Ctrl-C to stop)")
    _serve_until_stopped(server, thread)
    report.ok = True
    report.notes.append(f"app: served {server.url}; stopped")
    return EXIT_OK


def command_walk(args: argparse.Namespace, report: RunReport) -> int:
    """The lifecycle walk as one command (ADR-199).

    The iterate change (``--set``,
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
    if args.checkpoint_every < 0:
        report.error = "--checkpoint-every must be 0 (none) or a number of iterations."
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
    if args.complete:
        # Completion runs no trainer, so every flag that only reaches the
        # train leg would be read as an instruction and obeyed by nothing.
        # Refusing them is cheaper than a run that silently ignored them.
        for flag, on in (
            ("--detach", args.detach), ("--remote", args.remote),
            ("--allow-cpu", args.allow_cpu), ("--set", bool(args.assignments)),
        ):
            if on:
                report.error = (
                    f"--complete finishes a launched run; {flag} would change "
                    "or train again. Run them as their own walk."
                )
                return EXIT_USAGE
    remote_error = _remote_usage_error(args)
    if remote_error:
        report.error = remote_error
        return EXIT_USAGE
    if not args.remote and not args.complete and lock_held(machine_lock_path()):
        # Refused before the sweep moves the accepted revision, not at the
        # train leg after it (ADR-543).
        report.error = f"{SLOT_BUSY}; wait for it to end."
        return EXIT_REJECTED
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

    report.walk["mode"] = (
        "complete" if args.complete else "detach" if args.detach else "blocking"
    )

    # The run record (ADR-285): written as `running` now, so a walk that is
    # killed leaves a file saying it never finished, and rewritten whole
    # when the walk ends. `known` collects what later legs learn. It starts
    # with what the manifest says the training input is — revision, digest
    # and specs — so the record names the model being trained before the
    # first telemetry sample lands, and keeps naming it if the walk fails.
    known: dict[str, Any] = manifest_identity(report.project_root, "at walk start")
    requested = {
        "iterations": int(args.iterations), "envs": int(args.envs),
        "seed": int(args.seed), "timeout_s": float(args.timeout),
        "remote": bool(args.remote), "allow_cpu": bool(args.allow_cpu),
        "label": args.label or None, "task": args.task_name or None,
        "init_from": args.init_from or None,
        "init_from_parent_task": args.init_from_parent_task or None,
        "init_from_task_change": args.init_from_task_change or None,
        "assignments": dict(assignments),
    }

    def land_record(status: str, **extra: Any) -> None:
        try:
            path = write_run_record(
                out_dir, project_root=report.project_root, status=status,
                mode=report.walk["mode"], legs=legs, error=report.error or None,
                params=report.params, training=report.training, requested=requested,
                walk_seconds=time.monotonic() - walk_started,
                **{"snapshot_docs": True, **known, **extra},
            )
        except OSError as exc:
            report.notes.append(f"run record not written: {exc}")
            return
        report.walk["run_record"] = str(path)

    def learned(leg: Any) -> None:
        """A finished leg's envelope identity is the record's, from here on.

        Each leg reports the accepted revision it left the project at, so
        the last one to speak is the revision the next leg runs against —
        the train leg's is what the trainer was given, the rollout leg's
        is what the review measures.
        """

        legs.append(leg.to_json())
        revision = str(leg.envelope.get("accepted_revision") or "")
        if revision:
            known.update(
                accepted_revision=revision,
                digest=str(leg.envelope.get("digest") or ""),
                identity_source=f"{leg.name} leg envelope",
            )

    land_record("running")

    def failed(leg: Any, what: str) -> int:
        legs.append(leg.to_json())
        report.error = "{:s} (leg {:s}, exit {:d}): {:s}".format(
            what, leg.name, leg.code, str(leg.envelope.get("error") or "no envelope")
        )
        land_record("failed")
        return leg.code if leg.code in (EXIT_USAGE, EXIT_REJECTED) else EXIT_FAILURE

    if not args.complete:
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
            learned(leg)
        if legs:
            # The sweep moved the accepted revision: the specs
            # the record carries must be the moved manifest's, and the
            # `running` record on disk must name the training input before
            # the train leg starts writing telemetry beside it.
            specs = manifest_identity(report.project_root, "before the train leg")
            known.update(param_specs=specs["param_specs"],
                         specs_source=specs["specs_source"])
            land_record("running")

        from .review_server import retain_training_view
        with project_lock(Path(report.project_root), wait=bool(args.wait)):
            retain_training_view(report.project_root, out_dir)
            land_record("running")

        # Train, and bring the policy home.
        argv = [
            *common, "train", "--out", str(out_dir / TRAIN_DIRNAME),
            "--detach" if args.detach else "--put",
            "--iterations", str(int(args.iterations)), "--envs", str(int(args.envs)),
            "--seed", str(int(args.seed)), "--timeout", str(float(args.timeout)),
            # An unattended walk does not spend hours training a policy that
            # has learned to end its own episodes (ADR-410).
            "--stop-on-collapse", "--json",
        ]
        for flag, value in (
            ("--label", args.label), ("--name", args.policy_name),
            ("--task", args.task_name), ("--trainer-python", args.trainer_python),
            ("--init-from", args.init_from),
            ("--init-from-parent-task", args.init_from_parent_task),
            ("--init-from-task-change", args.init_from_task_change),
            ("--checkpoint-every", args.checkpoint_every),
        ):
            if value:
                argv += [flag, str(value)]
        for flag, on in (("--remote", args.remote), ("--allow-cpu", args.allow_cpu),
                         ("--allow-ungrounded", args.allow_ungrounded)):
            if on:
                argv.append(flag)
        _progress(" · walk  train" + (" (remote)" if args.remote else ""))
        leg = run_leg("train", argv, timeout=train_timeout)
        if leg.code != EXIT_OK:
            return failed(leg, "training did not produce a policy")
        learned(leg)
        training = leg.envelope.get("training") or {}
        if args.detach:
            # Pending is not success, and the difference is what this
            # branch exists to keep (ADR-282): the walk stops here with the
            # locator on disk, having verified, stored, declared and rolled
            # out nothing. `--complete` picks it up when the box is done.
            if training.get("state") != "pending" or not training.get("run_id"):
                report.error = (
                    "the detached train leg returned no pending run locator."
                )
                return EXIT_FAILURE
            report.training = dict(training)
            bundle, task_sha256 = task_bundle(out_dir / TRAIN_DIRNAME)
            known.update(task_bundle=bundle, task_sha256=task_sha256)
            pending_path = write_pending(
                out_dir, training=training, legs=legs, project=args.project,
                bundle=bundle, task_sha256=task_sha256, seed=int(args.seed),
            )
            report.walk["pending"] = dict(training)
            report.walk["pending_file"] = str(pending_path)
            report.notes.append(
                "walk pending: remote run {:s} launched; locator {:s}. "
                "Bring it home with `training/remote_train.sh watch {:s} {:s}`, "
                "then finish with `cadex walk --complete --project {:s} "
                "--out {:s}`. Nothing was verified, stored or declared.".format(
                    str(training["run_id"]), str(pending_path),
                    str(training["run_id"]),
                    str(training.get("destination") or out_dir / TRAIN_DIRNAME),
                    str(Path(args.project).expanduser()), str(out_dir),
                )
            )
            land_record("pending")
            report.ok = True
            return EXIT_OK
        stored = [row for row in leg.envelope.get("assets") or []
                  if row.get("sha256") == training.get("sha256")]
        report.training = dict(training)
        if not training.get("sha256") or not stored:
            report.error = "train reported no stored policy sha256; nothing to declare."
            land_record("failed")
            return EXIT_FAILURE
        report.assets = [dict(row) for row in leg.envelope.get("assets") or []]
        weights = str(stored[0].get("name") or Path(str(training.get("out"))).name)
        sha256 = str(training["sha256"])
        bundle, task_sha256 = task_bundle(out_dir / TRAIN_DIRNAME)
        known.update(policy_name=weights, policy_sha256=sha256,
                     task_bundle=bundle, task_sha256=task_sha256)
    else:
        # Completion: the policy the dispatcher brought home, stored through
        # the same `cadex asset --put` leg the blocking train leg's --put
        # runs, so every later leg reads exactly what it reads there.
        try:
            pending = read_pending(out_dir)
            policy_path, training = collect_detached(
                pending, out_dir / TRAIN_DIRNAME
            )
        except WalkError as exc:
            report.error = str(exc)
            land_record("failed")
            return EXIT_REJECTED
        # The comparison block the blocking train leg puts in its receipt,
        # off the same bundle, so a completed detached walk lands the same
        # PROGRESS.md comparison an in-line one does (ADR-263).
        bundle, bundle_digest = task_bundle(out_dir / TRAIN_DIRNAME)
        known.update(task_bundle=bundle, task_sha256=bundle_digest)
        if bundle is not None:
            training["comparison"] = {
                **task_comparison(bundle),
                "training_seed": int(pending.get("training_seed") or 0),
            }
        legs.extend(pending.get("legs") or [])
        report.walk["pending"] = dict(pending.get("training") or {})
        report.training = dict(training)
        _progress(" · walk  collect  " + policy_path.name)
        leg = run_leg("collect", [*common, "asset", "--put", str(policy_path),
                                  "--json"], timeout=leg_timeout)
        if leg.code != EXIT_OK:
            return failed(leg, "the returned policy could not be stored")
        learned(leg)
        report.assets = [dict(row) for row in leg.envelope.get("assets") or []]
        stored = [row for row in report.assets
                  if row.get("sha256") == training.get("sha256")]
        if not stored:
            report.error = (
                "the collected policy was stored under a different digest "
                "than the trainer reported; nothing to declare."
            )
            land_record("failed")
            return EXIT_FAILURE
        weights = str(stored[0].get("name") or policy_path.name)
        sha256 = str(training["sha256"])
        known.update(policy_name=weights, policy_sha256=sha256)

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
        land_record("failed")
        return EXIT_REJECTED
    script_path = out_dir / SCRIPT_FILENAME
    script_path.write_text(source, encoding="utf-8")
    leg = run_leg("declare", [*common, "script", "--set", str(script_path), "--json"],
                  timeout=leg_timeout)
    if leg.code != EXIT_OK:
        return failed(leg, "the re-declared script was refused")
    learned(leg)

    # Verify and roll out: the switch on, the trace exported.
    _progress(" · walk  rollout")
    leg = run_leg("rollout", [
        *common, "params", "--set", f"{POLICY_SWITCH}=1",
        "--out", str(out_dir / ROLLOUT_DIRNAME), "--json",
    ], timeout=leg_timeout)
    if leg.code != EXIT_OK:
        return failed(leg, "the policy did not verify")
    learned(leg)
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
        # The parameter specs at the accepted revision, for the run record
        # (ADR-285): read now, while the engine holds that revision, because
        # a historical run must never be re-run to learn what its
        # parameters meant. A read that fails is recorded as unavailable.
        try:
            known["param_specs"] = list(read_script_state(client)["params"]["specs"])
            known["specs_source"] = "inspect scope=script at the accepted revision"
        except RuntimeError as exc:
            known["param_specs"] = None
            known["specs_source"] = f"unavailable: {exc}"
        # A picture the renderer cannot draw is a missing picture, not a
        # failed walk: hex2 and hex3 both lost their whole review, gait
        # verdict included, to a render refusal (ADR-410).
        try:
            render_path, rendering = write_render(
                client, report.project_root, expected_revision=report.accepted_revision,
                accepted_snapshot=accepted_snapshot,
            )
        except InventoryError as exc:
            render_path = None
            rendering = {"revision": accepted_snapshot[1]["revision"],
                         "objects": accepted_snapshot[1]["objects"],
                         "reason": str(exc)}
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
    } if render_path is not None else {
        "available": False, "revision": rendering["revision"], "reason": rendering["reason"],
    }
    if render_path is None:
        report.notes.append("render: unavailable ({:s}); the rest of the review stands.".format(
            rendering["reason"]))
    else:
        report.notes.append("measures: " + describe_proxies(rendering["proxies"]) + ".")
    review["section"] = {
        **section, "summary_path": section_path.relative_to(Path(report.project_root)).as_posix(),
    }
    # What the mechanism declares, against what the project documents:
    # a driven joint asks for docs/actuators.md and an observed one for
    # docs/sensors.md (ADR-245's convention, ADR-256's check). The notes
    # are the agent's to write, so a gap is reported, never filled.
    subjects, model_path = declared_note_subjects(out_dir / TRAIN_DIRNAME)
    known["model_xml"] = model_path
    # Whether it walked (ADR-409): judged on the free body's tilt and
    # heading and on how long training episodes lasted, never on the reward
    # the task happened to pay.
    train_dir = out_dir / TRAIN_DIRNAME
    review["gait"] = gait_from_trace(
        read_json(review.get("trace")) if review.get("trace") else {},
        bases=floating_bases(model_path),
        task=read_json(known.get("task_bundle")),
        progress=read_json(train_dir / "progress.json")
        or read_json(train_dir / PROGRESS_FILENAME),
    ) if review.get("trace") else {"available": False, "reason": "no trace was exported."}
    # ...and that reading is one behaviour's (ADR-464): a task with a
    # success spec is judged by the spec, and the walk says so.
    review["behaviour"] = behaviour_authority(read_json(known.get("task_bundle")))
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
    gait = review["gait"]
    if gait.get("available"):
        report.notes.append(
            "gait: {:s}; {:.0f} mm in {:.1f} s, tilt ≤{:.0f}°, heading {:+.0f}°.".format(
                "walked" if gait["walked"]
                else "DID NOT WALK — " + "; ".join(gait["findings"]),
                gait["planar_travel_mm"], gait["duration_s"] or 0.0,
                gait["max_tilt_deg"], gait["heading_final_deg"],
            )
        )
    if review["behaviour"]["command"]:
        report.notes.append(
            "behaviour: the task declares a success spec, so `cadex evaluate` is the "
            "verdict on what the policy does; the gait reading is advisory."
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
    land_record("ok", review=review, trace=review.get("trace"))
    if review.get("total_reward") is None:
        report.notes.append(
            "the rollout exported no trace with a policy block; the walk "
            "verified the policy but has no number to review."
        )
    else:
        report.notes.append(
            "walk: {:s} ({:s}) verified; total_reward {:.6g} over {:d} legs{:s}.".format(
                weights, sha256[:12], float(review["total_reward"]), len(legs),
                "" if not review["gait"].get("available") or review["gait"]["walked"]
                else ", but the robot did not walk (see gait)",
            )
        )
    report.ok = True
    return EXIT_OK


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    # A bare `cadex` opens the dashboard; `cadex -h` is the help.
    command = args.command or "app"
    if command == "guidance":
        sys.stdout.write(guidance_text())
        return EXIT_OK

    report = RunReport(project_root=str(Path(args.project).expanduser()))
    # `cadex mcp`'s stdout is the protocol, and a script listing is its source.
    quiet = command == "mcp" or (command == "script" and not getattr(args, "source_file", ""))
    try:
        if command == "mcp":
            code = command_mcp(args, report)
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
        elif command == "smoke":
            code = command_smoke(args, report)
        elif command == "evaluate":
            code = command_evaluate(args, report)
        elif command == "walk":
            code = command_walk(args, report)
        elif command == "review":
            code = command_review(args, report)
        elif command == "app":
            code = command_app(args, report)
        elif command == "budgets":
            code = command_budgets(args, report)
        elif command == "revision":
            code = command_revision(args, report)
        else:  # argparse already refuses anything else
            return EXIT_USAGE
    except (ValueError, ExportError, InventoryError, TrainError, SmokeError, EvaluateError,
            WalkError) as exc:
        report.error = str(exc)
        code = EXIT_USAGE if isinstance(exc, ValueError) else EXIT_FAILURE
    except (EngineError, ProjectBusy, CadexdError) as exc:
        report.error = str(exc)
        code = EXIT_FAILURE
    except KeyboardInterrupt:
        report.error = "cancelled."
        code = EXIT_FAILURE

    if code == EXIT_OK and report.ok and not quiet:
        _record_progress(command, args, report)
        _commit_run(command, args, report)
    if command == "mcp":
        if report.error:
            _progress(f"mcp: {report.error}")
    elif not (quiet and code == EXIT_OK):
        emit(report, as_json=bool(args.json))
    return code


def _progress_what(command: str, args: argparse.Namespace, report: RunReport) -> str:
    """What this run did, in the words a person would use for the row."""

    if command == "mcp":
        return f"mcp: {getattr(args, 'mcp_summary', '') or 'a session'}"
    if command == "params":
        return "params " + ", ".join(
            f"{name}={value}" for name, value in sorted(
                _parse_assignments(args.assignments).items()
            )
        )
    if command == "script":
        return f"script --set {Path(args.source_file).name}"
    if command == "revision":
        change = report.revisions
        return "revision {:s} → {:s} (#{}) from {:s}".format(
            args.action, str(change.get("target") or "")[:12], change.get("ordinal"),
            str(change.get("from") or "")[:12])
    if command == "export":
        return f"export → {args.out}"
    if command == "section":
        where = "derived offset" if args.offset_mm is None else f"{args.offset_mm:g} mm"
        return f"section → review/section/ ({args.plane}, {where})"
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
        if getattr(args, "complete", False):
            return f"walk complete {label} (detached run collected)"
        return "walk {:d} it × {:d} envs → {:s}{:s}".format(
            int(args.iterations), int(args.envs), label,
            " (detached; pending)" if getattr(args, "detach", False) else "",
        )
    if command == "smoke":
        return "smoke {:g} s {:s} → {:s} ({:s})".format(
            float(args.seconds), str(args.mode),
            str(report.smoke.get("verdict") or "?"),
            str(Path(str(report.out_dir or args.out)).name),
        )
    if command == "evaluate":
        return "evaluate {:s} on {:s} → {:s} ({:s})".format(
            str(report.evaluation.get("policy_output") or "?"),
            str(report.evaluation.get("task_output") or "?"),
            str(report.evaluation.get("verdict") or "?"),
            str(Path(str(report.out_dir)).name),
        )
    if command == "train":
        if report.training.get("state") == "pending":
            return f"train pending {report.training['run_id']} (remote; no policy stored)"
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
    if command in ("review", "app", "budgets"):  # no run: no row, no commit (ADR-286)
        return
    if command == "revision" and args.action == "list":  # a read (ADR-506)
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
            numbers=(smoke_cell(report.smoke) if command == "smoke" else
                     evaluation_cell(report.evaluation) if command == "evaluate" else
                     "pending; no policy verified"
                     if report.training.get("state") == "pending" else (
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
            ) if command in ("walk", "train")
                 and report.training.get("state") != "pending" else ""),
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
    if command in ("review", "app", "budgets"):
        return
    if command == "revision" and args.action == "list":
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
