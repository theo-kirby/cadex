# Fifth servo source qualification

Verified against source: 2026-09-07

[Cadex-new] ADR-229. **Neither of the two candidates qualifies for delivery
through the unchanged ServoPart recipe.** No SKU or runtime change is made.

## Sources and bounded result

Manufacturer PDFs retrieved 2026-09-07, rendered with PyMuPDF and visually
inspected (Poppler was unavailable). Document identity is Ver2.2, filename
102623; hashes identify downloaded bytes, not a manufacturer certification.
No manufacturer files or code are redistributed.

| Candidate and manufacturer source | SHA-256 |
|---|---|
| [Hitec HS-311, Ver2.2](https://www.hiteccs.com/public/uploads/data_sheet/HCS_HS-311_Specsheetv2.2_102-1729889658.pdf) | `0e9558571142688dc64fe6025145f0996dec19fae8dba00cb41900cba9cea73b` |
| [Hitec HS-422, Ver2.2](https://www.hiteccs.com/public/uploads/data_sheet/HCS_HS-422_Specsheetv2.2_102-1729890502.pdf) | `b6b8b4779bf2149d564a3e375320a14738c929b9bcaa8b1d7e3902dcd4807576` |

HS-311: positional analog, 24T/6 mm spline; stall 3.0 kgf cm at 4.8 V,
3.7 at 6 V; travel ±60 degrees. Drawing: body 40 × 20, tab span 52.8,
hole diameter 4.5, transverse pitch 10.2, longitudinal axis-to-hole distances
33.9/13.9 (pitch 47.8), flange underside 26.5 above bottom. Open tab slots
have no width callout. Spline projection is 3.2, but the stepped shoulder
beneath it is not independently dimensioned for the recipe's case-top datum.

HS-422: positional analog, 24T/6 mm spline; stall 3.1 kgf cm at 4.8 V,
3.9 at 6 V; travel ±60 degrees. Drawing: body length 40.6, width 19.8,
tab span 53.4, hole diameter 4.5, axis-to-hole distances 34.2/14.2
(pitch 48.4). Open slot widths are unspecified. Cross pitch reads
9.0 mm beside 0.394 inches (10.0076 mm); table height 36.5 differs from
drawing 36.6. Do not choose a conflicting value or infer shoulder dimensions.

## Acceptance boundary and next step

`cadex_library_api.LibraryAPI.servo` makes one rectangular case, a centred
rectangular flange, round through-holes and a cylinder from the case top.
For either candidate's stated pitch/span, a 4.5 mm drill leaves 0.25 mm of
material between its outer rim and the flange end. This is a recipe
calculation, not a kernel measurement: it cannot reproduce the pictured open
slot. Slot access and spline seating are interfaces, not cosmetic details.
The current non-micro horn refusal also incorrectly assumes every such servo
is 25T; neither candidate may inherit a claimed 25T horn.

Acceptable cosmetic omissions are labels, seams, screw heads, internal gears
and cable detail; simplifying a mounting opening or guessing the case-to-output
stack is outside this qualification. Stall ratings must remain voltage-qualified;
no continuous rating follows from them. Keep physical-fit claims separate.

**Replan before proof or delivery.** A future bounded unit can obtain a
manufacturer mechanical drawing/STEP that resolves these datums and explicitly
decide whether a local recipe change is warranted, or qualify a different SKU.
This audit does not authorize a new abstraction, a third candidate, a horn
implementation or a fallback to guessed interfaces.

If a candidate later qualifies, independent OCCT checks must inspect actual
worker BREP surfaces and material/void points at mounting centres, slot mouths,
flange faces and output axis in canonical and rotated/translated frames.
Use source datums as expectations, not copied recipe arithmetic. A closed
mouth must fail for an open-slot source. Only after proof should a public row
land, with voltage/refusal tests and publication via write_script. The existing
baseline below is executable now; it proves no candidate geometry.

## Existing coverage and verification

Four distinct servo rows remain: TowerPro SG90, MG90S, MG996R and DSSERVO
DS3218 standard (not PRO). No aliases add breadth. The other powered hardware
rows are Pololu 2367, HOBBYWING 30415200 and Actuonix L12-50-210-12-S;
SKF GE 6 C is passive. Thus there are four of the required five servo identities
and seven powered identities even under an inclusive actuator count: at least
one servo and three powered identities remain, with their separate evidence
obligations. This count does not close L3, bearings/fastener evidence, or the
full robot-prompt breadth criterion.

At source HEAD `49a28a254ed4223d823dc8bf448dcd90730fe151`:

```sh
CADEX_ENGINE_ROOT="$PWD/build/engine/cadex-engine-0.0.0-macos-arm64" \
  pixi run python -m pytest -q \
  src/Mod/cadex/cadex_tests/test_cadexd_lifecycle.py \
  src/Mod/cadex/cadex_tests/test_library.py
```

**91 passed in 15.84 s**, no failures/skips. This includes existing real-worker
library publication. Source/staged SHA-256 pairs match for `CadexCatalog.py`
(`0926c5e293dce0bcae7d31fdf414bbb41aa2164d06802cb7c81963fe76eb674f`)
and `cadex_library_api.py`
(`2374b46748601a9fb18db22d99e8eb1f0a1d5c634c765a5b1a607418b299bf8d`).
No rebuild/stage was needed for this documentation-only unit. This is an
existing local development payload with external library references, not a
portable release certification or an assertion of whole-payload source equality.
No GUI, remote training, general headless review or rollout-video closure.
