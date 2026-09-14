---
node_id: 0a055fbd-b09e-54cf-b55c-8c11ecbb6d99
slug: sleepy-rain-9945
title: 'Finch: a buildable MG90S biped in a fresh project — one joint module on catalog horns, MR128 bearings and M2 screws, per-solid inventory, measured fit check, served on the operator URL (ADR-334, D5; D4''s real-biped evidence); the free-base engine change is D6''s prerequisite'
created_at: '2026-09-13T23:46:35+00:00'
parents:
- windy-rock-4850
summary: ''
---
## What

D5's design unit: **Finch**, a buildable MG90S biped in the fresh project `~/cadex-projects/ot6-finch` (accepted revision `f0450d9bdf1a…`, script sha256 `fe4e4231773e1c15…`, 17 319 bytes, entered with `cadex script --set` — no model turn, no reuse of Lark's script). Two 2-DoF legs on four catalog MG90S, every joint the same module dimensioned from the catalog's datasheet numbers: the servo in a 0.3 mm window through the parent's outboard cheek with its tabs seated and two M2×6 screws in 1.6 mm tap drills; the measured micro single-arm horn in a 2.5 mm form-fit slot on the child block (0.2 mm per side, arm forward) clamped to the spline by an M2×16 centre screw from the inboard end; the child's printed 7.9 mm stub in an MR128 bearing pressed into the parent's inboard cheek (0.05 mm radial, 1.0 mm block-to-cheek). Five printed parts (pelvis with top plate, open bay and two hip clevises; two thighs; two shins with integral soles), 24 catalog parts as separate components fixed to their hosts, 29 solids, 243.5 g (177.5 printed, 65.9 purchased). Box proxies per printed part and per servo case with their relation to the solid recorded; horns, bearings and screws mass only; 20 geoms, no plane. `docs/probes/ot6/finch/fit_check.py` generates the project's `docs/INVENTORY.md` and `docs/FIT.md` from published measurements — the engine's pairwise BREP clearance at the solved pose and `cadex section` contour gaps through each cheek — against the declared clearances and analytic thread volumes: **85 checks, all hold** (window 0.300 mm in all four sections, stub 0.05, block gap 1.0, centre-screw engagement 7.854 mm³ ×4, tab-screw 4.0715 mm³ ×8, no other intersection, no unmeasured pair, no initial proxy contact). The persistent operator dashboard now serves Finch; `operator_probe.py` recorded the accepted view (`showing: tessellated solids`, 61 665 pixels) and the labelled toggle (`… with collision proxies (20 outlines …)`, 62 492 pixels) plus close-ups in which the servo cases, screw heads and horn arms are recognisable. ADR-334; `docs/probes/ot6/finch/README.md` is the written assessment.

## Why

The critic named the unit: "Advance D5 next: build the fresh MG90S biped with catalog horns, bearings and fasteners, purposeful printable mounts, a per-solid inventory and measured pocket/horn fit checks. Keep world geometry out of its script. Serve that accepted project on the persistent operator URL and capture recognisable hardware with proxies off and on, supplying D4's remaining real-biped evidence." D5 (`cool-hill-9617`) is the highest-ranked open criterion once D4's toggle half landed, and D6–D8 all wait on it. Two deviations from the letter of the message: (1) the servo "pocket" is a through-window in a cheek plate rather than a cavity, because a cavity block needed either a back cap or a fastener on the same axis as the bearing bolt; the clearance is declared and measured either way. (2) The world could not be kept out of the *solver*: `assembly.solve` and the dynamics export both refuse an assembly with no grounded component, so the pelvis carries `grounded=True` as a flag rather than a floor being added; the free-base engine change is recorded as D6's prerequisite, not done here (one unit).

## Method

1. Read the catalog (`cadex_library_api.py`, `CadexCatalog.py`) and the swing-rig precedent `ot4-swing2` for how a placed MG90S, its `.spec`, `lib.bolt`, `lib.bearing` and `servo.actuator` are used; derived the module's Y layout from `mount_hole_z_mm`, `tab_thickness_mm`, `spline_height_mm` and the horn hub.
2. Authored `finch.py` with every link's frame on its joint axis and purchased parts in their host's frame; three runs to accept: the solver's grounded-component refusal, then a 2.4 mm seat-datum error (the catalog's `mount_hole_z_mm` is the tab plate's far face) that the engine's clearance table caught as 248 mm³ of servo inside each cheek.
3. `cadex inventory`, `cadex clearance`, four `cadex section --plane XZ` cuts at the cheek mid-planes (offset by 0.137 mm off any tessellation vertex); wrote `fit_check.py` (85 rules) and ran it: exit 0.
4. Restarted the persistent operator unit under its documented `systemd-run` command on `ot6-finch` (no trainer active); ran `operator_probe.py` against the operator URL; looked at every frame.
5. Committed the receipts (fit.json 13 KB, operator.json 10 KB, six PNGs 24–157 KB) with README and ADR-334; `cli/tests/test_review_design.py` **62 passed** (the cap and private-address checks cover the new directory). No product code changed, so no other suite was owed; the project's own `ARCHITECTURE.md`/`DECISIONS.md` were brought true.

## Result

What is true now: a biped exists that is built from catalog hardware and modelled mounts, with an inventory naming every solid's source and mass, a fit check that measures rather than asserts, no floor or wall in its script, its proxies declared per part, and the operator URL serving it with the toggle showing proxies that visibly stand off the solids — which is the real-biped evidence D4 was owed. D5's evidence list is complete pending the owner's tick.

Concerns and assumptions the next iteration must know:
- **The engine requires a grounded component** (`no_grounded_component` in both `cadex_assembly_worker.py` and `CadexDynamics.py`), so Finch's pelvis is grounded for the solver and the accepted MJCF has a static base. **D6 cannot start until an engine unit lets an assembly with no grounded component solve as a free base and supplies the ground from the environment** (the exporter's island path already gives an unreached component a free joint; the reset-variation floor checks must find an environment plane). That unit changes the xscript surface and needs the engine suite and the packaged gate; the script edit afterwards (drop `grounded=True`, add the task) is a new accepted revision.
- The fit check is at the solved pose only; knee flexion past ~60° brings the sole toward the thigh cheeks, and the horn hub and spline are inside the slot by design.
- The persistent dashboard no longer serves `ot5-lark-copy85`.
- No new dependency; the probes use PIL and the CLI's headless browser as the look probe did.
- The unreconciled tail is now three records (`brave-wave-1488`, `windy-rock-4850`, this one): reconcile is due.

Dispatch closed: 1 unit — Finch, a buildable MG90S biped with inventory, measured fit check and operator evidence (ADR-334, D5; D4's real-biped evidence); the free-base engine change is D6's prerequisite.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot6
- commit: ed5b158a7b030cdd5ad8c990533255a655d61e06

## State Impact

- target: cool-hill-9617 — D5's design unit landed (ADR-334, ed5b158a): Finch in the fresh project ot6-finch (revision f0450d9bdf1a…) is two 2-DoF legs on four catalog MG90S, every joint one module dimensioned from the datasheet (servo in a 0.3 mm window through the parent's outboard cheek with two M2×6 tab screws, the measured micro single-arm horn in a 2.5 mm form-fit slot on the child block clamped by an M2×16 centre screw, a printed 7.9 mm stub in an MR128 bearing pressed into the inboard cheek), five printed parts and 24 catalog parts as separate fixed components, 243.5 g; docs/INVENTORY.md names every solid's source and mass, docs/FIT.md holds 85 measured checks (engine BREP clearance at the solved pose plus section contour gaps) all passing, no floor or wall in the script, box proxies declared per part with their relation recorded; the operator URL serves it with servos and horn arms recognisable; still owed: nothing on D5's list except the owner's tick, and the pelvis is grounded for the solver because the engine refuses an ungrounded assembly
- target: chilly-banner-4507 — D4's real-biped evidence is in (ed5b158a): on the operator URL serving ot6-finch the labelled toggle moves the model pixel count from 61 665 to 62 492 with 20 outlines from the accepted attempt's finch_model export, the pelvis proxy spanning the open bay and the cheek proxies spanning their windows so the outlines visibly stand off the solids (docs/probes/ot6/finch/operator-solids.png, operator-proxies.png); D4's evidence list is complete pending the owner's tick
- target: dusty-otter-7562 — D6 is blocked on an engine unit: assembly.solve and the dynamics export both refuse an assembly with no grounded component (no_grounded_component), and the charter forbids a floor in the design, so Finch's pelvis is grounded and its accepted MJCF has a static base; the prerequisite is a free-base solve (first component held for the solver, free joint in the export) with the ground supplied by the environment, after which the script drops grounded=True, declares the task, and trains
- target: chilly-union-8972 — the persistent operator unit (port 8765) serves ot6-finch instead of ot5-lark-copy85, restarted under its documented systemd-run command with no trainer active; docs/probes/ot6/finch/ adds fit_check.py (inventory and fit generator) and operator_probe.py; cli/tests/test_review_design.py 62 passed with the new evidence under the caps
