---
node_id: abb136ef-a627-5e64-8694-c5546ef16d63
slug: sunny-fern-8059
title: 'Compare and record: the delta in the PROGRESS.md row and a git repository the project owns (ADR-194): §7c row 9 closes'
created_at: '2026-09-06T06:27:04+00:00'
parents:
- odd-fern-7024
summary: ''
---
## What

Row 9 of the lifecycle audit (`docs/MUJOCO.md` §7c, the last leg marked **missing**) closed: **compare and record, in a repository the project owns** (ADR-194). When the CLI writes a `PROGRESS.md` row, a number an earlier row also carried is written with its change against that row — `total_reward -293.4 (Δ -421.2 vs 2996fb73 at 127.8)`: the delta, the digest of the run compared against, and that run's value — so a comparison between two runs is one recorded row rather than two a reader lines up by eye. `total_reward` (the exported trace) and `reward/step` (the trainer's receipt) are compared, each against the last row that carried it, read back from the file as written; a row's own delta text is never read as a value. And the project root is its own git repository from the first visit: `ensure_project_repo` runs `git init` and writes a `.gitignore` (staged artifacts, frames, renders, the lock, `.blend1` backups out; script, history, assets, `.blend` and the three documents in), and `commit_project` commits after every accepted run with the row's words as the message, `--no-verify`, signing off, a fallback identity if the machine has none, `committed <sha>.` in the envelope's notes. A root inside somebody else's work tree is left alone with a note; no `git` on `PATH` is the same note and no history; neither fails a run. Documented in `docs/CLI.md` §2, `docs/MUJOCO.md` §7c row 9 and item 6, a ROADMAP tick, and ADR-194.

## Why

The goal's second priority: the iterate step's "comparison lands in the project's `PROGRESS.md` with the numbers" and "everything is committed in the project directory" were the two halves of row 9, the only §7c row still missing after ADR-193 on `calm-peak-5247`; the overseer's note for this iteration named row 9 and asked that the next real run land two comparison rows, not one. Assumptions made without a human: the parent for a comparison is the last row that carried the number (a loop iterates in order; a `--parent` flag is not taken); the row cannot carry its own commit hash, so the message carries the row instead; a project inside another work tree is that repository's and gets no `init` (the reversible choice); the `.blend` is committed by default because it is the document a shell user opens, while `frames/` (214 MB on the toy) and `script_artifacts/` (rebuildable) are ignored; ADR number 194.

## Method

Read `odd-fern-7024`, §7c, `project_docs.py`, `__main__.py` (`_engine_session`, `main`, `_record_progress`, `command_train`), the scratch project's layout and sizes, and the existing tests. Added to `project_docs.py`: `previous_numbers` (parses the table, first match per label per row), `_compared` and a `previous=` argument on `progress_numbers`; `ensure_project_repo`, `commit_project`, the `.gitignore` template, and the template wording for `PROGRESS.md` and the scaffold's ADR-001. Wired `ensure_project_repo` after the scaffold in `_engine_session` and `_commit_run` after `_record_progress` in `main()`; the housekeeping notes (`initialised`, `committed`, …) are excluded from the prompt row's outcome. Three new tests and the engine test extended (`cli/tests/test_project_docs.py`). Two things found by running: a read-only visit (`cadex script` with no `--set`) leaves `script.json` modified because opening a project re-stages the accepted attempt under a new id — the engine's, documented, the test allows it; and a delta that rounds to zero printed `-0.0`, fixed to take the sign from what is shown (`±0.0`). Real run on the ADR-192 scratch copy `/tmp/nt1-iter/proj` (never the live project): `cadex train --put` (2 it × 8 envs, seed 7) then a `sed` of the policy name and sha256 into a copy and `cadex script --set … --out`.

## Result

- Row 9 closes; every §7c row is now the agent's, the CLI's, or doc-only. The lifecycle frontier is item 5, the `INSPECTION_FAILED` frame, on the engine node.
- Real run, two rows and two commits: `cadex train` initialised the repository, trained in 4.6 s (20.9 s wall), stored `balance3.cxpolicy` (sha256 `36fb36f2…`) and landed `total_reward 127.8 (Δ -0.0 …), reward/step -0.9408` — the pre-training rollout of the incumbent, which is why the fix to `±0.0` followed; `cadex script --set` re-declaring it landed `| script | 506bfc86 | 68530963 | script --set switch9.py | total_reward -293.4 (Δ -421.2 vs 2996fb73 at 127.8) |` and commit `964a482` of exactly `PROGRESS.md`, `script.py`, `script.json` and the history entry. A fresh 2-iteration policy scores −293.4 against the ADR-192 warm one's 127.8 on the same task, and the row says so on its own.
- Gate for `cli/`: `pixi run python -m pytest cli/tests` **117 passed** in 83.8 s with the built engine and the training venv (114 before; the file alone 12 passed after the sign fix). No engine, shell or protocol change, so no other gate applies. Commit `87d3a9e4`.
- Noted, not chased: the `train` row carries the incumbent's `total_reward` because the dispatcher's rebuild exports the current policy's rollout — honest but easy to misread as the new policy's score, which only the re-declare row has; a project that predates the convention gets everything present as its first commit on its next visit; the commit message for `export` carries the caller's `--out` path.
- The unreconciled tail was two nodes on arrival; this makes it three, so the maintainer pass is due.

Dispatch closed: 1 unit — compare and record (ADR-194): the delta against the last row that carried the number, in the row; the project root git-inited on the first visit and committed after every accepted run; §7c row 9 closes.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/nt1
- commit: 87d3a9e4ac149fd93f8529abb2c99d157f94b95c

## State Impact

- target: calm-peak-5247 — §7c row 9 (compare and record) closes (ADR-194): a PROGRESS.md number an earlier row carried is written with its delta against that row (delta, that run's digest, that run's value; total_reward and reward/step, each against the last row that carried it), so the comparison is one recorded row; the project root is git-inited on the first visit with a CLI-written .gitignore (script_artifacts/, frames/, renders, the lock, .blend1 out) and every accepted run is one commit whose message is the row's words, committed <sha> in the envelope notes; a root inside another work tree or a machine without git gets a note and no history; measured on the ADR-192 scratch copy (train --put initialised and committed; script --set landed total_reward -293.4 (Δ -421.2 vs 2996fb73 at 127.8) and a commit of exactly the row, the script, its state and the history entry); every §7c row is now the agent's, the CLI's or doc-only, and the lifecycle frontier is item 5, the INSPECTION_FAILED frame, on the engine node
- target: chilly-union-8972 — the CLI records the comparison and commits the project (ADR-194): previous_numbers/progress_numbers(previous=) in cadex_cli/project_docs.py, ensure_project_repo after the scaffold in _engine_session, _commit_run after the PROGRESS.md row in main(); a read-only visit leaves the engine's re-staged script.json dirty until the next accepted run commits it (documented, docs/CLI.md §2); cli/tests 117 passed (114 before)
