---
node_id: c5090e95-da9e-5113-a091-3779499b8773
slug: tidy-cove-8382
title: A stopped walk leg kills its whole group, even when the child died politely
created_at: '2026-09-08T19:39:30+00:00'
parents:
- honest-river-1137
summary: ''
---
## What

Closed the critic's must-fix on ADR-261's leg bound: a walk leg that runs out
of time now kills its whole process group even when the direct child died
politely, and the drain that follows the kill is bounded.

Three corrections in `cli/cadex_cli/walk.py`, one regression in
`cli/tests/test_walk.py`, and the doc/ADR/ROADMAP text that described the
intended behaviour rather than the shipped one:

- `leg_pgid(process)` reads the group id once, in `run_leg`, immediately
  after `Popen` and while the child is certainly alive. `_stop_leg` and the
  `SIGINT`/`SIGTERM` relay both take it as an argument. Previously every
  signal call did `os.getpgid(process.pid)` at the moment of use, which
  raises once `wait` has reaped the child — so the group holding the
  survivor was unaddressable at exactly the moment it mattered.
- `_stop_leg` sends `SIGKILL` to the group after `LEG_TERMINATION_GRACE_S`
  **unconditionally**, instead of only in the `except TimeoutExpired` branch
  of the direct child's `wait`.
- `run_leg`'s post-stop drain goes through a new `_drain()` bounded by
  `LEG_DRAIN_S` (10 s): partial stdout from the `TimeoutExpired` is kept, the
  pipe is closed, and the walk moves on. It was an unbounded
  `process.communicate()`.

## Why

Charter criterion **"The walk exists and is tested headlessly"**
(`crisp-reef-5607`), and the frontier node behind it: the bound exists so an
unattended machine cannot be hung forever by a provider that stalls rather
than refusing. The shipped bound did not deliver that in the case that
actually occurs.

The failure the critic named, traced through the code: `_stop_leg` signalled
the group with `SIGTERM`, then `process.wait(grace)`. The direct child is a
`cadex` command with a default `SIGTERM` handler, so it dies at once and the
`wait` **succeeds** — which took the old code straight past the `except`
branch that held the only `SIGKILL`. The grandchild that ignores `SIGTERM`
(an agent CLI in a signal-swallowing state, an ssh, a trainer with its own
handler) then survives, still holding the stdout the leg inherited, and
`run_leg`'s unbounded `process.communicate()` blocks on that pipe forever.
The walk reports nothing, the leg never returns, and the machine is occupied
by the process the timeout was supposed to remove — strictly worse than no
bound at all, because the run now *looks* protected.

ADR-261's property 2 already claimed the subtree kill; this makes the code do
what the ADR said. The reversibility rule was followed by keeping every
existing knob: `--leg-timeout 0` still restores the old unbounded behaviour
exactly, and no leg semantics changed.

## Method

Read `_stop_leg`, `_signal_leg`, `_relaying_signals` and `run_leg`; threaded
a captured pgid through all four; moved the kill out of the `except`; added
`_drain`.

Wrote `test_a_stopped_leg_kills_the_grandchild_that_ignored_the_term`, whose
fake `cadex` spawns a grandchild that sets `SIGTERM` to `SIG_IGN`, writes its
pid to a marker, inherits the captured pipe and sleeps 120 s (self-bounding,
so a regression fails slowly instead of hanging a suite); the direct child
sleeps 600 s with the default handler. The walk runs with `--leg-timeout 2`;
the test asserts `EXIT_FAILURE`, leg exit 124, that the walk returned inside
40 s, and polls the grandchild's pid until it is gone.

**Mutation-verified.** With `_stop_leg` reverted to the shipped shape (kill
only inside the `except`) and everything else new, the test fails in 22.6 s:
`the leg's stubborn grandchild 1506134 outlived the walk`. That run also
shows `_drain` doing its half — without it the same case would have blocked
the full 120 s and failed the `elapsed < 40` assertion instead.

Docs updated in the same commit: `docs/CLI.md` §2's stop paragraph (the
unconditional kill, the pgid capture, the ten-second drain), an
**Amendment** section on ADR-261 saying the grace was a hole rather than a
grace, and the ROADMAP bullet.

## Result

`pixi run python -m pytest cli/tests`: **239 passed in 216.08 s**, exit 0 — the
whole suite, no skips.

The two subtree tests pass together (`-k "grandchild or subtree"`, 2 passed),
and the previously shipped `_stop_leg` fails the new one.

What is still missing before `crisp-reef-5607` can be ticked: the criterion
wants a clean end-to-end run of the documented entry point on this machine.
This unit removed a hazard in that entry point; it did not run it. The next
unit is the plan's unit 1 — the token-free `--set` iterate walk on
`ot4-quill` (no `--prompt`, one real parameter, 5 x 16 / seed 0, into
`runs/<name>`), which is the only unspent thing that exercises both the new
bound and ADR-260's two travel channels on geometry no fixture has seen.

The unreconciled tail is three nodes deep; a maintainer pass is due.

Dispatch closed: 1 unit — a stopped walk leg now SIGKILLs its whole group even when the direct child died on the term, and the drain after it is bounded; regression fails against the shipped stop; 239 cli tests pass.

## State Impact

- target: crisp-reef-5607 — the leg bound ADR-261 shipped did not stop the case it was built for: SIGKILL reached the group only when the direct child survived the grace, so a grandchild ignoring SIGTERM outlived its parent and hung the walk in an unbounded stdout drain. The kill is now unconditional, the group id is captured while the child is alive, the drain is bounded at 10 s, and a mutation-verified regression pins it. The walk's headless entry point is safe to run unattended; the criterion still needs a clean end-to-end run on this machine.
