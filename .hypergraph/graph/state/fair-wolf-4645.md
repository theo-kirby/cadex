---
node_id: c982757d-579a-5046-bd48-f0b531b38ffd
slug: fair-wolf-4645
title: D11. Viewport and videos match the neural-whoop visual reference
created_at: '2026-09-12T21:20:29+00:00'
parents:
- crisp-sun-1239
summary: ''
---
Status: working

## Current

**D11 now has a current Lark comparison on the persistent private dashboard, so the visual evidence no longer belongs only to Wren.** On `ot5-lark-copy85` serving `lark86-retry-video` (accepted revision `7f6c23913d55…`, policy `074e22f1070c…`, seed 0, 8 s), the existing `review-style/compare.py` and `wren-fresh/check_video.py` probes ran against port 8765 with the reference checkout read-only: same-pose/camera viewport and capture PNGs are byte-identical and the decoded video's RGB mean absolute error is 1.428984/255 (threshold 3). The retained side-by-side shows an actual reference-native shipped frame, the reference modules rendering Lark's geometry, the persistent viewport and the decoded video at matched close/wide views: floor/grid, seamless fog/sky, matte palette, grounded shadows and framing agree. Deliberate or benign differences: Cadex shadows are slightly sharper, and the fit camera includes the authored plate so the biped sits relatively small in frame. No presentation-stage edge in close, wide or pointer orbit; playback survived three refreshes, download was hash-equal, historical `lark2-final` and `lark2-checkpoint20` played and returned to current. Identities are retained in `style94-evidence.json` with images outside the checkout; no renderer, dependency or recording change [rec: windy-walrus-6950].

**Wren: current 90 mm `wren71-final` comparison on the persistent Wren dashboard.** Byte-identical same-pose PNGs; decoded-video error 1.50058/255. Reference modules at `31caeb28…` restaged with Wren geometry at fit/close/wide cameras beside a shipped dark-reference frame; matching grid, fog/sky fade, palette, lighting and grounded shadows, with the crisper close shadow consistent with ADR-301's fitted frustum/bias. Orbit/zoom and underside showed no stage edge; the finite blue plate is model geometry. Later decoded frames show a bent standing pose, not walking [rec: terse-walrus-5414]. The earlier 110 mm comparison gave 1.5044/255 with 23 evidence tests [rec: kind-oak-1484].

**One shipped browser scene renders both the live viewport and the recorded policy videos in the neural-whoop style; the charter evidence list is met on Reed copy100 and shin55-final.** ADR-300 chose one scene for viewport and explicit video frames after the baseline found two independent renderers (perspective WebGL for review, orthographic CPU for video), neither with floor, fog or shadows; shipped reference clips are dark-themed despite the owner's light request (the light palette wins), and Reed's apparent stage is authoritative ground-slab geometry, never replaced [rec: modest-journey-2059]. ADR-301 delivered the shared scene: the reference's MIT environment and floor code at `31caeb28…` adapted with notices plus a pinned upstream Three.js r160 module, self-contained and CDN-free; the DevTools pipe driver moved from tests into the CLI; Chromium and FFmpeg are video prerequisites. Video records carry style digest `27893221…` (`cadex-prototype-light-v1`), renderer version, projection, camera, bounds and resolution; older recordings survive. Reed evidence: byte-identical 512-square PNGs, decoded final video 1.64/255, light-reference side-by-side agreeing on floor/grid, fog/horizon, palette and occupancy, no edge at fit/0.7x/3x orbit; CLI 373 and engine 2103 passed [rec: royal-arrow-2065]. shin55 rendered checkpoint and final videos in this style during live training [rec: fair-crow-5108]; on shin55-final over port 8765, PNGs byte-identical, decoded error 1.6732/255, orbit/zoom/underside clean, receipt `docs/probes/review-style/shin55.json` test-guarded [rec: soft-aspen-5095].

Charter criterion: match the read-only sibling `neural-whoop` reference (fogged grey prototype-grid floor, seamless fade, sky gradient, lighting/materials, grounded soft shadows, antialiasing, camera quality), scaled with subject and framing; truthful CAD dimensions, placements and motion; licensing honoured and the renderer self-contained. Generic grid or pixel coverage alone cannot establish similarity. Declared target `gap-d11-viewport-videos-match-neural` [rec: modest-dawn-3706].

Reconcile judgement: `working`. The comparison has now been repeated on the current design of each fresh biped (Reed, Wren, Lark) with byte-identical viewport/capture images and decoded-video error under 1.7/255 each time. Only the checkbox edit is owner-reserved [rec: lucky-bramble-8274]. Remaining limits: all observations are same-machine private-address; no light-themed reference clip ships, so comparison uses the reference renderer on Cadex geometry; shadow frustum/bias differ deliberately [rec: soft-aspen-5095] [rec: windy-walrus-6950].

## Negative knowledge

- [scope: the pre-ADR-301 review WebGL shader and CPU video rasterizer | confidence: high | evidence: modest-journey-2059] Two independently tuned renderers cannot establish viewport/video agreement; neither had floor, fog or shadows, and close orbit clipped the torso while wide orbit left the slab floating.

## Provenance

- modest-dawn-3706 — operator directive introduces D11 and the shared visual-reference contract
- modest-journey-2059 — reference/baseline measurement, ADR-300 shared-scene decision, dark-reference and ground-slab findings
- royal-arrow-2065 — ADR-301 shared renderer delivered with real Reed videos, byte-identical PNGs, decoded-frame parity and light-reference comparison
- fair-crow-5108 — shin55 checkpoint/final videos rendered in the shared style during a live experiment
- lucky-bramble-8274 — corrects unsupported owner-acceptance reservation and inventories actual evidence limits
- soft-aspen-5095 — current-design visual comparison, pointer interaction and historical video evidence satisfy D11
- mild-river-8224 — Wren browser inspection explicitly makes no D11 comparison claim
- kind-oak-1484 — backfilled persistent Wren D11 comparison, reference camera restaging and shipped reference frame, with verification limits
- terse-walrus-5414 — current 90 mm matched-camera parity, identified reference comparison and orbit/zoom assessment close the current-design evidence gap
- windy-walrus-6950 — current Lark `lark86-retry-video` comparison on the persistent URL: byte-identical PNGs, decoded RGB MAE 1.428984/255, close/wide/orbit inspection, playback/download verified
