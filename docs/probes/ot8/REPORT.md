# ot8 closing report — the unassisted-design evidence, finished

Verified against source: 2026-09-20. [Cadex-new]

**This is G6, the run's last unit under the ot8 charter (ADR-399): one row per
experiment, the evidence for G1–G5, every call that was not an attempt, and
what remains open.**

ot7 designed three machines with no human design feedback and left three
things it had not established (`../ot7/REPORT.md`). The arm reached zero
failing fit checks with **two servos and two horns modelled by hand** instead
of placed from the catalog. The biped's smoke passed only on a model
**re-exported outside the accepted pin** (ADR-395), so nobody could point at
the project and say it holds. And the balancer's ordinary holding smoke
**failed** with no measured account of why. ot8 is those three gaps, each as a
bounded experiment with its own new identity, run against today's product
under a contract frozen before any of them started.

**ot8 is not ot7 and does not re-run it.** ot7's F4–F7 are exhausted, their
slots are spent and their receipts stand unedited; the three ot7 projects were
read read-only throughout this run and are hashed before and after in G5's
receipt. G2 designed a new arm from an empty project and used ot7's arm for
comparison only. G3 and G4 worked on **independent mechanical copies** of the
ot7 biped and balancer, prepared without their receipts or their session
state, and validated against [`baselines.json`](baselines.json) before
anything was sent.

**Three dispatches were made in total. Two reached the model and ended on
their own, one was void and spent nothing, and the third experiment dispatched
nothing at all.** Two of the three bars are met, on the initial prompt in both
cases, with **six of six continuations unspent** and **zero actor design
edits** anywhere. The third is not a design success and is not reported as
one: the balancer's smoke failure is a **measured control requirement**, and
the experiment stopped on it rather than passing it.

## Achieved success bars, and the outcome that is not one

These are different kinds of result and the report keeps them apart.

- **G2 (the arm) and G3 (the biped) met every count of their bars**, measured
  on the accepted artifacts, on one product turn each. Those are design
  successes.
- **G4 (the balancer) is control-blocked.** Its experiment finished; its
  design did not succeed. A wheeled inverted pendulum resting on a two-point
  line has no static margin about that line at any mass distribution, so
  holding it upright is a closed loop rather than a shape. The diagnosis is
  the deliverable; the behaviour is not, and nothing was grounded, supported,
  suppressed, weakened or shortened to make it read otherwise.

**A finished experiment is not a design success.** G4's row below says
`control-blocked`, and it means the smoke still fails.

## One row per experiment

Static counts are failing pairs of pairs checked, in dispatch order.
"Turns" counts only calls that reached the model and ended on their own; the
void call in G2's chain is not a turn and is listed under
[every call that was not an attempt](#every-call-that-was-not-an-attempt).

| Design / criterion | Outcome | Prompts (frozen) | Turns | Model | Continuations used | Accepted identity | Static fit per turn | Final static | Final swept | Smoke | Inventory | Actor edits | Remaining defects | ot7 comparison |
|---|---|---|---:|---|---:|---|---|---|---|---|---|---:|---|---|
| **Heron arm / G2** | **success — every bar met** | [`heron.create.prompt.txt`](prompts/heron.create.prompt.txt) `bcda5af5…`, byte-identical to ot7's; `continue-1..3` frozen and unsent | 1, on `ot8-heron-b` | `claude-opus-5` | **0 of 3** | revision `957044ae…` = working revision, digest `9cec3cc6…` | create **0** of 105 | **pass, 0 of 105** — 105 clear, 0 intersection, 0 below clearance, 0 unknown | **pass** — complete, 2 of 2 joints at 10°, 0 skipped, 0 failing | **pass** — ordinary `cadex smoke` on the pin; hold, 1.0 s, 51 samples, MuJoCo 3.10.0, `failing: []`, all five checks, MJCF `183fabff…` | 15 components; `servo/mg90s` ×2, `servo_horn/mg90s-single_arm` ×2, `bearing/mr128` ×2, `bolt/m2x6-socket` ×4, `bolt/m2x16-socket` ×2; `derived_catalog_sources` **empty**; uncatalogued exactly `base`, `upper_arm`, `forearm` | **0** | **none against the bar.** ot7's two modified servos and two modified horns are gone: all four purchased parts are unmodified catalog rows and the only uncatalogued sources are the three printed structural parts | `ot7-heron-c` (`58ff41b4…`) carries **no `servo` row and no `servo_horn` row at all** and lists `servo_shoulder_solid`, `servo_elbow_solid`, `horn_shoulder_solid`, `horn_elbow_solid` among its uncatalogued sources — same ask, same 15 components, four purchased parts hand-modelled, and it took the create prompt plus all three continuations |
| **Plover biped / G3** | **success — every bar met** | [`rebuild.prompt.txt`](prompts/rebuild.prompt.txt) `1dbff8e3…`; `continue-1..3` frozen and unsent | 1, on `ot8-plover` | `claude-opus-5` | **0 of 3** | revision `0491ead7…` unchanged; digest `a00d1aea…` → `9ef44502…` | seed 0 of 406 → **0** of 406 | **pass, 0 of 406** | **pass** — complete, 4 of 4 joints, 0 failing | **pass** — ordinary `cadex smoke` on the pin, **no substituted bundle**; MJCF `71b8b39c…`, task `a3a060e5…`, MuJoCo 3.10.0; 0 penetration breaches at 0.321 mm against 0.5 mm; support `free` on `c_pelvis`, 0.268 mm drop, 0.18° tilt; 1 termination rule unfired; exact BREP **406 of 406 pairs over 51 samples**, first-frame agreement satisfied | 29 components, 24 catalogued: `servo/mg90s` ×4, `servo_horn/mg90s-single_arm` ×4, `bearing/mr128` ×4, `bolt/m2x6-socket` ×8, `bolt/m2x12-socket` ×4 | **0** | **none against the bar.** One non-blocking observation: `script.json`'s learned `accepted_geometry` block is still keyed on the pre-rebuild digest `a00d1aea…`, so it is stale rather than wrong and the fallback re-measures | ot7's F7 smoke passed only on a model the re-export probe substituted (ADR-395); the baseline's own smoke refuses before it runs — `initial pose disagrees with published clearance: ('c_bearing_hip_l', 'c_bearing_hip_r')` on MJCF `c4c47094…`. ot8's pass comes from `cadex smoke` reading the accepted pin |
| **Robin balancer / G4** | **control-blocked — not a design success** | [`resolve.prompt.txt`](prompts/resolve.prompt.txt) `01694274…` and `continue-1..3`, **all four frozen and none dispatched** | **0**, on `ot8-robin` | `claude-opus-5` (none dispatched) | **0 of 3** | revision `0b438561…`, digest `b933d905…`, unchanged — nothing was accepted | seed 0 of 378; no turn | **pass, 0 of 378** | **pass** — complete, 2 of 2 joints, 0 failing | **fail** — support `comp_chassis` 102.2° against a 30° limit, the design's own `fallen` rule fired at 0.660 s, 4 penetrations; the exact-BREP check **passes**, 378 pairs over 51 samples | 28 components, 23 catalogued: `gearmotor/pololu-2367` ×2, `board/pi-zero-2-w` ×1, `heat_insert/m2-standard` ×10, `bolt/m2x4-socket` ×8, `bolt/m2x6.5-socket` ×2 | **0** | **the machine cannot hold itself upright without feedback** — the missing control contract is below, and supplying it is outside this charter. Secondary, non-blocking: a 0.576 mm standing wheel compression against a 0.5 mm tolerance, which follows the applied load and is the engine's contact spring rather than geometry | ot7 reported this smoke failing and gave no account of why; ot8 rules out a geometry or export mismatch and a design defect by measurement, confirms the missing feedback control, and states the contract it would take |

The receipts behind each row are the JSON files under
[`retained/`](retained/), each carrying its prompt digest, transcript digest
and measured counts; the full evidence stays project-local and is cited there
by path and digest.

## The slot ledger

Every dispatch lands in exactly one column of the ledger the contract froze
([`README.md`](README.md#the-slot-ledger)), and only the first column spends
anything. **Three dispatches, two slots spent, six of six continuations
unspent.**

| Criterion | Design | Dispatches | Completed (slot spent) | Void (no slot) | Interrupted | Unreached | Continuations used | Continuations unspent |
|---|---|---:|---|---|---:|---:|---:|---:|
| **G2** | Heron arm | 2 | 1 — `heron.create.prompt.txt` on `ot8-heron-b`, 3,015 s, exit 0 | 1 — the same prompt on `ot8-heron`, cut off mid-turn by a five-hour session limit after 51 model messages (ADR-355) | 0 | 0 | **0** | **3** |
| **G3** | Plover biped | 1 | 1 — `rebuild.prompt.txt` on `ot8-plover`, 211.6 s, exit 0 | 0 | 0 | 0 | **0** | **3** |
| **G4** | Robin balancer | **0** | 0 — nothing was dispatched | 0 | 0 | 0 | **0** | **3** |
| **total** | — | **3** | **2** | **1** | **0** | **0** | **0** | **9** |

G4 dispatched nothing because the freeze says so: its initial prompt is sent
**only if** the actor's own no-slot diagnosis finds an actionable design
defect, and the diagnosis instead reproduced an out-of-scope control
requirement. That experiment's project is `paused` with all four of its
prompts unspent.

Three further measurements spent no slot and are not calls: G1's window probe
(no project, no tools, no MCP server — ADR-358, ADR-364), G3's and G2's
ordinary `cadex smoke` on the accepted pin (ADR-392), and G4's whole
diagnosis.

## Every call that was not an attempt

One dispatch reached no design result. It spent no slot and kept all of its
evidence, and that evidence is neither a design failure nor a design success.

| # | Criterion | Project | Kind | What happened | Receipt |
|---:|---|---|---|---|---|
| 1 | G2 | `ot8-heron` | void | a five-hour session limit (429) cut the create turn off mid-turn after 2,867 s and 51 model messages, at a window already 20 % spent; transcript `60881a1a…` | [receipt](retained/g2-heron-create.json) |

None spent a slot. The project was closed under ADR-355 and the same frozen
prompt retried in `ot8-heron-b`, which was dispatched into a fresh window at
1 % and completed. `ot8-heron` (no suffix) is a closed void project and may
never be read as an outcome in either direction.

## Implemented checks and evidence for G1–G5

| Criterion | What it asked | Evidence |
|---|---|---|
| G1 | a frozen, bounded experiment contract, written before any product turn | [`README.md`](README.md) (baselines, prompts, bars, slot ledger), [`prompts/`](prompts/README.md) (six files, each pinned to its digest), [`baselines.json`](baselines.json), the access reading at the freeze [`retained/g1-window-probe.json`](retained/g1-window-probe.json); tests `cli/tests/test_ot8_prompts.py` and `cli/tests/test_ot8_runner.py` (slot accounting, seeded-copy validation, and that an ot8 attempt never writes an ot7 receipt); ADR-400; records [keen-stone-1720](../../../.hypergraph/graph/record/keen-stone-1720.md) (the charter) and [honest-ash-4208](../../../.hypergraph/graph/record/honest-ash-4208.md) |
| G2 | the arm's catalog-provenance gap, measured in a fresh project on ot7's create prompt | [`retained/g2-heron-create.json`](retained/g2-heron-create.json) — the void call, the completed turn, accepted identity, static fit, swept fit, attachments, inventory, ordinary smoke, and the ot7 comparison; record [winter-creek-7660](../../../.hypergraph/graph/record/winter-creek-7660.md) |
| G3 | the biped's smoke against its own accepted artifacts, with no substituted bundle | [`retained/g3-plover-rebuild.json`](retained/g3-plover-rebuild.json) — the pinned seed, the baseline's refused smoke, the completed rebuild turn, the passing ordinary smoke and two fresh-process reopens; ADR-401 with its collector fix and regression; record [sunny-quill-9617](../../../.hypergraph/graph/record/sunny-quill-9617.md) |
| G4 | an actionable measured diagnosis of the balancer's failed smoke | [`retained/g4-robin-diagnosis.json`](retained/g4-robin-diagnosis.json) — the failing smoke with its per-check breakdown, the MJCF-agreement and exact-geometry measurements, the mass/lever/torque numbers, the replayed free response and the control contract; the tool [`runner/balance_diagnosis.py`](runner/balance_diagnosis.py) pinned by `cli/tests/test_balance_diagnosis.py`; ADR-402; record [stormy-sand-3570](../../../.hypergraph/graph/record/stormy-sand-3570.md) |
| G5 | the regression floor at the final revision | [`retained/g5-retention.json`](retained/g5-retention.json) — both full suites, the packaged lifecycle gate and the packaged licensing audit against the staged payload, the two ADR-398 repeated-restore regressions named and passing, and ten clean restore/reopen phases across five independent copies; record [hidden-delta-8675](../../../.hypergraph/graph/record/hidden-delta-8675.md) |

### G4: the missing control contract

Stated from the design's own task bundle, so that a later run can supply it
without re-deriving it. The balancer already **exports** everything the loop
would read: nine sensors, twenty channels, addresses 0–19 — chassis
quaternion, angular velocity and position, both wheel velocities, the subtree
centre of mass and its velocity, and both actuator forces.

| the loop would | value |
|---|---|
| command | two wheel torques, ±92.18 N·mm each (184.365 N·mm about the topple axis) |
| at | 50 Hz, a 0.02 s control interval |
| against | an unstable eigenvalue of 11.59 /s — an 86.3 ms time constant, **4.3 samples per e-fold**, **1.26×** of tilt growth per control interval |
| holding | `chassis_pos_z ≥ 75.25 mm`, i.e. **45.573°** of tilt (the chassis origin stands 107.5 mm above the contact line), and inside the smoke's 30° support limit |
| for | the declared 8 s episode, from resets that already vary tilt to 3° and height by 3–5 mm |
| with authority | 184.365 N·mm available against **0.672 N·mm** required to hold the accepted pose |

The only things that could supply it are a trained policy or a hand-authored
feedback controller, and this charter forbids both. The experiment ends here.

## G5: the regression floor, measured

At source revision `39e02390`, with the staged payload
`build/engine/cadex-engine-0.0.0-linux-x64` (manifest `c6687a97…`, binary
`a5954c19…`) whose 57 top-level Python files compare **equal** to the source
tree:

| suite | result |
|---|---|
| `pixi run python -m pytest src/Mod/cadex/cadex_tests` | **2,196 passed, 53 skipped, 0 failed** in 296.0 s |
| `pixi run python -m pytest cli/tests` | **903 passed, 1 skipped, 0 failed** in 553.3 s |
| `CADEX_ENGINE_ROOT=<payload> … test_cadexd_lifecycle.py` | **23 passed, 0 skipped** in 19.6 s |
| `CADEX_ENGINE_ROOT=<payload> … test_licensing_compliance.py` | **11 passed, 0 skipped** |
| ADR-398 repeated-restore retention | **green**, named and PASSED inside the packaged gate, with `test_geometry_digest.py` (20 passed) beside it |

Every skip is a by-design gate, not a silenced failure: 34 offboard-trainer
tests needing jax/mjx (ADR-084), 5 needing a real Blender sandbox, the rest
payload- or environment-gated, and one CLI test needing a private network
address that is never committed.

Five independent copies — `ot7-heron-c`, `ot7-plover-e`, `ot7-robin-c`,
`ot8-heron-b` and `ot8-plover` — were each restored and then reopened in a
second process, ten phases in all. Every phase agrees with what the receipts
published: accepted revision, accepted digest and script digest all match, the
accepted attempt's `result.json` is **byte-identical after every open**, and
`restore_vs_reopen_pair_differences` is **0** on all five.
**Every measured difference is explained**, and there are exactly two of them:
`latest_candidate` and `updated_at` change on every open, because opening a
project rebuilds from the script and records the attempt it just made. No identity field moved. All
five source projects are hashed before and after and are unchanged.

## G6: what this run established, and what remains open

**What ot8 established.**

1. **The arm's catalog-provenance gap is closed by the product.** The same
   nine-thousand-byte create prompt that produced four hand-modelled purchased
   parts in ot7 produced four unmodified catalog parts in ot8, on the initial
   turn, with zero failing static and swept checks and a passing smoke. No
   repair prompt, no continuation and no actor edit was involved.
2. **The biped holds on its own pin.** The smoke that ot7 could only obtain
   from a substituted bundle now comes from `cadex smoke` reading the accepted
   artifacts, after one product-agent rebuild of **unchanged source** — the
   script digest is byte-for-byte the baseline's and only the export moved.
3. **The balancer's failure has a cause, and it is not a defect.** Geometry
   and export agree to 1.35e-29 mm; the motors carry a 274× margin over the
   torque holding the pose costs; the free response reproduces the published
   fall to the receipt's own digits. The requirement is feedback, and it is
   written down above rather than guessed at again.
4. **The floor holds.** Both suites, the packaged gate and the packaged
   licensing audit are green at the final revision, and every design this run
   touched still opens to the pins its receipts published.

**What remains open.**

- **Nine unspent continuations** — three on each design. G2 and G3 met their
  bars without them and the charter's bar is *at most* three, so they stay
  unspent under this freeze; G4's three are unspent because its experiment
  stopped on a control requirement rather than a repair.
- **The balancer still falls.** It needs a controller, and supplying one needs
  either policy training or a hand-authored feedback controller — both
  forbidden here. This is the one bar ot8 did not meet, and it is recorded as
  a control-blocked outcome, never as a success.
- **A 0.576 mm standing wheel compression** on the balancer, against a 0.5 mm
  tolerance. It follows the applied load and is the engine's contact spring
  (`CadexDynamics.CONTACT_TIMECONST_S = 0.02 s`, which the script surface does
  not expose), not geometry intersecting the floor. It is reported as a
  secondary observation; repairing it could not change a verdict that fails on
  support and termination regardless.
- **A stale learned-geometry key** on `ot8-plover`: `script.json`'s
  `accepted_geometry` block is still keyed on the pre-rebuild digest, so it
  will not match and the fallback re-measures. Harmless, and worth a look if a
  reopen is ever slower than expected.
- **ot7's own open items are unchanged by this run** and stay where ot7 left
  them (`../ot7/REPORT.md`): its unspent continuations, its discrete slot
  accounting and its unexecuted evidence are ot7's record, not ot8's.

**Done is claimed here**, under the charter's exhaustion policy: G1–G5 each
have a record with measured evidence, this report carries every outcome, and
the owner owns the checkboxes. Nothing above claims the balancer succeeded.
