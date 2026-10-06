---
node_id: 8ab314f6-8024-540f-9d61-1b73d9bb0b60
slug: dry-vale-5761
title: H2. A passed evaluation produces two heroes
created_at: '2026-10-06T07:42:22+00:00'
parents:
- nimble-pine-0740
summary: ''
---
Status: working

## Current

Charter criterion for run orun4: **H2. A passed evaluation produces two heroes.** When `evaluate` passes, Cadex renders the accepted design on the dark floor: (1) the hero, the studio shot in the H1 font; (2) the print-bed hero, every printable part laid flat as it would print and labelled, with a parts list of purchased hardware (from the inventory) beside it. Purchased parts are not on the bed; overflow goes on more beds in the same image or the image says how many beds it needs. Both show in the 2D viewport and are listed in `/api/project`; a failed evaluation makes neither. Tests cover passing and failing evaluations and the bed layout's non-overlap and bounds. The human owns the checkbox [rec: light-mist-9160].

**Implemented, evidence complete, pending the critic** (ADR-569 + ADR-570, fix in ADR-571) [rec: noble-vale-4742] [rec: peaceful-nest-6589] [rec: frosty-cabin-1461].

- **Print bed** (`CadexStudio.print_bed`): each printed part seated on its largest flat face, MaxRects-packed with a 6 mm gap onto as many 256 mm beds as it takes (bed size a parameter, stated in the image), numbered, with inventory hardware listed. On the scratch copy `orun4-biped-sts`: 10 parts on 2 beds at 256 mm, 1 at 300 mm; 6.0 s, 1536×1024. `test_studio_print_bed.py` (9) pins seat, non-overlap and bounds over 40 random packings, multi-bed, oversize [rec: noble-vale-4742].
- **On pass** (`evaluate.add_heroes`): a passing `cadex evaluate` (also `--film-only`, `--film none`) draws `hero.png` and `print-bed.png` beside `evaluation.json` from the retained accepted geometry (`render.retained_snapshot`, no rebuild, per ADR-457); a fail draws neither and deletes stale ones. Report block `cadex-heroes-v1`; each hero stands alone (no printed part → hero plus a bed error; exit code unchanged by choice). Listed per evaluation in `/api/project`, served by allowlist, shown in the 2D viewport before the film [rec: peaceful-nest-6589].
- **Agree across paths**: the retained-path `print-bed.png` is byte-identical to the rebuild-path example `docs/probes/orun4/h2-print-bed.png`; hero example `docs/probes/orun4/h2-hero.png` [rec: peaceful-nest-6589].
- **Agent path**: the MCP `evaluate` tool draws both heroes only since ADR-571 — ADR-570's claim that it did was false until then (the bridge never called `add_heroes`) [rec: frosty-cabin-1461].
- **Gates** at `b422aa5b`: `pixi run test-engine` 2611 passed, 58 skipped; CLI in thirds, GPU hidden, 400 / 356+1 skipped / 443 passed. Packaged lifecycle gate not run (no protocol change) [rec: peaceful-nest-6589].

## Negative knowledge

None yet.

## Provenance

- light-mist-9160 — operator-declared orun4 charter gap (gap-h2-passed-evaluation-produces-two)
- noble-vale-4742 — H2 unit 1: print-bed hero, parts laid flat and packed on N beds (ADR-569)
- peaceful-nest-6589 — H2 unit 2: passing evaluate draws hero and print bed, listed and shown (ADR-570)
- frosty-cabin-1461 — MCP evaluate tool now draws the heroes too; corrects ADR-570's claim (ADR-571)
