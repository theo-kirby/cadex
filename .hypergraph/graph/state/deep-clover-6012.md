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

**Persistent private port 8765 now serves the third fresh project, `ot5-lark`, and has tracked its first real experiment throughout.** The switch from `ot5-wren-copy54` was deliberate: one service restart with no trainer running, verified in a headless browser as ACCEPTED NOW default with zero runs, while the Wren copy's 2,392 files stayed byte-identical [rec: honest-rain-3132]. The page was re-verified without a restart after the ADR-312 tessellation fix (service PID unchanged, eight components, twenty parameters) [rec: soft-forest-5662]. During `lark1`'s real GPU run the active run was selected by default; afterwards `lark1-final` is the fresh-visit default, checkpoint 20 browses as HISTORICAL with its own revision and return-to-current works; no service restart; the operator status README names the served project [rec: upright-tide-4795].

**Before the switch, the same service followed Wren79's training, encoder failure, recovery and completion without restart.** Fresh visits selected the active `wren79` run and then `wren79-final` at playback revision `0d78fae96c22…`; the checkpoint page showed the failed re-render with CLI guidance beside its earlier retained video; historical `wren71-final` playback/download stayed verified; all 703 older run/asset files were preserved and the server reached 21 runs [rec: sweet-anchor-6246].

**Synthetic and Wren71-era coverage.** A browser regression publishes a distinct failed attempt while a historical video plays and shows selection, video element, revision and advancing playback surviving two polls; fresh visits and return-to-current select the new failure without a substituted video [rec: loyal-canyon-2866]. The dashboard followed real `wren71` training, checkpoint publication and completion, and its restart preserved the single trainer and historical playback with telemetry recovery in 0.957 s [rec: odd-pebble-9529]. Six historical/current views spanning 85/105/110/90 mm designs preserved model/document identities, curve histories and hash-matching playback/download through polling [rec: crisp-stream-4743] [rec: terse-walrus-5414]; Wren video-fault probes preserved all 3,769 source files [rec: fresh-timber-6139] [rec: blue-forest-5016].

Live-page document reading and accepted-geometry reload fixes remain in place (ADR-306/307) [rec: calm-grove-2647] [rec: violet-wave-6524]. The stable URL earlier followed `wren56c-interrupt` → `wren56c-retry` and `wren57-interrupt` → `wren57-retry`, with published operator status corrected after a refused product-agent turn [rec: small-wind-0172] [rec: fair-garden-6418] [rec: dawn-bell-5364]; the first working-copy switch verified review with the original path unavailable [rec: crimson-bell-5375]; revised Wren training and two provider refusals retained accepted/current/historical identities [rec: frosty-birch-2464] [rec: smooth-pine-9795].

Judgement: `working`. The stable URL has served through three project switches, real experiments on each, restarts, failures and recoveries. Every observation is a same-machine private-address check, not second-device evidence [rec: sweet-anchor-6246] [rec: upright-tide-4795].

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
