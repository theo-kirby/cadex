# Lark product-agent revision, retraining and comparison

Verified against source: 2026-09-13. [Cadex-new] Iteration 84, ADR-313.

Lark's review-driven design change was authored by the product agent from
`lark1`'s measured results, retrained under the same bounds as `lark2`, and
compared with `lark1` on the project's own declared seed set (0–9, eight
seconds, 50 Hz) from each run's retained model, task and hash-verified
policy. The persistent private-network port 8765 served `ot5-lark`
throughout and a fresh visit now selects **`lark2-final`**, playback
revision `ca88f223b54c…`. This is a measured survival result on one training
seed per design; it is not a claim of demonstrated walking.

## The agent's change

One bounded `cadex -p` turn (07:17:01Z–07:18:00Z UTC, session
`6319e8a1-8837…`, the stored `claude-fable-5` preference, exit 0) received the
`lark1` measurements — both policies falling within a second on seed 0, the
final policy's +194 mm lunge earning 83.2 of its 89.9 reward from
`forward_progress`, the trainer's episode estimate shrinking to 26 steps as
its reward rose — and was asked to change exactly one declared mechanism
parameter, keep the task's reward, episode, control-rate and fall-fraction
settings, and set `policy_on=0` because the declared `lark1` policy is bound
to the old model. It made five `inspect` calls and two `set_params` calls and
accepted **`torso_h` 70 → 45 mm, `policy_on` 1 → 0** as revision
`62f4e2a0e2df…`, digest `add12df51777…`, then returned its `DECISION:` and
`NOTE design-specs:`, which the CLI landed as the project's **ADR-004** and a
second `docs/design-specs.md` bullet. Its hypothesis: 0.433 kg of the
0.596 kg machine sat at z = 203 mm, so lowering and lightening the torso
(0.278 kg at z = 190.5 mm, 0.441 kg total) cuts the hip toppling moment by
about 35 % and static hip demand from ~120 to ~77 N·mm against the fixed
200 N·mm limit; the tradeoff it accepts is a shorter pendulum that tips
faster once disturbed and 36 % less torso volume for electronics, and it
names the forward-lunge exploit as a task-side issue if it persists. The
revised specs: standing height 213 mm, hip pivot z = 168 mm, fall threshold
133.35 mm, seed set 0–9 unchanged.

```bash
P="$HOME/cadex-projects/ot5-lark"; E="$P/evidence/agentrev84"   # prompt.txt retained there
timeout --signal=TERM --kill-after=10s 900 ./cadex --project "$P" --out "$E/output" \
  --json -p "$(cat "$E/prompt.txt")" > "$E/stdout.json" 2> "$E/stderr.log"
```

`before.json` beside the prompt is the SHA-256 inventory of the 125 files
under `runs/` and `assets/` taken before the turn; every one still matched
after it and after the retraining below.

## Retraining (`lark2`)

The same driver and bounds as `lark1` (240 PPO updates, 1024 environments,
training seed 0, checkpoints every 20, `timeout 1800`, `MemoryMax=20G`, the
existing `~/cadex-train-venv`, no new dependency), with the authorship
recorded in `run.json` and each playback review:

```bash
PYTHONPATH=cli:cli/tests pixi run python docs/probes/lark-fresh/train.py \
  "$HOME/cadex-projects/ot5-lark" lark2 "http://$(tailscale ip -4):8765/" \
  "product-agent-authored revision: torso_h 70->45 mm accepted by the agent in iteration 84 (revision 62f4e2a0e2df), rationale recorded as project ADR-004"
python3 docs/probes/wren-fresh/summarize_training.py \
  "$HOME/cadex-projects/ot5-lark" lark2 lark-training-evidence-v1 \
  > docs/probes/lark-fresh/training84-evidence.json
```

The export left the agent's revision `62f4e2a0e2df…` in place (`policy_on`
was already 0), so the training run carries it; model `1e318f184459…`, task
`4615c6ddcaaa…`, both different from `lark1`'s.

| `lark2` | value |
|---|---:|
| Trainer exit / updates | 0 / 240 (last index 239) on the GPU |
| Wall clock | 718.752 s |
| Sampled host peak / enforced cap | 7,424,741,376 / 21,474,836,480 bytes |
| Sampled GPU peak | 15,122 MiB |
| Final reward per step / loss / episode estimate | 0.348 / 0.0877 / 975 steps |
| Peak reward per step | 0.524 |
| Checkpoint 20 published at trainer updates | 18 → 33; render 23 → 32, 12.98 s |
| Checkpoint / final witness error | 2.85e-08 / 8.71e-08 (tolerance 1e-4) |
| Update medians before / during / after the render | 1.528 / 1.391 / 1.368 s |

The episode estimate above 400 is the trainer's batch estimate when few
episodes end in a batch, not measured survival. A fresh visit to the
persistent URL during training selected `RUN lark2` without a click, drew
the eight components with the 45 mm torso, orbited and zoomed, and moved
through seven page iterations (3 → 11) on its own poll with one navigation,
each 0.24–1.62 s after the trainer's commit. `lark2-checkpoint20` (policy
`8eb15d8a7570…`, playback revision `95a37e532dae…`, video `dfb45737df66…`,
81 frames, 8.0 s) played and downloaded hash-equal while the trainer was
active, with return-to-current selecting the live run. `lark2-final`
(policy `b79a63908e94…`, playback revision `ca88f223b54c…`, video
`af610491bedf…`, 81 frames, 8.0 s, rendered in 12.38 s) is the fresh-visit
default; checkpoint 20 selects as HISTORICAL and return-to-current works.
The `lark1` run records were unchanged by the playbacks. Receipt:
[`training84-evidence.json`](training84-evidence.json).

## Comparison on the declared seeds

Lark's design specs declare seed set 0–9, so `compare.py` and
`report_revision.py` now take the seed count from the project rather than
assuming Wren's five (Wren's committed `revision66-evidence.json`
regenerates byte-identically). Each of the four retained policies was
evaluated in its own fresh scratch project from its run's retained script,
recorded effective parameters, model, task and hash-verified policy, with
the seed set through the script's `rollout_seed` parameter; each seed-0 trace
reproduced the retained trace exactly and no source file changed.

```bash
for x in lark1-checkpoint20:c1 lark1-final:f1 lark2-checkpoint20:c2 lark2-final:f2; do
  pixi run python docs/probes/wren-fresh/compare.py \
    "$HOME/cadex-projects/ot5-lark" "$HOME/cadex-projects/ot5-lark-eval84-${x##*:}" "${x%%:*}" 10
  mkdir -p "$HOME/cadex-projects/ot5-lark/evidence/comparison84/${x##*:}"
  cp -R "$HOME/cadex-projects/ot5-lark-eval84-${x##*:}/evidence" \
    "$HOME/cadex-projects/ot5-lark/evidence/comparison84/${x##*:}/"
done
pixi run python docs/probes/wren-fresh/report_revision.py \
  "$HOME/cadex-projects/ot5-lark" "$HOME/cadex-projects/ot5-lark/evidence/agentrev84/before.json" \
  "$HOME/cadex-projects/ot5-lark"/evidence/comparison84/{c1,f1,c2,f2} \
  > docs/probes/lark-fresh/revision84-evidence.json
```

| Seeds 0–9, 8 s | lark1-checkpoint20 (70 mm) | lark1-final (70 mm) | lark2-checkpoint20 (45 mm) | lark2-final (45 mm) |
|---|---:|---:|---:|---:|
| Mean / min torso X displacement | +8.7 / −114.2 mm | +190.2 / +180.9 mm | +24.4 / +21.0 mm | +34.8 / +31.6 mm |
| Survival mean / min | 6.58 / 0.78 s | 0.51 / 0.50 s | 8 / 8 s | 8 / 8 s |
| Falls | 2 / 10 | 10 / 10 | 0 / 10 | 0 / 10 |
| Mean total reward | 163.8 | 88.4 | 205.8 | 149.9 |

`lark1-final` falls on every seed within 0.56 s after lunging 181–197 mm
forward; `lark1-checkpoint20` falls backward on seeds 0 and 2 and stands on
the other eight. Both 45 mm policies survive all ten eight-second episodes;
`lark2-final` moves the torso 31.6–38.5 mm forward per seed and scores less
reward than its own checkpoint 20, whose displacement is 21.0–27.7 mm. The
agent's balance hypothesis is consistent with these numbers — the revised
design stopped falling — but one training seed per design cannot isolate
geometry from training variance, and 35 mm in eight seconds is standing or
shuffling, not a gait. [`revision84-evidence.json`](revision84-evidence.json)
is the committed receipt; both receipts are guarded by
`cli/tests/test_lark_fresh_evidence.py`. Policies, videos, traces, full CLI
envelopes, the agent prompt and transcript, browser screenshots and trainer
logs remain project-local under `runs/lark2*`, `assets/` and
`evidence/agentrev84`, `evidence/comparison84` and `evidence/lark2-*`;
retain the whole project. Same-machine private-address browser evidence, not
a second-device test; the videos reuse the delivered common style without a
new D11 similarity claim. Lark still has no copy-isolation (D7) or
controlled-interruption (D8) evidence of its own.
