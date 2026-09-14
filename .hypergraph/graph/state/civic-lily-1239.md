---
node_id: 0aa1d364-4c43-5079-b21f-0c7dda4871cc
slug: civic-lily-1239
title: D9. Everything ot5 proved still holds
created_at: '2026-09-13T21:25:10+00:00'
parents:
- round-sun-8398
summary: ''
---
Status: working

## Current

**D9 has its final regression assessment, taken after D7 and D8 closed; its evidence list is complete pending the owner's tick** (commit `130abd29`). Its final assessment is committed and test-pinned and only the owner's checkbox is outstanding — `working` on the same reading D1–D8 carry [rec: bold-arbor-2078] [rec: frosty-path-5235].

On commit `aa293fc0`, after the redesign, the look change and the three model changes: `pixi run test-engine` 2,114 passed / 53 skipped (268 s) and `pixi run python -m pytest cli/tests` 610 passed / 1 skipped (523 s), run sequentially with logs, exit codes and timestamps kept outside the repo; the one CLI skip, the private-address fixture, run again on its own with `CADEX_REVIEW_HOST` read from the service unit and passing. A fresh visit to the persistent operator dashboard serving the active project `ot6-heron` at 1400×900 and at 400×850 under touch emulation selected `heron1-final` by itself, drew the run's real solids (15 components, 53,620 triangles, `showing: tessellated solids`), had zero horizontal overflow, polled `/api/project` with no gap over five seconds (longest gap 2.003 s), played the retained video to 0.20 s and downloaded it with its recorded digest `4f16f9117af6…` (by tap at 400 px), and orbited the model by one finger at 400 px without scrolling the page. Receipts under `docs/probes/ot6/regression/`: `final.json` (6.1 KB, CLI per-file counts only — the engine breakdown pushed the first attempt over the 16 KB cap), `final_probe.py`, `final-1400.png`, `final-400.png` (taken after the orbit, so it shows the orbited camera, not the default). The README's final assessment is a table mapping every ot5 behaviour the criterion names to the tests that exercise it (all passed) and to retained ot6 lifecycle evidence: Heron's live-page latency, Robin's failed `robin1` kept as failed, the scratch-copy evaluations, the persistent user unit. A receipt test in `cli/tests/test_review_design.py` pins the receipt's shape, the suite results, the visits and the digest, and holds the named tests to the tree by name [rec: bold-arbor-2078].

**Restart during training** rests on the fixture test and ot5's real Lark restart (ADR-325); ot6 performed no real restart during Finch's, Robin's or Heron's runs and the README says so. Not a gap in the criterion's wording (it asks that the ot5 proof still holds), but named so nobody reads more into it [rec: bold-arbor-2078].

The first pass (`copper-haven-4303`, taken mid-run on Finch before Robin and Heron existed: engine 2,114 / 53, CLI 560 / 1, the Finch final page at both widths with digest-matched downloads) said its own final assessment was pending and is superseded by the assessment above; its receipts `README.md` and `verification.json` remain beside it [rec: copper-haven-4303].

**The owner ticked D9 on 2026-09-14 with the evidence unchanged; it holds as worded** [rec: nimble-wing-3050].

Charter criterion: **D9. Everything ot5 proved still holds.** The review server and record suites, live polling within five seconds, playback and download, restart during training, copy isolation, failed-run states and headless operation all pass after the redesign, the look change and the model changes. Evidence: the CLI suite green, the engine suite green, and the operator URL serving the active project with the current run selected. Declared target `gap-d9-everything-ot5-proved-still`; the human owns the checkbox edit [rec: brisk-ledge-9638].

## Negative knowledge

- [scope: D9 regression verification | confidence: high | evidence: copper-haven-4303, bold-arbor-2078] Skips are not exercised coverage. The private-address fixture skips in the full suite without `CADEX_REVIEW_HOST`; the first pass covered it with an independent browser probe, the final pass ran the fixture alone with the host set. Lifecycle fixtures are not new GPU training; the final assessment reuses retained lifecycle evidence and did not train again.

## Provenance

- brisk-ledge-9638 — the ot6 directive (ADR-328) declared this criterion as gap `gap-d9-everything-ot5-proved-still`
- copper-haven-4303 — the first pass, mid-run on Finch: full engine and CLI suites green, live Finch playback and digest-matched downloads at both widths; final assessment then pending
- bold-arbor-2078 — the final assessment after D7 and D8: both suites green on the current tree, the one skip exercised, the persistent dashboard verified at both widths with heron1-final selected, the ot5 behaviours mapped to tests and retained evidence, receipt test-pinned
- frosty-path-5235 — the closing report: D9 evidenced pending the owner's tick; restart during real training rests on the fixture test and ot5's Lark restart, and the report says so
- nimble-wing-3050 — the owner ticked D9 on 2026-09-14; evidence unchanged
