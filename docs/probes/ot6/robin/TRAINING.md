# Robin trains — one diverged run, one bounded run measured over ten seeds (D7, ADR-338)

Verified against source: 2026-09-14. [Cadex-new]

The training half of the charter's D7 (ADR-328): Robin, the product-agent
balancer accepted at revision `5ad94d65…` ([BORE.md](BORE.md)), trained once
under the charter's bounds, its checkpoint and final videos in the D3 look on
the persistent operator dashboard, and its balance, survival and falls measured
over a declared episode and seed set. `training.json` is the receipt (15.8 KB);
`train.py` drove the run, `evaluate.py` rolled each retained policy over the
seeds in a fresh scratch project, and `report_training.py` wrote the receipt
and decoded one frame from each video. Everything else — traces, videos, the
trainer logs, the timelines, the observer's samples — stays in the project under
`evidence/` and `runs/robin*/`, cited by path and digest.

## The task, as declared in the script

`balance_task` on `robin_model`: 400 steps at 50 Hz (8 s); two raw-torque
wheel motors limited to the Pololu 2367's 92.18 N·mm stall torque, damped at
stall torque over no-load speed; reward `1` alive − `3·|pitch|` (radians, from
the chassis quaternion) − `0.05·Σ(τ/stall)²`; termination when `chassis_z`
(the chassis frame at deck-top centre, 66.0 mm upright) falls below
0.7 × 66.0 = **46.2 mm**, read back from the retained task bundle; reset
variation a 0–3° tilt with a 3–5 mm lift; seed set **0–9** through
`rollout_seed`. Nothing in the task is changed between the two runs below.

## Two runs

**`robin1` diverged.** Requested 240 PPO updates on 1024 environments,
checkpoints every 20, under `systemd-run` with `MemoryMax=20G` and a 3600 s
timeout, at the trainer's default learning rate 3e-4 (the driver did not yet
record the rate; the receipt says so). It trained normally to update 127
(reward per step 0.714, best 0.743 at update 122, running mean episode 109 of
400 steps), then reward and loss went non-finite at update 128 and the trainer
stopped itself, as ADR-088 made it do. Its checkpoint-20 video *was* published
while it was active (trainer at updates 18–38, browser check exit 0), it left
six numbered checkpoints and `best`, and its run record now carries
`status: failed` with the trainer's error, so the dashboard serves it as a
failed historical run beside its checkpoint video (the ot5 D8 state). Nothing
of it was deleted or re-used.

**`robin2` completed.** The same request with `--learning-rate 1e-4`, the
trainer's own suggestion in its divergence message, and nothing else changed.
The trainer exited 0 after 620.8 s of wall clock (state `done`, device `gpu`,
update 239); host peak 7.41 GB in the scope, GPU peak 15 139 MiB. Every
trainer-committed update interval is in the receipt: 204 plain updates with a
median of 0.812 s (0.724–0.897 s), the first-update compile at 46.9 s and each
checkpoint step at 33–35 s. Reward per step rose from 0.127 at update 0 to
0.688 at 239 (best 0.703 at 205); the trainer's running mean episode length at
the end was 126 of 400 steps across its 1024 environments.

## The two policies over the declared seed set

Chassis x-displacement over the episode, survival, falls, and the chassis pitch
(largest |pitch| over the episode and the pitch at the last frame); the retained
trace is seed 0 and reproduces byte for byte from the scratch project.

| policy | video | balanced the full 8 s | falls | survival s (mean, min–max) | max pitch ° (mean, min–max) | final pitch ° (mean) | x displacement mm (mean, min–max) |
|---|---|---|---|---|---|---|---|
| checkpoint 20 (`4ce768b6…`, update 19) | `video-robin2-checkpoint20.png` at 0.2 s of 0.4 s | 0 / 10 | 10 / 10 | 0.47, 0.40–0.58 | 69.7, 63.6–74.4 | −69.7 | −72.0, −77.6 to −64.4 |
| final (`5380d421…`, update 239) | `video-robin2-final.png` at 4.0 s of 8.0 s | 10 / 10 | 0 / 10 | 8.0, 8.0–8.0 | 12.2, 11.1–14.4 | +11.1 | −1825, −1852 to −1799 |

**The checkpoint falls on every seed** within 0.6 s: the frame at 0.2 s shows
the chassis already pitched far forward with the board tilting toward the camera,
and the pitch reaches 64–74° before `chassis_z` crosses 46.2 mm. The video is
0.4 s long because that is how long the checkpoint stayed up.

**The final policy meets the task's bar on every seed and not the operator's.**
It never falls, but it does not stand still: on every seed the pitch settles at
+11.0 to +11.2° and stays there, and the chassis drives **1.8 m backward** in
8 s (seed 0 also 1.9 m sideways, so the path is an arc at roughly 0.3 m/s).
That is a leaning, driving equilibrium: with the wheel joints damped at stall
torque over no-load speed, a constant wheel speed produces a constant motor
torque, and the policy holds the lean at which that torque balances gravity's
moment rather than driving back under the centre of mass. The task as declared
rewards being alive and penalises pitch and torque; it says nothing about
velocity or position, so this is what it asked for. Standing upright and still
is the bar a balancer should be measured against, and this policy fails it on
every seed — a measured result, recorded as one. A velocity or position term
in the reward is what remains, and it is a design decision for the next turn
on the project, not a training knob.

## In the new look, on the persistent dashboard

Both videos are `cadex-prototype-dark-v1` from the shared environment module —
the near-black grid mat, fog to the horizon, the contact shadow under the
wheels, the follow rig at its declared framing, the timer pill (0.20 s and
4.00 s in the two frames) — and each names what it shows: `tessellated solids
of the accepted revision; collision proxies not drawn` (ADR-333). Each frame
shows exactly that: the printed chassis with its open bay and clamp bars, the
Pi Zero on its bosses, the two printed wheels — not the nine declared proxies
(two boxes, two spheres, five boxes). Both browser checks decoded the downloaded
file to the recorded frame count (5 and 81) with differing frames and matching
digests.

**While the trainer was active.** The observer's fresh visit selected
`RUN robin2` without a click, loaded 24 components, and saw six successive
trainer updates each reach the page within 0.95 s of being committed, after one
navigation. The checkpoint video was rendered at trainer update 38–39 in 4.37 s.
Robin's updates take under a second and its checkpoint steps 34 s, and the
render fell entirely inside the checkpoint step at update 39, so no update
interval overlaps it; that step took 34.50 s against 33.3–34.5 s for the run's
other checkpoint steps, and the plain-update medians in the 90 s before and
after were 0.875 s and 0.849 s. One bounded concurrent render cost the trainer
nothing measurable. The other loads during the run were the checkpoint
declaration, rollout and record, the observer, and one browser check; the
ten-seed evaluations ran after the trainer had exited.

**At the end** a fresh visit at 1400×900 and at touch-emulated 400×850 selects
`robin2-final`, loads its 24 components (114 344 triangles from the rollout
leg's own STL exports), shows solids by default and nine proxy outlines under
the labelled toggle, with no horizontal overflow; `/api/project` serves
`ot6-robin` at accepted revision `8d727e18…` (the final playback's) with five
runs — `robin1` (failed), `robin1-checkpoint20`, `robin2`, `robin2-checkpoint20`
and `robin2-final` — and the reader's rule selects `robin2-final`.

## What this does not claim

One completed run, one seed for training, ten for evaluation; no shove band,
no disturbance, no claim about how a printed Robin with a 100 g battery pack
(declared but not modelled, per the project's script header) would behave. The
final policy's full-episode survival is a measured fact about the task as
declared; it is not a stationary balance. The diverged run is evidence that the
trainer's default rate is too high for this reward on this model, not a
diagnosis of why.

## Commands

```bash
PYTHONPATH=cli:cli/tests pixi run python docs/probes/ot6/robin/train.py "$P" robin2 "$URL" "<authored_by>" 1e-4
pixi run python docs/probes/ot6/robin/evaluate.py "$P" "$HOME/cadex-projects/ot6-robin-eval-robin2-c" robin2-checkpoint20
pixi run python docs/probes/ot6/robin/evaluate.py "$P" "$HOME/cadex-projects/ot6-robin-eval-robin2-f" robin2-final
PYTHONPATH=cli pixi run python docs/probes/ot6/robin/report_training.py "$P" robin2 "$URL" "$HOME/cadex-projects" docs/probes/ot6/robin
```
`$P` is `$HOME/cadex-projects/ot6-robin`; `$URL` is the persistent operator
address, read from the running service and never committed.
