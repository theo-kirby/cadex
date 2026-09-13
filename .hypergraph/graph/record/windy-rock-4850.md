---
node_id: 754831aa-85fc-59bc-b76d-6eafac75269f
slug: windy-rock-4850
title: 'The viewer shows the real model and says so: collision proxies only under a labelled toggle, the video names what it shows (ADR-333); D4''s real-biped evidence waits for D5'
created_at: '2026-09-13T23:14:40+00:00'
parents:
- brave-wave-1488
summary: ''
---
## What

The viewer shows the tessellated solids and says so; collision proxies appear only under a labelled toggle; the video names what it shows (ADR-333; D4's first unit, commit `fe181a85`). Every model manifest (`/api/model/run/<name>`, `/api/model/accepted`) now carries a `collision` block parsed with the standard library from the MJCF the view already retains at its own identity — a run's recorded `model_xml` export, refused with `digest mismatch` when the rollout trace's policy receipt names another model; the accepted attempt's `assembly.mjcf` output; the accepted attempt's for a run that borrows the accepted model — each geom in its component's frame in mm and xyzw with MuJoCo's size meaning, inline mesh assets as vertices and faces, planes and unknown types listed but not drawn, contact-free geoms counted as skipped. The shared scene module (`review_scene.js`) gains `setProxies`/`showProxies`: `--warn` outlines parented to the solid they belong to, depth test off, hidden unless shown; `stats()` reports `showing` and the counts. The page adds the checkbox **show collision geometry** (`#show-collision`, disabled with the reason when nothing is retained, the reader's choice kept across run selection, off on reload), ends the model status line with `· showing: tessellated solids[ with collision proxies (n outlines from <source>)]` (`data-showing`), and lists each component's proxies (`collision: 1 box`). `cadex_cli.video` never hands the capture proxies, refuses to publish unless the capture reports `tessellated solids`, and records `showing` and `proxies: {drawn: false, retained: n}`; the identity strip under each clip ends `· showing …`, and older recordings say `showing not recorded`. Tests: `test_collision_proxies_come_from_the_retained_mjcf_at_the_same_identity`; `test_browser_shows_solids_by_default_and_proxies_only_under_the_labelled_toggle` on a fixture whose proxies differ from its solids (the box three times the torso cube, the capsule five times the leg cube); `test_video_shows_the_solids_never_the_proxies_and_says_so` with the decoded-frame check. Docs: `docs/CLI.md`, `docs/REVIEW-DESIGN.md` §2 rows 3 and 5 and a new §11, ADR-333.

## Why

The critic named the unit: "Advance D4 next: add the visible collision-geometry toggle and video's showing field, with browser coverage on solids that differ from their proxies and a decoded-frame check. Preserve accepted-revision and historical-run identity. Defer D4's real-biped operator evidence until D5 supplies that project; do not claim D4 complete on Lark." D4 (`chilly-banner-4507`) was the highest-ranked open criterion with its predecessor D3 evidenced. Identity is preserved by construction: the proxies come from the file the run or attempt retained, never a rebuild, and a run's export is refused when the trace's receipt names another digest. The fix the critic put first — the iteration-7 record — is the parent of this one.

## Method

1. Read the scene module, page, capturer, renderer, the model routes and how `export_mjcf` names bodies (as the trace's components) and places geoms (in the body frame), and confirmed on the persistent Lark copy's `lark_model-model.xml`.
2. Wrote `collision_proxies` and wired it into the four manifest branches; `setProxies`/`showProxies`/`showing` in the scene module; the toggle, status hook, component summary and video strip in the page; the capture guard and `showing` in the renderer.
3. Fixture MJCF with proxies that differ from the cubes (and one contact-free sphere) in `_mesh_run` and `_stage_accepted`; the three tests; ran them, then `test_review_server.py`, `test_video.py`, `test_review_design.py`, `test_review_record.py`, `test_review_lifecycle.py`: **157 passed, 1 skipped** (248 s).
4. Restarted the persistent operator unit under its documented `systemd-run` command (no trainer active; the server process needed the new manifest code, the static files it already served fresh); verified it came back on `ot5-lark-copy85`. Ran a probe against the operator URL on `lark98-final` (`~/cadex-projects/ot6-look/proxies/`: `probe.py`, `receipt.json`, `operator-proxies-off.png`, `operator-proxies-on.png`, outside the repo): the collision block lists 8 geoms from `runs/lark98-final/rollout/lark_model-model.xml` (7 boxes drawn, the ground plane listed and not drawn), the status line reads `showing: tessellated solids` off and `… with collision proxies (7 outlines …)` on, the strip under the video says `showing not recorded` for the ADR-332 recording.
5. Full CLI suite on the final tree: **536 passed, 1 skipped** (the private-address test, which wants `CADEX_REVIEW_HOST`), 521 s, exit 0, under `pixi run`.

## Result

What is true now: the viewport draws the solids and says so; proxies are outlines under a checkbox labelled as collision geometry, off by default, drawn from the view's own retained MJCF; the video renderer cannot publish a frame with proxies and records what it shows; the page's identity strip names it. Measured on the fixture: off by default, the drawn pixel box grows on every side when on, proxies follow poses, each run's are its own, a run without its export disables the toggle and says why; the decoded first frame is within the codec tolerance of the shared scene with proxies hidden (error 1.1 / 255) and not with them shown (>1.5×, >1 000 outline pixels).

What D4 still owes, as the critic said: the operator URL on the real biped. On Lark the toggle draws 7 outlines and the model pixel count moves from 47 354 to 47 383 — its box proxies are the size of its box parts, so Lark cannot show the difference; D5's project can. Not claimed: D4 complete.

Assumptions recorded: MJCF bodies are named as the trace's components are and geoms are in the body frame (true of `export_mjcf`, checked on Lark's file); a plane is listed and never drawn; a geom taking part in no contact is not a proxy. No engine, protocol, payload, shell or dependency change (`xml.etree` is the standard library). The tail is now two unreconciled records on top of iteration 7's; reconcile is the next housekeeping when the critic calls it.

Dispatch closed: 1 unit — the viewer shows the real model and says so, collision proxies only under a labelled toggle, the video names what it shows (ADR-333); D4's real-biped operator evidence waits for D5.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot6
- commit: fe181a85e7a4c54f416600dec51ebba174fa66b3

## State Impact

- target: chilly-banner-4507 — D4's toggle half landed (ADR-333, fe181a85): every model manifest carries a collision block parsed from the MJCF the view retains at its own identity (a run's model_xml export, refused on a policy-receipt digest mismatch; the accepted attempt's assembly.mjcf output), the shared scene draws proxies as --warn outlines parented to their solids only while the page's 'show collision geometry' checkbox is on (off by default, disabled with the reason when none are retained), the model status line ends with what is showing (data-showing), each component lists its proxies, the video renderer never hands the capture proxies and refuses to publish otherwise, records showing, and the identity strip names it; tested on a fixture whose proxies differ from its solids (browser toggle, decoded-frame check) and shown on the operator URL on lark98-final (7 outlines from Lark's own MJCF, ground plane listed not drawn); still owed: the operator URL on the real biped, which needs D5's project because Lark's box proxies coincide with its box parts (pixel count 47 354 → 47 383)
- target: chilly-union-8972 — review_server.collision_proxies and the manifest's collision block; review_scene.js setProxies/showProxies and stats().showing/proxies; the page's #show-collision, #collision-note and #model-status[data-showing]; videos record showing and proxies.retained, the strip under each clip ends with showing; the persistent operator unit was restarted under its documented systemd-run command (no trainer active) and serves ot5-lark-copy85 with the new manifest; full CLI suite 536 passed, 1 skipped, 521 s
- target: floral-marsh-2830 — REVIEW-DESIGN.md kept true as the page changed: §2 rows 3 and 5 name the new hooks and a new §11 specifies what the viewport shows and the collision toggle
