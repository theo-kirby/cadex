# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileCopyrightText: 2025 FreeCAD contributors
# SPDX-FileNotice: Part of the FreeCAD project.

################################################################################
#                                                                              #
#   FreeCAD is free software: you can redistribute it and/or modify            #
#   it under the terms of the GNU Lesser General Public License as             #
#   published by the Free Software Foundation, either version 2.1              #
#   of the License, or (at your option) any later version.                     #
#                                                                              #
#   FreeCAD is distributed in the hope that it will be useful,                 #
#   but WITHOUT ANY WARRANTY; without even the implied warranty                #
#   of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.                    #
#   See the GNU Lesser General Public License for more details.               #
#                                                                              #
#   You should have received a copy of the GNU Lesser General Public          #
#   License along with FreeCAD. If not, see https://www.gnu.org/licenses      #
#                                                                              #
################################################################################

"""Machine safety validation for CAM jobs.

Validates the toolpaths and tool controllers of a CAM Job against the
physical capabilities of a Machine configuration:

* axis travel envelopes (linear and rotary)
* spindle / toolhead RPM limits
* feed rates versus axis maximum velocities

The entry point is :func:`validate_job_against_machine`, which returns a
list of structured :class:`Violation` records.  An empty list means the job
passed every check.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import Constants

from .machine import Machine, MachineFactory

# Severity levels
SEVERITY_ERROR = "error"
SEVERITY_WARNING = "warning"

# Violation codes
CODE_NO_MACHINE = "no_machine"
CODE_AXIS_LIMIT_EXCEEDED = "axis_limit_exceeded"
CODE_SPINDLE_RPM_EXCEEDED = "spindle_rpm_exceeded"
CODE_SPINDLE_RPM_BELOW_MINIMUM = "spindle_rpm_below_minimum"
CODE_FEED_EXCEEDS_AXIS_VELOCITY = "feed_exceeds_axis_velocity"

# Internal FreeCAD Path feed rates are stored in mm/s; machine axis
# max_velocity values are configured per-minute.
_FEED_PER_MINUTE_FACTOR = 60.0


@dataclass
class Violation:
    """A single machine-safety violation found while validating a job."""

    severity: str  # SEVERITY_ERROR or SEVERITY_WARNING
    code: str  # machine-readable violation code
    message: str  # human-readable description
    operation: Optional[str] = None  # label of the offending operation
    command_index: Optional[int] = None  # index of the offending path command
    details: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_error(self) -> bool:
        return self.severity == SEVERITY_ERROR

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to a plain dictionary."""
        return {
            "severity": self.severity,
            "code": self.code,
            "message": self.message,
            "operation": self.operation,
            "command_index": self.command_index,
            "details": dict(self.details),
        }


def _resolve_machine(job, machine: Optional[Machine]) -> Optional[Machine]:
    """Resolve the machine to validate against.

    Prefers an explicitly supplied machine; otherwise attempts to load the
    machine named on the job via MachineFactory.  Returns None when no
    machine can be resolved.
    """
    if machine is not None:
        return machine
    machine_name = getattr(job, "Machine", "") or ""
    if not machine_name:
        return None
    try:
        return MachineFactory.get_machine(machine_name)
    except (FileNotFoundError, ValueError):
        return None


def _job_operations(job) -> List[Any]:
    """Return the list of operations attached to a job (may be empty)."""
    operations = getattr(job, "Operations", None)
    group = getattr(operations, "Group", None)
    return list(group) if group else []


def _job_tool_controllers(job) -> List[Any]:
    """Return the list of tool controllers attached to a job (may be empty)."""
    tools = getattr(job, "Tools", None)
    group = getattr(tools, "Group", None)
    return list(group) if group else []


def _max_toolhead_rpm(machine: Machine) -> Optional[float]:
    """Highest max_rpm across toolheads, or None when unspecified."""
    limits = [th.max_rpm for th in machine.toolheads if getattr(th, "max_rpm", 0) > 0]
    return max(limits) if limits else None


def _min_toolhead_rpm(machine: Machine) -> Optional[float]:
    """Lowest positive min_rpm across toolheads, or None when unspecified."""
    limits = [th.min_rpm for th in machine.toolheads if getattr(th, "min_rpm", 0) > 0]
    return min(limits) if limits else None


def _validate_tool_controllers(job, machine: Machine) -> List[Violation]:
    """Check every tool controller's spindle speed against toolhead limits."""
    violations: List[Violation] = []
    max_rpm = _max_toolhead_rpm(machine)
    min_rpm = _min_toolhead_rpm(machine)
    if max_rpm is None and min_rpm is None:
        return violations

    for tc in _job_tool_controllers(job):
        speed = float(getattr(tc, "SpindleSpeed", 0) or 0)
        if speed <= 0:
            continue
        label = getattr(tc, "Label", getattr(tc, "Name", "ToolController"))
        if max_rpm is not None and speed > max_rpm:
            violations.append(
                Violation(
                    severity=SEVERITY_ERROR,
                    code=CODE_SPINDLE_RPM_EXCEEDED,
                    message=(
                        f"Tool controller '{label}' requests {speed:g} RPM but the "
                        f"machine's toolhead limit is {max_rpm:g} RPM"
                    ),
                    details={"tool_controller": label, "rpm": speed, "max_rpm": max_rpm},
                )
            )
        elif min_rpm is not None and speed < min_rpm:
            violations.append(
                Violation(
                    severity=SEVERITY_WARNING,
                    code=CODE_SPINDLE_RPM_BELOW_MINIMUM,
                    message=(
                        f"Tool controller '{label}' requests {speed:g} RPM which is "
                        f"below the machine's minimum spindle speed of {min_rpm:g} RPM"
                    ),
                    details={"tool_controller": label, "rpm": speed, "min_rpm": min_rpm},
                )
            )
    return violations


def _validate_command_position(
    machine: Machine,
    op_label: str,
    index: int,
    params: Dict[str, float],
    modal_position: Dict[str, float],
) -> List[Violation]:
    """Check one move command's axis words against the machine envelope."""
    violations: List[Violation] = []

    for axis_name, axis in machine.linear_axes.items():
        if axis_name not in params:
            continue
        value = params[axis_name]
        modal_position[axis_name] = value
        if not axis.is_valid_position(value):
            violations.append(
                Violation(
                    severity=SEVERITY_ERROR,
                    code=CODE_AXIS_LIMIT_EXCEEDED,
                    message=(
                        f"Operation '{op_label}' command {index} moves {axis_name} to "
                        f"{value:g} which is outside the machine's "
                        f"[{axis.min_limit:g}, {axis.max_limit:g}] envelope"
                    ),
                    operation=op_label,
                    command_index=index,
                    details={
                        "axis": axis_name,
                        "value": value,
                        "min_limit": axis.min_limit,
                        "max_limit": axis.max_limit,
                    },
                )
            )

    for axis_name, axis in machine.rotary_axes.items():
        if axis_name not in params:
            continue
        value = params[axis_name]
        modal_position[axis_name] = value
        if not (axis.min_limit <= value <= axis.max_limit):
            violations.append(
                Violation(
                    severity=SEVERITY_ERROR,
                    code=CODE_AXIS_LIMIT_EXCEEDED,
                    message=(
                        f"Operation '{op_label}' command {index} rotates {axis_name} to "
                        f"{value:g} which is outside the machine's "
                        f"[{axis.min_limit:g}, {axis.max_limit:g}] range"
                    ),
                    operation=op_label,
                    command_index=index,
                    details={
                        "axis": axis_name,
                        "value": value,
                        "min_limit": axis.min_limit,
                        "max_limit": axis.max_limit,
                    },
                )
            )

    return violations


def _validate_command_feed(
    machine: Machine,
    op_label: str,
    index: int,
    params: Dict[str, float],
) -> List[Violation]:
    """Check a command's feed rate against the max velocity of moving axes."""
    violations: List[Violation] = []
    feed = params.get("F")
    if feed is None or feed <= 0:
        return violations

    # Internal Path feed is mm/s; axis max_velocity is configured per-minute.
    feed_per_minute = feed * _FEED_PER_MINUTE_FACTOR

    moving_axes = [
        axis
        for name, axis in machine.linear_axes.items()
        if name in params and axis.max_velocity > 0
    ]
    if not moving_axes:
        return violations

    limit = max(axis.max_velocity for axis in moving_axes)
    if feed_per_minute > limit:
        violations.append(
            Violation(
                severity=SEVERITY_WARNING,
                code=CODE_FEED_EXCEEDS_AXIS_VELOCITY,
                message=(
                    f"Operation '{op_label}' command {index} feeds at "
                    f"{feed_per_minute:g} per minute which exceeds the fastest moving "
                    f"axis velocity of {limit:g}"
                ),
                operation=op_label,
                command_index=index,
                details={"feed_per_minute": feed_per_minute, "max_velocity": limit},
            )
        )
    return violations


def _validate_command_spindle(
    machine: Machine,
    op_label: str,
    index: int,
    params: Dict[str, float],
) -> List[Violation]:
    """Check an S word emitted in the path against toolhead RPM limits."""
    violations: List[Violation] = []
    speed = params.get("S")
    if speed is None or speed <= 0:
        return violations
    max_rpm = _max_toolhead_rpm(machine)
    if max_rpm is not None and speed > max_rpm:
        violations.append(
            Violation(
                severity=SEVERITY_ERROR,
                code=CODE_SPINDLE_RPM_EXCEEDED,
                message=(
                    f"Operation '{op_label}' command {index} sets spindle speed "
                    f"{speed:g} RPM above the machine's toolhead limit of {max_rpm:g} RPM"
                ),
                operation=op_label,
                command_index=index,
                details={"rpm": speed, "max_rpm": max_rpm},
            )
        )
    return violations


def _validate_operations(job, machine: Machine) -> List[Violation]:
    """Walk every path command of every operation and validate it."""
    violations: List[Violation] = []
    move_commands = set(Constants.GCODE_MOVE_ALL)

    for op in _job_operations(job):
        path = getattr(op, "Path", None)
        commands = getattr(path, "Commands", None)
        if not commands:
            continue
        op_label = getattr(op, "Label", getattr(op, "Name", "Operation"))
        modal_position: Dict[str, float] = {}

        for index, cmd in enumerate(commands):
            params = cmd.Parameters
            if cmd.Name in move_commands:
                violations.extend(
                    _validate_command_position(machine, op_label, index, params, modal_position)
                )
                violations.extend(_validate_command_feed(machine, op_label, index, params))
            violations.extend(_validate_command_spindle(machine, op_label, index, params))

    return violations


def validate_job_against_machine(job, machine: Optional[Machine] = None) -> List[Violation]:
    """Validate a CAM job against a machine configuration.

    Args:
        job: a CAM Job document object (Path.Main.Job feature).
        machine: an explicit Machine to validate against.  When omitted, the
            machine named by ``job.Machine`` is loaded through MachineFactory.

    Returns:
        List of Violation records.  Empty when the job passes every check.
        When no machine can be resolved, a single ``no_machine`` warning is
        returned instead of raising.
    """
    resolved = _resolve_machine(job, machine)
    if resolved is None:
        return [
            Violation(
                severity=SEVERITY_WARNING,
                code=CODE_NO_MACHINE,
                message=(
                    "No machine configuration is associated with this job; "
                    "machine safety checks were skipped"
                ),
            )
        ]

    violations: List[Violation] = []
    violations.extend(_validate_tool_controllers(job, resolved))
    violations.extend(_validate_operations(job, resolved))
    return violations
