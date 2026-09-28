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

**Where it stands:** the biped and the quadruped each have a design meeting every bar item; the hexapod has none after five attempts, and attempt 5 misses on the swept fit only [rec: humble-lily-1303] [rec: patient-banner-4052].

- **Prompts frozen** (commit `13246076`): the hexapod prompt verbatim from hex1–hex3, a quadruped, and a biped; `claude-opus-5-5`, `CADEX_EFFORT=medium`, one turn each [rec: soft-spark-6990].
- **P2 figures below are post-ADR-424** (world geometry — the floor — left out; see `warm-basin-7003`). Re-scoring changed no A5 verdict; the judge never sees P2 [rec: amber-flame-4976].

### Passing designs
- **Biped** — `ot10-biped-1`, revision `44b8497b`: static fit clean, swept fit complete and passing (6/6, the run's first), judged blind **15/21** (calls 15, 15, 16), P1 0.002, P2 0.103, P3 3, electronics carried. Scoring needed ADR-421's restore fix [rec: wise-walrus-6002] [rec: pale-ledge-0992] [rec: amber-flame-4976].
- **Quadruped** — `ot10-quadruped-3`, revision `7de6eea6` (frozen prompt/argv/model/effort, started `b20bb7a0`; launched by an iteration that left no record, found by amber-flame and published as conforming): judged **15/21** (calls 15, 15, 16; no trait 0), P1 0.0001, P2 0.116, P3 3, static fit clean (1,891 pairs), **swept fit 8/8 at 10°**, electronics carried. 0 CPU refusals; its binding limit was the 2,000-pair sweep budget (82 → 62 components). It overlapped hexapod-4 in time; recorded, not causal, since `RLIMIT_CPU` charges CPU time [rec: amber-flame-4976] [rec: humble-lily-1303].

### Failing attempts (every one published)
- `ot10-hexapod-1` (`7af6db09`): 13/21 vs bar 14, P2 0.508 fail, swept fit incomplete; the agent stripped caps, fillets and the sweep for the 300 CPU-s limit [rec: soft-spark-6990] [rec: amber-flame-4976].
- `ot10-hexapod-2` (`996a0b7e`): 14/21, P2 0.134, sweep turned off on the 180 s budget [rec: quiet-basin-1176]. `ot10-quadruped-1` was a harness stop, not an attempt [rec: late-glacier-7593].
- `ot10-quadruped-2` (`27ba92c6`): 16/21, P2 0.040, sweep off (budget) [rec: western-comet-0121].
- `ot10-hexapod-3` (`39dc8d60`): first complete hexapod sweep (12/12 at 20°), 13/21 — face too small and graphite-on-graphite (T5 1), flat star plate (T4 1) [rec: tiny-dusk-3648].
- `ot10-hexapod-4` (`f0b98de4`): all fit gates pass (sweep 12/12 at 15°), P2 0.220, 12/21 — T5 rose 1→2 after ADR-422, but accent feet and hip caps were dropped for the CPU cap (8 refusals) [rec: rustic-ivy-4753].
- `ot10-hexapod-5` (`d2198144`, frozen prompt/argv/model/effort, started `3008e1f7`; launched by an errored iteration, completed on its own and published as conforming): judged **16/21** (all calls 16; no trait 0; the highest hexapod total), P1 0.013, P2 0.168, P3 3, static fit clean (1,653 pairs), electronics carried, 12 accent joint caps back — but **swept fit incomplete, 10/12 joints** (`hip_rr` over budget, `knee_rr` not reached) under the 180 s `_SWEEP_TOTAL_SECONDS` even at 80° steps [rec: patient-banner-4052].
- Hexapod judged totals so far: 13, 14, 13, 12, 16 [rec: patient-banner-4052].

### Fixes made along the way
- ADR-418: workers pinned to 4 CPUs; 15 of attempt 1's 19 CPU refusals accept under the unchanged 300 CPU-s cap [rec: strong-summit-4135].
- ADR-419: the sweep measures near moving pairs exactly and bounds far ones; hexapod-2 replay 0/12 → 12/12 joints in 112 s [rec: western-comet-0121].
- ADR-420: swept findings against world geometry are advisory under `fit.sweep.world_geometry` [rec: fresh-timber-5181].
- ADR-423: static clearance bounds far pairs; the refused accent-feet candidate 416.6 → 114.5 CPU-s [rec: lucid-glacier-4889]. **Confirmed on a fresh turn:** hexapod-5 had 0 CPU-limit refusals (hexapod-4 had 8) and kept its accents [rec: patient-banner-4052].

### Still open
- A passing hexapod. The binding limit has moved to the swept fit's wall-time budget (one `FreeCADCmd` child per joint, in series; `_SWEEP_JOINT_SECONDS = 90`). Coarsening to 80° still left 10/12, which suggests a fixed per-joint cost (deserialising 58 BREPs, preparing moving pairs) — an inference from step changes, not a profile. The recorded next unit is to profile the sweep's wall time on a `/tmp` copy of `ot10-hexapod-5` and fix it with a regression test, before any new hexapod attempt and without changing a prompt or the language [rec: patient-banner-4052].
- Product gap seen twice (quadruped-3, hexapod-5): the build reply is too large for the agent to read (59.8 KB on hexapod-5), so it pages `inspect scope=clearance` by hand — 250 of 1,653 static pairs checked on hexapod-5 [rec: humble-lily-1303] [rec: patient-banner-4052].
- T4 (form) is the recurring weak trait; it reached 2 on quadruped-3 and hexapod-5. The hero camera (`render.HERO`, 35° from −Y) sees a +X face nearly edge-on; ADR-422 records it as *Not taken*, and it is a renderer unit, not the cause of a miss [rec: rustic-ivy-4753] [rec: patient-banner-4052].
- Measurement hygiene: re-measure and score only on `/tmp` copies — restore opens are not read-only (they bump `script.json`); hex1–hex3 are read-only. `cadex render` re-accepts through `rebuild`, so scoring moves `accepted_digest` with the revision unchanged [rec: amber-flame-4976] [rec: humble-lily-1303] [rec: pale-ledge-0992].

## Negative knowledge

- [scope: ot10-hexapod-1, one design-only turn, before ADR-418 | confidence: high | evidence: soft-spark-6990, strong-summit-4135] Under a host-dependent CPU cap, the agent meets the budget by deleting the design language's refinements (caps, fillets) and skipping the swept fit. The score then drops on exactly the traits A5 is judged on. A refusal about budget costs quality, not just time.
- [scope: ot10-hexapod-2 and ot10-quadruped-2, before ADR-419 | confidence: high | evidence: quiet-basin-1176, western-comet-0121] When the swept fit's 180 s budget cannot cover a 12-joint robot, the agent turns the sweep off to get accepted — so judged quality can meet the bar while the fit criterion still fails.
- [scope: ot10-hexapod-3 and ot10-hexapod-4, 300 CPU-s cap before ADR-423 | confidence: medium | evidence: tiny-dusk-3648, rustic-ivy-4753, lucid-glacier-4889] Teaching one more rule moves the trait it targets but not the total: with the cap still binding, the agent pays for the new rule by dropping another refinement (hexapod-4: face up, accent and caps gone). The cap was the binding limit, not an untaught rule.
- [scope: ot10-hexapod-5, after ADR-419/ADR-423, 58 components | confidence: medium | evidence: patient-banner-4052] Coarsening `sweep_step_degrees` (10 → 80) does not bring a 12-joint, 58-component hexapod inside the 180 s sweep budget; the step size is not the lever.

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
