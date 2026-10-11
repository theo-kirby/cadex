---
name: governor-record
description: Record a unit of work - a feature, fix, experiment, dead end or decision - as one append-only record in the project's governor graph, with its causal parent and its declared impact on state. Use after any meaningful unit of work in a project with a governor root. Never writes state.
---

# Record

Work that is not recorded did not happen, as far as the project's memory goes. A dead
end recorded is worth as much as a success.

1. **Pick the causal parent**: the record this work followed from, meaning the result
   that made you do it. Not simply the newest record. `governor orient` lists the recent
   ones, and the tail is usually where the parent is. A project's first record takes
   `root`.
2. **Pick the impact** on state, from the claims in `governor orient`:
   - an existing claim it changes: `--impact "<claim-slug>: <what is now different>"`;
   - a claim that does not exist yet: `--new "<kebab-name>: <what it should say>"`;
   - nothing in state changes: `--none "<why not>"`.
   Several `--impact`/`--new` flags are fine. The delta says what changed, not what you did.
3. **Write the body** to a file with exactly these sections:
   ```
   ## What      what was done or found, concretely
   ## Why       why this unit, and why this parent
   ## Method    how: commands, settings, what was measured
   ## Result    what is true now, numbers included; concerns for whoever is next
   ```
   Do not write `## Recorded` or `## State Impact`: governor generates both, with the
   git repo, branch, commit and time.
4. **Commit it**:
   ```
   governor record --title "<one line>" --body body.md --parent <slug> \
       --impact "<claim-slug>: <delta>"
   ```
   It prints the new slug. Exit 2 means nothing was written; the message says why.
   Delete the body file.

Records are immutable. A correction is a new record whose parent is the one it corrects.
Never fold, and never change a claim's status: that is the folder's job
(`governor-fold`). There is nothing to `git add`: the record is already committed to
the Flywheel repository.
