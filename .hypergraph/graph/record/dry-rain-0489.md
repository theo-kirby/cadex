---
node_id: 1e045f20-4e44-5052-bbf3-c2da38762bed
slug: dry-rain-0489
title: The provider refused, and the fall-through found the second walk locked the project out
created_at: '2026-09-08T23:25:27+00:00'
parents:
- humble-star-3313
summary: ''
---
## What

Attempted the overseer's named unit — **one uninterrupted
`./cadex walk --prompt … --resume` on `ot4-quill`, start through review** — and
the provider refused: `claude` is out of usage credits. Fell through in the same
iteration to the plan's short unit 2, the **token-free live section re-measure on
the swing-arm and carriage rigs**, and that measurement found a defect that
stopped the swing-arm walk dead at its third leg.

Fixed it: **neither form of `cadex script` needs the restore pass** (ADR-272).
The second walk of any project that trains under the default policy name
retrains *into the asset its accepted script declares by sha256*, so the stored
script stops re-running and `open_project`'s restore fails — taking with it the
two legs whose whole job is to rewrite that literal.

## Why

Charter criteria **"The walk exists and is tested headlessly"**
(`crisp-reef-5607`) and **"The walk holds on a second mechanism"**
(`swift-dusk-2951`). The overseer named the first; the fall-through was named in
advance for exactly the refusal that happened, so the iteration did not end
empty.

Assumption taken without asking: the fix belongs on the CLI side rather than in
the engine's restore pass. Opening with `restore=False` already exists and is
already used by the review path, so this is the smaller and more reversible of
the two — no build, no protocol, no payload, no engine diff.

## Method

1. `claude usage` and a direct `claude -p` probe both returned *"You're out of
   usage credits."* Ran the walk anyway, so the refusal is observed through the
   product's own path: `runs/uninterrupted-44`, leg `design`, exit 1, the
   provider's sentence carried verbatim into `walk.legs[0].error`, walk exit 1,
   `review` empty, no further leg run. The walk reported it honestly.
2. Walked `ot4-swing2` token-free (seed 0, 5 iterations × 16 envs, CPU, trainer
   timeout 600 s, leg timeout 300 s). Train exit 0 in 38.85 s; **script leg exit
   1: "The restore pass could not re-run the stored script"**; project
   unopenable afterwards by every command that restores.
3. Diagnosed it from `script.json`: the accepted script declares
   `sha256="497f49…"` for `swing_to_angle.cxpolicy`, and `train --put` had just
   overwritten that asset with `3120be…`. `ot4-quill` never hit this because
   every earlier walk there passed a per-run `--name`, leaving the declared asset
   untouched — the trap is the *default*, not the exotic case.
4. `cli/cadex_cli/__main__.py`: `command_script` opens with `restore=False` in
   both forms. Confirmed `restore=False` opens the stranded project (a
   `clearance` call, which already used it, succeeded there).
5. Recovered `ot4-swing2` through the CLI's own repair path — `cadex script`
   read, digest literal rewritten, `cadex script --set` accepted at revision
   `a69bd06…` — then walked it again, and walked `ot4-carriage`.
6. Regression in `cli/tests/test_commands.py`: records the `restore` argument
   each form asks for, against a real engine, and asserts `[False, False]`.
   Verified it **fails on the old source** for both forms.
7. ADR-272 and two `docs/CLI.md` corrections, including the claim that "a walk
   never puts a project there" — a walk interrupted between train and declare
   does exactly that.

## Result

**The uninterrupted walk is still unobserved, and the reason is the provider,
not the walk.** No leg after `design` ran. That criterion stays open.

**The live section re-measure, in objects cut** (the measurement the plan asked
for; not a reward row):

| rig | constant XZ 3.125 | derived | cut / objects |
|---|---|---|---|
| swing-arm (`ot4-swing2`) | 5 of 10 | **−9.2 mm**, `derived`, 8 candidates | **6 of 10** |
| carriage (`ot4-carriage`) | 2 of 2 | **0.0 mm**, `derived`, 5 candidates | **2 of 2** |

ADR-267's counts survive contact: 5 → 6 and 2 → 2, both confirmed on live
geometry. Its *plane* for the swing arm does not — the derivation picks
−9.2 mm, and the six it cuts are not the five plus one: it gains both mount
nuts and **loses `cmp_retainer`**. And the honest half: **`cmp_swing_arm`, the
moving part the rig exists to look at, is still `empty`**, along with the pinch
bolt and nut. That is the same class of miss ADR-267 set out to remove on the
quill, unremoved here, and it is a real gap rather than a rounding error —
coverage orders candidates by *bounds* crossed, and the arm's bounds are
crossed by planes that miss its solid. Render (4 views), inventory (10
components / 7 catalogued; 2 / 0) and clearance (13 offending of 45 pairs
checked; 0 of 1) all read as before on both rigs.

**Both rigs now walk end to end.** `ot4-swing2`: train 38.81, declare 1.28,
rollout 2.52 s, exit 0. `ot4-carriage`: 15.91 / 0.59 / 1.05 s, exit 0.

Gate: `pixi run python -m pytest cli/tests` — **263 passed in 223.03 s** (was
262). No engine, protocol, payload or `shell/` diff, so no other gate applies.
`git diff --check` clean. Commit `df7b0a11`.

Left behind, named rather than fixed: `ot4-quill` carries two uncommitted files
from the refused design leg — `agent.json`'s `model` was overwritten from
`claude-opus-5` to the walk's default `claude-fable-5` by a turn that never ran,
and `script.json` re-staged. Both are churn the next accepted run commits; the
model overwrite by a *failed* turn is worth a look as its own unit.

Criteria advanced: **"The walk holds on a second mechanism"** — the second
mechanism's walk was broken and is now fixed, with both rigs green. Still
missing before either walk criterion ticks: a single uninterrupted
`--prompt … --resume` invocation start-to-review (blocked on provider credits,
not on code), and the section eye still failing to cut the swing arm.

The unreconciled tail is 3 nodes after this one — still small; no action needed.

Dispatch closed: 1 unit — the provider refused the live walk, the fall-through
measurement found the second walk of a project locked it out, and ADR-272 fixed
it.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot4
- commit: df7b0a11f625b391ab42d2c76dbc11b6d3c4ac45

## State Impact

- target: swift-dusk-2951 — the second mechanism's walk was broken: train --put overwrites the asset the accepted script declares by sha256, the restore pass then fails, and cadex script plus script --set failed with it; both forms now open with restore=False (ADR-272) and ot4-swing2 and ot4-carriage each walk end to end
- target: crisp-reef-5607 — the single uninterrupted walk --prompt … --resume was attempted and refused by the provider (out of usage credits); the walk reported it as leg design exit 1 with the provider's sentence verbatim and ran no further leg, so the criterion stays open on credits rather than on code
- target: chilly-union-8972 — command_script opens with restore=False in both forms; a real-engine regression records the restore argument each form asks for and fails on the old source in both; cli/tests 263 passed
- target: damp-moon-9297 — the derived section is measured live on two more rigs: swing-arm -9.2 mm cutting 6 of 10 (constant cut 5) but still missing cmp_swing_arm, carriage 0.0 mm cutting 2 of 2, both offset_source derived
