---
node_id: fa4fb1fb-3b66-57f8-aa62-a2b4ca82e6d5
slug: cool-eagle-6400
title: The GUI-attached mode, leg by leg and pinned
created_at: '2026-09-08T22:29:38+00:00'
parents:
- terse-crane-6585
summary: ''
---
## What

The GUI-attached mode of the lifecycle walk is now documented **leg by leg**
and pinned to the code on both sides (ADR-269). `docs/CLI.md` §2 gains a
seven-row table: the six legs the walk spawns (`design`, `sweep`, `train`,
`script`, `declare`, `rollout`) and the review the walk runs in its own
engine session, each with its child command, the artifacts it lands at their
project-relative paths, and what an open Blender window changes about it.

Two tests in `cli/tests/test_project_docs.py` hold it: one parses the table's
leg column and asserts it equals the `run_leg("…")` names in
`cli/cadex_cli/__main__.py` **in order**, with the in-process review last and
`declare` the only row asking for a refresh; the other pins the four
`mesh_agent` facts the difference column rests on. `docs/DECISIONS.md`
(ADR-269) and a `docs/ROADMAP.md` bullet record it.

## Why

Charter criterion **"Three modes, one shape"** (`witty-spark-2613`), the
GUI-attached limb — the overseer's own next unit: derive the doc from the
actual shell/CLI paths rather than intent, name each of the walk's steps and
artifacts, say where a GUI-attached run differs, and pin it with a
consistency test so it is not prose alone.

ADR-201 had documented the mode as a paragraph: same commands, same store,
sequential by convention, refresh before the next edit. All true, and none of
it answers the question the criterion actually asks, which is per leg. A
reader could not tell from it whether the `train` leg or the review touched
the open window, and nothing failed if a seventh leg were added tomorrow.

## Method

Read the code, not the doc. The leg list came out of `__main__.py`'s
`run_leg` calls in source order; the artifact column out of each leg's own
`--out`/store paths and the walk's review block (`write_render`,
`write_section`, `write_inventory`, `write_clearance`, `review.json`, the
`PROGRESS.md` row, the project commit); the difference column out of
`session.py`'s `project_lock` (`flock`, per command, released before the row
and the commit) and `mesh_agent`'s `cadex_backend.py`, `cadexd_client.py`,
`history.py`, `backend.py` and `__init__.py`.

Then wrote the tests before believing the prose, which is what caught the
error: **the shell registers four application handlers, not two.** My first
draft said `load_post` and `save_post`; the pin failed with `save_pre` and
`frame_change_post` in the set. Reading them, `save_pre` records which
project holds the model before a Save-As renames the file and
`frame_change_post` tags the Cadex editors for redraw and writes no property
— so neither watches the project directory, the claim survives, and the
sentence was corrected to the real set. The test pins that exact set, so a
fifth handler has to be read against the claim before the line is widened.

The other three pins: no `mesh_agent` source names `flock` or
`.cadex-cli.lock` (the lock is the CLI's alone); neither `PROGRESS.md` nor
`DECISIONS.md` is named anywhere on that side (the three project documents
are the CLI's and a person's, so an in-app turn is not a substitute for the
`design` leg); and no `mesh_agent` source imports mujoco.

## Result

**The answer the table gives: a GUI-attached run differs nowhere in what the
walk writes.** It differs once in what the window may do *next* — after
`declare`'s digest edit a GUI edit against the pre-walk revision is refused
`STALE_PROGRAM_REVISION` and needs Rebuild Model or reopen (ADR-204) — and
once in what a turn costs, since the two windows resolve the turn model
separately (ADR-249's correction). Everything else is empty.

Evidence: `pixi run python -m pytest cli/tests` — **260 passed, 0 skipped, 3:49**. Docs and
tests only, in the LGPL CLI zone and `docs/`: no engine, protocol, payload or
`shell/` diff, and no source read from `shell/` was copied.

**Can "Three modes, one shape" be ticked? Not yet, and one thing remains,
which is not a document.** Headless is exercised twice on this machine;
remote is scripted, offline-tested and (since ADR-268) shape-complete; GUI is
now documented leg by leg and mechanically pinned. The criterion's own
wording asks the GUI mode to be documented *while the headless-only
constraint holds*, and by that reading it is met — but no GUI-attached walk
has ever been run, and this run's standing constraint forbids running one.
So: the one thing remaining is a human lifting the headless-only constraint
long enough for one GUI-attached walk to be executed. Until then the honest
state is `working`, not ticked, and the gap is a constraint rather than
missing work.

Dispatch closed: 1 unit — the GUI-attached mode documented leg by leg in
`docs/CLI.md` §2 and pinned by two consistency tests against `run_leg` and
four `mesh_agent` facts (ADR-269); the reading corrected the shell's handler
count from two to four.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot4
- commit: 464493860f616c2c3bb8bab333e822855895f35b

## State Impact

- target: witty-spark-2613 — the GUI-attached limb is now documented leg by leg (ADR-269): a seven-row table in docs/CLI.md §2 naming every run_leg leg plus the in-process review, its command, its artifacts and the difference an open window makes — nowhere in what the walk writes, once after declare's digest edit, once in model resolution. Two pins in cli/tests/test_project_docs.py hold the table's leg column equal to __main__.py's run_leg names in order and the four mesh_agent facts beneath it (no flock/.cadex-cli.lock, the exact four-handler set, no PROGRESS.md/DECISIONS.md, no mujoco import). The reading corrected the handler count from two to four. cli/tests 260 passed, 0 skipped. Still not claimed: any GUI-attached walk executed — that needs the headless-only constraint lifted, and is the one thing left before the criterion ticks.
- target: crisp-reef-5607 — the walk's leg list and per-leg artifacts are now stated in one table in docs/CLI.md §2 and pinned to the run_leg calls, so a new leg fails the doc rather than outdating it
