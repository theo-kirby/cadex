---
node_id: b88f672e-257e-57ba-83f3-e9061ff94571
slug: candid-harvest-2614
title: D4. Policy videos render, persist and play headlessly
created_at: '2026-09-12T14:51:24+00:00'
parents:
- crisp-sun-1239
summary: ''
---
Status: working

## Current

**D4 is repeated on the third fresh project, Lark.** `lark1-checkpoint20` (policy `e6dcbbcc68b4…`, witness error 8.0e-8) was published with a browser-verified video (11 frames, 0.98 s) while the trainer was active at updates 18–26; `lark1-final` (policy `396c013c3c35…`) has a verified downloadable video (6 frames, 0.50 s). Both identify revision, policy digest, seed and simulation time. Trainer update intervals were 1.39/1.42/1.34 s median before/during/after the render — descriptive render-overhead evidence, not a controlled measurement [rec: upright-tide-4795].

**A real Wren checkpoint re-render encoder failure is isolated and recovered on the persistent dashboard.** During the bounded `wren79` GPU run, the normal renderer was given an ffmpeg that exits 73; it validated and placed the real rollout, captured frames, failed at encoding in 4.056 s (starting at update 74) and wrote its own failed `video.json`. The page reported "Recorded video render: failed / FFmpeg encoding failed" with CLI retry guidance, separately from the earlier retained checkpoint video still available, while the unchanged trainer (one PID/start tick) advanced through browser-observed updates 78, 80, 82, 84 without reload. The retry with the real encoder played and downloaded at update 96, and the final video (81 frames, witness error 8.7e-8) is retained after 240 updates. An initial window overlapped a second trainer launched by a concurrent CLI live test and a second window failed an over-strict probe assertion; both receipts are retained and excluded, and the successful window used the corrected probe with no suite running. Sequential suites afterwards: CLI 422 passed/1 skipped, engine 2110 passed/53 skipped [rec: sweet-anchor-6246].

**Earlier Wren evidence.** Wren71 checkpoint20 was published during active training with its final video retained; both pass witness verification and decode to 81 frames at 10 fps [rec: odd-pebble-9529]. The 110 mm `wren57-retry` has an engine-witness-verified seed-0 video published with training identity retained, and historical `wren2-final` playback survived its arrival [rec: tender-vine-9199]. Revised checkpoint20/final videos were verified while GPU training remained active [rec: frosty-birch-2464]. Reed's probe3 supplied the first active intermediate, retained final and missing-trace refusal (exit 1 with training still active) [rec: light-brook-2640].

Judgement: `working`. Active checkpoint, final video and both refusal-path and real encoder-failure isolation are demonstrated across Reed, Wren and Lark. Renderer throughput cost is descriptive only, and all browser evidence is same-machine private-address rather than a second device [rec: sweet-anchor-6246] [rec: upright-tide-4795].

Charter criterion: **D4. Policy videos render, persist and play headlessly** At least one verified intermediate checkpoint is rendered and appears in the dashboard while training remains active, and the final policy also has a saved video; both play and download in the browser, each identifying model revision, policy digest, rollout seed and simulation time. Evidence: real biped video files, a decoded frame/timing check and a browser playback/download test; a failed render leaves training running and reports its own failure. Declared target `gap-d4-policy-videos-render-persist` [rec: lucky-comet-0031], introduced with no implementation claimed [rec: dusty-peak-9330].

## Negative knowledge

- [scope: headless Chromium download tests on a machine whose Chromium is the snap package | confidence: high | evidence: ready-orchard-4806] Snap confinement gives Chromium a private `/tmp` and refuses hidden paths under `$HOME`; a download directory in either place is invisible to the browser or to the host. A differently confined Chromium would need `CADEX_BROWSER` pointed at an unconfined binary.

## Provenance

- lucky-comet-0031 — the ot5 directive declared this criterion as gap `gap-d4-policy-videos-render-persist`
- dusty-peak-9330 — the owner's charter revision (ADR-284) that introduced D1–D9, claiming none complete
- long-cove-3626 — reproduced the baseline browser download failure against the clean startup commit
- ready-orchard-4806 — traced the failure to snap-confined Chromium; harness collects downloads where the browser can write and proves bytes and digest
- amber-gate-7498 — first real final-policy video, decoded and browser-played/downloaded
- merry-star-6951 — active-training checkpoint render, later successful browser verification and explicit interruption limits
- light-brook-2640 — active intermediate and final video verification; missing-trace refusal leaves trainer active
- sage-tower-6445 — Wren active-training checkpoint and final-policy videos with engine witnesses, decoded timing and browser playback/download
- frosty-birch-2464 — revised intermediate/final videos and all four retained reviews verified
- tender-vine-9199 — engine-verified 110 mm Wren retry video published with training identity retained; historical playback survives its arrival
- odd-pebble-9529 — active-training Wren71 checkpoint and retained final videos pass witness, decode, playback and download checks
- sweet-anchor-6246 — real Wren79 checkpoint encoder failure isolated during GPU training, visible with CLI guidance, recovered and final video retained; excluded windows disclosed
- upright-tide-4795 — D4 repeated on Lark: active-training checkpoint 20 video and verified final video, both identified
