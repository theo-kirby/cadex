---
node_id: 358a8ff6-511a-55d4-86dd-37d18b65f4e4
slug: late-valley-7350
title: long
created_at: '2026-09-06T19:21:31+00:00'
parents:
- fond-ember-4937
summary: ''
---
Status: open

## Current

1. **Toward the north star (mission 2, parked).** The unattended robot prompt, print-ready export, G-code and rollout video remain long directions. They require human promotion from Later criteria before dispatch; this pass selects none of them [rec: empty-wolf-3962] [rec: modest-summit-8554].
2. **Standing lifecycle maintenance (missions 1, 2 and 6).** The standing work that never ends: the walk keeps working, and every landed correction stays landed. ADR-245 (live domain notes), ADR-246 (the output label), ADR-247 (refusal metadata), ADR-243/244 (worker identity), and the first-visit Git, output-loss consent, suffix-parity and linked-part qualifications are complete and are not units; their evidence lives in their records. ADR-249 adds one to that set on this machine: `--model` reads `$CADEX_MODEL` before `DEFAULT_MODEL`, so a login whose default model has no credit no longer parks a walk, and nt3's provider-credit parking is retired with it (CLI 217 passed, no skips) [rec: open-hollow-2140] [rec: ancient-key-7299]. What remains standing rather than finished: run the documented headless entry point end to end whenever the short rung empties, and take the failure it names as the next unit [rec: curious-badger-0797] [rec: ready-otter-2700] [rec: lawful-dune-3795] [rec: forest-shade-2752] [rec: fond-star-1809].
3. **Measured review baseline and its limits.** Fresh arm/carriage external whole commands took 16.61/16.39 s; sampled peak process-tree RSS was 1,059,241,984/987,168,768 bytes. The pan-tilt walk from a design prompt took 371.70 s wall (347.25 s of it the one design turn) at 1.419 GB peak; the rerun through the installed bundle took 406.33 s (374.52 s the design turn) at 1.750 GB, both inside the 850 s and 2.9 GB guards. The two-servo leg walk from a prompt took 565.72 s wall (539.06 s the design turn, 19.13 s train, 1.82 s declare, 2.09 s verify/rollout) at 1,270,939,648 bytes sampled peak; its review covered 7,776 triangles, 10 objects and 45 pairs [rec: proud-beacon-8002]. Each full built-engine CLI gate passed 195 with zero skips. These walks overlapped gates, so samples are observations, not benchmarks. Four named views and interior sections were inspected on all four walks; arm contact and carriage separation remain explicit; the pan-tilt head carries one true 0.4 mm servo sink and three servo-to-bracket contacts after the frame fix, and the rerun's design fused its servos into hand solids. The swept check costs 0.374 ms/frame where box rejection dominates and about 3.0 ms where a distance query does. Policy witnesses pass, but carriage falls under gravity, and differing force/torque effort units prevent ranking these rewards as control improvements. These measurements establish neither swept safety in review nor analytic sections; ordinary-bundle evidence is separate [rec: first-branch-9614] [rec: quiet-vine-3426] [rec: empty-banner-7438] [rec: light-timber-5868] [rec: southern-otter-5999] [rec: morning-summit-7848].
4. **Inherited-tree reduction, standing only (mission 3).** nt2 removed 2.79M lines; reduction is done enough for this run. Take a removal only when an authorized change makes it obvious and cheap, never as an iteration's target or a fresh audit campaign; the surviving-diff and updater audits left only retained residue [rec: modest-summit-8554] [rec: autumn-arrow-3125].
5. **Parked criteria (missions 4, 5, 7, 8 and 9).** Catalog breadth, manufacturer geometry, compound mechanisms, L3 motors, outside-source mechanisms, variant studies, report rendering, fleet and mg-legs ambitions remain parked under Later criteria. Human charter edits govern promotion. The exhausted active frontier is recorded rather than silently replaced by those wider ambitions [rec: modest-summit-8554] [rec: modest-grotto-1192].
6. **Ordinary bundle evidence and limits.** After the supported refresh, the installed arm walk took 16.0437 seconds at 1,054,588,928 bytes sampled peak tree RSS; packaged lifecycle passed 15 and full CLI passed 195 without skips; the matching built bundle passed the background shell gate. The second refresh put ADR-241 and ADR-242 into the bundle with the assembly worker byte-identical across source, stage and bundle, manifest and binary unchanged; packaged lifecycle passed 15 against it and a four-leg pan-tilt walk ran clean. Payload resolution refuses only a nonempty schema disagreement; matching schemas prove neither worker completeness nor shared provenance. The deployment remains locally linked, not a portable release or hermetic import-closure proof. GUI-attached lifecycle stays documented-only and remote stays scripted-only [rec: strong-raven-3067] [rec: tiny-haven-0347] [rec: keen-pebble-3574] [rec: light-timber-5868] [rec: morning-summit-7848].

The installed application evidence above predates ADR-243 and ADR-244. The fresh local stage carries both corrections; ADR-244 qualification completed build/install/stage, engine 2085 passed/52 skipped, CLI 195 passed/no skips and packaged lifecycle 15 passed, plus real worker acceptance/rebuild with unchanged digest. It retains external LC_RPATH warnings and local linkage; no GUI refresh or portable release is claimed [rec: lawful-dune-3795] [rec: calm-beacon-7800].

The durable nt3-leg adds a sixth clean prompt walk: 630.22 s wall, 1,115,717,632 bytes peak, rollout total_reward 0.8530453495479725, 45 clearance pairs / 9 offending zero-volume contacts / 0 unknown, six catalog instances, four views and the XZ section inspected, ninety bound comparisons passing at 1e-3 mm. Its changed objective prevents comparison with the temporary leg's reward. A second row with unchanged objective/horizon will be the first comparable pair for this durable project, not the first iterate comparison in the product [rec: fond-star-1809] [rec: forest-shade-2752].


**This machine now has its own baseline, and it is a clean one.** The first walk here exited 3 at the train leg after 1:06:25, with the design leg alone taking 3,983.3 s [rec: open-hollow-2140]. The second, after ADR-249 and ADR-250, ran **exit 0 in 17:43** — `cadex walk --prompt` into a durable project outside this repository, `--model claude-opus-5` through `$CADEX_MODEL`, `JAX_PLATFORMS=cpu`: design 1,014.2 s, train 38.3 s, declare 2.2 s, rollout 2.4 s, `walk_seconds` 1,063.1 through review, **2,640 MB peak RSS**. Training was 5 iterations x 16 envs in 8.7 s over 4,673 parameters at reward/step -0.1254, witness error 7.2e-09 against a 1e-4 tolerance, and the verified rollout scored total_reward -0.1765 over 4 legs. The review leg used all four eyes: render front/top/right/iso at 13,432 triangles in 3.4 s, section XZ at 3.125 mm, inventory of 10 components with 7 catalogued, and a clearance bounds check passing over 45 pairs with 13 inside the 0.1 mm advisory band. `cli/tests` 217 passed, 0 skipped, including `test_walk.py`'s two real-engine walks [rec: wandering-jasper-6102]. **This is the figure to compare against on this machine**; the nt3 wall-clock and RSS numbers above remain another machine's observations.

**That thing is proved and is no longer standing.** `assembly.mjcf` does return for a rig the design agent actually produces: the fault was never in the dynamics declarations but in `import numpy` under `import mujoco`, where OpenBLAS sizes a per-thread scratch pool from the host's core count and reserved 4,432 MB on this 32-core box against the worker's 6,144 MB `RLIMIT_AS`, then spun in its allocation retry loop until `RLIMIT_CPU` killed it. Pinning `OPENBLAS_NUM_THREADS=4` in `worker_environment` (ADR-250) took the walk's own script from 300.0 s / exit 3 to **2.0 s**, and the full dynamics layer — ten bodies with per-component collisions, the servo actuator, joint dynamics, four observations, reward, termination, randomisation and both ranged disturbances — accepts in 1.2 s, where none of it had ever built [rec: lawful-wolf-9205]. The same commit made the kernel's budget kill legible: SIGXCPU and SIGXFSZ now surface as `DOMAIN_CPU_LIMIT_EXCEEDED` and `DOMAIN_OUTPUT_LIMIT_EXCEEDED` naming the cap and the CPU-second versus wall-clock asymmetry, rather than as "exited without a result". The caps themselves are unchanged.

**What is standing in its place, as a class rather than a bug:** the walk is the product's own integration test, and each clean run exposes the next thing that quietly needed a person. The live one is that the walk cannot tell when the installed engine predates the tree — it reports exit 0 on a stale runtime, and `cli/` has no engine-versus-tree staleness notion at all [rec: wandering-jasper-6102] [rec: glad-mesa-6299].

**This run's seeded frontier is now satisfied in state, with the charter left read-only.** The second mechanism is a prismatic force-motor carriage: exit 0 in 359.8 s, 1,721 MB peak RSS, design 340.7 s, train 15.8 s, declare 0.9 s and rollout 1.0 s. The 5 × 16 seed-0 baseline scored total_reward 3.2963; review covered four views, an XZ section, two components (zero catalogued) and one clearance pair with zero offending. This and the swing arm are pipeline evidence; their differing reward definitions do not rank mechanisms. A same-objective iterate comparison is the bounded follow-up [rec: rare-cliff-9595] [rec: western-reef-4119].

**Mode and gate limits remain explicit.** Remote dispatch is scripted and offline-tested; GUI attachment is documented and unexercised. CLI `$CADEX_MODEL` does not select the shell's model; that divergence is now documented, with 218 CLI tests passing and zero skips. This machine has no usable shell bundle for the file-lifecycle gate, so the plan selects no shell qualification or Linux shell build [rec: early-quill-3654] [rec: western-reef-4119].

**One bounded direction:** report the observed installed-engine/source discrepancy, then exercise it through the iterate walk. The unchanged charter keeps catalog, fleet, reports, outside-source mechanisms and gait ambitions parked; runtime reporting does not authorize those directions. Corrections to the unfinished Bet's wording and ordering are in short: the charter boxes are not ticked, and the reporting unit was never spent [rec: western-reef-4119].

## Negative knowledge

- [scope: cross-machine measurement | confidence: high | evidence: wandering-jasper-6102] The walk timings, peak-RSS figures and bundle observations recorded below and above were taken on the previous machine and are not this machine's baseline. This machine's baseline is now the exit-0 walk: 17:43 wall, 2,640 MB peak, design 1,014.2 s [rec: wandering-jasper-6102]. Cite that one here, and do not mix the two sets — the design leg alone differs by a factor of three between machines, so a cross-machine wall-clock comparison measures the hardware and the model turn, not the product.

- [scope: what the green walk qualifies | confidence: high | evidence: wandering-jasper-6102] Exit 0 qualifies the pipeline and its review step, not the mechanism, the control or a printable part. Five iterations by sixteen environments is a smoke test of the loop's shape; the 7.2e-09 witness error proves the policy the engine verified is the policy the trainer wrote and nothing about learned motion. The gait remains rung 3 and parked. The clearance check reported 13 pairs inside the 0.1 mm advisory band, and bound agreement there is AABB consistency, not OCCT volume validation [rec: proud-beacon-8002].

- [scope: the walk and the installed engine | confidence: high | evidence: wandering-jasper-6102] A walk on a fresh checkout runs whatever `build/release` last installed. ADR-250 is Python under `src/Mod/cadex/`, so it did not reach the walk until `pixi run build-engine` reinstalled it, and the walk gave no sign either way. Any walk result cited as evidence must say that the engine under it matched the tree; until the CLI reports the mismatch itself, that is a human precondition and the one remaining place the walk needs a person.

- [scope: exhausted maintenance dispatch | confidence: high | evidence: curious-badger-0797] Suite-count correction and its verification are complete. The role-transition record establishes no product defect; separate planning has now occurred. No current actor unit advances a demonstrated missing lifecycle leg. Conditional slots are not permission for an audit, repeated hold record or provider probe. Controller enforcement remains unproved [rec: curious-badger-6887] [rec: placid-sun-2737].

- [scope: completed onboarding correction and role transition | confidence: high | evidence: weathered-trail-0874] Onboarding verification passed; conditional repair has no work. The next actor recorded a dispatch conflict, not product progress. Do not repeat either correction or a handoff-only actor dispatch; this separate planning pass selects a different exact documentation correction [rec: shy-beacon-2513] [rec: cool-raven-8938].

- [scope: completed linked-part qualification | confidence: high | evidence: calm-sky-2656] Consumer cold restore/export holds with its source path absent; exact BREP, accepted identity and docs are preserved. No correction or repeated/adjacent qualification follows. This fixture establishes neither refresh behavior nor catalog identity [rec: lawful-union-8346].

- [scope: completed consent and suffix qualifications | confidence: high | evidence: silver-rain-7333] Accepted output preservation and cold recovery held; blank rejection-envelope identity is not evidence of data loss or authority for a reporting feature. The adjacent parity audit is source-only and warrants no runtime Save-As claim or automatic repeat [rec: empty-ledge-4581].

- [scope: completed provider-free rehearsal and scratch remediation | confidence: high | evidence: scarlet-journey-0203] The arm walk passed in 15.6578 s / 0.987 GiB with full review and portable output labels. Preinitialized scratch Git bypassed ignore scaffolding; this does not establish a product defect. Critic remediation untracked 33 generated paths without changing their bytes, deleting evidence or rewriting history; old commits still contain them. First-visit coverage remains unexercised by that rehearsal. No automatic baseline rerun or repeated scratch cleanup is dispatchable [rec: lucid-snow-0350] [rec: scarlet-journey-0203].

- [scope: completed refusal metadata work | confidence: high | evidence: ready-otter-2700] Diagnosis and ADR-247 are complete: restore locators intentionally refresh; unchanged session/model now preserves bytes and timestamp, while changed identity persists on failures. Five real-engine refusal/success regressions and 206 CLI passes establish the narrow boundary, not live provider resumption or general transaction safety. Earlier instructions below to investigate metadata are historical and not dispatchable. No reset of the durable project or repeated diagnosis follows [rec: vast-ledge-4610] [rec: ready-otter-2700].

- [scope: durable refused repair | confidence: high | evidence: sunny-walrus-5847] The one attempt was refused at design for usage credits; downstream legs and live label verification were unreached. Unchanged session id and --resume argv do not prove actual resumption. Accepted model and notes survived; dirty timestamps and attempt identifiers are a measured finding, not proof of corruption or authority for blanket rollback. No automatic retry or repeated scheduling record; investigate only in an isolated offline reproduction [rec: sunny-walrus-5847] [rec: gentle-wind-1003].

- [scope: current leg continuation | confidence: high | evidence: fond-star-1809] The temporary leg was reaped. The durable walk was a fresh design with findings supplied in its prompt; it proves neither resumed repair nor cross-project reward improvement. ADR-245 live notes are complete. The product automatically falls back on stale sessions; inspect the report and do not claim that fallback exercised resume. Existing records remain immutable; the new horizon narrows the Bet's “first comparison” wording to this durable project [rec: fond-star-1809] [rec: forest-shade-2752].

- [scope: the leg rehearsal's findings and what they do not prove | confidence: high | evidence: proud-beacon-8002] The two-servo leg walk is clean pipeline and review evidence, not a printable leg or a learned crouch: one PPO iteration, a 200-step rollout at reward/step -25.72, views and a section at the initial solved pose, tessellation cuts. Eleven offending pairs (seven zero-volume contacts, four positive-volume: shin/foot bolts 5.84 mm³, bolt/nyloc 9.28 mm³) and a 5 mm servo-to-driven-link gap are project design findings; the ideal revolute joints do not prove a physically attached drive, and damping = stall torque / no-load speed is an approximation. Bound agreement is AABB consistency, not OCCT volume validation. The catalog tally came from reading the script; no cold identity or occurrence guarantee follows. The design turn wrote no `docs/sensors.md` or `docs/actuators.md` despite the scaffold naming them: one compliance observation, not proof the convention is unreachable. Do not rerun the rehearsal to seek different findings; iterate on these [rec: proud-beacon-8002] [rec: weathered-hill-5955].

- [scope: completed dependency discovery and dispatch eligibility | confidence: high | evidence: early-gate-3510] Definition paths distinguish measured boolean roles, not surviving material or purchases. Fresh-map joins cannot recover cold or occurrence identity; unknown roles and ambiguous matches stay unknown. Discovery reached its stop condition; no implementation follows. chilly-spark-3931 records an ineligible administrative dispatch, not product progress or a provider failure. Do not redispatch before eligibility or repeat completed qualification [rec: early-gate-3510] [rec: chilly-spark-3931] [rec: clear-crest-9910].

- [scope: qualified repair and deferred rehearsal | confidence: high | evidence: lawful-dune-3795] ADR-244 closes the reproduced worker snapshot defect with completed source/build/payload/CLI gates; earlier broken-cache descriptions below are historical. Concurrent mutation after validation and disruption of existing readers during corrupt-directory replacement remain possible; no general race safety is claimed. calm-beacon-7800 is an eligibility deferral, not a new failed provider attempt. Do not redispatch repair or repeatedly record the same pre-reset blocker [rec: lawful-dune-3795] [rec: calm-beacon-7800].

- [scope: worker snapshot integrity | confidence: high | evidence: nimble-basin-8423] In-place source mutation through a hardlink reproduces wrong bytes under an existing content-addressed name. Tested CMake copy/install primitives replace destination inodes and do not reproduce it; the historical writer and races remain unproved. Guidance is delivered (CLI 195 passed), but agent compliance is unmeasured [rec: nimble-basin-8423] [rec: misty-tide-6394].

- [scope: fused catalog diagnostic and provider availability | confidence: high | evidence: odd-ridge-9607] The accepted pan-tilt design has fourteen outputs and no catalog stamps; scanning published outputs cannot recover either fused servo. The generator tally captured in 997293b8 was unqualified at that time; windy-dune-3488 subsequently removed it and supplied ADR-243 with fresh gates. Do not redispatch that removal [rec: windy-dune-3488]. Calls cannot establish purchased quantities. The two-servo attempt was refused before design; quota percentages do not establish availability [rec: odd-ridge-9607] [rec: silent-mist-5233].

- [scope: completed updater writer pair | confidence: high | evidence: autumn-arrow-3125] Disable 95c1286d and delete 25445f70 landed separately with 2034 engine passes, one release build each, 162 baseline-only CTest failures and the retained App/Base translation probe. Surviving FreeCAD M totals are 56/1635/1881 versus the nt2 start 47/1804/1907; zero whole-file saving; Blender unchanged 44/1046/129. Do not redispatch; the updater's remaining commands, App/Base resources and Qt consumers stay. Direct external helper imports ceased to work. [rec: green-stone-3882] [rec: autumn-arrow-3125]

- [scope: stopped accessory delivery | confidence: high | evidence: steady-reef-0162] Neither category qualified. Horn geometry is measured, but exact mating and redistribution are unresolved; DS archive is inaccessible; cable lead has no manufacturer STEP. Raw Part.read is not the assumed script-owned route. No new candidate, approximation or importer is dispatched; both charter categories remain open. [rec: steady-reef-0162] [rec: noble-clover-4083]

- [scope: sole qualified updater boundary | confidence: high | evidence: cold-clover-8123] Audit and disposition have landed: only updateTranslatorCpp, its two dispatch sites and exclusive PySide import qualify. App/Base each retain 39 TS files and live Qt consumers; upload discovers sources independently. External use is unknown. Separate disable/delete evidence is required; no whole-updater deletion, resource/Qt removal, location cleanup or live network execution follows. Planning claims no implementation or delta saving. [rec: eager-garden-8009] [rec: cold-clover-8123] [rec: damp-sand-1115]

- [scope: completed Test Tk pair | confidence: high | evidence: silver-lodge-1952] Separate copy/install disable and 399-line source deletion landed, retaining all 37 other Test files. Fresh engine 2023 passed/52 skipped, packaged 26 passed, GUI-denied text 12 passed and Cadex CTests 4/4; inherited failures remain 162 with no new baseline names, full inventory unchanged. No stale runner source/bytecode remains in the four audited roots. Do not redispatch; whole-Test remains unqualified. FreeCAD current M totals 56/1634/1820, inherited remaining 3433. Local stage is not portable-release proof. [rec: simple-oak-4775] [rec: silver-lodge-1952]

- [scope: exhausted fifth-servo qualification | confidence: high | evidence: hidden-ridge-7342] HS-311 and HS-422 both fail unchanged ServoPart mounting-mouth compatibility; output-stack evidence is incomplete and HS-422 dimension labels conflict. No independent proof or delivery occurred. Stop the conditional proof/delivery, third-candidate search and recipe refactor until new evidence and an explicit later bet. Four servos and seven inclusively counted powered identities remain, not full breadth or L3 coverage. [rec: hidden-ridge-7342]

- [scope: qualified Test Tk boundary | confidence: high | evidence: humble-tide-6752] Earlier 'Test unaudited' observations are historical: only standalone unittestgui.py is now qualified, at one Test_SRCS copy/install row. Retain TestSources, MainCmd's dependency, Init.py registrations, data, TestGui/QtUnitGui and all other files. Audit native text tests passed 12 and existing-stage baseline passed 26, without fresh build/removal proof. Test being pruned from the payload alone proves nothing about build/install consumers. [rec: humble-tide-6752]

## Provenance

- lone-wood-3732 — retain directions without invention or retirement
- empty-wolf-3962 — fold pending long seed and full charter coverage
- humble-bell-9017 — correct catalog horizon placement; retain standing directions

- nimble-glade-6200 — correct obsolete L2 placement; no new direction and no charter-gap retirement

- strong-grotto-8980 — acknowledge shipped N20 and next family units; preserve all long directions without invention

- western-water-1442 — retain L12 delivery after sourced BLDC; preserve all remaining charter gaps

- sunny-lily-7639 — both L12 units landed; promote bounded solenoid work and preserve all broader gaps

- clever-falcon-0085 — promote joints after solenoid source follow-up; preserve deferred delivery and all charter gaps

- true-fox-1464 — fold verified joint delivery; audit residual L3 and advance reduction while preserving every charter gap

- silver-sage-7486 — fold completed audits; sequence Phase 8 prerequisites and conditional deletion, retaining all gaps

- solar-cove-9793 — correct completed Phase 8 placement and mixed delta measurements; preserve all directions and gaps

- quiet-canyon-3950 — correct Measure completion and latest metrics; preserve every long direction

- warm-anchor-2441 — correct Help placement and delta metrics; retain every direction

- still-quill-0059 — record the Help delete, the Start audit and the two-number delta convention; retain every direction

- fair-snow-3443 — update Start evidence condition and corrected delta measures; retain all directions

- frosty-dawn-2061 — correct completed GSL/Start/N20 facts; preserve every standing direction

- vast-oak-7458 — fold set A and parked RI50; bound shafted qualification and preserve every charter gap

- shady-ivy-2659 — fold completed MeshPart pair; bound Material audit/disable, correct metrics and preserve all gaps

- easy-sea-7738 — refresh completed removal metrics and deferred motor qualification; retain all directions

- tidy-sea-8308 — fold completed audit/reduction, promote existing visibility defect and preserve all charter obligations

- rough-gate-7949 — fold completed visibility work; promote one fifth-servo sequence and preserve every broader obligation

- twilight-wolf-7995 — fold failed servo qualification and qualified Test Tk boundary; preserve all charter gaps

- narrow-pebble-8020 — fold completed Tk pair and current metrics; promote existing manufacturer STEP gap without retiring charter obligations

- noble-clover-4083 — fold pending offline updater audit and stop conditional accessory delivery
- hollow-reef-8734 — reconcile exhausted accessory sequence and audit-only updater direction; preserve all charter gaps

- damp-sand-1115 — fold completed updater audit/disposition; dispatch only separate disable and conditional delete, retaining all charter gaps

- placid-delta-6677 — mark compound gearing dispatched and mission 6 next; refresh delta totals; retain every direction

- flat-river-8853 — record compound mechanisms one unit from closure and mission 6 dispatched; retain every direction

- glad-snow-3838 — record the walk's measured baseline as the standing-work bar; directions unchanged
- witty-brook-9419 — fold verified preview rehearsal; promote remaining section sequence and preserve scope and measurement limits

- sage-crow-3224 — fold delivered sections and integration; rank separate fresh rehearsal evidence and retain scope

- modest-grotto-1192 — fold paired rehearsal evidence and select bounded persistence maintenance; preserve parked scope

- green-wolf-7549 — fold clean cold revisit; select demonstrated recovery documentation correction and preserve parked scope

- first-wing-3387 — fold accepted recovery correction and reconciled handoff; select only narrow orientation snapshot maintenance

- civic-snow-4700 — fold completed orientation work and dispatch only the selected offboard-training guidance correction

- empty-rain-5162 — fold completed VISION corrections; select one bounded bundled-engine qualification direction, retaining all charter obligations

- spring-wolf-7431 — fold clean bundle refresh; select only bounded schema-check guidance maintenance, retaining all charter obligations

- salty-nest-8235 — exhaust guidance maintenance; standing lifecycle maintenance selects only the ladder-rule walk

- simple-raven-2485 — standing lifecycle maintenance selects the rerun and the swept fix; review baseline refreshed with the pan-tilt numbers
- forest-hollow-9339 — fold the rerun and swept fix as landed; close the clearance direction; select the ladder-rule leg walk and the fused-catalog inventory signal
- staid-willow-6557 — correct unqualified inventory source, promote placement guidance and retain a quota-gated rehearsal; preserve scope and prior evidence

- modest-valley-3313 — fold qualified tally removal; retain guidance and eligible rehearsal; select bounded cache diagnosis and defer dependency discovery
- [rec: amber-fjord-1560] — Fold landed guidance and diagnosis; select bounded snapshot repair and retain the eligible rehearsal.
- [rec: brave-pebble-4147] — Fold qualified worker repair, promote existing bounded discovery and retain the eligible rehearsal without repeated deferrals.

- [rec: clear-crest-9910] — Fold completed dependency limits and administrative dead end; retain only the eligible rehearsal.

- weathered-hill-5955 — fold the landed leg rehearsal; select the review-driven iterate and a conditional domain-doc unit; keep cold identity and breadth unselected

- forest-shade-2752 — fold durable walk and live notes; fix output label before resumed repair, retaining evidence limits

- gentle-wind-1003 — fold portable-label delivery and refused repair; select bounded offline metadata diagnosis with conditional correction

- cool-garden-5811 — fold completed refusal diagnosis and ADR-247; select one finite provider-free walk with conditional correction, preserving all parked scope

- polished-tide-5222 — fold completed rehearsal and artifact remediation; qualify first-visit Git ownership while preserving parked scope
- rich-creek-7708 — close completed Git guidance; select finite output-loss consent qualification and conditional correction, retaining parked scope

- sleepy-meadow-2615 — fold completed consent and parity handoff; select finite linked-part source-independence qualification, preserving parked scope

- green-shade-8828 — fold completed linked-part qualification and actor handoff; select narrow onboarding version correction, preserving parked scope

- cool-raven-8938 — fold completed onboarding and actor handoff; select exact stale suite-count removal, preserving lifecycle evidence and parked scope
- curious-badger-0797 — close accepted suite-count maintenance; require concrete new lifecycle evidence and a later bet before actor dispatch

- ancient-key-7299 — retire nt3's provider-credit parking under ADR-249, mark this machine as a fresh measurement baseline, and name the standing thing to prove: assembly.mjcf must return for a rig the design agent actually produces

- glad-mesa-6299 — record this machine's clean walk baseline, retire the assembly.mjcf thing-to-prove as proved, and put walk-exposed reliability in its place as standing work

- western-reef-4119 — fold second-mechanism and mode evidence; bound evidence reporting and retain parked directions
