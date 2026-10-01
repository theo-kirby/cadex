"""Collect every ot11 training run's settings, budget and GPU time from its receipts.

C1 asks REPORT.md to list every training run with its settings, its budget
and the GPU time spent. Each number already exists in the project that ran
it: ``runs/<run>/registration.json`` is what ``train_start`` wrote before
launch, and ``runs/<run>/training-status.json`` is what the run's supervisor
wrote when it ended. This reads those two files and nothing else, keeps no
machine path, and writes one receipt the report's table is held to.

Two times are kept, because they measure different things:

- ``supervised_s`` is the supervisor's wall time, launch to exit. The
  trainer holds the GPU for all of it, so it is the GPU time the charter
  counts, and it is the figure that exists for every run.
- ``trainer_s`` is the trainer's own receipt, written only by a trainer
  that saved its final policy; a run stopped at its wall-clock budget, or
  stopped on collapse, ends without one.

    pixi run python docs/probes/ot11/runner/run_ledger.py --out OUT.json PROJECT [...]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def relative(path: str | None, project: Path) -> str | None:
    """A warm start's source, as a path inside its project."""

    if not path:
        return None
    candidate = Path(path)
    if candidate.is_absolute():
        return candidate.relative_to(project).as_posix()
    return candidate.as_posix()


def run_row(project: Path, run_dir: Path) -> dict:
    registration = json.loads((run_dir / "registration.json").read_text(encoding="utf-8"))
    status = json.loads((run_dir / "training-status.json").read_text(encoding="utf-8"))
    settings = registration["settings"]
    receipt = status.get("receipt") or {}
    policy = status.get("policy") or {}
    return {
        "project": project.name,
        "run": registration["run"],
        "seed": settings["seed"],
        "envs": settings["envs"],
        "iterations": settings["iterations"],
        "init_from": relative(settings.get("init_from"), project),
        "budget_s": registration["budget_s"],
        "task_sha256": registration.get("task_sha256"),
        "state": status["state"],
        "iterations_run": status.get("iterations_run"),
        "started_at": status["started_at"],
        "supervised_s": status["wall_time_s"],
        "trainer_s": receipt.get("wall_time_s"),
        "policy_sha256": policy.get("sha256"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("projects", type=Path, nargs="+")
    args = parser.parse_args()
    rows = []
    for project in args.projects:
        project = project.resolve()
        for run_dir in sorted((project / "runs").iterdir()):
            if (run_dir / "registration.json").is_file() and (run_dir / "training-status.json").is_file():
                rows.append(run_row(project, run_dir))
    rows.sort(key=lambda row: row["started_at"])
    receipt = {
        "schema": "ot11-run-ledger-v1",
        "source": "each project's runs/<run>/registration.json and training-status.json",
        "runs": rows,
        "supervised_s_total": round(sum(row["supervised_s"] for row in rows), 2),
    }
    args.out.write_text(json.dumps(receipt, indent=1) + "\n", encoding="utf-8")
    print(f"{len(rows)} runs, {receipt['supervised_s_total']} s supervised")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
