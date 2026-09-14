---
node_id: 151f7ab8-8a5b-5d38-9de7-3ed71d8ef10e
slug: crisp-sun-1239
title: Live headless project review — the ot5 charter (ADR-284)
created_at: '2026-09-12T14:51:03+00:00'
parents:
- nimble-pine-0740
summary: ''
---
Status: working

## Current

**Run ot5 is closed: the owner ticked D1–D11 on 2026-09-13, and no criterion under this root is open [rec: patient-pond-3886].** The run stopped between iterations after iteration 111 committed (`da05952c`); `ouroboros archive` wrote `.ouroboros/history/ot5.md`, and the branch merged into `main` with a merge commit. Numbers: 111 iterations in 19.4 h; 136 commits, 283 files, +47,157 / −103 lines; critic verdicts continue 101, reject 5 (each fixed forward the next iteration), looping 2, stuck 2, done_rejected 1; 0 reverts. The state graph had carried every criterion at `working` since about iteration 50, and only the owner's checkbox closes one, so iterations 52–111 repeated the lifecycle (Wren, then Lark and its working copy) while the loop detector fired `no_frontier` for 60 iterations straight and rotated the actor four times to no effect [rec: patient-pond-3886]. The successor charter is ot6 (ADR-328), whose umbrella node holds the new frontier.

**What ot5 built (ADR-284) [rec: dusty-peak-9330] [rec: lucky-comet-0031]:** a one-project inspection dashboard served from this machine over its private network, showing the selected project's model, design specs, training curves, run history and playable/downloadable policy videos, and a proof of the whole file lifecycle — create, save, reopen, train, record, review, revise, retrain, revisit — on three fresh, product-agent-designed parametric bipeds: Reed, Wren and Lark. The owner's fixed choices held throughout: inspection only, one project per server, no training controls or public hosting; measured gait rather than walking success as the gate; mg-legs retired from the charter (its history on `late-pond-2851`); headless only, one bounded training run at a time (≤ 2 h, ≤ 20 GB) on the existing offboard trainer; a historical view never rebuilds an old run with today's script. Each D1–D11 child node carries its own evidence and its own tick.

**The last three ot5 iterations (109–111) each did the critic's named unit.** Iteration 109 closed D6's last undemonstrated fact — the engine killed and restarted during real Lark training — with ADR-325, and moved the operator service back under its user unit after finding it running as a bare tmux process [rec: happy-gate-9091]. Iteration 110 made the failed-observation run `lark109-engine` honest on the dashboard and fixed the record writer's dangling policy locator (ADR-326) [rec: lean-orchard-0769]. Iteration 111 closed the completed-run retention gap: an ok run with an unstored policy is listed as a problem with the exact store command, and the drivers store before recording (ADR-327); the CLI suite ended at 481 passed / 1 skipped on `a0706aec` [rec: empty-vine-5860]. Three records were then unreconciled, which the run's last record named as the next unit; that fold is this pass.

**Gates at close.** CLI 481 passed / 1 skipped at `a0706aec`; the engine suite was unchanged from the pre-launch run (2102 passed / 54 skipped at launch [rec: hidden-reef-8369]; 2110 passed / 53 skipped after `lark98` [rec: quiet-pebble-5566]), no ot5 unit having touched the engine, payload or `shell/` [rec: empty-vine-5860].

**Standing limits, stated on every record and never claimed closed:** all browser evidence is same-machine private-address (headless Chromium or HTTP), never a second device; one training seed per design; gait poor everywhere (Lark's best is a 35 mm shuffle in eight seconds); pytest counts as a trainer to the probes' exclusion guard, so the CLI suite must not run while a probe trains; `cadex` defaults `--project` to `./.cadex`, so quoted advice must name it [rec: happy-gate-9091] [rec: lean-orchard-0769] [rec: empty-vine-5860].

Reconcile judgement: `open` → `working`, as the closure record declares. The criteria are owner-ticked and the evidence is on the children; the earlier per-iteration narrative of this node (Reed, Wren, Lark, the bounded-operation rung and the download repairs) lives on in the record graph and on D1–D11 and is compacted out of here [rec: patient-pond-3886].

## Negative knowledge

- [scope: unattended Ouroboros runs on this repo, carried into ot6's charter | confidence: high | evidence: patient-pond-3886] Evidence receipts committed under `docs/probes` grew to 26.5k lines (2.9 MB) against the charter's own "compact evidence" line, and the private Tailscale address appears 27 times in committed docs; ADR-328 caps committed receipts at 16 KB (screenshots 200 KB) with dumps left in the project directory and bars committing any private-network address or hostname.
- [scope: the Codex critic on this Ubuntu 24.04 host | confidence: high | evidence: patient-pond-3886] It issued zero tool calls in its first 106 verdicts because Codex's default bubblewrap sandbox cannot start under `kernel.apparmor_restrict_unprivileged_userns=1`; `features.use_legacy_landlock = true` in `~/.codex/config.toml` repairs it (reads work, writes denied). Codex's weekly window went 25 % → 100 % as critic and is blocked until 2026-09-19.
- [scope: a charter whose exhaustion policy is "repeat the lifecycle" | confidence: high | evidence: patient-pond-3886] With every criterion at `working` and only the owner able to tick, repeating produces evidence nobody asked for: 60 consecutive `no_frontier` iterations and four actor rotations moved no checkbox. ADR-328 chose `report_done` instead.

## Provenance

- dusty-peak-9330 — the owner redirected ot5 to live headless project review and lifecycle recording; ADR-284; the fixed choices
- lucky-comet-0031 — the ot5 operator directive: the charter verbatim, the nine criteria declared as gaps
- hidden-reef-8369 — the launch baseline: green engine and CLI suites, harnesses authenticated, GPU box available
- simple-raven-5405 — adds persistent current-project dashboard criterion D10
- modest-dawn-3706 — adds shared neural-whoop visual-reference criterion D11
- quiet-pebble-5566 — ADR-320: Lark's last Lark-only lifecycle limit closed; engine 2110 passed / 53 skipped
- easy-badger-5812 — iteration 107: the D6 engine-restart handoff bet that iteration 109 took
- happy-gate-9091 — iteration 109: ADR-325 engine restart during real training; operator service restored under its unit; D6's last fact demonstrated
- lean-orchard-0769 — iteration 110: ADR-326 policy-store row and honest failed-observation run; nested-project advice corrected
- empty-vine-5860 — iteration 111: ADR-327 retention gap listed and closed; CLI 481 passed / 1 skipped; names the reconcile pass as next
- patient-pond-3886 — run ot5 stopped at iteration 111; the owner ticked D1–D11; digest numbers, the two operational findings and the lessons carried into ADR-328
