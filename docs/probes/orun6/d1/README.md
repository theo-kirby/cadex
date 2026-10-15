# D1 proxy sweep, first pass (orun6, ADR-710)

Frozen evidence; read it, never cite it as current.

- `drives.json` — the drive library: the four CubeMars drives in
  `CadexCatalog.QDD_ACTUATORS`, copied field for field, plus two datasheet
  candidates not yet in the library (AK10-9 V3.0 KV60, AK80-64 KV80), read
  from the manufacturer's product pages on 2026-10-15.
- `configs.json` — the eight configurations screened.
- `sweep-trot.json`, `sweep-trot.md` — `training/cadex_proxy.py` on the
  1.0 m/s trot clip of the `orun6-cat` track-s3 bundle, seeds 1001–1010,
  support modes `full`, `attitude` and `swing`. Left-side drives tabulated.
- `sweep-trot.png` — each configuration's RMS torque over rated for the
  left scapula, shoulder, elbow, hip and knee, per support mode, with
  whether it holds and its worst share of time at the peak clamp.

Reading: ADR-710 in `docs/DECISIONS.md`.
