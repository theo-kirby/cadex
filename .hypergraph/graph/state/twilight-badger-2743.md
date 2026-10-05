---
node_id: 03ba7974-2810-527c-a2c0-6a53625ffbeb
slug: twilight-badger-2743
title: C1. Closing report
created_at: '2026-10-05T08:57:46+00:00'
parents:
- nimble-pine-0740
summary: ''
---
Status: working

## Current

orun3 charter criterion: **C1. Closing report.** `docs/probes/orun3/REPORT.md` must cover V2's training-cost and disk measurements, V3's bytes-per-revision, every ADR the run added, W1's screenshots (PNG, ≤300 KB, dark floor), and the remaining defects; then reconcile and claim done for critic review without ticking owner boxes. Declared target `gap-c1-closing-report-docs-probes`. [rec: golden-snow-6627]

**Status judgement (maintainer):** flipped to `working` — the report exists with every required section; done is claimed for critic review and the owner holds every checkbox. The "reconcile" step the charter names is this pass. [rec: damp-wave-8696]

- `docs/probes/orun3/REPORT.md` exists (verified at `0b1e5264`): a criterion table with records for V1–V4, P1, W1, C1, and §1 V2 cost/disk, §2 V3 bytes, §3 W1's ten `w1-*.png` with sizes, §4 ADR-542..553, §5 remaining defects, §6 done claim. Figures copied from their source records, not re-measured. [rec: damp-wave-8696]
- **V2:** +0.08% mean iteration wall time with rollouts on (under the 5% bar); 38.7–329.5 KB per trace, 224.7 KB mean, 2.47 MB for 11 checkpoints. [rec: damp-wave-8696]
- **V3:** ≈3,925 B per kept revision including its index row vs ≈11,400 B for a full copy (nine revisions: 35,327 B vs 102,612 B). [rec: damp-wave-8696]
- **Remaining defects listed:** (1) final-policy stop missing on a never-reloaded page; (2) the evaluating line names the evaluation directory; (3) progress stalls 37–39 s before each checkpoint. Also open: four unrebuildable stale-policy revisions, and the unworked long-term rungs (phone width, light theme, binary meshes). [rec: damp-wave-8696] [rec: soft-comet-8840]
- `test_project_docs.py` + `test_licensing_compliance.py`: 39 passed, 1 skipped; no code changed. [rec: damp-wave-8696]

## Negative knowledge

None yet.

## Provenance

- golden-snow-6627 — operator-declared orun3 charter gap (gap-c1-closing-report-docs-probes)
- damp-wave-8696 — report written, done claimed for critic review
- soft-comet-8840 — source of W1 figures and two of the three remaining defects
