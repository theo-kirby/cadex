---
node_id: f5b7827f-94be-5674-9bf1-327e24538d1c
slug: damp-flame-5523
title: P2. The product evaluates any policy against its task's spec
created_at: '2026-09-30T07:04:57+00:00'
parents:
- nimble-pine-0740
summary: ''
---
Status: open

## Current

Open charter criterion for run ot11: **P2. The product evaluates any policy against its task's spec.** The charter asks for: the success spec declared in xscript alongside the task and documented in `docs/XSCRIPT.md`; one command that evaluates an accepted policy on its frozen seeds and writes a report into the project (pass or fail per seed and per predicate, the reward term by term, termination causes, behaviour metrics, the video and a filmstrip on the dark floor); behaviour metrics for gait (step count, foot clearance, foot slip, duty factor, commanded-velocity tracking), reach (final error, time to target, overshoot) and balance (tilt, drift, heading, time to recover from a shove); the review dashboard showing the report; and tests pinning every metric on passing and failing fixtures, the `w2-2` shuffle among the failing ones. The human owns the charter checkbox; roles report results and do not tick it. Declared target: `gap-p2-product-evaluates-any-policy` [rec: kind-spire-3578].

**Every listed part now exists; the actor believes the criterion is met and has not ticked it** [rec: mild-horizon-5182]. Reconcile judgement: the status stays `open` because no record declares a flip and acceptance belongs to the owner and the critic.

**What exists**:

- **The behaviour metrics are engine code** (ADR-455, commit `3014ee62`). `src/Mod/cadex/CadexEvaluation.py` (pure standard library, outside the service's closure) reads a rollout trace into posture, gait and reach metrics, and `check()` holds them against `{id, metric, min, max}` predicates. `CadexDynamics.evaluation_rig` reads the model's half (base, floor, mass, COM height, feet and hip height, tip and arm length); it refuses a foot whose collision geom is a mesh or cylinder. There is no second reader: the probe's `measure.py` is only the contract binding [rec: ready-field-7940].
- **Every metric is pinned on a passing and a failing motion** (`cadex_tests/test_evaluation_metrics.py`), and `w2-2` is a failing fixture (`cadex_tests/fixtures/ot10_w2_2_feet.json`, a base-and-four-feet pose extract, 153 KB): it fails on speed (1.907×), step share (0.140), slip (0.666), leg balance (4.2×) and floor depth, and passes on tilt, heading, clearance and duty factor. Reach metrics are pinned on synthetic reaches only; no real arm has been measured [rec: ready-field-7940].
- **The success spec is declared in xscript** (ADR-456, commit `3ab0c538`). `assembly.success(predicates, seeds, feet, tip, tip_offset_mm, episode_seconds, reset_variation, disturbance, randomisation)` is passed to `assembly.task(success=...)` and lands resolved in the task bundle's `success` block (`cadex-success-spec-v1`), documented in `docs/XSCRIPT.md`. `CadexDynamics.evaluation_task(bundle)` returns the task under the spec's horizon and conditions. No protocol change [rec: first-mist-2505].
- **A spec states its own randomisation** (ADR-458, commit `21e368e6`), on the terms of its other two conditions: omitted is the task's own, `[]` is none, a list replaces it. The report's `spec` block states the randomisation played. A bundle without the key plays its task's randomisation [rec: glad-fjord-0764].
- **The reward cannot judge itself.** A predicate names one of the 26 metrics in `CadexEvaluation.METRICS`; the task's reward, a reward term or a channel is refused (`success_reads_the_reward`, `unknown_success_metric`), and a metric the model cannot measure is refused at declaration (`success_metric_needs_{feet,tip,shove,goal,base,floor}`) [rec: first-mist-2505].
- **The spec is outside the task's identity.** Two bundles differing only in their spec (its randomisation included) share one semantic digest, so a revised spec can be held against an earlier policy; a task with no spec writes the same bundle byte for byte [rec: first-mist-2505] [rec: glad-fjord-0764].
- **One command evaluates** (ADR-457, commit `f3a43b90`). `cadex evaluate` reads the retained accepted attempt as `cadex smoke` does, never rebuilds, and rolls the policy on each frozen seed under the spec's conditions through `CadexDynamics.evaluate_success`. It writes `evaluations/<revision>-<policy>/evaluation.json` (`cadex-evaluation-v1`): per seed, pass or fail, every predicate's value and reason, the behaviour metrics, the reward term by term, how the episode ended and every drawn value; plus a summary (predicate tallies, termination causes, min/median/max), one trace per seed and a `PROGRESS.md` row. It names no behaviour, and tests assert that. A seed with a solver warning is `void` and has not passed; a spec seed equal to the training seed is refused. The staged payload gives the same seed rows as the dev tree [rec: misty-timber-4175].
- **The command films what it measured** (ADR-459, commit `7cf3f906`, `cli/cadex_cli/film.py`). From each filmed seed's kept trace and the accepted attempt's retained tessellation it draws an overview sheet and a detail sheet, twelve 256 px frames each, on the dark prototype floor, every frame carrying its simulation time; the first filmed seed also gets a studio video. Flags: `--film` (`auto`/`all`/`none`/seeds), `--no-video`, `--detail-start`, `--detail-step`, `--film-only`. The report gains a `film` block (`cadex-evaluation-film-v1`). The measurement is written before anything is drawn; a film that cannot be drawn exits 1 and leaves it. Sheets are byte-repeatable across draws; the encoded video is not [rec: mild-horizon-5182].
- **The review dashboard shows the report.** An *Evaluation* tab (`docs/REVIEW-DESIGN.md` §17) over `/api/project`'s evaluations list, `/api/evaluation/<name>` and `/evaluation/<name>/<file>`, pinned in headless Chromium on the `w2-2` shuffle as the failing fixture and a passing one [rec: mild-horizon-5182].

Evidence at `7cf3f906`: `pixi run test-engine` 2439 passed, 53 skipped; `cli/tests` 1191 passed, 1 skipped. That unit changed no engine source, protocol or payload, so the packaged gate was last run at `21e368e6` (lifecycle plus live success spec, 27 passed) [rec: mild-horizon-5182] [rec: glad-fjord-0764].

**Limits and constraints for what follows**:

- Goal metrics (`speed_ratio`, `lateral_ratio`, the four reach metrics) are refused until a task can state a goal (P3). Reach cannot be specified through the product until then; walk can, using `mean_forward_speed_mm_s`. A reach frame shows no target marker for the same reason [rec: first-mist-2505] [rec: mild-horizon-5182].
- The `assembly` page of the model's `describe_api` view is at 21,411 of 21,500 characters (ADR-360) after one notes sentence was deleted to fit, and its notes do not mention `assembly.success`. P3's goal surface and P4's guidance will not fit until the notes are trimmed or the page is split [rec: glad-fjord-0764].
- The film's detail view follows the whole design's centre, not a named base, and "side-on" is the direction from the start to the farthest point [rec: mild-horizon-5182].
- Default `cadex evaluate` takes about 3.5 minutes longer on a sixty-part robot for one seed's sheets and video; about 21 s with `--no-video` [rec: mild-horizon-5182].
- A spec that inherits its task's randomisation changes its evaluation conditions whenever the training randomisation is revised. Nothing enforces stating it [rec: glad-fjord-0764].
- The trainer was not changed or run against a bundle with a `success` block. It does not refuse a `--seed` that is one of `success.seeds` (only the evaluation refuses), and `CURRICULUM_TASK_KEYS` does not list `success`, so a warm start across a spec revision is a whole-file digest mismatch there [rec: first-mist-2505] [rec: misty-timber-4175].
- A rollout is bounded by `MAXIMUM_TRACE_POSES` (100,000); the evaluation does not trim the trace to the bodies it reads. Each seed leaves about 6 MB of trace in the project (ignored by its git), and nothing prunes traces or old evaluation directories. Evaluations written with `--out` outside `evaluations/` are not on the dashboard [rec: misty-timber-4175] [rec: mild-horizon-5182].
- Rest thresholds, stance height and the step definition are engine constants a spec cannot override; the P1 contract uses the same values [rec: first-mist-2505].
- The product agent does not have the command as a tool, and nothing in its guidance mentions it (P4) [rec: misty-timber-4175].
- The `w2-2` fixture rests on a reading of the charter: a five-body pose extract is a test fixture, not a committed rollout trace. If that reading is rejected, the fixture goes and the `w2-2` tests must skip without the read-only project [rec: ready-field-7940].

## Negative knowledge

- [scope: the `cli/` assembly API page under ADR-360's 21,500-character ceiling, as of `21e368e6` | confidence: high | evidence: first-mist-2505, glad-fjord-0764] Describing the success spec in the assembly domain's notes does not fit the page. A paragraph took it to 23,344 characters and failed `test_every_page_of_the_live_contract_fits_one_tool_result`; one keyword (`randomisation=`) took it to 21,532 and failed the same test. Both times text was removed and the budget was not raised.
- [scope: `CadexDynamics.apply_randomisation` with more than one seeded episode on one compiled model, as of `f3a43b90` | confidence: high | evidence: misty-timber-4175] Playing several seeds on one compiled model compounds the draws, because randomisation is multiplied into the model in place: seeds 1103–1110 disagreed with the P1 receipts by up to a relative 33. Compiling one model per seed reproduces all ten to 2.0e-15. `apply_randomisation` itself is unchanged; the trainer's reference runner and live mode were not audited for this.
- [scope: `cadex evaluate` film sheets under the 300 KB committed-PNG cap, `ot11-w2-negative` seed 1101 | confidence: high | evidence: mild-horizon-5182] Twelve frames at 288 px gave a 304,531-byte detail sheet, over the cap. 256 px is the size that fits (sheets 107 KB to 258 KB).

## Provenance

- kind-spire-3578 — ot11 operator-declared charter gap
- ready-field-7940 — behaviour metrics moved into the engine (ADR-455), w2-2 failing fixture, reach metrics
- first-mist-2505 — assembly.success declares the spec in xscript (ADR-456); reward refused as a predicate
- misty-timber-4175 — cadex evaluate and its report (ADR-457); per-seed model compile, void seeds, training seed refused
- glad-fjord-0764 — a spec states its own randomisation (ADR-458); assembly API page at 21,411 of 21,500
- mild-horizon-5182 — film sheets and video on the dark floor, dashboard Evaluation tab (ADR-459); actor believes P2 met
