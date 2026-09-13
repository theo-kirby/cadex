---
node_id: ea05de6d-e99b-5b9b-ae3d-e01f0b496676
slug: red-jasper-1884
title: 'Complete Wren''s product-agent revision: retrain the agent''s 90 mm foot and compare it on the declared seeds'
created_at: '2026-09-13T03:38:41+00:00'
parents:
- kind-oak-1484
summary: ''
---
## What

Wren's product-agent revision step (D9) is complete on the working copy `ot5-wren-copy54`, and iteration 65's unrecorded changes are recorded here.

**Iteration 65 (commit `2fae1cf7`), which its own record `kind-oak-1484` did not cover:** it added `docs/probes/wren-fresh/report_revision.py` (a receipt assembler over retained `compare.py` evaluations that first re-hashes a pre-revision inventory) and gave `train.py` an optional `AUTHORED_BY` argument recorded in `run.json` and each playback review, replacing the hard-coded 85 mm default assertion with a `policy_on == 0` check. It also ran a real `cadex -p` design turn on the copy (`evidence/agentrev65/`): the agent inspected the script three times and called `set_params` once, and the engine accepted `foot_len=90`, `policy_on=0` as revision `03077ee9eb82…`, digest `4d327bf8081a…`. The turn was cut off after acceptance — `stdout.json` is empty, the transcript ends at "Accepted. Let me verify the foot geometry landed correctly." — so no `DECISION:` reached the project. Its verification limit: the helper was never executed against real artifacts, and no suite log exists for that iteration.

**This iteration:**
- One bounded turn finished the agent's own design turn (`evidence/agentrev66/`): given what it had accepted, the stored `claude-sonnet-5` preference made six `inspect` calls, confirmed revision, parameters and the 90×40×8 mm feet, deliberately changed nothing, and returned `DECISION:` and `NOTE design-specs:`. The CLI landed them as project ADR-002 and `docs/design-specs.md`, exiting 3 (`ok: false`, no script accepted this turn — the CLI's ordinary no-acceptance outcome, not a refusal). The hypothesis is the agent's: reward and fall-avoidance rose monotonically with foot length while frames showed standing, so 90 mm pulls back from a possible standing exploit at the cost of 105 mm's verified fall reduction.
- The unchanged bounded experiment retrained the design as `wren66` at the agent's revision: 240 updates, 1024 envs, seed 0, checkpoints every 20, `timeout 1800`, `MemoryMax=20G`; exit 0 in 700.402 s; host peak 7,402,741,760 bytes sampled; GPU peak 15,120 MiB. Checkpoint 20 was published while training was active (trainer 18→34 across the browser check, witness 3.39e-08, render 12.68 s; iteration medians 1.431/1.338/1.276 s before/during/after); the final policy's video verified (witness 9.63e-08, 81 frames, 8.0 s). The observer saw seven consecutive committed iterations reach the persistent page within 1.25 s each.
- `compare.py` evaluated the copy's three retained policies on seeds 0–4, eight seconds, 50 Hz, each from its own retained script/model/task/policy in a fresh scratch project; `report_revision.py` assembled `docs/probes/wren-fresh/revision66-evidence.json` after re-hashing all 465 pre-revision run/asset files (all match). `wren57-retry` (110 mm): mean X +40.137 mm, 0/5 falls, reward 214.882. `wren66-checkpoint20` (90 mm): +42.724 mm, 0/5, 213.622. `wren66-final` (90 mm): +55.147 mm (min +51.392), 0/5, 144.877. All fifteen episodes ran 400 steps.
- Two helper fixes found by executing them: `compare.py` reads the script the run record names (`artifacts.script`), since the in-place published retry keeps its training script beside `playback-script.py`; `report_revision.py` reads authorship from `training.requested.design_authored_by`, where the record actually stores it (`requested` at top level is null).
- Docs: new `REVISION66.md`; README, AGENT-REVISION.md, the operator-review README and `HEADLESS-BIPED-REVIEW.md` updated to the current run; ADR-308; the copy's PROGRESS.md gained the numbers. A new guard test in `cli/tests/test_wren_fresh_evidence.py` holds the receipt to the declared protocol, seeds, identities, authorship and browser selections.

## Why

The critic named two fixes: record iteration 65's real changes, and complete Wren's open D9 revision step through the product agent with one bounded retraining and a real comparison using the new helper. Both are done here in one unit. I completed the agent's cut-off turn rather than launching a fresh design turn because the accepted change already existed and was the agent's; asking it to endorse or replace its own acceptance keeps authorship honest and avoids training an unchanged design under a new authorship claim. Assumption: the iteration-65 transcript (`evidence/agentrev65/stderr.log`) is an accurate account of that turn's tool calls; it is retained project-local.

## Method

Commands, in order (all from the checkout; `URL=http://$(tailscale ip -4):8765/`, `P=$HOME/cadex-projects/ot5-wren-copy54`):

```
timeout --signal=TERM --kill-after=10s 900 ./cadex --project "$P" --out "$P/evidence/agentrev66/output" --json -p "$(cat "$P/evidence/agentrev66/prompt.txt")"
PYTHONPATH=cli:cli/tests pixi run python docs/probes/wren-fresh/train.py "$P" wren66 "$URL" "product-agent-authored revision: foot_len 110->90 mm accepted by the agent in iteration 65 (revision 03077ee9eb82), rationale returned in iteration 66 as project ADR-002"
pixi run python docs/probes/wren-fresh/compare.py "$P" "$HOME/cadex-projects/ot5-wren-eval66-{retry,c66,f66}" {wren57-retry,wren66-checkpoint20,wren66-final}   # three concurrent scratch projects
cp -R <scratch>/evidence "$P/evidence/comparison66/<x>/"
pixi run python docs/probes/wren-fresh/report_revision.py "$P" "$P/evidence/agentrev65/before.json" "$P"/evidence/comparison66/{retry,c66,f66} > docs/probes/wren-fresh/revision66-evidence.json
PYTHONPATH=cli:cli/tests pixi run python docs/probes/wren-fresh/current.py "$URL" "$P" wren66-final completion66
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 pixi run python -m pytest cli/tests -q      # 410 passed, 1 skipped, 386.00 s
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 pixi run test-engine                        # 2110 passed, 53 skipped, 253.65 s
```

Both suites ran after the GPU experiment and evaluations, so no CPU test trainer overlapped training. Suite logs are retained in `$P/evidence/agentrev66/`. The checkpoint and final browser screenshots were inspected: the persistent page shows the 90 mm model and the videos in the delivered common style. `git diff --check` passes. No build was needed; no product code under `cli/cadex_cli` or the engine changed.

## Result

True now: the persistent private port 8765 serves `ot5-wren-copy54`, 15 runs, and a fresh visit selects `wren66-final` (playback revision `de9692bd4ee5…`, 90 mm feet, 240 telemetry points, playable/downloadable video); `wren66-checkpoint20` and `wren57-retry` are HISTORICAL and return-to-current works; the service was never restarted and no trainer is running. Wren has a product-agent-authored, documented revision that was retrained once and compared with its 110 mm baseline on the declared seeds, with both designs' policies, videos and identities retained. The 90 mm final moves the torso further on every seed and earns markedly less reward than the 110 mm retry; nothing here is a gait or causal claim (one training seed per design, standing/shuffling poses).

Concerns: the design turn's CLI exit is 3 because the agent (correctly) accepted nothing new — a turn that reviews and endorses the current design has no success exit code, which a future unit may want to make explicit. In the final playback's telemetry the checkpoint files are labelled `missing` because they live under `runs/wren66/train`, not the playback run; the label is accurate but could point at the training run. The three evaluations ran concurrently; each seed-0 trace still reproduced its retained trace exactly. Same-machine private-address evidence only; no second-device test. No new dependency. The unreconciled tail is now two records (this one and `kind-oak-1484`).

Dispatch closed: 1 unit — Wren's product-agent revision (110→90 mm) authored, retrained as wren66 and compared with the 110 mm retry on seeds 0–4; persistent port 8765 selects wren66-final; iteration 65's changes recorded

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot5
- commit: 2fae1cf719443443db9665046d1ec4e9ecdbc69f

## State Impact

- target: silent-river-6649 — Wren's D9 product-agent revision step is complete: the agent's own foot_len 110→90 mm acceptance (revision 03077ee9eb82) has its rationale as project ADR-002, was retrained once as wren66 (240 updates, exit 0, checkpoint and final videos verified) and compared with the 110 mm wren57-retry on seeds 0–4: all three policies survive 5/5, mean X +40.1/+42.7/+55.1 mm, reward 214.9/213.6/144.9; not a gait claim
- target: deep-clover-6012 — persistent port 8765 now defaults to wren66-final (playback revision de9692bd4ee5, 90 mm feet) on ot5-wren-copy54, 15 runs, verified at experiment start (RUN wren66 during training) and completion, without a restart
- target: sharp-union-6036 — after the agent's design change and retraining, all 465 pre-revision run/asset files match their inventory and wren57-retry, wren66-checkpoint20 and wren66-final each evaluate from their own retained model/task/policy
- target: crisp-sun-1239 — iteration 65's real changes (report_revision.py, train.py AUTHORED_BY, the cut-off agent turn that accepted 90 mm) are recorded; the Wren product-agent authorship gap is closed; compare.py and report_revision.py fixed by executing them against real artifacts
