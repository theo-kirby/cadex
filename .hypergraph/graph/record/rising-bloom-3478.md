---
node_id: 2c2fcb14-bcaf-5cac-8c13-52b0eea229bc
slug: rising-bloom-3478
title: 'Critic fix: hollow-slope-2048''s machine-specific project path replaced by the portable name ot6-heron; receipt checks and graph check green; done claimed again under report_done'
created_at: '2026-09-14T05:35:23+00:00'
parents:
- hollow-slope-2048
summary: ''
---
## What

The critic's rejection of iteration 31 fixed: the record node `hollow-slope-2048` carried the operator's absolute project directory in its Method section (line 21), which the ot6 charter forbids committing. The line now names the project portably as `ot6-heron` "under the operator's cadex-projects directory". Nothing else in the node changed: the closing-report update it describes (commit `1ba64fd5`, `docs/probes/ot6/REPORT.md` §D10 recording the critic's `done_accepted` verdict) stands as written. Commit `9a203c24` on `ouroboros/ot6`, one file, one line. No product code, protocol, payload, engine, doc or dependency change. **Done is claimed again under `report_done`.**

## Why

The critic's message named exactly one defect and one remedy: replace the machine-specific path at `hollow-slope-2048.md:21` with `ot6-heron`, preserve the valid closing-report update, rerun the receipt checks and graph validation, claim done again, and start no lifecycle or new scope. This record does what was asked and nothing more. The charter's "never commit machine-specific absolute paths" rule is the standing constraint the fix serves; the frontier is otherwise fully evidenced (D1–D10), so the only correct unit is the fix-forward.

Editing a committed record node is unusual for an append-only graph; it is done here because the critic asked for it explicitly, because the edit removes a charter violation rather than rewriting history's meaning, and because the node's `node_id`, parents, timestamps, Repo and State Impact sections are untouched. The invariant checker accepts the edited node.

## Method

1. Read `.ouroboros/AGENTS.md`, `RUNS.md`, and the flagged node. Confirmed the only absolute path in it was the one at line 21.
2. Replaced that path with the project name; grepped `.hypergraph/graph` and `docs/probes/ot6` for home-directory absolute paths (Linux and macOS forms). **Pre-existing, not touched**: nine older records from ot4 and earlier (`dry-falcon-5463`, `chilly-basin-7378`, `candid-fern-3092`, `golden-dune-8756`, `steady-chart-0544`, `blue-quill-9477`, `lone-haven-0640`, `terse-crane-6585`) carry absolute paths committed and merged in earlier runs, before this charter's rule. Cleaning them is outside the critic's ask and outside this run; named here so nobody mistakes the fix for a sweep.
3. Receipt checks: `pixi run python -m pytest cli/tests/test_review_design.py -k "closing_report or ot6_evidence or spec_itself or receipt or caps"` — 121 passed, 9 deselected.
4. Graph validation: `hypergraph export` (511 record, 57 state, 4 plan nodes), then `hypergraph check --record .hypergraph/cache/record.json --state .hypergraph/cache/state.json` — 0 violations, 0 warnings. Note: `check` requires the explicit `--record`/`--state` cache paths; the bare form in AGENTS.md's Hypergraph block exits 2 with a usage error.
5. Operator dashboard verified at the unit's end, as the charter's standing rule asks: `cadex-operator-review` user unit active since 00:05 EDT today, serving `ot6-heron` on port 8765 at the operator's private address (read from the unit); `GET /` → 200; `GET /api/project` → project `ot6-heron`, accepted revision `0c8c64c92252711b`, three runs `heron1-checkpoint20`, `heron1`, `heron1-final`, all `ok`. Same state D9 and iteration 31 measured. Left running; nothing restarted.
6. Committed the fix alone (`9a203c24`).

## Result

The record graph contains no machine-specific path from this run; the closing report still records the critic's acceptance; every criterion D1–D10 has its evidence in a record; the operator dashboard serves the active project with its runs current. **This record claims done again under `report_done`**; with `on_done_accepted: 2`, one prior acceptance already stands (iteration 30), so this acceptance ends the run.

Concerns and assumptions: the unreconciled tail is now two nodes (`hollow-slope-2048` and this one); if the run continues, the next reconcile folds both. The nine pre-existing absolute paths in older records are a known, unfixed inconsistency with the current charter rule, deliberately left for an owner decision since they are merged history. No new dependency. No lifecycle repeated, no fourth mechanism, no long-term rung started.

Dispatch closed: 1 unit — critic's rejection fixed (absolute path in hollow-slope-2048 replaced by ot6-heron), checks green, dashboard verified, done claimed again.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot6
- commit: 9a203c24cadaae18ca45b2047aa72442ac32c94f

## State Impact

- target: chilly-road-8573 — the D10 record hollow-slope-2048 no longer carries a machine-specific absolute path (commit 9a203c24); its closing-report content is unchanged; done is claimed a second time under report_done after the critic's rejection was fixed
- target: round-sun-8398 — the run's records comply with the charter's no-absolute-paths rule; D1–D10 evidenced, dashboard serving ot6-heron with heron1-final at the run's end; done claimed again, the acceptance ends the run under on_done_accepted: 2
