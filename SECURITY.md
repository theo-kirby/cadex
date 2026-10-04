# Security Policy

Cadex is pre-release software under active development. It is three things —
an engine, a dashboard and an agent — and the engine is a fork of a much
larger project, so the first useful thing this document can do is tell you
**which project a given vulnerability belongs to** — and the second is
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
- The CLI, the agent bindings and the dashboard we wrote:
  `cli/cadex_cli/**`, including `cadex mcp`, the tool bridge and the review
  server.
- The cadexd protocol itself (`docs/INTEGRATION.md`) — anything that lets
  one side of the process boundary compromise the other.
- Packaging and the shipped bundle: `package/**`, the engine payload, and
  anything about how Cadex is built or installed.

**Out of scope — report upstream, where it can be fixed for everyone:**

- **Inherited FreeCAD code** (`src/App`, `src/Base`,
  `src/Mod/{Part,PartDesign,Sketcher,Assembly,Mesh,...}`) →
  <https://github.com/FreeCAD/FreeCAD/security/advisories/new>
- **OCCT, Python, three.js, MuJoCo and other dependencies** → their own
  projects.
- **The agent you connect to Cadex** (Claude Code, Codex or another) and
  its model provider → that agent's own project. For Claude Code and the
  Anthropic API: <https://www.anthropic.com/responsible-disclosure-policy>

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
CLI, the dashboard or `cadexd` itself. Source is first validated against an AST policy that blocks
`__import__`, `eval`, `exec`, `compile`, `breakpoint`, `globals` and related
names, rejects dunder access, NUL bytes, and unsafe project-relative paths,
and enforces size and syntax limits (`CadexScriptedRuntime.py`,
`CadexScriptedDomains.py`). It then runs in a windowless
`FreeCADCmd --safe-mode -c` subprocess, one per attempt
(`CadexScriptedProcess.py`), under timeout and memory bounds enforced by a
parent-side watchdog. The worker produces detached geometry and never
touches the live document; only a validated candidate is published.

**Cadex runs no agent; the agent's own permissions are its own.** The
person brings an agent and registers `cadex mcp --project DIR` with it
(ADR-538). That server speaks MCP over the stdin and stdout of the agent
that started it, opens no socket, serves only the enumerated tools in
`cli/cadex_cli/tools.py`, and refuses an unknown tool or method
(`cli/cadex_cli/mcp.py`). Its bridge is a plain object called in process
(`cli/cadex_cli/bridge.py`). Whatever else the agent can do on the machine
(its shell, its file access, running `cadex` commands) is granted by that
agent and its own permission system, not by Cadex. The boundary Cadex
enforces is the engine's sandbox above: whichever route a script arrives
by, it runs only in the worker.

**The dashboard is read-only and binds loopback by default.** `./cadex app`
and `./cadex review` bind `127.0.0.1` unless given `--host`
(`cli/cadex_cli/__main__.py`), and the server answers only `GET` and
`HEAD`; any other method is 501 (`cli/cadex_cli/review_server.py`,
ADR-537). Binding it
to another address exposes the project to whoever can reach that address;
reaching it from another device is meant to go through a private network
such as Tailscale in front of a loopback bind.

**No credentials pass through Cadex.** There are no API keys in the product;
authentication is your agent's, under your own login with it. See
[`PRIVACY_POLICY.md`](PRIVACY_POLICY.md).

**The engine and its clients are separate processes on purpose.** The
engine and the CLI communicate only over the NDJSON protocol in
`docs/INTEGRATION.md`, which is pinned by tests on both requests and
responses. Neither imports the other.

## Things that are working as designed

Report these if you can make them do something worse than described, but the
behavior itself is intentional:

- **A Cadex project *is* a program.** The script is the model, so opening a
  project from someone else means you are about to run their code. The
  sandbox above applies, but a sandbox is a mitigation and not a promise:
  **treat untrusted project files the way you would treat an untrusted
  script.**
- **The assistant can write and run geometry code without asking.** That is
  the product. The sandbox is what makes it acceptable; the sandbox is
  therefore where the interesting bugs are.
- **A project directory records how it was designed** — the script, its
  revision history, and the project's `ARCHITECTURE.md`, `DECISIONS.md`
  and `PROGRESS.md` (`PRIVACY_POLICY.md` §3). It is a disclosure risk
  when sharing a project, and a documented one.

## Dependencies

Cadex pins its build dependencies through pixi (`pixi.lock`); the offboard
`training/` and `analysis/` trees pin theirs in their own
`requirements.txt`. Vulnerabilities in those libraries are handled upstream;
if one needs a pin bumped here, an advisory or an issue is the way to say
so.

---

*This is Cadex's security policy. It is not FreeCAD's, and Cadex is not
endorsed by the FreeCAD project.*
