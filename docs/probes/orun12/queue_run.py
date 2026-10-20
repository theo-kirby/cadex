"""orun12 O7: queue the next screen behind the live run, so the GPU never idles.

    systemd-run --user --scope -p MemoryMax=30G \
      env PYTHONPATH=cli pixi run python docs/probes/orun12/queue_run.py \
        PROJECT RUN BUDGET_S ITERATIONS "REASON" [--expect-revision SHA] [--seed N] [--task gallop] [--envs N] \
        [--init-from POLICY --critic-warmup N [--learning-rate LR]]

Waits until the project has no live run and the machine's training slot is
free, then does what an iteration would by hand through ``cadex_cli.loop``:
``register`` (8192 envs unless ``--envs``, which O2a allows a heel screen;
unroll 20, a checkpoint every 25, the given seed and iterations, cold), ``retain_training_view`` so the dashboard follows it, and
``launch``. ``--init-from`` continues a policy on the same task bundle (the
trainer refuses one whose task or model digest differs), with
``--critic-warmup`` iterations of critic-only training first (ADR-740).
Launched from a ``systemd-run --scope``, the supervisor and the
trainer stay in that scope (a transient service would kill the trainer).

``--expect-revision`` refuses to register if the project's accepted revision
has moved on since the run was queued, so a later rebuild cannot slip an
unplanned change under a queued screen. A run that the loop refuses ends
the queue with the refusal on stderr; nothing retries.
"""

from __future__ import annotations

import argparse
import json
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
    args = ap.parse_args(argv)
    root = Path(args.project).expanduser().resolve()
    print(f"{time.strftime('%F %T')} queued {args.run}", flush=True)
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
