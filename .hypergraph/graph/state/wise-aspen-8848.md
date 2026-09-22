---
node_id: a82e42f5-b181-58fc-b1bb-82d40b1c0c1b
slug: wise-aspen-8848
title: G1. The follow-up has a frozen, bounded experiment contract
created_at: '2026-09-20T18:48:21+00:00'
parents:
- ancient-vine-9908
summary: ''
---
Status: working

## Current

**G1 is met in its artifacts and its tests; what remains for the owner's tick is the closing report, which is G6's work [rec: honest-ash-4208].** The freeze went in before any product turn was dispatched, which is the ordering the charter exists to enforce — no prompt can be tuned to a measurement it has already seen.

**The contract [rec: honest-ash-4208].** `docs/probes/ot8/README.md` identifies the three ot7 baselines with their pins, allocates one initial product prompt plus at most three continuations per design, states the success and failure bar for G2, G3 and G4 and what no bar may be passed with, carries the five-column slot ledger (completed / failed / void / interrupted / unreached) and the commands, and records the verified Opus access reading. `docs/probes/ot8/baselines.json` pins the identity of `ot7-heron-c`, `ot7-plover-e` and `ot7-robin-c`, read from the operator's projects read-only. `docs/probes/ot8/retained/g1-window-probe.json` holds the pre-freeze access reading: `claude-opus-5` allowed, five-hour window 10 %, seven-day 16 %, answered in 3.7 s. A probe carries no project and no tools, so it spends no slot.

**Six frozen prompts with a digest manifest** under `docs/probes/ot8/prompts/` [rec: honest-ash-4208]. The arm's create prompt is byte-identical to ot7's, and so to ot6's receipt, which is what keeps G2 a comparison of one ask. `rebuild.prompt.txt` (G3) and `resolve.prompt.txt` (G4) are the two seeded designs' initial prompts; `continue-1..3` are ot8's own. Two judgement calls are argued in `prompts/README.md` rather than hidden: **ot8's continuations are not ot7's** — ot7's direct the agent to the measured fit report alone, while ot8's direct it to "its measured fit, inventory and smoke evidence", because the arm's open gap is one the inventory names and the fit report does not; and **`resolve.prompt.txt` says a behaviour check is failing**, naming no part, no number and no defect, and giving "change nothing and state the missing control contract" equal standing with a repair — a prompt satisfiable only by making the check pass would be this run asking for the cheat its own charter forbids.

**The ot7 collector is reused, not forked (ADR-400) [rec: honest-ash-4208].** `docs/probes/ot7/runner/run.py` gained a `run` id: `--run ot8` selects the ot8 prompt root, the `ot8-*` project prefix and its two seeded designs, while a receipt with no `run` field is still ot7's. One `attempt_dir()` replaced three duplicated lookups and a `SEEDED` table is keyed by (run, design); `frozen`, `remaining`, `resume`, `smoke` and `reclassify` are otherwise unchanged, so the slot rules ot7's receipts rest on have one home. One behaviour is new for ot8's seeded attempts: the baseline is measured **and smoked** before any prompt is sent, with seed identity held equal across both. The measurement gates dispatch, as ot7's did; the smoke never does — G3 and G4 exist precisely because these baselines fail it.

**The seed-copy procedure is now part of the contract, because its first use showed it missing [rec: sunny-quill-9617].** `docs/probes/ot8/README.md` states how a seeded design's copy is prepared — every file of the baseline except `evidence/`, `agent.json` and `.cadex-cli.lock` — and that the attempt's own evidence directory is created exclusively while a copy that carries none is *started* rather than refused. `run()` matches: the parent is created with `exist_ok=True` before the exclusive `evidence.mkdir()`. Before that fix the first G3 dispatch crashed with a `FileNotFoundError` before sending anything, no prompt and no slot touched — the ot7 repair seed carried an `evidence/`, so nothing had exercised the case. It is pinned by `test_a_seeded_attempt_starts_on_a_copy_that_carries_no_evidence`, which fails on the old code and still asserts that a second dispatch on the same copy refuses.

**Test evidence [rec: honest-ash-4208] [rec: sunny-quill-9617].** `cli/tests/test_ot8_prompts.py` (8) and `cli/tests/test_ot8_runner.py` (22) pass; ot7's own 100 tests pass unchanged against the generalised collector. At the freeze: `pixi run test-engine` 2196 passed / 53 skipped, `pytest cli/tests` 891 passed / 1 skipped. After the collector fix: 892 passed / 1 skipped, engine unchanged. No engine protocol or payload change, so no packaged gate was owed.

*Reconcile judgement*: `working` rather than `open`, following the ot7 precedent that a criterion whose evidence exists is `working` while the human owns the checkbox. G1's artifacts, tests and freeze are all in place [rec: honest-ash-4208]; the one clause of the criterion still outstanding — the closing report's ot8-vs-ot7 distinction and its every-failed/void/interrupted/unreached table — is G6's unit, not a gap in the contract itself [rec: honest-ash-4208].

## Negative knowledge

- [scope: a seeded attempt whose project copy excludes the baseline's `evidence/` | confidence: high | evidence: sunny-quill-9617] The collector's non-recursive `evidence.mkdir()` crashes before any prompt is sent. ot7's repair seed carried an `evidence/` parent, so the path was never exercised until ot8's first seeded copy. Fixed and pinned; recorded because the same shape — a directory the old seed happened to provide — is what a mechanically prepared copy removes.

## Provenance

- keen-stone-1720 — the criterion as the ot8 charter declares it
- honest-ash-4208 — G1 frozen: the contract, six prompts with their digest manifest, the baseline pins, the pre-freeze window probe, the collector reused under `--run ot8` (ADR-400), and 30 new tests, with both full suites green
- sunny-quill-9617 — the contract and the collector amended together after the first seeded copy crashed: the three-exclusion copy procedure written down, `evidence.parent.mkdir(exist_ok=True)`, and the regression that fails on the old code
