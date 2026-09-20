---
node_id: aacdfba9-1707-5976-bcc6-6988a436f942
slug: lucid-flame-4255
title: G5. The regression floor still holds
created_at: '2026-09-20T18:48:22+00:00'
parents:
- ancient-vine-9908
summary: ''
---
Status: open

## Current

**Open — declared by the ot8 charter, unattempted at the run's start [rec: keen-stone-1720].** Both full suites and the packaged lifecycle gate pass at the **final** code revision; copies of the retained ot6/ot7 designs this run uses are reopened and their accepted pins and artifacts verified intact, with every measured difference explained; and the ADR-398 repeated-restore retention regressions stay green [rec: keen-stone-1720].

That last clause is the newest part of the floor and the reason it is worded that way: repeated restore could collect a project's accepted artifacts while still reporting a successful open, which is exactly the class of loss this criterion checks for (detail on `forest-wind-0342`) [rec: fierce-bloom-1076]. Flip to `working` only when the criterion is verifiably met at the final revision — an earlier green run does not carry.

## Negative knowledge

None yet.

## Provenance

- keen-stone-1720 — the criterion as the ot8 charter declares it
- fierce-bloom-1076 — ADR-398's repeated-restore retention regressions, named by the criterion
