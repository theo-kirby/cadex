---
node_id: 11db59df-f615-5abd-91c6-1420d3d5f72b
slug: smooth-vine-2389
title: G6. A closing report carries every outcome and is accepted by the critic
created_at: '2026-09-20T18:48:22+00:00'
parents:
- ancient-vine-9908
summary: ''
---
Status: working

## Current

**Met in its artifacts and tests; what remains is the owner's tick and the critic's acceptance [rec: rough-ridge-4729].** `docs/probes/ot8/REPORT.md` (commit `340b2334`, ADR-403) carries one row per experiment — frozen prompts with digests, turns, model, continuations used, accepted identity, static fit per turn, final static and swept checks, smoke, inventory, actor edits, remaining defects, and the ot7 comparison [rec: rough-ridge-4729].

**Success bars are held apart from the control-blocked outcome.** An **Outcome** column ot7's table lacked reads **success — every bar met** for G2 and G3 and **control-blocked — not a design success** for G4, whose smoke cell still reads **fail**; the report states "A finished experiment is not a design success." [rec: rough-ridge-4729].

The slot ledger totals **three dispatches, two slots spent, one void** (the `ot8-heron` session-limit cut-off, ADR-355), zero interrupted, zero unreached, and **nine of nine continuations unspent**. G2's remaining defects are stated as none against the bar, compared to `ot7-heron-c`'s four modified servo/horn parts. A G1–G5 evidence table links all five retained receipts, the contract, the prompts, `balance_diagnosis.py`, four ADRs and six record nodes by path. The report states ot8 did not re-run ot7 and that ot7's projects were read read-only and hashed before and after. Done is claimed under the exhaustion policy with **no owner checkbox ticked** [rec: rough-ridge-4729].

`cli/tests/test_ot8_report.py` (11 tests, sibling of `test_ot7_report.py`) pins all of it, including exactly two success rows and G4's `**fail**` smoke; all eleven fail with the report absent. CLI suite 914 passed, 1 skipped; engine suite 2196 passed, 53 skipped [rec: rough-ridge-4729].

## Negative knowledge

None.

## Provenance

- keen-stone-1720 — the criterion as the ot8 charter declares it
- rough-ridge-4729 — the closing report written and test-pinned (ADR-403), done claimed without an owner tick
