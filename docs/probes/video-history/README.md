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
