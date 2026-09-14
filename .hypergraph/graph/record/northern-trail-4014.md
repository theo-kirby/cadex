---
node_id: 93f4519f-7728-53de-be21-fde024bb206d
slug: northern-trail-4014
title: 'Robin recovery through Opus, Sonnet and Haiku: all provider-refused; D7 remains open'
created_at: '2026-09-14T01:58:34+00:00'
parents:
- copper-haven-4303
summary: ''
artifacts:
- docs/probes/ot6/robin/MODEL-RECOVERY.md
- docs/probes/ot6/robin/model-recovery.json
---
## What

Attempted the critic's D7 recovery through the product CLI with three alternate Claude model selections. All were refused by the provider session limit. Added the user-facing failed-experiment receipt `docs/probes/ot6/robin/MODEL-RECOVERY.md` and compact `model-recovery.json`, including identities and retained external log digests.

## Why

This follows [rec: copper-haven-4303]. The critic explicitly requested using the existing model option to finish Robin's recovered complete candidate, reset-floor correction, acceptance, inventory and measured fits. I supplied that complete candidate and repair instructions through `--model opus`, then `sonnet`, then `haiku`. None produced a repair because all returned the same session limit. The requested completed mechanism could therefore not be delivered within the product-agent constraint. This is a failed D7 experiment, not another D9 fallback; no actor-authored design, provider infrastructure change or clock waiting substituted for the requested work.

## Method

Before invoking the product CLI, reused the retained iteration16 operator browser probe with its output filename changed to iteration17-start.json. It read the private address from the service configuration and visited the persistent dashboard at 1400×900 and 400×850 with touch emulation for the latter. After all three attempts repeated it into iteration17-end.json. Full files remain under operator cadex-projects `ot6-robin-src/`; receipt paths are relative and portable.

For each model selection invoked `timeout --signal=TERM --kill-after=10s 1800 ./cadex --model <selection> --project <projects>/ot6-robin --out <projects>/ot6-robin-src/<selection>-out --json -p <complete-recovery-prompt>`. The prompt is the retained 28,296-byte resume.prompt.txt with SHA-256 90cf1b13a450f84d5e393b8e69b27f1bb4a03076f337d9759fd5998ab04cd096. Output, error, timestamps and exit status are retained per selection; model-recovery.json enumerates their hashes. The CLI echoes the requested alias, not a resolved model version, so none is claimed. An initial wrapper command used unavailable `python`; it exited 127 before any product invocation and was corrected to python3.

Ran `pixi run python -m pytest cli/tests/test_review_design.py -k 'caps or private_address'`: 63 passed, 15 deselected, exit 0. No product source, protocol, payload, dependency or shell changes; full suites and builds were not repeated. Export and graph check are required before committing. No state nodes or generated views changed.

## Result

All three product invocations exited 1 with the session-limit message and reported a 10:10 pm America/New_York reset. Changing these three selections did not bypass the provider limit at the tested time; this does not establish future availability. Robin's accepted revision remains f5f0533481457549b2f07637a9ac825a5bb32ca7270dafdb504c8adf5c7e16b4 and accepted contract contains only probe_motor. No reset-floor repair, complete balancer acceptance, inventory or fits were verified; no training began. D7 remains open, as does D8. The recovered candidate and prompt remain available for the next product-agent attempt.

Both start and end browser visits, at both widths, selected finch1-final with 29 real solids and 95,212 triangles, zero horizontal overflow and advancing video playback. All downloads were 155,239 bytes and SHA-256 f57c4c3bb2b3ce565d1feefa411c88879c92d4efe0561d45d3dddc9e995cb6f7. The persistent server remains running on Finch; Robin must be fully accepted and measured before moving it. No new dependency, no product defect inferred and no broken tree observed. The assumption was that existing Claude aliases might have separate available capacity; the actual refusals provide negative evidence against that workaround now. Do not repeat D9 suites to fill a blocked design dispatch.

Dispatch closed: 1 unit — attempted Robin recovery through three alternate product-CLI model selections, all provider-refused, with start/end operator checks and a failed D7 experiment receipt.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot6
- commit: ec691da0e1e7f87e5bf1451de6279f7cd77bb571

## State Impact

- target: ready-sand-2621 — Complete recovery prompt supplied via existing product CLI model selections opus, sonnet and haiku; all exited 1 with session limit, accepted motor probe unchanged, no repaired mechanism or measured fits. Start/end operator checks passed on Finch; D7 remains open.
