---
node_id: 4da6ed61-9241-55e9-8b59-d4d5d724fb05
slug: hidden-tooth-3627
title: 'ot10: ADR-430 concept sheet in cadex render; cadex review leads with it; three A5 sheets committed'
created_at: '2026-09-28T13:58:21+00:00'
parents:
- fierce-vale-7652
summary: ''
---
## What

A6 unit one: `cadex render` now writes a **concept sheet**, and `cadex review` opens on it (ADR-430).
- `cli/cadex_cli/sheet.py` is new. `review/render/sheet.png` is one 1536×1024 PNG:
  - on the left, the 1024 px studio hero, identical pixel for pixel to `hero.png`;
  - on the right, the project name, the revision, three key numbers (mass, servo count, size), a palette swatch for each appearance role the design uses, `front`/`right`/`top` as orthographic line drawings, and A1's three proxies.
- The line views reuse the renderer's depth pass, keyed by object and flat face normal. A pixel gets ink at an object change, at the silhouette, or at a crease sharper than 35°.
- The lettering is a 5×7 bitmap face in the same module. There is no new dependency.
- `summary.sheet` records the sheet's revision and digest, its numbers and where each number came from, and its seconds.
- `/api/project` gains a read-only `presentation` block: the revision and digest drawn, its relation to the accepted revision, the files offered and the numbers.
- `/presentation/{sheet,hero}.png` serves only what that block offers.
- The review page's stage gains a first tab, **Concept**. The page opens on it once when a sheet exists, and the phone column reads it before the model.
- `docs/REVIEW-DESIGN.md` gains §14 plus the §2 and §12 changes, in the same change as the page. `docs/CLI.md` and ADR-430 are updated too.
- Sheets for the three A5 designs that met the bar are committed under `docs/probes/ot10/`.

## Why

The target is charter criterion **A6**, frontier node `spring-glade-6801`. This follows the critic's message: the old bet is banned, and A5 now has a passing design for every body plan, so the next rung is A6. I did what the message asked, in the order it asked:
1. The review leads with the hero and the sheet.
2. The sheet is one PNG in the project's review directory.
3. REVIEW-DESIGN.md changes with the page.
4. A test pins the sheet's shape and identity.
5. Sheets of 300 KB or less are committed for biped-1, quadruped-3 and hexapod-10, built from `/tmp` copies.

W1 (the rollout video) is the next unit, not this one.

## Method

- **Where the numbers come from:**
  - Mass is the sum of the accepted MJCF output's `assembly_data.dynamics.inertials`, without the environment. It is read from the pinned accepted attempt's `result.json`, only when that attempt is the revision drawn and carries the accepted digest. The inventory has volumes but no densities, so it cannot give mass.
  - The servo count is the inventory's `catalog_counts` in family `servo`. Horns are their own family.
  - Size is the extent of the drawn solids.
  - A number that cannot be read is `null` with a reason, and the sheet prints `N/A`.
- **Where the sheet is built:** in `write_render`, because it needs the snapshot the render already holds. `cadex review` writes nothing (ADR-286).
- **Which render the review presents:** the accepted revision's walk render when that render has a sheet, otherwise the last `cadex render`.
- **Real runs:** each design was copied with `cp -a` to `/tmp/ot10-a6/<name>`, then `./cadex render --project /tmp/ot10-a6/<name>` was run with the default engine. The sheets were viewed and copied into `docs/probes/ot10/`.
- **Tests:**
  - `cli/tests/test_sheet.py` has 10 tests: shape and size limit, identity (revision, digest, hero pixels), numbers, refusals, line view, bitmap face, the presentation block, walk-render preference, and the routes (anything else under `/presentation/` returns 404).
  - A new browser test, `test_the_page_leads_with_the_concept_sheet_when_the_project_has_one`, runs at both charter sizes.
  - `test_rendered_page_follows_the_spec` now lists the Concept heading and region.

## Result

**What is true now:**
- A `cadex render` writes `sheet.png`, and `cadex review` presents it first.
- Measured on the `/tmp` copies:

| Design | Mass | Servos | Size (mm) | Sheet | Compose time | Views + hero | Rebuild |
|---|---|---|---|---|---|---|---|
| biped-1 | 0.389 kg | 6 | 92×108×221 | 138 KB | 1.2 s | 7.1 s | 58 s |
| quadruped-3 | 0.479 kg | 8 | 178×151×123 | 210 KB | 1.1 s | 7.0 s | 62 s |
| hexapod-10 | 0.654 kg | 12 | 212×231×136 | 212 KB | 1.9 s | 9.3 s | 98 s |

- All three committed sheets are within the 300 KB cap.
- **Suites:**
  - `pixi run python -m pytest cli/tests`: 1028 passed, 1 skipped.
  - The review-design and review-server browser tests ran; they were not skipped.
  - `pixi run test-engine`: 2242 passed, 53 skipped.
  - No engine, protocol or payload change was made, so the packaged gate does not apply.

**Concerns:**
- **A6 is not ticked; the owner ticks it.** Two gaps remain:
  - the sheets have not been seen on the operator URL;
  - the page has no side-by-side comparison of designs.
- **The line views are image-space drawings of the tessellation.** Silhouette, object boundaries and creases only: no hidden-line removal, no dimensions.
- **View labels use the product's axis names.** The biped faces +X, so its visor shows in `right`.
- **Found, not caused:** `~/cadex-projects/ot10-biped-1/script.json` was already modified in its own git tree at 00:40 local, before this session. I left it alone.

**Next:** W1, the rollout video.

**Reconcile:** the tail is now one record, so no reconcile is needed yet.

Dispatch closed: 1 unit — A6 concept sheet in `cadex render` and a Concept-first review page (ADR-430), three A5 sheets committed.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot10
- commit: 0f7747c63bb9ce6372d5c2cee6c348fc14a65223

## State Impact

- target: spring-glade-6801 — cadex render writes review/render/sheet.png (1536x1024: hero pixel-for-pixel, name, revision, mass from accepted MJCF inertials, servo count, size, palette, front/right/top line views, proxies; ADR-430, commit 0f7747c6); /api/project carries a presentation block and the review stage opens on a first Concept tab; REVIEW-DESIGN.md §14 changed with the page; test_sheet.py and a two-size browser test pin shape, identity, numbers and routes; sheets committed for ot10-biped-1 (138 KB, 0.389 kg, 6 servos), ot10-quadruped-3 (210 KB, 0.479 kg, 8) and ot10-hexapod-10 (212 KB, 0.654 kg, 12), drawn from /tmp copies. Evidence complete pending the owner's tick; not yet viewed on the operator URL.
- target: chilly-union-8972 — cadex render also writes the concept sheet (cli/cadex_cli/sheet.py, ADR-430) and cadex review serves /presentation/{sheet,hero}.png and a presentation block in /api/project; no new dependency.
