---
node_id: 4a05ca02-9de1-5175-a42d-54749faf7cfe
slug: twilight-sail-5604
title: The skills could not travel; the CLI was a release behind
created_at: '2026-08-09T18:03:03+00:00'
parents:
- rising-chart-1564
summary: 'Adoption audit: sound. Two fixes around it — .claude/skills/ un-ignored so a clone gets the workflows, and the 0.0.6 CLI brought to 0.0.7 and stamped. Found a defect in hypergraph upgrade: it overwrites project-specific content inside the AGENTS.md sentinels.'
---
## What

An audit of this project's Hypergraph adoption, then two fixes it found. The
adoption itself was sound — `check` exits 0, the graph is fully committed, and
five post-adoption record nodes show the protocol in real use. What was wrong sat
around the graph rather than in it:

1. **The skills could not travel with the repo.** `.gitignore` line 2 is `.*`,
   and the only escape hatch was `!/.hypergraph/`. So `.claude/skills/` was
   ignored and untracked. A clone got `AGENTS.md` telling it to "run the
   `hypergraph-orient` skill" and no skill to run — the contract without the
   means to follow it. Un-ignored `/.claude/skills/` only; the rest of `.claude/`
   (including `scheduled_tasks.lock`) stays local. 25 skill files are now
   trackable.
2. **The CLI was 0.0.6 while the skills were 0.0.7**, and the config carried no
   `hypergraph_version:` stamp, so nothing in the repo could report the skew.
   Upgraded the CLI (`uv tool upgrade`), then ran `hypergraph upgrade` here.

`.hypergraph/AGENTS.md` gained a **Getting the tool** section. It documented the
protocol thoroughly and never said how to obtain the CLI, which is not committable
— and it now names the two upgrade commands explicitly, because neither can see
the other's half.

## Why

This repository is about to take other contributors. Everything above is invisible
while one person works on one machine with the tool already installed, and all of
it fails on the second clone.

## Method

Audited against the eight steps of the `hypergraph-adopt` skill, then verified the
countable claims independently rather than trusting the nodes: 248 commits at the
adoption commit (stated: 248), highest ADR 136 (stated: 136), 16 surviving
`[VibeCAD-era]` tags (stated: they still label code), and 286 non-blank lines of
the retired `CLAUDE.md` traced into `AGENTS.md` — 4 absent, of which 3 are the
retired header and 1 is the test count `even-cliff-3863` deliberately corrected.
`rising-chart-1564`'s 56 -> 57 part-operation count re-measures as correct *at the
commit it cites*; the tree now reads 58 because `measurement` landed afterwards in
uncommitted work.

`hypergraph upgrade` was run with `--dry-run` first, which is what caught the
defect in the Result below.

## Result

**Fixed.** `check` still exits 0 — 0 violations, 0 warnings, 14 pre-epoch nodes
exempt, 0 unreconciled. The config is stamped `hypergraph_version: 0.0.7` and the
five skill directories are refreshed to 0.0.7.

**A defect in `hypergraph upgrade`, found by running it here.** It replaces
*everything* between the `<!-- hypergraph:begin -->` sentinels with the shipped
template, so it deleted two paragraphs this project needs:

- the clause reconciling the record graph with `docs/DECISIONS.md` — which the
  adopt skill's step 8 **requires** be written, under "contract reconciliation";
- the epoch-marker note naming `winter-rain-7897` and the 14 prehistory nodes.

Both were restored by hand after the upgrade. The same command treats
`.github/workflows/` the opposite way — it *reports* drift rather than
overwriting, "because adopters customize these". The AGENTS.md block has exactly
that property and got the opposite default. Until the tool changes, the block
carries a warning naming itself as overwritable, and `.hypergraph/AGENTS.md` says
to re-read it after every upgrade.

**Not fixed, and not a defect: ~38 files of ADR-139 work (the measurement and
dimension domain) are in the working tree with no record node.** That is ordinary
work in flight, noted here only so the next reader knows the tree is ahead of the
graph.

## Negative knowledge

A repository-wide `.*` ignore rule silently swallows every agent-tooling
directory, and the failure is invisible to the author: the files are on their
disk, `git status` is quiet, and only a fresh clone shows the gap. When a project
commits `.hypergraph/` through an un-ignore, `.claude/skills/` needs the same
treatment in the same commit — the graph and the workflows that maintain it are
one deliverable.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: main
- commit: 384f9b4b11e59bb13382cde99ea2ca4cb0e6a8a4

## State Impact

- target: early-arbor-7123 — The hypergraph skills are now committed under .claude/skills/ and arrive with a clone; the hypergraph CLI is not committable and is installed per machine with 'uv tool install hypergraph-protocol'. The CLI and this repo's copies upgrade through two different commands that cannot see each other — 'uv tool upgrade hypergraph-protocol' for the CLI, 'hypergraph upgrade' for the repo's skills and AGENTS.md block — and check warns when they are out of step. This project is stamped hypergraph_version 0.0.7. New negative knowledge: a repo-wide '.*' ignore rule hides agent tooling from every clone while looking clean on the author's disk, so a project that un-ignores .hypergraph/ must un-ignore .claude/skills/ in the same commit.
- target: early-arbor-7123 — New negative knowledge: 'hypergraph upgrade' overwrites the entire <!-- hypergraph:begin --> block in AGENTS.md, including this project's ADR-log reconciliation clause and its epoch note. Re-read and restore that block after every upgrade until the tool preserves project-specific content; it treats .github/workflows/ the opposite way, reporting drift instead of overwriting.
