# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""Cadex as a headless CLI, and the dashboard it serves — a client of the
cadexd protocol.

The engine's own test harnesses are one client of ``cadex-cadexd-v1``. This
package is the other, and since the Blender shell was deleted (ADR-498) it
is the only front end: no display of its own, and no second copy of the
protocol —
:mod:`cadex_cli.protocol` loads ``CadexdProtocol`` out of whichever engine
was resolved, so requests and responses are validated against the engine
under the CLI rather than against a restatement of it.

Licence boundary (``docs/PROVENANCE.md`` §1): everything here is engine-side
and therefore ``LGPL-2.1-or-later``. The deleted shell was
``GPL-2.0-or-later``, and no line of it was ever copied into this tree,
including from the ``v1-blender-shell`` tag. The precedents this
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
