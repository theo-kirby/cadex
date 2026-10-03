---
node_id: 0d004486-93de-533f-b983-b9a2f9cf0410
slug: gentle-badger-9718
title: 'orun1 D3 mounting check: every build reply says what holds each purchased part (ADR-486)'
created_at: '2026-10-03T03:05:00+00:00'
parents:
- solemn-arbor-0802
summary: ''
---
## What

D3's second half, the mounting check (ADR-486, commit `0b97765c`). Every
build reply's `fit` block now carries `fit.mounting`: for every purchased
part, which printed part holds it and by what, or that nothing does.

- **Library** (`cadex_library_api.py`): two run-scoped side tables beside
  `_CATALOG_IDENTITY` — each body's mounting-hole lines in placed coordinates
  (tab servos, STS3215 case `mount_points`, boards, gearmotor and BLDC bores,
  foot pad screw, a bolt's own axis) and, for every `.bay()` cavity, the body
  it was cut for. `library_mount_facts()` reads them.
- **Project worker**: `_stamp_mounting` writes `catalog_mount_axes` on every
  catalog output (empty list where no holes, so absence marks an older
  revision) and `houses` on a part output containing a bay cavity, both
  beside the definition — no digest moves (test-pinned).
- **Inspection**: `inspect scope=clearance` publishes `components` (the
  inventory rows with `mount_axes` and `houses`), so no second engine call.
- **`CadexFitReport.mounting_summary`** (in `fit_summary`, bounded in
  `fit_view`): `held` by `screws` (a placed bolt whose axis is within 0.5 mm
  and 5° of a hole axis, touching the part and a printed part), `bay` (a
  printed part housing it at the same solved placement; a wheel's well never
  counts), `press fit` (bearing/bushing/spherical joint touching a printed
  part) or `output` (horn or wheel on a held servo/motor); otherwise
  `contact only`, `inside shell` or `held by nothing`. Verdict
  `pass`/`reported`/`unknown`/`none`/`unavailable`; refuses nothing, counts
  among no fit failure. Older revisions are `unavailable`, never judged.
- Overlay's HOLD EVERY PART rule names the block and says to place each screw
  as a `lib.bolt` component on its hole's axis. Docs: `docs/CLI.md` (new
  section), `docs/INTEGRATION.md` (clearance value), ADR-486.

## Why

The critic's message: write the missing ADR-485 record first (done, as
`solemn-arbor-0802`, committed `7e358579`), then start the mounting check —
the open half of D3 (`loyal-ocean-0768`), the highest-ranked open criterion
with work available before D4. Done as asked. One deviation in form, not
substance: the critic named "a clip" among the holds; the catalog has no clip
part, so a clipped part cannot be told from a resting one and reads
`contact only`. Recorded in ADR-486's consequences.

## Method

Read how build replies are assembled (CLI `bridge.py` and shell
`cadex_backend.py` both build `fit_summary` from the full paged clearance
value via `CadexFitReport`), how catalog identity is stamped, and how bays
are generated. Designed the check on facts the engine already has (pair
distances) plus two new stamps, so it costs no new kernel query.

Tests, `cadex_tests/test_mounting_check.py` (14): ten on published values
(screws on axis; a bolt 1 mm off the axis is not a screw; axes carried
through a solved placement; a bay only at the part's own pose; a wheel well
is not a seat and a wheel on an unheld motor is held by nothing; horn on a
held servo; press fit; inside-shell vs held-by-nothing; unmeasured → unknown;
older revision → unavailable; view bounded to 12), two on the library and
stamp (axes/bays recorded; stamp stays out of the digest), and **two
real-kernel fixtures through a live cadexd**: a passing one (BNO085 screwed
by four placed M2.5 bolts into a tapped plate, a 2S pack in a cradle cut
with its `.bay()`) → `pass`, 4 of 4 holes; a failing one (board resting on a
plate, pack floating in a hollow printed shell, a loose board) → `reported`
with exactly `contact only`, `inside shell`, `held by nothing`.
Before-the-fix: the same file at `9ea7a4a8` fails at collection
(`ImportError: cannot import name 'mounting_summary'`).

Measured on real designs: copied three sweep Loves to `orun1-mount-*`
(originals untouched) and accepted a fresh revision of each (the script
plus one trailing comment) — a plain `rebuild` of the balancer copy left
its pre-change attempt pinned (its restore drifted and rolled back, F1's
path), which is why older revisions must read `unavailable`.

## Result

What is true now: D3's mounting check exists and every build reply the
product agent sees carries it (CLI and shell, via `fit_summary`/`fit_view`).
Both D3 halves have evidence; D3 is ready for critic review, owner tick
pending. The "anything else D4 transcripts show the agent reaching for"
clause waits on D4.

On the three sweep Loves at their fresh revisions:
- `orun1-mount-biped-c-exposed-mechanism`: **pass**, 11/11 (six MG996R by
  screws, three boards by screws, pack and ESP32 by bay).
- `orun1-mount-balancer-c-exposed-mechanism`: **reported**, 4/6 — both
  gearmotors `contact only`: the cheeks are drilled at the motor holes but
  no screw is placed. Correct per the script.
- `orun1-mount-quadruped-e-hard-surface`: **reported**, 17/21 — eight MG90S
  by screws, eight horns on their outputs, pack by bay; four boards
  `contact only` on printed bosses with no screws placed. Correct per the
  script.

Verification at `0b97765c`: `pixi run test-engine` → **2573 passed, 61
skipped, 0 failed** (8 min 30 s, built main tree, real-kernel tests run);
`CUDA_VISIBLE_DEVICES="" pytest cli/tests` → **1291 passed, 1 skipped**;
`pixi run build-engine` + `stage-engine`, then
`CADEX_ENGINE_ROOT=<payload> pytest test_cadexd_lifecycle.py
test_mounting_check.py` → **38 passed** against the staged payload. No
`OP_ARG_SPECS` change; no response golden moved (the inspect value gained a
key; reply shapes are unchanged). No shell diff. No new dependency.

Concerns for the next iteration: it is a holding check, not a strength
check (one bolt on one hole counts as screwed); a printed bracket that is
itself loose is not chased; projects accepted before ADR-486 read
`unavailable` until a new revision is accepted. The tail is now two
unreconciled records (`solemn-arbor-0802` and this one); a reconcile is due
at three. Next rung: D4 — freeze the plain prompts in the README, then
trial designs.

Dispatch closed: 1 unit — D3 mounting check in every build reply, with pass/fail real-kernel fixtures (ADR-486)

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/orun1
- commit: 0b97765cf7155b87ea77d89e483d48abe6a77f17

## State Impact

- target: loyal-ocean-0768 — Mounting check landed (ADR-486, commit 0b97765c): fit.mounting in every build reply names, per purchased part, the printed holder and how (screws on a hole axis, bay, press fit, drive output) or reports contact only / inside shell / held by nothing; pinned by pass and fail real-kernel fixtures; engine 2573 passed, CLI 1291 passed, packaged gate 38 passed. Both D3 halves have evidence; the transcript-driven catalog clause waits on D4.
