# orun18 B1: leo v05 on speed alone, the task and its launch

Verified against source: 2026-10-23. D4's task, written and launched cold
after A3 cleared the trainer (`a2.md`). Judging comes in later iterations, at
50 and at the end.

## The task, `speed`

`~/orun18-queue/orun18-b1.py` is leo's head script (`3b0942b`, sgt-5) with
two additions, set with `./cadex script --project ~/cadex-projects/leo --set`.
Leo accepted it as revision **`11140180`** (digest `ddab1aae`, project commit
`249c8bc`, ~4 min from the fit and part caches). The **model is unchanged**: the bundle's
model is `59bc5407…`, the same as sgt-4's and sgt-5's, and clearance reads as
at baseline (sweep 12 pairs, mounting pass, 46 panels reported, 0 failing).

1. **Command channels.** Each of the 20 leg and spine drives gets a
   `command` observation, `a_<tag>` and `a_<tag>_rate` (ADR-696), with
   `role="privileged"`. The reward reads them and the actor does not, so B1's
   actor reads exactly sgt-5's 55 channels. They are not sensors and do not
   count against the 128-channel cap (leo is at 122).
2. **`result["speed"]`**, beside `gallop_sg`:

| | B1 `speed` | sgt-4 / sgt-5 `gallop_sg` |
|---|---|---|
| reference clip | **none**; reset from the `solved` keyframe plus the reset variation | SG's 5-stride schedule, random start |
| goal | `cmd` speed 700–5000 mm/s, resampled every 3 s, 1 s ramp | 700–2400 mm/s, the same timing |
| reward terms | 10 | 18 (sgt-4), 19 (sgt-5) |
| kept from SG | `alive` 4; `track_speed` 20 (SG's tent: linear to the command, half the slope back past it); `near_peak` −0.5; `height_over_ground` −1; `posture` −1; `straight` −1; `tail` −2 | |
| added (D4's regularisers) | `torque` −0.5: mean over the 21 effort drives of (τ / rated)², 0.5 a step with every drive at its rating; `energy` −1: Σ \|dq·τ\| in kW; `action_rate` −0.05: Σ (command rate / 600 °/s)² over the 20 drives | none of the three |
| dropped (D4) | `track_pose`, `track_lift`, `track_contact`, `fore_tap`, `heel_pitch`, `paw_flat`, `fore_sync`, `hind_lag`, `heel_sched`, `overrun`, `hind_scuff`, `fore_lag` | |
| terminations | `tipped` (up < 0.85), `collapsed` (scan_4 below stand − 70 mm) | the same |
| randomisation | chest mass ×0.9–1.1; reset velocity up to 150 mm/s, 10 °/s | the same |
| episode | 10 s, 50 Hz, 2 ms solver step × 10 | the same |
| success (judging only) | `speed_spec`: completes, no_fall, upright, straight, top_speed ≥ 5000, hock_down ≥ 0.4 (reported), within_rated; C2_SEEDS 1001–1010; the goal's sequence swapped per judged command | `sg_spec` |

`tail` (tail links off the floor) and `straight` (D9's straight line) are
kept as staying-up terms, not style: neither says how a foot lands. The three
regularisers' weights are this run's choice, sized so each costs well under a
tenth of `alive + track_speed` in a vigorous gallop. No screen has priced
them on leo yet.

`no_tap`, `every_stride` and `overreach` leave the spec because the engine
computes them against a reference (`CadexEvaluation` needs `reference`), and
this task has none. Footfall order, flight, heel share and U are read from
the traces by the judge (D4: measured, not rewarded).

**Side effect on `gallop_sg`.** The command channels live on the model's
observation list, so the head's `gallop_sg` bundle now also carries 20
privileged command channels. Its rewards, reference and actor inputs equal
sgt-5's, but its task digest does not: a warm start from sgt-4 or sgt-5
re-sets `orun17-sgt4.py` or `orun17-sgt5.py` first, as orun17 did between
revisions.

## The launch

```
systemd-run --user --scope -p MemoryMax=30G env PYTHONPATH=cli pixi run python \
    docs/probes/orun13/queue_run.py ~/cadex-projects/leo b1-s1 18000 180 \
    "orun18 B1: ..." --expect-revision 11140180 --seed 0 --task speed --envs 4096
```

Cold, seed 0, 4096 envs, 180 iterations, checkpoints every 25 (50 is a
judged checkpoint), budget 18,000 s: orun17's ~83 s an iteration × 180 + 20 %.
Registered and launched 2026-10-23 06:18:51 as `runs/b1-s1`.

**The first ten iterations** (`runs/b1-s1/train/progress.json`): iteration 0
at 232 s (the compile), iteration 9 at 850 s, so **68.7 s an iteration**,
faster than sgt-4's ~83 s with no reference to track. 180 iterations come to
~12,500 s, and D7's asked + 20 % is ~15,000 s. The run was launched with
18,000 s from orun17's rate, before the timing: the cap is looser than D7's
by ~3,000 s and changes nothing unless the run stalls. Reward per step
−9.82 → −6.08 over iterations 0–9. The episode's mean length falls from 50
to 30 steps meanwhile: from the standing keyframe the cold policy falls
within a second.
