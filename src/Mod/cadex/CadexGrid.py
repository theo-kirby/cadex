# SPDX-License-Identifier: LGPL-2.1-or-later

"""Fusion-style always-on 3D grid for Cadex.

Cadex-owned viewport grid: every 3D view gets a two-tier (minor/major) line
grid on the global XY plane, rendered from a Coin ``SoSeparator`` that this
module builds and inserts into the view's scene graph. No Draft machinery is
involved.

Behavior:

- A lightweight observer on the MDI area initializes the grid for each 3D
  view at most once. A per-view camera observer keeps minor lines within a
  readable screen-space range and displays the minor/major spacing in the
  viewport.
- Grid visibility is stored in the ``Mod/cadex`` ``ShowGrid`` boolean
  preference (default: enabled) so views opened later follow suit. The
  native ``Cadex_ToggleGrid`` command owns the View-menu action and calls
  :func:`toggle_grid`.
- The automatic always-on-at-startup behavior sits behind the ``Mod/cadex``
  ``AlwaysShowGrid`` boolean preference (default: enabled) as a master
  kill-switch.

The module imports safely outside FreeCAD (guarded imports) so tooling such
as linters and test collectors can load it.
"""

from __future__ import annotations

import math
from typing import Any

try:
    import FreeCAD as App
except ImportError:  # pragma: no cover - only outside FreeCAD (tooling/tests)
    App = None  # type: ignore[assignment]

_PARAM_ROOT = "User parameter:BaseApp/Preferences/"
_CADEX_PARAM_PATH = _PARAM_ROOT + "Mod/cadex"

_TARGET_GRID_PIXELS = 28.0
_MIN_GRID_PIXELS = 18.0
_MAX_GRID_PIXELS = 44.0
_MIN_GRID_SPACING_MM = 1.0e-9
_MAX_GRID_SPACING_MM = 1.0e12
_IMPERIAL_SCHEMAS = frozenset({2, 3, 5, 7})
_FRACTIONAL_INCH_SCHEMAS = frozenset({2, 5})
_FOOT_BASED_SCHEMAS = frozenset({5, 7})
_MM_PER_INCH = 25.4

_MINOR_COLOR = (0.44, 0.47, 0.51)
_MAJOR_COLOR = (0.60, 0.64, 0.68)
_MINOR_TRANSPARENCY = 0.55
_MAJOR_TRANSPARENCY = 0.25

_adaptive_controllers: list[Any] = []
_observer_installed = False
_maintenance_timer: Any = None
_main_window_filter: Any = None
_close_suspended = False


def _document_restore_active() -> bool:
    if App is None:
        return False
    is_restoring = getattr(App, "isRestoring", None)
    if callable(is_restoring):
        try:
            if bool(is_restoring()):
                return True
        except Exception:
            pass
    document = getattr(App, "ActiveDocument", None)
    return document is not None and bool(getattr(document, "Restoring", False))


def _nearest_125(value: float) -> float:
    """Return the nearest positive value in the ``1, 2, 5 x 10^n`` series."""
    if not math.isfinite(value) or value <= 0:
        raise ValueError("grid spacing input must be finite and positive")
    exponent = math.floor(math.log10(value))
    candidates = [
        step * (10.0**power)
        for power in range(exponent - 1, exponent + 2)
        for step in (1.0, 2.0, 5.0)
    ]
    return min(candidates, key=lambda candidate: abs(math.log(candidate / value)))


def _nice_grid_spacing(raw_mm: float, unit_schema: int) -> float:
    """Quantize one raw spacing to an engineering-friendly internal value."""
    raw_mm = min(max(float(raw_mm), _MIN_GRID_SPACING_MM), _MAX_GRID_SPACING_MM)
    if unit_schema not in _IMPERIAL_SCHEMAS:
        return _nearest_125(raw_mm)

    raw_inches = raw_mm / _MM_PER_INCH
    if unit_schema in _FRACTIONAL_INCH_SCHEMAS and raw_inches < 1.0:
        spacing_inches = 2.0 ** round(math.log2(raw_inches))
    elif unit_schema in _FOOT_BASED_SCHEMAS and raw_inches >= 6.0:
        spacing_inches = 12.0 * _nearest_125(raw_inches / 12.0)
    else:
        spacing_inches = _nearest_125(raw_inches)
    return min(
        max(spacing_inches * _MM_PER_INCH, _MIN_GRID_SPACING_MM),
        _MAX_GRID_SPACING_MM,
    )


def _select_grid_spacing(
    world_units_per_pixel: float,
    current_spacing_mm: float | None,
    unit_schema: int,
) -> float:
    """Choose a stable spacing while keeping minor lines visually readable."""
    if not math.isfinite(world_units_per_pixel) or world_units_per_pixel <= 0:
        raise ValueError("world units per pixel must be finite and positive")
    if current_spacing_mm is not None and current_spacing_mm > 0:
        current_pixels = current_spacing_mm / world_units_per_pixel
        if _MIN_GRID_PIXELS <= current_pixels <= _MAX_GRID_PIXELS:
            return current_spacing_mm
    return _nice_grid_spacing(world_units_per_pixel * _TARGET_GRID_PIXELS, unit_schema)


def _xyz(vector: Any) -> tuple[float, float, float]:
    """Return XYZ components from a FreeCAD or Coin vector-like value."""
    if hasattr(vector, "x"):
        return float(vector.x), float(vector.y), float(vector.z)
    return float(vector[0]), float(vector[1]), float(vector[2])


def _ray_plane_intersection(
    ray_start: Any,
    ray_end: Any,
    plane_origin: Any,
    plane_normal: Any,
) -> tuple[float, float, float] | None:
    """Intersect one viewport projection line with the grid plane."""
    start = _xyz(ray_start)
    end = _xyz(ray_end)
    origin = _xyz(plane_origin)
    normal = _xyz(plane_normal)
    direction = tuple(end[index] - start[index] for index in range(3))
    denominator = sum(normal[index] * direction[index] for index in range(3))
    normal_length = math.sqrt(sum(component * component for component in normal))
    direction_length = math.sqrt(sum(component * component for component in direction))
    if normal_length <= 0 or direction_length <= 0:
        return None
    if abs(denominator) <= normal_length * direction_length * 1.0e-10:
        return None
    distance = sum(normal[index] * (origin[index] - start[index]) for index in range(3))
    parameter = distance / denominator
    point = tuple(start[index] + parameter * direction[index] for index in range(3))
    return point if all(math.isfinite(component) for component in point) else None


def _distance(first: Any, second: Any) -> float:
    a = _xyz(first)
    b = _xyz(second)
    return math.sqrt(sum((a[index] - b[index]) ** 2 for index in range(3)))


def _world_units_per_pixel(view: Any, grid: Any) -> float:
    """Measure local model-space scale where the camera sees the grid plane."""
    width, height = (int(value) for value in view.getSize())
    if width < 2 or height < 2:
        raise ValueError("3D view has no measurable viewport")

    center_x = width // 2
    center_y = height // 2
    sample_pixels = max(4, min(24, min(width, height) // 16))
    origin = grid.plane_origin()
    normal = grid.plane_normal()

    intersections: list[tuple[float, float, float] | None] = []
    for x, y in (
        (center_x, center_y),
        (center_x + sample_pixels, center_y),
        (center_x, center_y + sample_pixels),
    ):
        ray_start, ray_end = view.projectPointToLine((x, y))
        intersections.append(
            _ray_plane_intersection(ray_start, ray_end, origin, normal)
        )

    center, horizontal, vertical = intersections
    samples = [
        _distance(center, point) / sample_pixels
        for point in (horizontal, vertical)
        if center is not None and point is not None
    ]
    if samples:
        measured = max(samples)
        if math.isfinite(measured) and measured > 0:
            return measured

    # An edge-on grid plane cannot be intersected robustly. The focal plane
    # still provides a finite camera-scale estimate until the grid is visible
    # enough for exact plane intersections again.
    center = view.getPointOnFocalPlane((center_x, center_y))
    horizontal = view.getPointOnFocalPlane((center_x + sample_pixels, center_y))
    vertical = view.getPointOnFocalPlane((center_x, center_y + sample_pixels))
    measured = max(_distance(center, horizontal), _distance(center, vertical))
    measured /= sample_pixels
    if not math.isfinite(measured) or measured <= 0:
        raise ValueError("camera scale could not be measured")
    return measured


def _grid_plane_point(view: Any, grid: Any, pixel: tuple[int, int]) -> Any:
    """Project one viewport pixel onto the grid plane (None off-plane)."""
    ray_start, ray_end = view.projectPointToLine(pixel)
    return _ray_plane_intersection(
        ray_start, ray_end, grid.plane_origin(), grid.plane_normal()
    )


def _warn(message: str) -> None:
    """Print a console warning when FreeCAD is available."""
    if App is not None:
        App.Console.PrintWarning(f"Cadex grid: {message}\n")


def _unit_schema() -> int:
    if App is None:
        return 0
    try:
        return int(App.Units.getSchema())
    except (AttributeError, TypeError, ValueError):
        return App.ParamGet(_PARAM_ROOT + "Units").GetInt("UserSchema", 0)


def _format_length(value_mm: float) -> str:
    if App is None:
        return f"{value_mm:g} mm"
    try:
        return str(App.Units.Quantity(value_mm, App.Units.Length).UserString)
    except (AttributeError, TypeError, ValueError):
        return f"{value_mm:g} mm"


def _active_view_parent() -> Any:
    """Return the QWidget containing the active MDI view."""
    try:
        import FreeCADGui as Gui
        from PySide import QtWidgets

        mdi_area = Gui.getMainWindow().findChild(QtWidgets.QMdiArea)
        sub_window = mdi_area.currentSubWindow() if mdi_area is not None else None
        if sub_window is None:
            return None
        return sub_window.widget() or sub_window
    except (AttributeError, RuntimeError):
        return None


class _GridTracker:
    """Cadex-owned Coin line grid on the global XY plane for one 3D view.

    Builds a two-tier (minor/major) ``SoIndexedLineSet``-free line grid from
    plain ``SoCoordinate3`` + ``SoLineSet`` nodes under one unpickable
    ``SoSeparator`` and inserts it into the view's scene graph. Line
    positions are always integer multiples of ``space`` in world
    coordinates; the tracker recenters by whole major-cell quanta so lines
    never drift as the camera pans.
    """

    def __init__(self, view: Any) -> None:
        from pivy import coin

        self.view = view
        self.space = 10.0
        self.numlines = 100
        self.mainlines = _major_every()
        self.center = (0.0, 0.0)
        self._built_key: tuple | None = None
        self._in_scene = False

        self._root = coin.SoSeparator()
        self._root.setName("CadexGrid")
        pick_style = coin.SoPickStyle()
        pick_style.style = coin.SoPickStyle.UNPICKABLE
        self._root.addChild(pick_style)
        light_model = coin.SoLightModel()
        light_model.model = coin.SoLightModel.BASE_COLOR
        self._root.addChild(light_model)

        self._switch = coin.SoSwitch()
        self._switch.whichChild = coin.SO_SWITCH_NONE
        self._root.addChild(self._switch)

        content = coin.SoSeparator()
        self._translation = coin.SoTranslation()
        content.addChild(self._translation)
        self._minor_coords, minor_group = self._make_line_group(
            coin, _MINOR_COLOR, _MINOR_TRANSPARENCY, 1.0
        )
        self._major_coords, major_group = self._make_line_group(
            coin, _MAJOR_COLOR, _MAJOR_TRANSPARENCY, 2.0
        )
        self._minor_lines = minor_group[-1]
        self._major_lines = major_group[-1]
        content.addChild(minor_group[0])
        content.addChild(major_group[0])
        self._switch.addChild(content)

        view.getSceneGraph().addChild(self._root)
        self._in_scene = True

    @staticmethod
    def _make_line_group(
        coin: Any, color: tuple, transparency: float, line_width: float
    ) -> tuple:
        group = coin.SoSeparator()
        material = coin.SoMaterial()
        material.diffuseColor = color
        material.transparency = transparency
        group.addChild(material)
        style = coin.SoDrawStyle()
        style.lineWidth = line_width
        group.addChild(style)
        coords = coin.SoCoordinate3()
        group.addChild(coords)
        lines = coin.SoLineSet()
        group.addChild(lines)
        return coords, (group, lines)

    # -- grid plane -----------------------------------------------------

    def plane_origin(self) -> tuple[float, float, float]:
        return (self.center[0], self.center[1], 0.0)

    @staticmethod
    def plane_normal() -> tuple[float, float, float]:
        return (0.0, 0.0, 1.0)

    # -- geometry -------------------------------------------------------

    def recenter(self, x: float, y: float) -> None:
        """Move the grid to the major-cell quantum nearest ``(x, y)``."""
        quantum = self.space * max(1, int(self.mainlines))
        if not (math.isfinite(quantum) and quantum > 0):
            return
        snapped = (round(x / quantum) * quantum, round(y / quantum) * quantum)
        if snapped != self.center:
            self.center = snapped

    def update(self) -> None:
        """Rebuild the line sets when spacing, extent or center changed."""
        key = (self.space, self.numlines, self.mainlines, self.center)
        if key == self._built_key:
            return
        half = max(1, int(self.numlines) // 2)
        major_every = max(1, int(self.mainlines))
        spacing = float(self.space)
        extent = half * spacing

        minor_points: list[tuple[float, float, float]] = []
        major_points: list[tuple[float, float, float]] = []
        for index in range(-half, half + 1):
            offset = index * spacing
            target = major_points if index % major_every == 0 else minor_points
            target.append((offset, -extent, 0.0))
            target.append((offset, extent, 0.0))
            target.append((-extent, offset, 0.0))
            target.append((extent, offset, 0.0))

        self._translation.translation = (self.center[0], self.center[1], 0.0)
        self._set_lines(self._minor_coords, self._minor_lines, minor_points)
        self._set_lines(self._major_coords, self._major_lines, major_points)
        self._built_key = key

    @staticmethod
    def _set_lines(coords: Any, lines: Any, points: list) -> None:
        coords.point.setValues(0, len(points), points)
        coords.point.setNum(len(points))
        counts = [2] * (len(points) // 2)
        lines.numVertices.setValues(0, len(counts), counts)
        lines.numVertices.setNum(len(counts))

    # -- visibility -----------------------------------------------------

    @property
    def Visible(self) -> bool:
        from pivy import coin

        return int(self._switch.whichChild.getValue()) == coin.SO_SWITCH_ALL

    def set_visible(self, visible: bool) -> None:
        from pivy import coin

        self._switch.whichChild = (
            coin.SO_SWITCH_ALL if visible else coin.SO_SWITCH_NONE
        )

    def detach_from_scene(self) -> None:
        """Remove the grid node from a still-alive view scene graph."""
        if not self._in_scene:
            return
        self._in_scene = False
        try:
            self.view.getSceneGraph().removeChild(self._root)
        except (AttributeError, ReferenceError, RuntimeError):
            pass


class _AdaptiveGridController:
    """Keep one grid tracker legible and report its scale for one 3D view."""

    def __init__(self, view: Any, grid: Any, parent: Any) -> None:
        self.view = view
        self.grid = grid
        self.parent = None
        self.label = None
        self.camera = None
        self.camera_sensor = None
        self.spacing_mm: float | None = None
        self.unit_schema: int | None = None
        self.update_pending = False
        self.disposed = False
        self.last_error = ""
        self.ensure_parent(parent)
        self._attach_camera_sensor()
        self.schedule_update()

    def matches(self, view: Any) -> bool:
        try:
            return bool(self.view == view)
        except (ReferenceError, RuntimeError):
            return False

    def ensure_parent(self, parent: Any) -> None:
        if parent is None or self.label is not None:
            return
        try:
            from PySide import QtCore, QtWidgets

            label = QtWidgets.QLabel(parent)
            label.setObjectName("CadexGridScale")
            label.setTextFormat(QtCore.Qt.PlainText)
            label.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents, True)
            label.setFocusPolicy(QtCore.Qt.NoFocus)
            label.setStyleSheet(
                "QLabel#CadexGridScale {"
                "background-color: rgba(25, 29, 36, 218);"
                "color: #f4f6f8;"
                "border: 1px solid rgba(255, 255, 255, 42);"
                "border-radius: 3px;"
                "padding: 4px 7px;"
                "}"
            )
            label.hide()
            self.parent = parent
            self.label = label
        except (AttributeError, RuntimeError, TypeError) as exc:
            self._report_error(f"scale indicator creation failed: {exc}")

    def _report_error(self, message: str) -> None:
        if message != self.last_error:
            self.last_error = message
            _warn(message)

    def _attach_camera_sensor(self) -> None:
        try:
            camera = self.view.getCameraNode()
            if self.camera is not None and camera == self.camera:
                return
        except (AttributeError, ReferenceError, RuntimeError, TypeError) as exc:
            self._report_error(f"camera observer unavailable: {exc}")
            return

        try:
            from pivy import coin

            sensor = coin.SoNodeSensor(self._camera_changed, None)
            sensor.setPriority(0)
            sensor.attach(camera)
            old_sensor = self.camera_sensor
            self.camera = camera
            self.camera_sensor = sensor
            if old_sensor is not None:
                old_sensor.detach()
        except (AttributeError, ReferenceError, RuntimeError, TypeError) as exc:
            self._report_error(f"camera observer unavailable: {exc}")

    def _camera_changed(self, _data: Any, _sensor: Any) -> None:
        self.schedule_update()

    def schedule_update(self) -> None:
        if self.disposed or self.update_pending:
            return
        self.update_pending = True
        try:
            from PySide import QtCore

            QtCore.QTimer.singleShot(16, self._run_scheduled_update)
        except (AttributeError, RuntimeError):
            self.update_pending = False

    def _run_scheduled_update(self) -> None:
        self.update_pending = False
        self.update()

    def _hide_label(self) -> None:
        if self.label is not None:
            try:
                self.label.hide()
            except RuntimeError:
                self.label = None
                self.parent = None

    def _position_label(self) -> None:
        if self.label is None or self.parent is None:
            return
        self.label.adjustSize()
        x = 12
        y = max(12, self.parent.height() - self.label.height() - 12)
        self.label.move(x, y)
        self.label.raise_()

    def _desired_line_count(self, spacing_mm: float, units_per_pixel: float) -> int:
        width, height = (int(value) for value in self.view.getSize())
        spacing_pixels = max(spacing_mm / units_per_pixel, 1.0)
        visible_lines = math.ceil(max(width, height) / spacing_pixels)
        major_every = max(1, int(getattr(self.grid, "mainlines", 10)))
        quantum = 2 * major_every
        requested = max(quantum, math.ceil(1.6 * visible_lines) + quantum)
        requested = math.ceil(requested / quantum) * quantum
        return max(quantum, min(requested, max(600, quantum)))

    def update(self) -> bool:
        if self.disposed:
            return False
        try:
            if not bool(getattr(self.grid, "Visible", False)):
                self._hide_label()
                return True
            if int(getattr(self.grid, "mainlines", 0)) <= 0:
                self._hide_label()
                return True

            units_per_pixel = _world_units_per_pixel(self.view, self.grid)
            schema = _unit_schema()
            current = self.spacing_mm if schema == self.unit_schema else None
            spacing = _select_grid_spacing(units_per_pixel, current, schema)
            line_count = self._desired_line_count(spacing, units_per_pixel)

            self.grid.space = spacing
            self.grid.numlines = line_count
            width, height = (int(value) for value in self.view.getSize())
            look_at = _grid_plane_point(
                self.view, self.grid, (width // 2, height // 2)
            )
            if look_at is not None:
                self.grid.recenter(look_at[0], look_at[1])
            self.grid.update()

            self.spacing_mm = spacing
            self.unit_schema = schema
            major_every = max(1, int(getattr(self.grid, "mainlines", 10)))
            text = (
                f"Grid {_format_length(spacing)} | "
                f"Major {_format_length(spacing * major_every)}"
            )
            if self.label is not None:
                if self.label.text() != text:
                    self.label.setText(text)
                self._position_label()
                self.label.show()
            self.last_error = ""
            return True
        except (
            AttributeError,
            ReferenceError,
            RuntimeError,
            TypeError,
            ValueError,
        ) as exc:
            self._hide_label()
            self._report_error(f"adaptive update failed: {exc}")
            # Camera replacement can transiently invalidate a projection.
            # The parent-liveness check in maintain() owns final disposal.
            return True

    def maintain(self) -> bool:
        if self.disposed:
            return False
        try:
            self.view.getSize()
            if self.parent is not None:
                self.parent.objectName()
            self._attach_camera_sensor()
            return self.update()
        except (ReferenceError, RuntimeError):
            return False

    def dispose(self, remove_from_scene: bool = False) -> None:
        if self.disposed:
            return
        self.disposed = True
        if self.camera_sensor is not None:
            try:
                self.camera_sensor.detach()
            except (AttributeError, RuntimeError):
                pass
        if remove_from_scene and self.grid is not None:
            self.grid.detach_from_scene()
        if self.label is not None:
            try:
                self.label.deleteLater()
            except RuntimeError:
                pass
        self.camera_sensor = None
        self.camera = None
        self.label = None
        self.parent = None


def _live_3d_views() -> list[Any]:
    """3D views of all open documents.

    Closing a document frees its Coin scene graph synchronously while the
    Python view proxy and Qt widget can outlive it, so per-view liveness
    probes (getSize()/objectName()) pass on a dead view. Touching Coin
    through such a view segfaults; document membership is the authoritative
    liveness test.
    """
    views: list[Any] = []
    try:
        import FreeCAD as App
        import FreeCADGui as Gui

        for name in list(App.listDocuments()):
            try:
                gui_document = Gui.getDocument(name)
                if gui_document is not None:
                    views.extend(
                        gui_document.mdiViewsOfType("Gui::View3DInventor")
                    )
            except Exception:
                continue
    except Exception:
        pass
    return views


def _update_adaptive_controllers() -> None:
    if _document_restore_active():
        return
    live_views = _live_3d_views()
    for controller in list(_adaptive_controllers):
        alive = any(controller.matches(view) for view in live_views)
        if alive and controller.maintain():
            continue
        # A dead view already freed its Coin scene; only a still-alive view
        # that failed maintenance may have its grid node detached safely.
        controller.dispose(remove_from_scene=alive)
        _adaptive_controllers.remove(controller)


def _dispose_adaptive_controllers() -> None:
    """Detach every per-view Coin sensor before its native view disappears."""
    live_views = _live_3d_views()
    for controller in list(_adaptive_controllers):
        alive = any(controller.matches(view) for view in live_views)
        controller.dispose(remove_from_scene=alive)
    _adaptive_controllers.clear()


def _suspend_for_main_window_close() -> None:
    """Stop callbacks before FreeCAD processes its main-window close event."""
    global _close_suspended
    _close_suspended = True
    if _maintenance_timer is not None:
        try:
            _maintenance_timer.stop()
        except RuntimeError:
            pass
    _dispose_adaptive_controllers()


def _resume_after_cancelled_close() -> None:
    """Restore maintenance if a human cancels FreeCAD shutdown."""
    global _close_suspended
    if not _close_suspended:
        return
    try:
        from PySide import QtCore

        if QtCore.QCoreApplication.closingDown():
            return
    except (AttributeError, RuntimeError):
        return
    _close_suspended = False
    if _maintenance_timer is not None:
        try:
            _maintenance_timer.start()
        except RuntimeError:
            pass
    try:
        import FreeCADGui as Gui
        from PySide import QtWidgets

        mdi_area = Gui.getMainWindow().findChild(QtWidgets.QMdiArea)
        active = mdi_area.currentSubWindow() if mdi_area is not None else None
        if active is not None:
            _on_sub_window_activated(active)
    except (AttributeError, RuntimeError):
        pass


def _install_main_window_close_guard(main_window: Any) -> None:
    """Install one pre-close sensor guard on FreeCAD's main window."""
    global _main_window_filter
    if _main_window_filter is not None:
        return
    try:
        from PySide import QtCore, QtWidgets

        class _MainWindowCloseFilter(QtCore.QObject):
            def eventFilter(self, watched: Any, event: Any) -> bool:
                event_type = event.type()
                if event_type == QtCore.QEvent.Close:
                    _suspend_for_main_window_close()
                elif event_type in (QtCore.QEvent.Show, QtCore.QEvent.WindowActivate):
                    if _close_suspended:
                        QtCore.QTimer.singleShot(0, _resume_after_cancelled_close)
                return False

        observer = _MainWindowCloseFilter(main_window)
        main_window.installEventFilter(observer)
        application = QtWidgets.QApplication.instance()
        if application is not None:
            application.aboutToQuit.connect(_suspend_for_main_window_close)
        _main_window_filter = observer
    except (AttributeError, RuntimeError, TypeError) as exc:
        _warn(f"main-window close guard unavailable: {exc}")


def _ensure_maintenance_timer() -> None:
    global _maintenance_timer
    if _close_suspended:
        return
    if _maintenance_timer is not None:
        return
    try:
        import FreeCADGui as Gui
        from PySide import QtCore

        timer = QtCore.QTimer(Gui.getMainWindow())
        timer.setInterval(500)
        timer.timeout.connect(_update_adaptive_controllers)
        timer.start()
        _maintenance_timer = timer
    except (AttributeError, RuntimeError) as exc:
        _warn(f"adaptive grid timer unavailable: {exc}")


def _find_controller(view: Any) -> Any:
    for controller in _adaptive_controllers:
        if controller.matches(view):
            return controller
    return None


def _ensure_adaptive_controller(view: Any) -> Any:
    if _close_suspended:
        return None
    parent = _active_view_parent()
    controller = _find_controller(view)
    if controller is not None:
        controller.ensure_parent(parent)
        controller.schedule_update()
        return controller
    try:
        grid = _GridTracker(view)
    except Exception as exc:
        _warn(f"grid tracker creation failed: {exc}")
        return None
    controller = _AdaptiveGridController(view, grid, parent)
    _adaptive_controllers.append(controller)
    _ensure_maintenance_timer()
    return controller


def is_enabled() -> bool:
    """Return True when the always-on grid feature is enabled."""
    if App is None:
        return False
    return App.ParamGet(_CADEX_PARAM_PATH).GetBool("AlwaysShowGrid", True)


def _major_every() -> int:
    """Number of minor cells per major cell (``Mod/cadex`` preference)."""
    if App is None:
        return 10
    return max(1, App.ParamGet(_CADEX_PARAM_PATH).GetInt("GridMajorEvery", 10))


def _grid_should_always_show() -> bool:
    """Return the persisted grid visibility preference."""
    if App is None:
        return False
    return App.ParamGet(_CADEX_PARAM_PATH).GetBool("ShowGrid", True)


def is_grid_visible() -> bool:
    """Return True when the grid is visible in at least one 3D view.

    Reads the actual tracker state so the answer stays correct even when a
    tracker was toggled directly. Falls back to the ``ShowGrid`` preference
    before any tracker exists (e.g. at startup).
    """
    if App is None or not App.GuiUp:
        return False
    try:
        if _adaptive_controllers:
            return any(
                bool(getattr(controller.grid, "Visible", False))
                for controller in _adaptive_controllers
            )
    except Exception as exc:
        _warn(f"grid visibility query failed: {exc}")
    return _grid_should_always_show()


def toggle_grid(show: bool | None = None) -> None:
    """Show or hide the grid in every 3D view, current and future.

    Writes the ``ShowGrid`` preference (so views opened later follow suit)
    and flips all existing grid trackers. With ``show=None`` the current
    visibility is inverted.
    """
    if App is None or not App.GuiUp:
        return
    try:
        if show is None:
            show = not is_grid_visible()
        show = bool(show)
        App.ParamGet(_CADEX_PARAM_PATH).SetBool("ShowGrid", show)

        import FreeCADGui as Gui

        # A native View-menu command remains available before a document is
        # opened. In that state the preference is all that should change.
        if Gui.activeDocument() is None:
            return

        for controller in _adaptive_controllers:
            controller.grid.set_visible(show)
            controller.schedule_update()
        if show:
            _show_grid_in_active_view()
        else:
            _update_adaptive_controllers()
    except Exception as exc:
        _warn(f"grid toggle failed: {exc}")


# ---------------------------------------------------------------------------
# Per-view grid initialization
# ---------------------------------------------------------------------------


def _active_3d_view() -> Any:
    """Return the active ``View3DInventor`` or None."""
    try:
        import FreeCADGui as Gui

        gui_document = Gui.activeDocument()
        if gui_document is None:
            return None
        view = gui_document.activeView()
        if view is not None and hasattr(view, "getCameraNode"):
            return view
    except (AttributeError, RuntimeError):
        pass
    return None


def _show_grid_in_active_view() -> None:
    """Initialize and show the grid for the active 3D view, at most once.

    Only acts while the ``ShowGrid`` preference is set (i.e. the grid is
    toggled on). Views that already have a controller are only refreshed so
    a manual grid toggle by the user is never fought.
    """
    if App is None or not App.GuiUp or _close_suspended or _document_restore_active():
        return
    if not _grid_should_always_show():
        return
    try:
        view = _active_3d_view()
        if view is None:
            return
        already_tracked = _find_controller(view) is not None
        controller = _ensure_adaptive_controller(view)
        if controller is None:
            return
        if not already_tracked:
            controller.grid.set_visible(True)
            controller.schedule_update()
    except Exception as exc:
        _warn(f"unable to show grid in active view: {exc}")


def _on_sub_window_activated(_window: Any = None) -> None:
    """Defer grid initialization until the view activation settles."""
    if _window is None:
        # QMdiArea emits ``subWindowActivated(None)`` synchronously while the
        # final document view is closing. Detach Coin camera sensors now;
        # waiting for the maintenance timer can otherwise recreate a sensor
        # while FreeCAD is already tearing down the Coin database.
        _dispose_adaptive_controllers()
        return
    if _close_suspended:
        return
    try:
        from PySide import QtCore

        QtCore.QTimer.singleShot(0, _show_grid_in_active_view)
    except Exception as exc:
        _warn(f"deferred grid update failed: {exc}")


def _install_view_observer() -> None:
    """Install the MDI observer that grids new 3D views (idempotent)."""
    global _observer_installed
    if _observer_installed:
        return
    try:
        import FreeCADGui as Gui
        from PySide import QtWidgets

        main_window = Gui.getMainWindow()
        _install_main_window_close_guard(main_window)
        mdi_area = main_window.findChild(QtWidgets.QMdiArea)
        if mdi_area is None:
            _warn("MDI area not found; grid observer not installed")
            return
        mdi_area.subWindowActivated.connect(_on_sub_window_activated)
        _observer_installed = True
        _ensure_maintenance_timer()
        # Handle a 3D view that is already active at setup time.
        _on_sub_window_activated()
    except Exception as exc:
        _warn(f"observer installation failed: {exc}")


def setup() -> None:
    """Install the grid feature (idempotent).

    Gated by the ``AlwaysShowGrid`` kill-switch. The view observer follows
    the ``ShowGrid`` preference for current and future 3D views. View-menu
    ownership remains entirely native.
    """
    if App is None or not App.GuiUp:
        return
    if not is_enabled():
        return
    _install_view_observer()
