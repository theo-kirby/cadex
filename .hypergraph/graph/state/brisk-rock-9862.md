---
node_id: 2af180e9-6391-5f72-b437-4b4e48c7c567
slug: brisk-rock-9862
title: Projects trained before ADR-469 cannot be opened (stale policy locks the project)
created_at: '2026-10-04T01:57:02+00:00'
parents:
- calm-peak-5247
summary: ''
---
Status: working

## Current

**Resolved by ADR-520 (`ef69dd39`): a project whose policy was trained before ADR-469 now opens, names its stale policy, and can be set aside or retrained.** The policy is still refused at every build that declares it and nothing is re-accepted; `open_project` returns `restore: {performed: false, stale_policy: {output, reason, error, correction, *_sha256}}` instead of `CADEXD_RESTORE_FAILED`, and the CLI envelope carries a note naming the output and the two ways out (retrain, or set the policy aside) [rec: icy-tooth-7719].

- **Scope of the admission:** only when the restore run failed because the worker refused an `assembly.policy` output at its `policy_model` stage for one of the five `cadexd.STALE_POLICY_REASONS` (`policy_task_mismatch`, `policy_model_mismatch`, `policy_channels_mismatch`, `policy_actions_mismatch`, `policy_output_range_mismatch`). A corrupt container, a disagreeing witness, the right reason at another stage, or a script that will not run still refuse the open [rec: icy-tooth-7719].
- **Tests:** `src/Mod/cadex/cadex_tests/test_restore_stale_policy.py` (each reason, plus the four refusals; accepted state and candidate record unchanged) and `cli/tests/test_stale_policy_note.py`; a new golden `open_project.stale_policy.json` pins the one optional `restore` key in `OP_RESPONSE_SPECS` [rec: icy-tooth-7719].
- **Gates on that tree:** packaged lifecycle gate 24 passed / 0 skipped; `pixi run test-engine` 2606 passed / 56 skipped; CLI suite (GPU hidden) 1400 passed / 1 skipped [rec: icy-tooth-7719].
- **Reproduction cleared:** on `~/cadex-projects/orun2-w1-robin` (copy of `ot11-robin-1`), `cadex params --set policy_on=0` returned `ok: true` and accepted `bab6fa28`; W1 steps 7–8 then ran on it end to end [rec: icy-tooth-7719] [rec: dusty-bramble-8099].

**The original defect, for history:** ADR-469 moved `CONTACT_TIMECONST_S` 0.02 → 0.004, which moved every pre-2026-10-01 robot's task digest (`ca60b4ce…` → `d50e953b…` for `ot11-robin-1`); restore refused the policy and the open failed, so no command could run, not even one setting `policy_on` to 0 [rec: red-loom-2239].

Reconcile judgement: status `working` rather than a new status — the declared "resolved" maps onto this graph's vocabulary as a working capability. Not verified: the other ADR-469 casualties (`ot9-robin`, the `ot5`/`ot6` copies) were not opened, being read-only under the charter [rec: icy-tooth-7719].

## Negative knowledge

None yet.

## Provenance

- red-loom-2239 — found on W1's walk: restore refuses the pre-ADR-469 policy and open_project fails
- icy-tooth-7719 — ADR-520: stale policy refused without locking the project; packaged gate and both suites green
