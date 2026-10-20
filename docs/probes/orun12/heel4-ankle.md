# orun12 P1 (O2a): heel3-s1 at 25 and 50, and why the heel stays up

Verified against source: 2026-10-19. Frozen evidence (orun12, iteration 7).

## heel3-s1 at 25 and 50

heel3-s1 (`ac32d3b0`, digest `814e5213`; `heel3-screen.md`) is cold, at 4096
envs, and runs about 68 s an iteration. Its checkpoints were judged on the
bundle's `gallop_spec`, seeds 1001–1010, on the CPU:

```
CUDA_VISIBLE_DEVICES= PYTHONPATH=cli pixi run python docs/probes/orun11/judge.py \
    ~/cadex-projects/feline-v07 RUN/train RUN/train/gallop.000050.cxpolicy heel3-s1-50
python3 docs/probes/orun12/legs.py ~/cadex-projects/feline-v07/evaluations/heel3-s1-{25,50}
```

| checkpoint | pass | hock down LH / RH | at toe-off LH / RH | heel height mm LH / RH | top 2 s m/s (median) | overreach mm LH / RH | touchdown Hz LH / RH | worst RMS/rated | peak margin | loop gap mm |
|---|---|---|---|---|---|---|---|---|---|---|
| 25 | 0/10 | 0.07 / 0.07 | 0.00 / 0.03 | 41 / 50 | 1.55 | −78 / −140 | 3.67 / 3.67 | 1.54 (j_spine) | 0.00 | 3.4 |
| 50 | 0/10 | 0.17 / 0.07 | 0.00 / 0.00 | 12 / 25 | 3.02 | 283 / 221 | 2.50 / 2.78 | 2.15 (j_spine) | 0.00 | 3.6 |

At 50, overreach passes on 10/10, every_stride passes on 10/10, and every
stride has a flight phase (0.12 s). no_tap fails, with a median of 1.42.
The heels come lower: 12 / 25 mm, against heel2-s1's 24 / 19 at 50.
But the heel share barely moves (0.17 / 0.07), and no toe-off has a heel
down. The policy runs at **3.02 m/s even though speed is paid only up to
2 m/s**, so the speed cap did not hold the speed down.

The left heel's 0.17 is above the critic's 0.15 stop bar, so heel3-s1 runs
on to 100. Its 75 and 100 are still to be judged.

## The hock never takes the clip's heel-down angle

`hock_stance.py` (new) compares the hind hock's angle while the paw is in
stance with the clip's ankle-pin angle on the samples where the clip holds
the heel down. The hock drives the pin 1:1 through the parallelogram.

```
python3 docs/probes/orun12/hock_stance.py ~/cadex-projects/feline-v07/evaluations/{v07-g1-100,heel2-s1-50,heel2-s1-75,heel3-s1-25,heel3-s1-50}
```

| evaluation | leg | hock in stance p10 / p50 / p90 deg | clip ankle, heel down, deg | median gap deg |
|---|---|---|---|---|
| v07-g1-100 | LH | −16 / 6 / 13 | −30 … −24 | +33 |
| v07-g1-100 | RH | −15 / 7 / 20 | −30 … −24 | +34 |
| heel2-s1-50 | LH | −57 / 10 / 21 | −30 … −11 | +30 |
| heel2-s1-50 | RH | −11 / 0 / 12 | −30 … −11 | +21 |
| heel2-s1-75 | LH | −18 / 21 / 27 | −30 … −11 | +41 |
| heel2-s1-75 | RH | −6 / 2 / 27 | −30 … −11 | +23 |
| heel3-s1-25 | LH | −23 / 3 / 15 | −30 … −11 | +24 |
| heel3-s1-25 | RH | −13 / 9 / 16 | −30 … −11 | +30 |
| heel3-s1-50 | LH | −54 / 6 / 22 | −30 … −11 | +27 |
| heel3-s1-50 | RH | −58 / 10 / 22 | −30 … −11 | +31 |

(The right leg's sign is folded onto the left's.) On every judged policy,
on both legs, the stance hock's median is **21–41° above** the angle the
clip lays the heel down at. The paw stays on its toes because the hock
holds the metatarsus up.

The reward cannot see that gap. `track_pose` is
`exp(-Σ(q − q_ref)² / (900 · 19))` in degrees, at weight 1.5. A 30° error on
one hock costs `1 − exp(−900/17100)`, which is 5% of 1.5, or 0.08 a step.
The plantigrade term (10) pays the heel's contact, not the angle that
reaches it. So the policy is not pushed toward the pose that would earn it.

## heel4-s1: the ankle pins get their own tracking term

feline-v07 was rebuilt with one task change (O1, O2a): revision
`5bcadba8`, digest `39165e25`, and the same model bytes ("kept revision 12's
model").

```
track_ankle = (exp(-((q_ankle_l - q_ankle_l_ref) / 10)^2)
             + exp(-((q_ankle_r - q_ankle_r_ref) / 10)^2)) / 2      weight 6
```

- The term covers the whole stride and is 10° wide.
- It is a literal, because the script is at the 64-parameter cap.
- At the gaps above (about 27°), it pays about `exp(−7.3)` ≈ 0.001 of its 6.
  That is an estimate from the stance medians, not a per-step evaluation:
  the traces carry the hock but not the clip phase. So the term has nearly
  its whole weight to give.
- Everything else stays as heel3-s1 had it: `plant_w` 10, the speed pay
  capped at 2 m/s, and the chest box. That makes 18 terms.

heel4-s1 is cold, 100 iterations, 4096 envs, seed 0, with `budget_s` 9,000
(100 × about 68 s, plus 20% and the compile). It was queued with
`queue_run.py --expect-revision 5bcadba8 --envs 4096`, and it launches
when heel3-s1 ends.

It differs from heel3-s1 in this one term. So heel3-s1's 75 and 100,
against heel4-s1 at the same iterations, show whether the ankle term moved
the heel share (O5).
