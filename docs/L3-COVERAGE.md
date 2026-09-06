# L3 coverage and evidence audit `[Cadex-new]`

Verified against source: 2026-09-07

This is the remaining-scope audit requested by `true-fox-1464`, against
ROADMAP Phase 17 and source revision `333c805788e6`. It audits recorded
manufacturer evidence in PROVENANCE §§8b–8f, the catalog, LibraryAPI and
`cadex_tests/test_library.py`; it does not refresh outside sources or qualify
another part. **Full L3 remains open.** Four families each expose one SKU;
solenoids expose none. A catalog value is not a powered assembly.

## Coverage matrix

| ROADMAP promise | Delivered value and recorded ratings | Geometry and coupling limit | Evidence and exact residual gap |
|---|---|---|---|
| N20 gearmotor | `lib.gearmotor("pololu-2367")`: MP 6 V, nominal 100:1; 220 RPM ±20%, 70 mA ±50% no-load; extrapolated 0.94 kg·cm stall torque and 0.67 A (PROVENANCE §8b, ADR-205). | 12×10 mm rear envelope, 3 mm D shaft, 2.5 mm flat-to-opposite, M1.6 centres ±4.5 mm. Flat transition and 1 mm blind-bore depth are assumptions; no screw-engagement permission or physical inertia. | Canonical/placed recipes publish as solids in the real-kernel integration. Metadata/recipe tests pin dimensions, but no dedicated worker measurement of the N20 D shaft or bores exists. Narrow N20 delivery is supported; continuous torque, thermal behaviour and actuator coupling are absent. |
| Common BLDC sizes with kV/torque data | `lib.bldc("hobbywing-30415200")`: Skywalker 2820 SL 550KV; 550 rpm/V, 1.38 A no-load at 22.2 V, 6S, 144.5 g (PROVENANCE §8c, ADR-206). 40.9 A / 910.2 W are notes qualified to 46 s, not control limits. | Ø35.1×40 mm case, rear M3 pattern 19/25 mm. Ø10.5 mm collar reservation spans all 18 mm shaft projection; actual Ø5 mm shaft is metadata only. Free shaft length, screw engagement, wiring clearance and coupling fit are unsupported. | Dedicated actual-worker bounds/material/void and placement probes plus cadexd publication. Exactly one size/winding; no torque rating or constant. Neither plural common-size coverage nor torque promise is met. No kV-to-usable-torque inference is justified by the recorded evidence. |
| Linear actuator | `lib.linear_actuator("l12-50-210-12-s", extension=...)`: 12 V, ratio 210, 50 mm stroke; 80 N maximum lifted load, 6.5 mm/s unloaded, 62 N at 3.2 mm/s peak power are distinct points; ≤20% duty, −10 to 50°C (PROVENANCE §8d, ADR-207). | Nominal centres 102+extension mm, Ø4.25 mm bores, 8/6 mm rear-lug/clevis widths. Older STEP spacing is +0.5 mm, explicitly not a tolerance. Simplified filled exterior is not a conservative installation envelope. | Actual-worker surfaces and 180 canonical/placed material probes at 0/23.5/50 mm; packaged publication at 50 and placed 23.5 mm. Narrow geometry delivered. S switches stop within 0.5 mm of ends: geometric endpoints do not prove powered reachability, feedback or closed-loop motion. |
| Solenoid | None. TAU0730TM-14/Adafruit 412 partial experiment; Ledex B7 source follow-up only (PROVENANCE §8e, ADR-208/209). | Current 412 mounting callouts incomplete; older TAU slots conflict. B7 planar M3 centres are known, engagement depth and maximum mechanical travel are not. A force-plot axis is not a travel stop. | 412 standalone approximation: 72 probes at gaps 0/2.3/4.9 mm. No public recipe, worker delivery or packaged solenoid verification. Reopen only with new interface/travel evidence or an explicitly justified narrower contract; do not repeat the searches or silently weaken delivery. |
| Joints | `lib.joint("skf-ge-6-c", tilt_degrees=...)`: nominal SKF radial spherical bearing; 3.6/9 kN basic dynamic/static ratings, 4 g, qualified selection inputs (PROVENANCE §8f, ADR-210/211). | Two nominal rings, Ø6 bore / Ø14 OD, ±13° tilt conditional on ≤8 mm shaft shoulder. Coincident spherical faces omit running clearance, chamfers and liner. No press-fit or installed-motion guarantee. | Actual-worker surfaces, independent volumes, zero overlap, shaft/shoulder checks and 96 canonical/placed probes across −13/0/6.5/13°; packaged compound publication. Narrow joint delivery is verified; no solver, load-life model, friction or physical inertia follows. Do not redispatch delivery. |
| Gears and rack-and-pinion (separate slice) | No corresponding library values. | Involute profiles, mating geometry and parameter limits remain to be defined. | No compound gear mesh/clearance evidence. Keep separate from the four delivered values; the charter also requires a planetary gearbox. |

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

`test_the_library_builds_on_the_real_kernel` publishes canonical and placed
outputs for all four through cadexd, requiring solids except the joint compounds.
Dedicated interface tests exist for BLDC, L12 and joint; they select the payload
worker when `CADEX_ENGINE_ROOT` is set. This distinction matters for N20:
successful publication alone does not independently measure its mounting fit.

Reproduction of this audit's existing-payload baseline:

```bash
CADEX_ENGINE_ROOT=build/engine/cadex-engine-0.0.0-macos-arm64 \
  pixi run python -m pytest \
  src/Mod/cadex/cadex_tests/test_cadexd_lifecycle.py \
  src/Mod/cadex/cadex_tests/test_library.py
```

Audit baseline result: **90 passed, no skips, 15.85 s**, exit 0.

No build, staging, full engine suite or new hardware experiment is required
by this documentation-only audit. The local payload's recorded 248 external-path
relocation violations remain a portability limitation; passing these tests is
not release-bundle verification. Do not overlap a future suite with staging.

## Bounded follow-ups for the planner

1. **Next dispatch remains the planned Phase 8 dependency/readiness audit.**
   This L3 audit resolves the current short unit; catalog expansion should not
   displace mission 3's inherited reduction. No source deletion is authorized
   by this document.
2. **Smallest evidence-only L3 improvement:** add actual-worker N20 D-shaft and
   bore probes from the existing §8b contract, including placement. No new
   source or API is needed; retain assumed bore depth and transition limits.
   This improves verification, not the remaining common-BLDC/solenoid coverage.
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
