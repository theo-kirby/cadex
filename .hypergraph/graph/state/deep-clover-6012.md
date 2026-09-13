---
node_id: 5c38ed96-b7d8-5c80-9395-fb3e153b6597
slug: deep-clover-6012
title: D10. The persistent operator dashboard stays current
created_at: '2026-09-12T21:20:29+00:00'
parents:
- crisp-sun-1239
summary: ''
---
Status: working

## Current

**Persistent private port 8765 serves `ot5-lark-copy85`; a fresh visit now selects the completed `lark96-restart` with an explicit no-recorded-video state.** That run was the D6 restart-during-training experiment: while a real 100-iteration GPU trainer ran, `cadex-operator-review` was restarted (dashboard PID 4073466 → 4173669, restart command 0.164 s) and the open page resumed updating 0.585 s later without navigation; fresh visits before and after the restart selected the active `lark96-restart`, and the completion page shows it completed with done telemetry, the accepted revision and no recorded video. The service remained active with no experiment trainer left behind [rec: peaceful-walrus-0642]. Immediately before, the D8 video-fault probe served a disposable full copy on a separate private address and never touched this service: the persistent page was verified before and after the faults, still `ot5-lark-copy85` / `lark86-retry-video`, all 2,517 source files unchanged, service active [rec: light-orchard-1402]. The D11 style probe likewise ran against the same URL without a restart, verifying `lark86-retry-video` playback through three refreshes, hash-equal download, historical `lark2-final` and `lark2-checkpoint20` selection and return-to-current [rec: windy-walrus-6950].

**Before that, `lark86-retry-video` was the fresh-visit default, verified across two deliberate restarts with no trainer active.** The name-free checker reverified the default against `default_run`, historical browsing and return-to-current [rec: spring-lake-5256]. Iteration 91 restarted the service onto ADR-318; nine runs remained browsable and the 81-frame video played through polls and downloaded hash-equal (`1f53d43d1c18…`); that record also backfills the reader/server commits from iterations 89–90 [rec: easy-field-3407]. The ADR-319 restart kept project and URL stable and the browser verified displayed final-policy origin `lark86-retry`, historical `lark2-final` selection, return-to-current, polling playback and the same download digest [rec: stormy-shade-6266].

**The switch to Lark's working copy was followed by interruption, retry and video publication without restart.** The switch from `ot5-lark` was one deliberate restart with no trainer running, verified over the private address before and after, with the fresh-visit default `RUN lark2-final` shown HISTORICAL against the copy's accepted revision `083d086ad980…`; `ot5-lark` is retained, unchanged and no longer served, and the operator status README identifies the copy [rec: warm-falcon-0420]. The same service then showed a fresh visit selecting the failed `lark86-interrupt` with its controlled-interruption note, then the active and completed `lark86-retry`, then `lark86-retry-video` as the new default at accepted revision `7f6c23913d55…`, with the README updated at each transition [rec: scarlet-ocean-2381].

**Before the copy, the same service served `ot5-lark` through both of its real experiments.** The switch from `ot5-wren-copy54` was one restart with no trainer running, verified as ACCEPTED NOW with zero runs while the Wren copy's 2,392 files stayed byte-identical [rec: honest-rain-3132]; the page was re-verified without restart after the ADR-312 tessellation fix [rec: soft-forest-5662]. During `lark1` the active run was selected by default and afterwards `lark1-final` was the fresh-visit default with checkpoint 20 HISTORICAL [rec: upright-tide-4795]. The page tracked `lark2` from start through active training to completion without restart [rec: brave-water-4060].

**Wren-era coverage.** The service followed `wren79`'s training, encoder failure, recovery and completion without restart, with historical `wren71-final` playback verified and 703 older run/asset files preserved at 21 runs [rec: sweet-anchor-6246]. A browser regression publishes a distinct failed attempt while a historical video plays; fresh visits select the new failure without a substituted video [rec: loyal-canyon-2866]. The dashboard followed real `wren71` training, checkpoint publication and completion, and its restart preserved the single trainer and historical playback with telemetry recovery in 0.957 s [rec: odd-pebble-9529]. Six historical/current views spanning 85/105/110/90 mm designs preserved identities, curves and hash-matching playback [rec: crisp-stream-4743] [rec: terse-walrus-5414]; video-fault probes preserved all 3,769 source files [rec: fresh-timber-6139] [rec: blue-forest-5016]. Live-page document reading and accepted-geometry reload fixes remain in place (ADR-306/307) [rec: calm-grove-2647] [rec: violet-wave-6524]. The stable URL earlier followed `wren56c` and `wren57` interruption → retry pairs [rec: small-wind-0172] [rec: fair-garden-6418] [rec: dawn-bell-5364]; the first working-copy switch verified review with the original path unavailable [rec: crimson-bell-5375]; revised Wren training and two provider refusals retained accepted/current/historical identities [rec: frosty-birch-2464] [rec: smooth-pine-9795].

Judgement: `working`. The stable URL has served through four project switches (Reed, Wren, Wren copy, Lark, Lark copy) and real experiments on each, including interruptions, restarts with and without a trainer active, failures, fault probes on isolated copies and recoveries. Every observation is a same-machine private-address check, not second-device evidence [rec: peaceful-walrus-0642].

Charter criterion: fresh visits select active training first, otherwise the latest attempt including failed/interrupted work, with truthful identity, available curves/videos and explicit pending/stale/failed states; preserve historical browsing and playback with a route back; keep the stable URL serving between iterations; verify and publish identity at experiment start/completion and every working-project switch. Acceptance requires persistent-URL browser evidence across a real experiment and a working-copy switch plus current-selection and historical-preservation regressions. Declared target `gap-d10-persistent-operator-dashboard-stays` [rec: simple-raven-5405].

## Negative knowledge

None yet.

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
