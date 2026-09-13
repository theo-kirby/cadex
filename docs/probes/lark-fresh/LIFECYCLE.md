# Lark lifecycle review

Verified against source: 2026-09-13. [Cadex-new]

Lark has completed creation, save/reopen, training, recording, a product-agent
revision, retraining and an independent working-copy retry. **D9's lifecycle
report is now assembled below.** The persistent dashboard serves
**ot5-lark-copy85 / lark86-retry-video**, accepted playback revision
`7f6c23913d55…`, with 45 mm torso and 90 mm feet. The current browser check
and reference comparison passed in iteration 94 without restarting the service
or training. Lark-specific repeats of two failure/restart checks remain absent;
they are identified below rather than credited from another biped silently.

## Open and interpret the project

Open `http://<tailscale-ip>:8765/`, using `tailscale ip -4` on the server to
obtain its private address. The existing `cadex-operator-review` user service
owns that port and remains running. The standalone one-project command is:

```bash
./cadex review --project "$HOME/cadex-projects/ot5-lark-copy85" \
  --host "$(tailscale ip -4)" --port 8765
```

Do not start a second listener on the occupied port. The browser only inspects;
authoring and training use the CLI. Select a retained run to inspect its model,
parameters, documents, curves and videos. HISTORICAL refers to that run's
recorded revision, not today's accepted model. **Current run** returns to the
latest attempt; a newer failure is not replaced by an older successful video.

## Recorded lifecycle and comparison

1. [Creation and in-place reopen](README.md#what-happened-iteration-80): the
   product agent created Lark from an empty project, without prior mechanisms,
   checkpoints or history. Eight component links, six joints, twenty parameters
   and authored design/actuator/sensor notes were accepted. The first-view
   defects and their ADR-311/312 fixes are disclosed in that report.
2. [First training](README.md#first-bounded-real-training-probe-lark1-iteration-82):
   `lark1` completed 240 GPU PPO updates. Its verified checkpoint video appeared
   while training was active; its final video also played and downloaded.
   Both fell within one second on seed 0, motivating a review-driven change.
3. [Agent revision and retraining](REVISION84.md): the product agent inspected
   the results and reduced `torso_h` from 70 to 45 mm, documenting the balance
   hypothesis and electronics-volume tradeoff in project ADR-004 and design
   specs. `lark2` completed the same 240-update budget and retained both videos.
   All 125 pre-revision run/asset files remained byte-identical.
4. [Independent copy](COPY85.md): the whole project was copied to
   `ot5-lark-copy85`, the persistent service deliberately switched to it, and
   the CLI changed feet from 80 to 90 mm with policy disabled. The original
   path was unavailable during the edit, two engine restores and two-server
   browser review of all six retained runs and four videos. The original's
   1,852-file inventory, including git, was unchanged. This copy edit was
   caller-authored, distinct from the product-agent torso revision.
5. [Interruption and successful new attempt](INTERRUPTION86.md): a real GPU
   attempt stopped by SIGINT at iteration 5 remained visibly failed with six
   curve samples and CLI retry guidance. The new `lark86-retry` completed 40
   updates; its verified seed-0 policy video became `lark86-retry-video`.
   All 250 earlier run/asset files survived; the original's 1,419 non-git files
   remained unchanged after copy retraining. The original path was restored
   before this training; original-unavailable training is not claimed.

Each comparison below uses the policy's own retained model/task/script,
seeds **0–9**, **8 seconds**, **50 Hz**, at most **400 control steps**.
Seed-zero evaluations reproduce the retained traces exactly. Torso X is net
position change, including falling; survival is simulation duration, not the
trainer's batch episode estimate. [Per-seed identities and measurements](revision84-evidence.json)
retain model, task, policy and trace hashes.

| Policy | Torso mm | Mean torso X mm | Mean / minimum survival s | Falls / 10 |
|---|---:|---:|---:|---:|
| lark1-checkpoint20 | 70 | +8.7 | 6.58 / 0.78 | 2 |
| lark1-final | 70 | +190.2 | 0.51 / 0.50 | 10 |
| lark2-checkpoint20 | 45 | +24.4 | 8 / 8 | 0 |
| lark2-final | 45 | +34.8 | 8 / 8 | 0 |

The revised policies survive all ten episodes. One training seed per design
cannot isolate geometry from training variance; 35 mm in eight seconds is
standing/shuffling, not demonstrated walking. The 40-update copy retry is
not part of this equal-budget comparison and has only a seed-0 review.

## D1–D11 evidence and limits

| Criterion | Concrete evidence | Acceptance scope |
|---|---|---|
| D1 reachable | [Creation browser receipt](evidence.json), [current receipt](current94-evidence.json), command above | Headless Chromium on the same machine through its private address; no second-device test. |
| D2 model/specs | [Creation/reopen](evidence.json), [six historical models and curves on the copy](copy85-evidence.json), [current parameters/revision](current94-evidence.json) | Own retained identities, eight components, declared specs, real orbit/zoom; no historical rebuild using today's script. |
| D3 live training | [lark1](training-evidence.json), [lark2](training84-evidence.json) | Seven actual page updates each; commit-to-page latency 0.39–1.52 s and 0.24–1.62 s, respectively, under recorded conditions. |
| D4 videos | Same two training receipts; [retry](interruption86-evidence.json); [current full decode/playback/download](current94-evidence.json); [encoder failure during real training](render98-evidence.json) | Intermediate recordings played while training remained active and finals persisted. [RENDER98.md](RENDER98.md) repeats real encoder-failure isolation on Lark: the failed re-render was shown with retry guidance beside the still-available recording, `lark2-final` kept playing, and the sole trainer kept its PID through recovery to completion. |
| D5 history after revision | [Agent revision/comparison](revision84-evidence.json), [copy browser history](copy85-evidence.json), [current historical selection](current94-evidence.json) | Both designs retain their own documents, configurations, curves, policy identities and videos; earlier bytes preserved. |
| D6 reopen/restart | [Two in-place creation restores](evidence.json), [two copy restores](copy85-evidence.json), [service restarts with retained Lark video](../operator-review/README.md) | Lark save/reopen and [restart during real GPU training](RESTART96.md) now have receipts: same trainer PID/start identity, increasing telemetry, preserved historical playback and completion on the persistent URL. |
| D7 copy independence | [Original-unavailable edit, restore and two-server review](copy85-evidence.json), [copy retraining isolation](interruption86-evidence.json) | Complete copy, four inherited playable videos, original inventory unchanged. Original path renamed, not made inaccessible by every filesystem route. |
| D8 interruptions/failures | [Real Lark interruption and successful retry](interruption86-evidence.json) | Failed status, explanation, new-attempt guidance and prior results preserved. [Lark missing/partial-video injection](VIDEO95.md) now verifies explicit guidance, preserved historical playback/download and recovery after restoring artifacts. |
| D9 whole lifecycle | Ordered history and same-seed table above; [agent authorship](REVISION84.md) | Fresh creation, agent revision, both GPU runs, saved videos, copy/retry and comparative results linked in one report. Poor gait is measured. |
| D10 current operator | [Copy switch](COPY85.md), [real interruption/retry start/completion](INTERRUPTION86.md), [current receipt](current94-evidence.json) | Stable port 8765, fresh default retry video, historical selection/polling and return-to-current; service remains active. |
| D11 visual reference | [Current Lark comparison](style94-evidence.json), assessment below; [earlier reference implementation](../review-style/README.md) | Same-pose/camera, decoded current video, retained checkpoint frame, close/wide and pointer orbit. No renderer change or new recording in iteration 94. |

## Lark reference-style assessment

The smallest new acceptance gap closed with this report is the missing current
Lark visual comparison. The [existing probe](../review-style/compare.py) used
neural-whoop commit `31caeb28abb3bdab8d9030bfc91f0c3f48ffa63a` read-only.
It decoded the shipped `render-examples/orbit_maneuver_policy.mp4` at 4 s
(SHA-256 in the receipt) and rendered Lark's truthful geometry through the
reference's unmodified light-theme scene/environment modules at equivalent
cameras. The shipped drone frame is dark-themed; it establishes the reference
layout, not the light palette. Generic filenames `reference-light-reed*`
contain Lark here. The delivered Cadex renderer remains self-contained.

Images and `side-by-side.html` are retained in the working copy's
`evidence/style94/`; [the compact receipt](style94-evidence.json) pins their
hashes. Visual inspection of `side-by-side.png` found:

| Property | Assessment |
|---|---|
| Floor/grid | Reference and Cadex share grey prototype tiles, metre labels and major/minor subdivisions. The finite turquoise plate is authored model geometry, not the presentation floor. |
| Horizon/fog/sky | Fit, 0.7× close and 3× wide views fade into a cool grey sky without a stage edge, wall or ceiling seam. |
| Materials/palette | Comparable matte coloured links and subdued ground; readable face shading without distracting gloss. |
| Lighting/shadows | Grounded shadows remain beside the feet on the plate in fit/close views. Cadex's shadow is slightly sharper than the reference. Wide shadows shrink with the subject; no detached shadow observed. |
| Camera/antialiasing | Equivalent occupancy and smooth edges in 512² frames. The retained camera includes the whole authored plate, so the biped occupies a small part of the fit frame; close framing improves legibility. Codec softening is visible but minor. |
| Viewport/video parity | Same-pose/camera viewport and capture PNGs are byte-identical. Decoded frame-zero RGB mean absolute error is **1.42898/255**, below the probe's 3/255 bound. |
| Orbit/scale | Real pointer drag changed yaw 0.8→2.6 and pitch 0.5→0.8; wheel zoom reached 780.57 and 4722.18 mm. Near/far model coverage remained 123,363/3,901 pixels. The presentation floor restaged without a visible edge. |

Current `lark86-retry-video` retains `cadex-prototype-light-v1`, policy
`074e22f1070c…` and video `1f53d43d1c18…`: 81 decoded differing frames,
10 fps, 8.1 encoded seconds for 8.0 simulated seconds, seed 0. It played
through three refreshes and downloaded hash-equal. The comparison separately
played/downloaded historical `lark2-checkpoint20`, preserved it through polling,
and returned to current. Full style identity and camera are in the receipt.
This is visual similarity evidence, not a new gait or live-training claim.

## Reproduce the read-only checks

From the checkout, with a new evidence label for a repeat:

```bash
PYTHONPATH=cli pixi run python docs/probes/review-style/compare.py \
  "http://$(tailscale ip -4):8765/" "$HOME/cadex-projects/ot5-lark-copy85" \
  "$HOME/neural-whoop" lark86-retry-video lark2-checkpoint20 style94
PYTHONPATH=cli:cli/tests pixi run python docs/probes/wren-fresh/check_video.py \
  "$HOME/cadex-projects/ot5-lark-copy85" lark86-retry-video \
  "http://$(tailscale ip -4):8765/" --label lifecycle94
```

Both passed. These probes start no trainer and do not restart the persistent
server. Raw receipts and screenshots stay project-local; committed receipts
omit the private host address. Retain the **whole project**, including hidden
history/accepted artifacts, assets, runs, inputs, telemetry, checkpoints,
policies, traces, video files/metadata and evidence. Stop writers before copying;
[COPY85.md](COPY85.md) documents the operation. A script or compact JSON receipt
alone cannot recreate retained policy bytes or historical review outputs.

## Handoff and remaining acceptance evidence

D9 now has a user-facing report; the current Lark D11 comparison gap is closed.
The owner retains checkbox authority. The complete charter has evidence across
Lark and earlier fresh bipeds, and since iteration 98 every D1–D11 receipt
this report links was produced on Lark or its working copy: D4 real
render-failure isolation no longer relies on Wren ([RENDER98.md](RENDER98.md)).
[D6 restart during real Lark training](RESTART96.md)
was repeated in iteration 96. D8 missing/partial-video
faults now have a [Lark copy recovery pass](VIDEO95.md), including preserved
historical playback and restored artifact access. No new training was justified for this reporting unit.

The D8 missing/partial-video bet was exercised in iteration 95; see
[VIDEO95.md](VIDEO95.md). The D6 real-training restart bet was exercised in iteration 96; see
[RESTART96.md](RESTART96.md). The D4 render-failure bet was exercised in
iteration 98 on a third real GPU run, `lark98`; see [RENDER98.md](RENDER98.md).
No Lark-only acceptance gap remains named in this report; what remains is the
owner's checkbox authority and the standing limits above (same-machine browser,
measured rather than good gait). No further provenance or D8 audit is needed.

Verification for this documentation/evidence unit: both headless browser probes
above passed; `pixi run python -m pytest cli/tests/test_lark_fresh_evidence.py -q`
passed **15 tests**; all 36 report file links resolve and `git diff --check`
passed. These existing tests guard the earlier lifecycle receipts, not the new
visual assessment. No product code changed; full CLI/engine suites and builds
were not rerun. The visual assessment rests on inspected images and the
assertion-bearing browser probe, not on the receipt tests.
