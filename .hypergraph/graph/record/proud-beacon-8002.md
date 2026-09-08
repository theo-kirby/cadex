---
node_id: ba844e5c-24bb-562d-8f4e-213204b16675
slug: proud-beacon-8002
title: Two-servo leg completes the bounded walk with catalog placement and review findings
created_at: '2026-09-08T06:43:19+00:00'
parents:
- fresh-road-9595
summary: ''
---
## What

Executed the single eligible two-MG90S leg rehearsal through the unchanged documented `cadex walk`. Design, assembly/MJCF/task export, local CPU training, policy store/declaration/verification, rollout and review all completed. Inspected four named views and the XZ section, manually tallied catalog usage against placed inventory, and checked clearance against render/section bounds. This is fresh pipeline and review evidence, not a claim of a printable leg or learned crouching.

## Why

Iteration 183 executes the short bet retained in [rec: fresh-road-9595], following the overseer's redispatch instruction. Advances charter criteria **The walk exists and is tested headlessly** (`crisp-reef-5607`), **The walk holds on a second mechanism** (`swift-dusk-2951`) and **The agent can see its work without a screen** (`damp-moon-9297`), missions 2 and 6. The one permitted local UTC observation was **2026-09-08 06:30:04 UTC**, after the 06:30:00 boundary. One attempt was therefore eligible; no provider probe, wait for quota, fallback or switch was used. Unlike silent-mist-5233, the attempt was not refused by quota.

Assumption: run the exact recorded prompt with no operator correction to the generated mechanism. Let the product agent choose and record its own modeling assumptions. Do not implement the deferred catalog diagnostic: fresh placement guidance compliance is the question this experiment resolves. No state, plan or charter file is edited.

## Method

Read actor/record skills, STATE, graph contract, current bet and prior rehearsal/qualification/review evidence, VISION, CLI walk contract and training SETUP. Clean repository baseline `8b8d4155b0e3582a9feb04a693158a19d57c6944`. Use the current checkout CLI and a fresh external temporary project, basename `cadex-nt3-i183-leg`. Explicit engine: `build/engine/cadex-engine-0.0.0-macos-arm64`, resolving to that payload's `bin/freecadcmd` and `Mod/cadex`, not the stale installed application. Before dispatch, payload `CadexScriptedRuntime.py` SHA256 matched lawful-dune-3795: `602164e85c399ad203517eb269ec81bca549dc07b72d303659c1cffffe1dc6df`. The walk's child argv records the explicit payload on all four legs.

Command shape (placeholders avoid committing machine paths):

```sh
JAX_PLATFORMS=cpu <training-venv>/bin/python <existing-monitor> ./cadex walk \
  --engine <qualified-payload> --project <fresh-project> \
  --out <fresh-project>/runs/baseline --prompt '<exact prompt below>' \
  --trainer-python <repo>/.venv/bin/python \
  --iterations 1 --envs 4 --seed 0 --timeout 600 --json
```

Inherited PYTHONPATH, CADEX_ENGINE_ROOT and CADEX_MODULE_DIR were unset for dispatch. The existing monitor samples process-tree RSS every 0.2 s, with 2.9 GiB / 850 s cutoffs and TERM then five-second KILL fallback. Training uses the existing training venv per SETUP, never pixi dependencies or remote dispatch. Model: `claude-fable-5`.

Prompt: A single robot leg with hip and knee driven by two TowerPro MG90S catalog servos, a thigh, a shin, a foot pad and M3 hardware. Fix the hip support to the world. Give the hip and knee revolute joints position servo actuators at MG90S torque and speed limits, with a joint-angle sensor per axis. Declare a toy training task holding the named crouch angle pair hip 0.4 rad and knee -0.8 rad, with a small effort cost and joint-range termination. Declare the policy so the task can be trained.

Local ignored evidence: `build/lifecycle/nt3-i183-leg.json`, `build/lifecycle/nt3-i183-leg.err`, `build/lifecycle/nt3-i183-bounds.txt`; full project under the system temporary directory with the basename above. Images were inspected by extracting the lossless embedded PNGs from the four saved SVGs; the saved section SVG was rasterized with `sips` and inspected. No GUI was launched. Reused the morning-summit-7848 bound-agreement checker: 45 markdown clearance rows, 10 render bounds and 10 section bounds. No STL comparison is claimed: the checker found no world-placed STL in its export location, and the walk's source-solid STL exports are local-frame geometry.

## Result

**Execution clean, all reached, no operator guess/person:** design exit 0 in **539.06 s**; train (including rebuild/export/store) exit 0 in **19.13 s**; declare exit 0 in **1.82 s**; verify/rollout exit 0 in **2.09 s**; review available and completed. Whole monitor exit 0 in **565.7232 s**, sampled peak **1,270,939,648 bytes**, cutoff null. The design agent read the API in 34 inspect calls after reporting that the full dump exceeded one read. It accepted a first script, inspected catalog mass data, then replaced its fallback density with `effective_density_kg_m3`. No engine error or source repair was required from this actor.

Final accepted revision `671a1c289c95afef3da2f95a5419f7bde1effd57948a790de86ad491ae10b11c`, digest `0ee2ba83aeb579620a90e9edd5310e46966a17ab2311c2477ff200b407d33131`. Policy SHA256 `88a1063f1201b49c1cc496af599dedd7426f882bed6e5af3f5437dde99b8eba6`; task SHA256 `79dd73e2944234cfc2eaf8848c0b4d99e1010db10ff53327e7725bfbb4575179`. CPU trainer: 4,738 parameters, 1 iteration x 4 environments, seed 0; reported training wall **2.229455 s**, final batch reward/step **-34.1994285583**, witness error **3.757570462e-09** against **1e-4**. No training cutoff fired.

Verified rollout: **200 steps** (4 s at 50 Hz), no range termination (`terminated_step=null`, `truncated=true` at horizon), total reward **-5144.79219176905**, rollout reward/step **-25.72396095884525**. Reward terms: crouch pose **-5144.79196484324**, effort **-0.0002269258054864**. The project's committed PROGRESS rows carry training and rollout numbers and review counts. Prior hinged-arm and linear-carriage PROGRESS files retain their comparison at the same 1 x 4 / training seed 0 settings: rollout totals -27.1093842209 and -24159.1953563 over 50 steps, trainer means -0.380198150873 and -82.3199081421. These are comparable metric definitions, not a ranking: the new leg has a different pose objective, reward units/weights and 4 s horizon. No claim of trained-control quality follows from one PPO iteration.

**Catalog guidance observed working on this run:** 10 placed components, **6 catalogued instances**: `servo/mg90s` x2, `bolt/m3x10-socket` x2, `nut/m3-nyloc` x2. Manual script tally agrees: one servo body published and placed twice, one bolt body twice, one nut body twice; four independently modeled printed solids. The only other lib call is the scalar M3 clearance diameter. No catalog body feeds a printed-solid boolean, and there are no discarded catalog bodies or catalog-body cutters in this script. This conclusion comes from reading the script, not interpreting a zero/missing tally. No cold historical identity or general occurrence-tracing guarantee is established.

**Review observed:** four front/top/right/iso views, 7,776 triangles, 10 objects. Front shows straight hanging links, right and iso show the two servo bodies on opposite sides of the link plates, top shows their lateral offsets and the foot hardware. World XZ at Y=3.125 mm is available/ok: thigh, knee servo and foot intersect the plane, while seven other objects correctly report empty at this offset. The visible section shows the long thigh contour with the knee-shaft circle and a separate foot rectangle. These are initial-solved-pose views and tessellation cuts, not an animation or swept clearance.

Clearance: **45 pairs checked, 11 offending, 0 unknown** at 0.1 mm / 1e-6 mm³. Of the offending pairs, seven are zero-volume contacts and four have positive volume: shin / each foot bolt **5.8373525743 mm³**, each bolt / matching nyloc nut **9.2781252741 mm³**. The bolt/nut intersections may reflect simplified mating envelopes; they are not silently waived. The shin/bolt intersections are a concrete review finding. Servo / driven-link distances are **5 mm** for both hip-servo/thigh and knee-servo/shin; views likewise show separation. The ideal revolute joints therefore do not prove a physically attached drive interface. The agent's torque/speed model uses torque-limited position servos and damping = stall torque / no-load speed, an approximation, not a verified hard velocity cap under arbitrary loads.

Bound-agreement checker: **PASS, 90 comparisons, 0 failures**, covering both render and section for all 45 pairs; **39 pairs involve catalog instances**. This is a non-null fresh check of the published catalog-placement path, unlike the zero-catalog run. It establishes necessary AABB consistency, not exact independent validation of every OCCT volume. No STL pass or unseen view is claimed.

The external project has **five automatic commits**, HEAD `2832886`, and clean status. It carries source/history, ARCHITECTURE, five project ADRs, PROGRESS, inventory, clearance, review JSON and the four views/section. The canonical stored policy asset is committed by the existing product lifecycle; trainer checkpoints and rollout trace are ignored and not tracked. No checkpoint, rollout, policy or machine path is added to the Cadex repository. The agent did not add dedicated sensor/gear domain notes; only the generated inventory/clearance domain docs exist. This is a limitation of this fresh authoring run, not grounds to erase the previously working domain-doc convention.

No repository product edit, build, removal or direction change: engine/CLI/shell suites and packaged gates were not repeated, as the short plan explicitly reuses lawful-dune-3795 qualification. The actual walk is this experiment's runtime verification. No landed implementation checkbox or repository ADR was warranted. Graph export/check and diff inspection are the record-only gate; results are reported with the commit. The tail has two unreconciled records including this one; reconciliation belongs to the maintainer.

Next: the selected fresh rehearsal is now evidenced; no quota retry or repeated worker qualification is needed. Existing working headless-walk, second-mechanism and eyes claims gain fresh evidence; no pipeline leg remains missing for this rehearsal, and the human-owned checkboxes are unchanged. The generated leg is not yet mechanically qualified. Replan from the observed review into one bounded review-driven iterate unit, starting with the shin/foot-bolt interference and checking the physical servo/link attachment, while keeping catalog components separate. Record agent assumptions and sensor notes in the project when that unit is authorized by the next bet. Do not resume cold catalog diagnostics or promote Later criteria merely because execution passed.

Dispatch closed: 1 unit — eligible two-servo walk completes headlessly with catalog placement and review evidence; physical interference and attachment remain for iteration.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/nt3
- commit: 8b8d4155b0e3582a9feb04a693158a19d57c6944

## State Impact

- target: crisp-reef-5607 — Eligible exact two-servo prompt completes design, train, declare, verify/rollout and review on qualified payload in 565.7 seconds; no operator correction or quota refusal.
- target: swift-dusk-2951 — Fresh two-servo mechanism passes unchanged walk at 1 iteration x 4 CPU environments; PROGRESS records reward and review counts, without ranking different objectives.
- target: damp-moon-9297 — Inspect four views and section, confirm six separately placed catalog instances by script tally, and pass 90 bound comparisons; review names shin/bolt interference and servo/link attachment limits.
