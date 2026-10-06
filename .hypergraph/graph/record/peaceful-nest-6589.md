---
node_id: 57530394-e786-54b5-8ae1-ff5ff2030d35
slug: peaceful-nest-6589
title: 'H2 unit 2: a passed evaluation presents its hero and print bed (ADR-570)'
created_at: '2026-10-06T18:55:48+00:00'
parents:
- noble-vale-4742
summary: ''
---
## What

H2 unit 2 of 2: when `cadex evaluate` passes, it renders the studio hero and the print-bed
hero of the accepted revision that passed and stores both beside `evaluation.json`. They
are listed in `/api/project`, served under the evaluation allowlist and shown in the 2D
viewport (ADR-570, commit `b422aa5b`). With unit 1 (ADR-569), this closes the
implementation side of H2.

## Why

The critic named H2 unit 2 as the next unit, after one fix: `BED_APPROXIMATION` still
said "packed in rows". That fix went first. The string now says parts are packed "onto as
many beds as it takes by MaxRects with a fixed gap". Everything else follows the
critic's message: render on pass, store beside `evaluation.json`, list in `/api/project`,
show in the 2D viewport, add tests for pass, fail and the browser view, and update
`docs/DASHBOARD.md` and `docs/CLI.md` in the same commit. Target: frontier node
`dry-vale-5761` (H2).

## Method

- **Engine** (`CadexStudio.py`): factored `_scene` and `_hero` out of `render_files`
  and added `hero(triangles, source, fit, inventory)`. It returns the same hero picture
  as `cadex render`, alone, as `(png, facts)`.
- **No rebuild** (`render.retained_snapshot`): ADR-457 bars evaluate from rebuilding.
  This function rebuilds the display block a rebuild reply carries
  (`cadexd._display_block`: `solved_placement_matrix` plus tessellation paths made
  absolute) from the retained `result.json`, then reads it with `STUDIO.snapshot`.
- **`evaluate.add_heroes`** draws both heroes on `pass` and neither otherwise. It also
  deletes a stale `hero.png` or `print-bed.png` before drawing. It writes the report's
  `heroes` block (`cadex-heroes-v1`): state ready, partial, failed or skipped, the
  revision, a file and facts per hero, and errors. Each hero stands alone: a design with
  no printed part gets the hero and an error for the bed.
- **`command_evaluate`** calls `add_heroes` after the film, on `--film-only` too. The
  fit comes from `read_fit`. The inventory is the one the film already read, passed
  through `inventory_summary`, so it is not read a second time.
- **History**: the evaluation's `.gitignore` now lists the two heroes beside the film
  patterns (`film.write_ignore`).
- **Server and page**: each evaluation row carries `heroes`. `_film_files`, the
  allowlist, includes the files the report's `heroes` block names. `review.js` lists a
  pass's hero and print bed as images in the Evaluations group, ahead of its film.
- **Tests**:
  - `test_evaluate.py`, live engine: a pass makes both heroes of the evaluated revision,
    with both hand-modelled parts on one bed and no hardware. `--film none` still makes
    the heroes. A fail makes neither and removes a stale hero, and `--film-only` on a
    fail keeps it that way. A unit test pins the prose line on the report's block and on
    the envelope's view; that envelope case is the crash the live run found.
  - `test_review_evaluation.py`: the row's `heroes`; allowlist serving, including a 404
    for a hero file that the failing report does not name; and a Chromium test showing
    a pass's hero and print bed before its film, each loading.
  - The existing `--film none` assertion now globs `seed-*.png`, because its claim is
    about the film. A new assertion checks that the heroes are present.

## Result

- **H2 now meets its criterion as implemented.** A passing evaluation makes both heroes
  and a failing one makes neither. Both are listed in `/api/project` and appear in the
  2D viewport.
- **Measured** on the scratch copy `~/cadex-projects/orun4-biped-sts`, running
  `./cadex evaluate --film-only` on its passing evaluation `14b7223ee485-235b65eba72d`
  (55 drawn objects, 259,437 triangles):
  - retained snapshot 0.8 s, hero 5.8 s, print bed 5.9 s, fit and inventory read 5.5 s
    (which included a second inventory read, since removed);
  - heroes state `ready`: 10 printed parts on 2 beds, hardware listed;
  - `print-bed.png` is **byte-identical** (`cmp`) to `docs/probes/orun4/h2-print-bed.png`,
    which unit 1 drew from a rebuild snapshot. The retained-geometry path and the rebuild
    path therefore agree.
- **Example committed**: `docs/probes/orun4/h2-hero.png` (178 KB), the passing biped on
  the dark floor in the H1 font.
- **That live run found a bug, now fixed and tested**: `human_lines` crashed on the
  envelope's path-form `heroes`.
- **Gates, all at `b422aa5b`'s tree:**
  - `pixi run build-engine` exit 0;
  - `pixi run test-engine` 2611 passed, 58 skipped;
  - CLI suite in thirds with the GPU hidden: 400 passed; 356 passed, 1 skipped;
    443 passed.
- **Not run**: the packaged lifecycle gate. The protocol and `OP_ARG_SPECS` are
  unchanged. The payload change is only the studio module the CLI loads by path.
- **Concerns**:
  - A hero that cannot be drawn is reported in the block and the notes but does not
    change the exit code. This is a choice: a design made only of purchased parts
    legitimately has no print bed.
  - ADR-570 names the scratch copy `orun4-biped-sts` as measurement provenance, as
    ADR-569 did. No guidance, test or default names it.
- **Tail**: two unreconciled records (`noble-vale-4742` and this one).
- **Next**: H3, the shove video, filmed from the passing policy with the H1 font
  through `film.py` and `video.py`.

Dispatch closed: 1 unit — H2 unit 2: a passed evaluation draws hero + print bed from retained geometry, listed in /api/project and the 2D viewport (ADR-570)

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/orun4
- commit: b422aa5b01f35ca37de1027d6a5a0f6d313e7184

## State Impact

- target: dry-vale-5761 — H2 implemented: a passing cadex evaluate draws hero.png and print-bed.png from the retained accepted geometry (no rebuild) beside evaluation.json, a failing one draws neither and removes stale ones; listed per evaluation in /api/project, served by allowlist, shown in the 2D viewport before the film (ADR-570, b422aa5b); print bed byte-identical to the rebuild-path example
