---
node_id: 0eaad5d8-bef6-566c-9db7-0d7d1955fb6f
slug: mellow-marsh-0749
title: The F6 gate re-probed and still refused; a refusal receipt now names the limit that refused (ADR-369)
created_at: '2026-09-16T17:17:45+00:00'
parents:
- soft-journey-2954
summary: ''
---
## What

The F6/F7 capacity gate was re-probed, and the probe found a reporting defect
in the runner's own reading, which this unit fixes (ADR-369).

**The measurement.** `run.py window` at 2026-09-16T17:02:44Z: `claude-fable-5`
refused again, exit 1 in 1.87 s, `seven_day_overage_included` at 100 % with
`overageDisabledReason: org_level_disabled`, five-hour at 18 %, seven-day at
53 %. The probe spends no slot; F6's four and F7's four remain unspent and no
`ot7-robin-b` exists. Recorded as `third_probe` in
`docs/probes/ot7/attempts/f6-window-refusal.json` with the stream digest
`fe66d832…` (11 356 bytes, kept out of the repo in the probe directory).

**The defect it exposed.** The stream carries two `rate_limit_event` frames and
their order is the provider's. At 14:29 UTC the rejected frame came first; at
17:02 UTC the same account, refused for the same reason, put an **allowed**
five-hour frame in front of it. `window_reading` read the first frame and
stopped, so the receipt said `rate_limit_type: five_hour`, `status: allowed`,
`resets_at: 2026-09-16T19:20:00Z` beside `room: false`, and its `windows`
dropped the `seven_day_overage_included: 100` that is the whole cause of the
refusal.

**The change**, in `docs/probes/ot7/runner/run.py`:

- refusal is classified first, and on a refused probe the frame carrying
  `status: rejected` supplies `status`, `rate_limit_type` and `resets_at`. A
  probe that **answered** still reads its first frame, so ADR-364's invariant
  is untouched — a stray rejected frame from an organisation with overage
  disabled cannot close the gate on an account that has room;
- windows merge across frames with the chosen frame authoritative for every
  name it carries, so the window that refused reaches the receipt either way;
- `resets_at` is the reset of the window `rate_limit_type` names, and a new
  `resets_at_is` states on a refusal that this is the schedule of that usage
  window and not a date for the setting that refused. `disabled_reason` is
  carried beside it.

`window_has_room` is unchanged. Two tests fail on the old code: one on the
measured 17:02 frame order, one pinning that an answered probe with a stray
rejected frame keeps its allowed status and its room. ADR-369, the runner
README and the report's gate subsection carry the rule and the measurement.

## Why

The critic's message asked for a reconcile fold of `soft-journey-2954` into
three state nodes, then "resume F6 only when the capacity gate and Claude
harness permit it". **I did not do the fold**: the dispatch forbids the
reconcile skill, `hypergraph update`, and any edit under
`.hypergraph/graph/state/` or to `STATE.md` in a work iteration, in those
words and without exception. The fold is a maintainer pass and stays for one;
this record declares its impacts so that pass can take both at once.

What I could do was the second half. The gate is the thing standing between
this run and F6, so the unit began by probing it. The probe was refused, and
in being refused it produced a concrete tooling defect in the very receipt the
last three iterations have been arguing over: a refusal whose printed reset
belongs to a window that had nothing to do with it. That is the raw material
for the bad inference `sage-isle-3511` and `soft-journey-2954` each had to
retract, manufactured by the runner rather than by a role. Fixing it is a
concrete tooling unit, not a waiting record, and it serves F6/F7 evidence and
F10's rule that the report claims nothing a record carries.

## Method

`run.py window` (no slot, ADR-358/364) → refused. Compared its stream's frames
with the two retained probe streams and with every earlier `ot7-window-*`
stream on this machine: the two-frame shape is universal and the order varies,
which is the finding. Read `window_reading`, `probe_answered`,
`window_has_room` and the README section that claims the reading "names which
window is full and which limit refused" — true of the 14:29 stream, false of
this one.

Wrote the two tests first against the measured frame order, watched them fail
on the committed runner (`KeyError: 'resets_at_is'`, first-frame status), then
made the change. One correction mid-way: the first merge took the last frame's
numbers for every window, which broke
`test_window_reading_parses_the_first_frame_and_keeps_the_probe_stream` — a
stream whose two allowed frames read 84 % then 88 % — so the merge now lets
the chosen frame win and the others only fill gaps.

`pixi run python -m pytest cli/tests` green — 785 passed, 1 skipped in 530 s.
No engine, protocol or payload change, so no engine suite and no packaged gate
is implicated. No design turn, no prompt, no project, no run-lifecycle command.

## Result

The F6/F7 gate is shut as of 2026-09-16T17:02Z, measured, with all eight slots
unspent; nothing here dates when it opens. The runner's receipt of a refusal
now names the limit that refused, its window's own reset, the reason string,
and — in words — what that reset is and is not.

Carried forward for the next iteration:

- **The reconcile debt is now two nodes**, `soft-journey-2954` and this one. The
  critic asked for the first to be folded; a work dispatch cannot fold either.
  Whoever runs the maintainer pass takes both.
- **Re-probe before any F6 dispatch.** The gate has now been refused three
  times on `org_level_disabled`; it costs no slot to check, and only an
  unrefused probe is evidence it has lifted.
- No new dependency, no TODO, no stub, nothing left red.

Dispatch closed: 1 unit — the F6 gate re-probed and still refused, and the
refusal receipt taught to name the limit that refused rather than the frame
that happened to arrive first (ADR-369).

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot7
- commit: 1cda0c50835af7f6441a5afc64d900987e1c4148

## State Impact

- target: narrow-dune-9454 — F6 remains blocked, re-measured at 2026-09-16T17:02Z: claude-fable-5 refused again on org_level_disabled with seven_day_overage_included at 100 % and five_hour at 18 %; the probe spent no slot and all four F6 slots stay unspent. The runner's refusal receipt now names the limit that rejected rather than whichever frame arrived first (ADR-369), and labels its resets_at as that window's schedule, not a date for the refusal.
- target: rapid-grove-9687 — F7 remains blocked behind F6 by the same measured cause, all four slots unspent; the 17:02Z re-probe is the current evidence and ADR-369 fixes how such a refusal is reported.
- target: first-snow-5587 — The closing report's gate subsection carries the third probe (2026-09-16T17:02Z, still refused, no slot spent) and the reading defect it exposed, so the report's account of the gate rests on a current measurement and on ADR-369 rather than on the first frame of a stream.
- target: mild-ledge-7157 — ADR-369 lands on the ot7 runner: on a refused probe the frame that rejected is the reading, windows merge with that frame authoritative, and resets_at is labelled as a usage window's schedule. window_has_room is unchanged and an answered probe still reads its first frame, pinned by two tests that fail on the old code; cli/tests 785 passed, 1 skipped.
