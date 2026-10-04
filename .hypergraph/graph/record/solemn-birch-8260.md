---
node_id: 3a6ee705-c10e-56a7-85d0-524a049ce3bf
slug: solemn-birch-8260
title: 'orun2 W1 claim: walk 1–8, ledger complete, both suites and packaged gate green; 5090 leg owner-blocked'
created_at: '2026-10-04T04:53:54+00:00'
parents:
- neat-grove-1406
summary: ''
---
## What

W1's claim for critic review. W1 is "Nothing the product could do headlessly
was lost (orun2)". Every part of the criterion now has evidence. One deviation
is named and needs the owner: step 7 ran on the CPU, not the 5090. This record
claims W1 for critic review. It does not tick the owner's box.

## Why

The critic named this as the next unit, after neat-grove-1406: "If nothing
blocks W1, write the W1 claim record." The only items left on W1's state node
were these:

- the `cadex_dimension.py` row, now ported (neat-grove-1406);
- the rollout-playback flake, now fixed and green in a full run;
- closing gates on a final tree, run here;
- the 5090 leg.

The 5090 leg is blocked on root: the kernel has no `nvidia` module. Re-checked
this iteration: `lsmod | grep nvidia` is empty, and `nvidia-smi` cannot reach
the driver. No unattended role can fix that. So the claim goes forward with
the deviation stated, not hidden.

The critic offered R1's AGENTS.md line budget as the other candidate. It is
already met: `wc -l AGENTS.md` is 215, against a budget of at most 216 (half
of 432). No work was needed there.

## Method

The claim rests on the walk, the ledger and the gates.

- **Walk, steps 1–8, each seen in the dashboard:**
  - Steps 1–6 ran on `orun2-w1-quad`, a copy of `ot11-quad-1`
    (`docs/probes/orun2/w1/walk_dashboard.py`, `walk-steps.json`) [rec:
    red-loom-2239]:
    - prompt accepted `a7d487ae`;
    - Accept verdict;
    - `shin` sweep, 3/3;
    - render on the Concept tab;
    - Export: 62 STEP + 62 STL;
    - MJCF with 8 actuators, and the task JSON.
  - Steps 7–8 ran on `orun2-w1-robin`, a copy of `ot11-robin-1`
    (`walk_train_dashboard.py`, `walk-train-steps.json`) [rec:
    dusty-bramble-8099]:
    - `cadex walk` exit 0, with run `w1-cpu-2` on the Curves tab;
    - `cadex evaluate` exit 0, fail 0/10 seeds, on the Evaluation tab.
- **Ledger:** `docs/SHELL-PARITY.md`.
  - 47/47 module rows, 23/23 tool rows and 7/7 editor rows, none blank.
  - 0 rows say "to port".
  - Every ported row cites a test. The audit was mellow-fjord-5906. The rows
    ported since then each carry their test: ADR-521, 522, 523 and 524.
  - Two rows are "owner to confirm": face pins and the face-ID channel.
- **Gates, on `9fc13812` (HEAD; nothing but records since):**
  - `pixi run test-engine`: 2607 passed, 56 skipped, exit 0.
  - CLI suite with the GPU hidden: 1412 passed, 1 skipped, exit 0.
  - Packaged lifecycle gate,
    `CADEX_ENGINE_ROOT=build/engine/cadex-engine-0.0.0-linux-x64 pytest
    src/Mod/cadex/cadex_tests/test_cadexd_lifecycle.py`: **24 passed**.
    - The payload was staged on 2026-10-03 from `ef69dd39` (icy-tooth-7719).
    - `git diff --stat ef69dd39 HEAD -- src/Mod/cadex package src/App
      src/Base` touches only `cadex_tests/test_agent_guidance.py`, a test
      file. The engine code in the payload is therefore the engine code at
      HEAD, so the payload was not rebuilt.

## Result

**W1 is claimed for critic review**, with these residuals, all named:

1. **The 5090 deviation.** Step 7 trained on the CPU. Rerunning it on the 5090
   needs the owner to load the driver (root, DKMS rebuild or reboot). Then
   step 7 runs again at a real budget, `evaluate` runs again, and the two
   screenshots are replaced.
2. **Minor walk findings from red-loom-2239, not re-verified this
   iteration:**
   - the Model tab opens with the robot as a speck until **Fit** is pressed;
   - debug colours. ADR-522's role colours may have fixed this, but that is
     unverified;
   - a CLI turn's transcript and its `look` images do not appear on the
     project page.

   None of these is a lost capability. They are dashboard-polish defects for
   C1's defect list.
3. **Two "owner to confirm" ledger rows** stay with the owner.

Next is C1: start `docs/probes/orun2/REPORT.md`. R1's AGENTS.md budget is met
(215 lines).

Dispatch closed: 1 unit — W1 claimed for critic review with fresh gates (2607/1412/24 green); 5090 leg named as owner-blocked

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/orun2
- commit: 9fc1381218c7b96234baba408dab29debd9c6271

## State Impact

- target: shady-clover-5534 — claimed for critic review: walk steps 1–8 evidenced, ledger 0 to-port, gates on 9fc13812 test-engine 2607/56s, CLI 1412/1s, packaged lifecycle gate 24 passed (payload engine code unchanged since ef69dd39); residual: step 7 on CPU because nvidia driver not loaded (owner-only), minor walk display findings unverified
