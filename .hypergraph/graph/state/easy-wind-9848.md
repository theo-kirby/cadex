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

The repository's compliance and licensing posture, from the ADR-171 audit (PR #13, version 0.0.7) [rec: wild-sea-9905] as restated when the shell was deleted (ADR-498):

- **The repository carries no GPL code.** Since ADR-498 the Blender half of `docs/inherited-modifications.json` is gone (the manifest is FreeCAD-only), and `test_licensing_compliance.py` fails if a tracked source file declares a GPL SPDX header or anything is tracked under `shell/`. NOTICE, `THIRD_PARTY_LICENSES.md` and `docs/PROVENANCE.md` were rewritten to match [rec: calm-quartz-1493]. The `make_app_icon.py` GPL exemption went with that file in the disable commit [rec: lucky-haven-1081].
- **The attribution documents exist and ship**: root `NOTICE` and `THIRD_PARTY_LICENSES.md` (the component map and where each obligation lands), carried into the engine payload [rec: wild-sea-9905] [rec: calm-quartz-1493].
- **The payload ships the license texts of what it ships.** `package/engine/collect_licenses.py` harvests per-package texts under `licenses/<pkg>/` and `licenses/MANIFEST.json` (`cadex-licenses-v1`), and both it and `build_engine_payload.sh` hard-fail without the named obligations (OCCT exception, mujoco wheel LICENSE, NOTICE, …). The dead PySide/shiboken dylibs are pruned and gate-blocked [rec: wild-sea-9905].
- **Every file of ours names its holder** — `SPDX-FileCopyrightText: 2026 Cadex Authors` — and declares its license; modified inherited files carry §2(a) notices under the manifest discipline [rec: wild-sea-9905].
- **Nothing of unknown origin ships**: the audit removed the drone demo's seven commercial-part STLs [rec: wild-sea-9905]. The script-authored biped demo that replaced it (ADR-173) [rec: dawn-oak-0677] and its scrubbed `.blend` [rec: sleepy-shade-1485] lived in the shell and were deleted with it [rec: calm-quartz-1493].
- **It is all test-held**: `test_licensing_compliance.py` (in the engine suite and CI) plus the payload script's own assertions [rec: wild-sea-9905] [rec: calm-quartz-1493].

Open items, flagged in ADR-171 for the owner / counsel rather than resolved [rec: wild-sea-9905]: `libreadline` (GPL-3.0) in the conda runtime — still ADR-171's counsel item after ADR-498 [rec: calm-quartz-1493]; LGPL §4 relinking stated structurally but not lawyered; the GPL-2-only audit across the conda packages not exhaustive; Windows/Linux packaging paths unexamined.

## Negative knowledge

- [scope: pre-import fork deltas | confidence: high | evidence: wild-sea-9905] Modifications made to the FreeCAD fork before its squashed import commit cannot be enumerated from this repository. The 2026-dated notices cover this repo's own edits; the ledger states the bound. Do not claim completeness past the import commit.

- [scope: sanitizing a binary container for shipping | confidence: high | evidence: sleepy-shade-1485] A datablock container (the shell's `.blend` was the case) passes any text-file sweep while carrying a whole chat transcript and absolute machine paths. Sanitization must open the file, not just walk the store.

## Provenance

- wild-sea-9905 — ADR-171: the audit, the notices, the license material that now ships
- dawn-oak-0677 — ADR-173: the demo returns provenance-clean; the ADR-171 bar met by construction
- sleepy-shade-1485 — the transcript in the .blend, the scrub, and the open-the-file check
- quiet-creek-7756 — demo header repair, revision consistency and restore verification (the demo is gone with the shell)
- lucky-haven-1081 — ADR-495: make_app_icon.py and its SPDX exemption deleted
- calm-quartz-1493 — ADR-498: the repository carries no GPL code; licensing restated and test-pinned
