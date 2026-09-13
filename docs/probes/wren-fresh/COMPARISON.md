# Wren: retained review, foot revision and retraining

Verified against source: 2026-09-12 (execution completed 2026-09-13 UTC).
[Cadex-new] Iteration 52, ADR-304.

Wren's 105 mm foot revision completed the declared bounded GPU retraining.
Both revised policies survive the five declared eight-second episodes. The
original final policy falls twice; neither checkpoint falls. This is improved
final-policy survival on this small sample, **not evidence of repeatable
walking or a causal geometry effect**. There is only one training seed per
design, and mean displacement is small. The inspected revised checkpoint and
final frames at seven seconds show standing poses on Wren's modeled ground
plate, not a demonstrated alternating gait.

The original mechanism was authored by the product agent, with an accepted
creation followed by a provider-limit exit. The 85→105 mm foot edit was made
through `cadex params` in iteration 50. It is **not a product-agent revision
turn**. Playback changes only the policy declaration and enables that policy;
evaluation uses retained run scripts and effective parameters. Original and
revised task bundles differ only in their model reference.

## Declared comparison and results

Seeds **0–4**, **eight seconds**, **50 Hz / 400 steps**; unchanged reset
variation and torso-height fall threshold. X is forward. Displacement is final
minus initial torso X, including reset motion and any falling motion; it is
not distance walked. Survival is actual simulated time until threshold
termination or the eight-second time limit, never the trainer's batch episode
estimate. A recorded fall means crossing the declared threshold, not a
completed ground impact.

| Retained policy | Feet (mm) | Mean X displacement (mm) | Mean / minimum survival (s) | Falls / 5 |
|---|---:|---:|---:|---:|
| wren1-checkpoint20 | 85 | 43.08 | 8.00 / 8.00 | 0 |
| wren1-final | 85 | −10.36 | 4.98 / 0.44 | 2 |
| wren2-checkpoint20 | 105 | 41.78 | 8.00 / 8.00 | 0 |
| wren2-final | 105 | 52.65 | 8.00 / 8.00 | 0 |

[comparison-evidence.json](comparison-evidence.json) retains all twenty
per-seed displacement, survival, fall/termination, reward and trace/policy/
model/task identity rows. Every seed-zero trace reproduces its saved rollout
exactly. All 114 original run files still match the pre-revision inventory,
including models, documents, progress, policy receipts and videos. Current
geometry never supplies the old policy's model.

## Training and persistent review

The existing server on the private address, port 8765, stayed on `ot5-wren`
throughout; no temporary server satisfied these checks and no service restart
occurred. At start it selected `wren2`, accepted revision `a90b84033ced…`,
with 105 mm feet. During initial compilation the page accurately reported
stale telemetry, not training progress. Once GPU updates began, seven browser
observations spanned iterations 3–11 without a reload, with **0.50–1.53 s**
measured committed-to-page delays. Pointer orbit and zoom passed.

Training used the same 240 iterations, 1024 environments, training seed 0,
checkpoint interval 20, 1800-second timeout and MemoryMax=20G as Wren1.
The harness measured **750.3 s** from launch through trainer exit; the trainer
reported **681.8 s** internally. It exited 0 on GPU. Sampled host peak was
7,385,264,128 bytes and GPU peak 15,120 MiB (whole-device sampling, not exclusive
trainer allocation). Reward, loss and episode-estimate histories retain 240
points each. [retraining-evidence.json](retraining-evidence.json) carries the
resource, telemetry, witness and publication receipts.

The checkpoint-20 video was verified, rendered, played and downloaded while
training remained active: publication spans iterations 18–34, with the render
itself spanning 23–32. Witness errors are below the engine's 0.0001 tolerance.
Render wall time was **12.7 s**; median ordinary trainer intervals before,
during and after were **1.466 / 1.352 / 1.323 s**. These observations do not
show a slowdown, but they are not a controlled overhead measurement: CPU
policy evaluations and later suite execution shared the machine. One video
render ran at a time. The final video rendered in **12.2 s** after training.

At completion a fresh browser selects **`wren2-final`**, revision
**`26332a5955e3…`**, and shows the revised model, parameters, curves and video.
All four retained runs load eight components and their own 85/105 mm foot
parameter, revision and video policy identity. Historical playback survives
three polls, downloads match saved SHA-256 values, and return-to-current
reaches the latest run. The original final video is six frames / 0.6 encoded
seconds representing 0.46 simulated seconds; the other three are 81 frames /
8.1 encoded seconds representing eight simulated seconds. All decode at 10
fps with distinct first/last frames. Padding and final-pose sampling are not
extra survival time.

Both new recordings retain `cadex-prototype-light-v1` and style digest
`27893221b3c6…`, the existing shared viewport/video environment. This unit
inspected decoded frames but did not repeat the full D11 reference comparison.
All browser evidence is same-machine private-address evidence, not a
second-device test. The service remains running between iterations.

## Reproduction and retention

Run from the checkout. These commands use the existing environments and no
new dependency. Use a new run name and fresh scratch directory for repetition;
`train.py` refuses an existing training directory.

```bash
PYTHONPATH=cli:cli/tests pixi run python docs/probes/wren-fresh/train.py \
  "$HOME/cadex-projects/ot5-wren" wren2 "http://$(tailscale ip -4):8765/"
PYTHONPATH=cli:cli/tests pixi run python docs/probes/wren-fresh/current.py \
  "http://$(tailscale ip -4):8765/" "$HOME/cadex-projects/ot5-wren" wren2-final completion
pixi run python docs/probes/wren-fresh/compare.py \
  "$HOME/cadex-projects/ot5-wren" "$HOME/cadex-projects/ot5-wren-eval52-f2" wren2-final
PYTHONPATH=cli:cli/tests pixi run python docs/probes/wren-fresh/check_video.py \
  "$HOME/cadex-projects/ot5-wren" wren1-final "http://$(tailscale ip -4):8765/" --historical
```

`compare.py` was run separately for original checkpoint/final (`c1`, `f1`)
and revised checkpoint/final (`c2`, `f2`). It creates only the scratch project,
imports the hash-verified policy through the public asset command, rebuilds
the retained script with recorded parameter values, and checks all identities.
After each completed evaluation its `evidence/` was copied into Wren's
`evidence/comparison52/<c1|f1|c2|f2>/evidence/`. The report is regenerated by:

```bash
pixi run python docs/probes/wren-fresh/report_comparison.py \
  "$HOME/cadex-projects/ot5-wren" \
  "$HOME/cadex-projects/ot5-wren/evidence/comparison52/c1" \
  "$HOME/cadex-projects/ot5-wren/evidence/comparison52/f1" \
  "$HOME/cadex-projects/ot5-wren/evidence/comparison52/c2" \
  "$HOME/cadex-projects/ot5-wren/evidence/comparison52/f2"
```

Policies, videos, traces, full CLI envelopes, screenshots and training logs
remain outside the repository, inside Wren. Retain/copy the **whole project**
with its `assets`, `runs` and `evidence`; the scratch projects are not required
to interpret the retained comparison. No earlier recording was overwritten.
An early historical-video recheck raced checkpoint publication and failed the
probe's frozen-current-target assertion; its log is retained in
`evidence/comparison52/early-browser-failure.log`. The probe now verifies the
current target shown when clicked, and completion rechecks pass.

## Lifecycle scope and remaining evidence

| Criterion | Evidence used here and its limit |
|---|---|
| D1, D2 | [Wren creation/reopen](README.md), persistent start/completion browser receipts, model/parameter/revision checks on four runs. |
| D3, D4 | Real retraining receipt, live checkpoint publication and saved final video; playback/download/decoded timing on all four recordings. |
| D5 | [Foot revision](README.md#review-driven-foot-revision-iteration-50), all 114 original run bytes preserved, old/new seed evaluations and browser views retain their own identities. |
| D6 | [Wren in-place restore](README.md#in-place-restore-preservation-iteration-48-adr-303). No new during-training dashboard restart in this unit. |
| D7, D8 | Existing [Reed lifecycle report](../reed-lifecycle/README.md); no new Wren copy-isolation or controlled-interruption claim. |
| D9 | This report supplies Wren's review→CLI parameter edit→retraining comparison. Full product-agent revision authorship and Wren-specific D7/D8 repetition remain unproven; Reed's earlier report retains its own evidence. |
| D10 | Persistent start/current/completion identities and historical playback; service kept running. No project switch was needed. |
| D11 | Existing shared renderer and retained new style identities; [reference assessment](../review-style/README.md) remains the comparison evidence. |

## Verification

`OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 pixi run test-engine` passed
**2110 tests, 53 skipped**. An earlier unrestricted-BLAS invocation was stopped
after 76 passes because it oversubscribed CPU; the bounded rerun completed.
`OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 pixi run python -m pytest cli/tests`
reported **396 passed, 1 skipped, 1 failed**: the new evidence test incorrectly
expected iteration 240, while the trainer uses 0–239 for 240 updates. That
assertion was corrected to check the count and `done` state; all **nine**
`cli/tests/test_wren_fresh_evidence.py` tests then passed. The other CLI tests
were not rerun after this test-only correction. Persistent browser checks,
video decoding and all twenty public-CLI replays passed. No product behavior,
protocol, payload, trainer or shell code changed; no build was needed.
