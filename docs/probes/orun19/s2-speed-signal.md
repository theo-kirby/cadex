# orun19 S2: why s2a-hold runs ~1.2× its command: not the speed signal, the exploration noise

Verified against source: 2026-10-23. Frozen evidence (orun19, iteration 13).
The critic's question after lever 2's rejection (`s2b-tent-150.md`): does
`track_speed` reward a different speed (`comv_x`) from the one the judge
measures (the base point), by a constant ~20%? It does not. What the
measurements below find instead: the policy is calibrated for its noisy
training self, and the deterministic actor the engine judges runs faster.

```
R=~/cadex-projects/leo/runs/s2a-hold/train; E=~/cadex-projects/leo/evaluations; P=~/cadex-train-venv/bin/python
CUDA_VISIBLE_DEVICES= JAX_PLATFORMS=cpu $P docs/probes/orun19/speed_signal.py sensor  $R/cat_model-model.xml
CUDA_VISIBLE_DEVICES= JAX_PLATFORMS=cpu $P docs/probes/orun19/speed_signal.py judged  $R/cat_model-model.xml $E/s2a-hold-150-{700,1500,2400,3500,5000}
CUDA_VISIBLE_DEVICES= JAX_PLATFORMS=cpu $P docs/probes/orun19/speed_signal.py witness $R/speed.000{100,150}.rollout-trace.json
$P docs/probes/orun19/noise_speed.py $R $R/speed.000150.cxpolicy --envs 64 --noise-scale 0 0.5 1   # GPU, 8 min
```

The checkpoint is s2a-hold's `speed.000150.cxpolicy`, `efe7f96b` (trained
task `d5b25b15`, model `f9b8ab82`, leo v06), the policy judged in
`s2a-hold-150.md`. The v05 comparison is unchanged: `b1-s2-180` held, never
tracked.

## 1. The sensor is right

`comv` is `subtreelinvel` on `c_chest_frame`, the root (obs/64), in the
world frame, scaled ×1000 to mm/s. At the `solved` keyframe with random
joint velocities, MJX 3.10.0, stock MuJoCo and a finite-difference whole-body
COM velocity agree to 4 decimals (e.g. 4.1957 / 0.8702 / 1.8261 m/s for all
three). The trainer reads it from `data.sensordata` after `mjx.step`
(`cadex_train.py` `observe`) and evaluates the written expression as written
(`reward_of`: a weighted sum of `eval`s, no floor in this task).

## 2. COM speed is the base-point speed on the judged traces

The whole-body COM rebuilt from each frame's component placements (all 30.68
kg, every body found) against the judge's base point, over the last 2 s,
median over 10 seeds:

| command mm/s | 700 | 1500 | 2400 | 3500 | 5000 |
|---|---|---|---|---|---|
| COM m/s | 0.858 | 1.797 | 2.948 | 4.085 | 4.531 |
| base point m/s (the judge's; = `s2a-hold-150.md`) | 0.858 | 1.796 | 2.948 | 4.085 | 4.532 |
| COM / base | 0.9997 | 1.0001 | 1.0000 | 1.0002 | 0.9999 |
| COM / command | 1.226 | 1.198 | 1.228 | 1.167 | 0.906 |
| COM forward-speed s.d. in the window, share of command | 2.6% | 1.5% | 0.7% | 1.3% | 0.3% |

- **No offset.** What `track_speed` reads is what the judge measures, to 0.02%.
- **No within-stride swing big enough to move the tent's peak.** The COM's
  forward speed varies by 0.3–2.6% of the command within the window, so the
  asymmetric-tent reading in `s2a-hold-150.md` (the reward's expectation
  peaking over the command) cannot account for +20%. Lever 2's result
  (`s2b-tent-150.md`, further over under a steeper tent) agrees.

## 3. The trainer's own deterministic rollout overshoots the same way

The witness rollout (MJX, deterministic actor, nominal command 2850 mm/s)
runs 3.37–3.47 m/s from 2 s on: speed/goal **1.18–1.21 at 100** and
**1.20–1.22 at 150**. So training and evaluation agree; the overshoot is in
the policy, not in a train/evaluate mismatch.

## 4. With the noise it trained under, it runs at the command

`noise_speed.py` builds the trainer's own environment from the run's bundle
(`build_environment`, 64 environments, commands from the run's pool, one
500-step episode) and plays the actor's mean, then the same keys with the
container's recorded exploration noise added before the tanh (×0.5 and ×1
of `exploration.log_std`; mean σ at 150 is 0.52). Last 2 s `comv_x` /
command, median over environments that never reset:

| noise | ×0 (deterministic: what the engine judges) | ×0.5 | ×1 (what PPO sampled and was paid for) |
|---|---|---|---|
| all commands (64 envs) | **1.208** | 1.164 | **1.026** (62/64 whole) |
| 700–1150 mm/s (11 envs) | 1.21–1.28 | 1.16–1.28 | 1.03–1.27 |
| 1150–2900 mm/s (27 envs) | 1.19–1.25 | 1.16–1.23 | 1.00–1.15 (2 stalls) |
| 2900–3800 mm/s (12 envs) | 1.16–1.21 | 1.07–1.16 | 0.97–1.01, or a stall at 0.34–0.76 (6) |
| 3800–4570 mm/s (14 envs) | 0.99–1.17 | 0.91–1.05 (3 stalls) | 0.27–0.90, mostly stalls |

- The deterministic median, 1.208, reproduces the engine's +17–23% from an
  independent environment and a different command draw.
- **Under its training noise the same actor runs at 1.00–1.15× from about
  1.2 to 3.4 m/s**: what the reward asked for. The mean action is a faster
  gait than the noisy one it was rewarded as, so the judged (deterministic)
  policy overshoots by about the noise's slowdown.
- **At the slow end the noise explains only part of it** (×1 still
  1.13–1.27 at 700–1150): something else holds a floor of speed there.
- **Above ~3.4 m/s the full noise breaks the gait** (stalls at 0.27–0.9 with
  no reset); it is the deterministic actor that reaches 4.5 m/s.

## What it means for S2's levers

- Not a corrected speed signal: there is nothing to correct.
- Not lever 3 as charted (a regulariser weight): the regularisers cost 0.5–1.5
  per step against `track_speed`'s ~2.4 per step forgone by the overshoot
  (engine per-term rewards, `s2a-hold-150-*/evaluation.json`), and they
  pull toward *slower*; no weight on them removes a gap the noise opens.
- What would close it is the gap between the sampled and the played policy:
  a smaller exploration σ late in training (the entropy cost, or a long warm
  start, O5's L1 form, as σ falls; σ fell 0.92 → 0.60 → 0.52 at 1, 100 and
  150 while the witness gap held 1.18–1.21), or a task that pays the deterministic speed. Neither is
  one of O3's three listed levers; the report records this as the finding and
  the next unit chooses within the charter.
