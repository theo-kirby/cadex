# F2: declared static fit

Verified against source: 2026-09-14. Provenance: [Cadex-new]. ADR-347.

The assembly definition accepts `contacts=[(a, b)]` and
`clearances=[(a, c, minimum_mm)]`. Published exact-solid measurements report
all failed checks without refusing acceptance. World geometry is a separate
finding. XSCRIPT documents tolerances, default gaps and world detection.

Known-answer engine fixture (`cadex_tests/test_fit_intent.py`):

| Components | Measurement | Finding |
|---|---|---|
| cheek / servo_tab | 248.2 mm³ common volume | intersection, despite contact intent |
| horn / link | 0.2 mm gap | missed contact |
| base | collision plane, 500 × 500 mm, 50 mm grid | world geometry |
| base / bearing | zero gap and volume | intended contact passes |
| near / other | 0.05 mm gap | below default 0.1 mm |
| wide / mate | 0.4 mm gap | below declared 0.5 mm |
| floor_face | rotated planar CAD face, no solids | world geometry |

These are analytic fixtures reproducing Heron's defect classes and measured
sizes, not a new run of Heron's retained design. Heron's first accepted source
was read only to confirm that its floor defect was a collision plane attached
to its base. No product-agent turn or design edit occurred.

The CLI transaction accepts a failing design, returns its declared intent and
world finding, and restores with unchanged accepted revision, digest and
attempt. The generated clearance document names each declared threshold.
The same transaction passes against the staged payload.

## Verification

- One `pixi run build-engine`: exit 0. Install and staging: exit 0.
- `pixi run test-engine`: **2117 passed, 53 skipped**, 332.10 s, exit 0.
- Focused engine/API surface run: **15 passed**, including the API-description
  test added after full-suite collection. The final rotated-plane fixture
  subsequently passed in its two-test module, 0.25 s.
- `pixi run python -m pytest cli/tests`: **636 passed, 1 skipped, 1 failed**,
  542.34 s, exit 1. The failure is the unchanged review-lifecycle test's
  telemetry assertion at line 266: history points `15`, then iteration `18`
  (expected points `19`). It reads the two values in separate browser calls.
  This suggests a timing race; it does not prove a pre-existing failure.
  The previous F1 full-CLI baseline was green (record `steady-quartz-9854`).
- Isolated retry of that test: **1 passed**, 7.98 s. No dashboard code or test
  was edited. F9 remains open; this receipt does not call the full suite green.
- Final focused CLI clearance suite: **25 passed**, 2.07 s. This includes the
  final report-detail change made after the full suite collected its tests.
- Packaged `test_cadexd_lifecycle.py`: **16 passed**, 18.22 s.
- Packaged new fit-intent transaction: **1 passed**, 0.65 s.

No dependency, protocol op, shell change, policy training or design acceptance
outside test fixtures. Static fit is implemented; swept fit remains F3.
A solid bench must be marked `world=True`: shape alone cannot identify purpose.

## Retained logs

Paths are relative to the operator's cadex-projects directory. Logs are local,
not committed. Each file is under `ot7-fit-intent/evidence/`.

| File | SHA-256 |
|---|---|
| ot7-f2-build.log | `73aa544457a93178d7fe98e540a2fb70a405e6be0c0850a8342cf034379c12eb` |
| ot7-f2-cli.log | `015010c2f309443d63d0416a222bb10ece724c5d1d31401793f94d45dbb8d1e3` |
| ot7-f2-engine.log | `cc9cdfae6472522f838703e6dfe6638ea0ab8d41c4fc954ecac85efd50dca753` |
| ot7-f2-focused-cli.log | `77c325d8f413ea1337a6f3e7f01b28b5227b91a84133b24db93184ca7794632f` |
| ot7-f2-gate.log | `f8f0583019270a5a2160d613654a431aac82fbb463cfe9d252961bbcca5782b1` |
| ot7-f2-install.log | `5051bd995c05d88bb0736b822da488708ea96e89d9399b6f1fbf30bc3676b088` |
| ot7-f2-lifecycle-retry.log | `e2cc916c5679ef868a3ee62da1c10c69c5de4e19d8d1a07b17c2ad5b517edabd` |
| ot7-f2-packaged-fit.log | `82b3969ab6a7010a8f532f30c1064a0778c5b38dc55a702fb450351686f027aa` |
| ot7-f2-stage.log | `e6af0d4a960027d867cb0e194a8a09df882aefc2f7dbf9884d1a805a1a059d1c` |
