"""ADR-826: the RobStride RS04 catalog row, read through lib.qdd and lib.housing.

usage: pixi run python docs/probes/lurcher/rs04_catalog.py

Stages the library on the production part API (geometry stays deferred, so
no kernel is needed) and checks, one line each:

- the row carries RobStride's published figures (48 V, 9:1, 120 / 40 N*m,
  200 / 50 rpm, 1420 g, 120 x 56 mm, 10-M4 on 106 mm x 6, 9-M5 on 35.86 x 9);
- Kt times the rated and peak currents gives back the rated torque and at
  least the peak (the table's 2.1 N*m/Arms is output-side);
- lib.qdd places it: 10 front, 0 rear and 9 output holes, every hole inside
  the case, the effective density reproduces 1420 g over the solid's volume,
  the reflected inertia and the speed-line damping follow from the row;
- mounting(face='front') gives 10 M4 screws that engage, face='rear' and
  lib.housing(seat='rear') are refused, lib.housing(seat='front') builds;
- every other catalogued QDD still places and its rear circle is unchanged.

Exits non-zero on the first failure.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src" / "Mod" / "cadex"))

import CadexCatalog as catalog  # noqa: E402
import cadex_library_api as L  # noqa: E402
from cadex_part_api import PartDomainAPI  # noqa: E402


def check(ok: bool, what: str) -> None:
    print(("ok   " if ok else "FAIL ") + what, flush=True)
    if not ok:
        raise SystemExit(1)


def part_api():
    import cadex_part_api as A
    names = A.PartDomainAPI.exported_names.fget(None)
    return A.PartDomainAPI(names, A._PACK_OUTPUT_TYPES)


def main() -> int:
    spec = catalog.qdd_spec("robstride-rs04")
    want = {"rated_voltage_v": 48.0, "gear_ratio": 9.0, "peak_torque_nm": 120.0,
            "rated_torque_nm": 40.0, "no_load_speed_rpm": 200.0, "rated_speed_rpm": 50.0,
            "mass_g": 1420.0, "case_dia_mm": 120.0, "overall_length_mm": 56.0,
            "mount_count": 10, "mount_pcd_mm": 106.0, "mount_thread": "M4",
            "front_mount_depth_mm": 6.0, "output_count": 9, "output_pcd_mm": 35.86,
            "output_thread": "M5", "output_depth_mm": 9.0, "rear_mount_count": 0}
    bad = {k: spec[k] for k, v in want.items() if spec[k] != v}
    check(not bad, f"published figures carried ({bad or 'all match'})")
    kt_out = spec["kt_nm_per_a"] * spec["gear_ratio"]
    check(abs(kt_out * spec["rated_current_a"] - 40.0) < 0.5,
          f"Kt x rated current = {kt_out * spec['rated_current_a']:.1f} N*m (rated 40)")
    check(kt_out * spec["peak_current_a"] >= 120.0,
          f"Kt x peak current = {kt_out * spec['peak_current_a']:.1f} N*m (peak 120)")

    lib = L.create_library_api(part_api())
    q = lib.qdd("robstride-rs04")
    s = q.spec
    check(len(s["mount_holes"]) == 10 and len(s["rear_mount_holes"]) == 0
          and len(s["output_holes"]) == 9, "10 front, 0 rear, 9 output holes")
    r_m = max(math.hypot(x, y) for x, y in s["mount_holes"]) + 2.0
    r_o = max(math.hypot(x, y) for x, y in s["output_holes"]) + 2.5
    check(r_m < 60.0 and r_o < 60.0, f"holes inside the case (outer edges {r_m:.1f}, {r_o:.1f} < 60 mm)")
    vol = (math.pi * 60.0 ** 2 * 56.0 - 10 * math.pi * 4.0 * 6.0
           - 9 * math.pi * 2.5 ** 2 * 9.0)
    mass = s["effective_density_kg_m3"] * vol * 1e-9 * 1000.0
    check(abs(mass - 1420.0) < 1e-6, f"effective density {s['effective_density_kg_m3']:.0f} kg/m3 gives {mass:.1f} g")
    check(abs(s["reflected_inertia_kgmm2"] - 2045.0 * 0.1 * 81.0) < 1e-6,
          f"reflected inertia {s['reflected_inertia_kgmm2']:.0f} kg*mm2")
    check(abs(s["speed_line_damping_nmms_per_deg"] - 120000.0 / 1200.0) < 1e-9,
          f"speed-line damping {s['speed_line_damping_nmms_per_deg']:.1f} N*mm*s/deg (120 N*m over 1200 deg/s)")

    hold = q.mounting(wall=4.0)
    check(len(hold.stator.screws) == 10 and hold.stator.screw.lower() == "m4",
          f"front mounting: {len(hold.stator.screws)} x {hold.stator.screw} {hold.stator.length_mm:g} mm")
    check(len(hold.output.screws) == 9, f"output mounting: {len(hold.output.screws)} x {hold.output.screw}")
    try:
        q.mounting(face="rear")
        check(False, "rear mounting refused")
    except L.LibraryError as exc:
        check("no published" in str(exc), f"rear mounting refused: {exc}")
    import CadexPanels as P
    try:
        P.build_housing(lib, q, seat="rear")
        check(False, "rear housing refused")
    except P.PanelError as exc:
        check("seat='front'" in str(exc), f"rear housing refused: {exc}")
    housing = P.build_housing(lib, q, seat="front")
    check(housing is not None, "front housing builds")

    for sku in sorted(catalog.QDD_ACTUATORS):
        if sku == "robstride-rs04":
            continue
        other = lib.qdd(sku).spec
        n = catalog.QDD_ACTUATORS[sku].get("rear_mount_count", catalog.QDD_ACTUATORS[sku]["mount_count"])
        check(len(other["rear_mount_holes"]) == n and n > 0, f"{sku}: {n} rear holes as before")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
