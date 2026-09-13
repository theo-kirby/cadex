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

## Successful-retry experiment with the retained training snapshot

The next bounded attempt is `probe3`, using the same fresh biped and unchanged
model/task bytes. Its project-local harness invokes the existing CLI for export,
asset import, policy declaration, rollout and rendering. Before dispatch it calls
the CLI's `retain_training_view` under `project_lock`, then writes the running
record with the exported identity and document/spec snapshot. This measures the
snapshot contract directly; it is not a claim that `cadex walk` was exercised.

```bash
PYTHONPATH=cli:cli/tests pixi run python "$PROJECT/evidence/probe3-experiment.py" "$PROJECT"
```

The trainer uses the existing offboard venv, seed 0, 240 iterations, 1024
environments and checkpoints every 20 iterations. Its independent systemd scope
sets `MemoryMax=20G`; `timeout --signal=TERM --kill-after=20s 1800` bounds it,
with `XLA_PYTHON_CLIENT_MEM_FRACTION=0.45`. One trainer and one renderer at a
time. Browser failures are collected without terminating the bounded trainer.
There is no warm start or mechanism change. The initial `python` helper command
was unavailable; `python3` generated the harness before any training started.

Training revision `c26c92b09dbb3142c973d9807024373cf8d7c5b0f080a5c21ba8f66d3badf49e`
has digest `850acf23a05ade2fa76275a6484caaefc9e2d22230fb002ead681c533e530697`.
`training-view.json` retains eight components with declared placements (no solved
training trace), parameter defaults/values and project documents. The live browser
observer passed orbit/zoom and seven actual iterations (3, 5, 6, 7, 9, 10, 12)
over 11.78 seconds, one navigation, committed-to-page delay 0.18–1.33 seconds.
Reward/loss histories grew from 4 to 13 samples. Its `model_state` field was
captured during loading; the subsequent loaded-state, rendered-pixel and camera
assertions passed. Evidence: `evidence/probe3-observe.json` and observer log.

Checkpoint 20's policy is
`74750cc6d8e7f9817481e08e94ee01978120bbafe3edca5b25f53cabfe1b3c78`.
Its retained playback revision is
`0fb4ffb59c69f646897d5c4464876b954ad3531e807313d6163244f648dcad15`,
digest `9c6f79478f4d8acfce28bd33e9f56f622e891ef621a2cbe512839730d830872a`.
Video `757a0c4ed104a9238b26412d8a1570e3a5588a5e2cf78a6f6e8a340532218e74`
contains 81 decoded frames, 10 fps, 8.1 encoded seconds / 8 simulation seconds;
first and last frames differ. It rendered in 16.536 seconds and passed browser
playback, three refreshes without replacing/stopping the player, matching-byte
download and revision/policy/seed/time labels while the trainer was still active.
This browser was on the server machine, using its Tailscale address; no second
device was tested. `probe3-checkpoint20-publication.json` records the active
process check before and after the browser test. The trainer remained in its
checkpoint publication work throughout this render: committed iteration stayed
18. Thus this window proves coexistence, **not a throughput overhead estimate**.

A deliberately invalid render of the training-only `probe3` run exited 1 with
`video: no successful recorded rollout at this identity`; its scope remained
active. This is missing-trace refusal and failure isolation, not an injected
encoder crash. After checkpoint playback changed the accepted script, the
browser selected historical `probe3`, checked its retained revision/digest,
loaded model and exercised orbit/zoom. The first external history assertion used
`accepted_revision` where the snapshot uses `revision`; correcting that harness
field passed. No product code changed to make either browser test pass.

Keep the entire project, including ignored policies, traces and videos. The
project-local experiment scripts, publication receipts, telemetry timeline,
memory samples, browser checks and `runs/probe3*` are the detailed evidence;
this product document contains compact identities rather than bulk artifacts.

A sequential repeat of the checkpoint render took 27.675 seconds during
checkpoint 60's publication (committed iteration stayed 58). The engine suite
was also running then, so neither render timing is an isolated overhead
measurement. Re-encoding produced different container bytes, now referenced by
`video.json` as
`c479457f48ad7217cfa4d69f79925d8f4c35add98b0ed8fa17d9580020674f8f`;
the earlier file remains on disk. The currently referenced video independently
passed the same decode/playback/download checks while the scope was active
(`probe3-repeat-browser.log`). The first browser receipt is preserved as
`probe3-checkpoint20-first-check.json`; the current receipt names the new bytes.

The checkpoint's engine witness error was `3.996235200531828e-08` against
`0.0001`. Seed 0 completed 400 steps / 8 seconds, `truncated=true`, no fall
termination, reward 333.02443433799135. Torso-link displacement was
`[45.940988, 1.898436, -29.309025]` mm. This is link-origin displacement from
the retained trace, not a separately integrated centre-of-mass measurement and
not a multi-seed walking claim.

Verification on this source: `pixi run test-engine` passed (2103 passed,
54 skipped, 428.49 seconds); the focused browser/record suite
`pixi run python -m pytest cli/tests/test_review_server.py cli/tests/test_review_record.py -q`
passed (48 passed, one skipped, 51.46 seconds). The engine suite overlapped
training after the first checkpoint video check; its MJX-dependent training
checks skip in the pixi environment. Trainer-capable CLI verification is serial.

The trainer exited **0** on GPU, reporting 1003.681 seconds of training,
240 iterations (last index 239), reward/step 7.442540, loss 899.636 and
estimated episode length 25.409 steps. Sampled host peak was 9,321,664,512
bytes; GPU peak 15,152 MiB. The final policy is
`a06b4bf489529d6cd119576131b778a02789cf30e1bf3793ab5a5e5d4ea04911`,
82,008 bytes, engine witness error `7.370347304913593e-08 < 0.0001`.
It is retained in `runs/probe3/train` and imported into `assets/`; the training
record remains at its original snapshot identity with status `ok`.

Final playback revision
`a7ee956cafc8de6b1732bc83cb3f59d832a6fe46b5406f3624e88267f479fa2d`,
digest `14d56ed42ef87185db899cb2485180a81f8eb0959aaf2f8356c7031760a6ebb1`,
retains video
`59724f619c5540468f8fd6e109aa319507be6a449eafcc8ef9f3259af6046853`:
seven decoded frames at 10 fps, 0.7 encoded seconds, 1.407-second render.
The verified seed-0 rollout **fell after 26 steps / 0.52 seconds**
(`terminated_step=25`, `truncated=false`), reward 198.204299, torso-link
displacement `[210.535718, -0.018994, -83.103159]` mm. These are honest
poor-gait results: more forward travel before falling is not better survival.
Both policies used the same eight-second episode and seed 0; seeds 1–9 and
the review-driven design change/retraining remain unmeasured in this unit.

The first final browser assertion failed because Python's `.5g` generated
`0.52` while JavaScript's `toPrecision(5)` displayed `0.52000`. Parsing the
visible numeric time instead passed, including actual playback, three refreshes,
full matching-byte download and labels. The initial experiment harness exited 1
**after successful training and video rendering**; collection of those existing
artifacts passed without another trainer, import or render. This distinction is
retained in `probe3-experiment-result.json` (`training_exit=0`,
`initial_experiment_exit=1`, `collection_exit=0`) and its original failure log.

The subsequent browser retry/history check passed: `probe3` is `ok`, telemetry
is `done`, and both reward/loss curves have 240 points; `probe2` remains failed
with stale telemetry. Probe1 playback, probe2 checkpoint and both probe3 videos
all load at their own recorded revisions. Its initial harness assertion checked
page-poll freshness instead of training-telemetry staleness; using the telemetry
panel correctly passed. Evidence: `probe3-retry-browser.json`,
`probe3-summary.json`, final browser log and project-local publication receipts.
This supplies D8's successful new attempt following the real interruption and
D4's active intermediate plus final video evidence. It does not complete the
D5–D9 design-change/copy/restart lifecycle or measure an encoder crash.

The full serial CLI gate passed:
`pixi run python -m pytest cli/tests -q` — **361 passed, one skipped**,
297.44 seconds, exit 0. No product-code change or build was needed for this
experiment. Both product and external-project `git diff --check` passed.
External project commit `7a597cc` closes the experiment evidence and progress
entry; preceding CLI commits retain each accepted import/declaration/rollout.

## Real saved-project reopen and restart (D6, completed-run portion)

The saved probe3 project passed an engine/dashboard restart experiment:

```bash
PYTHONPATH=cli:cli/tests pixi run python "$PROJECT/evidence/d6-reopen.py" "$PROJECT"
```

The harness uses the public `open_project` protocol with `restore=true` in two
separate cadexd processes, shuts each down, stops the real `cadex review`
command and restarts it on the same port. The already-open Chromium page reports
stale while the server is down and recovers without navigation; a new browser
page then reopens the selected project. This test binds loopback on the server
machine; private-address reachability is evidenced separately above.

Both engine restores report `performed=true`, `matches_accepted=true` and
accepted digest `14d56ed42ef87185db899cb2485180a81f8eb0959aaf2f8356c7031760a6ebb1`.
The accepted revision remains
`a7ee956cafc8de6b1732bc83cb3f59d832a6fe46b5406f3624e88267f479fa2d`.
Before/after browser observations agree on the complete run list, selected
revision/digest, displayed parameters, project-document links, historical label
and loaded model statistics for `probe3`, `probe3-checkpoint20` and
`probe3-final`. Each model produces more than 1,000 non-background pixels.
Probe3 retains 240 points in each reward, loss and episode-length history;
checkpoint and final videos play with advancing browser time and download with
the same SHA-256 values recorded above. All **255 files** under retained runs,
assets and design documents, plus script source and project decisions, remain
byte-identical. The comparison excludes staging caches and checks the accepted
manifest semantically, removing only `updated_at`, cache `attempt_id` and
`staging` fields. Every other manifest field remains equal.

The harness initially made three incorrect assumptions: it read a video digest
from the wrapper rather than `videos[0]`, attempted unmuted autoplay without a
browser gesture, and expected cache attempt metadata to remain byte-identical
on engine restore. Correcting these assertions and muting browser playback
produced the pass; no product code changed. The three failure logs are retained
beside `evidence/d6-reopen.py`, `d6-reopen-result.json` and `d6-reopen.log`.
The result includes both engine replies, process IDs, browser observations and
the retained-file hash inventory. No training, policy import, authoring or
rendering was performed in this experiment.

Headless edits are saved when accepted; there is no separate `save_project`
protocol operation. This checks the saved acceptance from probe3's final
playback through actual engine restore, rather than issuing a new authoring
transaction and calling that a save. The automated fixture restart regression
also passed: `pixi run python -m pytest cli/tests/test_review_lifecycle.py -q`
— **1 passed**, 7.37 seconds, with Chromium and FFmpeg available. No engine,
CLI or shell code changed, so no build or full zone-suite rerun was needed;
the immediately preceding full-suite results remain reported above.

D6 remains open for the **real dashboard restart during active training**.
That check belongs in the upcoming design-change retraining and must prove the
same trainer continues without duplication. This completed-run experiment does
not claim that requirement, a new design revision, copy isolation, or a
second-device test.

## Ten-seed baseline before the design edit (D9)

The retained checkpoint20 and final policies were evaluated through the public
CLI on seeds **0–9**, each with the original **8-second / 400-step** episode.
The [evaluation harness](probes/reed-baseline/evaluate.py) creates an independent
whole-project copy and changes only the playback policy declaration and rollout
seed. Run it from the product repository with a stopped source project and a
destination that does not exist:

```bash
python3 docs/probes/reed-baseline/evaluate.py \
  ~/cadex-projects/ot5-biped ~/cadex-projects/ot5-biped-baseline-seeds-v2
```

The command exited 0 with **20 real engine rollouts**. Each accepted script
transaction verifies the policy witness. All model, task and policy hashes
match the retained reference for that policy; both seed-0 trace objects equal
the previous saved traces in full. The source project's non-Git file manifest
is byte-identical before and after. No training, rendering or browser change
was performed. The [compact results](probes/reed-baseline/results.json) retain
each seed's revision, trace digest, policy/model/task identity and measurements.
Full traces and CLI receipts live in the copied project's
`evidence/baseline-seeds/`; retain that directory with the copy.

| Policy | Falls / episodes | Observed seconds, mean (range) | Forward displacement mm, mean (range) |
|---|---:|---:|---:|
| checkpoint20, `74750cc6d8e7` | 0 / 10 | 8.000 (8–8) | 39.352 (34.295–45.941) |
| final, `a06b4bf489529` | 10 / 10 | 0.498 (0.48–0.52) | 200.854 (189.535–210.536) |

Displacement is last minus first published torso-link world X position, not
distance walked. Falls use the engine's `termination="fell"`; survival here
means reaching the episode limit without that declared termination, not a
separate physical assessment. The trace's sampled final pose need not be the
termination integration step. `truncated=true` means the episode reached its
time limit; the initial harness incorrectly rejected it, then passed after
checking that its end time is eight seconds. That initial copy and failure log
were retained outside the product repository.

The final policy's extra displacement comes with consistently short survival,
so it is not evidence of improved walking. A longer foot is a plausible single
parametric experiment to enlarge fore/aft support, but these measurements do
not establish why the policy falls or that this edit will help. Compare the
next design's retained policy on this same seed/episode set, keeping task and
training settings explicit. The physical edit and bounded retraining, new
verified video, two-design browser checks and live dashboard restart remain
open; this measurement alone does not tick D2, D5, D6 or D9.

## Review-driven foot-length revision (foot90)

The actor completed one 70 → 90 mm foot-length experiment through the public
CLI. Two product-agent prompts (default and `claude-sonnet-5`) were refused
with the provider's session-limit message before authoring. This is an explicit
fallback, **not a product-agent-authored revision**. Project ADR-005 and
`docs/design-specs.md` retain the rationale: test greater fore/aft support,
including the accompanying increase in foot mass/inertia, without assuming
an improvement. All other effective parameters are unchanged. The task JSON
changes only its model metadata; the model hash changes from `973dbfc260a4…`
to `3f84f92d3f57…`. Training acceptance is `cf98060cdac1…` /
`11394a342e1c…`; verified playback acceptance is `0596013572c6…` /
`395faa6bd23f…`.

From the product checkout, with `PROJECT` pointing at the external biped:

```bash
systemd-run --user --scope --unit=cadex-foot90 -p MemoryMax=20G \
  env XLA_PYTHON_CLIENT_MEM_FRACTION=0.45 \
  timeout --signal=TERM --kill-after=20s 2100 \
  ./cadex walk --project "$PROJECT" --out "$PROJECT/runs/foot90" \
  --set foot_len=90 --name foot90.cxpolicy --iterations 240 --envs 1024 \
  --seed 0 --timeout 1800 --leg-timeout 2000 --json
# While that independent command trains:
PYTHONPATH=cli:cli/tests pixi run python \
  docs/probes/reed-foot90/restart.py "$PROJECT" foot90
# After it finishes:
PYTHONPATH=cli pixi run python -m cadex_cli.video --project "$PROJECT" --run foot90
PYTHONPATH=cli:cli/tests pixi run python \
  "$PROJECT/evidence/check-probe3-video.py" "$PROJECT" foot90
PYTHONPATH=cli:cli/tests pixi run python \
  docs/probes/reed-foot90/history.py "$PROJECT"
# Stop all evidence writers before taking the evaluation copy:
python3 docs/probes/reed-baseline/evaluate.py "$PROJECT" \
  "$HOME/cadex-projects/ot5-biped-foot90-seeds-v2" \
  --run foot90 --evidence-directory foot90-seeds
```

The walk exited 0 after 240 GPU iterations (317.802 s reported training time).
The final policy is `4e573dd637af…`; all 32 witness samples passed, maximum
error `9.817e-08` against `0.0001`. The host cgroup enforced 20 GiB with an
independent timeout; thirty one-second samples observed a 5,060,366,336-byte
host peak and 15,084 MiB GPU use. These samples do not establish an unsampled
whole-run GPU peak. No other training run was started.

The real dashboard restart passed on the same machine's private address:
trainer PID and `/proc` start ticks remained identical, exactly one trainer
was present, and committed iterations advanced 35 → 43. The same Chromium
page labelled the outage stale, recovered automatically, and showed iterations
37, 39, 41 and 43 with growing loss histories and no navigation. This supplies
the previously missing active-training part of D6; it does not claim a
second-device test.

**A remaining D2 defect was exposed:** ordinary `walk --set` retained a
training view with `available: false`, reason `accepted attempt retained no
tessellation`. The first restart probe failed because it expected a loaded
model. Its corrected observation records the missing-model label and tests
restart independently. The trainer continued through both attempts. The
completed run's actual rollout model loads successfully, but this does not
repair or replace the missing pre-training snapshot. The earlier probe3
harness explicitly rendered before retaining that snapshot; the ordinary walk
path does not. Preserve this failure for a targeted product fix.

The final saved video decoded to six distinct-endpoint 512×512 frames at
10 fps: 0.6 encoded seconds for 0.5 simulated seconds, seed 0. Chromium played
it across three refreshes and downloaded bytes matching SHA-256
`1e17ab439a024be0908764aa00a90c2bb9999816c8a2d412dfa3c9c0b36719b7`.
Historical `probe3-final` and revised `foot90` both passed orbit/zoom, identity,
retained design-spec content, video playback and download checks. The browser
fetched each run's actual foot STL, matched it to retained bytes and measured
70 and 90 mm respectively. The baseline is visibly historical. This advances
D2/D5's two-design review evidence while leaving the live-model defect open.

The independent-copy ten-seed evaluation reproduces seed 0 exactly and pins
every policy/model/task digest. Results (`probes/reed-foot90/results.json`):

| Final policy | Eight-second survivors | Falls | Mean observed seconds | Mean +X displacement |
|---|---:|---:|---:|---:|
| probe3, 70 mm feet | 0/10 | 10/10 | 0.498 | 200.854 mm |
| foot90, 90 mm feet | 1/10 | 9/10 | 1.338 | 160.842 mm |

Foot90's nine falls occur at 0.50–0.80 s; seed 9 survives eight seconds with
43.370 mm displacement. This is still poor gait, not repeatable walking or
proof of a general improvement. The baseline checkpoint20 remains the more
reliable survivor in this declared seed set. No warm start was used.

The first history harness assumed binary STL and read the document-link list
as document text; both assumptions were corrected and the real browser check
rerun. An initial evaluation overlapped that browser's evidence write and
correctly failed its source-unchanged assertion. The successful fresh-copy
rerun starts after all writers stop. Initial logs/copies remain external.
All 250 pre-existing run/asset files retain their hashes. Compact evidence is
`probes/reed-foot90/evidence.json`; full outputs, video, traces and project
history remain outside this repository. Copy the whole project, including
ignored review artifacts. CLI regression suite: **362 passed, 1 skipped**.
No engine, shell or protocol code changed and no build was performed.

## Independent real-project copy (D7)

Copy a stopped project with the whole-directory command in `docs/CLI.md`;
retain hidden files, Git history, checkpoints, videos and traces. This pass uses
`ot5-biped-copy29`, copied from Reed after foot90. A SHA-256 inventory of every
file is retained in the copy's `evidence/copy29-before.json`. The source has no
active authoring, training or rendering process during this operation.

To reproduce the initial inventory and copy with an absent destination, run
this before any edits (set `SOURCE` and `COPY` to the external project paths):

```bash
python3 - "$SOURCE" "$COPY" <<'PYTHON'
import hashlib, json, subprocess, sys
from pathlib import Path
source, copy = map(Path, sys.argv[1:])
assert source.is_dir() and not copy.exists()
def inventory(root):
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in root.rglob('*') if p.is_file()}
before = inventory(source)
subprocess.run(['cp', '-R', str(source), str(copy)], check=True)
assert inventory(copy) == before
(copy / 'evidence/copy29-before.json').write_text(json.dumps(before, sort_keys=True))
PYTHON
```

The product-agent request to change the copy's feet from 90 to 100 mm was
refused on session quota before authoring. The copy's ADR-006 and design specs
explicitly record the actor's parameter fallback. The hypothesis is greater
fore/aft support, with increased foot mass/inertia; the nine foot90 falls in
ten seeds motivate a test but establish no improvement. This run tests copy
independence; it does not supply a new ten-seed gait comparison or satisfy D9's
product-agent revision requirement.

Commands from the repository root (`COPY` is the external copied project):

```bash
systemd-run --user --scope --unit=cadex-copy29 -p MemoryMax=20G \
  env XLA_PYTHON_CLIENT_MEM_FRACTION=0.45 \
  timeout --signal=TERM --kill-after=20s 2100 \
  ./cadex walk --project "$COPY" --out "$COPY/runs/copy100" \
  --set foot_len=100 --name copy100.cxpolicy --iterations 240 --envs 1024 \
  --seed 0 --timeout 1800 --leg-timeout 2000 --json
PYTHONPATH=cli pixi run python -m cadex_cli.video --project "$COPY" --run copy100
PYTHONPATH=cli:cli/tests pixi run python docs/probes/reed-copy/verify.py \
  "$HOME/cadex-projects/ot5-biped" "$COPY"
```

The [isolation probe](probes/reed-copy/verify.py) requires stopped writers and
an unchanged original inventory. It temporarily renames the source directory,
restores it in `finally`, reopens/exports the copy through the real engine with
its accepted revision and digest unchanged, and runs a new private-address review server with
headless Chromium against the copy. It compares the 70, 90 and 100 mm models
with retained STL bytes, declared parameters, exact saved design specs and
revision/digest identities; exercises orbit/zoom; checks all three training
curves; and plays/downloads each final video. Earlier designs must display
HISTORICAL. The additional video check decodes the new video and compares its
frame count, timing, policy/revision labels and download digest. The probe
checks every original file again after restoring the source. Bulk outputs
remain in the copy's `evidence/` and `runs/`; keep them with the project.

**Result: D7 has real lifecycle evidence.** The walk exited 0 after 240 GPU
iterations (324.882 seconds reported training time; 418.39 seconds for the
whole training leg). All 32 engine witness samples passed, maximum error
`9.154e-08` against `0.0001`. A cgroup sample recorded a 5,070,766,080-byte
peak with `MemoryMax=21,474,836,480`; this is a sampled peak, not a claim about
unsampled GPU memory. No other biped training or warm start occurred.

The separate private-address browser showed the accepted training model at
iteration 32 with 33 points in all three curves. After final recording, the
source-unavailable engine and browser checks passed. All **1,206 original
files**, including Git history, remain byte-identical, and all **322 inherited
run/asset files** match in the edited copy. The original was restored to its
normal path. Each of the three browser views retains its own model/spec identity,
240-point curves and playable/downloadable video. No second-device test is
claimed. The copy's accepted revision is `25d9b6ab7472…`; policy digest is
`9e1674abf4dd…`. Its final video SHA-256 is
`2308fe3baa4d0a5a2256a37deadfa798256ab6cca978ff8daeacc56c76a2ab24`.
It decodes to eight 512×512 frames at 10 fps, 0.8 encoded seconds for 0.62
simulation seconds, with distinct endpoint frames. On seed 0 the policy falls;
this single episode does not establish a ten-seed gait result.

[Compact evidence](probes/reed-copy/evidence.json) records exact identities,
measurements, browser observations and the full original-inventory digest.
The complete inventory, CLI receipts, renderer logs, browser screenshots and
original video-checker source remain project-local in `evidence/`. D9's
product-agent revision authorship remains unproven after the quota refusal.
No product implementation, engine, shell, protocol, payload or dependency changed.

Validation: `pixi run python -m pytest cli/tests` passed **363 tests, one
skipped**, in 305.12 seconds, after the biped trainer exited. Focused lifecycle
browser tests passed 2/2, review/record/video tests passed 57 with one skip,
and command tests passed 23/23. An earlier full-suite attempt was interrupted
to prevent its toy training from overlapping the biped. That interrupted run
showed one command-test failure without a completed diagnostic; its cause was
not established, and the isolated and full reruns both passed. Probe compilation
and `git diff --check` passed. No engine-suite rerun or build was required for
this documentation/probe-only unit.

## Missing and partial video recovery on the copy (D8, ADR-295)

The next product-agent request supplied the recorded ten-seed 70/90 mm
comparison and asked it to choose and author one reasoned physical revision.
It exited 1 on the session limit before authoring (model `claude-sonnet-5`).
D9 remains open; no actor-authored substitute or new training was performed.
The full request receipt is retained in the copy's
`evidence/revision30-agent.json`; the compact evidence records the refusal.

Run this against the stopped independent copy, with no video renderer active:

```bash
PYTHONPATH=cli:cli/tests pixi run python docs/probes/reed-copy/video_recovery.py "$COPY"
```

The probe temporarily moves copy100's real video to a backup, checks the
missing label and HTTP refusal, writes a 64-byte truncated file, checks the
refusal and CLI recovery message, then restores the backup. The same Chromium
page must resume playback and download the recorded SHA-256 without a reload;
foot90's prior completed video must remain available. A `finally` block restores
the original file even on assertion failure. Keep the whole project and its
retained inputs; an actual lost file can be regenerated with the documented
`python -m cadex_cli.video --project "$COPY" --run copy100` command.
This probe restores saved bytes; it does not claim to have rerendered them.

The first pass failed at the truncated-file label: the reader checked existence
but not the recorded video digest. ADR-295 fixes that defect. The corrected
private-address, same-machine browser pass observed missing refusal, partial
refusal, and restored playback/download. **418 copied run/asset/history and
accepted-script files** remained byte-identical; a separate inventory check
confirmed all **1,206 original project files** still matched the pre-copy
inventory. Video SHA-256 remains `2308fe3baa4d…`. No second-device test or
training-concurrency claim is made. [Compact evidence](probes/reed-copy/video-recovery.json)
contains the outcomes and quota limit; full outputs remain project-local.

The focused browser/server suite passed 27 tests with one skip. A local
100-read measurement of copy100 averaged 1.36 ms per `read_run_record`
with integrity verification; this short-video measurement does not establish
long-video or concurrent-training performance. Verification streams fixed-size
chunks but reads the recorded video bytes on each request.

Final validation: `pixi run python -m pytest cli/tests -q` — **364 passed,
1 skipped** in 329.64 s; `pixi run test-engine` — **2,103 passed, 54 skipped**
in 281.57 s. Probe compilation and `git diff --check` pass. No full build or
packaged/shell gate was run; no engine, protocol, payload or shell code changed.

## Product-agent shin-length revision and its recorded experiment (D9, D10)

The product agent, on the project's stored model `claude-sonnet-5`, authored
the design revision this time. A one-word capacity probe preceded the request,
as the earlier refusals suggested. The prompt (retained as
`evidence/agentrev.prompt.txt`) gave it the recorded 70/90/100 mm foot
results and asked it to choose exactly one physical geometry revision it could
justify, keep the task semantics unchanged, turn `policy_on` off first, record
the reasoning in the project's decisions and design specs, and not train:

```bash
timeout --signal=TERM --kill-after=10s 900 ./cadex --project "$COPY" \
  --out "$COPY/evidence/agentrev" --json -p "$(cat "$COPY/evidence/agentrev.prompt.txt")"
```

It chose to shorten the shin, `shin_len` 80 → 55 mm, keeping the 100 mm
feet and everything else, on the stated mechanism that the rigid-ankle
biped's forward-pitch recovery is bounded by the unchanged 200 N·mm hip/knee
torque against a gravitational tipping torque that scales with CoM height
(203 → 178 mm), whereas the three foot-length probes only widened the base of
support. Its receipt is `evidence/agentrev-agent.json` (exit 0, accepted
revision `fe266d481062…`, digest `a0dc163fde65…`, `policy_on` 0, all other
parameters unchanged); project ADR-007 and the design-specs entry are its own
words, committed by the CLI as `af0339d`. This is the product-agent-authored,
review-supported revision D9 was missing. The training model hash changed
from copy100's; the task JSON differs only in its model metadata.

`evidence/shin55-experiment.py` then ran one bounded GPU training on that
revision — 240 iterations, 1024 environments, seed 0, checkpoints every 20,
an independent 1800 s timeout and a 20 GiB host cgroup cap, no warm start —
and published from it. Unlike the probe2/probe3 harnesses it observes the
**persistent operator server on port 8765**, never a temporary one:

```bash
PYTHONPATH=cli:cli/tests pixi run python "$COPY/evidence/shin55-experiment.py" \
  "$COPY" shin55 "http://$(tailscale ip -4):8765/"
```

**Persistent dashboard at experiment start (D10).** The server listed
`shin55` as `running` on its next request, before the trainer's first
iteration. `evidence/agentrev_observe.py` opened the persistent URL fresh:
without a click, the page selected **RUN shin55** (`Current run: shin55`),
labelled CURRENT at revision `fe266d481062…`, loaded its retained model,
and passed orbit/zoom. It then saw page iterations 3, 4, 6, 7, 9, 10, 11
appear within **0.26–1.69 s** of their commit, one navigation, live
freshness, with reward, loss, episode-length and curve-point counts all
changing (`shin55-observe.json`). The observer's exit did not touch the
trainer.

**Checkpoint video while training.** Checkpoint 20 (policy
`4745829c6f80…`) passed the engine witness check at 3.66e-08 against 1e-4,
rolled out seed 0 for the full 8 s without a fall, and was retained as
`runs/shin55-checkpoint20` with its own script, specs, trace, model and
render. Its video (`89bfc9ecde0e…`, 81 frames, 10 fps, 8.1 s encoded for
8.0 s simulated, style `cadex-prototype-light-v1`) rendered in **14.2 s**
and passed decode, persistent-URL playback across three polls, matching
download and the revision/policy/seed/time labels while the trainer was
still active (committed iteration 18 before the publication, 34 after it).
The harness deliberately waited for the trainer to be back in ordinary
iterations (23) before rendering, so the window measures throughput rather
than the checkpoint's own publication cost: nine committed intervals fell
inside the 14.2 s render, median **1.414 s** (max 1.463 s), against a median
of **1.438 s** for the non-checkpoint intervals in the 90 s before it and
**1.341 s** in the 90 s after it. Under
these conditions the shared-scene renderer's overhead on GPU training was
not measurable; the trainer's own checkpoint publication (one ~53 s
interval at each boundary) dominates. This is one same-machine measurement,
not a general claim.

**A review defect this exposed (ADR-302).** The retained training view drew
five of Reed's eight parts — the left thigh, shin and foot were "mesh
missing" — because the accepted model mapped each BREP digest to one output
name, and a mirrored pair of identical boxes shares a digest. `copy100` and
`probe3` had frozen four of eight the same way. The fix and its regression
landed in this pass; frozen views from earlier runs stay as recorded.

**Final policy and the ten-seed comparison.** The trainer exited 0 on the
GPU after 850 s wall clock for the whole run (240 iterations, last index
239, reward/step 0.508, loss 2.37, estimated episode length 930.9 steps;
sampled host cgroup peak 8.28 GB, GPU peak 15,134 MiB). The final policy
`609ef8e83c18…` passed the witness check at 7.03e-08 and is retained as
`runs/shin55-final` with a 6-frame, 0.46 s video (`c23508ad3e92…`) that
passed the same decode/playback/download checks on the persistent URL.
All nine earlier `run.json` records are byte-identical to before the
experiment. The independent evaluation copy `ot5-biped-shin55-seeds`
(`docs/probes/reed-baseline/evaluate.py --run shin55-final`) reproduced the
seed-0 trace exactly and left the source unchanged:

| Design (final policy, seeds 0–9, 8 s) | Falls | 8 s survivors | Mean duration | Mean forward torso displacement |
|---|---:|---:|---:|---:|
| 70 mm feet (probe3) | 10 | 0 | 0.498 s | 200.9 mm (all during falls) |
| 90 mm feet (foot90) | 9 | 1 | 1.338 s | 160.8 mm |
| 100 mm feet + 55 mm shins (shin55) | 4 | 6 | 5.034 s | 79.1 mm |

The shin55 falls come at 0.44–0.90 s on seeds 0, 2, 5 and 6; the six
survivors end 44.7–49.5 mm forward, which is the same standing shuffle the
70 mm checkpoint 20 showed (39.4 mm), not a walking gait. So the product
agent's review-driven change measurably improved survival on the common
seed set and did not produce repeatable walking; both halves are the
recorded result. Compact identities: `docs/probes/reed-agentrev/evidence.json`.

**Persistent dashboard at completion and after the fix.** A fresh visit to
the persistent URL after the trainer exited opened **RUN shin55-final** by
default at revision `67b5000f3de1…`, played and downloaded its video with
the recorded digest, kept playback through a poll, showed `probe3-final`
as HISTORICAL on request and returned to the current run
(`evidence/shin55-operator-final.json`). The service was then restarted once
to load ADR-302; the accepted model now retains all eight meshes and the
same operator check passed again (`shin55-operator-restart.json`). The
restart happened after training, deliberately: D6's restart-during-training
evidence already exists and no run was active.

## Lifecycle report (D9)

The whole recorded lifecycle — every step above in order, the D1–D8
evidence each rests on, the twelve retained run identities with the model
view the page serves for each, which training snapshots are incomplete and
why, and the four-design common-seed comparison — is assembled from the
project's own records by `docs/probes/reed-lifecycle/report.py` and written
up in [`docs/probes/reed-lifecycle/README.md`](probes/reed-lifecycle/README.md).
`cli/tests/test_lifecycle_report.py` holds the committed report to its
evidence. The persistent operator URL was checked again while generating it:
`shin55-final` selected by default, historical `probe3-final` playable, and
a route back to the current run.

## Second fresh project: Wren

Iteration 46 repairs the previously unrecorded Wren probe and verifies
`ot5-wren` at accepted revision `5309bebc6597…` on the persistent port 8765.
[Receipt and limitations](probes/wren-fresh/README.md): eight drawn components (seven biped solids plus ground),
twelve declared defaults, pointer orbit/zoom, empty run state across polling,
and two accepted-identity engine reopens on a disposable full copy. Both Reed
projects remain byte-identical across this probe. At that point Wren had no training or
videos; this is the opening slice of the repeated lifecycle, not another
completed D9 lifecycle. In-place restore was found to replace retained
attempt artifacts without tessellation; the successful receipt deliberately
checks copy reopens and read-only browsing separately.


Iteration 48 fixed in-place restore preservation (ADR-303), with Wren's
retained display bytes unchanged across two engine restores. Iteration 49
then completed Wren's first bounded real GPU experiment, `wren1`, on the same
persistent private-network dashboard. See the [experiment command and evidence](probes/wren-fresh/README.md).
The observer has verified real telemetry updates without reload, and checkpoint
20 has a witness-verified rollout and browser-verified video published while
training was active. The final policy also has a verified video and was selected
by default then: it fell at 0.46 s on seed 0, whereas checkpoint 20 survived 8 s.
Both remain reviewable. This extends the repeated lifecycle; it does not yet establish Wren's
design-change/retraining comparison or independent-copy lifecycle.

Iteration 52 completes the [Wren design-change/retraining comparison](probes/wren-fresh/COMPARISON.md)
after iteration 50's public CLI foot edit from 85 to 105 mm. The persistent
server now defaults to `wren2-final`, revision `26332a5955e3…`; both revised
policies have verified videos and the checkpoint video played during training.
On the declared seeds 0–4, eight seconds at 50 Hz, the original final falls
2/5 times and the revised final 0/5; both checkpoints survive all episodes.
Mean torso displacement is small, so this is not a walking claim. All 114
original run files remain byte-identical and all four recordings pass browser
playback/download. This is a CLI parameter revision of a product-agent original,
not a product-agent revision turn. Wren-specific independent-copy and controlled
interruption evidence remains outside this unit; Reed's prior evidence stays
separate. The operator server keeps running.
