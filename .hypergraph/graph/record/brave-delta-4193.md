---
node_id: 8e228b7a-32c7-5e48-bdf9-0bbc43de3303
slug: brave-delta-4193
title: Bounded arm walk reproduces committed inventory and clearance review
created_at: '2026-09-07T23:11:54+00:00'
parents:
- mellow-beacon-8815
summary: ''
---
## What

Reran the documented hinged-arm lifecycle entry point in a fresh temporary
project: script design/assembly, MJCF/task export, bounded local CPU training,
policy installation and verification, rollout, inventory and clearance review.
This is the separate evidence unit requested before renderer implementation.
No product source, behavior, scaffold, roadmap checkbox or ADR changed.

## Why

Advances the frontier charter criterion “The agent can see its work without a
screen” (damp-moon-9297), serving missions 2 and 6, by revalidating the existing
review legs before adding named-angle images. It also refreshes evidence for
“The walk exists and is tested headlessly” (crisp-reef-5607).
This follows short item 1 in mellow-beacon-8815 and the overseer's rerun request.
The earlier requested reconciliation already has a checkpoint; contributor
rules prohibit further reconciliation here. No state, plan or charter edits.
Choose a fresh temporary project outside the repository to exercise project
commits without adding generated assets or machine paths to this repository.
No model call, GUI, remote dispatch, provisioning or human decision was needed.

## Method

From the repository root, with PROJECT a fresh temporary project directory:

```bash
./cadex script --project "$PROJECT" --set examples/lifecycle/hinged-arm/script.py --json
JAX_PLATFORMS=cpu ./cadex walk --project "$PROJECT" \
  --out "$PROJECT/runs/baseline" --trainer-python "$PWD/.venv/bin/python" \
  --iterations 1 --envs 4 --seed 0 --timeout 600 --json
JAX_PLATFORMS=cpu pixi run python -m pytest cli/tests -q
```

Use the existing training venv described in training/SETUP.md. An external
wrapper samples recursive process-tree RSS every 0.2 seconds; kill descendants
at 2,900,000,000 bytes or 850 seconds around each invocation (including the
whole CLI suite), in addition to the walk's 600-second trainer timeout.
Wall measurements include wrapper polling granularity; peak RSS is sampled,
not a kernel-enforced allocation ceiling. No cutoff triggered.

Assert all leg exits zero, CPU training, witness error below 1e-6, two inventory
components, clearance available with one checked/offending pair and zero unknowns,
and clearance revision equal to accepted rollout revision. Assert base/swing has
status “below clearance”, distance 0 mm and common volume 0 mm³. Compare bytes of
docs/inventory.md, docs/clearance.md, runs/baseline/review.json and PROGRESS.md
against git show HEAD:<path>; assert the project worktree is clean. Inspect the
trace's policy block and progress rows. Logs, resource receipts and the runtime
project remain temporary local evidence; no checkpoint or trace is added here.

## Result

Public script exit 0: 1.5220 seconds, sampled peak tree RSS 236,224,512 bytes.
Public walk exit 0: 15.2430 seconds, sampled peak tree RSS 1,054,392,320 bytes.
Review leg timings: train 11.38 s, declare 1.26 s, rollout 1.43 s; trainer receipt
wall time 1.187884875 s. These are whole-leg/whole-command measurements, not
isolated rebuild timings, and do not measure rendering acquisition or rendering.
Whole-walk cost is +0.7257 s (+5.00%) versus 14.5173 s in clear-ash-2884 and
+0.8530 s (+5.93%) versus the earlier 14.39 s. One sample is not a regression
benchmark; all commands stayed well inside the training resource limits.

CPU receipt: 4,609 parameters, final training reward/step -0.3801981508731842,
witness error 1.3841167412209642e-09. Verified rollout: 50 control steps, seed 3
(the recipe's rollout seed; training seed is 0), total reward
-27.109384220927513, lift -27.10907313052507, control_cost
-0.000311090402448284; truncated at the declared horizon, no early termination.
These reward and witness numbers reproduce the previous arm baseline.

Inventory: two procedural components, zero catalogued. Clearance: one checked
base/swing pair, one below-clearance finding, zero unknowns; 0 mm separation,
0 mm³ common volume, at 0.1 mm / 1e-6 mm³ thresholds in the initial solved pose.
The finding remains visible rather than failing the walk. Review revision
fe90d2fae75e91c34394ade5aa8f019468c87fc296912e5d26efdf5089a49845
matches the accepted rollout. Project commit
191c33e9723dc2b36ac80d7e39268d36957a26ed contains the four byte-checked review
and progress files, and its working tree is clean. PROGRESS.md carries training,
rollout reward and clearance counts. All explicit assertions passed.

Full built-engine CLI zone gate exit 0: 161 passed, zero skipped, 164.07 s.
External gate monitor: 164.6941 s, sampled peak tree RSS 1,140,097,024 bytes,
no cutoff. No engine/protocol/payload or shell changes; no build or packaged
or shell gate was required for this evidence-only unit. No failed leg remains.
Graph export/check before recording passed with zero violations and warnings;
post-mint export/check also passed with zero violations and warnings.

Next: short item 2, deliver ADR-239's named-angle CPU tessellation renderer as
one CLI call, then integrate it into the walk in a separate unit. Named-angle
rendering, named-plane sections and their walk integrations are still missing
before the headless-review criterion can be ticked. This rerun refreshes the
working walk evidence; it does not close the review frontier or the whole goal.
The tail becomes two unreconciled records; reconciliation stays with maintainer.
Dispatch closed: 1 unit — bounded public arm walk reproduces verified rollout and committed inventory/clearance review; CLI gate green.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/nt3
- commit: 0251a712511df7bfcf094fae6d90ee272c4c9b01

## State Impact

- target: damp-moon-9297 — Fresh bounded public arm walk preserves committed inventory and clearance, one below-clearance pair and zero unknowns; CLI gate 161 passed, zero skipped. Named-angle rendering and sections with walk integration remain open.
- target: crisp-reef-5607 — Fresh documented script and walk pass with local CPU training, verified 50-step rollout and unchanged baseline reward; whole walk 15.2430 s and sampled peak tree RSS 1,054,392,320 bytes.
