# ot7 regression receipt — F9

Verified against source: 2026-09-20. [Cadex-new]

**F9 has its required evidence:** both suites are green, the relevant packaged
gate is green, all three retained ot6 designs restore and reopen with accepted
identity preserved, and every difference from the ot6 fit probes is explained.
This receipt consolidates completed checks; no audit or design turn was repeated
to write it. The human owns the charter checkbox.

| Gate | Existing result | Evidence, including log paths and SHA-256 digests |
|---|---|---|
| Engine: `pixi run test-engine` | **2,195 passed, 53 skipped** (iteration 168, under ADR-393) | [Connector-sides record](../../../.hypergraph/graph/record/glad-chart-3979.md) |
| Build and stage: `pixi run build-engine`, `pixi run stage-engine` | Both exited 0 (iteration 168) | [Same record](../../../.hypergraph/graph/record/glad-chart-3979.md) |
| CLI: `pixi run python -m pytest cli/tests` | **849 passed, 1 skipped; 554.00 s** (iteration 169, this pass) | This receipt's [ADR-393 reach section](#adr-393s-historical-reach-on-the-three-retained-designs--none) |
| Packaged lifecycle gate | **23 passed** (iteration 168, under ADR-393) | [Connector-sides record](../../../.hypergraph/graph/record/glad-chart-3979.md) |
| Earlier checkpoint, superseded | engine 2,142 / 53, CLI 693 / 1, gate 18 passed | [Threshold-fix record](../../../.hypergraph/graph/record/hidden-lodge-4550.md), [runner validation](../../../.hypergraph/graph/record/peaceful-hill-3013.md), [restore receipt](retained/restore-open.json) |

The packaged command was `CADEX_ENGINE_ROOT=<payload> pixi run python -m pytest
src/Mod/cadex/cadex_tests/test_cadexd_lifecycle.py`. The payload was
`build/engine/cadex-engine-0.0.0-linux-x64`; its 56 top-level Python modules
matched source during the restore audit. The engine and packaged rows are
iteration 168's runs against the ADR-393 code these measurements exercise, not
re-run here; the CLI row is this pass's own run. Skips remain skips; this
receipt does not claim those cases ran.

| Retained design | Accepted revision prefix | Restore / reopen seconds | Pairs per open | Changed published / rebuilt pairs | Static failures |
|---|---|---:|---:|---:|---:|
| Finch | `b6862234` | 7.335 / 7.175 | 406 | 0 / 0 | 44 |
| Robin | `8d727e18` | 5.156 / 5.105 | 276 | 0 / 0 | 39 |
| Heron | `0c8c64c9` | 2.252 / 2.254 | 105 | 0 / 0 | 20 |

All six fresh-process opens reported `performed=true` and
`matches_accepted=true`. Accepted revision, digest, contract, attempt pointer,
parameters, script bytes and pinned result bytes were preserved. Only normal
restore metadata (`latest_candidate`, `updated_at`) changed. All 787 pairs
matched exactly in both published reads and newly rebuilt candidates, with no
missing or added pairs. The ot6 sources remained unchanged; checks used external
`ot7-open-*` copies. [The restore receipt](retained/restore-open.json) pins full
identities, replies, measurements, metadata and evidence digests.

The remaining static failures are expected under the new checker:

- **Finch — 44:** 12 screw overlaps explicitly allowed by ot6 (eight tab
  engagements at 4.07150 mm³, four centre engagements at 7.85398 mm³), 28
  undeclared zero-gap seatings and four designed 0.05 mm bearing-stub gaps.
- **Robin — 39:** eight insert/screw overlaps at 4.85222 mm³ allowed by ot6,
  29 undeclared zero-gap seatings and two designed 0.05 mm wheel/motor gaps.
- **Heron — 20:** six screw overlaps allowed by ot6 (four tab engagements at
  4.07150 mm³, two centre engagements at 9.42478 mm³) and 14 undeclared zero-gap
  seatings. The original comparison reported 22: ADR-353 removed only
  `comp_upper_arm` / `comp_bearing_shoulder` at 0.09999999999999952 mm and
  `comp_forearm` / `comp_bearing_elbow` at 0.09999999999999039 mm, both with zero
  common volume, using the absolute 1e-9 mm minimum-comparison allowance.

## ADR-393's historical reach on the three retained designs — none

ADR-393 fixed an engine defect that put a welded body at the **exact inverse**
of its parent-relative transform in the exported MJCF. It fires only on a weld
the script writes **hardware-first** — `joint("fixed", connector(part, ...),
connector(host, ...))` — because that is the order FreeCAD's
`ensureUnconnectedIsSecondRef` swaps. A defect in an engine that these three
accepted revisions are read back through has to be measured against them, not
argued about, so F9 owes this row.

**All three write their welds host-first, and all three are untouched.** Finch's
`purchase()` helper passes `connector(host, "origin")` first; Robin's
`fix_{name}` joints pass `chassis_conn()` first; Heron's `weld(hw, carrier, …)`
puts `connector(carrier, "origin")` first inside the joint despite naming the
hardware first in its own signature. So FreeCAD never swapped any of their 24,
21 and 12 fixed joints (of 28, 23 and 14 joints, the remainder being the four,
two and two revolutes), and the pre-fix worker read the right frame at the
right index by luck of the calling order.

Measured rather than read off the source, with
[`mjcf_agreement.py`](runner/mjcf_agreement.py) — the exported body tree
composed down to world and held against the `component_placements` the same
solve published, at 1e-4 mm and 1e-4°:

| Design | Bodies | Retained attempts measured | Disagreeing bodies | Worst error | Distinct model digests |
|---|---:|---:|---:|---:|---:|
| Finch | 29 | 4 | 0 | 0.0 mm, 0.0° | 1 (`4514e2fb…`) |
| Robin | 24 | 4 | 0 | 0.0 mm, 0.0° | 1 (`43660a9e…`) |
| Heron | 15 | 4 | 0 | 0.0 mm, 0.0° | 1 (`cc991b94…`) |

The four attempts per design are the ot6-era export, the two the ot7 restore
audit produced, and the rebuild taken for this section under the ADR-393
engine. **Each design's MJCF is byte-identical across all four**, so the fix
changed nothing these designs export, and the agreement holds exactly rather
than within tolerance.

The control is the design that found the defect: the same tool on
`ot7-plover-e`'s pre-fix model reports **24 of 29 bodies disagreeing, worst
`c_tabscrew_knee_l_0` at 121.86102740417053 mm and 179.99999879258172°** — the
number iteration 167 measured by other means, recomputed. A tool that returns
zero on three designs must be shown returning the right nonzero somewhere.

The probe's own arithmetic is pinned by
[`cli/tests/test_mjcf_agreement.py`](../../../cli/tests/test_mjcf_agreement.py):
four hand-written fixtures whose answers are stated in the file before they are
run — a matching body tree, the inverted-frame shape at its exact 28.284 mm and
180°, a body whose placement is missing (never a pass), and the tolerance
deciding a borderline body.

**The fit half, re-measured under the fixed engine.** Each `ot7-open-*` copy was
read twice in a fresh process: once from the published measurements, once
through `open_project`'s full restore pass, which re-runs the accepted script
and so exercises ADR-393's new refusal path.

| Design | Accepted revision | Pairs | Failing, published | Failing, after restore | Failing sets identical | Published read / restore |
|---|---|---:|---:|---:|---|---:|
| Finch | `b6862234` | 406 | 44 | 44 | yes | 0.149 s / 7.209 s |
| Robin | `8d727e18` | 276 | 39 | 39 | yes | 0.091 s / 5.341 s |
| Heron | `0c8c64c9` | 105 | 20 | 20 | yes | 0.070 s / 2.384 s |

Same counts as the table above, same accepted revisions, and pair-for-pair the
same failing sets between the published read and the rebuilt one. No joint was
refused at `stage: native_connector_frames`. The receipt is
[`retained/adr393-reach.json`](retained/adr393-reach.json).

**What this does not claim.** It is not a swept verdict and not a smoke result:
these revisions still publish no sweep, exactly as the sections above say. It
measures agreement between a model and its own solve, which is what ADR-393
broke — not whether these designs fit, which the 44/39/20 rows already answer.

The checker reports every overlap. It has exactly one implicit exception,
added after these numbers were taken: a pair welded by an **unsuppressed fixed
joint** is not held to the 0.1 mm undeclared-pair minimum (ADR-372), because a
fixed joint is the design saying the two components are one rigid body. That
exception cannot move a number above, and did not: a retained row is the
measurement the accepting engine published, it carries no intent, and reading
it back never recomputes one. These retained scripts declare no fit intent of
their own either.

**What the same measurements say under ADR-372's weld exemption**, with the
welds each script already declares — Finch's `purchase()` helper, Robin's
chassis welding everything but its two wheels, Heron's twelve `weld()` calls —
supplied as the `attached` intent the engine now implies for them:

| Design | Failing as retained | Cleared by the weld exemption | Would remain |
|---|---:|---:|---:|
| Finch | 44 | 16 | 28 |
| Robin | 39 | 11 | 28 |
| Heron | 20 | 8 | 12 |

Every cleared pair is a zero-volume gap under the default; no overlap is
silenced (12 / 8 / 6 intersections stand), and a pair that merely shares a host
with another — Finch's servo against the tab screws beside it, Robin's board
against its own inserts — is not welded to *it* and still fails, because
ADR-372 implies no transitivity through a common host. The [portable
regression](../../../cli/tests/test_retained_fit.py) computes both
columns from the retained receipts through `fit_summary`, so neither can drift
from the product without a red test. The [pair-by-pair explanation and
ot6 probe links](retained/README.md#f9-unchanged-retained-measurements-through-the-product-scope),
[original comparison](retained/comparison.json), and
[portable regression](../../../cli/tests/test_retained_fit.py) account for the
complete failing sets and exact numbers. The regression permits precisely the
two Heron threshold corrections and fails under the old threshold, as recorded
in [its validation](../../../.hypergraph/graph/record/keen-quill-2265.md).

**What that table models, and what it does not.** The two columns differ by
**ADR-372's weld exemption alone**. The second is the first recomputed by
`fit_summary` over the *same* retained rows, with the `attached` intent the
engine now implies supplied for the pairs each script already welds, and
nothing else varied. It is neither a re-measurement nor a rebuild, and it is
**not a fresh-build verdict** for these three designs: no retained project was
rebuilt or re-accepted to produce it, and the geometry behind both columns is
one retained measurement set. Four of the five checker changes that landed
after these designs were accepted are outside it, and stay outside it:

- **ADR-370's attachment block** is not modelled. It is reported, never
  failed, so it moves no count in either column — but a rebuild would publish
  it, and on these very rows it would have something to say. Of the welded
  pairs measured here (Finch 24, Robin 21, Heron 12), Finch's and Heron's all
  meet within the 0.001 mm tolerance, and **ten of Robin's do not**: its
  chassis stands 0.3 mm from each of its two motors and 0.6 mm from each of
  its eight board and clamp screws. The retained revisions predate the block
  and publish no `attachments` key at all, which reads `unavailable`, not
  empty, so no column here counts or shows that. Those counts are pinned by
  `test_welded_pairs_that_do_not_meet` in the same [portable
  regression](../../../cli/tests/test_retained_fit.py).
- **ADR-371's sweep-coverage rule** is not modelled, because there is nothing
  here for it to read: every retained receipt's `clearance_sweep` reads
  `unavailable`, with the reason *No published sweep for this accepted
  revision*, and missing coverage is never a pass. A rebuilt design's swept
  verdict is unknown from this table.
- **ADR-373** governs how far a declared clearance may be widened, and these
  three scripts declare no fit intent of their own.
- **ADR-374's swept roll-up** is outside it for the same reason ADR-371 is: it
  reads a joint row's minimum distance, maximum common volume and first
  contact over the pairs that joint moves, and there is no joint row here to
  read. Every retained receipt's `clearance_sweep` is `unavailable`, so
  `sweep_summary` returns no joint row, no `pairs_moving` and the verdict
  `unavailable` on all three designs — which is what
  `test_the_retained_receipts_publish_no_sweep_to_roll_up` in the same
  [portable regression](../../../cli/tests/test_retained_fit.py) pins. Neither
  column can move by it in any case: ADR-374 changes what a swept joint row
  rolls up and never a static row's status.

So read the third column as *what the weld exemption leaves standing on these
measurements*, not as what today's engine would say end to end about a fresh
build of Finch, Robin or Heron.

None of these three retained revisions has unknown measurements or world
geometry. Their swept reports remain unavailable. F9 requires compatibility
and explained comparisons; it does not require these old designs to pass fit
or acquire sweep declarations. Their 44/39/20 failures therefore do not keep F9
open. This corrects the closure interpretation in the current state projection;
the next authorized reconcile can fold that correction.

F4–F7 remain open. The retained final Heron above is distinct from F4's first
accepted seed. [Two provider refusals](retained/README.md#portable-regression-and-second-provider-refusal)
are not repair attempts with completed design turns. This receipt claims no
repair, new unassisted design, swept-fit pass or smoke pass, and does not close
the run or substitute for its eventual F10 report.

## The one project ADR-393 did shut: `ot7-plover-e` (ADR-395)

The section above measured ADR-393's reach on the three *retained ot6* designs
at zero. Its reach on the design that found the defect is not zero, and F9's
"existing projects keep opening" clause is what names it.

`ot7-plover-e` was accepted before the fix. Re-running its accepted script
through the fixed engine — the ordinary restore pass `open_project` performs on
every open — now produces a different project digest, so **the project refuses
to open**:

| What | Value |
|---|---|
| Restore | `CADEXD_RESTORE_FAILED`, 89.4 s |
| Accepted digest / restored | `a00d1aea…` / `9ef44502…` |
| Accepted geometry digest / restored | `a4c4cc28…` / `bb33c420…` |
| Geometry fallback (ADR-389) | `the rebuilt model is not the accepted one` |
| Outputs differing | **2 of 90** |

The two are `plover_model` (the MJCF, 16,519 → 16,521 bytes, `c4c47094…` →
`71b8b39c…`) and `plover_stand` (the training task, whose only two differing
fields are that MJCF's `sha256` and `bytes`). Every BREP artifact, every
canonical definition and every solved placement is identical, and two
independent rebuilds wrote the same model bytes, so this is not the
serialization noise ADR-389 was built for. Both the project digest and the
geometry digest include a non-BREP output's artifact bytes — `project_digest`'s
ADR-068 clause, and the `else` branch of `_entries` that the geometry digest
shares — so the fallback for *the same model serialized twice* has no answer for
*the same model exported better*.

This generalises: any project accepted before an engine change to a derived
artifact is shut the same way. Nothing else measured in this receipt moves —
the three ot6 copies open, restore and report their 406/44, 276/39 and 105/20
unchanged, because ADR-393 changes nothing they export. The immediate cost is
F7's: a design turn opens with `restore=True`, so its two unspent continuations
cannot be dispatched on this project until the digest question is answered.
Receipt: [`retained/plover-e-reexport.json`](retained/plover-e-reexport.json).

## Iteration 172 — the exception is closed: the geometry fallback stops reading derived bytes (ADR-396)

The row above is answered. `project_geometry_digest` no longer carries a
derived output's artifact bytes; `project_digest` still does and still refuses.
One keyword on the shared `_entries` is the whole diff.

**`ot7-plover-e` opens.** Measured first on the fresh copy
`ot7-plover-e-adr396`, then on the project itself:

| | before (ADR-395) | after (ADR-396) |
|---|---|---|
| `open_project(restore=True)` | `CADEXD_RESTORE_FAILED`, 89.4 s | **`ok: true`**, 89.5 s |
| `restore.matched_by` | — (refused) | `geometry` |
| Accepted digest / restored | `a00d1aea…` / `9ef44502…` | unchanged, still `a00d1aea…` / `9ef44502…` |
| Geometry digest, accepted / restored | `a4c4cc28…` / `bb33c420…` | `8c09313f…` / **`8c09313f…`** |
| Accepted pin preserved | yes | yes |
| Accepted revision | `0491ead7…` | `0491ead7…` |

The byte digests are the same numbers as before — the exporter fix still moves
them and the accepted-state guard still sees it. What changed is that the
second opinion now measures the model rather than the export, and the two sides
agree. The project learned `accepted_geometry` on that open, so the next reopen
needs no retained accepted attempt, and a second restore of the copy reproduced
`ok: true` at 89.3 s through the remembered value. No script, parameter or
accepted state moved; F7's `continue-2` and `continue-3` are spendable again.

**The three ot6 copies are unmoved**, re-measured under the ADR-396 engine with
`cadex clearance` before and after a full `open_project` restore:

| Design | Accepted revision | Pairs | Failing | clear / intersection / below | Restore |
|---|---|---:|---:|---|---|
| Finch | `b6862234` | 406 | 44 | 362 / 12 / 32 | byte match, 7.387 s |
| Robin | `8d727e18` | 276 | 39 | 237 / 8 / 31 | byte match, 5.249 s |
| Heron | `0c8c64c9` | 105 | 20 | 85 / 6 / 14 | byte match, 2.410 s |

Same counts and same breakdowns as every previous reading, accepted pins
preserved, and each `docs/clearance.md` **byte-identical** before and after its
restore. All three still match on bytes alone, so the geometry fallback is not
even consulted for them — which is the point: this change can only be reached
by a project the byte digest has already refused.

Suites: `pixi run test-engine` **2196 passed, 53 skipped in 295.61 s** (2195
before, plus this unit's fixture); packaged gate
`CADEX_ENGINE_ROOT=build/engine/cadex-engine-0.0.0-linux-x64 pytest
test_cadexd_lifecycle.py` **23 passed in 18.19 s** on a freshly staged payload;
`pixi run python -m pytest cli/tests` **855 passed, 1 skipped in 551.66 s**,
unchanged, since this unit touches no CLI code.
Receipt: [`retained/adr396-reopen.json`](retained/adr396-reopen.json).
