---
node_id: a4592539-95a3-58b8-a8e1-6b767f6a7e0e
slug: wild-sea-9905
title: 'ADR-171: Compliance and Licensing — the audit, the notices, and the license material that now ships'
created_at: '2026-08-29T16:19:29+00:00'
parents:
- gilded-trail-2519
summary: ''
artifacts:
- docs/inherited-modifications.json
- NOTICE
- THIRD_PARTY_LICENSES.md
---
## What

A three-way release-readiness audit of the repository's compliance and
licensing posture (docs/claims vs disk, packaging/dependencies,
inherited-tree deltas), and the eight-commit PR that fixes what it found —
branch `compliance-and-licensing`, ADR-171, version 0.0.7.

## Why

Three documents asserted a NOTICE file that did not exist; the payload
prune deleted the license texts of what it ships (153 OCCT dylibs with no
LGPL or exception text anywhere in the artifact); ~90 modified inherited
files carried no LGPL-2.1/GPL-2 §2(a) changed-file notice; PROVENANCE
claimed eight files were the entire Blender delta (it is ~43) and that the
conda dependencies stay on the build machine (they ARE the payload);
CONTRIBUTING/CODE_OF_CONDUCT were FreeCAD's verbatim; 7 STLs of real
commercial parts shipped in the demo with no recorded origin; and no
automated check guarded any of it.

## Method

Audit first (three sweeps, every claim traced to disk), then owner
decisions via three questions (demo STLs: remove; holder: "Cadex Authors";
notices: per-file + manifest + test), then eight commits, each verified:
root docs + docs/inherited-modifications.json (90 files: 47 FreeCAD, 43
Blender, one `premodified`); tools/apply_modification_notices.py (--check
/ --write, 81 comment notices, 9 FreeCAD files ledger-only after
formatter fights); the Cadex Authors sweep (~250 files); 
package/engine/collect_licenses.py harvesting from the SOURCE env on both
staging paths + payload assertions + dead PySide/shiboken prune
(otool-verified unlinked); demo removal with graceful landing-screen
degrade; recipe.yaml about: + NSHumanReadableCopyright;
test_licensing_compliance.py (11 checks, incl. manifest==git-diff equality
against both import commits and a CADEX_ENGINE_ROOT-gated payload check).

## Result

`pixi run test-engine` 1920 passed / 47 skipped; cli/tests 83 passed;
packaged lifecycle gate 14/14 against the staged payload; the payload now
carries licenses/MANIFEST.json (341 packages), OCCT LGPL + exception,
FreeCAD LICENSE.html, the mujoco wheel LICENSE (asserted by name, no
longer a glob accident), and root LICENSE/NOTICE/THIRD_PARTY_LICENSES.md;
pre-commit clean on every touched inherited file. Flagged, not resolved:
libreadline (GPL-3.0) in the conda runtime; make_app_icon.py's GPL header
in the LGPL tree; pre-import fork deltas unreconstructible (stated as a
bound in both ledgers).

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: compliance-and-licensing
- commit: 46594414da89270185e7c4da01b02502fff9fd64

## State Impact

- target: NEW compliance-and-licensing — the repo's compliance posture after ADR-171: NOTICE + THIRD_PARTY_LICENSES exist and ship; 90 modified inherited files manifested (docs/inherited-modifications.json) and noticed; the payload stages per-package license texts + MANIFEST.json; test_licensing_compliance.py holds it all; open counsel items: libreadline GPL-3, make_app_icon.py's GPL header, pre-import fork deltas
- target: round-glacier-2865 — the inherited-tree delta is now machine-pinned: any new edit to an inherited file fails test_licensing_compliance until manifested, noticed and ledgered; §2a's eight files are test-enforced for both forks
