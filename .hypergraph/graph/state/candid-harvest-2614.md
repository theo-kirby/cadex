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

**Wren71 checkpoint20 was published during active GPU training, and its final video is retained.** Both policies passed engine witness verification (errors 2.80e-08/7.88e-08 against 1e-4), and both videos fully decode to 81 differing frames at 10 fps: 8.1 encoded seconds for eight simulation seconds. Persistent-browser playback/download hashes match. Checkpoint rendering spanned updates 23–33; training stayed active after publication. Full suites passed, but concurrent tests prevent isolating renderer overhead; these seed-0 clips establish no alternating-gait or multi-seed claim [rec: odd-pebble-9529].

**The 110 mm Wren retry (`wren57-retry`) now has an engine-witness-verified, seed-0, eight-second video published on the persistent dashboard, with the original training identity retained.** Policy `a232fec1…` passed 32 witness samples (error 8.7e-09 < 1e-4); enabling it produced playback revision `79f86c69bfc3…`, while training revision `5b61ef31ff13…` and the original record stay under the explicit training filename, and model/task bytes are byte-identical to the training inputs. The WebM (`4d418967…`) fully decodes to 81 frames at 10 fps, 8.1 encoded seconds for 8.0 simulated, rendered in 12.6 s; it played through three polls and downloaded via Chromium with matching bytes and SHA-256. Historical `wren2-final` stayed selected and playing throughout, and a real-renderer regression with two distinct videos pins that the current attempt gaining its own video does not disturb historical playback. All 395 files in other runs are unchanged. No new D11 reference-matching claim; same-machine private-address evidence [rec: tender-vine-9199].

**Revised Wren checkpoint20 and final videos are witness-verified, decoded, browser-played and downloaded with matching hashes; the intermediate was published while GPU training remained active.** Checkpoint rendering spanned iterations 23–32 and took 12.731 s; final rendering took 12.18 s. Both revised videos and the original checkpoint encode eight simulated seconds as 81 frames/8.1 seconds; the original final retains its six-frame/0.6-second video of a 0.46-second fall. All four retain model/policy identity and historical playback through polling. The shared `cadex-prototype-light-v1` style is retained, without a new full D11 comparison; timing is descriptive, not controlled rendering-overhead evidence [rec: frosty-birch-2464].

**Probe3 has browser-verified intermediate playback/download while training is active and a retained verified final-policy video.** Checkpoint20 passes the engine witness check, runs eight simulated seconds and yields 81 decoded frames/8.1 encoded seconds. Both sequential checkpoint render collections pass playback, three refreshes, matching-byte download and revision/policy/seed/time labels while training remains active. The successful 240-iteration trainer produces a verified final policy and a seven-frame/0.7 encoded-second video of a seed-0 fall at 0.52 simulated seconds; a missing-trace render request exits 1 while training stays active, proving the refusal path rather than an encoder crash [rec: light-brook-2640].

Judgement: `working` because the required active checkpoint, final video and failed-render isolation are demonstrated across Reed and Wren. Renderer throughput cost is unisolated, and all browser evidence is on this machine's private address rather than a second device [rec: light-brook-2640] [rec: tender-vine-9199].

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
