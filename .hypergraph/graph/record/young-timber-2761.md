---
node_id: 001d5208-6598-5cef-af6d-91cbc8611985
slug: young-timber-2761
title: Quill stroke iterate preserves the objective and exposes comparison limits
created_at: '2026-09-08T20:01:48+00:00'
parents:
- lucky-creek-4303
summary: ''
---
## What

Ran the requested parameter-only ot4-quill iterate through the unchanged public
walk and documented its measured comparison in docs/CLI.md and ROADMAP.md.

## Why

Advances mission 2 and the charter's “The walk exists and is tested headlessly”
and “The walk holds on a second mechanism” criteria through another real
iterate on the third mechanism. Those criteria already have working evidence;
this unit strengthens their revisit/compare evidence, not gait quality.
Follows lucky-creek-4303 and the overseer's explicit next unit. Assumption:
keep cold training seed 0 and rollout seed 7; stroke 60 preserves reward literals.

## Method

From the repo root, with PROJECT the durable ot4-quill project:

```bash
JAX_PLATFORMS=cpu ./cadex walk --project "$PROJECT" \
  --out "$PROJECT/runs/stroke60-iterate29" --set stroke=60 \
  --name quill_stroke60_29.cxpolicy --iterations 5 --envs 16 --seed 0 \
  --timeout 600 --leg-timeout 120 --json
```

No prompt, provider tokens or remote execution. A /proc descendant monitor
sampled every 0.2 s, with 2.9 GB RSS and 850 s whole-walk cutoffs. Logs,
monitor receipt, task exports and baseline hashes stay under that project run.
Compared both reviews' actual parameters and both exported task objects;
checked four successful legs and available review eyes, CPU receipt, policy
SHA256 and preservation of all 19 baseline run files. These assertions passed.
This is a documentation/rehearsal unit, no implementation or scaffold behavior
change; no build or source pytest gate was run. git diff --check passed.

## Result

Exit 0, 24.613927 s external wall, 24.407433 s walk, peak tree RSS
1,984,507,904 bytes. Sweep/train/declare/rollout took 1.08/19.49/0.92/1.01 s;
trainer receipt CPU, 3.683735 s, witness error 2.0915064e-08. Engine/source
comparison matched all 56 top-level Python files.

Only actual stroke changed, 40 to 60 mm. Task objects differ only in model
metadata and action high 40 to 60 mm. Reward expressions/weights, observation
units, horizon (4 s, 50 Hz, 200 steps), termination, randomisation and
disturbance match. Geometry changed too: housing top 147 to 164 mm, quill top
135 to 152 mm. Rollout total reward -74.7919752856 to 175.4872111451,
delta +250.2791864307. Quill travel 20.2835524809 to 30.0784694363 mm,
delta +9.7949169555; rotation 0 to 0 degrees. Both use 201 solved frames.
Trainer reward/step -0.5796215534 to -1.0196909904 is a different batch.

PROGRESS.md has reward delta in the rollout params row and both motion deltas
in the walk row. Displayed travel delta +9.798 uses rounded prior 20.28;
it is not the exact review delta. Target 30 mm is now action midpoint, so
near-zero normalized actions command the target; changed geometry/action
scaling and one seed prevent a control-quality or significance conclusion.
Four reviews available, two components, no catalogue ids, two domain notes,
none missing. Initial-pose housing/quill intersection remains 960 mm³;
section XZ at 3.125 misses the quill. No swept-fit certification.

Project walk committed acbcb6e. Although the new run directory stayed ignored,
the CLI explicitly staged the stored policy despite local exclusion and
committed new review outputs. Forward project commit 076ac50 untracked those
new outputs, kept their files locally, added ignores and comparison caveats.
No history rewritten; the accidental generated commits remain in project
history. Nothing generated is added to the product repo. Baseline bytes intact.
This concrete artifact-retention failure needs a subsequent bounded fix before
another walk under the charter's no-generated-commits rule; seed/objective row
identity remains the other planned next unit. No additional mechanism or
parked rung was opened. Three records now await the separate maintainer.
Dispatch closed: 1 unit — bounded quill stroke iterate and measured comparison.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot4
- commit: ee47db39d52fc49690732a1a07430a44e2aa1176

## State Impact

- target: calm-peak-5247 — Quill stroke 40 to 60 iterate passed CPU 5x16 with fixed objective; reward +250.279186 and travel +9.794917 mm / 0 degrees, single-seed action-scaling caveats documented.
- target: chilly-union-8972 — Real walk comparison uses rounded previous travel; CLI automatic project commits staged new stored policy and review outputs despite local policy exclusion, requiring forward untracking and a subsequent retention fix.
