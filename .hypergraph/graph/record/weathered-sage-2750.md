---
node_id: eede7183-e0ec-5269-a514-cec204faf0bf
slug: weathered-sage-2750
title: Verify 257-run browser history across restart and corruption recovery
created_at: '2026-09-12T21:04:23+00:00'
parents:
- dusty-oak-7376
summary: ''
---
## What

Added a headless-browser lifecycle regression for 257 retained video paths, beyond the 256-entry digest cache. Early and late run selection preserves model/spec and training-history identities across a real dashboard-process restart, with playback, browser downloads, corruption refusal and recovery. Documented the exact coverage and limits in docs/probes/video-history/README.md. No product implementation change was needed.

## Why

Advances D5/D6/D8 long-history review reliability under the critic's explicit fallback, following dusty-oak-7376. First requested a product-agent-authored, review-informed physical revision on the independent Reed copy. The product CLI returned session-quota refusal before authoring, with an empty accepted_revision and no outputs. No actor-authored substitute, new training or D9 completion claim. This work dispatch forbids reconciliation; this record brings the unreconciled tail to three for a separate authorized pass.

## Method

Ran timeout --signal=TERM --kill-after=10s 240 ./cadex --project "$COPY" --out "$COPY/evidence/revision35" --json -p <read retained review, decisions and foot90 comparison; author, explain, save and accept one physical revision; do not train>. Project-local evidence/revision35-agent.json and .stderr retain the receipt. claude-sonnet-5 returned exit 1: session limit, reset announced as 5:30pm America/New_York. Reported working revision remains 25d9b6ab7472b968a3a72691ca44113ea86beda85802af3e22d9270952cb71fc; no accepted revision was returned.

The test renders the existing synthetic moving-cube rollout once, copies it to 257 independent retained paths and assigns separate run names, requested iterations and synthetic reward/loss/episode histories. These are repeated fixtures of one historical model, not 257 policies or new physical-design evidence. Early/late runs show the same recorded revision A against accepted B, their own run names, model digest, parameters/specs, policy digest, iteration counts and curve lengths. Both videos play and browser downloads match the recorded SHA-256.

After cache churn, one early video's first byte is changed without changing its size, and mtime is restored. The browser refuses it and both full/range HTTP requests return 404; the late video continues to play. SIGINT stops the real CLI dashboard process. A new process binds the same port with an empty process-local cache; the original page observes stale then live without navigation and revisits both runs. Corruption remains refused. Atomic restoration restores early playback/downloads. A content-hash inventory verifies all 4,122 project files equal their original contents after restoration. The 257 WebM files are 5,402 bytes each, totaling 1,388,314 bytes.

Focused command: pixi run python -m pytest cli/tests/test_video.py -k beyond_video_cache --basetemp "$PROJECTS/ot5-history35-tests-c" -q. Passed 1, deselected 8 in 16.13 seconds before adding an explicit done-state assertion to the fixture. The first fixture attempt failed before browser work because its helper argument and record run key collided; fixed direct record construction, not product code. Initial lifecycle-only version also passed in 14.76 seconds. Final verification includes the full CLI suite below. Dedicated fixtures and full CLI test projects are outside the checkout under the operator's cadex-projects directory; no original project artifacts were discarded.

## Result

Beyond-capacity history is browser-reviewable across server process restart under this small-file workload. Early/late identities, distinct training histories, playable videos, download digests and corruption refusal survive. No demonstrated implementation defect, new dependency, training, engine/shell/protocol/payload change, full build, charter edit or state/plan edit. No private-network, real-GPU, second-device, large-video throughput or universal five-second claim. D9 product-agent revision authorship remains open. Eviction still permits rehashing all video bytes on each full scan; this test proves correctness, not a throughput fix.

Final validation: pixi run python -m pytest cli/tests --basetemp "$PROJECTS/ot5-history35-cli-suite" -q: 370 passed, 1 skipped in 355.03 seconds. pixi run test-engine: 2103 passed, 54 skipped in 278.14 seconds. The final full CLI run includes the explicit done-state assertion and distinct retained-history checks. git diff --check passed. No packaged or shell gate required for a CLI test/documentation-only unit.

Dispatch closed: 1 unit — prove retained-history browser lifecycle beyond the video digest cache after product-agent quota refusal

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot5
- commit: adf0b6ae5b2a32453afff8f599346e6bf12aea05

## State Impact

- target: clever-field-7845 — A 257-video synthetic browser lifecycle survives real dashboard-process restart without reload; early and late run identities, histories, playback and downloads persist.
- target: cool-gate-3332 — Same-size early-video corruption with restored mtime remains refused after cache churn and process restart; intact late video plays and atomic recovery preserves all 4122 project files.
- target: silent-river-6649 — Product-agent revision35 request again refused on session quota before authorship; D9 remains open and the critic-authorized long-history lifecycle fallback passed.
