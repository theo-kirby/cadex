# Fresh Wren reopen and persistent review

Verified against source: 2026-09-12. [Cadex-new]

The corrected iteration 46 probe passes on `ot5-wren`, accepted revision
`5309bebc6597…`, digest `dbd02d7c12a0…`. The persistent private-network
port 8765 now serves Wren and stays running. A same-machine headless Chromium
visit loaded in 0.84 s, drew eight components (seven biped solids plus ground), showed twelve parameter defaults,
orbited and zoomed through real pointer input, and kept ACCEPTED NOW with zero
runs after polling. This is no second-device or training/video claim.

[evidence.json](evidence.json) is the compact receipt. Screenshots remain in
`ot5-wren/evidence/lifecycle46/`, with hashes in the receipt. Two engine
processes restored accepted identity on a disposable full copy. The served
project's 66 files were unchanged, excluding only this invocation's evidence
directory and `.git`. Earlier evidence directories are included. Both Reed
inventories matched (582 and 1017 files). Those snapshots were taken during
iteration 46 before the successful probe, after the server switch; they do
not establish isolation during Wren's earlier creation.

Run from the checkout, with pre-recorded SHA-256 inventories for Reed:

```bash
PYTHONPATH=cli:cli/tests pixi run python docs/probes/wren-fresh/lifecycle.py \
  "http://$(tailscale ip -4):8765/" "$HOME/cadex-projects/ot5-wren" lifecycle46 \
  --intact "$HOME/cadex-projects/ot5-biped=/tmp/ot5-biped-iteration46.json" \
  --intact "$HOME/cadex-projects/ot5-biped-copy29=/tmp/ot5-biped-copy29-iteration46.json"
```

The previous iteration committed the probe and receipt tests without a receipt
or record. Its product-agent creation reached an accepted script but the CLI
exited 1 on a provider session limit; project decision completion and training
are not claimed. This unit supplies the missing causal handoff.

The requested evidence-directory exclusion exposed additional faulty probe
assumptions: the endpoint is `/api/project`, and empty parameter overrides mean
values are shown in the declared-default column. Engine restore also rewrites
attempt metadata and replaces artifacts, dropping retained tessellation. Early
failed runs exercised that on Wren. An explicit public `rebuild` with standard
display regenerated the view; accepted revision and digest were asserted
unchanged. Copy-based reopens now avoid modifying served inputs. Thus this
receipt proves copy reopen plus read-only browser preservation, **not in-place
restore preservation**; the lost-tessellation behavior remains a demonstrated
D6 concern for the next unit. No product code or dependency changed.

The screenshot was inspected: the eight solids include Wren's modeled ground
plate, so the predecessor test's expected count of seven was wrong. This is
not a new D11 similarity assessment. The inventory regression also changes
an earlier evidence file and verifies it is still detected; generating this
invocation's screenshot alone does not change the inventory.


## In-place restore preservation (iteration 48, ADR-303)

The demonstrated restore loss above is fixed at acceptance: identical
revision/digest replays without a display request keep the existing accepted
attempt and its pruning pin. No post-restore rebuild is needed. The earlier
iteration 46 receipt remains historical; [restore-evidence.json](restore-evidence.json)
records the new in-place evidence. Wren was restored through two fresh engine
processes, preserving accepted revision, digest, contract, artifact locator and
all 28 retained attempt files byte-for-byte. Then the existing browser probe
loaded the persistent private URL in 1.19 seconds, drew eight solids, showed
12 defaults, exercised pointer orbit/zoom and kept the accepted view on polling.
Screenshots and full receipts live under Wren's evidence/restore48 and
evidence/restore48-browser directories. This is a same-machine private-network
check, with no training or second-device claim.

```bash
PYTHONPATH=cli pixi run python docs/probes/wren-fresh/restore.py \
  "$HOME/cadex-projects/ot5-wren" restore48
PYTHONPATH=cli:cli/tests pixi run python docs/probes/wren-fresh/lifecycle.py \
  "http://$(tailscale ip -4):8765/" "$HOME/cadex-projects/ot5-wren" restore48-browser
```

The real-engine regression creates and restores a disposable accepted project
in place twice, checks its stored mesh/sidecar and every retained byte, and
fails on the previous code's changed accepted_attempt. The source unit cases
also verify replacement on explicit display, changed revision/digest or absent
retained result, and verify that pruning keeps the preserved attempt.


## First bounded Wren GPU experiment (iteration 49)

The experiment uses the accepted Wren design with `policy_on=0`, without
changing its dimensions or using another project's policy. The public CLI
exports Wren's model/task and retains the training model before starting the
existing offboard GPU environment. Intermediate and final policies pass the
engine witness check before rollout. Their model XML and task bundle must
match the original training input byte-for-byte.

Run once with a new run name (an existing output directory is refused):

```bash
PYTHONPATH=cli:cli/tests pixi run python docs/probes/wren-fresh/train.py \
  "$HOME/cadex-projects/ot5-wren" wren1 "http://$(tailscale ip -4):8765/"
```

This runs 240 PPO iterations with 1024 environments, seed 0 and checkpoints
every 20 iterations, under `timeout --signal=TERM --kill-after=20s 1800`
and a systemd scope with `MemoryMax=20G` (21,474,836,480 bytes of host memory).
GPU memory is sampled separately. The existing offboard venv is used; no
new dependency is installed. `observe.py` checks fresh-visit current selection,
retained model identity, orbit/zoom and multiple real telemetry updates on the
persistent private URL. `check_video.py` decodes all frames and checks browser
playback, playback preservation across polling and downloaded bytes.
Neither browser probe starts or stops the persistent server. Render failures
are recorded separately and leave training under its own timeout.

Keep the entire project, including `runs/wren1*`, assets and evidence files.
The training script and configuration, task/model bytes, telemetry, checkpoints,
policy receipts, rollout traces, videos and browser receipts remain project-local.
The experiment imports its verified checkpoint/final policy via the public CLI
and enables Wren's existing policy declaration; this changes accepted script
identity, while the run retains its original training identity and model.


For the compact receipt, after successful collection:

```bash
python3 docs/probes/wren-fresh/summarize_training.py \
  "$HOME/cadex-projects/ot5-wren" wren1 > docs/probes/wren-fresh/training-evidence.json
```

The dashboard's `episode_steps` is the trainer's batch estimate
(`unroll * envs / max(endings, 1)`), which can exceed the 400-step episode
limit when few episodes end in a batch. It is not measured survival time.
The policy comparison uses the engine's verified rollout termination and
trace duration instead, on seed 0 with the declared eight-second limit.


The completed [training receipt](training-evidence.json) records exit 0,
240 GPU iterations (last index 239), 697.035 s training wall time,
sampled host peak 7,412,912,128 bytes and sampled total GPU peak 15,130 MiB.
The enforced host cap was 21,474,836,480 bytes. Final batch reward/step was
0.319398, loss 0.408266 and reported episode-length estimate 325.079 steps.
All 240 telemetry points are retained. The offboard JAX process emitted an
overflow-cast RuntimeWarning at initialization, but completed; both policies
passed independent engine witness verification. No new dependency or product
behavior change was needed.

| Seed 0, episode limit 8 s | Checkpoint 20 | Final policy |
|---|---:|---:|
| Observed simulation time | 8.00 s | 0.46 s |
| Fell | no | yes |
| Forward torso displacement | +49.451 mm | −105.757 mm |
| Control steps | 400 | 23 |
| Total rollout reward | 216.297 | −36.266 |
| Video frames at 10 fps | 81 | 6 |
| Encoded video duration | 8.1 s | 0.6 s |

The final policy is worse on this seed. This is one seed, not a gait-quality
or multi-seed reliability claim. The short final video faithfully records the
fall; its extra encoded time follows the renderer's final-pose sampling rule.
The checkpoint video was published while training advanced from iteration 23
to 32 during rendering; playback/download completed with training at 34.
Both videos use `cadex-prototype-light-v1`, style digest `27893221b3c6…`,
and were fully decoded and browser-tested. Saved screenshots were inspected.
This reuses the delivered common style; no new D11 visual similarity claim.

A fresh browser selected `wren1-final`, played/downloaded it, preserved playback
across three refreshes, selected checkpoint 20 as HISTORICAL with its own
revision, and returned to current. Both recorded model XML/task bundles match
the original training inputs. Training revision is `c2e89b36b1e2…` (explicit
`policy_on=0`, unchanged geometry digest); checkpoint playback is `ce541019cce8…`
and final playback is `a8073874ab76…`. Full identities are in the receipt.

The single-render throughput observation is 1.440 / 1.342 / 1.282 seconds
median per ordinary iteration before / during / after rendering, excluding
checkpoint boundaries. This uncontrolled observation shows continued progress,
not an assertion of zero overhead or renderer speedup. The render took 12.881 s
wall clock. No second training run overlapped this experiment. Wren still needs
multi-seed evaluation, a review-driven design change, retraining and the rest
of its repeated lifecycle; the operator service stays running on its final run.
