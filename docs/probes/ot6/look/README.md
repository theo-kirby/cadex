# The dark look beside the reference (D3, ADR-331)

Verified against source: 2026-09-13. [Cadex-new]

The review environment is dark only: `cli/cadex_cli/review_static/environment.js`
exports one `PALETTE` and no theme setter, and the viewer's style name is
`cadex-prototype-dark-v1`. This directory is the charter's D3 evidence for that
change (ADR-328): reference frames beside Cadex viewport screenshots and decoded
video frames, at equivalent framing, with the written assessment below. The
second half of D3 — the follow camera at a declared framing fraction and the
timer overlay (ADR-332) — is the last section, with its own frames and receipt.

## What was compared, and how

```bash
PYTHONPATH=cli pixi run python docs/probes/ot6/look/compare.py \
  "http://<private-address>:8765/" "$HOME/cadex-projects/ot5-lark-copy85" \
  "$HOME/neural-whoop" lark98-final "$HOME/cadex-projects/ot6-look" docs/probes/ot6/look
```

The persistent operator dashboard (port 8765, `ot5-lark-copy85`) was not
started or stopped. `lark98-final` — an eight-second recorded rollout of the
ot5 biped at revision `6f826037…` — was re-rendered first with
`python -m cadex_cli.video`, so its newest video is in the dark look
(`rollout-7bde92c0…webm`, 81 frames, 13.3 s to render) and its light
recording stays retained beneath it. The probe then:

1. decoded frames 0 and 4 s of that video, and one frame each of the shipped
   reference clips `orbit` (4 s), `swing` (2 s) and `flip` (2 s) from the
   read-only `neural-whoop` checkout at `31caeb28…`;
2. drew the persistent page's viewport at 512 × 512: the default fit, the
   video's own pose and camera, a close (0.7×) and a wide (3×) framing, the
   underside, and a **framed** shot at the reference's declared framing
   fraction — the subject's 236 mm height at 0.22 of the frame height, which
   puts the camera at 1 031 mm — then orbited by real pointer input (drag,
   wheel in, wheel out past 2×), reading the stage the environment derived at
   each camera and the model's pixel count;
3. drew the capture page at the same pose and camera and compared the bytes;
4. drew the **reference's own unmodified** `scene.js` / `environment.js`,
   dark theme, over the same Lark solids at the same four cameras, in an
   in-memory harness that writes nothing into the sibling checkout;
5. assembled the side-by-side and measured mean sRGB luminance of every frame
   (whole, top-left sky patch, bottom-right floor patch).

Full-resolution images and the full receipt stay in the operator's
`cadex-projects/ot6-look/`; `look.json` here is the compact receipt (digests,
cameras, stage numbers, luminances, pixel counts) and the PNGs are 256-colour
copies under the 200 KB cap — the composite at two-thirds scale.

## The frames

[side-by-side.png](side-by-side.png), four rows of four:

| row | reference | reference renderer, Lark, dark | Cadex viewport | Cadex video / orbit |
|---|---|---|---|---|
| 1 | `orbit` clip at 4 s | same pose and camera as the video | [same pose](persistent-same-pose.png) | [decoded frame 0](video-frame0.png) |
| 2 | `swing` clip at 2 s | framed at 0.22 | [framed at 0.22](persistent-framed.png) | decoded frame at 4 s |
| 3 | `flip` clip at 2 s | close, 0.7× | close, 0.7× | after a pointer drag |
| 4 | Cadex default fit | wide, 3× | [wide, 3×](persistent-wide.png) | [after wheeling out](persistent-orbit-far.png) |

Committed singly: [reference-shipped-orbit-4s.png](reference-shipped-orbit-4s.png),
[reference-dark-lark.png](reference-dark-lark.png), and the four linked above.

## Measured

| | viewport, same pose | capture, same pose | video frame 0 | reference renderer, same pose |
|---|---|---|---|---|
| bytes | `25455b63…` | **identical** | — | — |
| mean RGB error vs viewport | — | 0 | **1.10** / 255 | — |
| luminance all / sky / floor | 64.0 / 30.3 / 32.5 | same | 63.2 / 29.7 / 31.8 | **64.1 / 30.3 / 32.5** |

| framing | camera distance | fog near / far (m) | floor (m) | grid pitch / minor (m) | model pixels |
|---|---|---|---|---|---|
| close 0.7× | 938 mm | 1.41 / 13.1 | 52.5 | 1 / 0.2 | 57 589 |
| framed 0.22 | 1 031 mm | 1.55 / 14.4 | 57.7 | 1 / 0.5 | 72 421 |
| video / same pose | 1 340 mm | 2.01 / 18.8 | 75.0 | 1 / 0.5 | 49 679 (after drag) |
| wide 3× | 4 019 mm | 6.03 / 56.3 | 225.1 | 1 / none | 1 253 |
| wheeled out | > 2 680 mm | 7.08 / 66.1 | 264.5 | 1 / none | 3 924 |

At every camera reached the floor runs to four times the fog's far distance,
which the probe asserts; the reference clips' sky patch reads 18.2 and their
floor patch 35–46, ours 17–44 and 32–43 across the same range of framings.
The page's `--bg` is `#141414` and the body computes to `rgb(20, 20, 20)`:
the viewport's sky is the page's background.

## Assessment

Viewed the composite and the full-size frames named above.

| Property | Observed |
|---|---|
| **Floor / grid** | The same near-black checker (`#1c1c1c` / `#232323`) with `#3a3a3a` major lines every metre, the baked **1 METER** and **PROTOTYPE** labels reading the right way up, and a minor mesh chosen from the framing: 0.5 m at the video's standoff, 0.2 m close in, none at the wide and wheeled-out framings — the reference's `chooseGridPitch` behaviour, since the module is the reference's. The reference clips show the same tile, labels and subdivision at their own (closer) framings. The cyan slab under Lark is the ot5 design's own ground geometry, kept as history; the ot6 mechanisms carry no slab, so the mat will meet the feet directly. |
| **Horizon / fog** | Both fade the floor into the `#141414` background well inside the plane, and the sky gradient darkens to `#070707` overhead. No stage edge, seam or wall at the wide framing, after wheeling out past 2×, or under a pointer drag; the underside view (front-sided floor) shows only the slab's dark underside on black, the deliberate CAD-inspection exception. |
| **Palette** | Identical between viewport, capture and the reference renderer over the same solids (luminance equal to 0.1); the decoded video is within 1.1 of 255 of the viewport, the VP9 loss. The shipped clips are a shade darker overall (41–42 vs 64) because their subject is a small white drone on a mostly empty mat, ours a colourful biped on a bright slab that fills a third of the frame — a subject difference, not a palette one; sky patches agree (18 vs 17–30, ours brighter only where the slab reaches the corner). |
| **Lighting / shadows** | The reference's rig: hemisphere 1.6 over `#2a2a2a`, key 2.7 from `KEY_DIR`, opposite fill 1.0, ACES at 0.95. A grounded contact shadow lies on the slab beside the feet at the close, framed and same-pose framings; at 3× and after wheeling out it is too small to resolve at 512 px, which is a limit of the framing, not a lost shadow — the shadow camera is refitted to the model bounds on every fit. The shipped clips show a *separated* shadow because their drone flies; a standing biped's is a contact shadow by nature. |
| **Materials** | Rough (0.72) low-metalness plastics under the same tone mapping. The reference's drone is a white chassis from a GLB; Cadex's parts keep the eight-colour identity palette, which the design spec keeps on purpose because it names parts in the component list and the videos. |
| **Framing** | The framed shot places the biped at 0.22 of the frame height, the reference's default `droneFrac`, and reads like the `swing` frame beside it: subject small and central, mat filling the lower half, horizon a third down. Since ADR-332 the *video* is framed the same way in every frame: the subject's standing height fills 0.22 of the frame height at one standoff for the whole clip (analytic 0.2198–0.2201 across `lark98-final`), so a rollout that travels no longer shrinks its subject — the section below measures it. The viewer's *default* fit stays tighter (radius / sin 27.5° × 1.15), because that is an inspection fit, not a shot. |
| **Camera** | Same perspective, 55° vertical, same orbit convention; the viewport and capture agree to the byte at the same camera. **Matched since ADR-332:** the reference's follow rig — constant offset from a Hann-smoothed subject track, fixed orientation, declared framing fraction 0.22, subject resting 0.06 below centre, soft drift limit 0.26 — and its **timer overlay**, the `0.00 s` caption pill bottom-left, both computed and drawn by the one scene module the viewport and the capture share. |
| **Antialiasing** | MSAA on both; the decoded frame's only loss is the codec's. |

**What this first unit left owed** — a tracking camera in the capture at a
declared framing fraction, and the timer overlay on the video, each with its
own decoded frames — is the section below. A physical phone or a second
machine was not used; this is headless Chromium 152 on the operator's machine.

## The follow camera and the timer (ADR-332)

```bash
PYTHONPATH=cli pixi run python docs/probes/ot6/look/follow.py \
  "http://<private-address>:8765/" "$HOME/cadex-projects/ot5-lark-copy85" \
  "$HOME/neural-whoop" lark98-final "$HOME/cadex-projects/ot6-look/follow" docs/probes/ot6/look
```

`lark98-final` was re-rendered a second time on the persistent copy, after
the follow rig and the timer landed in the shared scene module
(`rollout-9ab49029…webm`, 81 frames, 16.4 s to render; its two earlier
recordings stay retained beneath it). The persistent server was again neither
started nor stopped. The probe decoded frames at 0, 4 and 8 s; drew the
persistent page's viewport at the **same** camera, pose and clock through the
viewport's own copy of the rig (`follow` on the same track gives the same
standoff and the same first camera as the recording, asserted); measured the
model's pixel count and box; framed the 4 s pose close (0.5) and wide (0.08)
through the same rig; orbited from the follow camera by real pointer input;
drew the capture page at the 4 s frame; and put the reference's shipped
frames in the first row. Receipt: [follow.json](follow.json); full-resolution
images in the operator's `cadex-projects/ot6-look/follow/`.

[follow-side-by-side.png](follow-side-by-side.png), four rows of three:

| row | | | |
|---|---|---|---|
| 1 | reference `orbit` at 4 s | reference `swing` at 2 s | reference `flip` at 2 s |
| 2 | [decoded 0 s](video-follow-0s.png) | [decoded 4 s](video-follow-4s.png) | [decoded 8 s](video-follow-8s.png) |
| 3 | [viewport, same frame as 4 s](viewport-follow-4s.png) | [close, 0.5](viewport-follow-close.png) | [wide, 0.08](viewport-follow-wide.png) |
| 4 | [after a pointer drag](viewport-follow-orbit.png) | capture page at 4 s | viewport at 8 s |

**The rig, as recorded into the video** (`framing`): fraction **0.22**,
standing height 235.4 mm at the first solved pose, standoff **1 027.7 mm**,
subject 0.06 below centre, drift limit 0.26, half-window 4 frames (0.4 s at
10 fps, the reference's 20 frames at 50 Hz). Measured over the clip: apparent
size 0.2198–0.2201 of the frame height, worst residual drift 0.0026 of the
half-frame. Lark crouches from 235.4 to 224.9 mm between 0 and 4 s and then
holds; the rig frames the standing height, so that reads as a crouch rather
than being re-fitted away.

| frame | camera distance / yaw / pitch | apparent fraction, analytic | viewport vs decoded, mean RGB error |
|---|---|---|---|
| 0 s | 1 027.7 mm / 0.8 / 0.5 | 0.2199 | **1.16** / 255 |
| 4 s | same | 0.2199 | **1.24** / 255 |
| 8 s | same | 0.2199 | **1.24** / 255 |

The viewport and the capture page at the 4 s frame are byte-identical,
timer included. The model's *pixel box* in those frames is 0.58–0.59 of the
frame height, not 0.22, because Lark's cyan slab is a component of the ot5
design and the box spans it; the analytic fraction is the rig's number, and
the ot6 mechanisms carry no slab.

| framing | camera distance | fog near / far (m) | floor (m) | grid minor (m) | model pixels |
|---|---|---|---|---|---|
| close 0.5 | 452 mm | 1.00 / 6.33 | 25.3 | 0.2 | 149 720 |
| follow 0.22 | 1 028 mm | 1.54 / 14.4 | 57.6 | 0.5 | 74 096 |
| wide 0.08 | 2 826 mm | 4.24 / 39.6 | 158.3 | none | 8 453 |
| after the drag | 1 028 mm | 1.54 / 14.4 | 57.6 | 0.5 | 82 458 |

At every framing the floor runs to four times the fog's far distance
(asserted), the model stays drawn, and the drag changes yaw and pitch and
nothing else. The contact shadow lies beside the feet at close and follow
framings; at 0.08 it is below what 512 px resolves, as before.

**The timer**: the reference's caption pill — panel `rgba(20,22,26,.72)`,
line `rgba(244,245,247,.22)`, the page's `--ink` and `--font`, tabular
letter-spaced numerals — drawn inside the WebGL frame 4.2 % of the height
from the bottom-left corner at 3.2 % of the height (16 px here), so the
viewport and the capture bake the same pixels. With the clock hidden and
shown at the same orbit camera, the 2 455 pixels that change are all inside
x 21–104, y 459–490: bottom-left, nothing else. It is larger relative to the
frame than the reference's 1.6 vh clock on purpose: a 512 px video has to
read on a phone.

**Assessment of what changed.** Row 2 beside row 1 now reads as the same
kind of shot: subject small and central with headroom, the mat filling the
lower half, the horizon a third down, a clock in the corner. What differs is
the subject — a colourful boxed biped on its own bright slab against a white
drone on the bare mat — and that Lark barely moves, so the rig's smoothing
and drift limiter are exercised by `test_video.py`'s synthetic walk and whip
rather than by this clip. The subject-tracking behaviour on a mechanism that
travels is measured there, not here, until a D6 run travels.

## Tests

`test_follow_receipt_records_the_tracking_camera_and_timer_on_the_operator_url`
pins the follow receipt: the run the persistent page selected, the rig's
declared numbers and the standoff formula, the viewport's rig agreeing with
the recording's, apparent size within 0.005 of 0.22 at every decoded frame
and of 0.5 / 0.08 at the close and wide framings, viewport and capture
identical, every decoded frame inside the codec tolerance, the floor
outrunning the fog, the drag leaving the distance alone, the timer's pixels
confined to the bottom-left, and every committed image cited here.
`cli/tests/test_video.py` adds the rig and the overlay on a fixture: the
standoff, a walk that moves the target without moving the horizon, a whip of
one standoff held inside the drift budget, and a clock whose pixels are the
only difference between two renders.

`cli/tests/test_review_design.py` also pins the first receipt: the compared run is the
one the persistent page selected, both style names are dark, the viewport
and capture bytes are equal, the decoded frame is inside the codec
tolerance, the reference renderer's same-pose luminance equals the
viewport's within 0.2, the floor outruns the fog at every framing, the
model stays drawn through the orbit, and every committed image is under the
cap. `test_the_environment_is_dark_only_and_the_style_says_so` holds the
module to one palette and no theme setter; `test_video.py` asserts new
recordings carry `cadex-prototype-dark-v1`.
