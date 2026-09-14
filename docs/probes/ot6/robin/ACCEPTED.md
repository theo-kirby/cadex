# Robin — reset repair accepted; reopen remains blocked

Verified against source: 2026-09-14. [Cadex-new]

Historical receipt for revision `71709063d6af…`. Current result: [D-bore construction revised; reopen holds](BORE.md).

Robin is now the complete **24-solid product-agent design**, accepted at
`71709063d6af7ee357d5bb5b409e3332730a1465e0caa62f92f93535ec04cd84`.
The [repair receipt](repair.json) separates the original authored candidate
from the actor's one literal repair: reset `height_mm=[1.0, 3.0]` became
`[3.0, 5.0]`. No geometry, catalog choice, joint, proxy or reward changed.
The original candidate's 1.31 mm extra floor penetration required at least
1.31 mm more minimum lift; the repair adds 2 mm. The accepted task reports
zero additional penetration at the engine's sampled worst-tilt azimuths.
This measurement is penetration, not a positive clearance-margin estimate.

The whole source was submitted through normal acceptance, explicitly dropping
`probe_motor`; no provider turn, alias retry or acceptance bypass was used:

```bash
PROJECTS="$HOME/cadex-projects"
./cadex script --project "$PROJECTS/ot6-robin" \
  --set "$PROJECTS/ot6-robin-src/repaired-candidate.py" --replace --json
python3 docs/probes/ot6/robin/fit_check.py \
  "$PROJECTS/ot6-robin" "$PROJECTS/ot6-robin-src"
```

## Inventory and measured fits

[fit.json](fit.json) carries all 24 inventory rows, masses, catalog identifiers,
proxy-to-solid relations and **84 passing checks** from 276 retained BREP
component-pair measurements. The generator writes `ot6-robin/docs/INVENTORY.md`
and `docs/FIT.md`; their digests are in the repair receipt. Five printed parts
(chassis, two wheels and two clamps) mount nineteen catalog solids: two Pololu
2367 gearmotors, one Pi Zero 2 W, eight M2 inserts and eight M2 screws.
Total mass is **139.601 g**, excluding the proposed ~100 g battery.
No floor or other world geometry is a design part.

Motor/chassis nearest clearance is **0.30 mm** on each side; each clamp contacts
its motor without overlap. The D-bore skin clearance is **0.05 mm**, matching
0.1 mm diametral clearance. Board, clamp screws and insert seats have no
unintended intersections. Only the eight matching screw/insert pairs overlap,
**4.852224 mm³ each**, exceeding a conservative 3 mm annular-thread-equivalent
engagement. The original stdout's 12.566 mm³ claim incorrectly treats the insert
as a solid cylinder; it is not used as evidence. Every output is a valid single
solid. Joint solve code and all joint residuals are zero, with two remaining
wheel DoFs. Only the two wheel proxies contact the environment initially.

Limits are explicit: these are initial-pose fits, not swept or fabrication
checks. The motor shoulder has 0.3 mm clearance rather than registering by face
contact. Wheel fit is a clearance fit, not demonstrated press-fit retention.
The 8 mm hub engagement, 1 mm boss gap and 39×68×21 mm usable battery bay are
source-derived dimensions; the attempted independent section did not complete.
No separate horn or bearing is needed by this gearmotor layout; the motor's
internal shaft support is part of its catalog envelope. The inventory records
sphere wheel proxies' overhang beyond the real tread; they are not shown by
default.

## Reopen refusal — unresolved, before training

Follow-up: [the restore probe](RESTORE.md) isolates nondeterminism to the
catalog shaft offset, including a direct kernel replay from identical input
BREP bytes. The accepted identity is unchanged and reopening remains blocked.

After acceptance, this command exited 1:

```bash
./cadex section --project "$PROJECTS/ot6-robin" --plane XY --offset-mm 50 --json
```

It refused **“The restore pass digest does not match the accepted digest.”**
The accepted result digest is `806ab1343b7c…`; the rebuilt digest is
`d7e568d29a53…`. Both results are retained externally. A read-only comparison
found reordered right-wheel face/edge details and very small inertia differences;
this is a lead, not a proven diagnosis of the digest mismatch. The task artifact
itself did not change. Nothing was re-accepted to hide the failure. Fix this
before training; the design's accepted-state durability remains unproven.

## Persistent review

The server was moved from Finch to Robin **after complete acceptance** and
remains running on `http://<private-address>:8765/`. A fresh browser at 1400×900
and 400×850 selected `accepted`, reported 24 components / **57,044 triangles**,
showed tessellated solids by default, and toggled nine collision outlines.
Neither width overflowed horizontally. [operator.json](operator.json) is the
browser receipt; [desktop](operator-1400.png) and [phone](operator-400.png)
show the empty battery bay, board on bosses, wheels and fasteners. Motors are
mostly concealed by their pockets from this view. The screenshot is evidence of
the retained model, not successful reopen. There are zero training runs.

The experiment start model API still showed Finch's 29 components; the end
browser checks showed Robin. No product code, dependencies or protocol changed;
no full build or full D9 suite was repeated. The meaningful checks for this
unit are real acceptance, retained fits, browser inspection and the evidence
size/privacy gate. **D7 remains open** for the restore repair, remaining fit
limitations, bounded training, recording and measurements.
