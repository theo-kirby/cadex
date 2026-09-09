---
node_id: 8dab78a6-0b85-5031-82a1-b6b798a26d95
slug: honest-river-1137
title: The walk bounds every leg in wall clock, subtree and all
created_at: '2026-09-08T19:21:43+00:00'
parents:
- hollow-cliff-1217
summary: ''
---
## What

`cadex walk` now bounds every leg in wall clock. `run_leg` takes a
`timeout`; `walk` takes `--leg-timeout SECONDS` (default 3600, `0` for no
limit) that applies to **all six** legs — design, sweep, train, script,
declare, rollout. A leg that runs out of time is stopped and comes back as
an ordinary failed leg (exit 124, reason in its envelope's `error`), so the
walk ends through the existing `failed(...)` path at `EXIT_FAILURE`. The
stop is a subtree kill: the leg runs in its own session and gets `SIGTERM`
then `SIGKILL` as a group, with `SIGINT`/`SIGTERM` to the walk relayed to it
so Ctrl-C still reaches the leg. `train_leg_timeout` gives the train leg
`max(--leg-timeout, --timeout + 300 s)`. The envelope carries
`walk.leg_timeout_s` and `walk.train_leg_timeout_s`.

ADR-261, a `docs/ROADMAP.md` bullet, and three edits to `docs/CLI.md` (the
command table, leg 3's flag list, and a new paragraph after the leg-failure
one) land in the same commit, because `--timeout`'s help and the doc both
read as though the walk were already bounded.

Zone: `cli/**` only (LGPL). No engine, no protocol, no `shell/` diff.

## Why

Charter criterion **"The walk exists and is tested headlessly"**
(`crisp-reef-5607`), and the premise under mission 9's fleet: the loop is
supposed to run with no human in it, and a team is supposed to run one
experiment per machine. It was the leading open unit on the plan's short
rung after the token-free iterate (`hollow-cliff-1217` unit 2), and the
source is worse than the plan's bet said: `run_leg` called
`subprocess.run` with **no `timeout=` at all**, and `walk --timeout` is
forwarded only into the train leg's argv, where it is the trainer's own
internal limit. A provider that stalls rather than refusing — or an ssh
that never returns — hung such a machine forever with nothing to notice.
The design turns measured on this run took 629.6 s and 1,014.2 s, so an
hour is ~3.5x the longest leg that has ever legitimately run.

The subtree kill is the part that is not optional: every leg spawns
something the walk does not control (`agent.py` uses `Popen` with no
timeout of its own), so killing the direct `cadex` child would leave the
process that was actually hanging alive, holding the project — and would
block draining the stdout the grandchild inherited.

**The overseer's message asked for a different unit** — a
clearance-and-intersection CLI call for the headless-review criterion,
"which no unit has touched". That is stale: `cli/cadex_cli/clearance.py`,
`cadex clearance`, `cli/tests/test_clearance.py` and the walk's own
`clearance` block already exist (ADR-237, ADR-238, ADR-248), the report
names offending pairs with catalog ids in the project's
`docs/clearance.md`, and `damp-moon-9297` reads *working* in STATE.md.
The third mechanism's walk found its first real offending pair with it
last iteration. It also asked for a reconcile pass; STATE.md's tail is one
node (the planner's own bet), below the charter's trigger of three, and a
work iteration may not reconcile. So the unit is the next open thing on
the plan instead, and this note is the assumption written down.

## Method

- Read the source rather than the record: `run_leg`
  (`cli/cadex_cli/walk.py`), `--timeout` (`__main__.py`, walk parser),
  `run_trainer` (`train.py`), `agent.py`'s `Popen`.
- `run_leg` moved from `subprocess.run` to `Popen(start_new_session=True)`
  + `communicate(timeout=...)`, with `_stop_leg` (group TERM, grace, group
  KILL), `_signal_leg` and `_relaying_signals`.
- `--leg-timeout` validated in `command_walk` (nonnegative, finite) and
  threaded into all six `run_leg` calls; the train leg through
  `train_leg_timeout`.
- Tests: a fake `cadex` that hangs **and** spawns a grandchild which hangs
  holding the captured pipe; the test polls the grandchild's pid until it
  is gone, so a direct-child kill fails it. Plus the `train_leg_timeout`
  table, the two envelope numbers on a walk that finished, and
  `--leg-timeout -1` added to the usage-error table.

## Result

`cli/tests/test_walk.py`: **42 passed in 132 s** including the real-engine
and real-trainer lifecycle walks. The new timeout test fails the walk in
well under its 60 s assertion against a fake that would otherwise sleep for
ten minutes, and the grandchild is reaped. Full `cli/tests`: **238 passed in 214 s**, exit 0, and the
offline half re-run after a cosmetic tidy (42 passed).

One caught mistake, fixed in the same working tree before commit: the
validation block first landed in `command_train`, which has no
`leg_timeout` attribute — the usage-error test caught it.

What is still missing before `crisp-reef-5607` can be ticked: nothing in
this unit; the walk already runs end to end on this machine on three
mechanisms. This closes the hazard that made an unattended walk unsafe to
leave alone, which is the fleet premise (mission 9) rather than the walk
criterion itself. `witty-spark-2613` (three modes) still needs the remote
handoff exercised or explicitly left scripted-not-executed.

Commit `dbb198e3`.

Dispatch closed: 1 unit — the walk's legs are bounded in wall clock, subtree and all (ADR-261).

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot4
- commit: dbb198e34e6a38881eae10cfed42d63071d6f5e4

## State Impact

- target: crisp-reef-5607 — the headless walk entry point is now bounded: every leg runs under --leg-timeout (default 3600 s, 0 for no limit), a leg that runs out of time fails the walk at exit 1 with the leg at 124, and the stop kills the leg's whole session so the agent CLI or trainer under it cannot outlive it (ADR-261). An unattended walk can no longer hang forever on a stalled provider.
