# PROVENANCE qualifications — source audits and probe narratives

> **Historical (moved out of `docs/PROVENANCE.md` 2026-10-27, ADR-828).** The qualification narratives behind the catalog parts: experiments, reproductions, measured results and audits that did not deliver a part, plus the Blender shell's detail. The source identities, licence facts and credits stay in `docs/PROVENANCE.md`. Probe scripts are in `docs/probes/experiments/`; relative links below are as they stood in `docs/`, now resolved from `docs/history/`.

## Blender — the shell (detail of PROVENANCE §3)


**What it was.** From 2026-07-25 to 2026-10-03, the shell was a Blender fork
(Blender 5.3 alpha, by way of our own `mesh` fork) and the product's user
interface: the viewport, the editors, the Blender file format, and the
assistant package. It was GPL-2.0-or-later, and it spoke to
the engine only over the cadexd protocol, through a client that imported no
engine code.

**What happened to it.** ADR-495 disabled it and ADR-498 deleted it, with
its vendored `extern/`, its four `lib/<platform>` library submodules, its
Git LFS assets and its half of `docs/inherited-modifications.json`. The
dashboard (`cli/cadex_cli/review_server.py`) is the only user interface now,
and [`SHELL-PARITY.md`](SHELL-PARITY.md) records, module by module, what
became of each part of the assistant package. The tag `v1-blender-shell` is the last
tree that carries the shell, and its ledger is
[`history/BLENDER-TREE.md`](BLENDER-TREE.md).

**What it left behind.** No code. The shell's code was GPL and the rest of
the repository is LGPL, so nothing of it was ever copied out; what the
dashboard and the CLI do in its place is re-derived (ADR-061). Ideas
survive — the review dashboard's dark palette, the appearance roles, the
rollout playback — and they are ours to carry because ideas are not code.

**Credit.** For two and a half months the interface Cadex presented —
viewport, navigation, tools, theming — was Blender's, built by the Blender
Foundation and its contributors. Cadex was never affiliated with or
endorsed by the Blender project.

## L12 nominal geometry experiment (PROVENANCE §8d)


[`experiments/l12_nominal_probe.py`](../probes/experiments/l12_nominal_probe.py) builds
an independently authored primitive approximation with the existing OCCT
engine. Its header gives the headless reproduction command; it imports no
manufacturer file. Datum is the rear bore centre, travel is +Z, and both
bores run along X. The newer drawing determines centre spacing and 4.25 mm
bore diameter. This experiment established the construction now used by
`lib.linear_actuator`; it does not establish a tolerance model.

Additional measurements from the already identified `l12_50mm_in.stp`:
the supplied clevis (zero-based solid 10) has planar bore-side flats at
X = ±3 mm. At source Y = -67, Z = 3, material exists at X = 2.9 but not
3.1 mm. The rear lug (solid 2 at this probe) has material at X = 3.9 but
not 4.1 mm at source Y = 35.5, Z = 3. These establish nominal bore-region
widths of 6 and 8 mm in that CAD, not fit tolerances. Reproduce with
`Part.read` as above, then `shape.Solids[10].isInside(FreeCAD.Vector(x,-67,3),
1e-7,True)` and `shape.Solids[2].isInside(FreeCAD.Vector(x,35.5,3),1e-7,True)`.
The sleeve's CAD bounds are approximately X/Z ±6, Y -60 to 0.

The experiment uses those bore widths and a 12 mm square sleeve. Its 9 mm
shaft and clevis diameter, 37 mm housing length, and 14.9/18 mm housing
dimensions follow the drawing. **Placement and transitions are explicit
approximations:** housing Z 4.5–41.5, rear lug Z -4.5–8, sleeve Z 35.5–95.5,
shaft Z 90–(98+extension), and clevis Z (97.5+extension)–(106.5+extension).
The rear lug is a box; the clevis is a flat-ended cylinder clipped to its
6 mm flats. This does not reproduce the rounded clevis tip, threaded neck,
housing bumps, fillets or local seams. The 9 mm rear drawing dimension is
**not** interpreted as a hole-centre offset. No blanket 0.5 mm correction
is applied to the manufacturer's surfaces.

The filled, fused solids omit internals, shaft hollowing, thread engagement,
clamps, mounting brackets, fasteners, cable/connector and their clearance.
They are neither a conservative overall collision envelope nor physical
mass/inertia geometry. Assembly fit, installation clearance, strength,
switch reachability and dynamics remain unverified.

| Extension (mm) | Measured bore spacing (mm) | Approximation volume (mm³) | Material/void probes, canonical + placed |
|---|---|---|---|
| 0 | 102 | 18730.103513 | 60 passed |
| 23.5 | 125.5 | 20225.108917 | 60 passed |
| 50 | 152 | 21910.966075 | 60 passed |

Each shape is valid with one solid. Bounds are X [-7.45,7.45], Y [-7.5,10.5],
Z [-4.5,106.5+extension] mm. Probes check the full bore width, points just
inside/outside the bore wall and lug flats, and sleeve/shaft material.
A 120° rotation about (1,1,1) followed by translation (100,30,20) preserves
volume and all probes, checked against the explicit coordinate mapping
(x,y,z) → (100+z,30+x,20+y). The volume grows because the exterior model
fills the exposed shaft; these numbers are kernel diagnostics only.

Next: translate this bounded construction into the existing LibraryPart
contract, retain these approximation limits in `.spec`, reject unsupported
selection/extension, and verify the actual recipe through the worker and
packaged gates. This experiment does not close L3 implementation.


## Solenoid 412 audit (PROVENANCE §8e)


Accessed 2026-09-07. Adafruit's [product 412](https://www.adafruit.com/product/412)
links the supplier Chaocheng TAU0730TM-14 documents below. The page identifies
its 12 V replacement as dating from 2018-01-17, but advertises 5.5 mm throw;
that is not the drawing's travel. This audit targets the documented supplier
variant, not every unit historically sold as 412.

| Source | Identity | SHA-256 of downloaded PDF |
|---|---|---|
| [Drawing](https://cdn-shop.adafruit.com/product-files/412/412_C514-B_diagram.PDF) | Part 10104-00073014, version 1, 2021-08-30 (filename says C514-B) | `adaa02703b1129b36f8a01174592ff464a68cc1a7ad1c7628bd83b9f47b44574` |
| [Technical specification](https://cdn-shop.adafruit.com/product-files/412/C514-datasheet.pdf) | TAU0730TM-14, version A, design 21/07/12, three pages | `6fd2bac2a24fcabca3323469fcf3e8f76f449f0e073a1b01f2e041d73a2cf808` |

**Electrical qualifications.** The specification gives 12 V, 40 ohms at
20°C, nominal 0.3 A (±5%) and 3.6 W, with 50% duty. Force is approximately
0.5 N at 4 mm and at least 5 N at zero gap; its standard test conditions
are 60±2°C, 65±5% RH, 1013 mbar, empty load and a vertical armature.
Temperature rise is at most 65°C at 12 V with one second on/one second off;
operation is -5 to 60°C, 45–85% RH. These are supplier claims, not Cadex
measurements. Neither point supplies a force curve or starting-force rating
at full drawing travel. Duty percentage alone does not specify an arbitrary
safe pulse length; no continuous-force, thermal or dynamics model is inferred.

**Drawing facts and missing interfaces.** The drawing explicitly depicts
energized holding position and lists 4.9 mm stroke. Body dimensions are
29.7±0.1 by 17 (+0.25/-0.1) by 14±0.1 mm; overall axial length is
51.9±0.1 mm. The push cap is diameter 5 by 10 mm, its tip projects
15.4 (+0/-0.1) mm beyond the main body face, and the rear head diameter is
6.9 mm. Mounting centres have an 18.2±0.05 mm transverse separation, but
hole diameter, axial positions, tab profile and plate thickness are not
specified. Do not scale pixels into manufacturing dimensions. The exposed
neck diameter, cap attachment and rear head height also lack callouts.

**Reproducible partial construction.** Run:

```bash
build/release/bin/FreeCADCmd -c 'exec(open("docs/probes/experiments/solenoid_412_probe.py").read())'
```

The independently authored experiment fills a box and cylinders; no supplier
CAD, drawing, code or artwork is redistributed. Z=0 is the main body's push
face, +Z is the energized push direction. `gap=0` represents the drawing's
held position; opening translates both plunger ends by `-gap`, within
[0,4.9] mm. This is a geometric convention, not powered endpoint proof.
The centered body occupies X ±8.5, Y ±7, Z [-29.7,0]. Its centering on the
plunger is an explicit approximation. The push cap occupies Z
[5.4-gap,15.4-gap]. The rear tip is inferred from the overall length as
-36.5-gap. A diameter-3 neck and a 2 mm long rear head are **cosmetic
choices**, not sourced dimensions. The omitted small face step is absorbed
into the filled-body/neck approximation.

Mounting tabs/holes, spring, retaining clip, leads, internal coil, armature
steps, insulation, chamfers and threads are omitted. Thus this is a partial
visual exterior, neither an installation/collision envelope nor physical
mass/inertia geometry. In particular no nominal mounting interface is proved.

| Gap (mm) | Measured Z bounds (mm) | Volume (mm³) | Canonical + placed probes |
|---|---|---|---|
| 0 | [-36.5,15.4] | 7411.834705 | 24 passed |
| 2.3 | [-38.8,13.1] | 7411.834705 | 24 passed |
| 4.9 | [-41.4,10.5] | 7411.834705 | 24 passed |

All three are valid single solids, with measured cap diameter/axial extents
and 51.9 mm total length. Placement maps (x,y,z) to (100+z,30+x,20+y),
with volume preserved and material/void probes repeated. Negative, nonfinite
and product-page 5.5 mm travel are refused by the experiment. The packaged
lifecycle/library **baseline** passes 76 tests, no skips; it does not test
an unimplemented solenoid API. No engine source, build or payload changed.

**Remaining leg.** Catalog delivery with sourced mounting interfaces is not
yet justified. Obtain a dimensioned mounting drawing for this exact revision,
or select a different traceable solenoid with complete interfaces in a new
bounded source unit. Do not repeat this partial construction, invent hole
locations, or block all L3: joints and other documented solenoids remain
available work. Full L3 stays open.

## Solenoid follow-up: incompatible older drawing and Ledex B7 (ADR-209)


Accessed 2026-09-07. This follow-up does **not** change the partial 412
construction or authorize a solenoid catalog API.

The [TAU-0730TM drawing](https://bc-robotics.com/datasheets/TAU-0730TM.pdf)
linked by [BC Robotics](https://bc-robotics.com/shop/small-push-pull-solenoid/)
is one page without a manufacturer title block, revision or date. SHA-256:
`288d672ee2cecf9c0e97176a856af2bd0e9a1523d9c5f768bde619c171545c5e`.
It depicts slots with R1.6 ends, 3.2 mm between arc centres, 20 mm
transverse separation and 16 mm axial separation; the lower slot centre
is 7 mm from the body end. Its body length is 30.5 mm and overall length
53.4 mm. Those dimensions conflict with the current 412 drawing's
18.2 mm transverse spacing, 29.7 mm body and 51.9 mm overall length.
Its illustrated actuation state is not stated. This is a discovery lead,
not manufacturer evidence for TAU0730TM-14: **do not transplant its slots**.
The indexed [Jameco specification](https://www.jameco.com/Jameco/Products/ProdDS/2219330.pdf)
could not be fetched (HTTP 403); it supplies no additional verified evidence.

The manufacturer-hosted [Ledex B7 sheet](https://www.johnsonelectric.com/pub/media/image/tmp/metric-imperial/B7_20210611.pdf)
offers a better mounting reference. Two pages; filename date 20210611,
no printed revision; SHA-256
`d699124bc39731bd25aa09d238fd538207459444f2d3ef760b55dedf8eab4864`.
For B7-212-B-4 it lists 12 V continuous at 20°C, 47.67 ohms;
18/24/38 V at 50/25/10% duty, with repeated-pulse on-time limits
110/27/8 seconds. Data is typical, force testing horizontal, no heatsink;
the listed holding force is 15.1 N, not a force law.

The energized drawing gives body 29.40 by 19.20 by 16.00 mm,
overall 36.47 mm, and two M3x0.5 mounting holes. One centre is 19 mm
from the rear face; the second is 12 mm nearer that face, with 10 mm
vertical separation (5 mm either side of the plunger axis).
This supports a nominal mounting-plane layout. It does **not** specify
tap depth, allowable screw penetration or frame thickness. Plunger end
diameter 6 mm, neck diameter 3 mm and end/neck lengths 1.5/2.5 mm are
dimensioned, but the intermediate shoulder is not. The force plot ends
at 0.4 inches; no mechanical maximum stroke is stated. Do not turn that
axis limit into a travel stop. No B7 geometry was constructed or tested.

The manufacturer's [open-frame catalog](https://www.johnsonelectric.com/pub/media/image/tmp/metric-imperial/20200212_Open_Frame_DC_in_2_.pdf)
(39 pages, filename date 20200212; SHA-256
`9b681436726ff19465ea42820624b245dfcb25ba15ff6db50ef7dd3c86716226`) has no `B7` text hit, and its
page-4 selection table has no B7 row to resolve the travel limit.
The [older tubular catalog](https://www.relayspec.com/suppliers/j/johnson_electric/news/2018/09_20b/Tubular%20mm_v2.pdf)
was located but no tubular variant was qualified in this unit.

**Decision and next leg.** Neither examined variant meets the planned
complete-interface contract. Keep solenoid implementation open and advance
to the planned joints source unit, rather than repeating this audit.
Resume B7 only with manufacturer engagement/travel evidence or a separately
justified, explicitly narrower contract; no claim that other solenoids are
unsupportable follows from this bounded search. No source assets, geometry,
runtime code or dependencies were added; existing packaged gates verify
the baseline only.

## SKF GE 6 C construction and qualification result (PROVENANCE §8f)

**Independent construction.** [ge6c_joint_probe.py](../probes/experiments/ge6c_joint_probe.py)
uses OCCT sphere/cylinder intersection and subtraction. The outer ring is
a Ø14 × 4 cylinder with a radius-5 spherical cavity; the inner ring is that
sphere clipped to width 6 with a Ø6 through bore. Inner tilt is about Y
through the common centre, bounded to ±13°; arbitrary assembly joint solving
is not introduced. Chamfers, liner thickness, manufacturing seams and radial
running clearance are omitted. The two ideal spherical surfaces coincide:
this is nominal geometry, not a tolerance model, press-fit guarantee,
conservative collision envelope or a manufacturing drawing. It supports
the bounded `lib.joint("skf-ge-6-c", tilt_degrees=...)` value using existing
primitives (ADR-211). The body retains two solids; metadata preserves the
source revision/hash, shoulder limits and qualified ratings.

**Reproduce and result.** Run the FreeCADCmd command in the probe's header
against the existing built headless engine. At -13/0/6.5/13°, each ring is
a valid single solid, outer/inner volumes are 318.348056/245.044227 mm³,
matching independent analytic integrals. Ring overlap is zero, a Ø5.98
test shaft remains clear, actual bore/OD cylinders and spherical surfaces
match nominal dimensions, and 96 material/void probes pass across canonical
and obliquely rotated/translated placements. Nonfinite/out-of-range tilt is
rejected. Ø8 shaft shoulders and Ø9.5 housing openings have zero interference
with the opposing ring at all four tilts (16 nominal shoulder checks).
Qualification-stage packaged lifecycle/library baseline: 76 passed, no skips, 16.23 s.
That audit needed no engine-source edits, build, staging or full engine suite;
the baseline is not packaged joint verification.
This establishes the stated approximation only. Delivery tests (deleted
by ADR-725) exercised the recipe through the actual
part worker, including canonical/placed interfaces, analytic volumes, shoulder
clearances and material/void probes at four tilts, plus cadexd publication and
discovery. The commands for delivery verification were the full engine suite,
`pixi run build-engine`, completed `pixi run stage-engine`, then the packaged
lifecycle/library gate; ADR-211 records the result. Full L3 and the solenoid
interface gaps remain open.

## ISO 53/54 gearing construction and result (PROVENANCE §8g)

**Independent construction.** One generator in `cadex_library_api.py`
samples the involute of the base circle eight times per flank between the
base (or root, when larger) circle and the tip circle, joins the flanks with
tip and root arcs into one counter-clockwise polygon, and extrudes the face;
below the base circle the flank is a radial line. Root fillets, tip relief,
backlash, profile shift and helix are omitted, and no density, strength or
torque rating is supplied. Tip and root vertices lie exactly on their
circles, so the real-kernel test measured the standard's diameters from the
built solid's vertices rather than from the recipe.

**Reproduce and result.** A real-kernel test (deleted by ADR-725; its
result stands as recorded in ADR-233) built m2z20 (bore 6), m2z8, m1z60 (bore 4) and m1z6 gears plus m2z10 and
m1.5z4 racks through the actual part worker: each is one valid solid, tip
and root radii match m(z+2)/2 and m(z−2.5)/2 within 1e-7, the volume lies
between the root and tip cylinders, the bore is the only cylindrical
surface, pitch-circle probes bracket the π·m/2 thickness, the rack pitch is
π·m and its tooth height 2.25 m, and the rack volume equals the exact
trapezoid sum. Placed instances keep their volume. cadexd publication of
canonical and placed gear and rack outputs was tested the same way; ADR-233
records the gates.

## Unqualified candidates: fifth servo, horn/pigtail STEP, planetary (2026-09-07)

### Fifth servo candidates (2026-09-07; ADR-229)

[Cadex-new] The [bounded source audit](FIFTH-SERVO-AUDIT.md) pins two Hitec
manufacturer sheets by URL, revision and SHA-256. Neither HS-311 nor HS-422
qualifies for the unchanged recipe: mounting-slot and output-datum evidence
must be resolved before delivery. No source assets or public SKU were added;
the four existing servo identities remain the catalog's coverage.

### Manufacturer horn and pigtail STEP qualification (2026-09-07; ADR-231)

[Cadex-new] [The bounded audit](HORN-PIGTAIL-AUDIT.md) pins and probes
goBILDA 1900-0025-0104 STEP, checks the named DS3218 archive lead and
rejects a generic cable listing without manufacturer CAD. Neither category
qualifies: asset permissions and exact horn compatibility remain unresolved;
DS download access fails; no small script-owned STEP import path is established.
No vendor bytes or catalog identities were added. Replan before delivery.

**Planetary experiment (ADR-235; not qualified).** The proposal reuses the
independently authored sampled involute above for a virtual external gear
cutting an internal ring's tooth spaces. It introduces no outside source
or copied geometry. `docs/probes/experiments/planetary_mesh_probe.py` tests m1,
sun18/planet18/ring54; the first planet–ring mesh overlaps by 0.000354806
mm³, above the 1e-6 bound. This is negative evidence, not a new catalog
part or a qualified internal-gear profile.
