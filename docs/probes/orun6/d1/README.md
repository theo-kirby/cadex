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

## Pass 2 (ADR-711): the support confound, and the clip followed exactly

- `sweep-trot-free.{json,md}`: `configs.json` on the same trot clip, with
  supports `attitude`, `height` and `posture`. Each row carries the
  support's forward push, the body's reached speed, and per joint
  `track_rms_deg`.
- `configs-2.json`: `configs.json` plus four hind candidates (AK10-9 at
  the hip, and at the hip and knee, with and without the wrist inboard;
  AK80-64 at scapula, shoulder and hip).
- `inverse-<clip>.{json,md}`: `--support inverse` over `configs-2.json`
  on these clips:
  - `trot-1.0`: the bundle's own clip, 50 Hz;
  - `trot-1.0-250hz`;
  - `trot-1.7`: stride 0.59 m;
  - `rotary-gallop-2.5`: stride 0.62 m;
  - `half-bound-2.5`: stride 0.55 m.

  Each generated clip uses `CadexGait.generate(model, {LF: c_paw_fl, RF:
  c_paw_fr, LH: c_paw_hl, RH: c_paw_hr}, gait, speed,
  stride_length_m=..., spine_joint="j_spine", sample_hz=250,
  home_qpos=<keyframe "solved">)` on the bundle's model. Each stride is
  the longest the legs reach at that sample rate. The 50 Hz trot
  regenerates the bundle's clip byte for byte.
- `inverse.png`:
  - top: one configuration across the held replays and the exact clip;
  - bottom: the worst drive per clip and configuration, with the share of
    base wrench no foot can supply.
