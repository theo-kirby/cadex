---
node_id: 3f781f52-2869-5851-98f4-7f27bf2ab442
slug: amber-glade-2813
title: 'Bet: name the comparable iterate, and make the row say what varied'
created_at: '2026-09-08T19:47:58+00:00'
parents:
- tidy-cove-8382
summary: ''
---
## What

Keep the token-free `--set` iterate on `ot4-quill` first, and name the one
assignment that is actually comparable. Take **one new direction**: the walk's
comparison row does not record the two things that decide whether its own delta
means anything — the **seed** it ran at, and the identity of the **objective** it
trained against. Rank a prompt-driven design turn last, first to drop on a
provider refusal. Fold the landed leg bound out of the medium rung and put the
noise-floor measurement there in its place.

Short becomes, in order:

1. `cadex walk --set stroke=60` on `ot4-quill`, no `--prompt`, 5 x 16 x seed 0,
   into `runs/<name>` beside the baseline. Report the delta; do **not**
   adjudicate finding-versus-noise.
2. **New direction.** The walk row carries the seed and an objective digest, so
   a reader can tell a re-seed from a redesign and an incomparable objective
   from a comparable one.
3. A `--prompt --resume` design turn against a project with a past.

## Why

**Unit 1 is unchanged in kind and sharpened in substance, because most `--set`
choices on this project silently invalidate the comparison.** `ot4-quill`'s
script clamps its setpoint to the stroke — `target_ext = min(p.target_ext,
p.stroke)` at `script.py:111` — and then interpolates that clamped value as a
**literal into the reward expressions**: `exp(-((quill_ext - %.4f)/%.4f)^2)` and
`abs(quill_ext - %.4f)` at `script.py:232-235`. With `target_ext=30` and
`stroke=40`, any `--set stroke=<20|30>` re-clamps the setpoint and rewrites the
objective, and `--set target_ext=...` rewrites it directly. The project's own
`PROGRESS.md` preamble already warns that objectives may be compared "only when
reward expressions, weights, units and episode lengths match" — so those
assignments produce a row whose `total_reward` delta is meaningless, and nothing
in the walk would say so. `--set stroke=60` is the assignment that keeps
`min(30, 60) = 30`: the reward expressions come out byte-identical, while the
joint's `length_limits_mm`, the actuator's `command_limits_mm` and the derived
`bore_z0` housing geometry all change (`script.py:102,158,208`). That is a real
mechanical iterate with an unchanged objective — the only kind whose delta is
readable. The action range widens with the command limit; that is a caveat to
report, not to hide.

The travel channel gets a physical prediction for the first time, rather than a
number to admire. The baseline row reads `travel_mm 20.28 on quill_component,
travel_deg 0`, and `travel_mm` is `max_displacement_mm` from the first solved
pose [rec: square-bay-3436]. The joint is limited for real —
`length_limits_mm=[0.0, p.stroke]` — and the setpoint stays at 30 mm, so travel
should stay in the 20-30 mm neighbourhood and **must not** approach 60. A
`travel_mm` that tracks the stroke rather than the setpoint would say the
channel is reading something other than the commanded coordinate. Both outcomes
are information; the carriage precedent, where an unlimited guide let a
component fall 4,699 mm, is why the bound is worth checking at all
[rec: solemn-journey-9731].

Unit 1 keeps its lead for the reasons that already held — it spends no provider
tokens (`--prompt` defaults to `[]`, and the parser's own help says "Spends
tokens only for `--prompt`"), and it is still the only unspent thing that
exercises ADR-260's two travel channels and ADR-261's leg bound on geometry no
fixture has seen [rec: hollow-cliff-1217] [rec: northern-comet-5917]. What
changes is its output contract: the previous rung asked the actor to "say
whether the delta reads as a finding or as noise at toy scale", and **no
evidence on this machine can support that judgement.** Every PROGRESS delta this
run has come from a single run at one seed, at 5 iterations x 16 environments;
nobody has ever run the same geometry twice and measured the spread. Asking for
a verdict with no yardstick invites a confident number. Unit 1 reports the
delta and names what would settle it.

**The new direction is what makes any of those deltas legible, and it is a
source-verified hole rather than a preference.** Two facts:

- The **seed never reaches the row.** `--seed` is read at `__main__.py:429`,
  threaded into the train leg's argv at `__main__.py:1402`, and appears nowhere
  in `_record_progress` or the row template. Meanwhile the generated preamble
  the CLI itself writes into every project instructs the reader, at
  `project_docs.py:264`, to "record iterations, environment count and seeds."
  The row carries the first two and drops the third. So two rows that differ
  only by seed are indistinguishable from two rows that differ by design, and
  the loop compares them anyway [rec: northern-comet-5917].
- The **objective has no identity in the row.** The row carries the script
  revision and digest, which move for any edit at all, and it carries
  `total_reward`, which is only meaningful across an unchanged objective. There
  is no field a reader or an agent can compare to know which case they are in —
  only the prose warning in the preamble. Unit 1 had to be planned around this
  by hand, by reading the script's reward interpolation; that reasoning should
  be a string compare in the row, not a planner's close reading.

This serves mission 2's "compare against the previous run" and mission 8's "test
them all the same way, rank them" at their premise, and it is `cli/` only,
offline, testable with the existing toy lifecycle fixtures. It is **not** the
parked variant study under `## Later criteria` — it generates no variants, ranks
nothing and renders no graph; it makes one row say what varied.

**Scope discipline.** No charter checkbox or gap node is retired, blocked or
superseded here. "Three modes, one shape" stays declined for a unit on the
standing reason: both unexercised limbs are unexercised by this run's
constraints rather than by missing work, remote parity is pinned offline by
`test_remote_walk_has_local_artifact_paths_with_a_cpu_dispatcher` and GUI
attachment is ADR-201 [rec: western-grotto-7499]. The frontier metric cannot
move from this rung — promotion is a human edit — so the rung is ranked by what
it adds to the product [rec: sleepy-hollow-9498]. Budget as the loop reports it:
27 iterations, 8.1 h elapsed, 39.9 h left; Claude five-hour **97%** (+68 this
run), seven-day 68%; Codex seven-day 79%. The five-hour window is a throttle
that resets many times inside 39.9 h, not a wall — but at 97% it is why units 1
and 2 both spend zero provider tokens and unit 3 is ranked last and dropped
rather than retried [rec: western-grotto-7499].

## Method

Read the source rather than the records for every claim above: `walk`'s parser
block (`__main__.py:386-478`), `_record_progress` and `_motion_cell`
(`__main__.py:1731-1800`), `motion_from_trace` (`walk.py:462`), the generated
preamble (`project_docs.py:264`), and `ot4-quill`'s own `script.py` params,
joint, actuator and reward blocks. Read `ot4-quill/PROGRESS.md` for the baseline
row's actual numbers. Confirmed the leg bound and its subtree fix landed
(`dbb198e3`, `ea725ca6`) and that neither record ran the walk, so unit 1 is
genuinely unspent [rec: honest-river-1137] [rec: tidy-cove-8382].

Rewrote `young-crane-9546` and `strong-birch-7412`, keeping their negative
knowledge verbatim and appending this bet to their provenance.

## Result

Unit 1 is settled by a walk that exits 0 with a row carrying both travel
channels and a `total_reward` delta against `runs/baseline`. It **falsifies this
bet's reading** if `travel_mm` moves toward 60 rather than staying near the 30 mm
setpoint, or if the reward expressions in the new bundle differ from the
baseline's — either would mean the "comparable iterate" analysis above is wrong
and unit 2 should be re-scoped around what actually varies.

Unit 2 is settled by a row that names its seed and an objective digest, with an
offline regression showing two runs differing only by seed produce different
seed fields and the **same** objective digest, and an `--set target_ext=...` run
producing a different one. It is falsified if the objective cannot be given a
stable digest from what the walk already exports — in which case the seed half
still stands alone and the objective half becomes a medium-rung question about
where task identity lives.

The noise floor moves to medium: the same project, same parameters, three
further seeds, and the spread of `total_reward` and `travel_mm` written down as
how to read a PROGRESS delta. It is deliberately **not** on short — it is worth
running once the row can distinguish its own four points, and worth little
before that.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot4
- commit: 3caf3886335663fbcb0b9bab4fe551b91f3fd4c6

## State Impact

- target: plan/young-crane-9546 — re-rank: unit 1 becomes --set stroke=60 (the one assignment that leaves ot4-quill's reward literals unchanged) and reports the delta without adjudicating it; unit 2 is the new direction, the walk row carrying its seed and an objective digest; the prompt-driven design turn stays last and drops first on refusal
- target: plan/strong-birch-7412 — fold the landed wall-clock leg bound (ADR-261 and its subtree fix) out of the rung as closed, and put the seed-spread noise floor in its place as the next gap in order
