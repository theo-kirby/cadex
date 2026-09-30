---
node_id: c96051cf-0c76-5f3b-ba41-4db543401b6e
slug: windy-nest-5080
title: ot11 R1 walk round 3 evaluated -- 0/10 on the pre-ADR-465 trainer; round 4 is the first on the fixed trainer; trainer_sha256 is hashed at save time (flagged)
created_at: '2026-09-30T23:58:51+00:00'
parents:
- long-badger-5117
summary: ''
---
## What
Published walk round 3 (`r3-nochatter`) on `ot11-quad-1`. The agent had
already evaluated it, and its best checkpoint `102133e9…` (iteration 788)
fails the frozen walk spec on 0 of 10 seeds. The receipt is
`docs/probes/ot11/retained/p4-quad-1-r3-evaluation.json`, and the seed-1101
filmstrip (overview and detail, dark floor) is in `docs/probes/ot11/`. The
new README section marks the round as trained on the pre-ADR-465 trainer.
Checking the trainer provenance of rounds 3 and 4 found a trainer defect:
`training.trainer_sha256` is computed at save time, not at start. Commit
`2a21210c`.

## Why
The critic's message: finish round 3 and publish it marked as old-trainer,
let the agent register round 4 on the fixed trainer, check round 4's
`trainer_sha256`, and record whether a new session is needed. R1 is the last
open behaviour. **Deviation:** round 4 was already registered by the agent
at 23:51:38Z, before this iteration. There was nothing to "let" happen, and
its reason cites round 3's measurements but **not ADR-465**. The session is
one continuous product turn, and its registered prompt never mentions
ADR-465 (0 hits in the transcript). I did not interrupt or re-prompt it,
because a killed job is an interruption, and changing a registered prompt
mid-session is not allowed. I also could not check round 4's digest
directly: its policy has not been saved yet, and the digest field turned
out to be untrustworthy (below). I established round 4's trainer from
timestamps instead.

## Method
- Read the loop ledger, `runs/r3-nochatter` (registration, progress, all
  eight checkpoints) and `evaluations/9f711fcaa419-102133e9310b`.
- Parsed each `.cxpolicy` header (CXPOLICY1 magic, 8-byte length, JSON) for
  `training.trainer_sha256`, and compared it with the sha256 of
  `training/cadex_train.py` at `b81dd2e1~1` (`8e06e1b0…`) and at
  `b81dd2e1`/HEAD (`abae5da0…`, identical to the working tree).
- Took file mtimes: the trainer was last written at 23:11:26Z. Took process
  and registration start times: r3 at 23:01:31Z, r4 at 23:51:38Z.
- Checked that the retained spec block is contained verbatim in script
  history 0027 (evaluated, `9f711fca…`) and 0029 (r4, `fbb2237e…`).
  0025→0027 differs only in the declared policy digest.
- Built the receipt in round 2's schema, plus a `trainer` block and
  `next_round.trainer_loaded`. Tray speed over the first 3 s came from the
  traces.
- Fixed the README's "started at 19:01Z", which was local time (23:01Z).
- `pytest cli/tests/test_ot11_{measure,contract,judge,rounds}.py
  test_review_evaluation.py`: 78 passed.

## Result
- **Round 3: 0 of 10 seeds, still backwards, and trained on the old
  trainer.**
  - Finished as budget_exhausted at 2,381 s, iteration 799. No final policy
    was written; the evaluated policy is `best` at iteration 788.
  - Training reward was +1.17 per step; on the evaluation seeds it was
    −3.10 to −2.37.
  - Failing predicates:
    - W3 on 10 seeds, −1.89 to −1.06, backing at 87–135 mm/s. It is already
      −55 to −137 mm/s over the first 3 s, before any shove.
    - W7 on 10, 0.63–0.73, worst on the rear feet.
    - W8-low on 10, 0.20–0.29.
    - W5-share, W9 and W10 on 10 each.
    - W6 on 9, W5-steps on 7, W4-heading on 5, and W1 and W4-lateral on 1
      each (1106 collapses at step 496).
  - The rear feet take 0–6 steps and drag. The knee joint-speed cost is still
    −0.65 per step.
- **Round 4 `r4-anglesonly` is the first walk round on the fixed trainer.**
  - Its process started 40 minutes after the fix was on disk.
  - Its change: gyro and joint-velocity observations become privileged, and
    hip and knee damping is randomised over 0.7–1.4×.
  - Settings: seed 31, 780 iterations, a 2,390 s budget, stop-on-collapse.
  - The spec block is unchanged.
  - It is the session's 4th and last run (`max_runs` 4). It was about 5
    minutes into training when this unit ended.
- **Broken (trainer): `training.trainer_sha256` is not evidence of the
  physics a policy trained on.** `cadex_train.py` hashes its file when it
  saves a policy (`hashlib.sha256(Path(__file__).read_bytes())` in the
  policy header).
  - In r3, checkpoints 000100 and 000200 record `8e06e1b0…`. Checkpoints
    000300–000700 and the evaluated `best` record `abae5da0…`, although the
    process ran the old code.
  - The fix is to hash once at import, with a regression test that rewrites
    the file between import and save. It must wait until r4 has ended:
    editing the trainer now would make r4's own final save record a wrong
    digest.
  - Next iteration: evaluate and publish round 4 when the session evaluates
    it, then land the digest fix (with an ADR line). The fix is a
    `training/` change, so test it from the venv and from pixi.
- **If round 4 fails, R1 needs a new pre-registered walk session.** Its
  prompt should state ADR-465, and that rounds 1–3's reward curves were
  MJX-only physics. The current session cannot give the agent that fact
  without changing its registered prompt, and it has no runs left after r4.
- Unreconciled tail: this is 1 record.

Dispatch closed: 1 unit — walk round 3 published as 0/10 on the pre-ADR-465 trainer; round 4 confirmed on the fixed trainer; the trainer_sha256 save-time-hash defect was found and flagged for the next iteration

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot11
- commit: 2a21210c828ce7cdeb8a97d8a0b7e962b121c504

## State Impact

- target: smooth-fountain-9832 — walk round 3 r3-nochatter (old trainer) fails 0/10, still backwards (W3 -1.89..-1.06); round 4 r4-anglesonly, the session's last run, is the first on the ADR-465 trainer; if it fails a new pre-registered walk session is needed
- target: late-pond-2851 — broken detail: a policy's training.trainer_sha256 is hashed when it is saved, not when the trainer starts, so r3's checkpoints after 23:11Z claim the fixed trainer; fix (hash at import + regression test) after r4 ends
