---
node_id: 09b6c0c7-8466-5ca4-a705-4c273c922e04
slug: round-sun-8398
title: Real models, reference-grade review — the ot6 charter (ADR-328)
created_at: '2026-09-13T21:24:59+00:00'
parents:
- nimble-pine-0740
summary: ''
---
Status: open

## Current

**Owner-directed work for run `ot6` (ADR-328): make what ot5 built worth looking at — the review dashboard, the rendered look, the model itself, then the range of mechanisms, in that order [rec: brisk-ledge-9638].** It replaces the ot5 charter (ADR-284), whose D1–D11 the owner ticked on 2026-09-13 (`crisp-sun-1239`, [rec: patient-pond-3886]). Nothing here is a new leg of the north star; it is the quality bar the existing legs must meet before print-ready export or the unattended robot prompt can be worth doing. What the owner saw at ot5's close: a dashboard that is a stack of cards in dark chrome around a light viewport and collapses at phone width; videos in a light scene with the subject small and the camera far, unlike the `neural-whoop` reference; and a biped, Lark, that is `part.box` everywhere, box collisions and a cyan ground slab that is itself part of the design — not a robot anyone could build.

The owner's fixed choices, not open to actor interpretation [rec: brisk-ledge-9638]:

- **Dashboard first.** One designed page under a written spec (`docs/REVIEW-DESIGN.md`): academic but modern, one type scale and one dark palette across chrome and viewport, a clear hierarchy (project and current run, model, curves, videos, history), readable on a phone and orbitable by touch [rec: brisk-ledge-9638].
- **Look second.** Viewport and videos match the read-only sibling `neural-whoop` checkout, **dark only**: the near-black grid mat with PROTOTYPE / 1 METER labels and subject-scaled pitch, a camera tracking the subject at a declared framing fraction, fog, grounded contact shadows, antialiasing and the timer overlay, from one environment module shared by viewport and capture. The light palette goes. Cadex's renderer stays self-contained, provenance recorded as `cli/cadex_cli/review_static/REFERENCE-LICENSE.txt` already does [rec: brisk-ledge-9638].
- **Model third.** Every model this run designs is built from catalog hardware — the **MG90S** from `lib.servo` as the standard actuator, catalog horns, bearings and fasteners — and modelled printable parts that mount them (servo pockets with declared clearance, horn attachments, shafts through bearings). The real tessellation is what the viewer shows; collision proxies only under a labelled toggle. Nothing of the world (floor, walls) is part of the design [rec: brisk-ledge-9638].
- **Range fourth.** The product agent designs a two-wheeled balancing robot and a single servo arm the same way, each through the full recorded lifecycle (train, record, review) on the dashboard. Poor performance is a valid measured result; box parts, missing hardware or skipped training are not [rec: brisk-ledge-9638].
- **ot5's operator-dashboard rules stand:** one project per server, inspection only, the persistent URL serves the project and run being worked on, kept running between iterations, verified on every experiment start and end [rec: brisk-ledge-9638].
- **Two rules from ot5's digest:** committed evidence receipts are capped at 16 KB (screenshots 200 KB) with dumps left in the project directory, and no private-network address or hostname is committed. Exhaustion policy is `report_done`, not repeat [rec: brisk-ledge-9638].

The ten done criteria D1–D10 are child state nodes (`floral-marsh-2830`, `western-journey-2108`, `silver-ledge-4640`, `chilly-banner-4507`, `cool-hill-9617`, `dusty-otter-7562`, `ready-sand-2621`, `civic-creek-8215`, `civic-lily-1239`, `chilly-road-8573`); a record may say "ticks Dn" when its evidence exists, and the human owns the checkbox edit. Reconcile judgement: this umbrella mirrors `crisp-sun-1239` for ot5 — the directive declared only the ten criterion targets, and the umbrella is the architecturally right parent for them rather than the state root [rec: brisk-ledge-9638].

**Where the run stands (2026-09-14, after D9's final assessment).** D1–D9 each carry evidence pending the owner's tick; D10, the closing report, is the only criterion without evidence [rec: bold-arbor-2078]. D7 (Robin, the two-wheeled balancing robot) and D8 (Heron, the two-DoF arm) each carry a full recorded lifecycle — product-agent design, inventory and fit check, one bounded training run, a seed-set measurement, checkpoint and final videos in the D3 look on the operator URL [rec: mild-hill-0753] — and D9's final regression assessment was taken on the tree after both closed, both suites green [rec: bold-arbor-2078]. Two rules D8 added: a fit check reads only the published clearance pairs, because the engine accepts scripts whose stdout contradicts them [rec: narrow-quill-3259]; and the operator service is on Heron (`ot6-heron`, fresh-visit default `heron1-final`), moved from Robin under the one-project-per-server rule, Robin's runs remaining retrievable by pointing the service back [rec: narrow-quill-3259] [rec: mild-hill-0753]. The reconcile the charter schedules before D10 is this pass, over the three-record tail `narrow-quill-3259`, `mild-hill-0753`, `bold-arbor-2078` [rec: bold-arbor-2078]. Reconcile judgement: no pending impact targets `ready-sand-2621`; the critic's earlier request to correct it through reconciliation (relayed in narrow-quill-3259) finds the D7 node already reading as the evidenced lifecycle with reward tuning left as an open design decision, so it is unchanged this pass.

## Negative knowledge

None yet.

## Provenance

- brisk-ledge-9638 — the ot6 operator directive: the charter (ADR-328) verbatim, the ten criteria declared as gaps
- patient-pond-3886 — the ot5 closure this charter follows from, and the digest lessons it carries as rules
- narrow-quill-3259 — ADR-339: D8's design half, Heron accepted after three measured corrections; the fit-check rule and the operator service's move to Heron
- mild-hill-0753 — ADR-340: D8's training half; D7 and D8 each a full recorded lifecycle, the frontier D9 then D10
- bold-arbor-2078 — D9's final assessment; D1–D9 evidenced pending the owner's tick, D10 the only criterion without evidence
