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

**Wren's revised GPU run completed 240 updates with 240 points in each reward, loss and episode-estimate history.** The persistent browser observed seven updates across iterations 3–11 without reload at measured committed-to-page delays of 0.50–1.53 s; initial compilation was correctly labelled stale. Trainer time was 681.823 s, harness wall 750.302 s. These same-machine observations establish neither a universal latency bound nor controlled renderer overhead, and trainer episode estimates are not measured rollout survival [rec: frosty-birch-2464].

**Real fresh-biped training telemetry passes the browser observation under the identity fix.** Probe2 showed seven actual iterations (20–29) over 12.03 seconds without reload; committed-to-page delays were 0.23–1.29 seconds, with reward, loss, episode-length histories and checkpoint availability visible. These are trainer-reported metrics, not independently measured rollout survival. The borrowed model was missing, a separate D2 issue. Full telemetry-containing CLI and engine suites passed [rec: merry-star-6951].

ADR-287 supplies atomic progress snapshots, bounded histories, two-second dashboard polling, missing/stale labels and checkpoint integrity checks. Starting/training snapshots older than 30 seconds are stale; terminal snapshots do not expire. Fixture browser coverage exercises live updates, missing/partial output, stale and terminal states and run switching [rec: kind-fountain-5086]. ADR-289 records revision, digest and specs from the manifest before training; the original probe1 observation exposed the identity defect that prompted it [rec: lively-gate-6535] [rec: lucid-journey-6875].

Reconciliation judgement: `working` is supported by the real multi-update observation under the fix plus existing telemetry tests; the charter specifies no minimum training duration beyond multiple actual updates. This does not edit the owner's checkbox or claim a longer observation. Histories remain sampled, remote progress mirrors are outside this path and checkpoint-hashing overhead is unmeasured [rec: merry-star-6951] [rec: kind-fountain-5086].

**Retained-video verification has measured steady-state bounds (ADR-296).** For 64 synthetic sparse 256 MiB files (16 GiB logical history), uncached project polling took 6.59–7.00 seconds. A process-local cache of at most 256 digest entries reduces unchanged requests to 12–13 ms after the initial 7.041-second verification; three synthetic browser telemetry updates arrived in 1.930–2.023 seconds without reload. This supplements the real-training evidence above; it does not replace it [rec: young-cedar-2719].

Browser polling permits one pending request per page: a 7.2-second blocked verification produced one byte read instead of four across timer ticks [rec: neat-vine-2517]. A process-local verification lock also lets concurrent clients hash shared unchanged video once; the cache remains capped at 256 entries. Cold verification still delays responses, and unrelated checks, including cached lookups, can wait behind the lock. Separate processes do not share coordination; no universal five-second bound follows [rec: dusty-oak-7376].

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
