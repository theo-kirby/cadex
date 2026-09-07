---
node_id: b2624764-9d38-5b8a-82f5-6861b2f79efb
slug: red-loom-6298
title: 25T horns and servo pigtails come from manufacturer STEP sources
created_at: '2026-09-06T19:18:34+00:00'
parents:
- nimble-pine-0740
summary: ''
---
Status: superseded
## Current

Open charter criterion: **25T horns and servo pigtails come from manufacturer STEP sources**, with the provenance recorded the way `docs/PROVENANCE.md` asks. [rec: empty-wolf-3962]

**ADR-231's bounded audit qualifies neither category.** The goBILDA 1900-0025-0104 STEP is a valid single solid with mounting holes matching published pitch/reach, but exact mating compatibility and redistribution rights remain unresolved. The DS3218 archive yielded no inspectable bytes; Pololu #780 supplied no manufacturer STEP. No assets or catalog identities were added [rec: steady-reef-0162].

**Conditional delivery is closed under ADR-232.** Further candidates or importer work require a separately authorized direction. Reconcile judgement: retain **open**, since stopping this delivery bet does not satisfy the manufacturer-source criterion [rec: noble-clover-4083].

## Negative knowledge

- [scope: manufacturer horn/pigtail leads examined in ADR-231 | confidence: high | evidence: steady-reef-0162] Measured 25-fold spline surfaces do not qualify mating fit or tolerance, and the examined evidence does not establish redistribution rights. DS archive access failure establishes no content claim; the generic Pololu cable lead has no manufacturer STEP. Raw `Part.read` is not a script-owned import, and the existing mesh/.cxpart route does not establish the assumed raw STEP delivery path. No offline reopen/rebuild assurance follows.

## Provenance

- empty-wolf-3962 — operator-declared charter gap
- steady-reef-0162 — bounded manufacturer audit leaves fit, rights, source and script-owned delivery blockers
- noble-clover-4083 — ADR-232 closes conditional delivery without closing the charter gap


## Superseded

Parked by the operator before nt3 (2026-09-07). The criterion moved to `## Later criteria` in the charter, where it seeds no gap. It is not abandoned: the human promotes it back into `## Done criteria` when the nt3 frontier — the lifecycle walk and the headless review calls — lands or blocks. No evidence about the criterion itself changed.
