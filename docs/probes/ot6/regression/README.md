# D9 regression verification

Verified against source: 2026-09-14. [Cadex-new]

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
