---
node_id: 958c3eac-505d-5aae-827d-318033002cf0
slug: empty-arrow-8425
title: G3. The biped's smoke is measured against its accepted artifacts
created_at: '2026-09-20T18:48:22+00:00'
parents:
- ancient-vine-9908
summary: ''
---
Status: working

## Current

**G3's success bar is met and measured [rec: sunny-quill-9617].** Work happened on `ot8-plover`, an independent copy of `ot7-plover-e` prepared mechanically — every file except the baseline's `evidence/`, `agent.json` and `.cadex-cli.lock` — and validated against `docs/probes/ot8/baselines.json` (script bytes, accepted revision, working revision and accepted digest all reproducing the pin) before anything was sent [rec: sunny-quill-9617].

**One frozen `rebuild.prompt.txt` (`1dbff8e3…`) on `claude-opus-5` completed on its own in 211.6 s**, spending G3's first slot and leaving three continuations unspent, with **zero actor design edits**: the script is still `d14bfbaad9…` byte for byte and the accepted revision still `0491ead7…`. The accepted **digest** moved, `a00d1aea…` → `9ef44502…` — the same source exported by the ADR-393 engine, which is exactly the digest ot7's restore produced and ADR-395 predicted [rec: sunny-quill-9617].

**The ordinary `cadex smoke` against that accepted pin passes**, with no substituted bundle and no re-export probe [rec: sunny-quill-9617]: MJCF `71b8b39c…`, task `a3a060e5…`, MuJoCo 3.10.0, verdict `pass` in 34.3 s — finite throughout; penetration 0 breaches with both shins on the floor at 0.321 mm against a 0.5 mm tolerance; support `pass` on a **free** base `c_pelvis` after a 0.268 mm drop at 0.182° of tilt; the one termination rule unfired; and the exact-BREP check passing **406 of 406 pairs across 51 samples with its first-frame agreement gate satisfied**. The baseline's own smoke, measured before the prompt, **failed with ot7's exact words** — `initial pose disagrees with published clearance: ('c_bearing_hip_l', 'c_bearing_hip_r')` on MJCF `c4c47094…` — and that failure is the control the pass is measured against [rec: sunny-quill-9617].

**The rest of the recorded evidence agrees on one pin [rec: sunny-quill-9617].** Baseline fit before the turn: static `pass` 406/406, sweep `complete` on 4 of 4 joints at 15° with 0 failing, 24 of 24 attachments touching, inventory 29 components / 24 catalogued (4 `servo/mg90s`, 4 `servo_horn/mg90s-single_arm`, 4 `bearing/mr128`, 8 `bolt/m2x6-socket`, 4 `bolt/m2x12-socket`). After the turn, two **fresh-process** reopens with restore, `cadex inventory` and `cadex clearance` both returned `ok: true` under the new pin. ADR-401, commit `c0bc852a`, receipt `docs/probes/ot8/retained/g3-plover-rebuild.json` (7,005 bytes); full evidence is project-local at `<projects>/ot8-plover/evidence/g3-rebuild/`.

**Nothing was grounded, supported, suppressed, weakened or shortened [rec: sunny-quill-9617].** The base is free, the rollout is the design's own bounded one, and the only state a product-agent turn wrote is a re-acceptance of unchanged source. `ot7-plover-e` is untouched — script `d14bfbaad9…`, accepted digest still `a00d1aea…`. The attempt is `paused` with three continuations unspent, and the charter's bar is *at most* three, so they stay unspent.

This is what ot7's F7 (`rapid-grove-9687`) could not close on its own terms: its biped smoke passed on the model the accepted script exports under today's engine, with the pin's own model as the failing control — a verdict taken off a re-export rather than a `cadex smoke` receipt [rec: humble-fox-6370]. The pass now belongs to the project rather than to a probe [rec: sunny-quill-9617].

*Reconcile judgement*: `working` rather than `open`, on the ot7 precedent that a criterion whose evidence exists is `working` while the human owns the checkbox. Every element G3's bar enumerates — accepted digest, MJCF digest, fit, inventory, smoke, fresh-process reopen — has a recorded measurement, and they agree [rec: sunny-quill-9617].

## Negative knowledge

- [scope: `ot8-plover`'s `script.json` after re-acceptance | confidence: high | evidence: sunny-quill-9617] The learned `accepted_geometry` block is still keyed on the *old* accepted digest `a00d1aea…`, so it is now stale rather than wrong: it will not match, and the fallback re-measures. Harmless here because the byte digest matches — worth looking at if a future reopen is slower than expected.

## Provenance

- keen-stone-1720 — the criterion as the ot8 charter declares it
- humble-fox-6370 — why ot7's F7 pass is not a smoke receipt against the pin
- sunny-quill-9617 — G3 measured and met on the independent copy `ot8-plover`: one completed rebuild turn with zero actor design edits, the predicted digest move, and an ordinary `cadex smoke` pass against the pin with the baseline's failing smoke as its control
