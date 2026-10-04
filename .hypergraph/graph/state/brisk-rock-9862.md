---
node_id: 2af180e9-6391-5f72-b437-4b4e48c7c567
slug: brisk-rock-9862
title: Projects trained before ADR-469 cannot be opened (stale policy locks the project)
created_at: '2026-10-04T01:57:02+00:00'
parents:
- calm-peak-5247
summary: ''
---
Status: broken

## Current

**A robot project whose policy was trained before ADR-469 cannot be opened at all.** ADR-469 (`22d30e7e`, 2026-10-01) changed `CONTACT_TIMECONST_S` from 0.02 to 0.004, which puts `solref="0.004"` on every contact geom and moves the task bundle digest (`ca60b4ce…` → `d50e953b…` for `ot11-robin-1`). The restore pass then refuses the declared policy (`policy_task_mismatch`), the accepted-source retry fails the same way, and `open_project` returns `CADEXD_RESTORE_FAILED` — so no command runs, not even a design turn that would set `policy_on` to 0 [rec: red-loom-2239].

- **Reproduction:** `~/cadex-projects/orun2-w1-robin`, a copy of `ot11-robin-1`, kept as-is [rec: red-loom-2239].
- **Reach:** every robot project trained before 2026-10-01 (for example `ot11-robin-1`, `ot9-robin`, the `ot6`/`ot5` copies); projects trained after ADR-469 (`ot11-quad-1`) open and walk normally [rec: red-loom-2239].
- **Why it matters:** a lost headless capability, counted against orun2 W1's "nothing lost" (`shady-clover-5534`) [rec: red-loom-2239].
- **Likely fix (not yet attempted):** refusing the stale policy is right; locking the project is not. Let the restore pass accept with the policy output reported stale rather than fail the open — an engine-zone change needing its own unit, ADR and tests [rec: red-loom-2239].

Reconcile judgement: parented under the robot lifecycle walk (`calm-peak-5247`), since the defect breaks the design → policy → iterate loop on older projects; declared slug `stale-policy-locks-project` was a placeholder for a minted one [rec: red-loom-2239].

## Negative knowledge

None yet.

## Provenance

- red-loom-2239 — found on W1's walk: restore refuses the pre-ADR-469 policy and open_project fails
