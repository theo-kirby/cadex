# Robin restore: nondeterministic shaft offset, still blocked

Verified against source: 2026-09-14. [Cadex-new]

Historical diagnosis of revision `71709063d6af…`. Current result: [the bore construction was revised as a new design revision; reopen holds](BORE.md). The reproducer below reads the project's accepted attempt, which is now that revision; the old revision's frozen inputs and replays stay under `ot6-robin-src/restore-probe/`.

Robin still cannot reopen. A fresh `cadex section --plane XY --offset-mm 50
--json` on its retained accepted project exited 1 with **“The restore pass
digest does not match the accepted digest.”** The accepted revision remains
`71709063d6af…`, digest `806ab1343b7c…`; this rebuild produced `c14013df428f…`.
No script, acceptance identity, or digest rule was changed. No training started.

## Where the output first diverges

[restore.json](restore.json) carries the hashes and measurements.
Comparing the accepted attempt to the fresh restore found exactly two changed
artifact files: `wheel_l` and `wheel_r`. All 75 output definitions and solved
placements match; all other retained output artifacts match byte-for-byte.
The BREP differences include curve and topology order and last-bit floating
point changes, so sorting textual lines would not repair them.

The [read-only reproducer](restore_probe.py) loads the accepted result's wheel
definitions and instruments each Part operation in four fresh FreeCAD processes,
with `PYTHONHASHSEED=0`. Of 40 operation results, 36 have identical BREP hashes.
The first divergent operation on **each** side is `part.offset` on the catalog
D-shaft segment, with four different hashes in four executions. The final wheel
cut also varies (see the receipt for counts). The upstream shaft intersection,
wheel blank, catalog geometry and transforms are byte-stable in these samples.

A second experiment removes that recursive evaluation entirely: save each
shaft intersection to one BREP file, load that **same file** in four fresh
processes, and call the exact kernel operation used by the worker:

```python
shape.makeOffsetShape(0.05, 1e-7, inter=False, self_inter=False,
                      offsetMode=0, join=0, fill=False)
```

Each loaded input has one hash across the four processes; each offset has four.
This isolates a kernel offset reproducibility failure independently of Python
memoisation and assembly solving. Loaded BREP volumes differ slightly from the
in-memory inputs because of serialization precision; compare **within** each
experiment, not across them. Equal volume or face counts do not prove identical
geometry and are not proposed as replacement acceptance checks.

## Reproduce without accepting anything

```bash
PROJECTS="$HOME/cadex-projects"
pixi run python docs/probes/ot6/robin/restore_probe.py \
  "$PROJECTS/ot6-robin" "$PROJECTS/ot6-robin-src/restore-probe/frozen" \
  .pixi/envs/default/bin/FreeCADCmd src/Mod/cadex
```

The probe checks that `script.json` is unchanged. Nine bounded child processes
(120-second timeout each) write operation hashes, logs, two frozen input BREPs
and a manifest outside the repo. The committed receipt identifies the manifest
by SHA-256; it indexes every full replay result and log. The separate failed
section output is retained as `ot6-robin-src/iteration20-section.json`.

## What remains

This is a completed diagnosis, **not a restore fix or passing regression for
Robin**. No smallest corrective change that reproduces its already accepted
bytes was established in this unit. The worker exposes no deterministic-order
option for this offset call. Stabilizing future output alone would not establish
agreement with the old accepted hash. A kernel correction must demonstrate that
agreement before being called a repair; changing the bore construction or
re-accepting a new result is a separate design revision, not recovery evidence.
The strict BREP digest and restore refusal remain intact.

The persistent operator service stayed on Robin. Fresh headless browsers at
1400×900 and touch-emulated 400×850 selected `accepted`, loaded 24 components /
57,044 triangles, and reported zero horizontal overflow. This proves retained
display, not reopen. The service was checked active before reproduction; the
project identity browser checks followed the probes, so this unit does not
claim a full browser identity measurement at experiment start.

Verification: the full engine suite passed **2,114 tests, 53 skipped** in
283.06 seconds. The existing packaged lifecycle gate passed **16 tests** in
18.07 seconds with `CADEX_ENGINE_ROOT` set to the staged Linux payload.
Evidence size/privacy checks passed **73 tests, 16 deselected**. The receipt
hashes both full suite logs. No product code changed and no build was run;
these general gates do not establish that Robin reopens.

The missing historical artifact reference on `ancient-field-7584` was repointed
to `design/capture_page.py`: git commit `9a4ff012` records the actual rename from
`capture_before.py` (88% similarity). The original script remains in historical
commit `1af3cb9c`; the current script has subsequent changes. No replacement
historical script was fabricated, and the original before receipt and images
remain retained.
