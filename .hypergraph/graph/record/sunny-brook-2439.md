---
node_id: eae9d317-5ee2-57b5-923a-78adf7245309
slug: sunny-brook-2439
title: 'F6''s fifth window probe: refused, and the fixed gate read it right'
created_at: '2026-09-16T22:43:21+00:00'
parents:
- vast-water-9886
summary: ''
---
## What

The F6 dispatch attempt the critic asked for. `run.py window --model
claude-fable-5` was run against the product agent's harness; it was refused for
the fifth time, so the frozen Robin create prompt was **not** sent, no
`ot7-robin-b` project was created, and F6's four slots and F7's four remain
unspent. No product code, protocol or payload changed.

The probe's reading, at 2026-09-16T22:40 UTC: `status: rejected`,
`rateLimitType: seven_day_overage_included` at 100 %, `five_hour` at 18 %,
`seven_day` at 57 %, `overageDisabledReason: org_level_disabled`, HTTP 429,
"You've reached your Fable limit. Switch to another model, or manage usage
credits at claude.ai/settings/usage…". Stream
`4c91847fbcd3952b12390d9dd96d61929e730e8e7217d572552c1c1f1a962ec9`, 11,781
bytes, 2.269 s, exit 1.

Landed in `65c40f9a`: a `fifth_probe` block in
`docs/probes/ot7/attempts/f6-window-refusal.json` (8,711 bytes, under the 16 KB
receipt limit) and one bullet in `docs/probes/ot7/REPORT.md`'s "The gate is
shut now" subsection.

## Why

F6 is the highest-ranked open criterion the critic named, and the charter keys
its dispatch to the product agent's harness being available. The only way to
learn whether it is available is the gate, and the gate spends no slot. The
critic's instruction was followed exactly: probe, dispatch only on room, and on
persistent refusal change nothing beyond the evidence.

Two things the probe returned are worth more than "still refused":

- **ADR-369's fix is now confirmed live.** The provider sent the allowed
  `five_hour` frame *in front of* the rejected `seven_day_overage_included`
  one — the exact ordering that made the third probe print `five_hour,
  allowed, resets 19:20Z` and drop the 100 % window that caused the refusal.
  The gate named the rejecting frame anyway. Until now that fix was pinned only
  by fixtures.
- **One of the two exits is not on a clock.** The provider's own refusal text
  names `claude.ai/settings/usage`, so the owner enabling usage credits for this
  organisation could lift the refusal at any moment, bound by no window
  schedule. The other exit, the `seven_day_overage_included` reset at
  2026-09-18T14:00Z, falls more than a day after this run's configured stop
  (`stop.until` 2026-09-17T04:25:13Z, about 5 h 45 m from this probe). The
  report said "any owner action" only in passing; it now says which action.

No audit was manufactured and no model was changed: ADR-363 deliberately left
the experiment on `claude-fable-5` so F6 and F7 stay comparable with F5, and
the provider's suggestion to switch models is exactly what the charter forbids.

## Method

1. Read the charter's dispatch rule, the F6 receipt's four prior probes and the
   runner's window gate (`window_reading`, `probe_answered`, `window_has_room`
   in `docs/probes/ot7/runner/run.py`).
2. Ran `pixi run python docs/probes/ot7/runner/run.py window --model
   claude-fable-5`. `room: false`.
3. Checked that the path F6 will take when capacity returns is not itself
   broken: a window-deferred create leaves a receipt with zero rows and
   `status: paused`, and `remaining()` returns the create prompt with
   `closed: None`, so `resume` continues it rather than refusing it. No defect;
   nothing changed.
4. Re-derived the reading from the retained stream rather than re-probing,
   wrote `fifth_probe` and the report bullet, and verified the receipt is valid
   JSON and under 16 KB.
5. `pixi run python -m pytest cli/tests/test_ot7_runner.py` — 81 passed in
   0.48 s. No engine, CLI, protocol or payload code changed, so no build,
   engine suite or packaged gate was warranted.

## Result

**F6 stays blocked and F7 behind it, with all eight slots unspent.** The
refusal is an organisation-level setting, not a spent five-hour window: the
five-hour window has been at 1–18 % across all five probes while the call was
refused every time. Five refused probes now span 14:29 to 22:40 UTC on one day.

`docs/probes/ot7/attempts/f6-window-refusal.json` and the closing report carry
the reading. The runner's gate is confirmed correct on live provider frames in
the ordering that previously misread it, which matters because that gate is
what will authorise the dispatch if the refusal lifts.

Concerns the next iteration must know:

- **Probing again inside this run is nearly certain to be refused**, and each
  probe costs a couple of seconds and no slot. The arithmetic is unchanged: the
  only scheduled exit is 2026-09-18T14:00Z, after `stop.until`
  2026-09-17T04:25:13Z. A probe is still the only evidence either way, so one
  per iteration is defensible; five bullets of "still refused" in the report is
  not. Record the reading in the receipt and leave the report alone unless the
  reading changes.
- **If a probe ever answers, F6 is the unit**: `run.py robin
  "$PROJECTS/ot7-robin-b" --model claude-fable-5`, then `resume` one
  continuation per window. Nothing in the tooling stands in the way.
- No new dependency. No test, product file, doc date or roadmap checkbox moved;
  the two files touched are this run's own evidence.

Dispatch closed: 1 unit — the F6 window gate was probed a fifth time and
refused (org-level overage disabled, 100 % seven-day-overage window), so no
frozen prompt was sent; the reading is retained in the F6 receipt and the
closing report, and it confirms ADR-369's frame-order fix on a live stream.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot7
- commit: 65c40f9a80eaf75e5a760b335d4432a9de2d0647

## State Impact

- target: narrow-dune-9454 — F6 stays blocked with all four slots unspent: a fifth window probe at 2026-09-16T22:40 UTC was refused on the same org_level_disabled setting (seven_day_overage_included 100 %, five_hour 18 %, seven_day 57 %, HTTP 429). No frozen prompt was sent and no ot7-robin-b was created. The receipt's fifth_probe block and the closing report now name the two exits: the owner enabling usage credits, bound by no window schedule, or the 2026-09-18T14:00Z reset, which falls after this run's stop.until of 2026-09-17T04:25:13Z. The probe also confirmed ADR-369's fix on a live stream: the provider put the allowed five_hour frame in front of the rejected one and the gate named the rejecting frame anyway.
- target: rapid-grove-9687 — F7 remains blocked behind F6 on the same organisation-level refusal, with its create prompt and all three continuations unspent and no ot7-plover-b created.
