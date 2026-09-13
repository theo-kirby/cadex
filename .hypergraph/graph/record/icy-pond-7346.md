---
node_id: 8925f511-240b-522e-94d6-a9d00b2ce2b3
slug: icy-pond-7346
title: Refuse damaged retained videos and prove Reed copy recovery
created_at: '2026-09-12T20:16:17+00:00'
parents:
- clever-fern-7568
summary: ''
artifacts:
- docs/probes/reed-copy/video-recovery.json
---
## What

Fixed a demonstrated D8 retained-video integrity defect (ADR-295). A missing or damaged copied-biped video is refused with a CLI recovery action; restoring recorded bytes recovers playback/download in the same browser page. Added an automated browser regression and a reusable real-copy fault probe, compact evidence and user-facing documentation.

## Why

Follows clever-fern-7568 and the critic's request: first supplied the recorded ten-seed 70/90 mm comparison to the product agent and requested one reasoned physical revision. The CLI returned exit 1 on the session limit before authoring. Followed the critic's explicit fallback to missing/partial video recovery on the independent copy. No actor-authored substitute, training or D9 authorship claim. Advances cool-gate-3332 (D8); silent-river-6649 (D9) stays open. No reconcile or generated/state/charter edit.

## Method

Ran timeout --signal=TERM --kill-after=10s 240 ./cadex --project "$COPY" --out "$COPY/evidence/revision30" --json -p <request>. Prompt includes the baseline/foot90 ten-seed survival, falls, duration and displacement, distinguishes copy100's single-seed result, asks the agent to choose a physical revision and document rationale/specs, preserves histories and forbids training. Full receipt remains in evidence/revision30-agent.json; compact error/model/revision in docs/probes/reed-copy/video-recovery.json.

PYTHONPATH=cli:cli/tests pixi run python docs/probes/reed-copy/video_recovery.py "$COPY" runs Chromium against a Tailscale-address server, temporarily backs up copy100's real video, observes missing refusal, injects a 64-byte partial file, restores original bytes, plays/downloads in the same page and selects prior foot90 video. The first pass failed waiting for the digest-mismatch label: the reader only checked existence. Finally restored the backup. The fix streams SHA-256 for recorded video entries carrying a digest; mismatch enters the existing refusal path for UI, full and range requests. Legacy entries without a hash preserve existence-only behavior. Browser regression additionally exercises equal-length corruption and missing recovery guidance.

## Result

Real-copy probe passes: missing refused, partial refused, restored playback/download matches SHA-256 2308fe3baa4d0a5a2256a37deadfa798256ab6cca978ff8daeacc56c76a2ab24; prior completed foot90 remains available. All 418 protected copy run/asset/history/accepted-script files remain byte-identical. Separate inventory confirms all 1206 original files match the pre-copy hashes. Same-machine private-network headless browser evidence only, no second-device, rerender, active-training or gait-improvement claim. D9 remains open: claude-sonnet-5 returned “You've hit your session limit · resets 5:30pm (America/New_York)” and no accepted revision.

No new dependency or engine/shell/protocol/payload change. Hashing adds disk reads proportional to recorded video size per reader request, with fixed-size memory chunks; long-video performance is not measured here. Stopped writers are an explicit probe prerequisite; the backup is restored even on assertion failure. Full outputs stay project-local outside the checkout. No full build was performed.

Validation: focused browser/server suite 27 passed, 1 skipped in 66.81 s; full CLI suite 364 passed, 1 skipped in 329.64 s; full engine suite 2103 passed, 54 skipped in 281.57 s. Real-copy probe passes against the fix and failed against the old reader at partial-video refusal. Probe compilation and git diff --check passed. A 100-read local copy100 measurement averaged 1.36 ms per record read including integrity verification. No packaged/shell gate required for this CLI-only change.

Dispatch closed: 1 unit — refuse damaged retained videos and prove real-copy browser recovery after product-agent quota refusal

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot5
- commit: 3da623f54385539c622558792cb49e8b7b14cf96

## State Impact

- target: cool-gate-3332 — D8 real-copy missing/partial video recovery exposed and fixed digest-verification defect; same-page playback/download recovers with original and copied histories unchanged.
- target: silent-river-6649 — D9 remains open: recorded comparison supplied to product agent, session quota refused before revision authorship; no actor substitute or new training.
