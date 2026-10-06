# Goal: What worked, made the default — and a page arranged like Blender

Verified against source: 2026-10-06. Operator charter for orun4, following
orun3 (`.ouroboros/history/orun3.md`) and the owner's first full lifecycle
on the new views: a printed biped driven by Feetech STS3215 bus servos,
designed, trained and passed 10/10 by an agent in one session. The human
owns this file; unattended roles never edit it.

## Mission

The owner's last design session worked. The agent produced a robot the
owner liked: a good style, well-placed mechanics, and a walk that passed
every check. That success came from one agent's choices in one project.
This run makes it **the system's**: Cadex's own guidance, its renders and
its dashboard carry what worked, so the next agent, on a different kind of
robot, starts there.

In priority order:

1. **Fix the two bugs the session found.** Evaluation ignores the command
   filter a policy was trained with. A run that was stopped on purpose
   reads as failed.
2. **Put the lessons into Cadex.** Read that project (below) for what made
   it work. Write the lessons into the agent guidance, split the way the
   owner asked: general mechanical and process lessons go in the
   domain-neutral **base**; the look goes in a named, optional **style**.
   Nothing in Cadex names or points at that project.
3. **Present a finished design.** When a policy passes evaluation, Cadex
   makes:
   - a hero image in a normal font;
   - a second hero with the printable parts laid out on a print bed, and a
     parts list;
   - a video of the walking policy taking shoves.

   The blocky 5×7 pixel font leaves every image and video.
4. **Make the page arrangeable like Blender.** Pan in the 3D viewport.
   The status overlay becomes its own editor. Layouts come from one-click
   presets: side by side, stacked, 2 over 1, 3 rows, quad.

If the run achieves only one thing, it is this: **a fresh agent session,
given only Cadex's guidance and the chosen style, can see what the
reference session learned the hard way: compact twin-keel feet, a target
speed the servos can actually hold, hips wide enough for the feet to
clear.**

Priority, in order: F1, F2 (bugs), G1, G2 (guidance), H1–H3
(presentation), D1–D3 (page), C1 (report).

## The reference project

`~/cadex-projects/biped-sts` is the reference. It has 26 revisions, 13
training runs, 11 ADRs in its `DECISIONS.md`, three evaluations, and a
passing policy (`walk-r13`, iteration 140). Read all of it:
- `script.py`, the final design;
- `DECISIONS.md`, the why of every change, including the dead ends;
- `PROGRESS.md` and `script_history/`, how the design moved;
- `runs/*/` and `evaluations/*/`, what each change did to the walk.

It is read-only (see Constraints). It is a source of evidence, never a
dependency. Lessons enter Cadex as general rules with their reasons. They
never enter as "do what biped-sts did", or with its numbers presented as
if they held for every robot.

## Owner-revisable assumptions

Until this section changes, the run works to these defaults:

- **B1. Base plus styles (owner, 2026-10-03).** Design is *form follows
  function*. Guidance never tells an agent to make something "look
  engineered"; to the owner that reads as fake, and it invites decoration.
  - **The base is domain-neutral.** Cadex designs cranes, vacuum robots
    and whole mechanisms, not only small printed legged robots. A base rule
    must hold across those, or it belongs in a style.
  - **A style is named and optional.** A project chooses it, and it is
    never on by default. The first new style is the reference project's
    look: the printed legged robot.
  - `docs/DESIGN-LANGUAGE.md` today is titled "small printed robots that
    look engineered". It is restructured into this base-plus-styles form,
    and that wording goes.
- **B2. Heroes and the shove video come when a policy passes
  evaluation.** They are not made on every revision, and the agent does not
  have to ask for them. They are made from the design and policy that
  passed, on the dark floor, and the 2D viewport shows them.
- **B3. No G-code.** The print-bed hero is a render of the printable
  parts laid out flat on a bed, with a parts list. Every capable open
  slicer is AGPL, so Cadex does not slice: it neither vendors nor imports
  one, and it does not run one as a subprocess this run.
- **B4. A normal font.** Images and videos use a plain sans-serif in the
  dashboard's type scale (`docs/DASHBOARD.md`). Everything else about the
  renders stays the same: palette, floor, framing, layout. The font is
  open-licensed and compatible with the repo's LGPL posture. It is shipped
  as a font file under `docs/PROVENANCE.md`, never as a prebuilt library,
  with an ADR recording its licence.
- **B5. The page stays read-only and light (ADR-537, charter A2).** It is
  a standard-library server, vanilla JS and the vendored three.js, with no
  npm, build step or framework. Layouts are per-viewer conveniences, kept
  in the browser.

## Done criteria

Each criterion needs a causally parented record with measured evidence.
The human owns the checkboxes. Roles report results and do not tick them.

- [ ] **F1. Evaluation applies the command filter the policy was trained
  with.**
  - The trainer writes `action_filter_alpha` into the `.cxpolicy`. The
    engine's rollout and evaluation read it from the policy and filter
    commands the same way the trainer does (`training/cadex_train.py`,
    about line 1597).
  - **The test:** a policy trained with a filter is evaluated and
    replayed, and both apply the same filter. A policy with no filter
    recorded behaves exactly as today (alpha 1.0). Old `.cxpolicy` files
    still load.
  - The checkpoint rollouts (ADR-544) and the evaluation film use the
    same path, so what the viewport plays is what was evaluated.
  - The packaged lifecycle gate passes if the change reaches the payload.
- [ ] **F2. A run reads as what happened to it.**
  - A run stopped through `train_stop`, or through `loop.request_stop`
    with a reason, reads as **stopped**, with that reason, in
    `/api/project`'s stage and on the page. It never reads as failed.
  - A walk killed without a stop request reads as **failed** (the
    unaccepted ADR-558 work on branch `orun3-wip-adr558` is the starting
    point; finish it, test it, and give it its ADR).
  - Tests cover stopped, killed, finished and crashed, through both
    `train_start` and `cadex walk`.
- [ ] **G1. The guidance is a base plus styles, and the agent can choose
  a style.**
  - The agent's guidance (`src/Mod/cadex/CadexAgentGuidance.md`,
    `cli/cadex_cli/guidance.py`, `docs/DESIGN-LANGUAGE.md`) is
    restructured into a domain-neutral base and named styles.
  - A project chooses a style through its project config (for example
    `agent.json`). `cadex guidance` and the MCP server's instructions
    carry the base plus that style only. With no style chosen, they carry
    the base alone.
  - Tests pin it:
    - the base names no robot type as the default;
    - no style text appears when none is chosen;
    - **no guidance file names `biped-sts` or any other project.**
  - The agent's tool surface changes only under AGENTS.md's rule. Choosing
    a style should need no new tool.
- [ ] **G2. The reference project's lessons are in Cadex.**
  - A ledger, `docs/probes/orun4/LESSONS.md`, lists every lesson drawn
    from the reference project. Each row gives:
    - the lesson as a general rule;
    - its evidence (the reference project's ADR, revision or run);
    - where it went: base, the printed-legged-robot style, a tool
      default, or *not adopted*, with the reason.
  - At the least, the ledger weighs:
    - **contact geometry:** a round single keel balanced on a knife edge,
      and a twin keel with a flat strip walked;
    - **the target speed against the actuator:** at 100 mm/s every run
      found a shuffle, and at a speed the servos could hold it walked;
    - **lateral clearance:** wider hips and a limit on inward hip roll, so
      the feet stop colliding;
    - **where the actuators sit:** the knee servo hung inside the thigh;
    - **training practice:** checkpoints on, the reward shaped against
      shuffling, warm starts;
    - **the look:** tapered plates with a lightening window, round bosses
      at the joints, a shin tapering in two directions, and compact
      hull-shaped feet that are never large or flat.
  - **The printed-legged-robot style** carries the look and the
    legged-specific rules. The base carries only what holds for any
    mechanism, phrased that way.
  - **The proof:** a fresh agent session on a scratch project
    (`orun4-*`), with the style chosen, is asked for a printed legged
    robot. Its first accepted design must show the style's foot, joint and
    clearance rules without being told them. The transcript excerpt and a
    render go in the record. This is a check of the guidance, not a full
    training run.
- [ ] **H1. One normal font in every image and video.**
  - The 5×7 glyph face in `src/Mod/cadex/CadexStudio.py` (`_FONT_ROWS`)
    is gone. Every caption, label and timestamp the engine or CLI draws is
    a plain sans-serif (B4). That covers the hero, the concept and detail
    sheets, the evaluation film's overview and detail images, and the
    rollout videos.
  - Nothing else about those renders changes. **Measured:** before and
    after images of each kind, side by side in the record, with only the
    text differing.
  - The font's licence and its source are in `docs/PROVENANCE.md`, with
    an ADR.
- [ ] **H2. A passed evaluation produces two heroes.**
  - When `evaluate` passes, Cadex renders the accepted design that
    passed, on the dark floor:
    1. **the hero**, the existing studio shot in the H1 font;
    2. **the print-bed hero**: every printable part laid flat on a print
       bed, oriented as it would print, and labelled, with a parts list of
       the purchased hardware (from the inventory) beside it.
  - The purchased parts are not on the bed. Parts that cannot fit one bed
    go on more beds in the same image, or the image says how many beds it
    needs.
  - Both are shown in the 2D viewport and listed in `/api/project`. A
    failed evaluation makes neither.
  - Tests cover a passing and a failing evaluation, and the bed layout's
    non-overlap and bounds.
- [ ] **H3. A passed evaluation produces a shove video.**
  - The passing policy is filmed taking shoves: horizontal pushes drawn
    from the task's disturbance model (`CadexDynamics` disturbances), each
    one marked on screen when it lands. The film shows whether it
    recovers.
  - The video uses the H1 font and the existing film pipeline
    (`cli/cadex_cli/film.py`, `video.py`). It plays in the 2D viewport
    beside the evaluation films.
  - The push magnitudes and the recovery outcome are written beside the
    video, from the rollout itself. A robot that falls is filmed falling;
    the outcome is never faked.
- [ ] **D1. The 3D viewport pans.**
  - Shift-drag pans, as does middle-drag. On touch, a two-finger drag
    pans and a pinch zooms. **Fit** resets it.
  - The gesture is listed in `docs/DASHBOARD.md` and covered by a browser
    test through `cli/cadex_cli/browser.py`.
- [ ] **D2. Status is its own editor.**
  - The stage overlay (ADR-542) becomes an editor, `data-editor="status"`,
    shown as **Status**, beside the 3D and 2D viewports. It can be put in
    any area like the others.
  - The default layout gives it an area of its own beside the 3D viewport
    on a desktop, and a tab on a phone. The 3D viewport keeps the
    checkpoint scrubber and the revision timeline, because those drive
    what it plays.
  - All of ADR-542's content moves with it: stage, training,
    checkpoints, the activity line and the warning. Its tests and the
    `docs/DASHBOARD.md` rows move too.
- [ ] **D3. Layouts come from one-click presets, and areas move like
  Blender's.**
  - A layout control (in the View menu or the top bar) offers at least
    these presets:
    - single;
    - side by side;
    - stacked;
    - 2 over 1, and 1 over 2;
    - three columns;
    - three rows;
    - quad.

    Each fills its areas with the editors in a sensible order. One click
    applies it.
  - Areas can still be dragged to dock and swap, and resized by their
    edges (`layout.js`). The run makes this discoverable: a visible drag
    handle, and a drop preview showing where the area will land.
  - A browser test applies every preset and asserts the area count and
    geometry, then drags one area onto another.
  - The layout stays per-browser (B5). A reset returns to the default.
- [ ] **C1. Closing report.**
  - `docs/probes/orun4/REPORT.md` covers:
    - F1's before and after on a filtered policy;
    - the G2 ledger summary and the fresh-session check;
    - H1's before and after images;
    - one example each of H2's heroes and H3's shove video (a still);
    - D3's presets, as one screenshot each (PNG, ≤300 KB each, on the
      dark floor);
    - every ADR the run added;
    - the remaining defects.
  - Reconcile, then claim done for critic review without ticking the owner
    boxes.

## Horizon ladder

- **short-term:**
  1. Read the reference project end to end, and write the G2 ledger's
     skeleton: every lesson, with its evidence, before deciding where any
     of them goes.
  2. F1: find where the engine rolls out a policy, apply the recorded
     filter there, then add the test and the ADR.
  3. F2: rebase `orun3-wip-adr558` onto main, finish it, and test
     stopped, killed, finished and crashed.
  4. D1: pan in the 3D viewport. It is small and self-contained, and the
     owner asked for it by name.
- **medium-term:**
  1. G1, then G2: the base-plus-styles structure, then the lessons folded
     in, then the fresh-session check.
  2. H1: the font, everywhere at once, with the before and after images.
  3. H2 and H3, both on a passing policy. To produce one, use a
     scratch copy of the reference project (`orun4-biped-sts`) with its
     passing policy.
  4. D2, then D3: status as an editor, then the presets and a
     discoverable drag.
- **long-term:**
  1. The closing report (C1).
  2. The small defects orun3 left:
     - a project being worked on reads "not found" until its first
       script;
     - the trainer stalls 37–39 s before each checkpoint (measure where
       the time goes before changing anything);
     - the guidance tells the agent to set `checkpoint_every` whenever
       the owner is watching.
  3. More styles, but only from reference images or projects the owner
     supplies. Never invent one.
  4. Keep every gate green and every doc true. Keep `STATE.md`
     reconciled.

## Constraints

**Standing:**
- Obey AGENTS.md, the licensing rules and the process boundaries. The
  repository carries no GPL or AGPL code, and that covers fonts and
  slicers too. The tag `v1-blender-shell` may be read but never copied
  from.
- Training stays offboard in `training/`. JAX and MJX never enter the
  engine or a payload, and `training/cadex_train.py` imports only the
  standard library at module scope. `analysis/` imports no GPL package.
- Never commit any of the following:
  - secrets, machine paths, private hostnames;
  - build outputs;
  - full transcripts or activity logs;
  - policy binaries, checkpoints or rollout traces.
- Do not hand-edit `STATE.md`, `PLAN.md`, `ROADMAP.md` or state nodes.
- **Keep earlier projects read-only:** biped-sts, biped-mg90, quad-qdd,
  hex*, ot5–ot11, orun1-*, orun2-*, orun3-*, every `sweep-*` and
  `digestbug-*`. Work on copies named `orun4-*`.

**This run:**
- **No guidance, doc, test or default in Cadex names the reference
  project**, or reads files from it at run time. Records and the G2 ledger
  may cite it as evidence.
- **The page stays read-only.** It gets no write route. Choosing a
  style is the agent's job (project config) or the CLI's, never the
  page's.
- **Do not rewrite the dashboard from scratch.** Grow `review_server.py`,
  `review_static/` and `layout.js`.
- **The protocol stays a contract.** Every `OP_ARG_SPECS` change updates
  `docs/INTEGRATION.md` in the same commit. The tool surface changes only
  under AGENTS.md's rule.
- The run branch builds and both suites pass at every accepted commit.
  The CLI suite runs with the GPU hidden whenever a training run is live.
- One training run at a time on the 5090. The machine lock is the
  arbiter.
- The actor may serve the dashboard on 127.0.0.1 for its own browser
  tests. It never runs `tailscale serve` and never binds a public address.
- Committed images are PNG, ≤300 KB each, under `docs/probes/orun4/`.
- No role starts, stops or restarts the loop or signals its process.

## Question policy

- Resolve reversible choices autonomously, using the smallest measured step
  towards the highest-ranked open criterion.
- **Base or style?** If a lesson would be wrong for a crane, a wheeled
  base or a fixed arm, it goes in a style. When unsure, put it in the
  style and mark the ledger row "owner to confirm".
- **Is it a lesson or a coincidence?** A lesson needs evidence in the
  reference project: a change, and what it did to the walk or the fit. A
  choice the agent made once, with no recorded effect, is not a lesson.
- Where B1–B5 and a measurement disagree, record both and follow B1–B5.
  They are the owner's to change.
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
- Once F1, F2, G1, G2, H1–H3, D1–D3 and C1 have evidence, write the
  closing report, reconcile and claim done. Two consecutive critic
  acceptances stop the run.
- Do not claim done while any criterion is unmet unless the 24-hour ceiling
  has arrived. Until then, work the highest-ranked open criterion, then the
  long-term rung.
- If the ceiling arrives first, report how far each criterion got and what
  is left. Do not redefine success.

## Quality bar

- Run `pixi run test-engine` and `pixi run python -m pytest cli/tests` at
  every accepted commit that touches code. Run the CLI suite with the GPU
  hidden.
- Python changes under `src/Mod/cadex/` need `pixi run build-engine`
  before the CLI's engine-needing tests count. For protocol or payload
  changes, rebuild and stage, then run the packaged lifecycle gate.
  Engine-needing tests that skip on a bare build do not count as passes.
- Every new page feature has a browser-driven test through
  `cli/cadex_cli/browser.py`. The page and `docs/DASHBOARD.md` change in
  the same commit.
- Every bug fix has a test that fails without it.
- Every new behaviour, route, style mechanism and font has an ADR,
  starting at ADR-558. Number them in the order they land, whatever the
  orun3 branch called its draft.
- Every iteration that changes code leaves a record. orun3 had three that
  did not; the critic rejects a fourth.

## Reconcile

- Every five work iterations or three unreconciled records:
  - fold impacts;
  - advance the high-water mark;
  - regenerate the views;
  - export and check.
- The separate maintainer and planner roles stay off. The critic names the
  next unit.
- Unattended roles never edit this charter.
