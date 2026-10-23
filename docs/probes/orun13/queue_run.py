"""orun13 (from orun12 O7): queue the next screen behind the live run, so the GPU never idles.

    systemd-run --user --scope -p MemoryMax=30G \
      env PYTHONPATH=cli pixi run python docs/probes/orun13/queue_run.py \
        PROJECT RUN BUDGET_S ITERATIONS "REASON" [--expect-revision SHA] [--seed N] [--task gallop] [--envs N] \
        [--init-from POLICY --critic-warmup N [--learning-rate LR] [--parent-task BUNDLE --task-change "WHY"]]
        [--after RUN --build SCRIPT [--build-param K=V ...]]

Waits until the project has no live run and the machine's training slot is
free, then does what an iteration would by hand through ``cadex_cli.loop``:
``register`` (8192 envs unless ``--envs``, which O2a allows a heel screen;
unroll 20, a checkpoint every 25, the given seed and iterations, cold), ``retain_training_view`` so the dashboard follows it, and
``launch``. ``--init-from`` continues a policy on the same task bundle (the
trainer refuses one whose task or model digest differs), with
``--critic-warmup`` iterations of critic-only training first (ADR-740);
with ``--parent-task`` (the policy's own task bundle) and ``--task-change``
(one line on what changed) it continues one across a task change that keeps
what the network reads and emits (``init_from_parent_task``).
Launched from a ``systemd-run --scope``, the supervisor and the
trainer stay in that scope (a transient service would kill the trainer).

``--expect-revision`` refuses to register if the project's accepted revision
has moved on since the run was queued, so a later rebuild cannot slip an
unplanned change under a queued screen. A run that the loop refuses ends
the queue with the refusal on stderr; nothing retries.

``--after RUN --build SCRIPT`` queues a screen whose revision is not built
yet behind one that is: it waits until RUN has registered (so RUN's own
``--expect-revision`` still sees its revision), then builds SCRIPT with
``cadex script --set --wait``, and expects the revision that build accepts.
A stored parameter value outranks the script's declared one, so a
``--build-param K=V`` is set first with ``cadex params --set`` on the
project's current script.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

from cadex_cli import loop
from cadex_cli.review_server import retain_training_view

POLL_S = 60.0


def accepted_revision(root: Path) -> str:
    from cadex_cli.review_record import read_accepted_identity

    return str(read_accepted_identity(root).get("revision") or "")


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("project")
    ap.add_argument("run")
    ap.add_argument("budget_s", type=float)
    ap.add_argument("iterations", type=int)
    ap.add_argument("reason")
    ap.add_argument("--expect-revision", default="")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--task", default="gallop")
    ap.add_argument("--envs", type=int, default=8192)
    ap.add_argument("--init-from", default="")
    ap.add_argument("--critic-warmup", type=int, default=0)
    ap.add_argument("--learning-rate", type=float, default=None)
    ap.add_argument("--parent-task", default="")
    ap.add_argument("--task-change", default="")
    ap.add_argument("--after", default="")
    ap.add_argument("--build", default="")
    ap.add_argument("--build-param", action="append", default=[])
    args = ap.parse_args(argv)
    if bool(args.parent_task) != bool(args.task_change) or (args.parent_task and not args.init_from):
        ap.error("--parent-task and --task-change go together, with --init-from")
    if bool(args.after) != bool(args.build):
        ap.error("--after and --build go together")
    root = Path(args.project).expanduser().resolve()
    print(f"{time.strftime('%F %T')} queued {args.run}", flush=True)
    if args.build:
        while not (root / "runs" / args.after / "registration.json").is_file():
            time.sleep(POLL_S)
        cadex = str(Path(__file__).resolve().parents[3] / "cadex")
        steps = []
        if args.build_param:
            steps.append(["params", "--project", str(root), "--wait", "--json"]
                         + [a for kv in args.build_param for a in ("--set", kv)])
        steps.append(["script", "--project", str(root), "--set", str(Path(args.build).resolve()), "--wait", "--json"])
        for step in steps:
            done = subprocess.run([cadex] + step, capture_output=True, text=True)
            built = ""
            try:
                built = str(json.loads(done.stdout).get("accepted_revision") or "")
            except ValueError:
                pass
            if done.returncode or not built:
                print(f"cadex {step[0]} failed ({done.returncode}): {done.stdout[-2000:]} {done.stderr[-2000:]}",
                      file=sys.stderr)
                return 1
        if args.expect_revision and not built.startswith(args.expect_revision):
            print(f"built revision {built[:8]} is not the expected {args.expect_revision}", file=sys.stderr)
            return 1
        args.expect_revision = built
        print(f"{time.strftime('%F %T')} built {built[:8]} after {args.after} registered", flush=True)
    while loop.live_run(root) or loop.lock_held(loop.machine_lock_path()):
        time.sleep(POLL_S)
    revision = accepted_revision(root)
    if args.expect_revision and not revision.startswith(args.expect_revision):
        print(f"accepted revision {revision[:8]} is not the queued {args.expect_revision}; not registering",
              file=sys.stderr)
        return 1
    settings = {"iterations": args.iterations, "envs": args.envs, "seed": args.seed, "unroll": 20,
                "checkpoint_every": 25, "label": f"{args.run}: {args.reason[:80]}"}
    if args.init_from:
        settings.update(init_from=args.init_from, critic_warmup=args.critic_warmup)
    if args.parent_task:
        settings.update(init_from_parent_task=str(Path(args.parent_task).expanduser().resolve()),
                        init_from_task_change=args.task_change)
    if args.learning_rate is not None:
        settings["learning_rate"] = args.learning_rate
    try:
        run_dir = loop.register(root, run=args.run, budget_s=args.budget_s, reason=args.reason,
                               settings=settings, task_name=args.task)
        retain_training_view(root, run_dir)
        state = loop.launch(run_dir)
    except loop.LoopError as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 1
    print(f"{time.strftime('%F %T')} launched {args.run} on {revision[:8]}: {json.dumps(state.get('state'))}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
