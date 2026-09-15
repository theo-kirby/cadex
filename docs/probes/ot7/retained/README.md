# Retained designs: repair refusal and checker comparison

Verified against source: 2026-09-15. [Cadex-new]

Current F9 assessment: [the regression receipt](../REGRESSION.md) consolidates
the green gates, six preserved opens and explained fit differences, completing
F9's evidence. The sections below retain each experiment's findings and the
gaps that were open at that point.

F4 did not run a design turn: the provider refused the frozen prompt at its
session limit. The critic's fallback advanced F9 instead: the product checker
reads all three retained ot6 designs, and every reported distance and common
volume equals the retained assembly measurements. **Their fit verdicts fail.**
The ot6 probes accepted specific mechanical contacts and thread engagements;
the product checker has no such exceptions without script declarations, and
reports every overlap regardless of intent.

## F4: the single frozen call

[repair-refusal.json](repair-refusal.json) preserves the seed identity, prompt
hash, transcript hashes, timing and post-call fit report. The fresh project
`cadex-projects/ot7-heron-repair` was extracted verbatim from ot6-heron's first
project commit `14bc75f…`, with accepted revision `7e9eff5c4ff2…`. Later correction
commits and conversations were not copied. No script, parameter or acceptance
edit was made by the actor. The call used `claude-fable-5`, without `--resume`:

```bash
./cadex --project "$PROJECTS/ot7-heron-repair" --model claude-fable-5 \
  --json -p "$(cat docs/probes/ot7/prompts/repair.prompt.txt)"
```

There was one invocation, zero completed design turns and no additional prompt.
It exited 1 after **4.090 s** with “You've hit your session limit”. The transcript
is retained at `evidence/turn1.transcript.jsonl` in that project. No model repair,
training or smoke run occurred. This is a provider refusal, not evidence that
the model tried and failed to repair the mechanism.

The seed's original artifact directory was no longer present in ot6-heron.
Before the call, both static and swept reads failed with “The accepted attempt
directory is missing.” During the normal product call, restore rebuilt the
current seed script, verified the same accepted digest, and replaced the attempt
pointer. Revision, accepted digest and script bytes stayed identical. This was
normal product restore during the requested turn, not an actor re-acceptance or
a historical-run rendering. The receipt names both attempt pointers. The
post-call measurements are **newly restored measurements**, not recovered ot6
artifact bytes; no before-fit report is invented.

The restored seed reports **105 pairs, 21 failures**: 8 intersections,
12 below-clearance pairs and one world-geometry failure. Both servo/cheek
intersections measure **248.20162986795 mm³**; `comp_base` carries the forbidden
collision plane. Both child/horn gaps are **0.2 mm**, but these are *not*
failures without declared contact: 0.2 exceeds the default 0.1 mm minimum.
Swept coverage is unavailable because this script declares no sweep step.
These limitations remain visible to a future repair turn; F4 is open.

## F4: the call that reached the model (iteration 44)

[repair-timeout-b.json](repair-timeout-b.json) is the first F4 call a model
saw. `ot7-heron-repair-b` is a fresh copy of the seed above (its `evidence/`,
`agent.json` and CLI lock excluded), validated by the runner against the
original receipt's script hash, accepted revision, digest and empty
overrides. The guarded before-read reproduced the retained baseline: 105
pairs, 15 failures, both horn attachments at 0.2 mm, the 248.2 mm³
servo/cheek overlap and the plane on `comp_base`.

The model read clearance, script and API for the whole 30-minute bound, hit
the provider's 64,000-token output cap on one thinking-only message, and was
killed by the runner at 1,800.0 s without calling submit. Script hash,
accepted revision and the 15-failure report are identical after the call.
The runner's own stream capture was lost to the kill; the provider stream
was recovered unmodified from the harness session store and its digest is in
the receipt. This is a measured result and not a void call: no limit
appeared. **Decision #44** (the critic, iteration 44) ruled it an
**interrupted execution**: it did not end on its own, so it is not a turn,
it consumed no frozen-prompt slot, and it is recorded apart from
provider-limit void calls. The receipt's `slot_consumed: true`,
`slots_spent: 1` and `continuations_used: 1` are the collector's historical
output under the timeout rule of that day, kept as written; its `ruling`
field carries the decision. Under the corrected collector (ADR-356), which
returns the slot on a runner-bound kill and writes the stream frame by frame,
the repair prompt and all three continuations are unspent, and the retry is
the same frozen prompt on the next fresh seed copy, `ot7-heron-repair-c`,
dispatched only while the product agent is available.

## F9: unchanged retained measurements through the product scope

[comparison.json](comparison.json) contains every failing pair by name and its
numbers, plus project and artifact digests. The copies are
`ot7-retained-finch`, `ot7-retained-robin` and `ot7-retained-heron`, outside the
checkout. Only each current script, metadata and pinned accepted attempt were
copied. The external reproducible probe is
`ot7-retained-fit/evidence/compare.py` (digest in the receipt): it opens via
`open_project(..., restore=False)`, reads all pages of `inspect scope=clearance`,
calls the product's `fit_summary` and `write_clearance`, and asserts exact
pair-table equality against the source attempt. It asserts source and copy
script, metadata and result hashes stay unchanged. No design is rebuilt.

| Copy | Revision prefix | Pairs | Intersections | Below clearance | Unknown | Total failing |
|---|---|---:|---:|---:|---:|---:|
| Finch | b6862234 | 406 | 12 | 32 | 0 | 44 |
| Robin | 8d727e18 | 276 | 8 | 31 | 0 | 39 |
| Heron | 0c8c64c9 | 105 | 6 | 16 | 0 | 22 |

Every difference from the ot6 fit probes is accounted for below; none changes
a measured solid or excuses a product failure. The comparison uses the current
retained revisions, including later policy declarations, not the older revision
identities in the initial ot6 fit receipts. Geometric relationships agree with
[Finch's probe](../../ot6/finch/fit_check.py),
[Robin's corrected-bore probe](../../ot6/robin/fit_check.py), and
[Heron's probe](../../ot6/heron/fit_check.py).

- **Finch:** 12 overlaps are the eight tab screw engagements at 4.07150 mm³
  and four centre screw engagements at 7.85398 mm³ that ot6 explicitly allowed.
  Of 32 below-clearance pairs, 28 are zero-gap seatings (per joint: parent/servo,
  parent/bearing, child/horn, child/centre screw, servo/horn, and servo/two tab
  screws); four are the designed 0.05 mm bearing-stub gaps. All lack fit intent.
- **Robin:** eight overlaps are insert/screw engagements at 4.85222 mm³ that
  ot6 explicitly allowed. Of 31 below-clearance pairs, two are 0.05 mm wheel/motor
  bore gaps. The 29 zero-gap seatings are chassis/two clamps/board (3),
  chassis/eight inserts (8), two motor/clamp pairs (2), and each of eight
  inserts and screws against its mounting clamp or board (16). The ot6 probe
  checks precisely those seatings and gaps; the script declares no fit intent.
- **Heron:** six overlaps are four tab screws at 4.07150 mm³ and two centre
  screws at 9.42478 mm³. Fourteen zero-gap seatings follow Finch's seven-per-joint
  pattern. Two more failures are bearing-stub gaps of
  **0.09999999999999952 and 0.09999999999999039 mm**: ot6's tolerance accepts the
  intended 0.1 mm, while the product's strict `< 0.1` comparison flags them.
  This is a measured threshold-rounding problem, left unchanged in this
  experiment, not a physical clearance defect newly discovered.

All three retained swept reports say unavailable. Opening their retained
clearance scopes proves these artifacts remain readable; it does not prove
fresh-process rebuilds or sweeps pass. No world geometry is reported on these
three current revisions. The missing horns' contact declarations on the older
F4 seed are a separate coverage limitation described above.

## Verification and remaining work

The external probe's exact pair-table and unchanged-file assertions passed on
all three copies. JSON receipts parse and remain below the 16 KB cap. This unit
changes evidence and documentation only: no build, product-code change, new
dependency, suite rerun or packaged-gate run. The preceding F8 suite results
remain the last full regression evidence; this pass does not claim F9 complete.
F4 still needs a product-agent repair when the provider is available; the
threshold-rounding finding is a concrete follow-up for the checker. No retry
was made after the refusal, and no design was edited to improve these scores.

## Threshold correction (ADR-353)

The follow-up checker fix uses an absolute 1e-9 mm allowance for declared and
undeclared minimum comparisons. Re-evaluating the exact same retained
`*.clearance.json` inputs with the corrected `fit_summary` gives Finch **44**,
Robin **39**, and Heron **20** failures. The only removed findings are
`comp_upper_arm` / `comp_bearing_shoulder` at 0.09999999999999952 mm and
`comp_forearm` / `comp_bearing_elbow` at 0.09999999999999039 mm, both with zero
common volume. No measurement, source design or original receipt was changed.
All three designs still fail; swept coverage remains unavailable. The F4
provider refusal above remains zero completed design turns, not a repair result.

## Portable regression and second provider refusal

Iteration 19 resumed the same frozen repair prompt in a fresh session, as the
critic requested. [The second receipt](repair-refusal-iteration19.json) records
another session-limit refusal after **4.020 s**, with zero completed design
turns. Before and after reads both report **15 failures** (8 intersections,
6 below-clearance pairs, 1 world plane). ADR-353 removes six nominal 0.1 mm
findings from the older seed's 21: two bearing gaps and four servo/tab-screw
gaps. No geometry changed. Script, accepted revision, digest and accepted
attempt remain unchanged; normal product restore updates `latest_candidate`
and `updated_at`. The transcript and full before/after reports are retained
under `ot7-heron-repair/evidence/iteration19/`, with hashes in the receipt.
F4 remains open; there was no repeated retry within this dispatch.

The fallback now has a portable regression in
`cli/tests/test_retained_fit.py`. The three `*.measurements.json` files here
encode **all 787 retained pairs** as component indices, distance and common
volume, preserving the source numbers without rounding. Each cites the digest
of the full original clearance report and is below 16 KB. They retain revision,
world-geometry and sweep availability metadata. These are measurement fixtures,
not substitutes for rebuilding the solids or proving that restore works.

The test replays the actual product `fit_summary`, compares every failing pair
and number against the original comparison receipt, and permits exactly the
two explained Heron boundary corrections. It also checks the thread-engagement
volumes, seating counts and designed 0.05 mm gaps against the explanation above.
Expected totals remain **44 / 39 / 20**, with all sweeps unavailable. Restoring
the old strict threshold in memory makes the Heron case fail on those two
extra named pairs. F9's retained classification is now pinned; its broader
restore/build evidence remains open.

Validation for this regression unit: full CLI suite **684 passed, 1 skipped**
in 530.16 s; focused replay **3 passed**. The deliberate old-threshold replay
fails as expected. Log digests are in the second refusal receipt. No engine,
protocol or payload implementation changed, so no full build or packaged gate
was rerun.

## Packaged restore and reopen (iteration 20)

[restore-open.json](restore-open.json) records two fresh packaged-engine opens
with `restore=True` for each of `ot7-open-finch`, `ot7-open-robin` and
`ot7-open-heron`. These new copies contain the retained script, metadata,
accepted attempt and policy assets. Source projects remained read-only. The
engine’s 56 top-level Python modules match the source tree; the receipt pins
its manifest and executable hashes separately. No build was needed.

| Design | Restore / reopen seconds | Pairs per open | Published / rebuilt pair differences | Fit failures |
|---|---:|---:|---:|---:|
| Finch | 7.335 / 7.175 | 406 | 0 / 0 | 44 |
| Robin | 5.156 / 5.105 | 276 | 0 / 0 | 39 |
| Heron | 2.252 / 2.254 | 105 | 0 / 0 | 20 |

All six replies report `performed=true` and `matches_accepted=true`. Each
accepted revision, digest, contract and attempt pointer remains unchanged,
as do script bytes, parameter values and the pinned accepted result. Only
`latest_candidate` and `updated_at` change during normal restore. The probe
also hashes every source asset and artifact before and after: none changed.
No design, parameter or accepted state was edited, and no explicit acceptance
operation was issued.

The public clearance scope reads the pinned accepted artifact. To avoid
mistaking that read for rebuild evidence, the probe separately compares every
pair in each **new restore candidate's result.json** with the portable fixture.
Both the published reports and all six newly rebuilt pair tables match exactly:
no changed distance, common volume, missing pair or added pair. The restored
digests match the accepted digests. The only fit-classification differences
from ot6 remain the previously explained contact/thread policies and ADR-353's
two Heron threshold corrections. No new defect was found to require a regression.
All designs still fail static fit, have no reported world geometry, and have
unavailable sweep coverage; successful restoration is not a fit pass.

The reproducible probes, full replies, metadata snapshots, pair comparisons and
fit reports live under `cadex-projects/ot7-retained-open/evidence/`; their
relative paths and SHA-256 digests are in the receipt. This closes F9's retained
restore/open evidence. Full-suite evidence remains the preceding engine
**2,142 passed / 53 skipped** and CLI **684 passed / 1 skipped** runs; this
experiment changes documentation only and does not claim new full-suite runs.
The current packaged lifecycle gate was rerun: **18 passed in 11.52 s**;
its command and log digest are in the receipt.
