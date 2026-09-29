---
node_id: e8082f35-5d76-5ac6-95b0-356f570d22b5
slug: sweet-sage-3253
title: 'ot10 A3c: P2 sharp printed edges (ADR-415) gated and measured; hex3 P2 0.332'
created_at: '2026-09-27T18:05:03+00:00'
parents:
- shy-clover-2326
summary: ''
---
## What
ot10 A3, the last proxy. This record covers two commits.
- **`fe21211a`** was committed as "no record". It holds the P2 implementation (ADR-415):
  - `cadex_part_worker.sharp_edge_facts` measures, per output, the solid edge length and its sharp convex part. The threshold is the frozen 60°. Seams are left out, and convexity comes from `(n1 × n2) · t > 0`.
  - `part_shape_facts` carries the result as `sharp_edges`. The assembly worker's two count-only calls opt out with `edge_convexity=False`.
  - The inventory's `source_facts` carries it.
  - The CLI sums it over printed placements (`inventory.printed_edges`), and `render.edge_proxy` reports P2 in `render`, `look` and review. It is `null` with a reason rather than a false zero when a printed part has no measurement.
  - Tests: a crude and a designed fixture on the real kernel (`test_part_sharp_edges.py`), and the same pair in the CLI (`test_look.py`).
- **`b829f43e`** does the critic's fix-first items:
  - writes ADR-415 in `docs/DECISIONS.md`;
  - runs the payload rebuild, stage and packaged gate;
  - measures hex3's P2 on a fresh rebuild and records it in `docs/probes/ot10/README.md`;
  - repairs `test_walk.py`'s pinned `measures:` note, which `fe21211a` had broken.

## Why
The critic's message asked for three fixes first:
1. ADR-415 was cited but never written.
2. There was no record for `fe21211a`.
3. The packaged gate was owed for a payload change.

After those, it asked for hex3's P2 measured against the 0.25 bar. All four are done here, and this node is the record for `fe21211a`. Serves `warm-basin-7003` (A3).

A4, the four refusal classes, was **not started**. The budget is one unit, and closing out P2 took it. A4 is next.

## Method
- `pixi run build-engine` and `pixi run stage-engine` both exited 0. The staged `Mod/cadex/cadex_part_worker.py` contains `sharp_edge_facts`.
- Packaged gate: `CADEX_ENGINE_ROOT=build/engine/cadex-engine-0.0.0-linux-x64 pytest src/Mod/cadex/cadex_tests/test_cadexd_lifecycle.py` gave **23 passed**. This also settles the gate that ADR-413 still owed.
- hex3 measurement:
  - Made a fresh `cp -a` of the read-only `hex3` project to `/tmp`. The earlier `/tmp/ot10-hex3` copy had a stale lock and an interrupted run, so it was not reused.
  - Ran `./cadex render --project <copy> --engine <staged payload> --json`. The accepted revision was `c1704bfcb631…`. The run took 7 min 1 s, mostly the rebuild that gives the parts their new fact.
- Suites: `pixi run test-engine`, then `pixi run python -m pytest cli/tests`. After the pin fix, `test_walk.py` was re-run on its own.

## Result
- **hex3 P2 = 0.332.** That is 6,793.3 of 20,468.1 mm of printed edge over 14 printed components, and it **fails** the ≤ 0.25 bar.
- hex3 now measures on all three proxies:

  | proxy | hex3 | bar | meets |
  |---|---|---|---|
  | P1 | 0.373 | ≤ 0.20 | no |
  | P2 | 0.332 | ≤ 0.25 | no |
  | P3 | 2 | 2–3 | yes |

- The hero from this run has sha256 `83cc8beb…`, byte-identical to the committed `hex3-studio_hero.png`, so no new image.
- **A3 now has evidence for every part:**
  - roles and palette (ADR-413);
  - P1 and P3 (ADR-414);
  - P2 (ADR-415);
  - all reported in `render`, `look` and review;
  - each tested with a crude and a designed fixture.

  The owner ticks the box.
- Suites:
  - `test-engine`: **2215 passed, 53 skipped**.
  - `cli/tests`: **987 passed, 1 failed, 1 skipped**. The failure was `test_walk`'s exact note pin, which `fe21211a`'s new P2 clause broke. The previous iteration left that failure silent. After fixing the pin, `test_walk.py` gave **70 passed**, so the net result is 988 passed and 1 skipped.
- Packaged gate: **23 passed** on the staged payload.

Concerns:
- The render summary does not surface `unresolved_edges`, only the summed lengths. On hex3 the engine counted edges it could not evaluate toward the total, not as sharp, so 0.332 is a lower bound if any went unresolved.
- The unreconciled tail is one record (this one); nothing is due for reconcile.

Next: A4. Close the four refusal classes, with one regression test each:
- a wrong horn style name;
- `edit_script` before any script exists;
- more than one assembly or diagnostics output;
- a joint missing or listed twice.

Dispatch closed: 1 unit — P2 closed out: ADR-415 written, payload rebuilt/staged/gated (23 passed), hex3 P2 0.332 (fails 0.25), walk pin repaired; A3 evidence complete

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot10
- commit: b829f43ef22540a5500e964dedc975249e1939ea

## State Impact

- target: warm-basin-7003 — P2 sharp_outside_edge_share measured by the part worker (sharp_edges fact) and reported in render/look/review beside P1 and P3 (ADR-415, fe21211a, b829f43e); packaged gate 23 passed; hex3 P2 0.332 fails 0.25 (P1 0.373 fails, P3 2 meets); all three proxies and roles/palette now have evidence, A3 ready for owner tick
