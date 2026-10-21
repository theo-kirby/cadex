# orun14 O1: leo-v03.1, the hind paw pin's toes-up stop 60° → 30° (refused by the clip)

Verified against source: 2026-10-21. Written before the build, as O1 asks.
Follows `ps-sole-50.md` ("A measurement for O1, not acted on here").

## The change

- **One literal:** `TOE_UP` 60.0 → 30.0 in leo's `script.py` (line 1044).
  The flat stop (`FLAT_STOP`, 0°), the seat (sole flat at hock −60), the
  damping (3.0 N·mm·s/deg) and friction (5 N·mm) are unchanged. No part's
  geometry changes; only `j_pawpin_hl` / `_hr`'s range, −30..0 and 0..30.
- **The script:** `~/orun14-pc.py`, `orun14-ps.py` with that one line, so
  ps-sole's task (pin encoders observed, `paw_flat` w10, `heel_pitch` w10,
  19 terms, the `flat_feet="sole"` clip) on the new model.
- **Tag:** `leo-v03.1` in the project's git, after the build's verdicts.

## The measurement

`pin_cap.py` (new) reads each evaluation's stance frames (paw down, after
the first second) with `paw_floor.py`'s series.

| evaluation | leg | stance frames | pin p50 / p90 ° | stance on pin > 30° | metatarsus ° of floor p50 | U now | U, pin clamped at 30° | R frames on pin > 30° |
|---|---|---|---|---|---|---|---|---|
| ps-sole-50 | LH | 995 | +45.2 / +61.4 | 0.83 | −4.3 | 0.85 | 0.71 | 0.57 of 136 |
| ps-sole-50 | RH | 976 | +59.2 / +63.3 | 0.97 | −16.9 | 0.79 | 0.53 | 0.85 of 140 |
| g1x-free-75 | LH | 1190 | +53.3 / +62.9 | 0.88 | −4.2 | 0.84 | 0.68 | 0.64 of 170 |
| g1x-free-75 | RH | 894 | +39.9 / +59.8 | 0.74 | −9.9 | 0.76 | 0.65 | 0.42 of 186 |
| s1-sole-50 | LH | 1035 | +38.1 / +58.0 | 0.63 | −12.3 | 0.46 | 0.41 | 0.51 of 511 |
| s1-sole-50 | RH | 885 | +52.4 / +62.5 | 0.94 | −19.4 | 0.80 | 0.49 | 0.80 of 155 |
| p1-flat-50 | LH | 2120 | +10.0 / +20.8 | 0.01 | −5.9 | 0.18 | 0.18 | 0.00 of 1236 |
| p1-flat-50 | RH | 1494 | +8.6 / +25.3 | 0.07 | −3.5 | 0.20 | 0.19 | 0.01 of 571 |

- **The fold is the pin, on its stop.** Every policy that ran at 2.2 m/s
  or more stands with the pin past 30° on 0.63–0.97 of stance, its p90 at
  58–63° (the stop at 60, a few degrees soft). The metatarsus itself is
  near level or toes-down of it (−4 to −19°): the paw's 37° toes-up of the
  floor is the pin's fold, not a raised metatarsus.
- **The one slow policy that kept the paw flat** (p1-flat-50, 1.46 m/s, U
  0.18 / 0.20) used under 30° on 0.93–0.99 of stance, and none of its roll
  (`R`) frames needed more.

The other stops, for the record (U if the metatarsus held its pitch and the
pin were clamped):

| stop | ps-sole-50 U LH / RH | g1x-free-75 U LH / RH | ps-sole-50 R frames over the stop LH / RH |
|---|---|---|---|
| 60 (now) | 0.85 / 0.79 | 0.84 / 0.76 | — |
| 40 | 0.77 / 0.66 | 0.76 / 0.72 | 0.36 / 0.79 |
| 30 | 0.71 / 0.53 | 0.68 / 0.65 | 0.57 / 0.85 |
| 20 | 0.60 / 0.37 | 0.60 / 0.46 | 0.76 / 0.94 |
| 15 | 0.51 / 0.26 | 0.52 / 0.30 | 0.85 / 0.96 |

## The expected effect, and what it is not

- **Expected:** with the stop at 30°, the paw can fold at most 30° of the
  metatarsus. At the metatarsus pitches measured, that is 13–26° toes-up
  of the floor where it is now 37°. The folded stance stops being one
  rigid foot on a 60° stop, and `paw_flat` (w10) pays more for a flat paw
  against a fold that can no longer reach its old pitch.
- **Not a pass by itself.** Held at the same metatarsus pitch, the clamp
  alone leaves U at 0.71 / 0.53 on ps-sole-50, far over the keep rule's
  0.2. Even a 15° stop leaves 0.51 / 0.26. The change works only if the
  retrained policy lowers the paw rather than standing on the new stop.
  The screen answers that.
- **Why 30 and not lower.** O2a asks a digitigrade stance when slow: heel
  up, paw flat, the pin toes-up of the metatarsus. A 30° stop keeps half
  the roll travel the owner gave. 20° or 15° buys 0.1–0.2 of static U and
  takes away 0.76–0.96 of the fast policies' roll frames, and most of the
  digitigrade posture SG needs.
- **The cost to watch:** the roll at push-off. ps-sole-50's `R` frames
  used more than 30° on 0.57 / 0.85 of them, so the heel's lift at toe-off
  is cut. If heel share at toe-off (`hock_at_toeoff`) falls, or the
  screen's speed falls more than ps-sole's spread at the same checkpoint,
  that is the price.

## The build: refused by the gallop clip

- **Queued** at 11:36:40 as `orun13/queue_run.py ... pc-sole 4800 50
  --envs 4096 --after hw-sole --build ~/orun14-pc.py`, so it built while
  hw-sole trained.
- **Refused** by `cadex script --set` (exit 3): "Task output 'gallop'
  could not be built: ... its gait reference cannot be generated: leg RH
  cannot put its heel down at 0.143 of the stride: it misses by 5.7 mm
  with j_pawpin_r at a stop (stride 700 mm, swing 40 mm)". The project's
  accepted revision stays `9820961f` (hw-sole's); nothing was tagged, and
  `leo-v03.1` is not taken.
- **Why: the clip itself folds the pin past 30°, in early swing.** The
  bundled sole clip (ps-sole's `gallop-task.json`, 21 samples), pin
  toes-up of the metatarsus per sample:

| leg | in stance (contact samples) | the samples after lift-off | max |
|---|---|---|---|
| LH (stance 0–4) | 1.6–3.8° | 25.2, 42.3, 57.7° (5–7) | 57.7° |
| RH (stance 18–20, 0–1) | 3.8° | 24.6, 41.2, 56.0° (2–4) | 56.0° |

  In stance the clip holds the paw within 4° of the flat stop. From
  toe-off it keeps the paw level as the metatarsus rises, so the
  reference walks the pin to within 2–4° of the 60° stop in the first
  three swing samples. A 30° stop leaves no reachable pose there, and the
  generator refuses the clip.
- **What it means.** The policies' fold sits on the same 56–60° the clip
  reaches at every lift-off. Tracking pays for that angle in swing, and
  the policies carry it into stance. A shorter stop is not buildable until
  the reference keeps its swing pin under the stop: a generator change
  (ADR from ADR-784) that lets the paw trail toes-down in swing, or a
  clip whose swing does not hold the paw level. That is a policy-side
  lever (O1: the policy first), and it could also answer the fold without
  any model change.

## For the owner (R1)

The charter names the free, unsprung paw pin as the owner's choice. This
keeps the pin free and unsprung and changes only its toes-up travel, 60° →
30°. The numbers: five screens at 2.2 m/s or more stood with the pin on its
60° stop through most of stance (above), and that fold is O2's fault.
