---
node_id: 58dfc260-2bfa-5cf5-b746-e50f471cf37c
slug: loyal-fountain-8709
title: A5. Unassisted designs meet the bar on more than one body plan
created_at: '2026-09-27T15:18:35+00:00'
parents:
- nimble-pine-0740
summary: ''
---
Status: open

## Current

Open charter criterion for run ot10: **A5. Unassisted designs meet the bar on more than one body plan.** - Frozen cold prompts for a hexapod, a quadruped and one body plan of the run's choosing, with frozen flags, each get one design-only product turn on a new `ot10-*` project. - Every design is accepted with zero failing static fit checks and a complete, passing swept fit. - Every design carries its electronics, is rendered by A2, and is scored blind under A1's procedure. - Every design meets A1's bar, and each one scores above the hex3 baseline. - One failing design fails this criterion. Publish every attempt and every score. [rec: damp-dusk-8045]

Declared target: `gap-a5-unassisted-designs-meet-bar`. This node tracks the criterion as a gap; it becomes working only with causally parented, measured evidence that the criterion is met. The human owns the charter checkbox; roles report results and do not tick it. The directive's impact line is truncated; its wording is resolved from the full charter carried verbatim in the same record [rec: damp-dusk-8045].

**Where it stands:** A5 is **not met by its letter**. Counted turns are **17 with 11 misses** (hexapods 1–8 and 12, quadruped-2, biped-2), and each miss fails A5 by itself under the clause "one failing design fails this criterion". The confirmation round closed **2 of 3**: hexapod-11 and quadruped-4 meet the bar, and biped-2 misses at 2/21 on an engine publication leak that ADR-434 has since fixed. A separately pre-registered biped turn, `ot10-biped-3`, then **met the bar at 14/21**. It is a new attempt, not a re-score, so no miss is withdrawn. **Six designs meet the bar, two per body plan** [rec: chilly-willow-8488] [rec: civic-falcon-6725] [rec: tidy-banner-2442] [rec: old-cabin-6515]. A further pre-registered hexapod turn, `ot10-hexapod-12`, **missed at 12/21** on its total alone — the eleventh miss; `ot10-hexapod-13` is pre-registered and not yet run [rec: sweet-harvest-8650] [rec: smooth-ivy-2460]. `docs/probes/ot10/REPORT.md` states this at HEAD (commits `eaef9f93`, `d75664fc`). At HEAD the engine suite is 2247 passed / 53 skipped, the CLI suite 1068 passed / 1 skipped and the packaged gate 23 passed. Done has been claimed for critic review, and the owner's boxes stay unticked. The node stays `open`, because the verdict by the letter is unchanged [rec: old-cabin-6515]. First round: 12 counted turns with 9 misses, where the charter allows one turn per body plan. The highest bar reached is one passing design per plan — biped-1 (15/21), quadruped-3 (15/21) and hexapod-10 (14/21) — every failed attempt published, no success redefined [rec: soft-cliff-8778]. A **confirmation round** is pre-registered at `96ed90d0`: one frozen turn per plan (`ot10-hexapod-11`, `ot10-quadruped-4`, `ot10-biped-2`), scored unchanged, all twelve earlier turns still counted, A5 not redefined [rec: honest-dawn-9522]. The hexapod took ten launches in the first round: fit misses were fixed at the source (ADR-425/426/427), the form miss taught (ADR-428), and a document wedge fixed (ADR-429) [rec: fierce-vale-7652] [rec: brisk-lodge-6248].

- **Prompts frozen** (commit `13246076`): the hexapod prompt verbatim from hex1–hex3, a quadruped, and a biped; `claude-opus-5-5`, `CADEX_EFFORT=medium`, one turn each [rec: soft-spark-6990].
- **P2 figures below are post-ADR-424** (world geometry — the floor — left out; see `warm-basin-7003`). Re-scoring changed no A5 verdict; the judge never sees P2 [rec: amber-flame-4976].

### Passing designs (first round)
- **Biped** — `ot10-biped-1`, revision `44b8497b`: static fit clean, swept fit complete and passing (6/6, the run's first), judged blind **15/21** (calls 15, 15, 16), P1 0.002, P2 0.103, P3 3, electronics carried. Scoring needed ADR-421's restore fix [rec: wise-walrus-6002] [rec: pale-ledge-0992] [rec: amber-flame-4976].
- **Quadruped** — `ot10-quadruped-3`, revision `7de6eea6` (frozen prompt/argv/model/effort, started `b20bb7a0`; launched by an iteration that left no record, found by amber-flame and published as conforming): judged **15/21** (calls 15, 15, 16; no trait 0), P1 0.0001, P2 0.116, P3 3, static fit clean (1,891 pairs), **swept fit 8/8 at 10°**, electronics carried. 0 CPU refusals; its binding limit was the 2,000-pair sweep budget (82 → 62 components). It overlapped hexapod-4 in time; recorded, not causal, since `RLIMIT_CPU` charges CPU time [rec: amber-flame-4976] [rec: humble-lily-1303].

- **Hexapod** — `ot10-hexapod-10`, revision `e8a82deb` (frozen prompt/argv/model/effort, launched at `9f13d33d` after ADR-429): judged **14/21** (all three calls T1 2, T2 2, T3 1, T4 2, T5 2, T6 3, T7 2; no trait 0), P1 0.0026, P2 0.1415, P3 3, every component declares a role, static fit clean (1,326 pairs, 0 intersections, only the floor's advisory row), **swept fit 12/12 at 10°**, electronics carried (ESP32, PCA9685, BNO085, D36V50F6, 2S LiPo, 12 × MG90S), MJCF and a walking task accepted. 6 CPU-limit refusals, escaped by swapping lofts for filleted boxes (ADR-428's advice). Weakest traits: T3 (bare hip pins, shell-coloured servo boxes under the body), then T5 (generic slot visor) [rec: fierce-vale-7652].

### Confirmation round (pre-registered at `96ed90d0`)
- **Turn 1 — `ot10-hexapod-11`** (frozen hexapod prompt, launched at `4288ef42`; commit `b2b40bff`): **meets the bar on every item** — judged **14/21** (T1–T7 2,3,1,2,2,2,2; three identical calls), P1 0.0186, P2 0.2285, P3 3, static fit clean, **swept fit complete and passing 12/12**, electronics carried [rec: wise-sea-0110].
- **Turn 2 — `ot10-quadruped-4`** (frozen quadruped prompt, `c2ee7399`, opus-5-5, effort medium, no continuation; commit `5ff575f5`): **meets the bar** — judged **16/21** (T1–T7 2,3,3,1,2,3,2), P1 0.0022, P2 0.1624, P3 3, static fit clean, **swept fit 8/8 passing**, electronics carried [rec: tidy-pebble-6206].
- **Turn 3 — `ot10-biped-2`** (frozen biped prompt, launched at `15f2bf9e`; commit `e7dcfc22`): **misses at 2/21** (T1–T7 0,1,0,0,0,0,1), P1/P2 unmeasured, P3 4, no fit, no electronics; exit 0 at a servo-orientation probe. **Not a looks verdict:** a publish refused mid assembly pass (an actuator stored as an output) leaked 43 objects into the live document under `UndoMode 0` and wedged every later write — the gap ADR-429 had recorded. Fixed by ADR-434 (details in `forest-wind-0342`); the miss stands [rec: chilly-willow-8488] [rec: civic-falcon-6725].
- **`ot10-biped-3`** (separately pre-registered at `e24ff330`, frozen biped prompt, a new project, on the ADR-434 engine; commit `98decddb`): **meets the bar** — judged **14/21** (medians T1–T7 2,2,2,1,3,2,2; T5 3), P1 0.0035, P2 0.2214, P3 3, static fit clean (2,485 pairs), **swept fit complete and passing 6/6**, electronics carried with MJCF and task; score file, renders, sheet and census row published [rec: tidy-banner-2442].
- A4 census: 0 of 208 refusals in the taught classes across 17 transcripts after the round [rec: chilly-willow-8488]; 0 of 213 across 18 after biped-3 [rec: tidy-banner-2442].

### After the confirmation round
- **`ot10-hexapod-12`** (pre-registered at `e4d3fd28`, frozen hexapod prompt and flags, a new project, on the ADR-435..438 engine; commit `b67ab975`): **misses at 12/21** (three calls 12, 12, 12; medians T1–T7 2,2,1,1,2,2,2). Every other item meets: P1 0.0038, P2 0.1844, P3 3, static fit clean (1,953 pairs, 0 intersections), **swept fit complete and passing 12/12 at 10°**, electronics carried with a walking task. Nothing re-scored [rec: sweet-harvest-8650].
  - Diagnosis, two halves. **Renderer:** the clustering grid was sized over the agent's undrawn 3,000 mm floor, so the robot drew on a 1.465 mm cell (52,303 of 970,004 triangles) and every judge call named faceted legs. Fixed by ADR-439 (`ab60e2c7`, see `damp-moon-9297`): the same revision now draws on a 0.271 mm cell, 352,317 triangles, 14.5 s; the 12/21 stands as taken [rec: sweet-harvest-8650] [rec: hidden-bloom-1188]. **Design:** T3 1 in all three calls, splined cross horns bare beside the pods — the hexapods' standing T3 weakness [rec: sweet-harvest-8650].
- **ADR-440** (`deccf6d9`): the CLI overlay now teaches the driven part's hub as the joint cap *over* the horn, radius ≥ horn `.spec["arm_reach_mm"]` + 1.6 mm, cut with `horn.body`; hexapod-12's caps sat on the servo's far face. Two regressions fail on the old overlay; rubric, proxies, bar and judging unchanged; the overlay is not pinned by `contract.json` (ADR-422/428 changed it the same way) [rec: smooth-ivy-2460].
- **`ot10-hexapod-13`** is pre-registered with the frozen prompt and flags, **not yet run** [rec: smooth-ivy-2460].
- A4 census: 0 of 221 refusals in the taught classes across 19 transcripts after hexapod-12 [rec: sweet-harvest-8650].

### Failing attempts (first round, every one published)
- `ot10-hexapod-1` (`7af6db09`): 13/21 vs bar 14, P2 0.508 fail, swept fit incomplete; the agent stripped caps, fillets and the sweep for the 300 CPU-s limit [rec: soft-spark-6990] [rec: amber-flame-4976].
- `ot10-hexapod-2` (`996a0b7e`): 14/21, P2 0.134, sweep turned off on the 180 s budget [rec: quiet-basin-1176]. `ot10-quadruped-1` was a harness stop, not an attempt [rec: late-glacier-7593].
- `ot10-quadruped-2` (`27ba92c6`): 16/21, P2 0.040, sweep off (budget) [rec: western-comet-0121].
- `ot10-hexapod-3` (`39dc8d60`): first complete hexapod sweep (12/12 at 20°), 13/21 — face too small and graphite-on-graphite (T5 1), flat star plate (T4 1) [rec: tiny-dusk-3648].
- `ot10-hexapod-4` (`f0b98de4`): all fit gates pass (sweep 12/12 at 15°), P2 0.220, 12/21 — T5 rose 1→2 after ADR-422, but accent feet and hip caps were dropped for the CPU cap (8 refusals) [rec: rustic-ivy-4753].
- `ot10-hexapod-5` (`d2198144`, frozen prompt/argv/model/effort, started `3008e1f7`; launched by an errored iteration, completed on its own and published as conforming): judged **16/21** (all calls 16; no trait 0; the highest hexapod total), P1 0.013, P2 0.168, P3 3, static fit clean (1,653 pairs), electronics carried, 12 accent joint caps back — but **swept fit incomplete, 10/12 joints** (`hip_rr` over budget, `knee_rr` not reached) under the 180 s `_SWEEP_TOTAL_SECONDS` even at 80° steps [rec: patient-banner-4052].
- `ot10-hexapod-6` (`3cb2b1d0`, frozen prompt/argv/model/effort, started `feb2190b`): judged **15/21** (no trait 0), P1 0.009, P2 0.198, P3 3, electronics carried — but the accepted `fasteners=1` revision's **swept fit was incomplete, 0/12** (pair budget exceeded: 87 components, 3,741 pairs > `_SWEEP_MAX_PAIRS` 2,000, a count that included rigid pairs the sweep never moves), and **six feet resting on `c_floor` read below clearance in the static pass**. With 63 components the sweep had passed 12/12 at 5°, confirming ADR-425 on a fresh turn [rec: true-rose-1584].
- `ot10-hexapod-7` (`f0a77bfb`): judged **13/21** < 14 — miss. Every measured item passes: P1 0.033, P2 0.247, P3 3, static fit clean with 6 advisory floor contacts, **sweep 12/12 at 17.5°** — the first hexapod clean on both fit halves. Diagnosis: constant-section legs and servo-shaped graphite cradles read as exposed servos (P1 is blind to printed cradles). The A4 failure classes did not recur. quadruped-3 still meets the bar under ADR-426/427 and was not rerun [rec: first-journey-3938].
- `ot10-hexapod-8` (`b69465f9`, launched at `070a8c23` after ADR-428): judged **8/21** (T5 0), swept fit incomplete (0/12), no electronics, MJCF or task — **not a looks verdict**: three builds hit the 300 CPU-s cap (superellipse lofts), then the live document wedged on `PUBLICATION_UNTAGGED_OBJECT ['Joints','Joints001']` and the accepted revision is a leg probe with a box body. Static fit clean (946 pairs), P1 0.020, P2 0.097, P3 2 [rec: shady-ember-3607].
- `ot10-hexapod-9`: a harness kill (the launching session ended ~4 min in; no exit file, no accepted revision), not an attempt; kept read-only as the receipt [rec: fierce-vale-7652].
- Hexapod judged totals: 13, 14, 13, 12, 16, 15, 13, 8, then 14 (passing) [rec: first-journey-3938] [rec: shady-ember-3607] [rec: fierce-vale-7652].

### Fixes made along the way
- ADR-418: workers pinned to 4 CPUs; 15 of attempt 1's 19 CPU refusals accept under the unchanged 300 CPU-s cap [rec: strong-summit-4135].
- ADR-419: the sweep measures near moving pairs exactly and bounds far ones; hexapod-2 replay 0/12 → 12/12 joints in 112 s [rec: western-comet-0121].
- ADR-420: swept findings against world geometry are advisory under `fit.sweep.world_geometry` [rec: fresh-timber-5181].
- ADR-423: static clearance bounds far pairs; the refused accent-feet candidate 416.6 → 114.5 CPU-s [rec: lucid-glacier-4889]. **Confirmed on a fresh turn:** hexapod-5 had 0 CPU-limit refusals (hexapod-4 had 8) and kept its accents [rec: patient-banner-4052].
- ADR-425: the sweep measures exact distances on boundary shells when no solid can nest; the accepted hexapod-5 request replays **12/12 in 125.1 s** (was 9/12 at 180 s), all 14,877 shared rows identical; budget, prompt and language unchanged [rec: swift-trail-3183].
- ADR-426 (`c8e02559`): the 2,000-pair sweep budget counts only the pairs a joint moves (the only ones measured). On hexapod-6 hips move 770 pairs and knees 332; a `/tmp` replay of `3cb2b1d0` went **0/12 → 12/12 complete, pass, in 97.9 s** (12 advisory `c_floor` rows). Attempt 6's accepted project and verdict are unchanged [rec: smooth-sky-9692].
- ADR-427: a below-clearance static pair against world geometry (a foot resting on the floor, 0.0 mm, 0.0 mm³) is reported under `world_geometry_contacts` and never fails; an intersection or an unmeasured pair still fails. hexapod-6's accepted revision replays 7 failing static rows → 1 (the floor's own advisory row), 6 contacts, sweep 12/12; attempt 6 stays a miss. Suites 2239 passed/53 skipped and 1012 passed/1 skipped at `cafd3960` [rec: steady-aspen-0430].
- ADR-428: the overlay and `docs/DESIGN-LANGUAGE.md` now teach depth taper to a foot and that servo-shaped printed cradles must be covered or rounded (regression in `test_turn_loop.py`) [rec: lawful-basin-3006]. Hexapod-8's legs taper to a ball foot in side view [rec: shady-ember-3607]; hexapod-10 escaped CPU refusals the way it advises [rec: fierce-vale-7652].
- ADR-429: renaming the assembly output re-keys the live assembly instead of wedging the document (details in `forest-wind-0342`) [rec: brisk-lodge-6248].
- ADR-434: a refused project publish rolls back completely, and an output type with no publisher (`actuator`) is refused at validation — the leak that ended biped-2 (details in `forest-wind-0342`) [rec: civic-falcon-6725].

- ADR-436/437/438: CPU-limit refusals name their costly stages; the static fit skips needless `common`, searches housing faces best first and cuts touching pairs to their shared region — hexapod-10's refused build static fit 1,143 → 600 CPU-s, rows identical (details in `forest-wind-0342`) [rec: mellow-light-0451] [rec: flat-tower-6825] [rec: scarlet-crane-7693].

### Still open
- `docs/probes/ot10/REPORT.md` lists every counted A5 turn and states the verdict plainly: not met by its letter (16 turns, ten misses at `old-cabin-6515`; hexapod-12 makes 17 and eleven). Whether to accept it is the owner's call [rec: old-cabin-6515] [rec: sweet-harvest-8650].
- CPU-limit refusals remain the largest refusal class (44 of 213 measured; hexapod-8: 3 of 20; hexapod-10: 6 of 15) [rec: shady-ember-3607] [rec: fierce-vale-7652] [rec: mellow-light-0451]. Diagnosed on hexapod-10's refused 12:40 build: geometry took 119 CPU-s and the static fit the rest. ADR-436/437/438 (details in `forest-wind-0342`) name the costly stages in the refusal and cut the static fit's housing and touching-pair cost; the build now passes every tub pair and tub/visor and dies at 292 CPU-s in dome/pca9685, with geometry (tub 73 s) and deck/dome 25 s the named remainder. The first real turn since, hexapod-12, had **0 CPU-limit refusals of 8** against hexapod-10's 6 of 15 — one turn against one, a different design, so not a rate and no causal claim for ADR-436..438 [rec: mellow-light-0451] [rec: flat-tower-6825] [rec: scarlet-crane-7693] [rec: sweet-harvest-8650].
- The build reply that was too large to read (59.8 KB on hexapod-5, so the agent paged `inspect scope=clearance` by hand) is now bounded for the model by ADR-435, about 12–14 KB on ot10 projects (see `chilly-union-8972`) [rec: humble-lily-1303] [rec: patient-banner-4052] [rec: sharp-tide-2612].
- T4 (form) is the recurring weak trait; it reached 2 on quadruped-3 and hexapod-5. The hero camera (`render.HERO`, 35° from −Y) sees a +X face nearly edge-on; ADR-422 records it as *Not taken*, and it is a renderer unit, not the cause of a miss [rec: rustic-ivy-4753] [rec: patient-banner-4052]. A different renderer defect did bear on hexapod-12's T4: the floor-sized clustering grid, fixed by ADR-439; every earlier decimated ot10 render would now draw finer than it was judged, recorded as a finding, nothing re-scored [rec: hidden-bloom-1188].
- Measurement hygiene: re-measure and score only on `/tmp` copies — restore opens are not read-only (they bump `script.json`); hex1–hex3 are read-only. `cadex render` re-accepts through `rebuild`, so scoring moves `accepted_digest` with the revision unchanged [rec: amber-flame-4976] [rec: humble-lily-1303] [rec: pale-ledge-0992].

## Negative knowledge

- [scope: ot10-hexapod-1, one design-only turn, before ADR-418 | confidence: high | evidence: soft-spark-6990, strong-summit-4135] Under a host-dependent CPU cap, the agent meets the budget by deleting the design language's refinements (caps, fillets) and skipping the swept fit. The score then drops on exactly the traits A5 is judged on. A refusal about budget costs quality, not just time.
- [scope: ot10-hexapod-2 and ot10-quadruped-2, before ADR-419 | confidence: high | evidence: quiet-basin-1176, western-comet-0121] When the swept fit's 180 s budget cannot cover a 12-joint robot, the agent turns the sweep off to get accepted — so judged quality can meet the bar while the fit criterion still fails.
- [scope: ot10-hexapod-3 and ot10-hexapod-4, 300 CPU-s cap before ADR-423 | confidence: medium | evidence: tiny-dusk-3648, rustic-ivy-4753, lucid-glacier-4889] Teaching one more rule moves the trait it targets but not the total: with the cap still binding, the agent pays for the new rule by dropping another refinement (hexapod-4: face up, accent and caps gone). The cap was the binding limit, not an untaught rule.
- [scope: ot10-hexapod-5, after ADR-419/ADR-423, 58 components | confidence: medium | evidence: patient-banner-4052] Coarsening `sweep_step_degrees` (10 → 80) does not bring a 12-joint, 58-component hexapod inside the 180 s sweep budget; the step size is not the lever. ADR-425 brought it inside (12/12 in 125.1 s) by changing how the exact distance is measured, not the step [rec: swift-trail-3183].

- [scope: ot10-hexapod-7's build, 300 CPU-s cap, 180 s sweep wall budget | confidence: high | evidence: lawful-basin-3006] The swept fit is not the build's CPU cost: the domain worker spends ~210 CPU-s of 300 with the sweep on (210) or off (212), because the sweep runs in per-joint children bounded by its own 180 s wall budget (10° incomplete at `hip_rr`; 17.5° complete in 129 s). Changing the sweep step or budget would not free CPU for refinement; no sweep/budget change was made.

## Provenance

- damp-dusk-8045 — ot10 operator-declared charter gap
- soft-spark-6990 — A5 attempt 1: hexapod 13/21 blind (bar 14), P2 and swept fit fail; the CPU cap is the cause
- strong-summit-4135 — ADR-418: the cap was mostly thread overhead; 15 of 19 refusals now accept, 4 remain on real work
- late-glacier-7593 — hexapod attempt 2 launched on ot10-hexapod-2 at 6dd4ce81; ot10-quadruped-1 a harness stop
- quiet-basin-1176 — hexapod attempt 2: 14/21 meets the bar, P1–P3 pass, swept fit off on budget → misses A5
- western-comet-0121 — ADR-419: 12/12 joints swept in 112 s; quadruped 16/21, swept fit off → misses A5
- fresh-timber-5181 — ADR-420: world-geometry swept findings advisory; hexapod-2 replay sweep fail → pass, 12/12
- wise-walrus-6002 — biped attempt: first complete passing swept fit, unscored because the restore fingerprint refused a reopen
- pale-ledge-0992 — ADR-421 replay: biped 15/21, P1 0.002, meets every A5 bar item
- tiny-dusk-3648 — hexapod attempt 3: first complete 12/12 hexapod sweep, every fit gate passes, judged 13/21 misses 14; face too small and graphite-on-graphite
- rustic-ivy-4753 — hexapod attempt 4 after ADR-422: fit gates pass, T5 1→2, judged 12/21 misses 14; accent and caps dropped for the CPU cap
- lucid-glacier-4889 — ADR-423 located the CPU cap in static clearance and lifted it: refused accent-feet candidate 416.6 → 114.5 CPU-s
- amber-flame-4976 — ADR-424: P2 leaves out the floor, all probes re-scored, no A5 verdict changed; unrecorded ot10-quadruped-3 found
- humble-lily-1303 — ot10-quadruped-3 conforms and meets every A5 bar item (15/21, swept 8/8); second passing body plan
- patient-banner-4052 — ot10-hexapod-5 judged 16/21 but swept fit 10/12 under the sweep budget; 0 CPU refusals confirm ADR-423
- swift-trail-3183 — ADR-425: swept fit on boundary shells; hexapod-5's accepted request replays 12/12 in 125.1 s, rows identical
- true-rose-1584 — hexapod attempt 6 judged 15/21, misses A5: sweep 0/12 on the pair budget, six feet below clearance on c_floor
- smooth-sky-9692 — ADR-426: sweep pair budget counts moving pairs; hexapod-6 replay 0/12 → 12/12 in 97.9 s
- steady-aspen-0430 — ADR-427: resting world-geometry contacts advisory at the solved pose; hexapod-6 replay 7 failing static rows → 1
- first-journey-3938 — hexapod attempt 7 judged 13/21, misses A5 on T3/T4; static fit and sweep 12/12 both pass
- lawful-basin-3006 — ADR-428: hexapod-7 build CPU measured (sweep off 212 vs on 210 CPU-s); depth taper and cradles taught in the overlay
- shady-ember-3607 — hexapod attempt 8 judged 8/21; live document wedged on orphaned Joints groups, not a looks verdict
- brisk-lodge-6248 — ADR-429 fixes the hexapod-8 wedge; hexapod attempt 9 named the next probe
- fierce-vale-7652 — hexapod attempt 10 meets every A5 bar item at 14/21; attempt 9 a harness kill
- lawful-tooth-6508 — REPORT.md tables all 12 counted A5 turns; the failing-design clause is left to the owner
- soft-cliff-8778 — C1 re-claim: A5 not met by its letter (12 turns, 9 misses); highest bar is one passing design per plan
- honest-dawn-9522 — confirmation round pre-registered at 96ed90d0: one frozen turn per plan, scored unchanged, earlier turns still counted
- wise-sea-0110 — confirmation turn 1: ot10-hexapod-11 meets every bar item at 14/21, swept 12/12
- tidy-pebble-6206 — confirmation turn 2: ot10-quadruped-4 meets the bar at 16/21, swept 8/8
- chilly-willow-8488 — confirmation turn 3: ot10-biped-2 misses at 2/21 on a publication leak; round closes 2 of 3, ten misses
- civic-falcon-6725 — ADR-434 fixes the biped-2 leak; no score changes; next is a new biped turn
- tidy-banner-2442 — ot10-biped-3, a separate pre-registration, meets the bar at 14/21 with swept fit 6/6; six designs now meet the bar, ten misses stand
- old-cabin-6515 — REPORT.md at HEAD states the A5 clause (16 turns, 10 misses); suites green; done claimed for critic review
- mellow-light-0451 — CPU-limit class (44 of 213) diagnosed on hexapod-10; ADR-436 names costly stages and skips needless common; no A5 probe since
- flat-tower-6825 — ADR-437: refused hexapod-10 build now passes every tub pair, dies at 293 CPU-s in deck/dome
- scarlet-crane-7693 — ADR-438: refused hexapod-10 build passes tub/visor, dies at 292 CPU-s in dome/pca9685; no A5 probe since
- sweet-harvest-8650 — ot10-hexapod-12 misses at 12/21 on its total; 0 CPU-limit refusals of 8; diagnosed as floor-sized render grid plus bare horns
- hidden-bloom-1188 — ADR-439 render grid fix; hexapod-12's same revision draws finer, nothing re-scored
- smooth-ivy-2460 — ADR-440 overlay teaches the cap over the horn, sized from its spec; hexapod-13 pre-registered, not run
