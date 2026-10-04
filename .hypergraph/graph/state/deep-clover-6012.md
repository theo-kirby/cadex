---
node_id: 5c38ed96-b7d8-5c80-9395-fb3e153b6597
slug: deep-clover-6012
title: D10. The persistent operator dashboard stays current
created_at: '2026-09-12T21:20:29+00:00'
parents:
- crisp-sun-1239
summary: ''
---
Status: superseded

## Current

**Superseded: the operator dashboard tooling is deleted.** `tools/operator_review.py` and `docs/OPERATOR-REVIEW.md` are removed and no product file names Ouroboros (ADR-536); the dashboard is now the read-only `cadex app` [rec: still-ivy-2146]. The current dashboard is on `sweet-bloom-8352`. The ot5 history below stands as recorded; the per-switch narrative is in the record graph (`happy-gate-9091` and earlier).

Judgement: `working`, and the owner ticked D10 on 2026-09-13 [rec: patient-pond-3886]. The stable URL has served through four project switches (Reed, Wren, Wren copy, Lark, Lark copy) and real experiments on each, including interruptions, dashboard and engine restarts with and without a trainer active, server upgrades deployed by restart and re-verified on the deployed change (ADR-318, 319, 321, 322 and its correction, 323, 324, 325, 326, 327), failures, fault probes on isolated copies and recoveries. Every observation is a same-machine private-address check — headless browser or HTTP — not second-device evidence [rec: peaceful-walrus-0642] [rec: easy-badger-5812] [rec: empty-vine-5860]. **The owner ticked D10 in the charter on 2026-09-13 after run ot5 stopped at iteration 111; the criterion is closed for ot5 with its evidence unchanged, and ot6's charter (ADR-328) supersedes it [rec: patient-pond-3886].**

Charter criterion: fresh visits select active training first, otherwise the latest attempt including failed/interrupted work, with truthful identity, available curves/videos and explicit pending/stale/failed states; preserve historical browsing and playback with a route back; keep the stable URL serving between iterations; verify and publish identity at experiment start/completion and every working-project switch. Acceptance requires persistent-URL browser evidence across a real experiment and a working-copy switch plus current-selection and historical-preservation regressions. Declared target `gap-d10-persistent-operator-dashboard-stays` [rec: simple-raven-5405].

## Negative knowledge

- [scope: the persistent operator service on this machine | confidence: high | evidence: happy-gate-9091] A restart done by hand from a tmux session leaves the port served by a bare session-scoped process that no unit supervises, which is what iteration 104 did and iteration 109 found. ADR-325: the URL is served by the `cadex-operator-review` user unit, never a bare process.
- [scope: CLI advice quoted on the dashboard | confidence: high | evidence: lean-orchard-0769] `cadex` commands default `--project` to `./.cadex`, so advice that says 'from the project directory' without `--project` creates a nested project inside the served copy; every quoted command names `--project <project-dir>`.

## Provenance

- simple-raven-5405 — operator directive introduces D10 and persistent dashboard obligations
- falling-ocean-4411 — working-copy switch to Reed and current-selection/historical regressions
- royal-arrow-2065 — service stays current through the shared-scene renderer update
- fair-crow-5108 — persistent URL observed at experiment start, during, at completion and after restart; render overhead measured
- lucky-bramble-8274 — persistent shin55-final revisit with identity, playback and history checks
- soft-aspen-5095 — persistent current-design pointer interaction and historical checkpoint revisit
- mild-river-8224 — deliberate switch to Wren and verified current accepted empty-run view
- late-walrus-6383 — persistent Wren display survives two in-place restores
- sage-tower-6445 — active-first selection and historical playback throughout first Wren GPU experiment
- honest-path-3451 — accepted 105 mm feet and historical original-policy identities remain explicit at the stable URL
- frosty-birch-2464 — persistent revised-training start, active checkpoint and final selection verified
- smooth-pine-9795 — unchanged current and historical reviews verified after provider refusals
- crimson-bell-5375 — stable operator URL switched to independently reviewed Wren copy; latest policy correctly historical
- small-wind-0172 — persistent copy dashboard follows interruption and successful retry
- fair-garden-6418 — clean repeat updates persistent current selection to wren57-retry
- dawn-bell-5364 — corrected published status and preserved current/accepted/history review after refusal
- tender-vine-9199 — retry video published to the persistent page; historical playback survives its arrival
- calm-grove-2647 — document reading stays selected across live polls while current navigation updates (ADR-306)
- violet-wave-6524 — accepted geometry reloads on live identity change; persistent Wren read-only checks pass (ADR-307)
- red-jasper-1884 — persistent page follows real wren66 training and defaults to its completed 90 mm final
- sunny-canyon-4438 — measured restart preserves open playback, all views and fresh-current selection
- odd-pebble-9529 — persistent dashboard follows wren71 through real-training restart and final publication
- crisp-stream-4743 — six historical/current views pass and 703 run/asset files remain unchanged
- terse-walrus-5414 — current and historical playback remain verified during current-design visual comparison
- fresh-timber-6139 — persistent current video verified before/after isolated Wren faults
- blue-forest-5016 — truthful available headline and unchanged persistent project verified
- loyal-canyon-2866 — new failed-attempt polling regression preserves historical playback; persistent current/history verification and full suites pass
- sweet-anchor-6246 — persistent page followed wren79 training, encoder failure, recovery and completion without restart; 21 runs, 703 files preserved
- honest-rain-3132 — deliberate switch of the persistent service to ot5-lark, verified headless; Wren copy byte-identical
- soft-forest-5662 — Lark page re-verified without restart after the tessellation fix
- upright-tide-4795 — persistent page tracked lark1 live, then defaulted to lark1-final with checkpoint 20 historical; no restart
- brave-water-4060 — persistent page tracked lark2 from start through active training to completion without restart
- warm-falcon-0420 — deliberate switch of the persistent service to the working copy ot5-lark-copy85, verified before and after with no trainer running
- scarlet-ocean-2381 — persistent page followed lark86-interrupt, lark86-retry and lark86-retry-video on the copy without restart
- spring-lake-5256 — iteration 88 identity-based fresh selection and history verification
- easy-field-3407 — iteration 91 ADR-318 restart, nine runs and playback/download verification; iterations 89–90 backfilled
- stormy-shade-6266 — ADR-319 restart and origin92 displayed-origin, history and playback/download verification
- windy-walrus-6950 — D11 style probe against the persistent URL without restart: current playback, download, historical selection and orbit/zoom verified
- light-orchard-1402 — persistent page verified before and after the D8 faults on a separate disposable copy; 2,517 source files unchanged, service active
- peaceful-walrus-0642 — persistent service restarted during real `lark96-restart` training; fresh visits select it before, after and on completion with explicit no-recorded-video state
- quiet-pebble-5566 — persistent service followed the real lark98 experiment, encoder failure and recovery without restart; 13 runs, PID unchanged
- dusty-fjord-4501 — restart onto ADR-321 with no trainer; bounded list poll, lark98-final default, playback/download and historical lark1-final verified (scale99-evidence.json)
- civic-nest-8285 — restart onto ADR-322 with no trainer; disk panel equals an independent walk, shared policy asset named, historical checkpoint playback kept (disk100-evidence.json)
- red-shade-9740 — restart onto the corrected ADR-322 reader with no trainer; lark98-final default, 61 entries visited, historical checkpoint playback through refresh (disk102-evidence.json)
- fierce-bloom-1023 — restart onto ADR-323 with no trainer; real lark98-final decode, playback and hash-equal download, history and return to current (download103-evidence.json)
- easy-badger-5812 — ADR-324 restart in iteration 104 and none since; browser receipts 104/106 pinned; iteration 107 HTTP identity check of PID 325201 serving ot5-lark-copy85, 13 runs, default_run lark98-final
- happy-gate-9091 — iteration 109: port 8765 moved back under the `cadex-operator-review` unit from a bare tmux process (ADR-325); unit stayed active on one MainPID through the lark109-engine2 engine-restart experiment; 15 runs
- lean-orchard-0769 — iteration 110: two deliberate restarts onto the ADR-326 reader with no trainer; policy-store states verified on the persistent URL; nested `.cadex` created by bare advice deleted and the advice corrected
- empty-vine-5860 — iteration 111: two deliberate restarts onto the ADR-327 reader with no trainer; every policy-carrying run stored, no problems listed, fresh visit lark109-engine2
- patient-pond-3886 — the owner ticked D10 on 2026-09-13 after run ot5 stopped at iteration 111; evidence unchanged
- still-ivy-2146 — superseded: tools/operator_review.py deleted (ADR-536)
