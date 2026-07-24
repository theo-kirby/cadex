# SPDX-License-Identifier: LGPL-2.1-or-later

"""End-user parameter slider dock for THE project script.

The panel lets a person tweak the project script's declared parameters
(``params``/``num`` declarations in the script) with sliders and see the
geometry rebuild — no assistant round-trip. Ranges come from the declared
parameter specs, with a value-bracketing band filling every gap, so a
spec with no bounds still gets a usable slider. Commits go through
``xscript.project.set_params`` — the same rebuild path the agent uses —
so a failed rebuild leaves the accepted live geometry untouched.

The resolution helpers at the top of this module are pure (no Qt, no
FreeCAD) so headless tests can import them; all Qt imports are lazy.
"""

from __future__ import annotations

import math
import re
from typing import Any, Mapping

DOCK_NAME = "CadexParametersPanel"
DOCK_MINIMUM_WIDTH = 280
DOCK_MINIMUM_HEIGHT = 200
DEBOUNCE_MS = 600

_controller: Any | None = None
_refresh_pending = False


# ---------------------------------------------------------------------------
# Pure control-resolution helpers (no Qt, no FreeCAD)
# ---------------------------------------------------------------------------


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


def _spec_number(spec: Mapping[str, Any], field: str) -> float | None:
    value = spec.get(field)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    return number if math.isfinite(number) else None


def spec_control(spec: Mapping[str, Any], value: float) -> dict[str, Any]:
    """Slider metadata for one declared project parameter spec.

    Declared fields win per-field. Missing bounds fall back to a usable
    band bracketing the current value; bounds are widened (never rejected)
    so the current value is always on the slider, then rounded outward
    onto the step grid.
    """
    number = float(value)
    name = str(spec.get("name") or "")
    label = str(spec.get("label") or "") or parameter_title(name)
    unit = str(spec.get("unit") or "")
    description = str(spec.get("description") or "")

    # Default band bracketing the current value (0 gets 0..10).
    if number >= 0.0:
        default_min, default_max = 0.0, max(3.0 * number, 10.0)
    else:
        default_min, default_max = min(3.0 * number, -10.0), 0.0
    declared_min = _spec_number(spec, "min")
    declared_max = _spec_number(spec, "max")
    minimum = declared_min if declared_min is not None else default_min
    maximum = declared_max if declared_max is not None else default_max

    # Widen so the current (possibly out-of-band) stored value stays reachable.
    if number < minimum:
        minimum = number
    if number > maximum:
        maximum = number
    if minimum >= maximum:
        pad = max(abs(number), 1.0)
        minimum = min(minimum, number - pad)
        maximum = max(maximum, number + pad)

    step = _spec_number(spec, "step")
    if step is None or step <= 0:
        step = nice_step(maximum - minimum)
    minimum = _round_to_step(minimum, step, up=False)
    maximum = _round_to_step(maximum, step, up=True)

    return {
        "label": label,
        "unit": unit,
        "min": minimum,
        "max": maximum,
        "step": step,
        "description": description,
    }


def parameter_rows(parameters: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Row models for the declared specs, in declaration order.

    ``parameters`` is the ``_project_parameters`` shape ({specs, values, ...});
    each row's value is the stored value when present, else the spec default.
    """
    values = parameters.get("values") or {}
    rows: list[dict[str, Any]] = []
    for spec in parameters.get("specs") or []:
        if not isinstance(spec, dict):
            continue
        name = str(spec.get("name") or "")
        if not name:
            continue
        stored = values.get(name) if isinstance(values, Mapping) else None
        if isinstance(stored, (int, float)) and not isinstance(stored, bool):
            value = float(stored)
        else:
            default = spec.get("default")
            if isinstance(default, (int, float)) and not isinstance(default, bool):
                value = float(default)
            else:
                value = 0.0
        rows.append(
            {"name": name, "value": value, "control": spec_control(spec, value)}
        )
    return rows


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


def _project_parameters(service: Any) -> dict[str, Any]:
    """Read the project script's declared parameter state from the store."""
    from CadexProject import CadexProjectScriptStore

    scope = service.project_scope_snapshot()
    root = str(scope.get("root") or "")
    if not root:
        return {"specs": [], "values": {}, "working_revision": "", "has_script": False}
    store = CadexProjectScriptStore(root)
    state = store.read_state()
    specs = [
        dict(spec) for spec in (state.get("param_specs") or []) if isinstance(spec, dict)
    ]
    return {
        "specs": specs,
        "values": dict(state.get("param_values") or {}),
        "working_revision": str(state.get("working_revision") or ""),
        "has_script": bool(store.read_source().strip()),
    }


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
        self.model_label = "Project script"
        self.has_script = False
        self.working_revision = ""
        self.rows: list[_ParameterRow] = []
        self._rebuilding = False
        self._bridges = [
            _connect_slot(
                dock.visibilityChanged, "invoke_bool", self._visibility_changed, dock
            ),
        ]

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

    def refresh(self) -> None:
        if self._rebuilding:
            return
        from CadexCore import get_service

        try:
            parameters = _project_parameters(get_service())
        except Exception as exc:
            _warn(f"could not read the project script parameters: {exc}")
            parameters = {
                "specs": [],
                "values": {},
                "working_revision": "",
                "has_script": False,
            }
        self.has_script = bool(parameters.get("has_script"))
        self.working_revision = str(parameters.get("working_revision") or "")
        self._clear_rows()
        layout = self.rows_layout
        for position, model in enumerate(parameter_rows(parameters)):
            row = _ParameterRow(
                self, model["name"], model["value"], model["control"]
            )
            layout.insertWidget(position, row.widget)
            self.rows.append(row)
        if self.rows:
            self.status.setText(
                f"{len(self.rows)} parameters | "
                f"revision {self.working_revision[:10]}"
            )
        elif self.has_script:
            self.status.setText("The project script declares no parameters.")
        else:
            self.status.setText(
                "No project script yet. Ask the assistant to build one."
            )

    def _clear_rows(self) -> None:
        layout = self.rows_layout
        for row in self.rows:
            layout.removeWidget(row.widget)
            row.widget.deleteLater()
        self.rows = []

    # -- commit -------------------------------------------------------------

    def _set_rows_enabled(self, enabled: bool) -> None:
        for row in self.rows:
            row.set_enabled(enabled)

    def _stop_pending_edits(self) -> None:
        for row in self.rows:
            row.debounce.stop()

    def commit(self, row: _ParameterRow, value: float) -> None:
        if self._rebuilding:
            return
        value = float(value)
        if value == row.committed_value:
            return
        self._commit(row, value, allow_retry=True)

    def _commit(self, row: _ParameterRow, value: float, *, allow_retry: bool) -> None:
        from CadexCore import get_service
        from CadexSession import run_project_xscript_operation

        self._stop_pending_edits()
        self._rebuilding = True
        self._set_rows_enabled(False)
        self.status.setText(
            f"Rebuilding the {self.model_label.lower()}: {row.name} = {value}..."
        )
        try:
            try:
                result = run_project_xscript_operation(
                    get_service(),
                    "xscript.project.set_params",
                    {
                        "values": {row.name: value},
                        "expected_revision": self.working_revision,
                    },
                )
            except Exception as exc:
                row.revert()
                self.status.setText(f"Parameter change failed: {exc}")
                return
            if result.get("ok"):
                self.working_revision = str(
                    result.get("revision") or self.working_revision
                )
                row.committed_value = value
                self.status.setText(
                    f"{row.name} = {value} | "
                    f"revision {self.working_revision[:10]}"
                )
                return
            code = str(result.get("failure_code") or "")
            observed = result.get("observed") or {}
            if code == "STALE_PROGRAM_REVISION" and allow_retry:
                current = str(observed.get("current_revision") or "")
                if current:
                    # The script advanced under us; re-guard and retry once.
                    self.working_revision = current
                    self._rebuilding = False
                    self._commit(row, value, allow_retry=False)
                    return
            model_state = result.get("model_state") or {}
            advanced = str(model_state.get("next_write_expected_revision") or "")
            if advanced:
                # A failed rebuild advances the working revision on disk; track
                # it so the next commit does not trip the stale check.
                self.working_revision = advanced
            row.revert()
            self.status.setText(
                f"{code or 'REBUILD_FAILED'}: "
                f"{result.get('error') or 'parameter change rejected.'} "
                "The accepted live geometry is unchanged."
            )
        finally:
            self._rebuilding = False
            self._set_rows_enabled(True)

    # -- assistant coordination ---------------------------------------------

    def automated_update_started(self, document_name: str) -> None:
        import FreeCAD as App

        if document_name != str(getattr(App.ActiveDocument, "Name", "") or ""):
            return
        self._stop_pending_edits()
        self._set_rows_enabled(False)
        self.status.setText(f"AI is updating the {self.model_label.lower()}...")

    def automated_update_finished(self, document_name: str) -> None:
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
    del model_id  # One project script; there is nothing to select.
    if engine == "xscript" and _controller is not None:
        _controller.automated_update_started(document_name)


def automated_model_update_finished(
    engine: str, document_name: str, model_id: str
) -> None:
    del model_id  # One project script; there is nothing to select.
    if engine == "xscript" and _controller is not None:
        _controller.automated_update_finished(document_name)


def _project_has_parameters() -> bool:
    from CadexCore import get_service

    try:
        parameters = _project_parameters(get_service())
    except Exception:
        return False
    return bool(parameters.get("has_script")) and bool(parameters.get("specs"))


def sync_experimental_mode_dock() -> None:
    """Experimental mode: show the panel under the assistant when params exist.

    Experimental mode hides all manual chrome, so the panel manages its own
    visibility there: visible below the assistant dock while the project
    script declares parameters, hidden otherwise.
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
        _project_has_parameters()
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
