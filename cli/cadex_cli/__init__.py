# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""Cadex as a headless CLI — a third client of the cadexd protocol.

The Blender shell (``shell/``) is one client of ``cadex-cadexd-v1``; the
engine's own test harnesses are another. This package is the third: no
Blender, no display, no shell code, and no second copy of the protocol —
:mod:`cadex_cli.protocol` loads ``CadexdProtocol`` out of whichever engine
was resolved, so requests and responses are validated against the engine
under the CLI rather than against a restatement of it.

Licence boundary (``docs/PROVENANCE.md`` §1): everything here is engine-side
and therefore ``LGPL-2.1-or-later``. ``shell/**`` is ``GPL-2.0-or-later``,
so no line of the add-on may be copied into this tree. The precedents this
package derives from are all LGPL: ``cadexd_latency_integration.py`` (the
raw-NDJSON client and ``CADEX_ENGINE_ROOT`` resolution) and
``test_cadexd_lifecycle.py`` (ready banner, events vs responses, response
checking). See ADR-061.
"""

from __future__ import annotations

__all__ = ["CLI_SCHEMA", "__version__"]

#: The ``--json`` envelope's schema tag. Bump it when the envelope's shape
#: changes, so a pipeline can tell what it is parsing.
CLI_SCHEMA = "cadex-cli-v1"

__version__ = "0.0.1"
