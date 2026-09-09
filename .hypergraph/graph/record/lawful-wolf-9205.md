---
node_id: 41f3ca44-caaf-5291-8c14-dd3140a68675
slug: lawful-wolf-9205
title: assembly.mjcf's 300 s stall is OpenBLAS reserving 4.4 GB of address space, not a dynamics declaration
created_at: '2026-09-08T13:39:01+00:00'
parents:
- ancient-key-7299
summary: ''
---
## What

Bisected the dynamics declarations that burned the sandboxed worker's 300 s
CPU cap on this run's machine, and the bisect cleared them all. **The fault
was `import numpy`, and it was address space rather than compute.**

`assembly.mjcf` reaches `import mujoco` in `CadexDynamics.build_model`,
which imports numpy, which dlopens OpenBLAS. OpenBLAS reserves a per-thread
scratch buffer at load time and sizes its pool from the *host's* core count.
Measured in `FreeCADCmd` on this 32-core box, address space reserved by
`import mujoco, numpy`: **216 MB at 1 thread, 352 at 2, 624 at 4, 1,168 at
8, and 4,432 MB unset (32)**. The worker's `RLIMIT_AS` is 6,144 MB and
FreeCAD, OCCT and the rig's own solids hold most of the rest, so the mapping
is refused and OpenBLAS spins in its allocation retry loop until the kernel
charges it the CPU cap. A stalled worker's `/proc/<pid>/status` reads
`VmSize: 6291360 kB` — the ceiling exactly — against `VmRSS: 169816 kB`:
four gigabytes reserved and never touched, for arithmetic the engine does
not do. On a four-core laptop it fits, which is why nothing saw it until the
loop moved to a build box.

Two fixes, ADR-250, one commit (`2b881775`):

1. `worker_environment` pins `OPENBLAS_NUM_THREADS=4` beside
   `PYTHONHASHSEED=0`, and for the same reason — a worker that behaves
   differently on a laptop and on a 32-core box is the bug. Not a speed
   knob: nothing in the engine is BLAS-bound and `analysis/` is offboard.
2. `_resource_signal_failure` maps SIGXCPU to `DOMAIN_CPU_LIMIT_EXCEEDED`
   and SIGXFSZ to `DOMAIN_OUTPUT_LIMIT_EXCEEDED`, naming the cap and the
   unit asymmetry. The caps themselves are unchanged.

## Why

The plan's short rung named this unit first and the overseer named it again:
bisect one dynamics group at a time, stop at the first that burns the cap,
land the fix plus a regression, and fix the opaque kill too if SIGXCPU is
the root cause. It serves **The walk exists and is tested headlessly**
(`crisp-reef-5607`) and mission item 2.

**The criterion still cannot be ticked.** This unit removes the blocker that
made the first walk exit 3 — it does not run the walk. What is still missing
is one clean `cadex walk --prompt` end to end on this machine, which is the
next unit and is the evidence that closes the gap.

Two decisions taken without a person. **Four threads, not one**: one is
216 MB and simplest, but four is 624 MB, leaves a sparse solve some
parallelism, and still fits with room; the value is a named constant with
the measurement table beside it, so revisiting it is one line. **Name the
kill before touching the cap**: raising `DEFAULT_SCRIPTED_TIMEOUT_SECONDS`
or `RLIMIT_AS` would have hidden this rather than fixed it, and the question
policy asks for the reversible option. The caps are untouched.

## Method

Bisect, each a fresh project via `cadex script --set`, timed from outside
the worker because a script's own `print(..., flush=True)` is lost on the
kill:

- **a1** — all ten bodies, **no collision shapes at all**, minimal
  `assembly.mjcf`: **299.1 s, exit 3.** The bisect was over before it
  started; collisions are not it.
- **b2** — the assembly cut to **two components and one revolute joint**,
  two bodies, no collisions: **300.0 s, exit 3.** So neither the component
  count nor the declarations.

Profiled instead. `ptrace_scope=1` blocks attaching, so py-spy (0.4.2, in a
throwaway venv outside the repo) recorded the whole command with
`--subprocesses`: **119.4 s of 120 sampled in one import chain** —
`mujoco/__init__.py` → `numpy/__init__.py` → `numpy/core/overrides.py:8` →
`create_module`, i.e. stuck in the dlopen of `_multiarray_umath`.

`import mujoco` in a bare `FreeCADCmd` takes 0.12 s under every one of the
worker's rlimits applied singly, so the limit was not the trigger on its
own. Read the stalled worker's `/proc` instead: `VmSize` pinned at the
6,144 MB ceiling with 166 MB resident and 33 threads — one per core. Then
measured the address-space delta of the import against
`OPENBLAS_NUM_THREADS` (the table above), which is linear at ~136 MB per
thread and named the cause outright.

Implementation: `WORKER_BLAS_THREADS`, the `worker_environment` entry, and
`_RESOURCE_SIGNAL_FAILURES` / `_resource_signal_failure` called ahead of
`DOMAIN_WORKER_NO_RESULT` in `CadexScriptedRuntime.py`; ADR-250; the
ROADMAP item flipped from open to fixed; the CPU-second vs wall-clock
asymmetry stated in `docs/XSCRIPT.md` and `docs/ARCHITECTURE.md`, both
re-dated.

## Result

**Fixed, and measured on the thing that failed.** The walk's own accepted
`script.py` at `params --set policy_on=1`: **300.0 s / exit 3 → 2.0 s**. The
two bisect variants that had burned the cap: **b2 300.0 s → 0.8 s**, **a1
299.1 s → 1.2 s**. The full dynamics layer — ten bodies with per-component
collisions, the servo actuator with its real limits, joint dynamics, four
observations, reward, termination, randomisation and both ranged
`assembly.disturbance` values — **accepts in 1.2 s**, where nothing of it
had ever built. What remains on the walk's script is `Policy output
'swing_policy' names no staged asset 'swing.cxpolicy'`, which is the walk's
ordinary ordering: `cadex train` writes that asset and the script
re-declares it.

`pixi run python -m pytest src/Mod/cadex/cadex_tests` — **2086 passed, 53
skipped, 0 failed** in 4:25. The two new regressions in
`test_scripted_process.py` cannot run on the old source (one `KeyError` on
the missing environment entry, one `ImportError` on the missing helper). No
protocol op, no payload change, no `shell/` diff; the diff is 224 lines over
`src/Mod/cadex/**` and `docs/**`.

Bisect variants, profiles and timings were written under `/tmp/ot4-bisect/`
and to `~/cadex-projects/ot4-swing/`, both outside this repository; nothing
generated entered the run branch. The numbers that matter are in ADR-250's
table and above.

The unreconciled tail was 1 node at dispatch and is 2 now.

Dispatch closed: 1 unit — the worker's 300 s dynamics stall is a 4.4 GB
OpenBLAS address-space reservation sized by the host's core count, not a
dynamics declaration; pinned to four threads and the SIGXCPU kill made
legible, taking the walk's own script from 300.0 s / exit 3 to 2.0 s.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot4
- commit: 2b88177533f8fb9c203cfde85787ce3834ada33a

## State Impact

- target: crisp-reef-5607 — the blocker that made the first walk exit 3 is fixed (ADR-250): the walk's own accepted script at policy_on=1 goes 300.0 s / exit 3 to 2.0 s and its full dynamics layer accepts in 1.2 s, so the training layer no longer has to be gated off; the criterion stays open until one clean cadex walk --prompt runs end to end on this machine
- target: salty-isle-4063 — assembly.mjcf's failure to return was never in the rig's dynamics declarations: a two-component model with one revolute joint and no collision shapes stalled identically. The stall is import numpy under import mujoco, where OpenBLAS sizes a per-thread scratch pool from the host's core count and reserves 4,432 MB on 32 cores against the worker's 6,144 MB RLIMIT_AS, then spins in its allocation retry loop until RLIMIT_CPU kills it
- target: forest-wind-0342 — worker_environment now pins OPENBLAS_NUM_THREADS=4 beside PYTHONHASHSEED=0, so a worker's address-space footprint no longer varies with the host's core count; and a kernel budget kill is legible — SIGXCPU and SIGXFSZ surface as DOMAIN_CPU_LIMIT_EXCEEDED and DOMAIN_OUTPUT_LIMIT_EXCEEDED naming the cap and the CPU-second vs wall-clock asymmetry, rather than as the generic 'exited without a result'. Caps unchanged; 2086 engine tests passed, 53 skipped
