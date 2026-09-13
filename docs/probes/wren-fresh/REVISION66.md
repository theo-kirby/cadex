# Wren product-agent revision, retraining and comparison

Verified against source: 2026-09-13. [Cadex-new] Iterations 65–66, ADR-308.

The product agent's own review-driven revision of Wren is now authored,
documented, retrained and compared on the working copy `ot5-wren-copy54`.
The persistent private-network port 8765 serves that copy and a fresh visit
selects **`wren66-final`**, playback revision `de9692bd4ee5…`, with 90 mm feet,
all 240 telemetry points and a playable, downloadable video. This closes the
Wren-specific product-agent authorship gap that iterations 53, 58 and 61
recorded as provider refusals. It is not a claim of demonstrated walking.

## The agent's change (iteration 65, completed in iteration 66)

Iteration 65 ran one real `cadex -p` design turn on the copy with the retained
comparison report as evidence (`evidence/agentrev65/prompt.txt`). The agent
inspected the script three times and called `set_params` once; the engine
accepted **`foot_len=90`, `policy_on=0`** as revision `03077ee9eb82…`, digest
`4d327bf8081a…`. The turn ended after acceptance and before the agent returned
its `DECISION:` text: `stdout.json` is empty and the stderr transcript ends at
"Accepted. Let me verify the foot geometry landed correctly." No rationale
reached the project, and the iteration committed without recording it.

Iteration 66 finished that turn rather than starting another design. With a
fresh evidence directory and inventory (`evidence/agentrev66/`), one bounded
turn told the agent what it had accepted and asked it to confirm the state and
return its decision, making no further change unless it no longer endorsed 90 mm:

```bash
timeout --signal=TERM --kill-after=10s 900 ./cadex \
  --project "$HOME/cadex-projects/ot5-wren-copy54" \
  --out "$HOME/cadex-projects/ot5-wren-copy54/evidence/agentrev66/output" \
  --json -p "$(cat "$HOME/cadex-projects/ot5-wren-copy54/evidence/agentrev66/prompt.txt")"
```

The stored `claude-sonnet-5` preference answered. It made six `inspect` calls,
confirmed the accepted revision, effective parameters and the 90×40×8 mm foot
solids, deliberately changed nothing, and returned a `DECISION:` and a
`NOTE design-specs:`. The CLI landed them as the project's **ADR-002** in
`DECISIONS.md` and as `docs/design-specs.md`, then exited **3** with
`ok: false` because no script was accepted in that turn. That exit is the
CLI's ordinary no-acceptance outcome, not a provider refusal; the acceptance
is the iteration-65 turn's. The agent's stated hypothesis: fall avoidance and
reward rose monotonically with foot length across 85, 105 and 110 mm while the
inspected frames showed standing rather than an alternating gait, so a longer
foot may let the policy farm survival reward by standing; 90 mm keeps a small
cushion over 85 mm while pulling back from that range, at the cost of forgoing
the retraining-verified fall reduction seen at 105 mm.

## Retraining (wren66)

The existing bounded experiment ran on the accepted 90 mm design, with the
authorship string recorded in `run.json` and each playback review:

```bash
PYTHONPATH=cli:cli/tests pixi run python docs/probes/wren-fresh/train.py \
  "$HOME/cadex-projects/ot5-wren-copy54" wren66 "http://$(tailscale ip -4):8765/" \
  "product-agent-authored revision: foot_len 110->90 mm accepted by the agent in iteration 65 (revision 03077ee9eb82), rationale returned in iteration 66 as project ADR-002"
```

The export left the accepted revision at `03077ee9eb82…`, so the training run
carries the agent's own revision. Settings were unchanged from wren1/wren2:
240 PPO iterations, 1024 environments, training seed 0, checkpoints every 20,
`timeout 1800` and a systemd scope with `MemoryMax=20G`. Trainer exit 0.

| wren66 | value |
|---|---:|
| Training wall time | 700.402 s |
| Sampled host peak (scope `memory.current`) | 7,402,741,760 bytes |
| Sampled GPU peak | 15,120 MiB |
| Final reward per step / loss / episode estimate | 0.324734 / 0.308523 / 320 |
| Checkpoint 20 published at trainer iteration | 18 → 34 across the browser check |
| Checkpoint render / witness error | 12.68 s / 3.39e-08 |
| Final render / witness error | 12.58 s / 9.63e-08 |
| Iteration medians before / during / after render (excluding checkpoint boundaries) | 1.431 / 1.338 / 1.276 s |

The persistent page selected `RUN wren66` for a fresh visit while training was
active, drew eight components with 90 mm feet, orbited and zoomed, and showed
seven consecutive committed iterations with each reaching the page within
1.25 s of its file commit. The checkpoint video played and downloaded while
training continued; return-to-current selected the live run. After completion
a fresh visit selects `wren66-final`; `wren66-checkpoint20` is HISTORICAL and
return-to-current selects the final run. `current.py` recorded that state in
`evidence/wren66-final-completion66-browser.json`. Checkpoint files are listed
as `missing` in the final playback's telemetry because they live under
`runs/wren66/train`, not under the playback run; the label is accurate.

## Comparison on the declared seeds

The three retained policies of this copy were each evaluated in a fresh scratch
project from their own retained script, model, task and hash-verified policy,
on seeds 0–4, eight seconds, 50 Hz. `compare.py` now takes the script the run
record names (`artifacts.script`), because `wren57-retry` was published in
place and keeps its training script beside `playback-script.py`. The three
evaluations ran concurrently in separate scratch projects; each seed-0 trace
reproduced the retained trace exactly and no source file changed.

```bash
for x in wren57-retry:retry wren66-checkpoint20:c66 wren66-final:f66; do
  pixi run python docs/probes/wren-fresh/compare.py \
    "$HOME/cadex-projects/ot5-wren-copy54" "$HOME/cadex-projects/ot5-wren-eval66-${x##*:}" "${x%%:*}"
  mkdir -p "$HOME/cadex-projects/ot5-wren-copy54/evidence/comparison66/${x##*:}"
  cp -R "$HOME/cadex-projects/ot5-wren-eval66-${x##*:}/evidence" \
    "$HOME/cadex-projects/ot5-wren-copy54/evidence/comparison66/${x##*:}/"
done
pixi run python docs/probes/wren-fresh/report_revision.py \
  "$HOME/cadex-projects/ot5-wren-copy54" \
  "$HOME/cadex-projects/ot5-wren-copy54/evidence/agentrev65/before.json" \
  "$HOME/cadex-projects/ot5-wren-copy54"/evidence/comparison66/{retry,c66,f66} \
  > docs/probes/wren-fresh/revision66-evidence.json
```

`report_revision.py` first re-hashes the 465 run and asset files inventoried
before the agent's change and refuses if any differs; all 465 match. It reads
the design authorship from the run record's training provenance.

| Seeds 0–4, 8 s | wren57-retry (110 mm) | wren66-checkpoint20 (90 mm) | wren66-final (90 mm) |
|---|---:|---:|---:|
| Mean / min torso X displacement | +40.137 / +36.445 mm | +42.724 / +39.075 mm | +55.147 / +51.392 mm |
| Survival mean / min | 8 / 8 s | 8 / 8 s | 8 / 8 s |
| Falls | 0 / 5 | 0 / 5 | 0 / 5 |
| Mean total reward | 214.882 | 213.622 | 144.877 |

Per-seed displacement for `wren66-final` is 61.6, 54.2, 55.4, 53.2 and
51.4 mm; for `wren57-retry` 46.5, 39.0, 40.7, 38.1 and 36.4 mm. All fifteen
episodes ran the full 400 steps. The 90 mm final policy moves the torso
further forward than the 110 mm retry on every seed and scores markedly less
reward; its trainer's reward per step peaked at 0.5357 and ended at 0.3247.
These are torso displacements and threshold survival on one training seed per
design. They do not show an alternating gait and do not isolate geometry as
the cause of the difference; the agent's standing-exploit hypothesis is
neither confirmed nor refuted by five eight-second episodes.

[revision66-evidence.json](revision66-evidence.json) is the committed receipt,
guarded by `cli/tests/test_wren_fresh_evidence.py`. Policies, videos, traces,
full CLI envelopes, browser screenshots, the agent prompts and transcripts,
and trainer logs remain project-local under `runs/wren66*`, `assets/` and
`evidence/agentrev65`, `evidence/agentrev66`, `evidence/comparison66` and
`evidence/wren66-*`. Retain the whole copy; the scratch projects are not
needed to read the comparison. This is same-machine private-address browser
evidence, not a second-device test, and the videos reuse the delivered common
style without a new D11 similarity claim.
