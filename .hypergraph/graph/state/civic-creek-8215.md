---
node_id: f77f2218-ce49-555a-95aa-31a8336d0130
slug: civic-creek-8215
title: D8. A single servo arm goes through the lifecycle
created_at: '2026-09-13T21:25:10+00:00'
parents:
- round-sun-8398
summary: ''
---
Status: working

## Current

**Heron, a two-DoF MG90S arm designed by the product agent, has been through the full recorded lifecycle: designed from one prompt, corrected three times against measurements, accepted with fits, reopened, trained once (bounded), evaluated over ten seeds, with checkpoint and final videos in the D3 look on the persistent dashboard.** Every clause of D8 has committed evidence and only the owner's checkbox is outstanding — `working` on the same reading D1–D7 carry; one design decision is left open for the next turn on Heron [rec: narrow-quill-3259] [rec: mild-hill-0753] [rec: frosty-path-5235].

**Design half (ADR-339, commit `bb215890`).** In the fresh external project `ot6-heron`, one 9,648-byte design prompt produced the mechanism in a 24-minute turn. The engine accepted it, but its retained clearance table and dynamics export disagreed with the script's own stdout on three points, each sent back as a `--resume` turn quoting the measurement: a floor `assembly.collision("plane")` on the base (world geometry in a design, which the charter forbids), 248.2016 mm³ of servo/cheek common volume (the cheek's outer face placed at the tab plate's spline-side face), and a 0.2 mm horn/child gap (the pocket cleared the horn on its floor too, so the horn met nothing until the centre screw closed the side gap). The agent made each correction itself; each is an ADR line in the project's `DECISIONS.md`. Accepted at revision `9c1f2fe7ea19…` (digest `f9be3985bc55…`): catalog MG90S, horns, MR128 bearings and M2 screws with three modelled printed parts, 15 components, 55 of 55 fit rules on 105 measured pairs plus three section cuts (tab seats, horn pockets, horn on spline and bearing press all 0/0; 0.30 mm window clearance; 1.00 mm side gap; 0.6 mm lip-hole clearance; no other intersection, no plane geom, no initial proxy contact), the base the only grounded component, two limited hinges, valid single solids; printed 86.6 g, purchased 33.0 g. Five fresh-process reopens through `cadex section` at the accepted digest, one digest. The persistent dashboard served its real tessellated solids (29,234 triangles, `showing: tessellated solids`, 20 proxy outlines under the labelled toggle, no horizontal overflow) at 1400×900 and touch-emulated 400×850. Receipts under `docs/probes/ot6/heron/` (README, design.json, fit.json, reopen.json, operator.json, two screenshots, `fit_check.py`, `operator_probe.py`), pinned by a receipt test in `cli/tests/test_review_design.py` [rec: narrow-quill-3259].

**Training half (ADR-340, commit `630ab736`).** One bounded run, `heron1`: 240 PPO updates on 1024 environments, seed 0, default learning rate 3e-4, `MemoryMax=20G`, 3600 s timeout; trainer exit 0 after 619.6 s, host peak 7.08 GB, GPU 15,137 MiB. The trainer launched by iteration 25 was left to finish under its own timeout rather than killed, so there is exactly one run and nothing retained was rewritten. Checkpoint-20 and final videos in the `cadex-prototype-dark-v1` look naming what they show, browser-checked on the persistent dashboard, which selects `heron1-final` on a fresh visit; the checkpoint render fell across plain updates with no measurable cost to live-page latency (median 1.072 s during against 1.071 s before and 1.070 s after). Each retained policy measured over seeds 0–9 in a fresh scratch project with seed 0 asserted byte-identical to the retained trace and the source run unchanged: **checkpoint 20 reached on 0/10** (folds the arm back to the joint limits, never nearer the target than its 67.08 mm start); **the final policy on 10/10** by the script's own bar (within 10 mm by 0.1 s on every seed, nearest 0.36–1.85 mm, ends 2.96–5.19 mm away, never beyond 9.60 mm over the final second after the two pushes, no termination). Reward per step −0.154 → 0.595, best at the last update and still rising. Receipts: `training.json` (15.1 KB), `TRAINING.md`, two decoded video frames, a servo-side viewport frame with `servo-view.json`, pinned by the receipt test. The run views draw 53,620 triangles against the accepted view's 29,234 — a different tessellation source (the rollout leg's STL exports), both the real solids [rec: mild-hill-0753].

**Open design decision for the next turn on Heron, observed not diagnosed**: the hold sits about 3 mm below the target on most seeds (the 30 mm reach scale makes that nearly free; servo sag is the plausible cause but the trace does not separate it from the policy's setpoint), and the tip oscillates within tolerance (final-second max 8.3–9.6 mm against a mean of 4.9–6.2 mm). A tighter tolerance, smaller reach scale or heavier tip-speed weight is noted in the project's `DECISIONS.md`, not taken [rec: mild-hill-0753].

Assumptions stated by the records: the reach target is fixed across episodes and per-seed variation is the two forearm pushes only (a grounded mechanism refuses `reset_variation`); the default dashboard view is from the bearing side, and the servo-side frame was taken by orbit [rec: narrow-quill-3259] [rec: mild-hill-0753].

Three accepted-revision identities appear across Heron's evidence and are one design, not three: the design receipt names `9c1f2fe7ea19…`, the training receipt `5971903121bf…`, and the operator page serves `0c8c64c92252…`; all carry the same script digest `f9be3985bc55…`, the revision identity carrying the playback parameter values [rec: frosty-path-5235].

Charter criterion: **D8. A single servo arm goes through the lifecycle.** Same as D7 for a 2 or 3 DoF arm on MG90S servos with a modelled base and links; its task is a reach or hold, measured. Declared target `gap-d8-single-servo-arm-goes`; the human owns the checkbox edit [rec: brisk-ledge-9638].

## Negative knowledge

- [scope: checking a product-agent mechanism's fits | confidence: high | evidence: narrow-quill-3259] The engine accepts mechanisms whose stdout claims contradict their own retained clearance pairs; the acceptance gate does not read a script's fit claims. Three such contradictions in one design. A fit check must read the published measurements, never stdout.
- [scope: section cuts on Heron | confidence: medium | evidence: narrow-quill-3259] A cut plane landing exactly on a tessellation edge (an exact 6 mm above a joint axis) reports `unsupported`; worked around by a 0.3 mm offset rather than changed.
- [scope: the trainer's `episode_steps` on a task whose only endings are the synchronized time limit | confidence: high | evidence: mild-hill-0753] The metric is unroll × envs over endings in the unroll, so it alternates 20,480 / 20.0 and says nothing about episode length; the receipt reports it as such.

## Provenance

- brisk-ledge-9638 — the ot6 directive (ADR-328) declared this criterion as gap `gap-d8-single-servo-arm-goes`
- narrow-quill-3259 — ADR-339, the design half: Heron accepted after three measured corrections, 55/55 fit rules on the retained pairs, five fresh-process reopens, real solids on the persistent dashboard at both widths
- mild-hill-0753 — ADR-340, the training half: heron1 trained once under the bounds, checkpoint 20 on 0/10 and the final policy on 10/10 over seeds 0–9, both videos in the new look on the operator dashboard
- frosty-path-5235 — the closing report: D8 evidenced pending the owner's tick, the 3 mm-low hold left as an open design decision in the project, the three revision identities reconciled to one script digest
