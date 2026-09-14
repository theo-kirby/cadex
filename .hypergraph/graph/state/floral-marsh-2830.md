---
node_id: 0328b92a-74ba-5f7c-be9a-99a6db55a762
slug: floral-marsh-2830
title: D1. The dashboard is one designed page
created_at: '2026-09-13T21:25:09+00:00'
parents:
- round-sun-8398
summary: ''
---
Status: working

## Current

**D1's evidence list is complete pending the owner's tick; its three units have all landed on the operator URL.** The spec `docs/REVIEW-DESIGN.md` exists: purpose, the six-region hierarchy with stable element hooks, one type scale (12/14/17/22 px, one family, no web font), a dark-only palette whose page background is the environment module's dark scene background, spacing and shape, and two breakpoints with test-asserted invariants. Beside it are the before screenshots at 1400×900 and 400×850 (`docs/review-design/before-*.png`, quantised under 200 KB) and a receipt pinning the sliver ot5 left: at phone width the fixed 280 px sidebar plus min-content tables widened the layout viewport to 868 px and left a 34 px canvas; at 1400 the chrome was blue-grey around a light viewport with six equal cards and no hierarchy [rec: ancient-field-7584]. The page follows the spec's §2–§6 at both charter sizes (ADR-329, commit `9a4ff012`, recorded retroactively by the next iteration from the commit and its re-run tests): one greyscale palette on `:root`, one type scale, six numbered sentence-case regions in the charter's reading order, the run list a sticky 280 px sidebar at desk and a closed disclosure below 600 px, every table scrolling inside its card, a 16:9 canvas (4:3 on phone); the after screenshots and receipt on the operator URL (`ot5-lark-copy85`, `lark109-engine2`, live) give layout viewport 1400 / 400 px with zero horizontal overflow, and the rendered-page half of `cli/tests/test_review_design.py` asserts the tokens by `getComputedStyle`, the type sizes, the overflow and the canvas fill — 17 passed with a Chromium present [rec: royal-road-2298]. The last gap — the viewport still rendering the light scene inside the dark chrome — closed with ADR-331: `environment.js` has one dark palette, the viewport's sky is the page's `--bg` (`#141414`), so one palette spans chrome and viewport (`docs/REVIEW-DESIGN.md` §10) [rec: keen-water-3378]. The spec has been kept true as the page changed since: ADR-333 named the collision-toggle hooks in §2 rows 3 and 5 and added §11, which specifies what the viewport shows and the labelled toggle [rec: windy-rock-4850].

Charter criterion: **D1. The dashboard is one designed page.** A written design spec and a page that follows it: one dark palette across chrome and viewport, one type scale, headings that read as an academic paper's and controls that read as a modern app's, no horizontal scroll at 1400 px or 400 px. Evidence: before/after screenshots at both widths beside the spec, a browser test asserting no horizontal overflow and the palette tokens on the rendered page, and the operator URL showing the new design on the active project. Declared target `gap-d1-dashboard-one-designed-page`; the human owns the checkbox edit [rec: brisk-ledge-9638].

Reconcile judgement: `working`, held the way ot5's ticked criteria were — every evidence item the charter lists has a committed artifact or a test, and only the checkbox edit is owner-reserved. Limit: the receipts were captured on this machine over the private address, which is passed as an argument and never committed; the cap test holds that [rec: ancient-field-7584].

## Negative knowledge

None yet.

## Provenance

- brisk-ledge-9638 — the ot6 directive (ADR-328) declared this criterion as gap `gap-d1-dashboard-one-designed-page`
- ancient-field-7584 — the design spec, the measured before at 1400 and 400×850, the sliver's mechanism, the receipt-cap test
- royal-road-2298 — ADR-329: the page brought to the spec at both sizes, after screenshots and receipt on the operator URL, the rendered-page design test (retroactive record for 9a4ff012)
- keen-water-3378 — ADR-331: the viewport renders the dark scene whose background is the page's `--bg`; D1's last gap closed
- windy-rock-4850 — ADR-333: REVIEW-DESIGN.md §2 rows 3 and 5 name the new hooks; new §11 specifies what the viewport shows and the collision toggle
