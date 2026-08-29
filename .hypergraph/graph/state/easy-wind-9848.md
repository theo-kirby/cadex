---
node_id: e6afbd28-dda0-52b0-a4f1-78a5edc55779
slug: easy-wind-9848
title: Compliance and licensing
created_at: '2026-08-29T16:31:12+00:00'
parents:
- nimble-pine-0740
summary: ''
---
Status: working

## Current

The repository's compliance and licensing posture after the ADR-171 audit (PR #13, version 0.0.7) [rec: wild-sea-9905]:

- **The attribution documents exist and ship.** Root `NOTICE` (MuJoCo Apache-2.0 §4(d), OCCT LGPL + exception, FreeCAD and Blender lineage, OpenTheme, VibeCAD) and `THIRD_PARTY_LICENSES.md` (the component map: both forks, all fourteen `src/3rdParty/` dirs, the conda payload with its dual-license elections, `shell/extern`/`shell/lib`, fonts, and where each obligation lands in the bundle). Both are carried into the payload and thence `Cadex.app/Contents/Resources/cadex/` [rec: wild-sea-9905].
- **The payload ships the license texts of what it ships.** `package/engine/collect_licenses.py` harvests from the source environment on both staging paths — per-package texts under `licenses/<pkg>/` and `licenses/MANIFEST.json` (`cadex-licenses-v1`, all 341 conda packages) — and both it and `build_engine_payload.sh` hard-fail without the named obligations (OCCT exception, mujoco wheel LICENSE, NOTICE, …). The dead PySide/shiboken dylibs are pruned and gate-blocked [rec: wild-sea-9905].
- **Every file of ours names its holder** — `SPDX-FileCopyrightText: 2026 Cadex Authors` — and declares its license; the 55 pre-merge "Mesh Authors" headers are renamed. Modified inherited files carry §2(a) notices under the manifest discipline (see the inherited-tree node) [rec: wild-sea-9905].
- **Nothing of unknown origin ships**: the drone demo's seven commercial-part STLs are removed; the landing screen degrades and the demo plumbing awaits a Cadex-authored replacement (ADR-170's balance toy is the natural candidate) [rec: wild-sea-9905].
- **It is all test-held**: `test_licensing_compliance.py` (11 checks, in the engine suite and CI) plus the payload script's own assertions [rec: wild-sea-9905].

Open items, flagged in ADR-171 for the owner / counsel rather than resolved [rec: wild-sea-9905]: `libreadline` (GPL-3.0) in the conda runtime; `package/app/make_app_icon.py` declaring GPL-2.0-or-later in the LGPL tree (a relicensing decision, carried as a test exemption); LGPL §4 relinking stated structurally but not lawyered; the GPL-2-only audit across all 341 conda packages not exhaustive; Windows/Linux packaging paths unexamined (macOS-only today).

## Negative knowledge

- [scope: pre-import fork deltas | confidence: high | evidence: wild-sea-9905] Modifications made to either fork before its squashed import commit cannot be enumerated from this repository. The 2026-dated notices cover this repo's own edits; both ledgers state the bound. Do not claim completeness past the import commits.

## Provenance

- wild-sea-9905 — ADR-171: the audit, the notices, the license material that now ships
