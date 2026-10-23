# orun13 O3: the leo v02 gallop clip reads tied, and which pair lags it can take

Verified against source: 2026-10-20. Frozen evidence (orun13, iteration 2).

## The bundled clip (g1-s1's, revision `a26dcc27`)

`docs/probes/orun13/p2_lag.py`'s clip block on `runs/g1-s1/train/gallop-task.json`:

- 0.70 m at 2.40 Hz (1.68 m/s), duty 0.2, 21 samples of 19.8 ms (a
  417 ms cycle).
- Touch-down phases LH 0, RH 0, RF 0.50, LF 0.55: the **hind pair lands
  together** (lag 0) and the fore pair 0.05 of a cycle apart, **21 ms**.
  The footfall order is undefined (LH and RH tie), the same clip that left
  orun12's every footfall tied (`docs/probes/orun12/p2-lag.md`).
- Each heel is down on 4 of its paw's 5 stance samples (0.8).
- Two flights a cycle, 99 and 119 ms. The spine bends 7° a joint each way
  (14.0° peak to peak a joint), `j_spine2` equal to `j_spine` on every
  sample.

So the clip cannot ask for O3's 40 ms on either pair.

## What the generator reaches on leo (`docs/probes/orun12/clip_lag.py`)

The engine's generator on g1-s1's exported model, at the bundle's
`heel_from` 0.2 and swing 40 mm. The bundle's own clip regenerates equal
first. Offsets are LH 0, RH *h*, RF 0.5, LF 0.5 + *f*:

| stride m | hind *h* | fore *f* | reachable | heels down / stance | airborne samples |
|---|---|---|---|---|---|
| 0.70 | 0 | 0.05 | yes (the bundle) | 4/5, 4/5 | 11/21 |
| 0.70 | 0 | 2/21, 3/21 | yes | 4/5, 4/5 | 10, 9/21 |
| 0.70 | 1/21 | 3/21 | no: RH misses its swing by 7.0 mm, `j_hip_r`, `j_knee_r` at a stop | | |
| 0.70 | 2/21 | 2/21 | no: RH's heel misses by 1.1 mm, `j_knee_r` at a stop | | |
| 0.70 | 3/21 | 3/21 | no: RH misses its swing by 4.5 mm, `j_knee_r`, `j_ankle_r` at a stop | | |
| 0.60–0.75 | 2/21–3/21 | 2/21–3/21 | no (the same misses) | | |
| 0.70 | −1/21 | −2/21 | yes | 4/5, 4/5 | 9/21 |
| 0.70 | −2/21 | −2/21, −3/21 | yes | 4/5, 4/5 | 8, 7/21 |
| 0.70 | −0.10 | −0.10, −0.15 | yes | 4/5, 4/5 | 8, 7/21 |
| 0.70 | −0.125 | −0.15 | yes | 4/5, 3/4 | 7/21 |
| 0.70 | −0.15 | −0.15 | yes | 4/5, 4/5 | 6/21 |
| 0.75 | −2/21 | −3/21 | yes | 4/5, 4/5 | 7/21 |

- A hind lag with **RH trailing** LH is refused from 1/21 up. A lag with
  **RH leading** (negative *h*: order RH LH LF RF, rotary) is reached at
  every lag tried up to 0.15.
- The hip and knee stops are mirror images (`j_knee_l` −60°..+50° about
  −y, `j_knee_r` −50°..+60° about +y). So the difference is not left
  against right. It is whether the trailing hind lands after the clip's
  phase 0, where the body's pitch and spine sine are anchored, or before
  it. The left-trailing order was not tried with LH moved off phase 0,
  because the API holds LH at 0.
- `assembly.gait` refuses a negative offset, so RH's is written
  `(1 - hind_lag) % 1` (the generator takes offsets mod 1; −0.15 and 0.85
  give the same clip).

## The clip chosen for g2-lag15 (revision `823ecfc5`)

- The script's offsets become `{"LH": 0, "RH": (1 - hind_lag) % 1, "RF":
  0.5, "LF": 0.5 - gallop_lag}`, with `hind_lag` and `gallop_lag` both
  0.15 (project git `314eb6b`, `cadex script --set leo-lag15.py`).
- Both lags are 0.15 of a cycle, **62.5 ms**, which leaves 22 ms of margin
  over O3's bar. A policy compresses the clip's lags (orun12: 21 ms asked,
  tied delivered), so the margin is the point. 0.10, at 41.7 ms, would leave
  almost none.
- The rebuilt bundle (`p2_lag.py` clip block):
  - LH 0, RH 0.85, LF 0.35, RF 0.50;
  - footfall order RH LH LF RF, **rotary**;
  - heels 4/5 on each leg;
  - two flights of 60 ms a cycle (down from 99/119 ms);
  - `j_spine2` = `j_spine` on every sample, 14.0° peak to peak.
- Its model XML is byte-identical to g1-s1's, and its 17 reward terms are
  the same. Only `reference` and its `tracking` table (`reset_qpos`,
  `reset_qvel`, `table`) differ. **The clip is the only change, and no
  model change is made (O1).**
- Assumption: a right-leading hind pair is acceptable. A real cat leads
  with either. Q1 still compares left and right, and the lead is a known
  asymmetry to check first: on feline v07 the leading hind was the one
  that laid its heel down.
