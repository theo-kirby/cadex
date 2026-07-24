# SPDX-License-Identifier: LGPL-2.1-or-later

"""Cadex experimental mode: 3D viewport plus assistant chat, no manual chrome.

Experimental mode hides every toolbar, dock (except the assistant panel), the
status bar, and the MDI tab bar, leaving the native menu bar and the
viewport navigation cube. The AI drives all modeling; task panels are
suppressed. Guards re-hide chrome that workbench activation re-shows.

The ``ExperimentalMode`` preference is read exactly once, at import: toggling it
in preferences only takes effect after a restart. The same session cache
exists on the C++ side in ``MainWindow::isVibeExperimentalModeSession()``, which
keeps an experimental-mode session from overwriting the saved manual layout.
"""

from __future__ import annotations

from typing import Any

import FreeCAD as App
import FreeCADGui as Gui

PREFERENCE_GROUP = "User parameter:BaseApp/Preferences/Mod/cadex"
ASSISTANT_DOCK_NAME = "CadexAssistantPanel"
# Single source of truth for the dock name lives in the panel module.
from CadexParametersPanel import DOCK_NAME as PARAMETERS_DOCK_NAME  # noqa: E402
TASKS_DOCK_NAME = "Tasks"
# Object name of the standalone model-tree dock. MainWindow::updateTreeView
# force-creates it on the right for experimental-mode sessions; the QDockWidget
# inherits the inner widget's object name ("Tree view").
TREE_DOCK_NAME = "Tree view"

# Single source of truth for the dock name lives in the view module.
from CadexScriptView import DOCK_NAME as SCRIPT_VIEW_DOCK_NAME  # noqa: E402

# Docks the end user is allowed to see in experimental mode: the assistant
# chat, the XScript parameter sliders, the model tree, and the read-only
# script view (each manages its own visibility below).
ALLOWED_DOCK_NAMES = frozenset(
    {
        ASSISTANT_DOCK_NAME,
        PARAMETERS_DOCK_NAME,
        TREE_DOCK_NAME,
        SCRIPT_VIEW_DOCK_NAME,
    }
)
EXPERIMENTAL_MODE_WORKBENCH = "PartDesignWorkbench"

_SUPPRESSED_PROPERTY = "VibeExperimentalModeSuppressed"
_REHIDE_PENDING_PROPERTY = "VibeExperimentalModeRehidePending"

ASSISTANT_DOCK_MINIMUM_WIDTH = 360
# Target split: right dock column takes this fraction of the window width
# (docs/ROADMAP.md Phase 3 — 50/50 viewport / panels).
RIGHT_COLUMN_FRACTION = 0.5


_activated = False
_hide_on_show_filter: Any = None
_launch_screen_active = False
_document_observer: Any = None
_half_layout_filter: Any = None
_half_layout_pending = False


def is_experimental_mode_session() -> bool:
    """Experimental mode is the only mode: 3D viewport plus assistant chat."""
    return True


def in_launch_state() -> bool:
    """True while experimental mode shows the launch screen (no open documents).

    Computed live from the document list so callers that run before the
    first deferred sync (e.g. the startup assistant open) see the correct
    state; falls back to the orchestrated flag when the App API is missing.
    """
    try:
        return len(App.listDocuments()) == 0
    except Exception:
        return _launch_screen_active


def _warn(message: str) -> None:
    App.Console.PrintWarning(f"{message}\n")


def _main_window() -> Any:
    try:
        return Gui.getMainWindow()
    except Exception:
        return None


def activate() -> None:
    """Apply experimental mode to the started GUI. Safe to call once at startup."""
    global _activated
    if _activated:
        return
    main_window = _main_window()
    if main_window is None:
        _warn("Cadex experimental mode could not find the main window.")
        return
    _activated = True
    _force_experimental_workbench()
    _hide_chrome()
    # Workbench toolbars and docks are built lazily during startup, often after
    # this first pass, so schedule follow-up hides to catch late-built chrome.
    _schedule_deferred_hide_chrome()
    _connect_workbench_guard(main_window)
    _install_half_layout_filter(main_window)
    _connect_edit_lockdown_observer()
    # The launch/parts state controller decides when the assistant dock is
    # pinned (documents open) or hidden behind the launch screen (none).
    _connect_document_observer()
    _schedule_launch_state_sync()
    # Reserved for future migrations of the experimental-mode layout.
    App.ParamGet(PREFERENCE_GROUP).SetInt("ExperimentalModeInitialized", 1)


def _schedule_deferred_hide_chrome() -> None:
    """Re-run _hide_chrome after startup builds chrome that the first pass missed.

    FreeCAD constructs a workbench's toolbars and docks lazily, sometimes after
    activate()'s initial hide. A few spaced follow-up passes hide chrome that
    appears once the main window has finished settling, without leaving a timer
    running for the whole session.
    """
    from PySide import QtCore

    for delay_ms in (0, 150, 500, 1500):
        QtCore.QTimer.singleShot(delay_ms, _hide_chrome)


def _force_experimental_workbench() -> None:
    """Experimental mode is always PartDesign; the user's autoload is untouched."""
    try:
        active = Gui.activeWorkbench().name()
    except Exception:
        active = ""
    if active == EXPERIMENTAL_MODE_WORKBENCH:
        return
    try:
        Gui.activateWorkbench(EXPERIMENTAL_MODE_WORKBENCH)
    except Exception as exc:
        _warn(f"Cadex experimental mode could not activate PartDesign: {exc}")


def _pin_assistant_dock(main_window: Any) -> None:
    """Show the assistant as a fixed, title-bar-less right dock."""
    from PySide import QtCore, QtWidgets

    dock = main_window.findChild(QtWidgets.QDockWidget, ASSISTANT_DOCK_NAME)
    if dock is None:
        try:
            import CadexGui

            CadexGui.show_assistant_for_active_workbench()
        except Exception as exc:
            _warn(f"Cadex experimental mode could not open the assistant: {exc}")
        dock = main_window.findChild(QtWidgets.QDockWidget, ASSISTANT_DOCK_NAME)
    if dock is None:
        _warn("Cadex experimental mode could not find the assistant panel.")
        return
    # A restored manual layout may have left the dock floating, tabbed, or
    # parked in an overlay; normalize to a plain right dock.
    dock.setFloating(False)
    main_window.addDockWidget(QtCore.Qt.RightDockWidgetArea, dock)
    dock.setFeatures(QtWidgets.QDockWidget.NoDockWidgetFeatures)
    dock.setTitleBarWidget(QtWidgets.QWidget(dock))
    dock.setMinimumWidth(ASSISTANT_DOCK_MINIMUM_WIDTH)
    dock.show()
    dock.raise_()
    _schedule_half_layout()


def _hide_chrome() -> None:
    """Hide all manual chrome; runs at activation and after workbench switches."""
    from PySide import QtWidgets

    main_window = _main_window()
    if main_window is None:
        return
    status_bar = main_window.statusBar()
    if status_bar is not None:
        # Startup code re-shows the status bar after activation (e.g.
        # BlankWorkbench::deactivated()); keep it hidden for the session.
        _install_hide_on_show_filter(main_window, status_bar)
    for toolbar in main_window.findChildren(QtWidgets.QToolBar):
        toolbar.hide()
        action = toolbar.toggleViewAction()
        if action is not None:
            # Also engages ToolBarManager::saveState()'s ignoreSave guard.
            action.setVisible(False)
    for dock in main_window.findChildren(QtWidgets.QDockWidget):
        if dock.objectName() in ALLOWED_DOCK_NAMES:
            continue
        _suppress_dock(dock)
    _hide_overlay_containers(main_window)
    _hide_mdi_tab_bar(main_window)
    # Native-route lockdown re-applies with the chrome pass: workbench
    # activation rebuilds menus and re-registers shortcuts.
    _apply_minimal_menu(main_window)
    _strip_native_shortcuts(main_window)
    _lock_tree_interactions(main_window)


def _hide_overlay_containers(main_window: Any) -> None:
    """Hide overlay tab containers that park docks outside the dock areas."""
    from PySide import QtWidgets

    for tab_widget in main_window.findChildren(QtWidgets.QTabWidget):
        try:
            class_name = str(tab_widget.metaObject().className())
        except Exception:
            continue
        if "OverlayTabWidget" in class_name:
            tab_widget.hide()


def _suppress_dock(dock: Any) -> None:
    """Hide a dock and keep it hidden for the rest of the session."""
    dock.hide()
    action = dock.toggleViewAction()
    if action is not None:
        action.setVisible(False)
    if bool(dock.property(_SUPPRESSED_PROPERTY)):
        return
    dock.setProperty(_SUPPRESSED_PROPERTY, True)
    dock.visibilityChanged.connect(
        lambda visible, dock=dock: _queue_dock_rehide(dock) if visible else None
    )


def _queue_dock_rehide(dock: Any) -> None:
    """Re-hide via the event loop; never hide() inside visibilityChanged."""
    from PySide import QtCore

    if bool(dock.property(_REHIDE_PENDING_PROPERTY)):
        return
    dock.setProperty(_REHIDE_PENDING_PROPERTY, True)

    def rehide() -> None:
        dock.setProperty(_REHIDE_PENDING_PROPERTY, False)
        if dock.objectName() == TASKS_DOCK_NAME:
            _close_active_task_dialog()
        dock.hide()

    QtCore.QTimer.singleShot(0, rehide)


def _close_active_task_dialog() -> None:
    """Chat-only modeling: no task panel may keep a dialog session open."""
    try:
        if Gui.Control.activeDialog():
            Gui.Control.closeDialog()
    except Exception as exc:
        _warn(f"Cadex experimental mode could not close a task dialog: {exc}")


def _install_hide_on_show_filter(main_window: Any, widget: Any) -> None:
    """Hide ``widget`` now and whenever something re-shows it."""
    global _hide_on_show_filter
    from PySide import QtCore

    if _hide_on_show_filter is None:

        class _HideOnShow(QtCore.QObject):
            def eventFilter(self, watched: Any, event: Any) -> bool:
                if event.type() == QtCore.QEvent.Show:
                    watched.hide()
                return False

        _hide_on_show_filter = _HideOnShow(main_window)
    widget.removeEventFilter(_hide_on_show_filter)
    widget.installEventFilter(_hide_on_show_filter)
    widget.hide()


def _hide_mdi_tab_bar(main_window: Any) -> None:
    from PySide import QtWidgets

    tab_bar = main_window.findChild(QtWidgets.QTabBar, "mdiAreaTabBar")
    if tab_bar is not None:
        _install_hide_on_show_filter(main_window, tab_bar)


# ---------------------------------------------------------------------------
# Launch <-> Parts state controller
# ---------------------------------------------------------------------------


class _ExperimentalModeDocumentObserver:
    """Schedules a launch-state sync on every document create/delete.

    slotDeletedDocument fires before the document is removed from the list;
    the deferred sync observes the post-removal state.
    """

    def slotCreatedDocument(self, _doc: Any) -> None:
        _schedule_launch_state_sync()

    def slotFinishRestoreDocument(self, _doc: Any) -> None:
        # Opening an existing file keys off a fully-restored document rather
        # than racing slotCreatedDocument, which fires mid-restore.
        _schedule_launch_state_sync()

    def slotDeletedDocument(self, _doc: Any) -> None:
        _schedule_launch_state_sync()


def _connect_document_observer() -> None:
    global _document_observer
    if _document_observer is not None:
        return
    observer = _ExperimentalModeDocumentObserver()
    try:
        App.addDocumentObserver(observer)
    except Exception as exc:
        _warn(f"Cadex experimental mode could not watch documents: {exc}")
        return
    _document_observer = observer


def _schedule_launch_state_sync() -> None:
    """Always defer: document events fire mid-transition."""
    from PySide import QtCore

    QtCore.QTimer.singleShot(0, _sync_launch_state)


def _sync_launch_state() -> None:
    """Idempotent two-state switch: launch screen <-> viewport + chat."""
    global _launch_screen_active
    main_window = _main_window()
    if main_window is None:
        return
    try:
        has_documents = len(App.listDocuments()) > 0
    except Exception:
        return
    _launch_screen_active = not has_documents
    # Document-observer events can fire before the panel is built or before a
    # document has finished restoring. Each step is individually guarded so a
    # premature call simply no-ops; the next event re-runs this sync.
    if has_documents:
        try:
            _close_start_view(main_window)
            _pin_assistant_dock(main_window)
            _repair_assistant_panel()
            _sync_parameters_dock()
            _pin_tree_dock(main_window)
            _sync_script_view_dock()
        except Exception as exc:
            _warn(f"Cadex experimental mode could not pin the workspace: {exc}")
    else:
        try:
            _hide_assistant_dock(main_window)
            _hide_parameters_dock(main_window)
            _hide_tree_dock(main_window)
            _hide_script_view_dock(main_window)
            # Idempotent find-or-create; also raises an existing StartView.
            Gui.runCommand("Start_Start", 0)
        except Exception as exc:
            _warn(f"Cadex experimental mode could not open the launch screen: {exc}")


def _sync_parameters_dock() -> None:
    """Show parameter sliders under the assistant when XScript models exist."""
    try:
        import CadexParametersPanel

        CadexParametersPanel.sync_experimental_mode_dock()
    except Exception as exc:
        _warn(f"Cadex experimental mode could not sync the parameters panel: {exc}")


def _hide_parameters_dock(main_window: Any) -> None:
    from PySide import QtWidgets

    dock = main_window.findChild(QtWidgets.QDockWidget, PARAMETERS_DOCK_NAME)
    if dock is not None:
        dock.hide()


def _sync_script_view_dock() -> None:
    """Show the read-only script view once the project script has content."""
    try:
        import CadexScriptView

        CadexScriptView.sync_experimental_mode_dock()
    except Exception as exc:
        _warn(f"Cadex experimental mode could not sync the script view: {exc}")


def _hide_script_view_dock(main_window: Any) -> None:
    from PySide import QtWidgets

    dock = main_window.findChild(QtWidgets.QDockWidget, SCRIPT_VIEW_DOCK_NAME)
    if dock is not None:
        dock.hide()


def _pin_tree_dock(main_window: Any) -> None:
    """Show the model tree as a locked right-side panel while a document is open.

    MainWindow::updateTreeView force-creates the standalone tree dock on the
    right for experimental-mode sessions, so here we only normalize and reveal it.
    Experimental mode hides all chrome, so the dock must not be closable or floatable
    (there is no menu left to bring it back); like the parameters panel it is
    not repositioned at runtime, which would sever the other panels' signals.
    """
    from PySide import QtWidgets

    dock = main_window.findChild(QtWidgets.QDockWidget, TREE_DOCK_NAME)
    if dock is None:
        return
    dock.setFloating(False)
    dock.setFeatures(QtWidgets.QDockWidget.NoDockWidgetFeatures)
    dock.show()
    dock.raise_()


def _hide_tree_dock(main_window: Any) -> None:
    from PySide import QtWidgets

    dock = main_window.findChild(QtWidgets.QDockWidget, TREE_DOCK_NAME)
    if dock is not None:
        dock.hide()


def _hide_assistant_dock(main_window: Any) -> None:
    """The assistant dock is excluded from _suppress_dock, so a plain hide
    does not fight the re-hide guards and _pin_assistant_dock re-shows it."""
    from PySide import QtWidgets

    dock = main_window.findChild(QtWidgets.QDockWidget, ASSISTANT_DOCK_NAME)
    if dock is not None:
        dock.hide()


def _repair_assistant_panel() -> None:
    """Heal the chat panel if a dock-layout restore severed its signals."""
    try:
        import CadexGui

        CadexGui.repair_assistant_panel_if_needed()
    except Exception as exc:
        _warn(f"Cadex experimental mode could not verify the assistant panel: {exc}")


def _close_start_view(main_window: Any) -> None:
    from PySide import QtWidgets

    view = main_window.findChild(QtWidgets.QWidget, "StartView")
    widget = view
    while widget is not None:
        if isinstance(widget, QtWidgets.QMdiSubWindow):
            widget.close()
            return
        widget = widget.parentWidget()


# ---------------------------------------------------------------------------
# Native-route lockdown (Phase 3.2)
#
# The AI drives all modeling; the only sanctioned interactions are chat,
# sliders, tree selection, the read-only script view, and viewport
# navigation. Everything else — menus, shortcuts, tree context menus,
# double-click edit sessions — is blocked. Preferences stays reachable:
# the API keys live there.
# ---------------------------------------------------------------------------

# Our own menu actions carry object names so the shortcut strip spares them.
_MINIMAL_MENU_PROPERTY = "CadexMinimalMenuAction"
_ALLOWED_SHORTCUT_ACTIONS = frozenset(
    {
        "Std_Quit",
        "Std_About",
        "Cadex_OpenPreferences",
    }
)

_tree_lockdown_filter: Any = None
_edit_lockdown_observer: Any = None
_edit_watchdog_pending = False
_sanctioned_edit_names: set[str] = set()


def sanction_native_edit(object_name: str) -> None:
    """Mark one upcoming native edit session (e.g. sketch edit) as tool-driven.

    Called by the xscript edit tools right before ``setEdit``; the edit
    watchdog resets every edit session that was not sanctioned this way
    (viewport double-clicks, stray native routes). The sanction is consumed
    when the edit session closes.
    """
    name = str(object_name or "").strip()
    if name:
        _sanctioned_edit_names.add(name)


def _menu_command(command_name: str) -> Any:
    def run() -> None:
        try:
            Gui.runCommand(command_name, 0)
        except Exception as exc:
            _warn(f"Cadex experimental mode could not run {command_name}: {exc}")

    return run


def _apply_minimal_menu(main_window: Any) -> None:
    """One minimal menu: About, Preferences, Quit — rebuilt after menu churn.

    MenuManager rebuilds the native menus on every workbench activation, so
    this reruns with each chrome pass instead of trying to hide the menu bar
    (macOS keeps a global menu bar regardless). The menu roles relocate the
    entries into the macOS application menu.
    """
    from PySide import QtGui
    from CadexParametersPanel import _connect_slot

    menu_bar = main_window.menuBar()
    if menu_bar is None:
        return
    actions = menu_bar.actions()
    if len(actions) == 1 and bool(actions[0].property(_MINIMAL_MENU_PROPERTY)):
        return  # Already minimal; nothing rebuilt the menus since.
    menu_bar.clear()
    menu = menu_bar.addMenu("Cadex")
    menu_action = menu.menuAction()
    menu_action.setProperty(_MINIMAL_MENU_PROPERTY, True)

    about = menu.addAction("About Cadex")
    about.setMenuRole(QtGui.QAction.AboutRole)
    _connect_slot(about.triggered, "invoke", _menu_command("Std_About"), menu)

    preferences = menu.addAction("Preferences…")
    preferences.setMenuRole(QtGui.QAction.PreferencesRole)
    preferences.setObjectName("Cadex_OpenPreferences")
    preferences.setShortcut(QtGui.QKeySequence("Ctrl+,"))
    _connect_slot(
        preferences.triggered, "invoke", _menu_command("Cadex_OpenPreferences"), menu
    )

    quit_action = menu.addAction("Quit")
    quit_action.setMenuRole(QtGui.QAction.QuitRole)
    quit_action.setObjectName("Std_Quit")
    quit_action.setShortcut(QtGui.QKeySequence("Ctrl+Q"))
    _connect_slot(quit_action.triggered, "invoke", _menu_command("Std_Quit"), menu)


def _strip_native_shortcuts(main_window: Any) -> None:
    """Clear every keyboard shortcut except the allow-listed ones.

    Workbench activation re-registers command shortcuts, so this reruns with
    each chrome pass. Text-editing shortcuts inside the chat input are
    widget-internal (not main-window QActions) and stay functional.
    """
    from PySide import QtGui

    for action in main_window.findChildren(QtGui.QAction):
        if str(action.objectName() or "") in _ALLOWED_SHORTCUT_ACTIONS:
            continue
        try:
            if not action.shortcut().isEmpty():
                action.setShortcut(QtGui.QKeySequence())
        except Exception:
            continue


def _lock_tree_interactions(main_window: Any) -> None:
    """Block the tree's context menu and double-click edit routes.

    Selection and expansion stay; right-click command menus and
    double-click-to-edit are native modeling routes and are blocked.
    """
    global _tree_lockdown_filter
    from PySide import QtCore, QtWidgets

    if _tree_lockdown_filter is None:

        class _TreeLockdown(QtCore.QObject):
            def eventFilter(self, _watched: Any, event: Any) -> bool:
                return event.type() in (
                    QtCore.QEvent.ContextMenu,
                    QtCore.QEvent.MouseButtonDblClick,
                )

        _tree_lockdown_filter = _TreeLockdown(main_window)
    dock = main_window.findChild(QtWidgets.QDockWidget, TREE_DOCK_NAME)
    if dock is None:
        return
    for tree in dock.findChildren(QtWidgets.QTreeWidget):
        for target in (tree, tree.viewport()):
            if target is None:
                continue
            target.removeEventFilter(_tree_lockdown_filter)
            target.installEventFilter(_tree_lockdown_filter)


class _EditLockdownObserver:
    """Reset native edit sessions that no tool sanctioned (D11 watchdog)."""

    def slotInEdit(self, _view_provider: Any) -> None:
        _schedule_edit_watchdog()

    def slotResetEdit(self, _view_provider: Any) -> None:
        # One edit session at a time: closing it consumes the sanction.
        _sanctioned_edit_names.clear()


def _schedule_edit_watchdog() -> None:
    """Defer: slotInEdit fires inside setEdit; never resetEdit reentrantly."""
    global _edit_watchdog_pending
    from PySide import QtCore

    if _edit_watchdog_pending:
        return
    _edit_watchdog_pending = True
    QtCore.QTimer.singleShot(0, _run_edit_watchdog)


def _run_edit_watchdog() -> None:
    global _edit_watchdog_pending
    _edit_watchdog_pending = False
    try:
        from CadexEditState import active_edit_state

        gui_document = getattr(Gui, "editDocument", lambda: None)() or getattr(
            Gui, "ActiveDocument", None
        )
        state = active_edit_state(gui_document)
        if not state.active:
            return
        name = str(getattr(state.document_object, "Name", "") or "")
        if name and name in _sanctioned_edit_names:
            return
        reset_edit = getattr(gui_document, "resetEdit", None)
        if callable(reset_edit):
            reset_edit()
            _warn(
                f"Cadex closed an unsanctioned edit session on {name or 'an object'}; "
                "modeling goes through the assistant."
            )
    except Exception as exc:
        _warn(f"Cadex edit watchdog failed: {exc}")


def _connect_edit_lockdown_observer() -> None:
    global _edit_lockdown_observer
    if _edit_lockdown_observer is not None:
        return
    observer = _EditLockdownObserver()
    try:
        Gui.addDocumentObserver(observer)
    except Exception as exc:
        _warn(f"Cadex experimental mode could not watch edit sessions: {exc}")
        return
    _edit_lockdown_observer = observer


# ---------------------------------------------------------------------------
# 50/50 layout (viewport left, panel column right)
# ---------------------------------------------------------------------------


def _right_column_docks(main_window: Any) -> list[Any]:
    """Visible right-area docks, in the fixed registration order."""
    from PySide import QtCore, QtWidgets

    docks = []
    for name in (
        ASSISTANT_DOCK_NAME,
        PARAMETERS_DOCK_NAME,
        TREE_DOCK_NAME,
        SCRIPT_VIEW_DOCK_NAME,
    ):
        dock = main_window.findChild(QtWidgets.QDockWidget, name)
        if (
            dock is not None
            and dock.isVisible()
            and not dock.isFloating()
            and main_window.dockWidgetArea(dock) == QtCore.Qt.RightDockWidgetArea
        ):
            docks.append(dock)
    return docks


def _apply_half_layout() -> None:
    """Resize the right dock column to half the window width.

    resizeDocks only — QMainWindow.addDockWidget/splitDockWidget on
    FreeCAD-managed docks at runtime severs the other panels' Python signal
    connections (verified on the parameters panel), so the split is enforced
    purely by re-issuing sizes on the docks where registration put them.
    """
    from PySide import QtCore

    global _half_layout_pending
    _half_layout_pending = False
    main_window = _main_window()
    if main_window is None or in_launch_state():
        return
    docks = _right_column_docks(main_window)
    if not docks:
        return
    width = max(
        int(main_window.width() * RIGHT_COLUMN_FRACTION),
        ASSISTANT_DOCK_MINIMUM_WIDTH,
    )
    main_window.resizeDocks(docks, [width] * len(docks), QtCore.Qt.Horizontal)


def _schedule_half_layout() -> None:
    """Coalesce layout passes onto the next event-loop turn."""
    from PySide import QtCore

    global _half_layout_pending
    if _half_layout_pending:
        return
    _half_layout_pending = True
    QtCore.QTimer.singleShot(0, _apply_half_layout)


def _install_half_layout_filter(main_window: Any) -> None:
    """Re-assert the 50/50 split whenever the window shows or resizes."""
    global _half_layout_filter
    from PySide import QtCore

    if _half_layout_filter is not None:
        return

    class _HalfLayout(QtCore.QObject):
        def eventFilter(self, _watched: Any, event: Any) -> bool:
            if event.type() in (QtCore.QEvent.Show, QtCore.QEvent.Resize):
                _schedule_half_layout()
            return False

    _half_layout_filter = _HalfLayout(main_window)
    main_window.installEventFilter(_half_layout_filter)


def _connect_workbench_guard(main_window: Any) -> None:
    """Workbench activation (e.g. sketch edit) re-shows chrome; re-hide it."""
    from PySide import QtCore

    def rehide_after_activation(_workbench_name: str = "") -> None:
        QtCore.QTimer.singleShot(0, _hide_chrome)

    try:
        main_window.workbenchActivated.connect(rehide_after_activation)
    except Exception as exc:
        _warn(f"Cadex experimental mode could not watch workbench activation: {exc}")
