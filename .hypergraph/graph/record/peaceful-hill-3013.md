---
node_id: 30e2067c-b527-5350-9520-99b69cd6804f
slug: peaceful-hill-3013
title: 'F5–F7: bounded frozen-design evidence runner before provider reset'
created_at: '2026-09-14T21:58:04+00:00'
parents:
- tidy-journey-9462
summary: ''
---
## What

Added the bounded frozen-design evidence runner and its usage document under
`docs/probes/ot7/runner/`, with known-answer CLI fixtures and ADR-354. It can
collect the three F5–F7 designs individually, preserving prompts, provider
streams, accepted static fit, raw swept coverage, inventory and final smoke.
No product code, design, frozen prompt, retained project or dashboard changed.

## Why

Advances F5 (`stormy-aspen-5433`), F6 (`narrow-dune-9454`) and F7
(`rapid-grove-9687`) by making their evidence collection bounded and repeatable.
The critic requested F4 after its provider reset, otherwise this runner.
At unit start the clock read 2026-09-14 21:44 UTC (17:44 America/New_York),
before the documented 20:20 local reset in the iteration-19 refusal receipt.
I took the requested fallback without another provider invocation or retained
project audit. F4's unchanged seed and frozen prompt remain ready after reset.

## Method

The runner validates all frozen hashes before creating an external ot7-*
project, refuses any existing target, and records each consumed prompt slot
before launching a child. One create plus three ordered continuations is the
entire schedule; restarting cannot grant a fourth continuation. Only ordinary
product-agent turns write designs. A wrapper at the existing turn-factory seam
captures provider frames and blocks the CLI's unfrozen no-tool nudge. Each turn
is followed by a restore=False read of every accepted clearance and inventory
page. Static counts use the product fit_summary; sweeps stay raw, without a
new verdict engine. Process errors/timeouts stop prompting. One final
one-second hold smoke has a 240-second internal and 300-second process bound.
Logs, traces and transcripts stay in the project with file hashes. Model calls
have a 30-minute bound and timed-out process groups are killed.

Known-answer fixtures force all four slots to fail, prove a second invocation
cannot dispatch another call, verify prompt/transcript hashes and fit counts,
stop on provider errors/timeouts, reject changed prompts, suppress a second
unfrozen provider call and exercise real child timeout cleanup.

## Result

Validation: `pixi run python -m pytest cli/tests` exited 0: **693 passed,
1 skipped in 530.97 s**. The focused runner/freeze run passed 12 tests.
`git diff --check` and the runner `--help` passed. Full CLI log:
`cadex-projects/ot7-runner-validation/evidence/cli-tests.log`, SHA-256
`d8329ee84efdb77a797d9b6ee3b5ee7e9075d0d4dc1a5ba11a35cf27c69a03f6`.
No engine source changed, so engine/build/packaged gates were not rerun.

F5–F7 have an executable evidence collector, not completed design results.
No provider call or design attempt ran in this unit, so no fit or smoke pass is
claimed and F4–F7 remain open. The collector uses all three frozen
continuations even if static fit passes, preserves unavailable coverage, and
requires the closing report author to assess swept extrema and smoke verdicts.
An interrupted collector cannot be restarted: its consumed budget and evidence
must be reported. Missing files after timeout mean missing evidence, never a
zero failure count. No new dependency, build, engine/payload/protocol change,
charter edit, state-node edit or reconcile. Assumption: the recorded provider
reset remains the correct earliest retry time.
Dispatch closed: 1 unit — bounded frozen-design evidence runner for F5–F7.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot7
- commit: 97662f5a1505aa0ee4856635b5320978d7b0884b

## State Impact

- target: stormy-aspen-5433 — F5 has a tested frozen evidence collector with one create and at most three continuations; no arm design attempt ran.
- target: narrow-dune-9454 — F6 shares the tested bounded collector with per-turn measured fit, transcript hashes, inventory and final smoke; no balancer attempt ran.
- target: rapid-grove-9687 — F7 shares the tested bounded collector; restart and automatic-follow-up guards prevent extra prompts. No biped attempt ran.
