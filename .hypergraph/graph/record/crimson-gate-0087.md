---
node_id: 3a358c5e-347b-525e-a6ca-c318ed58930b
slug: crimson-gate-0087
title: Landscape phone gets the review frame with drawers (ADR-344)
created_at: '2026-09-14T16:56:39+00:00'
parents:
- bold-river-6496
summary: ''
---
## What

A phone held landscape now gets the desk frame instead of the portrait column (ADR-344). The rule applies at 600–999 px wide, landscape, and no more than 560 px tall. In that frame:
- The top bar is 40 px.
- The model spans the full width.
- The sidebars open as drawers over the model, one at a time and closed by default. A tap beside an open drawer closes it.
- The page does not scroll.

## Why

The owner asked for landscape mobile to work better and more like desktop. Before this change, a phone at 844×390 showed the portrait column: 6 410 px of scroll with the model as a strip.

## Method

- **Stylesheet.** `review.css` widens the frame media query to `(min-width: 1000px), (min-width: 600px) and (max-height: 560px) and (orientation: landscape)`. A compact block adds drawers (absolutely positioned, slid off screen with a transform) and a `.scrim`.
- **Script.** `review.js` uses the same query in a `FRAME`/`COMPACT` pair and keeps drawer open state that is not remembered.
- **Dead end during the change.** Editing only the first line of a multi-line CSS comment left the rest outside it. That orphaned text swallowed the entire frame `@media` block, which vanished from `document.styleSheets` and silently fell back to the column. It was caught by listing the stylesheet's `cssRules` in the browser, then fixed.
- **Polish.**
  - The title no longer overlaps the accepted-identity line in the bar.
  - The compact status line is held to two lines, with a padding value that shows no glyph of a third line.
- **Test.** New `test_landscape_phone_gets_the_frame_with_drawers_over_the_model` at 844×390 under touch.

## Result

- Screenshots on the operator dashboard at 844×390 and 667×375 show the frame. Drawers open over the model, and the desk layout is unchanged at 1000×800.
- Review, video and style suites: 231 passed, 1 skipped.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: main
- commit: d93183baff24c74af2848a09f326e01ebd36afd2

## State Impact

- target: western-journey-2108 — landscape phones (600–999 px wide, ≤560 px tall) now get the desk frame with drawer sidebars over a full-width model (REVIEW-DESIGN §13, ADR-344); portrait phone layout unchanged
