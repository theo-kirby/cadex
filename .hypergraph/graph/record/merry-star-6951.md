---
node_id: cb989513-0809-59b9-8d66-0ba0c3a155e3
slug: merry-star-6951
title: Probe2 live telemetry and active-training checkpoint video, then explicit harness interruption
created_at: '2026-09-12T18:09:58+00:00'
parents:
- amber-gate-7498
summary: ''
artifacts:
- docs/HEADLESS-BIPED-REVIEW.md
---
## What

Ran one new bounded offboard GPU experiment on the fresh ot5-biped,
observed real live telemetry under the recorded-identity fix, and rendered
an engine-verified intermediate checkpoint while training remained active.
The experiment then interrupted its own trainer after an erroneous browser
assertion; no final policy was produced. Retained the checkpoint playback,
corrected and passed the standalone video check, explicitly recorded the
failed/interrupted training and browser-checked its stale state. Updated
docs/HEADLESS-BIPED-REVIEW.md with commands, measured results and limitations.
External project commit 73611af retains the evidence; CLI commits 1ea02e2,
ae593ef, 6de79c8, 3041fdc and a34c18d retain the real export/import/playback.

## Why

The critic requested one bounded fresh-biped training run advancing D3/D4,
with live telemetry, intermediate playback during training, render impact,
and a retained final video. The requested experiment was attempted, but the
final-policy stage and successful playback/download during active training
were not achieved: the experiment harness incorrectly expected a decimal
label for integer simulation time and terminated its training scope in
cleanup. I did not launch a second training run to conceal that failure.
This is one finished measurement unit with a failed outcome, not a partial
product implementation. It also supplies real interrupted-state evidence
for D8. The explicitly forbidden reconcile was not run; retired plan work
still needs replacing at the next authorized reconcile.

## Method

Project ot5-biped remains outside the product checkout under the operator's
cadex-projects directory. The project-local probe2-experiment.py exports
through cadex params policy_on=0, asserts model/task bytes equal probe1,
snapshots identity/specs and invokes the existing trainer under its existing
venv with 240 iterations, 1024 environments, seed 0, checkpoint-every 20,
XLA_PYTHON_CLIENT_MEM_FRACTION=0.45, systemd MemoryMax=20G and timeout 1800.
No warm start, geometry/task edit or second trainer. Exact command in the
updated user-facing report. Model hash remains 973dbfc260a4268a1e97817d7846a8302325b7a6b823f70f274bb8723e557756;
task 59508724bb6aef368fac7cc2c6cdfa11c342d8e1bec9d56c7698405b9376bfad.

The initial observer timed out waiting for loaded model despite the correct
revision 6ab8a1d090c812865d70d5d6c9300907dc1076cb19ec3f2d4885a44baeaa12c8,
digest 850acf23a05ade2fa76275a6484caaefc9e2d22230fb002ead681c533e530697.
Training stayed alive. probe2-collect.py attached to the existing process,
then ran probe2-telemetry-observe.py on the real review command over the
machine's private Tailscale address. Seven page iterations 20,21,23,24,26,27,29
appeared over 12.03 seconds, navigation count 1, committed-to-page delays
0.23–1.29 s. Reward changed 0.73584 to 1.0347, loss 15.488 to 53.784,
episode_steps 20480 to 143.22, reward/loss histories 21 to 30 samples, two
checkpoint references. These are trainer-reported metrics, including its
episode-length estimate; not independently measured rollout survival.

Checkpoint 20 was imported via cadex asset, declared through cadex script
--set with its measured hash and played via cadex params policy_on=1.
The engine's 32-sample witness error was 3.2584348144126806e-08 < 0.0001.
Policy fa37e8259a3a2846150e301d9aaf0bdc9971f33822f9c135bf112e5de182c9e6;
rollout revision 3d28c70c890f79ff6b98ef314dc8bf672746311aae5b3d23b845c89808c387f8;
digest c77cc2784bd465d9dcf8dfa31ac0281f2da845afaaa07ec3fe4752855fc8494a.
Seed 0 reached 400 steps, eight simulated seconds, truncated=true with no
fall termination, total reward 333.20822667851917. No walking or seeds 0–9
comparison claim. The record writer retains script/specs/trace/model and
component mapping in runs/probe2-checkpoint20, citing probe2.

PYTHONPATH=cli pixi run python -m cadex_cli.video --project "$PROJECT"
--run probe2-checkpoint20 produced 81 frames at 10 fps, 8.1 encoded seconds,
in 16.414 s, while the trainer was active. Video hash
e9255cbcb3dfdf5f6c7914de945c434cf8c6d40ba2f5b619d8b53391fe6adf17.
The first Chromium check reached the player but expected 8.00000 s instead
of the correctly displayed 8 s. The collector's cleanup sent SIGTERM to the
training scope. Last printed iteration 39, last committed 38; progress
remains state training and becomes stale, final probe2.cxpolicy absent.
The explicit failed run record reports harness interruption and next action.
The leg exit 1 records experiment failure, not an invented trainer receipt.

After correcting the numeric label expectation, PYTHONPATH=cli:cli/tests
pixi run python "$PROJECT/evidence/check-probe2-video.py" "$PROJECT"
probe2-checkpoint20 passed: all 81 frames decoded, first/last different,
ffprobe timing matches, private-address Chromium playback across three
refreshes, matching download bytes and revision/policy/seed/time labels.
This successful check occurred after training stopped. The separate real
probe2-interrupted-browser.py passed failed status, stale telemetry, the
next action, and continued access to probe1-playback and checkpoint20.
No second-device test was run.

Video metadata mtime minus renderer time bounds an approximate render
window: 11 preceding committed intervals median 1.325 s, four entirely
inside median 1.301 s, max 1.322 s. This shows trainer progress during
rendering, not a causal overhead estimate; checkpoint 40 overlaps the end
and the timeline is sparse. Peak host cgroup memory 5,501,710,336 bytes,
sampled GPU peak 15,092 MiB. Detailed evidence in probe2-result.json,
probe2-observe.json, probe2-timeline.json, probe2-memory.json, the browser
check JSONs and retained experiment/collector logs, all project-local.
Original probe1 and probe1-playback records are byte-identical to external
commit c6a9dc8 (hashes c28b023c1ee29d1cb1bb1d224b67b3ca4c27366254b08d639491f25733eeed56
and d5bdd195aa3e70b01033ac24c5f83cc9e3459ed4eade61f90e9e5ca7d64691b4).

## Result

D3 now has its real multi-update browser re-observation under the identity
fix. D4 advances with a verified checkpoint rendered during active training
and a retained video passing later playback/download; it remains open for
successful playback during active training, final policy/video for this run,
and reliable failure isolation. D2 remains open: borrowed current model was
missing, so no real orbit/zoom evidence. D8 has a real harness-induced
interruption with honest browser status, not yet the subsequent successful
new attempt. The existing probe1 final video is preserved.

The demonstrated orchestration failure is in the external experiment
harness, not a product renderer failure: its browser failure must not stop
training. The collector also briefly wrote an empty progress snapshot during
attachment; the trainer restored it on its next atomic update. Future
collectors must only read trainer telemetry. Those failed harnesses remain
historical evidence, not a recommended unattended launch path. No new
dependency, protocol/payload/shell change, engine build or product code edit.
Bulk videos, traces and checkpoints remain outside this repository and must
travel with the project, including ignored files. No criterion checkbox or
state node was edited.

Standing engine verification passed: pixi run test-engine, 2103 passed,
54 skipped, 280.69 seconds, exit 0. No build was required for this experiment.
Full CLI verification passed: pixi run python -m pytest cli/tests, 358 passed,
1 skipped, 311.78 seconds, exit 0. Real corrected video and interrupted-state
browser checks passed; the initial model and integer-label assertions failed
as documented. git diff --check is clean. The unreconciled tail is now two
records; this contributor dispatch did not reconcile.

Dispatch closed: 1 unit — real live telemetry and checkpoint video experiment, with explicit harness-induced interruption and no final policy.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot5
- commit: 8e9d69399d9c42e772aa7cdc21a6c155d46ed540

## State Impact

- target: dawn-delta-4361 — Real probe2 browser re-observation under the identity fix passed: seven actual training iterations 20 to 29 over 12.03 s without reload, committed-to-page delays 0.23–1.29 s, reward/loss/episode histories and checkpoint availability visible. Full telemetry-containing CLI and engine suites pass. The borrowed model was missing, separately affecting D2.
- target: candid-harvest-2614 — Verified fresh-biped checkpoint20 rendered during active training: 81 frames, 8 simulated seconds, 8.1 encoded seconds, 16.414 s render; corrected playback/download passed after trainer stopped. Harness browser assertion cleanup interrupted training before final policy; D4 remains open for active-training successful browser check, final video for the new run and reliable failure isolation. Prior probe1 final video preserved; sparse interval timing is not causal overhead proof.
- target: shy-meadow-0959 — Fresh real probe2 showed the correct current revision but model state missing; initial orbit/zoom browser check timed out. D2 remains open, and accepted-model availability on this headless export lifecycle needs investigation.
- target: cool-gate-3332 — Real probe2 was interrupted by experiment harness cleanup after an erroneous browser time-format assertion. Explicit failed/interrupted run record, stale telemetry and next CLI action browser-checked; prior and checkpoint videos retained. No final policy or subsequent successful attempt, so D8 remains open.
