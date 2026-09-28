---
node_id: a635cbce-321d-5d96-b85c-78f4c8b05746
slug: mellow-light-0451
title: 'ot10: CPU-limit refusals — diagnosed on hexapod-10, common skipped for pairs apart, refusal names the costly stages (ADR-436)'
created_at: '2026-09-28T23:53:17+00:00'
parents:
- old-cabin-6515
summary: ''
---
## What

ot10: the CPU-limit refusal class, diagnosed from `ot10-hexapod-10`'s receipts and prevented at the source (ADR-436, commit `5419d59e`, `cadex_tests/test_cpu_ledger.py`).
- The static fit and the sweep no longer run the boolean `common` on a pair whose distance is above 0.001 mm; the volume is 0.0, proved by the distance.
- The static fit measures distance between the boundary shells, as the sweep has since ADR-425.
- The sandboxed worker keeps a CPU ledger in its staging directory (`progress.json`). On SIGXCPU the refusal names the running stage and the costliest finished stages (`output NAME`, `static fit A / B`, `assembly solve`, …), says what each kind of stage is, and carries the ledger as `observed.cpu_ledger`.

## Why

The critic named this unit: long-term rung 2, through the largest refusal class still measured. That is CPU-limit refusals, 44 of 213 across ot10, 6 of them in hexapod-10. The critic asked to diagnose which ops hit the limit from the hexapod-10 receipts, then prevent it at the source, with a regression that fails before the fix and an ADR. I did that. Where I went beyond the critic's two options (a reference line, or an error naming the cheaper path): I did both an engine fix (the needless `common`) and the naming error. I added no overlay or reference line. The error names the part, and the fix needs no agent action.

## Method

1. **Receipts.** Found the product transcript by its `refusals.json` sha256. All six refusals ended with SIGXCPU 90–101 s in, the native solver's `MbD` lines already in stdout, and no stage named. Across all seven ot10 transcripts with CPU refusals, 27 of 45 matching results died after the solve and 18 before it.
2. **Reproduction.** Replayed the first refused `write_script` source (the agent's 12:40 call) with `cadex script --set` on `/tmp/ot10-cpu-diag`, a copy of the project (earlier projects stay read-only). `/proc` polling showed one worker spending 299 CPU-s in 98 s.
3. **Instrumentation.** Built the ledger. With a temporary per-pair timer (removed before committing), the measured split was:
   - geometry: 119 CPU-s (`output tub` 75.7, `output dome` 20.7, `output visor` 13.4);
   - static fit: `c_tub`/`c_deck` 24 CPU-s (16 of them in `common`);
   - `c_tub`/`c_dome`: 2.4 mm apart, 20 CPU-s for the distance, then over 137 CPU-s in `common` without finishing.
4. **Fixes, measured.** After the `common` fix and the shell distance, the same script is still refused: the static fit measures the tub exactly against every housed part, because the tub's box encloses them. The refusal now names `'output tub' 75.01, 'static fit c_tub / c_visor' 52.85, 'static fit c_tub / c_deck' 24.27, 'static fit c_tub / c_pca9685' 23.68`.
5. **Equivalence.** Rebuilt the accepted hexapod-10 script on another `/tmp` copy (83 s). Its 1,326 static clearance rows are identical to the old engine's, verdicts included.
6. **Regression.** Eight tests in `test_cpu_ledger.py`. Against the old assembly worker, `test_a_pair_measured_apart_is_not_intersected` fails with `assert 5.0 == 0.0`, and the per-pair ledger test fails too. The ledger and refusal tests error on the old source (no `PROGRESS_ENV`). One test is a real SIGXCPU kill.

## Result

What is true now:
- A CPU refusal names the stage it died in and where the budget went.
- Fit no longer spends CPU proving zero volumes the distance already proved.
- `docs/XSCRIPT.md` (fit section and resource limits), ADR-436, and remaining defect 1 in `docs/probes/ot10/REPORT.md` say so.

Suites at this revision: `pixi run test-engine` 2255 passed, 53 skipped. `pytest cli/tests` 1068 passed, 1 skipped. The engine was rebuilt and staged, and the packaged lifecycle gate (`CADEX_ENGINE_ROOT=<payload> test_cadexd_lifecycle.py`) passed 23/23 against a payload that carries the new worker.

Concerns for the next iteration:
- **This does not make hexapod-10's refused build fit the budget.** A hollow shell whose box encloses what it houses is still measured against each part. The next candidate unit is cheaper static-fit distances for such pairs, for example sub-shape culling. It must be measured the same way, and must not change the 10 mm cull or any verdict.
- The 18 refusals that died before the solve (geometry) were not re-run. The ledger will name their stages on the next probe.
- No probe has run since, so the class is not yet shown smaller in a transcript.
- No new dependency. No rubric, bar, judge or prompt changed, and no probe is re-scored.
- The tail now holds one unreconciled record.

Dispatch closed: 1 unit — CPU-limit refusals diagnosed on ot10-hexapod-10 (static fit: `common` on shells 2.4 mm apart), `common` skipped for pairs measured apart, and the refusal now names the costly stages (ADR-436).

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot10
- commit: 5419d59efe689f50fbcecbed7e8970669c01252a

## State Impact

- target: forest-wind-0342 — A CPU-limit refusal now names the stage it died in and the costliest finished stages, from a worker ledger (progress.json; observed.cpu_ledger). The static fit and the sweep skip the boolean common on any pair measured more than 0.001 mm apart, and the static fit uses the shell distance (ADR-436). The accepted ot10-hexapod-10 rebuild reproduces all 1,326 static rows exactly. hexapod-10's refused build is still over 300 CPU-s, because its tub's box encloses every housed part.
- target: loyal-fountain-8709 — The largest refusal class still measured (CPU limit, 44 of 213) was diagnosed on hexapod-10: geometry took 119 CPU-s, and the static fit spent the rest. The engine now removes a needless common and names the costly stages in the refusal. No A5 probe has run since, so the class is not yet shown smaller in a transcript.
