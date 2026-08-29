# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""Connections as a declared table: ``nets(...)`` and ``wire(...)`` (ADR-065).

``part.terminals`` gave a connection two named ends (ADR-062) and
``part.cable``/``part.bundle``/``part.solder`` gave it geometry (ADR-056,
ADR-057, ADR-063).  What none of them gave it is an *address*.  A harness
written today is a list comprehension over literal pairs::

    links = [(sen_t["s0"], esp_t["e0"], [sensor_board, esp32_board]), ...]
    wires = [part.cable(a, b, gauge_mm=WG, avoid=obs) for a, b, obs in links]

That builds correctly and cannot be edited by anything but the AI, because
nothing outside the script text names the row.  Changing what connects to
what costs a chat turn.

``nets()`` formalises exactly that comprehension and gives it the standing
``params()`` has: **a declaration in the script whose current values live
outside it**.  A port is a named ``TerminalSet``; a wire is a named row
addressing two of their terminals::

    n = nets(
        ports={"sen": sen_t, "esp": esp_t},
        wires={"s0_e0": wire("sen.s0", "esp.e0", gauge=WG, solder=True,
                             avoid=[sensor_board, esp32_board])},
    )

    for name, w in n.items():
        if not w.enabled:
            continue
        result["wire_" + name] = part.cable(w.a, w.b, gauge_mm=w.gauge,
                                            avoid=w.avoid)

``w.a`` and ``w.b`` are real :class:`~CadexTerminals.Terminal` objects, so
the three harness operations are untouched and a script converted to
``nets()`` builds byte-identically to the comprehension it replaces.

Three properties carry the module.

**The table carries exactly what the editor can edit.**  Overridable:
``a``, ``b``, ``gauge``, ``solder``, ``enabled``.  Declaration-only:
``avoid``, ``label``, and every other argument the script computes.  A pad
diameter per joint or a bundle's lay stays in the script, where it already
lives — the alternative is a second place to look for one value, and then a
rule about which place wins.

**An endpoint is ``"<port>.<terminal>"``.**  Human-readable, JSON-safe, and
validated at declaration against the actual ``TerminalSet``s, so a typo is a
refusal and not a silent miswire.  Port names are lower_snake_case and carry
no dot, so the split is on the *first* dot and terminal names may contain
as many more as they like.

**Stored overrides are a full row list, not a patch.**  That is what lets
the editor add and delete wires, and it makes the declared table a *default*
in exactly the sense ``num()``'s default is one.

Like ``CadexRouting``, ``CadexBundle``, ``CadexTerminals`` and
``CadexSolder``, this module imports nothing from FreeCAD and touches no
kernel object.  ``avoid`` is carried through opaquely; nothing here looks
inside it.

One spelling note, because both surfaces are named in ADR-065: the Python
keyword is ``wire(gauge=...)`` and the value object reads ``w.gauge``, while
the JSON row spells it ``gauge_mm`` like every other millimetre field the
engine serialises.  The two never meet — one is a script vocabulary, the
other a wire format.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
import re
from typing import Any, Iterator, Mapping, Sequence

__all__ = [
    "MAX_NETS",
    "NetError",
    "NetsCollector",
    "NetValues",
    "WireValue",
    "canonical_rows",
    "declared_ports",
    "effective_rows",
    "prune_rows",
    "wire",
]

#: One script's connection count.  ``MAX_TERMINALS`` bounds a component's
#: terminals at 256; a harness that wires more rows than one component can
#: terminate is a script that meant something else.
MAX_NETS = 256

#: Port and wire names, the same rule ``params()`` applies to parameters.
_NET_NAME = re.compile(r"^[a-z_][a-z0-9_]{0,63}$")

#: What ``wire()`` returns, so ``nets()`` can tell a declaration from a dict
#: that merely looks like one.  Same idiom as ``num()``'s spec marker.
_WIRE_MARKER = "cadex-project-wire-spec"

#: The row fields the editor may write, and their order in canonical JSON.
OVERRIDE_FIELDS = ("name", "a", "b", "gauge_mm", "solder", "enabled")


class NetError(ValueError):
    """A connection table that could not be stated, or could not be applied."""


# ---------------------------------------------------------------------------
# declaration


def _finite(value: Any, *, what: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise NetError(f"{what} must be a number; received {value!r}")
    result = float(value)
    if not math.isfinite(result):
        raise NetError(f"{what} must be finite; received {value!r}")
    return result


def _endpoint(value: Any, *, what: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise NetError(
            f"{what} must be a '<port>.<terminal>' string naming one end of "
            f"the connection; received {value!r}"
        )
    clean = value.strip()
    port, separator, terminal = clean.partition(".")
    if not separator or not port or not terminal:
        raise NetError(
            f"{what} must be '<port>.<terminal>', e.g. 'esp.sda'; received "
            f"{value!r}"
        )
    if not _NET_NAME.fullmatch(port):
        raise NetError(
            f"{what} names port {port!r}, which is not lower_snake_case; the "
            "port names are the keys of nets(ports=...)"
        )
    if len(clean) > 160:
        raise NetError(f"{what} must be at most 160 characters; received {value!r}")
    return clean


def _split_endpoint(address: str) -> tuple[str, str]:
    port, _separator, terminal = address.partition(".")
    return port, terminal


def wire(
    a: Any,
    b: Any,
    *,
    gauge: float,
    solder: bool = False,
    enabled: bool = True,
    avoid: Sequence[Any] = (),
    label: str = "",
) -> dict[str, Any]:
    """Declare one connection between two terminals.

    Usage inside a project script::

        n = nets(ports={"sen": sen_t, "esp": esp_t},
                 wires={"s0_e0": wire("sen.s0", "esp.e0", gauge=0.8)})

    ``a``/``b``/``gauge``/``solder``/``enabled`` are the table's editable
    columns.  ``avoid`` and ``label`` are declaration-only: they are carried
    to the value object unchanged and never appear in a stored override.
    """

    spec: dict[str, Any] = {
        "kind": _WIRE_MARKER,
        "a": _endpoint(a, what="wire() a"),
        "b": _endpoint(b, what="wire() b"),
        "gauge_mm": _finite(gauge, what="wire() gauge"),
    }
    if spec["gauge_mm"] <= 0.0:
        raise NetError(
            f"wire() gauge must be greater than zero; received {gauge!r}"
        )
    if spec["a"] == spec["b"]:
        raise NetError(
            f"wire() connects {spec['a']!r} to itself; the two ends of a wire "
            "must be different terminals"
        )
    if not isinstance(solder, bool):
        raise NetError(f"wire() solder must be True or False; received {solder!r}")
    if not isinstance(enabled, bool):
        raise NetError(f"wire() enabled must be True or False; received {enabled!r}")
    if isinstance(avoid, (str, bytes)) or not isinstance(avoid, (list, tuple)):
        raise NetError(
            "wire() avoid must be a list of obstacles, exactly as part.cable "
            f"takes; received {avoid!r}"
        )
    if not isinstance(label, str) or len(label) > 80:
        raise NetError("wire() label must be a string of at most 80 characters")
    spec["solder"] = bool(solder)
    spec["enabled"] = bool(enabled)
    spec["avoid"] = tuple(avoid)
    spec["label"] = str(label)
    return spec


# ---------------------------------------------------------------------------
# rows: the canonical JSON a declaration and an override share


def canonical_rows(rows: Any, *, what: str) -> list[dict[str, Any]]:
    """Validate a full row list into canonical JSON, or refuse it.

    Shared by the declared table, the stored overrides and the host-side
    ``set_params(nets=...)`` check, so all three agree on what a row is.
    """

    if not isinstance(rows, (list, tuple)):
        raise NetError(
            f"{what} must be a list of connection rows; received {rows!r}"
        )
    if len(rows) > MAX_NETS:
        raise NetError(
            f"{what} holds {len(rows)} rows; a project declares at most "
            f"{MAX_NETS}"
        )
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, row in enumerate(rows):
        if not isinstance(row, Mapping):
            raise NetError(f"{what}[{index}] must be an object; received {row!r}")
        unknown = sorted(set(map(str, row)) - set(OVERRIDE_FIELDS))
        if unknown:
            raise NetError(
                f"{what}[{index}] has unrecognised keys {unknown}; a row "
                f"carries {list(OVERRIDE_FIELDS)}. avoid and label are "
                "declaration-only and stay in the script"
            )
        name = str(row.get("name") or "")
        if not _NET_NAME.fullmatch(name):
            raise NetError(
                f"{what}[{index}] name {name!r} must be lower_snake_case "
                "(max 64 chars)"
            )
        if name in seen:
            raise NetError(
                f"{what}[{index}] repeats the row name {name!r}; a row is "
                "looked up by name, so the names in one table must be distinct"
            )
        seen.add(name)
        entry = {
            "name": name,
            "a": _endpoint(row.get("a"), what=f"{what}[{index}].a"),
            "b": _endpoint(row.get("b"), what=f"{what}[{index}].b"),
            "gauge_mm": _finite(row.get("gauge_mm"), what=f"{what}[{index}].gauge_mm"),
        }
        if entry["gauge_mm"] <= 0.0:
            raise NetError(
                f"{what}[{index}].gauge_mm must be greater than zero; received "
                f"{row.get('gauge_mm')!r}"
            )
        if entry["a"] == entry["b"]:
            raise NetError(
                f"{what}[{index}] connects {entry['a']!r} to itself; the two "
                "ends of a wire must be different terminals"
            )
        for flag in ("solder", "enabled"):
            value = row.get(flag, True if flag == "enabled" else False)
            if not isinstance(value, bool):
                raise NetError(
                    f"{what}[{index}].{flag} must be true or false; received "
                    f"{value!r}"
                )
            entry[flag] = bool(value)
        result.append(entry)
    return result


def declared_ports(specs: Mapping[str, Any] | None) -> dict[str, list[str]]:
    """``{port name: [terminal names]}`` from a stored ``net_specs`` block."""

    ports: dict[str, list[str]] = {}
    for entry in list((specs or {}).get("ports") or []):
        if not isinstance(entry, Mapping):
            continue
        name = str(entry.get("name") or "")
        if name:
            ports[name] = [str(item) for item in list(entry.get("terminals") or [])]
    return ports


def prune_rows(
    rows: Sequence[Mapping[str, Any]], ports: Mapping[str, Sequence[str]]
) -> list[dict[str, Any]]:
    """Drop rows whose endpoints the script no longer declares (ADR-039).

    A stored row is not a caller error the way a bad request is: it is what a
    rewritten script leaves behind.  Raising on it would wedge the editor
    forever the moment the AI renamed a port — the same failure ADR-039
    recorded for parameters, with the same fix.
    """

    kept: list[dict[str, Any]] = []
    for row in rows:
        addresses = (str(row.get("a") or ""), str(row.get("b") or ""))
        if all(
            _split_endpoint(address)[0] in ports
            and _split_endpoint(address)[1]
            in list(ports[_split_endpoint(address)[0]])
            for address in addresses
        ):
            kept.append(dict(row))
    return kept


def effective_rows(
    specs: Mapping[str, Any] | None, values: Any
) -> list[dict[str, Any]]:
    """The table as built: stored overrides when there are any, else declared.

    A **full row list**, never a patch — that is what lets the editor add and
    delete wires rather than only retune the rows the script happened to
    write.  An empty override list therefore means "no overrides", not "no
    wires"; deleting the last wire is expressed by disabling it.
    """

    declared = [dict(row) for row in list((specs or {}).get("wires") or [])]
    if not values:
        return declared
    ports = declared_ports(specs)
    return prune_rows(canonical_rows(values, what="net values"), ports)


# ---------------------------------------------------------------------------
# what a script holds


@dataclass(frozen=True)
class WireValue:
    """One effective connection, with its two ends already resolved.

    ``a``/``b`` are Terminals, which is what ``part.cable`` and
    ``part.solder`` take.  ``a_address``/``b_address`` are the same two ends
    as the ``"<board>.<terminal>"`` strings the stored row already carried,
    and they exist because a script cannot otherwise **size** a joint: a
    declared pad carries no area, so ``part.solder`` requires ``pad_dia_mm``
    there, and the right diameter is a property of the board — an RF bore at
    2.54 mm pitch and a camera's 0.5 mm pads want very different numbers. A
    Terminal knows its own name but not which port addressed it, so without
    these the loop that builds one joint per soldered end has nothing to key
    a per-board table on (ADR-122).

    Additive: no stored row changes shape, and a script that does not read
    them hashes exactly as it did.
    """

    name: str
    a: Any
    b: Any
    gauge: float
    solder: bool
    enabled: bool
    avoid: tuple[Any, ...] = ()
    label: str = ""
    #: ``"<port>.<terminal>"`` for each end, verbatim from the effective row.
    a_address: str = ""
    b_address: str = ""

    def __repr__(self) -> str:  # pragma: no cover - diagnostics only
        return f"WireValue({self.name!r}, gauge={self.gauge!r})"


class NetValues:
    """Ordered, immutable view of the effective connection table."""

    __slots__ = ("_ports", "_wires")

    def __init__(
        self, ports: Mapping[str, Any], wires: Sequence[WireValue]
    ) -> None:
        object.__setattr__(self, "_ports", dict(ports))
        object.__setattr__(self, "_wires", tuple(wires))

    @property
    def ports(self) -> dict[str, Any]:
        return dict(self._ports)

    def items(self) -> tuple[tuple[str, WireValue], ...]:
        return tuple((entry.name, entry) for entry in self._wires)

    def values(self) -> tuple[WireValue, ...]:
        return self._wires

    def names(self) -> tuple[str, ...]:
        return tuple(entry.name for entry in self._wires)

    def enabled(self) -> tuple[WireValue, ...]:
        """The rows a rebuild actually builds — the common loop, spelled once."""

        return tuple(entry for entry in self._wires if entry.enabled)

    def __len__(self) -> int:
        return len(self._wires)

    def __iter__(self) -> Iterator[WireValue]:
        return iter(self._wires)

    def __contains__(self, name: Any) -> bool:
        return any(entry.name == str(name) for entry in self._wires)

    def __getitem__(self, name: Any) -> WireValue:
        clean = str(name)
        for entry in self._wires:
            if entry.name == clean:
                return entry
        raise NetError(
            f"this script declares no connection named {clean!r}; it declares "
            f"{[entry.name for entry in self._wires]}"
        )

    def __setattr__(self, _name: str, _value: Any) -> None:
        raise TypeError("The connection table is immutable inside the script.")

    def __repr__(self) -> str:  # pragma: no cover - diagnostics only
        return f"NetValues({[entry.name for entry in self._wires]!r})"


class NetsCollector:
    """The ``nets(...)`` callable: collects specs, applies stored rows.

    The exact shape of :class:`~cadex_project_api.ParamsCollector`, because a
    connection and a slider are the same kind of thing: a control the script
    declares and something outside it currently sets.
    """

    def __init__(self, overrides: Any = None) -> None:
        self.overrides = overrides
        self.specs: dict[str, Any] = {}
        self.ports: list[tuple[str, Any]] = []
        self._called = False

    def __call__(self, *, ports: Any, wires: Any) -> NetValues:
        if self._called:
            raise NetError("nets(...) may be called at most once per script.")
        self._called = True
        clean_ports = self._clean_ports(ports)
        declared = self._clean_wires(wires, clean_ports)
        self.specs = {
            "ports": [
                {"name": name, "terminals": list(terminal_set.names)}
                for name, terminal_set in self.ports
            ],
            "wires": [
                {key: row[key] for key in OVERRIDE_FIELDS} for row in declared
            ],
        }
        rows = effective_rows(self.specs, self.overrides)
        extras = {row["name"]: row for row in declared}
        wire_values: list[WireValue] = []
        for row in rows:
            spec = extras.get(row["name"], {})
            wire_values.append(
                WireValue(
                    name=row["name"],
                    a=self._terminal(clean_ports, row["a"], row["name"]),
                    b=self._terminal(clean_ports, row["b"], row["name"]),
                    gauge=float(row["gauge_mm"]),
                    solder=bool(row["solder"]),
                    enabled=bool(row["enabled"]),
                    avoid=tuple(spec.get("avoid") or ()),
                    label=str(spec.get("label") or ""),
                    a_address=str(row["a"]),
                    b_address=str(row["b"]),
                )
            )
        return NetValues(clean_ports, wire_values)

    # -- helpers ----------------------------------------------------------

    def _clean_ports(self, ports: Any) -> dict[str, Any]:
        if not isinstance(ports, Mapping) or not ports:
            raise NetError(
                "nets(ports=...) expects a non-empty mapping of port name to "
                "the TerminalSet part.terminals/mesh.terminals returned; "
                f"received {ports!r}"
            )
        clean: dict[str, Any] = {}
        for name, terminal_set in ports.items():
            clean_name = str(name)
            if not _NET_NAME.fullmatch(clean_name):
                raise NetError(
                    f"port name {clean_name!r} must be lower_snake_case (max "
                    "64 chars); it is half of every endpoint address"
                )
            if not hasattr(terminal_set, "names") or not hasattr(
                terminal_set, "component"
            ):
                raise NetError(
                    f"nets(ports=...) entry {clean_name!r} must be the "
                    "TerminalSet part.terminals/mesh.terminals returned; "
                    f"received {terminal_set!r}"
                )
            clean[clean_name] = terminal_set
            self.ports.append((clean_name, terminal_set))
        return clean

    def _clean_wires(
        self, wires: Any, ports: Mapping[str, Any]
    ) -> list[dict[str, Any]]:
        if not isinstance(wires, Mapping):
            raise NetError(
                "nets(wires=...) expects a mapping of row name to wire(...); "
                f"received {wires!r}"
            )
        rows: list[dict[str, Any]] = []
        for name, spec in wires.items():
            clean_name = str(name)
            if not isinstance(spec, Mapping) or spec.get("kind") != _WIRE_MARKER:
                raise NetError(
                    f"connection {clean_name!r} must be declared with "
                    f"wire(...); received {spec!r}"
                )
            rows.append({**dict(spec), "name": clean_name})
        canonical = canonical_rows(
            [{key: row[key] for key in OVERRIDE_FIELDS} for row in rows],
            what="nets(wires=...)",
        )
        for row, source in zip(canonical, rows):
            row["avoid"] = tuple(source.get("avoid") or ())
            row["label"] = str(source.get("label") or "")
            for address in (row["a"], row["b"]):
                self._check_address(ports, address, row["name"])
        return canonical

    @staticmethod
    def _check_address(
        ports: Mapping[str, Any], address: str, row_name: str
    ) -> None:
        port, terminal = _split_endpoint(address)
        if port not in ports:
            raise NetError(
                f"connection {row_name!r} names port {port!r}, which "
                f"nets(ports=...) does not declare; it declares "
                f"{sorted(ports)}"
            )
        names = list(ports[port].names)
        if terminal not in names:
            raise NetError(
                f"connection {row_name!r} names terminal {terminal!r} on port "
                f"{port!r}, which has {names}"
            )

    def _terminal(
        self, ports: Mapping[str, Any], address: str, row_name: str
    ) -> Any:
        self._check_address(ports, address, row_name)
        port, terminal = _split_endpoint(address)
        return ports[port][terminal]
