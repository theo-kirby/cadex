---
node_id: 4e1d3098-0a5a-56ed-a9de-fd45d24fbc4e
slug: long-glacier-5252
title: 'ot9 B4: final Robin design measured unchanged against the ot8 baseline; contact compression reported apart'
created_at: '2026-09-22T19:49:00+00:00'
parents:
- candid-wood-6113
summary: ''
---
## What

B4 of ot9, measured on the final accepted Robin design and compared with the frozen ot8 baseline.
- **Measured:** static fit, complete swept fit of both wheel joints, the fixed-joint attachments and the component inventory with catalog provenance, on `ot9-robin`'s accepted revision `ae889a9b…` (digest `078ebe87…`).
- **Compared:** each measurement against ot8-robin's `evidence/g4-resolve/before/` files; also the script, the parameters, the MJCF bytes, the mass and the actuator limits.
- **Compression:** standing wheel contact compression, reported apart from intersections by a new pinned reader `docs/probes/ot9/runner/contact_compression.py`.
- **Where it is:** receipt `docs/probes/ot9/retained/r5-robin-fit.json`, regression `cli/tests/test_ot9_contact_compression.py`, and a README section. Repo commit `0c021f24`; project commit `a96b3b5` (evidence/b4-final).
- No product turn, and no design, task, reward or engine change.

## Why

The critic named this unit: B4 on the final accepted revision (`ae889a9b`, seed 9). It asked for static fit, complete swept fit for both wheel joints, and the inventory with catalog provenance, each compared with ot8 and measured rather than asserted, with a compact receipt, a regression, and compression reported separately. The target is the charter root `open-cabin-5892`, through B4 (`strong-arrow-1143`).

The critic's pre-unit fix was to commit or discard iteration 6's residue. **I found it already resolved and did not act on it by hand.**
- The four df58d4ff attempts are no longer on disk: the rebuild retention removed them during the r4 seed runs.
- `script.json`'s `latest_candidate` had been committed by those seed commits (last `997ac9e`) and now names the accepted attempt with status `accepted`.
- `git status` in the project was clean apart from ignored files.
- `script_artifacts/` still holds two attempts of superseded revision `842bd631…` (rollout_seed=8). This is a git-ignored rebuild cache, and I left it, as the reversible choice.

All of this is written into the receipt's `project_store` block.

## Method

- **Fit and inventory:**
  - Ran `pixi run python docs/probes/ot7/runner/run.py --child-measure $PROJECTS/ot9-robin $PROJECTS/ot9-robin/evidence/b4-final`. This is the same call that produced ot8's `before/` files. It reads the engine's published `inspect scope=clearance` and `scope=inventory` for the accepted revision.
  - Compared each file as JSON with every `revision` and `elapsed_seconds` key removed.
  - Confirmed that the baseline `fit.json` and `inventory.json` hashes equal those pinned in the g4 receipt.
- **Script and model:** diffed the script, compared `param_values`, hashed both MJCFs from their accepted attempts, and loaded each in MuJoCo to read mass and forcerange.
- **Catalog provenance:** cited per catalog row from `CadexCatalog`: the Pololu URLs, the Raspberry Pi drawing, ISO 4762 for the screws, and the vendor tables for the heat-set inserts.
- **Compression:**
  - The MJCF's wheel collision geoms are 32.5 mm spheres on the axle, and the floor is the world plane at z = 0.
  - For each solver frame of the ten r4 evaluation traces, the reader places each sphere's centre from its body's world pose and computes `radius − (centre_z − floor_z)`. It reports the peak, and the settled spread for t ≥ 1 s.
  - It also reads MuJoCo's `contact.dist` at the solved keyframe.
  - An independent numpy pass gave the same numbers.
- **Regression:** three tests.
  - A one-sphere fixture model: floor height, sphere and zero keyframe gap.
  - Stated compressions, including a quarter turn about X, so the rotation of the offset is checked.
  - The receipt test, which holds B4's bar on both sides:
    - static fit is 0 failing of 378 with 0 intersections;
    - swept fit is complete for exactly both wheel axles at 0 mm³;
    - the inventory adds up, has no derived sources, and every catalog row has sources;
    - the final design equals the baseline, the MJCF and task equal the contract pins and r4's last seed, and the only parameter changes are `policy_on` and `rollout_seed`;
    - each seed's settled compression is within 0.01 mm of ot8's 0.576 mm.
- **Tests:** `pixi run python -m pytest cli/tests` gave 934 passed and 1 skipped. The engine suite was not run because nothing under `src/` changed.

## Result

**B4's measurements pass on the final accepted design, and the design is measured unchanged from the ot8 baseline.**
- **Static fit:** pass, 0 failing of 378 pairs (378 clear, 0 intersection, 0 below clearance, 0 unknown).
- **Swept fit:** pass, coverage complete. `joint_wheel_l_axle` and `joint_wheel_r_axle` are each swept over ±1800° in 100° steps, 37 samples, with 75 moving pairs, a minimum distance of 0.050 mm and 0 mm³ of common volume. No joint was skipped.
- **Attachments:** all 25 fixed-joint pairs touch, with 0 reported.
- **Inventory:** 28 components, 23 catalogued. `gearmotor/pololu-2367` ×2, `board/pi-zero-2-w` ×1, `bolt/m2x4-socket` ×8, `bolt/m2x6.5-socket` ×2 and `heat_insert/m2-standard` ×10, each with its source cited. `derived_catalog_sources` is empty. The only uncatalogued sources are the printed parts `chassis`, `clamp_l`, `clamp_r`, `wheel_l` and `wheel_r`.
- **Comparison:**
  - `clearance.json`, `fit.json` and `inventory.json` all equal ot8's `before/` once revision and timing are removed.
  - The script differs only in the policy literal pair: `robin.cxpolicy`/`0…0` became `r3-ppo-1.cxpolicy`/`ef71f370…`.
  - The parameters differ only in `policy_on` (0 → 1) and `rollout_seed` (0 → 9).
  - The MJCF is byte-identical (`933b1ac6`), so mass (0.187926 kg) and actuator limits (±0.0921825 N·m) are identical.
  - No mechanical, task or reward change was made in ot9, so there is no product-agent change to trace.
- **Contact compression, not an intersection:**
  - The wheel spheres touch the floor at exactly 0.000 mm in the solved keyframe.
  - Under the policy, the settled compression (t ≥ 1 s) is 0.5775–0.5820 mm on all ten seeds, with a median of 0.5798 mm. ot8's zero-torque hold measured 0.5763 mm, and ot8's load sweep showed it follows the load.
  - Peaks of 1.83–2.30 mm occur at 0.04–0.06 s only, when the robot lands from the task's 3–5 mm reset height.
  - ot8's 0.60 mm peak came from a hold with no drop, so the two peaks are not like for like.

Concerns and assumptions for the next iteration:
1. B4's "every change comes from a product-agent turn with a before/after measurement" holds trivially, because there were no changes. The report should state that plainly rather than as an achievement.
2. The swept fit's 0.050 mm minimum distance is below the 0.1 mm clearance threshold, yet it counts as passing. This is the hub-bore running clearance declared as fit intent (ADR-347), identical in the baseline, and not a new finding.
3. The project store's accepted revision is the seed-9 revision. B5's final reopen should rebuild `ae889a9b…` and expect digest `078ebe87…`.
4. **Next, per the critic:** reconcile (the tail is now 2 records), then B5. B5 means both full suites, a final fresh reopen and `docs/probes/ot9/REPORT.md` listing r3-ppo-1, the ten seeds, the ~0.84 m drift, the interrupted iteration 6, and this compression.

No new dependency. No trace, policy binary or machine path is committed.

Dispatch closed: 1 unit — B4 measured on ot9-robin's accepted ae889a9b: static fit 0/378 failing, swept fit complete on both wheel axles, 28-component inventory with cited catalog provenance, all equal to the frozen ot8 baseline (MJCF byte-identical); standing contact compression 0.578–0.582 mm reported apart from intersections; receipt r5-robin-fit.json with a regression.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot9
- commit: 0c021f24b9ffaaf06b7461588e883faafcda67d8

## State Impact

- target: strong-arrow-1143 — B4 measured on the final accepted ot9-robin revision ae889a9b (digest 078ebe87): static fit 0 failing of 378, swept fit complete and passing on both wheel axles (±1800° at 100°, 0 mm³), 25 welds touching, 28-component inventory with 23 catalogued rows and cited sources, derived_catalog_sources empty; all measurements equal the ot8 baseline once revision/timing are removed, MJCF byte-identical, script differs only in the policy literals; no ot9 design/task/reward change to trace; standing wheel contact compression 0.578-0.582 mm (MuJoCo contact spring, keyframe gap 0.000 mm) reported apart from intersections (commit 0c021f24, docs/probes/ot9/retained/r5-robin-fit.json)
