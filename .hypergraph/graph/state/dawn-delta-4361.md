---
node_id: 633b6929-a3e6-5607-b5b0-5310d776f9a1
slug: dawn-delta-4361
title: D3. Training is visible while it runs
created_at: '2026-09-12T14:51:24+00:00'
parents:
- crisp-sun-1239
summary: ''
---
Status: working

## Current

**D3 is repeated on the third fresh project, Lark, in both of its real GPU runs.** During `lark1` a fresh visit to the persistent URL selected the active run without a click and showed seven trainer iterations without reload, each 0.39–1.52 s after the trainer's commit, with reward, loss, episode-estimate and curve updates (evidence in `docs/probes/lark-fresh/training-evidence.json`, test-guarded). The run's 1,052 s wall clock was two thirds checkpoint export (eleven exports at 54–58 s each), a cost worth measuring rather than assuming [rec: upright-tide-4795]. During `lark2`, after the agent's revision, a fresh visit again selected the active run and moved through seven page iterations on its own poll, each 0.24–1.62 s after the trainer's commit (`training84-evidence.json`, test-guarded) [rec: brave-water-4060].

**Wren's revised GPU run completed 240 updates with 240 points in each reward, loss and episode-estimate history.** The persistent browser observed seven updates across iterations 3–11 without reload at committed-to-page delays of 0.50–1.53 s; initial compilation was correctly labelled stale [rec: frosty-birch-2464]. Reed's probe2 showed seven iterations over 12.03 s at 0.23–1.29 s delays under the identity fix [rec: merry-star-6951]. Trainer-reported metrics are not independently measured rollout survival.

ADR-287 supplies atomic progress snapshots, bounded histories, two-second dashboard polling, missing/stale labels and checkpoint integrity checks; starting/training snapshots older than 30 seconds are stale, terminal snapshots do not expire [rec: kind-fountain-5086]. ADR-289 records revision, digest and specs from the manifest before training [rec: lively-gate-6535] [rec: lucid-journey-6875].

**Telemetry is served in two forms, so the run-list poll no longer grows with histories or checkpoints (ADR-321).** `/api/project` carries, per run, a bounded summary — the same validation and `state`, reason, latest metrics, `samples` counts, `checkpoints_reported` and `checkpoint_source` — with no histories and no checkpoint bytes read; `/api/run/<name>` attaches the full histories and the digest-verified checkpoint list for the selected run only. The page polls the list, then the selected run's detail, renders the telemetry panel from one response and shows a `pending` checkpoint line of the same DOM shape until the detail arrives. A 63-run regression (`cli/tests/test_review_history_scale.py`) pins that the current run's history growth (100 → 512 points) still appears within five seconds while a historical run stays selected with its own 512 points and playing video, and that a fresh visit selects a newly running run. Growth of one run's history was already bounded at the source (the trainer decimates each history to 512 points and the server refuses more); the unbounded term was the run count. Any script reading `curve`, `loss_curve`, `episode_steps_curve` or `checkpoints` from the list must use the detail route or `samples` [rec: dusty-fjord-4501].

**Retained-video verification has measured steady-state bounds (ADR-296).** For 64 synthetic sparse 256 MiB files, uncached project polling took 6.59–7.00 s; a process-local cache of at most 256 digest entries reduces unchanged requests to 12–13 ms [rec: young-cedar-2719]. Browser polling permits one pending request per page [rec: neat-vine-2517]; a process-local verification lock lets concurrent clients hash shared unchanged video once, but separate processes do not share coordination and no universal five-second bound follows [rec: dusty-oak-7376].

Judgement: `working`, supported by real multi-update observations on three fresh projects (four Lark and Wren runs plus Reed) and telemetry tests. Histories remain sampled and remote progress mirrors are outside this path; checkpoint hashing was measured on the live Lark server (97 files per two-second poll at 13 runs) and moved off the list poll to the selected run's detail [rec: dusty-fjord-4501]; no owner checkbox edit [rec: merry-star-6951] [rec: brave-water-4060]. **The owner ticked D3 in the charter on 2026-09-13 after run ot5 stopped at iteration 111; the criterion is closed for ot5 with its evidence unchanged, and ot6's charter (ADR-328) supersedes it [rec: patient-pond-3886].**

Charter criterion: **D3. Training is visible while it runs** The biped's real GPU training updates status, iteration, reward and loss histories, episode length and checkpoint availability without a page reload; committed telemetry appears within five seconds under the measured test conditions; missing or stale data is labelled. Evidence: a browser observation spanning multiple actual training updates plus telemetry tests — synthetic data alone cannot tick it. Declared target `gap-d3-training-visible-while-runs` [rec: lucky-comet-0031], introduced with no implementation claimed [rec: dusty-peak-9330].

## Negative knowledge

- [scope: ADR-296 64-file synthetic retained-video workload | confidence: high | evidence: young-cedar-2719] Initial verification, restart, changed files and eviction still require byte reads; histories exceeding 256 cached file versions are outside the measured steady-state result. Sparse files, warm filesystem cache and loopback Chromium do not establish cold-storage, real-video, second-device or universal five-second performance.

## Provenance

- lucky-comet-0031 — the ot5 directive declared this criterion as gap `gap-d3-training-visible-while-runs`
- dusty-peak-9330 — the owner's charter revision (ADR-284) that introduced D1–D9, claiming none complete
- kind-fountain-5086 — ADR-287: retained loss/episode histories, checkpoint integrity, stale/failed/terminal labelling and live polling, with browser and writer tests on fixtures
- long-cove-3626 — ADR-288 closed the final-publication stale-telemetry gap this node's limits listed
- lucid-journey-6875 — first real observation during the fresh biped's GPU probe; the null-identity defect
- lively-gate-6535 — ADR-289: run identity recorded from the manifest before training, fixture-browser-tested
- merry-star-6951 — real multi-update browser re-observation under the identity fix within the five-second threshold
- young-cedar-2719 — measured long-history verification cost and bounded cache with explicit first-read/eviction and synthetic-workload limits
- neat-vine-2517 — ADR-297: one pending browser poll prevents overlapping cold verification
- dusty-oak-7376 — ADR-298: shared cold verification across clients with explicit serialization limits
- sage-tower-6445 — first Wren GPU run, live persistent-browser telemetry and three retained 240-point histories
- frosty-birch-2464 — revised Wren GPU completion and seven real persistent-browser telemetry updates
- upright-tide-4795 — D3 repeated on Lark: seven live iterations on the persistent URL at 0.39–1.52 s
- brave-water-4060 — D3 repeated on lark2: seven live iterations on the persistent URL at 0.24–1.62 s
- dusty-fjord-4501 — ADR-321: summary telemetry on the run list, histories and verified checkpoints per selected run, pending checkpoint line, five-second growth preserved under a 63-run regression
- patient-pond-3886 — the owner ticked D3 on 2026-09-13 after run ot5 stopped at iteration 111; evidence unchanged
