# SPDX-License-Identifier: LGPL-2.1-or-later

"""Regression tests for assembly-solver verification and compound measurement.

Two previously broken behaviors are pinned down:

1. ``assembly.create_joint`` and ``assembly.solve`` rolled back the whole
   transaction with a generic "FreeCAD transaction verification failed."
   whenever the native solver reported redundant constraints — including
   partial redundancies on a solved assembly (solver_code 0), which a fixed
   joint on an already-positioned component almost always produces.
   Redundancy is now a warning; only conflicts, malformed constraints, and
   hard solver errors fail, and failures carry a named error message.
2. ``part.measure`` crashed with ``AttributeError: 'Part.Compound' object
   has no attribute 'CenterOfMass'`` on compound objects (STEP imports).
"""

from __future__ import annotations

from types import SimpleNamespace

from tool_impl.service import domain_runtime, partdesign_measure


class TestAssemblySolverVerification:
    def test_redundancies_on_solved_assembly_pass_with_warning(self) -> None:
        verification = domain_runtime.assembly_solver_verification(
            {
                "solver_code": 0,
                "solver_diagnostics": {
                    "available": True,
                    "has_conflicts": False,
                    "has_malformed_constraints": False,
                    "has_redundancies": True,
                    "has_partial_redundancies": True,
                },
            }
        )
        assert verification["ok"] is True
        assert "error" not in verification
        assert verification["warnings"]

    def test_redundant_solver_code_passes_with_warning(self) -> None:
        verification = domain_runtime.assembly_solver_verification(
            {
                "solver_code": -2,
                "solver_diagnostics": {"available": True},
            }
        )
        assert verification["ok"] is True
        assert verification["warnings"]

    def test_conflicts_fail_with_named_joints(self) -> None:
        verification = domain_runtime.assembly_solver_verification(
            {
                "solver_code": 0,
                "solver_diagnostics": {
                    "available": True,
                    "has_conflicts": True,
                    "conflicting_joints": ["Joint007"],
                },
            }
        )
        assert verification["ok"] is False
        assert "Joint007" in verification["error"]

    def test_malformed_constraints_fail_with_named_joints(self) -> None:
        verification = domain_runtime.assembly_solver_verification(
            {
                "solver_code": 0,
                "solver_diagnostics": {
                    "available": True,
                    "has_malformed_constraints": True,
                    "malformed_joints": ["Joint003"],
                },
            }
        )
        assert verification["ok"] is False
        assert "Joint003" in verification["error"]

    def test_hard_solver_error_fails_with_verdict(self) -> None:
        verification = domain_runtime.assembly_solver_verification(
            {
                "solver_code": -3,
                "solver_diagnostics": {"available": True},
            }
        )
        assert verification["ok"] is False
        assert "conflicting_constraints" in verification["error"]

    def test_missing_diagnostics_fail_with_message(self) -> None:
        verification = domain_runtime.assembly_solver_verification(
            {
                "solver_code": 0,
                "solver_diagnostics": {"available": False},
            }
        )
        assert verification["ok"] is False
        assert "diagnostics" in verification["error"]


class TestShapeCenterForCompounds:
    def test_center_of_mass_passes_through_unchanged(self) -> None:
        center = SimpleNamespace(x=1.0, y=2.0, z=3.0)
        shape = SimpleNamespace(CenterOfMass=center)
        assert partdesign_measure._shape_center(shape) is center

    def test_compound_uses_volume_weighted_solid_centers(self) -> None:
        compound = SimpleNamespace(
            Solids=[
                SimpleNamespace(
                    CenterOfMass=SimpleNamespace(x=0.0, y=0.0, z=0.0), Volume=1.0
                ),
                SimpleNamespace(
                    CenterOfMass=SimpleNamespace(x=3.0, y=6.0, z=9.0), Volume=2.0
                ),
            ]
        )
        center = partdesign_measure._shape_center(compound)
        assert (center.x, center.y, center.z) == (2.0, 4.0, 6.0)

    def test_solidless_compound_falls_back_to_bound_box_center(self) -> None:
        box_center = SimpleNamespace(x=1.0, y=2.0, z=3.0)
        compound = SimpleNamespace(
            Solids=[], BoundBox=SimpleNamespace(Center=box_center)
        )
        assert partdesign_measure._shape_center(compound) is box_center
