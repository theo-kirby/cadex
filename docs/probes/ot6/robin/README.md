# Robin — first product-agent design attempt (D7)

Verified against source: 2026-09-14. [Cadex-new]

**No balancer was accepted.** The product agent started from the empty external
project `ot6-robin`, accepted a catalog probe, then failed to accept the proposed
mechanism. [design-attempt.json](design-attempt.json) records the identities,
refusals and end-of-experiment dashboard check. D7 remains open: no verified
inventory, fit check, training, recording or balancer review exists yet.

## The experiment

The exact [creation prompt](create.prompt.txt) asks for Robin: two catalog
Pololu 2367 gearmotors, printed D-bore wheels, a chassis with motor pockets and
clamps, catalog M2 screws and inserts, a Pi Zero 2 W board mount and an empty
battery bay. It requires a free base, per-part proxies, a balance task, measured
fits and no world geometry. The pack's volume is reserved but its mass is
explicitly excluded. These are requested features, not verified design facts.

The invocation, with paths relative to the operator's `cadex-projects` directory
and executed from the product checkout:

```bash
PROJECTS="$HOME/cadex-projects"
timeout --signal=TERM --kill-after=10s 1800 ./cadex \
  --project "$PROJECTS/ot6-robin" --out "$PROJECTS/ot6-robin-src/create-out" \
  --json -p "$(cat "$PROJECTS/ot6-robin-src/create.prompt.txt")"
```

The turn used `claude-fable-5`, started at 01:15:05 UTC and ended at 01:33:06 UTC
on September 14 (1081 s, within the 1800 s limit), exit 1. Standard output and
error, timestamps and the exit status remain under `ot6-robin-src/`; the receipt
lists their SHA-256 digests. No training was started.

## What actually happened

The accepted revision `f5f053348145…` contains only `probe_motor`, the catalog
gearmotor body. The 569-byte script prints gearmotor, board, insert and bolt
specs. Its existence establishes that the product agent reached the engine and
catalog, not that Robin was built.

The proposed mechanism (`69241c70379b…`) failed with
`DOMAIN_CANDIDATE_FAILED`: its reset variation drives the mechanism **1.31 mm
further into the floor** at azimuth 0 degrees. The retained candidate declares
`tilt_degrees=[0.0, 3.0]` and `height_mm=[1.0, 3.0]`; the engine rejects the
combination before accepting the task. This is an observed candidate refusal,
not evidence that the engine's check is defective. No fit or inventory is
certified by this attempt.

The following `edit_script` also failed: the requested old text occurred zero
times. The stored script was still the accepted probe, not the rejected
candidate. Finally the provider reported its session usage limit (reset reported
as 10:10 pm America/New_York). There was no completed repair turn. The candidate
source remains in the failed attempt's `request.json` under `source`, with its
path and file digest in the receipt. A future product turn can recover that
proposal, repair and submit the whole script, then verify its geometry and fits;
editing presumed accepted candidate text will repeat the zero-match error.

## Handoff and the live page

The D6 repair is already recorded in `tiny-tooth-8197` (commit `7d48f13f`): the
Finch preservation claim now states that `preserved_records={}` proves nothing
about older run records, and the full CLI suite passed **557 tests, 1 skipped**.
The D7 turn overlapped that suite; no new product code has changed here.

At the end of this attempt a fresh headless browser visit to
`http://<private-address>:8765/` selected `finch1-final`, loaded its 29 components
and 95,212 triangles, and reported tessellated solids. The accepted model API
returned revision `b68622345563…`. The persistent server stays on that completed
lifecycle: switching it to a lone motor probe would falsely suggest the active
balancer design is ready to review. The supplied start-of-iteration D6 handoff
also names Finch and `finch1-final`; this receipt independently checks the end,
not the start of the earlier product turn.

The critic requested a finished balancer, inventory, fit checks and dashboard
handoff before training. That unit could not finish because the product agent
exhausted its usage while repairing the rejected candidate. Under the charter's
no-clock-wait rule this dispatch closes as a **failed design experiment**. It
does not replace the required product-agent design with an actor-authored one,
relax the floor check or claim any D7 completion. Resume D7 through the product
agent when it is available, verify all requested fits, then move the persistent
server to the accepted balancer before starting its bounded training unit.
