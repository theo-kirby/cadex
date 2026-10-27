# XSCRIPT history — direction notes and the multi-program era

> **Historical (moved out of `docs/XSCRIPT.md` 2026-10-27, ADR-828).** These
> are `docs/XSCRIPT.md`'s former Part II ("Direction") and "Historical note"
> as they stood on 2026-10-19. Not maintained; `docs/XSCRIPT.md` Part II
> says what is true now.

## Part II — Direction (as of 2026-10-19)

- **Incremental re-execution**: today every mutation re-runs the whole
  script (one worker attempt). Cached per-region revisions keyed by content
  hash are a possible optimization; the revision machinery points the way.
- ~~**Sub-modules**: whether large projects split into importable sub-modules
  under the project root, or stay one flat script.~~ **Answered (ADR-138):
  one flat script, and a project composes another through its *store*.**
  `link_part` pulls one accepted solid out of another project into this one's
  `assets/` as a `.cxpart`, and `part.import_part("sensor.cxpart")` reads it
  back as the exact OCCT solid — same path an imported STL travels, lossless
  instead of tessellated. So a large project splits into *projects*, each one
  flat, each rebuildable on its own, joined by content-addressed files rather
  than by an import graph. What crosses the boundary is a built artifact
  whose bytes are checked, not a program this project has to run; the AST
  policy's blanket refusal of `import` stays exactly as it is, and turns out
  to have been the right answer rather than a limitation to route around.
- **Interactive mesh editing**: still unscheduled, and still a decision
  rather than an oversight. The plan used to be that it would arrive via
  BMesh in the Blender shell. It did not, and the route closed: ADR-030
  deleted the local bpy modes, and ADR-498 the shell itself. Editing a mesh interactively
  would now mean either a new engine op or re-opening a second authoring
  path — and the second is a direct contradiction of "nothing happens
  outside the script".

  What this paragraph used to also say — that the `mesh` domain is
  deliberately minimal and *stays* that way — is **superseded by ADR-043**.
  The charter it stated was a *modelling* one, and it held; what it
  incidentally froze was the *ingest* path, which was not a decision anyone
  made. External geometry is now a first-class input: `put_asset` gets a
  file into the store, `mesh.transform` places it, `part.shape_from_mesh`
  takes it into the BREP domains, and `inspect scope="output"` measures the
  result. None of that is interactive mesh editing, and the "nothing happens
  outside the script" rule is untouched — the script still names every
  operation; the asset store is an input to it, the way a parameter value
  is.

---

## Historical note

The VibeCAD-era per-domain multi-program surface (eight lifecycle
operations × four domains, program manifests `cadex-xscript-program-v2`)
was dissolved by the Phase 2.4 tool-surface swap (ADR-013); existing v2
program stores were not migrated (ADR-011 — conversations preserved,
scripts start empty). The verification record for the still-earlier
multi-engine runtime is preserved at
`docs/history/RUNTIME_VERIFICATION.md`. Of its still-current facts, the
failure envelope's shape is pinned by `test_response_schemas.py`; the rest
are verified by running the engine (ADR-725).
