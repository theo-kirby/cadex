# hinged-arm — Decisions

## ADR-001 — Ideal mechanism for lifecycle coverage (2026-09-06)

Use one revolute joint, an 80×8×8 mm steel arm and a grounded plate. This is a repository-authored synthetic test mechanism,
not a manufacturer model. The arm derives from the LGPL fixture in
`cli/tests/test_train.py`; the carriage uses existing slider and force-motor
operations. No outside source or imported geometry is needed.

Keep the existing policy-switch convention and run `cadex walk` unchanged.
Use the arm's reward expressions and training caps, stating the force/torque
unit difference explicitly instead of treating scores as a design ranking.
One iteration tests the pipeline; it is insufficient to claim target holding.
No mechanism-specific dispatcher workaround was required.

These examples are inside Cadex's work tree, so the CLI correctly creates
no nested git repository. The parent experiment commit versions source,
documents and numbers. Ignore all policy assets and generated outputs,
and retain a policy-disabled source so a fresh clone can train it again.
