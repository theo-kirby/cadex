# Robin — wheel D-bore revised; reopen holds

Verified against source: 2026-09-14. [Cadex-new]

Robin reopens. Revision `71709063d6af…` could not pass its restore digest check
because each wheel's D-bore was the `part.offset` of the catalog D-shaft segment,
and that kernel offset was measured to be non-reproducible across fresh processes
([RESTORE.md](RESTORE.md)). This unit is a **design correction accepted as a new
revision**, not a recovery of the old bytes: the old revision keeps its identity,
its script (`script_history/0002-71709063d6af.py`) and its failure evidence.

## The change

The bore is now an analytic D-prism authored in the gearmotor's canonical frame
(axis +Z, flat towards +Y, as `lib.gearmotor` documents) and placed with the same
(origin, direction) transform the library applies, so the flat follows the motor:

```python
FLAT_Y = MS["shaft_flat_to_opposite_mm"] - SHAFT_R          # catalog flat plane, 1.0
bore_r = SHAFT_R + p.bore_clear / 2.0                       # 1.55
d_round = part.cylinder(bore_r, bore_len, origin=[0, 0, bore_z0])
d_flat = part.box(2 * bore_r + 2.0, 2 * bore_r, bore_len + 2.0,
                  origin=[-bore_r - 1.0, FLAT_Y + p.bore_clear / 2.0, bore_z0 - 1.0])
cutter = part.transform(part.cut(d_round, [d_flat]), translation=[0, s * mf, axle_z],
                        rotation_axis=[-s, 0.0, 0.0], rotation_degrees=90.0)
```

Nothing else in the mechanism changed: [bore.json](bore.json) hashes the previous
accepted source and the candidate; the diff is that block, its stdout line and one
header comment. The declared diametral clearance `bore_clear` = 0.1 mm is kept as
0.05 mm on the round and 0.05 mm on the flat. Where the offset shape rounded the
flat's corners the prism is sharp, so clearance there is larger, never smaller. The
engine's offset op and the digest rule are untouched; no product code changed.

## Acceptance, fits and reopen

Submitted the whole source through normal acceptance, dropping no output:

```bash
PROJECTS="$HOME/cadex-projects"
./cadex script --project "$PROJECTS/ot6-robin" \
        --set "$PROJECTS/ot6-robin-src/bore-candidate.py" --json
python3 docs/probes/ot6/robin/fit_check.py "$PROJECTS/ot6-robin" "$PROJECTS/ot6-robin-src/iteration21/fit"
for i in 1 2 3; do ./cadex section --project "$PROJECTS/ot6-robin" --plane XY --offset-mm 50 --json; done
```

Accepted revision `5ad94d65e61a…`, digest `185f9ccc4f96…`, history entry
`0003-5ad94d65e61a.py`. Then **three fresh-process `section` runs, each through the
default restore pass, exited 0 with the accepted digest** (this is the command that
exited 1 on the old revision). The retained restore attempts differ from one another
only in `budget/elapsed_seconds`.

[bore-fit.json](bore-fit.json) is the fit check on the restored attempt: 24 valid
single solids, 276 measured pairs, **84 passing checks**, 139.601 g. Wheel/motor
nearest approach is **0.05 mm on each side with zero overlap**; motor pockets 0.30 mm;
clamps and board in contact; eight screw/insert engagements; no grounded component;
solver code 0; zero additional reset penetration. The same script run on the
acceptance attempt before it was pruned gave identical rows and checks. Each wheel's
volume fell by 0.00104 mm³ against the old revision (the sharp-cornered prism removes
slightly more), and every other inventory row is byte-identical. The project's
`docs/INVENTORY.md` and `docs/FIT.md` are regenerated for this revision; its
`DECISIONS.md` carries the design-correction entry.

## The dashboard

The persistent `cadex-operator-review` user unit stayed active on Robin throughout.
Fresh headless browsers at 1400×900 and touch-emulated 400×850 showed, at the start,
revision `71709063d6af` (24 components, 57,044 triangles) and, at the end, revision
`5ad94d65e61a` (24 components, 56,996 triangles), `accepted` selected, tessellated
solids by default, nine proxy outlines under the labelled toggle, and no horizontal
overflow. [bore-operator-1400.png](bore-operator-1400.png) and
[bore-operator-400.png](bore-operator-400.png) are the end-state model views.

## What this does and does not establish

Three consecutive matching reopens are evidence that this construction is
reproducible in this environment; they are not a proof for every future process.
The old revision's script_artifacts were pruned by the store's ordinary ADR-045
lifecycle (they are rebuild output and git-ignored), so
[restore_probe.py](restore_probe.py) now reads the current revision; the old
revision's accepted result, failed section envelope and frozen replay inputs stay
under `ot6-robin-src/`. No training was started; reopen was the blocker, and D7's
next unit is Robin's bounded training run. Evidence-cap and privacy tests were run
after writing this receipt; the record carries their counts.
