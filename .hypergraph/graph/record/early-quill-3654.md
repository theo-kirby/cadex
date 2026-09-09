---
node_id: d3ac43e4-5c30-5f77-b6fd-8873e9053660
slug: early-quill-3654
title: 'Three modes currency audit: remote holds, the GUI mode''s model claim did not'
created_at: '2026-09-08T14:37:18+00:00'
parents:
- rare-cliff-9595
summary: ''
---
## What

The three-modes currency audit the plan's short unit 3 asked for, and the one
stale claim it found, fixed. `docs/CLI.md` §2's GUI-attached paragraph gains a
bullet saying that the two windows resolve the turn model separately; the
`DEFAULT_MODEL` comment in `cli/cadex_cli/agent.py` stops claiming one answer
for both front ends; ADR-249 and ADR-201 each carry a dated correction /
currency paragraph; the ROADMAP's ADR-249 bullet says what was wrong. Two test
pins in `cli/tests/test_project_docs.py` — the sentences in the doc, and the
underlying facts in `shell/scripts/startup/mesh_agent/`, so a shell that later
learns `$CADEX_MODEL` fails the doc rather than quietly outdating it.

Audited and found current, so deliberately not touched: ADR-200's remote
handoff in full, and the rest of ADR-201.

## Why

Charter criterion **Three modes, one shape** (`witty-spark-2613`), mission item
2. The reconcile judgement on that node said the missing piece was one clean
headless walk on this machine, which `wandering-jasper-6102` landed, and that
ADR-200 and ADR-201 "all still hold as written". The plan's unit was to check
that they still hold *after* ADR-249 (`$CADEX_MODEL`) and ADR-250 (the worker's
`OPENBLAS_NUM_THREADS=4` pin and the SIGXCPU mapping) landed on the same day —
explicitly not to re-script or re-document either mode, which would be
re-running a landed qualification.

The overseer asked for a maintainer pass first. A work iteration is forbidden
from reconciling; the tail is three nodes and this makes it four, so the next
maintainer dispatch has `glad-mesa-6299`, `rare-cliff-9595`, the plan node and
this one to fold — including the second-mechanism impact on `swift-dusk-2951`,
which is still pending a decision.

## Method

Read, not run — the modes' evidence is source by charter, and no GUI was
launched and nothing was dispatched.

- ADR-200, ADR-201 and their follow-ups; ADR-249 and ADR-250; `docs/CLI.md`
  §2 (the shared-mode-artifact table, the remote paragraph and its five
  bullets, the GUI paragraph and its five bullets); `training/SETUP.md`,
  `training/remote_train.sh`, `training/README.md`.
- `cli/cadex_cli/agent.py` (`default_model`, `MODEL_ENV`, `DEFAULT_MODEL`),
  `cli/cadex_cli/__main__.py`'s two argparse defaults.
- `shell/scripts/startup/mesh_agent/agent.py`, `prefs.py`, `backend.py`,
  `harness.py`, and a `CADEX_MODEL` grep over the whole tree.
- `git log -L` on the shell's `DEFAULT_MODEL` to date the divergence.

**Remote (ADR-200) is current.** `--remote` moves only the trainer. The box
runs no engine and no model turn, so ADR-249 cannot reach it; `remote_train.sh`
and `training/SETUP.md` name neither a model nor a thread count. ADR-250 is
engine-local (`CadexScriptedRuntime.worker_environment`), and the engine legs
are local in all three modes — so the pin makes the modes *more* alike across
hosts, not less. Nothing to fix.

**GUI (ADR-201) was stale in one place.** Its bullet calls `cadex -p` "the one
leg that can be done in either window" and says nothing about which model each
window spends. They differ: the CLI resolves `--model`, then `$CADEX_MODEL`,
then `claude-fable-5`; the shell resolves a Blender preference whose default is
`DEFAULT_MODEL = ""` — whichever model the agent CLI itself defaults to — and
**nothing under `shell/` names `CADEX_MODEL`**. So a box that names its model
once names it for the terminal legs only, and the credit refusal that motivated
ADR-249 still refuses the in-app turn while the walk beside it runs.

The claim was already false before ADR-249: the shell's default became `""` in
c99e6e60 ("Fix harness accounts, login and discovered model selectors"). ADR-249
repeated it, and so did the source comment it was written from. The code wins.

Reversible option per the question policy: **document the divergence** rather
than make the shell read the variable. Teaching `shell/` a new environment
variable is a `shell/` behaviour change with its own gate and its own unit, and
the preference already exists for a person who wants the two to match.

## Result

`pixi run python -m pytest cli/tests` — **218 passed, 0 skipped, 226.70 s**
(217 before this unit; the added test is
`test_the_gui_mode_doc_is_still_true_about_which_window_names_the_model`).
LGPL CLI zone and docs only: no engine, protocol, payload or `shell/` diff, so
`cli/tests` is the gate AGENTS.md asks for. Commit `07501464`, five files,
+91/−4. The new pin reads two facts out of `mesh_agent` and copies no line of
it, which the one-way LGPL/GPL boundary permits.

Toward `witty-spark-2613`: the criterion's three modes are now each backed by a
document that matches the source as of today, and the one divergence between
them is named where a person running the walk will meet it. **Still missing
before it can be ticked**, and none of it is this unit's to take: the GUI mode
is documented and not exercised, and the remote mode is scripted and not
dispatched — both by this run's standing constraints, so the criterion closes
on the strength of the documents plus the local artifact-parity test
(`cli/tests/test_walk.py`, a stand-in dispatcher), or it waits for the human to
lift a constraint. A maintainer pass is what decides that, not this iteration.

The unreconciled tail is four nodes and includes the second-mechanism impact
that has not been folded yet.

Dispatch closed: 1 unit — the three-modes currency audit; remote current, the GUI mode's turn-model claim corrected in doc, comment, two ADRs and two test pins.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot4
- commit: 07501464650bcf1635d2d080913eaec3eee968ac

## State Impact

- target: witty-spark-2613 — ADR-200's remote handoff re-read against ADR-249 and ADR-250 and found current (the box runs no engine and no turn); ADR-201's GUI-attached document corrected where it was not: $CADEX_MODEL reaches the terminal's cadex -p and not the in-app agent, whose DEFAULT_MODEL is "" and which names no environment variable. docs/CLI.md §2, the DEFAULT_MODEL comment, dated paragraphs under ADR-249 and ADR-201, ROADMAP, and two pins in cli/tests/test_project_docs.py. cli/tests 218 passed / 0 skipped. Neither mode was re-scripted or re-documented; both remain documented-only by the run's constraints.
