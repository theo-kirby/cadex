---
node_id: e48b4875-6eaf-529f-8e31-b16328fca2f9
slug: warm-falcon-0420
title: 'Prove D7 on Lark: the copy is the working project on the persistent dashboard, edited with the original unavailable (ADR-314)'
created_at: '2026-09-13T07:51:55+00:00'
parents:
- brave-water-4060
summary: ''
---
## What

D7 on the third fresh project, Lark: `ot5-lark` was copied whole to `ot5-lark-copy85`, the persistent private-network port 8765 service was deliberately switched to the copy, and with the original path renamed away for the entire pass the public CLI changed only the copy (`foot_len` 80 → 90 mm, `policy_on` 1 → 0), two fresh engine processes restored it, and a separately started server and the persistent one both reviewed all six retained runs with their own revisions, digests, parameters, curves, served meshes and four playable, downloadable videos. The original's 1,852 files are byte-identical to the pre-copy inventory. The copy is now the working project on the shared URL. ADR-314; committed as `ca78d935`, after the iteration-84 backfill record `brave-water-4060` (commit `2173c47a`).

## Why

The critic asked first for the missing iteration-84 record and then for exactly this unit: prove D7 on Lark by copying its retained project and review artifacts, switching the persistent operator URL deliberately, verifying historical models and video playback with the original unavailable, changing the copy through the CLI, checking the original inventory unchanged, and keeping the shared dashboard on the working copy. Lark had every other criterion's evidence except D7 and D8; D7 is the smaller of the two and needs no GPU time. Nothing deviates from the critic's message.

## Method

A pre-copy SHA-256 inventory of `ot5-lark` was written to `/tmp` before anything else; no trainer, renderer or agent turn was active. `cp -R` with the destination absent, then `systemctl --user stop` and `systemd-run` of `cadex review --project ot5-lark-copy85 --host <tailscale> --port 8765`, confirmed over the private address through `/api/project` (project `ot5-lark-copy85`, six runs). The driver `docs/probes/lark-fresh/copy_lifecycle.py` is the Wren copy driver with nothing named after a project: the default run and the parameter changes are arguments, the component count comes from each run's served model and the curve lengths from each retained progress file. It renames the original to `ot5-lark-unavailable-copy85`, runs `cadex params --set foot_len=90 --set policy_on=0` and `cadex render` on the copy, runs the project-agnostic `restore.py` twice, starts a second `cadex review` on a free port, checks both pages in headless Chromium (every run selected: revision, digest, HISTORICAL relation, the `foot_len` cell, three curve point counts against `train/progress.json`, served mesh hashes, and for the four playback runs video readiness, play, survival across a poll and hash-equal download; then ACCEPTED NOW with the new values and no video; then return-to-current), asserts the two servers' results equal, asserts the retained `runs/` and `assets/` bytes unchanged, and in `finally` puts the original back. A fresh visit after the restore was recorded with `docs/probes/wren-fresh/current.py`. The compact receipt is `docs/probes/lark-fresh/copy85-evidence.json`, guarded by a new test in `cli/tests/test_lark_fresh_evidence.py`; `COPY85.md`, the probe README, the operator status README, `docs/HEADLESS-BIPED-REVIEW.md`, `docs/CLI.md`, `docs/ROADMAP.md` and ADR-314 were written.

## Result

The persistent port 8765 serves `ot5-lark-copy85`: accepted revision `083d086ad980…`, digest `4c4171abfa4f…` (the original stays at `ca88f223b54c…` / `a1232a4a8c26…`), fresh-visit default `RUN lark2-final` shown HISTORICAL, all six runs browsable, screenshot inspected. Two engine restores (PIDs 3821742, 3821789) matched the accepted state with retained bytes unchanged. Both servers returned identical per-run identities and mesh hashes; the four videos (`lark1-checkpoint20` 0.98 s, `lark1-final` 0.50 s, `lark2-checkpoint20` 8.0 s, `lark2-final` 8.0 s) played, survived a poll and downloaded hash-equal from both. The 250 retained run/asset files in the copy and all 1,852 original files are byte-identical to their pre-copy inventories, checked by the driver and again independently. The service was restarted once with no trainer running and stays up; `ot5-lark` is retained, unchanged and no longer served.

Gates on the committed tree: `pixi run python -m pytest cli/tests` 437 passed, 1 skipped, exit 0 (432.9 s); `pixi run test-engine` 2110 passed, 53 skipped, exit 0. The only `cli/` change is the guard test. No protocol, payload, engine, shell or dependency change.

Limits and concerns: same-machine private-address browser checks, not a second-device test; the original was unavailable by path, not by every filesystem route; the copy's change is a parameter edit, not retraining; existing videos were retained, not re-rendered, so no new D11 claim. Lark's remaining gap is D8, a controlled interruption of a real training attempt followed by a successful new one; any further training now happens on the copy, which is the working project. The unreconciled tail is two records (`brave-water-4060` and this one).

Dispatch closed: 1 unit — D7 proved on Lark: whole-project copy served on the persistent dashboard, edited and restored with the original unavailable, six runs and four videos reviewed identically on two servers, original byte-identical (ADR-314).

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot5
- commit: ca78d93571bc01d8df3a439bfc4835a52ce59a26

## State Impact

- target: cold-vale-4232 — D7 repeated on the third fresh project: ot5-lark-copy85 served on the persistent URL, a copy-only CLI edit (foot_len 80→90, policy_on 0) and two engine restores with the original path unavailable, all six retained runs and four videos reviewed identically on a second server and the persistent one, the original's 1,852 files byte-identical; the copy driver is now project-agnostic (docs/probes/lark-fresh/copy_lifecycle.py).
- target: deep-clover-6012 — D10: the persistent port 8765 service was deliberately switched from ot5-lark to the working copy ot5-lark-copy85 with no trainer running, verified over the private address before and after the probe (fresh-visit default RUN lark2-final as HISTORICAL against the copy's accepted 083d086ad980…), and keeps serving; operator status README identifies the copy.
- target: crisp-sun-1239 — Lark now has D7 evidence of its own; the working project is ot5-lark-copy85 and ot5-lark is retained unserved; only Lark-specific D8 (controlled interruption) remains without evidence; gates CLI 437 passed/1 skipped and engine 2110 passed/53 skipped on commit ca78d935; unreconciled tail two records.
