# orun20 K1: leon I from the comparison cameras

Verified against source: 2026-10-24. Frozen run evidence (ADR-792).

Leon I (`~/cadex-projects/leon`, accepted revision `092997dd`), drawn with

    ./cadex hero --project ~/cadex-projects/leon --out <scratch> --only views --software --no-engine

The output is six `view-<name>.png` at 1920×1080 (drawn at 3840×2160), in Studio on the dark mat,
in 387 s on SwiftShader. On this machine the GPU path (ANGLE over Vulkan) returned blank white
frames, and the charter rules out GPU work anyway, so every comparison uses `--software`. Here
they are scaled to 960 px and quantised to 256 colours to stay under 300 KB.

| File | Camera (yaw from the front, pitch) |
|---|---|
| `leon-i-hero.png` | three-quarter, 0.75 rad, 0.42 |
| `leon-i-side.png` | side, π/2, 0.08 |
| `leon-i-front.png` | front, 0, 0.12 |
| `leon-i-rear.png` | three-quarter rear, π−0.75, 0.42 |
| `leon-i-top.png` | top, π/2, 1.45 |
| `leon-i-head.png` | head close-up, 0.6, 0.2, framed on the 15 focus parts alone |

The default `--focus` matched 15 parts on leon: the head-pitch drive, the skull frame, the nine skull
panels, both ears, the jaw servo, its link and the jaw plate. The front measured at yaw 0.00003 rad:
leon faces +X.

A grid of several projects for one camera:

    ./cadex hero-grid ~/cadex-projects/leon ~/cadex-projects/leon-soft ... --still head --tile-width 960 --out grid.png

Each tile is labelled with its project's name, and a missing last tile is filled with the mat.
