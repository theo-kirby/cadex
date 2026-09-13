# Retained-video history verification

Verified against source: 2026-09-12. Provenance: [Cadex-new]. ADR-296.

The dashboard previously hashed every retained video for each project poll.
On this machine, 64 synthetic files of 256 MiB each (16 GiB logical bytes)
made `/api/project` take 6.59–7.00 seconds, exceeding the five-second telemetry
visibility target before browser scheduling. With the bounded file-stamp digest
cache, subsequent requests took 12–13 ms. Three atomic telemetry updates
appeared in headless Chromium without reload in 1.93–2.03 seconds.

The initial request still took 7.04 seconds. Restart, changed files and cache
capacity misses require rehashing; histories beyond 256 cached file versions
are not covered by these latency results. This measures a warm filesystem
cache and synthetic sparse zero files, not decoded videos, GPU training,
second-device access, cold storage or a universal latency bound. The browser
uses loopback. Existing Reed real-video playback/corruption recovery is covered
separately by the retained-copy probe and browser regression.

Reproduce with a new directory outside the checkout (the script refuses an
existing destination):

```bash
PYTHONPATH=cli:cli/tests pixi run python docs/probes/video-history/measure.py \
  ~/cadex-projects/video-history --output /tmp/video-history.json --browser
```

The script creates one synthetic project with 64 historical files and one
synthetic active run, measures three HTTP responses, then observes three
committed telemetry updates in the browser. Sparse files occupy little storage
but verification reads 16 GiB per uncached pass. It never edits a real biped.
The compact [results](results.json) retain before/after timings and the latest
product-agent quota refusal. That refusal occurred before revision authorship;
D9 remains open, with no new physical revision or training in this iteration.

The initial-verification browser regression (ADR-297) injects a blocked hash
for 7.2 seconds, crossing three real two-second browser timer ticks. Before
poll coalescing it observes four simultaneous reads; after, exactly one.
While blocked the page says loading and offers no video. When released it
labels the intentionally corrupt artifact, then receives a changed run status
on a later poll. This is deterministic fault injection, not another storage
throughput measurement or a real training observation. Run it with:

```bash
pixi run python -m pytest cli/tests/test_review_server.py -k coalesces -q
```

Each page now shares its pending request. ADR-298 also serializes video cache
lookup and hashing within the server process. A second browser page is opened
while the first hash is blocked; the test waits until both requests reach
verification. Before this fix there are two byte reads, after it one. Both
pages refuse the corrupt video, and changed bytes trigger one fresh hash.
The unfixed control failed on the duplicate-read assertion in 1.19 seconds.
This counts duplicate work under deterministic fault injection, not storage
throughput or real training latency. Reproduce with:

```bash
pixi run python -m pytest cli/tests/test_review_server.py -k two_browser_clients -q
```

First-read latency and histories larger than the digest cache retain their
limits. Unrelated video checks may wait behind the process-wide lock; separate
servers have independent locks and caches. A 257-file reader regression proves
the cache remains bounded at 256 entries and rehashes an evicted file.

## Browser history beyond cache capacity

The browser lifecycle regression in `cli/tests/test_video.py` retains 257
independent video paths and revisits `history-000` and `history-256`. These
are synthetic repeats of one rendered model, with distinct run names,
requested iteration counts and reward/loss/episode-length histories. They
are not 257 training runs or evidence of a physical design change.

```bash
pixi run python -m pytest cli/tests/test_video.py -k beyond_video_cache -q
```

The test checks historical model/revision/digest and parameter/spec identity,
per-run training histories, playback and browser downloads. It changes one
early video's bytes without changing its size or mtime, verifies refusal
of both ordinary and range requests, then stops the server process. A new
process binds the same port; the original browser page recovers without a
reload and revisits both runs. The damaged early video remains refused while
the late video plays. Atomic restoration restores playback and downloads.
A content-hash inventory proves inspection left all project files unchanged
after the injected damage was restored.

The recorded fixture has 4,122 protected files and 257 WebM files of 5,402
bytes each (1,388,314 video bytes total). The full CLI suite including this
regression passed on 2026-09-12: 370 passed, 1 skipped in 355.03 seconds.

This exercises eviction and a genuinely empty cache after process restart,
using small playable files and a loopback browser on the server machine.
It does not establish large-video throughput, cold-storage performance,
private-network reachability or real GPU training. Histories above capacity
can still rehash on each full scan; no five-second guarantee follows from
this lifecycle check.
