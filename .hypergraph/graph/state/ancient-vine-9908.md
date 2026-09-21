---
node_id: 7f6bb06d-e4e8-5cba-8e2c-426a22d8d889
slug: ancient-vine-9908
title: The unassisted-design evidence finished — the ot8 charter (ADR-399)
created_at: '2026-09-20T18:47:46+00:00'
parents:
- nimble-pine-0740
summary: ''
---
Status: open

## Current

**Owner-directed work for run `ot8` (ADR-399): finish the unassisted-design evidence ot7 left measured-but-open [rec: keen-stone-1720] [rec: humble-fox-6370].** It follows the ot7 charter (ADR-341, `mild-ledge-7157`), which merged as `fa75c531` on 2026-09-20 after one correction, and it is deliberately a **bounded follow-up rather than a new leg**: ot7's own report says which of its claims are reviewable against accepted artifacts and which are not, and those three gaps are the whole scope [rec: humble-fox-6370].

The mission, in the owner's terms [rec: keen-stone-1720]: an **arm** whose purchased hardware retains catalog identity (ot7 ended with two servos and two horns modified); a **biped** whose accepted MJCF passes the shipped `cadex smoke` command (ot7's pass was taken off a re-exported model, not off the pin); and a measured **cause** for the balancer's failed holding smoke. The charter keeps fit, support and controlled behavior apart by name: a wheel balancer that needs feedback is a **measured control requirement**, not permission to ground the base, add supports, weaken a tolerance or shorten a rollout, and a no-feedback inverted pendulum need not pass. No training and no dashboard work is authorized [rec: keen-stone-1720].

Carried from ot7 unchanged, and verified before launch [rec: humble-fox-6370]: `claude-opus-5` for every role and every product-agent call with **no fallback**, a 48-hour ceiling, and two accepted done verdicts as the completion stop. A no-tool availability probe reached `claude-opus-5` at a five-hour window of 0 %, and the runner's window gate returned `room: true`. The previous charter is preserved in git history and ot7's archive was refreshed after the merge; only operator docs and config changed after ot7's last verified product revision, so that revision's suites stand as this run's baseline [rec: humble-fox-6370].

The owner's fixed choices, not open to actor interpretation [rec: keen-stone-1720]:

- **The actor never edits a test design.** An unchanged copy may be prepared mechanically; every change and every re-acceptance comes from a product-agent turn. All prior projects stay read-only, and experiments run on new `ot8-*` projects under the established projects root — ot7's exhausted slots stay exhausted [rec: keen-stone-1720].
- **Prompts are frozen before any design turn**, with one initial product prompt and at most **three** continuations per design. A continuation names no part, dimension or defect; it directs the agent to its own measured fit, inventory and smoke evidence [rec: keen-stone-1720].
- **A void call spends no slot**, and an interrupted or unreached call keeps its evidence and may not masquerade as a design failure or a success. Model access and window headroom are verified before each design turn, and a provider block is answered by returning no change and letting the runner back off — never by manufacturing tooling or waiting records [rec: keen-stone-1720].
- **A design may fail.** Grounding a free robot, adding stabilizers, suppressing required joints, weakening tolerances or shortening a declared smoke to make a result pass is barred; an explicit measured blocker is an acceptable outcome. Smoke rollouts stay bounded to five minutes [rec: keen-stone-1720].
- Product defects are fixed **only** when a reproduced failure blocks these experiments or violates an existing contract, and each fix carries a regression that fails before it. No policy training, reward redesign, hand-authored feedback controller, dashboard or visual work, unrelated catalog expansion, or inherited-tree removals [rec: keen-stone-1720].

Standing rules carry from ot7: committed receipts at most 16 KB and images 200 KB, no secrets or machine paths, full evidence kept project-local and cited by path plus digest; exhaustion policy `report_done`; a reconcile pass every five work iterations or three unreconciled records, with the separate maintainer and planner off and the critic naming the next unit. If closing a design success bar would require training under the no-training constraint, that boundary is recorded once and the bounded diagnosis finished — the run does not spend itself rediscovering it [rec: keen-stone-1720].

The six done criteria G1-G6 are child state nodes: G1 `wise-aspen-8848`, G2 `tender-bay-4302`, G3 `empty-arrow-8425`, G4 `scarlet-hill-8037`, G5 `lucid-flame-4255`, G6 `smooth-vine-2389`. A record may say "ticks Gn" when its evidence exists; the human owns the checkbox edit [rec: keen-stone-1720].

**Run progress as of the third reconcile pass.** The contract is frozen and the run has a dispatch path: ADR-400 reuses the ot7 collector under `--run ot8` rather than forking it, so the slot rules ot7's receipts rest on keep one home, and a receipt with no `run` field is still ot7's [rec: honest-ash-4208]. Three of the six criteria now carry measured evidence and are `working`: **G1** frozen with 30 new tests [rec: honest-ash-4208]; **G3** met on the independent copy `ot8-plover`, where one rebuild turn re-accepted unchanged source and the ordinary `cadex smoke` passes against that pin [rec: sunny-quill-9617]; and **G2** met on `ot8-heron-b`, where the byte-identical create prompt reached zero failing static and swept fit with all four purchased parts catalogued and a passing smoke, on the create turn alone [rec: winter-creek-7660]. **G4 is the last experiment with an open measurement**, and it spends a slot only if its no-slot diagnosis finds an actionable design defect; G5 and G6 follow [rec: winter-creek-7660].

Two things the charter's rules have already been made to do rather than merely asserted [rec: winter-creek-7660] [rec: sunny-quill-9617]. A void call really did cost no slot: `ot8-heron` was cut off mid-turn by a five-hour session limit after 51 model messages, was classified void under ADR-355, and its evidence is retained and never reportable as a design outcome in either direction. And the no-actor-edit rule held through both product turns — `actor_design_edits: 0` on G2's create and on G3's rebuild, with `ot7-plover-e` and `ot7-heron-c` read read-only throughout.

*Reconcile judgement*: this umbrella node was **not** declared by any impact — `keen-stone-1720` declared only the six gaps. It is created anyway, under the state root, because ot5 (`crisp-sun-1239`), ot6 (`round-sun-8398`) and ot7 (`mild-ledge-7157`) each hold their criteria under a charter node, and six parentless gaps would leave the charter's constraints — frozen prompts, slot accounting, the no-actor-edit rule, the control/fit distinction — with nowhere to live. Every sentence above is from the charter text carried verbatim in `keen-stone-1720` or from `humble-fox-6370`; nothing is inferred beyond that [rec: keen-stone-1720] [rec: humble-fox-6370].

## Negative knowledge

None yet.

## Provenance

- keen-stone-1720 — the ot8 operator directive: the charter (ADR-399) verbatim, the six criteria G1-G6 declared as gaps
- humble-fox-6370 — ot7 merged as fa75c531 and this charter prepared: Opus-only with no fallback, a 48-hour ceiling, two accepted done verdicts, the model and window checks that passed before launch
- honest-ash-4208 — ot8's contract frozen before any product turn, and the collector reused under `--run ot8` (ADR-400) rather than forked
- sunny-quill-9617 — G3 met: the biped's ordinary smoke passes on its own accepted pin
- winter-creek-7660 — G2 met on the create prompt alone, and the void/no-actor-edit rules exercised for real
