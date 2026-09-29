---
node_id: 85cb5b37-bca4-5443-bf7e-77a803a623fa
slug: late-glacier-7593
title: ot10 A5 hexapod attempt 2 launched detached on ot10-hexapod-2 at 6dd4ce81; aborted quadruped-1 turn is not an attempt
created_at: '2026-09-27T21:05:54+00:00'
parents:
- strong-summit-4135
summary: ''
---
## What
Launch receipt for A5 hexapod attempt 2 (`ot10-hexapod-2`), committed to `docs/probes/ot10/README.md`. The same section records an aborted quadruped turn (`ot10-quadruped-1`) as a harness stop, not an attempt.

## Why
Target: A5 (`loyal-fountain-8709`). The critic asked for a committed launch receipt, a detached turn, and then an end to the iteration. When this iteration started, the hexapod-2 turn was already running. An earlier session had started it at 2026-09-27T21:01:51Z and never recorded it. So I did not launch a second turn on the same frozen prompt, because that would have produced two attempts. I committed the receipt for the running turn instead. Everything else follows the critic's message.

## Method
- Checked the live process table.
  - PID 3606231 is `python -m cadex_cli --project ~/cadex-projects/ot10-hexapod-2 --model claude-opus-5-5 -p "<frozen hexapod prompt, verbatim>" --json`.
  - Its environment has `CADEX_EFFORT=medium`. Its parent is PID 1, in its own session, so it outlives the iteration.
  - stdout and stderr go to `~/cadex-projects/ot10-notes/hexapod-2/turn.{json,stderr}`, outside git.
  - The `started` file names revision 6dd4ce81, which is after the ADR-418 pin.
- Found `ot10-quadruped-1`, started at 20:49:25Z. Its turn.err stops at 16:57 local (8 min in) with three probe scripts and no design, and its process is gone. It was killed along with an undetached session.
- Wrote the receipt section. Ran `cli/tests/test_ot10_contract.py` and `test_part_sharp_edges.py`, which read that README: 14 passed.

## Result
- Hexapod attempt 2 is in flight. Attempt 1 took about 56 min, so expect it to finish around 22:00Z.
- `~/cadex-projects/ot10-notes/hexapod-2/pipeline.sh`, left by the earlier session, repeats attempt 1's render, look and judge steps. It does not run P1–P3 or the swept fit.
- Next iteration, once PID 3606231 has exited:
  - read turn.json;
  - run pipeline.sh, then measure P1–P3 and the swept fit;
  - count the A4 refusal classes;
  - publish the images and score.
  - If the turn is still running, do not start another one.
- `ot10-quadruped-1` is a burned name, kept as it is. The quadruped attempt goes on a new project (e.g. `ot10-quadruped-2`), detached with nohup/setsid.
- Assumption: a turn that was killed with no ending and no design is a harness stop under the question policy, not an A5 attempt.
- The tail is now 1 unreconciled record.

Dispatch closed: 1 unit — A5 hexapod attempt 2 launch receipt committed (turn already running detached); aborted quadruped-1 turn recorded as not an attempt

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot10
- commit: 6dd4ce811de6f313f9b6086989e5bf6caceb055f

## State Impact

- target: loyal-fountain-8709 — hexapod attempt 2 running detached on ot10-hexapod-2 since 2026-09-27T21:01:51Z at 6dd4ce81 (after ADR-418); ot10-quadruped-1 was killed 8 min in with no design, recorded as a harness stop, not an attempt
