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

## Re-run on the newest cat (2026-10-17)

`results-0f036864.json` repeats the frozen-actor comparison on `0f036864`
itself, now that a policy exists there: orun8-cat's c1-t7 `run.cxpolicy`
(trained on flat, reading the actor height scan of ADR-748), on the same
pools composed onto its own bundle. MJX: 256 envs, 0 non-finite events and a
finite final state on every kind. Tips in 200 steps, MJX / stock (128 seeds):
flat 1.6 / 3.9 %, mild 19.5 / 22.7 %, moguls 3.1 / 5.5 %, rock 3.5 / 5.5 %,
50 cm platforms 12.5 / 11.7 %, mixed 41.4 / 42.2 %, run-out 54.3 / 50.0 %;
every pair within 1.4 stock-side binomial SE. At 32 stock episodes flat read
4/32: seeds 1000-1031 hold a cluster of hard command and shove draws (one
more tip in the next 96), so 32 episodes is too few to compare a rate this
low.
