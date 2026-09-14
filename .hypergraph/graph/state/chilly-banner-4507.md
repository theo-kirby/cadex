---
node_id: 2e88fecf-ea5f-515e-93bf-304dbce1c3a9
slug: chilly-banner-4507
title: D4. The viewer shows the real model, and says so
created_at: '2026-09-13T21:25:09+00:00'
parents:
- round-sun-8398
summary: ''
---
Status: working

## Current

**D4's evidence list is complete pending the owner's tick (ADR-333, ADR-334).** *The toggle half* (ADR-333, commit `fe181a85`) [rec: windy-rock-4850]: every model manifest (`/api/model/run/<name>`, `/api/model/accepted`) carries a `collision` block parsed with the standard library (`xml.etree`) from the MJCF the view already retains at its own identity — a run's recorded `model_xml` export, refused with `digest mismatch` when the rollout trace's policy receipt names another model; the accepted attempt's `assembly.mjcf` output; the accepted attempt's for a run that borrows the accepted model — each geom in its component's frame in mm and xyzw with MuJoCo's size meaning, inline mesh assets as vertices and faces, planes and unknown types listed but not drawn, contact-free geoms counted as skipped. The shared scene module `review_scene.js` draws proxies as `--warn` outlines parented to the solid they belong to (`setProxies`/`showProxies`, depth test off) only while the page's checkbox **show collision geometry** (`#show-collision`) is on — off by default and on reload, the reader's choice kept across run selection, disabled with the reason when nothing is retained; the model status line ends with what is showing (`data-showing`: `showing: tessellated solids[ with collision proxies (n outlines from <source>)]`) and each component lists its proxies. `cadex_cli.video` never hands the capture proxies, refuses to publish unless the capture reports `tessellated solids`, and records `showing` and `proxies: {drawn: false, retained: n}`; the identity strip under each clip ends `· showing …`, and older recordings say `showing not recorded`. Tested on a fixture whose proxies differ from its solids (the box three times the torso cube, the capsule five times the leg cube, one contact-free sphere): the browser toggle test — off by default, the drawn pixel box grows on every side when on, proxies follow poses, each run's are its own, a run without its export disables the toggle and says why — and the decoded-frame check, within codec tolerance (1.1/255) of the shared scene with proxies hidden and not with them shown (>1.5×, >1 000 outline pixels). On the operator URL on `lark98-final` the toggle drew 7 outlines from Lark's own MJCF with the ground plane listed and not drawn, but Lark's box proxies coincide with its box parts (model pixel count 47 354 → 47 383), so Lark could not show the difference. Full CLI suite on that tree **536 passed, 1 skipped**. *The real-biped half* (ADR-334, commit `ed5b158a`) [rec: sleepy-rain-9945]: on the operator URL serving `ot6-finch` the labelled toggle moves the model pixel count from 61 665 to 62 492 with 20 outlines from the accepted attempt's `finch_model` export, the pelvis proxy spanning the open bay and the cheek proxies spanning their windows, so the outlines visibly stand off the solids (`docs/probes/ot6/finch/operator-solids.png`, `operator-proxies.png`). Docs: `docs/CLI.md`, `docs/REVIEW-DESIGN.md` §2 rows 3 and 5 and §11, ADR-333.

**The owner ticked D4 on 2026-09-14 with the evidence unchanged; it holds as worded** [rec: nimble-wing-3050].

Charter criterion: **D4. The viewer shows the real model, and says so.** The dashboard viewport and the videos render the accepted revision's tessellated solids, never the collision proxies, unless a visible toggle labelled as collision geometry is on; the video's identity strip names what is shown. Evidence: a browser test toggling proxies on a project whose proxies differ from its solids, a decoded video frame check, and the operator URL on the real biped. Declared target `gap-d4-viewer-shows-real-model`; the human owns the checkbox edit [rec: brisk-ledge-9638].

Reconcile judgement: `working`, held the way ot5's ticked criteria were — each of the charter's three evidence items has a committed test or receipt, and only the checkbox edit is owner-reserved. Identity is preserved by construction: proxies come from the file the run or attempt retained, never a rebuild. The assumptions the implementation rests on, as recorded: MJCF bodies are named as the trace's components and geoms are in the body frame (true of `export_mjcf`, checked on Lark's file); a plane is listed and never drawn; a geom taking part in no contact is not a proxy. No engine, protocol, payload, shell or dependency change [rec: windy-rock-4850].

## Negative knowledge

- [scope: Lark as evidence that the toggle shows something different from the solids | confidence: high | evidence: windy-rock-4850] Lark's box proxies are the size of its box parts, so on Lark the toggle moves the pixel count by 29 and the outlines lie on the solids; the real-biped evidence had to come from Finch (`cool-hill-9617`).

## Provenance

- brisk-ledge-9638 — the ot6 directive (ADR-328) declared this criterion as gap `gap-d4-viewer-shows-real-model`
- windy-rock-4850 — ADR-333: the manifest's `collision` block from the retained MJCF at the view's own identity; `--warn` outlines under the labelled checkbox, off by default; `data-showing` status and per-component proxy counts; the video renderer refuses proxies and records `showing`; fixture browser toggle and decoded-frame tests; Lark on the operator URL (7 outlines, 47 354 → 47 383); CLI 536 passed / 1 skipped; real-biped evidence deferred to D5
- sleepy-rain-9945 — ADR-334: the operator URL on `ot6-finch`, 20 outlines, 61 665 → 62 492 px, outlines visibly standing off the solids; D4's evidence list complete pending the owner's tick
- nimble-wing-3050 — the owner ticked D4 on 2026-09-14; evidence unchanged
