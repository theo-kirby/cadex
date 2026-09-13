# Goal: real models, reference-grade review

Verified against source: 2026-09-13. Owner-directed charter revision (ADR-328),
replacing the ot5 charter (ADR-284), whose D1-D11 the owner ticked on 2026-09-13
(`.ouroboros/history/ot5.md`, record `patient-pond-3886`).
The human owns this file; unattended roles do not edit it.

## Mission

Make what ot5 built worth looking at, in this order: the review dashboard, the
rendered look, the model itself, then the range of mechanisms. Nothing here is a
new leg of the north star; it is the quality bar the existing legs must meet
before print-ready export or the unattended robot prompt can be worth doing.

**First, the dashboard.** The persistent operator page on port 8765 is a stack
of cards in a dark chrome around a light viewport, and at phone width it
collapses into a sliver. It becomes one designed page: academic but modern, a
single type scale and palette across chrome and viewport, a clear hierarchy
(project and current run, model, curves, videos, history), readable on a phone
and orbitable by touch.

**Second, the look.** Rendered policy videos and the dashboard viewport match
the operator's sibling `neural-whoop` checkout, which is the look mg-legs had:
**dark only**, the near-black grid mat with its PROTOTYPE / 1 METER labels and
pitch that scales with the subject, a camera that tracks the subject at a
declared framing fraction, fog, grounded contact shadows, antialiasing and the
timer overlay. The light palette goes. The viewport and the capture share one
environment module so they show the same place. The reference checkout stays
read-only; Cadex's renderer stays self-contained, with provenance recorded as
`cli/cadex_cli/review_static/REFERENCE-LICENSE.txt` already does.

**Third, the model.** Lark, the ot5 biped, is boxes: every part is `part.box`,
every collision is a box, and the ground is a cyan slab that is itself a part
of the design. That is not a robot anyone could build. Every model this run
designs is built from catalog hardware, the **MG90S** from `lib.servo` as the
standard actuator, with horns, bearings and fasteners from the catalog, and
modelled printable parts that mount them: servo pockets with declared
clearance, horn attachments, shafts through bearings. Collision proxies are
never what the viewer shows by default; the real tessellation is, and the
proxies appear only under a labelled toggle. Nothing in the world (floor,
walls) is part of the design.

**Fourth, the range.** The product agent designs two more mechanisms the same
way, a two-wheeled balancing robot and a single servo arm, and each goes
through the full recorded lifecycle (train, record, review) on the dashboard.
Poor performance is a valid measured result; box parts, missing hardware or
skipped training are not.

Live operator dashboard rules from ot5 stand: one project per server,
inspection only, the persistent URL serves the project and run being worked on,
kept running between iterations, verified on every experiment start and end.

## Done criteria

Only these unchecked claims form this run's frontier. Each record names the
criterion it advances, the evidence now present, and what remains. A record may
say "ticks D1" when its evidence exists; the human owns the checkbox edit.

- [ ] **D1. The dashboard is one designed page.** A written design spec
  (`docs/REVIEW-DESIGN.md`: purpose, hierarchy, type scale, palette, spacing,
  breakpoints, what each region is for) and a page that follows it: one dark
  palette across chrome and viewport, one type scale, headings that read as an
  academic paper's and controls that read as a modern app's, no horizontal
  scroll at 1400 px or 400 px. Evidence: before/after screenshots at both widths
  committed beside the spec, a browser test asserting no horizontal overflow
  and the spec's palette tokens on the rendered page, and the operator URL
  showing the new design on the active project.
- [ ] **D2. The dashboard works on a phone.** At 400x850 with touch emulation:
  the page is readable without zoom, the sidebar collapses, the model view fills
  the width and orbits by touch, curves are legible, videos play and download.
  Evidence: a headless browser test with a mobile viewport and touch events,
  and screenshots of each region at that width.
- [ ] **D3. Viewport and videos match the neural-whoop reference.** Dark only:
  the reference's near-black grid mat with PROTOTYPE / 1 METER labels and
  subject-scaled pitch, fog, contact shadows, antialiasing, a camera tracking
  the subject at a declared framing fraction, and the timer overlay, from one
  environment module shared by viewport and capture. Evidence: reference frames
  (`neural-whoop/render-examples`) beside Cadex viewport screenshots and decoded
  video frames at equivalent framing, with an explicit written assessment of
  floor/grid, horizon/fog, palette, lighting/shadows, materials, framing and
  camera; the same pose/camera compared viewport-to-video; close and wide
  framing and orbit tested for stage edges, lost shadows or bad scale; the
  light palette removed from the code; existing playback, download, polling and
  headless tests still green.
- [ ] **D4. The viewer shows the real model, and says so.** The dashboard
  viewport and the videos render the accepted revision's tessellated solids,
  never the collision proxies, unless a visible toggle labelled as collision
  geometry is on; the video's identity strip names what is shown. Evidence: a
  browser test toggling proxies on a project whose proxies differ from its
  solids, a decoded video frame check, and the operator URL on the real biped.
- [ ] **D5. The biped is a buildable mechanism.** A redesigned biped in a fresh
  project uses MG90S servos from `lib.servo` with catalog horns, bearings and
  fasteners, and modelled printable parts that mount them. Evidence: a
  per-solid inventory in the project (`docs/INVENTORY.md`: every solid, its
  source as catalog family and part id or "modelled", its mass) with no bare
  primitive standing in for a part; a fit check that every servo sits in a
  pocket with the declared clearance and every horn meets its link; no floor,
  slab or wall in the design; a viewport screenshot in which the servos and
  horns are recognisable; and the collision proxies declared per part with
  their relation to the solid recorded.
- [ ] **D6. The real biped trains, is measured and is recorded in the new
  look.** One bounded real GPU training run on the redesigned biped, a
  checkpoint video and a final video in the D3 look on the operator dashboard,
  and the measured displacement, survival and falls over a declared episode
  and seed set. Standing for the full episode is the bar the report measures
  against; failing it is a valid measured result.
- [ ] **D7. A two-wheeled balancing robot goes through the lifecycle.** The
  product agent designs it from a prompt in a fresh project (MG90S or another
  catalog motor, catalog wheels or modelled printable wheels, a body that
  mounts the board and battery volume), it meets D5's inventory and fit rules,
  trains once (bounded), and its videos and measurements are on the dashboard.
- [ ] **D8. A single servo arm goes through the lifecycle.** Same as D7 for a
  2 or 3 DoF arm on MG90S servos with a modelled base and links; its task is a
  reach or hold, measured.
- [ ] **D9. Everything ot5 proved still holds.** The review server and record
  suites, live polling within five seconds, playback and download, restart
  during training, copy isolation, failed-run states and headless operation
  all pass after the redesign, the look change and the model changes. Evidence:
  the CLI suite green, the engine suite green, and the operator URL serving the
  active project with the current run selected.
- [ ] **D10. A closing report exists and the critic accepted done.**
  `docs/probes/ot6/REPORT.md` links the evidence for D1-D9, states what each
  measured, and names what remains open, with nothing claimed that a record
  does not carry. This is the run's last unit, not a repeat of any earlier one.

## Horizon ladder

Granularity, not elapsed time. The critic selects the next unit after each actor
turn; this ladder is the starting plan, not a fixed implementation sequence.

- **short-term:**
  0. Write `docs/REVIEW-DESIGN.md` from the current page: screenshot it at
     1400 and 400 px as the "before", then set the hierarchy, type scale,
     palette tokens and breakpoints (D1).
  1. Apply the spec: one dark palette across chrome and viewport, one type
     scale, the region layout; delete the light theme from the environment
     module (D1, D3).
  2. Make the layout responsive: sidebar collapses, cards stack, model view
     fills the width, touch orbit; add the phone browser test (D2).
  3. Bring the capture and viewport to the reference: grid mat labels and
     subject-scaled pitch, tracking camera at a declared framing fraction, fog,
     contact shadows, timer overlay; compare side by side with reference
     frames (D3).
  4. Add the collision-proxy toggle and the identity strip's "showing" field;
     test on a project whose proxies differ from its solids (D4).
  5. Redesign the biped in a fresh project on MG90S with catalog horns, bearings
     and fasteners and modelled mounts; write the inventory and the fit check
     (D5).
  6. Train it once, bounded; publish checkpoint and final videos in the new
     look on the operator URL; measure (D6).
  7. Prompt the balancer; inventory, fit, train, review (D7).
  8. Prompt the arm; inventory, fit, train, review (D8).
  9. Re-run every ot5 suite and the operator URL check; fix what the changes
     broke (D9).
- **medium-term:**
  1. The dashboard as a designed, phone-usable page (D1, D2), with the design
     spec kept true as the page changes.
  2. One environment module, reference-matched and dark only, behind both the
     viewport and the capture (D3, D4).
  3. Buildable mechanisms from catalog hardware: the biped, the balancer and
     the arm, each with inventory, fit check and a recorded lifecycle (D5-D8).
  4. The regression floor: everything ot5 proved, green after every change
     (D9), and the closing report (D10).
- **long-term:**
  1. Print-ready export: per-part STL/3MF, print orientation, fit tolerances
     around catalog hardware, a bill of materials and a fit check, from a
     reviewed project. The north-star leg after this run.
  2. The unattended robot prompt: one prompt to printable export, trained
     policy, video and report with no human step.
  3. Gait at scale: a biped that stands and walks in the declared shove band;
     the RL node says this is what remains blocked.
  4. Keep every gate green, every doc true, every project record usable, and
     the operator dashboard serving the live project.

## Constraints

**Standing:**

- Obey AGENTS.md: licensing boundaries, sandboxed geometry, unchanged process
  separation, zone gates, ADRs and record nodes. No UI in the engine, no copying
  GPL shell code into the CLI, and no replacement engine or shell work.
- Training remains offboard. No trainer/JAX/MJX in engine payloads or new
  training dependencies in pixi.toml. A dashboard observes artifacts and the
  public protocol; it never imports engine internals or becomes a trainer.
- Preserve accepted-state checks. Reading a project cannot re-accept changed
  geometry. A historical view must not rebuild an old run using today's script
  and present the result as the original.
- Keep records and retained artifacts project-local and portable. Large videos,
  checkpoints and traces stay outside the product repository; commit their
  identities and compact evidence, not generated dumps.
- Never commit secrets, machine-specific absolute paths, private-network
  addresses or hostnames, or build outputs. Write the operator address as
  `<private-address>` in committed text and read it from the environment in
  code and tests. Never hand-edit STATE.md, PLAN.md or state nodes.
- One logical change per commit, fix forward after critic rejection. At most
  one full build per unit; report incomplete verification honestly.

**This run:**

- **Evidence receipts are small.** A committed receipt under `docs/probes`
  holds identities, commands, numbers and the assessment and is at most 16 KB;
  screenshots and decoded frames at most 200 KB each. Full telemetry, traces,
  frame sets and logs stay in the project directory outside the repo and are
  cited by path and digest. A test enforces the size caps.
- **Dark only.** The light palette is removed, not kept behind a switch.
- **Nothing in the world is part of a design.** No floor slab, wall or stage in
  any project script; the environment supplies the ground.
- **Catalog hardware or modelled part, never a primitive standing in.** A box or
  cylinder is acceptable only as a modelled printable part with a named purpose
  in the inventory.
- Headless only: no desktop application launch. Headless browser automation
  and offscreen video rendering are in scope. The server needs no display.
- One project per server, inspection only. No training controls, chat editor,
  multi-project catalog, accounts or public hosting. Serve only the configured
  project's permitted artifacts. Existing private network; no tunnel or cloud.
- Work and training stay on this machine. One training run at a time, with an
  explicit timeout, at most two hours and 20 GB of memory per training run.
  Bound concurrent video rendering and measure its impact on training.
- New test projects live outside this checkout under the operator's
  cadex-projects directory. No writes to cdx-rl, no dependence on mg-legs,
  no reuse of Lark's script; Lark's history stays as history.
- The neural-whoop checkout is read-only reference. Anything taken from it is
  taken under its licence and recorded in `REFERENCE-LICENSE.txt`; the
  renderer must run with that checkout absent.
- Print-ready export, the unattended robot prompt, gait research, catalog
  expansion beyond what a design needs, fleet setup and inherited-tree
  removals are outside this frontier.

## Question policy

The owner has chosen dark only, the MG90S as the standard actuator, the
balancer and the arm as the two extra mechanisms, and dashboard first. Resolve
routine choices autonomously: choose the smallest reversible change advancing
the highest-ranked open D criterion, use code as truth and update its docs,
and record assumptions. Use existing project and training artifacts before
adding another source of truth. Never guess missing metrics or label an
unverified video as a verified policy rollout. Report pre-existing gate
failures against the baseline. Do not wait on clocks or for another loop role;
choose an unblocked unit. Scope expansion requires an owner charter revision,
not an actor interpretation.

## Exhaustion policy

`report_done`. When D1-D9 each have evidence, the next unit is D10: write the
closing report and claim done. The critic accepts done only when every
criterion's evidence is present in a record; the run stops after the runner's
`stop.on_done_accepted` count. Do not repeat a lifecycle, add a fourth
mechanism or start a long-term rung to fill the run: an evidenced frontier ends
the run, it does not restart it.

## Quality bar

- Run the zone's required suites; protocol/payload changes also need the
  packaged gate. Dashboard behaviour needs headless browser tests at both
  widths, not only HTTP responses; a design change ships with its screenshots.
- Look changes ship with decoded frames beside reference frames and a written
  assessment; a passing pixel-coverage test alone establishes nothing.
- A design ships with its inventory and fit check; a training run ships with
  its measurements; real training, decoded videos and real lifecycle artifacts
  are required where the criteria say so.
- A unit changes product code, a meaningful test or a user-facing document and
  advances a D criterion. The operator dashboard must track the active
  project/run. Bookkeeping alone is reserved for reconcile passes.
- Record causally with real State Impact targets; removals/direction changes
  earn an ADR, behaviour changes update their docs, and landed roadmap items
  are marked.
- Preserve existing file lifecycle behaviour. New review output must never
  corrupt accepted projects or require a browser to keep design or training
  running.

## Reconcile

Every five work iterations or three unreconciled records, the actor's next unit
is the reconcile pass: fold impacts, advance the high-water mark, regenerate the
views, export, check and commit. Separate maintainer and planner remain off; the
critic names the next unit. Unattended roles never edit this charter. The
runner ingests operator charter edits at the next iteration boundary and
records a versioned directive; confirm adoption in its charter-reload log. The
current actor and critic finish under their original charter. Do not launch or
restart a run as part of charter authoring.
