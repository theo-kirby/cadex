#!/usr/bin/env python3
# SPDX-License-Identifier: LGPL-2.1-or-later
"""Exercise GUI layout assertion kinds in a real FreeCAD/Qt process."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any


SMOKE_SCRIPT = r"""
import importlib.util
import json
import os
import sys
from pathlib import Path

driver_path = Path(os.environ["FREECAD_LAYOUT_SMOKE_DRIVER"])
output_path = Path(os.environ["FREECAD_LAYOUT_SMOKE_OUTPUT"])
required_path = Path(os.environ["FREECAD_LAYOUT_ASSERTION_CONFIG"])

spec = importlib.util.spec_from_file_location("gui_visual_baseline_driver_smoke", driver_path)
driver = importlib.util.module_from_spec(spec)
spec.loader.exec_module(driver)

QtCore = driver.QtCore
QtGui = driver.QtGui
QtWidgets = driver.QtWidgets

app = QtWidgets.QApplication.instance()
root = QtWidgets.QWidget()
root.setObjectName("layout_smoke_root")
root.setGeometry(100, 100, 500, 400)
root.show()

def process():
    app.processEvents(QtCore.QEventLoop.ProcessEventsFlag.AllEvents, 100)

def kinds(findings):
    return {finding.get("kind") for finding in findings}

observed = {}
examples = {}

zero = QtWidgets.QWidget(root)
zero.setObjectName("zero_size_probe")
zero.setGeometry(10, 10, 0, 0)
zero.show()
process()
findings = driver.layout_findings(zero)
observed["zero_size"] = "zero_size" in kinds(findings)
examples["zero_size"] = findings

clipped = QtWidgets.QLabel("This label text is intentionally far too long for the widget", root)
clipped.setObjectName("text_clipping_probe")
clipped.setGeometry(10, 40, 24, 16)
clipped.show()
process()
findings = driver.layout_findings(clipped)
observed["possible_text_clipping"] = "possible_text_clipping" in kinds(findings)
examples["possible_text_clipping"] = findings

blank_button = QtWidgets.QPushButton("", root)
blank_button.setObjectName("")
blank_button.setGeometry(10, 70, 32, 24)
blank_button.show()
process()
findings = driver.layout_findings(blank_button)
observed["missing_button_text_or_icon"] = "missing_button_text_or_icon" in kinds(findings)
examples["missing_button_text_or_icon"] = findings

low_contrast = QtWidgets.QLabel("low contrast", root)
low_contrast.setObjectName("low_text_contrast_probe")
low_contrast.setGeometry(10, 105, 140, 24)
palette = low_contrast.palette()
black = QtGui.QColor(0, 0, 0)
palette.setColor(QtGui.QPalette.ColorRole.WindowText, black)
palette.setColor(QtGui.QPalette.ColorRole.Window, black)
low_contrast.setAutoFillBackground(True)
low_contrast.setPalette(palette)
low_contrast.show()
process()
findings = driver.layout_findings(low_contrast)
observed["low_text_contrast"] = "low_text_contrast" in kinds(findings)
examples["low_text_contrast"] = findings

outside = QtWidgets.QLabel("outside", root)
outside.setObjectName("outside_parent_bounds_probe")
outside.setGeometry(-30, 140, 80, 24)
outside.show()
process()
findings = driver.layout_findings(outside)
observed["outside_parent_bounds"] = "outside_parent_bounds" in kinds(findings)
examples["outside_parent_bounds"] = findings

overlap_parent = QtWidgets.QWidget(root)
overlap_parent.setObjectName("overlap_parent_probe")
overlap_parent.setGeometry(10, 180, 160, 80)
left = QtWidgets.QLineEdit(overlap_parent)
right = QtWidgets.QLineEdit(overlap_parent)
left.setText("left")
right.setText("right")
left.setObjectName("overlap_left_probe")
right.setObjectName("overlap_right_probe")
left.setGeometry(5, 5, 80, 30)
right.setGeometry(5, 5, 80, 30)
overlap_parent.show()
left.show()
right.show()
process()
findings = driver.scene_layout_findings([overlap_parent, left, right])
observed["obvious_sibling_overlap"] = "obvious_sibling_overlap" in kinds(findings)
examples["obvious_sibling_overlap"] = findings

task_panel = QtWidgets.QWidget(root)
task_panel.setObjectName("task_panel_no_scroll_path_probe")
task_panel.setGeometry(200, 10, 120, 60)
overflow_child = QtWidgets.QLabel("overflow", task_panel)
overflow_child.setGeometry(0, 90, 80, 24)
task_panel.show()
overflow_child.show()
process()
original_class_name = driver.class_name
try:
    def smoke_class_name(widget):
        if widget is task_panel:
            return "Gui::TaskView::TaskPanel"
        return original_class_name(widget)
    driver.class_name = smoke_class_name
    findings = driver.scene_layout_findings([task_panel, overflow_child])
finally:
    driver.class_name = original_class_name
observed["task_panel_no_scroll_path"] = "task_panel_no_scroll_path" in kinds(findings)
examples["task_panel_no_scroll_path"] = findings

required = set(json.loads(required_path.read_text(encoding="utf-8")).get("required_assertions", []))
missing = sorted(name for name in required if not observed.get(name))
report = {
    "schema": "freecad-gui-layout-assertion-smoke-v1",
    "result": "ok" if not missing else "failed",
    "required": sorted(required),
    "observed": observed,
    "missing": missing,
    "examples": examples,
}
output_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
QtWidgets.QApplication.closeAllWindows()
QtCore.QTimer.singleShot(0, app.quit)
"""


def run_smoke(
    freecad: Path,
    driver: Path,
    required_config: Path,
    output: Path,
    timeout: int,
) -> dict[str, Any]:
    with tempfile.NamedTemporaryFile("w", suffix="-layout-assertion-smoke.py", delete=False) as script:
        script.write(SMOKE_SCRIPT)
        script_path = Path(script.name)
    try:
        command = [str(freecad), str(script_path)]
        xvfb = ["xvfb-run", "-a", *command]
        env = dict(os.environ)
        env["FREECAD_LAYOUT_SMOKE_DRIVER"] = str(driver)
        env["FREECAD_LAYOUT_SMOKE_OUTPUT"] = str(output)
        env["FREECAD_LAYOUT_ASSERTION_CONFIG"] = str(required_config)
        try:
            proc = subprocess.run(
                xvfb,
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=timeout,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            report = {
                "schema": "freecad-gui-layout-assertion-smoke-v1",
                "result": "timeout",
                "required": [],
                "observed": {},
                "missing": [],
                "process_returncode": 124,
                "process_output": (exc.stdout.decode("utf-8", errors="replace") if isinstance(exc.stdout, bytes) else (exc.stdout or "")),
                "timeout": timeout,
            }
            output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            return report
    finally:
        script_path.unlink(missing_ok=True)

    report = json.loads(output.read_text(encoding="utf-8")) if output.exists() else {}
    report["process_returncode"] = proc.returncode
    report["process_output"] = proc.stdout
    if proc.returncode != 0 and report.get("result") == "ok":
        report["result"] = "process_failed"
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("freecad", type=Path, help="FreeCAD GUI wrapper")
    parser.add_argument("--driver", type=Path, default=Path("tools/gui_visual_baseline_driver.py"))
    parser.add_argument("--required-config", type=Path, default=Path("tools/gui_layout_assertions.default.json"))
    parser.add_argument("--output", type=Path, default=Path("/tmp/freecad-test-results/gui-layout-assertion-smoke.json"))
    parser.add_argument("--timeout", type=int, default=90)
    args = parser.parse_args()

    report = run_smoke(args.freecad, args.driver, args.required_config, args.output, args.timeout)
    return 0 if report.get("result") == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
