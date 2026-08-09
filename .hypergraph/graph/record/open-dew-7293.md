---
node_id: d2572a37-16b3-55a4-8893-d7eddaf38742
slug: open-dew-7293
title: 'Prehistory: making it work standalone — the quality-of-life era'
created_at: '2026-08-09T15:15:58+00:00'
parents:
- merry-eagle-4093
summary: 'The era after the merge: menus, real editor types, imported geometry, three defects no live test could see, and the latency work down to a 33 ms preview.'
---
## What

29 commits over two days, ADR-031…ADR-055. Not a phase — the era **after** the
merge, in which things that had worked in VibeCAD or in Blender did not yet work
in Cadex, and two newly joined halves had to be made to behave like one
application.

## Why

Follows the merge. In the author's words: "now that they are together and the
merge has landed, how does this system work compared to how it used to work?"

## Method and Result, grouped by what each fixed

**The application became something a user meets.** The File menu came back, as
ours (ADR-041); no splash screen (ADR-042); chat and Parameters became real
Blender **editors** rather than abused area types (ADR-035) — which is what made
the layout a saved `.blend` instead of a 340-line Python template (ADR-037),
because a saved screen can record area types and until then the area types were
lying. An editor Cadex does not build is not offered (ADR-036). The input got a
strip of its own and Return sends (ADR-034).

**External geometry became a first-class input** (ADR-043). Phase 4 had shipped
an ingest path nothing could reach: no product surface wrote `assets/`, an
import could not be moved, could not enter the BREP domains, and could only be
measured on the rebuild that produced it. Four changes closed it — the
`put_asset` op plus File → Import Geometry…, `mesh.transform`, `inspect
scope="output"`/`"assets"`, and `part.shape_from_mesh`. Which promptly broke
Save-As, because the new project got no `assets/` and the first
`mesh.import_file` died (ADR-046).

**Three defects were invisible because no live test built a joint** (ADR-047,
ADR-048, ADR-049): joints failed headless, simulations could not publish, and a
solved assembly never reached the viewport because nothing in the response said
which output a component instanced. A simulation has played in the viewport
since ADR-050.

**Safety of the script store.** A refused script must not be able to shut the
project (ADR-044), and the script gained a history so `write_script` cannot
silently delete a model (ADR-045).

**Then the latency work.** The drag left the main thread (ADR-051); the
cold-path diet and shared sub-expressions took the engine median 0.505 s →
0.417 s (ADR-052, ADR-053); and the **warm-standby preview worker** (ADR-055)
answers a pose-only parameter change in **33 ms** against the same model's
0.588 s accepting run — a read-only oracle that writes nothing at all, with the
invariant asserted over the store's full file list, sizes and mtimes across a
burst of previews. Its stated limit is real: a preview cannot serve a parameter
that changes a *definition*, so the headline applies to a subset of sliders.

## Result

Most of the product's felt quality came from this era, and almost none of it was
planned in a phase. The pattern that repeats — and that later eras repeat again
— is that a capability shipped in an earlier phase turns out to have no
reachable product surface, and closing that gap breaks a second thing the first
was never written for.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: main
- commit: 41e6aa6ceeed3078210e02c1f94d85bd715fbb9d

## State Impact

- target: NEW shell — the shell is a real application: Cadex File/Edit menus, real editor types, a saved-layout startup file, imported geometry, and a simulation that plays.
- target: NEW engine — the preview/accept split: 33 ms pose-only previews against a ~0.42 s accepting path.
