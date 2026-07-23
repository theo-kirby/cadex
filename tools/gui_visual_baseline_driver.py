#!/usr/bin/env python3
# SPDX-License-Identifier: LGPL-2.1-or-later
"""Capture FreeCAD GUI screenshots and widget geometry from inside Qt."""

from __future__ import annotations

import json
import os
import time
import traceback
from pathlib import Path

import FreeCAD as App
import FreeCADGui as Gui

try:
    from PySide6 import QtCore, QtGui, QtWidgets
except ImportError:
    from PySide import QtCore, QtGui, QtWidgets


def clean_text(value):
    if value is None:
        return ""
    return str(value).replace("&", "").strip()


def class_name(obj):
    try:
        return obj.metaObject().className()
    except Exception:
        return type(obj).__name__


def text_for(obj):
    for attr in ("text", "windowTitle", "toolTip", "objectName"):
        try:
            value = getattr(obj, attr)()
        except Exception:
            continue
        value = clean_text(value)
        if value:
            return value
    return ""


def visible_text_for(obj):
    try:
        if isinstance(obj, QtWidgets.QLabel):
            return clean_text(obj.text())
        if isinstance(obj, QtWidgets.QAbstractButton):
            return clean_text(obj.text())
        if isinstance(obj, QtWidgets.QLineEdit):
            return clean_text(obj.displayText())
        if isinstance(obj, QtWidgets.QComboBox):
            return clean_text(obj.currentText())
        if isinstance(obj, QtWidgets.QAbstractSpinBox):
            return clean_text(obj.text())
    except Exception:
        return ""
    return ""


def widget_geometry(widget):
    rect = widget.geometry()
    top_left = widget.mapToGlobal(QtCore.QPoint(0, 0))
    return {
        "local": [rect.x(), rect.y(), rect.width(), rect.height()],
        "global": [top_left.x(), top_left.y(), rect.width(), rect.height()],
    }


def widget_record(widget):
    record = {
        "class": class_name(widget),
        "object_name": widget.objectName(),
        "text": text_for(widget),
        "enabled": widget.isEnabled(),
        "visible": widget.isVisible(),
        "geometry": widget_geometry(widget),
    }
    if isinstance(widget, QtWidgets.QLabel):
        record["word_wrap"] = widget.wordWrap()
    if isinstance(widget, QtWidgets.QAbstractButton):
        record["checked"] = widget.isChecked() if widget.isCheckable() else None
        record["icon_null"] = widget.icon().isNull()
    return record


def visible_widgets(app):
    widgets = []
    for widget in app.allWidgets():
        try:
            if widget.isVisible():
                widgets.append(widget)
        except RuntimeError:
            continue
    return widgets


def visible_transient_widgets(app, main_window):
    widgets = []
    for widget in app.topLevelWidgets():
        try:
            if widget is main_window or not widget.isVisible():
                continue
            widgets.append(widget)
        except RuntimeError:
            continue
    return widgets


def safe_scene_name(value):
    return "".join(ch if ch.isalnum() or ch in ("-", "_") else "-" for ch in value).strip("-")


def color_tuple(color):
    return [color.red(), color.green(), color.blue(), color.alpha()]


def relative_luminance(color):
    values = []
    for component in (color.redF(), color.greenF(), color.blueF()):
        if component <= 0.03928:
            values.append(component / 12.92)
        else:
            values.append(((component + 0.055) / 1.055) ** 2.4)
    return 0.2126 * values[0] + 0.7152 * values[1] + 0.0722 * values[2]


def contrast_ratio(foreground, background):
    first = relative_luminance(foreground)
    second = relative_luminance(background)
    lighter = max(first, second)
    darker = min(first, second)
    return (lighter + 0.05) / (darker + 0.05)


def contrast_roles(widget):
    palette = widget.palette()
    if isinstance(widget, QtWidgets.QLineEdit):
        return palette.color(QtGui.QPalette.ColorRole.Text), palette.color(QtGui.QPalette.ColorRole.Base)
    if isinstance(widget, QtWidgets.QAbstractSpinBox):
        return palette.color(QtGui.QPalette.ColorRole.Text), palette.color(QtGui.QPalette.ColorRole.Base)
    if isinstance(widget, QtWidgets.QComboBox):
        return palette.color(QtGui.QPalette.ColorRole.ButtonText), palette.color(QtGui.QPalette.ColorRole.Button)
    if isinstance(widget, QtWidgets.QAbstractButton):
        return palette.color(QtGui.QPalette.ColorRole.ButtonText), palette.color(QtGui.QPalette.ColorRole.Button)
    if isinstance(widget, QtWidgets.QLabel):
        return palette.color(QtGui.QPalette.ColorRole.WindowText), palette.color(QtGui.QPalette.ColorRole.Window)
    return None, None


def layout_findings(widget):
    findings = []
    try:
        rect = widget.rect()
        if widget.isVisible() and (rect.width() <= 0 or rect.height() <= 0):
            findings.append({"kind": "zero_size", "widget": widget_record(widget)})

        text = text_for(widget)
        if text and widget.isVisible() and isinstance(widget, (QtWidgets.QLabel, QtWidgets.QAbstractButton)):
            metrics = widget.fontMetrics()
            text_rect = metrics.boundingRect(text)
            margin = 8
            if text_rect.width() > rect.width() + margin or text_rect.height() > rect.height() + margin:
                findings.append(
                    {
                        "kind": "possible_text_clipping",
                        "text_size": [text_rect.width(), text_rect.height()],
                        "widget": widget_record(widget),
                    }
                )

        if widget.isVisible() and isinstance(widget, QtWidgets.QAbstractButton):
            if not text and widget.icon().isNull():
                findings.append({"kind": "missing_button_text_or_icon", "widget": widget_record(widget)})

        visible_text = visible_text_for(widget)
        if visible_text and widget.isVisible() and widget.isEnabled():
            foreground, background = contrast_roles(widget)
            if foreground is not None and background is not None and foreground.alpha() > 0 and background.alpha() > 0:
                ratio = contrast_ratio(foreground, background)
                if ratio < 4.5:
                    findings.append(
                        {
                            "kind": "low_text_contrast",
                            "contrast_ratio": round(ratio, 3),
                            "foreground": color_tuple(foreground),
                            "background": color_tuple(background),
                            "visible_text": visible_text[:120],
                            "widget": widget_record(widget),
                        }
                    )

        parent = widget.parentWidget()
        if widget.isVisible() and parent and parent.isVisible():
            local_rect = widget.geometry()
            parent_rect = parent.rect()
            tolerance = 3
            if (
                local_rect.right() < -tolerance
                or local_rect.bottom() < -tolerance
                or local_rect.left() > parent_rect.width() + tolerance
                or local_rect.top() > parent_rect.height() + tolerance
                or local_rect.left() < -tolerance
                or local_rect.top() < -tolerance
                or local_rect.right() > parent_rect.width() + tolerance
                or local_rect.bottom() > parent_rect.height() + tolerance
            ):
                findings.append(
                    {
                        "kind": "outside_parent_bounds",
                        "parent": widget_record(parent),
                        "widget": widget_record(widget),
                    }
                )
    except RuntimeError:
        findings.append({"kind": "deleted_widget_reference"})
    return findings


def rect_area(rect):
    return max(0, rect.width()) * max(0, rect.height())


def should_check_overlap(widget):
    ignored_classes = {
        "QScrollBar",
        "QToolBarSeparator",
        "QMenu",
        "QMenuBar",
        "QSizeGrip",
        "QStatusBar",
    }
    widget_class = class_name(widget)
    if widget_class in ignored_classes or "Overlay" in widget_class:
        return False
    if isinstance(widget, (QtWidgets.QFrame, QtWidgets.QStackedWidget, QtWidgets.QScrollArea)):
        return False
    if isinstance(widget, (QtWidgets.QLabel, QtWidgets.QAbstractButton, QtWidgets.QComboBox)):
        return True
    if isinstance(widget, (QtWidgets.QLineEdit, QtWidgets.QSpinBox, QtWidgets.QDoubleSpinBox)):
        return True
    if isinstance(widget, (QtWidgets.QPlainTextEdit, QtWidgets.QTextEdit)):
        return True
    return False


def scene_layout_findings(widgets):
    findings = []
    by_parent = {}
    for widget in widgets:
        try:
            parent = widget.parentWidget()
            if not parent or not parent.isVisible() or not should_check_overlap(widget):
                continue
            parent_class = class_name(parent)
            if parent_class in {"QStackedWidget", "QTabWidget", "QToolBar", "Gui::ToolBar"}:
                continue
            by_parent.setdefault(parent, []).append(widget)
        except RuntimeError:
            continue

    for siblings in by_parent.values():
        for index, left in enumerate(siblings):
            try:
                left_rect = left.geometry()
                left_area = rect_area(left_rect)
                if left_area < 64:
                    continue
                for right in siblings[index + 1:]:
                    right_rect = right.geometry()
                    right_area = rect_area(right_rect)
                    if right_area < 64:
                        continue
                    intersection = left_rect.intersected(right_rect)
                    overlap_area = rect_area(intersection)
                    if overlap_area <= 0:
                        continue
                    smaller = min(left_area, right_area)
                    if overlap_area / smaller >= 0.80:
                        findings.append(
                            {
                                "kind": "obvious_sibling_overlap",
                                "overlap_area": overlap_area,
                                "widget": widget_record(left),
                                "other_widget": widget_record(right),
                            }
                        )
            except RuntimeError:
                continue

    for widget in widgets:
        try:
            widget_class = class_name(widget)
            if widget_class not in {"Gui::TaskView::TaskPanel", "Gui::TaskView::TaskView"}:
                continue
            scroll_areas = [
                child
                for child in widget.findChildren(QtWidgets.QScrollArea)
                if child.isVisible()
            ]
            vertical_scrollbars = [
                area.verticalScrollBar()
                for area in scroll_areas
                if area.verticalScrollBar() is not None
            ]
            needs_scroll = any(bar.maximum() > 0 for bar in vertical_scrollbars)
            has_scroll_path = any(bar.isVisible() and bar.isEnabled() for bar in vertical_scrollbars)
            child_bottom = max(
                (child.geometry().bottom() for child in widget.findChildren(QtWidgets.QWidget) if child.isVisible()),
                default=0,
            )
            content_overflows = child_bottom > widget.rect().height() + 8
            if (needs_scroll or content_overflows) and not has_scroll_path:
                findings.append(
                    {
                        "kind": "task_panel_no_scroll_path",
                        "content_bottom": child_bottom,
                        "widget": widget_record(widget),
                    }
                )
        except RuntimeError:
            continue
    return findings


def assert_visible_expectations(scene, widgets):
    required_classes = scene.get("required_widget_class_contains") or []
    widget_classes = [class_name(widget) for widget in widgets]
    missing_classes = [
        required
        for required in required_classes
        if not any(required in widget_class for widget_class in widget_classes)
    ]
    if missing_classes:
        raise RuntimeError(
            "Required widget class not found: "
            + ", ".join(missing_classes)
            + "; visible classes include: "
            + ", ".join(sorted(set(widget_classes))[:60])
        )
    required_any_classes = scene.get("required_widget_class_contains_any") or []
    if required_any_classes and not any(
        required in widget_class
        for required in required_any_classes
        for widget_class in widget_classes
    ):
        raise RuntimeError(
            "Required widget class alternative not found: "
            + ", ".join(required_any_classes)
            + "; visible classes include: "
            + ", ".join(sorted(set(widget_classes))[:60])
        )

    required_object_names = scene.get("required_widget_object_names") or []
    object_names = [widget.objectName() for widget in widgets]
    missing_object_names = [
        required
        for required in required_object_names
        if required not in object_names
    ]
    if missing_object_names:
        raise RuntimeError(
            "Required widget object name not found: "
            + ", ".join(missing_object_names)
            + "; visible object names include: "
            + ", ".join(name for name in sorted(set(object_names)) if name)[:500]
        )

    required_texts = scene.get("required_visible_text_contains") or []
    visible_texts = [text_for(widget) for widget in widgets]
    missing_texts = [
        required
        for required in required_texts
        if not any(required in text for text in visible_texts)
    ]
    if missing_texts:
        raise RuntimeError(
            "Required visible text not found: "
            + ", ".join(missing_texts)
            + "; visible text includes: "
            + ", ".join(text for text in visible_texts if text)[:500]
        )
    required_any_texts = scene.get("required_visible_text_contains_any") or []
    if required_any_texts and not any(
        required in text
        for required in required_any_texts
        for text in visible_texts
    ):
        raise RuntimeError(
            "Required visible text alternative not found: "
            + ", ".join(required_any_texts)
            + "; visible text includes: "
            + ", ".join(text for text in visible_texts if text)[:500]
        )


class VisualBaseline:
    def __init__(self, config):
        self.config = config
        self.output_dir = Path(config["output_dir"])
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.app = QtWidgets.QApplication.instance()
        self.main_window = Gui.getMainWindow()

    def process_events(self, ms=100):
        deadline = time.time() + (ms / 1000.0)
        while time.time() < deadline:
            self.app.processEvents(QtCore.QEventLoop.ProcessEventsFlag.AllEvents, 25)
            time.sleep(0.01)

    def configure_window(self):
        font_scale = float(self.config.get("font_scale", 1.0))
        if font_scale != 1.0:
            font = self.app.font()
            if font.pointSizeF() > 0:
                font.setPointSizeF(font.pointSizeF() * font_scale)
            else:
                font.setPixelSize(int(font.pixelSize() * font_scale))
            self.app.setFont(font)

        size = self.config.get("window_size", [1600, 1000])
        self.main_window.resize(int(size[0]), int(size[1]))
        self.main_window.move(0, 0)
        self.main_window.show()
        self.main_window.raise_()
        self.process_events(500)

    def close_documents(self):
        for document in list(App.listDocuments().values()):
            try:
                App.closeDocument(document.Name)
            except Exception:
                pass
        self.process_events(200)

    def activate_workbench(self, workbench):
        if not workbench:
            return
        Gui.activateWorkbench(workbench)
        Gui.updateGui()
        self.process_events(700)

    def fit_active_view(self):
        try:
            view = Gui.ActiveDocument.ActiveView
        except Exception:
            return
        for method_name in ("viewIsometric", "fitAll"):
            try:
                getattr(view, method_name)()
            except Exception:
                pass
        Gui.updateGui()
        self.process_events(500)

    def open_scene_document(self, scene):
        file_name = scene.get("file")
        if not file_name:
            return None
        path = Path(file_name)
        if not path.is_absolute():
            path = Path(self.config.get("repo_root", os.getcwd())) / path
        if not path.exists():
            raise FileNotFoundError(path)
        document = App.openDocument(str(path))
        if document is not None:
            App.setActiveDocument(document.Name)
        Gui.updateGui()
        self.process_events(700)
        return str(path)

    def resolve_scene_path(self, file_name):
        path = Path(file_name)
        if not path.is_absolute():
            path = Path(self.config.get("repo_root", os.getcwd())) / path
        return path

    def capture_target_widget(self, scene_config):
        target = (scene_config or {}).get("capture", "main_window")
        if target == "active_modal":
            widget = self.app.activeModalWidget()
            if widget:
                return widget
        if target == "active_window":
            widget = self.app.activeWindow()
            if widget and widget.isVisible():
                return widget
        if target == "top_level_dialog":
            for widget in self.app.topLevelWidgets():
                try:
                    if widget.isVisible() and widget is not self.main_window:
                        return widget
                except RuntimeError:
                    continue
        return self.main_window

    def capture_scene(self, scene_name, scene_config=None):
        self.process_events(300)
        target_widget = self.capture_target_widget(scene_config or {})
        pixmap = target_widget.grab()
        screenshot = self.output_dir / f"{scene_name}.png"
        pixmap.save(str(screenshot), "PNG")

        widgets = []
        findings = []
        widget_objects = visible_widgets(self.app)
        assert_visible_expectations(scene_config or {}, widget_objects)
        for widget in widget_objects:
            try:
                widgets.append(widget_record(widget))
                findings.extend(layout_findings(widget))
            except RuntimeError:
                findings.append({"kind": "deleted_widget_reference"})
        findings.extend(scene_layout_findings(widget_objects))

        scene = {
            "scene": scene_name,
            "screenshot": str(screenshot),
            "variant": self.config.get("variant", {}),
            "scene_config": scene_config or {},
            "captured_widget": widget_record(target_widget),
            "active_workbench": Gui.activeWorkbench().name(),
            "active_document": App.ActiveDocument.Name if App.ActiveDocument else None,
            "screen_size": [pixmap.width(), pixmap.height()],
            "visible_widget_count": len(widgets),
            "widgets": widgets,
            "findings": findings,
        }
        scene_path = self.output_dir / f"{scene_name}.json"
        scene_path.write_text(json.dumps(scene, indent=2, sort_keys=True), encoding="utf-8")
        return {
            "scene": scene_name,
            "screenshot": str(screenshot),
            "metadata": str(scene_path),
            "visible_widget_count": len(widgets),
            "finding_count": len(findings),
        }

    def transient_window_records(self):
        return [
            widget_record(widget)
            for widget in visible_transient_widgets(self.app, self.main_window)
        ]

    def close_transient_windows(self):
        before = self.transient_window_records()
        for widget in list(self.app.topLevelWidgets()):
            try:
                if widget is self.main_window or not widget.isVisible():
                    continue
                if hasattr(widget, "reject"):
                    widget.reject()
                else:
                    widget.close()
            except RuntimeError:
                continue
            except Exception:
                try:
                    widget.close()
                except Exception:
                    pass
        try:
            if Gui.Control.activeDialog():
                Gui.Control.closeDialog()
        except Exception:
            pass
        self.process_events(300)
        after = self.transient_window_records()
        return {
            "before_count": len(before),
            "after_count": len(after),
            "before": before,
            "after": after,
            "result": "ok" if not after else "left_open",
        }

    def select_and_accept_dialog_file(self, scene):
        file_name = scene.get("accept_file")
        if not file_name:
            return
        try:
            path = self.resolve_scene_path(file_name)
            if not path.exists():
                raise FileNotFoundError(path)
            for widget in self.app.topLevelWidgets():
                try:
                    if widget is self.main_window or not widget.isVisible():
                        continue
                    combined = " ".join(
                        [
                            class_name(widget).lower(),
                            clean_text(widget.objectName()).lower(),
                            text_for(widget).lower(),
                        ]
                    )
                    if not isinstance(widget, QtWidgets.QFileDialog):
                        if "filedialog" not in combined and "open document" not in combined:
                            continue
                    if hasattr(widget, "setDirectory"):
                        widget.setDirectory(str(path.parent))
                    if hasattr(widget, "selectFile"):
                        widget.selectFile(path.name)
                    line_edit = widget.findChild(QtWidgets.QLineEdit, "fileNameEdit")
                    if line_edit is not None:
                        line_edit.setText(str(path))
                        line_edit.editingFinished.emit()
                    self.process_events(300)
                    if hasattr(widget, "accept"):
                        widget.accept()
                    else:
                        widget.close()
                    return
                except RuntimeError:
                    continue
            raise RuntimeError("No visible file dialog found for accept_file")
        except Exception:
            self.close_transient_windows()
            raise

    def verify_dialog_return(self, scene):
        file_name = scene.get("expect_opened_file")
        if not file_name:
            return None
        expected = self.resolve_scene_path(file_name).resolve()
        active = App.ActiveDocument
        opened = None
        if active is not None and active.FileName:
            opened = Path(active.FileName).resolve()
        if opened != expected:
            raise RuntimeError(f"Expected active document {expected}, got {opened}")
        return {
            "kind": "opened_file",
            "expected": str(expected),
            "active_document": active.Name,
            "opened": str(opened),
        }

    def run_dialog_action(self, scene):
        if scene.get("new_document"):
            self.close_documents()
            App.newDocument(scene.get("document_name", "GuiVisualDialogBaseline"))
            self.process_events(300)
        if scene.get("file"):
            self.close_documents()
            self.open_scene_document(scene)
        self.activate_workbench(scene.get("workbench"))
        command = scene.get("command")
        if command:
            Gui.runCommand(command)
            Gui.updateGui()
        self.process_events(int(scene.get("wait_ms", 1200)))

    def run_modal_dialog_scene(self, scene_name, scene):
        captured = []
        wait_ms = int(scene.get("wait_ms", 1200))
        close_delay_ms = int(scene.get("close_delay_ms", 1000))
        accept_delay_ms = int(scene.get("accept_delay_ms", 800))

        def capture_open_dialog():
            try:
                captured.append(self.capture_scene(scene_name, scene))
            except Exception:
                captured.append(
                    {
                        "scene": scene_name,
                        "error": "capture_failed",
                        "traceback": traceback.format_exc(),
                        "scene_config": scene,
                    }
                )

        QtCore.QTimer.singleShot(wait_ms, capture_open_dialog)
        if scene.get("accept_file"):
            QtCore.QTimer.singleShot(
                wait_ms + accept_delay_ms,
                lambda: self.select_and_accept_dialog_file(scene),
            )
        else:
            QtCore.QTimer.singleShot(wait_ms + close_delay_ms, self.close_transient_windows)
        self.run_dialog_action(scene)
        if captured:
            result = captured[0]
            return_check = self.verify_dialog_return(scene)
            if return_check:
                result["return_check"] = return_check
            return result
        raise RuntimeError(f"Modal dialog scene {scene_name} did not capture before command returned")

    def run_dialog_scenes(self):
        scenes = []
        configured = list(self.config.get("dialog_scenes") or [])
        max_dialogs = int(self.config.get("max_dialogs", 0))
        if max_dialogs > 0:
            configured = configured[:max_dialogs]

        for index, scene in enumerate(configured, start=1):
            base_name = safe_scene_name(scene.get("name") or f"dialog-{index:03d}")
            scene_name = f"dialog-{base_name}"
            try:
                self.close_transient_windows()
                if scene.get("modal", True) and scene.get("command"):
                    scenes.append(self.run_modal_dialog_scene(scene_name, scene))
                else:
                    self.run_dialog_action(scene)
                    scenes.append(self.capture_scene(scene_name, scene))
            except Exception as exc:
                scenes.append(
                    {
                        "scene": scene_name,
                        "error": repr(exc),
                        "scene_config": scene,
                        "traceback": traceback.format_exc(),
                    }
                )
            finally:
                if scene.get("close_after_capture", True):
                    cleanup = self.close_transient_windows()
                    if scenes:
                        scenes[-1]["cleanup"] = cleanup
                    if cleanup["result"] != "ok" and scenes:
                        scenes[-1]["error"] = "transient_windows_left_open_after_cleanup"
                    self.close_documents()
        return scenes

    def run_task_action(self, scene):
        self.close_transient_windows()
        self.close_documents()
        self.open_scene_document(scene)
        self.activate_workbench(scene.get("workbench"))
        if scene.get("fit_view", True):
            self.fit_active_view()

        select_objects = scene.get("select_objects")
        if select_objects is None and scene.get("select_object"):
            select_objects = [scene.get("select_object")]
        if select_objects:
            Gui.Selection.clearSelection()
            for object_name in select_objects:
                if App.ActiveDocument is None or App.ActiveDocument.getObject(object_name) is None:
                    raise RuntimeError(f"Task scene select_object not found: {object_name}")
                Gui.Selection.addSelection(App.ActiveDocument.Name, object_name)

        object_name = scene.get("edit_object")
        if object_name:
            if App.ActiveDocument is None or App.ActiveDocument.getObject(object_name) is None:
                raise RuntimeError(f"Task scene edit_object not found: {object_name}")
            Gui.ActiveDocument.setEdit(object_name)

        command = scene.get("command")
        if command:
            Gui.runCommand(command, int(scene.get("command_source", 0)))

        script = scene.get("python")
        if script:
            exec(script, {"App": App, "Gui": Gui})

        Gui.updateGui()
        self.process_events(int(scene.get("wait_ms", 1500)))

        assert_visible_expectations(scene, visible_widgets(self.app))

    def run_task_scenes(self):
        scenes = []
        configured = list(self.config.get("task_scenes") or [])
        max_tasks = int(self.config.get("max_tasks", 0))
        if max_tasks > 0:
            configured = configured[:max_tasks]

        for index, scene in enumerate(configured, start=1):
            base_name = safe_scene_name(scene.get("name") or f"task-{index:03d}")
            scene_name = f"task-{base_name}"
            try:
                self.run_task_action(scene)
                scenes.append(self.capture_scene(scene_name, scene))
            except Exception as exc:
                scenes.append(
                    {
                        "scene": scene_name,
                        "error": repr(exc),
                        "scene_config": scene,
                        "traceback": traceback.format_exc(),
                    }
                )
            finally:
                if scene.get("close_after_capture", True):
                    try:
                        Gui.ActiveDocument.resetEdit()
                    except Exception:
                        pass
                    cleanup = self.close_transient_windows()
                    if scenes:
                        scenes[-1]["cleanup"] = cleanup
                    if cleanup["result"] != "ok" and scenes:
                        scenes[-1]["error"] = "transient_windows_left_open_after_cleanup"
                    self.close_documents()
        return scenes

    def cleanup_for_exit(self):
        try:
            if Gui.ActiveDocument:
                Gui.ActiveDocument.resetEdit()
        except Exception:
            pass
        try:
            Gui.Selection.clearSelection()
        except Exception:
            pass
        self.close_transient_windows()
        self.close_documents()
        self.process_events(1000)

    def discovered_workbenches(self):
        return sorted(Gui.listWorkbenches().keys())

    def run_workbench_scenes(self):
        workbenches = self.discovered_workbenches()
        include = self.config.get("workbenches") or []
        if include:
            workbenches = [name for name in workbenches if name in include]
        max_workbenches = int(self.config.get("max_workbenches", 0))
        if max_workbenches > 0:
            workbenches = workbenches[:max_workbenches]

        scenes = []
        for workbench in workbenches:
            scene_name = f"workbench-{workbench}"
            try:
                if self.config.get("isolate_workbenches", True):
                    self.close_documents()
                    App.newDocument(f"GuiVisualBaseline_{workbench}")
                elif App.ActiveDocument is None:
                    App.newDocument("GuiVisualBaseline")
                self.activate_workbench(workbench)
                scenes.append(
                    self.capture_scene(
                        scene_name,
                        {
                            "kind": "workbench",
                            "workbench": workbench,
                            "isolated": self.config.get("isolate_workbenches", True),
                        },
                    )
                )
            except Exception as exc:
                scenes.append({"scene": scene_name, "error": repr(exc)})
            finally:
                if self.config.get("isolate_workbenches", True):
                    self.close_documents()
        return scenes

    def run_configured_scenes(self):
        scenes = []
        configured = list(self.config.get("scenes") or [])
        max_scenes = int(self.config.get("max_scenes", 0))
        if max_scenes > 0:
            configured = configured[:max_scenes]

        for index, scene in enumerate(configured, start=1):
            base_name = scene.get("name") or f"scene-{index:03d}"
            scene_name = f"fixture-{safe_scene_name(base_name)}"
            try:
                self.close_documents()
                self.open_scene_document(scene)
                self.activate_workbench(scene.get("workbench"))
                if scene.get("fit_view", True):
                    self.fit_active_view()
                scenes.append(self.capture_scene(scene_name, scene))
            except Exception as exc:
                scenes.append(
                    {
                        "scene": scene_name,
                        "error": repr(exc),
                        "scene_config": scene,
                        "traceback": traceback.format_exc(),
                    }
                )
        return scenes

    def run(self):
        App.TestEnvironment = True
        self.configure_window()

        scenes = []
        if self.config.get("fixtures_first", True):
            scenes.extend(self.run_configured_scenes())
            scenes.extend(self.run_dialog_scenes())
            scenes.extend(self.run_task_scenes())
            if self.config.get("include_workbenches", True):
                scenes.extend(self.run_workbench_scenes())
        else:
            if self.config.get("include_workbenches", True):
                scenes.extend(self.run_workbench_scenes())
            scenes.extend(self.run_configured_scenes())
            scenes.extend(self.run_dialog_scenes())
            scenes.extend(self.run_task_scenes())

        summary = {
            "result": "ok",
            "freecad_version": App.Version(),
            "discovered_workbenches": self.discovered_workbenches(),
            "captured_workbenches": [
                scene.get("scene", "").removeprefix("workbench-")
                for scene in scenes
                if isinstance(scene, dict) and str(scene.get("scene", "")).startswith("workbench-")
            ],
            "scene_count": len(scenes),
            "scenes": scenes,
        }
        (self.output_dir / "summary.json").write_text(
            json.dumps(summary, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        self.cleanup_for_exit()
        del App.TestEnvironment


def main():
    config = json.loads(Path(os.environ["FREECAD_VISUAL_BASELINE_CONFIG"]).read_text(encoding="utf-8"))
    output_dir = Path(config["output_dir"])
    try:
        VisualBaseline(config).run()
    except Exception as exc:
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "summary.json").write_text(
            json.dumps(
                {"result": "fatal", "error": repr(exc), "traceback": traceback.format_exc()},
                indent=2,
                sort_keys=True,
            ),
            encoding="utf-8",
        )
    finally:
        QtCore.QTimer.singleShot(0, QtWidgets.QApplication.instance().quit)


QtCore.QTimer.singleShot(1500, main)
