"""ADR-867: the RobStride RS05 and RS00 catalog rows, read through lib.qdd and lib.housing.

usage: pixi run python docs/probes/robstride/small_catalog.py

Stages the library on the production part API (geometry stays deferred, so
no kernel is needed) and checks, per drive, one line each:

- the row carries RobStride's published figures (manual and STEP model);
- Kt times the rated and peak currents gives back the rated torque and at
  least the peak (the manuals' Kt is output-side);
- lib.qdd places it: its front, rear and output holes, every hole inside the
  case, the effective density reproduces the mass over the solid's volume,
  the reflected inertia and the speed-line damping follow from the row;
- front and rear mountings give screws of the row's thread, and a front and
  a rear housing build;
- every other catalogued QDD still places with its rear circle unchanged.

Exits non-zero on the first failure.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src" / "Mod" / "cadex"))

import CadexCatalog as catalog  # noqa: E402
import cadex_library_api as L  # noqa: E402

PUBLISHED = {
    "robstride-rs05": {"rated_voltage_v": 48.0, "gear_ratio": 7.75, "peak_torque_nm": 5.5,
                       "rated_torque_nm": 1.6, "no_load_speed_rpm": 480.0, "rated_speed_rpm": 100.0,
                       "mass_g": 191.0, "case_dia_mm": 46.0, "overall_length_mm": 44.0,
                       "mount_count": 8, "mount_pcd_mm": 41.5, "mount_thread": "M3",
                       "front_mount_depth_mm": 7.0, "rear_mount_count": 4, "rear_mount_pcd_mm": 38.5,
                       "rear_mount_depth_mm": 10.0, "output_count": 6, "output_pcd_mm": 24.0,
                       "output_thread": "M4", "output_depth_mm": 3.5},
    "robstride-rs00": {"rated_voltage_v": 48.0, "gear_ratio": 10.0, "peak_torque_nm": 14.0,
                       "rated_torque_nm": 5.0, "no_load_speed_rpm": 315.0, "rated_speed_rpm": 100.0,
                       "mass_g": 310.0, "case_dia_mm": 57.0, "overall_length_mm": 51.4,
                       "mount_count": 6, "mount_pcd_mm": 50.0, "mount_thread": "M3",
                       "rear_mount_count": 4, "rear_mount_pcd_mm": 38.0, "rear_mount_depth_mm": 4.0,
                       "output_count": 6, "output_pcd_mm": 27.0, "output_thread": "M3",
                       "output_depth_mm": 5.0},
}
MAJOR = {"M3": 3.0, "M4": 4.0}


def check(ok: bool, what: str) -> None:
    print(("ok   " if ok else "FAIL ") + what, flush=True)
    if not ok:
        raise SystemExit(1)


def part_api():
    import cadex_part_api as A
    names = A.PartDomainAPI.exported_names.fget(None)
    return A.PartDomainAPI(names, A._PACK_OUTPUT_TYPES)


def solid_volume(row) -> float:
    vol = sum(math.pi * (d / 2.0) ** 2 * (z1 - z0) for d, z0, z1 in row["segments"])
    for count, thread, depth in ((row["mount_count"], row["mount_thread"], row["front_mount_depth_mm"]),
                                 (row["rear_mount_count"], row["mount_thread"], row["rear_mount_depth_mm"]),
                                 (row["output_count"], row["output_thread"], row["output_depth_mm"])):
        vol -= count * math.pi * (MAJOR[thread] / 2.0) ** 2 * depth
    return vol


def main() -> int:
    lib = L.create_library_api(part_api())
    import CadexPanels as P
    for sku, want in PUBLISHED.items():
        row = catalog.qdd_spec(sku)
        bad = {k: row[k] for k, v in want.items() if row[k] != v}
        check(not bad, f"{sku}: published figures carried ({bad or 'all match'})")
        kt_out = row["kt_nm_per_a"] * row["gear_ratio"]
        rated = kt_out * row["rated_current_a"]
        check(abs(rated - row["rated_torque_nm"]) < 0.05 * row["rated_torque_nm"],
              f"{sku}: Kt x rated current = {rated:.2f} N*m (rated {row['rated_torque_nm']:g})")
        check(kt_out * row["peak_current_a"] >= row["peak_torque_nm"],
              f"{sku}: Kt x peak current = {kt_out * row['peak_current_a']:.1f} N*m (peak {row['peak_torque_nm']:g})")

        q = lib.qdd(sku)
        s = q.spec
        n = (len(s["mount_holes"]), len(s["rear_mount_holes"]), len(s["output_holes"]))
        check(n == (row["mount_count"], row["rear_mount_count"], row["output_count"]),
              f"{sku}: {n[0]} front, {n[1]} rear, {n[2]} output holes")
        case_r = row["case_dia_mm"] / 2.0
        edge = max(math.hypot(x, y) for x, y in s["mount_holes"] + s["rear_mount_holes"]) + MAJOR[row["mount_thread"]] / 2.0
        check(edge < case_r, f"{sku}: stator holes inside the case (outer edge {edge:.2f} < {case_r:g} mm)")
        hub_r = min(d for d, _, _ in row["segments"]) / 2.0
        edge = max(math.hypot(x, y) for x, y in s["output_holes"]) + MAJOR[row["output_thread"]] / 2.0
        check(edge < hub_r, f"{sku}: output holes inside the flange (outer edge {edge:.2f} < {hub_r:g} mm)")
        mass = s["effective_density_kg_m3"] * solid_volume(row) * 1e-9 * 1000.0
        check(abs(mass - row["mass_g"]) < 1e-6,
              f"{sku}: effective density {s['effective_density_kg_m3']:.0f} kg/m3 gives {mass:.1f} g")
        check(abs(s["reflected_inertia_kgmm2"] - row["rotor_inertia_gcm2"] * 0.1 * row["gear_ratio"] ** 2) < 1e-6,
              f"{sku}: reflected inertia {s['reflected_inertia_kgmm2']:.1f} kg*mm2")
        omega = row["no_load_speed_rpm"] * 6.0
        check(abs(s["speed_line_damping_nmms_per_deg"] - row["peak_torque_nm"] * 1000.0 / omega) < 1e-9,
              f"{sku}: speed-line damping {s['speed_line_damping_nmms_per_deg']:.2f} N*mm*s/deg")

        for face, count in (("front", row["mount_count"]), ("rear", row["rear_mount_count"])):
            hold = q.mounting(face=face, wall=3.0)
            check(len(hold.stator.screws) == count and hold.stator.screw.lower() == row["mount_thread"].lower(),
                  f"{sku}: {face} mounting {len(hold.stator.screws)} x {hold.stator.screw} {hold.stator.length_mm:g} mm")
        check(len(hold.output.screws) == row["output_count"],
              f"{sku}: output mounting {len(hold.output.screws)} x {hold.output.screw}")
        for seat in ("front", "rear"):
            check(P.build_housing(lib, q, seat=seat) is not None, f"{sku}: {seat} housing builds")

    for sku in sorted(catalog.QDD_ACTUATORS):
        if sku in PUBLISHED:
            continue
        other = lib.qdd(sku).spec
        n = catalog.QDD_ACTUATORS[sku].get("rear_mount_count", catalog.QDD_ACTUATORS[sku]["mount_count"])
        check(len(other["rear_mount_holes"]) == n, f"{sku}: {n} rear holes as before")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
