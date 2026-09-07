# Manufacturer STEP horn and pigtail audit

Verified against source: 2026-09-07

[Cadex-new] ADR-231; executes the bounded bet `narrow-pebble-8020`.
**Neither category qualifies for delivery.** This is source qualification,
not a new library value. Two horn candidates were inspected: goBILDA
1900-0025-0104 and the DS3218 accessory/archive lead. Two cable leads were
inspected: Pololu #780 and that same DS3218 archive. No third candidate,
servo qualification, importer, vendor geometry or runtime download was added.

## Sources and disposition

1. **goBILDA 1900-0025-0104.** The manufacturer's
   [product page](https://www.gobilda.com/1900-series-single-servo-arm-25-tooth-spline-32mm-length/)
   identifies a 25-tooth, 32 mm single arm with 8 mm hole spacing. Its
   [STEP ZIP](https://www.gobilda.com/content/step_files/1900-0025-0104.zip)
   downloaded successfully: 58,947 bytes, SHA-256
   `36435899424a48e917bee3b740446d579744917314cac2a27f07e78d1942a7d9`.
   It contains only `1900-0025-0104.STEP`: 328,304 bytes, SHA-256
   `c2ae4475cd8f5b333f9dfceee811230a64e9390bb3d73d22ca9cb4acfd218e9f`.
   Header: AP203, SolidWorks 2016, timestamp `2017-04-13T14:12:00`;
   no separately declared product revision. The ZIP has no licence file.
   Neither the product page nor [support page](https://www.gobilda.com/support)
   supplied asset-use or redistribution terms in this inspection. A guessed
   `/terms-and-conditions/` URL could not be opened by the web tool; that is
   not evidence of the site's full legal terms. **Permission is unresolved,
   not asserted forbidden.** A public download is insufficient for this
   delivery gate. Category links to servos do not establish an exact mating
   SKU or its spline tolerances. Do not infer DS3218/MG996R compatibility.
2. **DS3218 archive, horn and cable lead.** The manufacturer's
   [download page](https://www.dsservo.com/en/show_down.asp?id=25) labels
   `DS3218-3d.rar` for DS3218, DS3115 and DS3225, uploaded 2018-08-05.
   Its actual [download link](https://www.dsservo.com/en/down.asp?id=25)
   returned HTTP 403 to Python urllib; the web tool returned an empty page.
   The page itself also returned 403 to urllib but was readable with the web
   tool. No archive bytes were acquired. Hash, revision, units, frame,
   contents, horn interface, connector identity, pitch, pinout and cable
   representation are **unverified**. No redistribution grant was found on
   the viewed page. Do not claim this archive contains a horn or pigtail.
3. **Pololu #780 cable lead.** The seller's
   [product page](https://www.pololu.com/product/780) and
   [resources URL](https://www.pololu.com/product/780/resources) identify a
   generic-brand 300 mm female/female JR-style extension, 22 AWG,
   2.54 mm contact spacing. The page gives colour conventions (dark ground,
   red supply, remaining conductor signal), not a dimensioned keyed-face
   pin-number drawing. It shows zero resources and no STEP link. It does
   not identify the manufacturer. It therefore fails manufacturer provenance
   and STEP availability before geometry or rights qualification. No STEP
   hash, revision, frame, connector internals or cable-shape claim is possible.
   A drawing inferred from the photographs would not satisfy this criterion.

## Real-kernel evidence

Only the downloaded goBILDA STEP was probed, using the existing installed
engine: `pixi run FreeCADCmd /tmp/cadex-58-audit/probe.py`, exit 0, explicit
`AUDIT58_COMPLETE` marker. No build, GUI, staged update or product reopen was
performed. The script called `Part.read`, `isValid`, `Solids`, `Faces`,
`Volume`, `BoundBox`, and enumerated `Part.Cylinder` surfaces. Measurements:

| Observation | Result |
| --- | --- |
| Topology | valid; one solid; 131 faces |
| Volume | 1157.652238130733 mm³ |
| Native bounds | X −36..5, Y −5..5, Z 0..7.75 mm |
| Frame | hub axis through X=Y=0 along Z; arm extends toward −X |
| Four hole axes | X −8, −16, −24, −32; Y=0; parallel to Z |
| Hole radii | 2 mm (eight half-cylinder faces) |
| Independent published check | successive centres 8 mm apart; last centre 32 mm from hub axis |
| Spline-related surfaces | 25 cylindrical patches at radius 2.65 mm and 25 at 3.05 mm |
| Declared units | STEP entity #2282: millimetre length unit |

This establishes hole spacing independently from topology rather than mesh
nonemptiness. The spline surface counts support a repeated 25-fold model;
they do not establish manufacturing tolerances, spline standard or fit to a
specific servo. The central 1.5 mm-radius surfaces and the two spline radii
were observed, not independently qualified against an interface drawing.
No fit, interference, load capacity or printable-horn claim is made.

To reproduce, download and hash-check the ZIP and STEP above outside the
repository, then run this body with FreeCADCmd (set `step_path` to that file):

```python
import Part
shape = Part.read(step_path)
print(shape.isValid(), len(shape.Solids), len(shape.Faces), shape.Volume)
print(shape.BoundBox)
for face in shape.Faces:
    surface = face.Surface
    if isinstance(surface, Part.Cylinder):
        print(surface.Radius, surface.Center, surface.Axis)
print('AUDIT58_COMPLETE')
```

No acquired third-party bytes are committed. Hashes identify inspected bytes;
they are not a promise that future downloads remain available.

## Existing import path and next decision

Source inspection finds `mesh.import_file` accepts STL/OBJ/PLY only
(`cadex_mesh_api.py`, `CadexScriptedRuntime._ASSET_SUFFIXES`), while
`part.import_part` accepts `.cxpart` snapshots of accepted project parts
(`cadex_part_api.py`, `CadexLinkedPart.py`). The presence of
`file.import_model` in a tool-name set is not a script-owned STEP reader;
ROADMAP Phase 11 still leaves STEP import/export open. Thus the bet's small
existing STEP delivery path is **not established**. Raw `Part.read` in this
probe is an engine inspection, not an authorized project authoring route.
Converting to a mesh would lose analytic interfaces and still require
asset rights. Forging a linked-project snapshot is not the prescribed path.

Stop the conditional delivery bet and replan. A later horn delivery needs
explicit redistribution evidence, exact mating-interface evidence and a
separately authorized script-owned path; the cable needs an identifiable
manufacturer STEP with connector and cable contents first. No contact was
sent. Neither category nor any servo/actuator count advances.

Documentation/provenance validation: `pixi run python -m pytest
src/Mod/cadex/cadex_tests/test_licensing_compliance.py -q` passed (see work
record for count). `git diff --check` and hypergraph export/check run at close.
No product source, payload or shell change: full engine/CLI and packaged
lifecycle suites were not run; no runtime regression coverage is claimed.
