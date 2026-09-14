# Heron trains — one bounded run, the reach measured over ten seeds (D8, ADR-340)

Verified against source: 2026-09-14. [Cadex-new]

The training half of the charter's D8 (ADR-328): Heron, the product-agent
two-DoF MG90S arm accepted at revision `9c1f2fe7ea19…` ([README.md](README.md)),
trained once under the charter's bounds, its checkpoint and final videos in the
D3 look on the persistent operator dashboard, and its reach measured over a
declared episode and seed set. `training.json` is the receipt (15.1 KB);
`train.py` drove the run, `evaluate.py` rolled each retained policy over the
seeds in a fresh scratch project, `report_training.py` wrote the receipt and
decoded one frame from each video, and `servo_view.py` orbited the dashboard's
viewport to the servo side. Everything else — traces, videos, the trainer log,
the timeline, the observer's samples — stays in the project under `evidence/`
and `runs/heron1*/`, cited by path and digest.

## The task, as declared in the script

`heron_task` on `heron_model`: 200 steps at 50 Hz (4 s); two MG90S position
servos through `servo.actuator` (stall 176.5 N·mm at 4.8 V, damping from stall
over no-load speed); reward `exp(−|tip − (100, 0, 60)| / 30)` − 2e-6·Σf² −
5e-4·|tip velocity|, the tip being the forearm's component frame, which the
agent authored at the tip; termination when `tip_z` falls below **5 mm**, read
back from the retained task bundle; per-seed variation two horizontal 0.2–0.6 N
pushes on the forearm, 0.2 s each, at azimuth 0° and 180°, each drawn between
1.4 and 2.6 s; the target fixed across episodes; seed set **0–9** through
`rollout_seed`. Success is the script's own stated bar: within `reach_tol`
10 mm of the target at episode end **and** over the whole final second, without
termination. The tip starts at (70, 0, 120), 67.08 mm from the target.

## The run

**`heron1` completed at the trainer's default rate.** 240 PPO updates on 1024
environments, checkpoints every 20, seed 0, learning rate 3e-4 (recorded in the
run's `requested` block), under `systemd-run` with `MemoryMax=20G` and a 3600 s
timeout. The trainer exited 0 after 619.6 s of wall clock (state `done`, device
`gpu`, update 239); host peak 7.08 GB in the scope, GPU peak 15 137 MiB. Every
trainer-committed update interval is in the receipt: 204 plain updates with a
median of 1.067 s (1.053–1.080 s), the first-update compile at 49.1 s and each
checkpoint step at 25.8–26.8 s. Reward per step rose from −0.154 at update 0 to
0.595 at 239, the best of the run and still rising at the end (0.447 at 39,
0.556 at 79, 0.582 at 199). The trainer's episode-length metric is
uninformative here and the receipt says so: it is unroll × environments over
episode endings in the unroll, so it reads 20 480 when no episode ends in the
20-step unroll and 20.0 when all 1024 hit the time limit together every tenth
update — no floor termination was ever recorded during training. Nothing
diverged and no earlier run of this project exists.

## The two policies over the declared seed set

Reach error at episode end, the largest and mean error over the final second,
the smallest error over the episode, when the tip first came within 10 mm,
survival and terminations; the retained trace is seed 0 and reproduces byte for
byte from the scratch project.

| policy | video | reached (end and final second within 10 mm) | terminated | end error mm (mean, min–max) | final-second max mm (mean, min–max) | final-second mean mm | min error mm (min–max) | first within 10 mm |
|---|---|---|---|---|---|---|---|---|
| checkpoint 20 (`eb761030…`, update 19) | `video-heron1-checkpoint20.png` at 2.0 s of 4.0 s | 0 / 10 | 0 / 10 | 137.61, 137.58–137.66 | 137.76, 137.58–138.44 | 137.63 | 67.08–67.08 | never |
| final (`68e1ee7b…`, update 239) | `video-heron1-final.png` at 2.0 s of 4.0 s | 10 / 10 | 0 / 10 | 3.33, 2.96–5.19 | 9.15, 8.33–9.60 | 5.69 | 0.36–1.85 | 0.1 s on every seed |

**The checkpoint drives the arm away from the target and holds it there.** On
every seed its smallest error is 67.08 mm — the starting error — and its tip
ends at (−6.0, 0, 147.7): the upper arm upright and the forearm folded back over
the elbow, at the joints' limits. The frame at 2.0 s shows exactly that, the
forearm pointing back and up above the base. Its total reward is −0.33 to −0.68
per episode: at 137 mm the reach term is worth 0.01 per step and the control
and tip-speed costs are all that remain. It never terminates because a folded
arm never lowers its tip toward the bench.

**The final policy meets the task's bar on every seed.** The tip is within
10 mm of the target by 0.1 s on all ten seeds, comes within 0.4–1.9 mm of it at
some point, and ends 3.0–5.2 mm away; over the final second — after both
pushes, which land between 1.4 and 2.6 s — it never strays further than 9.6 mm.
Six seeds end at the same pose to 0.1 mm, (100.6, 0, 57.1); the other four end
higher (z 58.2–65.2), so the push each seed drew leaves a small residual the
policy does not fully take out in the time left. Two things are true of the
hold that the bar does not measure. The tip sits about 3 mm *below* the target
on most seeds, which the reach scale of 30 mm makes almost free (exp(−3/30) is
0.90 of the maximum) — consistent with the position servos sagging under the
forearm's weight, though the trace does not separate that from the policy's own
setpoint. And the final-second maximum of 8.3–9.6 mm against a mean of 4.9–6.2
says the tip is not still: it oscillates within the tolerance rather than
settling, which the 5e-4 tip-speed weight does not penalise enough to remove.
Reaching and holding within 10 mm is what the script asked for and what this
policy does; a tighter tolerance or a heavier stillness term is a design
decision for the next turn on the project, not a training knob. The success
criterion here is the task's, met; a measured result either way.

## In the new look, on the persistent dashboard

Both videos are `cadex-prototype-dark-v1` from the shared environment module —
the near-black grid mat with its PROTOTYPE and 1 METER labels, fog to the
horizon, the contact shadow under the base foot, the follow rig at its declared
framing, the timer pill (2.00 s in both frames) — and each names what it shows:
`tessellated solids of the accepted revision; collision proxies not drawn`
(ADR-333). Each frame shows exactly that: the printed base with its clevis, the
shoulder and elbow servo cases with their horns, the upper arm and the rounded
forearm — not the twenty declared proxies. Both browser checks decoded the
downloaded file to the recorded 41 frames with matching digests.

**While the trainer was active.** The observer's fresh visit selected
`RUN heron1` without a click, loaded 15 components, and saw six successive
trainer updates each reach the page within 1.1 s of being committed, after one
navigation. The checkpoint video was declared, rolled and rendered with the
trainer at updates 18–37; the 13.2 s render fell across plain updates 23–35,
and the eleven update intervals inside the render window have a median of
1.072 s against 1.071 s in the 90 s before and 1.070 s in the 90 s after
(largest during the render 1.077 s). One bounded concurrent render cost the
trainer nothing measurable. The other loads during the run were the checkpoint
declaration, rollout and record, the observer, and one browser check; the
ten-seed evaluations ran after the trainer had exited.

**At the end** a fresh visit selects `heron1-final`, loads its 15 components
(53 620 triangles from the rollout leg's own STL exports), shows solids by
default and the proxy outlines under the labelled toggle; `/api/project` serves
`ot6-heron` at accepted revision `0c8c64c9…` (the final playback's) with three
runs — `heron1` (historical, the training run, no video), `heron1-checkpoint20`
(historical) and `heron1-final` (current) — and the reader's rule selects
`heron1-final`. [`servo-view-1400.png`](servo-view-1400.png) is the same
viewport orbited by one 200 px drag from yaw 0.8 to −1.2, looking from the −Y
side: the shoulder servo case and tab plate on the base's outboard cheek, the
elbow servo on the upper arm's, both horns and the forearm's reach in front,
with the arm at the final run's first traced pose ([servo-view.json](servo-view.json)).

## What this does not claim

One completed run, one seed for training, ten for evaluation; a fixed target,
so nothing about generalising to other reaches; pushes as the only variation;
no claim about a printed Heron's backlash, servo deadband or sag. "Reached" is
the script's 10 mm bar met at episode end and over the final second; it is not
a stationary hold, and the 3 mm low bias is observed, not diagnosed.

## Commands

```bash
P="$HOME/cadex-projects/ot6-heron"
PYTHONPATH=cli:cli/tests pixi run python docs/probes/ot6/heron/train.py "$P" heron1 "$URL"
pixi run python docs/probes/ot6/heron/evaluate.py "$P" "$HOME/cadex-projects/ot6-heron-eval-heron1-c" heron1-checkpoint20
pixi run python docs/probes/ot6/heron/evaluate.py "$P" "$HOME/cadex-projects/ot6-heron-eval-heron1-f" heron1-final
PYTHONPATH=cli pixi run python docs/probes/ot6/heron/report_training.py "$P" heron1 "$URL" "$HOME/cadex-projects" docs/probes/ot6/heron
PYTHONPATH=cli pixi run python docs/probes/ot6/heron/servo_view.py "$URL" docs/probes/ot6/heron heron1-final
```
`$URL` is the persistent operator address, read from the running service and
never committed. The driver was started by iteration 25 and finished under
iteration 26; the evaluations, receipt and frames are iteration 26's.
