---
node_id: c4657ecb-e270-52aa-b41d-36b38d45e3ae
slug: copper-haven-4303
title: 'D9 regression fallback: both full suites green and Finch final plays and downloads at desktop and phone widths; Robin provider still blocked'
created_at: '2026-09-14T01:54:05+00:00'
parents:
- wise-brook-4842
summary: ''
artifacts:
- docs/probes/ot6/regression/README.md
- docs/probes/ot6/regression/verification.json
---
## What

Advanced D9 with full current-tree regression verification and a live persistent-dashboard check at desktop and phone widths. The user-facing receipt is `docs/probes/ot6/regression/README.md` and `verification.json`; full logs and the browser probe stay outside the checkout under operator cadex-projects `ot6-robin-src/`.

## Why

This follows [rec: wise-brook-4842]. The critic requested recovering Robin's failed candidate through the product agent, correcting reset-floor penetration, submitting the complete source and finishing inventory and measured fits before switching the dashboard or training. The critic explicitly allowed D9 regression verification if provider availability still prevented the design turn. I recovered the complete source and attempted that turn; the provider refused it immediately with its session usage limit. I therefore took the authorized fallback without clock-waiting or actor-authoring a replacement design. This dispatch is one D9 verification unit, with the availability check as its prerequisite.

## Method

Recovered the prior failed request's `source` into external `recovered-candidate.py` and composed `resume.prompt.txt` from the complete candidate plus original creation requirements. The product invocation used `timeout --signal=TERM --kill-after=10s 1800 ./cadex --project "$PROJECTS/ot6-robin" --out "$PROJECTS/ot6-robin-src/resume-out" --json -p "$(cat "$PROJECTS/ot6-robin-src/resume.prompt.txt")"`. It ran 2026-09-14 01:42:22–01:42:25 UTC, exit 1, model claude-fable-5, provider session limit. Accepted revision remains `f5f0533481457549b2f07637a9ac825a5bb32ca7270dafdb504c8adf5c7e16b4`; no candidate was accepted, inventory measured or training started.

Ran `pixi run test-engine` and `pixi run python -m pytest cli/tests` concurrently, retaining full logs externally. The CLI suite includes rendered design checks at both widths, touch interaction, polling, playback/download, failed states and copy/restart lifecycle fixtures. These fixture producers are not new GPU training; earlier real-training evidence remains in its existing records. Skipped tests are not claimed as exercised. No product source, protocol, payload, shell or dependencies changed; no build or packaged gate was required.

The persistent dashboard start check at 01:42:43 UTC (after the 2.67-second provider refusal, not retroactively before it) loaded `finch1-final`, 29 real solids and 95,212 triangles. The closing headless probe visited the configured private address at 1400×900 and 400×850, with touch emulation for the latter, checked selected run and zero horizontal overflow, played the final video and downloaded it at both widths. Both 155,239-byte downloads match the retained final-run video manifest SHA-256 `f57c4c3bb2b3ce565d1feefa411c88879c92d4efe0561d45d3dddc9e995cb6f7`. Probe setup first used a nonexistent Page.call method, then mistakenly treated desktop scrollbar width as horizontal overflow; both harness-only errors were corrected to Page.send and scrollWidth minus clientWidth before the successful check. No product defect was inferred from those errors.

## Result

Engine: 2,114 passed, 53 skipped in 324.49 s, exit 0. CLI: 560 passed, 1 skipped in 556.46 s, exit 0. The private-address fixture was skipped because CADEX_REVIEW_HOST was unset; the independent browser probe exercised the actual persistent private address. Final receipt cap/privacy checks: 60 passed, 16 deselected, exit 0. D9 now has both full suites green on this source revision plus the live Finch final view, playback and download at both widths. D9's final assessment must still account for the unfinished D7/D8 work; this does not tick the whole charter.

No new dependency or source change. No broken tree observed. Robin remains an accepted probe, with recovery inputs retained and no verified balancer inventory or fits. Keep the persistent operator dashboard on Finch until a complete balancer is accepted. Next useful D7 work remains the critic's complete-source recovery through the product agent, inventory and measured fits, followed by dashboard handoff before bounded training. Export and graph check are run before committing this record; no state nodes or generated views are edited.

Dispatch closed: 1 unit — D9 current-tree regression verification after Robin's product-agent recovery was refused by the provider.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot6
- commit: 33d3452f2a7f44ad8eb33876055a1d8bed0ef59d

## State Impact

- target: civic-lily-1239 — Current-tree D9 regression verified: engine 2114 passed/53 skipped, CLI 560 passed/1 skipped, persistent Finch final real-solids page at 1400 and 400 px with playback and digest-matched downloads; final assessment still follows unfinished D7/D8 work
- target: ready-sand-2621 — Complete failed Robin candidate recovered and supplied to product-agent repair turn, but provider immediately refused with session limit; accepted probe unchanged, inventory and fits unverified, no training; D9 fallback taken
