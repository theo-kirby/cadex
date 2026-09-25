# ot9 — closing report: Robin balances

Verified against source: 2026-09-22. [Cadex-new]

**Result: the bar is met.** One offboard PPO run, `r3-ppo-1`, produced a
policy that keeps Robin upright for the whole 8.0 s episode on **all ten**
frozen evaluation seeds, at 50 Hz, never firing `fallen`, with a worst peak
tilt of 5.35° against the 30° limit. It was installed through the ordinary
script path, witness-verified by the engine, and reopened in three fresh
processes with the same policy and model identity. Robin's design, task and
reward are the ot8 baseline's, unchanged and measured unchanged.

The contract this is measured against is [`README.md`](README.md) (B1) and
[`contract.json`](contract.json). Every number below comes from a receipt in
[`retained/`](retained/), and `cli/tests/test_ot9_report.py` holds this page
equal to those receipts.

## Accepted identity

| field | value |
|---|---|
| project | `ot9-robin`, a mechanical copy of `ot8-robin` (baseline read-only) |
| final accepted revision | `ae889a9b81e4c9f442f63f70cefaca06883d2c997bacca459b785166157585f8` (= working) |
| final accepted digest | `078ebe8788fc1a8f0a85420b6b2f0d68c96512a78a242ecf1fd732782319847c` |
| policy | `r3-ppo-1.cxpolicy`, sha256 `ef71f370a2f189665f81f96026ba7281d73de332f0927cff7cf7a56944b0a94e` |
| MJCF | `933b1ac6288d61904d8b7245076b96a5e02f13f7e0538ba0b5f49a322b869614` (= baseline pin) |
| task | `1f8c1040d6668a4f86a0cabb5d41d40a2c03bb5b1830d50d10c731d590269246` (= baseline pin) |
| policy receipt | `8df0c267aa5705fd6d70ffb684d8ec36215188a9377cb488333659ee85fe8c67`, witness error 6.9e-8 against 1e-4 over 32 samples |

`rollout_seed` is a script literal, so each evaluation seed was an ordinary
accepted rebuild; the final accepted revision is the seed-9 one. Policy, MJCF
and task are the same on every revision from installation onward.

## Every run

| run | kind | class | receipt | outcome |
|---|---|---|---|---|
| `r2` no-policy hold | `cadex smoke`, zero torque | completed | [`r2-robin-no-policy.json`](retained/r2-robin-no-policy.json) | `fallen` at 0.66 s, 102.234° — ot8's G4 fall reproduced to 1e-9; never a pass by construction |
| `r3-ppo-1` | offboard PPO training | completed | [`r3-robin-train-1.json`](retained/r3-robin-train-1.json) | seed 1001, 300 iterations × 1024 envs, gpu, 308.9 s, exit 0; reward/step 0.9686 at the end |
| iteration 6 | ten-seed evaluation | **interrupted** | [`r4-robin-eval-1.json`](retained/r4-robin-eval-1.json) `interrupted_residue` | left four unaccepted attempts, an empty `eval/r3-ppo-1/` and an uncommitted `latest_candidate`; no trace, no row, no evidence; reran as a whole |
| `r3-ppo-1` eval | frozen ten-seed evaluation | completed | [`r4-robin-eval-1.json`](retained/r4-robin-eval-1.json) | **pass, 10/10** |
| r4 reopen | fresh-process `cadex export` | completed | [`r4-robin-eval-1.json`](retained/r4-robin-eval-1.json) `reopen` | `df58d4ff…` → `6ff77527…`, trace byte-identical to the installing chain's seed 0 |
| B4 measurement | fit, swept fit, inventory | completed | [`r5-robin-fit.json`](retained/r5-robin-fit.json) | equal to ot8's `before/`; see below |
| B5 reopen | fresh-process `cadex export` | completed | [`r6-robin-final.json`](retained/r6-robin-final.json) | `ae889a9b…` → `078ebe87…`, trace byte-identical to seed 9's |
| ADR-405 reopen | fresh-process `cadex export` | completed | [`r7-robin-adr405.json`](retained/r7-robin-adr405.json) | same revision, digest, policy, MJCF, task and trace as the B5 reopen; `script.json`'s stale `accepted_geometry` cleared on its first write |

No training run failed, was interrupted or was void. There was one training
run, and so one candidate.

**Checkpoint choice.** The installed policy is the **final** iteration's
(299), not the best-reward checkpoint (`r3-ppo-1.best.cxpolicy`, sha256
`dc4d392e…`, iteration 255, reward/step 0.9836), which was kept and never
installed or evaluated. The final checkpoint was chosen before evaluation, as
the plan in `r3-robin-train-1.json` states, so no evaluation seed selected it.
The trainer's `episode` figure (409.6 at the end) is not an 8 s episode length
and is cited nowhere as balance evidence.

## The ten seeds

Candidate `r3-ppo-1`, policy `ef71f370`, MJCF `933b1ac6`, task `1f8c1040` on
every row; 400 steps at 50 Hz, 401 solver frames each.

| seed | duration | termination | peak tilt | min chassis height | reward | xy drift | trace |
|---|---|---|---|---|---|---|---|
| 0 | 8.0 s | truncated | 5.352° @ 0.06 s | 105.37 mm | 393.47 | 838 mm | `6db76948` |
| 1 | 8.0 s | truncated | 3.975° @ 0.06 s | 105.13 mm | 393.25 | 847 mm | `9a0cee81` |
| 2 | 8.0 s | truncated | 4.850° @ 0.08 s | 105.82 mm | 393.68 | 829 mm | `aac77a35` |
| 3 | 8.0 s | truncated | 3.793° @ 0.06 s | 105.54 mm | 393.31 | 848 mm | `867dca01` |
| 4 | 8.0 s | truncated | 3.048° @ 0.06 s | 105.55 mm | 393.46 | 843 mm | `d919ce85` |
| 5 | 8.0 s | truncated | 5.130° @ 0.06 s | 105.05 mm | 393.41 | 840 mm | `04068ad1` |
| 6 | 8.0 s | truncated | 4.877° @ 0.06 s | 105.34 mm | 393.63 | 834 mm | `be1651d7` |
| 7 | 8.0 s | truncated | 3.173° @ 0.06 s | 105.36 mm | 393.33 | 845 mm | `1f22e6f9` |
| 8 | 8.0 s | truncated | 3.063° @ 0.06 s | 105.71 mm | 393.62 | 839 mm | `ab0e7265` |
| 9 | 8.0 s | truncated | 2.783° @ 0.06 s | 105.83 mm | 393.33 | 848 mm | `5d64a9ee` |

`fallen` (chassis below 75.25 mm) fired on no seed. Every peak tilt is in the
first 0.08 s, the landing from the task's 3–5 mm reset drop; the tilt reference
is the accepted solved pose, not the reset pose.

## Design, task and reward

**No mechanical, task or reward change was made in ot9.** No product-agent
turn was dispatched, so B4's "every change has a before/after measurement"
holds only because there was nothing to change; it is not an achievement.
The final design was measured anyway (`r5-robin-fit.json`): static fit 0
failing of 378 pairs; swept fit complete and passing on both wheel axles
(±1800° in 100° steps, 0 mm³ common volume, minimum 0.050 mm — the hub-bore
running clearance declared as fit intent, identical in the baseline); all 25
welds touching; 28 components, 23 catalog rows with cited sources. All three
measurement files equal ot8's `before/` once revision and timing keys are
removed. The script differs from the baseline only in the two policy literals,
the parameters only in `policy_on` and `rollout_seed`, and the MJCF is
byte-identical — mass 0.18793 kg, torque ±0.0921825 N·m.

**Standing contact compression**, reported apart and not an intersection: the
wheel spheres touch the floor at 0.000 mm in the solved keyframe; under the
policy the settled MuJoCo contact compression is 0.578–0.582 mm on all ten
seeds (ot8's zero-torque hold: 0.576 mm), with 1.8–2.3 mm transient peaks only
at 0.04–0.06 s, on landing from the reset drop.

## Regressions at the final revision

The final revision is ADR-405's (commit `c2f1c802`), which changed
`src/Mod/cadex/CadexScriptStore.py` after the B5 reopen, so everything was
taken again there ([`r7-robin-adr405.json`](retained/r7-robin-adr405.json)):
`pixi run test-engine`: 2197 passed, 53 skipped, 0 failed.
`pixi run python -m pytest cli/tests`: 939 passed, 1 skipped, 0 failed,
including this report's own tests. Because the store ships in the payload,
the engine was rebuilt and staged and the packaged lifecycle gate
(`test_cadexd_lifecycle.py` against the staged payload) ran: 23 passed, 0
failed. The earlier B5 counts (2196 / 938, gate not required) are kept in
[`r6-robin-final.json`](retained/r6-robin-final.json).

## Remaining defects

1. **Drift.** The policy balances while driving about 0.84 m in nearly the
   same direction on every seed (ending near (−365, 758) mm) and turning. The
   task rewards only being alive, pitch and torque, so nothing holds position
   or heading. The bar does not measure it, and it is not judged a failure,
   but a user would see it as Robin wandering off. A position or velocity
   term in the reward is the obvious next change, and it must come from a
   product-agent turn.
2. **Robustness is unmeasured.** Only reset variation (0–3° tilt, 3–5 mm drop)
   was evaluated. Shove recovery and printability are later rungs and were
   not attempted.
3. **Fixed (ADR-405): `script.json`'s learned `accepted_geometry` was
   stale**, carried from the baseline (README, "The baseline"), keyed on
   `0a6fe0f5…` rather than the accepted `078ebe87…`. The store now drops a
   measurement whose accepted digest has moved on; the fresh reopen's first
   store write cleared it to `null` with the accepted revision and digest
   unchanged ([`r7-robin-adr405.json`](retained/r7-robin-adr405.json)).

## Claim

With this report, B1–B5 all have measured, causally parented evidence, and
ot9 **claims done for critic review**. The owner holds the checkboxes, and
none is ticked here. The ADR-405 record still needs a reconcile pass to fold
it into the state graph; a work iteration may not run one, so it is left to
the loop's reconcile iteration.
