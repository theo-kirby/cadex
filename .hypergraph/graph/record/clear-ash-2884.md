---
node_id: bce2b07b-52ad-521f-beea-cbde2507567b
slug: clear-ash-2884
title: Walk review commits clearance findings and preserves unknown measurements
created_at: '2026-09-07T22:54:46+00:00'
parents:
- humble-stream-3878
summary: ''
---
## What

Wire accepted pair clearance into the lifecycle walk review (ADR-238).
The walk commits docs/clearance.md, its review.json summary and a dedicated
PROGRESS.md row together. The CLI call and walk share threshold constants.
Docs, shared mode-artifact table, project scaffold and recipe architecture
notes now describe the same artifacts.

## Why

Advances the charter criterion “The agent can see its work without a screen”
(damp-moon-9297), serving missions 6 and 2. Follow the overseer's requested
clearance integration and the second short bet in humble-stream-3878.
The overseer's reconciliation request conflicts with the explicit work-iteration
ban; no reconcile, state edit or plan edit was performed. The observed tail
had one pending record, not three. Treat this dispatch as the authorized
clearance wiring unit, rather than combining a separate rerun-only unit with it.

## Method

Reuse write_clearance in the existing restore=False inventory inspection
session, with no extra rebuild. Persist initial-pose scope, accepted revision,
0.1 mm minimum distance and 1e-6 mm³ maximum common volume, checked/offending/
unknown counts, offending pairs with labels/catalog identities, unknown pairs
with null measurements/errors, and the project-relative report path. Unavailable
counts are null. Findings do not fail a walk; inspection errors still do.
Remove the blanket walk progress-row suppression: the new row carries clearance
counts only, preserving the child legs' reward comparisons.

Run JAX_PLATFORMS=cpu pixi run python -m pytest cli/tests -q under a process-tree
RSS/wall monitor (2.9 GB and 850 s cutoffs). Exercise real toy/iterate and carriage
walks, project commits, local/remote-flag CPU stand-in parity, and unavailable,
unknown and inspection-failure reader boundaries. No SSH or GUI was launched.
The focused test first found a parity assertion incorrectly comparing accepted
revisions across separately trained policy hashes; correct it to retain each
revision and compare the findings, thresholds and report paths.

Also run the documented public script then walk commands from
examples/lifecycle/README.md for both recipes in fresh temporary project roots:
./cadex script --project PROJECT --set examples/lifecycle/MECHANISM/script.py --json
then JAX_PLATFORMS=cpu ./cadex walk --project PROJECT --out PROJECT/runs/baseline
--trainer-python "$PWD/.venv/bin/python" --iterations 1 --envs 4 --seed 0
--timeout 600 --json. The same 2.9 GB/850 s external monitor surrounds the two
sequential recipe runs. Assert inventory and clearance findings, tracked
reports/review/progress in HEAD and clean project working trees.

## Result

Full built-engine CLI suite: 161 passed, zero skipped, 165.42 s; external monitor
exit 0, 165.94 s, peak RSS 1,143,390,208 bytes. Initial focused run: 17 passed,
one test assertion failed (mode revision equality); fixed forward before the
full green run. No product failure remains.

Fresh public recipes: arm walk exit 0, 14.5173 s, total reward -27.1093842209,
witness error 1.3841167412e-09; base/swing distance 0 mm, common volume 0 mm³,
one below-clearance pair. Carriage walk exit 0, 13.1840 s, total reward
-24159.1953563045, witness error 5.4188947392e-09, one clear pair. Both have
zero unknown pairs and two inventory components. Both project HEADs track
docs/inventory.md, docs/clearance.md, runs/baseline/review.json and PROGRESS.md;
both working trees are clean. Combined recipe monitor exit 0, 29.66 s,
peak RSS 1,071,398,912 bytes. The arm's whole-walk cost is +0.1273 s (+0.88%)
versus the recorded 14.39 s baseline; this single sample is not a benchmark
or rebuild-latency claim. All training was local toy CPU, below either cutoff.
Logs and temporary projects are local evidence, not committed checkpoints.

The CLI zone gate passed; no engine/protocol/payload or shell code changed,
so no full build or packaged/shell gate was needed. ADR-238 logs the removed
row suppression and resulting behavior; ROADMAP ticks only clearance review.
Graph export/check passed with no violations or warnings before recording;
repeat after minting is required before the single commit.

Next: named-angle rendering probe, then render delivery and walk integration;
section-view call and its integration remain open too. Those are still missing
before the headless-review charter criterion can be ticked. The maintainer
retains reconciliation ownership; this record adds one impact to the tail.
Dispatch closed: 1 unit — clearance findings and explicit unknowns join the walk review and project commit.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/nt3
- commit: 891ece9d67ae37eb64d066c6053721cc9bd0feb8

## State Impact

- target: damp-moon-9297 — Clearance is wired into lifecycle review and project commits with explicit unavailable and unknown outcomes; real arm/carriage walks and CPU mode parity pass. Rendering and section calls with walk integration remain open.
- target: calm-peak-5247 — Walk review now commits docs/clearance.md, review.json clearance summary and comparable PROGRESS.md counts without an extra rebuild; CLI gate 161 passed.
