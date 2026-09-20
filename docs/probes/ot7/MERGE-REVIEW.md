# ot7 merge review

Verified against source: 2026-09-20. [Cadex-new]

Reviewed the final ot7 product diff against main, concentrating on accepted
state and artifact retention, geometry digest fallback, native connector
frames, fit intent and sweep coverage, CLI replies, retained-artifact smoke
and operator project selection. Checked the critic history against later
fixes; ADR-380 withdraws the rejected weld/clearance rule and ADR-382 corrects
the provenance overclaim. No inherited Blender source changed.

## Finding and correction

**Blocking, fixed in `775974f9` (ADR-398):** restore's provisional acceptance
pruned the original accepted artifacts before rolling its locator back.
Repeated geometry-fallback opens could say success while leaving a dangling
accepted-artifact pin. The offset lifecycle test previously required this
deletion instead of detecting it.

The corrected regression failed before the fix. Restore now defers collection
until the accepted pin is settled. Five fresh-process opens retain every
accepted file byte-for-byte; five refused changed-script opens retain the
accepted pin and result. Normal acceptance collection remains bounded.
Existing projects whose artifacts were already deleted still need explicit
reacceptance to replace them; review did not modify any design project.

No other merge blocker was identified in this review. This is not a claim
that the statistical BREP fingerprint is a complete geometric equivalence
proof, or that sampled motion checks prove continuous collision freedom.
The declared step, coverage and artifact identity remain part of each result.

## Verification

| Check | Result |
|---|---|
| `OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 pixi run test-engine` | 2196 passed, 53 skipped; 296.01 s |
| `pixi run python -m pytest cli/tests` | 861 passed, 1 skipped; 606.77 s |
| `pixi run build-engine` | passed |
| `pixi run stage-engine` | passed |
| Packaged `test_cadexd_lifecycle.py`, `CADEX_ENGINE_ROOT` set to the staged payload | 23 passed; 22.47 s |
| `pixi run python tools/operator_review_selftest.py` | 1 passed |
| Hypergraph export/check with repository config | 0 violations, 0 warnings |
| `git diff --check` | passed |

The initial engine run overlapped the corrected retention assertion and
failed that test; the final full run above supersedes it. The initial payload
check also failed the offset retention path; the rebuilt payload passes.
Skipped cases were not claimed as exercised. No shell code changed, so no
GUI gate was run on this Linux host.

## Outcome and next scope

Merge with a merge commit so record-cited commit identities survive. ot7
completed a bounded experiment, not every design success bar. The repair
reached passing reported fit partly by declaring a clearance; the arm still
modified purchased servos/horns, the balancer toppled without feedback, and
the biped smoke used re-exported rather than accepted artifacts. Preserve
those outcomes and all original projects.

The next bounded follow-up should measure purchased-part identity on the
arm, smoke the biped's actual accepted export, and classify the balancer's
control requirement without weakening its checks or silently adding training.
