# cadex-nt3-i19-carriage — Decisions

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

## ADR-002 — Comparable review evidence (2026-09-08)

Keep the exact two-mechanism measurements in PROGRESS.md, with separate timing
boundaries and effort units. Script import carries code only; the reviewing
agent carries existing example sensor notes. Preserve initial contact and
unknown counts rather than treating policy acceptance as a safety claim.
