---
node_id: c3d29332-cf73-5ef0-86db-e14fcaccfc56
slug: glad-chart-3979
title: The misplaced MJCF bodies were a connector frame FreeCAD swapped (ADR-393)
created_at: '2026-09-20T00:39:35+00:00'
parents:
- pale-dew-4616
summary: ''
---
## What

The 24 misplaced MJCF bodies iteration 167 measured on `ot7-plover-e` are
fixed, and the cause was **not** where that record put it (ADR-393, commit
`63236e54`).

**The reading that was wrong.** `pale-dew-4616` named
`CadexDynamics.py:3350` — a non-root body's frame derived as
`parent_local_matrix × inverse(child_local_matrix)` while only the root uses
the solved placement. That line is correct. A fixture built forwards, with
connector frames labelled by the components they belong to, recovers exactly
the parent-relative transform the solved assembly holds, for a weld and for a
hinge alike. What was wrong was the *labelling of its two inputs*.

**The cause.** `JointObject.setJointConnectors` calls
`ensureUnconnectedIsSecondRef` (upstream FreeCAD issue 29355), which swaps
`Reference1`/`Reference2` **together with** `Placement1`/`Placement2`,
`Offset1`/`Offset2` and `Detach1`/`Detach2` whenever the first reference's
part is the unconnected one and the second's is connected.
`cadex_assembly_worker._build_joint` read `Placement{i}` at the *script's*
own connector index while naming the component from the script's own
connector list, so after a swap each component was handed the other one's
connector frame. Correct arithmetic on mislabelled inputs put the body at
the exact inverse of its parent-relative transform.

The trigger is the ordinary weld. A script fixing a bought part to the
printed part carrying it writes `joint("fixed", connector(part, "origin"),
connector(host, ...))` — the unconnected part first. Plover does it 24 times;
its four hinges are written host-first and were never swapped. That is the
24-and-4 split exactly, and it is why Robin, Heron and every fixture in the
suite missed it.

**The fix.** `_native_connector_sides` maps each script connector to the
native slot whose reference names its component, and `_build_joint` reads
`Reference`/`Placement` through that map. A joint whose native references
cannot be matched one-to-one against the components the script connected is
refused at `stage: native_connector_frames` rather than published.

## Why

The critic's unit, and its hypothesis was the one thing I did not do as
asked. It said `CadexDynamics.py:3351` "does match your reading" and to write
the fixture there. I wrote that fixture first and **it passed on the unfixed
code** — `extract_tree` gave `p_local = L_host`, `c_local = I`, and
`L_p ∘ inv(L_c)` equalled `inv(T_host) · T_hw` to 1e-16. So the pure module
was exonerated by the fixture the critic asked for, and the search moved one
layer down to where the two frames get their names. Everything else the
message asked for stands: the fixture came before the fix, the four revolute
bodies still pass, the engine suite and the packaged gate ran, it has an ADR
that states what it touched historically, and `ot7-plover-e` was re-smoked.

Frontier: `salty-isle-4063` (dynamics on MuJoCo) carries the defect;
`rapid-grove-9687` (F7) carries the smoke that is still open; F9's regression
pass has to state the historical reach.

## Method

**Measured, not reasoned.** A three-component assembly through a live
`cadexd` — a grounded plate at 37° about +Z, a tab welded to it
unconnected-first, an arm hinged to it host-first — reproduced the inversion
in one run: the tab exported at `pos="-0.02 -0.006 0"` with a −90° X
rotation, the exact inverse of the host-side connector frame, while the
hinged arm was right. Reading `setJointConnectors` from there found the swap.

`test_dynamics_connector_sides_live.py` is that assembly, with two tests:
the exported body tree composed down to world against the placements the
solver produced (tolerance 1e-4 mm — the hinge disagrees by 4.1e-6 mm, which
is the Ondsel solver's own convergence residual), and the welded tab's
parent-relative frame against the number stated before it was measured,
20 mm along the base's +X, 6 mm up, 90° about X. **Both fail on the old
code**, verified by reverting the worker, reinstalling and running them.

Verification: `pixi run build-engine`; `pixi run test-engine` → **2195
passed, 53 skipped**; `pixi run stage-engine` then the packaged gate
`CADEX_ENGINE_ROOT=build/engine/… pytest test_cadexd_lifecycle.py` → **23
passed**; `cli/tests/test_ot7_{runner,prompts}.py` and `test_retained_fit.py`
→ 115 passed. The plover script rebuilt through a live `cadexd` from the
fixed engine: **all 29 bodies agree with their solved placements**, against
24 wrong before.

No actor edit to any `ot7-*` design: the plover script was read and rebuilt
in a throwaway project, never in `ot7-plover-e`.

## Result

The engine no longer exports a welded body at the inverse of its pose.
Historically the defect touched **only assemblies with a weld written
unconnected-first**, and only through frames — a swapped joint's published
`local_frame`/`global_frame`, its MJCF body pose, and any swept-clearance row
using them. Solved placements, clearance measurements and every static fit
check read component placements and were never affected, which is why
`ot7-plover-e` reported zero failing fit checks on a model whose bodies were
inverted. F9's regression pass must say this.

**F7's smoke is still unproven, now for a correct reason.** `cadex smoke`
measures the accepted revision's **retained** artifacts, and
`ot7-plover-e`'s stored `plover_model-model.xml` (`c4c47094…`) was exported
by the pre-fix engine. A historical view never rebuilds an old run, so the
retry smoke (`evidence/smoke-interim-retry-1`, exit 1, no slot spent) read
the same file and failed the same agreement gate on
`('c_bearing_hip_l', 'c_bearing_hip_r')`. A freshly built plover writes
`71b8b39c…` and passes. **Closing that smoke needs the design built again
under a turn that re-accepts it — a design slot.** `continue-2` and
`continue-3` are still unspent and that decision is open for the next
iteration: spending one on a design whose fit report names nothing would
again be buying a measurement with a slot, and the alternative is to record
F7's smoke as unproven in the closing report.

No new dependency. The unreconciled tail is 2 nodes after this one; the
high-water mark said 1 before it, so no reconcile was due and none was run.

Dispatch closed: 1 unit — the swapped connector frame found, fixed and
pinned by a live test (ADR-393); F7's smoke still blocked on a stale
retained artifact.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot7
- commit: 63236e54b157adce1088c514910d5714f05ba15a

## State Impact

- target: salty-isle-4063 — A weld written unconnected-first no longer exports its body at the inverse of its parent-relative transform: FreeCAD's ensureUnconnectedIsSecondRef swaps Placement1/Placement2 with Reference1/Reference2, and _build_joint read the placement at the script's connector index. _native_connector_sides resolves the native slot by the component its reference names, and refuses an unmatchable joint. CadexDynamics' L_p . inv(L_c) derivation is correct and unchanged. Pinned by test_dynamics_connector_sides_live.py, both tests failing on the old code; all 29 ot7-plover-e bodies now agree with their solved placements.
- target: rapid-grove-9687 — F7's smoke stays unproven: cadex smoke measures the accepted revision's retained MJCF, exported before the fix, so the retry still fails its frame-0 agreement gate. A freshly built plover passes. Closing it needs a turn that re-accepts the design; continue-2 and continue-3 remain unspent.
