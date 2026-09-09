---
node_id: ba028b28-0199-558a-ac18-9ea558afb472
slug: brisk-eagle-8550
title: The lifecycle walk detaches in two halves
created_at: '2026-09-09T05:54:36+00:00'
parents:
- dry-falcon-5463
summary: ''
---
## What

`cadex walk` now carries `--detach` through to the end, in two halves.

`cadex walk --remote --detach` runs the design turns and the iterate change
unchanged, spawns the train leg with `--detach` instead of `--put`, and stops at
the pending receipt. It writes `--out/walk-pending.json` (`cadex-walk-pending-v1`
— the dispatcher's locator, the exported bundle and its sha256, the seed the
launch used, the legs that ran, a `claims` line saying a launch was acknowledged
and nothing more, and the two commands that finish the run). It writes no
`review.json`, stores no asset, rewrites no script, rolls nothing out; its
`PROGRESS.md` row is ADR-278's `pending; no policy verified`, with no comparison
cell.

`cadex walk --complete --project P --out DIR` runs the second half from that
marker. One new leg, `collect`, puts the returned policy into the store through
`cadex asset --put` — the write the blocking `train --put` does inside its own
leg — and after it `declare`, `rollout` and the review are the legs that already
existed, unmodified. The walk's leg list carries the launch's legs forward from
the marker, so a completed detached walk reads as one run.

ADR-282, `docs/CLI.md` §2 (including the GUI-attached leg table's new `collect`
row), the ROADMAP line, and twelve new tests in `cli/tests/test_walk.py`.

## Why

Charter criterion **Three modes, one shape** (`witty-spark-2613`), whose own
words named this as the last opening: "`--detach` still does not travel through
the walk, and remains its own unit". It was the overseer's named next unit and
short plan item 1. ADR-278 made the detached *training leg* honest and stopped
there; `docs/CLI.md` said in its own words that `--detach` was "unavailable on
`walk`; automatic detached collection and walk continuation remain
unimplemented", which meant the one mode of the lifecycle walk that survives a
closed laptop was the one mode that could not be run end to end.

Assumption written here rather than asked: completion is a **second command**, not
a background watcher. The run's constraints forbid a live remote, ssh, GPU
dispatch and a scheduler, and a poller would be the least reversible of the
options — so the walk reaches a box only through `remote_train.sh`, exactly as
before, and `--complete` reads files that command already brought home.

## Method

Collection reads only what the dispatcher mirrors back: `training-progress.json`
for the run's state, `train.log`'s last JSON line for the trainer's own receipt
(the same object a blocking dispatch reads off the dispatcher's stdout, so every
later leg sees what it sees in the blocking mode), and the policy itself.
`train.py`'s `_last_json_line` became public `last_json_line`; `walk.py` gained
`task_bundle`, `write_pending`, `read_pending` and `collect_detached`.

The hazard of splitting a walk in time is declaring a policy that is not its own,
so four checks with six messages, each with its own remedy: state must be `done`
(a `running` run says watch it, a `failed` one quotes its error and names
`train.log`, a missing progress file says pull it); the policy must hash to the
receipt's `sha256`; the receipt's `task_sha256` must be this walk's bundle; and
that bundle must still hash to what the launch recorded. `--complete` refuses
`--prompt`, `--set`, `--remote`, `--allow-cpu` and `--detach` rather than
ignoring them.

The seed travels in the marker rather than being re-derived: the trainer's
receipt does not carry it and `--complete`'s own `--seed` is a default nobody
typed, so a comparison row naming the wrong seed would be worse than none.

Tests run both halves against the existing stand-in dispatcher (`FAKE_CADEX`,
taught `--detach` and an `asset --put` leg) and a local directory standing in for
the box's mirror. No ssh, no box, no `.remote.env`, no GUI, no engine build.

## Result

Landed as `00964ac8`, 719 insertions / 70 deletions across
`cli/cadex_cli/{__main__,walk,train}.py`, `cli/tests/test_walk.py`,
`docs/{CLI,DECISIONS,ROADMAP}.md`.

Gate, honestly: `pixi run python -m pytest cli/tests` — **301 passed, 0 failed**
(241 s), run after the code and the CLI.md leg-table row and before the ADR /
ROADMAP / CLI.md prose edits; `pytest cli/tests/test_project_docs.py
cli/tests/test_train.py` — **60 passed** — re-run after those doc edits, which
are the two suites that read the docs. The twelve new tests pin: the pending half
leaves script, store and review untouched and spawns `train` with `--detach` and
without `--put`; the completing half lands the same review, the same stored
policy and the same comparison block at the launch's seed, with the trainer's box
path kept as `trainer_out` and the local path as `out`; and the words of each of
the six refusals. Engine zone untouched, so no packaged gate was needed and none
was run.

Criterion advanced: **Three modes, one shape** (`witty-spark-2613`). What is
still missing before it can be ticked: nothing about `--detach`, but the
criterion also asks for the **GUI-attached** mode to be documented — the leg
table in `docs/CLI.md` §2 covers it and now carries `collect`, so a maintainer
folding this should judge whether the criterion is met or whether it wants the
handoff exercised, which this run's headless-only constraint forbids. The
detached path is documented and scripted, never executed against a live box, as
the constraints require.

Not done, deliberately: no polling, no scheduler, no live dispatch, no second
clearance engine. The unreconciled tail is now three records deep and the
completed-walk evidence from `chilly-basin-7378` is still unfolded — the
maintainer pass the overseer asked for is the next thing due.

Dispatch closed: 1 unit — `--detach` now travels through the walk in two halves, launch and completion, with six named refusals and no live remote.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot4
- commit: 00964ac84eb0fc4591ca5237af9f9e8c1bfa50cd

## State Impact

- target: witty-spark-2613 — --detach now travels through the walk: --remote --detach stops at a pending walk-pending.json marker (locator, bundle digest, launch seed, completion commands) declaring and storing nothing, and --complete collects the dispatcher-returned policy through a new asset --put 'collect' leg and runs the unchanged declare/rollout/review legs. Six named refusals guard a split-in-time walk (state not done, wrong policy bytes, foreign task digest, moved bundle). The remote handoff is now scripted and documented; never executed against a live box. ADR-282.
- target: chilly-union-8972 — cadex walk gains --detach and --complete; walk.py gains task_bundle/write_pending/read_pending/collect_detached, train.py's last_json_line is public, and the walk's leg set gains 'collect' (documented in the GUI leg table docs/CLI.md holds equal to run_leg order).
