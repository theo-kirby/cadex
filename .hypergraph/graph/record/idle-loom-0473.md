---
node_id: 9c1f5999-c7f9-51fc-9bed-675487f6b851
slug: idle-loom-0473
title: 'orun1 F1: accepted digestbug projects reopen — blend search in measured order, recipe-level restore (ADR-476)'
created_at: '2026-10-02T18:42:07+00:00'
parents:
- sweet-brook-2725
summary: ''
---
## What

F1 diagnosed and fixed (ADR-476, commit `9989b45c`). Three sweep projects refused every open with "The restore pass digest does not match the accepted digest". They now open and render at their accepted revisions, on fresh `orun1-*` copies. The `digestbug-*` originals were only ever copied.

## Why

The critic named F1, the top rung of the orun1 ladder (`red-pond-8515`). This unit did what the message asked: copy, rebuild, diff, find the cause, write a regression that fails before the fix, fix it in the product, and show all three open and render.

## Method

- Copied the three projects to `~/cadex-projects/orun1-{balancer-b-motors-in-body,balancer-d-product-shell,hexapod-h-free}`. Re-copied from the read-only originals before the final proof.
- Reproduced the refusal with `./cadex render` on all three. Drove `open_project` over raw NDJSON to read the `observed` block that the CLI drops. Ran a second driver with artifact pruning disabled, so the restored attempt survived for comparison.
- Diffed every output's geometry entry between the accepted attempt and the restored one, then the vertex sets, counts and blend diagnostics of each differing output.
- Inputs that were the same: `script.py` is byte-identical to the accepted revision's source in all three. The engine code had not changed since acceptance (the last `src/Mod/cadex` commit is 2026-10-01 17:01; acceptance was 2026-10-02 06:49–11:05). Every output's definition hash matched. Only the kernel fingerprint differed.
- Causes:
  1. **Partial blends depended on kernel edge order.** `fillet(…, on_failure="skip")` with no edge selector probes greedily and stops at 48 calls. Boolean results enumerate edges in a per-process order. On balancer-b's `tub`, 20, 19 and 31 of 165 edges were kept across three runs, with vertex moves of 0.8–3.6 mm. The cap was `calls`, not the 15 s clock (1.2–2.3 s spent).
  2. **`part.offset` moved vertices.** The hexapod's `shell`: same topology and bounding box, 3 of 92 vertices moved 4.5–4.9 µm (about 40× their own BREP tolerance), volume moved in the 4th decimal. ADR-421's fingerprint assumed the vertex set stayed exact.
  - With a canonical order, balancer-b `tub` reproduced exactly. `frame` still kept 36 edges in one process and 37 in the next, so the kernel's verdict on a marginal subset is itself not reproducible.
- Resumed turns were not a cause. Restore runs the accepted source, and the drift reproduces with no session. Load only changes how often it shows: `d` opened when run alone and refused when three opens ran in parallel. Side observation: the hexapod's accepted attempt is staged under revision dir `c5c63c30…` while its accepted revision is `94759ef5…`. The path is recorded, so restore reads it correctly.
- Fix, in two parts:
  - `cadex_part_worker._blend_canonical_order`: when the whole selection fails, the partial-blend search walks the edges in measured order. Every blend it builds still passes them in kernel order. A first version also sorted the one-call fast path. That re-indexed every filleted output against ADR-025's golden (`test_subshape_enumeration`, caught by the full suite) and was narrowed, so the fast path is byte- and ordinal-identical to before.
  - `cadexd._recipe_agrees` runs when the byte and geometry digests disagree. If the source, settings (`param_values`, mounts, cages, nets, boards, inputs) and every output's name/domain/type/definition match the accepted attempt (`CadexGeometryDigest.staged_recipe_digest`), the open succeeds with `matched_by: "recipe"` and `drifted_outputs` (`staged_drifted_outputs`). The accepted digest, attempt and candidate stay pinned. Missing evidence or a changed script still refuses.
  - `CadexdProtocol` gains the optional `restore.drifted_outputs`. `docs/INTEGRATION.md` and ADR-476 updated.

## Result

- **All three open and render at their accepted revision with the fixed product**, each opened twice (raw `open_project`, then `cadex render`):
  - balancer-b at `2fb82493`, drifted `frame`, `tub`;
  - balancer-d at `68c37ac1`, drifted `base`, `core`, `hood`;
  - hexapod at `94759ef5`, drifted `chassis`, `coxa_*` ×6, `shell`.
  - Every render reply is `ok: true`, with a hero, four views and a sheet under each copy's `review/render/`.
- **Regressions, each failing on the old source:**
  - `test_part_blending.py::test_a_capped_partial_blend_does_not_depend_on_the_kernels_edge_order`;
  - `test_cadexd_lifecycle.py::test_the_accepted_recipe_reopens_when_the_kernel_rebuilds_it_differently` (real kernel; also pins the refusal when the accepted request is missing).
  - The changed-script refusal test now also asserts the recipe verdict.
- **Suites at this revision:** `pixi run test-engine` 2545 passed, 61 skipped. Engine rebuilt and staged; packaged lifecycle gate (`CADEX_ENGINE_ROOT=build/engine/cadex-engine-0.0.0-linux-x64`, `test_cadexd_lifecycle.py`) 24 passed. The first full-suite run failed `test_subshape_enumeration` on the first version of the sort, which was then narrowed. `pixi run python -m pytest cli/tests` with the GPU hidden: 1290 passed, 1 skipped.
- **Concerns for the next iteration:**
  - `cadex render` sends an accepting `rebuild` with a display request (ADR-303). After a render, a drifted project's accepted digest and attempt become the render's own rebuild, at the same accepted revision. On a fresh copy of balancer-d, three renders in a row all succeeded and left the accepted digest at `c01707f1`, then `4b2126ce`, then `c01707f1`: d's rebuild still alternates between two kernel answers after the sort. Every open still succeeds through the recipe path. Whether a display rebuild should re-accept is left open; it is not changed here.
  - One render of balancer-d failed with "The restore pass could not re-run the stored script" while the engine suite and an engine build were running on the same machine. It opened and rendered when re-run alone. The CLI dropped the failure detail, so the cause is not measured. It is most likely the 300 s worker budget under load.
  - Sorting changes which edges any cap-bound partial blend keeps. Every accepted design that relies on one rebuilds those outputs differently once and opens through the recipe path, which names them. Recorded, not hidden.
  - The restore pass now proves "same recipe", not "bit-reproducible". The byte and geometry digests are still consulted first.
  - The CLI's open-failure message still drops cadexd's `observed` detail. Not changed here.
  - `drive.py`-style diagnosis lives in /tmp and is not committed.

Dispatch closed: 1 unit — F1 fixed: partial blends sort their edges, and an accepted recipe reopens when the kernel rebuilds it differently (ADR-476); all three digestbug copies open and render.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/orun1
- commit: 9989b45cb3a0889619ed1835f87c6fd7990dfe17

## State Impact

- target: red-pond-8515 — F1 evidence: cause diagnosed (kernel-order-dependent partial skip blends; part.offset µm vertex drift; resumed turns not a cause), fixed in product (ADR-476, commit 9989b45c) with two regressions that fail before the fix; all three orun1-* copies open (matched_by recipe, drifted outputs named) and render at accepted revisions 2fb82493/68c37ac1/94759ef5; engine 2545/61 skipped, cli 1290/1 skipped, packaged gate 24 passed. Open: render's display rebuild re-accepts a drifted model.
- target: forest-wind-0342 — open_project restore gains a recipe-level last opinion (matched_by: recipe, drifted_outputs) and partial blends search edges in measured order (ADR-476).
