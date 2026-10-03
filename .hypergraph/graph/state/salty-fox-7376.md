---
node_id: 545132fc-9826-5329-a325-301574ba8635
slug: salty-fox-7376
title: D4. Plain prompts produce designs that clear the owner's bar (orun1)
created_at: '2026-10-02T17:02:00+00:00'
parents:
- nimble-pine-0740
summary: ''
---
Status: working

## Current

Open charter criterion for run orun1: **D4. Plain prompts produce designs that clear the owner's bar.** - **Plain prompts, frozen before generation** in the README: one per type (quadruped, hexapod, biped, 5-axis arm, 3-axis arm, two-wheeled balancer, and one wildcard of the agent's choosing). Each names the type, its joint count, "design only" and nothing about style. The style must come from the product's guidance, not the prompt. - Each design is a fresh `orun1-*` project at the final product revision. It is accepted, its static and swept fit pass, its purchased parts are all from the catalog, and every one of them passes D3's mounting check. - **The bar, judged by D1's frozen version** that met the held-out bar: - each new design wins the majority of its pairwise comparisons against the sweep designs of the same type that the owner rated Like or Love; - the new hexapod is held to the same bar, with no exemption. - **Confirmation, not fishing.** One pre-registered confirmation turn per type at the final revision counts. Every earlier attempt is published. A second confirmation of a type needs a recorded product change between the two. - The final set (hero, concept sheet and the judge's result for each) is committed under `docs/probes/orun1/final/` for the owner to review. [rec: sweet-brook-2725]

Declared target: `gap-d4-plain-prompts-produce-designs`. The human owns the charter checkbox; roles report results and do not tick it. Reconcile judgement: earlier runs have criteria with the same letters, so every orun1 gap title carries the run.

**Prompts frozen before any generation** (commit `bd3bbb0d`): seven plain prompts in `docs/probes/orun1/runner/prompts.py` (sha256 `f69ab5c8…`), quoted in the README and held equal by `runner/test_prompts.py`; no style words (test-checked); wildcard fixed as an 8-joint snake; turn settings frozen as `claude-opus-5-5`, effort `medium`. `runner/versus.py` is the frozen-v2 bar: it judges a new design against the same-type sweep Likes/Loves and refuses to run unless opponent heroes hash to the ones D1 judged [rec: spring-ivy-9833].

**Trial 1 (not a confirmation; counts for nothing toward D4)** — `orun1-t1-balancer`, accepted revision `8dd43825…`, faceless: mounting `pass` 9/9 held, all parts from the catalog, static fit 861 pairs 0 failing; **swept fit `incomplete`** (4.26 mm³ between the turning wheel bore and the catalog gearmotor's static D-shaft at ±180°); frozen v2 **3 of 5** (beat d, f, h Likes; lost to c Love and e Like, both citing plain solid-disc wheels with no hub). Published in `docs/probes/orun1/d4/t1-balancer/` [rec: spring-ivy-9833].

Next units named by the trial, both product changes rather than prompt changes: (1) the motor shaft must turn with the wheel, or the sweep must exclude the wheel–shaft pair; (2) model the 1430 wheel's rim, hub and tyre rather than a slab [rec: spring-ivy-9833]. Reconcile judgement: status moved open → working because generation has started.

## Negative knowledge

- [scope: wheeled designs using the `pololu-1430` wheel on the catalog gearmotor, as of commit dbc0c544 | confidence: high | evidence: spring-ivy-9833] No catalog wheel on its catalog gearmotor can pass a swept fit: the gearmotor's D-shaft is static while the wheel joint turns, so the sweep always finds the bore–shaft overlap (4.26 mm³ at ±180° in trial 1). Measured once with the mechanism understood; a product fix is the named next unit.

## Provenance

- sweet-brook-2725 — orun1 operator-declared charter gap
- spring-ivy-9833 — prompts frozen and hash-pinned; balancer trial 1 (9/9 held, static clean, sweep incomplete on catalog shaft, v2 3 of 5)
