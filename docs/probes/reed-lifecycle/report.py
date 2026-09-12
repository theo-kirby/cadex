# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""Assemble the fresh biped's lifecycle report from what the project retains.

PYTHONPATH=cli pixi run python docs/probes/reed-lifecycle/report.py PROJECT \
    [--operator-check operator.json] > docs/probes/reed-lifecycle/report.json

Reads only: every ``runs/<name>/run.json`` through the review reader, the
model view the dashboard would serve for each run, and the committed
common-seed evaluation rows. It writes nothing into the project and starts
no server. The operator check is the output of
``docs/probes/operator-review/verify.py`` against the persistent URL, passed
in so the report carries the identities that check observed.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from cadex_cli.review_record import read_run_record
from cadex_cli.review_server import accepted_model, run_model

REPO = Path(__file__).resolve().parents[3]
PROBES = REPO / "docs" / "probes"

# Where each design's common-seed rows live, and the policy label used there.
SEED_SOURCES = {
    "probe3-checkpoint20": ("reed-baseline/results.json", "probe3-checkpoint20"),
    "probe3-final": ("reed-baseline/results.json", "probe3-final"),
    "foot90": ("reed-foot90/results.json", "foot90"),
}

TRAINING_SNAPSHOT_SOURCES = (
    "assembled model retained before training",
    "retained training export parts at this run's revision; assembly placements "
    "not recorded (parts shown at identity, not a solved pose)",
)

# The evidence each criterion rests on: documents in this repository, the
# compact probe files beside them, the ADRs and the record-graph nodes.
EVIDENCE_INDEX = {
    "D1": {
        "title": "A live project dashboard is reachable",
        "docs": ["docs/CLI.md", "docs/probes/operator-review/README.md"],
        "probes": ["docs/probes/operator-review/evidence.json"],
        "tests": ["cli/tests/test_review_server.py"],
        "adrs": ["ADR-286"],
        "records": ["rapid-crest-8826"],
    },
    "D2": {
        "title": "The browser shows the right model and specs",
        "docs": ["docs/HEADLESS-BIPED-REVIEW.md"],
        "probes": ["docs/probes/reed-foot90/evidence.json", "docs/probes/reed-copy/evidence.json"],
        "tests": ["cli/tests/test_review_server.py", "cli/tests/test_walk.py"],
        "adrs": ["ADR-289", "ADR-290", "ADR-291", "ADR-293", "ADR-302"],
        "records": ["rapid-crest-8826", "lively-gate-6535", "misty-trail-1655", "quiet-arbor-0259",
                    "light-brook-2640", "candid-forest-9800", "forest-ledge-2219", "fair-crow-5108"],
    },
    "D3": {
        "title": "Training is visible while it runs",
        "docs": ["docs/HEADLESS-BIPED-REVIEW.md"],
        "probes": ["docs/probes/reed-agentrev/evidence.json"],
        "tests": ["cli/tests/test_review_server.py", "cli/tests/test_train.py"],
        "adrs": ["ADR-287", "ADR-288", "ADR-289", "ADR-296", "ADR-297", "ADR-298"],
        "records": ["kind-fountain-5086", "merry-star-6951", "young-cedar-2719", "neat-vine-2517",
                    "dusty-oak-7376", "fair-crow-5108"],
    },
    "D4": {
        "title": "Policy videos render, persist and play headlessly",
        "docs": ["docs/HEADLESS-BIPED-REVIEW.md", "docs/probes/review-style/README.md"],
        "probes": ["docs/probes/reed-agentrev/evidence.json", "docs/probes/review-style/implementation.json"],
        "tests": ["cli/tests/test_video.py", "cli/tests/test_review_server.py"],
        "adrs": ["ADR-300", "ADR-301"],
        "records": ["amber-gate-7498", "merry-star-6951", "light-brook-2640", "royal-arrow-2065",
                    "fair-crow-5108"],
    },
    "D5": {
        "title": "Review history survives a design change",
        "docs": ["docs/HEADLESS-BIPED-REVIEW.md"],
        "probes": ["docs/probes/reed-foot90/evidence.json", "docs/probes/reed-foot90/results.json",
                   "docs/probes/reed-agentrev/evidence.json"],
        "tests": ["cli/tests/test_review_record.py", "cli/tests/test_walk.py"],
        "adrs": ["ADR-285", "ADR-291", "ADR-292", "ADR-293"],
        "records": ["wild-cove-4437", "quiet-arbor-0259", "light-brook-2640", "candid-forest-9800",
                    "forest-ledge-2219"],
    },
    "D6": {
        "title": "Save, reopen and restart preserve the project",
        "docs": ["docs/HEADLESS-BIPED-REVIEW.md"],
        "probes": ["docs/probes/reed-foot90/evidence.json"],
        "tests": ["cli/tests/test_review_lifecycle.py"],
        "adrs": ["ADR-291"],
        "records": ["shady-bay-0771", "simple-quartz-9812", "candid-forest-9800", "weathered-sage-2750"],
    },
    "D7": {
        "title": "Save-As/copy produces an independent project",
        "docs": ["docs/HEADLESS-BIPED-REVIEW.md", "docs/CLI.md"],
        "probes": ["docs/probes/reed-copy/evidence.json"],
        "tests": ["cli/tests/test_review_lifecycle.py"],
        "adrs": ["ADR-294"],
        "records": ["careful-gate-4868", "clever-fern-7568"],
    },
    "D8": {
        "title": "Interrupted and failed runs remain understandable",
        "docs": ["docs/HEADLESS-BIPED-REVIEW.md"],
        "probes": ["docs/probes/reed-copy/video-recovery.json"],
        "tests": ["cli/tests/test_review_server.py", "cli/tests/test_review_lifecycle.py"],
        "adrs": ["ADR-287", "ADR-288", "ADR-289", "ADR-295", "ADR-296"],
        "records": ["merry-star-6951", "light-brook-2640", "icy-pond-7346", "young-cedar-2719",
                    "neat-vine-2517", "dusty-oak-7376", "weathered-sage-2750"],
    },
}


def summarize_seed_rows(rows: list[dict]) -> dict:
    """Falls, survivors, mean duration and mean forward displacement over one policy's rows."""
    seeds = sorted(row["seed"] for row in rows)
    falls = sum(1 for row in rows if row["fell"])
    survivors = sum(1 for row in rows if row["time_limit_reached"])
    policies = {row["policy_sha256"] for row in rows}
    if len(policies) != 1:
        raise ValueError(f"rows mix policies: {sorted(policies)}")
    return {
        "seeds": seeds,
        "episode_limit_s": sorted({row["episode_limit_s"] for row in rows})[0],
        "falls": falls,
        "survivors": survivors,
        "mean_observed_s": round(sum(row["observed_s"] for row in rows) / len(rows), 3),
        "mean_forward_displacement_mm": round(sum(row["displacement_mm"][0] for row in rows) / len(rows), 3),
        "observed_s": [row["observed_s"] for row in sorted(rows, key=lambda r: r["seed"])],
        "forward_displacement_mm": [round(row["displacement_mm"][0], 3)
                                    for row in sorted(rows, key=lambda r: r["seed"])],
        "policy_sha256": policies.pop(),
    }


def common_seed_comparison() -> dict:
    """The same declared seeds and episode limit over every design that was evaluated on them."""
    designs: dict[str, dict] = {}
    for run, (relative, label) in SEED_SOURCES.items():
        payload = json.loads((PROBES / relative).read_text())
        rows = [row for row in payload["rows"] if row["policy"] == label]
        summary = summarize_seed_rows(rows)
        summary["source"] = "docs/probes/" + relative
        designs[run] = summary
    agentrev = json.loads((PROBES / "reed-agentrev" / "evidence.json").read_text())["ten_seed_evaluation"]
    designs["shin55-final"] = {
        "seeds": agentrev["seeds"],
        "episode_limit_s": agentrev["episode_limit_s"],
        "falls": agentrev["falls"],
        "survivors": agentrev["survivors"],
        "mean_observed_s": agentrev["mean_observed_s"],
        "mean_forward_displacement_mm": agentrev["mean_forward_displacement_mm"],
        "observed_s": agentrev["observed_s"],
        "forward_displacement_mm": agentrev["forward_displacement_mm"],
        "policy_sha256": agentrev["policy_sha256"],
        "source": "docs/probes/reed-agentrev/evidence.json",
    }
    limits = {d["episode_limit_s"] for d in designs.values()}
    seed_sets = {tuple(d["seeds"]) for d in designs.values()}
    if len(limits) != 1 or len(seed_sets) != 1:
        raise ValueError("designs were not evaluated on one common seed set")
    return {
        "seeds": list(seed_sets.pop()),
        "episode_limit_s": limits.pop(),
        "designs": designs,
        "not_evaluated_on_common_seeds": {
            "copy100": "seed 0 only (D7 copy evidence); no ten-seed evaluation was run",
            "probe1-playback": "seed 0 only; the first probe's failed walk had no revision recorded",
            "probe2-checkpoint20": "seed 0 only; probe2 was interrupted at iteration 38",
        },
    }


def describe_view(model: dict) -> str:
    """Whether a run's model view is a training-time snapshot or a rollout pose."""
    source = model.get("source")
    if source is None:
        return "none"
    if source in TRAINING_SNAPSHOT_SOURCES:
        return "training snapshot"
    return "rollout view"


def run_identity(root: Path, name: str) -> dict:
    record = read_run_record(root / "runs" / name, root)
    model = run_model(root, record)
    components = model.get("components") or []
    retained = sum(1 for c in components if c.get("mesh_status") == "retained")
    videos = []
    for index, video in enumerate(record.get("videos") or []):
        videos.append({
            "index": index,
            "sha256": video.get("sha256"),
            "style": video.get("style"),
            "frames": video.get("frames"),
            "sim_seconds": video.get("sim_seconds"),
            "seed": video.get("seed"),
            "policy_sha256": video.get("policy_sha256"),
            "accepted_revision": video.get("accepted_revision"),
        })
    return {
        "run": name,
        "mode": record.get("mode"),
        "status": record.get("status"),
        "outcome": record.get("outcome"),
        "accepted_revision": record["model"].get("accepted_revision"),
        "digest": record["model"].get("digest"),
        "policy_sha256": (record.get("policy") or {}).get("sha256"),
        "rollout_seed": (record.get("rollout") or {}).get("seed"),
        "view": {
            "kind": describe_view(model),
            "source": model.get("source"),
            "reason": model.get("reason"),
            "components": len(components),
            "meshes_retained": retained,
            "meshes_missing": len(components) - retained,
        },
        "videos": videos,
        "problems": record.get("problems") or [],
    }


def build(root: Path, operator_check: dict | None) -> dict:
    accepted = accepted_model(root)
    components = accepted.get("components") or []
    runs = sorted(p.name for p in (root / "runs").iterdir() if (p / "run.json").exists())
    identities = [run_identity(root, name) for name in runs]
    return {
        "schema": "reed-lifecycle-report-v1",
        "project": root.name,
        "accepted": {
            "revision": accepted.get("revision"),
            "digest": accepted.get("digest"),
            "components": len(components),
            "meshes_retained": sum(1 for c in components if c.get("mesh_status") == "retained"),
        },
        "runs": identities,
        "common_seed_comparison": common_seed_comparison(),
        "evidence_index": EVIDENCE_INDEX,
        "persistent_operator_check": operator_check,
    }


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("project")
    parser.add_argument("--operator-check", help="output of docs/probes/operator-review/verify.py")
    args = parser.parse_args(argv)
    check = json.loads(Path(args.operator_check).read_text()) if args.operator_check else None
    json.dump(build(Path(args.project).resolve(), check), sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
