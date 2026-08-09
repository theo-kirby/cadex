---
node_id: ff7dac1f-36a9-5332-aa6e-951844690070
slug: forest-wind-3489
title: 'Dimensions: a declared output with no geometry, drawn in screen space'
created_at: '2026-08-09T18:27:02+00:00'
parents:
- ancient-current-9419
summary: ''
---
## What

Dimensions. A script declares one with `part.measurement(shape, kind=...)`, and
the viewport draws it like a drawing sheet's: an extension line at each anchor,
a dimension line between them, and the number in the middle with the line
broken around it.

Three pieces, shipped together (ADR-139):

- **`part.measurement`**, the first part output that carries no geometry at
  all. Three kinds — `distance` between two selected subshapes, `diameter` of
  one circular edge or cylindrical face, `extent` along an axis of the
  bounding box. What it publishes is two exact anchor points in the measured
  shape's own frame plus a number already formatted to text.
- **an optional `measurement` key** on the response's `display` entry, on
  exactly ADR-049's terms.
- **`cadex_dimension.py`**, a `POST_PIXEL` overlay, plus a Dimensions toggle
  and a Measure button.

No new op, no new `artifact_kind`, no change to `compute_project_digest`, no
change to `cadex_hydrate`, and no line added to the inherited Blender tree.

## Why

Nothing like it existed. The word "measurement" appeared once in
`cadex_domain_api.py:47` as an output-type mapping for the **inspection**
domain — which is not one of the five live domains, has no API, no worker and
no test. A dead row in a table.

The stated requirement was that a dimension read correctly *from any viewing
angle*, which is the whole difficulty: a dimension needs a plane, and any plane
fixed in the model goes edge-on if you orbit far enough.

## Method

Four findings from exploration carried the design, all checked before code.

**`cadex_live.py`'s force arrows are the overlay architecture** — a 3D pass and
a `blf` text pass, with the handler add/remove/reload discipline already worked
out. **`resolve_selected_subshapes` already resolves an ADR-029 fingerprint**
to kernel subshapes; the part worker calls it for six existing ops.
**`distToShape` is already used twice in this tree** and returns the distance
*and both closest points*, so `kind="distance"` needs no per-geometry special
case at all. And **two artifact-less output types already worked** — `points`
and `solver_diagnostics` — each as a branch in
`cadex_domain_worker._serialize_output` that attaches a dict and sets no
`artifact_kind`.

**The decision the whole overlay rests on: screen space.** Project the two
anchors, then compute every other part of the drawing in 2D pixels. The offset
direction is perpendicular *on the screen*, so it cannot go edge-on by
construction rather than by care; gaps, ticks and text size are pixel
constants, so a 2 mm boss and a 2 m beam read identically at any zoom; and it
is one `POST_PIXEL` pass where the force arrows need two, because a dimension
is not a world object.

**In the script, not the shell.** Scene data in the `.blend` would have been
much cheaper and would have been the only piece of model state not in the
script — lost by a Save-As, unauthorable by the agent, unable to travel in a
`.cxpart`. In the script it is anchored by selector and *recomputed*, which is
what makes it follow a parameter.

Build order was pure drawing half → engine primitive → the record on the wire →
end-to-end against a real engine → shell → docs, with the end-to-end step
non-optional for ADR-135's reason.

## Result

**All gates green.**

- `pixi run python -m pytest src/Mod/cadex/cadex_tests` — **1,730 passed, 22
  skipped** (was 1,723).
- `pixi run python -m pytest cli/tests` — **80 passed**, unchanged; the CLI
  needed no code.
- `CADEX_ENGINE_ROOT=<payload> pytest test_cadexd_lifecycle.py
  test_measurement.py test_linked_part_live.py` — **21 passed against the
  staged payload**, which is what proves the primitive ships (ADR-023).
- `pixi run gate` — **675 checks, `"ok": true`**, no failures.

**The measured claim.** The gate builds a measured part and then asks for the
drawing from three view matrices: from the front it is a dimension with six
segments carrying its number; after a 60° orbit it is still a dimension and the
drawing has moved although the anchors have not; and **looking straight down
the measured axis it becomes a leader still carrying `10.00 mm`**. Then a
slider moves the width and the span reads `100.00 mm` while the height, which
nothing moved, does not budge.

The live engine test says the same thing in numbers: on a 60×40×10 plate with a
6 mm bore, `extent axis="z"` is 10.00 mm with anchors at `[30, 20, 0]`–`[30,
20, 10]` — down the centre line, not off a corner — and the diameter is
`Ø6.00 mm` with its centre on the bore axis.

**The digest was not touched, and that is a property rather than luck.**
`compute_project_digest` keys on *having* an artifact, so an artifact-less
output falls through to `payload_sha256`, the hash of its own declaration. A
measurement's identity is which selectors it names, not what today's parameters
make it read.

**Two constants had to come apart.** `_PUBLISHABLE_TYPES` was both the part
pack's output-type contract and the validator for a caller's `output_type=`
argument. Those were the same set only for as long as every output was a shape.

**What it gives up**, stated rather than discovered later: a selector that a
parameter change removes fails the rebuild (correctly, naming the selector);
`distToShape` returns a *minimum*, which is the thickness for two parallel
planes and the closest approach for two angled faces; one subject shape per
measurement; and faces and edges only, with viewport picking still faces only.

**Shell diff:** one new file (650 lines) plus +331/-3 across six, every one
under `shell/scripts/addons_core/mesh_agent/` or `shell/tests/python/`. Nothing
in `docs/BLENDER-TREE.md` §2 moved; §2a is still eight files.

## Negative knowledge

- **The viewport polygon count cannot tell you anything about a dimension** —
  the mesh in the viewport is a tessellation whatever the output is. This is
  the second time that assertion has been written and thrown away in this tree
  (ADR-138's gate test made it first). The check that works is calling the
  drawing function with a made-up region and view matrix, which is why
  `drawing_for` is a function rather than something living inside a draw
  handler.
- **A circle's in-plane basis must not come from a fixed reference axis.** A
  bore drilled down Z is the single most common thing anyone measures, so the
  naive choice fails on the first real model rather than an exotic one; the
  basis comes off the world axis least parallel to the circle's own.
- **The gate exits 0 when a test raises mid-run.** An `AttributeError` in one
  test ended the suite after 355 checks with no `CADEX-BLENDER-GATE` line at
  all — and `pixi run gate` still exited 0. Checking the exit code is not
  enough; the `"ok": true` line has to be read. Pre-existing, and not fixed
  here.
- `docs/INTEGRATION.md`'s two contract tables are scraped by regex on any line
  starting with `` | ` ``, across the whole document for ops and within the
  response section for keys. A new markdown table anywhere in the file is read
  as protocol rows. Nested records get a bullet list.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: main
- commit: 62bd3848a31517ee71eb503203ec12b96d44b779

## State Impact

- target: forest-wind-0342 — The engine gains declared dimensions (ADR-139): part.measurement is the first part output carrying no geometry at all, publishing two exact anchor points and a pre-formatted number. Three kinds: distance (via distToShape, which supplies value and both anchors in one call, so no per-geometry special case), diameter (publishes the circle, since its legible endpoints are per frame) and extent (bounding span along an axis). Anchored by ADR-029 selector and recomputed rather than remembered, so a dimension follows the parameter that moves its part. Third artifact-less output type after points and solver_diagnostics; compute_project_digest keys on having an artifact, so it enters the digest as payload_sha256 of its own declaration and no digest code changed. Part domain 57 -> 58 operations. _PUBLISHABLE_TYPES split from a new _PACK_OUTPUT_TYPES, which were the same set only while every output was a shape. Suite 1,723 -> 1,730 passed / 22 skipped; 21 passed against the staged payload.
- target: shy-crane-2573 — The shell gains cadex_dimension.py (ADR-139), a POST_PIXEL overlay that draws a declared measurement as an architectural dimension. Everything except the two anchors is computed in screen space: the offset direction is perpendicular on the screen so it can never go edge-on however you orbit, and gaps/ticks/text are pixel constants so any scale of part reads identically. Below MINIMUM_SPAN_PX -- looking down the measured axis -- it becomes a leader carrying the number, so the value survives every viewing angle. It creates no Blender objects, so unlike cadex_collision and cadex_cage it needs no sibling collection and cannot be swept by the contract GC. Plus a Dimensions toggle in the same one-button-is-the-state row the collision overlay uses, and a Measure button that queues a request on the pin queue rather than writing the script -- the script keeps exactly one author. Shell diff: one new file (650 lines) plus +331/-3 across six, all under mesh_agent/ or tests/python/; BLENDER-TREE section 2a still eight files. Gate 675 checks, ok true.
