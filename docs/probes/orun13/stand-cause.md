# orun13 B1: g1-s1 at 50 still stands, and why leo stood cold

Verified against source: 2026-10-20. Frozen evidence (orun13, iteration 3).

## g1-s1 at 50 (final, `gallop.cxpolicy`, sha256 `84806d76`)

Judged as `g1-s1-25.md`, on the bundle's `gallop_spec`, seeds 1001–1010,
on the CPU (`judge.py`, `legs.py`, `p2_lag.py`, `spine_foot.py`,
`trace_check.py`):

| evaluation | pass | top 2 s m/s min / med / max | hock_down LH / RH | at toe-off LH / RH | no_tap | every_stride | overreach mm LH / RH | stride mm | worst RMS/rated | peak margin | front rod loop max mm |
|---|---|---|---|---|---|---|---|---|---|---|---|
| heel5c-s1-final (orun12) | 0/10 | 2.81 / 2.91 / 3.01 | 0.60 / 0.61 | 1.00 / 1.00 | 10/10 | 10/10 | 279 / 286 | – | 2.01 (j_spine) | 0.00 | 2.9 |
| g1-s1-25 | 0/10 | 0.11 / 0.21 / 0.27 | 0.47 / 0.20 | 0.71 / 0.29 | 0/10 | 0/10 | −214 / −224 | – | 2.36 (j_tail1) | 0.00 | 3.0 |
| **g1-s1-50** | 0/10 | **0.24 / 0.32 / 0.45** | 0.09 / 0.21 | 0.09 / 0.00 | 4/10 | 9/10 | −186 / −148 | 92 / 93 | 1.98 (j_tail1) | 0.00 | 2.7 |

- `completes`, `no_fall`, `upright` (18.9° median) and `straight` pass
  10/10. P1 0/10: `hock_down` median 0.087, `hock_at_toeoff` 0.
- **It shuffles in place.** The paws step at 2.44 Hz (the clip's clock)
  with 92 mm strides; 27 strides over ten seeds, 14 of them tied, 2/10 seeds
  rotary. The pair lags read 0 (fore) and 0.024 (hind) of a cycle, so the
  footfalls are tied (O3).
- **Spine.** Both joints sit flexed between −10° and −25° each. They swing
  14.4° (sum of the two) per stride at the median. 0.00 of frames are
  within 1° of a stop; the cable gap is at most 0.19°.
- **Feet.** Heel share 0.09 / 0.21 (the engine's equal). When the heel is
  down the toes are up in 0.90 / 0.83 of those frames: it rocks back on
  its heels, as at 25.
- **Trace.** No real-mesh pair deeper than 5 mm. Front rod loops 2.54 /
  2.69 mm, over O9's 2 mm (already on the Q2 list). Front paw meshes 16.8
  / 17.7 mm under the floor (the 18 mm front paw mesh offset from
  `g1-s1-25.md`).

The trainer's reward rose to 16.27/step at 49 while the judged speed stayed
under 0.5 m/s, so the reward was paying the shuffle.

## Why it stood: the task was not heel5's (`reward_terms.py`)

`docs/probes/orun13/reward_terms.py` (new) scores a bundle's reward and
terminations per step with the trainer's own expression compiler, channel
order, contact flags, tracking clock and height scan, on stock MuJoCo on
the CPU. It runs three scenarios:
- `hold`: from each of the 21 clip samples, every drive held;
- `keyframe`: the `solved` keyframe, held;
- `clip`: the clip replayed kinematically.

Means per step after the first 0.5 s, over 3 s:

| term | g1-s1 hold | g1-s1 keyframe | **g1-s1 clip** | heel5c (v07) clip | **g2-heel5 clip** |
|---|---|---|---|---|---|
| track_speed | −0.06 | 0.00 | **3.34** | 16.70 | **16.70** |
| track_contact | 4.13 | 2.12 | 8.45 | 8.07 | 8.51 |
| heel_pitch | 1.39 | 0.00 | 2.24 | 1.69 | 2.18 |
| fore_tap | −4.90 | −6.46 | −0.57 | −0.57 | −0.49 |
| hind_flat | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| plantigrade (kinematic, reads 0) | 0.33 | 0.00 | 0.00 | 0.00 | 0.00 |
| outside_hind | – | – | – | 0.64 | 0.65 |
| **total** | 4.44 | 4.17 | **18.68** | 32.44 | **32.38** |

- **The cause.** leo's `script.json` stores no parameter values, so the
  gallop task was built on the script's declared defaults. feline v07, where
  heel5 trained, stores `sprint_speed` 2000, `sprint_speed_w` 20, `plant_w`
  10 and `outside_hind_w` 4. On leo these defaulted to 7000, 14, 4 and 0.
  - `track_speed` became 14 · v / 7 m/s instead of 20 · min(v, 2 m/s) /
    2 m/s.
  - At the clip's 1.68 m/s that pays **3.34 per step instead of 16.7**.
  - So the speed share of perfect tracking fell from 51% to 18%.
  - A policy that steps in place on the clip's clock collects most of what
    is left: alive 4, contact, pose, lift, fore_sync and heel_pitch.
  - g1-s1 found that shuffle and the trainer's reward climbed on it.
- **Not the cause.**
  - **Terminations.** Every clip-sample hold tips or collapses within 3 s on
    both cats (21/21 starts):
    - leo: `tipped` 0.39 and `collapsed` 0.47 of steps;
    - v07: 0.15 and 0.50.
  - **Stand pitch.** The keyframe hold neither tips nor collapses on either
    cat, and pays `posture` −0.002. The ~11° stand pitch does not end
    episodes.
  - **Stand pay.** Standing pays 4.2–4.4 per step on leo against 7.7–10.1
    on v07. Standing is no more attractive on leo; running was less so.
- **`hind_flat` (weight 6) pays 0 on leo in every scenario.** Its 0.588
  target (a 36° paw pitch) is v07's pinned paw, which leo does not have.
  On v07 the keyframe hold earns 5.3 from it. It is a dead term on leo's
  rigid foot. It is left in for now: O7 cuts a term only on a judged run.
- **`plantigrade` and `hind_flat` read 0 in the clip column.** A kinematic
  replay gives the hock-case contact sensors no force. This is the
  replay's limit, not the task's.

## The fix, and the screen on it

- `cadex params --set sprint_speed=2000 --set sprint_speed_w=20 --set
  plant_w=10 --set outside_hind_w=4` on top of the 62.5 ms rotary clip
  (`clip_lag.md`).
  - Revision `e46d3273`, project git `da3b5f4`.
  - The build kept revision 9's model (0 new bytes of tessellation), and
    the bundled model XML is byte-identical to g1-s1's. This is a task
    change, not a model change (O1).
- The bundle's 18 reward terms now equal heel5c-s1's in weight. Only
  `heel_pitch`'s expression differs, by leo's `2 * q_spine`. The clip
  table is the lag-0.15 one. `reward_terms.py` reads 32.38 per step for
  the clip, against heel5c's 32.44.
- **g2-heel5**:
  - cold, 50 iterations, 4096 envs, seed 0, `budget_s` 6,000;
  - launched 2026-10-20 21:49:52 through `queue_run.py` in its own
    scope;
  - 21.0 reward/step at iteration 0, against g1-s1's 10.3.
- The queued g2-lag15 (`clip_lag.md`, revision `823ecfc5`) was stopped
  before it registered: its task carried the same defaults.
