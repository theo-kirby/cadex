---
node_id: 79df8eab-2148-5739-8acc-5bddf17fc381
slug: tiny-ash-6709
title: 'H1: Noto Sans replaces the 5x7 face in every render and video (ADR-568)'
created_at: '2026-10-06T17:58:11+00:00'
parents:
- witty-bay-1622
summary: ''
---
## What

H1, the font: every caption, label and clock Cadex draws into an image or video is now
set in Noto Sans Regular (SIL OFL 1.1), read from a 9.7 KB subset TrueType file shipped
beside `CadexStudio.py` and rasterised there in the standard library. The 5×7 bitmap
face (`_FONT_ROWS`, `FONT`) is deleted. ADR-568.

## Why

The critic's message named H1 as this unit: remove `_FONT_ROWS`, put in an open-licensed
sans with a PROVENANCE entry and an ADR, and render one image of each kind before
changing anything. Done as asked. H1 is also the highest-ranked open criterion whose
work is unblocked (G2's proof stands; H2 and H3 need the H1 font first).

## Method

- **Before images first.** Scratch copy `~/cadex-projects/orun4-biped-sts` of the
  reference project (read-only original untouched). One harness (kept out of the repo)
  rendered, from accepted revision `14b7223ee485` and its passing evaluation
  `14b7223ee485-235b65eba72d`: the hero and concept sheet (`render_files`), a blueprint
  (`blueprint_report`), the evaluation film's overview and detail sheets and its video
  (`film.film_evaluation`, seed 9101), and one decoded video frame at 1.0 s. Same
  harness after the change.
- **The face.** Noto Sans Regular 2.004 from Debian `fonts-noto-core` 20201225-2,
  subset with the environment's fontTools `pyftsubset` (ASCII + 17 symbols, no hinting,
  no layout tables). Licence text from the package's copyright file into
  `NotoSans-OFL.txt`. Both added to `src/Mod/cadex/CMakeLists.txt`; PROVENANCE §8j and
  THIRD_PARTY_LICENSES §4 record it. No new runtime dependency: fontTools was used once
  at authoring time and is not imported by anything.
- **The rasteriser** (`CadexStudio.Face`, `_coverage`): cmap format 4, loca/glyf simple
  and composite glyphs, hmtx, OS/2 cap height; quadratic curves in six segments;
  nonzero winding with exact horizontal coverage over five scanlines per pixel; glyph
  cache; alpha blend. `scale` keeps its meaning (capitals 7×scale px, top at y).
- Clocks `T 0.90 S` → `0.90 s` (film.py, video.py); `film_digest`/`studio_digest` hash
  the font; blueprint part numbers right-aligned by measured width; `Ø`/`°` drawn rather
  than spelled out.
- Tests: CLI `test_the_face_is_a_plain_antialiased_sans_and_marks_what_it_lacks`
  replaces the 5×7 test; engine `test_the_render_font_ships_with_its_licence`.

## Result

**Measured before/after** (`docs/probes/orun4/h1-*-before-after.png`, six PNGs, each
≤ 88 KB, left before, right after): hero 0 px changed; concept sheet 0 px changed outside
the lettered right panel (28,657 inside it); film overview 0 px outside the clock boxes
(6,409 inside); film detail 0 outside (6,560 inside); blueprint drawing unchanged, text
column re-flows because the notes fit one line; video frame differs outside the clock
by ≤ 32 grey levels, which is VP9 coding noise (the same renderer's film sheets differ by
0 outside text).

`pixi run build-engine`
installed both new files into `build/release/Mod/cadex/`.

- `pixi run test-engine`: **2602 passed, 58 skipped** in 5:39.
- CLI suite, GPU hidden, in the owner's three interleaved thirds: **400 passed** (2:45),
  **353 passed, 1 skipped** (5:30), **443 passed** (2:08): green. The suite as **one**
  command was tried first and was killed at the shell's 10-minute limit (the thirds sum
  to about 10.4 min of wall time). So the owner's under-8-minute target is **not** met
  on this machine today. Either ADR-564's measurement does not hold here or the machine
  was slower; the next iteration should re-measure before relying on one command. The
  slowest test is `test_walk.py::test_the_walk_takes_the_toy_to_a_verified_rollout_and_iterates`
  at 63 s.

Concerns for the next iteration: the text is drawn in the case the caller wrote, so
labels that relied on upper-casing now read lower-case (`front`, `mass`, `palette`) —
deliberate, as a normal font reads in normal case. The 18 px blueprint parts rows are
tight for descenders (`_`, `p`) but do not overlap. The packaged payload was not
re-staged this unit; the font is in the CMake install list (pinned), so the next
`stage-engine` carries it. H1's charter evidence is complete for the critic to judge;
next by priority is H2 (the two heroes on a passed evaluation), on the scratch copy
`orun4-biped-sts` made this unit.

Dispatch closed: 1 unit — H1: Noto Sans replaces the 5×7 face in every render and video (ADR-568), with before/after images

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/orun4
- commit: 1a39f6c1b07d6fea08e1492c226daec12e43faaa

## State Impact

- target: solemn-key-8049 — evidence complete pending critic: _FONT_ROWS deleted; Noto Sans Regular (OFL 1.1) subset shipped beside CadexStudio.py with licence, PROVENANCE §8j and ADR-568; before/after images of hero, concept sheet, blueprint, film overview/detail and video frame in docs/probes/orun4/h1-*, text-only differences measured (commit 1a39f6c1)
