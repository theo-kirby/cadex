---
node_id: 1d7dc6fa-cdcc-542d-a943-dabb96f6d15f
slug: easy-grove-4224
title: Never-reloaded page adds the final-policy stop when the walk lands its rollout (ADR-554); REPORT count fixed
created_at: '2026-10-05T16:18:20+00:00'
parents:
- damp-wave-8696
summary: ''
---
## What

Fixed orun3 remaining defect 1: a dashboard left open through a walk now adds the
`final policy` stop to the checkpoint scrubber when the walk lands its own rollout (ADR-554),
and corrected `docs/probes/orun3/REPORT.md:18` from "seven" to "ten" `w1-*.png`.

## Why

The critic's message asked two things in order: correct the REPORT.md screenshot count, then
take the next rung, the never-reloaded scrubber missing its `final policy` stop (REPORT §5
defect 1, seen in `soft-comet-8840`), with a browser test and an ADR. Both done here. The
done claim made in `damp-wave-8696` stands, with the count corrected; this record re-claims it.

## Method

- Cause, read from `review.js`: the poll keyed a run source's model on its name alone ("a
  run's model is fixed"), so `/api/model/run/<run>` was fetched once. During training that
  manifest is the frozen training view with no `playback`; ADR-545's `final policy` stop is
  built from the manifest's `playback`, which only exists after the rollout leg. Nothing
  re-read it.
- Fix: `runModelKey(review, name)` keys the run model on the run's `status` and its resolved
  `trace` and `model_xml` artifacts, all already in `/api/project`'s `runs`. They do not move
  while training, so no extra fetches per poll; no route, hook, poll loop or write.
- Test: `test_a_never_reloaded_page_adds_the_final_policy_stop_when_the_walk_lands_its_rollout`
  in `cli/tests/test_review_checkpoints.py` (Chromium via `browser.py`, no engine needed):
  a checkpoint loops `iteration 20 · reward 0.5 · 1/1 · newest` across settled polls; the
  walk then writes its rollout trace, parts and an `ok` record; one poll later, no reload,
  the label is `final policy · 2/2 · newest`, the final rollout loops, and the older
  checkpoint is still pickable. With `review.js` reverted, the test times out on the
  `final policy` label (checked); with the fix it passes.
- Docs: ADR-554 in `docs/DECISIONS.md`; `docs/DASHBOARD.md` §2 3D-viewport row; REPORT §4
  ADR table gains ADR-554 and §5 defect 1 says fixed, not yet re-walked.

## Result

True now: a page that watched a run's checkpoints adds the run's own rollout as the newest
`final policy` stop on the poll after the walk lands it. REPORT.md says ten screenshots.
Suites: `pixi run python -m pytest cli/tests` with the GPU hidden: 1173 passed, 1 skipped; `pixi run test-engine`: 2585 passed, 58 skipped. No protocol or payload change, so no packaged gate.

Concern: the fix is proved on a fixture, not re-walked on `orun3-biped` with the 5090; REPORT
§5 says so. Defects 2 (evaluating line names the evaluation directory) and 3 (37–39 s
progress stalls before checkpoints) remain open. No new dependency. Done is re-claimed for
critic review; no owner box ticked.

Dispatch closed: 1 unit — never-reloaded page adds the final-policy stop (ADR-554), REPORT count fixed

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/orun3
- commit: 6bb7ea7fa7f93b29a64edca201a430dadaf06431

## State Impact

- target: candid-harvest-2614 — a page left open through a walk now adds the run's own rollout as the final-policy checkpoint stop on the next poll (ADR-554, commit 6bb7ea7f); orun3 REPORT defect 1 fixed on a fixture, not yet re-walked on orun3-biped
