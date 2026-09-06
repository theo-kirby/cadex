---
node_id: ef1a62d6-2886-5cb8-83dc-bc63ec1c95de
slug: odd-fern-7024
title: 'The project is a codebase: ARCHITECTURE/DECISIONS/PROGRESS scaffolded by the CLI, read on every turn, appended by convention (ADR-193): §7c row 10 closes'
created_at: '2026-09-06T06:18:32+00:00'
parents:
- keen-sail-4481
summary: ''
---
## What

Row 10 of the lifecycle audit (`docs/MUJOCO.md` §7c, frontier item 6's first half) closed: **the project is a codebase** (ADR-193). `cli/cadex_cli/project_docs.py` scaffolds `ARCHITECTURE.md`, `DECISIONS.md` and `PROGRESS.md` in the project root on the first visit — idempotent, never overwriting — from `_engine_session`, so every CLI command that opens a project creates them and the envelope's `notes` say so once. Every `cadex -p` turn gets the three pasted into its system prompt between the overlay and the engine's contract, bounded at 8 000 characters each (the head of the first two, the tail of the log). The CLI appends one `PROGRESS.md` row after every accepted run — time, command, accepted revision, digest, what was done, numbers — where the numbers are what the run produced and nothing inferred: the exported trace's `policy.total_reward`, the trainer's `reward_per_step`, wall time and sha256. A turn's closing lines that start `DECISION:` become numbered `## ADR-NNN` entries in `DECISIONS.md`; the scaffold's `ADR-001` is the project's creation. `docs/<subject>.md` (`gear-ratios`, `sensors`, `actuators`, `rejected`) is the documented domain-doc convention, linked from `ARCHITECTURE.md`. Documented in `docs/CLI.md` §2 (a table of the four and who writes each) and §4, `docs/MUJOCO.md` §7c row 10 and item 6, a ROADMAP tick, and ADR-193.

## Why

The goal's second priority names "treat each cadex project directory as its own codebase" and the done criterion "Project as codebase"; the overseer's note for this iteration named project-scaffold first. On `calm-peak-5247` rows 9 and 10 were the remaining **missing** legs after ADR-192 closed row 8, and item 5 (the `INSPECTION_FAILED` frame) is tracked on the engine node. Row 10 is the smaller and the more reversible of the two — files and a prompt section — and row 9 (compare and record, with the git repository) builds on it. Assumptions made without a human: the CLI's agent keeps having **no file tool** (its whole world is the engine, on purpose, `agent.py`), so "the agent reads them" is the CLI pasting them in and "the agent updates them" is a closing-line convention — the question policy says a doc convention before a new tool; the git repository is left for row 9 because what a project commits is a decision about the store's layout (frames, renders, the `.blend`) that deserves its own entry; ADR number 193 (nothing claims it); the shell mode needs no change because a shell-attached agent has file tools and edits the same files, which is what makes the two modes one shape.

## Method

Read the state node, the §7c table and item 6, `__main__.py` (`_engine_session`, `command_prompt`, `main`), `agent.py` (`--tools ""`, `system_prompt`), `session.py` (the `agent.json` precedent: a CLI-owned sibling of `script.json`), `report.py`, `export.py` (copied artifacts carry their staged basename, so the trace is found by name among the outputs' files), the mock backend and `test_turn_loop.py`. Wrote `project_docs.py`: templates, `scaffold_project_docs`, `read_project_docs` (bounded, head/tail), `append_progress_row` (one line, pipes escaped, short hashes, scaffolds first if missing), `trace_total_reward` and `progress_numbers`, `decision_lines` and `record_decisions` (numbered after the last `## ADR-` present). Wired: scaffold in `_engine_session` after `open_project`; `system_prompt(api, project_docs=...)`; `record_decisions` after the turn; `_record_progress` in `main()` after a command returns `EXIT_OK` with `report.ok`, skipping the script print and the store listing, never fatal. Added a "THE PROJECT IS A CODEBASE" paragraph to the overlay. Wrote nine tests in `cli/tests/test_project_docs.py`: seven pure (scaffold and never-overwrite, bounded read with the log's tail, empty read, the row's shape, numbers from a trace and a receipt, the `DECISION:` parser and numbering, the overlay and prompt section) and two against the engine (`script --set` then `params` land two rows and a print lands none; a scripted turn's prompt carries the project's `ARCHITECTURE.md` and its `DECISION:` lands as `ADR-002`). Two test bugs fixed on the first run (the envelope omits an empty `notes`; a decision with no sentence break kept its trailing period in the title). Ran one real command on the ADR-192 scratch copy of the §7b toy (`/tmp/nt1-iter/proj`, never the live project).

## Result

- Row 10 closes. Legs 1–8 and 10 of the walk are agent-driven or the CLI's; row 9 (compare and record, with the git repository the project owns) is the frontier, then item 5 on the engine node.
- Real run: `cadex export --project /tmp/nt1-iter/proj --out …` scaffolded the three (note in the envelope) and landed `| 2026-09-06T06:17:37Z | export | 4df77b13 | 2996fb73 | export → … | total_reward 127.8 |` — the ADR-192 iterate result, now a row a reader can compare against the parent's 1729.9 once that run is re-exported; row 9 is where the comparison becomes one recorded row rather than two.
- Gate for `cli/`: `pixi run python -m pytest cli/tests` **114 passed** in 76.7 s with the built engine and the training venv present, nothing skipped (105 before; the new file alone 9 passed). No engine, shell or protocol change, so no other gate applies. Commit `ea23f49d`.
- Noted, not chased: `read_project_docs` shows the agent the tail of `PROGRESS.md`, so a very long log loses its header in the prompt (the overlay restates what the file is); the prompt turn's row quotes the first non-scaffold note as the outcome, which is the model's own sentence; a project that predates the convention gets its docs on its next visit, with `ADR-001` dated that day rather than the project's real birth.
- The unreconciled tail was one node on arrival (`keen-sail-4481`); this makes it two.

Dispatch closed: 1 unit — the project is a codebase (ADR-193): the three documents scaffolded on first visit, pasted into every turn, one `PROGRESS.md` row per accepted run with the numbers, `DECISION:` lines as ADR entries; §7c row 10 closes.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/nt1
- commit: ea23f49dcfc3e43613d646ea8e7702869c072ecf

## State Impact

- target: calm-peak-5247 — §7c row 10 (project as a codebase) closes (ADR-193): cli/cadex_cli/project_docs.py scaffolds ARCHITECTURE.md, DECISIONS.md and PROGRESS.md on the first visit from _engine_session (idempotent, never overwriting, a note in the envelope once); every cadex -p turn gets the three pasted into its system prompt bounded at 8 000 characters each (head of the first two, tail of the log); the CLI appends one PROGRESS.md row per accepted run with time, command, revision, digest, what and the numbers the run produced (trace total_reward, trainer reward/step, wall time, sha256), no row for the script print or the store listing; a turn's closing DECISION: lines land as numbered DECISIONS.md entries; docs/<subject>.md is the domain-doc convention; the CLI agent still has no file tool by decision (a convention before a tool) and no git repository yet (row 9's work, because what a project commits is a store-layout decision); measured on the ADR-192 scratch copy (export scaffolded and landed a row with total_reward 127.8); frontier is now row 9 (compare and record with the git repository) then item 5 on the engine node
- target: chilly-union-8972 — the CLI scaffolds and maintains the project's three documents (ADR-193): cadex_cli/project_docs.py, a THE PROJECT IS A CODEBASE paragraph in the overlay, system_prompt(api, project_docs=...), a PROGRESS.md row after every accepted run in main(), DECISION: lines recorded after a turn; docs/CLI.md §2 carries the table of the four files and who writes each; cli/tests 114 passed (105 before)
