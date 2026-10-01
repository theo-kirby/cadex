"""Collect every stored ot11 evaluation, and every judge score, into one receipt.

C1 asks REPORT.md to list every evaluation and every judge score. Each
evaluation the product stored is ``evaluations/<key>/evaluation.json`` in the
project that ran it, written by ``cadex evaluate`` (or the agent's
``evaluate`` tool, which is the same code). Each judge score is a
``retained/judge-*.json`` receipt written by ``runner/judge.py``. This reads
those and nothing else, keeps no machine path, and writes one receipt the
report's tables are held to.

Rows are in the order the projects are named on the command line, then by
the start of the run that trained the policy, then by when the evaluation
was written.

Which run trained an evaluated policy is found by hashing: every policy file
under a *registered* run's ``train/`` directory (one with a
``registration.json``, the same rule ``run_ledger.py`` uses) is hashed, and
an evaluation's ``policy_sha256`` is looked up among them. A policy that no
ot11 run trained -- ot10's ``w2-2`` and ot9's ``r3-ppo-1``, measured as
known negatives -- is left unattributed rather than guessed.

    pixi run python docs/probes/ot11/runner/eval_ledger.py \\
        --out OUT.json --judges docs/probes/ot11/retained PROJECT [...]
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def policy_tag(name: str) -> str:
    """``walk_task.000300.cxpolicy`` -> ``it 300``; the final and best by name."""

    parts = name.split(".")
    if len(parts) == 3 and parts[1].isdigit():
        return f"it {int(parts[1])}"
    if len(parts) == 3 and parts[1] == "best":
        return "best"
    return "final"


def trained_policies(project: Path) -> dict[str, tuple[float, str]]:
    """sha256 -> (run start, ``<run> <tag>``) over every registered run's policy files.

    A final policy is preferred over a checkpoint with the same bytes, and a
    checkpoint over ``best``, so a label names the file a reader would open.
    """

    rank = {"final": 0, "best": 2}
    found: dict[str, tuple[int, str, float]] = {}
    runs = project / "runs"
    if not runs.is_dir():
        return {}
    for run_dir in sorted(runs.iterdir()):
        if not (run_dir / "registration.json").is_file():
            continue
        status = json.loads((run_dir / "training-status.json").read_text(encoding="utf-8"))
        for policy in sorted((run_dir / "train").glob("*.cxpolicy")):
            tag = policy_tag(policy.name)
            digest = hashlib.sha256(policy.read_bytes()).hexdigest()
            entry = (rank.get(tag, 1), f"{run_dir.name} {tag}", status["started_at"])
            if digest not in found or entry < found[digest]:
                found[digest] = entry
    return {digest: (started, label) for digest, (_, label, started) in found.items()}


def evaluation_row(project: Path, report: Path, trained: dict[str, tuple[float, str]]) -> dict:
    evaluation = json.loads(report.read_text(encoding="utf-8"))
    summary = evaluation["summary"]
    seeds = summary["seeds"]
    film = evaluation.get("film") or {}
    started, trained_by = trained.get(evaluation["policy_sha256"], (0.0, None))
    return {
        "project": project.name,
        "key": report.parent.name,
        "written_at": report.stat().st_mtime,
        "label": evaluation.get("label"),
        "weights": evaluation.get("weights"),
        "policy_sha256": evaluation["policy_sha256"],
        "trained_by": trained_by,
        "run_started_at": started,
        "accepted_revision": evaluation["accepted_revision"],
        "verdict": evaluation["verdict"],
        "seeds": seeds,
        "passed": len(summary["passed"]),
        "failed": len(summary["failed"]),
        "void": len(summary["void"]),
        "failing_predicates": {
            predicate["id"]: seeds - predicate["passed"]
            for predicate in summary["predicates"]
            if predicate["passed"] < seeds
        },
        "terminations": dict(sorted(summary.get("terminations", {}).items())),
        "film": film.get("state"),
    }


def judge_row(path: Path) -> dict:
    judge = json.loads(path.read_text(encoding="utf-8"))
    evaluation = judge["evaluation"]
    return {
        "receipt": path.name,
        "label": judge["label"],
        "behaviour": judge["behaviour"],
        "model": judge["model"],
        "seed": judge["seed"],
        "calls": judge["calls"],
        "medians": judge["medians"],
        "total": judge["total"],
        "bar": judge["bar"],
        "meets_bar": judge["meets_bar"],
        "verdict": evaluation["verdict"],
        "accepted_revision": evaluation["accepted_revision"],
        "policy_sha256": evaluation["policy_sha256"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--judges", type=Path, required=True,
                        help="the directory holding the judge-*.json receipts")
    parser.add_argument("projects", type=Path, nargs="+")
    args = parser.parse_args()
    rows = []
    for index, project in enumerate(args.projects):
        project = project.resolve()
        trained = trained_policies(project)
        found = [evaluation_row(project, report, trained)
                 for report in (project / "evaluations").glob("*/evaluation.json")]
        # In the order the projects are named, then the runs were trained, then
        # the evaluations were written. A file's time alone would put a policy
        # re-read later (ADR-467) after the runs that followed it.
        found.sort(key=lambda row: (row["run_started_at"], row["written_at"]))
        rows.extend(found)
    judges = [judge_row(path) for path in sorted(args.judges.glob("judge-*.json"))]
    for judge in judges:
        judge["evaluations"] = [
            f"{row['project']}/{row['key']}" for row in rows
            if (row["accepted_revision"], row["policy_sha256"])
            == (judge["accepted_revision"], judge["policy_sha256"])
        ]
    receipt = {
        "schema": "ot11-evaluation-ledger-v1",
        "source": "each project's evaluations/<key>/evaluation.json, and retained/judge-*.json",
        "evaluations": rows,
        "judges": judges,
    }
    args.out.write_text(json.dumps(receipt, indent=1) + "\n", encoding="utf-8")
    print(f"{len(rows)} evaluations, {len(judges)} judge scores")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
