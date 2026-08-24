---
node_id: ab834382-7bee-5b80-87f4-a1eb3508cc70
slug: early-arbor-7123
title: Orientation, build and the working environment
created_at: '2026-08-09T15:22:46+00:00'
parents:
- nimble-pine-0740
summary: ''
---
Status: working

## Current

**Read this before touching anything.** The author's answer to "what would waste a fresh agent's whole day" was immediate and was not about code: **not knowing which stack a thing is in** — C++ versus Python, the Blender shell versus the FreeCAD engine versus Blender's own engine, what `pixi` covers, **what needs a build versus what needs an install**, and what runs on this machine versus the remote GPU box [rec: western-badger-3023].

- **Two toolchains that must not see each other.** The engine builds inside the pixi/conda-forge environment; the shell builds against `shell/lib/<platform>` with Xcode and a homebrew `cmake`/`ninja`. Both supply zlib, libpng, OpenSSL and Python at different versions. `package/app/build_app.sh` scrubs pixi and conda off `PATH` and unsets ~50 conda variables before invoking cmake on `shell/` — which is why `build-shell` is a script and not a `cmd = ["cmake", …]` task. Do not route the shell build around it [rec: merry-eagle-4093].
- **The whole build is `pixi run setup && pixi run app`**, measured at ~21 minutes end to end on a fresh clone with a warm ccache [rec: merry-eagle-4093].
- **What needs a build**: Python-only changes under `src/Mod/cadex/` need `pixi run build-engine` before the shell's suites see them, and `pixi run stage-engine` before the *bundled* engine does. A source tree that passes proves nothing about a payload [rec: merry-eagle-4093] [rec: simple-hollow-8675].
- **`AGENTS.md` is the single agent contract**; `CLAUDE.md` holds one line, `@AGENTS.md`, and nothing else. Adding content to `CLAUDE.md` is the violation — it would recreate the split ADR-005 closed [rec: quiet-wing-7912].
- **`docs/DECISIONS.md` is the project's primary memory** — 115 of 248 commits, 136 ADRs. Almost all of the code was written by agents, and the ADR discipline is what has kept that coherent [rec: slender-basin-4979].
- **ADR numbering is not contiguous.** 054 was deliberately never written, 069–072 and 111 are absent, and 060–067 plus 074 were renumbered when `MJC` merged. Cite an ADR by number **and** title [rec: slender-basin-4979] [rec: open-key-6334].
- **One branch.** The `MJC` ref still exists, pointing at the merge; nothing should be committed to it [rec: open-key-6334].
- **Related repositories, and what they are not.** `~/cdx-rl` and `~/cdx-mjc` are independent spin-off projects that *use* Cadex and occasionally open a wishlist pull request here; they are not part of this repository's concerns. `~/arch` is not a project at all — it is where the author's `.blend` and `.cadex` files live, and they are **live files**: copy before building or probing [rec: western-badger-3023].
- **Where code and doc disagree, the code wins** — and the doc is fixed in the same PR with its `Verified against source:` date bumped [rec: slender-basin-4979].
- **The hypergraph tooling comes in two halves that upgrade separately.** The skills under `.claude/skills/hypergraph-*` are **committed** and arrive with a clone; the `hypergraph` CLI is a Python package and is not, so each machine runs `uv tool install hypergraph-protocol` once. `uv tool upgrade hypergraph-protocol` moves the CLI, `hypergraph upgrade` moves this repo's copies, and neither can see the other's half — `check` warns on the skew, which is what `hypergraph_version: 0.0.7` in the config exists to make visible [rec: twilight-sail-5604].
- **CI is green again as of 2026-08-24, after three walls each hiding the next** (ADR-163). The macOS job had failed every scheduled and push run for weeks, always at *Build the shell*: (1) `actions/checkout` does not fetch Git LFS and all 6713 LFS paths here are under `shell/`, so `startup.blend` was a pointer file the shell's own CMake refuses; (2) `platform_apple_xcode.cmake` requires **Xcode 16.0** and the `macos-14` image tops out at 15.4, so the job runs on **`macos-15`**; (3) the gate's 0.65 s slider-drag parity bar cannot be met on a shared runner. The Linux engine job was green throughout [rec: weathered-sand-9705].
- **`CADEX_GATE_LATENCY_BAR`** raises the gate's *enforced* latency ceiling (CI sets 2.6 s) without relabelling the bar: `parity_bar_seconds` and `median_within_bar` in the payload always report against the real 0.65 s [rec: weathered-sand-9705].


## Negative knowledge

- [scope: building the shell | confidence: high | evidence: merry-eagle-4093] Never route the shell build around package/app/build_app.sh. Conda on PATH during a shell configure silently resolves the wrong zlib, libpng, OpenSSL and Python, and fails at link time or misbehaves at runtime.
- [scope: verifying engine changes | confidence: high | evidence: simple-hollow-8675, merry-eagle-4093] A green source tree proves nothing about a payload. Anything touching the protocol or the payload must run the packaged gate with CADEX_ENGINE_ROOT pointed at a staged payload.
- [scope: citing ADRs | confidence: high | evidence: slender-basin-4979, open-key-6334] ADR numbering is not contiguous — 054 was deliberately never written, 069-072 and 111 are absent, and 060-067 plus 074 were renumbered on the MJC merge. Cite by number and title.
- [scope: ctest | confidence: high | evidence: merry-eagle-4093] The inherited FreeCAD ctest has roughly 160 pre-existing environmental failures. Diff against build/ctest_baseline_failures.txt; never expect 100%.

- [scope: figures restated in summary docs | confidence: high | evidence: even-cliff-3863] A number restated in a summary doc has no owner and drifts silently — the engine suite count sat at 1,105 in CLAUDE.md while the ADR log tracked it to 1,698. The ADR log and the command are the live sources; treat an undated figure in a summary doc as unverified.
- [scope: a repo-wide `.*` ignore rule | confidence: high | evidence: twilight-sail-5604] Agent tooling disappears from every clone while looking clean on the author's disk — the files are present locally and `git status` is quiet, so only a fresh clone shows the gap. `.claude/skills/` was ignored here for the whole first week of the adoption, which would have handed a collaborator the AGENTS.md contract with no skills to run it. A project that un-ignores `.hypergraph/` must un-ignore `.claude/skills/` in the same commit.
- [scope: running `hypergraph upgrade` | confidence: high | evidence: tidy-banner-0293] **Superseding the 0.0.7 behaviour recorded here previously.** From 0.0.8 it replaces the `<!-- hypergraph:begin -->` block only while that block is still verbatim a template the project shipped; anything you have edited is reported as `customized`, left untouched, and the shipped template is named for you to merge against by hand. Verified here against the very block 0.0.7 destroyed — both project-specific paragraphs survived. `--agents-block` opts into overwriting. So: merge the new template after an upgrade; you no longer have to restore lost paragraphs.
- [scope: a build that aborts early | confidence: high | evidence: weathered-sand-9705] It tells you about exactly one problem. A job red for weeks has been accumulating them silently: three separate walls stood behind one another here, and each was invisible until the one in front was removed. Budget for "fix, re-run, find the next" rather than for one diagnosis.
- [scope: a CI job that has failed for weeks | confidence: high | evidence: weathered-sand-9705] It stops being read. This one failed on reconcile commits whose entire diff was markdown, and ADR-159 recorded it as "standing state" — a true sentence that functioned as a reason not to look. The actual first cause took one `gh run view --log-failed` to find.
- [scope: an absolute wall-clock bar in CI | confidence: high | evidence: weathered-sand-9705] It cannot be enforced on a machine you do not control. Every timing in the gate is uniformly 2.2–2.5× slower on a GitHub macOS runner than on the developer Mac (open 2.005 → 5.102 s, refine 1.358 → 3.021 s, drag 0.520 → 1.268 s), so the drag is not slow — the runner is. Raise the enforced ceiling, and keep reporting the real bar, or the uploaded artifact becomes evidence for a parity claim that was never met.


## Provenance

- western-badger-3023 — the author's own answer to what wastes a fresh agent's day, and what the related repositories are
- merry-eagle-4093 — the two toolchains, the scrubbing build script and the measured build time
- slender-basin-4979 — the ADR log as primary memory, and the doc conventions
- even-cliff-3863 — measured evidence that summary docs drift while the ADR log does not
- quiet-wing-7912 — the contract's move to AGENTS.md and the pointer left behind
- open-key-6334 — one branch, and the ADR renumbering
- simple-hollow-8675 — why a passing source tree proves nothing about a payload
- twilight-sail-5604 — the two-halves tooling install, the `.*` ignore trap, and what 0.0.7's `hypergraph upgrade` overwrote
- tidy-banner-0293 — 0.0.8 preserves an edited block; verified against the one 0.0.7 destroyed
- weathered-sand-9705 — the three CI walls, and why a latency bar is not enforceable on a shared runner
