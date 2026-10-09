---
node_id: 80810a3a-67e5-5be4-8aea-10a9050973ed
slug: golden-flame-1650
title: 'Creature fix: anatomy, light QDDs, panels, creature style, retired hardware bar, tooling (ADR-608..627)'
created_at: '2026-10-09T14:31:00+00:00'
parents:
- light-wing-5639
summary: ''
---
## What

The creature fix: six changes from the blind-rated cbase baseline sweep (six design-only QDD creatures, mean 2.3/5 overall, 2.6 "every part designed"; no design jointed head, jaw, tail, arms or wings; only the jointed-neck herons reached 3). ADR-608 to ADR-627.

## Why

Owner verdict on the Deinonychus run: no articulated tail, arms, head or neck, and organic shells that were "cosmetic half-assed revolutions" on a biped. The owner asked for all six proposed fixes implemented end to end without a charter.

## Method

Five worktree agents in parallel plus the guidance on main, merged into main:
1. Articulation: `assembly.anatomy` and the `anatomy` block in every build reply, `inspect scope=anatomy`, a `look` measure; catalog motors on a joint's axis count as drives in design-only projects (ADR-613, ADR-614); a base rule in step 1 and "a met bar is a floor" in step 6 (ADR-627).
2. Catalog: `cubemars-ak60-6-v3` (380 g) and `cubemars-ak45-10-v3` (262 g); `QddPart.mounting()`; output-flange bolts turn with the flange in the sweep (ADR-608, ADR-609).
3. Shells: `lib.panel` grown station by station from what it covers, `lib.housing` around a drive, and `fit.shells` naming floating/solid/unmounted/covers-nothing shells (ADR-610..612).
4. Style: `CadexAgentStyle.creature.md` from the owner's north stars, and the agent chooses the style its brief names, from `cadex style --json`'s `about` (ADR-625, ADR-626).
5. Bars: `hardware_silhouette_share` reported with no bar (ADR-624).
6. Tooling: named failing calls and kernel crashes, full solver diagnostics bounded for the model, `math` and safe introspection in xscript (a frame-attribute escape closed), `describe_api section=library_parts`, prints on refusal (ADR-615..620); closed loops swept from their limited joints and planar revolute loops accepted per linkage, a geometry-keyed fit cache, `world=True` floors never failing fit (ADR-621..623).

## Result

- Engine suite on the final tree: 2778 passed, 61 skipped. CLI suite: 1258 passed, 1 skipped, 1 failed (the `describe_api` library page at 21,899 of 21,500 characters), fixed in 972d8198 by pointing catalog notes at `library_parts` (21,475); client and library tests then 176 passed.
- Real engine, per the agents: the heron's neck and legs read articulated via its QDDs with the head and toes flagged; lib.panel panels at 2.5-4.7 mm median gap against 31.3 mm for an egg by eye; leopard-b static fit 229.7 CPU-s cold to 0.84 warm with identical rows; heron-a's hip pushrod closes only to 40 degrees of a declared 50.
- The re-run (six `cfix-*` projects, same briefs, same isolation) is set up but waits on the owner: the auto-mode classifier refused launching the sessions with `--dangerously-skip-permissions`.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: main
- commit: 972d8198d6734179d8abcf6dab2dda9d4ae0ed22

## State Impact

- target: brave-stone-9609 — the catalog has a light QDD tier (AK60-6 V3, AK45-10 V3) and QddPart.mounting() (ADR-608, ADR-609)
- target: curious-quill-9036 — closed loops are swept from their limited joints and re-closed per sample; fit is cached by geometry (ADR-621, ADR-622)
- target: pale-arrow-4660 — a creature style exists and the agent chooses the style its brief names (ADR-625, ADR-626)
- target: NEW creature-design-quality — creature designs are articulated and their shells wrap the mechanism: measured by anatomy and shell blocks; open until the cfix re-run is rated blind against the 2.3/5 baseline
