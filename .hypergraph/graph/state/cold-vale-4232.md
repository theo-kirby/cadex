---
node_id: 9220fe11-e411-5d55-a2a3-53e57c5dd269
slug: cold-vale-4232
title: D7. Save-As/copy produces an independent project
created_at: '2026-09-12T14:51:25+00:00'
parents:
- crisp-sun-1239
summary: ''
---
Status: working

## Current

**D7 is repeated on the third fresh project, Lark, including the retraining half.** `ot5-lark` was copied whole to `ot5-lark-copy85` after a pre-copy SHA-256 inventory with no writer active; the persistent port 8765 service was deliberately switched to the copy; and with the original path renamed away for the whole pass, the public CLI changed only the copy (`foot_len` 80→90 mm, `policy_on` 1→0, accepted `083d086ad980…` against the original's unchanged `ca88f223b54c…`), two fresh engine processes restored it with retained bytes unchanged, and a separately started server and the persistent one returned identical per-run identities, mesh hashes and four playable, hash-equal-downloadable videos across all six retained runs. The copy's 250 retained run/asset files and all 1,852 original files were byte-identical to their inventories, checked by the driver and again independently; the driver `docs/probes/lark-fresh/copy_lifecycle.py` is project-agnostic and its receipt is test-guarded (ADR-314) [rec: warm-falcon-0420]. The copy then took two real training attempts, a policy declaration and a rendered video, after which the original `ot5-lark` (1,419 files excluding `.git`) was still byte-identical to its pre-experiment inventory, checked by the driver and once more independently [rec: scarlet-ocean-2381]. The copy is the working project.

**Wren independently repeats the copy/edit/reopen/review portion.** With the original path unavailable, the whole-project copy accepts an isolation-only public-CLI 105→110 mm foot edit with policy disabled, restores through two fresh engine processes and passes review on a second server and the persistent private URL; six retained models/curves and four videos retain identity, polling playback and hash-matching downloads; all 1,566 original files and 232 copied run/asset files remain byte-identical [rec: crimson-bell-5375]. Wren copy training preserved 294 and then 362 prior run files and 963 original non-git files, with new policies retained only in the copy; the original path was available during those GPU attempts [rec: small-wind-0172] [rec: fair-garden-6418].

**Real Reed copy/edit/GPU retraining and source-unavailable reopen first proved D7.** A stopped-writer whole-directory copy matched all 1,206 source files; the copy alone received a disclosed actor-applied 90→100 mm foot revision, fresh 240-iteration GPU training and a verified final video; with the original temporarily unavailable, real engine reopen preserved accepted identity and a new private-address dashboard passed three-design (70/90/100 mm) browser checks. All 1,206 original files and 322 inherited run/asset files remained unchanged [rec: clever-fern-7568]. The earlier fixture established copied historical review and original isolation [rec: careful-gate-4868].

Judgement: `working`. Three fresh projects show whole-project copies edited, reopened, reviewed and (Reed, Wren, Lark) retrained without touching the original. Temporary path unavailability does not imply OS-wide denial of access to the renamed source; the owner's checkbox is not edited [rec: warm-falcon-0420] [rec: scarlet-ocean-2381]. **The owner ticked D7 in the charter on 2026-09-13 after run ot5 stopped at iteration 111; the criterion is closed for ot5 with its evidence unchanged, and ot6's charter (ADR-328) supersedes it [rec: patient-pond-3886].**

## Negative knowledge

The copy procedure requires authoring, training and rendering to stop first; it is not atomic and external symlinks remain outside its contract. The original was renamed temporarily, not deleted, and was unavailable by path rather than by every filesystem route. Browser evidence is same-machine private-address access, not a second-device test. Copy100's seed-0 fall at 0.62 seconds is not a ten-seed comparison or evidence of gait improvement; the quota-refused product-agent request led to an explicitly disclosed actor fallback [rec: clever-fern-7568] [rec: warm-falcon-0420].

## Provenance

- lucky-comet-0031 — the ot5 directive declared this criterion as gap `gap-d7-save-as-copy-produces`
- dusty-peak-9330 — the owner's charter revision (ADR-284) that introduced D1–D9, claiming none complete
- careful-gate-4868 — browser copy-isolation fixture and documented procedure; real biped copy/edit/retraining remains open
- clever-fern-7568 — real independent copy revision, GPU retraining, verified video and source-unavailable engine/browser reopen close D7
- crimson-bell-5375 — Wren isolated copy edit, two restores and independent browser reviews with original path unavailable
- small-wind-0172 — copy-local training preserves original and prior run files; overlap disclosed
- fair-garden-6418 — clean sequential repeat preserves 362 prior run files and 963 source files
- warm-falcon-0420 — Lark whole-project copy served on the persistent URL, edited and restored with the original unavailable, reviewed identically on two servers, original byte-identical (ADR-314)
- scarlet-ocean-2381 — the original ot5-lark byte-identical after the copy's two training attempts, declaration and video (ADR-315)
- patient-pond-3886 — the owner ticked D7 on 2026-09-13 after run ot5 stopped at iteration 111; evidence unchanged
