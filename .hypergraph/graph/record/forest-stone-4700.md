---
node_id: 4d85a960-a479-5051-bccb-6768ecdbc681
slug: forest-stone-4700
title: ot11 R1 walk session 4 diagnosed, pre-registered and launched (r12 training); C1 REPORT remaining defects; packaged lifecycle gate 23/23
created_at: '2026-10-01T06:30:39+00:00'
parents:
- terse-bramble-7437
summary: ''
---
## What

Walk session 4 diagnosed, pre-registered and launched on `ot11-quad-1` (commit `cb5fd966`); REPORT.md's remaining-defects section written and test-pinned, and the packaged lifecycle gate C1 owed since ADR-465..468 run (commit `54894c40`).

- `docs/probes/ot11/README.md` § "Walk session 4: the diagnosis it starts from, and what it changes".
- `docs/probes/ot11/prompts/walk.s4.loop.prompt.txt` (`ca1d1b99…`), `walk.s4.continue.prompt.txt` (`3a6e6f17…`).
- `docs/probes/ot11/retained/p4-quad-1-s4-preregistration.json` (registered 06:12:49Z, before launch).
- `docs/probes/ot11/REPORT.md` § "Remaining defects"; `cli/tests/test_ot11_report.py::test_remaining_defects_cite_receipts_that_exist`.

## Why

The critic's message named this unit: diagnose session 3 from its receipts, pre-register session 4 and launch it under setsid, then while it trains write REPORT.md's remaining-defects section and pay the packaged gate. R1 (smooth-fountain-9832) is the only open behaviour and the GPU was idle; C1 (golden-bay-4173) owed the gate. Done as asked, with one deviation in wording: the critic said "steel feet stay". I did not instruct the agent to keep them, because the mechanism is the agent's to author; the prompt states that the steel feet passed W10 on every seed and leaves the mechanism rule exactly as session 3's. The agent's own DECISIONS.md already keeps them. Likewise the convex-speed / progress-gated swing proposal reaches the agent as its own closing report and DECISIONS.md, not as the actor's instruction.

## Method

- **Diagnosis from receipts** (r10/r11 evaluations, s3 rounds, the agent's turn-1 closing text): steel feet passed W10 −0.021..−0.043 HH on every seed of rounds 9–10; no session-3 round stepped (worst foot 0 steps, W8-low 0.00, RR held up on all ten seeds of r10 and r11); r11's speed_track paid +1.0..+1.65/step vs +0.25 at rest by rocking (tray v/command sd 0.47–0.84 around ~0), since a Gaussian of instantaneous speed is concave near zero. The agent proposed a convex speed cost and progress-gated swing pay; its DECISIONS.md marks the r11 reward farmable.
- **Session 4 changes no rule.** Same mechanism bounds, spec block and mechanism_rule, seeds, trainer `97bc1d9a…`, driver `86a96079…` (digests re-checked). Stop rule counts this session's runs (≤3, each ≤2,400 s, `--stop-on-collapse`), since session 3's "ten in total" cap is spent; a refused start is not a run. Driver `--max-runs 16 --max-turns 2` (ledger holds 13 evaluations).
- **Launch.** `setsid nohup pixi run python docs/probes/ot11/runner/rounds.py --project ~/cadex-projects/ot11-quad-1 --prompt …walk.s4.loop… --continue-prompt …walk.s4.continue… --max-runs 16 --max-turns 2 --out ~/cadex-projects/ot11-notes/quad-1-s4` at 06:13:10Z; its `registration.json` digests equal the pre-registration's. GPU idle, no other supervisor alive. Project head before: `08161b6f`, accepted revision `bfb59bb5…`, model `5e28d393…`.
- **Gate.** The CLI agent runs the dev tree (`src/Mod/cadex`), so rebuilding did not touch the live session. `pixi run build-engine` then `pixi run stage-engine` (exit 0; payload Mod/cadex equal to source); `CADEX_ENGINE_ROOT=build/engine/cadex-engine-0.0.0-linux-x64 pytest src/Mod/cadex/cadex_tests/test_cadexd_lifecycle.py`: 23 passed, 0 skipped. Engine source unchanged since `d410b098` (ADR-468).
- **Remaining defects** (each with a receipt link or ADR the test checks exists): R1 0/10 on rows 13–23 with session 4 running; no walking gait judged; the judge's stepping/slip blind spot (ADR-460/461/463); W10 under a gait on steel feet unmeasured; rounds 1–3 on the pre-ADR-465 trainer; the spec-block mechanism_rule check is the actor's, not the product's; the gate paid. The new test fails on the old source (no section).
- Tests: `test_ot11_contract/rounds/report` 35 passed before the README edit committed; `test_ot11_report.py` 12 passed after; full `cli/tests -x`: **1 failed, 1222 passed, 1 skipped** (885.5 s). The failure is `test_walk.py::test_the_same_walk_handles_a_linear_carriage`, `jaxlib XlaRuntimeError: INTERNAL: cuSolver internal error`, and it reproduces in isolation (`--lf`, 7.7 s). It failed because the agent's session-4 run `r12-convex-sym` had started training at 06:23:58Z and holds 24.7 GB of the GPU's 32.6 GB, and the walk test trains with JAX on the same GPU. The two files after `test_walk.py` (`test_wren_*`) pass, 18 of 18. The 11 `test_walk.py` tests after the failed one did not run (`-x`).

## Result

- Walk session 4 is live under setsid (rounds.py pid 2042431). Its first run, `r12-convex-sym` (the agent's own convex speed cost, reward-only; registered reason cites r11's W8-low 0.00, W5-steps 0, W3 0.015-0.033 and the +1.3/step rocking pay), is training under its supervisor: at iteration 100 its reward was about −2.1/step, with `--stop-on-collapse` on.
- **Deviation: a second GPU user, briefly.** My full `cli/tests` run overlapped r12's start, and its JAX walk test used the GPU while r12 trained. That broke the charter's one-GPU-job rule for the test's duration. r12 was unharmed (its train.log continued through iteration 100 and the checkpoint, with no errors in trainer-stdout). I did not rerun GPU-using tests while it trains.
- **Not green, and named so: `cli/tests` is unverified at this revision** for `test_walk.py` from `test_the_same_walk_handles_a_linear_carriage` onward (12 tests). The cause is environmental (GPU contention), not code: this unit changed only docs and `test_ot11_report.py`. The next iteration must rerun `pixi run python -m pytest cli/tests/test_walk.py` when no training job holds the GPU. Receipts land in `~/cadex-projects/ot11-notes/quad-1-s4/` and the project's `loop-ledger.jsonl`.
- The packaged lifecycle gate passes against a payload staged from the current engine source; C1 owes it again only after a later engine change.
- REPORT.md has every section C1 names; it will move with session 4's rounds.
- Next iteration: publish whichever session-4 rounds have finished under session 3's validity checks (spec block vs `retained/walk-spec-block.txt` under mechanism_rule, HIP_MM/WEIGHT_N vs rig, revision differing only in the policy line), regenerate both ledgers and REPORT.md. Do not start a second GPU job, including a JAX test suite, while it runs.
- Tail: 1 unreconciled record after this one.

Dispatch closed: 1 unit — walk session 4 diagnosed, pre-registered and launched (r12 training); REPORT.md remaining defects; packaged lifecycle gate 23/23; cli/tests walk tail unverified (GPU contention)

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot11
- commit: 54894c403c70b7e6734ef7c3a1e5bf7b9f3003dc

## State Impact

- target: smooth-fountain-9832 — walk session 4 pre-registered (retained/p4-quad-1-s4-preregistration.json; no rule changed from session 3, at most 3 runs of 2400 s with --stop-on-collapse over 2 turns) and launched under setsid at 06:13:10Z; its first run r12-convex-sym (the agent's convex speed cost) is training; R1 still 0/10
- target: golden-bay-4173 — REPORT.md has a test-pinned Remaining defects section; the packaged lifecycle gate owed since ADR-465..468 passes 23/23 against a payload staged from current engine source; cli/tests is unverified for test_walk.py's last 12 tests, which failed or did not run on GPU contention with r12 and must be rerun with the GPU idle
