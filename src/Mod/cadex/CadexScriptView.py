# SPDX-License-Identifier: LGPL-2.1-or-later

"""Read-only dock showing THE project script.

The script is the sole source of truth (docs/XSCRIPT.md); this dock lets
the user read it. It is deliberately not an editor: mutations go through
the assistant's ``xscript.project.*`` tools or the parameter sliders, so
the view only ever renders ``script.py`` as stored. Refreshes ride the
same hooks as the Parameters panel: assistant model-update notifications,
launch-state syncs, and dock visibility changes.

Like every experimental-mode dock, the widget is registered ONCE via
``addDockWindow(..., "right")`` and never repositioned at runtime —
QMainWindow.addDockWidget/splitDockWidget on FreeCAD-managed docks severs
other panels' Python signal connections (see CadexParametersPanel).
"""

from __future__ import annotations

from typing import Any

DOCK_NAME = "CadexScriptView"
DOCK_MINIMUM_WIDTH = 280
DOCK_MINIMUM_HEIGHT = 160

EMPTY_STATE_TEXT = "# No project script yet.\n# Ask the assistant to build one."

_controller: Any | None = None
_refresh_pending = False


def _warn(message: str) -> None:
    import FreeCAD as App

    App.Console.PrintWarning(f"Cadex script view: {message}\n")


def _project_script_source() -> str:
    """The stored project script source, or '' when there is none."""
    from CadexCore import get_service
    from CadexProject import CadexProjectScriptStore

    scope = get_service().project_scope_snapshot()
    root = str(scope.get("root") or "")
    if not root:
        return ""
    return CadexProjectScriptStore(root).read_source()


def _find_dock() -> Any | None:
    import FreeCADGui as Gui
    from PySide import QtWidgets

    main = Gui.getMainWindow()
    return (
        main.findChild(QtWidgets.QDockWidget, DOCK_NAME) if main is not None else None
    )


def _build_widget():
    from PySide import QtGui, QtWidgets

    root = QtWidgets.QWidget()
    root.setObjectName("CadexScriptViewRoot")
    root.setWindowTitle("Script")
    layout = QtWidgets.QVBoxLayout(root)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(0)

    editor = QtWidgets.QPlainTextEdit(root)
    editor.setObjectName("CadexScriptViewText")
    editor.setReadOnly(True)
    editor.setLineWrapMode(QtWidgets.QPlainTextEdit.NoWrap)
    font = QtGui.QFontDatabase.systemFont(QtGui.QFontDatabase.FixedFont)
    editor.setFont(font)
    layout.addWidget(editor)
    return root


class ScriptViewController:
    def __init__(self, dock: Any):
        from PySide import QtWidgets

        # Meta-object slot bridge, not a direct bound-method connect: plain
        # Python receivers route through PySide's shared registry, which dock
        # setup bursts can corrupt (see CadexParametersPanel._slot_bridge_class).
        from CadexParametersPanel import _connect_slot

        self.QtWidgets = QtWidgets
        self.dock = dock
        self.root = dock.widget()
        self._bridges = [
            _connect_slot(
                dock.visibilityChanged, "invoke_bool", self._visibility_changed, dock
            ),
        ]

    @property
    def editor(self):
        return self.root.findChild(self.QtWidgets.QPlainTextEdit, "CadexScriptViewText")

    def _visibility_changed(self, visible: bool) -> None:
        if visible:
            self.refresh()

    def refresh(self) -> None:
        try:
            source = _project_script_source()
        except Exception as exc:
            _warn(f"could not read the project script: {exc}")
            return
        editor = self.editor
        if editor is None:
            return
        text = source if source.strip() else EMPTY_STATE_TEXT
        if editor.toPlainText() == text:
            return
        # Preserve the reading position across refreshes of the same script.
        scrollbar = editor.verticalScrollBar()
        position = scrollbar.value() if scrollbar is not None else 0
        editor.setPlainText(text)
        if scrollbar is not None:
            scrollbar.setValue(min(position, scrollbar.maximum()))


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
        _controller = ScriptViewController(dock)
    elif _controller is None or _controller.dock is not dock:
        _controller = ScriptViewController(dock)
    dock.toggleViewAction().setVisible(True)
    return dock


def ensure_script_view_registered() -> Any:
    """Create the native dock once so View > Panels can always reopen it.

    Registration order fixes the right-side stacking (chat, parameters,
    tree, script) — call this after the parameters panel registration.
    """
    return _ensure_controller()


def schedule_refresh() -> None:
    """Coalesce refresh requests onto the next event-loop turn."""
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


def automated_model_update_finished(engine: str, document_name: str, model_id: str) -> None:
    del document_name, model_id  # One project script; nothing to select.
    if engine == "xscript" and _controller is not None:
        schedule_refresh()


def _project_has_script() -> bool:
    try:
        return bool(_project_script_source().strip())
    except Exception:
        return False


def sync_experimental_mode_dock() -> None:
    """Experimental mode: show the script under the tree once a script exists.

    Experimental mode hides all manual chrome, so the dock manages its own
    visibility: visible while the project script has content, hidden
    otherwise. Never repositioned at runtime (see module docstring).
    """
    import FreeCADGui as Gui
    from PySide import QtWidgets

    main = Gui.getMainWindow()
    if main is None:
        return
    dock = _ensure_controller()
    if _project_has_script():
        dock.setFloating(False)
        # No chrome is left to reopen a closed dock, so it must not be
        # closable or floatable.
        dock.setFeatures(QtWidgets.QDockWidget.NoDockWidgetFeatures)
        dock.show()
        if _controller is not None:
            _controller.refresh()
    else:
        dock.hide()
