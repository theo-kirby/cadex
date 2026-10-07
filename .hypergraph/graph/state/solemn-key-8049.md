---
node_id: e0986e85-176b-515a-9503-50e97ab88b1b
slug: solemn-key-8049
title: H1. One normal font in every image and video
created_at: '2026-10-06T07:42:22+00:00'
parents:
- nimble-pine-0740
summary: ''
---
Status: working

## Current

Charter criterion for run orun4: **H1. One normal font in every image and video.** The 5×7 glyph face in `src/Mod/cadex/CadexStudio.py` (`_FONT_ROWS`) is gone; every caption, label and timestamp the engine or CLI draws is a plain sans-serif (B4) — hero, concept and detail sheets, evaluation film overview and detail images, rollout videos. Nothing else about those renders changes, measured by before/after images of each kind with only the text differing. The font's licence and source go in `docs/PROVENANCE.md`, with an ADR. The human owns the checkbox [rec: light-mist-9160].

**Evidence complete, pending the critic** (ADR-568, commit 1a39f6c1) [rec: tiny-ash-6709].

- **The face**: `_FONT_ROWS`/`FONT` deleted. Noto Sans Regular 2.004 (SIL OFL 1.1), a 9.7 KB ASCII+17-symbol subset TrueType shipped beside `CadexStudio.py` with `NotoSans-OFL.txt`; both in `src/Mod/cadex/CMakeLists.txt`; PROVENANCE §8j and THIRD_PARTY_LICENSES §4. No new runtime dependency: fontTools used once at authoring time [rec: tiny-ash-6709].
- **The rasteriser** (`CadexStudio.Face`, `_coverage`): standard library only — cmap 4, simple and composite glyphs, nonzero winding, antialiased coverage, glyph cache; `scale` keeps its meaning. Clocks read `0.90 s`; `film_digest`/`studio_digest` hash the font; `Ø`/`°` drawn [rec: tiny-ash-6709].
- **Before/after** (`docs/probes/orun4/h1-*-before-after.png`, six PNGs): hero 0 px changed; concept sheet, film overview and film detail 0 px changed outside their text regions; blueprint drawing unchanged with its text column re-flowed; video frame differs outside the clock only by ≤ 32 grey levels of VP9 noise [rec: tiny-ash-6709].
- **Tests**: CLI `test_the_face_is_a_plain_antialiased_sans_and_marks_what_it_lacks` replaces the 5×7 test; engine `test_the_render_font_ships_with_its_licence`. Gates: `pixi run test-engine` 2602 passed, 58 skipped; CLI suite in thirds 400 / 353+1 skipped / 443 passed [rec: tiny-ash-6709].
- Seen in passing: the CLI suite as one command was killed at the 10-minute shell limit, so the owner's under-8-minute target is not met on this machine; re-measure before relying on one command [rec: tiny-ash-6709].

## Negative knowledge

None yet.

## Provenance

- light-mist-9160 — operator-declared orun4 charter gap (gap-h1-one-normal-font-every)
- tiny-ash-6709 — Noto Sans replaces the 5×7 face in every render and video; before/after measured; ADR-568
