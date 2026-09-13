# Fresh Lark: create, save, reopen on the persistent dashboard

Verified against source: 2026-09-13. [Cadex-new]

**Iteration 88 (recording reliability, ADR-316):** the video checker's
run-name dependency is gone. `check_video.py` had hard-coded the
`-final`/`-checkpoint20` pairing, eight components and "a `-final` run is the
fresh visit's selection", which is why iteration 86's playback had to be
named `lark86-retry-video`. It now resolves the training run behind a video
and the older sibling to select from retained identities
(`cadex_cli.review_record.policy_lineage`: the run whose own `train/` retains
the policy bytes, with the record's `source_run` checked against it), the
expected fresh-visit selection from the reader's rule
(`cadex_cli.review_server.default_run`), every declared parameter from the
record, and the component count from the run's own trace. Regressions with
unrelated run names (`kestrel`, `pear`, `quince`, `zebra`, `aardvark`) are in
`cli/tests/test_review_record.py` and `cli/tests/test_review_server.py`. Both
Lark videos re-checked on the persistent working-copy URL without a restart:
`lark86-retry-video` (default; origin `lark86-retry`, final policy, no
sibling, so `lark2-final` is the historical run selected) and `lark1-final`
(not default; origin `lark1`, sibling `lark1-checkpoint20` at checkpoint
iteration 19 by identity), each decoded whole, played through three polls and
downloaded hash-equal. Receipt:
[`lineage88-evidence.json`](lineage88-evidence.json), guarded in
`cli/tests/test_lark_fresh_evidence.py`; the images and per-run receipts are
`evidence/*-lineage88-*` in the copy. No training, no new video, no server
restart.

**Current state (iteration 86):** the working project is the whole-project
copy **`ot5-lark-copy85`**, served on the persistent port 8765 with
`lark86-retry-video` selected by default. Iteration 86 completed Lark's D8
evidence on it ([INTERRUPTION86.md](INTERRUPTION86.md),
[`interruption86-evidence.json`](interruption86-evidence.json), ADR-315): a
real GPU attempt interrupted by SIGINT at iteration 5 and shown failed with
retry guidance, a successful 40-update new attempt, and that policy's
verified, playable, downloadable video, with every earlier result preserved
and the original `ot5-lark` byte-identical after the copy's retraining. The
driver, `interruption.py`, is the Wren one made project-agnostic.

**Iteration 85:** the copy was made and the persistent port 8765 switched
to it, with `lark2-final` selected by default as HISTORICAL against the
copy's own accepted 90 mm-foot, policy-off edit (revision `083d086ad980…`). The copy
proved D7 on Lark with the original path unavailable throughout the edit,
two engine restores and both browser checks, and `ot5-lark` (1,852 files)
is byte-identical to its pre-copy inventory. See [COPY85.md](COPY85.md) and
[`copy85-evidence.json`](copy85-evidence.json). Before that (iteration 84)
the product agent revised Lark from `lark1`'s measured results (`torso_h`
70 → 45 mm, project ADR-004), `lark2` retrained it under the same bounds,
and all four retained policies were compared on the declared seeds 0–9:
both 45 mm policies survive every episode where `lark1-final` fell on all
ten. See [REVISION84.md](REVISION84.md) and its receipts
[`training84-evidence.json`](training84-evidence.json) and
[`revision84-evidence.json`](revision84-evidence.json).

The exhaustion-policy clean-project repeat (charter `docs/…/goal.md`,
ADR-284): a **third** fresh biped project, `ot5-lark`, created by the product
agent in one `cadex -p` turn from an empty directory, with no import, link,
copy or conversation from Reed, Wren or any earlier mechanism, checkpoint or
policy. This unit is bounded to **creation, save and reopen**; training,
recording, revision and retraining follow in later units and are not claimed.

## What happened (iteration 80)

The product agent created and accepted Lark in one fresh conversation
(session `8357686c-ee1b…`, `claude-fable-5`, exit 0, 05:56:53Z to 06:02:03Z
UTC): a 238 mm, 0.596 kg biped of eight solids (`torso`, `thigh_l/r`,
`shin_l/r`, `foot_l/r`, `ground_plate`), eight component links, six joints,
one MJCF model and exactly one training task, accepted at revision
`753cf0cc4600…`, digest `3b704a3fc1c4…`, with **twenty** declared
parameters (the twelve asked for plus `servo_torque_nmm`, `joint_damping`,
`joint_armature`, `joint_friction`, `fall_frac`, `episode_steps`,
`control_hz` and `rollout_seed`; `policy_on` defaults to 0). It returned two
`DECISION:` lines (the project's ADR-002 and ADR-003) and design-spec,
actuator and sensor notes, which the CLI landed as `docs/design-specs.md`,
`docs/actuators.md` and `docs/sensors.md`. The script names no earlier
project or mechanism; `ot5-wren-copy54` (2,392 files), `ot5-wren` (963) and
`ot5-biped` (582) match their pre-creation inventories byte for byte.

The persistent private-network service on port 8765 was deliberately
switched from `ot5-wren-copy54` to `ot5-lark` and verified: project name,
accepted revision, zero runs. **Two review defects were exposed on the
fresh project** ([pre-fix receipt and screenshot](evidence.json)
`after_creation`):

1. **The dashboard refused the accepted attempt.** The page showed
   identity and twenty specs but `no model to show: accepted attempt's
   staging does not belong to the accepted revision`. The attempt's
   directory was named `91b312a2e73d…` — the revision the engine computes
   before the worker runs, over an empty spec cache — while the accepted
   revision includes the collected specs. The attempt's `result.json`
   carried the accepted digest. **Fixed (ADR-311)**: the reader now
   trusts the manifest's pin plus the attempt's digest over the directory
   name, with a regression in `cli/tests/test_review_server.py` that failed
   on the old reader. The service was restarted once, with no trainer
   running, to load it.
2. **The agent's turn retained no tessellation.** After the fix the page
   said `accepted attempt retained no tessellation`: `write_script` never
   asked for `display`. Not fixed in iteration 80: the documented public
   remedy, `cadex render`, republished the accepted attempt under the
   accepted revision with tessellation at unchanged revision and digest.
   Wren's creation had this same shape and its later rebuild hid it.
   **Fixed in iteration 81 (ADR-312)**: the bridge now injects the standard
   tessellation request on every modelling op, so a project straight out
   of `cadex -p` has a model to show. The regression in
   `cli/tests/test_review_server.py` writes a first script through the
   bridge on a fresh project through the built engine and asserts the
   dashboard draws it with no render present; it failed on the old bridge.
   Lark itself keeps the attempt `cadex render` republished — the fix
   changes nothing already accepted, and a fresh visit to the persistent
   URL after it is recorded in [`tessellation81.json`](tessellation81.json).

Then the create/save/reopen probe passed on the persistent URL: the page
loaded in 0.84 s, drew eight components (96 triangles, 41,840 non-background
pixels, style `cadex-prototype-light-v1`), listed all twenty parameters,
three decision headings and six documents, orbited under real pointer drag
and wheel zoom, and was screenshotted. Two fresh engine processes (PIDs
3654714 and 3654760) then reopened the project **in place** with
`matches_accepted: true`, keeping the accepted revision, digest, attempt and
contract and all 28 retained accepted-attempt files byte-identical. After a
poll of the still-open page and a fresh visit, the components, viewer
statistics, parameters, decisions and documents were identical to the
record, the eight served STL meshes and placements were byte-identical, and
the before/after viewport PNGs have the same hash
(`4ab7045fb646…`). Restore replays staged 36 unpinned candidate-attempt files
and the store pruned older unpinned ones; no source, history, document or
accepted-attempt file changed. This is a same-machine private-address
check, not a second-device test, and no training, video or gait claim.


## Commands

The creation turn, from the checkout, with the prompt retained beside its
receipt (the project directory did not exist before this):

```bash
P="$HOME/cadex-projects/ot5-lark"; mkdir -p "$P/evidence"
# write "$P/evidence/create.prompt.txt" (the retained prompt), then:
date -u +%FT%TZ > "$P/evidence/create.started"
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 timeout --signal=TERM --kill-after=30s 3600 \
  ./cadex -p "$(cat "$P/evidence/create.prompt.txt")" --project "$P" --json \
  > "$P/evidence/create.json" 2> "$P/evidence/create.stderr"
echo $? > "$P/evidence/create.exit"; date -u +%FT%TZ > "$P/evidence/create.finished"
```

The deliberate working-project switch of the persistent operator service,
from the Wren copy to Lark (the same private address and port; see
[the operator status](../operator-review/README.md)):

```bash
systemctl --user stop cadex-operator-review
systemd-run --user --unit=cadex-operator-review --property=Restart=on-failure \
  --working-directory="$PWD" "$PWD/cadex" review \
  --project "$HOME/cadex-projects/ot5-lark" \
  --host "$(tailscale ip -4)" --port 8765
```

The create/save/reopen probe, against that persistent server, with
pre-creation SHA-256 inventories of the earlier projects (taken **before** the
creation turn started, `.git` excluded, as `{relative path: sha256}` maps):

```bash
PYTHONPATH=cli:cli/tests pixi run python docs/probes/lark-fresh/create_reopen.py \
  "http://$(tailscale ip -4):8765/" "$HOME/cadex-projects/ot5-lark" create80 \
  --intact "$HOME/cadex-projects/ot5-wren-copy54=/tmp/ot5-wren-copy54-iteration80.json" \
  --intact "$HOME/cadex-projects/ot5-wren=/tmp/ot5-wren-iteration80.json" \
  --intact "$HOME/cadex-projects/ot5-biped=/tmp/ot5-biped-iteration80.json"
```

It never starts or stops a server. It checks the creation receipt (exit 0,
accepted revision equal to the manifest, no `runs/`, no policy asset, and a
script that names no earlier project or mechanism), records the server's
accepted model (every component's name, output, placement and served STL
bytes) and a headless Chromium view of the page (identity, every declared
parameter, the component list, viewer statistics, drawn pixels, real pointer
orbit and wheel zoom), then reopens the project **in place** through two
fresh engine processes with `restore`, asserting the accepted revision,
digest, attempt and contract unchanged and every retained accepted artifact
byte-identical. The still-open page is then polled and a fresh visit made;
both must show the same components, statistics, parameters, decisions and
documents as before, the served meshes and placements must be byte-identical,
and the earlier projects must match their pre-creation snapshots. The compact
receipt is [`evidence.json`](evidence.json), guarded by
`cli/tests/test_lark_fresh_evidence.py`; screenshots stay in the project's
`evidence/create80/`, with their hashes in the receipt.

## First bounded real training probe, `lark1` (iteration 82)

Lark's first real GPU experiment ran on the accepted design through the
persistent private-network dashboard, using the Wren experiment driver with
nothing named after Wren:

```bash
PYTHONPATH=cli:cli/tests pixi run python docs/probes/lark-fresh/train.py \
  "$HOME/cadex-projects/ot5-lark" lark1 "http://$(tailscale ip -4):8765/"
python3 docs/probes/wren-fresh/summarize_training.py \
  "$HOME/cadex-projects/ot5-lark" lark1 lark-training-evidence-v1 \
  > docs/probes/lark-fresh/training-evidence.json
```

`train.py` discovers the model, task and policy outputs from the CLI's own
envelopes by kind (`assembly_mjcf_xml`, `assembly_training_task_json`,
`assembly_policy_receipt_json`) rather than by name, and reuses the
project-agnostic `observe.py` and `check_video.py` beside the Wren driver by
path; `summarize_training.py` now takes the receipt schema as its third
argument and finds the torso as the one traced component named for it
(`c_torso` on Wren, `torso_link` on Lark), and regenerates Wren's
`training-evidence.json` byte-identically. Same bounds as `wren1`: 240 PPO
updates, 1024 environments, training seed 0, checkpoints every 20 updates,
`timeout 1800` and a `MemoryMax=20G` scope, from the existing
`~/cadex-train-venv`; no new dependency. The compact receipt is
[`training-evidence.json`](training-evidence.json), guarded by
`cli/tests/test_lark_fresh_evidence.py`; raw outputs, trainer log, timeline,
screenshots and all checkpoints stay in the project's `runs/lark1*` and
`evidence/`.

**Training.** Exit 0 on the GPU, 240 updates (last index 239), 1,052 s of
wall clock; sampled host peak 9.33 GB of the enforced 21,474,836,480-byte cap
(the scope's own `MemoryPeak` 5.02 GB at first sample), sampled GPU peak
15,152 MiB. The training export (`policy_on=0` explicit) is revision
`ebe0f62df802…` at the unchanged creation digest `3b704a3fc1c4…`; model
`7e24cabd622d…`, task `402cca3b869d…`. Ordinary updates took a median of
1.34 s; the wall clock is dominated by the eleven checkpoint exports, which
cost 54–58 s each (694 s of the 992 s between the first and last committed
update). Final batch reward/step 3.29, loss 78.2, episode-length estimate
26.4 steps, up from 0.30 / 20,480 at update 0 — the estimate falling means
episodes end early, and the rollouts below confirm it. The offboard JAX
process emitted its usual overflow-cast RuntimeWarning at initialisation.

**Live observation (D3, D10).** A fresh headless-browser visit to the
persistent URL during training selected `RUN lark1` without a click, showed
`CURRENT — this run's revision is the accepted revision now`, drew the eight
retained components (orbit and zoom exercised), and over 180 s moved through
seven page iterations (3 → 11) on its own poll with one navigation; each
appeared 0.39–1.52 s after the trainer committed it, with reward, loss,
episode-length and both curves updating. Receipt `evidence/lark1-observe.json`
and screenshot beside it in the project.

**Checkpoint published during training (D4).** `lark1.000020.cxpolicy`
(`e6dcbbcc68b4…`) was imported through the public CLI, declared, rolled out
with the engine's witness (error 8.0e-8 under 1e-4), rendered and recorded as
`lark1-checkpoint20` (playback revision `54ec0ef7958d…`) while the trainer
was at updates 18–26; its video (`c5f165541dd1…`, 11 frames, 0.98 s of
simulation, `cadex-prototype-light-v1`) rendered in 3.07 s, decoded, played
and downloaded hash-equal on the persistent page, which still selected the
active `RUN lark1` for a fresh visit and returned to it afterwards. Trainer
intervals were 1.39 s median in the 90 s before the render, 1.42 s during it
and 1.34 s after: continued progress, not a zero-overhead claim.

**Final policy (D4).** `lark1.cxpolicy` (`396c013c3c35…`) was recorded as
`lark1-final` (playback revision `44f8f6a113a3…`) with a verified video
(`25b363291b40…`, 6 frames, 0.50 s); a fresh visit selected `RUN lark1-final`,
played and downloaded it, selected `lark1-checkpoint20` as HISTORICAL with
its own revision, and returned to the current run. The accepted script now
carries the final policy declaration (digest `bfd2bdeb36a2…`); the training
run keeps its own recorded identity, and the run record written before
training was unchanged by the playbacks.

| Seed 0, episode limit 8 s | Checkpoint 20 | Final policy |
|---|---:|---:|
| Observed simulation time | 0.98 s | 0.50 s |
| Fell | yes | yes |
| Control steps | 49 | 25 |
| Torso X displacement | −110.8 mm | +194.3 mm |
| Total reward | −19.9 | +89.9 |

Both policies fall within a second: the final one lunges forward and drops
(+194 mm in 0.5 s before crossing the fall threshold), the checkpoint falls
backward. This is the honest measured result of one 240-update run on one
seed; it is not a gait, and the reward rising while episodes shorten says
the forward-progress term is paid for by falling. Limits: same-machine
private-address checks, not a second-device test; one training seed and one
rollout seed; no design revision, retraining, copy or interruption evidence
for Lark yet.
