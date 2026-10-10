# CLI-EVIDENCE.md — CLI.md's dated evidence and old dashboard prose

> **HISTORICAL (moved to `docs/history/` 2026-10-10, ADR-631).** Dated records cut out of `docs/CLI.md`; never cite them as current. The live doc is `docs/CLI.md`.

Moved verbatim from `docs/CLI.md` §2. Each passage is the record of what was
measured or shown when it was written; flags such as `walk --prompt` and
`$CADEX_MODEL` are gone (ADR-538).

## 1. Copy proofs on real projects (Wren, Lark)

The [real Wren copy lifecycle](../probes/wren-fresh/COPY.md) supplies an executable
engine/browser check with the original path unavailable throughout a copy-only
parameter edit and two restores, plus retained model/curve/video checks on the
then-persistent operator URL and a second server.
The [Lark copy lifecycle](../probes/lark-fresh/COPY85.md) repeats it on the third
fresh project with the same driver made project-agnostic: the default run and
the parameter changes are arguments (`docs/probes/lark-fresh/copy_lifecycle.py`).
The [Lark interruption probe](../probes/lark-fresh/INTERRUPTION86.md) then retrains
the copy (an interrupted attempt, a completed one and its video) with the same
project-agnostic treatment (`docs/probes/lark-fresh/interruption.py`) and checks
the original's inventory again afterwards.

This test uses synthetic fixtures. The separate
[real Reed copy lifecycle](../HEADLESS-BIPED-REVIEW.md#independent-real-project-copy-d7)
records a whole-project copy, physical revision and bounded GPU retraining,
then engine reopen and three-design browser/video review with the original
path unavailable and every original file unchanged.

## 2. Walk rehearsals on real projects (ot4, 2026-09-08 → 2026-09-09)

**Model-free carriage iterate rehearsal (2026-09-08).** On the durable
`ot4-carriage` project, the unchanged public entry point ran:

```bash
JAX_PLATFORMS=cpu ./cadex walk --project "$PROJECT" \
  --out "$PROJECT/runs/iterate-1" --set carriage_wid=80 \
  --name lift_iterate1.cxpolicy --iterations 5 --envs 16 --seed 0 \
  --timeout 600 --json
```

Width increased from 70 to 80 mm; task bundles differed only in `model`,
keeping the objective, episode, observations and randomisation fixed.
Both verified rollouts used seed 7 and 200 steps (4 s): reward
**3.296298 → 2.760187** (delta **-0.536111**), with the comparison written
into `PROGRESS.md`. All 21 baseline files, including the policy, retained
their bytes. All four legs and review passed; the four review eyes check
only the initial pose, not swept motion or printable fit. One cold training
seed at toy scale does not establish a general design ranking.

See [ADR-251](../DECISIONS.md#adr-251--the-walk-reports-enginesource-differences-before-its-first-leg-2026-09-08)
and the [immutable rehearsal record](../../.hypergraph/graph/record/mellow-quartz-8093.md)
for timings, policy witness, component volumes and project commit evidence.

**A third mechanism, and what its second coordinate measured (2026-09-08).**
The unchanged entry point also ran a *quill lift* rig on the durable
`ot4-quill` project: one **cylindrical** joint — a slide and a hinge on the
same axis — driven by a **position servo on its linear coordinate**, which
is the fourth and last `(kind, motion)` pair the engine derives an action
range for. A **velocity** actuator cannot be the third variable: the engine
refuses one at `action_range_underivable`, because a joint states position
limits and nothing in an assembly states a speed. Exit 0 in 10:53 at 5
iterations x 16 envs, seed 0, `total_reward` -74.79 over 200 steps. The
motion block read **`travel_mm 20.28`, `travel_deg 0` on the same
component**: the joint offers both channels and the rollout used one, since
gravity exerts no torque about a vertical axis. A zero in a channel is a
fact about that rollout, not a missing measurement, which is why both are
always written. No delta rendered on that row, correctly — a project's
first walk has no previous row carrying either label. The clearance eye
returned its first offending pair on an agent-authored design: `housing`
against `quill`, verdict `intersection`, 960 mm3 of common volume. That one
is deliberate and the project says so itself — its ADR-005 records that the
shaft is modelled inside a solid bore cylinder and that the joint, not
contact, constrains the quill — so the report is a known choice read back
rather than a defect found. The walk still exits 0, as the table above says
it should: the report was written, and reading it is the next design turn's
job.

**Quill parameter-only iterate (2026-09-08).** With `PROJECT` pointing at
that same project, the bounded, unchanged entry point ran:

```bash
JAX_PLATFORMS=cpu ./cadex walk --project "$PROJECT" \
  --out "$PROJECT/runs/stroke60-iterate29" --set stroke=60 \
  --name quill_stroke60_29.cxpolicy --iterations 5 --envs 16 --seed 0 \
  --timeout 600 --leg-timeout 120 --json
```

Exit 0 in 24.61 s, peak process-tree RSS 1.98 GB (0.2 s monitoring;
2.9 GB / 850 s external cutoffs). All four legs and four review calls
succeeded; the 56-file engine/source comparison matched. Actual parameters
differ only in stroke, 40 → 60 mm. Exported task JSON differs only in model
metadata and the action upper bound, 40 → 60 mm: reward expressions and
weights, observation units, termination, randomisation, disturbance and
4 s / 200-step horizon are identical. Both verified rollouts use seed 7.

| Measurement | Baseline | Stroke 60 | Exact delta |
|---|---:|---:|---:|
| Rollout total reward | -74.791975 | 175.487211 | +250.279186 |
| Quill travel mm | 20.283552 | 30.078469 | +9.794917 |
| Quill travel degrees | 0 | 0 | 0 |

The reward delta lands in the rollout's `params` row; both travel deltas
land in the `walk` row of `PROGRESS.md`. Its displayed **+9.798 mm** uses
the baseline row's rounded **20.28**, not the full-precision review value.
Trainer reward/step fell from -0.579622 to -1.019691; it measures a different
batch. The target remains 30 mm, now the midpoint of the action range, so
near-zero normalized actions already command it. Geometry and action scaling
changed together; this cold single-seed toy run cannot establish significance
or better control. The housing/quill intersection remains 960 mm³ in the
initial pose; the XZ section misses the quill. All 19 baseline run files
retained their bytes. New generated artifacts remain local after a forward
project commit removed outputs that the CLI had automatically staged.

**Fixed-geometry quill seed reference (2026-09-08).** The same project,
already at stroke 60, ran the command above without `--set`, using fresh
`runs/stroke60-seed0-33` and `quill_stroke60_seed0_33.cxpolicy` names.
CPU 5 × 16, training seed 0, rollout seed 7, trainer timeout 600 s and
leg timeout 120 s; the same external 0.2 s watchdog retained its
2.9 GB / 850 s cutoffs. Exit 0, 24.835810 s wall (24.685678 s reported
walk), peak tree RSS 1,986,134,016 bytes. Trainer time 3.773088 s,
reward/step -1.019690990448, witness error 2.092e-08.

The reference total reward is **175.487211145051**, travel
**30.078469436328 mm / 0 degrees**, over 200 steps / 4 s.
Parameters, exported MJCF bytes and full task JSON match the stroke-60
iterate; only policy filename and digest changed in the script. Recomputed
comparison hashes match: objective `v1:ddee1f6a0bae7c4753c06a17fa09dd3db9799de30d823c4e4586e41868a937dc`,
actions `770b4e2f0899853fed23b8727ea08f607ceef3c383189357f27c02179cc30882`.
Both seeds and identities are recorded in project `PROGRESS.md`; prior-row
identity remains `unavailable (legacy row)`.

All four render views exist; the XZ section still misses the quill;
inventory lists two uncatalogued components; clearance names the same
960 mm³ housing/quill intersection. The engine/source comparison matches
56 Python files. All 48 earlier run files retain their bytes. Explicit
root exclusions after the policy negation kept every new run, stored policy
and review output out of project commits; historical tracked output stays
untouched. This is the seed reference, with the 30 mm action-midpoint
confound unchanged, not evidence of learned improvement. Seeds 1–3 were
the selected continuation, measured below.

**Fixed-geometry seed continuation (2026-09-08).** Seeds 1, 2 and 3 each
completed all three walk legs and four review calls. The command is the
reference command with `--seed N`, `--out "$PROJECT/runs/stroke60-seedN-34"`
and `--name quill_stroke60_seedN_34.cxpolicy`, substituting N = 1, 2, 3.
CPU 5 iterations × 16 environments, rollout seed 7, trainer timeout 600 s,
leg timeout 120 s and the 0.2 s tree-RSS watchdog (2.9 GB / 850 s) were fixed.

| Training seed | Total reward | Travel mm | Travel deg | Wall s | Peak tree RSS bytes |
|---:|---:|---:|---:|---:|---:|
| 0 | 175.487211145051 | 30.078469436328 | 0 | 24.835810 | 1986134016 |
| 1 | 175.935971673601 | 31.421759939733 | 0 | 23.783088 | 1994547200 |
| 2 | 170.952826823611 | 31.360988060147 | 0 | 24.625217 | 1986662400 |
| 3 | 172.081298535925 | 31.085486620484 | 0 | 25.470796 | 1997832192 |

Comparison references are `runs/stroke60-seed0-33/review.json` and
`runs/stroke60-seed{1,2,3}-34/review.json` in the same quill project.
Across these four seeds, reward ranges **170.952826823611–175.935971673601**
(span 4.983144849990), translational travel **30.078469436328–31.421759939733 mm**
(span 1.343290503405 mm), and angular travel stays **0 degrees**.
These are descriptive ranges, not significance, a winner or learned
improvement: the 30 mm target remains the action midpoint, which near-zero
normalized actions already command. No further seeds follow this measurement.

Every exported MJCF and full task JSON is byte-identical to seed 0; the
full parameter map, objective and actions match the reference hashes above.
Both training and review comparison metadata carry the requested training
seed, and review carries rollout seed 7. Script changes are confined to
policy filename/digest. Project PROGRESS rows retain explicit previous
comparison identities; rounded row deltas are not the full-precision ranges.
Trainer durations for seeds 1/2/3 were 3.628307/3.878131/3.883964 s;
reward/step -1.016377091408/-1.313315391541/-1.432229399681 and witness
errors 2.700e-08/2.926e-08/3.163e-08. These training batch rewards differ
from the verified 200-step, 4 s rollout totals in the table.

All named render files and section/inventory/clearance outputs exist locally.
The XZ section at 3.125 mm still misses the quill -- the measurement that
ADR-267 later answered by deriving the offset -- inventory has two
uncatalogued components, and initial-pose clearance still reports the
960 mm³ housing/quill intersection with no unknown pairs. Each run verified
all preceding run files unchanged (75/102/129 files respectively); prior
policy hashes, script history and unrelated tracked content are preserved.
Fresh root output and policy exclusions follow the default policy negation;
new run/policy/review paths are absent from the index and committed trees.
This is additional evidence for the existing headless walk and review
criteria, with no runtime, entry-point or project-scaffold behavior change.

*The four dated runs below (`ot4-crank48`, `ot4-mix52`, `ot4-mix55`,
`ot4-cart`) began with a design leg, `walk --prompt`, that ADR-538 removed:
today the person's own agent designs through `cadex mcp` and the walk starts
from the project it left. They stay as evidence of what was measured, not as
commands to run.*

**Fresh crank-slider attempt (2026-09-08, iteration 48).** A new
`ot4-crank48` project (only output exclusions existed before invocation)
was prompted for a grounded frame, position-servo revolute crank, coupler
and prismatic slider, with masses, task, policy switch and domain notes.
`ot4-crank` already existed, so this attempt used a distinct root and no
`--resume`. The command was `CADEX_MODEL=claude-opus-5 JAX_PLATFORMS=cpu
./cadex walk --project "$PROJECT" --prompt "$PROMPT" --out
"$PROJECT/runs/fresh48" --name fresh48.cxpolicy --iterations 5 --envs 16
--seed 0 --timeout 600 --leg-timeout 1800 --json`.

| Leg or measurement | Result |
|---|---|
| Design (`claude-opus-5`) | Exit 1, 1.94 s; provider reported “You've hit your session limit” |
| Train / declare / rollout | Not reached |
| Render / section / inventory / clearance | Not reached; review block empty |
| Total reward / witness error | Unavailable; no training or rollout |
| Whole invocation | Exit 1, 2.003486 s |
| Peak process-tree RSS | 382,861,312 bytes, sampled every 0.2 s |

No watchdog intervention occurred (2.9 GiB memory guard; trainer bounded
by 600 s). The source comparison reported one differing file out of 56,
`cadex_assembly_worker.py`, from pre-existing uncommitted edits; this
attempt neither changed nor built the engine. The refusal preceded geometry,
so it provides no evidence about crank-slider solver support. The project
has scaffold documents but no accepted revision or progress row. Its local
`runs/fresh48/` retains the envelope, stderr and monitor receipt, excluded
from Git along with policy and review output. This leaves the fresh
mixed-joint walk unevidenced; the model refusal is the observed stopping
point, with no retry scheduled against a clock. Runtime and scaffold
behavior are unchanged.

**Measured fresh crank-slider walk, `ot4-mix52` (2026-09-08).** The same
invocation into an empty project, with `--iterations 5 --envs 16 --seed 0
--timeout 600 --leg-timeout 1800`, reached geometry this time.

| Leg | Result |
|---|---|
| Design (`claude-opus-5`) | **Exit 0, 1135.85 s**; accepted revision `3892e8cd…`, digest `df4ee45f…` |
| Train | Exit 1, 2.27 s; `mjx.put_model` raised `NotImplementedError: (mjGEOM_CYLINDER, mjGEOM_BOX) collisions not implemented` |
| Declare / rollout | Not reached |
| Render / section / inventory / clearance | Not reached; review block empty |
| Total reward / witness error | Unavailable; training produced no policy |
| Whole invocation | Exit 1, 1138.30 s |
| Peak process-tree RSS | 729,931,776 bytes, sampled every 0.2 s |

No watchdog intervention (2.9 GiB guard). The engine source comparison
reported `match` across 56 files against a freshly built and installed
engine. The design turn produced a four-body closed-loop slider-crank —
grounded frame with a round guide rail, an 11.3 g crank on a revolute
driven by a 250 N·mm position servo, a 25.7 g coupler and a 38.3 g slider
block on a prismatic joint — mobility 1, one MuJoCo `connect` closure,
worst closure residual 0.0015 mm over a 2 s driven run, peak servo effort
17.3 N·mm unsaturated. It refused the all-revolute version as redundant and
spent the three surplus 3D constraints on a cylindrical crank pin and a
ball wrist pin rather than disconnecting anything, which is what the prompt
asked for. Four `DECISION:` lines and three notes (`linkage-geometry`,
`actuators`, `sensors`) landed in the project.

*(The tail of the MJX geom-pair paragraph, which stays in CLI.md:)* Local evidence is in
`runs/fresh52/{walk.json,walk.stderr,monitor.json}`, excluded from Git.
This leaves the fresh mixed-joint walk **evidenced through design and
stopped at train**, with the stop moved forward into the design turn that
can act on it.

**The same fresh walk, end to end, `ot4-mix55` (2026-09-09).** The identical
prompt into a second empty project, same flags, against a freshly built and
installed engine (source comparison `match` across 56 files), **completed every
leg**.

| Leg | Result |
|---|---|
| Design (`claude-opus-5`) | Exit 0, 1649.63 s; accepted revision `70fd2a53…`, digest `ee279ea9…` |
| Train (CPU, 5 it × 16 envs, seed 0) | Exit 0, 26.71 s; reward/step −0.4055 at best iteration 4, 4,609 parameters, 5.20 s trainer wall time |
| Policy verify | Witness error 1.14e-08 against a 1e-04 tolerance over 32 samples |
| Declare | Exit 0, 0.81 s |
| Rollout (`policy_on=1`) | Exit 0, 1.53 s; total reward −19.85 over seed 1 |
| Render | Four views (front, iso, right, top), 4,756 triangles, 0.90 s |
| Section | Plane XZ at 0.0 mm, 4 of 4 objects cut, status `ok` |
| Inventory | 4 components, 0 catalogued |
| Clearance | 6 pairs checked, 0 unknown, **1 intersection**: frame ∩ slider, 648.0 mm³ |
| Whole invocation | **Exit 0, 1680.78 s** |
| Peak process-tree RSS | 2,312,118,272 bytes, sampled every 0.2 s |

No watchdog intervention (2.9 GiB guard; trainer bounded by 600 s). The design
turn again refused the four-revolute-plus-prismatic loop as over-constrained by
three rows, and again spent those constraints on real hardware freedoms — a ball
rod end at the crank pin and a keyed cylindrical bushing at the rail — rather
than disconnecting anything. Six project `ADR-` entries and five domain notes
(`actuators`, `architecture`, `linkage-geometry`, `rejected`, `sensors`) landed,
with `PROGRESS.md` rows for the prompt, train, script, params and walk runs.

**The MJX geom-pair constraint held without the refusal having to fire.** Every
collision shape the design turn authored is a box or a capsule, in contact group
1 against an empty group 0, with the comment that the loop is carried by its
joints and the shapes exist only to be visible in a viewer. ADR-281's check
therefore never raised, and `train` ran. That is one run, not a guarantee that
the guidance always steers an unaided turn.

**Clearance reports; it does not gate.** The frame and slider intersect by
648.0 mm³ at the initial solved pose — the carriage groove clears the rail bar,
but the two solids still share volume elsewhere — and the walk exited 0 anyway.
The eyes name the offending pair for the next design turn to act on; nothing in
the walk refuses a model over it. Local evidence is in
`runs/fresh55/{walk.json,walk.stderr,monitor.json}`, excluded from Git along
with the policy, the trace and the review output.

**A second mechanism through the same entry point, `ot4-cart` (2026-09-09).**
A different prompt — an inverted-pendulum cart: grounded frame and rail, a cart
on a **prismatic** joint driven by a bounded **force motor**, and a slender pole
on a **passive revolute** joint nothing drives — into a third empty project,
with the same flags, the same bounds and **no code change of any kind**. It
**completed every leg**, and it is the first ot4 walk whose mechanism carries an
unactuated degree of freedom and whose task declares a termination the rollout
actually reaches.

| Leg | `ot4-mix55` (crank-slider) | `ot4-cart` (cart-pole) |
|---|---|---|
| Design (`claude-opus-5`) | Exit 0, 1649.63 s; revision `70fd2a53…` | Exit 0, 1196.04 s; revision `0aa617e2…`, digest `b3b699e6…` |
| Train (CPU, 5 it × 16 envs, seed 0) | Exit 0, 26.71 s; reward/step −0.4055 | Exit 0, 20.27 s; reward/step 0.6936, best 0.7013 at iteration 0, 4,609 parameters, 3.95 s trainer wall time |
| Policy verify | Witness error 1.14e-08 | Witness error 6.34e-09 against 1e-04 over 32 samples |
| Declare | Exit 0, 0.81 s | Exit 0, 0.65 s |
| Rollout (`policy_on=1`) | Exit 0, 1.53 s; total reward −19.85, seed 1 | Exit 0, 1.21 s; total reward 28.756, seed 7, **31 of 200 steps** |
| Render | 4 views, 4,756 triangles | 4 views, 5,002 triangles, 3.19 s |
| Section | XZ at 0.0 mm, 4 of 4 objects cut | XZ at **−15.0 mm** (derived), **2 of 3** objects cut, status `ok` |
| Inventory | 4 components, 0 catalogued | 3 components, 0 catalogued |
| Clearance | 6 pairs, 1 intersection (648.0 mm³) | 3 pairs, 0 unknown, **0 offending**; bounds check `pass` |
| Documentation | 5 notes, none missing | 3 notes (`actuators`, `rejected`, `sensors`), none missing |
| Whole invocation | Exit 0, 1680.78 s | **Exit 0, 1222.22 s** (`walk_seconds` 1222.11) |
| Peak process-tree RSS | 2,312,118,272 bytes | 1,997,844,480 bytes |

Both at `--iterations 5 --envs 16 --seed 0 --timeout 600 --leg-timeout 1800`
under `JAX_PLATFORMS=cpu`, both sampled every 0.2 s under the same 2.9 GiB
guard, neither stopped by it. The two `total_reward` columns are **different
objectives in different units over different episode lengths** and do not rank
the mechanisms; the columns and their definitions are what is comparable, and
both projects' `PROGRESS.md` carry the same rows for prompt, train, script,
params and walk, committed by the walk's own child commands (five commits in
`ot4-cart`, ending `fac73fc`).

Two findings the run produced that are worth reading as findings rather than
failures:

- **The rollout ended on the task's own termination, not on the horizon.**
  `termination: pole_fell` fired at step 30, so the verified rollout is 31
  steps of a 200-step, 4 s episode and `total_reward 28.756` is a sum over
  those 31. Training's mean episode was 16.8 steps. Five PPO iterations is a
  smoke test of the loop; nothing here claims the policy balances a pendulum.
- **The derived section offset cut 2 of 3 objects, and named the one it
  missed.** Of the candidates `[0.0, −2.0, 2.0, −8.5, 8.5, −15.0, 15.0]` the
  most-coverage rule (ADR-273, ADR-275) chose −15.0 mm; the pole came back
  `empty` and the review's `section.missed_objects` reports it as
  `moved: true` — the object carrying all 35.75° of the mechanism's rotation.
  On a rig whose moving part is a slender rod near the centre plane, maximum
  object coverage and maximum *interest* are not the same plane. The eye
  reported that itself rather than leaving a reader to infer it from a
  drawing they cannot see.

Local evidence is in `runs/cart1/{walk.json,walk.stderr,monitor.json}` and
`runs/cart1/review.json` in that project, excluded from this repository along
with the policy, the trace and the review output.

## 3. Dashboard proofs (ot5, 2026-09-10 → 2026-09-13)

The synthetic browser test spans committed updates without reloading and
requires each to appear within five seconds on the test machine. One real
observation exists: the fresh biped's first GPU probe, seven iterations shown
within 0.21–1.4 s of their commit on the page's own poll, with the run's
revision still unrecorded while it trained (`docs/HEADLESS-BIPED-REVIEW.md`).

`cli/tests/test_review_server.py` pins the refusals
and, in a headless Chromium driven over its DevTools pipe
(`cli/tests/cdp_browser.py`, no Playwright), the labels, the historical
view, real mouse orbit and zoom on the canvas, the stale label and
reachability over a private address (`CADEX_REVIEW_HOST`).
`cli/tests/test_video.py` adds the D4 half in the same browser: a
rendered rollout plays, keeps playing across freshness polls, and
downloads — the harness saves the download where that Chromium can
write (a snap's `/tmp` is private to it, and it may not write hidden
paths under `$HOME`), waits on the browser's own download-progress events,
and compares the bytes it wrote with the retained file's digest.

Reproduce the private-address smoke on the serving machine, without a desktop:

```bash
CADEX_REVIEW_HOST="$(tailscale ip -4)" pixi run python -m pytest cli/tests/test_review_server.py -q -s
```

This starts a temporary fixture server, opens its private-address URL in
headless Chromium, checks the displayed project and accepted revision, and
stops the server. It is a same-machine private-address check, not evidence
of access from a second device or of the fresh biped lifecycle. The browser
suite also narrows a loaded model view from 1280 to 1000 pixels and checks
that the canvas stays within the page before exercising orbit and zoom.

**Restarting the dashboard is not an event for the project or its training**
(D6, fixture half). `cli/tests/test_review_lifecycle.py` runs the real
`cadex review` command, opens the page, selects a run whose telemetry a
separate producer process — one the server never spawned and never learns
about — commits every 0.3 s in the trainer's snapshot format, stops the
command with SIGINT, checks the open page reads `stale` with its last
identities and its video element intact, restarts the command on the same
port, and checks the same page returns to `live` on its own poll without
reloading: same selected run, same recorded revision, the loss history one
point longer than the iteration it now shows, the same video element still
decodable, and the served video byte-identical to the retained file. A
second page opened afresh against the restarted server reads the accepted
revision, the same run list, the historical label, the recorded parameters,
telemetry still advancing and a playable, downloadable video. Throughout,
the producer is the same PID, its iteration sequence never resets, and on
Linux exactly one process carries its marker; every file in the project other
than the producer's own snapshot has the same digest afterwards as before.
No engine runs anywhere in this test — the reader opens none, which is why
restarting an engine cannot change what the dashboard shows — but this is
fixture evidence: D6's required pass on the fresh biped with real training
artifacts, and save/reopen of a project a real walk wrote, remain separate.
The [Wren working-copy restart proof](../probes/wren-fresh/RESTART.md) supplies
that retained-artifact check on the persistent private URL: two engine
reopens, all 15 run views compared, current/historical video downloads and
an open playing page preserved across a service restart. No trainer was
running during that real-project check. The subsequent
[real-training restart proof](../probes/wren-fresh/RESTART-TRAINING.md) restarted
the same persistent service during Wren GPU training: one unchanged trainer,
automatic telemetry recovery within five seconds, historical playback and
download preserved, and a fresh page selecting the active attempt.

## 4. The dashboard page as CLI.md described it (before ADR-537)

The page is specified in `docs/DASHBOARD.md`. These paragraphs name panels,
cards, buttons and selectors, many of which ADR-533 removed; the data each
drew is still served by the `GET /api/...` route it names.

The page's layout, type and colour follow `docs/DASHBOARD.md`: a dark
theme by default and a light one, one type scale. **Since ADR-534 the
project page is the app**: a screen tiled by resizable, movable areas after
Blender's, each showing one editor — the 3D viewport, the 2D viewport and
Status (an editor since ADR-572) — and one
editor at a time, picked from a tab bar, on a phone; since ADR-539 the
settings are a File, Revisions and View menu bar, and the default screen is
the 3D viewport with Status beside it. ADR-533 had cut what it shows to the accepted model, a design turn, the
parameter sliders and the revisions; ADR-534 adds back run models and
playback, drawings, images, documents and training plots, all read from
routes that were already served. **Since ADR-537 it writes nothing**: the
design turn, the sliders and the revision verdicts are gone, the server
answers GET and HEAD only, and the page follows what the agent's CLI and
`cadex mcp` calls change.
`cli/tests/test_review_design.py` reads the spec back from the rendered page
at 1400×900 and 400×850.

**What follows describes what the server reads and serves.** Every route
below still answers. Where a paragraph names a panel, a tab, a button or a
run selector, that page element was removed by ADR-533 and is not on the
page; the data it drew is still in the `GET /api/...` reply the paragraph
names, for the CLI, the agent, or a panel added back later.

An untouched page follows
current work on polls; selecting a view or playing a video preserves that view.
Opening a document also preserves the selected view. Its loaded text stays open
across polls; click its link again to refresh it. Changing the selected view or
its recorded revision clears the document, so another model cannot inherit the
previous view's specs or decisions (ADR-306).
When the selected model revision or digest changes, polling reloads its geometry
as well as its identity and parameters (ADR-307). This includes the first
acceptance in an already-open empty view. Unchanged polls preserve the camera;
selecting a historical run keeps its retained geometry.
The **Current run** button names the current attempt and returns to following it.
Missing/stale output stays labelled; an older success is never substituted for
a newer failure. The frozen [operator review record](../probes/operator-review/README.md)
describes the shared Reed server and its browser verification as they
were; that operator tooling was removed (ADR-536).

The Artifacts card shows the total, the per-directory split,
the skipped links, the shared references with the runs that share them,
and a size column on the artifact table that says `missing — nothing on
disk` and `refused — not read` where the reader did; the accepted view has
no run to count and says so. Video size labels update in place when the
selected detail arrives; receiving a size never replaces or pauses the player.

What the page shows, and where each thing comes from:

- **Accepted now**: the revision, digest and parameter specs from the
  project manifest, the current documents and decision headings, and the
  model from the **accepted attempt's own tessellation** — the
  `display/*.tess` files under the staging directory the manifest names,
  each linked to its output by the BREP's sha256 — every output whose
  BREP bytes match keeps that tessellation, so a mirrored pair of limbs
  shows both sides (ADR-302) — placed where the attempt's own simulation
  trace put each component at its first frame.
  This is the second and last read the review client makes of the
  project store's layout (ADR-285 documented the first, `script.json`);
  a staging directory that does not lie under the accepted revision is
  refused rather than shown as the accepted model — **unless** the
  manifest's `accepted_attempt` pin names the accepted revision *and* the
  attempt's own `result.json` carries the accepted digest (ADR-311). That
  is the shape of every project's **first** accepted script: the engine
  stages an attempt under the revision it can compute before the worker
  runs, over an empty parameter-spec cache, and records the revision
  recomputed with the collected specs as the accepted one. The agent's
  modelling calls and `cadex script --set` carry the same standard
  tessellation request `cadex params` makes (ADR-312), so a project
  straight out of an agent's first `write_script` has a model to show; `accepted attempt
  retained no tessellation` now names a project accepted before ADR-312,
  or through a `restore` replay alone, and a public rebuild with display —
  `cadex render`, `cadex params` — republishes the accepted attempt. The
  review client never rebuilds anything itself.
- **A run**: everything from its `run.json` (ADR-285) — identity, params
  and specs *as recorded*, training request and receipt, rollout seed and
  reward, artifacts with each one's status, the document snapshot — and
  the model from the **meshes its rollout leg exported beside its trace**,
  placed by that trace's first frame, with component-to-output links from
  the run's render summary. A historical run is labelled `HISTORICAL —
  recorded at <its revision>, accepted now is <today's>` and drawn from its
  own files only; nothing is rebuilt from today's script. A `running`
  record is labelled as started and never finished, with the next CLI
  action; a legacy run reads `unrecorded`. A `failed` record whose
  telemetry reads `done` is explained rather than left as a contradiction
  (ADR-326): the note says training itself finished, at which iteration of
  how many and which policy the trainer saved, and that the failure came
  after it — in the run's observation or recording, not in the trainer —
  above the run's own error. The identity card's **policy store** row shows
  `policy_store` for every selected run: its state, the reason, the
  retained trainer copy and the next CLI action; a store write the operator
  makes afterwards flips it to `stored` on the next poll, with the run's
  status and history untouched. A `completed` run whose policy is retained
  only under its own `train/` is also listed under the run's problems with
  that store command (ADR-327), and the entry leaves on the poll after the
  store write.
  Before a rollout, new walks show their retained assembled training view,
  including component identities and the recorded placement source (a trace's
  first frame or declared placements, explicitly labelled). Missing snapshot
  meshes remain missing. Older runs are not backfilled from current state.
  Without this snapshot, a run with recorded revision/digest and `model_xml`
  can show the STL parts retained beside that training export (ADR-290).
  These are explicitly labelled **individual parts at identity, not a
  solved pose**: the export does not retain component placements. This
  works after the accepted revision changes or staging is pruned. Missing
  or refused recorded exports show the reason. With neither a trace nor a
  training export recorded, current tessellation can be borrowed only
  when both revision and digest match; historical geometry is never rebuilt.
- **Labels, never guesses**: an artifact is `retained` (linked, with a
  download), `missing`, `not recorded` or `refused: <why>`; a run with no
  recorded trace whose file is missing has *no model to show* and says
  which file is missing; the header
  reads `live: updated <time>` while the server answers and `stale: server
  unreachable, last update <time>` when it stops, with the last good view
  left on screen. Retained videos with a recorded SHA-256 are verified before
  playback or download; a mismatch is refused and labelled with a CLI retry
  action. Restoring the matching artifact recovers on the next poll. Older
  entries without a digest retain existence-only checks. The video list leads with current file
  availability and a retained/recorded count; missing or refused files show
  unavailable (or partly available when other recordings remain). The separately
  labelled recorded render outcome is historical: `ready` does not mean its
  output still exists or passes verification. Restoring the original bytes
  recovers playback on the next poll. Videos are the D4 slot: a recorded video plays inline
  from the page's own Play control or the native controls (byte ranges are
  served, so seeking works) and downloads, identified by policy digest, seed
  and simulated seconds; none recorded says so. The model orbits by mouse or
  finger and pinch-zooms (ADR-330).
  Downloads preserve Unicode filenames through an encoded UTF-8 name and an
  ASCII fallback in the response header (ADR-323).
  A download the browser cancels mid-transfer is the client's decision: the
  server logs one line naming the bytes sent, prints no traceback, and the
  next whole or byte-range request serves the file (ADR-324).
