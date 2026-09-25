---
node_id: 6e90ae97-b45a-5ee5-929d-ff5b236fa770
slug: tidy-arbor-3203
title: B2. Robin's policy is trained and installed on accepted artifacts.
created_at: '2026-09-22T17:39:47+00:00'
parents:
- open-cabin-5892
summary: ''
---
Status: working

## Current

**B2. Robin's policy is trained and installed on accepted artifacts.** At least one offboard PPO run produces a `.cxpolicy` with recorded task and model digests, seed, settings, checkpoint identity and training curve. Store it in a new `ot9-*` project, witness-verify it in the engine, accept it through the ordinary script path, and reopen it in a fresh process with the same policy and model identity. Trainer exit alone is not success. [rec: curious-branch-9704]

**ot9-robin exists [rec: windy-tide-4050].** A mechanical copy of ot8-robin with every B1 pin reproduced (rebuilt digest b933d905); its accepted training bundle is exported (`bundle/`, MJCF 933b1ac6, task 1f8c1040). Receipt: commit 9bba56cf, `docs/probes/ot9/retained/r2-robin-no-policy.json` [rec: windy-tide-4050].

**r3-ppo-1 trained, installed and accepted [rec: hidden-wing-6674].** Offboard PPO on the pinned bundle: seed 1001, 300 iterations x 1024 envs, 308.9 s on GPU, final reward/step 0.9686. `r3-ppo-1.cxpolicy` (sha256 ef71f370) is stored in ot9-robin, declared by a digest edit and engine-verified at rebuild — accepted revision df58d4ff, digest 6ff77527. Receipt: commit 34f310b5, `docs/probes/ot9/retained/r3-robin-train-1.json` [rec: hidden-wing-6674]. The final iteration 299 was installed rather than the best checkpoint (`dc4d392e`, iteration 255), chosen before evaluation [rec: falling-fountain-6090].

**Fresh-process reopen holds the identity [rec: candid-wood-6113].** A new `./cadex export` process rebuilt df58d4ff to digest 6ff77527 with policy ef71f370, model 933b1ac6, task 1f8c1040, witness error 6.9e-8 (tolerance 1e-4); its trace is byte-identical to the installing chain's seed-0 trace. Receipt: commit e5e181c9, `docs/probes/ot9/retained/r4-robin-eval-1.json` [rec: candid-wood-6113]. The same identity reopened again at the final accepted revision ae889a9b (digest 078ebe87) under B5 [rec: falling-fountain-6090].

*Reconcile judgement*: the declared evidence for B2 is now complete; status stays `working` because only the owner ticks the checkbox (the B1 precedent) [rec: candid-wood-6113].

## Negative knowledge

None yet.

## Provenance

- curious-branch-9704 — the criterion as the ot9 charter declares it
- windy-tide-4050 — ot9-robin prepared, bundle exported, no policy yet
- hidden-wing-6674 — r3-ppo-1 trained, stored, engine-verified and accepted; reopen outstanding
- candid-wood-6113 — fresh-process reopen reproduces revision, digest, policy, model, task and trace
- falling-fountain-6090 — checkpoint choice stated; identity reopened again at the final revision
