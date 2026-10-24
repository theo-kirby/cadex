# orun19 S1: leo v06 on speed alone, the task and its launch (s1-v06 training)

Verified against source: 2026-10-23. Charter S1: orun18's B1 task
(`b1-s2`'s weights) on leo v06, trained cold. Judging comes in later
iterations, at 50 and at the end, beside v05's `b1-s2-180`.

## The task is already in v06's script

The frozen model's script (`~/orun19-queue/leo_v06.py`, leo tag `leo-v06`,
accepted revision **`62e391eb`**, the project's head is `656282c`, which
adds only clearance and render output after `356e547`) builds one task,
`speed`, and its source is b1-s2's `result["speed"]` unchanged. With
`LEAN_TASKS` (sphere feet and no wrist) nothing else is built. No script
was set this iteration, so there was no build.

Read from the two bundles, `runs/b1-s2/train/speed-task.json` (v05) and
`runs/s1-v06/train/speed-task.json` (v06, sha256 `bca307a2…`, model
`f9b8ab82…`):

| | v05 b1-s2 | v06 s1-v06 |
|---|---|---|
| reward terms, weights | alive 4, track_speed 20, near_peak −0.5, height_over_ground −1, posture −1, straight −1, tail −2, torque −0.2, energy −0.2, action_rate −0.002 | **the same ten** |
| goal | `cmd` speed 700–5000 mm/s, resample 150 steps, ramp 50 | the same |
| terminations | tipped, collapsed | the same |
| episode | 10 s, 50 Hz, 2 ms × 10, keyframe `solved` | the same |
| actions | 22 | 20: `j_wrist_l/r` gone |
| actor channels | 50 | 42: `q`/`dq` of `wrist_l/r` and `pawpin_l/r` gone |
| privileged channels | 42 | 38: `q_carpus_l/r`, `tau_wrist_l/r` gone |
| drives in `torque` and `energy` | 21 | 19 |
| commands in `action_rate` | 20 | 18 |

So the only differences are the channels and drives that went with the
model; the weights are b1-s2's. The 24 drives the charter counts include
four the task does not command (`j_neck1`, `j_neckyaw`, `j_headpitch`,
`j_jaw`, as on v05): the 20 actions are 16 leg, 2 spine and 2 tail drives.

## The launch

```
systemd-run --user --scope -p MemoryMax=30G env PYTHONPATH=cli pixi run python \
    docs/probes/orun13/queue_run.py ~/cadex-projects/leo s1-v06 15100 180 \
    "orun19 S1: leo v06 speed only, b1-s2 weights on 24 drives, cold" \
    --expect-revision 62e391eb --seed 0 --task speed --envs 4096
```

Cold, seed 0, 4096 envs, 180 iterations (b1-s2's count, so the end
judgement compares like for like), checkpoints every 25, budget 15,100 s
(b1-s2's: its 232 s compile + 179 × 68.7 s, + 20 %). Registered and launched
2026-10-23 13:53:39 as `runs/s1-v06`.

**The first ten iterations** (`runs/s1-v06/train/progress.json`,
`train/train.log`): iteration 9 at 336 s of wall, 10 at 355 s, 15 at
449 s, so **~19 s an iteration** once compiled, against b1-s2's 68.7 s on
the same 4096 envs, unroll 20 and GPU (99 % busy, 24.7 GB). The trainer's
own ETA at 15 was 4,607 s for the remaining 164, ~28 s an iteration, so the
whole run comes to ~3,500–5,000 s, and O5's asked + 20 % is ~5,500 s. The
budget was set at launch from b1-s2's rate, before the timing, and the
supervisor reads it once at launch (`cadex_cli/loop.py`), so the 15,100 s
cap is ~3× looser than O5's. It changes nothing unless the run stalls; it
was not relaunched to tighten it. Why v06 is ~3–4× faster is not measured
here; the likely cause is fewer contacts and constraints (spheres for the
paw meshes, no paw pin, no wrist rod loop).

Reward per step over iterations 0–15: +0.09, 0.21, 0.18, 0.73, 1.63, 2.35,
2.72, 2.90, 3.17, 3.37, 3.49, 3.57, 3.68, 3.84, 3.87, 4.00. Episode length
20, 30, 59, 43, 35, 33, 34, 35, 40, 43, 48, 50, 57, 64, 67, 68 steps: past its
low and lengthening, with σ 0.92 → 0.85. b1-s2 was still negative through
iteration 6 (−0.93 at 0, +3.56 at 12) with episodes of 35–49 steps at 9–12:
v06 starts positive and its episodes lengthen sooner.

Iteration 50 is S1's first judged checkpoint (`speed.000050.cxpolicy`),
with orun18's `speed_judge.py` and `b1_summary.py`, beside `b1-s2-180`.
