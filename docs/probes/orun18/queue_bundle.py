"""orun18 C3: launch a hand-built task bundle through ``cadex_cli.loop``, cold.

    systemd-run --user --scope -p MemoryMax=30G \
      env PYTHONPATH=cli pixi run python docs/probes/orun18/queue_bundle.py \
        PROJECT RUN BUNDLE BUDGET_S ITERATIONS "REASON" --base-task speed [--seed N] [--envs N]

``loop.register`` trains only a task the accepted attempt retained. C3's
bundle (``c3_bundle.py``) is that attempt's ``speed`` task with the
retargeted strides added, on the same model, so this registers the base task
on the accepted revision, refuses unless BUNDLE names the very model file
registered (same name, same sha256), then puts BUNDLE in the base bundle's
place: the file, ``task_output``, ``task_sha256``, the policy name and the
trainer command, and ``base_task`` / ``base_task_sha256`` saying what it
replaced. The supervisor then holds the trainer's receipt to BUNDLE's
digest as for any run. ``retain_training_view`` and ``launch`` follow, as in
``orun13/queue_run.py``.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
from pathlib import Path

from cadex_cli import loop
from cadex_cli.review_server import retain_training_view


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("project")
    ap.add_argument("run")
    ap.add_argument("bundle")
    ap.add_argument("budget_s", type=float)
    ap.add_argument("iterations", type=int)
    ap.add_argument("reason")
    ap.add_argument("--base-task", required=True)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--envs", type=int, default=4096)
    args = ap.parse_args(argv)
    root = Path(args.project).expanduser().resolve()
    source = Path(args.bundle).expanduser().resolve()
    task = json.loads(source.read_text(encoding="utf-8"))
    output = source.name[:-len("-task.json")] if source.name.endswith("-task.json") else ""
    if not output:
        print(f"{source.name} is not a <task>-task.json bundle", file=sys.stderr)
        return 1
    settings = {"iterations": args.iterations, "envs": args.envs, "seed": args.seed, "unroll": 20,
                "checkpoint_every": 25, "label": f"{args.run}: {args.reason[:80]}"}
    try:
        run_dir = loop.register(root, run=args.run, budget_s=args.budget_s, reason=args.reason,
                                settings=settings, task_name=args.base_task)
    except loop.LoopError as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 1
    reg_path = run_dir / loop.REGISTRATION_NAME
    reg = json.loads(reg_path.read_text(encoding="utf-8"))
    model = run_dir / reg["model"]
    named = task.get("model") or {}
    if Path(str(named.get("path") or "")).name != model.name or named.get("sha256") != reg["model_sha256"]:
        shutil.rmtree(run_dir)
        print(f"refused: {source.name} names model {named.get('path')} {str(named.get('sha256'))[:8]}, "
              f"not the registered {model.name} {reg['model_sha256'][:8]}", file=sys.stderr)
        return 1
    old_bundle = run_dir / reg["bundle"]
    bundle = old_bundle.parent / source.name
    shutil.copyfile(source, bundle)
    old_bundle.unlink()
    policy = bundle.parent / f"{output}.cxpolicy"
    reg.update(
        base_task=reg["task_output"], base_task_sha256=reg["task_sha256"],
        task_output=output, task_sha256=loop._sha256(bundle),
        bundle=str(bundle.relative_to(run_dir)), policy=str(policy.relative_to(run_dir)),
        evaluation_seeds=[int(s) for s in (task.get("success") or {}).get("seeds") or []],
        has_success_spec=bool(task.get("success")))
    command = list(reg["command"])
    command[command.index(str(old_bundle))] = str(bundle)
    command[command.index("--out") + 1] = str(policy)
    reg["command"] = command
    reg_path.write_text(json.dumps(reg, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    loop._record(root, run_dir, reg, "running")
    try:
        retain_training_view(root, run_dir)
        state = loop.launch(run_dir)
    except loop.LoopError as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 1
    print(f"{time.strftime('%F %T')} launched {args.run} on {reg['accepted_revision'][:8]}, task "
          f"{output} {reg['task_sha256'][:8]} (in place of {reg['base_task']} "
          f"{reg['base_task_sha256'][:8]}): {json.dumps(state.get('state'))}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
