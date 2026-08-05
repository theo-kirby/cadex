# ORGANIC.md — Organic Modelling, and the CAD/Mesh Interface

Verified against source: 2026-08-05
Status: **O0 closed (ADR-124), O1 closed (ADR-125), O2 closed (ADR-126),
O3 closed (ADR-127).** The phase's four slices are done; O2b and O4 are
parked by decision.

This is Phase 15's arc doc, and it stands to Phase 15 as `docs/MUJOCO.md`
stands to Phase 14: the measurement the phase is sized from, the slices, the
hazards, and a benchmark log that says what actually changed.

`docs/VISION.md` is still authoritative. Provenance: everything here is
`[Cadex-new]`.

The question this phase answers — `docs/VISION.md`'s open question about
whether interactive mesh editing ever arrives, and if so as engine ops or as
shell tools — is answered by O3: **as engine ops, on a declared table, with
the shell supplying only the gesture.**

---

## 1. The measurement: a robot wolf

ADR-123 made `describe_cad_api` serve whole domains, which put `part`'s
surfacing operations in front of the model for the first time. The robot
wolf was re-run against that surface. The project it produced is
`~/arch/woof.cadex` — **read-only; copy it before touching it** — and this
section is measured from its store, not from the conversation that made it.

**What the agent built.** 154 lines, eight parameters, and it is 100%
`part`: not one mesh operation. Sixteen solids, every one a `part.loft`
through elliptical sections built by three helper functions (`sec`, `zsec`,
`tsec`), fused at the end. A hand-written section table — 6 rings for the
torso, 8 for the neck and head, 3 per ear, 6 per leg, 3 per paw, 5 for the
tail. That is a surfacing workflow, and it is why the silhouette improved.

**Eleven accepted revisions in seventeen minutes**, ordinals 1…11 in
`script_history/history.json`, 12:01:16Z to 12:18:28Z. The script grows
5,376 → 6,190 → 6,861 characters. Between them the store also holds **three
attempts that did not survive**, and those are the phase.

**The three ways it tried to weld the seams, in order.**

1. **Morphological closing** — `part.offset(wolf_raw, wr)` then
   `part.offset(grown, -wr)`, with the comment "replaces every concave
   crease where parts meet with a tangent blend of radius wr, without
   selecting edges". The engine answered:

   ```
   api.offset: OpenCascade produced an invalid shape
   ```

   No radius suggested, no failing region named, no partial result.

2. **Fillet the intersection curves** — the agent restructured the model so
   a blend would only hit the big junctions, declared
   `weld_radius=num(8, unit="mm", min=1, max=12, label="Weld blend radius")`,
   and wrote:

   ```python
   wr = min(p.weld_radius, 0.10 * cwh)
   core = part.fillet(core, wr, edges={"geometry_type": "BSpline"})
   ```

   This is exactly right: on a fused loft the seams *are* the B-spline
   intersection curves. It was refused **before reaching OCCT**, by the
   selector contract:

   ```
   api.fillet: invalid edges: must declare expected_count — the cardinality
   is what makes a wrong selector fail instead of silently doing less work.
   Received {'geometry_type': 'BSpline'}.
   ```

   That contract is right in general (`CadexSubshapeQuery.py:24`) and
   unsatisfiable here in particular: **how many intersection curves a
   sixteen-way boolean produced is not knowable to the party writing the
   script.** It is knowable only to the operation that made them.

3. **Give up on blending, and shape instead.** The accepted revision drops
   `weld_radius` for `muscle_blend` — a dimensionless 0…1 that flares each
   limb root wider and buries it deeper, so the joins are grazing rather
   than sharp. It is a real modelling technique and it is what shipped. It
   is also a workaround for an operation that refused.

So the accepted wolf is sixteen lofted tubes fused with **hard creases at
every join**, which is precisely the "looks better but not good" the user
reported.

### What this proves

Not that CAD is the wrong paradigm for organic shapes. `part` already lofts
NURBS through spline sections, which is how car bodies were designed for
thirty years. The gap is four specific things:

1. **The agent cannot see what it built.** `viewport_screenshot` is one
   768 px grab of whatever the user's viewport happens to be showing. It
   iterated on a silhouette nearly blind. → **O0**
2. **Blends fail all-or-nothing and say nothing.** The single most important
   organic operation — round the seams a boolean just made — is unusable on
   any real model, and the one selector that describes those seams cannot
   declare its own cardinality. → **O1**
3. **Nothing lines the aesthetic and mechanical halves up.** A skin and a
   mechanism have no declared interface, so "put the mechanism inside it and
   have everything line up" is done by copying numbers. → **O2**
4. **Shaping requires a chat turn.** Every ring in that wolf is a literal in
   Python. Nudging one silhouette costs a full turn plus a rebuild. → **O3**

---

## 2. The slices

One ADR per slice as it lands; one PR per slice minimum.

### O0 — The agent can see what it built — **closed (ADR-124)**

Shell-side, non-authoring, no engine change. `capture.py` already rendered
through `gpu.types.GPUOffScreen.draw_view3d(...)` with an **explicitly
supplied** `view_matrix` / `window_matrix`; it just happened to read them off
the user's `region_3d`. Feeding it computed matrices instead is the whole
feature.

- `capture.view_matrices(bbox, aspect)` fits four cameras to the Model
  collection's world bounding box — front (−Y), right (+X), top (+Z) in
  orthographic, and a three-quarter perspective at azimuth 45° / elevation
  25° — and returns plain tuples, importing no `bpy`. That is the half the
  headless suite tests and the half Phase 12 re-binds rather than redesigns,
  and it is the same split `cadex_collision.py` keeps between `extents_mm`
  and its overlay.
- `capture.render_views()` renders the four at equal size and composites
  them 2×2 by slice assignment, with the Model collection isolated, solid
  studio shading and overlays off.
- `tools.render_views` is a new tool that does **not** replace
  `viewport_screenshot`: that one answers "what does the user see", which is
  a different question. Read-only, so it is in neither `_ENGINE_TOOLS` nor
  `MUTATING_TOOLS` — the classification `collision_view` got in ADR-091.

What ADR-124 measured, and what it could not: see the ADR. The short form is
that the composite is real (1024×1024, four distinct quadrants, verified by
driving the built application), and that **the gate cannot see it** —
`draw_view3d` needs a real VIEW_3D and the gate runs `--background`.

### O1 — Blends that survive, and the ops that make muscle — **closed (ADR-125)**

Two commits, one PR. This is the slice §1's three failures demand.

**Commit 1 — `part.fillet` survives partial failure and says what happened.**
`TopoShapePy::makeFillet` builds `BRepFilletAPI_MakeFillet` and calls
`.Shape()` without checking `IsDone`, so one impossible edge in three hundred
throws away the other 299. No C++ change: the fallback is Python calling the
existing binding repeatedly, which keeps the diff in `cadex_part_worker.py`,
which is ours. Try the whole set first (today's fast path, unchanged when it
works); on `Part.OCCError` **bisect** the edge set — O(log n) kernel calls,
not O(n) — then act on a new `on_failure` argument: `refuse` (default, but
naming the failing edges by the fingerprint `_selected_subshape_details`
already computes, the count that did succeed, and the largest radius that
worked), `skip`, or `reduce`.

**Commit 2 — the seams, and three ops with organic leverage.**

- `part.fuse(..., blend=radius, blend_on_failure=...)`. The agent's instinct
  is right and fails only because it cannot name the seam set. `fuse` knows
  its own inputs, so it can select exactly the edges lying on two or more
  distinct ones and blend only those. *Rejected alternative:* a `"seam"` key
  in `CadexSubshapeQuery.SELECTOR_KEYS`. That vocabulary is deliberately
  closed and purely **geometric**; "which operation created this edge" is
  provenance, and smuggling it in would make every selector's meaning depend
  on history.
- **Variable-radius fillet**, nearly free: `makeFillet` already has a
  two-radius overload that evolves the radius along each edge. Exposed as
  `part.fillet(shape, radius, radius_end=...)`.
- **`part.sweep` guides and a scaling law** via `BRepOffsetAPI_MakePipeShell`
  — the operation the wolf worked around by hand-lofting four tilted circles
  for the tail.
- **`part.ellipse(..., x_direction=...)`.** Ergonomics, and evidenced: `sec`
  and `zsec` burn an if/else plus up to two `part.transform` calls **per
  section**, thirty-odd times, purely to orient a major axis in plane.
  `part.plane` already takes `x_direction`.

**Landed with one thing cut, and one thing found.** Guide curves on `sweep`
are **not** here: `TopoShapeWirePy::makePipeShell` exposes neither `SetLaw`
nor the guide-curve `SetMode`, so reaching them means a new binding in
inherited `src/Mod/Part` — a decision about the fork's delta, not a fix. The
scaling law is the half the wolf paid for and it needs no binding.
*(**O1b, ADR-128** took that decision and two others; the guide half turned
out to need no binding either. See below.)* What was
found is in ADR-125 and worth repeating here: a partial fillet of a fused
body returns a **compound that passes `IsDone` and fails
`BRepCheck_Analyzer`**, so the probe has to check validity, not just catch
exceptions. Before that, `skip` and `reduce` both "succeeded" and were then
refused by the output validator with the blend context gone.

### O1b — The three things O1 parked — **closed (ADR-128)**

Not a planned slice: it is O1's *deliberately not here* list, taken once the
owner decided the inherited trees are going to be edited over this product's
life and rationing single-method additions buys nothing.

- **`sweep(guide=…, guide_mode=…)`.** Needed no C++ at all.
  `Part.BRepOffsetAPI.MakePipeShell` is the same OCCT class bound whole,
  with `setAuxiliarySpine` on it; O1 priced the fork delta off the wrong
  file. `guide_mode` is `"follow"` (scale the section onto the guide —
  the default, and what "guide" means to a person), `"touch"` (move it) or
  `"orient"` (steer it). The names are ours because OCCT's mislead:
  `BRepFill_Contact` *translates*, and it is `ContactOnBorder` that scales.
- **A real scaling law.** `setLaw` is new in
  `BRepOffsetAPI_MakePipeShellPyImp.cpp`, and with it a lawed sweep lands on
  the closed-form volume to six figures where the station-loft only
  approximated it. The loft is deleted.
- **Per-edge `reduce`.** `makeFillet([r, …], edges)` is new in
  `TopoShapePyImp.cpp`. `on_failure="reduce"` now keeps the requested radius
  on every edge that accepts it, so one impossible edge stops flattening the
  whole body.

Plus the blend probe cap, 10 s → 15 s: it was the *binding* cap on every row
of O1's cost table, so every refusal measured there was a timeout rather
than an answer.

The two C++ additions are the first entries in `docs/FREECAD.md` **§2a** —
the engine's ledger of our delta against upstream FreeCAD, which until now
was empty because everything reached OCCT through bindings FreeCAD already
had.

### O2 — Mounts: the interface, declared once and verified — **closed (ADR-126)**

`CadexTerminals.py` already defines a named, geometry-anchored,
rebuild-derived attachment point, and `CadexBoards.py` (ADR-120) already
makes a table of them that the script declares, the store overrides, the
shell edits, and drift-prunes. A mount is that plus a roll reference and
fastener metadata. **Extend, do not parallel-build.**

- `mounts({...})` / `mount(...)` on `CadexBoards`'s row machinery; canonical
  rows in millimetres in the component's own frame; store keys beside
  `board_specs`/`board_values`; applied through the same `set_params(...)`
  path. A mount row is a terminal row plus `roll` (so the frame is fully
  determined, not just an axis), `fastener` and `clearance`.
- `part.mate(shape, "a", other, "b", *, flip=False, offset=0.0)` — pure frame
  arithmetic, so it lives where `CadexTerminals`'s placement arithmetic
  lives: a module importing nothing from FreeCAD, unit-testable headless.
- **Static interference, refused with numbers** — after a mate, boolean the
  two and refuse a non-zero common volume, naming the millimetres.
- **Shell:** *Define Mount*, reusing `cadex_terminal_pick.py` wholesale.
  Written into the table, not handed to the AI (ADR-121's rule).

**Landed with the roll defaulted rather than picked.** A rim selection gives
an origin and an axis; the third degree of freedom is not in it. Rather than
ask for a second pick — a gesture with no precedent in this UI and no
obvious affordance — the operator projects world **up** across the mount
axis, writes the row, and *says in its report what roll it wrote*. The row
is in a table the user can edit, which is the whole argument for the table.
A second-pick roll stays available if the default turns out to be wrong in
practice; it is not something to build before that is known.

### O3 — The section cage: shaping without a chat turn — **closed (ADR-127)**

The wolf's script *is already a section table* — it is just spelled in Python
literals. Making it declared and editable is a small semantic step with a
large interaction payoff, and it needs **no new kernel math**.

- `CadexCage.py`, modelled line-for-line on `CadexBoards.py`: `cage({...})` /
  `section_cage([...])` / `ring(...)`. A ring row is position along the
  spine, half-width, half-height, roll, and a **shape exponent**
  (superellipse: 2.0 is an ellipse, higher is a rounded rectangle). That one
  number is what makes a limb read as muscled rather than tubular, and it
  costs a parameter rather than an operation.
- `part.loft_cage(cage_value, *, solid=True, closed=False)`.
- `cage_specs` / `cage_values` beside the board keys; `set_params(cages=[...])`
  down the same path as `nets=` / `boards=`.
- **Shell — no new space type.** Rings draw as an edge-only overlay in a
  sibling collection, tagged and never `cadex_output` — `cadex_collision.py`'s
  exact pattern, sibling for the same reason (the contract GC walks
  `all_objects` and would sweep a child). Grab a ring, move or scale it,
  press **Apply**, which goes through `wiring.py`'s single-slot pump
  (ADR-122). Panel in the existing parameters editor. **Adding a space type
  would spend `docs/BLENDER-TREE.md` §2b budget; this slice must not.**

**Landed with two gestures deliberately ignored.** Dragging a ring *across*
the spine is dropped rather than honoured — a cage is a straight spine by
construction and bending it silently would produce a shape the script cannot
express — and rotating a ring does not become its roll, nor does anything
become its exponent. Both stay editable as numbers. Inventing a value from a
gesture the user may have made by accident is the quiet reinterpretation a
declared table exists to prevent.

### O2b — Swept-volume clearance `(parked, by decision)`

Sweep the mechanism through its joint ranges and boolean against the skin.
It is the differentiating check and `assembly` already has the joint limits
to drive it, but it roughly doubles O2. Parked here rather than dropped.

### O4 — subD `(parked, unscheduled)`

Catmull-Clark on a quad cage with per-patch NURBS fitting
(`GeomAPI_PointsToBSplineSurface`) is the real industry answer. It reuses
O3's table, its overlay and its apply path — which is the argument for doing
sections first. **It stays unscheduled until the section cage has been used
in anger and §4 says what it still cannot do.** It is a real project, not a
stretch goal.

---

## 3. Hazards

- **Blend probing is slow on a real body.** Mitigated by bisection, the
  existing shape memo (`test_part_shape_memo.py`) and a stated cap. Measure
  on the wolf; report the number; if it costs more than a few seconds, cap
  the probe depth and **say so in the result** rather than silently doing
  less work.
- **`shell/` diff creep.** O0 and O3 both add UI. Every line must stay inside
  `mesh_agent/` and `shell/tests/python/`; `docs/BLENDER-TREE.md` §2a stays
  eight files, §2b and §2c unmoved (ADR-091). If a slice seems to need a
  space type, that is a decision to bring back, not a fix to slip in.
- **Phase 12 deletes `shell/`.** O0's compositor and O3's overlay get
  rewritten in Rust then. Keeping the pure halves `bpy`-free is what makes
  that a re-binding rather than a re-design.
- **A selector contract that cannot be satisfied is worse than a missing
  op.** §1's second failure is the case: the refusal was correct, actionable
  in general, and impossible to act on there. O1 answers it by moving the
  cardinality to the party that knows it, not by weakening the contract.

---

## 4. The benchmark log

**The wolf is the standing benchmark.** After each slice, rebuild it and
record what changed: does the blend land, does the silhouette hold, how many
turns did it take. Copy `~/arch/woof.cadex` to a scratch directory first —
**never build or probe in `~/arch`, those projects are live.** Drive
rebuilds through the `test_project_rebuild` driver rather than hand-editing
`script.py`, which breaks `cadex params`; back the script up before every
rebuild, because a refused `write_script` silently restores the last
accepted one.

| Slice | Date | What changed |
|---|---|---|
| baseline | 2026-08-05 | 154 lines, 8 params, 16 lofted solids, one `part.fuse`, hard creases at every join. Three weld attempts refused (§1). 11 accepted revisions in 17 minutes. |
| O0 | 2026-08-05 | No model change — O0 authors nothing. The agent can now see the silhouette it is iterating on: four fitted views, 1024×1024, one call. |
| O1 | 2026-08-05 | **The weld lands.** `fuse(blend=8.0, blend_on_failure="skip")` builds the wolf with 25 of its 48 seams rounded, in 25.04 s against a 13.61 s baseline. `blend=15.0, "reduce"` rounds every seam at a reduced radius. The refusal path quotes a workable radius instead of `StdFail_NotDone`. Turns: **one** — the change is one keyword on the `fuse` the script already had. |

| O2 | 2026-08-05 | No wolf change — it has no mechanism to mount yet. What O2 adds is the check: a mate that overlaps refuses with the cubic millimetres, so the skin/mechanism interface stops being two copied numbers. |
| O3 | 2026-08-05 | **The torso ports in one edit.** Its six `sec(...)` literals become a six-`ring(...)` `section_cage`, `part.loft` becomes `part.loft_cage`, and the script accepts and builds — with an exponent per ring, which the sections never had. Rendered, the front view shows a squared-off, fuller torso section instead of an ellipse. The legs, neck, ears and tail are **not** ported: that is a modelling turn rather than a code change, and it is the first thing to do with this phase. |

### What porting the torso showed (2026-08-05)

Done as a check on O3 rather than as a rebuild of the wolf: replace the
torso's six hand-written sections with a `cage(...)` of six rings, leave
everything else alone.

- It is a **smaller** edit than the original, not a larger one: six
  `ring(...)` rows and one `part.loft_cage` replace six `sec(...)` calls and
  a `part.loft`, and the `sec` helper stops being needed by that body at all.
- The **exponent is visible immediately.** At 2.8–3.4 the torso's section
  reads as a rounded rectangle rather than an ellipse — a fuller back and
  flatter flanks — which is exactly the "muscled rather than tubular" the
  parameter exists for, and it cost one number per row.
- **The disc is still there**, because the leg roots were not ported. That
  is the honest state of the benchmark: O3 gives the wolf's worst row a
  handle, and nobody has yet grabbed it.

### What the first render actually showed (2026-08-05)

Rendering the accepted wolf through O0's `render_views`, and the blended one
beside it, moved the benchmark's own conclusion. **The seams were not the
wolf's biggest problem.** In the front view the model is dominated by a
smooth disc roughly twice the body's height, centred on the shoulders, with
the head and ears poking through the middle of it — a pancake, not a
silhouette. It comes from the leg-root sections, whose X half-width is
computed as

```python
rx_top = min(r * (1.50 + 0.60 * b), 0.5 * L - abs(x) - 0.015 * L + 0.1 * T)
```

so at default parameters the "muscle root" flares to something like half the
body length and lofts into a plate. The seam blend is visible and correct
where the legs meet the body — and it is rounding the edges of a disc that
should not be there.

Three things follow, and they are the argument for the rest of the phase.

1. **O0 was worth doing first, and by a wider margin than it was sold on.**
   This defect survived eleven accepted revisions and a user's report of
   "looks better but not good", because nobody in the loop could see the
   model from the front. One tool call now shows it.
2. **The remaining gap is a bad row in a section table**, not a missing
   kernel operation — which is exactly O3's case. A table the user can grab
   and drag fixes this in a gesture; the current spelling needs a chat turn
   to change one arithmetic expression buried in a helper.
3. **The benchmark is not "does the blend land" any more.** It is *does the
   silhouette read as an animal*, and O1 does not answer that. Recorded here
   rather than in the ADR because it is a fact about the wolf, not about the
   decision.
