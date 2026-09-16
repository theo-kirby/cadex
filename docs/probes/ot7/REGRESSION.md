# ot7 regression receipt — F9

Verified against source: 2026-09-16. [Cadex-new]

**F9 has its required evidence:** both suites are green, the relevant packaged
gate is green, all three retained ot6 designs restore and reopen with accepted
identity preserved, and every difference from the ot6 fit probes is explained.
This receipt consolidates completed checks; no audit or design turn was repeated
to write it. The human owns the charter checkbox.

| Gate | Existing result | Evidence, including log paths and SHA-256 digests |
|---|---|---|
| Engine: `pixi run test-engine` | 2,142 passed, 53 skipped; 315.52 s | [Threshold-fix record](../../../.hypergraph/graph/record/hidden-lodge-4550.md) |
| Build and stage: `pixi run build-engine`, `pixi run stage-engine` | Both exited 0; staged worker hash equals source | [Same build record](../../../.hypergraph/graph/record/hidden-lodge-4550.md) |
| Latest CLI: `pixi run python -m pytest cli/tests` | 693 passed, 1 skipped; 530.97 s | [Runner validation record](../../../.hypergraph/graph/record/peaceful-hill-3013.md) |
| Latest packaged lifecycle gate | 18 passed; 11.52 s | [Restore receipt](retained/restore-open.json), [restore record](../../../.hypergraph/graph/record/still-raven-7629.md) |

The packaged command was `CADEX_ENGINE_ROOT=<payload> pixi run python -m pytest
src/Mod/cadex/cadex_tests/test_cadexd_lifecycle.py`. The payload was
`build/engine/cadex-engine-0.0.0-linux-x64`; its 56 top-level Python modules
matched source during the restore audit. Later units added tests, documentation
and the experiment runner, without changing the engine or payload. The engine
and packaged results above are carried evidence, not newly run checks. Skips
remain skips; this receipt does not claim those cases ran.

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

The checker reports every overlap. It has exactly one implicit exception,
added after these numbers were taken: a pair welded by an **unsuppressed fixed
joint** is not held to the 0.1 mm undeclared-pair minimum (ADR-372), because a
fixed joint is the design saying the two components are one rigid body. That
exception cannot move a number above, and did not: a retained row is the
measurement the accepting engine published, it carries no intent, and reading
it back never recomputes one. These retained scripts declare no fit intent of
their own either.

**What the same measurements say under today's checker**, with the welds each
script already declares — Finch's `purchase()` helper, Robin's chassis welding
everything but its two wheels, Heron's twelve `weld()` calls — supplied as the
`attached` intent the engine now implies for them:

| Design | Failing as retained | Cleared by the weld exemption | Would remain |
|---|---:|---:|---:|
| Finch | 44 | 16 | 28 |
| Robin | 39 | 11 | 28 |
| Heron | 20 | 8 | 12 |

Every cleared pair is a zero-volume gap under the default; no overlap is
silenced (12 / 8 / 6 intersections stand), and a pair that merely shares a host
with another — Finch's servo against the tab screws beside it, Robin's board
against its own inserts — is not welded to *it* and still fails, because
ADR-372 implies no transitivity through a common host. These three rows are
not a re-measurement and not a rebuild: they are what a *new* design putting
the same solids in the same places would be told, and the gap between the two
columns is the four checker changes (ADR-370 – ADR-373) that landed after
these designs were accepted. The [portable
regression](../../../cli/tests/test_retained_fit.py) computes both
columns from the retained receipts through `fit_summary`, so neither can drift
from the product without a red test. The [pair-by-pair explanation and
ot6 probe links](retained/README.md#f9-unchanged-retained-measurements-through-the-product-scope),
[original comparison](retained/comparison.json), and
[portable regression](../../../cli/tests/test_retained_fit.py) account for the
complete failing sets and exact numbers. The regression permits precisely the
two Heron threshold corrections and fails under the old threshold, as recorded
in [its validation](../../../.hypergraph/graph/record/keen-quill-2265.md).

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
