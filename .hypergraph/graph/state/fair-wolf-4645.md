---
node_id: c982757d-579a-5046-bd48-f0b531b38ffd
slug: fair-wolf-4645
title: D11. Viewport and videos match the neural-whoop visual reference
created_at: '2026-09-12T21:20:29+00:00'
parents:
- crisp-sun-1239
summary: ''
---
Status: open

## Current

**One shipped browser scene now renders both the live viewport and the recorded policy videos in the neural-whoop style; owner visual acceptance remains explicit and open.** ADR-300 chose one scene for viewport and explicit video frames after the baseline measurement found two independent renderers (perspective WebGL for review, orthographic CPU for video), neither with floor, fog or shadows; it keeps Python validation, locking, sampling, encoding and a fixed whole-trajectory camera. The baseline also recorded that shipped reference clips are dark-themed despite the owner's light request (the light palette wins), and that Reed's apparent stage is authoritative ground-slab geometry, which is never replaced [rec: modest-journey-2059].

ADR-301 delivered that shared scene: the reference's MIT environment and floor code at commit `31caeb28…` adapted with notices, plus a pinned upstream Three.js r160 module, self-contained and CDN-free. The DevTools pipe driver moved from tests into the CLI; Chromium and FFmpeg are video prerequisites. New video records carry style digest `27893221…` (`cadex-prototype-light-v1`), renderer version, projection, camera, bounds and resolution; older recordings and `run.json` references survive [rec: royal-arrow-2065].

Evidence: persistent viewport and capture page at the same solved pose/camera/resolution produce byte-identical 512-square PNGs; the decoded final video differs by mean absolute RGB error 1.64/255 (threshold 3). Side-by-side against an actual light reference frame rendered with the unmodified reference modules on Reed's own geometry, floor/grid, fog/horizon, palette and camera occupancy agree; no environment edge appears in fit, 0.7x close or 3x wide orbit, and the underside stays inspectable. Deliberate differences: a tighter shadow frustum and scale-derived bias; neither side simulates area-light penumbrae. Real Reed copy100 final and probe3 checkpoint20 videos were re-rendered; CLI suite 373 passed and engine suite 2103 passed [rec: royal-arrow-2065]. The shin55 experiment then rendered checkpoint and final videos in this style during and after live training [rec: fair-crow-5108].

Charter criterion: match the read-only sibling `neural-whoop` reference (fogged grey prototype-grid floor, seamless fade, sky gradient, lighting/materials, grounded soft shadows, antialiasing, camera quality), scaled with subject and framing; truthful CAD dimensions, placements and motion; licensing honoured and the renderer self-contained. Generic grid or pixel coverage alone cannot establish similarity. Declared target `gap-d11-viewport-videos-match-neural` [rec: modest-dawn-3706].

Reconcile judgement: keep `open`. Implementation and comparison evidence exist, but the records claim no acceptance and the charter reserves visual acceptance for the owner [rec: royal-arrow-2065].

## Negative knowledge

- [scope: the pre-ADR-301 review WebGL shader and CPU video rasterizer | confidence: high | evidence: modest-journey-2059] Two independently tuned renderers cannot establish viewport/video agreement; neither had floor, fog or shadows, and close orbit clipped the torso while wide orbit left the slab floating.

## Provenance

- modest-dawn-3706 — operator directive introduces D11 and the shared visual-reference contract
- modest-journey-2059 — reference/baseline measurement, ADR-300 shared-scene decision, dark-reference and ground-slab findings
- royal-arrow-2065 — ADR-301 shared renderer delivered with real Reed videos, byte-identical PNGs, decoded-frame parity and light-reference comparison
- fair-crow-5108 — shin55 checkpoint/final videos rendered in the shared style during a live experiment
