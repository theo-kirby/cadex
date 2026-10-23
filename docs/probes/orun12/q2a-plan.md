# orun12 Q2 (O9, O3): the paw in the forearm is the policy's; heel7-s1 at 25; the q2a screen

Verified against source: 2026-10-20. Frozen evidence (orun12, iteration 20).

## O3: the right hind paw in the right forearm swaps sides under the mirror

`heel5c-final-q2.md` found the P1 policy (`910cdb5a`) putting the right hind
paw 8.5 mm into the right forearm's outer panel on 10 of 10 seeds, with no
pair on the left. O3 asks for a mirror test before any explanation. The
model was already shown to mirror and the clip to be symmetric
(`heel2-clip.md`), so the policy was mirrored with `mirror_policy.py`
(witness error 2.8e-14) and judged on the same ten seeds. The mirrored
evaluation was then replayed against the real meshes:

```
pixi run python docs/probes/orun12/mirror_policy.py RUN/train/cat_model-model.xml \
    RUN/train/gallop.cxpolicy RUN/train/gallop.mirror-final.cxpolicy
CUDA_VISIBLE_DEVICES= PYTHONPATH=cli pixi run python docs/probes/orun11/judge.py \
    ~/cadex-projects/feline-v07 RUN/train RUN/train/gallop.mirror-final.cxpolicy heel5c-s1-finalm
CUDA_VISIBLE_DEVICES= PYTHONPATH=cli pixi run python docs/probes/orun12/trace_check.py \
    ~/cadex-projects/feline-v07 RUN/train/cat_model-model.xml \
    ~/cadex-projects/feline-v07/evaluations/heel5c-s1-finalm --jobs 10
```

(RUN is `~/cadex-projects/feline-v07/runs/heel5c-s1`.)

Real-mesh pairs over 5 mm (frames / deepest mm / seeds):

| pair | 910cdb5a | mirrored |
|---|---|---|
| hind paw × forearm outer panel | **R**: 205 / 8.5 / 10 | **L**: 238 / 8.3 / 10 |
| forearm × hind paw | R: 29 / 6.5 / 9 | L: 35 / 7.1 / 8 |
| humerus × hind paw | R: 5 / 6.7 / 4 | L: 4 / 5.9 / 3 |
| chest frame × wrist drive | R: 117 / 6.3 / 10 | L: 84 / 6.2 / 10 |
| chest frame × forearm | R: 4 / 5.3 / 4 | L: 6 / 5.6 / 4; R: 1 / 5.4 / 1 |
| battery × forearm | R: 5 / 5.3 / 4 | L: 2 / 5.1 / 2 |

**Every pair swaps sides**, at about the same depth and frequency. The
model and the simulation are not handed. The policy is: its right hind
overreaches into the right fore leg, and its right wrist drive folds into
the chest. A symmetry term would not cure a collision the model does not
register. The geometry the sim does not see would stay unseen.

The judged predicates match too. hock_down 10/10 (0.603 against 0.602),
hock_at_toeoff 8/10, overreach 289 / 279 mm (mirror of 279 / 286), and
2.86 m/s median (2.91). One number does not mirror: the rotary count, 54
of 176 ordered strides on the policy against 1 of 208 on its mirror.
`legs.py`'s classifier is mirror-symmetric. The fore pair's median lag is
0.0 (`pair_lag_fore_median`), so the fore paws land almost together, and
the stride's order turns on which fore lands a frame first. The rotary
count on this policy is noise around a simultaneous fore pair. It is not
evidence of a handed gait. P2's rotary bar needs a fore lag, not a side.

## The fore-rod loop cannot be stiffened by solref

The critic asked for a stiffer fore-rod `solref`. Every `equality/connect`
in the export already carries `solref` 0.004 = 2 × the 2 ms timestep and
`solimp` (0.99, 0.9999, 0.0001) (`CadexDynamics.py`, `_EQUALITY_SOLIMP` and
`equality.solref = [2.0 * time_step_s, 1.0]`). The comment there records
that two timesteps is the stiffest time constant the integrator accepts.
There is nothing stiffer to declare. The 2.7 / 2.9 mm fore gaps can close
only through:

- a smaller timestep, which would be an engine change and would double the
  step cost;
- less load through the rod, which is the policy's to give.

No engine change was made. The q2a screen measures the gap again under the
damped paw pin.

## heel7-s1 at 25

heel7-s1 (`de868f8f`: heel5-s1's 18-term task on the `flat_feet` clip,
`pin_damp` 3.0, cold, 4096 envs) left `gallop.000025.cxpolicy`. It was
judged on the CPU as the run went on (`judge.py ... heel7-s1-25`,
`legs.py`, `stance_pose.py`, `paw_pin.py`):

| checkpoint | pass | hock down LH / RH | at toe-off LH / RH | heel mm LH / RH | metatarsus deg LH / RH | top 2 s m/s min / med / max | touchdown Hz LH / RH | fore/hind touchdown ratio max | stride mm LH / RH | overreach mm LH / RH | flight s | rotary | worst RMS/rated | peak margin | loop gap mm |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| heel5-s1-25 | 0/10 | 0.13 / 0.16 | 0.06 / 0.06 | 14 / 12 | 23 / 22 | 1.10 / 1.16 / 1.86 | 2.56 / 2.44 | 1.11 | 405 / 424 | −81 / −142 | 0.22 | 97/158 | 1.43 (j_spine) | 0.00 | 3.8 |
| **heel7-s1-25** | 0/10 | 0.10 / 0.13 | 0.06 / 0.07 | 17 / 15 | 25 / 23 | 1.30 / 1.48 / 1.92 | 2.78 / 3.78 | 1.55 | 516 / 277 | −34 / −167 | 0.20 | 154/185 | 1.49 (j_spine) | 0.00 | 3.9 |

Hind paw pin (`paw_pin.py`), steps over 900 °/s, LH / RH:

| evaluation | snaps | rate p99 deg/s |
|---|---|---|
| heel5-s1-25 | 0.106 / 0.079 | 1518 / 1468 |
| heel7-s1-25 (`pin_damp` 3.0) | **0.002 / 0.007** | 729 / 849 |
| heel5c-s1-final (P1) | 0.104 / 0.145 | 1495 / 1851 |

- At 25 the heels sit where heel5-s1's did (0.10 / 0.13 against
  0.13 / 0.16). The stance pitch is the same (23–25°), and the heel is down
  at 5–10° of metatarsus pitch on 0.84 of frames. O2a's stop rule (both
  heels under 0.15 at 50) is judged at 50.
- The hind legs are not yet alike. Stride is 516 / 277 mm and touchdown
  3.78 against 2.78 Hz, so the right steps twice for some left strides.
  `no_tap` fails 0/10 (1.55). Not judged for Q1: this is an iteration-25
  policy.
- **`pin_damp` 3.0 does what `pin-candidate.md` predicted.** The pin's
  snaps fall from about 10% of frames to under 1%, on a policy at the same
  stage. This is the `pin_damp` the q2a screen takes.

## heel7-s1 at 50

`gallop.000050.cxpolicy` (`041bbf6b`), judged the same way:

| checkpoint | pass | hock down LH / RH | at toe-off LH / RH | heel mm LH / RH | metatarsus deg LH / RH | top 2 s m/s min / med / max | touchdown Hz LH / RH | fore/hind touchdown ratio max | stride mm LH / RH | overreach mm LH / RH | flight s | rotary | pin snaps LH / RH | worst RMS/rated | peak margin | loop gap mm |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| heel5-s1-50 | 0/10 | 0.19 / 0.18 | 0.32 / 0.09 | 11 / 8 | – | 2.90 / 2.99 / 3.11 | 2.44 / 2.44 | 1.62 (no_tap) | 1189 / 1203 | 339 / 314 | 0.18 | 117/149 | – | 2.11 (j_spine) | 0.00 | 2.8 |
| **heel7-s1-50** | 0/10 | 0.09 / 0.17 | 0.21 / 0.21 | 17 / 11 | 26 / 22 | 2.90 / 2.94 / 3.00 | 2.33 / 2.44 | 1.94 | 1188 / 1193 | 241 / 379 | 0.16 | 57/125 | 0.012 / 0.004 | 2.18 (j_spine) | 0.00 | 3.3 |

- O2a's stop rule (both heels under 0.15 at 50) does not fire. The right
  heel is at 0.17. The run continues to 100.
- At 50, heel7-s1 is behind heel5-s1 on the left heel (0.09 against 0.19)
  and on fore taps (`no_tap` 1.94 against 1.62). Its heels are 48% apart,
  with the left the lower one. Toe-off (0.21 / 0.21) is level with heel5's
  better leg. Speed is the same, 2.94 m/s.
- The damped pin holds: snaps 1.2% / 0.4% of frames, against heel5c's
  10% / 15%.

So far the `flat_feet` clip has not beaten heel5's clip. That is why q2a
takes heel5's clip and only heel7's `pin_damp`.

## The q2a screen (specified and queued)

One cold screen aimed at Q2 on the task that reached P1:

- **heel5c-s1's task**: heel5-s1's 18 terms with `heel_pitch` weight 10, on
  heel5-s1's clip, not the `flat_feet` one;
- **`pin_damp` 3.0**, from heel7-s1-25 above;
- **a collision capsule on each forearm's outer panel**: r 20 mm, 71 mm
  between centres, fore-aft through the panel's outer half at
  (185.4, ±140, 161) mm. The panel spans x 130–241, |y| 100–160, z 137–185
  in the build pose. The capsule is in the limb group (3, meeting 0, 1, 3),
  so it meets both paws. It is a contact setting on a part, so the part's
  shape, mass and joints are unchanged (O1);
- no `solref` change (above);
- cold, because the model's digest changes (ADR-736);
- 200 iterations, 4096 envs, seed 0, a checkpoint every 25. P1 took about
  205 iterations on this task (heel5-s1 100 + heel5c-s1 105), so a
  100-iteration screen could not judge it;
- `budget_s` 19,500. heel7-s1 runs at about 79 s an iteration with
  `pin_damp` 3.0, so 200 iterations take about 15,800 s, plus 23% (O8).

The revision is `/tmp/o12/v07-q2a.py`, which is heel7's accepted script
(`de868f8f`) with `flat_feet` removed and the two panel shapes added. It
was built with `cadex script --set` as feline-v07 revision **`7ccbf80f`**,
digest `ec9f54bf`. The checks on the built bundle:

- Its `gallop-task.json` equals heel5c-s1's in every field but the model's
  bytes and digest. The 18 terms, the clip and the tracking table are
  unchanged.
- The MJCF has `c_pnl_forearm_{l,r}_outer/collision0`: a capsule of
  0.02 × 0.0355 m at (0.1854, ±0.14, 0.161), contype 8, conaffinity 11.
- In the keyframe neither capsule touches anything, and the nearest geom
  it can collide with is its own fore paw, 98.7 mm away.
- `j_pawpin_*` damping is 0.1719 N·m·s/rad, as on heel7.

It is queued as **q2a-s1** behind heel7-s1:

```
systemd-run --user --scope -p MemoryMax=30G env PYTHONPATH=cli pixi run python \
    docs/probes/orun12/queue_run.py ~/cadex-projects/feline-v07 q2a-s1 19500 200 "..." \
    --expect-revision 7ccbf80f --seed 0 --envs 4096
```

heel7-s1 trains on its own registered bundle and is not touched by the new
revision.

Judged at every checkpoint on P1 per leg, the pin's snap share, the loop
gaps and `trace_check.py`'s mesh pairs. The aim is to show whether the panel
capsule removes the 8.5 mm pair while the heel stays down.
