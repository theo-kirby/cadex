---
node_id: 0d1755fd-e113-53fb-9393-31d06b2ce68d
slug: shady-clover-5534
title: W1. Nothing the product could do headlessly was lost (orun2)
created_at: '2026-10-03T10:54:47+00:00'
parents:
- nimble-pine-0740
summary: ''
---
Status: open

## Current

Open charter criterion for run orun2: **W1. Nothing the product could do headlessly was lost.** - On a copy of an existing robot project, the whole walk runs and every step is visible in the dashboard: 1. prompt; 2. accepted design; 3. params sweep; 4. `look` and render; 5. STEP/STL export; 6. MJCF export; 7. a short training run on the 5090; 8. `evaluate`. - Both full suites pass, and so does the packaged lifecycle gate. - The CLI and dashboard have no feature the shell parity ledger below marks "ported" without a test. - **The parity ledger is complete:** `docs/SHELL-PARITY.md` gives each of these one row: - every `mesh_agent` module; - each of its 23 tools; - each of the seven Cadex editors. Each row says one of three things: **ported** (where, and the test), **already covered** (where), or **dropped** (why, and the ADR). No row is blank. [rec: winter-stone-5109]

**All eight walk steps have run on copies of real robot projects and are visible in the dashboard.** Steps 1–6 on `orun2-w1-quad` (a copy of `ot11-quad-1`), driven in headless Chromium by `docs/probes/orun2/w1/walk_dashboard.py` (`walk-steps.json`, `9d487b65`): prompt 335 s accepted `a7d487ae`; Accept verdict, 62 components; `shin` sweep 3/3 at ~116 s, 55 mm back to `25984e70`; render 155 s on the Concept tab; page Export 62 STEP + 62 STL in 116.8 s; MJCF (8 actuators) and task JSON downloaded [rec: red-loom-2239]. Steps 7–8 on `orun2-w1-robin` (a copy of `ot11-robin-1`, unlocked by ADR-520), seen through `walk_train_dashboard.py` (`walk-train-steps.json`, `fbdf9d88`): `cadex walk` exit 0, run `w1-cpu-2` shown as current on the Curves tab with the policy stored under its digest; `cadex evaluate` exit 0, **fail 0/10 seeds**, shown on the Evaluation tab with tables and film [rec: dusty-bramble-8099].

- **Deviation: step 7 ran on the CPU, not the 5090.** Kernel `7.0.0-34-generic` has no `nvidia` module (`modinfo nvidia` missing, no `updates/dkms`; `lspci` still shows `10de:2b85`); fixing it needs root and a DKMS rebuild or reboot — owner-only. Every training unit is CPU-only until then. The 5090 leg (rerun step 7 at a real budget, re-evaluate, replace the two screenshots with the same driver) remains [rec: dusty-bramble-8099].

**Parity ledger audited row by row (`07746b65`).** 47/47 `mesh_agent` entries, 23/23 tools and 7/7 editors rowed against tag `v1-blender-shell`, none blank (skeleton `94b5be8f` [rec: old-arrow-4088]); every cited test exists and passes (9 CLI files 77 passed / 0 skipped against the built engine, 2 engine files 23 passed); **no ported row lacks a passing test**. Counts — §1: 17 ported / 15 covered / 24 dropped / 5 to port / 2 owner to confirm; §2: 6 / 17 / 2 / 0 / 0; §3: 5 / 2 / 5 / 1 / 0 (split rows count under each part). Earlier ported with tests: blueprint rows (`draw_blueprint`, Drawings panel, ADR-516) [rec: sweet-arrow-0695]; `prefs.py` as project budgets (ADR-517) [rec: curious-flint-4836]; this audit added `model.py`/`model_api.py` (ADR-503), `history.py` (live transcript, ADR-504) and `ui.py` [rec: mellow-fjord-5906].

**Six rows still say "to port" and block the claim** [rec: mellow-fjord-5906]:
- `agent.py`: per-turn cost and the text-tool-call warning [rec: mellow-fjord-5906];
- `cadex_dimension.py`: the viewer overlay (sheets already ported, ADR-516) [rec: mellow-fjord-5906];
- `cadex_print.py` and the Parameters editor: printable-part display [rec: mellow-fjord-5906];
- `cadex_roles.py`: appearance-role display [rec: mellow-fjord-5906];
- `modes.py`: the §4 guidance points (none yet in `CadexAgentGuidance.md` or `CLI_OVERLAY`) [rec: mellow-fjord-5906].
Suggested order: §4 guidance, then role colours plus printable roster in the viewer, then per-turn cost. Two face-level "owner to confirm" rows stay with the owner [rec: mellow-fjord-5906].

**Gates:** packaged lifecycle gate 24 passed; engine 2606 passed / 56 skipped; CLI 1400 passed / 1 skipped (GPU hidden) — all green on the ADR-520 tree [rec: icy-tooth-7719]; the ledger audit was docs-only. The pre-ADR-469 lock that counted against "nothing lost" is resolved (`brisk-rock-9862`) [rec: icy-tooth-7719]. Minor findings still open from the walk: the Model tab opens with the robot as a speck until **Fit** and in debug colours; a CLI turn's transcript and `look` images do not appear on the project page [rec: red-loom-2239].

Reconcile judgement: stays `open` — the six to-port rows, the 5090 leg and closing gates stand between this and the criterion [rec: mellow-fjord-5906] [rec: dusty-bramble-8099].

Declared target: `gap-w1-nothing-product-could-do`. The human owns the charter checkbox; roles report results and do not tick it. Reconcile judgement: earlier runs have criteria with the same letters, so every orun2 gap title carries the run [rec: winter-stone-5109].

## Negative knowledge

None yet.

## Provenance

- winter-stone-5109 — orun2 operator-declared charter gap
- old-arrow-4088 — SHELL-PARITY.md skeleton: 47 module / 23 tool / 7 editor rows, none blank, statuses interim
- sweet-arrow-0695 — blueprint ledger rows ported: draw_blueprint and the Drawings panel, tested (ADR-516)
- curious-flint-4836 — prefs.py ledger row ported: engine budgets belong to the project, tested (ADR-517)
- amber-moon-9415 — both full suites green at 21d130f5; restart flake and viewer-settle race fixed in test logic
- red-loom-2239 — W1 walk steps 1–6 on orun2-w1-quad, each seen in the dashboard; pre-ADR-469 trained projects unopenable
- icy-tooth-7719 — ADR-520 unlocks pre-ADR-469 projects; packaged gate and both suites green
- dusty-bramble-8099 — walk steps 7–8 on orun2-w1-robin seen in the dashboard; CPU because the 5090 driver is not loaded
- mellow-fjord-5906 — parity ledger audited: 77 rows, all cited tests pass, six rows still to port
