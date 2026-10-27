# INTEGRATION history — the split, its gate, and its settled questions

> **Historical (moved out of `docs/INTEGRATION.md` 2026-10-27, ADR-828).** How the engine came to run headless behind `cadex-cadexd-v1`, the gate that confirmed the split, and the open questions it settled. The live contract is `docs/INTEGRATION.md`. Shell-era text is as it stood; the Blender shell is deleted (ADR-498).

Until ADR-498 a second client sat on the other side: the Blender shell, a
GPL fork that spoke this protocol from its own process (its account is
`docs/history/BLENDER.md`; its pre-merge history is at
`github.com/theo-kirby/mesh`, the parent fork's at
`github.com/theo-kirby/vibecad`). The CLI was built against this document
without widening it, which is why deleting the shell changed no op. With it
went `mesh.blender` (ADR-496), whose runtime was the shell's binary; that
removed no op or field.

## Options considered (historical)

How the engine came to run headless behind a protocol. Option B was the
endpoint until ADR-498 deleted the shell; ADR-500 replaced it with the
engine, the dashboard and the agent.

| Option | Shape | Assessment |
|---|---|---|
| **A. cadex as base** | Keep the Qt/Coin3D app; invest in its UI until it feels right. | Rejected as endpoint. Coin3D/Quarter is a dead end for Blender-level viewport feel; every hour on Qt chrome is spent on a shell we don't want. |
| **B. Blender as shell** | Blender (mesh fork) is the UI; cadex runs headless as a geometry service. | **Confirmed endpoint until ADR-498** deleted the shell and left the CLI and dashboard as the front end. The fork's assistant package already prototyped the target UX; BMesh solves mesh editing natively; the engine already runs headless (`FreeCADCmd`, worker subprocesses). |
| **C. Two-app bridge** | Both apps stay full apps; a live bridge syncs geometry. | Rejected: two documents of record, two undo systems, permanent sync complexity. |
| **D. Staged** | Keep working engine-side in cadex now; split engine from shell; then adopt a shell endpoint. | **Confirmed path**, with B as the endpoint. Near-term work stays in `src/Mod/cadex/**` and carries over unchanged. |

**Decision: D with B as the endpoint.** Cadex became **cadexd**, a headless
xscript geometry service; the mesh fork was the product shell until ADR-498. The Qt shell
was the interim harness and was **deleted in Phase 7** (ADR-021) — options
A and D's interim state are now history, not plan.

## Decision gate (historical: before Phase 5 committed to the split)

Measured with a real cadexd prototype streaming into Blender:

1. **Tessellation & picking fidelity** — face/edge ID maps survive into
   Blender attributes; picking a face in the viewport resolves to the correct
   `@face-N` pin ≥ 99% of the time on the test-part corpus.
2. **Slider-drag latency** — param change → updated mesh in viewport fast
   enough to feel live on mid-size parts (target: comparable to today's
   in-process slider path; measure both).
3. Rebuild determinism — same script + params → identical content digest
   across cadexd restarts.

If the gate fails, the fallback is continuing on the Qt shell (Phase 3
result) while the gaps are fixed — the engine work is endpoint-neutral either
way. *(Historical: the gate passed, and the Qt shell no longer exists.)*

### Gate status (2026-07-25, closed with Phase 6 — ALL CRITERIA MET)

**Re-confirmed after the merge (ADR-030).** The same gate, against
`Cadex.app` built entirely from this repository, with `MESH_FREECADCMD`,
`MESH_CADEXD_MODULE` and `MESH_CADEX_ENGINE` all unset: `ok: true`,
`engine_from_bundle: true`, picking 372/372 (fidelity 1.0), slider-drag
median **0.576 s**, restore performed and digest-matched, cancellation
answered, 127 main-thread ticks during a 1.59 s rebuild. The pre-merge
baseline measured on the same machine in the same session was 0.629 s, so
nothing regressed; the spread between 0.548, 0.572, 0.576 and 0.629 across
runs is machine load, not change, and a comparison should be made against a
number measured the same day.

Phase 6 (ADR-019) supplied the shell halves in the real Blender shell
(its gate script, deleted with the shell in ADR-498, headless Blender
5.3.0-alpha against release cadexd):

1. **Tessellation & picking fidelity — PASSED.** ID maps land as
   `cadex_face` INT face attributes, byte-identical to the sidecar
   ranges, 100% face coverage; 372/372 ray-cast picks (bar ≥ 99%)
   resolved through `resolve_pin {element_type, index}` to faces whose
   tessellation aggregates (area, centroid, planar residual) match the
   engine's geometric truth on the corpus (box, cone, torus,
   drilled+filleted plate); mesh-domain outputs refuse pins.
2. **Slider-drag latency — PASSED.** Median **0.548 s** over 10
   `set_params` drags on the 24-hole/fillet/mesh-skin baseline through
   Blender → cadexd → worker → tessellation → hydration (bar ≤ 0.65 s) —
   *including* the display streaming the Qt 0.479 s measurement did not
   carry, via the `draft` drag preset + background standard refine
   (1.38 s at rest).
3. **Rebuild determinism — PASSED** (unchanged; re-proven continuously by
   the restore pass and ctest `CadexdLifecycle`).

Engine-half history (pre-Phase 6 evidence). None of the drivers named
below exists now: `cadexd_shell_switchover_integration.py` drove the Qt shell
and died with it (ADR-021), and the other two went with ADR-725. Slider-drag
latency over raw NDJSON is `cadex_tests/cadexd_latency_integration.py`
today.

1. **Tessellation & ID maps — engine half SHIPPED (ADR-017).**
   `cadex-tessellation-v1` display artifacts ride every lifecycle response
   on request: per-face triangle ranges + per-edge polylines mapping to
   the exact 1-based Face/Edge enumeration, 100% face coverage asserted on
   the corpus CI (`tessellation_id_map_integration.py`), adaptive
   deflection `clamp(rel × bbox_diagonal, 0.05, 5.0)` with
   coarse/standard/fine presets (the 409k-triangle fixed-deflection
   failure mode is designed out). Headless `resolve_pin` resolves
   fingerprints and picked indices against the accepted staged BREP
   (`pin_resolution_integration.py` proves fingerprint↔index↔face_details
   agreement and re-resolution across a `set_params` move). Remaining:
   attribute transport into Blender + viewport picking fidelity (needs the
   prototype).
2. **Slider-drag latency — parity MEASURED THROUGH THE PROTOCOL.**
   10 `set_params` drags on the 24-hole/fillet/mesh-skin baseline part
   through the full client → cadexd → worker → hydrate path: **median
   0.479 s** (`cadexd_shell_switchover_integration.py`; bar ≤ 0.65 s,
   in-process baseline 0.57 s). Protocol framing + shell hydration cost
   less than the in-process publication they replaced. The per-drag
   `FreeCADCmd --safe-mode` worker spawn (~0.4–0.5 s) still dominates; a
   **warm-standby worker** inside cadexd is the identified (not yet
   built) lever for sub-100 ms drags.
3. **Rebuild determinism — PASSED, now re-proven continuously.** Same
   script + params → identical content digest across process restarts and
   across two FreeCAD builds (ADR-016 evidence stands). Since Phase 5
   every `open_project` runs a restore pass that re-executes THE script
   and asserts digest equality against the accepted digest, and ctest
   `CadexdLifecycle` kills cadexd with SIGKILL and verifies the respawned
   restore digest — restart determinism is exercised on every open, not
   once per audit.

## Open questions

- ~~Exact transport (stdio vs socket); per-project vs multiplexing~~ —
  decided 2026-07-25 (ADR-017): stdio NDJSON, one cadexd per project,
  spawned/owned by the client.
- ~~Where conversation history lives post-split~~ — decided 2026-07-25
  (ADR-020, decision 4): **the Blender file**, together with the Claude
  Code `session_id` — then, after the shell's deletion (ADR-498), the
  project's `agent.json`. Since ADR-538 Cadex runs no model loop and keeps
  no conversation at all: it belongs to whichever agent drives `cadex mcp`.
  What has not changed is that the conversation is client state — the
  engine has no notion of a turn. The engine's conversation store was deleted with the Qt shell
  (ADR-021).
- ~~Progressive tessellation (stream coarse then refine)~~ — shipped
  2026-07-25 (ADR-019): drag requests `draft` quality, a cancellable
  background `rebuild` restores `standard` after the drag settles.
- ~~The warm-standby worker for sub-100 ms slider drags~~ — shipped as
  `CadexWarmWorker.py`: one resident worker per open project, spawned on
  the first `preview_params` (`docs/ARCHITECTURE.md`).


## Published joint sweeps (as INTEGRATION.md carried them until 2026-10-27)

The canonical description is now `docs/XSCRIPT.md` "Sampled hinge and slider fit".


`inspect scope=clearance path=/clearance_sweep` reads the accepted assembly's
published sweep unchanged: coverage status, the declared steps (`step_degrees`
for hinges, `step_mm` for sliders, either null when undeclared) and runtime
bounds, per-joint timings, pair minimum distances (mm), maximum common volumes
(mm³), and first-contact values in each joint's own `unit`: a revolute joint
reports `range_degrees`, `initial_degrees` and `first_contact_degrees`; a
slider reports `range_mm`, `initial_mm` and `first_contact_mm`. First contact
is the first sample from the lower limit within 0.001 mm; other joints stay at
their solved pose. Missing data returns `status: unavailable` with a reason;
unsupported joints, a limited joint whose step is undeclared, and budget
exhaustion retain `status: incomplete` and their reasons.
Complete coverage means measurements exist, **not** that fit passes: an
assembly with no limited joint publishes complete coverage of an empty set.
Since ADR-367 the sweep is published whether or not a step is declared, so an
assembly declaring neither names every limited joint `incomplete` with the
missing declaration instead of publishing nothing; a revision accepted by an
older engine still has no sweep and reads `unavailable`. Since ADR-371 a
**suppressed** limited joint retains `status: skipped` with its reason and no
measurements: the solver ignores it, so it holds no range to sweep, no
subprocess runs for it and it does not make the assembly's coverage
`incomplete`. A revision accepted before ADR-371 carries it as `incomplete`
with an unsupported-kind reason instead; no response shape or op argument
changed either way. Since ADR-375 a joint that could move and declares **no limits** is
`incomplete` with a reason naming the limit to declare, rather than absent
from `joints` entirely; only a `fixed` joint and a suppressed joint the
assembly also left unlimited are omitted, neither holding a range to sweep.
A revision accepted before ADR-375 simply has no row for such a joint, so its
coverage may read `complete` while an unbounded joint went unmeasured. Since
ADR-374 each pair row also carries
`relative_motion`: true when exactly one side of the pair sits inside the
swept joint's moving subtree, which is the only case that joint can change.
A pair with `relative_motion: false` is one rigid body for this sweep and
repeats its solved-pose measurement at every sample, so a reader rolling a
joint row up reads its minimum distance, maximum common volume and first
contact over the moving pairs alone — otherwise a horn welded flush against
the link it turns with reports 0.0 mm at every value and takes first contact
at the bottom of the range. Until ADR-692 every pair was published under
every joint. The `relative_motion` key is **absent** on a revision accepted
before ADR-374, which a reader counts as moving so an older receipt reads as it
always did. Since ADR-419 a moving pair whose exact-geometry boxes stay more
than 10 mm apart at every sample carries `culled: true`. Its
`minimum_distance_mm` is that box gap, a lower bound rather than a
measurement; its common volume is 0.0 and its first contact is null, both
proved by the boxes. Since ADR-686 the bound at a sample may also come from
the distance measured at another sample less how far the parts travel
between the two, so a pair can be measured at some samples and still be
`culled` once every sample is proved past 10 mm (or past its declared
floor, when that is larger); the row's meaning is unchanged. A rigid pair's row repeats the static solved-pose
measurement, and since ADR-423 carries `culled: true` when that static
measurement is itself a bound. The `culled` key is absent on every exactly
measured row and on a revision accepted before ADR-419. No op argument changed.
Since ADR-692 a joint's `pairs` holds only the pairs it moves that were
measured exactly, each with `relative_motion: true` and no `culled` key: the
rows a verdict can rest on. The rest are counted on the joint row:
`pairs_rigid` (pairs with `relative_motion: false`, whose numbers are the
static rows' at `/pairs`), `pairs_culled` (moving pairs bound past their cull
margin, none able to touch or reach a floor) with
`culled_minimum_distance_mm`, the least of their lower bounds (null when
none), and `pairs_moving`, the kept rows and the culled ones together. On
`panel-cat-4`, 307 components (46,971 pairs) and 17 swept joints, this took the published
sweep from 168 MB to 35 kB. These four keys are absent on a revision
accepted before ADR-692, whose `pairs` still lists every pair. No op
argument changed.
Since ADR-621 a joint on a **closed loop** is swept rather than refused: a
limited revolute or slider of the loop is driven through its range and every
other joint of the loops sharing a joint with it is re-solved at each sample,
the loop's other limited joints held at their solved value unless holding
them would lock it. Its row adds `loop` (`closures`, `joints`), `held`,
`passive`, `free_freedoms`, `reached_degrees`/`reached_mm` (the range that
closed), `unclosed` (each sample that did not close, with its value in the
joint's unit and `residual_mm`, null past the first), `worst_closure_residual_mm`
and `closure_tolerance_mm`; `sample_count` counts the closed samples only, and
a row with any `unclosed` sample is `incomplete` with a reason saying where
the loop stopped closing. A pair row's `relative_motion` is then true when the
two bodies move differently at some closed sample. A loop joint with no
limits of its own retains `status: passive` with `loop`, `driven_by` (the
loop's limited joints) and a reason, and no measurements: it is not missing
coverage. A loop with no limited joint keeps every joint `incomplete`, naming
the loop. All of these keys are absent on a revision accepted before ADR-621,
whose loop joints read `incomplete`. No op argument changed.

`cadex clearance --sweep` writes these facts and the accepted revision to
`docs/clearance-sweep.md`. Exit 0 means the report was written, including when
coverage is missing or incomplete. Static threshold flags do not reinterpret
sweep extrema as fit-intent verdicts. Inspection never rebuilds or re-accepts.
To acquire measurements, explicitly build a script declaring
`assembly.assembly(..., sweep_step_degrees=...)` and/or
`assembly.assembly(..., sweep_step_mm=...)`. Legacy projects keep their
accepted identity. The existing inspect arguments and generic paged response
contract are unchanged; clients continue to pass the scope value through.
