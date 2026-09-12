# Review environment: measured baseline and delivery contract

Verified against source: 2026-09-12. [Cadex-new]

**D11 is not met.** This probe captures the current Reed dashboard and decodes
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

## Shared renderer contract (ADR-300; not implemented)

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
