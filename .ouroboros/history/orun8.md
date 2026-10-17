---
run: orun8
machine: sb1x
started: 2026-10-16T18:20:40
ended: 2026-10-17T12:40:12+00:00
hours: 13.9
state: killed
iterations: 33
commits: 24
criteria_ticked: 0
criteria_closed: 0
criteria_total: 14
merged: 8699109c93da3cf69b7f2b8bc91b2e93ec07b89a
branch: ouroboros/orun8
memory: governor
actor: claude:claude-opus-5-5
---

# Run orun8

33 iterations in 13.9h on `sb1x`, killed (-). Branch `ouroboros/orun8`, merged as `8699109c`.

## The numbers

| | |
|---|---|
| iterations | 33 (changed 23, recorded 24) |
| commits | 24 — 38 files changed, 4327 insertions(+), 429 deletions(-) |
| criteria | **this run ticked 0**; 0 of 14 checked at the tip |
| reverts | 0 |
| verdicts | continue 33 |
| loop detector | no firing |
| roles | actor claude:claude-opus-5-5, critic claude:claude-opus-5-5 |
| usage | claude seven_day 18% -> 26% (+8 this run); claude five_hour 2% -> 32% (+30 this run) |

## What landed

- probe: G3's stock-vs-MJX comparison on the newest cat with c1-t7's frozen actor
- gait: a reference for two feet, walk and run (ADR-754)
- training: a cold-start recipe for legged policies, drafted from orun6-orun8's runs (B1)
- trainer: a warm start keeps the weight of the source's normaliser (ADR-753)
- gait: a reference's clock may follow the commanded speed (ADR-752)
- goals: a waypoint, a place on the ground the base is sent to (ADR-751)
- evaluation: scripted goal sequences reach the engine (ADR-750); platforms_crossed, terrain predicates read every kind (ADR-749)
- dynamics: a height scan may be the actor's, role="policy" (ADR-748)
- training: a course of moguls alone trains; G3 probe of the new ground (ADR-747)
- film: a course is drawn as the dashboard's one ground (ADR-746)
- terrain: platforms, rock patches and a run-out; the drawn ground is the physics ground (ADR-745)
- terrain: a box course's bump is a dome; a re-placed slot reads its own rotation (ADR-744)
- dashboard: a course is drawn as one ground (ADR-743)
- dashboard: the mat follows the camera, so the ground never ends (ADR-742)

<!-- notes: everything below this line is yours; a rewrite keeps it -->

## What this taught

Owner-stopped at iteration 34 (13.9 h of 24), during c1-t8's judging; the operator recorded that verdict (`silent-trail-8306`) and folded it.

**Where each criterion ended.**
- **G1, G2, G3 (ground): working.** One drawn ground built from the physics shapes (ADR-743, 745, 746), a mat that follows the camera (ADR-742), domes, moguls, platforms, rock and a flat run-out (ADR-744, 745). MJX and stock agree on tip rates on every kind on the newest cat with a ground-reading actor (`solemn-mesa-5694`). Rock and mixed courses cost ~5.5× a flat iteration (ADR-747).
- **C1, C2 (cat): open, nothing passes on all seeds.** Ten runs (c1-s1 to c1-t8). Best per bar:
  - run speed: c1-t6, 2.3–2.5 m/s at a 3 m/s command (RMS 503–672 mm/s against 300);
  - stand: c1-t5, 2/10;
  - shove: 10/10 (c1-t6, c1-t8);
  - turn2: c1-t7, 8/10;
  - reverse and points: 0/10 throughout.
  - c1-t8's per-drive over-rated price put every spec within rated but cost speed (806 mm/s RMS).
  - A c1-t9 (`hinge_w=3`) is staged, uncommitted, in `~/cadex-projects/orun8-cat` and was never launched.
- **C3, C4, C5:** not started.
- **B1:** a recipe draft (`training/RECIPE.md`) and a two-foot gait reference (ADR-754), on `~/cadex-projects/orun8-biped`.
- **B2–B4:** not started.

**What this taught.**
1. **Reward tuning one term per 150-iteration run is slow.** It took eight runs to trade torque against speed, and every fix moved the failure to another bar (speed, then rated, then stand drift). Next time, screen several weightings in one batch, e.g. a sweep of short runs, instead of one guess per iteration.
2. **Cold restarts threw away progress.** c1-t5 started from scratch to merge C1 and C2, and it gave up the ~450 iterations behind c1-t4b. ADR-753 (a warm start keeps the normaliser's count) made warm starts safe; prefer them.
3. **The ground-first order held.** G closed in about 10 iterations. The charter's priority order works when the first criteria are engineering, not training.
4. **The base models got under 10% of the run.** The C criteria have no natural end inside a run, so the strict priority order starved B. A later rung needs a trigger (for example, after N cat runs without a new pass) or its own share of the GPU.
5. **An idle GPU while judging.** Judging runs on the CPU for ~60 s, but the 20-minute rebuilds of a 100-part model blocked the launch of the next run. Launch training first and rebuild for the next revision while it trains.

**Next run (orun9):** C1/C2 from c1-t6/c1-t8 by warm start, with weight screens; then C3/C4 on the G courses; B2–B4 with a guaranteed share.
