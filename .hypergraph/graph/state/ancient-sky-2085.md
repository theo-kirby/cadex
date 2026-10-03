---
node_id: d7a50fdf-9a74-56f2-abe1-a680b9a03559
slug: ancient-sky-2085
title: D2. The design language says what the owner rated, and the product teaches it (orun1)
created_at: '2026-10-02T17:01:59+00:00'
parents:
- nimble-pine-0740
summary: ''
---
Status: working

## Current

Charter criterion for run orun1: **D2. The design language says what the owner rated, and the product teaches it.** `docs/DESIGN-LANGUAGE.md` and the overlay the product agent reads (`src/Mod/cadex/CadexAgentGuidance.md`) rewritten on A1–A3 and the ratings; every rule cites sweep ids and verdicts or the charter, or is marked judgement; the face, single soft primitive, "never an exposed case or a bare board" and "split lines only" rules go, each with an ADR; inside out is the procedure; no guidance or prompt quotes ratings, renders or the judge; the ot10 rubric is retired or rewritten by ADR [rec: sweet-brook-2725]. The human owns the checkbox.

**Evidence complete, awaiting the owner's tick** [rec: golden-bay-7992] (commit `921030e4`). Reconcile judgement: status `working`, as for D1.

- **Rewrite** (ADR-479): rules cite sweep design ids with verdict and split, or the charter, or carry **[judgement]**. The overlay's design section is a six-step inside-out procedure: concept (pick the exposed-mechanism or panelled hard-surface finish, with a reason), parts first, place them, the structure that carries them, finish, refine with `look` [rec: golden-bay-7992].
- **Removals, one ADR each:** mandated face (ADR-480; a real sensor may sit where it was), single soft body primitive (ADR-481), "never an exposed case or a bare board" (ADR-482; hardware that shows is ordered — ADR-428's cradle half went with it), "split lines only" → "detail is real" (ADR-483) [rec: golden-bay-7992].
- **ot10's T1–T7 rubric retired as the authority** (ADR-484); judge v2 replaces it; ot10's files stay as its record and the baseline [rec: golden-bay-7992].
- **Test-pinned** in `cli/tests/test_turn_loop.py`: inside-out order, the old archetype absent, and the overlay quoting no sweep id, image name, owner/Love/held-out/judge words or `.png`. With the old guidance swapped back, the inside-out, archetype and taper tests fail (3); the quotes test passes on both, since the old overlay quoted no ratings either. `cli/tests` 1291 passed, 1 skipped; `test-engine` 2545 passed, 61 skipped [rec: golden-bay-7992].
- One named tension: two Loves have a forward "eye-bar" / "two lenses"; the no-face rule separates a sensor on a hard front from a mascot face, and preferring one part over two round lenses is marked judgement [rec: golden-bay-7992].

**Open ends handed on** [rec: golden-bay-7992]: `look`'s `hardware_silhouette_share` still carries ot10's 0.20 bar and `meets` flag (`CadexStudio.PROXY_BARS`) — the overlay tells the agent to read it as how much shows, not as a failure; a small engine change could make it report-only. Step 4's "a part held only by being inside a cover is not held" is unmeasured until D3's mounting check. Until the catalog has a camera or ToF part (D3), "a real sensor at the front" can only be a slot. The bundled engine sees the new guidance only after `pixi run stage-engine`.

## Negative knowledge

None yet.

## Provenance

- sweet-brook-2725 — orun1 operator-declared charter gap
- golden-bay-7992 — design language and overlay rewritten from the owner's ratings; inside-out procedure test-pinned; ADR-479–484 incl. ot10 rubric retired
