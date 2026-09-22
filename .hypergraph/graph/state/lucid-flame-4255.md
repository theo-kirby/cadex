---
node_id: aacdfba9-1707-5976-bcc6-6988a436f942
slug: lucid-flame-4255
title: G5. The regression floor still holds
created_at: '2026-09-20T18:48:22+00:00'
parents:
- ancient-vine-9908
summary: ''
---
Status: working

## Current

**Met in its evidence at the final code revision, pending the owner's tick [rec: hidden-delta-8675].** Measured against a freshly built and staged payload (`cadex-engine-0.0.0-linux-x64`, manifest `c6687a97…`, source comparison `match` over 57 files) at `39e02390` [rec: hidden-delta-8675]:

- engine suite **2196 passed, 53 skipped**; CLI suite **903 passed, 1 skipped** [rec: hidden-delta-8675];
- packaged lifecycle gate **23 passed, 0 skipped**; packaged licensing audit **11 passed** — run because one of its tests skips without a payload [rec: hidden-delta-8675];
- the ADR-398 repeated-restore retention regressions (`test_an_offset_project_reopens_although_its_bytes_never_repeat`, `test_a_changed_script_is_still_refused_at_the_restore_pass`) **PASSED** inside the gate, with `test_geometry_digest.py` 20 passed beside them [rec: hidden-delta-8675].

Retention probe over the five designs this run used — `ot7-heron-c`, `ot7-plover-e`, `ot7-robin-c`, `ot8-heron-b`, `ot8-plover` — each copied (script, params and accepted attempt only) into a fresh `ot8-open-*` project, restored, then reopened in a second process: **ten phases, all ok**. Accepted revision, digest and script hash equal the published pins; the accepted `result.json` is byte-identical after both opens; every clearance pair is equal restore-to-reopen and `clear`. The only measured differences are `latest_candidate` and `updated_at` — the attempt each open records and its clock. Sources were hashed before and after; none moved [rec: hidden-delta-8675]. Receipt `docs/probes/ot8/retained/g5-retention.json`, commit `001981c8`; the probe itself stays project-local, following ot7's precedent [rec: hidden-delta-8675].

Later commits (G6) added only docs, one test and a record; G6 re-ran both suites green (engine 2196/53, CLI 914/1) and no engine, CLI or shell source changed, so the gate result still stands at HEAD [rec: rough-ridge-4729].

The `ot8-open-*` projects are probe working copies, not designs; nothing should dispatch into one [rec: hidden-delta-8675].

## Negative knowledge

None.

## Provenance

- keen-stone-1720 — the criterion as the ot8 charter declares it
- fierce-bloom-1076 — ADR-398's repeated-restore retention regressions, named by the criterion
- hidden-delta-8675 — G5 measured green at the final revision: suites, packaged gate and licensing audit, ten clean restore/reopen phases
- rough-ridge-4729 — suites re-run green after the docs-and-test-only G6 commit
