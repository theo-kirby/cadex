---
name: governor-fold
description: Fold the unfolded tail of records into the project's state - rewrite the claims they impact, set statuses, add citations, create the claims they ask for, and mark them folded - as the single writer of state. Use when `governor check` warns the tail is long, or when asked to reconcile or fold. Only one fold at a time, on the default branch.
---

# Fold

State is a small, honest distillation of what is true now. The fold is the only thing
that writes it, which is what keeps parallel agents from drifting it.

1. `governor fold` prints the tail: every unfolded record with its declared impacts,
   both `→ <claim>: <delta>` and `→ NEW <name>: <delta>`. For anything unclear, read the
   records themselves (`governor snapshot`, filtered).
2. For each claim the tail touches, write its new **whole** text:
   - `current`: what is true now, as short bullets, each ending with the record slugs it
     rests on, `[rec: slug]`. Merge what is redundant and drop what is superseded; the
     records keep the history.
   - `negative`: what was tried and does not work, and why. Keep it tight.
   - `status`: `working` (true and evidenced), `open` (not done), `broken` (was working,
     now is not), `blocked` (cannot move until something else does), or `superseded`
     (replaced; keep it for its history).
   - `cites`: every record the claim now rests on. Citations accumulate; list the new
     ones at least. Governor writes them into the claim's `## Evidence`, after keeping
     what it already cited, so do not write an evidence section yourself.
   A `NEW` impact becomes a new claim: give it a `new` name, a `title`, a `parent` (the
   component it belongs under, or `root` for a new component) and the same fields.
   Several records may impact one claim; write it once with all of them in mind.
   To group claims under a new component, add `{"new": "<name>", "title": "…",
   "component": true, "current": "- what it covers"}` (no status, parent the root) and
   parent the claims to its name. A rewrite that keeps a claim's status may leave out
   `cites` it already has.
3. Write the plan to a file and apply it:
   ```json
   {"claims": [
      {"slug": "steady-oak-1234", "status": "working",
       "current": "- … [rec: brave-owl-0001]", "negative": "- …",
       "cites": ["brave-owl-0001"]},
      {"new": "engine-speed", "parent": "grand-creek-1270", "title": "Engine speed",
       "status": "open", "current": "- not measured yet", "cites": []}],
    "folded": ["brave-owl-0001", "calm-fox-0002"]}
   ```
   `governor fold --apply plan.json` validates the whole plan first: every folded slug
   in the tail, every claim and citation real, and an evidenced status for every
   non-open claim. Then it writes everything in one commit under the fold lock.
   `folded` lists every tail record you applied, including the `none` ones.
4. `governor check` must exit 0. Then `governor render -o STATE.md` if the project
   keeps a rendered snapshot, and commit that file to git.

Report what was folded, what changed status, what was created, and anything you could
not fold cleanly: a contradictory delta, or an impact on a claim you think is wrong.
Report those. Do not guess at them.
