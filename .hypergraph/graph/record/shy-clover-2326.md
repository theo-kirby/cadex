---
node_id: aaf6e1e1-73cd-5ddd-8b78-8a92884f787e
slug: shy-clover-2326
title: 'ot10 A3b: P1 and P3 measured on the hero in render, look and review; hex3 P1 0.373, P3 2'
created_at: '2026-09-27T17:33:33+00:00'
parents:
- fresh-orchard-6718
summary: ''
---
## What
ot10 A3, second half, partly: `cadex render`, the agent's `look` and the walk's review now measure A1's two **image** proxies on the hero view (ADR-414, commit `bba15a47`):
- **P1** `hardware_silhouette_share`: of the hero subsamples the design covers, the fraction whose front-most surface is a purchased component;
- **P3** `material_count`: the distinct colours of the objects visible in the hero, listed.

Each proxy carries its frozen bar and `meets`. hex3 is measured on both. **P2 (sharp printed outside edges) is not in this unit**: see *Why*.

## Why
The critic asked for the second half of A3: all three proxies in `look` and review, roles carried into review, a crude/designed test for each, hex3 scored, both suites, and a before/after on hex3. Serves `warm-basin-7003`.

**Deviation: P2 is split out, not done.** P1 and P3 are image measures computed in the CLI. P2 needs BREP edges and the faces on each side of them, which only the engine's worker holds. That means a new per-output fact in `part_shape_facts`, carried by the inventory scope. It is an engine and payload change, so it also needs a rebuild, a stage and the packaged lifecycle gate. And hex3's accepted attempt would have to be re-produced to carry the new fact. Doing that in the same unit would have made it two units. Under "shrink the unit, not the work", P2 is the next unit. Nothing in this commit stubs it: no P2 field is emitted until it is measured.

**Not done: reconcile.** The critic also asked for a reconcile. Work iterations are forbidden to reconcile, so none was run. The critic's first fix, the missing ADR-413 record, was written as `fresh-orchard-6718` (commit `dbd8a410`) before this unit.

## Method
- **`cli/cadex_cli/render.py`**
  - The studio renderer's depth pass is extracted as `_depth_pass`. The shading pass is unchanged.
  - New `design_proxies(triangles, summary, *, exclude, purchased, appearance, palette)`. It runs that depth pass alone on the hero view, at a fixed `PROXY_SIZE` of 512 px with 2×2 subsamples, and counts front-most subsamples per object. Because the size is fixed, `render`, `look` and review report the same numbers whatever size they draw at.
  - With no inventory, P1 is `null` with a reason. A zero would be a false pass.
  - `PROXY_BARS` holds the frozen bars. `describe_proxies` gives a one-line note.
  - `write_render` writes `summary.proxies`.
- **`bridge.py`**: `look`'s reply gains a `measures` fact (value, bar and meets for P1 and P3), measured on the hero whatever views were asked for.
- **`__main__.py`**: `cadex render` and the walk's review add a `measures:` note. The review's `render` block is the whole render summary, so `review.json` now carries both the ADR-413 roles (`appearance`, `palette`) and `proxies`.
- **Tests** (`cli/tests/test_look.py`):
  - P1 fails a servo on a plate (> 0.5) and passes the same servo inside a printed shell (0.0). It is unmeasured, not zero, with no inventory.
  - P1 counts only what is in front: a servo half hidden behind a wall.
  - P3 fails one colour (1) and a rainbow (4), and passes shell, mechanism and accent (3). Environment geometry is not counted.
  - The proxies do not depend on the size `look` draws at.
  - `render` and bridge `look` both report the proxies.
- **Contract test.** `test_ot10_contract.py` holds `PROXY_BARS` equal to `contract.json`.
- **Walk test.** `test_walk.py`'s pinned note list gains the new `measures:` line.
- **Docs.** Updated `docs/CLI.md`, the `docs/probes/ot10/README.md` A3 section with hex3's before and after, and ADR-414.

## Result
- **hex3, measured.** Read-only original; the same `/tmp` copy at revision `c1704bfcb631…`; `./cadex render --project <copy> --json`, 7 min 2 s in all, 207 s of it the rebuild.
  - **P1 = 0.373** (76,170 of 204,356 subsamples). That is over the ≤ 0.20 bar: over a third of hex3's hero silhouette is bought servos and boards.
  - **P3 = 2** (`#2F3237`, `#E9E6DF`). That meets the 2–3 bar.
  - P2 is not measured.
- **Before and after.**
  - Before (A1): hex3's proxies were not measured, and P3 was 2 only by construction.
  - After: the values above, now in `docs/probes/ot10/README.md`.
  - The measurement changes no pixel. The hero it wrote has sha256 `83cc8beb…`, byte-identical to the committed `hex3-studio_hero.png`. So no new image is committed, and none is needed: this is not a renderer change.
- **Suites** at the final tree.
  - `pixi run test-engine`: **2212 passed, 53 skipped**.
  - `pixi run python -m pytest cli/tests`: **985 passed, 1 failed, 1 skipped**. The one failure was `test_walk`'s exact note-list pin, which the new `measures:` note broke. After fixing the pin, `test_walk.py` passed in full: 70 passed. So the net result is 986 passed and 1 skipped.
  - There is no engine, protocol or payload change in this unit, so the packaged gate does not apply.

Concerns and assumptions:
- **Next unit: P2.** It should be a worker fact (sharp convex edge length and total edge length per printed solid, per the frozen definition), carried in inventory rows. That needs a packaged gate.
- **ADR-413's gate is still owed.** ADR-413's engine change has not had its packaged gate run either. The same unit should run it.
- **Measurement cost.** The P1/P3 pass adds about 1 s on hex3 (a depth pass at 1024² subsamples). It was not separately timed.
- **Tail.** The unreconciled tail is now four records (`terse-falcon-8320`, `happy-garden-2470`, `fresh-orchard-6718` and this one), past the three-record trigger. It is left for the reconcile pass.

Dispatch closed: 1 unit — P1 and P3 measured on the hero in render, look and review (ADR-414); hex3 P1 0.373 (fails), P3 2 (meets); P2 split to the next unit

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot10
- commit: bba15a47bfe60fe02cf92f9a7e2e9124d03cdefc

## State Impact

- target: warm-basin-7003 — render, look and review report P1 hardware_silhouette_share and P3 material_count measured on the hero (512 px depth pass, frozen bars, meets), roles and proxies reach review.json via the render block (ADR-414, bba15a47); hex3 P1 0.373 fails, P3 2 meets; P2 sharp_outside_edge_share still open (needs a worker fact and packaged gate)
