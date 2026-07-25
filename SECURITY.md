# Security Policy

Cadex is pre-release software under active development. It is a fork of two
much larger projects, so the first useful thing this document can do is tell
you **which project a given vulnerability belongs to** — and the second is
describe the trust boundaries Cadex actually relies on, so you know what
counts as a bug.

## Reporting a vulnerability

Report privately, through GitHub's security advisory tool:

**<https://github.com/theo-kirby/cadex/security/advisories/new>**

Please do not open a public issue for a security problem. Include what you
did, what happened, and — if you have one — a minimal reproduction. A commit
hash helps; this project has no release series yet.

Expect a first response within a week. Cadex is maintained by one person on
a pre-release codebase: there is no security team, no SLA, and no bounty
program. Reports held hostage for payment will not be entertained.

## Scope

**In scope — report to us:**

- The engine we wrote: `src/Mod/cadex/**`, including the xscript sandbox,
  the `cadexd` service, and the worker isolation described below.
- The shell add-on we wrote: `shell/scripts/addons_core/mesh_agent/**`,
  including the tool bridge and the Claude Code integration.
- The cadexd protocol itself (`docs/INTEGRATION.md`) — anything that lets
  one side of the process boundary compromise the other.
- Packaging and the shipped bundle: `package/**`, the engine payload, and
  anything about how Cadex is built or installed.

**Out of scope — report upstream, where it can be fixed for everyone:**

- **Inherited FreeCAD code** (`src/App`, `src/Base`, `src/Gui`,
  `src/Mod/{Part,PartDesign,Sketcher,Assembly,Mesh,...}`) →
  <https://github.com/FreeCAD/FreeCAD/security/advisories/new>
- **Inherited Blender code** (everything under `shell/` except
  `mesh_agent/`) → <https://projects.blender.org/blender/blender> (see
  Blender's own security policy)
- **OCCT, Qt, Python, and other dependencies** → their own projects.
- **The Claude Code CLI or the Anthropic API** →
  <https://www.anthropic.com/responsible-disclosure-policy>

If a vulnerability is inherited but Cadex's use of it makes the impact
materially worse, tell us too — that combination is ours.

[`docs/PROVENANCE.md`](docs/PROVENANCE.md) has the full map of which code
came from where.

## Supported versions

None yet, in the usual sense. Cadex has made no release; `main` is the only
supported branch and fixes land there. There is no backport policy because
there is nothing to backport to.

## The security model

These are the boundaries Cadex is designed around. A way past any of them is
a vulnerability worth reporting.

**AI-authored code runs in a sandbox, not in the application.** The
assistant writes an xscript program; that program never executes in the
shell process. Source is first validated against an AST policy that blocks
`__import__`, `eval`, `exec`, `compile`, `breakpoint`, `globals` and related
names, rejects dunder access, NUL bytes, and unsafe project-relative paths,
and enforces size and syntax limits (`CadexScriptedRuntime.py`,
`CadexScriptedDomains.py`). It then runs in a windowless
`FreeCADCmd --safe-mode -c` subprocess, one per attempt
(`CadexScriptedProcess.py`), under timeout and memory bounds enforced by a
parent-side watchdog. The worker produces detached geometry and never
touches the live document; only a validated candidate is published.

**The assistant's tools are the only surface it gets.** Claude Code is
launched with its built-in tools disabled (`--tools ""`) and with
`--strict-mcp-config`, allowed to call only the `mcp__mesh__*` tools Cadex
defines (`mesh_agent/backend.py`). It has no shell, no filesystem access,
and no route into Blender except through that list.

**The tool bridge is loopback-only and authenticated per session.** It binds
`127.0.0.1` on an ephemeral port and rejects any request whose token does
not match a `secrets.token_hex(16)` value generated for that session
(`mesh_agent/bridge.py`). The token is never written anywhere but the
per-session MCP config in a temporary directory.

**No credentials pass through Cadex.** There are no API keys in the product;
authentication is Claude Code's, under the user's own login. See
[`PRIVACY_POLICY.md`](PRIVACY_POLICY.md).

**The two halves are separate processes on purpose.** The engine and the
shell communicate only over the NDJSON protocol in `docs/INTEGRATION.md`,
which is pinned by tests on both requests and responses. Neither imports the
other.

## Things that are working as designed

Report these if you can make them do something worse than described, but the
behavior itself is intentional:

- **A Cadex project *is* a program.** The script is the model, so opening a
  project from someone else means you are about to run their code. The
  sandbox above applies, but a sandbox is a mitigation and not a promise:
  **treat untrusted project files the way you would treat an untrusted
  script.**
- **`.blend` files can carry Python.** This build sets
  `WITH_PYTHON_SECURITY=ON` (`shell/CMakeLists.txt`), so Blender does not
  auto-run embedded scripts by default. If you turn that off, you own the
  consequences.
- **The assistant can write and run geometry code without asking.** That is
  the product. The sandbox is what makes it acceptable; the sandbox is
  therefore where the interesting bugs are.
- **A `.blend` stores its own chat transcript** (`PRIVACY_POLICY.md` §3). It
  is a disclosure risk when sharing files, and a documented one.

## Dependencies

Cadex pins its build dependencies through pixi (`pixi.lock`) and consumes
Blender's prebuilt library sets as submodules
(`shell/lib/<platform>`, from `projects.blender.org`). Vulnerabilities in
those libraries are handled upstream; if one needs a pin bumped here, an
advisory or an issue is the way to say so.

---

*This is Cadex's security policy. It is not FreeCAD's or Blender's, and
Cadex is endorsed by neither project.*
