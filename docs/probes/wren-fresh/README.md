# Fresh Wren reopen and persistent review

Verified against source: 2026-09-12. [Cadex-new]

Current working project: [`ot5-wren-copy54`](COPY.md), independently edited
and reviewed with the original path unavailable. Port 8765 serves the copy,
selecting retained `wren2-final` (105 mm) as historical relative to its accepted
110 mm feet. No new training or product-agent authorship is claimed.

Previous experiment: [the completed revised-foot comparison](COMPARISON.md)
retains both training runs and their four videos; the persistent dashboard
now selects `wren2-final`, revision `26332a5955e3…`. The sections below are
historical evidence of the earlier lifecycle steps.

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


## Review-driven foot revision (iteration 50)

The retained checkpoint and final frames were inspected. The final policy pitches
backward and crosses the torso-height threshold at 0.46 s, with −105.757 mm
torso X displacement; checkpoint 20 survives eight seconds. This motivates one
parametric hypothesis: grow `foot_len` from 85 to 105 mm for more support behind
the ankle. With the existing length/8 centroid offset, heel reach grows from
31.875 to 39.375 mm, toe reach from 53.125 to 65.625 mm. Each foot gains
7.936 g. Extra mass/inertia and toe length may hurt control; this does not
establish that geometry caused the learned policy's failure. No gait improvement
or retraining is claimed. The final image records threshold crossing, not a
completed ground impact.

The public CLI accepted revision `a90b84033ced…`, digest `502fc7ad0409…`:

```bash
./cadex --project "$HOME/cadex-projects/ot5-wren" params \
  --set policy_on=0 --set foot_len=105 \
  --out "$HOME/cadex-projects/ot5-wren/evidence/revision50/export" --json
./cadex --project "$HOME/cadex-projects/ot5-wren" render --json
```

The source script text stays unchanged: accepted parameter values author the
revision through the product's parameter operation. `policy_on=0` disables the
old model-bound policy. All other dimensions and task settings remain equal;
the task bundle differs only in its model reference. Project DECISIONS.md and
PROGRESS.md explain the hypothesis and comparison protocol.

Before the edit, every file under `runs/` was hashed to the project-local
`evidence/revision50/runs-before.json`, and the script/manifest were retained
beside it. [revision.py](revision.py) checks that inventory after the edit and
again after browser review. Re-run this read-only check with the same inputs:

```bash
PYTHONPATH=cli:cli/tests pixi run python docs/probes/wren-fresh/revision.py \
  "http://$(tailscale ip -4):8765/" "$HOME/cadex-projects/ot5-wren"
```

[revision-evidence.json](revision-evidence.json) records the pass. The actual
served STL feet measure 85 mm for both historical playback runs and 105 mm for
ACCEPTED NOW. Both old models load eight components, retain their revision,
digest, curves, policy and video identities, play through three refreshes and
download with matching hashes. All retained run files remain byte-identical.
Accepted view shows 105 mm and disabled policy with no substituted old video.
Screenshots and decoded frames remain in `evidence/revision50/`; the accepted
viewport screenshot was inspected. This is a same-machine private-address
check, not a second-device or new D11 similarity claim. The service was never
stopped: fresh visits select latest attempt `wren1-final`, explicitly HISTORICAL
relative to the new accepted design, and return-to-current works. Select
ACCEPTED NOW for the untrained revision.

**Declared before retraining:** evaluate the original checkpoint 20 and final
policy, and their revised-design counterparts, on rollout seeds **[0,1,2,3,4]**,
**eight seconds**, **50 Hz / 400 steps**, with the same reset distribution and
fall threshold. Record per-seed torso X displacement, actual survival duration,
fell/termination and total reward, then mean/min survival and fall count.
Original seed 0 exists; seeds 1–4 remain unmeasured. Use the retained original
model/task for old-policy evaluations. Train the revision from scratch with
the same **240 iterations, 1024 environments, training seed 0, checkpoint interval
20, 1800-second timeout and MemoryMax=20G** as wren1. Retraining and additional
seed evaluations belong to the next experiment; no result is inferred here.

## Product-agent revision attempt (iteration 53)

Both product-agent model attempts were refused at their provider session limit.
No new design was authored; all 228 retained run files, accepted identity and
four playable reviews remain intact on the persistent dashboard. See
[the attempt report and retry instructions](AGENT-REVISION.md) and
[compact receipts](agent-attempt-evidence.json). The authorship gap remains
open; the earlier caller parameter edit is not retroactively credited.
