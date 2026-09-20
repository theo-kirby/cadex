---
node_id: 750d60da-fcd4-5e00-a67b-2bdb36be8719
slug: sleepy-ridge-6259
title: A geometry digest unshuts the projects part.offset locked (ADR-389)
created_at: '2026-09-19T19:52:20+00:00'
parents:
- cool-grotto-2512
summary: ''
---
## What

`compute_project_digest` identified a BREP output by its exported bytes, and
`part.offset` — OCCT's `BRepOffset_MakeOffset` — does not write the same bytes
twice for an identical solid. Every `open_project` re-runs the accepted script
and asserts digest equality, so **any accepted design using `part.offset`
could never be reopened**. Robin was shut by exactly this, which is why F6's
frozen continuation never reached the model.

Landed as one change (ADR-389, commit `ece37fa6`):

1. **The byte digest is untouched.** `cadex-project-digest-v1` is every stored
   `accepted_digest` on disk. Its material moved to a new `CadexGeometryDigest`
   so `cadexd` can build the same entries without importing the sandboxed
   worker, and a frozen fixture pins the result bit-for-bit against the
   implementation it replaced (measured equal before the move).

2. **`cadex-project-geometry-digest-v1`**, the same entries with a BREP output
   identified by its canonical definition *plus* what the kernel measures on
   the shape: counts, the exact vertex set, the exact edge-length and
   face-area multisets, bounds, total area. Nothing rounded (ADR-016's rule).
   **Volume excluded by name** — measured over four processes, every other
   quantity was bit-identical and the volume moved in its last two digits.
   Carrying the definition is what keeps this from being a weaker guard: a
   hand-edited script fails on the recipe before the geometry is consulted.

3. **Consulted only on a mismatch.** `open_project` re-measures the two
   retained attempts and opens when they agree, adding `matched_by:
   "geometry"` and `geometry_digest` to `restore`. A byte-for-byte match
   reports neither, so the ordinary reply and its golden are unchanged.
   Missing evidence never means agreement — a gone staging directory, an
   unreadable result or a kernel that will not read an artifact back each
   refuse and say which.

4. **The project remembers**, as `accepted_geometry` =
   `{accepted_digest, geometry_digest}`. Without that the fix had a fuse:
   `prune_artifacts` keeps three attempts and pins whatever `accepted_attempt`
   says *during the rerun*, which is the candidate — so a sixth reopen would
   shut a project the fifth one opened. Keyed to the accepted digest because
   `rebuild` and `write_script` both re-accept, and a measurement of the
   previous design would refuse the current one.

## Why

The critic named this unit: the `part.offset` rebuild-digest break on
`forest-wind-0342`, the local refusal that made F6's `continue-1` unreached
(`terse-dew-6200`) and left Robin unopenable. It is the highest-ranked
unblocked frontier item and the only thing standing between F6 and its three
unspent continuations.

The critic also said not to collect `ot7-plover-d` while it runs, and to
collect it when the child exits. **No `ot7-plover-d` file was touched.** Its
runner process is no longer alive (`ps` shows no `run.py` and no plover
child), so collection is now available — but that is a second unit and this
dispatch had a budget of one. It is the obvious next unit.

## Method

Diagnosis first, because the prior record recorded one dead end (face-sorted
canonicalization) and I needed to know which routes were actually open.

- **A pure-text canonicalization of the BREP file is out.** Three exports of
  one offset solid differ in the *order* of the 2D-curve and surface tables,
  in the order of the topology section that indexes into them, and in a
  written tolerance (`1e-06` vs `1e-07`); sizes differ (2552 / 2549 / 2549
  bytes). Sorting records cannot survive the index remapping. Measured, not
  argued.
- **The kernel's own measurements are bit-stable.** Four processes, same
  offset solid: the sorted vertex set, edge-length multiset, face-area
  multiset, counts, bounding box and total area were identical every time;
  the volume was not (`557.0428410647723` vs `…725`). That is the fingerprint,
  and that is why volume is excluded.
- **Confirmed on the real project.** Robin's two retained attempts, 24 BREP
  outputs each: **bytes differ on exactly `wheel_l` and `wheel_r`; the
  geometry fingerprint and the canonical definition differ on none.**

Then the implementation, then verification:

- `test_geometry_digest.py`, 19 tests: order-insensitivity, four ways the
  fingerprint must move, the **frozen byte digest** guarding the refactor, the
  drift case, the changed-recipe refusal, non-BREP sensitivity, the four
  refusals, and the staleness rule.
- Two real-kernel tests in `test_cadexd_lifecycle.py`, **both failing on the
  old `cadexd`** (verified by checking it out and re-running). The first
  reopens an offset project **five** times so `ATTEMPT_KEEP` really collects
  the accepted attempt — it asserts that directory is gone — and requires at
  least one reopen to have drifted, so if OCCT ever becomes reproducible the
  test says so loudly.
- `pixi run test-engine` **2190 passed, 53 skipped**. `cli/tests` **842
  passed, 1 skipped**. Packaged gate against a freshly built and staged
  payload: **23 passed**; `CadexGeometryDigest.py` is in the payload via
  `CMakeLists.txt`.
- End to end: a copy of `ot7-robin-c` fails to export before the change
  (exit 1, the same six-second refusal) and exports three times in a row
  after it.

`docs/INTEGRATION.md`, `docs/ARCHITECTURE.md` and `docs/probes/ot7/
DIGEST-DRIFT.md` moved with the code; the protocol's `restore` contract gained
two optional keys. The shell copies `restore` wholesale and needed no change.
No design was edited by the actor (`actor_design_edits: 0`).

## Result

**`forest-wind-0342` is no longer broken on this count, and F6 is no longer
blocked.** Robin's `ot7-robin-c` opens; its create turn and three unspent
continuations stand; the same frozen `continue-1` prompt can now be sent in
the same project.

Two things the next iteration must know:

- **`ot7-plover-d`'s runner is dead.** No `run.py` and no plover child is
  alive. Nothing in this iteration read or wrote any file under it. Collecting
  it through `run.py`, classifying by the receipt's own 3600 s bound and
  recording F7's outcome is the next unit, unless the critic prefers F6's
  continuation now that it is unblocked.
- **A rebuild re-accepts, and for a byte-unstable project that means
  `accepted_digest` moves each time.** This is `rebuild`'s pre-existing
  contract (`cadex export` issues one), invisible until now because a stable
  project re-accepts to the same value. The remembered measurement follows the
  new accepted digest, the geometry digest itself stayed constant across three
  Robin exports, and the project opened every time — but a receipt that quotes
  `accepted_digest` for such a project is quoting the last rebuild, not a
  fixed identity.
- `cadex_rebuild.py`'s determinism audit (`digest_matches_accepted`, exit 2)
  was deliberately left alone: it is a diagnostic, not a gate that shuts a
  project, and a drifted byte digest genuinely is non-reproducible bytes.
- No new dependency. The unreconciled tail is 1 node after this one.

Dispatch closed: 1 unit — the `part.offset` rebuild-digest break is fixed by a
geometry digest consulted only when the bytes disagree; Robin opens again,
every suite and the packaged gate are green, and F6 is unblocked.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot7
- commit: ece37fa665d65118987ae2e1f7b37c7019f5b9c1

## State Impact

- target: forest-wind-0342 — the part.offset rebuild-digest break is fixed (ADR-389, commit ece37fa6): the byte digest is unchanged and frozen-fixture pinned through the move of its material to CadexGeometryDigest, and open_project now falls back to cadex-project-geometry-digest-v1 (definition + exact vertex set, edge-length and face-area multisets, counts, bounds, area; volume excluded as measured-unstable) when the bytes disagree, opening with matched_by: geometry. Missing evidence still refuses; a changed recipe still refuses; the project remembers the measurement keyed to its accepted digest so pruning and later re-accepts cannot strand it.
- target: narrow-dune-9454 — F6 is unblocked: ot7-robin-c opens again (a copy exported three times in a row where it refused before), so the frozen continue-1 prompt can be sent in the same project with all three continuations still unspent.
