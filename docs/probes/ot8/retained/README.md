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
| [`g2-heron-create.json`](g2-heron-create.json) | G2 | the arm's whole evidence chain: the void create call that a five-hour session limit cut off on `ot8-heron` (ADR-355, no slot spent), then the completed `heron.create.prompt.txt` turn on the fresh `ot8-heron-b` and the accepted identity, static fit, swept fit, attachments, inventory and ordinary `cadex smoke` measured after it, beside the ot7 baseline's four hand-modelled purchased parts |
| [`g3-plover-rebuild.json`](g3-plover-rebuild.json) | G3 | the biped's whole evidence chain on `ot8-plover`: the pinned seed, the baseline's fit, inventory and refused smoke measured before any prompt, the one completed `rebuild.prompt.txt` turn, and the accepted identity, fit, inventory, ordinary `cadex smoke` and two fresh-process reopens measured after it |
| [`g4-robin-diagnosis.json`](g4-robin-diagnosis.json) | G4 | the balancer's measured diagnosis on `ot8-robin`, taken with **no prompt dispatched and no slot spent**: the pinned seed, the baseline's fit, inventory and failing ordinary `cadex smoke` with its per-check breakdown, the MJCF-agreement and exact-geometry measurements that rule out an export mismatch, the mass, lever arm and torque margin that rule out a design defect, the replayed free response that reproduces the published fall, and the exact missing control contract that ends the experiment |
