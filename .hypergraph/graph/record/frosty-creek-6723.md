---
node_id: 067bfa95-6b91-5292-a76f-ea6b39a3c09d
slug: frosty-creek-6723
title: Solenoid 412 partial geometry passes; mounting source remains incomplete
created_at: '2026-09-06T22:12:33+00:00'
parents:
- sunny-lily-7639
summary: ''
artifacts:
- docs/experiments/solenoid_412_probe.py
---
## What

Audited Chaocheng TAU0730TM-14 through Adafruit product 412 and proved a partial nominal exterior using the existing headless OCCT engine. Added source identities, hashes, operating qualifications, conflicting travel claims and missing mounting callouts in PROVENANCE §8e; added docs/experiments/solenoid_412_probe.py, ADR-208 and a checked narrow ROADMAP audit item. No catalog API shipped.

## Why

Iteration 15 implements short-plan unit 1 from sunny-lily-7639, serving mission 4 and rising-banner-4325 / brave-stone-9609. The bounded choice was to audit a common identifiable solenoid with publicly linked supplier documents. Drawing dimensions take precedence for this experiment; missing interfaces are omitted rather than estimated from image pixels. The conditional catalog unit is not authorized by this evidence because mounting dimensions remain incomplete. Other solenoids and joints remain available; this does not block all L3.

The overseer message asks for reconciliation, but this dispatch explicitly forbids reconciliation and state writes. Its referenced L12 tail is already checkpointed; the supplied tail has one planner node. Followed the current solenoid plan without repeating L12 or editing STATE.md, PLAN.md, .ouroboros or state nodes. No human answer, GUI, remote machine or training was needed.

## Method

Read STATE.md, PLAN.md, .hypergraph/AGENTS.md, VISION.md, the actor and record skills, prior L12 evidence and source/provenance conventions. Read https://www.adafruit.com/product/412 and its supplier drawing https://cdn-shop.adafruit.com/product-files/412/412_C514-B_diagram.PDF and specification https://cdn-shop.adafruit.com/product-files/412/C514-datasheet.pdf. PROVENANCE §8e records revisions and SHA-256 hashes. PDFs were downloaded outside the repo. Poppler was unavailable and pixi lacked fitz; uv's available pymupdf rendered the drawing and all specification pages for visual inspection. No dependency files changed and no supplier assets are committed.

The source comparison and missing mounting callouts are detailed in PROVENANCE §8e. The independent box/cylinder construction explicitly marks arbitrary neck/head details, centered body and omitted mounting/coil/spring/wire geometry. Gap represents displacement away from the drawing's held state, not a force or powered endpoint prediction.

Ran build/release/bin/FreeCADCmd -c 'exec(open("docs/experiments/solenoid_412_probe.py").read())'. Checked actual cylindrical cap surfaces, bounds, cap/body material and nearby void, endpoints plus intermediate gap, and the explicit placed mapping (x,y,z) to (100+z,30+x,20+y). Invalid travel checks include negative, nonfinite and the larger product-page value.

Ran CADEX_ENGINE_ROOT=build/engine/cadex-engine-0.0.0-macos-arm64 pixi run python -m pytest src/Mod/cadex/cadex_tests/test_cadexd_lifecycle.py src/Mod/cadex/cadex_tests/test_library.py using the existing completed payload. No build/staging occurred. This documentation/experiment unit edits no engine source; the full engine suite was not run and packaged solenoid implementation is not claimed.

## Result

SOLENOID-412-PARTIAL-OK, exit 0: gap 0/2.3/4.9 mm yields valid single solids and 72 total canonical/placed material/void probes. Z bounds are [-36.5,15.4], [-38.8,13.1], [-41.4,10.5] mm; measured total length 51.9 mm and diagnostic volume 7411.834705 mm3 at all positions. X bounds [-8.5,8.5], Y [-7,7]. These numbers verify the declared approximation, not hardware fit, collision clearance, inertia or performance.

Packaged lifecycle/library baseline: 76 passed, no skips, 16.06 s, exit 0. Git diff --check passed. Graph export/check will run after minting and before the one commit. No known regression introduced.

Next: the source unit is closed with an explicit incomplete-interface result. Obtain a dimensioned mounting drawing for this exact revision or qualify another traceable solenoid before implementing a mounting-capable variant. Do not repeat the same partial model or silently scale hole positions. Catalog delivery still needs actual worker probes, source suite, one build, completed staging and packaged verification. L3 and catalog breadth remain open; no lifecycle criterion changes.

Dispatch closed: 1 unit — audit a sourced solenoid and prove its partial exterior while recording missing mounting interfaces.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/nt2
- commit: 39224263a6cafb65b9210aefa05c24b6516570f0

## State Impact

- target: rising-banner-4325 — Solenoid source/partial-geometry unit identifies TAU0730TM-14 documents and passes 72 OCCT probes; missing mounting callouts leave conditional catalog implementation and full L3 open.
- target: brave-stone-9609 — PROVENANCE section 8e and ADR-208 preserve source hashes, travel discrepancy, qualified force/duty points and explicit partial-exterior limits; no solenoid API shipped.
