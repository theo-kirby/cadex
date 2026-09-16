---
node_id: bbdc9406-0ba8-5c12-b3e9-4a28179fa41e
slug: idle-crow-9434
title: A refused window probe is no room, whatever the window reads (ADR-364); F6 blocked by a Fable org-level limit with all four slots intact
created_at: '2026-09-16T14:47:22+00:00'
parents:
- wandering-ocean-3301
summary: ''
---
## What

The ot7 collector's window gate now reads the probe's own outcome, not just a
number it reported. A one-word probe the provider **refused** is no room
however low the five-hour window reads; the reading keeps every unified
window as a percentage beside `rate_limit_type` and the refusal; and a probe
that *answered* is never treated as a refusal, so a stray rejected overage
frame cannot strand the remaining frozen prompts. ADR-364,
`docs/probes/ot7/runner/run.py`, five fixtures in
`cli/tests/test_ot7_runner.py`, the runner README, and the receipt
`docs/probes/ot7/attempts/f6-window-refusal.json`.

No design turn was dispatched. F6's create prompt and all three continuations
are unspent and no `ot7-robin-b` exists.

## Why

F6 was the run's next unit: the frozen Robin create on `ot7-robin-b`, gated on
the window probe reading under 45 % (`narrow-dune-9454`). The probe was run
and **F6 is blocked** — but not by the five-hour window, which stood at 1 %.
`claude-fable-5` refused the probe in 2.369 s because
`seven_day_overage_included` was at 100 % with `overageDisabledReason:
org_level_disabled`: "You've reached your Fable limit."

The charter's answer to a limited harness is an unblocked tooling unit, and
inspecting the gate that had just fired produced one. The gate returned no
room only by accident: it reads the frame's top-level `status` and
`unifiedWindows.five_hour`, and on that probe `status` happened to carry the
*overage* rejection. It did not repeat. The **next** live probe, same account
twenty minutes later, returned `status: allowed`, `rateLimitType: five_hour`,
five-hour at 2 % — refused just the same. Against the retained stream, the
pre-ADR-364 gate reads that frame as **room** and sends the prompt. F6 was
minutes of luck from losing slots to calls no model would see, through the
very gate ADR-358 added to prevent exactly that.

The product agent's model was deliberately left at `claude-fable-5`: ADR-363
moved the Ouroboros roles to `claude-opus-5` and explicitly preserved the
experiment's settings, so F6 and F7 stay comparable with F5, which ran on
Fable. Changing the experiment's model to unblock it would be an actor
interpretation of scope, not a routine choice.

## Method

1. Probed the window (`run.py window`, spends no slot): refused, five-hour
   1 %, `seven_day_overage_included` 100 %, overage disabled at org level.
2. Reproduced the hole directly: fed the real frame with `status` set to
   `allowed` to `window_has_room` — `True` at 1 % against a 45 % bound.
3. Read the probe's stream as what it is, a model call: classified it with
   `void_reason`, the same ADR-355 rule a design call's stream already gets,
   and made `window_has_room` return false on any refusal before it looks at a
   number. Kept every `unifiedWindows` entry, `rate_limit_type` and the
   refusal in the reading, because `five_hour 1 %, no room` names no cause.
4. Closed the opposite error, which would have been worse: an org with overage
   disabled emits a rejected overage frame beside an ordinary allowed window,
   and reading that as a refusal would strand every remaining prompt. The
   classifier runs only on a probe that did **not** answer (`probe_answered`).
5. Five fixtures built from the real frames. The first four fail on the old
   code, and two of them fail on the *verdict*, not on shape: `window_has_room`
   returns `True` at 1 %, and the whole Robin schedule ends `exhausted` with
   four slots spent instead of `paused` with zero.
6. Re-probed live after each change: still `room: false`, now with the reason
   recorded.

## Result

`pixi run python -m pytest cli/tests` — **773 passed, 1 skipped, exit 0** in
8 m 48 s, the whole suite on the changed tree. Of those, the runner's own file
is **76 passed** (71 before this unit). The four regression fixtures were
confirmed red on stashed `run.py`, two of them failing on the verdict rather
than on shape. No engine, protocol, payload or `shell/` code is touched, and
`test_ot7_runner.py` is the only importer of `run.py`, so no engine suite or
packaged gate applies.

Measured, and the operative fact for the next iteration: **`claude-fable-5` is
refused on this account at the organisation level** — `seven_day` 51 %,
`seven_day_overage_included` 100 %, overage `org_level_disabled` — while the
five-hour window sits at 1–2 %. **F6 cannot be dispatched by any five-hour
reset**, which is what the previous plan was waiting for (`narrow-dune-9454`
named the 18:50 UTC reset; the probe now reports 19:20 UTC, and neither
matters). It waits on Fable capacity returning to the account, or on an owner
decision. Do not spend a frozen prompt against it; `run.py window` is the cheap
check and now says why.

Assumption recorded: the product agent's model stays `claude-fable-5`. ADR-363
preserved it on purpose and F5 ran on it, so switching F6/F7 to `claude-opus-5`
would break the cross-design comparison the charter's F5–F7 bar rests on. That
is a charter question for the owner, not an actor's call — but it is the one
decision that would unblock F4–F7 today, and the next iteration should surface
it rather than idle on a five-hour reset that will not help.

No new dependency. F6 and F7 remain open with every slot unspent; F4 and F5
remain exhausted as recorded.

Dispatch closed: 1 unit — ADR-364, the window gate reads the probe's own
refusal, not just its number; F6 blocked by a Fable org-level limit with four
slots intact.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot7
- commit: 02f6b246d2ee4e726365ea6c7df37c091bf141fb

## State Impact

- target: narrow-dune-9454 — F6 is blocked not by the five-hour window but by claude-fable-5 being refused at the organisation level (seven_day_overage_included 100%, overage org_level_disabled) while five_hour reads 1-2%; no design turn was dispatched, the create prompt and all three continuations are unspent and no ot7-robin-b exists. Waiting on a five-hour reset will not unblock it; the product agent's model stays claude-fable-5 per ADR-363, so F6 waits on that account's Fable capacity or an owner decision.
- target: mild-ledge-7157 — ADR-364: the collector's window gate now reads the probe's own outcome, not only its number. A probe the provider refused is no room however low the five-hour window reads (classified by void_reason, the same ADR-355 rule a design call gets); the reading keeps every unifiedWindows entry as a percentage beside rate_limit_type and the refusal; and a probe that answered is never a refusal, so a stray rejected overage frame cannot strand the remaining frozen prompts. Verified: against the retained live stream the pre-ADR-364 gate dispatches F6's create and all three continuations into a refusing model. cli/tests 773 passed, 1 skipped.
- target: rapid-grove-9687 — F7 is blocked by the same org-level Fable refusal as F6 and follows it; its four slots are unspent.
