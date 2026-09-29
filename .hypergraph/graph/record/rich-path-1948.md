---
node_id: 83e016b8-8438-522f-9105-c3e29b9e28a6
slug: rich-path-1948
title: 'ot10: C1 closing run at f2b97e01 — suites and gate green; REPORT claims done for review with A5 unmet at 7 of 18'
created_at: '2026-09-29T05:30:20+00:00'
parents:
- morning-tooth-4242
summary: ''
---
## What
C1 closure for ot10. The report's regressions section now has a closing run at `f2b97e01`. The top verdict states the final count up front. The sheet table links every committed image, and the report claims done for critic review with A5 marked unmet. No box is ticked.

## Why
The critic's message named C1 closure as the next unit, in four steps. Steps 2–4 were done as asked. **Step 1 was not done.** The critic asked me to reconcile and fold morning-tooth-4242 into loyal-fountain-8709. This dispatch forbids the hypergraph-reconcile skill and all state writes in a work iteration, with no exceptions. The fold belongs to the next reconcile pass. That pass should make loyal-fountain-8709's "Still open" line read eighteen counted turns, eleven misses and seven that meet the bar. This record's impact states that count too, so the fold carries it.

## Method
- Ran `pixi run test-engine` and `pixi run python -m pytest cli/tests` at HEAD `f2b97e01`.
- Compared the staged payload `build/engine/cadex-engine-0.0.0-linux-x64` with `src/Mod/cadex/*.py` using cmp: 57 of 57 identical. No engine or package commit has landed since ADR-438 (`2e63b5b6`). The payload was not rebuilt, and the packaged lifecycle gate ran against it.
- Audited REPORT.md against `docs/probes/ot10/`:
  - All 18 counted attempts plus hex3 are in the attempts table. Each counted attempt has a hero, five look views and a `*-score.json`.
  - `refusals.json` covers all 20 transcripts, the two killed turns included.
  - Both W2 runs are listed, and all five W1/W2 rollout images are linked.
  - The sheets of the two later misses (`ot10-biped-2`, `ot10-hexapod-12`) and `ot10-hexapod-12-hero-grid-after.png` were committed but not linked in the renders table. They are now linked.
- Rewrote the verdict's opening. It used to begin "Twelve turns were counted and nine missed" (the chronological start). It now states 18 counted, 11 missed, and 7 of 18 as the highest bar reached, then tells the story in order.
- `test_ot10_report.py` and `test_ot10_contract.py` pass on the edited page, 48 of 48.

## Result
- Engine suite: 2,263 passed, 53 skipped, 0 failed (307 s).
- CLI suite: 1,075 passed, 1 skipped, 0 failed (736 s).
- Packaged lifecycle gate: 23 passed, 0 skipped.
- The skip causes are unchanged: JAX/MJX offboard (47), no Blender runtime (5), a packaged-gate-only test (1), and a private review host (1).
- REPORT.md has its closing C1 section and claims done for review with A5 **not met**: 7 of 18 counted turns meet the bar and 11 miss. W1 and W2 have evidence (`w2-2` walked = true). No owner box is ticked. Hexapod-13 holds as counted.
- **Owed to the next reconcile:** fold morning-tooth-4242 and this node. loyal-fountain-8709 should read 18 counted, 11 misses, 7 meeting the bar. The tail is now two nodes.
- **Not verified:** `hypergraph check` must be passed `--config .hypergraph/config.yml` (see REPORT §C1).

Dispatch closed: 1 unit — C1 closing run green at f2b97e01 (engine 2263/53s, CLI 1075/1s, gate 23), REPORT audited and claims done with A5 unmet at 7 of 18; reconcile deferred to its own pass.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot10
- commit: 595f49ffd3b4aff18fc84c516720283e3f0709c7

## State Impact

- target: loyal-fountain-8709 — A5 still not met by its letter: eighteen counted turns, eleven misses, seven that meet the bar (7 of 18 is the highest bar reached); the loop does not accept it, only the owner can
- target: southern-prairie-3683 — ot10 REPORT.md closing C1 run at f2b97e01: engine 2,263 passed/53 skipped, CLI 1,075 passed/1 skipped, packaged gate 23/23 against a payload identical to source; the report lists every probe, render and training run and claims done for critic review with A5 unmet and no box ticked
