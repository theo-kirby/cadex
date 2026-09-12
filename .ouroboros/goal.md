# Goal: live headless project review

Verified against source: 2026-09-12. Owner-directed charter revision (ADR-284).
The human owns this file; unattended roles do not edit it.

## Mission

Make a headless Cadex project observable while work is happening and reliably
reviewable afterward. Build and test a live web dashboard, served from this
machine over its private network, that shows the project's model, design specs,
training curves, run history, and playable/downloadable policy videos. Prove the
whole file lifecycle with a fresh biped designed by the product agent: create,
save, reopen, train, record, review, revise, retrain, and revisit earlier results.

This is the whole run's focus. The dashboard serves **one project per server**
and is **for inspection only**; the agent continues authoring and training through
the CLI. The script and project records remain authoritative. Browser state is
not project state. The dashboard is a review client, not the replacement shell.

**Live operator dashboard (owner steering, 2026-09-12).** The persistent
private-network dashboard must show the project and experiment currently being
worked on. Maintaining that live page is part of every experiment, not only a
test fixture. At the next work iteration, update the existing shared dashboard
on port 8765 from the obsolete ot4-carriage project to the active Reed/biped
project or its current working copy. Keep that operator URL stable and the
server running between iterations. Run one project per server as before.
When work moves to a copy, deliberately update the served project, identify it
clearly, and verify the operator-facing page over the private-network address.
Use the dashboard yourself during design, training and review. A temporary
browser-test server does not satisfy this instruction.

Success means the complete recorded lifecycle works. Measure gait quality
honestly; a repeatable walking gait is not a completion gate. Retire mg-legs
from the active charter and test workflow. Create a new parametric biped from a
fresh project through the product agent, without importing the old mechanism,
checkpoints, or project history. Historical records and the separate cdx-rl tree
are not deletion targets.

## Done criteria

Only these unchecked claims form this run's frontier. Each record names the
criterion it advances, the evidence now present, and what remains. A record may
say "ticks D1" when its evidence exists; the human owns the checkbox edit.

- [ ] **D1. A live project dashboard is reachable.** One documented command
  serves one selected project over the machine's Tailscale/private-network
  address. A browser can open it without a desktop session on the server.
  Evidence: a headless-browser smoke test against that address, with its command
  and result recorded; no claim of a second-device test unless one was run.
- [ ] **D2. The browser shows the right model and specs.** Interactive 3D
  orbit/zoom, component identity, declared parameters, design specs and project
  decisions come from the selected accepted revision. Selecting an earlier run
  shows its model and specs, visibly identified as historical. Evidence: browser
  tests comparing displayed revision/run identities with recorded inputs and
  exercising model interaction on the fresh biped.
- [ ] **D3. Training is visible while it runs.** The biped's real GPU training
  updates status, iteration, reward and loss histories, episode length and
  checkpoint availability without a page reload. Committed telemetry updates
  appear within five seconds under the measured test conditions. Missing or
  stale data is labelled. Evidence: a browser observation spanning multiple
  actual training updates, plus telemetry tests; synthetic data alone cannot
  tick this criterion.
- [ ] **D4. Policy videos render, persist and play headlessly.** At least one
  verified intermediate checkpoint is rendered and appears in the dashboard
  while training remains active, and the final policy also has a saved video.
  Both play and download in the browser; each identifies the model revision,
  policy digest, rollout seed and simulation time. Evidence: real biped video
  files, a decoded frame/timing check and a browser playback/download test.
  A failed render leaves training running and reports its own failure.
- [ ] **D5. Review history survives a design change.** Each run retains the
  model/script revision, specs, task/training configuration, metrics, policy
  identity and review/video references needed to interpret it. After a design
  edit and retraining, both runs remain selectable with their own curves, models
  and videos. Evidence: before/after identity and artifact checks, and browser
  assertions that old results have not silently switched to the new design.
- [ ] **D6. Save, reopen and restart preserve the project.** Save/reopen and
  restarting the dashboard and engine preserve accepted identity, specs, run
  history, curves and video access. Restarting the dashboard during training
  neither stops nor duplicates that training. Evidence: an automated lifecycle
  test and a recorded pass on the fresh biped with real artifacts.
- [ ] **D7. Save-As/copy produces an independent project.** A documented
  headless operation copies the project and its retained review artifacts;
  another server can inspect the copy. Changing/retraining the copy leaves the
  original unchanged, and the copy remains usable with the original unavailable.
  Evidence: isolation, artifact resolution and browser reopen tests on the copy.
- [ ] **D8. Interrupted and failed runs remain understandable.** Test a
  controlled training interruption, a failed run, and missing/partial review
  output. The dashboard distinguishes interrupted/failed/stale states from
  success, preserves prior completed results and explains the next CLI action.
  Evidence: fault-injection tests and one real interrupted biped training run
  followed by a successful new attempt. Checkpoint resume is not required.
- [ ] **D9. The fresh biped completes the whole recorded lifecycle.** The
  product agent creates and documents a new biped, trains and reviews it through
  this system, uses that review to make a reasoned design change, and retrains.
  Both runs have saved playable videos and measured displacement, survival and
  falls over the same declared episode/seed set. Evidence: the project history,
  a lifecycle report linking D1-D8 evidence, and the comparative results. Poor
  gait is a valid measured result; skipped training or missing recording is not.

- [ ] **D10. The persistent operator dashboard stays current.** The existing
  shared dashboard URL serves the actual working project, with the current run
  selected by default for a new visit (active training first, otherwise the
  latest attempt, including failed/interrupted attempts). It shows that run's
  model/spec identity, available curves and videos, and explicit pending/stale/
  failed states where outputs are not ready. Never silently substitute an older
  successful run for a newer failed one. Preserve deliberate historical browsing
  and video playback in an already-open page, with a visible route back to the
  current run. On each experiment start/completion and working-project switch,
  verify the persistent URL's project/run identity and update the published
  status. Keep serving after tests and between iterations. Evidence: browser
  checks on the persistent private-network URL across a real experiment and a
  working-copy switch, plus regression coverage for current-run selection and
  historical-view preservation. The immediate acceptance check is that the
  shared URL shows the active biped work rather than ot4-carriage.

## Horizon ladder

Granularity, not elapsed time. The critic selects the next unit after each actor
turn; this ladder is the starting plan, not a fixed implementation sequence.

- **short-term:**
  0. First, put the active biped project/run on the persistent shared dashboard,
     verify it through the browser, and keep it current throughout work (D10).
  1. Define the smallest project/run recording contract and its revision and
     artifact identities; document it alongside a tested reader (D2, D5).
  2. Deliver a vertical slice: one-project server, real model/spec view and a
     headless browser test; establish private-network reachability (D1, D2).
  3. Create the fresh agent-authored biped and start a bounded training probe;
     connect its actual telemetry, including retained loss history (D3, D9).
  4. Render one verified rollout into a saved browser-playable video (D4).
- **medium-term:**
  1. Publish checkpoint videos during active training, preserving model/policy
     identity and recording measured overhead (D3, D4).
  2. Exercise reopen, restart, copy isolation and interrupted/failed runs against
     real project artifacts; fix each demonstrated lifecycle defect (D5-D8).
  3. Complete the biped's review-driven design change and retraining, compare
     both runs and assemble the evidence report (D9).
- **long-term:**
  1. Repeat the same lifecycle from a clean project to expose hidden dependencies
     on the first fixture, its paths or its cache.
  2. Improve review clarity and recording reliability for longer histories,
     including bounded telemetry, disk use and visible missing artifacts.
  3. Close remaining browser/video/lifecycle regressions with measured evidence;
     keep every gate green, every doc true, and project records usable.

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
  identities and compact evidence, not generated dumps. Document retention and
  copying explicitly; being ignored by git is not permission to discard history.
- Never commit secrets, machine-specific absolute paths, or build outputs.
  Never hand-edit STATE.md, PLAN.md or state nodes. Only reconcile writes state.
- One logical change per commit, fix forward after critic rejection. At most
  one full build per unit; report incomplete verification honestly.

**This run:**

- Headless only: no desktop application launch. Headless browser automation and
  offscreen video rendering are explicitly in scope. A human's remote browser
  is a client; the server must need no display session.
- One project per server, inspection only. No training controls, chat editor,
  multi-project catalog, accounts system or public hosting. Serve only the
  configured project's permitted artifacts, never arbitrary filesystem paths.
  Use the existing private network; no public tunnel or cloud provisioning.
- Work and training stay on this machine. One training run at a time, with an
  explicit timeout, at most two hours and 20 GB of memory per training run.
  Use the existing offboard training environment. Detach/collect if needed.
  Bound concurrent video rendering and measure its impact on training.
- New test projects live outside this checkout under the operator's
  cadex-projects directory, each with its own project history. No writes to
  cdx-rl and no dependence on mg-legs in new acceptance tests.
- The old gait/shove benchmark, five-variant study, catalog expansion, fleet
  setup and standalone inherited-tree removals are outside this frontier.
  Existing review defects are in scope when this lifecycle exposes them.

## Question policy

The owner has chosen inspection only, one project per server, and lifecycle
completion with honest gait measurements. Resolve routine choices autonomously:
choose the smallest reversible change advancing an open D criterion, use code
as truth and update its docs, and record assumptions. Use existing project and
training artifacts before adding another source of truth. Never guess missing
metrics or label an unverified video as a verified policy rollout. Report
pre-existing gate failures against the baseline. Do not wait on clocks or for
another loop role; choose an unblocked unit. Scope expansion requires an owner
charter revision, not an actor interpretation.

## Exhaustion policy

Maintain within this mission. Once D1-D10 have evidence, repeat the lifecycle,
fix demonstrated recording/review defects and improve bounded operation. Do not
expand into gait research, another dashboard mode or parked product work merely
to fill the run. Report completion evidence honestly when no defect remains.

## Quality bar

- Run the zone's required suites; protocol/payload changes also need the packaged
  gate. Dashboard behavior needs headless browser tests, not only HTTP responses.
- Real training, decoded videos and real lifecycle artifacts are required where
  the criteria say so. Record commands, observed identities, failures and limits.
- A unit changes product code, a meaningful test or a user-facing document and
  advances a D criterion. The operator-facing dashboard must track the active
  project/run; fixture-only success cannot excuse leaving it on an obsolete project. Bookkeeping alone is reserved for reconcile passes.
- Record causally with real State Impact targets; removals/direction changes earn
  an ADR, behavior changes update their docs, and landed roadmap items are marked.
- Prove project isolation and permitted-path handling; distinguish a valid empty
  state, stale telemetry, failed work and successful completion in browser tests.
- Preserve existing file lifecycle behavior. New review output must never corrupt
  accepted projects or require a browser to keep design/training running.

## Reconcile

Every five work iterations or three unreconciled records, the actor's next unit
is the reconcile pass: fold impacts, advance the high-water mark, regenerate the
views, export, check and commit. Separate maintainer and planner remain off; the
critic names the next unit. Unattended roles never edit this charter. The runner ingests operator charter edits at the next iteration boundary and
records a versioned directive; confirm adoption in its charter-reload log.
The current actor and critic finish under their original charter. Do not launch or restart a run as
part of charter authoring.
