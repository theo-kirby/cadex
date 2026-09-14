---
node_id: 565b8db1-f390-523b-832d-3c9f7150d614
slug: narrow-quill-3259
title: 'Heron: the product agent''s two-DoF MG90S arm accepted after three measured corrections, fit-checked, reopened and on the dashboard (D8 design half)'
created_at: '2026-09-14T04:16:46+00:00'
parents:
- candid-delta-9314
summary: ''
---
## What

D8's design half: Heron, a two-DoF MG90S servo arm, designed by the product agent from one prompt in the fresh external project `ot6-heron`, corrected three times by the same agent against measurements the actor quoted back to it, accepted at revision `9c1f2fe7ea19…` (digest `f9be3985bc55…`), inventoried and fit-checked (55 of 55 rules on 105 measured pairs plus three section cuts), reopened in five fresh processes at the accepted digest, and served on the persistent operator dashboard at 1400×900 and touch-emulated 400×850 with its real tessellated solids. Receipts under `docs/probes/ot6/heron/` (README.md, design.json, fit.json, reopen.json, operator.json, two screenshots, fit_check.py, operator_probe.py), ADR-339, and a receipt test in `cli/tests/test_review_design.py`. Commit `bb215890`.

## Why

The critic named this unit: proceed to D8 (`civic-creek-8215`), prompt the product agent to design a fresh two-DoF MG90S arm with catalog horns, bearings and fasteners, modelled base and links, inventory and measured fits; accept and verify fresh-process reopening; show its real solids on the persistent dashboard at both widths; training as its own bounded unit. The critic's first line asked for `ready-sand-2621` to be corrected through reconciliation, but the tail is empty and D7's node already reads as the evidenced lifecycle with reward tuning not a blocker, and reconcile is forbidden in a work iteration; nothing was done there. Everything else followed the message. Training was not started.

## Method

- Start-of-experiment check: the persistent URL served Robin's `robin2-final` at both widths (receipt in `ot6-heron-src/iteration24/start`).
- One design prompt (9,648 bytes) modelled on Robin's: catalog datums, the parent/child joint module in words, a grounded base, the forearm frame at the tip, a fixed-target reach task with `assembly.disturbance` pushes for per-seed variation (a grounded mechanism refuses `reset_variation`), verification through inspect facts. `./cadex --project … --json -p` under `timeout 1800`, model the CLI default (claude-fable-5); the turn took 24 min, exit 0, eight script-history entries (three catalog probes, two horn/servo orientation probes, the mechanism, and later the three corrections).
- The engine accepted the first mechanism. The retained clearance table and dynamics export disagreed with the script's own stdout on three points, each sent back as a `--resume` turn quoting the measurement: (1) `assembly.collision("plane")` on the base — the engine supplies a floor only to a free base (ADR-335), the charter forbids world geometry in a design; (2) 248.2016 mm³ common volume between each servo and its cheek, exactly (32.5−23.4)×12.2×2.4 − 2π·1.1²·2.4, the tab plate outside the window minus its holes: the cheek's outer face had been placed at the tab plate's spline-side face; (3) 0.2 mm child/horn distance: the pocket cleared the horn on its floor too, so the horn met nothing until the centre screw closed the modelled side gap. The agent made each correction itself and submitted the whole script; each is an ADR line in the project's `DECISIONS.md`. Turns took 3, 6 and 4 minutes, all exit 0.
- `fit_check.py`, derived from Finch's: per joint tab seat 0/0, horn pocket 0/0, horn on spline 0/0, bearing press 0/0, stub 0.1 mm radial in the bearing, centre-screw spline engagement π·1²·3.0 = 9.4248 mm³, tab-screw cheek engagement π(1²−0.8²)·3.6 = 4.0715 mm³, the stub's nearest cheek approach the 0.6 mm lip-hole clearance; window clearance 0.30 mm from the XZ section through the cheeks' mid-plane; side gap 1.00 mm from XY sections 5.3 mm above each axis (an exact 6 mm lands on a tessellation edge and the cut reports `unsupported` — worked around by offset, not changed); no other intersection, no plane geom, no initial proxy contact, base the only grounded component, two limited hinges, valid single solids, solved, task as declared. Masses: printed 86.6 g, purchased 33.0 g, total 119.5 g. Writes the project's `docs/INVENTORY.md` and `docs/FIT.md`.
- Reopen: five `cadex section` runs (XZ −16.5, XY 46, XY 126, XY 45.3, XY 125.3), each a fresh process through the restore pass that refuses on digest mismatch (Robin's first-revision failure mode); all exit 0 at the accepted revision, one digest.
- Dashboard: `systemctl --user stop`, `systemd-run --user --unit=cadex-operator-review … review --project ot6-heron --host $(tailscale ip -4) --port 8765`; `operator_probe.py` at both widths: `accepted` selected, 15 components, 29,234 triangles, `showing: tessellated solids`, 20 proxy outlines under the labelled toggle, no horizontal overflow; screenshots quantised under the 200 KB cap.
- Tests: `test_heron_design_receipt_is_a_buildable_arm_on_the_operator_url` added; the parametrised cap/privacy gate covers the new files (96 passed in the selection); full CLI suite 597 passed, 1 skipped (526 s). Engine suite not re-run: no engine code changed.

## Result

- **D8 has its design half**: a product-agent arm on catalog MG90S, horns, MR128 bearings and M2 screws with three modelled printed parts, a per-solid inventory with masses and proxy relations, a fit check that every servo sits in its window at the declared clearance, every tab plate seats on its cheek, every horn meets its link and its spline, every stub turns in its bearing at the declared clearance; no floor, bench or wall in the design; fresh-process reopen holds; the persistent URL serves it at both widths. **What remains for D8**: one bounded training run with checkpoint and final videos in the D3 look and the reach (tip-to-target at episode end and over the final second, within `reach_tol` 10 mm) measured over seeds 0–9. Poor reach is a valid result.
- **Finding worth keeping**: the engine accepts mechanisms whose stdout claims contradict their own retained clearance pairs; the acceptance gate does not read a script's fit claims. A fit check must read the published measurements, never stdout. Three such contradictions in one design.
- **Finding, engine**: for a grounded mechanism the export has no environment floor (`environment: None`), by ADR-335's design; a grounded arm's only bench is its termination channel. Any future arm task that needs the tip to collide with the bench would need the environment floor extended to grounded exports — an engine unit, not taken here.
- Assumptions: the reach task's target is fixed across episodes (the prompt asked for this and the agent stated it); per-seed variation is the two forearm pushes only. The default dashboard view is from the bearing side, so the servo cases are partly hidden behind the cheeks; orbit shows them, no screenshot of that was taken.
- The operator service is on Heron (one project per server, the project being worked on); Robin's project is untouched and its runs remain retrievable by pointing the service back.
- Reconcile: the tail was empty at the start of this iteration; this record is the first unreconciled node. The critic's request to correct `ready-sand-2621` through reconciliation is for a reconcile pass, not this one.
- No new dependency. No product code or protocol change. No engine build.

Dispatch closed: 1 unit — Heron, the product agent's two-DoF MG90S arm, accepted after three measured corrections, fit-checked, reopened and served on the operator dashboard at both widths (ADR-339, D8 design half).

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot6
- commit: bb215890cfce4df436fd1d343a41a3c0aa40b877

## State Impact

- target: civic-creek-8215 — D8's design half is evidenced (ADR-339): Heron, the product-agent arm in ot6-heron, accepted at 9c1f2fe7ea19 with 55/55 fit rules on the retained pairs, five fresh-process reopens at the accepted digest, and the persistent dashboard serving its real solids at both widths; open for the bounded training run and the measured reach
- target: round-sun-8398 — D8 gains its design evidence; a fit check reads only the published clearance pairs because the engine accepts scripts whose stdout contradicts them; the operator service moved from Robin to Heron
- target: calm-peak-5247 — a grounded mechanism exports with no environment floor (ADR-335 is free-base only); an arm's bench is its termination channel unless the floor is extended to grounded exports, an engine unit not taken
