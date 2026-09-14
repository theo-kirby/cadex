# Retained designs: repair refusal and checker comparison

Verified against source: 2026-09-14. [Cadex-new]

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
