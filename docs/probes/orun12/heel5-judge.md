# orun12 P1 (O2a): heel5-s1 at 25 and 50, and heel6-s1's budget

Verified against source: 2026-10-20. Frozen evidence (orun12, iteration 11).

## heel5-s1 at 25 and 50

heel5-s1 (`44411418`, digest `e4327e17`; `heel5-pitch.md`) is heel3-s1's
task with `heel_pitch` (weight 10) in place of `track_ankle`. It is cold,
4096 envs, seed 0. Its checkpoints were judged on the bundle's
`gallop_spec`, seeds 1001–1010, on the CPU, about 37 s each:

```
CUDA_VISIBLE_DEVICES= PYTHONPATH=cli pixi run python docs/probes/orun11/judge.py \
    ~/cadex-projects/feline-v07 RUN/train RUN/train/gallop.000050.cxpolicy heel5-s1-50
python3 docs/probes/orun12/legs.py ~/cadex-projects/feline-v07/evaluations/heel5-s1-{25,50}
python3 docs/probes/orun12/stance_pose.py RUN/train/cat_model-model.xml \
    ~/cadex-projects/feline-v07/evaluations/heel5-s1-{25,50}
```

The rows beside it are heel3-s1 (the same task without `heel_pitch`) and
heel4-s1 (with `track_ankle` instead) at the same iterations.

| checkpoint | pass | hock down LH / RH | at toe-off LH / RH | heel mm LH / RH | metatarsus pitch LH / RH | top 2 s m/s min / med / max | touchdown Hz LH / RH | stride mm LH / RH | overreach mm LH / RH | flight s | worst RMS/rated | peak margin | loop gap mm |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| heel3-s1-25 | 0/10 | 0.07 / 0.07 | 0.00 / 0.03 | 41 / 50 | 49 / 56 | 1.41 / 1.55 / 1.71 | 3.67 / 3.67 | 537 / 547 | −78 / −140 | 0.04 | 1.54 (j_spine) | 0.00 | 3.4 |
| heel5-s1-25 | 0/10 | 0.13 / 0.16 | 0.06 / 0.06 | 14 / 12 | 23 / 22 | 1.10 / 1.16 / 1.86 | 2.56 / 2.44 | 405 / 424 | −81 / −142 | 0.22 | 1.43 (j_spine) | 0.00 | 3.8 |
| heel3-s1-50 | 0/10 | 0.17 / 0.07 | 0.00 / 0.00 | 12 / 25 | 26 / 38 | 2.92 / 3.02 / 3.10 | 2.50 / 2.78 | 1195 / 1188 | 283 / 221 | 0.12 | 2.15 (j_spine) | 0.00 | 3.6 |
| heel4-s1-50 | 0/10 | 0.14 / 0.07 | 0.15 / 0.06 | 28 / 40 | 39 / 49 | 2.83 / 3.21 / 3.33 | 4.28 / 5.17 | 676 / 663 | −278 / −277 | 0.10 | 1.66 (j_tail1) | 0.00 | 3.4 |
| **heel5-s1-50** | 0/10 | **0.19 / 0.18** | 0.32 / 0.09 | 11 / 8 | 18 / 18 | 2.90 / 2.99 / 3.11 | 2.44 / 2.44 | 1189 / 1203 | 339 / 314 | 0.18 | 2.11 (j_spine) | 0.00 | 2.8 |

The heel shares come from `legs.py`, which reads the medians over seeds of
the engine's `detail.heels`. The metatarsus pitch and the stance pose come
from `stance_pose.py`. Its stance frames equal the engine's
(627 / 865 at 50).

Other predicates at heel5-s1-50:

- passing on 10/10: completes, no_fall, upright, straight, every_stride
  and overreach (median 313 mm);
- no_tap 0/10, with a median of 1.62;
- top_speed 0/10 (the bar is 5 m/s).

There are no falls, and every stride has a flight phase. At 25, no_tap
passed on 4/10 (median 1.11).

**The heel is the best yet at 50, and the legs are alike.**

- Both shares are above the 0.15 stop bar, so heel5-s1 runs on to 100.
- The right heel's 0.18 is 2.6× heel3-s1's 0.07 at the same iteration, and
  the first right heel of the run above 0.09.
- The left/right spread is 7%, against 60% on heel3-s1.
- The heels sit at 11 / 8 mm, the lowest of any policy, and the stride
  matches heel3-s1's at the same speed.
- The left heel is down at toe-off on 0.32 of toe-offs.
- `hock_down` still fails on every seed. The predicate asks for 0.40, so
  the share has to double.

**`heel_pitch` moved what it pays (O5).** The stance metatarsus fell from
heel3-s1's 26 / 38° to 18 / 18°. heel3-s1's right-leg handedness is gone:
the right knee is at −2° against the left's +14°, where heel3-s1's right
knee folded 23° more. The term pays 0.62 of full on both legs in stance.

The binding limit is unchanged. Across both legs' stance frames at 50, the
heel is down on 0.67 of frames at 5–10°, 0.08 at 10–15° and 0 at 15° or
more. The median of 18° still sits above the bar, so the next gains come
from pushing the pitch under 10°, not from new terms. heel6-s1's flat clip
asks for 7.5°.

Torque (O4): the worst drive is `j_spine` at 2.11× rated RMS, about
heel3-s1's 2.15. One drive reaches its clamp on every seed (peak margin
0.00), as on every policy judged. The loop gap is 2.8 mm, still over O9's
2 mm.

## Timing, and heel6-s1's budget

heel5-s1's checkpoints landed at 00:30:29 (25) and 00:58:20 (50).

- The run started at 23:56:49.
- That is 67 s an iteration, after about 340 s to the first iteration.
- So 100 iterations come to about 7,040 s, inside `budget_s` 9,000.

The critic asked for heel6-s1's budget to carry O8's 20% over the earlier
8,060 s estimate. The queued heel6-s1 was stopped by PID while still
waiting. It was re-queued with the same command, revision guard
(`d3b4e838`) and 4096 envs, at `budget_s` **9,700**, in its own
`systemd-run --user --scope -p MemoryMax=30G`. It starts when heel5-s1
ends.
