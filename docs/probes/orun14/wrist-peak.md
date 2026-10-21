# orun14 Q2/O1: the front wrist at peak is the carpus stop giving way

Verified against source: 2026-10-21. Follows `p1-flat-50.md` and `rod_gap.py`.
The critic asked for the wrist's peak share per stride as O1 evidence, so a
fix for Q2's open front rod loops is ready once P1 moves.

## The measurement

`wrist_peak.py` on each run's `train/cat_model-model.xml` (leo 4c9de98d;
d5192106 has the same model) and its judged evaluation, over every frame
from 1 s, on 10 seeds. "At peak" means |effort| ≥ 0.95 of the AK60-6
wrist drive's 9 N·m. Fore stance is read as the engine reads it
(`foot_series` on the paw's collision geoms).

| evaluation | leg | paw stance share | at peak: all / stance / swing | per stride (median) | strides with a peak frame | wrist ° at peak | cmd − pos ° at peak | rod gap > 2 mm frames (all at peak) | past the stop: frames / of peak frames / deepest ° |
|---|---|---|---|---|---|---|---|---|---|
| g1-free-50 | LF | 0.25 | 0.185 / 0.722 / 0.000 | 0.198 | 1.00 | −25.6 | +26.6 | 23 (1.00) | 0.200 / 0.83 / 26.5 |
| g1-free-50 | RF | 0.22 | 0.186 / 0.855 / 0.000 | 0.190 | 1.00 | +24.4 | −49.2 | 49 (1.00) | 0.149 / 0.78 / 24.0 |
| h1-meta-25 | LF | 0.42 | 0.121 / 0.282 / 0.000 | 0.125 | 0.88 | −16.5 | +22.5 | 0 | 0.080 / 0.55 / 14.6 |
| h1-meta-25 | RF | 0.42 | 0.025 / 0.068 / 0.000 | 0.000 | 0.24 | +4.5 | −15.7 | 1 (1.00) | 0.006 / 0.20 / 5.5 |
| p1-flat-25 | LF | 0.48 | 0.018 / 0.040 / 0.000 | 0.000 | 0.13 | −10.8 | +19.7 | 0 | 0.006 / 0.21 / 11.9 |
| p1-flat-25 | RF | 0.36 | 0.003 / 0.009 / 0.000 | 0.000 | 0.07 | −6.2 | −7.0 | 0 | 0.000 / 0.00 / 0.0 |
| **p1-flat-50** | LF | 0.25 | **0.207 / 0.839 / 0.000** | 0.200 | 1.00 | −27.3 | +43.3 | 39 (1.00) | **0.217 / 0.91 / 26.1** |
| **p1-flat-50** | RF | 0.17 | **0.119 / 0.696 / 0.000** | 0.127 | 0.98 | +20.5 | −25.6 | 25 (1.00) | **0.099 / 0.75 / 14.8** |

The wrist joint (`j_wrist_l`, the crank on the forearm) runs −15…+40°;
`j_wrist_r` mirrors it at −40…+15. On p1-flat-50 seed 1001 the crank angle
from the placements (crank relative to forearm) equals the trace's joint
position frame for frame, down to −38.3°. The overrun is in the motion, not
in the reading.

## What it says

- **The drive is at peak only in fore stance, never in swing.** It is at
  peak on 84% / 70% of p1-flat-50's LF / RF stance frames, and on every
  stride but one. At 1.46 m/s the fore stance is short: shares 0.25 /
  0.17, against 0.48 / 0.36 at p1-flat-25's 0.41 m/s. So the load per
  stance frame rises with speed, and the peak share rises with it.
- **It is the load, not the clip.** At peak the drive pushes towards its
  command (LF effort +, RF −), and the paw sits 26–43° behind it. The clip's
  carpus asks −1…−7° in LF stance (+3…+7° RF), inside the stop. The paw's
  stance load drives the crank and paw through the −15° stop by up to
  26°. The 9 N·m drive then holds the body.
- **The stop is soft.** `j_wrist_*` and `j_carpus_*` take MuJoCo's default
  `solreflimit` (0.02 s). leo's script gives them only bushing damping
  and friction. ADR-724 measured the same default letting a light pin fold
  25° past at 2 N·m. The hind paw pins already carry
  `limit_time_constant_s=0.004`. Design note D27 in leo's script says this
  stop is meant to be load-bearing: "the paw hyperextends against a stop
  15° past standing, as a cat's carpus locks".
- **The rod loop opens only then.** Every front-rod frame over O9's 2 mm,
  on every run, is a peak frame. The loop is the third constraint in a
  fight between a yielding stop and a saturated drive.

## The model change this argues for (O1, written before the build)

- **The change:** in leo's script, add `limit_time_constant_s=0.004` to the
  `joint_dynamics` of `j_carpus_l` and `j_carpus_r`. That is the hind pins'
  value, two solver steps (ADR-724). If the carpus alone does not hold, add
  it to `j_wrist_*` too. No geometry, mass or drive changes.
- **The measurement:** the front stop yields up to 26° (0.22 / 0.10 of all
  frames past it). With the drive at peak on 70–84% of stance frames, the
  front rod loops open to 3.80 / 2.89 mm, against O9's 2 mm.
- **The expected effect:**
  - the stop holds the carpus lock within about 2°;
  - the wrist drive comes off peak in stance;
  - the front rod gap stays under 2 mm (Q2);
  - the worst drive's peak margin rises above 0.00 (O6).
- **The risk:** a stiff stop is a hard surface the paw lands on. The fore
  touchdown impulse and the carpus rate need checking after the build.
- **The test:**
  - rebuild with no new clearance pair (`clearance-baseline.md`);
  - re-judge the policy that P1 next keeps on the new model, with
    `wrist_peak.py` and `rod_gap.py`;
  - keep the change only if the stop overrun and the > 2 mm frames fall.
- **When:** not now. The question policy puts P1 first, and the GPU is on
  s1-sole. This waits for the screen that next moves P1, so one rebuild
  carries the clip and the stop together.
