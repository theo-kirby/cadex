---
node_id: c1e64944-a027-59bb-80ed-a530f6fc6dad
slug: young-crane-9546
title: short
created_at: '2026-09-06T19:21:31+00:00'
parents:
- fond-ember-4937
summary: ''
---
Status: open

## Current

1. **Report the rollout's travel in the walk's review, in two channels
   (missions 2/6).** `cli/` and `docs/` only. From the rollout trace the walk
   already locates, compute per component the **position travel** (per-axis
   range and the largest displacement from frame 0's pose) **and the rotation
   swing** (the largest angle `2·acos(|q0·q|)` between frame 0's quaternion and
   any frame's), and report both as a `motion` block in `review.json` beside the
   clearance one. The `PROGRESS.md` row the walk already writes carries **both
   figures, millimetres and degrees** — either naming the largest mover under a
   stated rule that can rank a pure rotation against a pure translation, or
   declining to rank and naming both. A displacement-only row is not a partial
   answer, it is a wrong one: the repository's own hinged-arm example travels
   **0.0000 mm and rotates 178.8334°** [rec: solemn-journey-9731]. Three premise
   corrections the unit must honour rather than rediscover: frame 0 is **not**
   the identity (placements are absolute world poses — `swing` starts at
   `[12, 0, 6]`, `base` at the origin), frame 0 is `frame_kind: "input"` with
   `nominal_time_s: None` so a duration read from it is `None`, and the raw
   frame count mixes that one pre-solve pose into the solved ones (27 = 1 + 26
   on both examples) — say which frames are counted [rec: solemn-journey-9731].
   The component join is proven on real data: the trace's per-frame
   `component_placements` keys equal the render summary's `objects` keys
   [rec: sleepy-hollow-9498]. Two regressions on real traces, and the material
   already exists — `examples/lifecycle/{hinged-arm,linear-carriage}` reproduce
   in 13–15 s with no model call [rec: western-gate-9567] and give one rotating
   and one translating case — plus an all-identity trace, which must report zero
   travel rather than unavailable. Reuse the existing review serialization and
   trace locator; no engine, protocol, payload or `shell/` diff. ADR, ROADMAP
   bullet, verified dates, and the full `pixi run python -m pytest cli/tests` on
   the shared `cpu_training` fixture with no outer backend override.

2. **Carry travel into the iterate comparison, both channels (missions 2/5).**
   Only after unit 1 lands. The comparison the walk writes into `PROGRESS.md`
   reports `total_reward` and nothing about whether the mechanism moved, so a
   retrain that killed the motion and a retrain that merely scored worse read
   the same. Add the travel figures beside the reward in the comparison row and
   in its `review`/history record, carrying the millimetre **and** the degree
   channel for the same reason unit 1 does — a revolute rig's whole motion is in
   the second one [rec: solemn-journey-9731]. Extend the existing iterate
   lifecycle regression rather than adding a matrix. The carriage pair is the
   worked example and the reason: baseline 103.298 mm travel at `total_reward`
   3.296298, iterate 103.719 mm at 2.760187 — the reward fell while the travel
   held, and the walk could not say so [rec: sleepy-hollow-9498]
   [rec: mellow-quartz-8093]. No ranking claim follows: travel is a fact about
   the rollout, never a score, and two projects' travels do not compare any more
   than their rewards do — 4,739 mm of a carriage free-falling on an ideal guide
   outranks 178.8° of a swing arm working [rec: solemn-journey-9731].

3. **One fresh prompt walk, third mechanism, reviewed by both new eyes
   (missions 2/6).** Only after units 1 and 2. One `cadex walk --prompt` on this
   machine into a durable project outside this repository, on a mechanism whose
   named joint and actuator differ from the swing arm (revolute, position
   servo) and the carriage (prismatic, force motor) — not a re-roll of either
   prompt, which is not evidence [rec: morning-summit-7848]. No code change
   specific to the mechanism. Toy scale, ≤5 iterations × 16 envs, `--timeout
   600`, `$CADEX_MODEL=claude-opus-5`, explicit CPU, ≤18 min and ≤3 GB, nothing
   generated committed to this repository. What makes it a unit rather than
   re-evidence: it is the first walk whose review carries the ADR-256
   documentation eye reading a real design turn's own notes back — the two
   documented example walks are *recipe* walks and run no design turn at all
   [rec: western-gate-9567] — and the first carrying a travel figure. Report
   both, plus whether the design turn wrote `NOTE` lines unprompted. If the
   provider refuses on credit, record the refusal and stop; do not probe.

## Negative knowledge

- [scope: what a displacement-only travel figure gets wrong | confidence: high | evidence: solemn-journey-9731] Reading position alone is not a partial motion report, it is an inverted one. Measured on the two documented example rollouts on this machine: the hinged arm's `swing` holds `[12, 0, 6]` for all 27 frames and turns **178.8334°** — travel `0.0000 mm`, indistinguishable from a dead rollout — while the linear carriage's `slide` travels **4739.3783 mm**, all of it the free fall on an ideal unlimited guide that `crisp-reef-5607` already records as `z = -4699 mm at 1 s`, and rotates `0.0000°`. Across the four real traces this run has produced, both revolute rigs have near-zero displacement. Do not ship a single-number travel figure, do not rank projects by it, and do not treat the rotation channel as completeness work.

- [scope: three premises the rung asserted and measurement falsified | confidence: high | evidence: solemn-journey-9731] Frame 0 is **not** the identity — placements are absolute world poses, so travel is a delta from frame 0 and the "no composition needed" licence was read off a false premise. Frame 0 is **not** a rollout frame — it is `frame_kind: "input"` with `nominal_time_s: None`, so a duration taken from it is `None` and a raw frame count (27) mixes one pre-solve pose into 26 `solver_output` ones. What survives unchanged is the component join: `component_placements` keys equal the render summary's `objects` keys. Do not restate the identity claim, and do not let a test pin it as an invariant.


- [scope: the rollout motion-clearance screen, retired unbuilt | confidence: high | evidence: sleepy-hollow-9498] The screen's own stop condition is met before a line of it exists. The join holds — the trace's `component_placements` keys equal the render summary's `objects` keys and frame 0 is the identity — but the verdict would be vacuous: on the swing rig **22 of 45 pairs already overlap in world AABB at the accepted pose** (every bolt in its plate, both nuts on their bolts, the servo in the retainer, all nine pairs against the base plate whose AABB is the whole envelope), so those pairs read `not proven clear` at every frame whatever the policy does, and they are exactly the pairs a person asks about. The other 23 are the ones nobody worries about, and the motion cannot reach them: 1.094 mm of travel over 152 frames on the swing, 103.298 mm on the carriage whose single pair overlaps throughout because the block rides a column inside the base's AABB. This is a property of axis-aligned boxes over jointed assemblies, not of toy scale, and no threshold fixes it. Do not rebuild it, do not tune it, and do not read the retirement as authority for the engine-zone swept check, which stays on the long rung.

- [scope: the domain-note write half, already exercised here | confidence: high | evidence: sleepy-hollow-9498] `eager-lake-5745`'s claim that "no walk has yet produced a domain note from a real design turn's closing text on this machine" is **false** and is corrected here: `docs/actuators.md` and `docs/sensors.md` in `ot4-carriage`, `ot4-swing2` and `ot4-swing` were each committed by a `cadex prompt:` commit — the design turn's own closing text, three times on this machine. ADR-245's write half is exercised; only the ADR-256 read-back eye has never run on a real prompt walk. Do not spend an iteration re-proving the write half, and do not cite that record's sentence as a gap.

- [scope: what the travel report may claim | confidence: high | evidence: sleepy-hollow-9498] Travel is a fact about one rollout of one project: how far a component went, over sampled frames, under one seed and one toy-scale policy. It is never a score, never a ranking, and never a claim about gait, control quality or mechanical function — the swing rig's 1.094 mm and the carriage's 103.298 mm say the mechanisms are different, not that one is better. Motion between sampled frames is uncovered and rotation is read from quaternions the trace already carries. A travel figure that rises while reward falls is a finding to report, not a defect to tune.

- [scope: the inventory retention tail, dropped | confidence: high | evidence: sleepy-hollow-9498] Removed from this rung rather than deferred. Five iterations went to inventory report prose and fixtures against an unmoved frontier and the overseer's verdict at #16 was `looping`; the boundary is already stated in `docs/CLI.md`, in the generated scaffold and as negative knowledge on `damp-moon-9297`, and every superseded report survives in its project's own Git. It is not blocked and not a defect — it is a sixth pass that the rung declines. Do not reinstate it and do not open anything adjacent to it [rec: soft-crane-2369] [rec: scarlet-ocean-2920].

- [scope: the overseer's third-mechanism steer, honoured and re-ordered | confidence: high | evidence: sleepy-hollow-9498] The #19 verdict hard-commits the next unit to a fresh mechanism walk because the frontier has been unmoved thirteen iterations. The frontier cannot move from this rung: all four seeded criteria are `working`, the three open nodes are standing work or parked under `## Later criteria`, and the charter reserves promotion to a human edit. So the walk is kept and ranked third rather than dropped or led with — after the two eyes that make it more than a fourth pass at the same review shape [rec: rare-cliff-9595] [rec: proud-beacon-8002].

- [scope: the engine's swept check versus the walk's own motion | confidence: high | evidence: strong-falcon-1463] ADR-130/ADR-242's `clearance=` is an argument of `assembly.simulation` — the kinematic OndselSolver trace, capped at 32 pairs — and a breach **raises** (`cadex_assembly_worker.py:3248`). The walk's motion is `assembly.rollout`, a MuJoCo dynamics trace with no clearance surface at all, which is why that path is exercised only by its regression [rec: morning-summit-7848]. Do not auto-declare pairs into the accepted script to reach it: a breach would kill a walk after its training is already spent, and this rung has already declined refusal in favour of reporting. The kernel check over the dynamics rollout is an engine-zone successor on the long rung, not this unit.

- [scope: completed CPU direction and historical inventory | confidence: high | evidence: scarlet-ocean-2920] Both CPU units are spent. The inventory limitation is source-derived: current project docs are mutable, while Git retains prior reports. Only the bounded rehearsal/documentation and existing-data projection are selected; no data-loss, catalog-discovery or general archival claim follows [rec: floral-arrow-7365] [rec: keen-field-4379] [rec: scarlet-ocean-2920].

- [scope: completed recovery and selected CPU maintenance | confidence: high | evidence: dry-grove-2638] Recovery rehearsal and permanent regression have landed; earlier recovery dispatches are historical. The observed cuSolver failure motivates explicit CPU setup and scoped test consolidation only; it establishes no general CUDA defect or authority for GPU work [rec: placid-ember-6741] [rec: dry-grove-2638].

- [scope: the charter's frontier, now empty | confidence: high | evidence: western-reef-4119] All four seeded criteria are working in the state projection; the charter boxes remain untouched. The three open frontier nodes are standing work or parked under `## Later criteria`. The charter's own rule is that promotion "is a human edit, and it mints a new directive" — so an agent may not open the backlog, and an empty frontier is not licence to invent a campaign. One direction was taken; the rest of the rung is the charter's standing work. Do not target catalog breadth, compound mechanisms, report rendering, the variant study, the fleet script, outside-source mechanisms or the mg-legs shove band until a human moves one up.

- [scope: the review step's teeth, checked and found present | confidence: high | evidence: western-reef-4119] Mission 6 says the loop is only as good as its review step, and `command_clearance` (`cli/cadex_cli/__main__.py:851`) does return `EXIT_OK` whatever `pair_status` decided. But offending pairs are **not** silent: they land in `docs/clearance.md`, in `review.json` as `offending_pair_count` and `offending_pairs` (`__main__.py:1426–1438`), and in the `PROGRESS.md` row template (`__main__.py:1624`, documented at `project_docs.py:169`). The only open question is whether a design finding should *refuse*, and the question policy's reversible option — report it — is already taken three times over. Do not open this as a unit; it is a non-problem dressed as one.

- [scope: mission 1's file lifecycle on this machine | confidence: high | evidence: western-reef-4119] File lifecycle is the charter's **first** priority and its three criteria are shipped, but nothing here can re-run them: there is no shell build tree (`shell/build_darwin` absent; only `shell/build_files` on disk), `package/app/build_app.sh` is macOS-shaped, and `pixi run gate` runs against a bundle that does not exist. So on this machine the file-lifecycle regressions can be **read and not run**, and no unit may claim to have verified them here. This is also a fact about mission 9's fleet: a "fresh machine runs the walk" script would qualify the headless half only. Do not spend an iteration rediscovering this, and do not attempt a Linux shell build to work around it.

- [scope: the walk's own green result | confidence: high | evidence: wandering-jasper-6102] Exit 0 in 17:43 qualifies the pipeline, not the mechanism or the control. Training was 5 iterations x 16 envs in 8.7 s at reward/step -0.1254; that is a smoke test of the loop's shape, and the witness error of 7.2e-09 proves the policy the engine verified is the policy the trainer wrote, nothing about a learned motion. The gait is rung 3 and stays parked. Do not cite this walk as evidence that a rig works mechanically.

- [scope: the design turn as a source of mechanisms | confidence: high | evidence: morning-summit-7848] [rec: empty-banner-7438] The design turn is nondeterministic: the same prompt has yielded placed catalog servos once and fused hand solids the next time, with different reward expressions. So a second mechanism must differ **in the prompt's named joint and actuator**, not by re-rolling the same prompt hoping for a different assembly. Same prompt is not same design, and re-rolling to seek a wanted outcome is not evidence.

- [scope: the stale-engine unit's blast radius | confidence: medium | evidence: wandering-jasper-6102] The observed failure is one direction — an installed runtime older than the tree — found by grepping `OPENBLAS_NUM_THREADS` out of the installed `CadexScriptedRuntime.py`. It is not authority to redesign engine resolution, to add a build step to the walk, or to make the CLI rebuild anything. Report first; a refusal is a second unit and needs the reporting to have proved insufficient.

- [scope: the failed walk's own diagnosis, now resolved | confidence: high | evidence: lawful-wolf-9205] [rec: open-hollow-2140] The design agent's `docs/rejected.md` asserted that a single grounded box exhausts the worker cap; that was measured false, and the real fault was `import numpy` under `import mujoco` reserving 4,432 MB of address space on 32 cores against a 6,144 MB `RLIMIT_AS`, fixed by pinning `OPENBLAS_NUM_THREADS=4` (ADR-250). The lesson that outlives the bug: do not treat a design turn's written diagnosis as evidence. The bisect and the legibility repair are both complete and are not units.

- [scope: nt3's provider-credit parking, retired | confidence: high | evidence: open-hollow-2140] The entries below that park work on usage-credit refusals are superseded. ADR-249 at `bc203d28` makes `--model` read `$CADEX_MODEL` before `DEFAULT_MODEL`; on this login `claude-opus-5` answers and the constant `claude-fable-5` does not. A machine whose default model has no credit is no longer a reason to park a walk. This does not license a provider probe as a unit, and the durable nt3-leg baseline noted below still stands [rec: open-hollow-2140] [rec: wandering-jasper-6102] [rec: sunny-walrus-5847].

- [scope: the inherited conditional slots | confidence: high | evidence: ancient-key-7299] nt3's short horizon — two conditional, non-dispatchable repair slots and a recommendation that the controller stop actor dispatch — is spent, not deleted. It described a frontier with no trigger; triggers now exist and have been taken. Do not restate that disposition, and do not read this replacement as authority for an audit campaign, a repeated hold record or scope expansion beyond the three ranked units [rec: curious-badger-0797] [rec: ancient-key-7299].

- [scope: exhausted maintenance dispatch | confidence: high | evidence: curious-badger-0797] Suite-count correction and its verification are complete. The role-transition record establishes no product defect. Conditional slots are not permission for an audit, repeated hold record or provider probe. Controller enforcement remains unproved [rec: curious-badger-6887] [rec: placid-sun-2737].

- [scope: completed onboarding correction and role transition | confidence: high | evidence: weathered-trail-0874] Onboarding verification passed; conditional repair has no work. Do not repeat either correction or a handoff-only actor dispatch [rec: shy-beacon-2513] [rec: cool-raven-8938].

- [scope: completed linked-part qualification | confidence: high | evidence: calm-sky-2656] Consumer cold restore/export holds with its source path absent; exact BREP, accepted identity and docs are preserved. No correction or repeated/adjacent qualification follows. This fixture establishes neither refresh behavior nor catalog identity [rec: lawful-union-8346].

- [scope: completed consent and suffix qualifications | confidence: high | evidence: silver-rain-7333] Accepted output preservation and cold recovery held; blank rejection-envelope identity is not evidence of data loss or authority for a reporting feature. The adjacent parity audit is source-only and warrants no runtime Save-As claim or automatic repeat [rec: empty-ledge-4581].

- [scope: completed provider-free rehearsal and scratch remediation | confidence: high | evidence: scarlet-journey-0203] The arm walk passed in 15.6578 s / 0.987 GiB with full review and portable output labels. Preinitialized scratch Git bypassed ignore scaffolding; this does not establish a product defect. No automatic baseline rerun or repeated scratch cleanup is dispatchable [rec: lucid-snow-0350] [rec: scarlet-journey-0203].

- [scope: completed refusal metadata work | confidence: high | evidence: ready-otter-2700] Diagnosis and ADR-247 are complete: unchanged session/model now preserves bytes and timestamp, while changed identity persists on failures. Five real-engine regressions and 206 CLI passes establish the narrow boundary, not live provider resumption or general transaction safety. No reset of the durable project or repeated diagnosis follows [rec: vast-ledge-4610] [rec: ready-otter-2700].

- [scope: durable refused repair | confidence: high | evidence: sunny-walrus-5847] The one attempt was refused at design for usage credits; downstream legs were unreached. Unchanged session id and `--resume` argv do not prove actual resumption. Dirty timestamps and attempt identifiers are a measured finding, not proof of corruption or authority for blanket rollback. No automatic retry; investigate only in an isolated offline reproduction [rec: sunny-walrus-5847] [rec: gentle-wind-1003].

- [scope: current leg continuation | confidence: high | evidence: fond-star-1809] The temporary leg was reaped. The durable walk was a fresh design with findings supplied in its prompt; it proves neither resumed repair nor cross-project reward improvement. The product automatically falls back on stale sessions; do not claim that fallback exercised resume [rec: fond-star-1809] [rec: forest-shade-2752].

- [scope: the leg rehearsal's findings and what they do not prove | confidence: high | evidence: proud-beacon-8002] The two-servo leg walk is clean pipeline and review evidence, not a printable leg or a learned crouch: one PPO iteration, views and a section at the initial solved pose, tessellation cuts. Eleven offending pairs and a 5 mm servo-to-driven-link gap are project design findings; the ideal revolute joints do not prove a physically attached drive. Bound agreement is AABB consistency, not OCCT volume validation. Do not rerun the rehearsal to seek different findings; iterate on these [rec: proud-beacon-8002] [rec: weathered-hill-5955].

- [scope: eligibility scheduling, historical | confidence: high | evidence: proud-beacon-8002] The 06:30 UTC boundary rule and the 113-iteration scheduling stall are spent. No clock observation, eligibility record or provider probe is a unit now [rec: happy-tide-1066] [rec: proud-beacon-8002].

- [scope: repeated premature dispatch | confidence: high | evidence: lawful-orchard-3508] Iterations 47 and 48 performed no rehearsal or provider request. Re-recording a scheduling hold cannot satisfy the critic's required lifecycle evidence. No repeated administrative unit is selected [rec: dawn-light-8546] [rec: lawful-orchard-3508] [rec: strong-trail-5488].

- [scope: completed dependency discovery and dispatch eligibility | confidence: high | evidence: early-gate-3510] Definition paths distinguish measured boolean roles, not surviving material or purchases. Fresh-map joins cannot recover cold or occurrence identity. Discovery reached its stop condition; no implementation follows. Do not redispatch before eligibility or repeat completed qualification [rec: early-gate-3510] [rec: chilly-spark-3931] [rec: clear-crest-9910].

- [scope: qualified repair and deferred rehearsal | confidence: high | evidence: lawful-dune-3795] ADR-244 closes the reproduced worker snapshot defect with completed source/build/payload/CLI gates. Concurrent mutation after validation remains possible; no general race safety is claimed. Do not redispatch repair or repeatedly record the same pre-reset blocker [rec: lawful-dune-3795] [rec: calm-beacon-7800].

- [scope: worker snapshot integrity | confidence: high | evidence: nimble-basin-8423] In-place source mutation through a hardlink reproduces wrong bytes under an existing content-addressed name. Tested CMake copy/install primitives do not reproduce it; the historical writer and races remain unproved. Guidance is delivered (CLI 195 passed), but agent compliance is unmeasured [rec: nimble-basin-8423] [rec: misty-tide-6394].

- [scope: fused catalog diagnostic and provider availability | confidence: high | evidence: odd-ridge-9607] The accepted pan-tilt design has fourteen outputs and no catalog stamps; scanning published outputs cannot recover either fused servo. Calls cannot establish purchased quantities. Quota percentages do not establish availability [rec: odd-ridge-9607] [rec: windy-dune-3488] [rec: silent-mist-5233].

- [scope: the walk as evidence for catalog-part clearance | confidence: high | evidence: morning-summit-7848] The pan-tilt rerun fused both `lib.servo` bodies into hand solids, so its structural clearance check passed vacuously. Do not re-roll a walk to seek catalog components; check an assembly that has them. ADR-242's swept path is exercised only by its regression, because the walk's design turns declare no simulation clearance pairs [rec: morning-summit-7848] [rec: southern-otter-5999].

- [scope: delivered CPU render coverage and remaining limits | confidence: high | evidence: silver-key-8483] SVG wraps a 512px lossless CPU image, not analytic vectors. Shell-only visibility, transparency, analytic edges, subpixel fidelity, motion coverage and large-assembly throughput are not established. Separate command timings are not walk overhead. Blender background rendering refusals and the stale ordinary bundle from the probe remain historical constraints [rec: silver-key-8483] [rec: zesty-aspen-6846] [rec: first-branch-9614].

- [scope: the inherited-tree removal ledger | confidence: high | evidence: autumn-arrow-3125] The updater, Test Tk, Material, Main-resource, Help and Start pairs have all landed with their own gates and ADRs; surviving FreeCAD M totals and the inherited CTest baseline are recorded in their records. Do not redispatch any of them, and do not open a fresh audit campaign — reduction is standing work on the long rung for this run, not a target [rec: green-stone-3882] [rec: autumn-arrow-3125] [rec: silver-lodge-1952] [rec: chilly-summit-3112] [rec: proud-moon-9023] [rec: modest-summit-8554].

- [scope: stopped accessory delivery | confidence: high | evidence: steady-reef-0162] Neither horn nor pigtail category qualified. Horn geometry is measured, but exact mating and redistribution are unresolved; the DS archive is inaccessible; the cable lead has no manufacturer STEP. No new candidate, approximation or importer is dispatched [rec: steady-reef-0162] [rec: noble-clover-4083].

- [scope: exhausted fifth-servo qualification | confidence: high | evidence: hidden-ridge-7342] HS-311 and HS-422 both fail unchanged `ServoPart` mounting-mouth compatibility; output-stack evidence is incomplete and HS-422 dimension labels conflict. Stop the conditional proof/delivery, third-candidate search and recipe refactor until new evidence and an explicit later bet [rec: hidden-ridge-7342].

- [scope: completed render visibility fix | confidence: high | evidence: civic-moss-7263] The hydration/EEVEE regression fails on old source and passes after independent source/edge render ownership; the full headless gate passed. Do not redispatch the audit or the fix. Legacy viewport restoration and manual render hiding during existing ownership remain limited; general headless review video is still open [rec: sunny-canyon-1138] [rec: civic-moss-7263].

## Provenance



- lone-wood-3732 — retain the short horizon without invention or retirement
- ancient-key-7299 — replace nt3's spent conditional slots with three dispatchable units on the trigger the first failed walk supplied
- glad-mesa-6299 — the short rung's three units all landed; re-rank onto the second mechanism, the stale-engine report and the three-modes currency audit, with a credit-refusal fallback order
- western-reef-4119 — the charter frontier ran dry; re-rank onto the model-free iterate row, the stale-engine report, and a model-gated end-to-end re-run over the changed cli/
- frosty-wolf-4770 — fold completed reporting and iterate evidence; select bounded subtractive guide maintenance

- sharp-garden-2483 — both guide units folded; evidence-triggered standing maintenance selected with no actor dispatch.

- northern-sage-7087 — fold failed-retraining preservation; select finite recovery continuation and retain parked scope.
- dry-grove-2638 — fold completed recovery; select two finite CPU-contract units from observed backend failure
- scarlet-ocean-2920 — fold completed CPU work and select bounded historical inventory maintenance
- strong-falcon-1463 — fold the measured inventory boundary and the offline training plan; lead the rung with motion coverage over the rollout trace and demote inventory retention to its tail
- sleepy-hollow-9498 — retire the motion screen on measurement; re-rank onto the rollout travel report, the iterate carry and a deferred third-mechanism walk
- solemn-journey-9731 — correct the travel unit's premises and require both a millimetre and a degree channel; keep the rung's three units and their order
