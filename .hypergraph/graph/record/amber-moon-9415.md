---
node_id: 5c7d80cb-e361-5b68-92fc-050d0367a53d
slug: amber-moon-9415
title: 'orun2 D3: CLI agent turns listed as runs beside the Ouroboros runs (ADR-519); restart flake and viewer race fixed'
created_at: '2026-10-04T01:24:40+00:00'
parents:
- quiet-ivy-3898
summary: ''
---
## What

orun2 D3's last item: the dashboard lists **CLI agent turns as runs**,
beside the Ouroboros runs (ADR-519, commit `21d130f5`). In the same unit I
fixed the CLI flake reported in #36 at its root cause, plus a second race
of the same kind that the gate run turned up.

- `GET /api/turns` (`cadex-agent-turns-v1`) and an **Agent turns** list
  inside the index's **Runs** card, under **Ouroboros**. Newest first, at
  most 100, and `count` gives the full total.
- Each row shows: the project (linked to `/p/<name>/`), when the turn ran,
  the revision it left and that revision's ordinal, the owner's latest
  verdict as a badge (`accepted` / `rejected` / `restored` /
  `unreviewed`), the prompt, the agent's first words, and the agent's notes
  on that revision with the count still unanswered.
- **No new store (A3).** A turn is a `prompt` row of the project's
  `PROGRESS.md`. The CLI already writes one per accepted turn, whether it
  came from a terminal or the dashboard. The row's revision prefix links it
  to `script_history/history.json` (ordinal) and `comments.jsonl` (verdicts
  and notes). `project_docs.progress_rows` is the single reader of that
  table.
- Fixed while doing it: when a turn delivered owner comments, its
  `PROGRESS.md` row recorded `delivered N comment(s) from the owner.` as
  the agent's words. `delivered ` is now a housekeeping prefix.
- **Flake #36 root cause:** in `test_review_lifecycle.py`, the fixture's
  four run records have second-resolution `recorded_at`, and ties are
  broken by run name. `second` was the default view only when all four
  were written within the same second. Under load, `sample` (written last)
  was newest. Reproduced with a 1.1 s sleep (fails) and fixed by stamping
  the order the test intends (passes with and without the sleep).
- **Second race, found by the first gate run:**
  `test_browser_attaches_an_image_to_a_turn…` failed with 30 mm instead of
  48 mm. `review.js` sets `state.model` when the manifest arrives and draws
  the meshes later. Four browser tests waited on `state().model.revision`
  and then measured the viewer. Each now also waits for the model status to
  settle (`_model_state`), as the turn test already did. No retry was
  added and no assertion was weakened.

## Why

The critic's message named this unit: D3's last item, CLI agent turns as
runs, read-only from the existing turn store with a browser test against a
real engine, an ADR and a record, plus the #36 flake's root cause with no
retry. I did all of it. The one deviation: there is no stored transcript
to read. The CLI keeps none, a dashboard turn's transcript lives only in
memory by design, and the charter bars committing full transcripts. So the
turn store is the `PROGRESS.md` row joined with the revision trail and
`comments.jsonl`. The ADR records that choice and the alternatives it
rejected: a store of its own, project git log, transcripts.

## Method

- Read `default_run` and `read_project_review`'s sort to find the flake's
  cause, then reproduced it with a sleep before fixing it.
- Built the reader in `review_server.agent_turns`, added
  `ProjectsDirectory.turns`, the `/api/turns` route and the list in
  `projects.js`. Ties on second-resolution timestamps fall to the later row.
- Tests: `cli/tests/test_agent_turns.py`.
  - No engine: rows hand-laid with an escaped pipe, a params row in
    between and a turn with no revision, joined to the trail, verdicts and
    answered/unanswered notes, with nothing written. `/api/turns` across two
    projects is newest first and bounded at 100 with the count.
  - Headless Chromium against a **real engine** and the real bridge, with
    only the model faked (`fake_claude.py`): two `cadex -p` turns, then
    `revision accept` on the first and `revision reject --note` on the
    second. Both appear on the already-open index without a click, newest
    first, with the revision each left, its ordinal (#2), its verdict, and
    the second turn's unanswered agent note. They sit in the same card as
    the Ouroboros runs.
- Docs: `docs/DASHBOARD.md` §29, `docs/CLI.md` (`cadex app` row), ADR-519.

## Result

- **D3 now has evidence for all six items.** CLI agent turns are listed as
  runs, browser-tested against a real engine. The owner ticks the box.
- **Gates at `21d130f5`**, both suites run concurrently:
  - `pixi run test-engine`: 2594 passed, 56 skipped.
  - `pixi run python -m pytest cli/tests` (GPU hidden): 1398 passed,
    1 skipped (`CADEX_REVIEW_HOST`), 0 failed.
- The first gate run, before the second race was fixed, had 1 failure:
  the image-turn viewer race described above, now fixed.
- No engine, protocol or payload change, so no build and no packaged gate.
- **Limits:**
  - A turn's prompt and the agent's words are split on the first ` → `,
    so a prompt that itself contains ` → ` is split early.
  - Cross-project ties within one second have no defined order.
  - Turns the CLI did not accept wrote no row, so they are not listed.
- **Next:** the critic's order, starting R1 with the AGENTS.md rewrite to
  216 lines or fewer.
- The unreconciled tail is 1 record (this one).

Dispatch closed: 1 unit — CLI agent turns listed as runs beside the Ouroboros runs (ADR-519), closing D3's last item, with the #36 restart flake and a viewer-settle race fixed at their root causes

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/orun2
- commit: 21d130f5b0118513682d8bad9bfd16c3a942d269

## State Impact

- target: swift-nest-0229 — CLI agent turns as runs: evidenced — /api/turns and an Agent turns list beside the Ouroboros runs, read from each project's PROGRESS.md prompt rows joined to script_history and comments.jsonl verdicts/notes, no new store; browser-tested against a real engine (ADR-519, commit 21d130f5); all six D3 items now evidenced, owner to tick
- target: shady-clover-5534 — both suites green at 21d130f5 (engine 2594 passed/56 skipped; CLI 1398 passed/1 skipped, GPU hidden); the dashboard-restart flake (fixture recorded_at ties) and a viewer-settle race in four dashboard-write browser tests fixed in test logic, no retry
