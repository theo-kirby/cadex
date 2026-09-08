# hinged-arm — Decisions

One entry per decision that shaped the model or its training: what was
chosen, what it was chosen over, and why. Newest last. A `cadex -p` turn
that ends with a line starting `DECISION:` lands here as the next entry.

## ADR-001 — Project scaffolded (2026-09-08)

Created by the `cadex` CLI on first visit, with `ARCHITECTURE.md` and
`PROGRESS.md` beside it, and a git repository the project owns: the CLI
commits after every accepted run. `.gitignore` keeps out what a rebuild
recreates (`script_artifacts/`), what is bulk (`frames/`, renders) and
what is transient (the lock, `.blend1` backups); the script, its history,
the stored assets and these documents are the project.

## ADR-002 — Cold revisit evidence

Keep existing example sensor notes as domain documentation after script-only import. Preserve baseline review evidence and record public cold-revisit results in PROGRESS.md. Normalize local project paths to <project> in report prose. Runtime cache restaging is expected; unchanged policy assets, accepted identity and actual review geometry determine persistence success.
