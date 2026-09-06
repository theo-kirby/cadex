---
node_id: c1e64944-a027-59bb-80ed-a530f6fc6dad
slug: young-crane-9546
title: short
created_at: '2026-09-06T19:21:31+00:00'
parents:
- fond-ember-4937
summary: ''
---
Status: open

## Current

1. **L2 boards family over `CadexCatalog` (mission 4; ready-falcon-6286, brave-stone-9609).** Next dispatch: the GUI documentation and its correction have landed. Follow L0/L1's shape exactly (ADR-181): sourced catalog rows for ESP32 DevKit, Pi Zero 2 W and PCA9685 with mounting-hole interfaces and terminal pinout rows, approximate dimensions labelled in `spec["approximate"]`, generators composed as lib values with simple cosmetics, the library tests extended with a real-kernel build of the new generators, `docs/PROVENANCE.md`-style source lines, a ROADMAP tick and an ADR. Use at most one full build, stage the resulting engine payload, and run the packaged lifecycle gate; if it cannot finish inside the iteration, land the family with the source-tree evidence and record the gate as the remaining leg. Engine zone: `pixi run test-engine` minimum. [rec: golden-mist-0498] [rec: twilight-lake-8164] [rec: lone-wood-3732] [rec: humble-bell-9017]
2. **The same `cadex walk` on a second repo-owned mechanism (mission 2; swift-dusk-2951); the GUI documentation prerequisite has landed.** Add one distinct xscript fixture — a mechanism the toy is not, built from what the repo already has (the L1 servos are candidates) — and take it through the unchanged entry point with the same entry-point options and the toy's training caps (venv, CPU, at most 15 minutes and 3 GB). Both projects' `PROGRESS.md` carry the same metric definitions (`total_reward` over the verified rollout, reward per step, iterations and envs) and the record says what is comparable; a changed reward weight is not an improvement. Commit source, docs and numbers; never policies, checkpoints or traces. A change the walk needs for the new mechanism is a generality defect recorded on `swift-dusk-2951`, and if it touches the walk it carries the doc and scaffold edit in the same commit. [rec: golden-mist-0498] [rec: shy-cabin-0798] [rec: fond-mesa-1562] [rec: humble-bell-9017]

## Negative knowledge

- [scope: GUI-attached walk and foreign revisions | confidence: high | evidence: grand-fjord-0624] Documentation landed with sequential ownership only. The shell takes no CLI lock and retries original mutation arguments on a stale revision, which can overwrite CLI work. Rebuild Model or reopen before GUI editing resumes; the re-accept box is not the ordinary refresh path. Runtime safety remains separate medium work.

- [scope: any unit that changes the lifecycle walk | confidence: high | evidence: wild-marsh-9611] The critic rejected iteration 3 because `cli/cadex_cli/project_docs.py` did not change with the walk; the fix-forward pinned the scaffold's Training section to `docs/CLI.md` by a test. A walk change carries the doc and the scaffold in one commit, and a documentation unit names the scaffold sentence it relies on.
- [scope: a warm start under `--remote` | confidence: high | evidence: green-delta-7130] Refused before any leg; the dispatcher copies two files out and the `--init-from` policy is not one of them. The second-mechanism unit does not use `--remote`.

## Provenance

- lone-wood-3732 — qualify current implementation and sequence lifecycle legs
- empty-wolf-3962 — fold pending short seed under charter constraints
- golden-mist-0498 — two units landed; GUI doc first, L2 boards and the second mechanism promoted from medium
- humble-bell-9017 — GUI documentation dispatch landed; retain L2 and second mechanism with corrected runtime limits
