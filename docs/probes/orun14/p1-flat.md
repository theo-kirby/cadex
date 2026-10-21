# orun14 P1: the paw's floor pitch, read right, and a term on it

Verified against source: 2026-10-21. Follows `g1-free-50.md`.

## The floor-pitch column, fixed (`paw_floor.py`)

`floor_pitch` took the paw's forward direction from the paw body's own x
axis, projected flat. That axis pitches with the paw, so at a pin of about
45° toes-up its flat part was short and turned. That is why g1-free-50 read
+146° / +78°. Forward is now the horizontal normal to the pin's axis (the
paw's local y), signed to world +x (the runs are straight, O10).

g1-free-50 re-read (medians over 10 seeds; the other columns are as in
`g1-free-50.md`):

| leg | on-ground F / R / T / U | floor pitch ° in stance | pin ° in stance | pin ° / floor pitch ° at lift | lifts toes-up of floor |
|---|---|---|---|---|---|
| LH | 0.02 / 0.22 / 0.00 / 0.76 | **+32.8** | +43.8 | +48.9 / +7.0 | 0.50 |
| RH | 0.03 / 0.19 / 0.01 / 0.77 | **+25.7** | +38.1 | +37.9 / +20.0 | 0.63 |

g1-free-25 reads +0.7 / +1.9 (flat paws, heels up), as before. The
diagnosis in `g1-free-50.md` stands: g1-free-50's hind paws stand toes-up
of the floor in stance.

## The floor pitch from channels (`paw_flat.py`)

The task already reads the metatarsus as heel_pitch's `_META`. The pin turns
the paw toes-up of the metatarsus by `-q_pawpin_l` / `+q_pawpin_r`. So:

    F = toes-up pin − _META + C

On 9,826 paw-down frames of g1-free-25 and g1-free-50, C = +1.89. F matches
the pad-to-toe floor pitch within 2°, p10–p90, on each leg and evaluation:

| evaluation | leg | frames | F − floor pitch p10 / median / p90 ° | floor pitch median (p10–p90) ° | U share |
|---|---|---|---|---|---|
| g1-free-25 | LH | 3,672 | −0.1 / +0.1 / +1.4 | +0.7 (−2.2–+3.6) | 0.02 |
| g1-free-25 | RH | 3,859 | −0.5 / −0.1 / +1.2 | +1.9 (−0.1–+3.8) | 0.03 |
| g1-free-50 | LH | 1,273 | −0.3 / +0.3 / +2.2 | +33.1 (+0.9–+50.9) | 0.75 |
| g1-free-50 | RH | 1,022 | −1.9 / −0.3 / +0.4 | +26.7 (−1.1–+48.4) | 0.71 |

The geometry and the joint chain are two independent readings, and they
agree, which also checks the fixed column.

## The term: `paw_flat` (O7, scored before training)

    paw_flat = (ref_lh_down · chl_down · max(0, 1 − |F_l| / 15)
              + ref_rh_down · chr_down · max(0, 1 − |F_r| / 15)) / 2,  weight 10

The term pays the paw lying flat on the floor in the clip's hind stance.
It pays a heel-up roll on a flat paw just as it pays a flat foot, because
the pin is there for that roll (O2). heel_pitch, which reads only the
metatarsus, stays.

Mean pay on paw-down frames, split by `paw_floor.py`'s letters:

| evaluation | leg | all | F flat | R roll | T toes | U toes-up |
|---|---|---|---|---|---|---|
| g1-free-25 | LH | 0.84 | 0.86 | 0.86 | 0.23 | 0.10 |
| g1-free-25 | RH | 0.83 | 0.89 | 0.85 | 0.28 | 0.10 |
| g1-free-50 | LH | 0.20 | 0.74 | 0.77 | 0.19 | 0.01 |
| g1-free-50 | RH | 0.22 | 0.73 | 0.77 | 0.19 | 0.01 |

- **The clip:** its 5 hind-stance samples on each leg hold the pin +17 /
  +19° toes-up, and F is +8 / +10 (−20…+14, −30…+18). The term pays the
  clip 0.15 / 0.24, so `track_pose` pulls slightly against it, as it does
  against heel_pitch (`g1-free-50.md`).
- **Compiler check:** the trainer's compiler gives the same value as the
  Python formula on every clip sample, with a worst difference of 0.

## The bundle and the screen: p1-flat

- **The script:** `orun14-p1.py` is h1-meta's script plus two changes,
  each guarded by `RIGID_FOOT and FREE_PAW`:
  - **The actor reads the paw pins.** Each pin gets an encoder, observed
    as `q_pawpin_*` and `dq_pawpin_*` (4 channels, `role="policy"`). The
    hind paws' world orientations are dropped (`ohl` / `ohr`, 8
    privileged channels): no term has read them since orun13. That leaves
    122 channels of 128.
  - **`paw_flat`** at weight 10, making 19 terms.
- **The question:** does a paw the policy can see, paid flat on the
  floor, undo g1-free's toes-up landing without losing heel share or
  speed? h1-meta, the same task without these two changes, is its
  comparison.
- **The queue:** `orun13/queue_run.py p1-flat 4800 50 --envs 4096
  --after h1-meta --build orun14-p1.py`, cold.
  - It builds once h1-meta registers.
  - It trains when the slot frees, at about 76 s an iteration, so 50
    iterations take about 3,800 s. The 4,800 s budget is that plus 20%.
  - The observations change, so a warm start is impossible.
- **Judge at 25 and at 50:**
  - with `paw_floor.py`: the floor pitch and U share in stance, and the
    pin angle;
  - with the engine: the heel share;
  - against h1-meta at the same checkpoints.
- **Keep rule:** the U share in stance under 0.2 on both legs, with heel
  share and speed no worse than h1-meta's.

## Not done this iteration

The critic also asked for orun12's mirror tests on RH's 5.5 Hz double
contact (O5). They were not run. They are the next measurement owed
before another screen is queued.
