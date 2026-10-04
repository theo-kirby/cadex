# orun2 W1 — the headless walk, steps 1–6, seen in the dashboard

Measured 2026-10-04 on `orun2-w1-quad`, a whole copy of `ot11-quad-1` (the
eight-MG90S quadruped walker whose `walk_r24` policy passed 10/10 seeds on
2026-10-01). The source project was not touched. `walk_dashboard.py` is the
driver: it serves `cadex app` over the projects directory on 127.0.0.1 and
drives it in headless Chromium (`cli/cadex_cli/browser.py`) against the dev-tree
engine. `walk-steps.json` holds everything it measured. Training on the 5090
and `evaluate`, steps 7–8, are the next unit.

| Step | How it ran | Measured | Seen in the dashboard |
|---|---|---|---|
| 1. Prompt | `cadex -p` (CLI): two cable-tie slots through the hood, `policy_on` 0 because the mass changed | exit 0 in 335 s; tools `inspect`×5, `look`×1, `edit_script`, `set_params`, `rebuild`; accepted `a7d487ae`, digest `25984e70`; four new `tie_*` params; two `DECISION` lines, one saying the policy must be retrained | index lists the project at `a7d487ae` and the turn under CLI agent turns (`w1-1-index.png`) |
| 2. Accepted design | **Accept** on the page (`cadex revision accept`) | model `loaded`, 62 components, index and page agree on `a7d487ae`; verdict `accepted` | `w1-2-accepted.png` |
| 3. Params sweep | the `shin` slider, 52 → 58 → 55 mm (`cadex params`) | 3 of 3 ok, 115.96 / 117.02 / 116.46 s each; revisions `193a15a6`, `bde111d9`, `27150b47`; model reloaded after each; 3 project commits; 55 mm returns to digest `25984e70` | `w1-3-sweep.png` |
| 4. `look` and render | `look` inside the step 1 turn; `cadex render` (CLI) | render exit 0 in 155.0 s | Concept tab: "the accepted design, drawn from revision 27150b476953", 0.51 kg, 8 servos, 178 × 151 × 123 mm (`w1-4-render.png`) |
| 5. STEP/STL | **Export STEP + STL** on the page (`cadex export`) | done in 116.8 s; 62 `.step` + 62 `.stl` offered; `battery.step` starts `ISO-10303-21;`, `battery.stl` downloads | export list (`w1-5-export.png`) |
| 6. MJCF | the same export stages the model beside them | `model-model.xml` (24,828 bytes, `<mujoco`, 8 actuators) and `walk_task-task.json` offered and downloaded | export list |

## Defects found on the way

- **A project trained before ADR-469 does not open at all.** The first copy
  tried was `ot11-robin-1` (Robin, passed 10/10 on 2026-09-30). ADR-469
  (2026-10-01) wrote `solref="0.004"` on every contact geom, so the MJCF and
  the task bundle digest changed (`ca60b4ce…` → `d50e953b…`). The restore
  pass then refuses the declared policy (`policy_task_mismatch`), and
  retrying with the accepted source fails the same way, so `open_project`
  returns `CADEXD_RESTORE_FAILED`. Every command fails before it starts,
  including a design turn that would set `policy_on` to 0. A refusal is right
  for the policy. Locking the whole project is not. Nothing in the CLI or
  dashboard can repair it short of editing `script.json` by hand.
- **The Model tab opens with the robot as a speck.** A 178 mm quad sits in
  the middle of the metre grid until **Fit** is pressed, and it is drawn in
  per-component debug colours (`w1-5-export.png`).
- **A CLI turn's transcript is not on the project page.** The index lists
  the turn and its revision, but the agent's text and its `look` images
  reach the page only when the turn was started from the page (§19). Steps
  1 and 4 are visible through their results, not their transcripts.
