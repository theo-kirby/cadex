---
node_id: 0dcba915-4c83-5832-8a3f-316e4ab4d247
slug: southern-quartz-3293
title: 'ot11 P4: the product agent runs the loop on a copy of Robin -- one pre-registered run, 10 of 10 seeds pass the frozen balance spec; a tool call may block 900 s'
created_at: '2026-09-30T17:29:21+00:00'
parents:
- chilly-arrow-2197
summary: ''
---
## What

The first real-model use of the ot11 training loop (ADR-464), on balance,
as the critic named it. Commit `0ffc6569`.

- **How long one tool call may block, measured first.**
  `docs/probes/ot11/runner/block_probe.py` (new) runs one `claude -p` call,
  with `cadex -p`'s flags and `claude-opus-5-5`, against a
  standard-library MCP tool that sleeps. A 900 s call (`train_status`'s
  ceiling) blocked 900.1 s and returned with no error. The 5 s control
  returned in 5.1 s. Receipts: `retained/p4-block-probe-{900s,5s}.json`.
- **`ot11-robin-1`**, a copy of `ot9-robin`. `ot9-robin` is untouched, and
  its baseline `ef71f370…` stays in the copy's store, undeclared.
- **`docs/probes/ot11/runner/rounds.py`** (new, names no behaviour). It
  runs a frozen first prompt, then a frozen `--resume` continuation while
  the project's `loop-ledger.jsonl` shows neither a pass nor four evaluated
  runs. It writes every stream frame as it arrives, runs detached
  (`setsid`), and reads tool timings back.
- **Frozen prompts**: `prompts/balance.loop.prompt.txt` and
  `prompts/continue.loop.prompt.txt`. Their digests are in
  `retained/p4-robin-1-registration.json`.
- **One round, and it passed.** The agent rewrote `balance_task`
  (observations, reward, terminations, training shoves). It wrote the
  frozen spec byte for byte, which a diff after the turn confirmed. It
  registered `bal-1`: 650 it × 1024 envs, seed 7, a 900 s budget, and a
  reason citing the baseline's B3/B4/B5 measurements. The run ended
  `budget_exhausted` at iteration 400, after 900.6 s of GPU. The agent
  stored and declared the iteration-400 checkpoint `8919a22d…` and called
  `evaluate`: **pass, 10 of 10 seeds**, none void. Worst seed per
  predicate: B2 11.5° (limit 30), B3 0.92 COM heights (limit 2.0), B4
  0.97° (limit 20), B5 0.42 s (limit 2.0). B1: all ten ran the full 10 s.
- **Published**: the seed-1101 filmstrips
  (`docs/probes/ot11/p4-robin-1-bal-1-seed-1101-{overview,detail}.png`,
  124 KB and 182 KB) and the round receipt
  (`retained/p4-robin-1-rounds.json`: ledger, registration, ending,
  per-seed rows and tool timings, with no transcript and no machine path).
- **Docs**: a new section in `docs/probes/ot11/README.md`, a follow-up
  paragraph in ADR-464, and the Limits line in `docs/CLI.md`.
- **Tests**: `cli/tests/test_ot11_rounds.py` (new, 5 tests). The stop
  rule, including that a pass followed by a fail is not over. Transcript
  tool timings. No behaviour words and the pinned model in the runner. The
  probe's MCP server. Retained registrations name prompts whose digests
  match the files on disk.

## Why

The critic's next unit: real-model rounds, balance first. It targets
`wild-harvest-4848` (P4) and serves `staid-tooth-3475` (R3).

**Deviation, stated again.** The critic asked for a housekeeping fold of
`rich-lantern-3026` and `chilly-arrow-2197` "where your standing rules
allow one". This dispatch's rules forbid reconcile in a work iteration with
no exceptions, so I skipped it, as the critic anticipated.

**Where the critic's ask was not fully met.** The critic asked for three or
more rounds. The frozen prompt's stop rule ("stop when an evaluation passes
on all ten seeds") ended the session after round 1, because round 1
passed. I did not force further rounds: with no failed evaluation there is
no measurement to motivate a revision, and extra rounds after a pass would
be fishing.

## Method

1. Measured the block time first (critic's order). The 900 s probe ran in
   the background while the rest was set up.
2. Copied the project with `cp -a`.
3. Wrote the prompts. The prompt hands over the frozen spec as the
   xscript that `ot11-robin-negative` already carries under ADR-457 and
   ADR-458. It states the baseline's measured failure and the rules:
   budget ≤ 900 s, one run at a time, the training seed not an evaluation
   seed, a reason citing a measurement, diagnosis before the next run, and
   at most four runs. The prompt fixes no reward term, weight or setting.
4. Launched `rounds.py` under `setsid` at 16:45:33Z so the turns would
   outlive this session. The turn ended at about 17:10Z, the ledger showed
   a pass, and the driver stopped.
5. Checked the result:
   - diffed the spec against the frozen block (identical);
   - confirmed the policy reads only declared sensor channels (IMU on the
     board, encoders on the wheels; chassis pose, COM and torques are
     privileged);
   - confirmed the training seed 7 is not an evaluation seed;
   - looked at the seed-1101 detail sheet myself: the shove is visible at
     2.4 s and the robot is upright again by 2.6 s. This is not the blind
     judge.

## Result

**True now.**
- A real `claude-opus-5-5` product turn ran the whole loop through the
  ordinary product path in one turn: design task, pre-registered bounded
  train, `train_status` (4 calls, longest 618.6 s), store and declare,
  `evaluate` (189.8 s). The turn took 24.5 min, made 28 tool calls with
  none failing, and cost $2.80.
- Robin's new policy `8919a22d…` (on `ot11-robin-1`, accepted revision
  `cbf14e3c…`) passes the frozen balance spec on all ten evaluation
  seeds, with wide margins. The baseline wandered 16 COM heights and
  turned 131°. This one drifts at most 0.92 COM heights and turns under 1°.
- One tool call may block at least 900 s under Claude Code 2.1.285.
- Suites: `pixi run python -m pytest cli/tests`: 1251 passed, 1 skipped (1246 and 1 before; +5 from `test_ot11_rounds.py`). No engine, protocol or payload
  file changed, so `pixi run test-engine` and the packaged gate were not
  due and were not run.

**Not met, and not claimed.**
- **P4's three-round transcript requirement is still open.** Balance
  passed in round 1, so no revision happened. Reach (R2), which has goal
  sampling and is harder, is the natural place for motivated rounds.
- **R3 is not claimed.** These are training rounds. R3 needs a
  pre-registered confirmation evaluation at the final revision plus the
  blind judge's bar on seeds 1101, 1105 and 1110 (`runner/judge.py`).
- **Concern for R3: a sensor the mechanism does not carry.** The policy
  reads an IMU declared on the Pi Zero board's component, and the
  gearmotors are declared with encoders. No IMU part is modelled and the
  catalog gearmotor has no encoder. The agent reported this itself.
  ADR-408 accepted the declaration. Whether R3's "supported path, accepted
  design" wants these parts modelled is a question for the confirmation
  unit.

**Defect found (named, not fixed; one unit per iteration).** The ledger's
`evaluated.trained_by_run` matches only a run's final policy. `bal-1`
ended `budget_exhausted` with no final policy, and the agent evaluated its
checkpoint, so the ledger row carries `trained_by_run: []`. The
checkpoint's sha256 is in `runs/bal-1/train/progress.json`, so the fix is
to also match checkpoint digests in `bridge.py`'s `trained_by`. The
receipt makes the link by digest in the meantime.

**Other notes.**
- `bal-1` ran about 2.25 s per iteration (1204-step mean episodes), so
  650 iterations could not fit in 900 s.
- The 900 s budget ceiling is the prompt's number; the loop's own ceiling
  is 6 h.
- No new dependency.
- The unreconciled tail is now three records (`rich-lantern-3026`,
  `chilly-arrow-2197`, this one), which meets the pressure threshold: a
  reconcile is due.
- The transcript lives in `~/cadex-projects/ot11-notes/robin-1/`,
  uncommitted, as the charter requires.

Dispatch closed: 1 unit — the product agent ran the ot11 loop on a copy of Robin with claude-opus-5-5: one pre-registered 900 s run whose checkpoint passes the frozen balance spec on 10 of 10 seeds; a tool call may block 900 s; P4's three motivated rounds and R3's confirmation remain open.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot11
- commit: 0ffc6569df156e8a6a752666fb2d9d5ffe46c9b1

## State Impact

- target: wild-harvest-4848 — First real-model use of the loop (commit 0ffc6569): claude-opus-5-5 on ot11-robin-1 designed the task, wrote the frozen balance spec exactly, trained one pre-registered 900 s run and evaluated its iteration-400 checkpoint in one 24.5-min turn; a tool call was measured to block 900 s. The three motivated rounds are still unmet: the first evaluation passed, so nothing was revised. Defect: the ledger's trained_by_run leaves an evaluated checkpoint of a budget-exhausted run unlinked.
- target: staid-tooth-3475 — Training round, not a confirmation: Robin's new policy 8919a22d on ot11-robin-1 passes the frozen balance spec on 10 of 10 seeds (worst B2 11.5 deg, B3 0.92 COM heights, B4 0.97 deg, B5 0.42 s). R3 still needs a pre-registered confirmation evaluation and the blind judge's bar; the policy reads an IMU and wheel encoders declared on parts the mechanism does not model.
