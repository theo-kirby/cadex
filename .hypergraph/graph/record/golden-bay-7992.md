---
node_id: b25c90be-bd76-5253-8abc-2d0447ce315a
slug: golden-bay-7992
title: 'orun1 D2: design language and overlay rewritten from the owner''s ratings, inside-out procedure, ot10 rubric retired'
created_at: '2026-10-03T02:05:27+00:00'
parents:
- plain-horizon-5009
summary: ''
---
## What

orun1 D2: rewrote `docs/DESIGN-LANGUAGE.md` and the overlay the product agent reads (`src/Mod/cadex/CadexAgentGuidance.md`) from the owner's blind sweep ratings and charter A1–A3. The doc's rules now cite sweep design ids with their verdict and split, or the charter, or are marked **[judgement]**. The overlay's design section is now a six-step inside-out procedure: concept (choose the exposed-mechanism or panelled hard-surface finish, with a reason), parts first, place them, the structure that carries them, finish, refine with `look`. Added ADR-479 (the rewrite), ADR-480 (mandated face removed; a real sensor may go where it was), ADR-481 (single soft body primitive removed), ADR-482 ("never an exposed case or a bare board" removed; hardware that shows is ordered), ADR-483 ("split lines only" replaced by "detail is real") and ADR-484 (ot10's T1–T7 rubric retired as the authority; judge v2 replaces it; ot10's files kept as its record and as the baseline). Updated AGENTS.md's doc index, docs/CLI.md's overlay section, a retirement banner on docs/probes/ot10/README.md and a D2 section in docs/probes/orun1/README.md.

## Why

The critic named D2 as the next unit, and it is the highest-ranked open criterion after D1 (met, `plain-horizon-5009`). I did what the message asked: every rule cites evidence or is marked; one ADR for each of the four contradicted rules; inside out is the procedure; an ADR retires the ot10 rubric; no ratings, renders or judge prompt in the guidance; test-engine run.

## Method

- Read ratings.json (55 designs, verdicts, split, notes and palettes) and viewed the hero of every Love (balancer-c, biped-c, quadruped-e, arm5-g), every No (biped-a, hexapod-g, biped-h), and quadruped-d, hexapod-c, quadruped-c and hexapod-f. The rules came from those designs and their agents' notes. For example, every Love's notes describe inside-out packing, and all four Loves use the bone/graphite/orange palette.
- I named one honest tension in the doc. Two Loves have a forward element their own notes call an "eye-bar" and "two lenses". So the no-face rule separates a sensor on a hard front from a mascot face, and the advice to prefer one part over two round lenses is marked as judgement.
- Held-out designs are cited as evidence in the doc. D1's judge was frozen and measured before this was written, so nothing D1 counts was tuned on them. D2 asks for citations from the ratings.
- Tests, in `cli/tests/test_turn_loop.py`:
  - `test_the_design_section_runs_inside_out` holds the six-step order and the key rules in each step.
  - `test_the_old_archetype_is_gone_from_the_overlay` fails if the face, hidden-hardware, single-primitive or split-line rules come back.
  - `test_the_overlay_quotes_no_rating_render_or_judge` checks the CLI overlay and the guidance file against every sweep id and image name, and against the words owner, Love, held-out, judge v2, `V2_INSTRUCTIONS` and `.png`.
  - The taper test is rewritten: ADR-428's cradle half went with ADR-482.
- Other test changes: `test_ot10_contract.py`'s rule that the language must cite all ten ot10 references now only forbids embedded images and reference paths (ADR-484). The engine `test_agent_guidance.py` headings are updated.
- Regression check: with the old guidance file swapped back in, the inside-out, archetype and taper tests fail (3 failed). The quotes test passes on old and new alike, because the old overlay quoted no ratings either.

## Result

- `CUDA_VISIBLE_DEVICES= pytest cli/tests`: 1291 passed, 1 skipped. That full run started before the AGENTS.md and CLI.md doc edits. Afterwards test_project_docs, test_turn_loop and test_ot10_contract re-ran green: 128 passed. `pixi run test-engine`: 2545 passed, 61 skipped.
- No engine code, protocol or payload change besides the shipped guidance text, so no packaged gate was run. The guidance file ships in the payload, so a bundled engine sees the new text only after `pixi run stage-engine`.
- **Concern for the next iteration:** `look`'s `hardware_silhouette_share` still carries ot10's 0.20 bar and its `meets` flag (`CadexStudio.PROXY_BARS`). The overlay now tells the agent to read it in the exposed finish as how much shows, not as a failure. A small engine change could drop that bar, or make it report-only, with its test and ADR.
- **Concern:** the overlay's step 4 now says "a part held only by being inside a cover is not held", but nothing measures it yet. D3's mounting check is the producer for that.
- D3, the next criterion, needs the catalog additions (STS3215 bus servo, a Pi 4/5-class board, camera, ToF sensor, wheel and tyre, foot pad) and the mounting check. Until the catalog has a camera or ToF part, the overlay's "a real sensor at the front" can only become a slot.
- The tail is now 3 unreconciled records: reconcile is due by the charter's rule.

Dispatch closed: 1 unit — D2 design language and overlay rewritten from the owner's ratings (ADR-479–484), inside-out procedure test-pinned

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/orun1
- commit: 921030e495e7574ab551c0889c8ad01d3787072c

## State Impact

- target: ancient-sky-2085 — DESIGN-LANGUAGE.md and CadexAgentGuidance.md rewritten on A1–A3 with every rule citing sweep ids and verdicts or marked judgement; inside-out six-step procedure in the overlay; face, single soft primitive, hidden hardware and split-lines-only removed (ADR-479–483); ot10 rubric retired (ADR-484); overlay test-pinned to quote no rating, id, render or judge text. Evidence complete pending owner tick.
