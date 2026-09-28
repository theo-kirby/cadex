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

- **Prompts frozen** (commit `13246076`): the hexapod prompt verbatim from hex1–hex3, a quadruped, and a biped; `claude-opus-5-5`, `CADEX_EFFORT=medium`, one turn each [rec: soft-spark-6990].
- **Attempt 1 fails the bar** — `ot10-hexapod-1`, revision `7af6db09`: judged blind **13/21 against a bar of 14** (far above the hex3 baseline of 2), P1 0.078, **P2 0.655 FAIL**, P3 3, static fit clear, **swept fit incomplete FAIL**, electronics carried. The agent stripped caps, fillets and the sweep to fit the 300 CPU-s limit [rec: soft-spark-6990].
- **CPU limit mostly removed** (ADR-418, `d14f3b32`): 32-CPU OCCT threading tripled the CPU-s charge of `distToShape`; with workers pinned to 4 CPUs, 15 of attempt 1's 19 CPU refusals accept under the unchanged 300 CPU-s cap, and 4 still exceed it on real exact-distance work [rec: strong-summit-4135].
- **Hexapod attempt 2** — `ot10-hexapod-2`, launched detached at `6dd4ce81` (after ADR-418) [rec: late-glacier-7593]; accepted revision `996a0b7e` scored **14/21 median (meets 14)**, P1 0.022, P2 0.088, P3 3, static fit clean — but the agent turned the swept fit off after the 180 s `_SWEEP_TOTAL_SECONDS` budget ran out on the first hip at 63 components, so it **misses A5** [rec: quiet-basin-1176]. An earlier `ot10-quadruped-1` was killed 8 min in with no design; it is a harness stop, not an attempt [rec: late-glacier-7593].
- **Quadruped attempt** — `ot10-quadruped-2`, revision `27ba92c6`: **16/21 median (meets 14)**, P1 0.004, P2 0.238, P3 3, static fit clean, swept fit off (budget), so it also **misses A5** [rec: western-comet-0121].
- **The sweep now fits a 12-joint robot** (ADR-419, `f08f336b`): the joint sweep measures near moving pairs exactly, bounds far ones (>10 mm box gap, culled lower bound) and stops re-measuring rigid pairs. Replayed on `ot10-hexapod-2` it sweeps **12/12 joints in 112 s** of the 180 s budget (was 0/12; one hip 287 s → 7.3 s). The complete sweep then fails only on knee foot/tibia vs `c_floor` — an undecided policy question, not a measurement gap [rec: western-comet-0121].
- **Swept findings against world geometry are advisory** (ADR-420, `9cf27ea6`): a swept pair with a world-geometry side (e.g. `c_floor`, detected by the engine's existing rule, not by name) is published under `fit.sweep.world_geometry` and never fails the verdict; printed and purchased pairs still fail. Replayed on a copy of `ot10-hexapod-2` at `sweep_step=15`: sweep **fail (12 floor-only rows) → pass, 12/12 joints, 12 advisory**. Scored attempts keep their verdicts — they were accepted with the sweep off, and the actor may not re-accept product geometry [rec: fresh-timber-5181].
- **Biped attempt** — `ot10-biped-1`, one frozen-prompt turn (34 min 30 s, exit 0), accepted revision `44b8497b`: static fit clean, **swept fit complete and passing (6/6)** — the first in the run — P2 0.068, P3 3, electronics carried. It first could not be reopened (`CADEXD_RESTORE_FAILED`, an engine fingerprint defect, see `forest-wind-0342`) and was published unscored [rec: wise-walrus-6002]. After ADR-421 the replay rendered through the product and scored blind **15/21 median** (calls 15, 15, 16; T4 = 1 is the weakest trait, above hex3's lowest), P1 0.002 — **the biped meets every item of the A5 bar** [rec: pale-ledge-0992].
- **Still open:** a hexapod and a quadruped that pass — both need a rerun with the sweep on. The P2 `c_floor`/`floor` exclusion is an unrecorded frozen-proxy decision (it can only lower the sharp share, so the biped's P2 does not depend on it; the quadruped's 0.238 against 0.25 does). T4 (flat link plates, box servo covers) is the weakest trait on both the quadruped and the biped — the obvious lever. Watch: `cadex render` re-accepts through `rebuild`, so scoring moves `accepted_digest` with the revision unchanged [rec: fresh-timber-5181] [rec: pale-ledge-0992].

## Negative knowledge

- [scope: ot10-hexapod-1, one design-only turn, before ADR-418 | confidence: high | evidence: soft-spark-6990, strong-summit-4135] Under a host-dependent CPU cap, the agent meets the budget by deleting the design language's refinements (caps, fillets) and skipping the swept fit. The score then drops on exactly the traits A5 is judged on. A refusal about budget costs quality, not just time.
- [scope: ot10-hexapod-2 and ot10-quadruped-2, before ADR-419 | confidence: high | evidence: quiet-basin-1176, western-comet-0121] When the swept fit's 180 s budget cannot cover a 12-joint robot, the agent turns the sweep off to get accepted — so judged quality can meet the bar while the fit criterion still fails.

## Provenance

- damp-dusk-8045 — ot10 operator-declared charter gap
- soft-spark-6990 — A5 attempt 1: hexapod 13/21 blind (bar 14), P2 0.655 and swept fit fail; the CPU cap is the cause
- strong-summit-4135 — ADR-418: the cap was mostly thread overhead; 15 of 19 refusals now accept, 4 remain on real work
- late-glacier-7593 — hexapod attempt 2 launched on ot10-hexapod-2 at 6dd4ce81; ot10-quadruped-1 a harness stop
- quiet-basin-1176 — hexapod attempt 2: 14/21 meets the bar, P1–P3 pass, swept fit off on budget → misses A5
- western-comet-0121 — ADR-419: 12/12 joints swept in 112 s; quadruped 16/21, swept fit off → misses A5
- fresh-timber-5181 — ADR-420: world-geometry swept findings advisory; hexapod-2 replay sweep fail → pass, 12/12
- wise-walrus-6002 — biped attempt: first complete passing swept fit, unscored because the restore fingerprint refused a reopen
- pale-ledge-0992 — ADR-421 replay: biped 15/21, P1 0.002, meets every A5 bar item
