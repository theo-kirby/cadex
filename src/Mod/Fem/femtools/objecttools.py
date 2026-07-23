# SPDX-License-Identifier: LGPL-2.1-or-later

# ***************************************************************************
# *   Copyright (c) 2026 Mario Passaglia <mpassaglia[at]cbc.uba.ar>         *
# *                                                                         *
# *   This file is part of FreeCAD.                                         *
# *                                                                         *
# *   FreeCAD is free software: you can redistribute it and/or modify it    *
# *   under the terms of the GNU Lesser General Public License as           *
# *   published by the Free Software Foundation, either version 2.1 of the  *
# *   License, or (at your option) any later version.                       *
# *                                                                         *
# *   FreeCAD is distributed in the hope that it will be useful, but        *
# *   WITHOUT ANY WARRANTY; without even the implied warranty of            *
# *   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU      *
# *   Lesser General Public License for more details.                       *
# *                                                                         *
# *   You should have received a copy of the GNU Lesser General Public      *
# *   License along with FreeCAD. If not, see                               *
# *   <https://www.gnu.org/licenses/>.                                      *
# *                                                                         *
# ***************************************************************************

__title__ = "Abstract base class for the work with solvers and meshers"
__author__ = "Mario Passaglia"
__url__ = "https://www.freecad.org"


from PySide.QtCore import QProcess
from abc import ABC, abstractmethod
from datetime import datetime, timezone
import os
import tempfile
import uuid

import FreeCAD


class ObjectTools(ABC):
    """Abstract base class for the work with solvers and meshers"""

    def __init__(self, obj):
        obj.Tool = self
        self.obj = obj
        self.model_file = ""
        self.process = QProcess()
        self.operation_id = str(uuid.uuid4())
        self.operation_state = "created"
        self.operation_error = None
        self.program = None
        self.arguments = []
        self.started_at = None
        self.finished_at = None
        self.cancel_requested = False
        self.stdout = ""
        self.stderr = ""
        self.property_update = {"status": "not_started"}
        self.analysis = obj.getParentGroup()
        self.fem_param = FreeCAD.ParamGet("User parameter:BaseApp/Preferences/Mod/Fem")
        self._create_working_directory()

        self.process.finished.connect(self._process_finished)
        self.process.started.connect(self._process_started)
        self.process.readyReadStandardOutput.connect(self._read_stdout)
        self.process.readyReadStandardError.connect(self._read_stderr)
        self.process.errorOccurred.connect(self._process_error)

    def _create_working_directory(self):
        """
        Create working directory according to preferences
        """
        if not os.path.isdir(self.obj.WorkingDirectory):
            gen_param = self.fem_param.GetGroup("General")
            if gen_param.GetBool("UseTempDirectory", True):
                self.obj.WorkingDirectory = tempfile.mkdtemp(prefix="fem_")
            elif gen_param.GetBool("UseBesideDirectory", False):
                root, ext = os.path.splitext(self.obj.Document.FileName)
                if root:
                    self.obj.WorkingDirectory = os.path.join(root, self.obj.Label)
                    os.makedirs(self.obj.WorkingDirectory, exist_ok=True)
                else:
                    # file not saved, use temporary
                    self.obj.WorkingDirectory = tempfile.mkdtemp(prefix="fem_")
            elif gen_param.GetBool("UseCustomDirectory", False):
                sub_dir = self.obj.Document.Name + "-" + self.obj.Label
                base_dir = gen_param.GetString("CustomDirectoryPath")
                # no custom directory, use home directory
                if not base_dir:
                    base_dir = FreeCAD.ConfigGet("UserHomePath")
                self.obj.WorkingDirectory = os.path.join(base_dir, sub_dir)
                os.makedirs(self.obj.WorkingDirectory, exist_ok=True)

    @abstractmethod
    def prepare(self):
        pass

    @abstractmethod
    def compute(self):
        pass

    @abstractmethod
    def update_properties(self):
        pass

    def run(self, blocking=False):
        self.operation_state = "preparing"
        try:
            self.prepare()
            self.operation_state = "starting"
            self.compute()
        except Exception as exc:
            self.operation_state = "failed"
            self.operation_error = str(exc)
            self.finished_at = self._utc_now()
            raise
        if blocking:
            return self.process.waitForFinished(-1)
        return self.operation_id

    def _process_finished(self, code, status):
        self._read_stdout()
        self._read_stderr()
        self.finished_at = self._utc_now()
        if self.cancel_requested:
            self.operation_state = "cancelled"
            self.property_update = {"status": "not_run", "reason": "cancelled"}
            return
        if status == QProcess.ExitStatus.NormalExit and code == 0:
            self.operation_state = "importing_results"
            try:
                self.update_properties()
                self.property_update = {"status": "completed"}
                self.operation_state = "completed"
            except Exception as exc:
                self.property_update = {
                    "status": "failed",
                    "native_error": str(exc),
                }
                self.operation_error = str(exc)
                self.operation_state = "failed"
        else:
            self.operation_state = "failed"
            if not self.operation_error:
                self.operation_error = (
                    f"External process exited with code {code} and status "
                    f"{self._exit_status_name(status)}."
                )

    def _process_started(self):
        self.operation_state = "running"
        self.started_at = self._utc_now()

    def _read_stdout(self):
        data = bytes(self.process.readAllStandardOutput()).decode("utf-8", errors="replace")
        if data:
            self.stdout += data

    def _read_stderr(self):
        data = bytes(self.process.readAllStandardError()).decode("utf-8", errors="replace")
        if data:
            self.stderr += data

    def _process_error(self, error):
        self._read_stdout()
        self._read_stderr()
        self.operation_error = self.process.errorString()
        if self.operation_state not in {"cancel_requested", "cancelled"}:
            self.operation_state = "failed"

    def cancel(self):
        """Request cancellation without blocking the GUI thread."""
        self.cancel_requested = True
        state = self.process.state()
        if state == QProcess.ProcessState.NotRunning:
            if self.operation_state not in {"completed", "failed"}:
                self.operation_state = "cancelled"
                self.finished_at = self._utc_now()
            return self.process_diagnostics()
        self.operation_state = "cancel_requested"
        self.process.terminate()
        return self.process_diagnostics()

    def kill(self):
        """Force a process to stop after a prior graceful cancellation request."""
        self.cancel_requested = True
        self.operation_state = "cancel_requested"
        self.process.kill()
        return self.process_diagnostics()

    def process_diagnostics(self):
        """Return exact external-process state without consuming output."""
        self._read_stdout()
        self._read_stderr()
        process_state = self.process.state()
        exit_code = None
        exit_status = None
        if process_state == QProcess.ProcessState.NotRunning and self.started_at:
            exit_code = int(self.process.exitCode())
            exit_status = self._exit_status_name(self.process.exitStatus())
        return {
            "operation_id": self.operation_id,
            "operation_state": self.operation_state,
            "process": {
                "state": self._process_state_name(process_state),
                "pid": int(self.process.processId()) if self.process.processId() else None,
                "program": self.program,
                "arguments": list(self.arguments),
                "working_directory": self.process.workingDirectory(),
                "exit_code": exit_code,
                "exit_status": exit_status,
                "error": self.operation_error,
                "stdout": self.stdout,
                "stderr": self.stderr,
            },
            "progress": self._progress(),
            "cancel_requested": self.cancel_requested,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "property_update": dict(self.property_update),
        }

    def _progress(self):
        fractions = {
            "created": 0.0,
            "preparing": 0.05,
            "starting": 0.15,
            "running": 0.5,
            "importing_results": 0.9,
            "completed": 1.0,
            "failed": 1.0,
            "cancel_requested": 0.5,
            "cancelled": 1.0,
        }
        return {
            "stage": self.operation_state,
            "fraction": fractions.get(self.operation_state),
            "indeterminate_within_stage": self.operation_state == "running",
        }

    @staticmethod
    def _process_state_name(state):
        return {
            QProcess.ProcessState.NotRunning: "not_running",
            QProcess.ProcessState.Starting: "starting",
            QProcess.ProcessState.Running: "running",
        }.get(state, str(state))

    @staticmethod
    def _exit_status_name(status):
        return {
            QProcess.ExitStatus.NormalExit: "normal_exit",
            QProcess.ExitStatus.CrashExit: "crash_exit",
        }.get(status, str(status))

    @staticmethod
    def _utc_now():
        return datetime.now(timezone.utc).isoformat()
