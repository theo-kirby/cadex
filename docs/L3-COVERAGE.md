# L3 coverage and evidence audit `[Cadex-new]`

Verified against source: 2026-09-07

The original remaining-scope audit requested by `true-fox-1464`, against
ROADMAP Phase 17 and source revision `333c805788e6`, audits recorded
manufacturer evidence in PROVENANCE §§8b–8f, the catalog, LibraryAPI and
`cadex_tests/test_library.py`; it does not refresh outside sources or qualify
another part. The dated additional audit below inspects new sources.
**Full L3 remains open.** Four families each expose one SKU;
solenoids expose none. A catalog value is not a powered assembly.

## Coverage matrix

| ROADMAP promise | Delivered value and recorded ratings | Geometry and coupling limit | Evidence and exact residual gap |
|---|---|---|---|
| N20 gearmotor | `lib.gearmotor("pololu-2367")`: MP 6 V, nominal 100:1; 220 RPM ±20%, 70 mA ±50% no-load; extrapolated 0.94 kg·cm stall torque and 0.67 A (PROVENANCE §8b, ADR-205). | 12×10 mm rear envelope, 3 mm D shaft, 2.5 mm flat-to-opposite, M1.6 centres ±4.5 mm. Flat transition and 1 mm blind-bore depth are assumptions; no screw-engagement permission or physical inertia. | Canonical/placed recipes publish as solids in the real-kernel integration. Dedicated actual-worker surface measurements and 160 canonical/placed material probes verify the D shaft and both bores (2026-09-07); the assumed depth/transition remain unqualified for hardware fit. Narrow N20 delivery is supported; continuous torque, thermal behaviour and actuator coupling are absent. |
| Common BLDC sizes with kV/torque data | `lib.bldc("hobbywing-30415200")`: Skywalker 2820 SL 550KV; 550 rpm/V, 1.38 A no-load at 22.2 V, 6S, 144.5 g (PROVENANCE §8c, ADR-206). 40.9 A / 910.2 W are notes qualified to 46 s, not control limits. | Ø35.1×40 mm case, rear M3 pattern 19/25 mm. Ø10.5 mm collar reservation spans all 18 mm shaft projection; actual Ø5 mm shaft is metadata only. Free shaft length, screw engagement, wiring clearance and coupling fit are unsupported. | Dedicated actual-worker bounds/material/void and placement probes plus cadexd publication. Exactly one size/winding; no torque rating or constant. Neither plural common-size coverage nor torque promise is met. No kV-to-usable-torque inference is justified by the recorded evidence. |
| Linear actuator | `lib.linear_actuator("l12-50-210-12-s", extension=...)`: 12 V, ratio 210, 50 mm stroke; 80 N maximum lifted load, 6.5 mm/s unloaded, 62 N at 3.2 mm/s peak power are distinct points; ≤20% duty, −10 to 50°C (PROVENANCE §8d, ADR-207). | Nominal centres 102+extension mm, Ø4.25 mm bores, 8/6 mm rear-lug/clevis widths. Older STEP spacing is +0.5 mm, explicitly not a tolerance. Simplified filled exterior is not a conservative installation envelope. | Actual-worker surfaces and 180 canonical/placed material probes at 0/23.5/50 mm; packaged publication at 50 and placed 23.5 mm. Narrow geometry delivered. S switches stop within 0.5 mm of ends: geometric endpoints do not prove powered reachability, feedback or closed-loop motion. |
| Solenoid | None. TAU0730TM-14/Adafruit 412 partial experiment; Ledex B7 source follow-up only (PROVENANCE §8e, ADR-208/209). | Current 412 mounting callouts incomplete; older TAU slots conflict. B7 planar M3 centres are known, engagement depth and maximum mechanical travel are not. A force-plot axis is not a travel stop. | 412 standalone approximation: 72 probes at gaps 0/2.3/4.9 mm. No public recipe, worker delivery or packaged solenoid verification. Reopen only with new interface/travel evidence or an explicitly justified narrower contract; do not repeat the searches or silently weaken delivery. |
| Joints | `lib.joint("skf-ge-6-c", tilt_degrees=...)`: nominal SKF radial spherical bearing; 3.6/9 kN basic dynamic/static ratings, 4 g, qualified selection inputs (PROVENANCE §8f, ADR-210/211). | Two nominal rings, Ø6 bore / Ø14 OD, ±13° tilt conditional on ≤8 mm shaft shoulder. Coincident spherical faces omit running clearance, chamfers and liner. No press-fit or installed-motion guarantee. | Actual-worker surfaces, independent volumes, zero overlap, shaft/shoulder checks and 96 canonical/placed probes across −13/0/6.5/13°; packaged compound publication. Narrow joint delivery is verified; no solver, load-life model, friction or physical inertia follows. Do not redispatch delivery. |
| Gears and rack-and-pinion (separate slice) | `lib.spur_gear(module, teeth, face_width, bore=None)` and `lib.rack(module, teeth, face_width, height)`: ISO 53 type A profile on ISO 54 series I modules, spec carrying pitch/base/root/tip diameters, π·m pitch and π·m/2 tooth thickness (PROVENANCE §8g, ADR-233). | Sampled involute polygon (eight points per flank, radial line below the base circle), no fillets, tip relief, backlash, profile shift or helix; undercut below 17 teeth is warned, not generated. No density, strength or torque rating. | Actual-worker diameters, volumes, bore surface and pitch-circle probes for four gears and two racks; cadexd publication of canonical and placed outputs. Standalone values only: no rack-and-pinion or planetary composition, and no mesh or clearance evidence yet — those are the next two units. |

All four return ordinary `LibraryPart` values. The actuator helper is on
`ServoPart`, not these L3 values. Authoring `assembly.actuator` manually does
not make their envelopes physical rotor/stator, translating bodies, or inertias.
Catalog mass and basic load ratings do not supply those missing contracts.

## Verification ledger

Historical full engine and freshly staged lifecycle/library results are recorded
in the delivery nodes; counts describe the suites at those revisions:

| Delivery record | Full engine | Packaged lifecycle/library |
|---|---|---|
| `idle-dawn-5426` (N20) | 1980 passed, 52 skipped | 54 passed, no skips |
| `floral-stone-2866` (BLDC) | Stable rerun: 1987 passed, 52 skipped | 61 passed, no skips |
| `frosty-snow-9642` (L12) | Post-build: 2002 passed, 52 skipped | 76 passed, no skips |
| `morning-field-8202` (joint) | Final: 2016 passed, 52 skipped | 90 passed, no skips |
| gear values (ADR-233) | Pre-build: 2050 passed, 52 skipped | 107 passed, no skips |

`test_the_library_builds_on_the_real_kernel` publishes canonical and placed
outputs for all four through cadexd, requiring solids except the joint compounds.
Dedicated interface tests now exist for N20, BLDC, L12 and joint; they select
the payload worker when `CADEX_ENGINE_ROOT` is set. The N20 test measures
OCCT cylindrical and planar surfaces: shaft Ø3 mm, flat-to-opposite 2.5 mm,
flat Z=1–10 mm, and bore radii 0.8 mm at (±4.5, 0), Z=−1–0 mm. Eighty
material/void probes per instance straddle bore walls/bottoms, shaft edges,
flat transition and tip. A cyclic rotation plus translation is verified
independently. These prove the declared simplified geometry, not installed fit.

Reproduction of this audit's existing-payload baseline:

```bash
CADEX_ENGINE_ROOT=build/engine/cadex-engine-0.0.0-macos-arm64 \
  pixi run python -m pytest \
  src/Mod/cadex/cadex_tests/test_cadexd_lifecycle.py \
  src/Mod/cadex/cadex_tests/test_library.py
```

Audit baseline result: **90 passed, no skips, 15.85 s**, exit 0.

The original documentation-only audit required no build, staging, full engine
suite or new hardware experiment. Its payload recorded 248 external-path
relocation violations; this is historical evidence, not release-bundle
verification. Do not overlap a future suite with staging.

N20 follow-up (2026-09-07): full engine **2023 passed, 52 skipped,
254.80 s**; after completed `pixi run stage-engine`, the lifecycle/library
command above reports **91 passed, no skips, 19.44 s**, including all four
actual-worker interface tests. Catalog, library API and part-worker bytes
match source in the payload. No runtime edit or build was needed. The new
2.4 GB local staging reports **144 external-path relocation violations**;
staging exits 0 in stage-only mode, but this is not a shippable bundle.

## Bounded follow-ups for the planner

1. **Inherited reduction preceded the N20 follow-up.** Phase 8 and the
   Help/Start removals have since landed; current dispatch order lives in
   PLAN.md. No source deletion is authorized by this document.
2. **N20 evidence-only improvement landed (2026-09-07):** actual-worker D-shaft
   and bore measurements/probes include placement and retain the §8b assumed
   bore depth and transition limits. No source refresh or API change. This
   improves verification, not the remaining common-BLDC/solenoid coverage.
3. **Smallest missing BLDC delivery candidate:** qualify one additional named
   size/winding with manufacturer mounting geometry, kV and a torque operating
   point with voltage/current/duration/cooling qualifications. Select the SKU
   only after a bounded source audit; none is prequalified here. Separate
   geometry proof from delivery, then run the full engine suite, one build,
   completed staging and packaged tests. A second envelope without torque data
   can be useful but cannot close the existing promise. ROADMAP does not name
   a common-size set or minimum count; define that acceptance set explicitly
   before claiming plural coverage, rather than treating two as sufficient.
4. **Coupling follow-up, conditional on new evidence:** for the delivered BLDC,
   obtain collar axial length/free shaft and engagement limits before replacing
   the conservative reservation. Prove mating surfaces and placed geometry;
   do not infer torque, inertia or thermal duty from improved fit geometry.
5. **Solenoid restart stays deferred** under ADR-209. Complete a named revision's
   mounting and mechanical-travel evidence before an endpoint/placement proof
   and public implementation, or record a separate decision justifying a
   narrower contract. Neither missing dimension is supplied by this audit.

Powered assemblies, physical inertia, installed fit, further N20/L12/joint
variants and compound mechanisms are distinct future units with their own
source and test prerequisites. They are not hidden completions of this audit.

## Additional BLDC source audit — RI50 KV100 (ADR-223)

**2026-09-07: qualification blocked; no geometry experiment or delivery.**
This section refreshes outside evidence for one candidate only; the coverage
matrix above still describes the delivered catalog.

### Common-size acceptance set

Adopt **robot-prototype BLDC set A** as an explicit engineering sampling
contract, not a claim about market share or a universal motor-size standard:

| Required member | Robot design reason | Current evidence |
|---|---|---|
| 28xx-class shafted outrunner | Compact belt/reduction input for a small robot | Existing Skywalker 2820 SL 550KV envelope; torque qualification still missing |
| 50-class hollow frameless motor | Small integrated joint with a central cable passage | RI50 KV100 without Hall sensors audited below; blocked |
| 80-class hollow frameless motor | Larger proximal joint packaging for the same robot | No SKU/winding qualified; separate future audit |

These are nominal class names, not interchangeable mounting standards. Require
one named winding in **each** row, manufacturer interface dimensions, kV and
at least one torque operating point tied to voltage, current definition,
speed, duration/duty, cooling and temperature conditions. Each then needs
independent canonical/placed worker interface proof and packaged publication.
Three envelopes alone do not pass; the existing winding counts only after its
missing rating evidence lands. Powered mechanisms and the rest of L3 remain
separate. This reversible acceptance decision serves mission 4 without
claiming that two catalog values finish plural coverage.

### Inspected manufacturer evidence

Sources retrieved 2026-09-07; PDFs visually inspected after rendering with
PyMuPDF in an isolated `uv run --with pymupdf` environment (system Poppler
was unavailable). No dependency or binary source is added to the repository.

- [RI50 product page](https://www.cubemars.com/product/ri50-kv100-frameless-inrunner-torque-motor.html):
  selects KV100 and with/without-Hall variants. Lists 100 rpm/V, 0.58 N·m
  rated torque at 4.8 ADC, 24/36/48 V and respective 1090/1860/2600 rpm;
  1.67 N·m peak at 14.8 ADC. FOC, ambient −20 to 50°C. It calls the rated
  torque continuous but gives no cooling arrangement, winding temperature,
  test duration or peak duty. ADC is retained as printed, not converted to
  phase RMS current. No torque is inferred from kV.
- [One-page parameter sheet, printed page 22](https://img.cubemars.com/products/cubemars-product-parameter/RI50-KV100.pdf):
  corroborates the rating table; its drawing includes Hall wiring, 8 mm
  maximum upper overhang, Ø54±0.03 and Ø22±0.02 mm. No revision/date is
  printed. SHA256 `9533f3b3869dfd9540693d91fac55a24345205753871684ab905ff67fe290ddf`.
- [Without-Hall drawing](https://www.cubemars.com/data/cms/202602/ri50-frameless-torque-motor-without-hall-sensor-2d-drawing.pdf):
  download index dated 2026-02-06; no drawing revision printed. Ø54 with
  +0/−0.08 tolerance, Ø22±0.03 bore, 19 +0.1/0 rotor length, 16 mm stack,
  upper/lower overhangs 5/3 mm maximum, Ø25 maximum locating shoulder.
  Thus the older Hall sheet cannot supply this variant's tolerances or
  overhang. SHA256 `39c27addcdee7fe8a224bb2cb4505d6d3f15e2e041f65b1985b2453180bc4e16`.
- [Test fixture ZIP](https://www.cubemars.com/data/cms/202602/ri50-frameless-torque-motor-test-fixture.zip):
  index dated 2026-02-06. Retrieved and listed only: Hall test-base DWG/STEP,
  pivot fixture DWG/STEP, pivot BOM XLSX. Contents were not geometrically
  inspected and do not establish the rating's thermal setup in this audit.
  SHA256 `41dff1a5e8848aedf9c5aba2efc2259e4046da56557f424e01e92ff8e37ad1fb`.

The page's relative download links resolve under `/product/data/` and return
404; the `/data/` URLs above downloaded successfully with `curl -fLsS`.
An update-index date and a content hash identify inspected bytes, **not** a
manufacturer revision match between the rating and the no-Hall drawing.

### Exact blocker and next decision

The no-Hall rotor/stator interfaces are partly dimensioned, but there is no
qualified thermal operating point or documented revision link to the rating
sheet. A frameless motor has no supplied output shaft/collar or rear M3 mount;
forcing it through the present shafted BLDC recipe would invent interfaces.
Retention method, customer housing/bearings and installed fit are unqualified.

**Do not dispatch short item 2 or 3 for this candidate.** The fixture
follow-up below exhausts the authorized repeat; RI50 is parked until genuinely
new manufacturer test evidence closes both gaps. Full L3 remains open.

### Fixture follow-up — RI50 parked (2026-09-07)

Inspected the previously listed archive's BOM cells and STEP headers, not
fixture geometry or DWG annotations. The ZIP hash matches the audit above.
`RI50 Pivot BOM.xlsx` has SHA256
`ce7d7fd26fe670d9760e6c8c9fb8318696deb06b03bdfeeae8ca2228d9d317fa`.
Read all three worksheet XML files and shared strings without modifying the
workbook: Sheet1 A1:C6 lists a pivot fixture, rear cover, two MR148 bearings
and six M2.5×4 screws; Sheets2/3 have no populated cells. No thermal procedure,
winding identifier or rating/drawing revision link appears in these cells.
The archive contains only this workbook and two DWG/STEP pairs; no separate
test report or instructions.

The Hall-base STEP header exports at `2025-02-24T08:29:09`; the pivot at
`2025-04-01T06:32:11`. Their SHA256 values are respectively
`9eea2e2ad01d494428cf005f9d1ca17f2b675712b6f0cae4aafe37962ea4f722` and
`8e1d7b06a5a5718d220582c6a42e085167aabfc65f3b5fcfa2b2a6fe6a919357`.
Export timestamps establish neither test dates nor rating revision linkage.
No housing material, thermal resistance or cooling boundary is inferred from
these mechanical files. Unread DWG annotations remain unverified.

Two targeted manufacturer test/thermal searches found no new RI50 test report.
The Japanese installation-guide search result could not be opened; its video
was not inspected. The accessible English
[technical-support index](https://www.cubemars.com/article-261-Technical%2BSupport%2Band%2BDownload.html)
lists other families' manuals, software and a catalog, without a visible RI50
thermal-test procedure. The July 10, 2026
[frameless-joint article](https://store.cubemars.com/blogs/news/cubemars-frameless-motor-for-robot-joint)
discusses potting and heat transfer generally; it does not tie cooling,
temperature, duration or a drawing revision to the RI50 KV100 rating. This is
a bounded negative result about inspected evidence, not proof that no such
manufacturer document exists.

**Next decision:** park RI50; replace the conditional RI50 proof/delivery
sequence with one source audit of a shafted 28xx winding in set A's first row.
Choose using a manufacturer dynamometer report with explicit test conditions
and matching mounting drawing; qualify before any worker experiment. No
alternative is qualified here. Do not repeat the RI50 page/fixture searches,
relax the torque gate, or infer usable torque from kV. The planner owns the
plan update; this contributor changes no state or plan nodes. No runtime,
geometry, payload or relocation result changes.

### Shafted alternative — AT2814 Long Shaft KV900 (2026-09-07)

**Qualification blocked; stop the motor-search sequence.** This is the one
alternative audit authorized by `vast-oak-7458`, against unchanged set A.
Sources inspected on 2026-09-07:

- [T-MOTOR bench report and specifications](https://uav-en.tmotor.com/2019/Motors_0226/214.html):
  KV900, 3–4S, 5 mm shaft; APC 12×6 at full throttle gives 11.05 V,
  27.02 A, 7601 rpm and 0.291 N·m. The associated 68°C is motor **surface**
  temperature after three minutes at full throttle; ambient is blank (`/`).
  Current is labelled only A, with no bus/phase or RMS/peak definition.
  Cooling airflow, fixture heat sinking and repeat duty are unspecified.
  Propeller airflow is plausible, not a documented cooling condition.
  Peak 45 A and maximum 650 W are separately marked 180 s; neither supplies
  a continuous torque rating. No test revision ties these rows to V2.0.
- [Manufacturer store](https://store.tmotor.com/product/at2814-long-shaft-fixed-wing-motor.html)
  repeats the bench table and surface-temperature note; it does not resolve
  the missing conditions. No torque was inferred from kV.
- [Download index](https://uav-en.tmotor.com/download/33.html) lists the
  [AT2814 drawing](https://cn.tmotor.com/uploadfile/downloads/tmotor-at2814-motor-2d-drawings.pdf)
  dated 2026-06-25. Its single raster page, visually rendered at 2× with
  PyMuPDF because Poppler was unavailable, is labelled **AT2814 V2.0**:
  diameter 35.2, overall length 54.5 and shaft diameter 5 mm; rear four M3
  holes have opposed spacings 19 and 25 mm; front four M3 holes lie on a
  15 mm circle. A separate collar shows 5 mm bore, 11 mm outside diameter,
  5.5 mm width and M3 screw. Motor thread depths are absent. The drawing
  names no winding or test revision. SHA256:
  `4aa8603a19baf1c8f0c36b1c0a4e294b4d598329f1a2ecfa404bee45ba11e747`.
  The web PDF screenshot failed (cache miss); direct PDF download succeeded.
  The product-page JPEG download returned HTTP 403 and was not inspected.

**Decision:** these are useful measured bench data and nominal interfaces,
but they do not establish set A's qualified operating point or rating/drawing
revision linkage. No geometry proof or catalog delivery is authorized by this
result. Keep RI50 parked. The next planner pass should move to medium's
bounded residual GUI obligation before further BLDC searches. Full L3 and
all three set-A qualification obligations remain open. This audit changes
documentation only; it establishes no installed fit or powered behavior.
