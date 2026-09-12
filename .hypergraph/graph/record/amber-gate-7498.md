---
node_id: beca70bf-071d-5d48-9f6a-c777883d96b3
slug: amber-gate-7498
title: Fresh biped final policy verified, retained and played in the browser
created_at: '2026-09-12T17:57:34+00:00'
parents:
- lively-gate-6535
summary: ''
artifacts:
- docs/HEADLESS-BIPED-REVIEW.md
---
## What

Recovered the fresh biped's retained final policy into a separately recorded,
engine-verified rollout and its first real retained browser-playable video.
Updated docs/HEADLESS-BIPED-REVIEW.md with commands, measured identities,
provider refusal, recovery provenance and explicit limits. The external
project's commits 842c2ea, 8be0602, e11dd72 and c6a9dc8 retain the script
change, acceptance, render and recording/browser evidence respectively.

## Why

One D4 unit (candid-harvest-2614), following the critic's retained-policy
recovery request. Two explicit deviations: this dispatch forbids reconcile
without exception, so I did not reconcile the stale plan despite the critic's
request; the next authorized reconcile must replace retired clearance work
with this charter's D1-D9 frontier. The product-agent repair was attempted,
but the default model and a Sonnet probe both returned session-limit refusals
(the latter HTTP 429, reset reported at 5:30pm America/New_York). Rather
than wait on a clock, the actor authored the minimal playback-only edit via
cadex script --set. The original biped remains product-agent-authored; this
repair does not claim to be a successful product-agent turn. No training,
physical design change or completed walk is claimed.

## Method

- Project: ot5-biped under the operator's cadex-projects directory, outside
  this repository. Detailed commands in docs/HEADLESS-BIPED-REVIEW.md.
  Product-agent refusal: evidence/policy-switch.json and .log; alternate
  model probe: evidence/policy-switch-model-probe.json.
- Added policy_on=num(0, min=0, max=1, step=1) and one conditional
  assembly.policy/assembly.rollout block, the stored probe1.cxpolicy with
  its measured SHA-256, 50 fps, seed 0. Applied with cadex script --set,
  then cadex params --set policy_on=1 --out runs/probe1-playback/rollout,
  then cadex render. All three exited 0. No engine/product code changed.
- The new rollout's exported MJCF and task bytes equal probe1's retained
  training inputs. Engine receipt: 32 witness samples, error
  7.302745071768867e-08 < tolerance 0.0001. Policy SHA-256 remains
  01865c8e06aa8a1f7884053099fa988a3ae0be1e91a3511d11a3574ac46b3abe;
  model 973dbfc260a4268a1e97817d7846a8302325b7a6b823f70f274bb8723e557756;
  task 59508724bb6aef368fac7cc2c6cdfa11c342d8e1bec9d56c7698405b9376bfad.
- Accepted playback revision ddf021a4d3c06a403b2b3b3c83d5de3b19ef0132aab22db23992fd35f6f06610,
  digest 4213e25e49c6f11343c365cdf72123e2a9d2bb15aa89f5045fd684781eed324f.
  Real seed 0 rollout: fell, terminated_step 32, 33 control steps, 0.66 s
  out of eight declared seconds, total reward 169.94907921196852.
- Project-local evidence/retain-playback.py calls the existing CLI record
  writer on actual CLI envelopes, snapshots source/specs/docs and the
  component-source render summary, retains exported trace/model/meshes and
  copies original telemetry with explicit source_run probe1 provenance.
  Mode retained-policy-playback, only a successful rollout leg, no invented
  train leg. Original failed probe1/run.json SHA-256 unchanged. This
  experiment harness is not a new CLI recovery subcommand.
- PYTHONPATH=cli pixi run python -m cadex_cli.video --project "$PROJECT"
  --run probe1-playback: 1.621 s render, eight 512x512 frames at 10 fps,
  0.8 s encoded for the 0.66 s trace. Video SHA-256
  d0222e198ca79ae6cdc120cea7fba685a41592502cc768142ab49a7a432ae722.
- PYTHONPATH=cli:cli/tests pixi run python
  "$PROJECT/evidence/check-playback.py" "$PROJECT": passed on actual
  artifacts. FFmpeg decoded all eight frames with first/last different,
  ffprobe timing matched; headless Chromium over the private Tailscale
  address played the video across three dashboard refreshes, checked
  revision/policy/seed/simulation time labels and downloaded matching bytes.
  Selecting probe1 still showed failed with no video. Same-machine private
  address only, no second-device claim. Evidence/probe1-video-check.json
  and a screenshot retained locally; video.json retained with the run.

## Result

The first real final-policy video now exists and plays/downloads from the
inspection dashboard. D4 advances but stays open: no intermediate checkpoint
was rendered during active training and no training overhead was measured.
D9 now has one verified rollout and one honestly failed gait measurement,
not a seeds 0-9 comparison or a review-driven design change. Probe1 remains
failed; the playback is a separate successful recording of the same policy.
No dependencies, engine builds or protocol/payload/shell changes. Video and
trace remain outside this product repository and must travel with the project;
Git ignores are not retention permission. The product-agent quota failure
remains observable, and this actor edit does not prove its prompt is fixed.

Verification: full CLI suite 358 passed, 1 skipped in 339.81 s; standing
engine suite 2103 passed, 54 skipped in 314.10 s; both exited 0. Real
browser/decoded-video check passed twice (second pass after snapshotting
the recovery decision, with the screenshot scrolled to the video).
Git diff --check clean. No D checkbox is claimed complete.

Dispatch closed: 1 unit — recover, verify, retain and browser-check the fresh biped's first real final-policy video.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot5
- commit: f5364608dd64959bdbb81689428de13696b72adf

## State Impact

- target: candid-harvest-2614 — First real final-policy video exists for ot5-biped in probe1-playback: retained probe1 policy verified against identical model/task bytes, seed 0 fell at 0.66 s, eight decoded frames at 10 fps and 0.8 s encoded, private-address Chromium playback across refreshes and byte-identical download passed. Remains open: no intermediate checkpoint rendered during active training and no training-overhead measurement.
- target: silent-river-6649 — Fresh biped now has a verified seed-0 rollout and retained playable final-policy video, separate from unchanged failed probe1. Product-agent repair hit quota; actor applied playback-only switch through CLI. No physical design change, new training, seed-set comparison or complete lifecycle is claimed.
- target: plan/young-crane-9546 — The next authorized reconcile must replace the retired clearance-first priority with the owner D1-D9 mission. Retained final-policy playback now works; prioritize the remaining active-training intermediate video and real lifecycle evidence, not clearance or parked catalog work. This contributor dispatch explicitly forbade reconciliation; no plan or state node was edited.
