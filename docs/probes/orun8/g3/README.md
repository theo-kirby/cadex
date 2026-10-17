# orun8 G3: the new ground in MJX (ADR-747)

Frozen run evidence, 2026-10-16. Read it, never cite it as current.

- `compose.py BUNDLE OUTROOT [kind...]` puts the engine's own course
  (`terrain_grid`, `_environment_box_course`) on an exported bundle, one
  16-course pool per kind (mild, moguls, rock, platform50, mixed, runout).
  Run from the training venv.
- `probe.py mjx BUNDLE ACTOR` steps the trainer's own MJX environment
  (`build_environment`) with a frozen `.cxpolicy`, or `random` / `zero`
  actions, and counts non-finite events and first-episode tips.
  `probe.py stock BUNDLE ACTOR` plays the same pool in stock MuJoCo through
  `CadexDynamics.rollout_policy`.
- `wallcheck.py BUNDLE ACTOR N` reports how deep any body sits inside a
  platform on a feet-only course.
- `results.json` holds every leg's numbers and the iteration costs
  (`cadex_train.py --envs 8192 --iterations 5`, timestamped per iteration).

The bundles were orun8-cat's `0f036864` `run` export and terrain-cat's
`rough-c4` training bundle; the frozen actor was rough-c4's
`run.000050.cxpolicy` (its `run.best` is iteration 0 and tips every
episode).
