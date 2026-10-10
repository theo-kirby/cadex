# ROADMAP-RUNS.md — ROADMAP's run logs and old diagram

> **HISTORICAL (moved to `docs/history/` 2026-10-10, ADR-629).** Dated records cut out of `docs/ROADMAP.md`; never cite them as current. The live doc is `docs/ROADMAP.md`.

Moved verbatim.

## 1. The phase-dependency diagram (as drawn 2026-07-25 → 2026-08-01)

Dependencies: 0 → 1 → 2 strict; 3 and 4 run in parallel after 2; 5 needs 2;
6 needs 4 + 5; 7 needs 6. Then 8, 9 and **13a** are independent; **10 gates
11**; 12 needs 11; 13b needs 13a and otherwise runs forever. **14 depends on
nothing after 9 and nothing depends on it** — which is exactly what made it
a separable vertical rather than a fork in the roadmap.

```
0 truth ─► 1 shrink ─► 2 one-script ─┬─► 3 Qt UX (capped)
                                     ├─► 4 mesh domain ──┐  (gate: confirm
                                     └─► 5 cadexd split ─┴─► 6 Blender shell ─► 7 convergence
                                                                                    │
   ┌────────────────────────────────────────────────────────────────────────────────┘
   ├─► 8 delete src/Gui
   ├─► 13a MERGE (done) ─► 13b source reduction, ongoing ──────────────┐
   ├─► 9 one surface ─► 10 probe + characterize ═► 11 our engine ─► 12 our shell
   │                                (go/no-go)      └── unscheduled, behind the unchanged protocol ──┘
   └─► 14 dynamics + control (M0–M9, closed) ── independent of 0–13, in main since ADR-102
```

## 2. Later — the finished items (as logged 2026-08-01 → 2026-10-03)

*Many items below are walk, prompt and shell work from before ADR-498 and
ADR-538. The walk survives as the tokenless legs (`cadex walk`, no
`--prompt`, `--model` or `$CADEX_MODEL`); items about a design turn's
prompt, its model or the shell are marked where they stand.*

- [x] **Hydrate on file open** (ADR-073 measured it, ADR-186 landed it).
  `load_post` → `on_file_changed` → `cadex_backend.queue_open`: a saved
  `.blend` beside an existing `.cadex` queues the open, a timer runs the
  restore-verified `open_project` and the display `rebuild` off the main
  thread, and the accept hydrates. The gate's
  `test_opening_a_file_hydrates` drains the queue by hand and asserts
  `model_objects_on_open > 0`. A1 still stands: it would make that open one
  script run instead of two.
- [x] **A digest-moving engine change locked a project out of the UI, with
  no visible way back in** (measured after ADR-074, ADR-187 landed the way
  back). The failure is at *open*: `ensure_open` runs the restore pass,
  `CADEXD_RESTORE_FAILED` comes back, and every operation that would fix it
  is behind the same call. **Rebuild Model cannot be the remedy** — it
  passes `unrestored_ok=False`, correctly. The remedy is `write_script`,
  which re-accepts on success, and `adopt_script` was drawn only for an
  *empty* project or a *dirty* buffer, so nothing was drawn at all.
  Measured on `wiring-demo/harness.cadex` after ADR-074: accepted
  `7e073ae6…`, restored `25fdf64f…`, four cables; recovered by hand with
  `open_project restore=false` then `write_script`. That is now
  `MESH_AGENT_OT_reaccept_script` ("Re-accept Stored Script"), drawn in the
  chat panel off the failure code both open paths cache on the per-root
  state, and offered in place of Rebuild Model in the parameters panel's
  alert row. The gate's `test_a_locked_out_project_is_reaccepted_from_the_chat`
  moves the accepted digest with the script untouched and drives the
  operator from the locked-out state. VISION's obsolete missing-recovery
  claim was corrected against this shipped behavior on 2026-09-08 (ADR-187).
- [x] **Qualify assembly camera visibility** (2026-09-07, ADR-228):
      actual hydration and EEVEE render reproduce unposed source leakage;
      `docs/history/ASSEMBLY-VISIBILITY-AUDIT.md` defines ownership and regression gates.
- [x] **Hide instanced sources from camera renders** (2026-09-07) with
      independent render ownership and a hydration/EEVEE regression failing
      on old source (ADR-228). Pre-hidden sources retain their render flags.
- [x] **Save-As dropped a trained policy** (named in ADR-138, ADR-188 landed
  the carry). The shell's `CARRIED_ASSET_SUFFIXES` filtered the carry-forward
  to meshes and `.cxpart`, so a project that replayed a `.cxpolicy` Saved-As
  into a script that could not bind its weights — the one asset that cannot
  be rebuilt from the script. `POLICY_SUFFIXES` (`.cxpolicy`, `.json`,
  `.xml`) joins the list, which is now the engine's whole stored union; the
  gate's `test_save_as_carries_imported_geometry` carries the triple and
  refuses a file the store would not accept.
- [x] **One reproducible lifecycle entry point** (ADR-199, `docs/CLI.md`
  §2). `cadex walk --out <project>/runs/<name>` runs the legs as child
  `cadex` commands — design turns, the blanked sweep, `train --put`, the
  digest edit as a two-literal rewrite of the script's one
  `assembly.policy` call, the verified rollout — and lands `review.json`
  in the project as its own commit; checkpoints and traces stay out of the
  project's history. Qualified on the repository's plate-and-arm toy, twice
  (a placeholder digest to a verified rollout, then a reward change with a
  warm start), by `cli/tests/test_walk.py` with the real engine and trainer.
  The domain-doc convention is exercised by the caller (`docs/sensors.md`),
  not generated. The second mechanism is qualified below; the GUI-attached
  mode was documented in ADR-201, below. *Since ADR-538 the walk runs no
  design turns (`walk --prompt` is gone); the agent designs, and the walk
  runs the tokenless legs.*
- [x] **Portable walk output labels** (ADR-246). `PROGRESS.md` and the
  project commit subject use a project-relative output path, or its basename
  outside the project; absolute `--out` no longer records a machine path.
- [x] **The same walk on a second mechanism** (ADR-203).
  `examples/lifecycle/linear-carriage` uses a slider and force motor through
  the unchanged entry point, at the arm's 1 iteration × 4 environments.
  Both projects' `PROGRESS.md` carry matched metric definitions and measured
  numbers. The carriage reaches a verified 50-step rollout but does not learn
  to hold height in one iteration. `cli/tests/test_walk.py` pins the slide
  joint, policy digest and review with the real engine and trainer.
- [x] **Teach purchased hardware placement in the walk** (ADR-243 follow-up).
  Design instructions and project scaffold distinguish separate purchased
  components from printed solids and catalog clearance cutters; contract tests
  pin delivery of the guidance, not agent compliance.
- [x] **Remove unsupported inventory purchase inference** (ADR-243).
  Keep catalog identity and placed-instance totals, including repeated links;
  remove generator-call tally and generated-minus-placed reports.
- [x] **Inventory is part of the walk review** (ADR-236 follow-up).
  After rollout, write `docs/inventory.md` and the `review.json` inventory
  counts and project-relative path, committed together in every mode.
  No published assembly yields an explicit unavailable report; the walk
  retains its dynamics prerequisites. Real toy and carriage walks test it.
- [x] **Clearance is part of the walk review** (ADR-238).
  Commit `docs/clearance.md`, the review summary and comparable progress
  counts together; preserve unavailable and unknown measurements. Initial
  solved pose only. Arm/carriage walks and CPU mode parity pin the result.
- [x] **The walk's remote-training handoff is scripted** (ADR-200,
  `docs/CLI.md` §2). `cadex train --remote` and `cadex walk --remote` run
  the train leg through `training/remote_train.sh train <bundle> <out> --
  <the same trainer flags>` (ADR-089), verify the returned policy against
  the receipt's sha256, and leave every artifact where the local walk puts
  it — `DIR/train`, the store, `review.json` — so the three modes share
  one shape. Offline evidence: the command pinned against the script's
  usage line, the leg end to end against a stand-in dispatcher with the
  real engine. **Not executed**: no dispatch, and a warm start does not
  travel (`--remote` with `--init-from` is a usage error).
- [x] **Three-mode artifact parity is tested through the whole walk**
  (ADR-200 audit). Local and remote-flag walks use real CPU training and
  engine verification with a local stand-in dispatcher; both land the same
  project-relative paths, committed review and comparable progress rows.
  The shared table in `docs/CLI.md` is pinned to the project scaffold.
  Remote transport and GUI attachment remain unexercised by constraint.
- [x] **The remote training leg can be planned instead of dispatched**
  (ADR-255, `docs/CLI.md` §2, `training/SETUP.md` §d). `cadex train
  --dry-run` rebuilds and exports for real, then reports `training_plan`
  — the four files the leg would touch and the ordered steps that touch
  them, `executed: false` — instead of training. The local and remote
  plans carry the same `artifacts`; the remote `steps` are the local ones
  with `copy-out`/`copy-back` around the trainer, which is the whole
  difference between the modes and is now checkable from the command line
  offline. It is the preflight for `cadex walk --remote`, whose train leg
  otherwise fails after the design and assembly legs have run. **Still not
  a substitute for `remote_train.sh check`**: a plan proves the shape of
  the leg, never that the box is reachable, and nothing here does ssh.
- [x] **The walk with the GUI attached is documented against the client
  code** (ADR-201, `docs/CLI.md` §2, `docs/MUJOCO.md` §7c row 11). It is
  the same `cadex` commands from a terminal beside the open `.blend`:
  the CLI's `flock` is per command and released before the `PROGRESS.md`
  row and the commit, and the shell takes no lock. Rebuild Model or reopen
  before the next GUI edit. The in-app agent has no shell or file tool;
  project docs stay the CLI's and a person's. **GUI not exercised.**
  *Three modes, one shape* is headless exercised, remote scripted, GUI documented.
  *The GUI-attached mode went with the shell (ADR-498).*
- [x] **...and leg by leg, with the difference column pinned** (ADR-269,
  `docs/CLI.md` §2). Every leg the walk spawns, plus the review it runs
  itself, with its command, its artifacts and what an open window changes:
  nothing the walk writes, one refresh after `declare`, one model
  resolution. Two tests hold the table's leg column equal to
  `__main__.py`'s `run_leg` names and pin the four `mesh_agent` facts
  beneath it. Reading the source corrected the handler count from two to
  four. **GUI still not exercised.** *The `mesh_agent` facts went with the
  shell (ADR-498).*
- [x] **Inventory resolves large inspection previews** (ADR-236 follow-up).
  Page catalog totals and uncatalogued outputs as well as components; expand
  previewed rows and their fields before rendering. Regression uses the real
  inspection pager with 60 catalog entries and names over the 1 KiB budget.
- [x] **Headless clearance and intersection name every pair** (ADR-237).
  `cadex clearance` writes `docs/clearance.md`, with read-time distance and
  common-volume thresholds. Every separated pair is measured too; missing
  measurements remain unknown. Initial solved pose only. Recipe rebuild
  medians remain within the 2 s / 20 percent budget; digests are unchanged.
  Walk wiring is the next unit; rendering and section views remain open.
- [x] **Named-angle headless rendering route probed** (ADR-239). Valid
  background blueprint calls refuse after accepted hydration; independent CPU
  tessellation projection produced and inspected front/top/right/iso SVGs.
  The product render call follows below; section views and walk integration remain open.
- [x] **Named-angle CPU render CLI** (ADR-239 follow-up). `cadex render`
  writes revision-bearing front/top/right/iso SVGs and a summary in the
  project. Bounded accepted buffers, solved placements and pixel depth;
  real arm/curved assembly image tests. Walk wiring follows below; sections remain open.
- [x] **Named-plane tessellation section CLI** (ADR-240). World XY/XZ/YZ
  cuts write revision-bearing SVG/JSON with closed contours and cavity fills,
  solved placements, offsets, explicit empty/unsupported statuses and limits.
  Real-kernel cavity/rotation tests; walk integration remains a separate unit.
- [x] **Walk review commits named-angle previews** (ADR-239 follow-up).
  One review session snapshots accepted display before inventory/clearance,
  checks rollout revision, commits four SVGs and summary under that revision,
  and reports render/acquisition and whole-walk timings. ADR-262 later keeps
  these generated previews local by default.
- [x] **Walk review commits named-plane sections** (ADR-240 follow-up).
  Shared accepted snapshot, world XZ at a derived offset (ADR-267; the fixed
  3.125 mm this landed with missed whole parts), revision/digest checks,
  explicit empty/unsupported/error semantics and committed SVG/JSON. Both
  mechanisms and local/remote-flag CPU stand-in parity are tested; a separate
  fresh complete-review rehearsal remains required. ADR-262 later keeps
  these generated sections local by default.
- [x] **Fresh hinged-arm complete-review rehearsal** (2026-09-08).
  Public walk, bounded CPU training, four inspected views and interior section,
  accepted identity, tracked artifacts and explicit contact/unknown counts;
  evidence in `docs/probes/complete-review/hinged-arm/`. Fresh carriage comparison
  is recorded immediately below for combined criterion assessment.
- [x] **Fresh carriage complete-review rehearsal and comparison** (2026-09-08).
  Identical public entry point and bounded CPU settings; four inspected views,
  interior section, accepted identity and committed-byte audit. Both projects
  carry comparable measurements; arm contact and carriage 34 mm separation
  remain explicit. Evidence in `docs/probes/complete-review/linear-carriage/`;
  combined review evidence is ready for maintainer assessment.
- [x] **The fresh mixed-joint walk completes every leg** (2026-09-09,
  `docs/CLI.md` §2). `ot4-mix55`: the same crank-slider prompt into a second
  empty project, no `--resume` and no supplied script, `--iterations 5 --envs 16
  --seed 0 --timeout 600 --leg-timeout 1800`, against a freshly installed engine
  reporting `match` across 56 files. **Exit 0 in 1680.78 s**, peak process-tree
  RSS 2,312,118,272 bytes, no watchdog intervention. Design 1649.63 s (revision
  `70fd2a53…`, digest `ee279ea9…`, four bodies, one closed loop, ball rod end
  and keyed cylindrical bushing in place of the over-constrained all-revolute
  loop); train 26.71 s on CPU at reward/step −0.4055, witness error 1.14e-08
  against 1e-04; declare 0.81 s; rollout total reward −19.85. All four eyes ran:
  four render views, an XZ section cutting 4 of 4 objects, a 4-component
  inventory, and a clearance check reporting one 648.0 mm³ frame/slider
  intersection. ADR-281's MJX geom-pair refusal never fired — the design turn
  authored box and capsule collision shapes in an empty contact group — which is
  one run of evidence that the guidance steers an unaided turn, not a guarantee.
- [x] **A second mechanism, a passive joint, and a task that terminates**
  (2026-09-09, `docs/CLI.md` §2). `ot4-cart`: an inverted-pendulum cart —
  grounded frame and rail, cart on a **prismatic** joint driven by a bounded
  **force motor**, pole on a **passive revolute** joint nothing drives — from
  one prompt into a third empty project through the *same* `cadex walk`, same
  flags, **no code change of any kind**. **Exit 0 in 1222.22 s**, peak
  process-tree RSS 1,997,844,480 bytes, no watchdog. Design 1196.04 s (revision
  `0aa617e2…`, digest `b3b699e6…`); train 20.27 s on CPU at reward/step 0.6936,
  witness error 6.34e-09 against 1e-04; declare 0.65 s; rollout total reward
  28.756 at seed 7. All four eyes ran: 4 render views (5,002 triangles), an XZ
  section at a derived −15.0 mm cutting **2 of 3** objects, a 3-component
  inventory, and a clearance check with **0 offending pairs of 3** and a
  passing bounds check. Two findings the walk reported on itself: the verified
  rollout ended on the task's own `pole_fell` termination at step 30 of 200, so
  its reward is a sum over 31 steps and says nothing about learned balance; and
  the most-coverage section rule chose a plane that misses the pole, naming it
  in `section.missed_objects` as `moved: true` — on a slender moving rod near
  the centre plane, maximum coverage is not maximum interest. Both projects'
  `PROGRESS.md` carry the same columns; the two `total_reward` figures are
  different objectives in different units and rank nothing.
- [x] **A machine names its turn model once** (ADR-249, `docs/CLI.md` §2).
  `--model` defaults to `$CADEX_MODEL`, the recorded project model, then
  `claude-fable-5` (ADR-276). Found by the
  first prompt walk on the Linux GPU box, whose design leg refused in 2.4 s:
  the default model was out of usage credit while `claude-sonnet-5`,
  `claude-opus-5` and `claude-haiku-4-5` all answered on the same login.
  One resolver, two argparse defaults and a regression; LGPL CLI zone only.
  **Corrected on the three-modes currency audit**: the entry's claim that
  both front ends still answer "what does Cadex run" the same way was false
  — the shell's `DEFAULT_MODEL` is `""` and nothing under `shell/` names
  `CADEX_MODEL`, so `$CADEX_MODEL` governs the terminal legs only.
  `docs/CLI.md` §2's GUI-attached paragraph now says so, and a test pins the
  fact rather than the sentence. ADR-200's remote handoff was re-read in the
  same pass and is current: the box runs no engine and no turn, so neither
  ADR-249 nor ADR-250 reaches it. *Gone with `cadex -p` (ADR-538).*
- [x] **`assembly.mjcf` never returns for a ten-component rig** — fixed
  (ADR-250, 2026-09-08, found on the Linux GPU box). The first prompt walk
  there designed a one-servo swing rig — MG90S from the catalog, printed
  base/arm, M3 hardware, 10 components, 3 joints — whose geometry and
  `assembly.solve` accept in 1 s, and whose dynamics layer killed the
  sandboxed worker at the 300 s CPU cap (SIGXCPU, returncode -24), reported
  as `The isolated domain worker exited without a result`. The bisect
  cleared the rig: a **two**-component model with one revolute joint and no
  collision shapes stalls identically. The stall is `import numpy` under
  `import mujoco`, and it is address space, not compute — OpenBLAS sizes a
  per-thread scratch pool from the host's core count and reserves 4,432 MB
  on 32 cores against the worker's 6,144 MB `RLIMIT_AS`, then spins in its
  allocation retry loop. `worker_environment` pins
  `OPENBLAS_NUM_THREADS=4` (624 MB), and SIGXCPU/SIGXFSZ now surface as
  `DOMAIN_CPU_LIMIT_EXCEEDED` / `DOMAIN_OUTPUT_LIMIT_EXCEEDED` naming the
  cap and the CPU-second vs wall-clock asymmetry. The walk's own script at
  `policy_on=1`: **300.0 s / exit 3 → 2.0 s**; the full dynamics layer with
  collisions, actuator, joint dynamics, observations, reward, termination,
  randomisation and both ranged disturbances accepts in **1.2 s**.
- [x] **The prompt walk runs end to end on the Linux GPU box** (2026-09-08;
  this and the two items after it ran `walk --prompt`, gone since ADR-538;
  the evidence ADR-249 and ADR-250 were cleared for). `cadex walk --prompt`
  took a one-servo swing-arm rig from a prompt to a verified policy with no
  human step past documented flags: **exit 0, 17:43 wall clock, 2,640 MB peak
  RSS**, into a durable project outside this repository. Legs, all exit 0 —
  design 1,014.2 s (one turn, `--model` from `$CADEX_MODEL`), train 38.3 s,
  declare 2.2 s, rollout 2.4 s; `walk_seconds` 1,063.1 through review.
  Training was local CPU inside the run bound: 5 iterations x 16 envs, 8.7 s,
  4,673 parameters, reward/step **-0.1254**, witness error 7.2e-09 against a
  1e-4 tolerance. The rollout the engine verified scored **total_reward
  -0.1765** over 4 legs. The review step used all four headless eyes: render
  (front/top/right/iso, 13,432 triangles, 3.4 s), section (XZ at 3.125 mm),
  inventory (10 components, 7 catalogued), and the clearance bounds check
  (**pass**, 90 comparisons over 45 pairs, 13 pairs inside the 0.1 mm
  advisory band). The project landed as a codebase: five commits, five
  `PROGRESS.md` rows, and `docs/{actuators,clearance,inventory,sensors}.md`.
  The only host-specific input was `CADEX_MODEL=claude-opus-5`, because the
  `claude-fable-5` default is out of usage credit on this login; the
  trainer, engine and venv resolved themselves.
- [x] **The walk holds on a second mechanism, on the same machine**
  (2026-09-08). The same `cadex walk --prompt` entry point, **no code change
  of any kind** (`git status` clean at `526d43fb`), took a *vertical linear
  carriage* rig — **prismatic** joint, **force motor**, against the swing
  arm's revolute joint and position servo — from a prompt to a verified
  policy: **exit 0, 5:59.8 wall clock, 1,721 MB peak RSS**, into a second
  durable project outside this repository. Legs, all exit 0 — design 340.7 s
  (one turn), train 15.8 s, declare 0.9 s, rollout 1.0 s; `walk_seconds`
  359.7 through review. Training local CPU at the same 5 iterations x 16 envs
  and seed 0: 2.8 s, 4,673 parameters, reward/step **0.02347** (best
  iteration 0.16748), witness error 2.8e-09 against a 1e-4 tolerance. The
  verified rollout scored **total_reward 3.2963** over 4 legs (`height`
  +3.3085, `effort` -0.0122). All four review eyes again: render
  (front/top/right/iso, 60 triangles, 0.32 s), section (XZ at 3.125 mm),
  inventory (2 components, 0 catalogued — this rig is printed, not
  purchased), clearance bounds check **pass** (2 comparisons over 1 pair, 0
  offending). Five commits, five `PROGRESS.md` rows and five project ADRs,
  all written by the walk's child commands. **The two projects' rows are
  comparable line for line** — same columns, same metric definitions, same
  toy scale — and, per the standing caveat `PROGRESS.md` itself carries,
  their reward expressions are different objectives in different units, so
  the totals never rank the two designs against each other.
  `--trainer-python` was dropped from this invocation: the documented
  fallback resolved `~/cadex-train-venv` on its own.
- [x] **The walk holds on a third mechanism, whose joint carries two
  coordinates** (2026-09-08). The same `cadex walk --prompt` entry point,
  again with **no code change of any kind**, took a *quill lift* rig — one
  **cylindrical** joint (a slide and a hinge on one axis) driven by a
  **position servo on the linear coordinate** — from a prompt to a verified
  policy: **exit 0, 10:53 wall clock, 1,946 MB peak RSS**, into a third
  durable project outside this repository. Legs, all exit 0 — design 629.6 s
  (one turn), train 19.6 s, declare 0.9 s, rollout 1.0 s; `walk_seconds`
  652.9. Local CPU training at the same 5 iterations x 16 envs and seed 0:
  3.7 s, 4,801 parameters, reward/step **-0.5796**, witness error 2.9e-08
  against a 1e-4 tolerance; the verified rollout scored **total_reward
  -74.79** over 4 terms. The joint is the point: `(position, linear)` is the
  fourth and last pair in the engine's action-source table and the only one
  no earlier walk had driven, and a **velocity** actuator cannot be the
  variable instead — the engine refuses it at `action_range_underivable`
  because a joint states position limits and no speed. Two review findings
  the two earlier walks could not produce: the motion block reported
  **`travel_mm 20.28`, `travel_deg 0`** on the same component, so a
  two-coordinate joint moved in one channel only (gravity exerts no torque
  about a vertical axis — a fact about the rollout, not a missing
  measurement), and the clearance eye reported its **first offending pair on
  an agent-authored design**: `housing`/`quill`, verdict `intersection`, 960
  mm3 of common volume. The project's own ADR-005 says why and says it was
  deliberate — the shaft is modelled inside a solid bore cylinder, the joint
  rather than contact constrains the quill, and the two collision groups are
  disjoint — so the eye is reporting a known modelling choice back, not
  catching an unnoticed defect. Exit 0 remains correct: the report was
  written, not "all pairs are clear". The ADR-260 delta did not
  render and could not: a project's first walk has no previous row carrying
  either label. Five commits, five `PROGRESS.md` rows, and
  `docs/{actuators,sensors,inventory,clearance}.md`, all written by the
  walk's child commands.
- [x] **Walk reports engine/source differences** (2026-09-08, ADR-251).
  Before its first leg, JSON and stderr carry a bounded Python-file comparison
  with match/different/unavailable evidence; no refusal, rebuild or binary
  provenance claim. Offline walk regressions and the CLI suite verify it.

- [x] **Explicit CPU toy-walk setup** (2026-09-08, ADR-253). Rehearsed the
  public walk with a CUDA-capable venv and explicit CPU selection; setup,
  CLI guide and project scaffold share the measured invocation contract.
- [x] **The walk checks its domain-note convention** (2026-09-08, ADR-256).
  The review reads the MJCF it trained on and names the note subjects the
  mechanism declares — `<actuator>` → `docs/actuators.md`, `<sensor>` →
  `docs/sensors.md` — against the notes the project keeps. `review.json`
  gains `documentation` and the walk's `PROGRESS.md` row the same finding.
  Reported, never written and never fatal: the notes are the design turn's,
  and the generated `ARCHITECTURE.md` scaffold says so where the project's
  next agent reads it.
- [x] **The walk's mechanism-blindness is pinned by a test** (2026-09-08,
  ADR-260). Two offline regressions in `cli/tests/test_walk.py`: the two
  example recipes — revolute/torque against slider/force — walk through
  `command_walk` with identical flags and must dispatch byte-identical child
  argv once the project path is substituted out, and the digest edit rewrites
  the same two literals on both. `examples/lifecycle/README.md` names the
  entry point, the two regressions and both projects' comparable numbers side
  by side. Verified by mutation: a `--label` added for scripts containing
  `slider` fails the first test.
- [x] **Every walk leg is bounded in wall clock** (2026-09-08, ADR-261).
  `run_leg` called `subprocess.run` with no `timeout=`, so every leg —
  design, sweep, train, script, declare, rollout — was unbounded, while
  `walk --timeout` bounded only the trainer's internals inside the train
  leg and its help text implied otherwise. `--leg-timeout SECONDS` (default
  3600, `0` for no limit) stops any one leg and fails the walk through the
  existing `failed(...)` path at exit 1, the leg reporting 124. The stop is
  a **subtree kill** — the leg is its own session, `SIGTERM` then `SIGKILL`
  to the group — because the process that hangs is the agent CLI or the
  trainer under the child, not the child; `SIGINT`/`SIGTERM` to the walk are
  relayed to the leg so Ctrl-C still reaches it. The train leg gets
  `max(--leg-timeout, --timeout + 300 s)`, so a long training run asked for
  by name is never shot by a default. The regression hangs *and* spawns a
  grandchild holding the captured pipe, then polls that pid until it is
  gone: a direct-child kill fails it. **Amended the same day** (ADR-261
  amendment): the kill went to the group only when the *direct child* had
  survived the grace, so a grandchild that ignores `SIGTERM` outlived its
  parent and hung the walk in the drain. `SIGKILL` now goes to the group
  unconditionally after the grace, the group id is read while the child is
  alive so it stays addressable after the reap, and the final drain is
  bounded at 10 s. A second regression whose grandchild sets `SIGTERM` to
  `SIG_IGN` fails against the previous stop.
- [x] **A warm start travels to the box** (2026-09-08, ADR-268).
  `remote_train.sh` lifts `--init-from` and `--init-from-parent-task` out of
  the trailing flags, copies both files into the run directory's `warm/` and
  re-points the flags, so `--remote` is no longer a cold-run-only mode and an
  iterate has the same shape locally and on the box. Tested against the real
  script with stand-in `ssh`/`rsync`; still no dispatch.
- [x] **The walk names section misses and their rollout movement**
  (2026-09-08, ADR-277). Exact published identities join uncut objects to
  translation and rotation; unavailable or ambiguous matches remain unknown.
  Fixture regressions cover pure rotation, translation, stationary components,
  shared source instances and missing motion.
- [x] **The section eye derives its own plane when called by hand**
  (2026-09-08, ADR-275). `cadex section --plane XZ` with no `--offset-mm`
  now takes the derived path the walk has used since ADR-267; the flag's
  old `default=0.0` made that path unreachable from the command line, so a
  hand caller got exactly the constant derivation replaces. The note reports
  the offset, `explicit` or `derived`, and the objects-cut count. Explicit
  offsets, the derivation itself and the walk are unchanged.
- [x] **The walk's section cuts where the geometry is** (2026-09-08, ADR-267).
  The review's offset is derived from the accepted snapshot's own bounds --
  most objects' bounds crossed, first supported cut wins -- instead of a
  literal 3.125 mm that reported `ok` while missing the ot4-quill's moving
  part in all six recorded runs. `cadex section --offset-mm` is unchanged.
- [x] **Correct lifecycle history promises** (2026-09-08, ADR-266).
  Remove unconditional repository/commit claims from the lifecycle audit;
  point to ownership rules and clarify the scaffold commit-success signal.
- [x] **Retain recent decisions in prompt context** (2026-09-08, ADR-265).
  Keep the bounded ADR tail; overflowing-log regressions cover fresh and resumed
  turns, unchanged limits, architecture/domain selection and preserved source files.
  *Gone with `cadex -p` (ADR-538).*
- [x] **Preserve project docs on failed updates** (2026-09-08, ADR-264).
  Progress, decisions and domain notes replace only fully written files; partial
  write and replacement-failure regressions preserve history and verify retry.
- [x] **Pin project history on resumed agent turns** (2026-09-08). Real-engine
  regression delivers prior decisions/domain notes and between-visit edits to
  the resumed prompt, and preserves old notes when new decisions/notes land.
  Provider behavior and a history-guided trained iterate remain unmeasured.
  *Gone with `cadex -p` (ADR-538).*
- [x] **Identify comparison seeds, objective and action scaling** (2026-09-08,
  ADR-263). Train/walk rows carry current and prior evidence; review JSON keeps
  exported objective fields and actions. Legacy rows remain explicitly unknown.
- [x] **Keep generated review outputs local and explain policy exclusions**
  (2026-09-08, ADR-262). Fresh scaffolds ignore `/review/`; explicit policy
  exclusions go after the root policy negation. A real Git regression inspects
  commit trees, retained files, tracked history and pre-staged content.
- [x] **Preserve stopped descendants' cleanup grace** (2026-09-08, ADR-261
  correction). A monotonic deadline keeps the full grace when the direct child
  exits immediately; a delayed descendant cleanup regression fails on the old
  code. The final group kill remains unconditional.
- [x] **A walk's `PROGRESS.md` row carries a delta** (2026-09-08, ADR-260).
  Measuring ADR-259's motion cell against ADR-194's comparison found neither
  half worked for a walk: `_record_progress` passed `previous=` only on the
  non-walk branch, so **no walk row had ever carried a delta for any figure**,
  and `motion N mm (component)` was unreadable by `_NUMBER_RE`, which wants
  `<label> <number>`. The cell is now `motion travel_mm N on <component>,
  travel_deg N on <component>`, `COMPARED_NUMBERS` gains both travel labels,
  and the walk branch reads `previous_numbers()` like every other. The
  carriage pair is the worked example: travel held at 103 mm while
  `total_reward` fell 3.296 → 2.760, and the row can now say both — without
  ranking them, since a delta is not a verdict. One spelling for row and
  note; `review.json` untouched. The real-engine lifecycle regression asserts
  the first walk carries no delta, the second carries one on each channel,
  and the row still fits 320 characters with its documentation finding.
- [x] **The walk reports whether the mechanism moved** (2026-09-08, ADR-259).
  `review.json` gains a `motion` block beside `clearance`, and the walk's
  `PROGRESS.md` row and notes gain a motion cell: per component the per-axis
  position range, the largest displacement from the first solved frame, and
  the largest rotation swing from its orientation. Two channels always, and
  neither ranked against the other — the repository's own hinged arm travels
  0.0000 mm and rotates 178.8334°, so a millimetre-only row would call a
  working revolute rig motionless. Only solved frames count (frame 0 is the
  solver's input pose), an all-identical trace reports zero rather than
  unavailable, and the progress row's numbers cell grows to 320 characters so
  motion does not truncate the documentation half off the row.
- [x] **The lifecycle examples reproduce on a second machine** (2026-09-08,
  ADR-257). Both documented recipe walks re-run unchanged on `sb1x`, exit 0,
  trainer means bit-identical and rollout totals agreeing to the JAX build's
  summation order; the README's dead `--trainer-python` path is replaced by the
  documented discovery order, and both examples gain the `docs/actuators.md`
  their own ADR-256 review asked for.
- [x] **Walk inventory history contract** (2026-09-08, ADR-254). Measured
  a component rename after a public walk: latest report advances, saved counts
  stay fixed and Git retains original rows; guide and scaffold distinguish them.
- [x] **Shared toy CPU test selection** (2026-09-08, ADR-253). Real train,
  iterate and walk tests request one CPU fixture and assert receipt devices.
- [x] **Failed retraining preserves history and retries successfully**
  (2026-09-08, ADR-252). Real-engine regression injects partial output/exit 7,
  then resumes the retained sweep with the prior successful policy/task. It
  pins prior hashes/history, verified new policy, all four reviews and the
  last successful comparison references; CLI §2 gives the tested command.

- [x] **Correct the walk progress-row guide** (2026-09-08, ADR-238).
  Child reward/delta rows and the successful walk's clearance row are distinct;
  failed legs add no walk review row. Existing CLI behavior and tests retained.

- [x] **Shorten the carriage iterate guide** (2026-09-08, ADR-251).
  Retain the command, comparable rewards, baseline and limits; link the
  immutable rehearsal evidence instead of repeating its detailed log.

- [x] **Model-free iterate comparison on the durable carriage** (2026-09-08).
  Width 70 → 80 mm through unchanged `walk --set`, cold CPU 5 × 16 seed 0:
  exit 0 in 20.89 s; same reward and 200-step horizon, total 3.296298 →
  2.760187, comparison automatically committed to project `PROGRESS.md`.
  All four review eyes inspected; 56-file engine report matches. Baseline
  bytes preserved. Single-seed toy evidence and command in `docs/CLI.md` §2.

- [x] **Parameter-only quill iterate with objective comparison** (2026-09-08).
  Stroke 40 → 60 mm, CPU 5 × 16 seed 0, finite leg bounds: exit 0;
  reward +250.279186, travel +9.794917 mm / 0 degrees. Objective fields
  match; geometry and action bounds differ. Evidence and limits: CLI §2.

- [x] **Fixed-geometry quill reference with current comparison identities**
  (2026-09-08). CPU 5 × 16, training seed 0 / rollout seed 7; unchanged
  stroke 60, MJCF and task. Exit 0, 24.84 s, peak 1.99 GB; all review
  outputs local and new generated artifacts excluded. CLI §2 carries
  exact reward/travel and identity hashes; continuation is recorded below.

- [x] **Fixed-geometry quill seed spread, seeds 1–3 against seed 0**
  (2026-09-08). All legs pass at CPU 5 × 16 and rollout seed 7;
  inputs/identities match, each walk <26 s and <2 GB peak tree RSS.
  Four-seed reward range 170.952827–175.935972, travel 30.078469–31.421760 mm
  / 0 degrees; CLI §2 and project PROGRESS retain individual measurements,
  explicit references and the action-midpoint caveat. This direction is spent.

- [x] **Attempt a fresh mixed-joint crank-slider walk** (2026-09-08,
  iteration 48; `docs/CLI.md` §2). `claude-opus-5` refused design at its
  session limit: exit 1, 1.94 s design, 2.003486 s total, 382,861,312 bytes
  peak tree RSS. No later leg or eye ran; fresh crank-slider success remains
  unevidenced. This checkbox records the experiment, not lifecycle completion.
- [x] **A fresh mixed-joint crank-slider walk reaches geometry** (2026-09-08,
  iteration 52; ADR-280, `docs/CLI.md` §2). Design exit 0 in 1135.85 s against
  `claude-opus-5`: a four-body closed-loop slider-crank, mobility 1, worst
  closure residual 0.0015 mm, with `DECISION:` lines and `linkage-geometry`,
  `actuators` and `sensors` notes landed in the project. The train leg then
  failed in 2.27 s — `mjx.put_model` does not implement cylinder-box
  collisions, so the guide rail is untrainable under MJX though the MJCF is
  valid. 1138.30 s total, 729,931,776 bytes peak tree RSS, no watchdog
  intervention. Declare, rollout and all four eyes were not reached. This
  checkbox records the experiment and the geometry result, not lifecycle
  completion.
- [x] **A failed training leg names its cause in the envelope** (ADR-280,
  2026-09-08). `run_trainer` tees the trainer's stderr instead of only
  inheriting it, so the `--json` error carries the crash rather than two
  benign stdout warnings. Regression fails on the previous source; 24 CLI
  train tests pass.
- [x] **A training task is refused when MJX cannot build its model**
  (ADR-281, 2026-09-09, `docs/MUJOCO.md` §5 hazard 20). `assembly.task`
  enumerates the exported model's candidate collision pairs and refuses the
  four MJX has no contact function for — box/cylinder, cylinder/mesh,
  box/ellipsoid, ellipsoid/mesh — naming both geoms, both bodies and both
  kinds. The filter is written out rather than imported, because the engine
  may not import MJX; it reproduces `mjx.geom_pairs` exactly on the walk's
  own exported model, where it names the cylinder rail against the coupler
  box that `mjx.put_model` refused. `assembly.mjcf` and `assembly.rollout`
  are untouched. Regression fails on the previous source; engine suite 2099
  passed / 54 skipped, CLI suite 289 passed.
- [x] **Fresh walk survives a cold public CLI revisit** (2026-09-08).
  Accepted revision/digest, policy assets, trace and review geometry survive
  separate script/asset/inventory/clearance/render/section processes. Expected
  restore attempts and report refreshes are distinguished from lost artifacts;
  evidence in `docs/probes/cold-revisit/`. No persistence correction needed.
- [x] **The agent can name what it assembled, headlessly** (ADR-236,
  `docs/CLI.md` §2). `cadex inventory` writes `docs/inventory.md` in the
  project: one row per component with the output it places, its catalog
  family and part number where a `lib.*` generator built it, the solved
  pose and its volume, plus a roll-up and the hand-modelled outputs that
  have no catalogue row. Behind it, `inspect scope="inventory"` joins the
  ADR-049 `source_output` stamp to a new `catalog` stamp on library-value
  outputs — written beside the definition, so the content digest cannot
  move. No protocol change and no `shell/` diff. Qualified against a real
  engine building a plate with two catalogued M3 bolts. **The first of the
  four headless review calls**; render-from-angles and section view, each
  with walk integration, remain open.
- [x] **Stale shell mutations preserve accepted work** (ADR-204).
  Remove automatic revision adoption/replay after `STALE_PROGRAM_REVISION`.
  Script and parameter edits remain refused until explicit refresh; headless
  regression covers a foreign accepted script, repeated refusal, successful
  editing after Rebuild Model, and a synthetic refusal with a newer guard.
  Current engine stale responses omit that guard; the prior claimed overwrite
  was not reproduced. The dormant retry is removed defensively.
  Shared locking and simultaneous acceptance remain outside this fix.
  *The shell went with ADR-498.*
- [x] **A trained policy comes home headlessly** (ADR-190). `cadex asset
  --put walk.cxpolicy` for a pipeline and `put_asset` in the CLI agent's
  tool surface, both on the op the shell has had since ADR-043; the
  envelope's `assets` rows carry the sha256 `assembly.policy` names. The
  lifecycle audit's row 5 (`docs/MUJOCO.md` §7c) closes; the `cadex train`
  dispatcher (item 3) is next.
- [x] **The training leg is one command** (ADR-191). `cadex train --out
  DIR --iterations N --envs N --put` rebuilds, exports the bundle, runs
  `training/cadex_train.py` under the training venv with its real flags,
  and stores the policy with its sha256 in the envelope. Training stays
  offboard (ADR-084): a subprocess, and no venv is ever created. §7c row 4
  closes; the iterate shape (item 4) is next.
- [x] **Iterate is a script convention, not a flag** (ADR-192). The
  policy is declared behind a numeric switch parameter; `cadex params
  --set policy_on=0 --set <change>` is accepted and exports the bundle
  at its new digest, `cadex train` carries the ADR-161 curriculum pair
  for the warm retrain, and `cadex script --set` plus `params --set
  policy_on=1` re-declare. Run headlessly on the §7b toy and pinned by a
  real-trainer test. §7c row 8 closes; compare-and-record (row 9) and
  the project scaffold (row 10) are next.
- [x] **The project is a codebase** (ADR-193). The CLI scaffolds
  `ARCHITECTURE.md`, `DECISIONS.md` and `PROGRESS.md` on the first visit,
  pastes them into every turn's prompt, lands one `PROGRESS.md` row per
  accepted run with the numbers, and turns a turn's closing `DECISION:`
  lines into numbered `DECISIONS.md` entries; `docs/<subject>.md` is the
  domain-doc convention. No engine change, no file tool for the agent.
  §7c row 10 closes. *Since ADR-538 the CLI scaffolds and appends
  `PROGRESS.md` only; the person's agent reads the documents and writes
  `DECISIONS.md` and the notes itself (`cli/cadex_cli/project_docs.py`).*
- [x] **A project's own architecture survives its guide** (ADR-279). Prompt
  context bounds `ARCHITECTURE.md` from both ends, so a scaffold that outgrows
  the budget no longer evicts what the project wrote below it; regression built
  on the real scaffold. *Gone with `cadex -p` (ADR-538).*
- [x] **The walk detaches in two halves** (ADR-282). `walk --remote --detach`
  stops at pending with `walk-pending.json` under `--out` — the locator, the
  bundle it was launched against, the seed, and the two commands that finish
  the run — declaring and storing nothing; `walk --complete` collects the
  policy the dispatcher brought home and runs the same `declare`, `rollout`
  and review legs, refusing a run that is not `done`, a policy that does not
  hash to the trainer's receipt, and a bundle that moved under the run.
  Tested against a stand-in dispatcher and a local run destination; no ssh
  and no box.
- [x] **Detached train reports pending honestly** (ADR-278). Project-local run
  receipt, preserved prior policy, no verify/store or completion claims; tested
  with the real dispatcher over local transport stand-ins.
- [x] **Project model continuity survives a refused override** (ADR-276).
  Prompt and walk turns resolve flag, environment, recorded model, default;
  failed turns with the same session ID preserve the previous record.
  *Gone with `cadex -p` (ADR-538).*
- [x] **Unchanged CLI sessions preserve their metadata** (ADR-247).
  Refused and successful turns retain agent.json when session ID and model
  match; changed session IDs persist even on failure. Restore attempt metadata
  remains truthful; offline walk regressions preserve pre-existing user edits.
  *The turn's session half went with `cadex -p` (ADR-538); `agent.json`
  remains the CLI's own state file.*
- [x] **A domain note lands the way a decision does** (ADR-245). The
  `docs/<subject>.md` convention was documented and unreachable — the
  agent has no file tool and the instruction told it to ask its caller,
  and a headless walk has no caller. A closing `NOTE <subject>: <text>`
  line now appends a dated bullet to `docs/<subject>.md`, the notes are
  pasted back into the next turn beside the three documents, and the
  design instruction asks for `docs/actuators.md` and `docs/sensors.md`
  from any mechanism with actuators or sensors. `inventory.md` and
  `clearance.md` are the CLI's generated reports and are refused as
  subjects. CLI suite 197 passed, no skips. *The `NOTE` and `DECISION:`
  lines went with `cadex -p` (ADR-538): the agent has files of its own now.*
- [x] **Compare and record, in a repository the project owns** (ADR-194).
  A `PROGRESS.md` number an earlier row carried is written with its
  change against that row (delta, digest, value), so the comparison is
  one recorded row. Outside another work tree, a fresh root is initialized
  with default ignore rules only if absent; existing root repositories keep
  their rules. Accepted runs attempt to commit all working changes with the
  row's words as the message. Nested projects without their own `.git` get
  rows but no automatic commits, leaving the parent index untouched. Measured
  on the §7b toy's scratch copy; pinned by `cli/tests/test_project_docs.py`. §7c row 9 closes.
- [x] **The `INSPECTION_FAILED` frame is the one tool-failure envelope**
  (ADR-195). `complete_inspection`'s refusal is built by `tool_failure`,
  validated by a test and pinned by an `inspect.failure` golden, so an
  inspect exception reaches the validating CLI as a refusal rather than a
  hard client error. §7c item 5 closes; the lifecycle frontier is empty
  on the engine side.
- ~~**Linux and Windows shell bundles.**~~ Moot: the shell is deleted
  (ADR-498) and Phase 12 superseded (ADR-500).

## 3. Live headless project review (ADR-284), run ot5

*Closed: the owner ticked D1–D11 on 2026-09-13 (`STATE.md`, `crisp-sun-1239`),
so the "remains open" clauses below are as written at the time. The
persistent operator server (`tools/operator_review.py`, ADR-299) is deleted
(ADR-536), and since ADR-537 the dashboard (`cadex app`, `cadex review`)
writes nothing.*

- [x] Lark interruption, retry and retry video on the working copy (ADR-315):
      a real GPU attempt interrupted by SIGINT and shown failed with retry
      guidance and no substituted video on the persistent dashboard, a
      successful 40-update new attempt, its verified playable/downloadable
      video, earlier results preserved and the original byte-identical after
      the copy's retraining. D8 and D7's retraining half now have Lark evidence.

- [x] Lark copy isolation on the persistent dashboard (ADR-314): whole-project
      copy `ot5-lark-copy85` served on port 8765, edited through the CLI and
      restored with the original path unavailable; six retained runs and four
      videos review from the copy on two servers; the original is byte-identical.

- [x] Lark's review-driven revision, retraining and declared-seed comparison
      (ADR-313): the product agent chose `torso_h` 70 → 45 mm from `lark1`'s
      measurements, `lark2` retrained it on the persistent dashboard with
      checkpoint and final videos, and all four retained policies were compared
      on seeds 0–9 from their own retained models. Survival on every seed for
      the revision; one training seed per design, not a gait claim.

- [x] Current-attempt default and persistent Reed operator server (ADR-299):
      active training first, newest attempt otherwise; preserve deliberate history
      and playback, with a route back to current. Private-address browser check
      passes on the real working copy; D10 experiment-spanning evidence remains.

- [x] Share cold retained-video verification across concurrent browser clients
      (ADR-298), with two-client corruption refusal and bounded-cache eviction tests.

- [x] Bound retained-video digest memory and reuse unchanged verification
      (ADR-296): 64-file/16 GiB synthetic history measured through HTTP and
      headless-browser telemetry, with corruption/refusal/recovery regression.
      Cold reads and cache eviction retain their full hashing cost.

- [x] Retained training telemetry and dashboard polling (ADR-287): bounded
      reward/loss/episode histories, checkpoint integrity and missing/stale/failed
      states, verified across atomic updates in a headless browser. D3's actual
      fresh-biped GPU observation remains open; fixture evidence does not tick it.

- [x] Bounded operation over long histories: the run list carries a telemetry
      summary per run and histories/verified checkpoints travel per selected run
      (ADR-321); the same detail carries per-run disk use counted from permitted
      files, each inode once, no symlink followed, with shared project references
      sized once and missing/refused references named (ADR-322). Both verified
      on the persistent Lark dashboard and in headless-browser regressions.

- [x] Final policy publication failures publish failed telemetry (ADR-288),
      retaining metrics/checkpoints with headless browser fault-injection evidence.
      The real interrupted runs and new attempts are Wren's `wren57-*` (ADR-305)
      and Lark's `lark86-*` (ADR-315).

- [x] Dashboard restart lifecycle test (D6, fixture half): the real `cadex review`
      command stopped and restarted on its port under an independent telemetry
      producer; the open page recovers without reload, a reopened page reads the
      same identities, curves, history and video, the producer is neither stopped
      nor duplicated, and no project file changes. D6's fresh-biped pass with real
      artifacts and its engine restart remain open.

- [x] Engine restart during real training (D6, ADR-325): on the persistent Lark
      copy, a public `cadex export` had its engine SIGKILLed mid-work and the next
      `cadex export` started a fresh engine while a bounded GPU run trained; the
      killed call exited 1 naming the closed stream, no engine or worker outlived
      it, the trainer kept its PID and start ticks, the open page kept receiving
      committed telemetry, and accepted identity and earlier run files were
      unchanged (`docs/probes/lark-fresh/ENGINE109.md`). Same-machine browser only.

- [x] The fresh biped exists and trained once on the GPU: `ot5-biped` was
      authored by the product agent on the default model after three quota
      refusals (no model override needed); a 40 × 1024 PPO probe stored its
      policy in 90 s under the memory bound, and the live dashboard was observed
      against it (`docs/HEADLESS-BIPED-REVIEW.md`). The walk failed at declare
      because the fresh script has no `policy_on` switch, and a running or failed
      run shows no model identity; both are open defects, D2–D9 stay open.

- [x] A run is identified from its first record (ADR-289): the walk records
      the manifest's revision, digest and specs before training and each leg's
      reported identity after it, a failed run keeps the last one, and a run
      with no rollout is drawn from the accepted attempt only when both halves
      of its identity are the accepted ones now. Browser-tested through failure
      on fixtures; the `policy_on` defect and the real-artifact passes stay open.


- [x] Freeze assembled review inputs before walk training (ADR-291): run-local
      meshes, component mappings/placements, parameter specs and document snapshots
      survive accepted-design changes and staging pruning, verified in a headless
      browser. Older missing history is not reconstructed; the real D5/D9 design
      change and retraining remain open.
- [x] Retain tessellation on ordinary parameter sweeps (ADR-293): real-engine
      `walk --set` browser regression checks the assembled model before trainer
      dispatch and preserves its identity and mesh bytes across a later revision.

- [x] Byte-identical outputs each keep their accepted tessellation (ADR-302):
      a mirrored pair of limbs no longer loses one side in the accepted view or
      the retained training view; regression on two identical thighs. Exposed
      by the persistent dashboard during the Reed shin55 experiment.

- [x] Shared reference environment for the live review viewport and headless
      checkpoint/final videos (ADR-301): local attributed Three.js scene, exact
      retained poses, fixed trajectory camera, portable style identity and
      retained legacy recordings; real Reed same-camera/frame comparison.

- [x] Lifecycle report for the fresh biped (D9): `docs/probes/reed-lifecycle/`
      assembles the D1–D8 evidence index, twelve retained run identities with
      the model view served for each (incomplete training snapshots named),
      and the four-design common-seed comparison from the project's records;
      a test holds the committed report to its evidence. Survival improved,
      no design walks; the checkbox edit is the owner's.


- [x] Advisory static fit intent (ADR-347, ot7 F2): assembly contact pairs and
      minimum-clearance triples annotate published measurements; overlaps,
      missed contacts, insufficient gaps and world geometry reach the agent.
      Failing fit still accepts, with real-kernel defect fixtures and accepted
      identity preserved across reopen. Swept fit remains a separate frontier.

- [x] Bounded accepted-design smoke command (ADR-352, ot7 F8): retained
  artifacts, finite-state and support checks, exact BREP overlaps at sampled
  dynamics poses, known passing/failing CLI fixtures, and a shared five-minute
  simulation/measurement bound. No acceptance or project-script execution.
