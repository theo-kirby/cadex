"""orun19 L1: launch a hand-built task bundle warm, through ``cadex_cli.loop``.

    systemd-run --user --scope -p MemoryMax=30G \
      env PYTHONPATH=cli pixi run python docs/probes/orun19/queue_warm.py POLICY \
        PROJECT RUN BUNDLE BUDGET_S ITERATIONS "REASON" --base-task speed [--seed N] [--envs N]

orun18's ``queue_bundle.py`` with one setting added: ``init_from=POLICY``.
A long run (O5) is a warm start on the *same* task, so no
``init_from_parent_task`` / ``init_from_task_change`` is passed; the trainer
refuses the warm start unless POLICY was trained on BUNDLE's model and
channels (``cadex_train.py``'s ``--init-from`` check).
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "orun18"))

import queue_bundle  # noqa: E402


def main(argv):
    if not argv:
        print(__doc__, file=sys.stderr)
        return 2
    policy = Path(argv[0]).expanduser().resolve()
    if not policy.is_file():
        print(f"refused: no such policy {policy}", file=sys.stderr)
        return 1
    register = queue_bundle.loop.register

    def warm(root, *, settings=None, **kwargs):
        return register(root, settings={**(settings or {}), "init_from": str(policy)}, **kwargs)

    queue_bundle.loop.register = warm
    return queue_bundle.main(argv[1:])


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
