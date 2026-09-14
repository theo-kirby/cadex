# Heron — a buildable two-DoF MG90S arm, designed by the product agent (D8, design half)

Verified against source: 2026-09-14. [Cadex-new]

Heron is the charter's single servo arm (ADR-328 D8), designed by the product
agent from [one prompt](design.json) in the
fresh external project `ot6-heron`, corrected three times by the same agent
against **measurements** the actor put in front of it, accepted at revision
`9c1f2fe7ea19…` (digest `f9be3985bc55…`), reopened in five fresh processes, and
served on the persistent operator dashboard at both charter widths. Its
training half is [TRAINING.md](TRAINING.md) (ADR-340). [design.json](design.json) is the
identity receipt (prompt digests, the four turns' timings and exit codes, the
eight-entry script history, the three defects and where each was corrected);
[fit.json](fit.json) the inventory and fit check; [reopen.json](reopen.json)
the fresh-process restores; [operator.json](operator.json) the dashboard.
Full stdout/stderr, the four accepted sources and the section envelopes stay
under `$PROJECTS/ot6-heron-src/`, cited by SHA-256 in `design.json`.

## The machine

Two `lib.servo("mg90s")` on one printed joint module, the servo on the
**parent** (window through the outboard cheek at `window_clear` 0.3 mm per
side, tab plate seated on the cheek's outer face, two `m2x6-socket` screws
into 1.6 mm tap-drilled holes) and the catalog `single_arm` horn on the
**child** (form-fit pocket, floor in contact, sides at `horn_clear` 0.2 mm,
an `m2x16-socket` centre screw down the spline), with the child's printed
7.9 mm stub turning in an `mr128` bearing pressed into the inboard cheek
(`stub_clear` 0.1 mm radial) behind a 9 mm retaining lip. Three printed parts:
a grounded **base** (bench foot with four M3 clearance holes, webs, shoulder
clevis), an **upper arm** (80 mm axis to axis, elbow clevis at its far end) and
a **forearm** (70 mm to a rounded tip, its component frame *at the tip* so
`component_position` reads the tip). Reach 150 mm from a shoulder at z = 40.

| | |
|---|---|
| solids | 15: 3 modelled printable parts, 12 catalog parts (2 servos, 2 horns, 2 bearings, 4 tab screws, 2 centre screws) |
| mass | printed 86.6 g, purchased 33.0 g, total 119.5 g |
| task | `heron_task`: 200 steps at 50 Hz; reward `exp(-|tip − (100, 0, 60)|/30)` − 2e-6·Σf² − 5e-4·|tip velocity|; terminate on `tip_z` < 5 mm; two 0.2–0.6 N, 0.2 s horizontal pushes on the forearm at world azimuth 0° and 180°, drawn between 1.4 and 2.6 s; seeds 0–9 through `rollout_seed`; the target does not vary |
| actuators | two MG90S position servos through `servo.actuator`, stall 176.5 N·mm at 4.8 V, damping from stall over no-load speed |
| world | nothing: no floor, bench, wall or stage geom; the base is grounded because an arm is bolted to its bench |

## Three defects the measurements found, and the agent corrected

The first accepted mechanism (`7e9eff5c4ff2…`) was accepted by the engine and
was wrong three ways that only the published measurements showed. Each was
put back to the product agent as a resumed turn quoting the measurement; each
correction was the agent's own, submitted whole through normal acceptance, and
its `DECISIONS.md` carries a line for each (ADR-006 to ADR-008 in the project).

1. **A bench plane in the design.** The grounded base carried
   `assembly.collision("plane")`. The engine supplies a floor only to a free
   base (ADR-335), so the agent had reached for one; the charter forbids world
   geometry in a project script. Removed (`2207f8b96b01…`).
2. **Servo tabs buried in the cheeks.** The published clearance table reported
   **248.2016 mm³** of common volume between base and shoulder servo and the
   same between upper arm and elbow servo, while the script's stdout claimed
   "tabs seat on cheek outer face (contact, volume 0)". The number is exactly
   the tab plate outside the window minus its two holes,
   (32.5 − 23.4) × 12.2 × 2.4 − 2π·1.1²·2.4: the cheek's outer face had been put
   at the tab plate's spline-side face. Cheeks moved one `tab_thickness_mm`
   inboard (`ac441479204d…`).
3. **A horn that met nothing.** Child/horn distance was **0.2 mm**: the pocket
   cleared the horn on its floor as well as its sides, so the horn only met its
   link once the centre screw pulled the modelled side gap shut. Pocket depth
   made exactly the hub height (`9c1f2fe7ea19…`); each child grew by the
   analytic 18.7168 mm³ floor layer and nothing else changed.

A script's own stdout is not evidence; the retained clearance pairs are. The
fit check below reads only those.

## Inventory and fit check

[`fit_check.py`](fit_check.py) reads the accepted attempt's published
measurements (pair distance and common volume on the exact BREP at the solved
rest pose, ADR-237; masses from the mjcf export; catalog identity per output)
and three `cadex section` cuts, writes the project's `docs/INVENTORY.md` and
`docs/FIT.md`, and exits 1 on any failed rule. **55 of 55 checks hold** on 105
measured pairs with no unmeasured pair:

- per joint: tab plate on the cheek 0 / 0; horn in its pocket 0 / 0; horn on
  the spline top 0 / 0; bearing pressed in the cheek 0 / 0; stub in the bearing
  0.1 mm radial; centre screw head seated in the block counterbore 0 / 0 and
  its spline engagement π·1²·3.0 = 9.4248 mm³; each tab screw's cheek
  engagement π(1² − 0.8²)·3.6 = 4.0715 mm³ with no tab overlap; the stub's
  nearest approach to the cheek the 0.6 mm lip-hole clearance;
- the window clearance 0.30 mm around both cases, from the XZ section through
  the outboard cheeks' mid-plane (y = −16.5); the side gap 1.00 mm at both
  joints, from XY sections 5.3 mm above each axis (an exact 6 mm lands on a
  tessellation edge and the cut refuses rather than guesses);
- no intersection other than the six thread engagements; no plane or world
  geom; no initial proxy contact; the base the only grounded component;
  exactly two limited hinges; every output a valid single solid; solved at
  zero residual; the task's episode, termination and disturbances as declared.

Limits: the solved rest pose only, not swept motion or fabrication; a press fit
and a screw engagement are modelled overlaps, not tested retention.

## Reopen, and the dashboard

Five fresh-process `cadex section` runs on the accepted project, each through
the default restore pass that refuses on a digest mismatch, exited 0 at the
accepted revision with the one digest `f9be3985bc55…` ([reopen.json](reopen.json)).

```bash
PROJECTS="$HOME/cadex-projects"
timeout 1800 ./cadex --project "$PROJECTS/ot6-heron" --out "$PROJECTS/ot6-heron-src/create-out" --json -p "$(cat "$PROJECTS/ot6-heron-src/create.prompt.txt")"
# ...three --resume correction turns, then:
for c in "XZ -16.5" "XY 45.3" "XY 125.3"; do ./cadex section --project "$PROJECTS/ot6-heron" --plane ${c% *} --offset-mm ${c#* } --json; done
pixi run python docs/probes/ot6/heron/fit_check.py "$PROJECTS/ot6-heron" "$PROJECTS/ot6-heron-src/iteration24/fit"
systemctl --user stop cadex-operator-review
systemd-run --user --unit=cadex-operator-review --property=Restart=on-failure --working-directory="$PWD" \
  "$PWD/cadex" review --project "$PROJECTS/ot6-heron" --host "$(tailscale ip -4)" --port 8765
PYTHONPATH=cli pixi run python docs/probes/ot6/heron/operator_probe.py "http://<private-address>:8765/" docs/probes/ot6/heron
```

At the start of this iteration the persistent dashboard served Robin's
`robin2-final` at both widths (receipt under `ot6-heron-src/iteration24/start`).
After acceptance the service was moved to Heron — one project per server, the
project being worked on. Fresh headless browsers at 1400×900 and touch-emulated
400×850 selected `accepted`, loaded **15 components, 29,234 triangles**,
`showing: tessellated solids`, toggled **20 proxy outlines** under the labelled
collision control, and neither width overflowed horizontally
([operator-1400.png](operator-1400.png), [operator-400.png](operator-400.png)).
The default view is from the bearing side: the base, the upright upper arm and
the forward forearm with the servo cases outboard of the cheeks and the centre
screws at the joints. `cli/tests/test_review_design.py` pins these receipts.

No product code, protocol or dependency changed. The section tool's refusal of
a cut through a tessellation edge (`unsupported`) is pre-existing behaviour,
worked around by offset, not changed. D8's training half — one bounded run,
checkpoint and final videos in the D3 look, the reach measured over seeds 0–9
— is [TRAINING.md](TRAINING.md) and `training.json` (ADR-340).
