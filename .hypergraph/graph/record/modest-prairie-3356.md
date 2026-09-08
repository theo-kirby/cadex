---
node_id: b6d229ec-6be7-5165-b403-e14b79bfa61b
slug: modest-prairie-3356
title: Comparisons identify training and rollout seeds, objective and action scaling
created_at: '2026-09-08T20:31:53+00:00'
parents:
- easy-beacon-3803
summary: ''
---
## What

Train and walk comparisons identify the bounded training seed, the independent
rollout seed, a stable objective identity from exported task metadata, and a
separate action identity. Review JSON preserves the objective fields and full
action metadata. CLI docs, the project scaffold, ADR-263 and ROADMAP describe
the identity contract and its limitations.

## Why

Follows easy-beacon-3803 and the overseer's explicit second short-rung unit.
Advances missions 1/2 and the charter's tested headless lifecycle walk and
second-mechanism comparison criteria: a numeric delta needs evidence of what
changed. Those criteria already have working evidence; this strengthens their
comparison contract without claiming a new mechanism, mode or learning result.
Assumption: reuse exported metadata, preserve legacy rows and Git's existing
tracked/staged semantics, and identify declared objective syntax rather than
claiming mathematical or experimental equivalence.

## Method

The CLI accepts training seeds in 0..4294967295 and records the passed seed.
The review reads the rollout seed from the exported trace policy block, never
from that training flag. Objective v1 hashes compact key-sorted JSON of schema,
observations, reward, termination, episode and functions. Model identity,
actions, seeds and stochastic conditions are excluded; full actions are retained
and hashed separately. The quill's 40/60 mm action scaling can therefore differ
while objective identity stays fixed. Progress cells retain current and prior
same-kind row evidence; missing historical identity/seeds stay unavailable.
Existing per-metric delta references are unchanged and can name a different row.

Tests cover seed/model invariance, reward sensitivity, action-bound separation,
legacy rows, invalid seed bounds, trace seed parsing, and propagation through
the existing real CPU walk/iterate regression. No independent rehearsal,
provider turn, ranking, seed study, remote dispatch or GUI launch was run.

## Result

`pixi run python -m pytest cli/tests -q`: 244 passed, no skips, in
227.33 s; full output remains local at /tmp/cadex31-cli-verified.log. The
first full run passed 242 tests before the strengthened real-review assertions
and two seed-bound cases. The next run had 243 passes and one test-only failure:
the new assertion assumed rollout seed 7, while this toy fixture declares 3.
Corrected the assertion to 3, then reran the full suite successfully. The saved
real review reports training seed 0 and rollout seed 3, and the reward-weight
iterate changes objective identity. `git diff --check` passed. Engine, payload
and shell code were untouched; their build and packaged gates were not required.

No generated review dump or training asset enters this commit. The retention
fix's limits remain: existing tracked or explicitly staged artifacts still enter
ordinary Git commits; no project is silently migrated or untracked. Standalone
rollout numeric rows retain their old format; train/walk rows provide the new
evidence, and comparison prose explicitly distinguishes their prior-row reference
from per-metric delta references. Equal objective identity never proves equal
control difficulty, statistical significance or improvement.

Nothing new remains to tick the already-evidenced walk criteria on this unit's
account. Next is the plan's conditional project-history prompt iterate, subject
to its capacity and per-project retention constraints; no quota probes or parked
criterion opened here. The unreconciled tail reaches three records including
this one; reconciliation remains a separate role.
Dispatch closed: 1 unit — identify comparison seeds, objective and action scaling.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot4
- commit: 5b74b257d1a258feb9c970e46c774c311be1a70f

## State Impact

- target: chilly-union-8972 — Train and walk comparisons carry bounded training seeds, independent trace rollout seeds, exported-task objective identity and action identity; legacy evidence is unavailable. Retention semantics are unchanged. Full CLI suite passes 244 tests.
- target: calm-peak-5247 — Review JSON preserves objective fields and full action metadata; real CPU iterate test verifies seed propagation and changed objective identity after a reward change. Equal objective identity is explicitly not equal control difficulty; standalone rollout rows retain their prior numeric format.
