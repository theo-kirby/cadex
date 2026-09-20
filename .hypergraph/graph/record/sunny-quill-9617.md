---
node_id: 0bdf9be1-71aa-57a5-9545-06a343104e2b
slug: sunny-quill-9617
title: 'G3: the biped''s smoke passes on its own accepted pin'
created_at: '2026-09-20T19:41:56+00:00'
parents:
- honest-ash-4208
summary: ''
---
## What

G3's measurement, end to end, on `ot8-plover` — an independent copy of
`ot7-plover-e` prepared mechanically (every file except the baseline's
`evidence/`, `agent.json` and `.cadex-cli.lock`) and validated against
`docs/probes/ot8/baselines.json` before anything was sent.

One frozen `rebuild.prompt.txt` (`1dbff8e3…`) on `claude-opus-5`. It
**completed on its own in 211.6 s**, spending G3's first slot and leaving
three continuations unspent, with **zero actor design edits**: the script is
still `d14bfbaad9…` byte for byte and the accepted revision still
`0491ead7…`. The accepted **digest** moved, `a00d1aea…` → `9ef44502…`, which
is the same source exported by the ADR-393 engine — exactly the digest ot7's
restore produced and ADR-395 predicted.

**The ordinary `cadex smoke` against the accepted pin passes**, with no
substituted bundle and no re-export probe: MJCF `71b8b39c…`, task `a3a060e5…`,
MuJoCo 3.10.0, verdict `pass` in 34.3 s — finite throughout, penetration 0
breaches with both shins on the floor at 0.3214283954748017 mm against a 0.5 mm
tolerance, support `pass` on a **free** base `c_pelvis` after a
0.2683688948842189 mm drop at 0.18159412499621788° of tilt, the one termination
rule unfired, and the exact-BREP check passing **406 of 406 pairs across 51
samples with its first-frame agreement gate satisfied**.

Also: ADR-401, a retained receipt, one collector fix with a regression, and
the seed-copy preparation written into the contract document.

## Why

The critic named this unit — ladder rung 2, the cheapest closeable bar, one
product turn. It is G3 in `.ouroboros/goal.md` and the frontier node
`empty-arrow-8425`. I did what the message asked, in its order: prepare the
copy mechanically with those three exclusions, let the identity check refuse a
bad one, measure and smoke the baseline before dispatch, re-verify Opus access
and window headroom, then send the prompt and record accepted digest, MJCF
digest, fit, inventory, smoke and a fresh-process reopen.

One deviation worth naming: the first dispatch **crashed before sending
anything**, because `run()` created the attempt's evidence directory with a
non-recursive `mkdir` and the prepared copy has no `evidence/` parent — the ot7
repair seed carried one, so nothing had exercised this. That is a reproduced
failure blocking the experiment, so I fixed it under the charter's
fix-with-a-regression rule rather than papering over it with a manual `mkdir`,
which would have left G4's copy to hit the same wall. No prompt was sent by the
crashed invocation and no slot was touched.

## Method

1. Window probe on `claude-opus-5`: five-hour 15 %, seven-day 16 %, `room:
   true` against the 45 % bound. Probed again by the collector at dispatch: 16 %.
2. `pixi run build-engine`, then `diff -rq src/Mod/cadex build/release/Mod/cadex`
   clean — ADR-390's lesson is that a source/install skew poisons a turn, and
   the installed tree was one comment behind.
3. Copy prepared with `tar --exclude` for the three paths; `validate_seed`
   confirmed script bytes, accepted revision, working revision and accepted
   digest all reproduce the pin.
4. `run.py --run ot8 plover … --model claude-opus-5`. Baseline before the
   prompt: static fit `pass` 406/406, sweep `complete` 4 of 4 joints at 15° with
   0 failing, 24 of 24 attachments touching, inventory 29 components / 24
   catalogued (4 `servo/mg90s`, 4 `servo_horn/mg90s-single_arm`, 4
   `bearing/mr128`, 8 `bolt/m2x6-socket`, 4 `bolt/m2x12-socket`), and the
   ordinary smoke **failing** with ot7's exact words — `initial pose disagrees
   with published clearance: ('c_bearing_hip_l', 'c_bearing_hip_r')` — on MJCF
   `c4c47094…`. That failure is the control the pass is measured against.
5. After the turn: `run.py smoke` (ADR-392, no slot, nothing substituted), then
   two **fresh-process** reopens with restore, `cadex inventory` and `cadex
   clearance`, both `ok: true` under the new pin.
6. Collector fix: `evidence.parent.mkdir(exist_ok=True)` before the exclusive
   `evidence.mkdir()`. `test_a_seeded_attempt_starts_on_a_copy_that_carries_no_evidence`
   fails on the old code with the `FileNotFoundError` and passes on the new,
   and still asserts a second dispatch on the same copy refuses.
7. Suites: `pixi run python -m pytest cli/tests` **892 passed, 1 skipped**;
   `pixi run test-engine` **2196 passed, 53 skipped**. No protocol or payload
   change in this unit, so the packaged gate is G5's, not this unit's.

## Result

**G3's success bar is met, measured.** Accepted digest, MJCF digest, fit,
inventory, reopen and an ordinary accepted-artifact smoke all agree, and the
smoke passes. The biped's pass now belongs to the project rather than to a
probe: ot7 could only get one on a substituted bundle, and this one came from
`cadex smoke` reading the pin. Commit `c0bc852a`, ADR-401, receipt
`docs/probes/ot8/retained/g3-plover-rebuild.json` (7,005 bytes); full evidence
is project-local at `<projects>/ot8-plover/evidence/g3-rebuild/`.
`ot7-plover-e` is untouched — script `d14bfbaad9…`, accepted digest still
`a00d1aea…`. Three continuations stay unspent and the attempt is `paused`; the
charter's bar is *at most* three, so they should stay unspent.

Nothing was grounded, supported, suppressed, weakened or shortened. The base is
free, the rollout is the design's own bounded one, and the only state a
product-agent turn wrote is a re-acceptance of unchanged source.

Two things the next iteration should know. **One**: `script.json`'s learned
`accepted_geometry` block is still keyed on the *old* accepted digest
`a00d1aea…` after re-acceptance, so it is now stale rather than wrong — it
simply will not match and the fallback re-measures. Harmless here because the
byte digest matches; worth a look if a future reopen is slower than expected.
**Two**: G4's copy of `ot7-robin-c` will need the same three exclusions, and
now starts rather than crashing.

Ladder rung 3 is G2, the arm — a create turn from an empty project, which is
the expensive one (ot7's cost 15 window points for 2,695.8 s), so check the
window before starting it. G4's no-slot diagnosis is cheaper and could go
first. The unreconciled tail is 2 nodes.

Dispatch closed: 1 unit — G3 measured and met: the biped's ordinary smoke passes on its own accepted pin after one rebuild turn, with a collector fix and a regression behind it.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot8
- commit: c0bc852acba2bf2df4370ca73f49cb5e9cb54501

## State Impact

- target: empty-arrow-8425 — G3 is met and measured: on the independent copy ot8-plover, one completed rebuild.prompt.txt turn (claude-opus-5, 211.6 s, zero actor design edits, script and accepted revision unchanged, accepted digest a00d1aea… → 9ef44502…) re-accepted unchanged source, and the ordinary cadex smoke against that pin passes in 34.3 s with no substituted bundle — MJCF 71b8b39c…, 0 penetration breaches at 0.321 mm against 0.5 mm, free base resting at 0.182° of tilt, 406 of 406 exact-BREP pairs over 51 samples with the first-frame agreement gate satisfied. The baseline's own smoke, measured first, failed with ot7's exact refusal. Fit 406/406 static and sweep complete on 4 joints, inventory 29 components with 24 catalogued, two fresh-process reopens ok, ot7-plover-e untouched, three continuations unspent. ADR-401, commit c0bc852a, receipt docs/probes/ot8/retained/g3-plover-rebuild.json
- target: wise-aspen-8848 — the G1 contract gained the one thing its first use showed missing: docs/probes/ot8/README.md now states how a seeded design's copy is prepared (every file of the baseline except evidence/, agent.json and .cadex-cli.lock) and that the attempt's own evidence directory is created exclusively while a copy without one is started rather than refused. The collector matches: run() creates the parent with exist_ok=True, pinned by test_a_seeded_attempt_starts_on_a_copy_that_carries_no_evidence, which fails on the old code
