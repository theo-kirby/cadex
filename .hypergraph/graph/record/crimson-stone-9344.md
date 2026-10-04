---
node_id: 23fc3c66-e6df-5079-b82e-44215ab28f89
slug: crimson-stone-9344
title: 'orun2 R1: frontier clean-up — supersede stale earlier-run and shell-moot nodes; R1 items audited on disk'
created_at: '2026-10-04T01:26:30+00:00'
parents:
- amber-moon-9415
summary: ''
---
## What

R1's last open piece, the state-graph frontier clean-up: I checked every R1 doc item against the files on disk, then superseded eight stale nodes from earlier runs and the deleted shell, each with its reason, through this record's State Impact.

## Why

The critic named R1 next. AGENTS.md is already 215 lines, which meets the ≤216 bar, so it was **not** rewritten again (critic's fix-first item: that step is dropped from the plan). The critic asked for each R1 item to be checked on disk, then for stale criteria from earlier runs to be superseded with reasons, "then reconcile until check exits 0". **Deviation:** this dispatch forbids the reconcile skill in a work iteration, so this record only declares the supersessions. The next reconcile pass folds them. I ran `hypergraph check` read-only.

## Method

On-disk audit of R1 (no edits needed):
- `docs/VISION.md`: ADR-500 three-part framing at l.13; "dashboard is the only UI" at l.74; the non-goal that named the Rust shell now says it is not coming (l.197–199).
- `README.md`, `docs/ARCHITECTURE.md`, `docs/INTEGRATION.md`: shell references appear only as history with ADR-498/496 citations.
- `docs/ROADMAP.md`:
  - Phase 6 is "historical since ADR-498" (l.215);
  - Phase 12 is "superseded by ADR-500 … a desktop app that copies the dashboard" (l.735);
  - Phase 13b's shell half is `[x]` "closed by deletion" (l.834).
- The direction-change ADR is ADR-500. It has the bet, "What it costs" and "What would make the owner reverse it".
- `docs/BLENDER.md`, `BLENDER-TREE.md` and `BLENDER-RECIPES.md` are in `docs/history/` only.
- `docs/DASHBOARD.md` exists and `docs/REVIEW-DESIGN.md` is gone (ADR-501).
- AGENTS.md is 215 lines.
- The charter's named stale criteria are already `superseded` in STATE.md through `light-path-5130`:
  - ot7 F4–F7 and F10;
  - ot10 A5 and A7;
  - orun1 C1.

Then I read the body of every `working` node under an earlier run's charter or under the shell. The rule I applied:
- A criterion whose claim is **met with evidence** stays `working`, even if its run is archived and the owner never ticked it. Superseding met work would hide it.
- A node is superseded when it is **unfinished on an archived run**, **moot because the shell is deleted**, or a **run root left `working` after its run ended**. The last case follows the precedent of the ot6 and ot7 roots.

## Result

Superseded, as declared below:
- `loyal-ocean-0768` (orun1 D3): its transcript-driven catalog clause waited on D4 runs that never confirmed, and orun1 is archived (`3e345fd2`).
- `salty-fox-7376` (orun1 D4): it had trials only and no confirmation. The orun1 reconcile explicitly left it to this clean-up.
- `happy-key-3312` (GUI parity) and `simple-willow-8989` (.blend file lifecycle): the app they describe was deleted (ADR-498).
- `wild-comet-8096` (`hide_render` shell bug): the code it fixed is deleted.
- `witty-spark-2613` (three modes): its GUI-attached mode no longer exists.
- `ancient-vine-9908` and `open-cabin-5892` (the ot8 and ot9 roots): their runs ended and merged.

Kept `working` because they are met on evidence:
- **ot11 R1** (`smooth-fountain-9832`: 10/10 seeds and the judge bar met). **This differs from the critic**, which named ot11 R1 as stale. Its title says "Open charter criterion", but its body is a passed, pre-registered confirmation.
- ot11 P1–P4, R2, R3 and C1;
- the ot10 criteria;
- orun1 F1, D1 and D2;
- the ot5, ot6, ot8 and ot9 children.

Concerns:
- Two unreconciled records now sit in the tail, and the next reconcile must fold these supersessions.
- R1 has evidence for every item once that pass runs.
- The critic's next unit after this one is W1's full walk.

Dispatch closed: 1 unit — R1 audited on disk (all items met), 8 stale nodes superseded with reasons

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/orun2
- commit: 26880abd77f235604782b5039c88bafae3b2fbe6

## State Impact

- target: loyal-ocean-0768 — superseded: orun1 archived (3e345fd2); the transcript-driven catalog clause waited on D4 confirmations that never ran; base-plus-styles charter carries the design bar next
- target: salty-fox-7376 — superseded: orun1 archived (3e345fd2) with trials only and no confirmation turn; the orun1 reconcile deferred this to orun2 R1's clean-up
- target: happy-key-3312 — superseded: the GUI app it brought to parity is deleted (ADR-498); the dashboard is the only UI (ADR-500)
- target: simple-willow-8989 — superseded: .blend open/save/Save-As belonged to the deleted shell (ADR-498); the project directory is the truth (ADR-500)
- target: wild-comet-8096 — superseded: the hide_render defect lived in the shell's hydration code, deleted by ADR-498
- target: witty-spark-2613 — superseded: its GUI-attached mode was the deleted shell (ADR-498); headless and remote-training modes stay covered by crisp-reef-5607 and training/SETUP.md
- target: ancient-vine-9908 — superseded: run ot8 ended and merged; its G1–G6 children keep their recorded evidence (ot6/ot7 root precedent)
- target: open-cabin-5892 — superseded: run ot9 ended and merged (8a7a6919); its B1–B5 children keep their recorded evidence (ot6/ot7 root precedent)
- target: eager-sea-3906 — every R1 item audited on disk and met (VISION, README, ARCHITECTURE, INTEGRATION, ROADMAP 6/12/13b, ADR-500, BLENDER docs in history, DASHBOARD.md, AGENTS.md 215 lines); frontier clean-up declared here; evidence complete pending reconcile and the owner's tick
