---
node_id: 46266e35-0af6-583a-bae5-d0045b9c027e
slug: rough-ridge-4729
title: 'G6: ot8''s closing report, and the column that keeps a finished experiment from reading as a success'
created_at: '2026-09-21T02:23:34+00:00'
parents:
- hidden-delta-8675
summary: ''
---
## What

G6, the ot8 charter's last criterion: `docs/probes/ot8/REPORT.md`, the closing
report that carries every outcome of this run, plus `cli/tests/test_ot8_report.py`
holding it in shape and ADR-403 recording what it does and does not claim.
Commit `340b2334`.

The report has one row per **experiment** — frozen prompts with digests, turns
that reached the model, model, continuations used, accepted identity, static
fit per turn, final static and swept checks, smoke, inventory, actor edits,
remaining defects and the ot7 comparison — an explicit slot ledger, the single
call that was not an attempt, a G1–G5 evidence table linking every receipt by
path, and a closing section that claims done without ticking an owner box.

## Why

The critic named G6 as the next and last unit and listed four non-negotiables.
I did all four, and nothing beyond them.

## Method

Read the five retained receipts rather than restating anything from memory:
`g1-window-probe.json`, `g2-heron-create.json`, `g3-plover-rebuild.json`,
`g4-robin-diagnosis.json`, `g5-retention.json`. Mirrored
`docs/probes/ot7/REPORT.md`'s section shape so the sibling test could mirror
`test_ot7_report.py`.

**The critic's four, each discharged:**

1. **Success bars kept visually separate from the control-blocked outcome.**
   ot8's per-experiment table opens with an **Outcome** column ot7's did not
   have. G2 and G3 read `**success — every bar met**`; G4 reads
   `**control-blocked — not a design success**` and its Smoke cell still reads
   `**fail**`. A section above the table ("Achieved success bars, and the
   outcome that is not one") states the rule, and the sentence *"A finished
   experiment is not a design success."* is in the report and asserted by the
   test. Without the Outcome column G4's row — turns 0, static pass, swept
   pass — would read as a third success beside two real ones.
2. **The slot ledger is explicit**: a table of dispatches / completed / void /
   interrupted / unreached / continuations, with a totals row. G2 = 1 void
   (five-hour session limit on `ot8-heron`, ADR-355, no slot) + 1 completed
   create on `ot8-heron-b`; G3 = 1 completed rebuild; G4 = 0 dispatched.
   Totals: 3 dispatches, 2 slots spent, 1 void, 0 interrupted, 0 unreached,
   **9 of 9 continuations unspent**.
3. **G2's remaining defects stated against ot7's four modified parts**: "none
   against the bar", with the comparison cell naming that `ot7-heron-c`'s pin
   carries no `servo` row and no `servo_horn` row at all and lists
   `servo_shoulder_solid`, `servo_elbow_solid`, `horn_shoulder_solid`,
   `horn_elbow_solid` among its uncatalogued sources.
4. **ot8 distinguished from ot7, G1–G5 linked by path.** A bolded paragraph
   says ot8 does not re-run ot7, that ot7's slots stay spent and receipts
   unedited, and that the three ot7 projects were read read-only and hashed
   before and after. The evidence table links all five receipts, the contract,
   the prompts, `balance_diagnosis.py`, the four ADRs and six record nodes.

**The test.** `cli/tests/test_ot8_report.py`, eleven tests: the six sections
and a verified date with no private address or hostname; the per-experiment
table's fifteen columns and every row's values, with each prompt digest
recomputed from the frozen file; the "finished experiment is not a design
success" assertion (exactly two `**success` outcomes, exactly one
`**fail**` smoke, the balancer's outcome string exact); G2's remaining-defects
wording; the ledger's per-row and totals values; the one-row non-attempt list
with its receipt resolving; a G1–G5 row per criterion each carrying a link;
the open-items list and the done claim; the ot8/ot7 distinction; every
relative link, same-file anchor, record slug and ADR resolving; and the G5
suite numbers. **All eleven fail with the report absent** (verified by moving
it aside), which is the state at `a51169cc`.

Suites, run rather than reasoned about: `pixi run python -m pytest cli/tests`
**914 passed, 1 skipped** (903 + the 11 new); `pixi run test-engine` **2196
passed, 53 skipped**. No engine, CLI or shell source changed, so the packaged
gate is not owed again — G5 took it at `39e02390` and the only commits since
add docs, a test and this record.

## Result

**G6 is met in its artifacts and its tests, and G1–G6 all have evidence now.**
The run's measured shape, as the report states it: three dispatches, two
reached the model and ended on their own, one void; two of three bars met on
the initial prompt with zero actor design edits anywhere; the third
control-blocked with its missing control contract written down rather than
guessed at again.

For the next iteration:

- **The unreconciled tail is three nodes** — `stormy-sand-3570`,
  `hidden-delta-8675` and this one — and is at the charter's threshold. A
  reconcile pass is due and it is not mine to run.
- **Done is claimed in the report**, under the exhaustion policy. The owner
  owns the G1–G6 checkboxes and none was ticked. Two consecutive critic
  acceptances stop the run.
- **Nothing in the report claims the balancer succeeded**, and the test is
  what keeps that true if the report is ever edited: it asserts exactly two
  success rows and that G4's smoke cell reads `**fail**`.
- No new dependency; docs, one test file and one ADR.
- Assumption taken, reversible: the report cites six record slugs rather than
  ot7's fifteen, because ot8 is five units long. The test's floor is six.

Dispatch closed: 1 unit — G6 written: ot8's closing report carries one row per
experiment, an explicit slot ledger, every non-attempt and the G1–G5 evidence,
with G4's control-blocked outcome held apart from two met bars by a test.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot8
- commit: 340b2334b169a34c5f915ba745e5adfcf8e39f98

## State Impact

- target: smooth-vine-2389 — G6 is met in its artifacts and its tests; what remains is the owner's tick and the critic's acceptance. docs/probes/ot8/REPORT.md (commit 340b2334, ADR-403) carries one row per experiment with frozen prompts and digests, turns, model, continuations used, accepted identity, static fit per turn, final static and swept checks, smoke, inventory, actor edits, remaining defects and the ot7 comparison; an Outcome column ot7's table did not have, reading **success — every bar met** for G2 and G3 and **control-blocked — not a design success** for G4 whose smoke cell still reads **fail**; an explicit slot ledger totalling three dispatches, two slots spent, one void under ADR-355, zero interrupted, zero unreached and nine of nine continuations unspent; the one call that was not an attempt with its receipt; a G1-G5 evidence table linking all five retained receipts, the contract, the prompts, balance_diagnosis.py, four ADRs and six record nodes by path; and a closing section that claims done without ticking an owner box. cli/tests/test_ot8_report.py, the sibling of test_ot7_report.py, pins all of it in eleven tests including that exactly two rows read as a success -- all eleven fail with the report absent. cli/tests 914 passed 1 skipped; test-engine 2196 passed 53 skipped.
- target: ancient-vine-9908 — Every ot8 criterion now has a record with measured evidence: G1 the frozen contract, G2 the arm's met bar, G3 the biped's met bar, G4 the control-blocked diagnosis, G5 the green regression floor and G6 the closing report. Done is claimed in docs/probes/ot8/REPORT.md under the charter's exhaustion policy, with no owner checkbox ticked.
