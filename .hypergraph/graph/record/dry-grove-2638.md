---
node_id: 1b9fdeca-ea6e-51c4-9d31-cc410f2d7625
slug: dry-grove-2638
title: 'Bet: make toy CPU lifecycle verification explicit and shared'
created_at: '2026-09-08T16:06:49+00:00'
parents:
- placid-ember-6741
summary: ''
---
## What

Close the two spent recovery dispatches and select one finite direction: make the documented toy CPU lifecycle and its CLI regressions independent of a CUDA-capable trainer environment (missions 1/2/6). Short has two units: one public CPU walk with a concise correction to the CPU instructions, then consolidation of CPU selection in the existing real-training tests.

## Why

Recovery is measured and permanently covered: 46 preserved artifacts in the rehearsal, honest last-success comparison references, and 223 CLI tests with no skips in the final CPU gate [rec: dusty-vale-2809] [rec: placid-ember-6741]. Neither recovery unit remains dispatchable. The latter record supplies fresh evidence: an unpinned focused run selected CUDA and failed in cuSolver before recovery, then passed with CPU explicitly selected [rec: placid-ember-6741]. This is an environment-dependent toy verification boundary, not a diagnosis of CUDA or a production device-selection defect.

Read-only inspection confirms a bounded remaining inconsistency: training/SETUP.md section (b) calls the pinned installation CPU-only and shows invocations without JAX_PLATFORMS, while also allowing discovery of the shared trainer venv. test_walk.py pins CPU independently in two tests; test_train.py's real train and iterate tests do not, and the receipt assertion accepts any nonempty device. The existing recovery and carriage guide commands already select CPU. The useful frontier is exhausted although standing state nodes remain open. Three candidates: (1) select this CPU contract consolidation because the new failure directly motivates it and duplicated setup/prose can be removed; (2) decline another recovery/failure matrix because successful continuation is now covered; (3) decline wider catalog or fleet work because Later remains human-promoted. Empty bookkeeping dispatch already failed [rec: careful-union-7585]. Only candidate 1 opens.

Signals are 13 iterations, 4.5h elapsed and 43.5h remaining; seven iterations without frontier movement, Claude five_hour 100%, Codex seven_day 71%. Two small model-free units fit; remaining budget is not authority for another campaign. This is maintenance of the headless-walk criterion and its CPU evidence, not retirement of a charter gap or promotion of a parked rung. The empty-short rehearsal happens first, once, at this newly observed environment boundary.

## Method

Fold this bet into all three plan horizons, retaining historical negative knowledge and provenance and explicitly overriding spent recovery dispatches. Unit 1 runs the public walk with JAX_PLATFORMS=cpu through the existing trainer venv in an isolated existing-script toy project, verifies the reported backend and full review, then replaces misleading CPU-only setup prose with the measured invocation and aligns the CLI guide/scaffold concisely. Unit 2 uses a narrowly requested shared CPU fixture for real local train/walk tests, replacing duplicated per-test selection and strengthening existing device assertions; fake remote refusal tests retain their contracts. No global production override, CUDA investigation, new device flag, dependency change or GPU training. Keep each training run below 15 minutes and 3 GB; no GUI or remote dispatch. Each unit must change a test or document outside bookkeeping, remove more than it adds across the finite direction, run the applicable zone gates, and record ADR removals and ROADMAP evidence.

## Result

One new direction selected with two bounded units; completed recovery is evidence rather than future work. No state nodes, charter checkboxes or code changed in this planning pass. Plan export/check and sync are required before committing the fold; no further direction follows automatically after these two units.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot4
- commit: 49b763e49965cebe1570b710078ee6c807aa99b2

## State Impact

- target: plan/young-crane-9546 — replace completed recovery with two bounded CPU-contract units
- target: plan/strong-birch-7412 — select CPU environment consistency from the observed cuSolver failure
- target: plan/late-valley-7350 — preserve recovery evidence and constrain CPU maintenance
