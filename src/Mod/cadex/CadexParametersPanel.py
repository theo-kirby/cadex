# SPDX-License-Identifier: LGPL-2.1-or-later

"""End-user parameter slider dock for XScript models.

The panel lets a person tweak a model's driving inputs with sliders and
see the geometry rebuild — no assistant round-trip. Ranges come from
agent-declared ``input_controls`` metadata when present, with a naming
heuristic filling every gap, so a controls-less model still gets usable
sliders. Commits reuse the exact rebuild path the agent uses
(``xscript.<domain>.set_inputs``), so a failed rebuild leaves the
guarded live geometry untouched.

The resolution helpers at the top of this module are pure (no Qt, no
FreeCAD) so headless tests can import them; all Qt imports are lazy.
"""

from __future__ import annotations

import math
import re
from typing import Any

DOCK_NAME = "CadexParametersPanel"
DOCK_MINIMUM_WIDTH = 280
DOCK_MINIMUM_HEIGHT = 200
DEBOUNCE_MS = 600

_controller: Any | None = None
_refresh_pending = False


# ---------------------------------------------------------------------------
# Pure control-resolution helpers (no Qt, no FreeCAD)
# ---------------------------------------------------------------------------

_ANGLE_PREFIXES = ("angle", "rot", "tilt", "twist", "taper")
_COUNT_TOKENS = frozenset(
    {
        "count",
        "counts",
        "num",
        "number",
        "teeth",
        "sides",
        "segments",
        "copies",
        "qty",
        "quantity",
        "instances",
        "blades",
        "spokes",
        "divisions",
        "turns",
    }
)

CONTROL_FIELDS = ("label", "unit", "min", "max", "step", "description")


def _name_tokens(name: str) -> list[str]:
    parts = re.split(r"[^a-zA-Z0-9]+", str(name or ""))
    tokens: list[str] = []
    for part in parts:
        # Split camelCase runs so "bladeCount" tokenizes like "blade_count".
        tokens.extend(
            match.lower()
            for match in re.findall(r"[A-Z]?[a-z0-9]+|[A-Z]+(?![a-z])", part)
        )
    return [token for token in tokens if token]


def parameter_title(name: str) -> str:
    tokens = _name_tokens(name)
    return " ".join(token.capitalize() for token in tokens) or str(name)


def nice_step(span: float) -> float:
    """A 1/2/5-decade step giving roughly 50-200 slider positions over span."""
    if not math.isfinite(span) or span <= 0:
        return 1.0
    raw = span / 100.0
    magnitude = 10.0 ** math.floor(math.log10(raw))
    for multiplier in (1.0, 2.0, 5.0, 10.0):
        step = magnitude * multiplier
        if step >= raw:
            return round(step, 12)
    return round(magnitude * 10.0, 12)


def _round_to_step(value: float, step: float, *, up: bool) -> float:
    scaled = value / step
    rounded = math.ceil(scaled - 1e-9) if up else math.floor(scaled + 1e-9)
    return round(rounded * step, 9)


def heuristic_control(name: str, value: Any) -> dict[str, Any]:
    """Guess slider metadata for a parameter with no declared control."""
    number = float(value)
    tokens = _name_tokens(name)
    label = parameter_title(name)
    if any(
        token.startswith(prefix) for token in tokens for prefix in _ANGLE_PREFIXES
    ):
        return {
            "label": label,
            "unit": "°",
            "min": 0.0,
            "max": 360.0,
            "step": 1.0,
        }
    if any(token in _COUNT_TOKENS for token in tokens):
        upper = max(10.0, float(math.ceil(abs(number) * 3.0)))
        return {"label": label, "unit": "", "min": 1.0, "max": upper, "step": 1.0}
    # Length-like default: a nice-rounded 0.1x-3x band around the value.
    if number == 0.0:
        return {"label": label, "unit": "mm", "min": 0.0, "max": 10.0, "step": 0.1}
    if number > 0.0:
        low_raw, high_raw = number * 0.1, number * 3.0
    else:
        low_raw, high_raw = number * 3.0, number * 0.1
    step = nice_step(high_raw - low_raw)
    return {
        "label": label,
        "unit": "mm",
        "min": _round_to_step(low_raw, step, up=False),
        "max": _round_to_step(high_raw, step, up=True),
        "step": step,
    }


def resolve_control(name: str, value: Any, declared: Any) -> dict[str, Any]:
    """Merge declared metadata over the heuristic and widen to fit the value.

    Declared fields win per-field; the heuristic fills every gap; bounds are
    widened (never rejected) so the current value is always on the slider.
    """
    control = heuristic_control(name, value)
    control.setdefault("description", "")
    if isinstance(declared, dict):
        for field in CONTROL_FIELDS:
            if field in declared and declared[field] is not None:
                control[field] = declared[field]
    control["min"] = float(control["min"])
    control["max"] = float(control["max"])
    control["step"] = float(control["step"])
    number = float(value)
    if number < control["min"]:
        control["min"] = number
    if number > control["max"]:
        control["max"] = number
    if control["min"] >= control["max"]:
        pad = max(abs(number), 1.0)
        control["min"] = min(control["min"], number - pad)
        control["max"] = max(control["max"], number + pad)
    if not math.isfinite(control["step"]) or control["step"] <= 0:
        control["step"] = nice_step(control["max"] - control["min"])
    return control


def slider_steps(control: dict[str, Any]) -> int:
    """Integer positions on the slider: steps of control['step'] across the range."""
    span = control["max"] - control["min"]
    return max(1, int(round(span / control["step"])))


def value_to_slider(value: Any, control: dict[str, Any]) -> int:
    position = int(round((float(value) - control["min"]) / control["step"]))
    return max(0, min(slider_steps(control), position))


def slider_to_value(position: int, control: dict[str, Any]) -> float:
    value = control["min"] + float(position) * control["step"]
    return min(control["max"], max(control["min"], round(value, 9)))


def spin_decimals(step: float) -> int:
    if not math.isfinite(step) or step <= 0:
        return 2
    if step >= 1.0 and float(step).is_integer():
        return 0
    return max(0, min(3, math.ceil(-math.log10(step) - 1e-9)))


# ---------------------------------------------------------------------------
# Qt dock widget and controller
# ---------------------------------------------------------------------------


def _warn(message: str) -> None:
    import FreeCAD as App

    App.Console.PrintWarning(f"Cadex parameters panel: {message}\n")


def _active_xscript_surface(service: Any) -> tuple[str, str]:
    """Return the (engine, domain) of the live modeling surface.

    ``domain`` is only meaningful — and only returned — when the active engine
    is XScript and the surface is available; otherwise it is empty.
    """
    from CadexModelingSurface import resolve_modeling_surface

    try:
        engine = service.modeling_engine()
        workbench = service.active_workbench_name()
        resolution = resolve_modeling_surface(workbench, engine)
    except Exception:
        return "", ""
    resolved_engine = str(getattr(resolution, "engine", "") or "")
    if resolved_engine != "xscript" or not getattr(resolution, "available", False):
        return resolved_engine, ""
    return resolved_engine, str(resolution.domain or "")


def _list_xscript_programs(service: Any, domain: str) -> list[dict[str, Any]]:
    """Read the domain's bounded program index (identities, inputs, controls)."""
    import CadexScriptedDomains as dc

    snapshot = dc.domain_program_index_snapshot(service, domain)
    completed = dc.complete_domain_program_index(snapshot)
    return list(completed.get("programs") or [])


_slot_bridge = None


def _slot_bridge_class():
    """QObject bridge whose endpoints are true meta-object slots.

    Connecting Qt signals to bound methods of plain Python objects routes
    them through PySide's shared Python receiver registry — and a burst of
    such connections (parameter rows during document open) corrupts that
    registry, silently severing unrelated Python connections elsewhere
    (observed: every assistant-panel button went dead). @Slot methods on a
    QObject receiver use the C++ meta-object path instead, which does not
    touch the shared registry.
    """
    global _slot_bridge
    if _slot_bridge is None:
        from PySide import QtCore

        class SlotBridge(QtCore.QObject):
            def __init__(self, callback: Any, parent: Any):
                super().__init__(parent)
                self._callback = callback

            @QtCore.Slot()
            def invoke(self) -> None:
                self._callback()

            @QtCore.Slot(int)
            def invoke_int(self, value: int) -> None:
                self._callback(value)

            @QtCore.Slot(float)
            def invoke_float(self, value: float) -> None:
                self._callback(value)

            @QtCore.Slot(bool)
            def invoke_bool(self, value: bool) -> None:
                self._callback(value)

        _slot_bridge = SlotBridge
    return _slot_bridge


def _connect_slot(signal: Any, signature: str, callback: Any, parent: Any) -> Any:
    """Connect signal -> callback through a meta-object slot endpoint."""
    bridge = _slot_bridge_class()(callback, parent)
    signal.connect(getattr(bridge, signature))
    return bridge


def _find_dock() -> Any | None:
    import FreeCADGui as Gui
    from PySide import QtWidgets

    main = Gui.getMainWindow()
    return (
        main.findChild(QtWidgets.QDockWidget, DOCK_NAME) if main is not None else None
    )


def _build_widget():
    from PySide import QtCore, QtWidgets

    root = QtWidgets.QWidget()
    root.setObjectName("VibeParametersRoot")
    root.setWindowTitle("Parameters")
    layout = QtWidgets.QVBoxLayout(root)
    layout.setContentsMargins(8, 8, 8, 8)
    layout.setSpacing(6)

    selector = QtWidgets.QComboBox(root)
    selector.setObjectName("VibeParametersModelSelector")
    selector.setSizePolicy(
        QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed
    )
    layout.addWidget(selector)

    scroll = QtWidgets.QScrollArea(root)
    scroll.setObjectName("VibeParametersScroll")
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
    rows_host = QtWidgets.QWidget(scroll)
    rows_host.setObjectName("VibeParametersRows")
    rows_layout = QtWidgets.QVBoxLayout(rows_host)
    rows_layout.setContentsMargins(0, 0, 0, 0)
    rows_layout.setSpacing(8)
    rows_layout.addStretch(1)
    scroll.setWidget(rows_host)
    layout.addWidget(scroll, 1)

    status = QtWidgets.QLabel(root)
    status.setObjectName("VibeParametersStatus")
    status.setWordWrap(True)
    status.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
    layout.addWidget(status)
    return root


class _ParameterRow:
    """One parameter: label, int-scaled slider, and a debounced spinbox."""

    def __init__(self, controller: Any, name: str, value: float, control: dict):
        QtCore = controller.QtCore
        QtWidgets = controller.QtWidgets
        self.controller = controller
        self.name = name
        self.control = control
        self.committed_value = float(value)
        self._updating = False

        self.widget = QtWidgets.QWidget()
        grid = QtWidgets.QGridLayout(self.widget)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(6)
        grid.setVerticalSpacing(2)

        title = QtWidgets.QLabel(str(control.get("label") or name), self.widget)
        grid.addWidget(title, 0, 0, 1, 2)

        self.slider = QtWidgets.QSlider(QtCore.Qt.Horizontal, self.widget)
        self.slider.setRange(0, slider_steps(control))
        grid.addWidget(self.slider, 1, 0)

        self.spin = QtWidgets.QDoubleSpinBox(self.widget)
        self.spin.setRange(control["min"], control["max"])
        self.spin.setDecimals(spin_decimals(control["step"]))
        self.spin.setSingleStep(control["step"])
        self.spin.setKeyboardTracking(True)
        unit = str(control.get("unit") or "")
        if unit:
            self.spin.setSuffix(unit if unit == "°" else f" {unit}")
        self.spin.setMinimumWidth(90)
        grid.addWidget(self.spin, 1, 1)

        description = str(control.get("description") or "")
        if description:
            self.widget.setToolTip(description)
            self.slider.setToolTip(description)
            self.spin.setToolTip(description)

        self.debounce = QtCore.QTimer(self.widget)
        self.debounce.setSingleShot(True)
        self.debounce.setInterval(DEBOUNCE_MS)

        self.set_value_silently(value)
        self._bridges = [
            _connect_slot(
                self.slider.sliderMoved, "invoke_int", self._slider_moved, self.widget
            ),
            _connect_slot(
                self.slider.sliderReleased, "invoke", self._slider_released, self.widget
            ),
            _connect_slot(
                self.slider.valueChanged,
                "invoke_int",
                self._slider_value_changed,
                self.widget,
            ),
            _connect_slot(
                self.spin.valueChanged, "invoke_float", self._spin_changed, self.widget
            ),
            _connect_slot(
                self.spin.editingFinished,
                "invoke",
                self._spin_editing_finished,
                self.widget,
            ),
            _connect_slot(
                self.debounce.timeout, "invoke", self._debounce_fired, self.widget
            ),
        ]

    def set_value_silently(self, value: float) -> None:
        self._updating = True
        try:
            self.spin.setValue(float(value))
            self.slider.setValue(value_to_slider(value, self.control))
        finally:
            self._updating = False

    def revert(self) -> None:
        self.debounce.stop()
        self.set_value_silently(self.committed_value)

    def set_enabled(self, enabled: bool) -> None:
        self.widget.setEnabled(enabled)

    # -- signal handlers ----------------------------------------------------

    def _slider_moved(self, position: int) -> None:
        # Live drag: preview the number only; the rebuild waits for release.
        self._updating = True
        try:
            self.spin.setValue(slider_to_value(position, self.control))
        finally:
            self._updating = False

    def _slider_released(self) -> None:
        self.debounce.stop()
        self.controller.commit(self, slider_to_value(self.slider.value(), self.control))

    def _slider_value_changed(self, position: int) -> None:
        if self._updating or self.slider.isSliderDown():
            return
        # Groove clicks and arrow keys change the value without a drag;
        # debounce them like typed edits so key repeats coalesce.
        self._updating = True
        try:
            self.spin.setValue(slider_to_value(position, self.control))
        finally:
            self._updating = False
        self.debounce.start()

    def _spin_changed(self, _value: float) -> None:
        if self._updating:
            return
        self._updating = True
        try:
            self.slider.setValue(value_to_slider(self.spin.value(), self.control))
        finally:
            self._updating = False
        self.debounce.start()

    def _spin_editing_finished(self) -> None:
        if self.debounce.isActive():
            self.debounce.stop()
            self.controller.commit(self, self.spin.value())

    def _debounce_fired(self) -> None:
        self.controller.commit(self, self.spin.value())


class ParametersPanelController:
    def __init__(self, dock: Any):
        from PySide import QtCore, QtWidgets

        self.QtCore = QtCore
        self.QtWidgets = QtWidgets
        self.dock = dock
        self.root = dock.widget()
        self.model_id = ""
        self.model_label = ""
        self.domain = ""
        self.working_revision = ""
        self.rows: list[_ParameterRow] = []
        self.loading = False
        self._rebuilding = False
        self._summaries: dict[str, dict[str, Any]] = {}
        self._bridges = [
            _connect_slot(
                self.selector.currentIndexChanged,
                "invoke_int",
                self._select_model,
                dock,
            ),
            _connect_slot(
                dock.visibilityChanged, "invoke_bool", self._visibility_changed, dock
            ),
        ]

    @property
    def selector(self):
        return self.root.findChild(
            self.QtWidgets.QComboBox, "VibeParametersModelSelector"
        )

    @property
    def status(self):
        return self.root.findChild(self.QtWidgets.QLabel, "VibeParametersStatus")

    @property
    def rows_layout(self):
        host = self.root.findChild(self.QtWidgets.QWidget, "VibeParametersRows")
        return host.layout()

    def _visibility_changed(self, visible: bool) -> None:
        if visible and not self._rebuilding:
            self.refresh()

    # -- refresh ------------------------------------------------------------

    def refresh(self, preferred_model_id: str = "") -> None:
        if self._rebuilding:
            return
        from CadexCore import get_service

        service = get_service()
        engine, domain = _active_xscript_surface(service)
        self.domain = domain
        models: list[dict[str, Any]] = []
        if engine == "xscript" and domain:
            try:
                models = _list_xscript_programs(service, domain)
            except Exception as exc:
                _warn(f"could not list XScript programs: {exc}")
        self._summaries = {
            str(item.get("program_id") or ""): item
            for item in models
            if item.get("program_id")
        }
        target = preferred_model_id or self.model_id
        self.loading = True
        try:
            self.selector.clear()
            self.selector.addItem("None", "")
            for model_id, item in self._summaries.items():
                label = str(item.get("label") or model_id)
                self.selector.addItem(label, model_id)
            index = self.selector.findData(target) if target else -1
            if index < 0:
                # Auto-select the only model so the common case needs no click.
                index = 1 if len(self._summaries) == 1 else 0
            self.selector.setCurrentIndex(index)
        finally:
            self.loading = False
        if engine != "xscript":
            self._clear_rows()
            self.model_id = ""
            self.status.setText(
                "Parameter sliders drive XScript models. Switch the modeling "
                "engine to XScript to use them."
            )
            return
        model_id = str(self.selector.currentData() or "")
        if model_id:
            self._load_model(model_id)
        else:
            self._clear_rows()
            self.model_id = ""
            self.status.setText(
                "No XScript models yet. Ask the assistant to build one."
                if not self._summaries
                else "Select a model to edit its parameters."
            )

    def _select_model(self, index: int) -> None:
        if self.loading or index < 0:
            return
        model_id = str(self.selector.itemData(index) or "")
        if model_id:
            self._load_model(model_id)
        else:
            self._clear_rows()
            self.model_id = ""
            self.status.setText("Select a model to edit its parameters.")

    def _clear_rows(self) -> None:
        layout = self.rows_layout
        for row in self.rows:
            layout.removeWidget(row.widget)
            row.widget.deleteLater()
        self.rows = []

    def _load_model(self, model_id: str) -> None:
        summary = self._summaries.get(model_id)
        if summary is None:
            return
        self.model_id = model_id
        self.model_label = str(summary.get("label") or model_id)
        self.working_revision = str(summary.get("working_revision") or "")
        inputs = summary.get("inputs")
        declared = summary.get("input_controls")
        if not isinstance(inputs, dict):
            inputs = {}
        if not isinstance(declared, dict):
            declared = {}
        self._clear_rows()
        layout = self.rows_layout
        numeric = [
            (name, value)
            for name, value in sorted(inputs.items())
            if isinstance(value, (int, float)) and not isinstance(value, bool)
        ]
        for position, (name, value) in enumerate(numeric):
            control = resolve_control(name, value, declared.get(name))
            row = _ParameterRow(self, name, float(value), control)
            layout.insertWidget(position, row.widget)
            self.rows.append(row)
        if numeric:
            self.status.setText(
                f"{self.model_label} | revision {self.working_revision[:10]} | "
                f"{len(numeric)} parameters"
            )
        else:
            self.status.setText(f"{self.model_label} has no numeric parameters.")

    # -- commit -------------------------------------------------------------

    def _set_rows_enabled(self, enabled: bool) -> None:
        for row in self.rows:
            row.set_enabled(enabled)

    def _stop_pending_edits(self) -> None:
        for row in self.rows:
            row.debounce.stop()

    def commit(self, row: _ParameterRow, value: float) -> None:
        if self._rebuilding or not self.model_id:
            return
        value = float(value)
        if value == row.committed_value:
            return
        self._commit(row, value, allow_retry=True)

    def _commit(self, row: _ParameterRow, value: float, *, allow_retry: bool) -> None:
        from CadexCore import get_service
        from CadexSession import run_domain_xscript_operation

        self._stop_pending_edits()
        self._rebuilding = True
        self._set_rows_enabled(False)
        self.status.setText(f"Rebuilding {self.model_label}: {row.name} = {value}...")
        try:
            try:
                result = run_domain_xscript_operation(
                    get_service(),
                    f"xscript.{self.domain}.set_inputs",
                    {
                        "program_id": self.model_id,
                        "expected_revision": self.working_revision,
                        "patch": {row.name: value},
                    },
                )
            except Exception as exc:
                row.revert()
                self.status.setText(f"Parameter change failed: {exc}")
                return
            if result.get("ok"):
                self.working_revision = str(
                    result.get("working_revision") or self.working_revision
                )
                row.committed_value = value
                self.status.setText(
                    f"{self.model_label} rebuilt | {row.name} = {value} | "
                    f"revision {self.working_revision[:10]}"
                )
                return
            code = str(result.get("failure_code") or "")
            observed = result.get("observed") or {}
            if code == "STALE_PROGRAM_REVISION" and allow_retry:
                current = str(observed.get("current_revision") or "")
                if current:
                    # The program advanced under us; re-guard and retry once.
                    self.working_revision = current
                    self._rebuilding = False
                    self._commit(row, value, allow_retry=False)
                    return
            failed = result.get("failed_candidate") or {}
            advanced = str(failed.get("revision") or "")
            if advanced:
                # A failed rebuild advances the working revision on disk; track it
                # so the next commit does not trip the stale check.
                self.working_revision = advanced
            row.revert()
            self.status.setText(
                f"{code or 'REBUILD_FAILED'}: "
                f"{result.get('error') or 'parameter change rejected.'} "
                "The guarded live geometry is unchanged."
            )
        finally:
            self._rebuilding = False
            self._set_rows_enabled(True)

    # -- assistant coordination ---------------------------------------------

    def automated_update_started(self, document_name: str, model_id: str) -> None:
        import FreeCAD as App

        if document_name != str(getattr(App.ActiveDocument, "Name", "") or ""):
            return
        self._stop_pending_edits()
        self._set_rows_enabled(False)
        if model_id == self.model_id:
            self.status.setText(f"AI is updating {self.model_label}...")

    def automated_update_finished(self, document_name: str, model_id: str) -> None:
        import FreeCAD as App

        if document_name != str(getattr(App.ActiveDocument, "Name", "") or ""):
            return
        self._set_rows_enabled(True)
        schedule_refresh()


# ---------------------------------------------------------------------------
# Dock registration and module-level API
# ---------------------------------------------------------------------------


def _register_dock(widget: Any) -> Any:
    import FreeCADGui as Gui

    main = Gui.getMainWindow()
    if main is None:
        raise RuntimeError("FreeCAD main window is unavailable.")
    add_dock_window = getattr(main, "addDockWindow", None)
    if not callable(add_dock_window):
        raise RuntimeError("FreeCAD DockWindowManager is unavailable.")
    dock = add_dock_window(widget, DOCK_NAME, "right")
    dock.toggleViewAction().setVisible(True)
    return dock


def _ensure_controller() -> Any:
    global _controller
    dock = _find_dock()
    if dock is None or dock.widget() is None:
        widget = _build_widget()
        if dock is None:
            dock = _register_dock(widget)
        else:
            dock.setWidget(widget)
        dock.setMinimumWidth(DOCK_MINIMUM_WIDTH)
        dock.setMinimumHeight(DOCK_MINIMUM_HEIGHT)
        dock.hide()
        _controller = ParametersPanelController(dock)
    elif _controller is None or _controller.dock is not dock:
        _controller = ParametersPanelController(dock)
    dock.toggleViewAction().setVisible(True)
    return dock


def ensure_parameters_panel_registered() -> Any:
    """Create the native dock once so View > Panels can always reopen it."""
    return _ensure_controller()


def show_parameters_panel() -> None:
    dock = _ensure_controller()
    dock.show()
    dock.raise_()
    if _controller is not None:
        _controller.refresh()


def schedule_refresh() -> None:
    """Coalesce refresh requests onto the next event-loop turn.

    Safe to call from any document/tool callback; a no-op before the dock
    has been registered or when the GUI is not running.
    """
    global _refresh_pending
    if _controller is None or _refresh_pending:
        return
    try:
        from PySide import QtCore
    except Exception:
        return
    _refresh_pending = True

    def fire() -> None:
        global _refresh_pending
        _refresh_pending = False
        if _controller is None:
            return
        try:
            try:
                from CadexExperimentalMode import is_experimental_mode_session
            except Exception:
                is_experimental_mode_session = None
            if is_experimental_mode_session is not None and is_experimental_mode_session():
                sync_experimental_mode_dock()
            elif _controller.dock.isVisible():
                _controller.refresh()
        except Exception as exc:
            _warn(f"refresh failed: {exc}")

    QtCore.QTimer.singleShot(0, fire)


def automated_model_update_started(
    engine: str, document_name: str, model_id: str
) -> None:
    if engine == "xscript" and _controller is not None:
        _controller.automated_update_started(document_name, model_id)


def automated_model_update_finished(
    engine: str, document_name: str, model_id: str
) -> None:
    if engine == "xscript" and _controller is not None:
        _controller.automated_update_finished(document_name, model_id)


def _has_xscript_models() -> bool:
    from CadexCore import get_service

    service = get_service()
    engine, domain = _active_xscript_surface(service)
    if engine != "xscript" or not domain:
        return False
    try:
        return bool(_list_xscript_programs(service, domain))
    except Exception:
        return False


def sync_experimental_mode_dock() -> None:
    """Experimental mode: show the panel under the assistant when models exist.

    Experimental mode hides all manual chrome, so the panel manages its own
    visibility there: visible below the assistant dock while the open
    document has XScript models, hidden otherwise.
    """
    import FreeCADGui as Gui
    from PySide import QtWidgets

    main = Gui.getMainWindow()
    if main is None:
        return
    dock = _ensure_controller()
    assistant = None
    try:
        from CadexExperimentalMode import ASSISTANT_DOCK_NAME

        assistant = main.findChild(QtWidgets.QDockWidget, ASSISTANT_DOCK_NAME)
    except Exception:
        pass
    if (
        _has_xscript_models()
        and assistant is not None
        and assistant.isVisible()
    ):
        dock.setFloating(False)
        # Experimental mode hides all chrome, so the dock must not be closable or
        # floatable: there would be no control left to bring it back.
        dock.setFeatures(QtWidgets.QDockWidget.NoDockWidgetFeatures)
        # Deliberately no QMainWindow.addDockWidget/splitDockWidget here.
        # Repositioning FreeCAD-managed dock windows at runtime makes the
        # dock manager sever the Python signal connections of the other
        # panels (verified: the assistant header buttons went dead). The
        # registration-time addDockWindow(..., "right") placement stands.
        dock.show()
        if _controller is not None:
            _controller.refresh()
    else:
        dock.hide()
