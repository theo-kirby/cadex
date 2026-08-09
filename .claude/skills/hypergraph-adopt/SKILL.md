---
name: hypergraph-adopt
description: Bring a project with a past under the Hypergraph protocol - import an existing hosted graph as legacy history (mode A) or author honest prehistory from the repo itself (mode B), draw the adoption epoch, distill a real state graph, and install the AGENTS.md onboarding. Use hypergraph-init only for day-zero projects.
---

# Hypergraph Adopt

Conversion path for a repo **without** `.hypergraph/config.yml` that already has a
history: an existing hosted graph, a mature codebase, or both. Protocol:
[spec.md](references/spec.md) — especially *Adoption epochs*. Day-zero projects use
hypergraph-init instead; everything init does, this skill does *plus* the past.

## The CLI

Invocations below write `hypergraph …`. In a dev checkout of the protocol repo that is
`uv run tools/hypergraph.py …`; an adopter gets the bare `hypergraph` from
`uv tool install hypergraph-protocol`. Same tool, same flags — pick whichever resolves.

## Modes

- **Mode A — a legacy graph exists** on a hosted store: import it verbatim as the
  fork; the original graph is never modified and remains the archive.
- **Mode B — no graph**: author 3–10 "Prehistory" record nodes distilled from the repo
  itself and the author's memory. Honest summary, never event-by-event reconstruction.

The adopted project's graphs are node files committed in its repo, exactly as for a
day-zero project. Nothing to decide.

## Workflow

1. **Inventory.** Start with the computed facts:
   ```
   hypergraph adopt --survey          # add --json to consume it structurally
   ```
   One call for the git shape (first commit, contributors, timeline signals,
   highest-churn paths), top-level source dirs, doc inventory, test framework, and
   **whether `CLAUDE.md` is a symlink to `AGENTS.md`** — which step 8 must not break.
   It replaces roughly fifteen exploratory bash calls; spend what it saves on reading
   the docs it lists.

   **Timeline signals** are evidence about where an epoch might fall, not a decision:
   tags (the author's own markers), directory births (when each top-level dir first
   appeared — usually the signal that fires), and quiet gaps (idle stretches — the
   strongest signal on a paused-and-revived repo, and silent on a steadily-worked
   one). Take them to the interview in step 3; the author says which meant something.

   Then detect the mode. Mode A: resolve **all** graph anchors — the root(s) *plus any
   index nodes the repo's docs declare as anchors* (docs saying "node X is the system
   of record" make X an anchor even if it isn't the root). Then pull them in one call:
   ```
   hypergraph mirror pull --record-node-id <id> [--record-node-id <id>…] \
       [--state-node-id <id>] --out-dir .hypergraph/cache
   ```
   It writes `record.json` / `state.json` ready for step 5, prints a draft `archive:`
   block on stderr, and errors if a node is reachable from both graphs' anchors.
   Confirm the node count covers what the docs cite before proceeding.
2. **Read the repo properly.** The docs the survey listed (README, CHANGELOG,
   ARCHITECTURE/DESIGN, any `docs/` tree) and the highest-churn paths it named. In
   mode A, skim the pulled graph too. You are reading for the questions you cannot
   answer — what a directory birth was *for*, why a decision went the way it did,
   which doc claim the code now contradicts. Those are step 3's material.
3. **Interview the author.** See [The interview](#the-interview) below — one sitting,
   two parts: history (feeds the prehistory nodes in step 5) and current state (feeds
   the distillation in step 7). Run it once, here, after the reading and before any
   node is written. This is the part nothing can compute and it is the highest-value
   cargo in the whole adoption.
4. **Init.** Let the CLI write the mechanical parts — hand-written YAML is a proven
   failure mode (a stub config once made `check` report 0 violations while it silently
   guessed the roots):
   ```
   hypergraph adopt --init                 # both roots + a valid config
   ```
   **The rule is `--init` before anything is *authored*** — nothing can be authored
   until a root exists to parent on. It is not "before anything happens", and the two
   modes want different orders:
   - **Mode B**: `--init` first, exactly as numbered. It mints both roots.
   - **Mode A**: **import first, then `--init`.** `--init` adopts the imported legacy
     root instead of minting a rival, and says which it did (`adopted existing` /
     `minted`). Run it the other way and you get a *minted* root plus the imported
     one, i.e. two parentless roots — which `check` does not flag, so nothing tells
     you. Recovering means deleting the minted root file and re-running
     `--init --force`.

   `hypergraph import` does not need a config, which is what makes the mode A order
   possible — pass `--graph-dir .hypergraph/graph` and it writes node files directly.
5. **Bring in the history.**
   - **Mode A**: `hypergraph import --record <export> [--state <export>] --fork` —
     node_ids and slugs are preserved verbatim; this *is* the fork (the host has no
     native one — slugs are minted on create and immutable). **`--fork` is mandatory
     here**: it files the archive's ids under `origin:` as provenance, so the repo
     becomes the continuing graph and owns its whole history. Config must
     gain a mandatory `archive:` block naming the legacy roots, each with a `title` —
     **artifacts do not survive import** (node files have no artifact op), so
     the archive reference is the only pointer to them. For graphs above ~1000 nodes,
     offer **epoch-split**: import only the recent epoch and leave older history on the
     archive (never truncate — the archive keeps everything); it is also how you
     mirror less history when a full push would be thousands of creates.

     The pull writes `legacy-record.json` / `legacy-state.json`. **Keep them.** Step 7
     reads the legacy export (`--resolve-prefixes --against`), and it is the only
     record of what stayed on the archive — pre-import artifact counts included.
   - **Mode B**: author the prehistory record nodes (`hypergraph new record`; they may
     parent on the record root) from the repo evidence *and* the interview. **Roughly
     one node per era or workstream** — about 3 for a young project, up to about 10
     for a long-lived one. Each carries `## State Impact` lines feeding step 7. Do not
     let 10 become a changelog: each node is an honest summary of a real era, never an
     event-by-event reconstruction. Cite what each claim came from — a doc, a commit
     range, or the interview.
6. **Epoch marker.** One decision record node titled "Adopted Hypergraph"
   documenting the conversion (what was imported/authored, from where, what stayed
   on the archive). Parentage (SPEC: Adoption epochs): full-import mode A → parent =
   the **newest legacy node**; mode B → parent = the **newest prehistory node**
   (they resolve locally, and the CLI refuses a second parentless root per graph);
   epoch-split only → the marker becomes the record **root** of the local graph
   (`--root`, no other root exists locally) and records the archive lineage in its
   content, since local files cannot parent on slugs that don't resolve locally.

   **Mode B with several workstreams**: parent the marker on **every** prehistory tip,
   not just the newest. That makes the marker the single record tip, so one
   high-water mark covers the whole authored history instead of one branch of it.
   ```
   hypergraph adopt --marker <slug>        # records the epoch, refusing a slug that
                                           # does not resolve
   ```
   That `epoch:` block is what makes `check` exempt strictly-older nodes from I2.
   Then gitignore `.hypergraph/cache/` and advance the HWM — **see step 7 for what
   to advance it to; it is usually not the marker.**

   **Do not put state-graph statistics in the marker.** You are writing it before the
   state graph exists, so any "three broken, two blocked" is a guess, and record nodes
   are immutable — a wrong count can only be corrected by a child node. Describe what
   you imported or authored; leave the distillation to describe itself.
7. **Distillation → state graph.** The state skeleton must reflect what is *actually
   known*, not an empty template. **Re-read the interview answers before you start** —
   they were given in step 3, several steps of authoring ago, and working from memory
   of them is how a `broken` status quietly becomes `working`:
   - Architecture components from the repo + graph (3–8 nodes, init granularity).
   - **Per-branch mining**: walk the legacy graph / repo docs for current-status
     claims, key decisions, and dead ends. If the graph exceeds one context window,
     fan out subagent readers per branch and merge their briefs.
   - **Id-prefix→slug resolution**: docs citing raw node-id prefixes (e.g.
     `b3ea0b95`) must be mapped to slugs before you write provenance — never cite a
     prefix. `hypergraph adopt --resolve-prefixes --against <export.json>` does the
     mapping across every tracked doc and **reports ambiguity rather than guessing**;
     hex tokens matching no node (mostly git SHAs) are listed apart.
   - Dead ends land as **negative knowledge** with real evidence slugs (legacy slugs
     are valid — they resolve in the imported record graph; in mode B cite the
     prehistory/marker nodes).
   - Statuses honest: a claim the docs contradict is `broken`, unverified is `open`,
     don't default everything to `working`.
   - Route the interview's Part 2 answers: 1–2 become negative knowledge and `broken`
     statuses; 4 becomes `blocked`; 5 belongs in a decision record node, not the
     state graph.
   - Every claim cites resolvable slugs (legacy, prehistory, or marker). `check`
     enforces this, and a claim is a bullet **or a prose paragraph** — both are
     checked. **One slug per bracket**: `[rec: a] [rec: b]`, never `[rec: a, b]`,
     which the checker does not read as a citation at all.
   - **Advance the HWM to the record *tips*, not to the marker.** On a wide DAG the
     marker's ancestors are one branch, so marking it leaves everything else
     unreconciled — one adoption set it and found 111 nodes still outstanding. Run
     `hypergraph hwm --record <export> --state <export>`; `--suggest` prints the
     frontier to write. In the adoption you *are* the reconcile pass, so the write is
     `hypergraph update <state-root> --reconcile`, by hand, in the root's
     `## Reconciliation` block.
8. **Onboarding install.**
   - Append [agents-block.md](references/agents-block.md) to the repo's `AGENTS.md`
     (create the file if absent) — idempotently: if `<!-- hypergraph:begin -->` is
     already present, replace the existing block instead of appending a second one.
   - **Contract reconciliation**: when the existing AGENTS.md prescribes a
     conflicting discipline (e.g. "commit findings as <other system> nodes"), amend
     those sections to route through hypergraph — never leave two contradictory
     contracts standing.
     This is **two writes, not one**, and doing only the first is the common failure:
     1. The authoritative amendment goes **inside the sentinels**, woven into the
        numbered item it qualifies, alongside whatever else is project-specific (the
        epoch marker slug, the prehistory count).
     2. A short pointer goes **at the head of each conflicting section**, where a
        reader actually meets it. An amendment 300 lines away does not stop someone
        following the instructions in front of them. Never rewrite the author's prose
        — a dated one-line note above it is enough.

     `hypergraph upgrade` will not overwrite a block once you have edited it — it
     reports the block and steps back, naming the shipped template to merge against.
     Only a block still verbatim as we shipped it is refreshed automatically.
   - **Never break a CLAUDE.md→AGENTS.md symlink**: step 1's survey already reported
     whether either file is a link and where it points. Edit the *target*, never the
     link.
   - Write `.hypergraph/AGENTS.md`: the full onboarding — the four non-negotiables
     expanded, this project's graph roots and epoch, where the archive lives (mode
     A), the skills to use, and the check command verbatim.
   - **Install the skills, and make sure they can be committed.**
     ```
     hypergraph skills install            # into ./.claude/skills
     git check-ignore -v .claude/skills   # silence is what you want
     ```
     The block you just wrote says "run the `hypergraph-orient` skill". If the repo
     has no `.claude/skills`, or a broad ignore rule (`.*`, `.claude/`) hides it,
     every instruction you installed is dead on arrival for the next clone. Un-ignore
     it in the same commit that un-ignores `.hypergraph/`. Say in
     `.hypergraph/AGENTS.md` how to get the CLI too — it is a package, not a file, so
     it cannot travel with the repo: `uv tool install hypergraph-protocol`.

   Finally, before you commit: **`hypergraph sync`** — it exports, regenerates
   `STATE.md`, checks, and publishes if a mirror is configured, and it must **exit 0**.
   (`render` alone prints to stdout and does not write `STATE.md` unless you pass
   `-o`; `sync` is the gate.)

## The interview

Step 3, and prose on purpose: nothing here is a CLI verb, because CLI-generated
questions become CLI-generated answers become claims nobody derived. **One sitting,
two parts.** Ask the generic questions below *seeded with what the survey actually
reported* — name the directory births, the churn leaders, the contributors, the
tags. "What was `dashboard/` for, when it landed in February?" gets an answer;
"describe your project's eras" gets a shrug.

**Part 1 — History** (feeds the prehistory nodes, step 5):

1. Does the project split into eras? Here are the timeline signals — which of these
   boundaries are real, and what would you call each era?
2. What did the project set out to do, and how did that change?
3. What was the biggest architectural decision, and what were the alternatives you
   rejected?
4. What was built and later abandoned or ripped out?
5. What did you try that failed?
6. What kept forcing `<highest-churn file>` open, over and over?
7. What triggered each of these directory births — `<dir>` in `<month>`, …?
8. Who owned what? (the survey names the contributors)
9. What would you do differently if you started again?
10. What context exists only in your head, or in a PR thread nobody will read again?

**Part 2 — Current state** (feeds the distillation, step 7):

1. What did you try that didn't work, and would waste a fresh agent's day?
2. What in the docs is now false?
3. What is the most fragile part — what breaks when touched?
4. What is blocked on something outside this repo?
5. What are you deliberately *not* doing, and why?

Three rules:

- **A brain-dump substitutes for the questions.** If the author would rather write
  than be asked — a pasted message, a notes file, an old design doc — mine that
  first and then ask only what it left open. Someone who already has the context
  written down somewhere is the common case.
- **A declined interview is recorded, not hidden.** If the author skips it, say so in
  as many words: claims derived from repo evidence alone, no author input. In mode B
  that goes in the prehistory bodies; **in mode A there are no prehistory bodies, so
  it goes in the epoch marker and in `.hypergraph/AGENTS.md`.** Say what the gap
  costs, not just that it exists — intent is the part evidence cannot supply, so
  phrase those claims as claims about the evidence, or mark them `open`. Hand the
  author the questions it could not settle. An adoption that reads as author-informed
  when it was not breaks I8.
- **Answers are evidence, not prose to paste.** You still write the claims and you
  still cite. An interview answer is cited to the prehistory node that records it.

## Authoring nodes: four traps

Every one of these cost a real adoption a throwaway node or a hand-edit. None is
discoverable from the templates.

- **`## State Impact` comes from flags, never from the body.** A body containing that
  heading is refused (`--body already contains a '## State Impact' heading`). Use
  `--impact` once per line, or `--none "<reason>"`. The same is true of `## Current`
  on a state node.
- **`--impact` already writes `- target: `.** Pass `"<slug> — <delta>"`, *not*
  `"target: <slug> — <delta>"` — copying a line out of the template verbatim yields
  `- target: target: …` and an I2 violation.
- **You cannot choose a state node's slug.** They are minted `adjective-noun-####`;
  `--slug sim-substrate` is refused. So the readable `NEW <kebab-name>` target in an
  impact line never resolves to the node you then mint. Write the mapping down —
  kebab name → minted slug — in the node that declared them.
- **Record nodes are immutable.** `hypergraph update <record-slug>` refuses. A
  correction is a **new child node**, which is why you should not write a count you
  have not measured yet.

## Mode A, end to end

The order below is the one that works; §4 says why it is not the numbered one.

```bash
# 1. anchors. No repo writes them down as UUIDs — find them from the docs' own
#    description of the graph, then confirm every node slug the docs cite is
#    reachable from the root you picked. That reachability check is what proves it
#    is the only anchor.
flywheel nodes:get --node_id <root> --projection full

# 2. pull the legacy graph (this needs no config)
hypergraph mirror pull --record-node-id <root> --out-dir .hypergraph/cache
#    → legacy-record.json; a draft `archive:` block on stderr — keep it

# 3. import BEFORE init: --fork preserves node_ids, slugs and topology verbatim
hypergraph import --record .hypergraph/cache/legacy-record.json --fork \
                  --graph-dir .hypergraph/graph

# 4. now init — it adopts the imported root rather than minting a rival
hypergraph adopt --init          # expect: "record root: <slug> (adopted existing)"

# 5. paste the archive: block into the config, and say what stayed behind
#    (artifact counts, tag taxonomies — none of it travels)

# 6. marker on the newest legacy node, then the epoch
hypergraph new record --title "Adopted Hypergraph" --parent <newest-legacy-slug> \
                      --repo-auto --impact "..." --body marker.md
hypergraph adopt --marker <marker-slug>

# 7. distil, then set the HWM to the record tips (not the marker)
hypergraph adopt --resolve-prefixes --against .hypergraph/cache/legacy-record.json
hypergraph hwm --record <export> --state <export> --suggest

# 8. onboarding + skills, then the gate
hypergraph skills install && git check-ignore -v .claude/skills
hypergraph sync                  # must exit 0
```

**The archive is read-only for the whole of this.** Verify it afterwards if you want
the proof: its root's `revision` and `updated_at` must be unchanged.

## Guardrails

- The legacy graph is read-only throughout — the fork is the import; the archive is
  frozen. Never write, tag, or re-parent archive nodes.
- Record nodes at/after the marker follow full I2 discipline immediately — the epoch
  exempts only strictly-older history, and authoring is never exempted.
- Distilled claims must be derivable from cited nodes/docs (SPEC I8); when the
  source is ambiguous, say so in the claim rather than rounding up to certainty.
- Don't inflate the state graph: 3–8 components with honest statuses beat 20 nodes
  of aspiration. Negative knowledge is the highest-value cargo — mine for it.
- **The CLI computes facts; you write claims.** `--survey`, `--resolve-prefixes`,
  `--pull` and `--init` deliberately generate no prose: no prehistory bodies, no
  `## Current` text, no negative-knowledge entries. A claim nobody derived from
  evidence they read is not re-derivable, which breaks I8 by definition — and it is
  exactly the aspirational template-filling these guardrails exist to prevent.
- Mode A needs read access to the legacy graph. If `mirror pull` cannot reach it,
  authenticate first (`hypergraph mirror doctor` says what is wrong) — do not fall
  back to a repo-docs-only adoption of a graph-bearing project, which silently
  discards its memory.
