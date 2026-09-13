# Review environment: shared renderer and visual comparison

Verified against source: 2026-09-13. [Cadex-new]

**The shared renderer is delivered (ADR-301) and its comparison has been
repeated on the current design.** The persistent Reed dashboard, the
`copy100`, `shin55-final` and Wren's `wren57-retry` final-policy videos and the
`probe3-checkpoint20`, `shin55-checkpoint20` and `wren2-final` recordings use
the same reference-derived light scene. The charter's D11 evidence list is assessed item by item in the
[lifecycle report](../reed-lifecycle/README.md#d11-assessment); the evidence
below is that assessment's source and claims no new training experiment or
completion of the lifecycle charter.

## Current 90 mm Wren comparison — iteration 73

The persistent private-network dashboard still serves **ot5-wren-copy54**,
with **wren71-final** selected on a fresh visit, revision `e9dee22bc90c…`,
90 mm feet and 18 retained runs. The [compact receipt](wren90.json) closes
the current-design comparison gap recorded by the Wren lifecycle report.
No new training, video publication, project switch or server restart occurred.

```bash
PYTHONPATH=cli pixi run python docs/probes/review-style/compare.py \
  "http://$(tailscale ip -4):8765/" "$HOME/cadex-projects/ot5-wren-copy54" \
  "$HOME/neural-whoop" wren71-final wren57-retry style73
```

Images, `side-by-side.html`, its screenshot and `comparison.json` remain in
this project's `evidence/style73/`. The additional `check_current.py` there
fully decodes the current video, extracts frames 40/80 and checks current
playback/download through three refreshes; run it with `PYTHONPATH=cli pixi
run python` and the same private URL. The reference checkout was read-only:
commit `31caeb28abb3bdab8d9030bfc91f0c3f48ffa63a`, actual shipped
`render-examples/orbit_maneuver_policy.mp4` at 4 s (video SHA-256
`cbb4a98684bcc96ac9a85d4fa53e74522ac66684c94c62e401ef04a3b1bae26f`).
That shipped frame is dark-themed. The light comparison renders the exact
Wren geometry through the reference's unmodified scene/environment modules
at identical fit, close and wide cameras. No drone glyph enlargement is applied.
The retained filenames `reference-light-reed*` are the generic probe's names;
their actual subject here is the current Wren, not Reed.

| Property | Assessment from the retained images |
|---|---|
| Pose/camera parity | Persistent viewport and capture-page 512² PNGs are byte-identical. Decoded current frame zero has RGB mean absolute error **1.50058/255** (tolerance 3/255). Camera yaw 0.8, pitch 0.5, distance 1111.04 mm and target `[0, 0, 127.88133]` mm match the video record. |
| Floor/grid | Same grey tiles, metre labels, major lines and framing-derived subdivisions in reference and Cadex. The finite blue plate is actual 600×600 mm model geometry, not the presentation floor. |
| Horizon/fog/sky | Fit and low-pitch 3× wide pairs fade smoothly into the cool-grey sky gradient. No stage edge, wall or ceiling seam is visible. |
| Palette/materials | Same bright, rough coloured components and subdued floor. Faces have comparable light/dark separation, with no glossy or metallic distraction. The shipped dark drone frame establishes the reference-native grid/fog layout; its palette is not misrepresented as the light target. |
| Lighting/shadows | Both lights cast the torso shadow beside and connected to the feet on the plate. Cadex's close-view shadow is slightly crisper than the reference's filtered edge, consistent with ADR-301's fitted frustum/bias. No floating contact or lost shadow at close framing was seen. At 3× wide the shadow becomes a small mark, as it does in the reference. |
| Camera/antialiasing | Fit and 0.7× close retain torso and feet with comparable occupancy. Edges are smooth at 512²; video encoding slightly softens them. At 3× wide the subject is deliberately small but remains visible. |
| Pointer orbit/zoom | Real drag changes yaw 0.8→2.6 and pitch 0.5→0.8. Wheel zoom reaches 647.46 mm then 3916.90 mm; model coverage is 50,553/130,069/4,138 pixels for drag/near/far. The floor restages from 62.22 m to 219.35 m with fog far 15.55→54.84 m; the far view has major lines only and no edge. |
| Underside/motion | Below-floor orbit removes the front-sided presentation floor and exposes the real plate underside. Decoded frames 40 and 80 (4 and 8 s) show the biped holding a bent pose on the same floor with grounded shadow; no gait claim follows. |

The current video (`a2fde70a2239…`, policy `fa7b28b8732a…`, rollout seed 0)
fully decodes to **81 frames at 10 fps**, 8.1 s encoded for 8 s simulation.
It plays and downloads with its recorded digest, retaining playback through
three polls. Historical `wren57-retry` (110 mm) also plays/downloads, stays
historical through polling, and returns to the current run. Both retain
`cadex-prototype-light-v1`, style SHA-256
`27893221b3c6cf784d62c16fdaa5c88d1beb031bcb195e5f34e1598ea56e5b0c`.

No visual mismatch requiring a renderer change was demonstrated. This is a
same-machine browser check through the private address, not a second-device
test or a new live-training telemetry measurement. Old recordings remain
historical; no accepted state or retained run artifact was rewritten.

## Repeat on Wren `wren57-retry` — iteration 64

The persistent operator page now serves the Wren working copy, so the D11
comparison was repeated on the run it selects by default, `wren57-retry` at
accepted/playback revision `79f86c69bfc3…` (110 mm feet), with the earlier
design's complete recording `wren2-final` (105 mm feet, its own revision
`26332a5955e3…`) as the historical clip played, downloaded and polled from the
same page:

```bash
PYTHONPATH=cli pixi run python docs/probes/review-style/compare.py \
  "http://$(tailscale ip -4):8765/" "$HOME/cadex-projects/ot5-wren-copy54" \
  "$HOME/neural-whoop" wren57-retry wren2-final style64
```

`compare.py` gained two things for this repeat, and its earlier commands stay
true: the reference renderer is now restaged at the **same close (0.7×) and
wide (3×) cameras** the persistent viewport is staged at, so framing scale, fog
and shadow are compared like for like rather than only at the fit camera; and
an **actual shipped reference frame** — `render-examples/orbit_maneuver_policy.mp4`
at 4 s, the file the baseline decoded (`cbb4a98684bc…`), dark theme — sits in
the side-by-side beside the reference-module light renders. [Compact
evidence](wren.json) retains identities, cameras, stage, orbit numbers and
image digests; the PNGs, the three-row `side-by-side.html` and its screenshot
live in the project's `evidence/style64/`, with the retry's frames 40 and 80
and the historical clip's frame 40 decoded afterwards with the same FFmpeg and
digested under `motion_frames`. Nothing in the server, project or reference
checkout was changed; the service on port 8765 was not restarted.

What the run established, and what was seen in the images:

- **Same pose, same camera, viewport and video.** The persistent viewport at
  the video's fixed camera and the capture page at the identical pose are
  byte-identical 512² PNGs (`38e90eef7395…`); the page's default fit is that
  camera, so `persistent-default` is the same image. FFmpeg's decoded frame
  zero of the real `wren57-retry` clip differs by mean absolute RGB error
  **1.5044 / 255**, inside the 3 / 255 tolerance and below both Reed figures.
- **Side by side with the reference, at three framings.** At fit, close and
  wide, `reference-light-reed*` and `persistent-*` show the same fogged grey
  prototype grid with `PROTOTYPE` / `1 METER` labels and fine subdivisions,
  the same floor-to-sky fade, the same cool-grey palette and bright rough
  component colours, the same steep key and grounded filtered shadow on Wren's
  authored blue ground plate, at identical occupancy. At close range the
  reference's shadow is marginally softer and wider — ADR-301's deliberate
  tighter frustum and scale-derived bias — and at wide range both fade the
  floor into the horizon with no stage edge, wall or ceiling seam. The shipped
  dark drone frame has the same tile layout, label placement, major/minor
  lines, fog-to-horizon and grounded contact shadow under a different palette
  and subject; it is the reference-native look the light theme re-colours.
- **Motion frames.** The retry's frames 40 and 80 (4 s and 8 s) show the policy
  holding a bent standing pose on the plate — the recorded motion, unaltered,
  and not a gait claim — and the historical clip's frame 40 shows the 105 mm
  design in its own pose; all keep the same grid, labels, fog and lighting.
- **Close and wide framing, underside, and orbit by real pointer input.**
  Underside removes the front-sided presentation floor and leaves the plate's
  real underside inspectable. A real left-button drag moved the camera from
  yaw 0.8 / pitch 0.5 to yaw 2.6 / pitch 0.8 at the same 1111 mm and the grid
  restaged around it; a wheel zoom-in to 647 mm kept the contact shadow under
  the feet; a wheel zoom-out to 3917 mm (3.5×) restaged the environment from a
  62 m room with fog far at 15.6 m to a 219 m room with fog far at 54.8 m and
  major lines only, with no edge or seam. The model stayed drawn throughout
  (50 553 / 130 069 / 4 138 model pixels).
- **Playback, download, polling and history.** `wren2-final` is labelled
  `HISTORICAL — recorded at 26332a5955e3, accepted now is 79f86c69bfc3`; its
  clip played, its download digest matched its record (`59825c07950c…`, 81
  frames, same style digest and renderer as the retry), playback survived a
  poll, and the current-run control returned to `wren57-retry`.

No visual defect was demonstrated, so no renderer change was made. Every
observation is same-machine over the private address; the checkout still
ships no light-themed clip, so the shipped frame is dark and the light
comparison is the reference renderer on Wren's own geometry.

## Repeat on `shin55-final` — iteration 44

The same-pose, same-camera comparison was first made on `copy100`. It has now
been repeated on the run the persistent operator page selects by default,
`shin55-final`, at accepted revision `67b5000f3de1…`, with `shin55-checkpoint20`
as the historical clip played, downloaded and polled from the same page:

```bash
PYTHONPATH=cli pixi run python docs/probes/review-style/compare.py \
  "http://$(tailscale ip -4):8765/" "$HOME/cadex-projects/ot5-biped-copy29" \
  "$HOME/neural-whoop" shin55-final shin55-checkpoint20 style44
```

[Compact evidence](shin55.json) retains the identities, camera, stage, orbit
numbers and image digests; the PNGs, `side-by-side.html` and its screenshot
live in the project's `evidence/style44/`, beside the decoded final frame
(`video-frame5.png`) and a mid-clip checkpoint frame (`checkpoint-frame40.png`)
decoded afterwards with the same FFmpeg. Nothing in the server, project or
reference checkout was changed; the service on port 8765 was not restarted.

What the run established, and what was seen in the images:

- **Same pose, same camera, viewport and video.** The persistent viewport at
  the video's fixed camera and the capture page at the identical pose are
  byte-identical 512² PNGs (`3bd31fe2d227…`). FFmpeg's decoded frame zero of
  the real `shin55-final` clip differs from that viewport by mean absolute RGB
  error **1.6732 / 255**, inside the 3 / 255 codec tolerance and within 0.03 of
  the `copy100` figure. The page's default fit for this design is the same
  camera, so `persistent-default` and `persistent-same-pose` are one image.
- **Side by side with the reference.** `reference-light-reed` (the unmodified
  reference modules on Reed's exact `shin55` geometry), `persistent-same-pose`
  and `video-frame0` show the same fogged grey prototype grid with its
  `PROTOTYPE` / `1 METER` tile labels and fine subdivisions, the same smooth
  floor-to-sky fade, the same cool-grey palette and bright rough component
  colours, the same steep key with the biped's grounded, filtered shadow on the
  orange slab, and identical framing. The only differences are the ones ADR-301
  chose deliberately: Cadex's tighter shadow frustum and scale-derived bias
  give a slightly crisper contact edge.
- **Motion frames.** The final clip's last frame (0.46 s, fallen forward) and
  the checkpoint's frame 40 (crouched, 4 s) keep the same grid, labels, fog and
  lighting; the falls are the recorded motion, unaltered.
- **Close and wide framing, and orbit by real pointer input.** Staged 0.7×
  close (torso and feet retained, shadow on slab), 3× wide at low pitch (floor
  fades into the horizon, no stage edge) and underside (front-sided
  presentation floor gone, real slab underside inspectable) match the
  `copy100` findings. A real left-button drag on the persistent canvas then
  moved the camera from yaw 0.8 / pitch 0.5 to yaw 2.6 / pitch 0.8 at the same
  distance and the grid restaged around the new view; a wheel zoom-in to
  400 mm kept the contact shadow and the grid under the feet; a wheel zoom-out
  to 2423 mm (3.5×) restaged the environment to a 136 m room with fog far at
  33.9 m and major lines only, and showed no edge, wall or ceiling seam. The
  model stayed drawn throughout (46 134 / 117 678 / 3 763 model pixels).
- **Playback, download, polling and history.** `shin55-checkpoint20` is
  labelled `HISTORICAL — recorded at a3591f651443, accepted now is
  67b5000f3de1`; its clip played, its download digest matched its record
  (`89bfc9ecde0e…`, 81 frames, same style digest as the final), playback
  survived a poll, and the current-run control returned to `shin55-final`.

No visual defect was demonstrated, so no renderer change was made. The
`shin55-checkpoint20` and `shin55-final` clips share their first frame because
they share geometry, initial pose, bounds and camera; their policies, traces
and later frames differ. As before, every observation is same-machine over the
private address, and the checkout still ships no light-themed reference clip.

## First comparison on `copy100` — iteration 40

```bash
PYTHONPATH=cli pixi run python -m cadex_cli.video \
  --project "$HOME/cadex-projects/ot5-biped-copy29" --run copy100
PYTHONPATH=cli pixi run python -m cadex_cli.video \
  --project "$HOME/cadex-projects/ot5-biped-copy29" --run probe3-checkpoint20
PYTHONPATH=cli pixi run python docs/probes/review-style/compare.py \
  "http://$(tailscale ip -4):8765/" "$HOME/cadex-projects/ot5-biped-copy29" \
  "$HOME/neural-whoop"
```

[Implementation evidence](implementation.json) retains the camera, model, policy,
style and image digests. The full PNGs, a standalone `side-by-side.html`, its
screenshot, and the detailed receipt live in the project's `evidence/style40/`.
The images are **actual rendered/decoded images**, with no AI image generation.
Keep them with the project; no video or image dump is committed here.

The comparison uses the persistent private-network server, verifies `copy100`
and its accepted revision, and changes only browser camera/framing. Its model
comes from the server's retained geometry and initial pose. The capture page
receives that same pose and fixed trajectory camera. Their 512² PNGs are
**byte-identical**. FFmpeg's decoded final-policy frame differs by mean absolute
RGB error **1.6423 / 255**, below the test's 3 / 255 codec tolerance.

The light reference is generated by the **unmodified actual reference scene,
environment and floor modules**, hosted read-only by a temporary in-memory
harness. It renders Reed's exact geometry, colours, pose and camera, so geometry
and framing cannot conceal a visual mismatch. Its light frame supplements the
actual dark drone policy frames inspected in the prior baseline. Neither the
sibling checkout nor its assets are modified, and Cadex's renderer never imports
from that checkout. This harness needs the reference's existing pinned Three.js
cache; that is a probe prerequisite, not a delivered runtime dependency.

### Side-by-side assessment

Viewed `reference-light-reed`, `persistent-same-pose`, decoded `video-frame0`
and their combined comparison; also inspected `persistent-default`, `close`,
`wide`, `under` and the decoded checkpoint frame.

| Property | Observed result |
|---|---|
| Floor/grid | Same light checker/grid, metre labels and fine subdivisions. The orange 400×300×10 mm slab remains finite model geometry; the environment extends below it. |
| Horizon/fog | Smooth floor-to-background fade and subtle sky gradient in all three images. Low wide orbit shows no stage edge, wall or ceiling seam. |
| Palette/materials | Matching cool greys and bright rough component colours with ACES exposure 0.95. The material and colour mapping is shared; recorded poses and sizes are unchanged. |
| Lighting/shadows | Same steep key and hemisphere/opposite fill. Grounded, filtered cast shadows land on the model slab. Cadex fits the shadow map more tightly and uses a smaller scale-derived normal bias than the reference's minimum 1 m extent / 2 mm bias. Its contact is correspondingly tighter; neither uses area-light penumbra simulation. |
| Framing/antialiasing | Identical perspective camera and occupancy for the decisive comparison. Close orbit at 0.7× distance retains the torso and feet; 3× wide orbit retains the grounded slab at appropriately smaller scale. Shared MSAA, with small VP9 edge/colour loss only. |
| Underside | Front-sided presentation floor disappears underneath, leaving the real slab underside inspectable. This deliberate CAD adaptation avoids the reference's double-sided plane occluding the model. |

The real final clip is **8 frames / 0.62 simulated seconds**, rendered in
**2.313 seconds**; the checkpoint is **81 frames / 8 simulated seconds**,
rendered in **20.025 seconds**. Both decoded completely and share style digest
`27893221b3c6cf784d62c16fdaa5c88d1beb031bcb195e5f34e1598ea56e5b0c`.
The compact receipt records full policy/video hashes and Chrome version.
Prior video files and references remain, explicitly labelled legacy when no
style exists. Re-render publication preserves videos even when their original
references live in `run.json` rather than `video.json`.

The persistent operator probe passes final playback/download, current identity,
poll preservation, historical selection and return to current. `compare.py`
also plays/downloads the real checkpoint and checks playback across a poll.
The probe activates the dashboard tab after opening capture: Chromium correctly
suspends background-tab video playback. Early probe attempts timed out there;
they were harness errors, not corrupt recordings. Initial implementation checks
also exposed/fixed a module initialization cycle, a DOM-ready race and bounds
rounding in display metadata. Final source keeps millimetre bounds independent
of GPU float conversion. No successful claim rests on those failed attempts.

Source guards and fixture tests include decoded moving frames, same-camera
viewport/video error, both old/new encodings' playback/download, existing
polling/history/orbit checks, model-only pixel counting and invalid-input failure
isolation. Full zone results are in implementation.json and the work record.
No GPU training was started, so this unit does not measure render overhead on
active training or close D10's experiment-spanning gap. The persistent service
stays on Reed `copy29/copy100` at port 8765 between iterations.

## Historical baseline — iteration 39, before replacement

**At this baseline D11 was not met.** The baseline probe captured the Reed dashboard and decodes
actual reference recordings. It establishes the visual gap before renderer
replacement; it does not claim equivalent framing or a same-pose/camera match.
The persistent port 8765 still serves `ot5-biped-copy29`, run `copy100`, revision
`25d9b6ab7472b968a3a72691ca44113ea86beda85802af3e22d9270952cb71fc`.

Run from the checkout using the existing headless browser and FFmpeg:

```bash
PYTHONPATH=cli:cli/tests pixi run python docs/probes/review-style/baseline.py \
  "http://$(tailscale ip -4):8765/" "$HOME/cadex-projects/ot5-biped-copy29" \
  "$HOME/neural-whoop"
PYTHONPATH=cli:cli/tests pixi run python docs/probes/operator-review/verify.py \
  "http://$(tailscale ip -4):8765/" "$HOME/cadex-projects/ot5-biped-copy29" copy100
```

The reference argument is read-only, used only by this research probe. The
probe neither starts a server nor changes a run. Images and its full receipt
live in the working project's `evidence/style39/`; retain that directory with
the project. [Compact evidence](evidence.json) includes source, recording and
image SHA-256 values, camera coordinates, model bounds and accepted identity.
[Operator checks](operator.json) independently prove real playback, matching
download bytes, polling preservation, historical selection and return to current.
No new training or second-device test occurred.

## Reference examined

The source checkout is `31caeb28abb3bdab8d9030bfc91f0c3f48ffa63a`.
Read `web/studio/{environment,scene,geometry}.js`, both `web/capture/` files
and `render-examples/README.md`; the evidence hashes identify their actual bytes.
Decoded and visually inspected frame zero of the flip, swing and orbit policy
MP4s (720×720). Their clocks show 0.02 seconds. The flip provides a wide view,
the swing a closer product view, and the orbit a middle distance.

**The shipped examples are dark.** They show a charcoal prototype checker/grid,
fine subdivisions and metre labels, fading into a near-black sky with no stage
edge. The white drone has shaded surfaces and visible cast shadows. The flip's
shadow is noticeably separated from the flying subject; it is not a contact
shadow demonstration. The clips' glyph is enlarged threefold, explicitly stated
in their README. Neither that enlargement nor flight-specific framing belongs
in Cadex geometry.

The owner's light-grey request takes precedence over those examples' dark theme.
The light palette exists in `environment.js`, but no light reference frame was
rendered in this unit. Visual acceptance must include one produced by the actual
reference renderer with its light theme, rather than recolouring a decoded image.

## Observed Cadex gap

Inspected `cadex-fit.png`, `cadex-close-orbit.png`, `cadex-wide-orbit.png` and
`cadex-video-frame0.png` alongside the three decoded references.

| Property | Current Reed viewport and saved video | Reference / delivery requirement |
|---|---|---|
| Floor/grid | Orange model slab; no environment grid | Measured prototype grid and framing-dependent subdivisions |
| Horizon/fog | Viewport flat charcoal, video flat near-white; no fade | Floor fades fully before its edge; sky meets fog at the horizon |
| Lighting/shadows | Flat component shading; no cast shadows | Steep key, hemisphere and opposite fill; resolved grounded shadows |
| Materials | Component palette with simple face brightness | Readable rough surfaces and rolled-off highlights |
| Camera | Viewport perspective, video orthographic; different orientation and framing | One explicit camera representation and identical projection for comparison |
| Close/wide orbit | Interaction works; close orbit clips torso; wide view shrinks slab into empty background | Useful fit plus staged close/wide/orbit visual checks |
| Antialiasing | Viewport requests MSAA; CPU video has visibly harder pixel edges | Shared capture quality, measured in decoded output |

The orange slab is **authoritative geometry**, not a defective environment plane:
`runs/copy100/script.py` declares a 400×300×10 mm ground box, from Z=-10 to 0,
and a grounded assembly component. Do not remove, flatten or enlarge it to hide
its edges. A separate environmental floor can extend behind it while preserving
the finite slab and its identity. Its top can receive shadows; no visual fix may
change the biped poses, dimensions or ground contact. Colour order also differs
between the current viewport and video, making shared component identity mapping
part of the renderer contract.

## Original shared renderer contract (ADR-300; implemented above)

Use one browser scene implementation for both the interactive viewport and
explicit offscreen frame capture. Python retains the existing input validation,
policy/model/task/seed checks, solved-sample selection, project render lock,
timeout, encoding and full decode verification. It sends validated geometry and
poses to the shared renderer, rather than maintaining a second visual algorithm.
Camera and lighting operate in one documented frame; a uniform mm-to-m conversion
is valid, per-component glyph enlargement is not. Keep the fixed whole-trajectory
camera as the default so camera tracking does not conceal displacement.

The reference light theme uses tile colours `#9aa0a9`/`#a3a9b2`, major line
`#d7dbe1`, minor line `#b7bdc6`, horizon/fog `#c4c8cf` and upper sky `#a9b0bb`.
Its exposure is 0.95 with ACES tone mapping. Its key direction in Y-up coordinates
is `[0.22, 1, 0.15]`. Hemisphere/key/fill intensities are 2.2/2.2/1.1, plus a
1.4 hemisphere fill. These values specify a coupled colour-management/light
system; copying hex values into today's ungraded shader cannot establish a match.

For camera distance d in metres the reference derives fog near=max(1,1.5d),
far=max(6,14d), with far capped inside the camera frustum. Floor width is at least
four times fog far and covers camera reach. The honest major grid is 1 m; minor
pitch comes from frame span using the 1/2/5 scale ladder. Shadow resolution is
2048², fitted around the subject/trajectory rather than the huge floor. Recompute
staging as orbit/zoom changes framing; preserve visibility and small-scale shadow
contact without lifting the model. Test below-floor orbit explicitly as a CAD
inspection view, rather than accidentally covering the model with a solid stage.

Every newly published video must retain a style version and content digest,
renderer identity, dimensions, projection and camera parameters alongside the
existing revision/policy/seed/time identities. Re-rendering must retain earlier
video entries and files as history: today's `videos=[video]` publication replaces
the references even though older files survive. Preserve the old recordings as
historical, and distinguish their style from newly rendered results.

A single shared scene makes the decisive test possible: supply the identical
Cadex pose, camera, aspect and resolution to the viewport and capture page, then
compare the screenshot with the decoded frame (allowing codec error). Separately
compare light-reference and real-biped scenes at comparable subject occupancy,
with close/wide orbit, floor horizon, contact shadows and material assessments.
Repeat the persistent-server browser probe after delivery. A static baseline
poll is not evidence of five-second updates during GPU training.

## Provenance and verification limits

The reference is MIT, copyright 2026 Theo. This unit imports no implementation
or dependency. Any later adaptation must carry its licence/attribution and ship
local assets; the delivered renderer cannot import sibling paths or depend on a
CDN. If Three.js is chosen, pin and include its MIT notice and write the dependency
reason in the implementation record. This is an implementation choice, not a
licence exception for shell code.

Baseline probe and persistent operator probe both passed. Image decoding and
browser orbit/zoom assertions ran against real files and the private address.
No product code changed, so no build or full CLI/engine suite was run. D11 remains
open: light reference capture, shared rendering implementation, newly styled
videos, same-pose/camera parity and full visual acceptance have no evidence yet.
