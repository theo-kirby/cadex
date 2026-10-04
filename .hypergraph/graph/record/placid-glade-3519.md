---
node_id: 50e4e8ac-7b23-5453-a2d6-5d76e3ad9a76
slug: placid-glade-3519
title: 'Ouroboros run: orun2 [0b9b3c89] — operator directive'
created_at: '2026-10-03T22:54:12+00:00'
parents:
- chilly-reef-3115
summary: ''
---
## What

Operator directive: an Ouroboros loop starts on this repo. Every work node of the run descends from this node.

This directive supersedes `chilly-reef-3115`: the operator edited the charter; this version applies at a run start or iteration boundary.

## Why

The charter (the operator's goal document), verbatim:

# Goal: Cadex is three things — the engine, the dashboard, the agent

Verified against source: 2026-10-03. Operator charter for orun2, following
orun1 (`.ouroboros/history/orun1.md`). The human owns this file; unattended
roles never edit it. The base-plus-styles design charter that was drafted
under this name was shelved, unlaunched, for this run; it runs next, on the
product this one leaves behind.

## Mission

The owner uses Cadex almost entirely through autonomous CLI runs. The
Blender shell is 19,000 tracked files, a second toolchain, a GPL half, and
a 1.3 GB library checkout, and it is the part of Cadex the owner uses least.
This run is a bet on autonomy. **Cadex becomes three things and nothing
else:**

1. **The engine** builds, verifies, measures, renders, simulates and exports
   a design from its script. It is unchanged in role. It loses only what
   existed for the shell.
2. **The dashboard** is how a person sees results and steps in when needed.
   It grows from today's review page (`cli/cadex_cli/review_server.py` and
   `review_static/`), takes in the parts of the Blender UX that serve
   *looking, reviewing and light steering*, and becomes the only UI.
   A desktop app may later be built from scratch to copy it. That is not
   this run.
3. **The agent** is how Claude Code works with the engine and the dashboard:
   - one tool surface;
   - one guidance source;
   - one path for the agent to show the owner something or ask for
     something, without ever stopping to wait for an answer.

Preserve every idea, theme and capability that is not purely about the
Blender UI. Anything removed is recorded and justified. This run is also the
moment to reset the contract: the docs, the agent entry point and the state
graph should describe this three-part product as if it had always been the
plan.

If the run achieves only one thing, it is this: **`shell/` is deleted,
both suites and the packaged gate are green, and a person can watch an
autonomous design turn from a browser and steer it.**

Priority, in order: S1 (delete), R1 (contract), D1–D3 (dashboard), A1
(agent), W1 (nothing lost), C1 (report).

Before launch, the operator tags `main` as `v1-blender-shell`. The old
application is always one checkout away, so nothing here needs to be kept
"just in case".

## Owner-revisable assumptions

Until this section changes, the run works to these defaults:
- **A1. Port what serves looking and light steering. Drop hands-on
  modelling UI.**
  - **Port** (or confirm the dashboard already covers):
    - the model viewer;
    - parameter sliders;
    - accept, reject and restore a revision;
    - `look`/render views, section and exploded views, and the collision
      overlay;
    - simulation and rollout playback in the viewer;
    - training curves and evaluation films;
    - drawings and concept sheets, as rendered outputs;
    - exports;
    - the turn transcript;
    - attaching an image to a prompt;
    - printable-part and appearance-role display.
  - **Drop:**
    - the cage ring-drag;
    - the wiring editor UI;
    - the interactive blueprint *editor* (drawings stay as outputs);
    - Blender playback baking;
    - the landing page, top bar and window chrome;
    - the Blender-side transcript store.
  - **Picking survives in a review form:** click a part in the viewer to
    attach a comment to it.
- **A2. The dashboard stays light:**
  - a standard-library Python server;
  - vanilla JS and the vendored three.js;
  - no npm, no bundler, no build step, no front-end framework;
  - no new Python dependency unless an ADR measures its weight.
- **A3. The project directory is the truth:**
  - The dashboard reads it.
  - The dashboard writes only through the same code paths the CLI uses
    (params, prompt turns, accept/restore, comments). There is never a
    second write path.
  - Live rebuilds may hold a warm `cadexd` per open project.
- **A4. Claude Code is the only harness.** Codex and pi support goes with
  the shell.

## Owner notes

Answers to the parity ledger's "owner to confirm" rows, given on 2026-10-03
during the run. They settle those rows, and the ledger's text and its ADRs
should say so.

- **The live policy session is dropped.** That covers `cadex_live.py`, the
  Live editor and pushing a running policy. Reviewing a policy means
  rollout playback plus `evaluate`'s disturbance tests.
- **The blueprint composer is kept, as a headless engine-side tool.**
  - The agent can still compose dimensioned multi-view drawing sheets
    (views, callouts, dimensions, title block). The shell's `make_blueprint`,
    `save_blueprint` and `cadex_sheet.py` did this.
  - Re-derive it under `cli/` or the engine. **Copy nothing from
    `shell/`.** Read it as reference only, and do so before the shell
    delete commit.
  - Drawings are versioned with the project. The dashboard shows them as
    outputs.
  - It counts as a "ported" ledger row under W1, so it needs a test.
  - Schedule it after D2's write paths, not before.
- **`collision_view`'s agent half is kept.** The agent gets the contact
  report at t=0 (which parts touch at rest) without a person looking. Fold
  it into `inspect` or a tool and pin it with tests. The tool-surface rule
  in AGENTS.md applies.
- **The demo biped is dropped**, as ADR-498 already did. Nothing is
  restored.
- **Agent timeout and memory budgets move to the project.** They are
  stored in the project config (for example `agent.json`), with CLI flags
  that override them per call. The dashboard shows them read-only. Tests
  pin both the stored values and the overrides.
- **Next, before more D3 work (added 2026-10-03, iteration 32):** D2 is
  complete. Land the blueprint composer and the project budgets above
  next, each as its own unit with an ADR, tests and a record, then resume
  D3. `shell/` is already deleted, so read the old composer from the tag
  `v1-blender-shell` (`git show v1-blender-shell:shell/scripts/startup/mesh_agent/cadex_sheet.py`). It is
  reference only, and copying from it is still barred.

## Done criteria

Each criterion needs a causally parented record with measured evidence.
The human owns the checkboxes. Roles report results and do not tick them.

- [ ] **S1. The shell is gone and nothing reaches for it.**
  - `git ls-files shell | wc -l` is 0.
  - No pixi task, `package/` script, CMake rule, test, `.gitattributes`
    LFS rule or live doc refers to `shell/`, `mesh_agent`, a `.blend`, or
    `CADEX_BLENDER_EXECUTABLE`. ADRs and `docs/history/` are the exception.
  - The removal follows the two-commit protocol: a disable commit, then a
    delete commit, each green.
  - The licensing posture is restated without the GPL half:
    - `test_licensing_compliance.py`, `docs/inherited-modifications.json`
      and `docs/PROVENANCE.md` say what is now true;
    - an ADR records that the repo no longer carries GPL code, if that is
      what the audit finds.
  - **`mesh.blender` is retired**, with an ADR naming every project and
    example that used it:
    - the op, its runner, worker and adapters, `examples/blender_enclosure.py`,
      its tests and `docs/BLENDER-RECIPES.md` are all removed;
    - `OP_ARG_SPECS` and `docs/INTEGRATION.md` change in the same commit.
  - Codex and pi support is removed.
  - Shell-only tests are gone. Tests that only *mention* the shell are
    rewritten:
    - purity guardrails;
    - `rollout_bake_integration.py`;
    - `test_project_docs.py`.
- [ ] **R1. The contract describes the three-part product.**
  - Rewrite these for engine + dashboard + agent:
    - `docs/VISION.md`: the interface section, and the non-goals that named
      the Rust shell;
    - `AGENTS.md`, at **no more than half its current 432 lines**;
    - `README.md`, `docs/ARCHITECTURE.md`, `docs/INTEGRATION.md`;
    - `docs/ROADMAP.md`:
      - Phase 12 is superseded by "a desktop app that copies the
        dashboard";
      - Phase 13b's shell half is closed;
      - Phase 6 is marked historical.
  - One direction-change ADR states the bet, what it costs, and what would
    make the owner reverse it.
  - `docs/BLENDER.md`, `docs/BLENDER-TREE.md` and `docs/BLENDER-RECIPES.md`
    move to `docs/history/`.
  - A new `docs/DASHBOARD.md` replaces `docs/REVIEW-DESIGN.md` as the UI
    spec. It keeps that document's palette, type scale and dark-floor rules.
  - **The state graph's frontier lists only live work.** Every stale open
    criterion is superseded through a record that gives its reason:
    - ot7: F4–F7, F10;
    - ot10: A5, A7;
    - orun1: C1;
    - anything else the shell made moot.

    `STATE.md` regenerates clean, and `hypergraph check` exits 0.
- [ ] **D1. One command from a clone to a running dashboard.**
  - On a fresh clone on linux (sb1x), a documented, short command sequence
    builds the engine and serves the dashboard over a projects directory:
    - for example `pixi run setup-engine && pixi run app`;
    - `./cadex` with no project should open or serve the dashboard.
  - No step needs git-lfs, Xcode or `shell/lib`.
  - **Measured before and after:**
    - tracked files;
    - working-tree size;
    - Python and JS LOC by tree;
    - the number of setup steps;
    - wall time from clone to the dashboard's first page;
    - installed footprint.
- [ ] **D2. From a browser alone, a person can watch and steer a design.**
  - Each of the following is proven by a test driven through the existing
    headless Chromium path (`cli/cadex_cli/browser.py`) against a real
    engine:
    1. **Start a turn.** Start a design turn from a prompt, optionally with
       an attached image. Watch it live as the transcript streams and the
       renders and model update as revisions are accepted.
    2. **Move a slider.** Move a parameter slider and see the rebuilt model.
       Report p50 and p95 latency on a warm project beside the raw-NDJSON
       bar (`cadexd_latency_integration.py`).
    3. **Leave a comment.** Comment on the whole design or on a picked
       part. The next agent turn receives it.
    4. **Manage revisions.** Accept, reject and restore a revision.
    5. **Inspect.** Use the section, exploded and collision views, and play
       a rollout in the viewer.
    6. **Export.** Export STEP and STL, and download a concept sheet.
  - Write endpoints are safe by default:
    - the server binds 127.0.0.1;
    - writes need a per-launch token or a same-origin check;
    - remote viewing is documented as `tailscale serve` in front of it.
- [ ] **D3. Autonomous runs are first-class in the dashboard.**
  - The dashboard lists runs beside projects:
    - CLI agent turns;
    - Ouroboros runs (read-only from `.ouroboros/runs/<run>/` and the run
      branch).
  - Each run shows:
    - its iterations and critic verdicts;
    - the charter criteria;
    - the artifacts its records point to (renders, reports, probe pages).
  - orun1's review material (`docs/probes/orun1/`) renders in the dashboard
    from the repo alone. It replaces what `~/orun1-review/build.py` built
    by hand, which proves the per-run review pages are no longer needed.
- [ ] **A1. The agent has one contract, and a way to reach the owner
  without waiting.**
  - The product agent's tools (`cli/cadex_cli/tools.py`, pinned by
    `test_project_tool_surface.py`) and its guidance
    (`CadexAgentGuidance.md` plus `agent.system_prompt`) are the single
    source. Nothing that was only in the shell's `modes.py` is lost:
    - re-derive anything worth keeping, because the shell's code is GPL
      and must not be copied;
    - record what was not kept.
  - **The agent gains a non-blocking channel to the dashboard:**
    - it can flag a revision or artifact for the owner's review, or post a
      question;
    - the dashboard shows these;
    - the owner's answers and comments arrive in the agent's next turn;
    - the agent never stops to wait for an answer.
  - Tests pin the channel at the protocol or tool surface. Changing the
    surface follows AGENTS.md's tool-surface rule.
- [ ] **W1. Nothing the product could do headlessly was lost.**
  - On a copy of an existing robot project, the whole walk runs and every
    step is visible in the dashboard:
    1. prompt;
    2. accepted design;
    3. params sweep;
    4. `look` and render;
    5. STEP/STL export;
    6. MJCF export;
    7. a short training run on the 5090;
    8. `evaluate`.
  - Both full suites pass, and so does the packaged lifecycle gate.
  - The CLI and dashboard have no feature the shell parity ledger below
    marks "ported" without a test.
  - **The parity ledger is complete:** `docs/SHELL-PARITY.md` gives each
    of these one row:
    - every `mesh_agent` module;
    - each of its 23 tools;
    - each of the seven Cadex editors.

    Each row says one of three things: **ported** (where, and the test),
    **already covered** (where), or **dropped** (why, and the ADR). No
    row is blank.
- [ ] **C1. Closing report.**
  - `docs/probes/orun2/REPORT.md` covers:
    - D1's before and after numbers;
    - the parity ledger summary;
    - every removal and its ADR;
    - D2's latencies;
    - screenshots of the dashboard (PNG, ≤300 KB each, on the dark
      floor);
    - the remaining defects.
  - Reconcile, then claim done for critic review without ticking the owner
    boxes.

## Horizon ladder

- **short-term:**
  1. Measure the "before" numbers for D1 and write the parity ledger
     skeleton. Read every `mesh_agent` module once, so that nothing is
     deleted unread.
  2. The disable commit for `shell/`: pixi tasks, package scripts and
     tests stop reaching it, and both suites stay green.
  3. Retire `mesh.blender` and the Codex/pi backends (S1), each with its
     ADR.
- **medium-term:**
  1. The delete commit for `shell/`, with the licensing restatement.
  2. The dashboard's write paths:
     - params;
     - prompt turns with live transcript streaming;
     - comments and part-picks;
     - accept, reject and restore;

     then the inspection views and rollout playback (D2).
  3. The agent channel (A1) and runs as first-class (D3), with orun1's
     probes as the fixture.
  4. The contract rewrite (R1): docs, AGENTS.md, ROADMAP, and pruning the
     state-graph frontier.
- **long-term:**
  1. W1's full walk, then the closing report (C1).
  2. The dashboard's design pass against `docs/DASHBOARD.md`: hierarchy,
     the dark palette shared with renders, and phone-width review. This is
     a direction, not a bar.
  3. Further subtraction now the shell is gone: anything in `src/Mod/cadex`,
     `cli/` or `package/` that existed only to serve it, such as the
     shell-only bridge answers and payload staging into a bundle. Every
     removal gets an ADR.
  4. Keep every gate green and every doc true. Keep `STATE.md` reconciled.

## Constraints

**Standing:**
- Obey AGENTS.md, the licensing rules and the process boundaries. `cli/` is
  LGPL: **copy nothing from `shell/`**. Read it as reference and re-derive
  what you need. This matters most in this run, because it is deleting the
  code it is porting.
- Training stays offboard in `training/`. JAX and MJX never enter the
  engine or a payload. `analysis/` imports no GPL package.
- Never commit any of the following:
  - secrets, machine paths, private hostnames;
  - build outputs;
  - full transcripts;
  - policy binaries or rollout traces.
- Do not hand-edit `STATE.md`, `PLAN.md`, `ROADMAP.md` or state nodes.
- Keep earlier projects read-only: hex, ot5–ot11, orun1-*, every `sweep-*`
  and `digestbug-*`. Work on copies named `orun2-*`.

**This run:**
- **Do not start a replacement engine or a desktop app.** The FreeCAD
  application layer stays (Phase 11 is not this run). The dashboard is the
  only UI.
- **Do not rewrite the dashboard from scratch.** Grow `review_server.py`
  and `review_static/`. A2 holds: no npm, no build step, no framework.
- **The protocol stays a contract.** Every `OP_ARG_SPECS` change updates
  `docs/INTEGRATION.md` in the same commit, as AGENTS.md requires.
- The run branch builds and both suites pass at every accepted commit. The
  disable commit and the delete commit are separate commits.
- The actor may serve the dashboard on 127.0.0.1 for its own browser
  tests. It never runs `tailscale serve` and never binds a public address.
- Committed images are PNG, ≤300 KB each, under `docs/probes/orun2/`.
- No role starts, stops or restarts the loop or signals its process.

## Question policy

- Resolve reversible choices autonomously, using the smallest measured step
  towards the highest-ranked open criterion.
- **Port or drop?** If a shell feature helps a person *look at, review,
  or lightly steer* an autonomous result, port it. If it exists for
  hands-on modelling, drop it and record why in the ledger. When still
  unsure, drop it and mark the row "owner to confirm".
- Where A1–A4 and a measurement disagree, record both and follow A1–A4.
  They are the owner's to change.
- Deleting is cheap because `v1-blender-shell` exists. Being *unread* is
  not: never delete a module the parity ledger has not described.
- Code and accepted artifacts outrank docs. Update the docs with the
  behaviour they describe.
- A harness or usage limit is not an attempt: keep the receipt and wait for
  capacity.
- Never invent a measurement, never weaken a test to pass, and never mark
  a parity row "ported" without a test.

## Exhaustion policy

`report_done`.
- Once S1, R1, D1–D3, A1, W1 and C1 have evidence, write the closing
  report, reconcile and claim done. Two consecutive critic acceptances stop
  the run.
- Do not claim done while any criterion is unmet unless the 72-hour ceiling
  has arrived. Until then, work the highest-ranked open criterion, then the
  long-term rung.
- If the ceiling arrives first, report how far each criterion got and what
  is left. Do not redefine success.

## Quality bar

- Run `pixi run test-engine` and `pixi run python -m pytest cli/tests` at
  every accepted commit that touches code. Run the CLI suite with the GPU
  hidden.
- For protocol or payload changes, rebuild and stage, then run the packaged
  lifecycle gate. Report skips and failures as such. Engine-needing CLI
  tests that skip on a bare build do not count as passes.
- Every dashboard feature D2 counts has a browser-driven test against a
  real engine.
- Every removal has an ADR, and is verified by a build and tests in the
  same commit series.
- Record each unit with its State Impact. Direction changes, new APIs and
  removals also earn ADR entries.

## Reconcile

- Every five work iterations or three unreconciled records:
  - fold impacts;
  - advance the high-water mark;
  - regenerate the views;
  - export and check.
- The separate maintainer and planner roles stay off. The critic names the
  next unit.
- Unattended roles never edit this charter.

**Done criteria as gaps** (one open state node each; work closes them through declared impacts):

- [gap] gap-s1-shell-gone-nothing-reaches: **S1. The shell is gone and nothing reaches for it.** - `git ls-files shell | wc -l` is 0. - No pixi task, `package/` script, CMake rule, test, `.gitattributes` LFS rule or live doc refers to `shell/`, `mesh_agent`, a `.blend`, or `CADEX_BLENDER_EXECUTABLE`. ADRs and `docs/history/` are the exception. - The removal follows the two-commit protocol: a disable commit, then a delete commit, each green. - The licensing posture is restated without the GPL half: - `test_licensing_compliance.py`, `docs/inherited-modifications.json` and `docs/PROVENANCE.md` say what is now true; - an ADR records that the repo no longer carries GPL code, if that is what the audit finds. - **`mesh.blender` is retired**, with an ADR naming every project and example that used it: - the op, its runner, worker and adapters, `examples/blender_enclosure.py`, its tests and `docs/BLENDER-RECIPES.md` are all removed; - `OP_ARG_SPECS` and `docs/INTEGRATION.md` change in the same commit. - Codex and pi support is removed. - Shell-only tests are gone. Tests that only *mention* the shell are rewritten: - purity guardrails; - `rollout_bake_integration.py`; - `test_project_docs.py`.
- [gap] gap-r1-contract-describes-three-part: **R1. The contract describes the three-part product.** - Rewrite these for engine + dashboard + agent: - `docs/VISION.md`: the interface section, and the non-goals that named the Rust shell; - `AGENTS.md`, at **no more than half its current 432 lines**; - `README.md`, `docs/ARCHITECTURE.md`, `docs/INTEGRATION.md`; - `docs/ROADMAP.md`: - Phase 12 is superseded by "a desktop app that copies the dashboard"; - Phase 13b's shell half is closed; - Phase 6 is marked historical. - One direction-change ADR states the bet, what it costs, and what would make the owner reverse it. - `docs/BLENDER.md`, `docs/BLENDER-TREE.md` and `docs/BLENDER-RECIPES.md` move to `docs/history/`. - A new `docs/DASHBOARD.md` replaces `docs/REVIEW-DESIGN.md` as the UI spec. It keeps that document's palette, type scale and dark-floor rules. - **The state graph's frontier lists only live work.** Every stale open criterion is superseded through a record that gives its reason: - ot7: F4–F7, F10; - ot10: A5, A7; - orun1: C1; - anything else the shell made moot. `STATE.md` regenerates clean, and `hypergraph check` exits 0.
- [gap] gap-d1-one-command-from-clone: **D1. One command from a clone to a running dashboard.** - On a fresh clone on linux (sb1x), a documented, short command sequence builds the engine and serves the dashboard over a projects directory: - for example `pixi run setup-engine && pixi run app`; - `./cadex` with no project should open or serve the dashboard. - No step needs git-lfs, Xcode or `shell/lib`. - **Measured before and after:** - tracked files; - working-tree size; - Python and JS LOC by tree; - the number of setup steps; - wall time from clone to the dashboard's first page; - installed footprint.
- [gap] gap-d2-from-browser-alone-person: **D2. From a browser alone, a person can watch and steer a design.** - Each of the following is proven by a test driven through the existing headless Chromium path (`cli/cadex_cli/browser.py`) against a real engine: 1. **Start a turn.** Start a design turn from a prompt, optionally with an attached image. Watch it live as the transcript streams and the renders and model update as revisions are accepted. 2. **Move a slider.** Move a parameter slider and see the rebuilt model. Report p50 and p95 latency on a warm project beside the raw-NDJSON bar (`cadexd_latency_integration.py`). 3. **Leave a comment.** Comment on the whole design or on a picked part. The next agent turn receives it. 4. **Manage revisions.** Accept, reject and restore a revision. 5. **Inspect.** Use the section, exploded and collision views, and play a rollout in the viewer. 6. **Export.** Export STEP and STL, and download a concept sheet. - Write endpoints are safe by default: - the server binds 127.0.0.1; - writes need a per-launch token or a same-origin check; - remote viewing is documented as `tailscale serve` in front of it.
- [gap] gap-d3-autonomous-runs-first-class: **D3. Autonomous runs are first-class in the dashboard.** - The dashboard lists runs beside projects: - CLI agent turns; - Ouroboros runs (read-only from `.ouroboros/runs/<run>/` and the run branch). - Each run shows: - its iterations and critic verdicts; - the charter criteria; - the artifacts its records point to (renders, reports, probe pages). - orun1's review material (`docs/probes/orun1/`) renders in the dashboard from the repo alone. It replaces what `~/orun1-review/build.py` built by hand, which proves the per-run review pages are no longer needed.
- [gap] gap-a1-agent-has-one-contract: **A1. The agent has one contract, and a way to reach the owner without waiting.** - The product agent's tools (`cli/cadex_cli/tools.py`, pinned by `test_project_tool_surface.py`) and its guidance (`CadexAgentGuidance.md` plus `agent.system_prompt`) are the single source. Nothing that was only in the shell's `modes.py` is lost: - re-derive anything worth keeping, because the shell's code is GPL and must not be copied; - record what was not kept. - **The agent gains a non-blocking channel to the dashboard:** - it can flag a revision or artifact for the owner's review, or post a question; - the dashboard shows these; - the owner's answers and comments arrive in the agent's next turn; - the agent never stops to wait for an answer. - Tests pin the channel at the protocol or tool surface. Changing the surface follows AGENTS.md's tool-surface rule.
- [gap] gap-w1-nothing-product-could-do: **W1. Nothing the product could do headlessly was lost.** - On a copy of an existing robot project, the whole walk runs and every step is visible in the dashboard: 1. prompt; 2. accepted design; 3. params sweep; 4. `look` and render; 5. STEP/STL export; 6. MJCF export; 7. a short training run on the 5090; 8. `evaluate`. - Both full suites pass, and so does the packaged lifecycle gate. - The CLI and dashboard have no feature the shell parity ledger below marks "ported" without a test. - **The parity ledger is complete:** `docs/SHELL-PARITY.md` gives each of these one row: - every `mesh_agent` module; - each of its 23 tools; - each of the seven Cadex editors. Each row says one of three things: **ported** (where, and the test), **already covered** (where), or **dropped** (why, and the ADR). No row is blank.
- [gap] gap-c1-closing-report-docs-probes: **C1. Closing report.** - `docs/probes/orun2/REPORT.md` covers: - D1's before and after numbers; - the parity ledger summary; - every removal and its ADR; - D2's latencies; - screenshots of the dashboard (PNG, ≤300 KB each, on the dark floor); - the remaining defects. - Reconcile, then claim done for critic review without ticking the owner boxes.

## Method

Ouroboros iterations on branch `ouroboros/orun2`: orient, one dispatched unit, record, commit; a reconcile pass folds the tail on pressure; with the planner on, a bet follows each reconcile.

## Result

Directive recorded. Work follows as child nodes.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/orun2
- commit: 65e25d4e4a14ca8a5c59e9c8461586ac2e820f8f

## State Impact

none: operator directive with no new gaps; impacts are declared by the work nodes that follow
