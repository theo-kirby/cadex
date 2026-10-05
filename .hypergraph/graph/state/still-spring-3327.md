---
node_id: c23b6445-8a7b-5d24-bf40-737efb9e541c
slug: still-spring-3327
title: P1. The dashboard is portable
created_at: '2026-10-05T08:57:46+00:00'
parents:
- nimble-pine-0740
summary: ''
---
Status: open

## Current

Open orun3 charter criterion: **P1. The dashboard is portable.** [rec: golden-snow-6627]

- No page script or server-built URL is root-absolute. Every fetch and every link resolves relative to the page, or through one API base. The page works unchanged behind a path prefix: a test serves it under `/some/prefix/` through a rewriting-free proxy and loads a project. [rec: golden-snow-6627]
- The HTTP API is a documented contract. Every `GET /api/...` route and its top-level response keys are listed in `docs/CLI.md`, or in one file it points to. A test fails if a route is added, removed or renamed without the doc changing too, in the same way the `OP_ARG_SPECS` test works. [rec: golden-snow-6627]
- No page state lives only in the browser, except per-viewer conveniences such as the layout, the theme and a collapsed overlay. [rec: golden-snow-6627]

Declared target: `gap-p1-dashboard-portable-no-page`. This node tracks the criterion as a gap; it becomes working only with measured evidence, in a causally parented record, that the criterion is met. The owner ticks the charter box; roles do not. Truncated impact wording is resolved from the full charter in the same record [rec: golden-snow-6627].

## Negative knowledge

None yet.

## Provenance

- golden-snow-6627 — operator-declared orun3 charter gap (gap-p1-dashboard-portable-no-page)
