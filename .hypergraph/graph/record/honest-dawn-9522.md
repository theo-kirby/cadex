---
node_id: cc09f706-94f1-5d8f-b123-6817a0877752
slug: honest-dawn-9522
title: 'ot10: A5 confirmation round pre-registered (hexapod-11, quadruped-4, biped-2; earlier turns still counted)'
created_at: '2026-09-28T18:21:19+00:00'
parents:
- soft-cliff-8778
summary: ''
---
## What
Handoff record for the A5 confirmation-round pre-registration in `docs/probes/ot10/README.md` (commit `4288ef42`), which landed last iteration without a record node.

## Why
The critic's fix-first: "No handoff was recorded this iteration. Add a record node for the confirmation-round pre-registration, parented on the A5 C1 re-claim record, with a State Impact on loyal-fountain-8709."

## Method
Read the committed section at `4288ef42` and restated it here; no file changed in this record.

## Result
The confirmation round is frozen at revision `96ed90d0`, before any of its turns:
- one turn per body plan, frozen prompt from `contract.json` `a5.prompts`, argv as frozen (`claude-opus-5-5`, `CADEX_EFFORT=medium`, no continuation), on new projects `ot10-hexapod-11`, then `ot10-quadruped-4`, then `ot10-biped-2`;
- hexapod first, as the weakest plan (first pass on its ninth counted turn);
- all twelve earlier counted turns stay published and counted; A5 is not redefined;
- scoring unchanged: blind `runner/judge.py`, frozen rubric, proxies and bar, rendered and judged from a `/tmp` copy;
- a miss is diagnosed and recorded before any prompt, overlay or tool change;
- a harness kill is a receipt, not an attempt, and the plan gets a new project.

Dispatch closed: 1 unit — handoff record for the pre-registered A5 confirmation round (commit 4288ef42).

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot10
- commit: 4288ef4207b15f58f489ff1a256b576280dc6c17

## State Impact

- target: loyal-fountain-8709 — a confirmation round is pre-registered at 96ed90d0: one frozen turn per plan (ot10-hexapod-11, ot10-quadruped-4, ot10-biped-2), scored unchanged, all twelve earlier turns still counted, A5 not redefined
