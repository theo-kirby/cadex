# D9 regression verification

Verified against source: 2026-09-14. [Cadex-new]

D9 asks that everything ot5 proved still holds after the redesign (D1, D2),
the look change (D3, D4) and the model changes (D5–D8). This directory holds
two passes. The **final assessment** below was taken after D7 and D8 closed,
on the tree at the commit `final.json` names, with the persistent operator
dashboard serving Heron and `heron1-final` selected. The **first pass**
further down was taken mid-run, when Robin's product agent was unavailable,
and is kept as history.

## Final assessment

[final.json](final.json) is the receipt; [final_probe.py](final_probe.py)
produced it and the two frames, and is pinned by
`test_final_regression_receipt_shows_everything_ot5_proved_still_holds` in
`cli/tests/test_review_design.py`, which also holds every ot5 behaviour below
to tests that still exist in the tree.

```
pixi run test-engine                        # 2114 passed, 53 skipped, exit 0, 268.06 s
pixi run python -m pytest cli/tests         # 610 passed, 1 skipped, exit 0, 523.25 s
CADEX_REVIEW_HOST=<private-address> pixi run python -m pytest \
    cli/tests/test_review_server.py -k private_network_address   # 1 passed (the one skip, exercised)
PYTHONPATH=cli pixi run python docs/probes/ot6/regression/final_probe.py \
    "http://<private-address>:8765/" "$HOME/cadex-projects/ot6-regression-src" docs/probes/ot6/regression
```

Both suites ran on the committed tree before this unit's own files were
added; the CLI count is one higher than the first pass's 560 because the
Finch, Robin and Heron receipt tests and the caps parametrisation over their
files landed in between. The one CLI skip is the private-address fixture,
which the full suite skips without `CADEX_REVIEW_HOST`; it was run again on
its own with the host set and passed, so nothing in the CLI suite is
unexercised. The 53 engine skips are the MJX-gated measurements and the
Blender-recipe cases that need a shell, as before; they are not claimed.

### The ot5 behaviours, each held to a test and to a retained lifecycle

| behaviour | tests in the CLI suite (all passed) | real lifecycle evidence, retained |
|---|---|---|
| review server and record suites | `test_review_server.py` 57 passed / 1 skipped, then exercised; `test_review_record.py` 34 passed; `test_review_history_scale.py` 3; `test_review_disk_use.py` 8; `test_review_lifecycle.py` 2 | the persistent server has served Finch, then Robin, then Heron across this run, one project at a time (`../finch/`, `../robin/`, `../heron/`) |
| live polling within five seconds | `test_browser_polls_training_histories_checkpoints_and_stale_states`; `test_browser_long_history_keeps_selection_and_playback_with_bounded_poll_work` | Heron's trainer updates reached the live page within 1.1 s of being committed, six sampled, one reload (`../heron/training.json` `live_browser`); on the persistent page in this pass, 5 project fetches in 10.5 s with a longest gap of 2.003 s at 1400 px and 2.002 s at 400 px |
| playback and download | `test_recorded_videos_are_served_whole_or_by_range`; `test_browser_playing_video_survives_new_current_attempt`; `test_browser_interrupted_download_leaves_polling_and_a_fresh_download_working` | at both widths the retained `heron1-final` video played to 0.20 s and downloaded (by tap at 400 px) with the recorded digest `4f16f9117af6…`, 35 809 bytes |
| restart during training | `test_restarting_the_dashboard_keeps_the_review_and_leaves_training_alone` (a fixture producer keeps writing across the restart) | the real-training restart is ot5's, on Lark (ADR-325); ot6 did not restart the server during Finch's, Robin's or Heron's runs, and does not claim to have. What ot6 adds is the checkpoint video published while each trainer was active, browser-checked, with the render's cost on the trainer's update interval measured (`../*/training.json` `render_overhead`) |
| copy isolation | `test_copied_project_reopens_without_source_and_keeps_edits_isolated`; `test_the_reader_reads_a_copied_project_the_same` | each policy was measured in a fresh scratch copy of its project (`ot6-*-eval-*`), with the source run asserted unchanged afterwards (`../heron/evaluate.py`, `../robin/`, `../finch/`) |
| failed-run states | `test_browser_explains_a_failed_observation_whose_training_finished`; `test_browser_lists_a_completed_run_whose_policy_was_never_stored_as_a_problem`; `test_browser_observes_final_policy_publication_failure` | Robin's `robin1` diverged at the default rate and is served as a failed historical run beside its checkpoint video (`../robin/TRAINING.md`, ADR-338) |
| headless operation | `test_the_review_command_serves_until_interrupted_and_writes_nothing`; `test_browser_reaches_the_dashboard_over_the_private_network_address` | the operator service is a user unit with no display, active since its last deliberate restart (`final.json` `service`); every browser check in ot6 was a headless Chromium |

### The persistent dashboard at both widths

A fresh visit at 1400×900, and one at 400×850 under touch emulation,
each selected `heron1-final` by itself (relation `current`, not stale), loaded
the run's own rollout exports (15 components, 53 620 triangles, `showing:
tessellated solids`), drew the model (8 801 non-background pixels at 400 px),
and had zero horizontal overflow. At 400 px one finger dragged 120×50 px
across the viewport: yaw moved from 0.8 to −0.4 and pitch from 0.5 to 1.0 at
an unchanged distance, and the page did not scroll. The two frames are the
`#model` region, quantised to 256 colours: [final-1400.png](final-1400.png)
(121 747 bytes) and [final-400.png](final-400.png) (51 208 bytes, taken after
the orbit, so the arm is seen from the orbited camera). Both show the dark
grid mat, the arm's real solids in the identity colours with the servos,
horns and base recognisable, the collision toggle off and the per-component
list naming each solid's retained mesh, placement source and proxy count.

### What this pass does not claim

- No source, protocol or payload behaviour changed in this unit, so no build
  and no packaged gate; the probe and its test are the only additions.
- Skipped tests are not exercised coverage, except the one CLI skip run
  separately as above.
- The restart-during-training fact rests on ot5's Lark evidence and the
  fixture test; ot6 adds no real restart.
- The operator address is read from the service unit by the caller and never
  written here; suite logs, the probe's stdout and the private-address run's
  log stay under `~/cadex-projects/ot6-regression-src/`, identified by the
  digests in `final.json`.

## First pass (iteration 16, before D7 and D8 closed)

This is the regression fallback requested by the iteration-16 critic when
Robin's product agent remained unavailable. It verifies the current product;
it does not complete Robin's design or substitute for the remaining balancer
and arm lifecycles. [verification.json](verification.json) carries suite
results, live browser observations and SHA-256 identities of external logs.

## Scope

From the product checkout, run `pixi run test-engine` and
`pixi run python -m pytest cli/tests`. The CLI suite includes headless browser
checks at 1400 px and 400 px, touch orbit and pinch, playback and download,
polling, failed-run presentation, historical views and copy isolation.
`test_review_lifecycle.py` checks restart recovery within five seconds while
its fixture producer keeps writing. That is a fixture producer, not a new GPU
training run; the earlier real-training evidence remains in the Finch and
ot5 lifecycle records. No training, build or product-code change occurs here.

The additional persistent-page check visits the configured private operator
URL, `http://<private-address>:8765/`, at 1400×900 and 400×850 with touch
emulation on the latter. It requires Finch's `finch1-final` selection, loaded
real solids and zero horizontal overflow, plays the retained video and downloads
it at both widths. The two downloads match each other and the retained final-run `video.json`
SHA-256: `f57c4c3bb2b3ce565d1feefa411c88879c92d4efe0561d45d3dddc9e995cb6f7`
(155,239 bytes). Screenshots are
not refreshed because this unit changes no visual behavior; the D1–D4 image
comparisons remain the visual evidence.

## Why the D7 continuation did not run

The full retained failed candidate was recovered from its `request.json` into
external `ot6-robin-src/recovered-candidate.py`. The recovery prompt supplies
that complete source and the original design requirements, requests correction
of reset-floor penetration and a complete `write_script` submission, followed
by inventory and measured fits. The bounded product CLI invocation exited 1
immediately with the provider's session limit. It did not accept a balancer.
The accepted Robin revision remains the catalog probe `f5f053348145…`.

The dashboard therefore stays on Finch's completed lifecycle. No inventory or
fit is certified for Robin, and no training starts. The next D7 turn can reuse
the preserved recovery prompt and candidate when provider access permits it.
This dispatch takes the critic's explicit D9 fallback without waiting for the
provider's advertised reset time.

## Verification limits

The engine suite passed **2,114 tests, 53 skipped**, exit 0, in 324.49 s.
The CLI suite passed **560 tests, 1 skipped**, exit 0, in 556.46 s.
Skipped cases are not claimed as exercised. The CLI private-address fixture
requires `CADEX_REVIEW_HOST`; the full suite is run without that variable,
while the separate browser probe reaches the actual persistent private address.
No packaged gate is needed for this documentation-only unit: no protocol,
payload or source behavior changed. This is current-tree regression evidence;
the final D9 assessment must also account for subsequent D7 and D8 work.
