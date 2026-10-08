---
node_id: 34e1328a-ff40-590f-8b1c-25a8ad1ad2be
slug: solemn-quartz-2619
title: 'orun5: REPORT §10.2 checkpoint count fixed; done claimed for critic review, reconcile deferred'
created_at: '2026-10-08T04:23:20+00:00'
parents:
- rustic-bloom-7305
summary: ''
---
## What

Fixed REPORT.md §10.2: a 60-iteration run with `--checkpoint-every 10` has no tenth checkpoint, so "the tenth checkpoint" is now "the fifth", matching `rustic-bloom-7305`. Moved the header's verified line to `593f9cb8`, and updated the Done claim's tail paragraph to name the nodes still unreconciled. Then, following the exhaustion policy, this record claims done for critic review. No owner box is ticked.

## Why

The critic asked for the §10.2 fix first; it is done as asked. The critic then named a reconcile pass as the unit. **I did not do that.** This iteration's dispatch rules forbid the hypergraph-reconcile skill, `hypergraph update` and state-node edits in a work iteration "no exceptions", and those rules outrank the critic's message. What I did instead: the fix, plus the done claim the critic asked to follow the reconcile, with each criterion's record and numbers below, so the reconcile pass only has to fold the tail. The reconcile is left to the next pass that may run it.

## Method

- `sed` on `docs/probes/orun5/REPORT.md` lines 3 and 452, and a scripted replace of the Done claim's tail paragraph. The checkpoint numbering was checked against `rustic-bloom-7305`'s body: checkpoints at 10–50, fifth equals second.
- Docs only, no code touched. `pixi run python -m pytest cli/tests -q -k "orun5 or report"` gave 118 passed, which covers the report pins. The full gates were not rerun because no code changed.

## Result

The report now matches its record. The done claim, criterion by criterion (REPORT.md table and §1–§7):

- **S1**, position tracker (ADR-588/589/590; `peaceful-heron-7678`, `long-isle-5502`, `smooth-stream-7287`): reading follows the true plate-frame position through a ±160° turn at a 20° tilt, worst error 0.24 mm against 0.5 mm resolution. Out of range reads zeros with flag 0, never clamped. The trainer's noise matches the engine's on 200 draws, with σ within 6 %.
- **M1**, turns/laps/distance predicates (ADR-587; `dusty-meadow-8719`, `dusty-canyon-3027`): a circling trace passes, a rocking trace on the same arc fails, and a trace that ends early fails rather than crashing. A trained rocking policy (circle-6) fails it on 8/8 seeds.
- **S2**, load sensor (ADR-591; `tiny-lake-4065`): the channel tracks applied effort and saturates at stall. A PWM servo's load sensor is refused.
- **L1**, closed linkage (ADR-593/594/595; `civic-sun-5811`, `spring-river-3041`, `young-aspen-5297`): a four-bar and a slider-crank each reach the analytic output angle. An over-constrained loop is refused. The fit sweep **refuses** a loop by name rather than solving it, which the charter allows.
- **R1**, body-frame goal (ADR-592; `long-cabin-6279`): the goal stays put in a drifting base's frame, and error is measured against it. Its first real use was P2.
- **P1**, ball-plate as built (`smooth-stream-7287`, `dusty-canyon-3027`, then circle-7…11 through `glad-valley-4220`): the free ball is read by the S1 panel, and centring **passes 8/8** with M1 distance and no point goal. The circle task is on the charter's *otherwise* branch. The predicate fails rocking and passes circling, and the best trained circle policy (circle-11, ADR-598 phase goal plus a state-gated catch) passes **7/8**. Seed 9102 is lost to the start kick, so this is **not a spec pass**, and circle iteration has stopped.
- **P2**, excavator floor (`hidden-sand-7542`, `misty-water-8806`): `reach-p2-cold` on frozen seeds 101–110 has median **11.5 mm, 7/10**, against reach-05's 23.6 mm, 2/10, so the floor moved. The spec still fails on seeds 102, 103 and 107. Servo sag is ruled out directly: load ≤0.19 of stall, tip shift 1.5 mm median and 4.3 mm max, and reach-05's commands already miss by 19.7 mm under rigid kinematics. **Attribution caveat:** the run changed goal frame, load channels and schedule (1400 uninterrupted iterations against 600+400+400) together, so the cause of the move is not separated. The new error is also measured in the track frame (drift ≤8.6 mm). The bucket four-bar was not built.
- **C1**, closing report: `docs/probes/orun5/REPORT.md` and `LESSONS.md`. All three carried defects are measured and closed (§10.1–§10.3; `rustic-bloom-7305` for the checkpoint stall, where ADR-576 holds).

The owner's boxes are not ticked.

Concern: the unreconciled tail is now `rustic-bloom-7305` plus this node. The next permitted pass should fold both into `late-pond-2851` and C1, advance the mark, regenerate the views, and make export and check exit 0, before the critic judges this claim. No new dependency.

Dispatch closed: 1 unit — REPORT §10.2 "tenth"→"fifth" fixed; done claimed for critic review; reconcile deferred (forbidden in a work iteration)

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/orun5
- commit: 593f9cb8fff6666823af07454bcb3f27a2d4b5a8

## State Impact

none: docs-only correction and a done claim; state folds at the next reconcile
