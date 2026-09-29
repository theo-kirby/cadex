---
node_id: 5f1253fd-68e8-569a-8727-9369eba20bcd
slug: soft-spark-6990
title: 'ot10 A5 attempt 1: hexapod unassisted, 13/21 blind (bar 14); P2 0.655, sweep incomplete, both from the 300 CPU-s limit; 0 of 4 A4 refusal classes'
created_at: '2026-09-27T20:04:45+00:00'
parents:
- solemn-hill-7272
summary: ''
---
## What

The first A5 probe: the three cold prompts are frozen, and the hexapod has been run as one design-only product turn, rendered by A2 and scored blind under A1's frozen procedure. **It misses the bar, at 13 of 21 against 14.** It also misses on P2 (0.655) and on the swept fit (incomplete). It scores far above hex3's 2. None of the four A4 refusal classes recurred.

## Why

This is the critic's named unit (medium-term rung 1). It is the only way A4 and A5 can move now. The critic's first ask was that A2's state node say plainly that the whole-command render misses the 60 s bar. I cannot write state nodes, so that correction is declared below as an impact on `sweet-arbor-1947`, with a new measurement. I did not change any prompt or tool after the miss. The diagnosis is below, as the charter asks.

## Method

- **Freeze first** (commit `13246076`, before the turn started). `contract.json` gains `a5`: model `claude-opus-5-5`, effort `medium`, one turn, argv `./cadex --project <new ot10-*> --model claude-opus-5-5 -p <prompt> --json`, env `CADEX_EFFORT=medium`, and three prompts.
  - **hexapod**: hex1–hex3's prompt, word for word.
  - **quadruped**: the same prompt with "two per leg: hip pitch and knee".
  - **biped**: the same prompt with "three per leg: hip pitch, knee and ankle". The biped is the run's own choice, as the plan furthest from a flat deck.
  - The README has an "A5: the cold prompts" section, and `cli/tests/test_ot10_contract.py::test_a5_cold_prompts_are_frozen_on_page_and_file` pins it: page equals file, the hex prompt is verbatim, there is no fallback, and no look words appear in any prompt.
  - **Assumption:** `medium` is hex2/hex3's effort, after hex1 stalled at `high`. The prompts keep "declare a training task" so that W2 can train an A5 design unchanged.
- **Turn.** `CADEX_EFFORT=medium ./cadex --project ~/cadex-projects/ot10-hexapod-1 --model claude-opus-5-5 -p "<hexapod prompt>" --json` ran from 18:52:16Z to 19:48:00Z (55 min 44 s), exit 0, session `e5b57c7e…`. It accepted revision `7af6db090950…`, digest `ab571337a4d3…`. I observed only, and touched no geometry.
- **Render.** `./cadex render --project <it> --json` took 63.7 s in all: 29.3 s of rebuild, 5.9 s drawing, and 2.1 s for the 1024 px hero, at 81,876 triangles. The five `look` views came from a helper outside the repo that calls `render.look` exactly as the bridge does: roles and palette from the inventory, floor excluded, 768 px.
- **Judge.** `docs/probes/ot10/runner/judge.py` was run unchanged on the hero, then iso, iso_back, front, right and top. That is three calls in 58 s, with no retries.
- **Published.** `docs/probes/ot10/ot10-hexapod-1-{hero,look_*}.png` are six PNGs of 33–101 KB each. `ot10-hexapod-1-score.json` holds every raw reply. The README has an "A5 attempt 1" section. `test_a5_hexapod_attempt_is_published_with_its_score` pins the hashes, the sizes, the total 13 and the miss.

## Result

- **Scores.** The medians are T1 2, T2 3, T3 1, T4 1, T5 2, T6 2, T7 2, for a **total of 13** (hex3: 2). The three calls were identical on every trait.
- **Proxies.** P1 is **0.078** (meets ≤ 0.20). P2 is **0.655** (21,133 of 32,275 mm over 17 printed parts; fails ≤ 0.25). P3 is **3** (`#2A2C31`, `#E9E4D8`, `#F26A1B`; meets).
- **Fit.** Static: 1,035 pairs clear, 0 intersections, 32 welded pairs touching. The only "failing" row is the floor's advisory world-geometry row, hex's known quirk. **Sweep: incomplete, with 12 of 12 joints unswept**, because the accepted script declares no `sweep_step_degrees`.
- **Electronics.** It carries all of them: ESP32, PCA9685, BNO085, D36V50F6, the 2S LiPo and 12 × MG90S.
- **A5 fails at attempt 1** on three bar items: the total (13 < 14), P2, and the swept fit.
- **A4 behavioural evidence.** **0 of the 4 classes recurred.** There was no horn style error, no edit before a script existed, no double assembly or diagnostics output, and no missing or doubled joint.
  - The other refusals: **19 CPU-limit refusals (300 CPU-s)**, `import`, `dir`, a catalog body as an `assembly.component` source, 6 kernel and selector refusals, 2 unmatched `edit_script` replacements, 1 guessed pointer (`/accepted/revision`), 1 reset-variation refusal, and 1 refusal to retire `joint_cap` while the script's own assembly links still referenced it. The error text calls those links "human-created or foreign", which looks like an engine defect.
  - 33 refusals in all. `look` was used 3 times, including the hero.
- **Diagnosis.** The language reached the design. It has a rounded shell over a dark belly tray, hip servos inside the body, three materials by role, one accent on a visor-slot face, and ball feet (see `ot10-hexapod-1-hero.png`).
  - The low traits, T3 joints and T4 form, are the details the agent built and then **removed to fit the engine's 300 CPU-second limit**. Its project `DECISIONS.md` lists what went: the spline-loft carapace, the joint caps, the leg fillets, the servo-shaped pockets, 34 screws, and the motion sweep. It names total face count as the lever.
  - P2's 0.655 and the incomplete sweep are the same cut. So the binding constraint was the cost of checking the design, not what the agent was taught.
  - The agent's bisection saw 4 full legs build and 6 fail. Six legs with only hip servo and coxa also failed. It fit only after the face count came down.
- **A2 against the 60 s bar.** It is still unmet end to end on hex3: about 7 min, of which 207 s is the rebuild. This new 46-component design took **63.7 s whole-command** (29.3 s rebuild), so it also misses 60 s, by 3.7 s. Only the drawing meets the bar.
- **Next step, recorded before any prompt or tool change.** Measure where a 46-component, 1,035-pair `edit_script` spends 300 CPU-seconds, since hex3's 12-servo filleted assembly fit. Then make the check cheaper; do not raise the limit blindly and do not change the prompt. Only after that should the quadruped and biped run. Running them now would measure the same ceiling again.
- **Concerns.**
  - The `joint_cap` retire refusal is a probable engine defect and is not yet reproduced.
  - The look-views helper lives outside the repo, in the notes directory. If the next attempts need it, it should become a committed, tested runner.
  - `pixi run python -m pytest cli/tests`: 993 passed, 1 skipped. The engine suite was not rerun, because this unit changed no engine file.
- **Tail.** This is the first record since the last reconcile.

Dispatch closed: 1 unit — A5 prompts frozen; hexapod attempt 1 designed unassisted, scored 13/21 (bar 14, hex3 2), P2 0.655 and sweep incomplete, all traced to the 300 CPU-s limit; 0 of 4 A4 refusal classes recurred

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot10
- commit: de0330b92df154c48ddbc33941869312fa542605

## State Impact

- target: loyal-fountain-8709 — Prompts frozen (commit 13246076: hexapod verbatim hex1-3, quadruped, biped; opus-5-5, CADEX_EFFORT=medium, one turn). Attempt 1 ot10-hexapod-1 rev 7af6db09: judged 13/21 (T1 2,T2 3,T3 1,T4 1,T5 2,T6 2,T7 2; hex3 2), P1 0.078, P2 0.655 FAIL, P3 3, static fit clear, sweep incomplete 12/12 FAIL, electronics carried. A5 currently failing; cause is the 300 CPU-s limit forcing the agent to strip caps, fillets and the sweep. Next: measure and cut the check cost before quadruped/biped.
- target: odd-tree-6681 — First behavioural evidence: the ot10-hexapod-1 transcript shows 0 of the 4 hex refusal classes (horn style, edit before script, >1 assembly/diagnostics, joint missing/twice). 33 other refusals, 19 of them the 300 CPU-s limit; sandbox import/dir and guessed pointers still recur. Stays open until the remaining A5 transcripts.
- target: sweet-arbor-1947 — Correction: the charter's 60 s bar is NOT met end to end. Whole-command ./cadex render is ~7 min on hex3 (207 s rebuild) and 63.7 s on ot10-hexapod-1 (29.3 s rebuild, 5.9 s draw, hero 2.1 s). Only the drawing meets it; working status covers the renderer, not the bar, and A2 is incomplete until acquisition fits.
