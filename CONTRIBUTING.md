# Contributing to Cadex

Verified against source: 2026-08-29

Cadex is an experimental side project (see the author's note in
`README.md`). Contributions are welcome, and the bar for them is the same
bar the repository holds itself to: small, coherent, owner-mergeable
changes, verified by running the suites.

This file replaces the FreeCAD contribution process the fork inherited.
That document described FreeCAD's maintainer structure, forum routes and
copyright-assignment option, none of which exist here; keeping it verbatim
was the same class of error ADR-031 fixed for `SECURITY.md`.

## Process

1. Read `AGENTS.md` — the repo map, the commands, and the change policy.
   It is the contract this repository actually enforces.
2. One logical change per pull request. State the user-visible outcome,
   the risk, and the test evidence in the description.
3. Verify by running: `pixi run test-engine` for engine changes,
   `pixi run gate` for shell changes, `pixi run python -m pytest cli/tests`
   for CLI changes. Report failures honestly, with output.
4. Removals are normal work here — the philosophy is *remove more than we
   add* — but every removal gets a `docs/DECISIONS.md` entry and is proven
   by build + tests in the same PR.

## Licensing, ownership and credit

1. The engine side of this repository (everything outside `shell/`) is
   distributed under the GNU Lesser General Public License, version 2.1 or
   later — see `LICENSE`. The shell (`shell/`) is under the GNU General
   Public License, version 2 or later — see `shell/COPYING`. The boundary
   between them is one-way and hard: `docs/PROVENANCE.md` §7.
2. Contributions must be under a compatible license, and new files must
   carry an `SPDX-License-Identifier` for the side of the boundary they
   land on, plus `SPDX-FileCopyrightText: 2026 Cadex Authors`.
3. Contributors keep the copyright in their contributions. There is no
   copyright assignment, mandatory or optional.
4. Changes to inherited FreeCAD or Blender files must keep the upstream
   license headers intact and carry the per-file modification notice —
   `tools/apply_modification_notices.py --check` and the licensing
   compliance suite enforce this.
5. You are responsible for reasonable assurance that your contribution
   does not infringe third-party copyrights or license terms. Code of
   unknown origin does not land — that includes assets.
