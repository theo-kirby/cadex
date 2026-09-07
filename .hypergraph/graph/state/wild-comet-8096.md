---
node_id: 9e164834-49a7-5a54-b176-5130bf494381
slug: wild-comet-8096
title: The `hide_render` shell bug from `docs/IDEAS.md` is fixed
created_at: '2026-09-06T19:18:34+00:00'
parents:
- nimble-pine-0740
summary: ''
---
Status: working

## Current

**The `hide_render` shell defect is fixed with a regression that fails on the old source**, meeting the declared charter criterion [rec: civic-moss-7263]. Actual hydration and headless EEVEE first reproduced raw-source leakage; the source/ordinary/posed pixel bands changed from 1024/1024/1024 to 0/1024/1024 after the fix [rec: sunny-canyon-1138] [rec: civic-moss-7263].

`cadex_hydrate` hides instanced source solids and edge companions from camera renders, owning only false-to-true render changes independently of viewport markers. Regression covers repeat hydration, component removal and restoration, renderable posed components, pre-hidden sources and unrelated explicit visibility. The full headless gate passed with `ok true`, bundled engine, 372/372 picks and slider median 0.527 s against 0.65 s [rec: civic-moss-7263].

This closes the source-code criterion only: the gate reloads source application code, the installed startup copy was not refreshed, and general headless review/video criteria remain open [rec: civic-moss-7263].

## Negative knowledge

- [scope: assembly source visibility restoration | confidence: high | evidence: sunny-canyon-1138, civic-moss-7263] Legacy viewport restoration remains unchanged and can lose a source's prior viewport hide. Independent render ownership preserves pre-hidden sources, but a manual render hide while the hydrator already owns a true flag remains ambiguous.

## Provenance

- empty-wolf-3962 — operator-declared charter gap
- sunny-canyon-1138 — reproduced camera leakage and qualified independent render ownership
- civic-moss-7263 — landed fix, old-source-failing regression and full headless gate; criterion working with installation and visibility limits
