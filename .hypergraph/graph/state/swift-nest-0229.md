---
node_id: 24999ced-c15e-59f7-88d3-3792e2cf3b41
slug: swift-nest-0229
title: D3. Autonomous runs are first-class in the dashboard (orun2)
created_at: '2026-10-03T10:54:46+00:00'
parents:
- nimble-pine-0740
summary: ''
---
Status: superseded

## Current

Open charter criterion for run orun2: **D3. Autonomous runs are first-class in the dashboard.** - The dashboard lists runs beside projects: - CLI agent turns; - Ouroboros runs (read-only from `.ouroboros/runs/<run>/` and the run branch). - Each run shows: - its iterations and critic verdicts; - the charter criteria; - the artifacts its records point to (renders, reports, probe pages). - orun1's review material (`docs/probes/orun1/`) renders in the dashboard from the repo alone. It replaces what `~/orun1-review/build.py` built by hand, which proves the per-run review pages are no longer needed. [rec: winter-stone-5109]

**Superseded: Ouroboros is out of the product (ADR-536).** The runs listing (`GET /api/runs`, `/r/<run>/`) and `cadex app --runs` are removed; no product file names Ouroboros. Nothing in Cadex replaces it: a run is read with the Ouroboros tooling, outside the repo's product [rec: still-ivy-2146].

Before removal, all six items carried browser-tested evidence: runs listed beside projects (ADR-513) [rec: mellow-otter-0798]; charter criteria from the run branch (ADR-514) [rec: polished-reef-4161]; `docs/probes/<run>/` served read-only, orun1 rendered from the repo (ADR-515) [rec: lean-star-6139]; record-linked artifacts, retiring `~/orun1-review/build.py` (ADR-518) [rec: quiet-ivy-3898]; CLI agent turns listed as runs (ADR-519) [rec: amber-moon-9415]. ADR-533 then cut the run page to charter criteria plus iterations with the critic's verdict and reason, and the index to projects newest first, 20 a page (`?page=N`) [rec: glad-wood-4169]. The pagination outlives the runs listing; the agent-turns list went with `cadex -p` (ADR-538) [rec: still-ivy-2146].

Declared target: `gap-d3-autonomous-runs-first-class`. The owner held the charter checkbox; the owner's direction of 2026-10-04 retired the criterion rather than ticking it [rec: still-ivy-2146].

## Negative knowledge

None yet.

## Provenance

- winter-stone-5109 — orun2 operator-declared charter gap
- mellow-otter-0798 — Ouroboros runs listed with iterations and critic verdicts (ADR-513)
- polished-reef-4161 — run pages show the charter's done criteria from the run's branch (ADR-514)
- lean-star-6139 — run pages serve and render docs/probes/<run>/ read-only; orun1 renders from the repo (ADR-515)
- quiet-ivy-3898 — run pages list their records and serve the docs/ artifacts they name at /r/<run>/linked/; build.py retired (ADR-518)
- amber-moon-9415 — CLI agent turns listed as runs beside the Ouroboros runs (ADR-519); all six D3 items evidenced
- glad-wood-4169 — run page cut to criteria + iterations; index paginated (ADR-533)
- still-ivy-2146 — superseded: runs listing removed, Ouroboros out of the product (ADR-536)
