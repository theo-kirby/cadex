---
node_id: a257082c-58b6-554c-8161-d788733b3a03
slug: rough-vale-0587
title: A7. The designs reach the reference level, not just the bar
created_at: '2026-09-29T06:16:57+00:00'
parents:
- nimble-pine-0740
summary: ''
---
Status: open

## Current

Open charter criterion for run ot10, **added by the owner mid-run: A7 (stretch). The designs reach the reference level, not just the bar.** For each of the three body plans, the latest pre-registered confirmation turn at its final revision scores **17 or more of 21** with **T4 (form) at 3**. It must also meet every other A5 bar item: the proxies, static and swept fit, and the electronics. Everything is judged under A1's frozen rubric, judge and procedure, unchanged. Every confirmation turn is pre-registered before it runs, and every attempt and score is published, misses included [rec: rapid-spark-0680].

The charter names the gap to close: a rounded box on legs, servo cases hanging outside the shell, and a form score that never reaches 3. It is to be closed with product changes (the design language, the overlay, the API, the engine); the actor never authors robot geometry. Missing A7 at the ceiling is an honest incomplete result [rec: rapid-spark-0680].

**Deferred by the owner (2026-09-29) [rec: snowy-quill-0006].** The later directive supersedes `rapid-spark-0680`'s priority: A7 no longer blocks done, ot10 ends after A8, and A7 goes into the closing report (C1) as open and carried forward with whatever was measured towards it. An A7 unit in progress may land with its tests and record, but no new A7 confirmation turn starts. (Maintainer judgement: this status note is derived from `snowy-quill-0006`'s exhaustion policy, which declared no impact on this node.)

**Servo-case half of the gap now has a product surface (ADR-443) [rec: brave-rain-8039].** `lib.servo` carries `.bay()` and the overlay teaches wrapping it in the limb (detail on `brave-stone-9609`, `chilly-union-8972`). A read-only 2 mm shroud-share diagnostic (printed share of a shroud outside 0.5 mm clearance) on the three 16/21 designs: `ot10-quadruped-2` hips **0.198**, knees 0.734; `ot10-quadruped-4` hips **0.390**, knees 0.763; `ot10-hexapod-5` hips 0.847, knees 0.714–0.719 — the quadrupeds' hip cases are the ones hanging outside. Every hand-cut pocket is tighter than 0.5 mm somewhere or lacks a lead exit (273–2,814 mm³ printed inside the default bay per servo). The shroud share is a diagnostic, not an A1 proxy (quadruped-2's hero `hardware_silhouette_share` is 0.004); nothing was re-scored and no confirmation turn has run [rec: brave-rain-8039].

Declared target: `gap-a7-stretch-added-owner-mid` [rec: rapid-spark-0680]. This node tracks the criterion as a gap. It becomes working only with causally parented, measured evidence that the criterion is met. The human owns the charter checkbox [rec: rapid-spark-0680]. Maintainer note: no A7-qualifying turn exists yet. The highest A5 totals so far are 16/21 (quadruped-2, quadruped-4, hexapod-5), and none has T4 at 3 (see `loyal-fountain-8709`) [rec: western-comet-0121] [rec: tidy-pebble-6206] [rec: patient-banner-4052].

## Negative knowledge

None yet.

## Provenance

- rapid-spark-0680 — operator directive adds A7 mid-run
- brave-rain-8039 — ADR-443 servo `.bay()` + overlay limb wrap; read-only shroud share on 16/21 designs (quadruped hips 0.198/0.390); no confirmation turn
- snowy-quill-0006 — owner directive: A7 deferred, does not block done; ot10 ends after A8
