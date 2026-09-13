---
node_id: 1786c5f3-56e0-57d7-9655-d4371617d752
slug: young-cedar-2719
title: Bound retained-video verification after measuring long-history polling delay
created_at: '2026-09-12T20:27:57+00:00'
parents:
- icy-pond-7346
summary: ''
artifacts:
- docs/probes/video-history/results.json
---
## What

Fixed the measured retained-video polling cost with a bounded process-local digest cache (ADR-296). Added reproducible synthetic long-history HTTP/browser measurements, file-change regression coverage, user-facing operation limits and a roadmap entry. Re-ran real Reed copy corruption/recovery with the cache enabled.

## Why

Follows icy-pond-7346 and advances D3's bounded review operation and D8 integrity preservation. The critic first requested product-agent revision authorship from the recorded comparison. Retried the product CLI on the independent Reed copy with its project review, decisions and foot90 seed report, asking it to author, document and accept one physical revision without training. It returned exit 1 on session quota before authoring. Took the critic's explicit fallback to measuring retained-video verification and fixing demonstrated polling delay. No actor-authored substitute, new training, accepted change or D9 authorship claim.

## Method

The bounded agent request used timeout --signal=TERM --kill-after=10s 240 ./cadex --project "$COPY" --out "$COPY/evidence/revision31" --json -p <review-driven physical revision request>. Full receipt and stderr remain project-local under evidence/revision31-agent.*. Compact model/error/revision is in docs/probes/video-history/results.json.

PYTHONPATH=cli:cli/tests pixi run python docs/probes/video-history/measure.py "$NEW_PROJECT" --output "$EVIDENCE" measures three /api/project requests against 64 synthetic sparse 256 MiB retained files (16 GiB logical bytes) plus one synthetic active run. The pre-fix requests took 6.997, 6.591 and 6.595 seconds. After the fix, --browser also observes three atomic telemetry updates without reload in headless Chromium. Both generated projects live outside the checkout under the operator's cadex-projects directory; no original history is used or overwritten by the scale fixture.

Only video digests are cached, at most 256 entries, keyed by resolved path, device, inode, size, mtime_ns and ctime_ns. Paths and current record digests are checked on each read. A post-hash stamp check refuses mutation without caching. Tests exercise unchanged polling, same-size corruption with restored mtime, atomic replacement, changed record hash, escaping symlink and mutation during verification. Replacing the cache call with the old uncached hash path makes the browser regression fail on repeated byte reads (1 failed in 1.93 seconds); no source-file rollback was needed.

PYTHONPATH=cli:cli/tests pixi run python docs/probes/reed-copy/video_recovery.py "$COPY" re-runs real missing/truncated/restored video recovery over this machine's private address, plays/downloads restored bytes, selects the prior completed foot90 video and verifies all 418 protected copied-project files remain unchanged.

## Result

The fixed 64-file workload takes 7.041 seconds initially and 0.0132/0.0123 seconds subsequently. Three browser telemetry updates arrive in 1.930, 2.023 and 2.023 seconds. The first verification still reads all bytes: restart, changed files and eviction can pay that cost again; histories exceeding 256 cached file versions are not covered by the steady-state result. Synthetic sparse data, warm filesystem cache and loopback browser measurement are explicitly not real training/video evidence, cold-storage performance, second-device access or a universal five-second guarantee. Real-copy recovery separately preserves video SHA-256 2308fe3baa4d0a5a2256a37deadfa798256ab6cca978ff8daeacc56c76a2ab24 and all 418 protected files.

D9 remains open: claude-sonnet-5 again returned “You've hit your session limit · resets 5:30pm (America/New_York)” with no accepted revision. No engine, shell, protocol, payload, dependency, charter or generated state/plan change. No full build required or performed. This is the third unreconciled record; reconciliation is due in a separate authorized pass, and this dispatch explicitly forbids it.

Validation: focused reader/server suite 52 passed, 1 skipped in 67.00 seconds; full CLI suite 366 passed, 1 skipped in 328.34 seconds; full engine suite 2103 passed, 54 skipped in 282.40 seconds. Real-copy recovery and scale browser probe pass. The intentional uncached browser control fails as expected on repeated reads. Probe compilation and git diff --check pass. No packaged/shell gate required for this CLI-only change.

Dispatch closed: 1 unit — bound and reuse retained-video verification after measuring long-history polling delay; preserve quota-blocked revision authorship

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot5
- commit: 6fe31f803511e5d02a633c9abf4f78500d730764

## State Impact

- target: dawn-delta-4361 — D3 bounded review operation: 64-file 16 GiB synthetic polling falls from 6.59–7.00 seconds to 12–13 ms after first verification; browser updates 1.93–2.03 seconds, with cold/eviction limits explicit.
- target: cool-gate-3332 — D8 retained-video integrity survives bounded digest caching; same-size restored-mtime corruption, replacement and escaping references refused; real Reed copy recovery preserves 418 protected files.
- target: silent-river-6649 — D9 still open: product-agent physical revision request again refused on session quota before authorship, no substitute revision or training; critic fallback advances measured long-history polling.
