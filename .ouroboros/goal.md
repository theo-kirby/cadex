# Goal: Watch the design and the training as they happen

Verified against source: 2026-10-05. Operator charter for orun3, following
orun2 (`.ouroboros/history/orun2.md`) and the owner's own ADR-533 to
ADR-541 work on the dashboard. The human owns this file; unattended roles
never edit it. The base-plus-styles design charter stays shelved and runs
after this one, on the views this run builds.

## Mission

Cadex is three things: the engine, the read-only dashboard, and the
owner's own agent driving the engine through `cadex mcp` (ADR-500,
ADR-537, ADR-538). The owner works in their agent and keeps the dashboard
open beside it. The page has one job: **show what is happening, so the
owner knows when to step in.** Today it shows the accepted model well, but
it shows a design's *history* and a training run's *progress* only after
the fact, or as plots in a different viewport.

This run makes the 3D viewport tell the story while it is happening:

1. **An overlay over the model** says what stage the project is in, and
   how training is going: iteration, ETA, reward and loss sparklines, the
   best reward, and the collapse warning.
2. **Training is visible as motion.** Each checkpoint is rolled out
   through the engine as soon as it lands. The viewport loops the newest
   one, and a scrubber steps through the older ones, so the owner can
   watch a gait go from flailing to walking.
3. **The design is visible as change.** Each accepted revision's model is
   kept. A revision timeline scrubs through them in the 3D viewport, with
   the previous revision shown as a ghost and the changed parts tinted.
4. **The agent's current activity is one line on the page.** The MCP
   server appends every tool call to a project activity log, and the
   overlay shows the latest entry.

The data for (1) is already on disk (`runs/<run>/train/progress.json`,
served in `/api/project`). (2), (3) and (4) each need a small write on
the CLI side, and the page stays read-only.

While the run adds routes, it also makes the dashboard **portable**: URLs
relative to the page, and an HTTP API pinned by tests. Then a desktop
wrapper or a reverse proxy can host it without rewriting paths.

If the run achieves only one thing, it is this: **on a copy of the biped `ot5-biped`, while
a short training run is going on the 5090, the 3D viewport shows the
overlay updating and the newest checkpoint's rollout playing.**

Priority, in order: V1 (overlay), V2 (checkpoints), V3 (revisions), V4
(activity), P1 (portability), W1 (walk), C1 (report).

## Owner-revisable assumptions

Until this section changes, the run works to these defaults:

- **B1. The page stays read-only (ADR-537).** The server answers GET and
  HEAD only. Everything new on the page is read from the project
  directory. The writes this run needs (checkpoint traces, retained
  revision meshes, the activity log) happen in the CLI, on paths the CLI
  already owns: `cadex walk`/`loop.py` supervision, revision acceptance in
  `revisions.py`, and the MCP server.
- **B2. Panels come back one at a time (ADR-533).** V1–V4 each land as
  their own change with their own ADR, test and record, in priority order.
  None of them is a redesign of the page.
- **B3. The dashboard stays light.** It is a standard-library server,
  vanilla JS and the vendored three.js. There is no npm, bundler, build
  step or framework, and no new Python dependency unless an ADR measures
  its weight.
- **B4. Training runs locally on the 5090 through `cadex walk`.** The
  checkpoint rollouts run in the CLI's supervision of the trainer (or a
  sibling process it starts), through the engine on the CPU. They never
  run in `training/`. A checkpoint is any file on disk under
  `runs/<run>/train/`, whoever put it there, so a run synced back by
  `remote_train.sh` works the same way.
- **B5. Snapshots, not a live stream.** The owner accepted that a 1:1
  live view of training is not worth it. A deterministic rollout per
  checkpoint is the view. Do not stream poses out of the trainer.
- **B6. The overlay is the 3D viewport's, and it gets out of the way.**
  It collapses to one line. It reads at phone width. It follows
  `docs/DASHBOARD.md`'s palette and type scale in both themes. The page
  must still render with no overlay data at all (an old project, a run
  without checkpoints).

## Done criteria

Each criterion needs a causally parented record with measured evidence.
The human owns the checkboxes. Roles report results and do not tick them.

- [ ] **V1. The 3D viewport has a training and stage overlay.**
  - The overlay is a new element in the 3D viewport's area, with stable
    hooks listed in `docs/DASHBOARD.md` §2 and pinned by
    `test_review_design.py`.
  - It shows:
    - the project's stage: idle, designing (a revision accepted recently),
      training (the iteration out of the total, and the ETA), evaluating,
      or failed;
    - reward-per-step and loss sparklines from `progress.json`'s curves;
    - the best reward and its iteration;
    - `progress.json`'s `warning`, styled as a warning;
    - which run it is reading, when there is more than one.
  - It updates on the page's existing poll, with no new polling loop. A
    browser test driven through `cli/cadex_cli/browser.py` shows it
    changing as a fixture's `progress.json` is rewritten.
  - It collapses to one line, and the collapsed state is a per-browser
    convenience. Measured at 390 px wide, it covers no more than a quarter
    of the viewport when expanded.
  - An ADR records it as the first panel brought back after ADR-533.
- [ ] **V2. Each checkpoint becomes motion in the viewport.**
  - When a new checkpoint lands during a `cadex walk` training leg, the
    CLI rolls it out through the engine. It writes a
    `cadex-assembly-simulation-trace-v1` trace beside the checkpoint,
    tagged with the checkpoint's iteration, reward and sha256.
  - The rollout happens while training continues. **Measured:** mean
    iteration wall time with checkpoint rollouts on, against off, on the
    same task and seed. The cost is reported, and it is under 5% or an ADR
    explains why the owner should accept more.
  - The server serves each checkpoint's playback through the existing
    `trace_playback`. The 3D viewport loops the newest one, labelled with
    its iteration and reward. A checkpoint scrubber selects older ones,
    and switching to a newer checkpoint is automatic unless the owner has
    picked one.
  - A browser test against a real engine shows a second checkpoint's
    playback replacing the first one while the run is still training.
  - A failed rollout is shown with its reason. It never stops or slows
    the training run.
  - The traces are run outputs. They are never committed, and their disk
    cost per checkpoint is measured and reported.
- [ ] **V3. The design's history plays in the viewport.**
  - When a revision is accepted, its tessellation is kept, stored by
    content hash per part. A part that did not change between revisions
    costs no new bytes. **Measured:** bytes added per revision across
    `orun3-biped`'s thirteen revisions, against the size of a full copy.
  - Revisions accepted before this change have no retained meshes. The
    page says so, and it never shows another revision's geometry in
    their place. Rebuilding old revisions to fill the gap is an explicit
    CLI command, not a side effect of opening the page.
  - The 3D viewport gets a revision timeline. Scrubbing it shows each
    retained revision's model. The previous revision is drawn as a ghost,
    and parts whose digest changed are tinted. A browser test drives the
    scrubber across at least three revisions.
  - The Revisions menu and the timeline agree on ordinals and on which
    revision is current.
- [ ] **V4. The page says what the agent is doing.**
  - The MCP server appends one line per tool call to a project activity
    log: time, tool name, a short summary of the arguments, and the
    outcome. Arguments are never logged in full. The log is bounded
    (rotated or capped), and that bound is tested.
  - `test_project_tool_surface.py` is unchanged: this adds no tool, no
    argument and no result field. If that turns out to be impossible, the
    tool-surface rule in AGENTS.md applies.
  - The overlay shows the latest activity and how long ago it happened. An
    expanded view lists the last few entries. When nothing has happened
    for a while, the line says the agent is idle rather than showing a
    stale action as current.
  - A test drives a tool call through `cadex mcp` and reads the entry back
    from `/api/project`, or from a route the HTTP API pins.
- [ ] **P1. The dashboard is portable.**
  - No page script or server-built URL is root-absolute. Every fetch and
    every link resolves relative to the page, or through one API base. The
    page works unchanged behind a path prefix: a test serves it under
    `/some/prefix/` through a rewriting-free proxy and loads a project.
  - The HTTP API is a documented contract. Every `GET /api/...` route and
    its top-level response keys are listed in `docs/CLI.md`, or in one
    file it points to. A test fails if a route is added, removed or
    renamed without the doc changing too, in the same way the
    `OP_ARG_SPECS` test works.
  - No page state lives only in the browser, except per-viewer
    conveniences such as the layout, the theme and a collapsed overlay.
- [ ] **W1. The whole lifecycle is watchable, on a real robot.**
  - On `orun3-biped`, a copy of `~/cadex-projects/ot5-biped`:
    1. the agent accepts at least two new design revisions through
       `cadex mcp`;
    2. a short `cadex walk` training leg runs on the 5090 with checkpoints
       on;
    3. `evaluate` runs on the result.
  - The dashboard, opened before step 1 and never reloaded, shows each
    stage in the overlay, the revisions on the timeline, and at least
    three checkpoint rollouts. Screenshots are taken at each stage.
  - Both full suites pass, and so does the packaged lifecycle gate if the
    run touched the protocol or the payload.
- [ ] **C1. Closing report.**
  - `docs/probes/orun3/REPORT.md` covers:
    - V2's training-cost and disk measurements;
    - V3's bytes-per-revision measurement;
    - every ADR the run added;
    - W1's screenshots (PNG, ≤300 KB each, on the dark floor);
    - the remaining defects.
  - Reconcile, then claim done for critic review without ticking the owner
    boxes.

## Horizon ladder

- **short-term:**
  1. Read `docs/DASHBOARD.md`, `review.js`, `layout.js`, the
     `training_telemetry` path in `review_server.py`, and `loop.py`'s
     `supervise`. Write down the overlay's hooks and data sources before
     writing any code.
  2. V1: the overlay, reading only what `/api/project` already carries.
     Use a fixture `progress.json`, a browser test, the DASHBOARD.md
     rows, and an ADR.
  3. Measure the baseline V2 needs: a `cadex walk` leg on `orun3-biped`
     with checkpoints on, and its mean iteration wall time with no
     rollouts.
  4. P1's first cut: make every URL in `review.js`, `projects.js` and the
     server's built URLs relative, behind the existing tests.
- **medium-term:**
  1. V2: checkpoint rollouts in the walk's supervision, then playback and
     the scrubber in the viewport, then the cost measurement against the
     baseline.
  2. V3: retain meshes on acceptance, the timeline, the ghost and the
     tint, then the explicit backfill command.
  3. V4: the activity log in the MCP server and its line in the overlay.
  4. P1's API contract test and its doc table.
- **long-term:**
  1. W1's full walk on `orun3-biped`, then the closing report (C1).
  2. Make the overlay and both scrubbers good at phone width and in the
     light theme. Read `docs/DASHBOARD.md` against the page and close any
     gaps. This is a direction, not a bar.
  3. Cheaper meshes on the way to the page: binary or glTF meshes, where a
     measurement shows STL is the bottleneck for the timeline. Add an ADR
     if the format changes.
  4. Keep every gate green and every doc true. Keep `STATE.md`
     reconciled.

## Constraints

**Standing:**
- Obey AGENTS.md, the licensing rules and the process boundaries. The
  repository carries no GPL code. The tag `v1-blender-shell` may be read
  but never copied from.
- Training stays offboard in `training/`. JAX and MJX never enter the
  engine or a payload, and `training/cadex_train.py` imports only the
  standard library at module scope. `analysis/` imports no GPL package.
- Never commit any of the following:
  - secrets, machine paths, private hostnames;
  - build outputs;
  - full transcripts or full activity logs;
  - policy binaries, checkpoints or rollout traces.
- Do not hand-edit `STATE.md`, `PLAN.md`, `ROADMAP.md` or state nodes.
- **Every fixture, test project, measurement and screenshot in this run is
  a biped.** The working copy is `orun3-biped`, copied from
  `~/cadex-projects/ot5-biped`; other biped copies are named `orun3-biped-*`.
  Hexapods and other robots are not used, not even as a second fixture.
- Keep earlier projects read-only: hex, hex1–hex3, ot5–ot11, orun1-*,
  orun2-*, every `sweep-*` and `digestbug-*`. Work on copies named
  `orun3-*`.

**This run:**
- **The page stays read-only.** No write route, no form that posts, no
  slider. A change that needs one is out of scope: record it as a
  question for the owner and move on.
- **Do not start a replacement engine or a desktop app.** P1 makes a
  wrapper possible. It does not build one.
- **Do not rewrite the dashboard from scratch.** Grow `review_server.py`
  and `review_static/`.
- **The protocol stays a contract.** Every `OP_ARG_SPECS` change updates
  `docs/INTEGRATION.md` in the same commit. The agent's tool surface
  changes only under AGENTS.md's tool-surface rule.
- The run branch builds and both suites pass at every accepted commit.
  The CLI suite runs with the GPU hidden whenever a training run is live.
- One training run at a time on the 5090. The machine lock in `loop.py`
  is the arbiter, and nothing works around it.
- The actor may serve the dashboard on 127.0.0.1 for its own browser
  tests. It never runs `tailscale serve` and never binds a public address.
- Committed images are PNG, ≤300 KB each, under `docs/probes/orun3/`.
- No role starts, stops or restarts the loop or signals its process.

## Question policy

- Resolve reversible choices autonomously, using the smallest measured step
  towards the highest-ranked open criterion.
- **Is it a view or a control?** If it helps the owner see what is
  happening, it may go on the page. If it changes anything, it belongs in
  the agent's tools or the CLI, never the page.
- Where B1–B6 and a measurement disagree, record both and follow B1–B6.
  They are the owner's to change.
- When the page has no data for something (an old project, a missing
  checkpoint trace, a revision accepted before V3), show the absence with
  its reason. Never substitute other data.
- Code and accepted artifacts outrank docs. Update the docs with the
  behaviour they describe.
- A pre-existing test failure is recorded and left alone, unless the
  unit's own change touches it.
- A harness or usage limit is not an attempt: keep the receipt and wait for
  capacity.
- Never invent a measurement, never weaken a test to pass, and never wait
  for a human.

## Exhaustion policy

`report_done`.
- Once V1–V4, P1, W1 and C1 have evidence, write the closing report,
  reconcile and claim done. Two consecutive critic acceptances stop the
  run.
- Do not claim done while any criterion is unmet unless the 24-hour ceiling
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
- Every new page feature has a browser-driven test through
  `cli/cadex_cli/browser.py`. V2 and W1's tests run against a real engine.
- The page and `docs/DASHBOARD.md` change in the same commit, as
  `test_review_design.py` requires. Every new route is in the P1 contract
  once that exists.
- Every new panel, write path and route has an ADR, starting at ADR-542.
- Record each unit with its State Impact.

## Reconcile

- Every five work iterations or three unreconciled records:
  - fold impacts;
  - advance the high-water mark;
  - regenerate the views;
  - export and check.
- The separate maintainer and planner roles stay off. The critic names the
  next unit.
- Unattended roles never edit this charter.
