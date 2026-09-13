# The dark look beside the reference (D3, ADR-331)

Verified against source: 2026-09-13. [Cadex-new]

The review environment is dark only: `cli/cadex_cli/review_static/environment.js`
exports one `PALETTE` and no theme setter, and the viewer's style name is
`cadex-prototype-dark-v1`. This directory is the charter's D3 evidence for that
change (ADR-328): reference frames beside Cadex viewport screenshots and decoded
video frames, at equivalent framing, with the written assessment below. It also
says plainly what D3 still owes.

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
| **Framing** | The framed shot places the biped at 0.22 of the frame height, the reference's default `droneFrac`, and reads like the `swing` frame beside it: subject small and central, mat filling the lower half, horizon a third down. Cadex's *video*, though, is still the fixed fit over every visited pose (`sampling: … fixed camera`), so a rollout that travels shrinks its subject; and the viewer's default fit is tighter (radius / sin 27.5° × 1.15) than the reference's follow rig. |
| **Camera** | Same perspective, 55° vertical, same orbit convention; the viewport and capture agree to the byte at the same camera. **Not matched:** the reference's follow rig — constant offset from a Hann-smoothed subject track, fixed orientation, declared framing fraction, soft drift limit — and its **timer overlay** (the `0.00 s` clock pill). The Cadex capture has neither yet. |
| **Antialiasing** | MSAA on both; the decoded frame's only loss is the codec's. |

**What D3 still owes** after this unit: a tracking camera in the capture at a
declared framing fraction, and the timer overlay on the video, each with its
own decoded frames; the light palette is gone and the environment is shared,
so those two are the remainder. A physical phone or a second machine was not
used; this is headless Chromium 152 on the operator's machine.

## Tests

`cli/tests/test_review_design.py` pins the receipt: the compared run is the
one the persistent page selected, both style names are dark, the viewport
and capture bytes are equal, the decoded frame is inside the codec
tolerance, the reference renderer's same-pose luminance equals the
viewport's within 0.2, the floor outruns the fog at every framing, the
model stays drawn through the orbit, and every committed image is under the
cap. `test_the_environment_is_dark_only_and_the_style_says_so` holds the
module to one palette and no theme setter; `test_video.py` asserts new
recordings carry `cadex-prototype-dark-v1`.
