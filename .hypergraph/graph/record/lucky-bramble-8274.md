---
node_id: e2719a0a-59de-5d21-b38f-e2e3ff4f1ffd
slug: lucky-bramble-8274
title: Assemble the fresh biped's D9 lifecycle report and assess D11 against the charter
created_at: '2026-09-12T22:43:05+00:00'
parents:
- fair-crow-5108
summary: ''
artifacts:
- docs/probes/reed-lifecycle/report.json
- docs/probes/reed-lifecycle/report.py
---
## What

Wrote the fresh biped's D9 lifecycle report: `docs/probes/reed-lifecycle/report.py` assembles, from the real Reed project's own records and the committed common-seed evaluation rows, the accepted identity, twelve run identities with the model view the dashboard serves for each (rollout view or training snapshot, meshes retained/missing), the four-design comparison on seeds 0–9, the D1–D8 evidence index (documents, probe files, tests, ADRs, record nodes) and the persistent-URL operator check it was generated beside; `report.json` is that output on 2026-09-12, and `README.md` is the user-facing report: the lifecycle in order with links into `docs/HEADLESS-BIPED-REVIEW.md`, the evidence index with each criterion's remaining limit, the identity table, an explicit section on why training snapshots are not rollout views and which are incomplete (`probe3` 4 of 8, `shin55` 5 of 8, `probe2` unposed, `probe1` none), the comparison table, the revisit check, a D11 assessment item by item against the charter's evidence list, and the report's limits. `cli/tests/test_lifecycle_report.py` (6 tests) holds the committed report to itself and to the repository: video policy/revision/seed agree with their run, the operator check agrees with the run it selected, the comparison recomputes from the committed rows, every linked path/ADR/record exists, and the README names every incomplete or absent view with the report's counts. Linked from `docs/HEADLESS-BIPED-REVIEW.md`, `docs/CLI.md` and `docs/ROADMAP.md`; `docs/probes/review-style/README.md` no longer says the owner retains visual acceptance; `docs/probes/operator-review/README.md` records the iteration-43 revisit.

## Why

The critic's message after fair-crow-5108 asked for exactly this: complete D9's lifecycle report linking D1–D8 evidence, retained artifact identities and the common-seed comparison, disclose incomplete historical meshes, distinguish training snapshots from final rollout views, verify the persistent dashboard still defaults to shin55-final with historical playback, assess D11 against the charter's evidence requirements, and correct fair-wolf-4645's unsupported claim that the charter reserves visual acceptance for the owner. All of it was done as asked; no training was launched, because none was needed. The correction is declared as this record's impact on fair-wolf-4645: the charter's D11 text lists evidence, and the only owner-reserved act is the checkbox edit common to every criterion.

## Method

Read the charter, the last three records, the D1–D8/D10/D11 state nodes and their provenance, `review_server.py`'s routes and `run_model`'s view sources. Queried the persistent server's `api/model/accepted` and `api/model/run/<name>` for all twelve runs, and read every `run.json` through `read_run_record`, to establish view kind and mesh counts from the served data rather than from memory; verified that each playback's parameter values equal its training record's apart from `policy_on`, and that copy100/probe3/shin55 training-view directories hold 4/4/5 STL files. Ran `docs/probes/operator-review/verify.py "http://$(tailscale ip -4):8765/" "$COPY" shin55-final` (exit 0) and passed its output to `report.py`. Recomputed the comparison from `reed-baseline/results.json`, `reed-foot90/results.json` and `reed-agentrev/evidence.json`; every figure matched the narrative doc (probe3-checkpoint20 0 falls / 39.352 mm, probe3-final 10 / 200.854, foot90 9 / 160.842, shin55-final 4 / 79.128). Assessed D11 by mapping each clause of the charter's evidence list to an existing artifact and naming its limit. Verification: focused test 6 passed; full CLI suite with `--basetemp` outside the checkout — see Result; `git diff --check` clean. No engine, protocol, payload, shell or trainer change, so no engine suite, packaged gate or build.

## Result

D9's lifecycle report exists and is test-guarded; the persistent URL, opened fresh, selects `shin55-final` by default at accepted revision `67b5000f3de1…`, plays and downloads video `c23508ad3e92…`, keeps playback across a poll, shows `probe3-final` HISTORICAL and returns to current. The report discloses that the page serves training snapshots for `probe3` (4 of 8 meshes), `shin55` (5 of 8) and `probe2` (parts at identity), none for `probe1`, and complete rollout views for every playback and walk run; `copy100`'s frozen snapshot is also 4 of 8 but its rollout view takes precedence. D11 assessment: every evidence item the charter lists has an artifact behind it; the honest remaining limits are that the same-pose viewport/video parity and the side-by-side were made on `copy100` and not repeated on `shin55-final`, the light reference is the unmodified reference renderer on Reed's geometry because the checkout ships no light clip, shadow frustum/bias differ deliberately, and every observation is same-machine. The state node's sentence "the charter reserves visual acceptance for the owner" is unsupported by the charter text and is corrected through this record's impact; whether that evidence set is sufficient to tick D11 is the checkbox edit the human owns for every criterion, not a charter clause. Whole-goal completion is not claimed. No second-device visit; no training active; the service was not restarted. No new dependency. The unreconciled tail is now one record (this one) on top of the fair-crow-5108 reconcile.

Verification: `pixi run python -m pytest cli/tests -q --basetemp=/tmp/it43/pytest` — 380 passed, 1 skipped in 371.44 s (374 before this unit plus the 6 new); `git diff --check` clean.

Dispatch closed: 1 unit — D9 lifecycle report with D1–D8 evidence index, retained identities, snapshot/rollout disclosure, common-seed comparison, persistent-URL revisit and D11 assessment

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot5
- commit: 51610bd62bd8ff699d6af09abb8566369b442b21

## State Impact

- target: silent-river-6649 — The D9 lifecycle report exists (docs/probes/reed-lifecycle): D1–D8 evidence index, twelve retained run identities with served view kind and mesh counts, snapshot-vs-rollout disclosure (probe3 4/8, shin55 5/8, probe2 unposed, probe1 none), four-design common-seed comparison recomputed from committed rows, persistent-URL revisit; test-guarded. Both designs have playable videos and common-seed measurements; no design walks; checkbox edit remains the owner's
- target: fair-wolf-4645 — Correction: the charter's D11 text lists evidence and reserves nothing to the owner beyond the checkbox edit common to every criterion; the earlier 'charter reserves visual acceptance for the owner' sentence was unsupported. Item-by-item assessment finds an artifact behind every listed evidence clause; actual limits are that same-pose parity and the side-by-side were made on copy100 rather than repeated on shin55-final, the light reference is the reference renderer on Reed geometry (no light clip ships), shadow frustum/bias differ deliberately, and all observations are same-machine
- target: deep-clover-6012 — Persistent port 8765 reverified fresh on 2026-09-12 with no restart: shin55-final selected by default at the accepted revision, playback/download digest match, poll preservation, historical probe3-final and return to current; published status unchanged
