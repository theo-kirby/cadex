# ROADMAP.md — Where Cadex Stands and What's Next

Verified against source: 2026-10-30

The destination is [`VISION.md`](VISION.md): *describe a robot or mechanism
to your agent; get back a design you can build and a policy that moves it*,
measured on three benchmark briefs (B1 printed servo robot, B2 QDD
creature, B3 non-legged machine). This page is the status against it and
the plan for the next release. Tick a box when its work lands, in the same
PR as its ADR (`AGENTS.md`). The phase roadmap that got Cadex to 0.2.0
(Phases 0–17, every checkbox) is in
[`history/ROADMAP-PHASES.md`](history/ROADMAP-PHASES.md); the live
frontier, record by record, is `STATE.md`.

## Where it stands (main, 2026-10-27)

| Area | State |
|---|---|
| **Engine** | Five domains on OCCT; dynamics, MJCF export, tasks, gait references, terrain and policy rollouts on MuJoCo. A rebuild builds only the parts that changed (ADR-782). Linux x86-64 tested; macOS arm64 green in CI only. |
| **Dashboard** | Read-only, Blender-style areas: 3D viewport, Outliner, Status, Training, Version, Activations, Network, Settings; rollouts with their course and trail; run picker (ADR-790). |
| **Agent bindings** | `cadex mcp` with 14 tools plus the bridge's own; `cadex guidance` = base + five styles. No model loop of its own. |
| **Trainer** (offboard) | Brax PPO (ADR-712), warm starts across tasks, courses and robots, family training (ADR-759), teacher distillation by command band (ADR-825). |
| **Analysis** (offboard) | Stress, SIMP topology optimisation, skeleton fit to a script. Unchanged since August. |

**Against the benchmarks**

| Brief | Where it got | What stops it |
|---|---|---|
| **B1** printed servo robot | The design → MJCF → train → verify → rollout arc closed at toy scale (ADR-085), rehearsed on one CPU (ADR-170). The last unattended attempts (hex1–3, September) ran through `cadex walk --prompt`, removed by ADR-538. | Not measured since Cadex stopped running its own agent: there is no current way to run a brief unattended and score it. |
| **B2** QDD creature | The cat line (orun6–orun20, then leo, leon, lurcher and honey badger in their own repos): designed with a person's agent, trained to a 5.7 m/s gallop, walk-to-gallop schedules, rough-ground courses. | Turning within rated torque, rough ground at speed, jumping and one policy for all of it are open; design is agent-assisted, not one prompt. |
| **B3** non-legged machine | Three breadth waves (28 machines, 2026-10-10 → 12, `MACHINES.md`) designed; some trained. | Path and coverage readings exist but are not wired into `assembly.success`, so a machine's job can't be the success spec. |

## 0.3.0

The release that makes Cadex say true things about itself, closes the
contract gaps the 0.2.0 audit left open, fixes the defects a new user would
meet first, and gives the North Star a measurement again. Version 0.3.0
rather than 0.2.x, because behaviour changed since 0.2.0 (partial rebuilds,
the worker bundle, new script surface: `height_scan_far`, gait families,
banded goals).

### Cloud training (ADR-872)

- [x] Runpod provisioning, isolated trainer bootstrap, bounded detached CLI
      dispatch, local collection and Pod stop with retained disk.
- [x] Verify a real Runpod GPU smoke run from the Mac, including disconnect,
      collection, local policy verification and confirmed compute shutdown.
- [ ] Route MCP training tools through the configured cloud worker.

### Must

- [x] Remove redundant CLI restores, reuse accepted render/section display,
  and parallelize cold static fit pairs within worker budgets (ADR-875).
- [x] Edits defer the fit; `rebuild` / `cadex clearance` check it once a
  design settles. A leon V geometry edit takes 469 s, against 1,332 s with the fit (ADR-876).

**Truth and cleanup**
- [x] **The identity docs agree** (ADR-833): README, VISION (broadened North
      Star and benchmark set), this roadmap, AGENTS.
- [x] **The doc set says what is true now** (ADR-828): false statements
      fixed, history moved out, CLI/XSCRIPT/MUJOCO/INTEGRATION/PROVENANCE
      trimmed and de-duplicated.
- [x] **The governor frontier is the product's frontier.** Retire the ~90
      finished-run criteria (orun9–orun20), rewrite the shell-era PLAN
      rungs, correct `shy-sky-8568` and `crisp-cloud-1105`; `governor
      check` exits 0 and `STATE.md` is short enough to orient from.
- [x] **Dead engine and CLI code is gone** (ADR-829).
- [x] **The build tree's GUI residue is gone** (ADR-830): unreachable
      `BUILD_GUI` CMake, unused Find modules and `src/Tools` scripts,
      workbench examples and test data, GUI files in kept modules,
      macOS-bundle packaging.
- [x] **pixi carries no GUI-era dependency** (ADR-831): coin3d, pivy,
      pyside6, Qt Wayland, X11 test sets, ifcopenshell, opencamlib, PCL and
      the rest, with a clean re-solve and the payload size before and after.
- [ ] **`version.json` names Cadex** (ADR-832). Tried on 2026-10-27 and
      reverted: `sync_version.py` renames the rattler package `freecad` →
      `cadex` with it, and that recipe then fails to solve for linux-aarch64.
      Needs the rattler recipe solved under the new name first.

**Contracts** (open since the 0.2.0 audit, ADR-730)
- [ ] **Trainer ↔ engine parity.** One test, run from the `training/` venv,
      that feeds a fixed task bundle through the trainer's copies and the
      engine's originals and requires equal results: reward whitelist,
      `encode_policy`, goal and waypoint draws (incl. weighted bands,
      ADR-824), terrain boxes, height scans (incl. `height_scan_far`,
      ADR-821), policy channels, the speed-schedule blend (ADR-822).
- [ ] **The worker bundle's closure is a guard, not a probe.**
      `_unstaged_member_imports` reads function-scope imports too, so the
      ADR-827 failure (a dev build silently using installed modules) is
      refused, not rediscovered.
- [ ] **Every trainer setting a recipe uses reaches it.** `train_start` and
      `cadex train` pass `reward_floor`, `minibatches`, `max_grad_norm`
      and the distillation flags (`teacher`, `teacher_goal`,
      `distill_weight`); tool-surface change, with its test and an ADR.

**Defects a new user meets**
- [ ] **`cadex hero` never writes a blank frame.** On a machine whose GPU
      path renders nothing (sb1x), detect it and fall back to
      `--software`, or fail loudly (`shy-tower-2038`).
- [ ] **`look` after `export` or `clearance` renders**, instead of failing
      "missing tessellation" (`autumn-hawk-8597`); root-cause how the
      accepted attempt is pinned.
- [ ] **`cadex smoke` finishes on a ~100-part model.** Re-measure after
      ADR-781/782; scale the shared bound with part count if still needed
      (`keen-acorn-7595`).

**The North Star measured**
- [ ] **A benchmark protocol.** `docs/BENCHMARKS.md`: the three briefs
      verbatim, how to run one from an empty project with a person's agent
      over `cadex mcp` (no human turns), and one scorecard row per run:
      built, exported (STEP/STL/MJCF/BOM), trained, evaluation passed,
      filmed, wall time, where it stopped.
- [ ] **B1 and B3 run once on 0.3.0's tree**, scorecards committed (B2 has
      fresh evidence in the cat line's repos).

**Release**
- [ ] CI off the deprecated Node 20 actions, on a pinned Ubuntu image.
- [ ] Packaged gate green on a staged payload; `docs/releases/v0.3.0.md`
      written from ADR-731…; `VERSION` bumped; tag.

### Nice, if they fit

- [ ] **Machine tasks.** Wire the path and coverage readings into
      `assembly.success` (ADR-645), so B3 can train against its job.
- [ ] **MJX on the heightfield.** Try a newer MJX or heightfield contact
      parameters; otherwise make the box course the only trained form and
      say so (`winter-bay-5176`).
- [ ] **macOS by hand**: one person builds, runs the dashboard and drives a
      project on Apple silicon.
- [ ] **Probe weight.** `docs/probes/` is 64 MB, mostly PNG. Stop committing
      renders for new runs (link a hosted page instead) and decide whether
      the largest existing sets move out.
- [ ] **The payload's "no GUI" gate checks `lib/`** for `*Gui` libraries, not
      only `Mod/`.
- [ ] **`src/Mod/Import` and `src/Mod/Measure`**: dependency audit, then
      removal under `FREECAD.md` §3 if nothing headless needs them.

## After 0.3.0

Directions, in rough order of how much they move the benchmarks:

- **B2, the creature, finished**: turning and reversal within rated torque,
  rough ground at speed, jumping, one policy for all of it, and covers that
  wrap a jointed head, tail and spine (`STATE.md`: `odd-key-8337`).
- **B3, a machine that does its job**: machine tasks above, then one
  trained machine per `MACHINES.md` family worth having.
- **Parts library L3**: common BLDC sizes, a solenoid, a qualified
  planetary stage (`history/ROADMAP-PHASES.md`, Phase 17).
- **STEP import** for manufacturer models.
- **Posing in the dashboard**: a joint gimbal that poses the model without
  writing the design (`IDEAS.md`).

## Parked

Deliberately not started; the test-pinned protocol keeps each available
(`VISION.md`): a replacement engine on a direct OCCT binding (old Phase 11),
a desktop app, subdivision surfaces (O4).
