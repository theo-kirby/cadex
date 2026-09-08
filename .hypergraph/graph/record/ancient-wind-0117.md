---
node_id: f03137b1-6df2-5039-9ef0-c239551de7f1
slug: ancient-wind-0117
title: Carry the design leg's reason into the walk's refusal envelope
created_at: '2026-09-07T21:15:21+00:00'
parents:
- cool-fountain-2483
summary: ''
---
## What

`cadex -p`'s refusal envelope now carries the *reason* a turn ended with no
accepted script, and `cadex walk` gets it for free.

The `accepted is None` branch in `cli/cadex_cli/__main__.py` wrote one
sentence — "the turn finished without the engine accepting a script" — and
dropped everything the parent knew. It now writes, in one line: the last tool
call the engine refused (op, failure code, clipped message) or, when nothing
was refused, `the engine refused nothing` with the ops the agent did call and
`never offered a script`; and in both cases the agent's own closing words.
Both clipped to 400 characters (`REASON_CHARS`) so a walk's `error` line stays
one readable paragraph. `docs/CLI.md` §2's walk-failure paragraph says what a
design leg at exit 3 now reports. Commit `dca63b13`.

## Why

Plan rank 2 of the short rung (`glad-snow-3838`), reaffirmed by the overseer,
serving mission 2 and the frontier node **`crisp-reef-5607` — the walk exists
and is tested headlessly**. `misty-rain-9048` measured the failure this
answers: inside `cadex walk --prompt` the design turn ended after 3.76 s with
one `describe_api` call and that bare sentence, while the same argv run
directly succeeded in 214 s. The envelope said the same thing for a refused
script and for a script never offered, so the record could not name a cause
and a later retry policy would have nothing to branch on.

Assumption written down, per the plan's "not authorized" list: no automatic
retry, no change to leg order, no `OP_ARG_SPECS` change, and no widening of
`declare_policy`. This unit only makes the existing refusal legible.

## Method

- Read the `accepted is None` branch and `bridge.state.calls`: the parent
  already records every tool call with `ok`, `failure_code` and a summary, so
  no new plumbing was needed — only a helper that reads them.
- Added `_rejection_reason(text, calls)` plus `_clip`/`REASON_CHARS` beside
  `_refresh_script_state`, and wired the branch to it. `bridge.state` outlives
  the `with Bridge(...)` block, so the calls are readable where the branch is.
- No `walk.py` change: `run_leg` already copies a child envelope's `error`
  into the leg, and `command_walk` already interpolates it into the walk's own
  `error`, which `test_walk.py` pins.
- Three tests in `cli/tests/test_turn_loop.py`, all with a stubbed turn
  (`mock_backend`) against the real bridge socket and the real engine: the
  refused-script branch names `write_script` and the closing words; a new
  `describe_api`-only turn names "the engine refused nothing", the op it did
  call and "never offered a script"; and a direct call with no calls and no
  text still reads distinguishably.
- Zone gate: `JAX_PLATFORMS=cpu pixi run python -m pytest cli/tests`.

## Result

**142 passed in 126.93 s, no skips** — the engine is built here, so the
engine-needing half of the suite really ran (it was 140 before; three added,
one rewritten in place). `docs/CLI.md` updated in the same commit, its
`Verified against source:` date already today.

Charter criterion advanced: **the walk exists and is tested headlessly**
(`crisp-reef-5607`). What is still missing before it can be ticked, and I am
not ticking it: the clean prompt-to-review run recorded in `cool-fountain-2483`
is a single run: there is no evidence yet that the design leg is *reliably*
clean, and this unit deliberately adds no retry — it only makes the next
failure nameable. The reliability evidence a tick needs is at least one more
independent `--prompt` walk, and the frontier's other legs (`witty-spark-2613`
three modes, `swift-dusk-2951` second mechanism) are untouched by this unit.

The unreconciled tail is three record nodes after this one, which is the
declared reconcile threshold; the maintainer pass is next, then the planner.

Dispatch closed: 1 unit — the design leg's refusal now names its cause (last
engine refusal or "refused nothing" plus the agent's closing words), pinned by
three stubbed-turn tests, whole CLI suite green at 142.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/nt3
- commit: dca63b13cbf17d2581358e45f5f6e01579da8caf

## State Impact

- target: crisp-reef-5607 — a cadex -p turn that ends with no accepted script now reports why: the last engine refusal (op, failure code, message) or 'the engine refused nothing' with the ops the agent did call, plus the agent's closing words, both clipped to 400 chars; cadex walk copies a failed leg's envelope error verbatim, so a design leg at exit 3 names its cause in the walk envelope with no walk.py change (commit dca63b13, 142 CLI tests passed, no skips). The criterion stays open: one clean prompt-to-review run is not reliability evidence, and this unit adds no retry.
