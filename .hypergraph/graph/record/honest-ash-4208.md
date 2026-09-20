---
node_id: db3bdc88-d0b8-5c81-8b36-7175bcad018a
slug: honest-ash-4208
title: Freeze the ot8 experiment contract and reuse the ot7 collector
created_at: '2026-09-20T19:12:16+00:00'
parents:
- keen-stone-1720
summary: ''
---
## What

G1: run ot8's experiment contract, frozen before any product turn.

- `docs/probes/ot8/README.md` — the contract: the three ot7 baselines with
  their pins, the prompt allocation (one initial prompt plus at most three
  continuations per design), the success and failure bar for G2, G3 and G4,
  what no bar may be passed with, the five-column slot ledger, the commands,
  and the verified Opus access reading.
- `docs/probes/ot8/prompts/` — six frozen prompts and their digest manifest.
  The arm's create prompt is byte-identical to ot7's (and so to ot6's
  receipt). `rebuild.prompt.txt` (G3) and `resolve.prompt.txt` (G4) are the
  two seeded designs' initial prompts; `continue-1..3` are ot8's own.
- `docs/probes/ot8/baselines.json` — the pinned identity of `ot7-heron-c`,
  `ot7-plover-e` and `ot7-robin-c`, read from the operator's projects
  read-only.
- `docs/probes/ot8/retained/g1-window-probe.json` — the `claude-opus-5` access
  and window reading taken at the freeze.
- `docs/probes/ot7/runner/run.py` — generalised, not copied: `--run ot8`
  selects ot8's prompt root, the `ot8-*` project prefix and its two seeded
  designs. Plus `docs/probes/ot7/runner/README.md`, ADR-400.
- `cli/tests/test_ot8_prompts.py` (8) and `cli/tests/test_ot8_runner.py` (22).

## Why

G1 is the top of the short horizon, the critic's named unit, and the gate on
G2–G4: no product turn may be dispatched before the freeze exists.

The critic also asked, before the unit, for a one-line cross-reference in the
ot7 frontier nodes F5/F6/F7 to the G-node that now carries their work. A work
iteration may not edit anything under `.hypergraph/graph/state/`, so this
record **declares those cross-references as State Impacts** instead and the
reconcile pass folds them. That is the same content by the protocol's route.

Two judgement calls worth stating, both reversible and both argued in
`prompts/README.md`:

1. **ot8's continuations are not ot7's.** ot7's three direct the agent to the
   measured fit report alone; this charter directs it to "its measured fit,
   inventory and smoke evidence". The arm's open gap is one the inventory
   names and the fit report does not, so ot7's text could not close it. The
   create prompt stays byte-identical, so the arm comparison stays a
   comparison of one ask; the continuation difference is reported, not hidden.
2. **`resolve.prompt.txt` says a behaviour check is failing**, because G4's
   question *is* which of two things that failure is. It names no part, no
   number and no defect, and it gives "change nothing and state the missing
   control contract" equal standing with a repair — a prompt satisfiable only
   by making the check pass would be this run asking for the cheat its own
   charter forbids.

## Method

1. Read ot7's report, prompts, runner and tests; read the three baselines'
   `script.json` read-only and pinned their four identity fields.
2. Probed `claude-opus-5` for access and window headroom **before** freezing
   anything: allowed, five-hour 10 %, seven-day 16 %, probe answered in 3.7 s.
   A probe carries no project and no tools, so it spends no slot.
3. Wrote the prompts, checked the design-agnostic ones mechanically against
   ot7's forbidden vocabulary (no digit, no design name, no part or defect
   word), and generated the README digest table from the bytes on disk.
4. Generalised the collector rather than forking it: a `run` id in the
   receipt (absent means ot7), a prompt root per run, a `SEEDED` table keyed
   by (run, design), one `attempt_dir()` replacing three duplicated lookups,
   and a pin source per seeded design. `frozen`, `remaining`, `resume`,
   `smoke` and `reclassify` are otherwise unchanged.
5. One behaviour is new for ot8's seeded attempts: the baseline is measured
   **and smoked** before any prompt is sent, with the seed identity held equal
   across both. The measurement gates dispatch, as ot7's did; the smoke never
   does — G3 and G4 exist because these baselines fail it.
6. Tests, then ADR-400, then the doc amendments.

## Result

G1 has its artifacts and its tests. `cli/tests/test_ot8_prompts.py` and
`cli/tests/test_ot8_runner.py` pass (30 tests), and ot7's own 100 tests pass
unchanged against the generalised collector. Both full suites are green at
this revision: `pixi run test-engine` **2196 passed, 53 skipped** (340.2 s)
and `pytest cli/tests` **891 passed, 1 skipped** (577.0 s). No engine
protocol or payload change, so no packaged gate was needed.

No product turn has been dispatched, no ot8 project exists yet, and no ot7
project or receipt was written: the baselines were read read-only.

What the next iteration should know:

- **The freeze is live.** Changing any byte under `docs/probes/ot8/prompts/`
  starts a new attempt, and the digest tests will say so.
- **G3 and G4 need a copy prepared mechanically** before their first prompt:
  `ot8-plover*` from `ot7-plover-e`, `ot8-robin*` from `ot7-robin-c`,
  excluding the source's `evidence/`, `agent.json` and CLI lock, as ot7's
  repair copy was made. The collector refuses a copy whose identity does not
  match `baselines.json`, before any prompt is sent.
- **G4's initial prompt is conditional.** The diagnosis comes first and spends
  no slot; `resolve.prompt.txt` is dispatched only if that diagnosis finds an
  actionable design defect.
- **G3's smoke after the rebuild turn is the no-slot `smoke` subcommand**
  (ADR-392), not a spent continuation; the closing smoke only runs at
  exhaustion.
- No new dependency. `--turns 1` plus `resume` remains the way to spend one
  window at a time.

Dispatch closed: 1 unit — G1's ot8 experiment contract is frozen (contract,
six prompts, baseline pins, slot ledger, collector reuse via `--run ot8`,
30 new tests, ADR-400), with Opus access and window headroom verified first.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot8
- commit: eff15f84d3cffd6ffb94fdb7d2570b5f14f5b516

## State Impact

- target: wise-aspen-8848 — G1's artifacts exist and are test-pinned: docs/probes/ot8/README.md (the three ot7 baselines with their pins, one initial prompt plus at most three continuations per design, the success/failure bar for G2-G4, what no bar may be passed with, the five-column slot ledger of completed/failed/void/interrupted/unreached, the commands, the access reading); docs/probes/ot8/prompts/ with six frozen prompts and a digest manifest (the arm's create prompt byte-identical to ot7's; rebuild.prompt.txt and resolve.prompt.txt as the two seeded designs' initial prompts; continue-1..3 ot8's own, directing the agent to fit, inventory AND smoke evidence); docs/probes/ot8/baselines.json; and docs/probes/ot8/retained/g1-window-probe.json (claude-opus-5 allowed, five-hour 10 percent, seven-day 16 percent, read before the freeze). The ot7 collector is reused rather than copied (ADR-400): run.py --run ot8 selects the ot8 prompt root, the ot8-* project prefix and its two seeded designs, with every slot rule ot7's unchanged and a receipt with no run field still ot7's. cli/tests/test_ot8_prompts.py (8) and cli/tests/test_ot8_runner.py (22) pass; ot7's 100 pass unchanged; test-engine 2196 passed/53 skipped and cli/tests 891 passed/1 skipped. What G1 still needs for its owner tick: the closing report's ot8-vs-ot7 distinction and its every-failed-void-interrupted-unreached table, which is G6's work.
- target: ancient-vine-9908 — the ot8 run has its frozen contract and a dispatch path: ADR-400 reuses the ot7 collector under --run ot8 rather than forking it, so the slot rules ot7's receipts rest on have one home. No product turn has been dispatched and no ot8 project exists yet; the baselines were read read-only.
- target: stormy-aspen-5433 — cross-reference: F5 is exhausted and is NOT to be re-run; the arm's remaining catalog-identity gap is carried by G2 (tender-bay-4302), which designs a fresh arm in a new ot8 project from the byte-identical create prompt and compares against ot7-heron-c.
- target: narrow-dune-9454 — cross-reference: F6 is exhausted and is NOT to be re-run; the balancer's failed holding smoke is carried by G4 (scarlet-hill-8037), which diagnoses it on an independent ot8 copy of ot7-robin-c.
- target: rapid-grove-9687 — cross-reference: F7 is exhausted and is NOT to be re-run; the biped's accepted-artifact smoke is carried by G3 (empty-arrow-8425), which works on an independent ot8 copy of ot7-plover-e.
