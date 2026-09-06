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

1. **Prevent foreign-revision overwrite (missions 1 and 2; witty-spark-2613, simple-willow-8989).** Next dispatch: one owned-shell fix that pins stale script and parameter mutation replay with regression evidence, then removes blind replay or refuses stale mutation while preserving foreign accepted work. Cover ordinary same-revision success and the explicit refresh/retry recovery path. Prefer refusal over introducing session-wide locking. Keep docs/CLI.md, MUJOCO guidance and the project-doc scaffold true to the actual result; record the removal/direction ADR and ROADMAP change where applicable. Run `pixi run gate` headlessly and the CLI suite if its scaffold changes; at most one full build. Sequential-use documentation alone does not prove runtime safety. [rec: grand-fjord-0624] [rec: nimble-glade-6200]
2. **L3 first family: sourced N20 gearmotor (mission 4; rising-banner-4325, brave-stone-9609).** After unit 1 lands or is evidenced blocked, add one manufacturer-specific N20 family over CadexCatalog using L0–L2's lib-value shape. Source dimensions, shaft/mounting interfaces and electrical/mechanical ratings with their operating conditions; label approximations and do not invent missing torque data. Include provenance, a real-kernel generator test, ADR and a narrowly worded ROADMAP subitem; the whole L3 checkbox stays open. Run the engine suite, at most one full build, stage the payload, then run packaged lifecycle/library tests. Staging must finish before suites inspect the payload. If verification cannot finish, record the exact outstanding gate as a remaining leg. BLDC, linear actuator, solenoid, joints and compound gearing remain separate units. [rec: stormy-quill-5350] [rec: nimble-glade-6200]

## Negative knowledge

- [scope: GUI-attached walk and foreign revisions | confidence: high | evidence: grand-fjord-0624] Documentation landed with sequential ownership only. The shell takes no CLI lock and retries original mutation arguments on a stale revision, which can overwrite CLI work. Rebuild Model or reopen before GUI editing resumes; the re-accept box is not the ordinary refresh path. Runtime safety is now the first short dispatch.

- [scope: any unit that changes the lifecycle walk | confidence: high | evidence: wild-marsh-9611] The critic rejected iteration 3 because `cli/cadex_cli/project_docs.py` did not change with the walk; the fix-forward pinned the scaffold's Training section to `docs/CLI.md` by a test. A walk change carries the doc and the scaffold in one commit, and a documentation unit names the scaffold sentence it relies on.
- [scope: a warm start under `--remote` | confidence: high | evidence: green-delta-7130] Refused before any leg; the dispatcher copies two files out and the `--init-from` policy is not one of them. Local second-mechanism qualification did not exercise this remote restriction.

- [scope: L2 and second-mechanism qualification | confidence: high | evidence: sage-peak-2689] Both former short dispatches landed. Slider training verified the pipeline, not height holding; do not treat unlike effort units as a design ranking.

- [scope: payload verification sequencing | confidence: high | evidence: stormy-quill-5350] Finish stage-engine before suites inspect the payload; concurrent staging exposed ccx before its normal prune and produced a transient failure.

## Provenance

- lone-wood-3732 — qualify current implementation and sequence lifecycle legs
- empty-wolf-3962 — fold pending short seed under charter constraints
- golden-mist-0498 — two units landed; GUI doc first, L2 boards and the second mechanism promoted from medium
- humble-bell-9017 — GUI documentation dispatch landed; retain L2 and second mechanism with corrected runtime limits

- nimble-glade-6200 — promote safety and one L3 family after verified L2 and second-mechanism work
