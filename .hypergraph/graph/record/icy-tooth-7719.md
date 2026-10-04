---
node_id: 411957e8-6af2-5005-bef7-8c3592756074
slug: icy-tooth-7719
title: 'orun2 W1: ADR-520 — a stale policy is refused without locking the project; packaged gate and both suites green'
created_at: '2026-10-04T02:34:41+00:00'
parents:
- red-loom-2239
summary: ''
artifacts:
- src/Mod/cadex/cadex_tests/test_restore_stale_policy.py
- cli/tests/test_stale_policy_note.py
---
## What

ADR-520 (commit `ef69dd39`, iteration 42, which landed without a record): a
project whose declared policy was trained before ADR-469 now **opens**
instead of failing with `CADEXD_RESTORE_FAILED`. The open reports
`restore: {performed: false, stale_policy: {output, reason, error, correction,
*_sha256}}`. The open is admitted only when the restore run failed because
the worker refused an `assembly.policy` output at its `policy_model` stage
for one of five reasons (`cadexd.STALE_POLICY_REASONS`):
`policy_task_mismatch`, `policy_model_mismatch`, `policy_channels_mismatch`,
`policy_actions_mismatch` and `policy_output_range_mismatch`. The policy is
still refused at every build that declares it. Nothing is re-accepted. The
CLI adds a note to the envelope naming the output and the two ways out:
retrain, or set the policy aside.

## Why

Written now because the critic's verdict on iteration 42 asked for it first:
the fix was accepted, but iteration 42 minted no record, so the broken node
`brisk-rock-9862` had nothing to close it. The critic also asked for the
packaged lifecycle gate, because the reply shape of `open_project` changed
(one optional `restore` key, declared in `OP_RESPONSE_SPECS` and pinned by a
new golden). That gate was not run in iteration 42, so it was run here.

## Method

- **Code (iteration 42, `ef69dd39`):**
  - `src/Mod/cadex/cadexd.py`, about 72 lines;
  - `CadexdProtocol.py`, one response-spec key;
  - the golden `open_project.stale_policy.json`;
  - the `restore` section of `docs/INTEGRATION.md`;
  - `cli/cadex_cli/__main__.py`, the note.
- **Tests:**
  - `src/Mod/cadex/cadex_tests/test_restore_stale_policy.py` covers each of
    the five reasons. Each one opens, names the output, reason and both
    digests, and validates against the pinned spec, with the accepted state
    and the candidate record unchanged. Four cases still refuse the open: a
    corrupt container, a disagreeing witness, the right reason at another
    stage, and a script that will not run.
  - `cli/tests/test_stale_policy_note.py` covers the note.
- **Gates (run this iteration on that tree, unchanged since):**
  - `pixi run build-engine` exit 0;
  - `pixi run stage-engine` exit 0, giving
    `build/engine/cadex-engine-0.0.0-linux-x64/` (3.2 GB);
  - the packaged gate, `CADEX_ENGINE_ROOT=<payload> pytest
    src/Mod/cadex/cadex_tests/test_cadexd_lifecycle.py`;
  - `pixi run test-engine`;
  - `CUDA_VISIBLE_DEVICES= pixi run python -m pytest cli/tests`.
- **Reproduction:** `~/cadex-projects/orun2-w1-robin`, a whole copy of
  `ot11-robin-1` and the project iteration 41 found locked. This iteration
  ran `cadex params --set policy_on=0` on it. Iteration 42 had proved the
  open only on a scratch copy of it.

## Result

**True now: a project trained before ADR-469 opens, names its stale policy,
and can be set aside or retrained from the CLI.**

| Gate | Result |
|---|---|
| Packaged lifecycle gate | **24 passed**, 0 failed, 0 skipped (21.6 s) |
| `pixi run test-engine` | **2606 passed, 56 skipped**, 0 failed (5 min 52 s) |
| CLI suite, GPU hidden | **1400 passed, 1 skipped**, 0 failed (20 min 8 s) |

The 56 engine skips and the 1 CLI skip are the standing environmental and
MJX-gated skips.

On `orun2-w1-robin`:
- `cadex params --set policy_on=0` returned `ok: true` and accepted
  `bab6fa28`. Before ADR-520, every command on this project failed at
  `open_project`.
- The walk and evaluation in the next record then ran on it end to end.

No concern is left open. ADR-469's other casualties (`ot9-robin`, the
`ot5`/`ot6` copies) open the same way. They were not opened here, because
they are read-only under the charter.

Dispatch closed: 1 unit — the missing record for ADR-520 (stale policy refused without locking the project), with the packaged gate and both suites green

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/orun2
- commit: fbdf9d88f6d1d3d6ecbe4022028cf47363538da9

## State Impact

- target: brisk-rock-9862 — resolved (status → working): ADR-520 (ef69dd39) opens a project whose policy predates ADR-469 with restore.stale_policy named instead of CADEXD_RESTORE_FAILED; pinned by test_restore_stale_policy.py and test_stale_policy_note.py; orun2-w1-robin reproduction now opens and accepts params policy_on=0; packaged gate 24/24, engine 2606 passed, CLI 1400 passed
- target: calm-peak-5247 — a pre-ADR-469 trained project opens with its stale policy named (ADR-520) and can be set aside or retrained
