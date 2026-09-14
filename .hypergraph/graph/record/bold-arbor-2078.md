---
node_id: 7ccac87e-5000-5cfb-adcd-c54acdceb917
slug: bold-arbor-2078
title: 'D9 final regression assessment: both suites green, the one skip exercised, the persistent dashboard verified at both widths on heron1-final, the ot5 behaviours mapped to tests and retained evidence'
created_at: '2026-09-14T05:14:24+00:00'
parents:
- mild-hill-0753
summary: ''
---
## What

D9's final regression assessment, taken after D7 and D8 closed: `pixi run test-engine` (2114 passed, 53 skipped, exit 0, 268.06 s) and `pixi run python -m pytest cli/tests` (610 passed, 1 skipped, exit 0, 523.25 s) on commit `aa293fc0`; the one CLI skip (the private-address fixture) run again on its own with `CADEX_REVIEW_HOST` set from the service unit and passing; and a fresh visit to the persistent operator dashboard at 1400×900 and at 400×850 under touch emulation, each selecting `heron1-final` by itself, drawing the run's real solids (15 components, 53 620 triangles, `showing: tessellated solids`), with zero horizontal overflow, project polling with no gap over five seconds (5 fetches in 10.5 s, longest gap 2.003 s and 2.002 s), the retained video playing to 0.20 s and downloading with its recorded digest `4f16f9117af6…` (by tap at 400 px), and one finger orbiting the model at 400 px without scrolling the page. Receipts under `docs/probes/ot6/regression/`: `final.json` (6.1 KB), `final_probe.py`, `final-1400.png` (121 747 bytes) and `final-400.png` (51 208 bytes, after the orbit), and the README's final assessment mapping each ot5 behaviour D9 names to the tests that exercise it and to the retained ot6 lifecycle evidence. A new receipt test in `cli/tests/test_review_design.py` pins the receipt's shape, the suite results, the visits and the digest, and holds the named tests to the tree by name. Commit `130abd29`.

## Why

The critic asked for D9 to be finished: run the required engine and CLI suites, verify the persistent dashboard at both widths with `heron1-final` selected, and publish a compact final regression assessment covering the ot5 behaviours, reusing retained lifecycle evidence and not training again. That is this unit. The first D9 pass (`copper-haven-4303`, iteration 16) was taken mid-run on Finch before Robin and Heron existed and said its own final assessment was pending; this record is that assessment. The reconcile the critic named for afterwards is not done here: a work iteration may not reconcile, and the tail is now three records.

## Method

- Ran both suites sequentially in a detached shell with logs, exit codes and timestamps under `~/cadex-projects/ot6-regression-src/` (outside the repo). The new receipt test was set aside while the CLI suite ran so the suite measured the committed tree, then restored; it and the caps parametrisation ran targeted afterwards (109 passed), and the whole design file ran once more (128 passed).
- The private-address fixture, which the full suite skips without `CADEX_REVIEW_HOST`, was run alone with the host read from `systemctl --user cat cadex-operator-review`: 1 passed.
- `final_probe.py` takes the URL from argv (the caller reads it from the unit), reads `/api/project` and `/api/run/heron1-final` for the run list and the retained video's identity, then at each width waits for the page, the loaded model and `showing === 'solids'`, measures overflow and drawn pixels, clears resource timings and counts `/api/project` fetches over 10.5 s, on the phone drags one finger 120×50 px across the viewport and checks yaw and pitch changed at an unchanged distance with `scrollY` unmoved, screenshots the `#model` region quantised to 256 colours, plays the video, downloads it (by tap on the phone) and checks the digest, and records the service's `ActiveState`.
- The receipt's per-file counts are kept for the CLI suite only (the engine breakdown pushed the first attempt to 20 KB, over the 16 KB cap); the pytest log's bare continuation lines are attributed to the preceding file, which the first parser missed (492 of 610).
- The README's final assessment is a table: behaviour → tests (all passed) → retained real evidence (Heron's live-page latency, Robin's failed `robin1` kept as failed, the scratch-copy evaluations, the persistent user unit), with what is not claimed stated.

## Result

- **D9 has its final assessment; its evidence list is complete pending the owner's tick.** Both suites green on the current tree after the redesign, the look change and the three model changes; the one CLI skip exercised separately; the persistent dashboard serving the active project (`ot6-heron`) with the current run (`heron1-final`) selected at both widths, polling, playing, downloading and orbiting by touch.
- **Restart during training** rests on the fixture test and ot5's real Lark restart (ADR-325); ot6 performed no real restart during Finch's, Robin's or Heron's runs and the README says so. Not a gap in the criterion's wording (it asks that the ot5 proof still holds), but named so nobody reads more into it.
- The 400 px frame shows the orbited camera (yaw −0.4, pitch 1.0), not the default; the README says so.
- The CLI count is 610, one above iteration 26's 609, because the untracked probe script joined the caps parametrisation during the run; after this commit the receipt test adds one more.
- Operator service `cadex-operator-review` active throughout, serving `ot6-heron`, fresh-visit default `heron1-final`, unchanged by this unit.
- No product code, protocol or payload change; no build; no packaged gate needed. No new dependency. Suite logs, the probe's stdout and the private-address run's log stay under `~/cadex-projects/ot6-regression-src/`, cited by digest in `final.json`.
- Frontier now: D10, the closing report, is the only open criterion without evidence. The unreconciled tail is three records (`narrow-quill-3259`, `mild-hill-0753`, this one), so the reconcile the charter schedules is due before D10.

Dispatch closed: 1 unit — D9's final regression assessment: engine and CLI suites green, the one skip exercised, the persistent dashboard verified at both widths with heron1-final selected, the ot5 behaviours mapped to tests and retained evidence, receipt test-pinned.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot6
- commit: 130abd291223ae058e0e7761b2e53900265494d2

## State Impact

- target: civic-lily-1239 — D9's final assessment exists (commit 130abd29): engine 2114 passed / 53 skipped and CLI 610 passed / 1 skipped on the current tree after the redesign, look and model changes, the one CLI skip (private-address fixture) run separately with the host set and passing; the persistent dashboard at 1400×900 and 400×850 under touch selects heron1-final by itself, draws the real solids, has zero overflow, polls with a longest gap of 2.0 s, plays and downloads the retained video with its digest, and orbits by one finger without scrolling; docs/probes/ot6/regression/README.md maps every ot5 behaviour the criterion names to passing tests and retained lifecycle evidence, and a receipt test pins final.json and holds those tests to the tree; restart-during-training rests on the fixture test and ot5's real Lark restart, stated as such; evidence list complete pending the owner's tick
- target: round-sun-8398 — D1–D9 each carry evidence pending the owner's tick; D10, the closing report, is the only criterion without evidence; the unreconciled tail is three records and the scheduled reconcile is due before D10
