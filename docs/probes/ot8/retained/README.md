# ot8 retained receipts

Verified against source: 2026-09-20. [Cadex-new]

Committed copies of ot8's evidence: at most 16 KB each, each carrying the
digests by which the full evidence beside it in the external project can be
identified. Full transcripts, streams and artifacts stay project-local and are
never committed. The contract these receipts answer to is
[`../README.md`](../README.md); the closing report that reads them is
[`../REPORT.md`](../REPORT.md).

| receipt | criterion | what it is |
|---|---|---|
| [`g1-window-probe.json`](g1-window-probe.json) | G1 | the `claude-opus-5` access and window reading taken at the freeze, before any product turn. A probe carries no project and no tools, so it is not a product-agent call and spends no slot (ADR-358, ADR-364) |
| [`g3-plover-rebuild.json`](g3-plover-rebuild.json) | G3 | the biped's whole evidence chain on `ot8-plover`: the pinned seed, the baseline's fit, inventory and refused smoke measured before any prompt, the one completed `rebuild.prompt.txt` turn, and the accepted identity, fit, inventory, ordinary `cadex smoke` and two fresh-process reopens measured after it |
