# Fresh biped review evidence

Verified against source: 2026-09-12. [Cadex-new]

The project is `ot5-biped` under the operator's `cadex-projects` directory,
outside this checkout, with its own Git history. Nothing was imported from
any older project, mechanism, checkpoint or policy.

## Creation

Three product-agent attempts (`evidence/create.*`, `retry-7.*`, `retry-8.*`)
were refused before authoring: `claude-fable-5` reported "You've hit your
session limit", quoting a reset at 2:30pm America/New_York. The CLI's
documented correction for an unavailable default model is `--model` or
`$CADEX_MODEL` (§2); it was **not needed**. A one-word probe of the default
model succeeded at 12:54 local, before the quoted reset, and the ninth
attempt — the same documented command, no `--resume`, no model override,
prompt retained in `evidence/attempt-9.prompt.txt` — authored the biped:

```bash
timeout --signal=TERM --kill-after=20s 1500 ./cadex --project "$PROJECT" --json \
  -p "$(cat "$PROJECT/evidence/attempt-9.prompt.txt")"
```

Envelope: `ok: true`, accepted revision `23c6fe93f47a…`, digest
`850acf23a05a…`, 37 tool calls, one `write_script`. The script declares
fourteen parameters (`torso_w/d/h`, `thigh_len`, `shin_len`, `limb_w`,
`foot_len/w/t`, `hip_spacing`, `printed_density`, `servo_torque`,
`fall_height`, `episode_s`), seven solids plus a ground plate, revolute hips
(±60°) and one-way knees (0–110°), fixed ankles, a free torso root, box
collisions, four 200 N·mm torque motors, the MJCF `reed_model` and one
training task `reed_walk` (400 steps at 50 Hz, forward axis world +X, fall
below 120 mm ends the episode, reset tilt/lift/stumble variation). The
agent's closing lines landed as ADR-002/003 in the project's `DECISIONS.md`
and `docs/design-specs.md`, `actuators.md`, `sensors.md`: standing height
238 mm, mass 0.651 kg at 1250 kg/m³, success measured as forward
displacement, survival and falls over seeds 0–9. A refused prompt leaves no
progress row; the accepted one is the first row in `PROGRESS.md`.

## The first bounded training probe

```bash
XLA_PYTHON_CLIENT_MEM_FRACTION=0.5 /usr/bin/time -v ./cadex walk --project "$PROJECT" \
  --out "$PROJECT/runs/probe1" --name probe1.cxpolicy --iterations 40 --envs 1024 \
  --seed 0 --timeout 1800 --leg-timeout 2400 --json
```

The train leg ran on the local RTX 5090 from `~/cadex-train-venv`: 40 PPO
iterations × 1024 environments in 89.5 s of training (182 s for the leg
with export and compile), final reward/step 1.211, policy `probe1.cxpolicy`
stored as sha256 `01865c8e06aa…`, `probe1.best.cxpolicy` beside it. Peak
host RSS 5.7 GB, GPU memory 16.7 GB, sampled every 5 s
(`evidence/probe1-memory.log`) — inside the 20 GB bound. The walk then
**exited 3 at its declare leg**: "the script declares no `policy_on=num(...)`
parameter: the walk needs the iterate convention (§2, ADR-192)". The system
prompt asks for the switch only *when a script declares a policy*; the fresh
script declared none, so the first walk on an agent-authored project cannot
finish. `runs/probe1/run.json` is retained as `status: failed` with that
error, the stored policy and the two legs. At that point no rollout,
review or video existed. The retained-policy recovery below adds them in
a separate record, preserving this failed record.

## Live observation of the real training (D3)

`evidence/probe1_observe.py` started the real `cadex review` command on the
machine's Tailscale address, opened it in headless Chromium, selected
`probe1` while the trainer was iterating and, at 0.25 s, read the trainer's
committed `progress.json` iteration beside the page's. Over 12 s the page
moved 13 → 23 through seven distinct iterations on its own 2 s poll, with no
reload (`performance` navigation count 1); each shown iteration appeared
between 0.21 s and 1.4 s after the trainer's `updated_at`. Reward, loss,
episode length and the reward/loss histories (14 → 24 retained samples)
updated with it; telemetry state `training`, freshness `live`. Results in
`evidence/probe1-observe.json` and a screenshot beside it.

The same observation exposed a review defect, since fixed (ADR-289): **a
run in progress had no model identity.** `run.json` was written at walk
start with `identity_source: "not reached"` and null revision/digest, and
the failed record kept them null although the train leg reported both. The
page therefore showed `RELATION UNKNOWN — no revision recorded for this
run` and `no model to show` for the run being trained, and for the failed
run afterwards, while the accepted-now view showed the biped. Now the walk
records the manifest's revision, digest and specs before its first leg and
each leg's reported identity after it, a failed run keeps the last one it
learned, and a run with no rollout of its own is drawn from the accepted
attempt when — and only when — its recorded revision *and* digest are the
accepted ones now, labelled as borrowed. `probe1`'s record is left exactly
as it was written: records are what the walk said at the time, and the fix
is proven by `cli/tests/test_walk.py` (the record as the train leg saw it,
and after a refusal at train and at declare) and by a headless-browser test
that follows a training run into failure
(`cli/tests/test_review_server.py`). The next real walk on this project is
what ticks the fixture evidence over to real-artifact evidence.

D2's orbit/zoom check on the fresh biped, D4's active-training checkpoint
video and D5–D9 remain open.
A quota reset time is a provider report, not proof a subsequent attempt
will succeed.

## Retained final-policy playback (D4, partial evidence)

The requested product-agent repair was attempted through `cadex -p` and
refused with a session-limit report; a `claude-sonnet-5` probe also returned
HTTP 429. Both quoted a 5:30pm America/New_York reset. Evidence:
`evidence/policy-switch.json`, `.log` and `policy-switch-model-probe.json`.
No authoring occurred through that agent. Instead, the loop actor made the
small script edit through the supported CLI: a numeric `policy_on=0`
parameter and one conditional policy/rollout block naming the stored
`probe1.cxpolicy`, its measured hash, 50 fps and seed 0. No geometry or
task declaration changed; no training was launched.

```bash
./cadex --project "$PROJECT" script \
  --set "$PROJECT/evidence/policy-switch-script.py" --json
./cadex --project "$PROJECT" params --set policy_on=1 \
  --out "$PROJECT/runs/probe1-playback/rollout" --json
./cadex --project "$PROJECT" render --json
```

All three commands exited 0. Project commits `842c2ea`, `8be0602` and
`e11dd72` retain the declaration, rollout acceptance and render visit.
The rollout accepted revision is `ddf021a4d3c0…`, digest `4213e25e49c6…`.
The exported MJCF **and task file bytes equal** probe1's retained training
inputs (model SHA-256 `973dbfc260a4…`, task `59508724bb6a…`). The final
policy remains `01865c8e06aa…`; its engine receipt reports 32 witness
samples, maximum error `7.302745071768867e-08`, tolerance `0.0001`.
No policy was relabelled or replaced to obtain compatibility.

Seed 0 terminated with **`fell`**, `terminated_step: 32`, after 33 control
steps and **0.66 simulated seconds** of the declared eight-second episode.
Total reward was **169.94907921196852**. This is a failed gait measurement,
although verification and recording succeeded. It is only one seed, not
the declared seeds 0–9 comparison.

`evidence/retain-playback.py` uses the existing CLI record writer to retain
these actual envelopes, accepted parameters/specs, script, project documents,
model, trace and component-source mapping in **`runs/probe1-playback/`**.
Its mode is `retained-policy-playback`; its review identifies `probe1` as
the source of the unchanged final policy and copied telemetry. It records
only the successful rollout leg, not a fictional new train leg. This is an
experiment harness, **not a new recovery subcommand**. The original failed
`probe1/run.json` was checked byte-for-byte unchanged. The model-source
render summary is copied into this run so later project renders cannot
silently change its component mapping. Project commit `c6a9dc8` retains
the recovery record, harnesses and compact evidence; the bulk video and
trace remain on disk outside Git.

From the product checkout, the retained evidence commands are:

```bash
PYTHONPATH=cli pixi run python "$PROJECT/evidence/retain-playback.py" "$PROJECT"
PYTHONPATH=cli pixi run python -m cadex_cli.video \
  --project "$PROJECT" --run probe1-playback
PYTHONPATH=cli:cli/tests pixi run python \
  "$PROJECT/evidence/check-playback.py" "$PROJECT"
```

The retention script is specific to this measured recovery and checks the
current accepted identity before writing; do not use it to reconstruct an
old record after a design change. The last command uses real artifacts,
FFmpeg decoding and headless Chromium on this machine's Tailscale address.
It passed: **eight 512×512 decoded frames**, first and last different,
**10 fps**, **0.8 seconds encoded**, playback continuing across three
dashboard refreshes, and the browser's downloaded bytes matching video
SHA-256 `d0222e198ca79ae6cdc120cea7fba685a41592502cc768142ab49a7a432ae722`.
The player identifies the accepted revision, policy digest, seed 0 and
0.66 simulated seconds. Selecting `probe1` still shows failed with no video.
Results are in `evidence/probe1-video-check.json`, video metadata in
`runs/probe1-playback/video.json`; a browser screenshot is retained beside
the check result. This was a same-machine private-address test, not a
second-device observation.

Rendering took **1.621 seconds**. No trainer was active, so this measures
neither training overhead nor intermediate-checkpoint publication. D4
remains open for those requirements. The video and trace stay outside the
product repository; copy the entire project including ignored review
artifacts for portability. Git alone does not carry its WebM or trace.

## Active-training checkpoint experiment (probe2)

`evidence/probe2-experiment.py` is a project-local experiment harness using
existing CLI commands and record writers. It exports with `policy_on=0`,
checks model/task bytes against probe1, snapshots the accepted identity and
specs in `runs/probe2`, and launches the existing offboard trainer. This
attempt was interrupted by its harness, as detailed below; the harness is
retained as experimental evidence, not a recommended unattended launcher:

```bash
systemd-run --user --scope --unit=cadex-probe2 -p MemoryMax=20G \
  timeout --signal=TERM --kill-after=20s 1800 \
  "$HOME/cadex-train-venv/bin/python" training/cadex_train.py \
  "$PROJECT/runs/probe2/train/reed_walk-task.json" \
  --out "$PROJECT/runs/probe2/train/probe2.cxpolicy" \
  --iterations 240 --envs 1024 --seed 0 --checkpoint-every 20
```

The launcher sets `XLA_PYTHON_CLIENT_MEM_FRACTION=0.45`. This is one local
GPU training run; `MemoryMax` bounds host memory, while GPU use is sampled
separately. No old policy initializes it. The checkpoint flag belongs to the
offboard trainer; `cadex train` does not currently expose it.

The browser observer (`evidence/probe2_observe.py`) opens the real review
command at the machine's private Tailscale address, selects probe2, checks
its recorded revision, exercises orbit/zoom on its drawn model, and compares
multiple automatic telemetry updates with committed progress timestamps.
The playback harness imports checkpoint 20 through `cadex asset`, declares
its actual hash through `cadex script --set`, and exports an engine-verified
seed-0 rollout through `cadex params`. The original mechanism and task stay
unchanged. It retains that playback as `probe2-checkpoint20`, with its own script, specs, trace, model, component mapping and video,
citing the training run. The planned final-policy stage was not reached.
The original `probe1` and `probe1-playback` records are checked unchanged.

This is an explicit CLI-driven experiment, not an automatic checkpoint
publication service or a successful product-agent design revision. The
training process reads its retained inputs independently of subsequent
playback edits. Videos and bulk artifacts remain project-local outside this
repository. Preserve the entire project, including ignored files.

**Measured outcome: partial success, then harness-induced interruption.**
The initial browser assertion timed out waiting for probe2's model to load.
Its revision label was correct (`6ab8a1d090c8…`, digest `850acf23a05a…`),
but model state was `missing`. Training continued independently. The
collector attached to that same trainer; it did not start another run.
The retained observer log documents the failure. The telemetry-only retry
passed: page iterations **20, 21, 23, 24, 26, 27, 29**, navigation count **1**,
committed-to-page delays **0.23–1.29 s**, with changing reward, loss, episode
length and curve samples and checkpoint availability. This supplies real D3
observation under the identity fix; it does not supply D2's model interaction.

Checkpoint 20 policy `fa37e8259a3a…` passed 32 engine witness samples at
maximum error **3.2584348144126806e-08**, below `0.0001`. Its retained rollout
revision is `3d28c70c890f…`, digest `c77cc2784bd4…`; model/task bytes still
match the training input. Seed 0 ran **8.0 simulated seconds**, total reward
**333.20822667851917**. This is not the declared seeds 0–9 gait comparison.
Rendering while training was active produced **81 frames, 10 fps, 8.1 encoded
seconds**, in **16.414 s**. Video SHA-256:
`e9255cbcb3dfdf5f6c7914de945c434cf8c6d40ba2f5b619d8b53391fe6adf17`.

The first video browser check reached the player but incorrectly expected
`8.00000 s`; the UI correctly formats the integer as `8 s`. The collector's
`finally` cleanup then terminated the training scope. The trainer printed
iteration 39; its last committed snapshot is **iteration 38, state training**.
No final policy exists. The run record now explicitly reports the harness
failure/interruption and tells the operator to start a new bounded attempt;
the stale telemetry is preserved. This is neither a successful train run nor
a product renderer failure. Future experiment orchestration must keep a
browser/render failure from terminating training. The collector also briefly
rewrote the initial empty progress snapshot when attaching; the trainer's
next atomic update restored it. A collector must only read trainer telemetry.

After correcting the integer-label expectation, the standalone video check
passed: all 81 frames decoded, first/last differ, timing matches, Chromium
played across three dashboard refreshes, and download bytes matched the hash.
That successful playback/download check happened **after training stopped**.
No probe2 final-policy video or successful browser playback during active
training is claimed. The original final-policy video in `probe1-playback`
remains intact, and both original run records match project commit `c6a9dc8`.

The approximate render window comes from `video.json` mtime minus the
renderer elapsed time. Eleven preceding committed iteration intervals had
median **1.325 s**; four wholly inside the window had median **1.301 s**, max
**1.322 s**. A checkpoint boundary overlapped the end; these sparse intervals
show progress during rendering, not an isolated causal overhead estimate.
Peak host cgroup memory was **5,501,710,336 bytes**; sampled GPU use peaked at
**15,092 MiB**. Raw timing/memory samples, witness, hashes and qualifications
are retained in `evidence/probe2-result.json`, `probe2-timeline.json`,
`probe2-memory.json`, `probe2-observe.json`, `probe2-checkpoint20-check.json`
and the experiment/collector logs. This was a same-machine private-address
browser test. D4 remains open; no final-policy completion is inferred from
an intermediate checkpoint. No second training run was launched to hide the
failed attempt.

A subsequent private-address browser check also passed on the real interrupted
record: probe2 shows **failed**, telemetry **stale**, and the explanatory next
CLI action; both probe1's earlier video and checkpoint20 remain accessible
(`evidence/probe2-interrupted-browser.json`). This advances the interruption
half of D8, but no successful new attempt follows it yet. The checkpoint
trace has 400 steps, `truncated: true`, and no fall termination; no walking
claim follows from one seed surviving the declared horizon.

External project commit `73611af` retains the interrupted record, checkpoint
review and compact evidence. The saved experiment harnesses document this
attempt's failure; use the standalone video/interruption checks to inspect
its artifacts, rather than rerunning the launcher into the same run directory.

## Retained probe2 training parts (iteration 17)

The missing-model investigation found eight original STL parts beside
`runs/probe2/train/reed_model-model.xml`. `run.json` names that permitted
model artifact and the successful `probe2-export.json` envelope names those
same STL exports at revision
`6ab8a1d090c812865d70d5d6c9300907dc1076cb19ec3f2d4885a44baeaa12c8`, digest
`850acf23a05ade2fa76275a6484caaefc9e2d22230fb002ead681c533e530697`.
The old revision's staging directory no longer exists. There is no retained
assembly placement map for this export; the mesh parts are in local frames.

ADR-290 makes those exports inspectable, explicitly labelled as individual
parts at identity, **not a solved pose**. The project-local read-only check:

```bash
PYTHONPATH=cli:cli/tests pixi run python "$PROJECT/evidence/check-training-parts.py" "$PROJECT"
```

passed against a server bound to the machine's Tailscale address. Chromium
selected historical `probe2`, checked exact revision/digest and the placement
limitation label, loaded all eight parts (96 triangles), and compared every
mesh response byte-for-byte with the retained STL. Mouse orbit changed yaw
0.8 to -0.2 and pitch 0.5 to 0.9; wheel zoom changed distance 658.2674 to
459.2576 mm; 219,902 non-background pixels remained. The accepted manifest,
run record, trainer telemetry and all eight meshes had unchanged hashes
before/after. Evidence is `evidence/training-parts-result.json`. No engine
was started, no trainer was started/stopped, and no telemetry was written.
No second-device claim. D2 advances with real exported-part interaction,
but remains open for a retained, assembled training-model pose and the full
model/spec history checks. This check does not reconstruct missing poses
from the later checkpoint playback or today's script.

The same check then selected `probe2-checkpoint20` and exercised the assembled
biped from that run's own meshes, mapping and first rollout frame at revision
`3d28c70c890f79ff6b98ef314dc8bf672746311aae5b3d23b845c89808c387f8`.
Its eight components / 96 triangles passed orbit (yaw 0.8 to -0.2, pitch
0.5 to 0.9) and zoom (distance 731.7874 to 510.5507 mm), with 135,542
non-background pixels. Thus real assembled-biped interaction is also proven;
this does not supply the missing assembly placement record for `probe2`.
