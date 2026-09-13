# Live accepted-model refresh

Verified against source: 2026-09-13. [Cadex-new]

Iteration 62 fixes a D2/D10 lifecycle defect (ADR-307). An already-open
accepted view updated its revision label and parameters after acceptance, but
kept drawing the previous model. A previously empty view stayed empty.
Polling now compares the selected model revision and digest and reloads its
geometry when they change. Unchanged polls preserve orbit/zoom and a selected
historical run retains its own mesh.

Two headless Chromium regressions failed against the old source, with the
visible identity at revision A while the model remained B or null. Both pass
with the fix, checking a newly published 40 mm cube's actual bounds, a deliberate
camera change surviving another poll, and a retained run's distinct revision.
These acceptance transitions use fixtures; no new Wren acceptance is claimed.

The persistent private-network port 8765 still serves **ot5-wren-copy54**,
selecting **wren57-retry**, revision `79f86c69bfc3…`. Current, accepted and
historical `wren2-final` documents stayed visible through 6.5 seconds of polling
each. Return-to-current passed. The retry video played through three polls,
downloaded with SHA-256 `4d418967d41c1fe39b3ec2fa6945a0e8b5cf18343c4e3f5b1d0cf3dffbc3945e`,
and decoded to 81 frames at 10 fps: 8.1 encoded seconds for eight simulation
seconds. Its eight model components, 110 mm feet and curves were present.
The service remains running. These are same-machine private-address checks,
not a second-device test or a new visual-reference comparison.

No provider attempt was made: the unit was chosen at 22:38 local time, before
the retained refusal's reported 22:40 reset, using the critic's concrete-defect
fallback. The reset has since passed; a subsequent iteration may attempt the
product-agent revision once, without treating this as proof capacity recovered.
No design, policy, training or project history was modified by this unit.

Full probes, screenshots, decoded-video receipt and suite logs remain
project-local under `evidence/model62/`; retain that directory with the copy.
[Compact receipt](model62-evidence.json). Reproduce the persistent checks with:

```bash
PYTHONPATH=cli:cli/tests pixi run python \
  "$HOME/cadex-projects/ot5-wren-copy54/evidence/model62/browser.py"
PYTHONPATH=cli:cli/tests pixi run python \
  "$HOME/cadex-projects/ot5-wren-copy54/evidence/model62/check_video.py" \
  "$HOME/cadex-projects/ot5-wren-copy54" wren57-retry \
  "http://$(tailscale ip -4):8765/"
```

Verification: `OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 pixi run python -m
pytest cli/tests` passed **403 tests, one skipped** in 387.61 s. Sequential
`pixi run test-engine` with the same thread bounds passed **2110 tests,
53 skipped** in 254.05 s. Both gates exited 0; no build or dependency was
needed. The compact receipt includes the full-log hashes.
