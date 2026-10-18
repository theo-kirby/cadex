# orun10 S3: the outside-hind stride, measured on s1-g4 and set up as s3-h1

Verified against source: 2026-10-18. Frozen evidence (orun10, iteration 13).

## The measurement (O8 before the reward edit)

O6 asks for a stride where the hind feet swing outside the forefeet and land
ahead of them. Before a reward was written, the fastest judged policy,
s1-g4's final (4.498 m/s, `s1-g4-judged.md`), was measured for it. The probe
is `~/orun10-progress/s10/hind_offset.py`, outside the repo. It reuses the
engine's own foot geometry (`CadexDynamics.evaluation_rig`,
`CadexEvaluation.foot_series` and `gait`) on the ten retained seed traces of
`orun10-cat/evaluations/s1-g4-final`. Positions are in the starting heading
frame, after the 1 s settle. "Outside" is positive when the hind foot is
farther from the midline than the fore foot on the same side.

| s1-g4 final, 10 seeds | value (median; p10, p90) |
|---|---|
| hind half-track minus fore half-track, every settled frame | **−15 mm** (−92, +67); positive on 45% of frames |
| hind outside the fore's print as the hind passes it | **+8 mm** (−11, +83); 657 passes |
| hind outside the fore's last print at hind touchdown | −5 mm |
| hind touchdown ahead of the same-side fore's last print | **+148 mm** (+116, +1085) |
| hind touchdown against where the fore foot is then | −433 mm (the fore has already left) |

The fastest gallop already oversteps the fore print: the hind lands 148 mm
ahead of it (430–470 mm on six seeds, 140–150 mm on four). But it does so
**in line**, not outside: the hind track runs within about 10 mm of the
fore's. The model allows more. The design stance has the forepaws at
y = ±116 mm and the hind paws at ±106 mm. The hind abduction `j_hhaa` acts
over ±10°, about 430 mm above the paw, so it reaches about 75 mm of side
travel. The fore `j_fhaa` acts over ±8°.

## The term, and s3-h1

The stride is tried as a reward term on the gallop task. The reference is a
task key, and a warm start may not move it (RECIPE §3.5). orun10-cat's script
gains `outside_hind_w` (default 0, which adds no term) and `outside_hind_mm`
(default 60). The term `outside_hind` pays the hind half-track's excess over
the fore's, in world y:
`d = ((phl_y − phr_y) − (pfl_y − pfr_y)) / 2`, paid as `min(max(d, 0), 60) / 60`.
The heading term holds the course to +x, so world y is the lateral.

The parameters were set back to s1-g4's clip (2.4 Hz, 700 mm, duty 0.25),
with `outside_hind_w` = 4 (orun10-cat revision `ccf3d180`, project commit
`83c1f0b`). The first rebuild (`facd48f8`) differed from s1-g4's bundle in
the reference's label as well as the reward: the duty suffix was added after
s1-g4. The trainer refuses that, so at duty 0.25 the label is now s1-g4's.
The rebuilt `gallop` bundle differs from s1-g4's in `reward` alone, with 13
terms against 12. The trainer's own `check_policy_fits` accepts s1-g4's final
policy onto it, moving `['reward']` only
(`~/orun10-progress/s10/warm_check.py`).

On s1-g4 final's traces the term pays 0.326 a step, or 1.30 at weight 4. Full
pay is 4.0, against the speed term's 9.0 at 4.5 m/s. The weight is set so
that being outside is worth a little speed. It cannot buy a stop: standing
still loses 9 a step to gain at most 2.7.

s3-h1 is warm from s1-g4's final, at lr 3e-5, with a 10-iteration critic
warm-up, for 100 iterations, with a checkpoint every 25. It is registered
through `cadex_cli.loop` with `retain_training_view` and launched in its own
`systemd-run --user --scope -p MemoryMax=30G` as soon as j1-s2 frees the GPU
(`launch_h1_when_free.sh`). Each checkpoint is judged on `gallop_spec` for
speed, and with `hind_offset.py` for the lateral offset at the pass and where
the hind lands, against the s1-g4 row above.
