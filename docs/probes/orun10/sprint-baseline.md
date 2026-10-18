# orun10 S1: the flat sprint spec, and the baseline judged on it

Verified against source: 2026-10-17. Frozen evidence (orun10, iteration 1).

## The project

`~/cadex-projects/orun10-cat` is a copy of `orun8-cat` at project commit
`24bc528` (the cat `0f036864`, model `f321f89c`), without its 29 GB of
evaluations. The sprint spec landed as revision `73028f72` (project commit
`a98dd51`); the model was kept unchanged ("0 new bytes of tessellation").

## The spec: `sprint` (ADR-771)

A `c1_task` on the C1 task, so a C1 policy is judged on it. The success
alone is new:

- the speed command is held at **5000 mm/s** for the whole 10 s episode, the
  yaw rate at 0, and the cmd mode is on (`nav` −1);
- `completes` ≥ 1, `no_fall` (`falls`) ≤ 0, `upright` (`max_tilt_deg`) ≤ 30,
  `straight` (`max_heading_deg`) ≤ 25;
- `top_speed`: `max_forward_speed_2s_mm_s` ≥ 5000, the best 2 s mean along
  the starting heading;
- the 10 frozen seeds 1001–1010.

O3 is honoured by the model and the report: every drive is clamped at its
peak in the model, and RMS over rated is reported, not bounded. S2's
numbers come from the same episodes: `flight_stride_share`,
`flight_s_median`, `stride_length_mm_median`, `stride_hz_median`, and the
`flight` detail's footfall orders.

## The judge

`~/orun10-progress/s1/judge_sprint.py` (outside the repo) splices the
`sprint` success into the bundle a policy trained on. It plays the trained
model's own bodies and writes only under `orun10-cat/evaluations`; earlier
projects are only read. Goals the trained task lacks are dropped: orun7's
bound task reads no command, so it runs its own gait. So does its
appendage, because orun7's tail was shorter and no sprint predicate reads
it. `--cmd 3500` holds a lower command for a policy trained up to 3.5 m/s.
`table.py` prints the tables below.

## Results (10 seeds each, CPU)

| policy (model) | cmd | pass | top 2 s speed, m/s: min / median / max | straight | flight strides | flight per stride | stride length × freq | worst RMS / rated | peak ratio |
|---|---|---|---|---|---|---|---|---|---|
| orun7 f1-g3 `run.best` (`d0401683`) | — | 0/10 | 4.203 / **4.220** / 4.228 | 10/10 (2.4°) | 1.00 | 60 ms | 1.753 m × 2.381 Hz | 1.92 (j_spine) | 1.000 |
| orun7 f1-g3 final, it 299 | — | 0/10 | 4.214 / 4.222 / **4.236** | 10/10 | 1.00 | 60 ms | 1.760 m × 2.381 Hz | 1.92 (j_spine) | 1.000 |
| orun7 f1-g2 `run.best` | — | 0/10 | 4.245 / **4.253** / 4.280 | 10/10 | 1.00 | 60 ms | 1.770 m × 2.381 Hz | 1.85 (j_spine) | 1.000 |
| orun9 c1-c6 @100 (`f321f89c`, this cat) | 3500 | 0/10 | 2.682 / **2.744** / 2.753 | 5/10 (23.9°) | 1.00 | 60 ms | 0.711 m × 3.571 Hz | 1.19 (j_spine_yaw) | 1.000 |
| orun9 c1-c6 @100 | 5000 | 0/10 | 2.000 / 2.175 / 2.283 | 0/10 (47.3°) | 0.925–1.00 | 40 ms | 0.426 m × 4.545 Hz | 1.33 (j_wrist_l) | 1.000 |

The only failing predicates were `top_speed` (every row) and `straight`
(the c1-c6 rows). No seed fell or tipped.

**Footfall order**, counted over every stride, with the left fore's landing
as the clock:

- orun7 f1-g2 and f1-g3: fl → hl → hr → fr on all 208–209 strides.
- c1-c6 at 3.5 m/s: fl → hr → fr → hl on 265 of 309 strides, a trot-like
  diagonal sequence with a flight phase.

**Drives at peak** on every seed:

- f1-g3 `run.best`: both elbows and wrists, both hocks, the right shoulder
  and j_spine.
- c1-c6 at 3.5 m/s: both wrists, and the tail servos tail2 and tail4. The
  left hock reached peak on 6 of 10 seeds.

## Reading

- **The baseline on this cat is 2.74 m/s.** A command past the 3.5 m/s that
  c1-c6 trained on does not help. At 5000 it runs slower (2.17 m/s) on a
  shorter, quicker stride (0.43 m at 4.5 Hz, the trot clock's cadence), and
  drifts off line (47°). The cmd input is out of its range there.
- **orun7's gallop reached 4.22–4.25 m/s on its earlier model.** Its stride
  is **2.5× longer** than c1-c6's (1.75 m against 0.71 m), at **two-thirds of
  the frequency** (2.38 Hz, the reference's 2.4 Hz). Both have 60 ms of
  flight every stride.
- **The gap is stride length.** The trot clock's cadence rises with the
  command, and that buys frequency, not reach. The gallop reference held
  2.4 Hz and let the policy lengthen its stride. This agrees with orun9's
  cadence finding.
- **Every policy touched peak on some drive.** At ~4.2 m/s that is the fore
  wrists and elbows, the hocks and the spine; the worst RMS is the spine's,
  at 1.9× rated. So a faster gallop on this cat will meet its drives' peak
  first at the wrists and hocks. That is O3's limit, measured per drive in
  the next O8 step.
- **Next**, per the ladder: O8's measurement on f1-g3 and c1-c6, then a
  gallop reference on this cat's legs, with a 2.4 Hz clock and a long stride.
