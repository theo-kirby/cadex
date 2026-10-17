# Operating Ouroboros in cadex

You are the operator. A human talks to you here, and you start, watch, read and
land unattended runs of this repo. This file is yours and the human's; Ouroboros
does not rewrite it. Keep it true.

## The shape of a run

A run is a loop of iterations against a charter. Each iteration has three roles, in order. The **actor** does one unit of work,
commits it and ends with a report. The **critic** reads the change and the memory,
accepts or rejects it, answers as the sleeping user would, and writes the message
the next iteration starts from. The **scribe** records the unit in the governor
graph (a rejected one as a dead end), folds the memory when a fold is due, renders
`STATE.md`, and keeps the run's page. Agents reach memory only through
`ouroboros mem`, and only the scribe writes it. There is no maintainer, planner or
plan layer any more (Ouroboros `a38d801`, 2026-10-17); `journal.md`, `plan.md` and
`handoff/` are gone with them. It
runs on a branch (`ouroboros/<run>`), as a systemd user unit
(`ouroboros-<run>.service`, `launcher: systemd`), for as long as the charter's
stop rules allow.

The human owns exactly one document: `.ouroboros/goal.md`, the charter. No agent
role may write it. Everything else -- the plan, the bets, the record -- is the
loop's.

## What you do, in order

**1. Before a run: read the last one.** `.ouroboros/RUNS.md` is the index and
`.ouroboros/history/<run>.md` is the digest. Read the notes below the marker
first: they are what a human concluded, and they are the only part not derivable
from the logs.

**2. Design or revise the charter.** Use the `ouroboros-design` skill, or edit
`.ouroboros/goal.md` directly. Two rules earn their place here:

- **A done criterion is a claim about the world that one run can make true.**
  A criterion nobody can tick is worse than no criterion: it looks like a target
  and behaves like scenery. If the index shows a run that ticked nothing, suspect
  the charter before you suspect the loop.
- **The horizon ladder is granularity, not time.** Agents have no clock. Never
  write hours, days or weeks in the charter.

**3. Pre-flight, then launch.**

    ouroboros preflight
    ouroboros run --for 24h

`run` refuses a dirty tree, so `git status` first -- untracked directories count.
Check the harnesses are authenticated and their usage windows have room; a
subscription window that is nearly full will stall the run rather than fail it.

`launcher: systemd` in `config.yml` puts the loop in a transient user unit,
`ouroboros-<run>.service`, started straight from your shell: no second session,
and no tmux or tern to keep alive. It belongs to no terminal, so restarting tern
(whose daemon lives inside the `tern-remote` service) or tmux cannot end it, and
lingering keeps it past logout. `memory_max: 40G` caps the run and everything it
starts, so a runaway engine is killed alone. Do not wrap `ouroboros run` in
`tmux`, `tern new` or `systemd-run` yourself: the launcher does that, and records
what it started so `ouroboros stop` takes it down. For a short run you want to
watch in a pane instead, pass `--launcher tern` (a tern session of its own,
`ouroboros-<run>`) or `--launcher tmux`. Tell the human to open
`ouroboros top` in a tab of their own, e.g. `tern new tab --cwd ~/cadex -- ouroboros top`.

**4. While it runs**, do not touch the files the loop is working in. An operator charter
edit applies at the next iteration boundary; the current actor and critic finish
under their original charter. Save edits atomically and check loop.log for
"charter reloaded". Config changes still require a restart. To watch:

    ouroboros refresh         # after switching accounts or restoring credits
    ouroboros status          # one shot
    ouroboros top             # the live view, in a window of its own
    ouroboros view            # serves runs/<run>/view/, the run's page the scribe keeps
    ouroboros mem orient      # the memory, as the roles see it
    journalctl --user -u ouroboros-<run>.service -f   # the loop's console log
    systemctl --user status ouroboros-<run>.service    # the unit, its memory and its processes

After switching a harness login or restoring credits, `ouroboros refresh`
(alias `ouroboros --refresh`) rechecks configured providers and wakes backoff.
Active turns finish first. It uses small no-tool availability probes; failed
probes retain cooldowns. This does not reload configuration.

The run's page replaces the hand-built `~/orunN-progress/site` pages of orun6
to orun8. Serve it on the tailnet for the owner: `ouroboros view` on a local
port, then `tailscale serve --bg --set-path /<run>/ http://127.0.0.1:<port>`.

**5. Reading it.** Use the `ouroboros-checkup` skill. It works mid-run and after,
and it leads with the question the numbers hide: is this moving, or going in
circles?

**6. Stopping and landing it.**

    ouroboros stop            # also writes the run's digest

Then merge with a merge commit -- **never squash a run whose memory cites commit
SHAs** -- and re-run `ouroboros archive` afterwards, because `merged:` is a fact
about the base branch and changes without the run changing.

## The record

| path | who writes it |
|---|---|
| `.ouroboros/goal.md` | the human, alone |
| `.ouroboros/RUNS.md` | generated by `ouroboros archive`; never hand-edit |
| `.ouroboros/history/<run>.md` | generated above the notes marker, **yours below it** |
| `.ouroboros/runs/<run>/` | the loop; gitignored, does not leave this machine |

The digests are the only part of a run that survives its machine, so commit them
with the merge. When a run teaches something -- a charter criterion that could
never close, a model that stalled, a config that wasted a window -- write it
under `## What this taught` in that run's digest. That is what the next
operator, including you, reads first.

## This project

- **Where runs happen:** the GPU box, `sb1x`, over Tailscale. It has the 5090,
  so it is the only machine where a run can train a policy and check the result.
  Work in `~/cadex` there; the run is a systemd user unit (above). nt1 to nt3 ran on the
  Mac (`mmini`) and could not train.
- **Naming:** `orun<n>`, from orun1 (2026-10-02). ot1 to ot11 were `ot<n>`,
  Ouroboros Test; nt1 to nt3 before them. Runs are not nights: one may start
  in the afternoon and go for two days, so never name one for a time of day.
- **Harnesses:** since ot9, `claude-opus-5-5` for every Ouroboros role
  (actor, critic, scribe, reporter) and product-agent call, with no fallback. See `.ouroboros/config.yml`. Verify
  product-model access and the usage window before launch; actor availability
  alone does not establish product access.
- **Green means** both suites, from `~/cadex`:

      pixi run test-engine                     # the engine, ~160 contract tests, ~30 s (ADR-725)
      pixi run python -m pytest cli/tests      # the CLI, ~50 contract tests, ~10 s

- **Pre-flight, learned the hard way:** `git status` must be clean *including
  untracked directories* -- an untracked `src/3rdParty/GSL/` blocked ot4's
  launch. Check `governor version` runs (memory is the governor graph, ADR-672).
  Confirm both harnesses are logged in. `~/ouroboros` tracks upstream `main`
  (the old local `reporter` branch is merged into it).
- **Never:** hand-edit `STATE.md` or `PLAN.md`; they are generated from the
  governor graph. `docs/ROADMAP.md` is hand-maintained: tick its checkboxes
  when a work item lands (AGENTS.md, Methodology 8). Never squash a run branch: records cite commit SHAs.
