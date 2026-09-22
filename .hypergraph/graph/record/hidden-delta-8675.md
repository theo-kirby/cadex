---
node_id: b3c424b6-93c9-5fe4-acd1-beeda2a3297b
slug: hidden-delta-8675
title: 'G5: the regression floor measured green at the final revision'
created_at: '2026-09-21T02:03:21+00:00'
parents:
- stormy-sand-3570
summary: ''
---
## What

G5's regression floor, measured at the final revision and reported as it
reads. Nothing was fixed, because nothing was broken; the unit is the
measurement and its receipt.

Four verification runs against the freshly built and staged payload
(`build/engine/cadex-engine-0.0.0-linux-x64`, manifest `c6687a97…`, binary
`a5954c19…`, top-level Python source comparison `match` over 57 files):

- `pixi run python -m pytest src/Mod/cadex/cadex_tests` — **2196 passed, 53
  skipped**, 296 s, exit 0.
- `pixi run python -m pytest cli/tests` — **903 passed, 1 skipped**, 553 s,
  exit 0.
- `CADEX_ENGINE_ROOT=<payload> … test_cadexd_lifecycle.py` — **23 passed, 0
  skipped**, 19.6 s.
- `CADEX_ENGINE_ROOT=<payload> … test_licensing_compliance.py` — **11 passed,
  0 skipped**. Run because one of its tests *skips* without a payload, so the
  ordinary suite never audits the staged one.

And a retention probe over **five** designs — the three ot7 baselines this run
used (`ot7-heron-c`, `ot7-plover-e`, `ot7-robin-c`) and ot8's own two products
(`ot8-heron-b`, `ot8-plover`). Each was copied into a fresh `ot8-open-*`
project, restored, and then reopened in a second process: **ten phases, all
`ok`, all clean.**

Landed as `001981c8`: the receipt `docs/probes/ot8/retained/g5-retention.json`
(15,448 bytes) and the two README rows that index it. The fix to
`stormy-sand-3570`'s unreconciled-tail count the critic asked for landed first
and separately, as `39e02390`.

## Why

The critic named G5 as the next unit and said to run it rather than reason
about it, listing the exact commands. That is what was done, in that order,
with the build and stage first so the gate ran against a payload built from
this revision rather than a stale one. No deviation.

Two judgements inside the charter's question policy. **The probe stays
project-local**, at `<projects>/ot8-retained-open/evidence/restore.py`,
following ot7's `ot7-retained-open/evidence/restore.py` (ADR-394's run) rather
than G4's committed-tool precedent: it measures existing behaviour through
existing library functions and pins nothing a test does not already pin, so
committing it would add surface for no contract. **No ADR**: this unit changes
no direction and removes nothing; the record, the receipt and the README rows
are its log.

## Method

The probe copies only `script.py`, `script.json` and the **accepted attempt's**
staging directory — never `evidence/`, `agent.json` or the lock — into a
project that must not already exist, then opens it twice with `restore: True`,
reading `inspect scope=clearance` through the CLI's own `_read_path` and
`fit_summary` each time. Every source project is hashed whole before and after
and the run fails if one moved. Where ot7's probe asserted the restore agreed,
this one records the reply, so `ot7-plover-e`'s pre-ADR-396 accepted digest
would have been reported rather than crashing the probe.

| design | source | pairs | failing | restore | reopen |
|---|---|---|---|---|---|
| ot7 heron | `ot7-heron-c` | 105 | 0 | ok, 32.6 s | ok, 32.5 s |
| ot7 plover | `ot7-plover-e` | 406 | 0 | ok, 89.7 s | ok, 89.4 s |
| ot7 robin | `ot7-robin-c` | 378 | 0 | ok, 99.2 s | ok, 99.1 s |
| ot8 heron | `ot8-heron-b` | 105 | 0 | ok, 24.5 s | ok, 24.6 s |
| ot8 plover | `ot8-plover` | 406 | 0 | ok, 90.0 s | ok, 89.5 s |

For all five: `accepted_revision`, `accepted_digest` and `script_sha256` equal
the published pins (`baselines.json` for the ot7 three, the G2 and G3 receipts
for ot8's two); the accepted attempt's `result.json` is **byte-identical after
both opens**; and restore and reopen report the **same pair-for-pair
measurements**, zero differences, with every pair `clear`.

**Every measured difference, explained.** Exactly two metadata fields moved,
in all ten phases: `latest_candidate` and `updated_at`. Opening rebuilds from
the script and records the attempt it just made; `latest_candidate` names that
attempt and `updated_at` is its clock. No identity field moved —
`accepted_attempt`, `accepted_contract`, `accepted_digest`,
`accepted_revision`, `working_revision`, the param/mount/net/board/cage specs
and values, and the schema are all equal. There are no other differences.

The **ADR-398 repeated-restore retention regressions** are green and named:
`test_an_offset_project_reopens_although_its_bytes_never_repeat` and
`test_a_changed_script_is_still_refused_at_the_restore_pass`, both **PASSED**
(not skipped) inside the packaged gate, with the fixture half —
`test_geometry_digest.py`, 20 passed, 0 skipped — beside them. The probe is
that behaviour measured live: it is precisely the byte-identical accepted
`result.json` after a second open that ADR-398 bought.

Skips reported as skips. The engine suite's 53 are by design: 34 want the
offboard trainer's `jax`/`mjx` (ADR-084), 5 want a real
`CADEX_BLENDER_EXECUTABLE` sandbox, the rest are payload- or
environment-gated — and the one payload-gated licensing test was then run
*with* the payload and passed. The CLI suite's single skip is
`test_review_server.py:851`, which needs `CADEX_REVIEW_HOST`, the machine's
private-network address, which is never committed.

## Result

**G5 has its evidence, and the floor holds: no regression, no unexplained
difference, nothing red.** G1–G5 now all have measured evidence.

For the next iteration:

- **G6 is the next and last unit before reconcile**: `docs/probes/ot8/REPORT.md`,
  one row per experiment, written last. The five receipts it reads are
  `g1-window-probe.json`, `g2-heron-create.json`, `g3-plover-rebuild.json`,
  `g4-robin-diagnosis.json` and now `g5-retention.json`. It must keep G2's and
  G3's achieved success bars separate from G4's control-blocked outcome, and
  carry the slot ledger: G2 one void plus one completed create, G3 one
  completed rebuild, G4 **nothing dispatched**.
- The verification was taken at `39e02390`; the only commit after it in this
  unit (`001981c8`) adds `docs/probes/ot8/**` and nothing else, so the suites
  and the gate still stand at HEAD. The doc-reading tests
  (`test_ot8_prompts`, `test_ot8_runner`, `test_project_docs`,
  `test_ot7_report`, `test_lifecycle_report`, `test_balance_diagnosis`) were
  re-run after the README edits: 91 passed. A G6 commit that adds
  `REPORT.md` is in the same class and needs the same re-run, not a full
  rebuild.
- Five new external projects exist, `ot8-open-{ot7,ot8}-*`, each a copy that
  has now been opened twice. They are the probe's working copies and are not
  designs; nothing should dispatch into one. The ot7 baselines and ot8's own
  projects are unchanged and were verified so.
- No new dependency. No code changed, so no regression test was owed; the
  probe pins nothing a suite does not already pin, which is why it is not
  committed.
- One unreconciled record before this one (`stormy-sand-3570`); two after it.
  The tail is thin.

Dispatch closed: 1 unit — G5 measured green at the final revision: both
suites, the packaged gate and licensing audit, and ten clean restore/reopen
phases over five copied designs with every difference explained.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot8
- commit: 001981c8d69d9683ffb27f051f98be65b01a7b2a

## State Impact

- target: lucid-flame-4255 — G5 has its evidence and is met pending the owner's tick: at the freshly staged payload the engine suite is 2196 passed/53 skipped, the CLI suite 903 passed/1 skipped, the packaged lifecycle gate 23 passed/0 skipped and the packaged licensing audit 11 passed; the ADR-398 repeated-restore retention regressions are named and PASSED inside that gate, with test_geometry_digest.py 20 passed/0 skipped beside them; and an independent copy of all five designs this run used (ot7-heron-c, ot7-plover-e, ot7-robin-c, ot8-heron-b, ot8-plover) was restored and reopened in a second process, ten phases all ok, every accepted pin and accepted result.json byte-identical, every clearance pair equal restore-to-reopen and equal to what was published, with the only measured difference being latest_candidate and updated_at — the attempt each open records and its clock. Sources hashed before and after; none moved. Receipt docs/probes/ot8/retained/g5-retention.json, commit 001981c8 [rec: hidden-delta-8675]
- target: ancient-vine-9908 — G1-G5 all have measured evidence now; only G6, the closing report, remains before reconcile
