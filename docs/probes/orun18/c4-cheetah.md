# orun18 C4: AcinoSet's cheetah gallop strides, and their noise

Verified against source: 2026-10-23. Data: AcinoSet (Joska et al., ICRA 2021,
arXiv 2103.13282), its FTE 3D trajectories, under the owner's D5a terms
(`SOURCES.md`). Everything fetched or derived sits in `~/mocap/acinoset/`, never
in the repository. The probe is `acino_strides.py`.

## What was fetched

- 90 `fte_pw/fte.pickle` files and their `reconstruction_params.json` (180
  files, 21 MB), found by walking the Dropbox folder the README links. Videos,
  2D labels and DLC outputs were skipped.
- Each file's size matched the listing. `~/mocap/acinoset/SHA256SUMS` (sha256
  `ad04186673454fbd…`, 182 lines with the two metadata pickles) holds every file's
  hash, and `LISTING.txt` (`19f29767f35da314…`) the folder as it stood.
- Each pickle holds the FTE's 20 points (eyes, nose, neck base, spine, tail
  base, mid and tip; per leg the girdle point, knee or elbow and the distal
  "ankle") in metres with z up, plus its 25-number state `x`, `dx` and `ddx`.
- **The model has no paws.** Its distal point is the wrist or hock.

**Frame rate, read from each file:** `dx / diff(x)` gives 90.0 for the 2017
takes and 120.0 for the 2019 takes. The DLC metadata says 90 and 119.88
(`~/mocap/acinoset/meta/`).

## The strides (12 Hz filter; `strides-12.json`, sha256 `c327844ac2f9d882…`)

The probe found 66 left-hind-to-left-hind strides across the 90 takes. **30 are
steady**: the heading turns under 10° and the speed changes under 10% between
the stride's halves, with each foot landing once.

- Speeds run from 5.20 to 14.17 m/s.
- **20 are rotary** gallops: every steady stride from 8.9 m/s up except
  `2019_02_27/ebony/run` at 13.7 m/s, plus one at 7.05 m/s.
- The rotary order is LH, LF, RF, RH (read cyclically: RH lands at phase
  0.84–0.92, just before LH, so the hind pair goes R then L and the fore pair L
  then R).
- **10 are transverse**, and they are the slow ones: all 7 from 5.20 to
  6.74 m/s, then 7.86, 8.50 and the 13.7 m/s exception. Two orders appear:
  - LH, RH, LF, RF (RH at 0.07–0.18);
  - LH, RF, LF, RH (RF at 0.05–0.10, on `cetane` and `zorro`).

The four slowest steady strides are the ones that reach leo's range:

| take | frames | v (m/s) | period (s) | order | gait | flight | hip (m) | Fr | leo at equal Fr (m/s) |
|---|---|---|---|---|---|---|---|---|---|
| 2017_12_12/top/cetane/run1_2 | 146–188 | 5.20 | 0.467 | LH RF LF RH | transverse | 0.43 | 0.49 | 5.7 | 4.69 |
| 2017_09_02/top/phantom/run1_2 | 71–109 | 5.84 | 0.422 | LH LF RH RF | transverse | 0.50 | 0.40 | 8.8 | 5.85 |
| 2017_12_12/top/cetane/run1_2 | 106–146 | 5.87 | 0.444 | LH RF LF RH | transverse | 0.43 | 0.49 | 7.2 | 5.29 |
| 2017_09_03/bottom/zorro/run2_1 | 32–73 | 6.08 | 0.456 | LH RF LF RH | transverse | 0.54 | 0.47 | 8.0 | 5.56 |

The full table of 30 strides is the probe's output.

- **Faster strides.** The next fastest are 6.3–6.7 m/s (leo 6.1–6.3 m/s). The
  rotary strides start at 7.05 m/s (leo 6.3). They lie above leo's 5 m/s command
  range.
- **The leo speeds are upper bounds.**
  - "hip" is the hind hip's height over the hind distal points' floor. That
    point is the hock, which stands above the planted paw by the metatarsus. The
    model does not carry the metatarsus, and this probe does not measure it.
  - So the cheetah's true hip height is greater. Its Froude number, and the
    leo-equivalent speed (v·√(0.396 / hip)), are smaller than shown.
- **Footfalls come from the hock and wrist, not the paw.** A point counts as
  down while it is within 40 mm of its floor and moving at under 0.35 of the
  trunk's speed. Both stop for only part of the paw's stance, so:
  - duty reads short (median 0.15 / 0.16 fore, 0.12 / 0.12 hind);
  - flight reads long (0.41–0.70).

  The touchdown order is what is claimed, not stance length. C4's retarget must
  supply the paw below the hock and find stance from it.

## Noise, and what the filter does

The FTE is already a smoothed estimate: a fixed-length kinematic model fitted
with a motion prior. The probe ran the same scan at three cutoffs of a
zero-phase 4th-order Butterworth low-pass, with medians over the 90 takes:

| cutoff | removed, head / trunk / tail / knees / distal (mm RMS) | raw acceleration power above cutoff | strides found / steady |
|---|---|---|---|
| 16 Hz | 0.1 / 0.3 / 1.2 / 1.3 / 1.9 | 0.03 | 71 / 33 |
| **12 Hz** | **0.3 / 0.9 / 3.6 / 4.0 / 5.5** | **0.11** | **66 / 30** |
| 8 Hz | 1.4 / 3.5 / 11.8 / 13.8 / 17.5 | 0.35 | 44 / 18 |

- **The noise is small.** Counting everything above 12 Hz as noise, it is at
  most 5.5 mm RMS at the distal points and 0.9 mm on the trunk. Above 16 Hz it is
  under 2 mm.
- **12 Hz removes it without cutting motion.**
  - 12 and 16 Hz share 22 steady strides, with the same frames and footfall
    order on all 22.
  - At 8 Hz the filter starts to remove the motion itself: strides found drop
    from 66 to 44, steady ones from 30 to 18, and the residual triples.
  - 12 Hz is about four harmonics of a ~3 Hz stride (periods 0.24–0.49 s).
- **The hock and wrist move about 43 mm (median) over a detected stance.** That
  is real motion, the joint rolling over the planted paw, not noise. The filter
  leaves it unchanged (47 mm filtered, ~2 m/s RMS either way). So planted-foot
  slip cannot be read off this model's points. C4's retarget measures slip on the
  paw it places.

## What this means for C4's retarget

- The cheetah's slowest steady gallops are **transverse**. Its rotary gallop
  starts above 7 m/s, i.e. above 6 m/s on leo even before the hip height bias.
  The dog clip in C3 is rotary at 2.8–4.2 m/s.
- So a cheetah reference in leo's range is a transverse gallop near leo's top
  command (about 4.7–5.9 m/s at the bound, less once the hip height is
  corrected). It is not a slower one: this capture has no cheetah stride under
  5.2 m/s that reads as steady.
- The spine is in the data (neck base, spine and tail base points, and the
  state's torso angles), for `j_spine` / `j_spine_yaw`.
- Two things are still open for the retarget:
  - the paw below the hock and wrist;
  - the true hip height.
