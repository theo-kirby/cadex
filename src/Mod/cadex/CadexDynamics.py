# SPDX-License-Identifier: LGPL-2.1-or-later

"""The assembly-to-MuJoCo translator (ADR-062, docs/MUJOCO.md slice M2).

This module imports nothing from FreeCAD and knows nothing about topology.
The worker reads the solved assembly out of FreeCAD and hands this module
plain JSON-round-trippable dicts: solved component placements, per-connector
local frames, per-solid mass-property readings. Everything after that --
frame algebra, unit conversion, spanning-tree extraction, the ``mjSpec``
build, the stepping loop -- happens here, headless and unit-testable, in the
same idiom as :mod:`CadexRouting` (ADR-056).

**The split rule, stated once:** the pure module does every arithmetic
operation *including every unit conversion*; the worker does every FreeCAD
read and nothing else. ``test_dynamics_units`` greps the assembly stack to
keep that true, which is why the three conversion functions below carry
their factors as literals rather than hiding them behind a constant.

``mujoco`` is imported inside the functions that build a model, never at
module scope. Two reasons, both load-bearing: the graph algebra stays
testable in an environment without it, and
``test_engine_purity_guardrails`` asserts the engine's import closure equals
``DECLARED_ENGINE_MODULES`` exactly -- this module is staged into the
sandbox *by filename* like every other worker module, so nothing in
``cadexd`` may ever reach it.

Conventions, chosen once and not renegotiated anywhere downstream:

* **Lengths are millimetres** at every boundary this module is handed and
  every boundary it produces, because that is what FreeCAD, the trace schema
  and the shell all speak. Metres exist only between :func:`build_model` and
  :func:`simulate`, inside MuJoCo.
* **Placements are 16-float row-major 4x4 matrices**, exactly what
  ``cadex_assembly_worker._placement_fact`` already publishes as ``matrix``.
* **Quaternions are (w, x, y, z) inside MuJoCo and (x, y, z, w) in the
  trace.** Both orders appear in this module, and every function says which
  it means in its name.
"""

from __future__ import annotations

import ast
import math
from typing import Any, Mapping, Sequence

__all__ = [
    "DynamicsError",
    "MM_PER_METRE",
    "DEFAULT_GRAVITY_M_S2",
    "MINIMUM_DENSITY_KG_M3",
    "MAXIMUM_DENSITY_KG_M3",
    "length_m",
    "length_mm",
    "vector_m",
    "vector_mm",
    "mass_kg",
    "inertia_kg_m2",
    "torque_nm",
    "angle_radians",
    "speed_m_s",
    "stiffness_nm_per_rad",
    "stiffness_n_per_m",
    "damping_nms_per_rad",
    "damping_ns_per_m",
    "armature_kg_m2",
    "checked_density",
    "IDENTITY_MATRIX",
    "checked_rigid_matrix",
    "matrix_multiply",
    "matrix_inverse",
    "matrix_translation_mm",
    "matrix_rotation",
    "matrix_z_axis",
    "matrix_from_rotation_translation",
    "quaternion_wxyz_from_matrix",
    "matrix_from_quaternion_wxyz",
    "quaternion_wxyz_from_xyzw",
    "quaternion_xyzw_from_wxyz",
    "quaternion_multiply_wxyz",
    "quaternion_conjugate_wxyz",
    "quaternion_rotate_wxyz",
    "quaternion_normalised",
    "quaternion_from_axis_angle_wxyz",
    "rotation_angle_between",
    # inertia
    "body_inertial",
    "full_inertia_six",
    # collision
    "DEFAULT_COLLISION_DEFLECTION_MM",
    "COLLISION_CONVEXITY_TOLERANCE",
    "COLLISION_TESSELLATION_TOLERANCE",
    "MAXIMUM_COLLISION_VERTICES",
    "collision_deflection_mm",
    "mesh_volume_mm3",
    "convex_hull_volume_mm3",
    "collision_geoms",
    # the graph
    "JOINT_TABLE",
    "classify_joints",
    "extract_tree",
    "joint_transform",
    "joint_coordinates",
    "closure_residuals",
    # actuation
    "joint_dynamics_records",
    "actuator_records",
    "compile_control",
    "evaluate_control",
    "control_si",
    # the model
    "build_model",
    "simulate",
    "model_evidence",
    # export
    "export_mjcf",
    "MAXIMUM_MJCF_BYTES",
    "MJCF_KEYFRAME_NAME",
    "MJCF_MASS_TOLERANCE",
    "MJCF_INERTIA_TOLERANCE",
    "MJCF_FIELD_TOLERANCE",
    "MJCF_POSE_TOLERANCE_MM",
    "DEFAULT_TIME_STEP_S",
    "CLOSURE_RESIDUAL_MM",
    "CLOSURE_RESIDUAL_RADIANS",
    "CLOSURE_EQUALITY_TOLERANCE",
    "MAXIMUM_ACTUATOR_OMEGA_STEP",
    "MAXIMUM_DAMPING_RATE_PER_S",
]


#: One metre, in the unit FreeCAD speaks.
MM_PER_METRE = 1000.0

#: Standard gravity, in the unit MuJoCo integrates in. Not a script
#: parameter in M2 -- deliberately, so there is exactly one number to be
#: wrong about while the translator is being proved.
DEFAULT_GRAVITY_M_S2 = (0.0, 0.0, -9.81)

#: Density is required and never defaulted: a default is a number that makes
#: the output look plausible and be wrong. The bounds are wide enough for
#: foam (~30) through tungsten (~19300) with headroom, and narrow enough to
#: catch a value entered in g/cm³ (steel would read 7.85) or kg/mm³.
MINIMUM_DENSITY_KG_M3 = 0.0
MAXIMUM_DENSITY_KG_M3 = 30000.0

#: Below this a matrix column is not an axis and a quaternion is not a
#: rotation.
_TINY = 1.0e-12

#: How far a claimed rigid placement may drift from orthonormal before it is
#: refused. FreeCAD placements are built from unit quaternions, so real ones
#: land many orders of magnitude inside this; a mirrored or scaled
#: occurrence lands far outside it.
_ORTHONORMAL_TOLERANCE = 1.0e-9

IDENTITY_MATRIX: tuple[float, ...] = (
    1.0, 0.0, 0.0, 0.0,
    0.0, 1.0, 0.0, 0.0,
    0.0, 0.0, 1.0, 0.0,
    0.0, 0.0, 0.0, 1.0,
)


class DynamicsError(ValueError):
    """A model that could not be built, with the reason named.

    ``reason`` is a stable machine-readable code the worker turns into a
    candidate-failure stage; ``correction`` is the sentence the model reads
    and acts on. Every refusal in this module carries both -- an unmappable
    joint, an ungrounded assembly and a mirrored occurrence are all author
    errors, and a refusal that does not say what to change is a bug report
    addressed to nobody.
    """

    def __init__(
        self,
        message: str,
        *,
        reason: str,
        correction: str = "",
        observed: Mapping[str, Any] | None = None,
    ) -> None:
        self.reason = str(reason)
        self.correction = str(correction)
        self.observed = dict(observed or {})
        super().__init__(str(message))


# ---------------------------------------------------------------------------
# The units boundary. All of it, and nothing else anywhere.
# ---------------------------------------------------------------------------


def length_m(value_mm: float) -> float:
    """Millimetres to metres."""

    return float(value_mm) / MM_PER_METRE


def length_mm(value_m: float) -> float:
    """Metres to millimetres."""

    return float(value_m) * MM_PER_METRE


def vector_m(value_mm: Sequence[float]) -> list[float]:
    return [length_m(item) for item in value_mm]


def vector_mm(value_m: Sequence[float]) -> list[float]:
    return [length_mm(item) for item in value_m]


def mass_kg(density_kg_m3: float, volume_mm3: float) -> float:
    """ρ·V, with the volume carried in mm³ and the answer in kilograms.

    1 mm³ is 1e-9 m³. A 100 mm steel cube is 7.85 kg.
    """

    return float(density_kg_m3) * float(volume_mm3) * 1.0e-9


def inertia_kg_m2(density_kg_m3: float, tensor_mm5: Sequence[float]) -> list[float]:
    """ρ·J, with OCCT's unit-density tensor in mm⁵ and the answer in kg·m².

    The exponent is the point: an inertia tensor is mass times length
    squared, so the density carries 1e-9 (mm³ to m³) and the moment arm
    another 1e-6 (mm² to m²).
    """

    return [float(density_kg_m3) * float(item) * 1.0e-15 for item in tensor_mm5]


def torque_nm(value_nmm: float) -> float:
    """Newton-millimetres to newton-metres.

    A torque is a force times a lever arm and only the arm carries a length,
    so this is the same thousand :func:`length_m` divides by. 8000 N·mm is a
    small servo; 8000 N·m is a driveshaft.
    """

    return float(value_nmm) / MM_PER_METRE


def torque_nmm(value_nm: float) -> float:
    """Newton-metres to newton-millimetres, for a torque leaving MuJoCo.

    The inverse of :func:`torque_nm`, and it exists for the same reason
    :func:`angle_degrees` does: an ``actuator_force`` observation is a
    torque, and the surface that reads it speaks N·mm.
    """

    return float(value_nm) * MM_PER_METRE


def angle_radians(value_degrees: float) -> float:
    """Degrees to radians, at the one boundary that is allowed to do it.

    ``compiler.degree`` is False for every model this module builds (M2
    measured what leaving it alone costs), so a setpoint that arrived in
    degrees and was not converted would be a 57x error that runs.
    """

    return math.radians(float(value_degrees))


def angle_degrees(value_radians: float) -> float:
    """Radians to degrees -- the first angle to travel *out* of MuJoCo.

    Every conversion above carries a number the script wrote into the unit
    MuJoCo reads. This one goes the other way, and the reason that is more
    dangerous rather than less is who does the arithmetic downstream: an
    observation channel is read by a *trainer*, outside this process, out of
    a raw ``sensordata`` array. So the factor is not applied here and hoped
    for -- it is emitted into the task bundle as that channel's ``scale``,
    and the trainer multiplies rather than converts (M6).

    Note it is also the only conversion on this boundary that is not a power
    of ten: a decimal point in the wrong place looks wrong, and 57x looks
    like a mechanism.
    """

    return math.degrees(float(value_radians))


def speed_m_s(value_mm_per_s: float) -> float:
    """Millimetres per second to metres per second."""

    return length_m(value_mm_per_s)


def speed_mm_per_s(value_m_s: float) -> float:
    """Metres per second to millimetres per second."""

    return length_mm(value_m_s)


def stiffness_nm_per_rad(value_nmm_per_deg: float) -> float:
    """N·mm per degree to N·m per radian -- two conversions in one factor.

    The length divides by a thousand and the angle multiplies by 180/π, and
    both moves are in the *same* direction, so getting one right and the
    other wrong lands within a factor of sixty of correct: an arm that still
    holds, badly, and that nobody looks at again.
    """

    return torque_nm(value_nmm_per_deg) / math.radians(1.0)


def stiffness_n_per_m(value_n_per_mm: float) -> float:
    """N per millimetre to N per metre.

    Note the direction: this *multiplies* by a thousand where the angular
    gain above divides. That opposition is the whole argument for the
    suffixed parameter pairs -- one ``stiffness=`` whose meaning depended on
    the joint's kind would be off by five million between its two readings
    of the same number.
    """

    return float(value_n_per_mm) * MM_PER_METRE


def damping_nms_per_rad(value_nmms_per_deg: float) -> float:
    """N·mm·s per degree to N·m·s per radian -- the gain factor, per second."""

    return stiffness_nm_per_rad(value_nmms_per_deg)


def damping_ns_per_m(value_ns_per_mm: float) -> float:
    """N·s per millimetre to N·s per metre."""

    return stiffness_n_per_m(value_ns_per_mm)


def armature_kg_m2(value_kg_mm2: float) -> float:
    """kg·mm² to kg·m².

    Unlike :func:`inertia_kg_m2` there is no density in it: an armature is a
    rotor inertia the script states outright, so only the length unit moves
    and the exponent is 6 rather than 15.
    """

    return float(value_kg_mm2) * 1.0e-6


def checked_density(value: Any, *, context: str) -> float:
    """One density, validated with the refusal naming real materials."""

    try:
        density = float(value)
    except (TypeError, ValueError):
        density = math.nan
    if isinstance(value, bool) or not math.isfinite(density):
        density = math.nan
    if math.isnan(density) or not (
        MINIMUM_DENSITY_KG_M3 < density <= MAXIMUM_DENSITY_KG_M3
    ):
        raise DynamicsError(
            f"{context} needs a density greater than {MINIMUM_DENSITY_KG_M3:g} and "
            f"at most {MAXIMUM_DENSITY_KG_M3:g} kg/m³; received {value!r}.",
            reason="density_out_of_range",
            correction=(
                "Give density_kg_m3 in kilograms per cubic metre -- steel 7850, "
                "aluminium 2700, ABS 1040. There is no default: a guessed density "
                "makes every mass, every inertia and every fall time wrong while "
                "the animation still looks plausible."
            ),
            observed={"context": context, "density_kg_m3": repr(value)},
        )
    return density


# ---------------------------------------------------------------------------
# Frame algebra. 16-float row-major 4x4, exactly what _placement_fact emits.
# ---------------------------------------------------------------------------


def _floats(value: Any, *, count: int, context: str) -> list[float]:
    if isinstance(value, (str, bytes)) or not isinstance(value, (list, tuple)):
        raise DynamicsError(
            f"{context} must be {count} finite numbers, not {type(value).__name__}.",
            reason="malformed_frame",
            observed={"context": context},
        )
    items = list(value)
    if len(items) != count:
        raise DynamicsError(
            f"{context} must be {count} finite numbers; received {len(items)}.",
            reason="malformed_frame",
            observed={"context": context, "length": len(items)},
        )
    result: list[float] = []
    for index, item in enumerate(items):
        try:
            number = float(item)
        except (TypeError, ValueError) as exc:
            raise DynamicsError(
                f"{context}[{index}] is not a finite number.",
                reason="malformed_frame",
                observed={"context": context, "index": index},
            ) from exc
        if not math.isfinite(number):
            raise DynamicsError(
                f"{context}[{index}] is not a finite number.",
                reason="malformed_frame",
                observed={"context": context, "index": index},
            )
        result.append(number)
    return result


def checked_rigid_matrix(value: Any, *, context: str) -> list[float]:
    """One placement matrix, proved to be a rotation plus a translation.

    A mirrored occurrence (negative determinant) is refused rather than
    approximated: MuJoCo has no way to represent a reflection, and the
    nearest rotation to one is a part built inside out.
    """

    matrix = _floats(value, count=16, context=context)
    bottom = [matrix[12], matrix[13], matrix[14], matrix[15]]
    if any(abs(bottom[index]) > _ORTHONORMAL_TOLERANCE for index in range(3)) or abs(
        bottom[3] - 1.0
    ) > _ORTHONORMAL_TOLERANCE:
        raise DynamicsError(
            f"{context} is not an affine placement; its last row is {bottom}.",
            reason="malformed_frame",
            correction="Placements come from FreeCAD; this one has been rewritten.",
            observed={"context": context, "bottom_row": bottom},
        )
    columns = [
        [matrix[0], matrix[4], matrix[8]],
        [matrix[1], matrix[5], matrix[9]],
        [matrix[2], matrix[6], matrix[10]],
    ]
    for index, column in enumerate(columns):
        norm = math.sqrt(sum(item * item for item in column))
        if abs(norm - 1.0) > _ORTHONORMAL_TOLERANCE:
            raise DynamicsError(
                f"{context} carries a scale: axis {index} has length {norm:.12g}.",
                reason="scaled_occurrence",
                correction=(
                    "MuJoCo bodies are rigid and unscaled. Model the part at its "
                    "real size instead of scaling an occurrence."
                ),
                observed={"context": context, "axis": index, "length": norm},
            )
    determinant = (
        columns[0][0] * (columns[1][1] * columns[2][2] - columns[1][2] * columns[2][1])
        - columns[1][0] * (columns[0][1] * columns[2][2] - columns[0][2] * columns[2][1])
        + columns[2][0] * (columns[0][1] * columns[1][2] - columns[0][2] * columns[1][1])
    )
    if determinant < 0.0:
        raise DynamicsError(
            f"{context} is mirrored (determinant {determinant:.6g}).",
            reason="mirrored_occurrence",
            correction=(
                "A reflection is not a rotation and MuJoCo cannot carry one. "
                "Model the mirrored part as its own solid rather than mirroring "
                "an occurrence into the assembly."
            ),
            observed={"context": context, "determinant": determinant},
        )
    return matrix


def matrix_multiply(first: Sequence[float], second: Sequence[float]) -> list[float]:
    """``first ∘ second`` -- apply ``second`` first, in ``first``'s frame."""

    result = [0.0] * 16
    for row in range(4):
        for column in range(4):
            result[row * 4 + column] = sum(
                float(first[row * 4 + index]) * float(second[index * 4 + column])
                for index in range(4)
            )
    return result


def matrix_inverse(matrix: Sequence[float]) -> list[float]:
    """The inverse of a rigid placement, by transposing its rotation."""

    rotation = [
        [float(matrix[0]), float(matrix[1]), float(matrix[2])],
        [float(matrix[4]), float(matrix[5]), float(matrix[6])],
        [float(matrix[8]), float(matrix[9]), float(matrix[10])],
    ]
    translation = [float(matrix[3]), float(matrix[7]), float(matrix[11])]
    inverse_translation = [
        -sum(rotation[index][row] * translation[index] for index in range(3))
        for row in range(3)
    ]
    return [
        rotation[0][0], rotation[1][0], rotation[2][0], inverse_translation[0],
        rotation[0][1], rotation[1][1], rotation[2][1], inverse_translation[1],
        rotation[0][2], rotation[1][2], rotation[2][2], inverse_translation[2],
        0.0, 0.0, 0.0, 1.0,
    ]


def matrix_translation_mm(matrix: Sequence[float]) -> list[float]:
    return [float(matrix[3]), float(matrix[7]), float(matrix[11])]


def matrix_rotation(matrix: Sequence[float]) -> list[float]:
    """The 3x3 rotation block, row-major."""

    return [
        float(matrix[0]), float(matrix[1]), float(matrix[2]),
        float(matrix[4]), float(matrix[5]), float(matrix[6]),
        float(matrix[8]), float(matrix[9]), float(matrix[10]),
    ]


def matrix_z_axis(matrix: Sequence[float]) -> list[float]:
    """The frame's local +Z in its parent's coordinates.

    The same three entries ``cadex_assembly_worker._frame_z_axis`` reads,
    and for the same reason: FreeCAD's JCS convention puts every joint axis
    on the connector frame's +Z.
    """

    return [float(matrix[2]), float(matrix[6]), float(matrix[10])]


def matrix_from_rotation_translation(
    rotation: Sequence[float], translation_mm: Sequence[float]
) -> list[float]:
    return [
        float(rotation[0]), float(rotation[1]), float(rotation[2]), float(translation_mm[0]),
        float(rotation[3]), float(rotation[4]), float(rotation[5]), float(translation_mm[1]),
        float(rotation[6]), float(rotation[7]), float(rotation[8]), float(translation_mm[2]),
        0.0, 0.0, 0.0, 1.0,
    ]


# ---------------------------------------------------------------------------
# Quaternions.
# ---------------------------------------------------------------------------


def quaternion_normalised(quaternion: Sequence[float]) -> list[float]:
    values = [float(item) for item in quaternion]
    magnitude = math.sqrt(sum(item * item for item in values))
    if magnitude <= _TINY:
        raise DynamicsError(
            "A zero-length quaternion is not a rotation.",
            reason="malformed_frame",
        )
    return [item / magnitude for item in values]


def quaternion_wxyz_from_matrix(matrix: Sequence[float]) -> list[float]:
    """Shepperd's method: pick the largest diagonal term, never divide by ~0."""

    m00, m01, m02 = float(matrix[0]), float(matrix[1]), float(matrix[2])
    m10, m11, m12 = float(matrix[4]), float(matrix[5]), float(matrix[6])
    m20, m21, m22 = float(matrix[8]), float(matrix[9]), float(matrix[10])
    trace = m00 + m11 + m22
    if trace > 0.0:
        scale = math.sqrt(trace + 1.0) * 2.0
        quaternion = [
            0.25 * scale,
            (m21 - m12) / scale,
            (m02 - m20) / scale,
            (m10 - m01) / scale,
        ]
    elif m00 > m11 and m00 > m22:
        scale = math.sqrt(1.0 + m00 - m11 - m22) * 2.0
        quaternion = [
            (m21 - m12) / scale,
            0.25 * scale,
            (m01 + m10) / scale,
            (m02 + m20) / scale,
        ]
    elif m11 > m22:
        scale = math.sqrt(1.0 + m11 - m00 - m22) * 2.0
        quaternion = [
            (m02 - m20) / scale,
            (m01 + m10) / scale,
            0.25 * scale,
            (m12 + m21) / scale,
        ]
    else:
        scale = math.sqrt(1.0 + m22 - m00 - m11) * 2.0
        quaternion = [
            (m10 - m01) / scale,
            (m02 + m20) / scale,
            (m12 + m21) / scale,
            0.25 * scale,
        ]
    return quaternion_normalised(quaternion)


def matrix_from_quaternion_wxyz(
    quaternion: Sequence[float], translation_mm: Sequence[float] = (0.0, 0.0, 0.0)
) -> list[float]:
    w, x, y, z = quaternion_normalised(quaternion)
    rotation = [
        1.0 - 2.0 * (y * y + z * z), 2.0 * (x * y - z * w), 2.0 * (x * z + y * w),
        2.0 * (x * y + z * w), 1.0 - 2.0 * (x * x + z * z), 2.0 * (y * z - x * w),
        2.0 * (x * z - y * w), 2.0 * (y * z + x * w), 1.0 - 2.0 * (x * x + y * y),
    ]
    return matrix_from_rotation_translation(rotation, translation_mm)


def quaternion_wxyz_from_xyzw(quaternion: Sequence[float]) -> list[float]:
    x, y, z, w = (float(item) for item in quaternion)
    return [w, x, y, z]


def quaternion_xyzw_from_wxyz(quaternion: Sequence[float]) -> list[float]:
    w, x, y, z = (float(item) for item in quaternion)
    return [x, y, z, w]


def quaternion_multiply_wxyz(
    first: Sequence[float], second: Sequence[float]
) -> list[float]:
    w1, x1, y1, z1 = (float(item) for item in first)
    w2, x2, y2, z2 = (float(item) for item in second)
    return [
        w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2,
        w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2,
        w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2,
        w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2,
    ]


def quaternion_conjugate_wxyz(quaternion: Sequence[float]) -> list[float]:
    w, x, y, z = (float(item) for item in quaternion)
    return [w, -x, -y, -z]


def quaternion_rotate_wxyz(
    quaternion: Sequence[float], vector: Sequence[float]
) -> list[float]:
    rotated = quaternion_multiply_wxyz(
        quaternion_multiply_wxyz(quaternion, [0.0, *(float(item) for item in vector)]),
        quaternion_conjugate_wxyz(quaternion),
    )
    return rotated[1:]


def quaternion_from_axis_angle_wxyz(
    axis: Sequence[float], angle_radians: float
) -> list[float]:
    values = [float(item) for item in axis]
    magnitude = math.sqrt(sum(item * item for item in values))
    if magnitude <= _TINY:
        raise DynamicsError(
            "A zero-length axis is not a rotation axis.", reason="malformed_frame"
        )
    half = float(angle_radians) / 2.0
    scale = math.sin(half) / magnitude
    return [math.cos(half), *(item * scale for item in values)]


def rotation_angle_between(
    first_wxyz: Sequence[float], second_wxyz: Sequence[float]
) -> float:
    """The absolute angle in radians between two orientations.

    Hemisphere-insensitive: q and -q are the same rotation, and comparing
    them componentwise is one of the five silent failure modes the shell's
    animation bake documents.
    """

    dot = abs(
        sum(
            float(a) * float(b)
            for a, b in zip(
                quaternion_normalised(first_wxyz),
                quaternion_normalised(second_wxyz),
                strict=True,
            )
        )
    )
    return 2.0 * math.acos(max(-1.0, min(1.0, dot)))


# ---------------------------------------------------------------------------
# Inertia. The differentiator: exact OCCT mass properties, not a hull guess.
# ---------------------------------------------------------------------------


def _symmetric_eigenvalues(tensor: Sequence[float]) -> list[float]:
    """Principal moments of a symmetric 3x3, by cyclic Jacobi rotations.

    Fixed sweep count rather than a convergence tolerance, so the answer is
    the same on every run and every platform -- ``open_project`` re-runs the
    accepted script and asserts digest equality, and an inertia validation
    that varies breaks the project rather than merely the body.
    """

    matrix = [
        [float(tensor[0]), float(tensor[1]), float(tensor[2])],
        [float(tensor[3]), float(tensor[4]), float(tensor[5])],
        [float(tensor[6]), float(tensor[7]), float(tensor[8])],
    ]
    for _sweep in range(24):
        if all(
            matrix[row][column] == 0.0 for row, column in ((0, 1), (0, 2), (1, 2))
        ):
            break
        for row, column in ((0, 1), (0, 2), (1, 2)):
            pivot = matrix[row][column]
            if pivot == 0.0:
                continue
            theta = (matrix[column][column] - matrix[row][row]) / (2.0 * pivot)
            sign = 1.0 if theta >= 0.0 else -1.0
            tangent = sign / (abs(theta) + math.sqrt(theta * theta + 1.0))
            cosine = 1.0 / math.sqrt(tangent * tangent + 1.0)
            sine = tangent * cosine
            row_value = matrix[row][row]
            column_value = matrix[column][column]
            matrix[row][row] = row_value - tangent * pivot
            matrix[column][column] = column_value + tangent * pivot
            matrix[row][column] = 0.0
            matrix[column][row] = 0.0
            for index in range(3):
                if index in (row, column):
                    continue
                first = matrix[index][row]
                second = matrix[index][column]
                matrix[index][row] = cosine * first - sine * second
                matrix[row][index] = matrix[index][row]
                matrix[index][column] = sine * first + cosine * second
                matrix[column][index] = matrix[index][column]
    return sorted(matrix[index][index] for index in range(3))


def _parallel_axis_mm5(volume_mm3: float, offset_mm: Sequence[float]) -> list[float]:
    """``V·(‖d‖²E − d·dᵀ)`` -- the shift term, at unit density, in mm⁵."""

    dx, dy, dz = (float(item) for item in offset_mm)
    squared = dx * dx + dy * dy + dz * dz
    return [
        volume_mm3 * (squared - dx * dx),
        volume_mm3 * (-dx * dy),
        volume_mm3 * (-dx * dz),
        volume_mm3 * (-dy * dx),
        volume_mm3 * (squared - dy * dy),
        volume_mm3 * (-dy * dz),
        volume_mm3 * (-dz * dx),
        volume_mm3 * (-dz * dy),
        volume_mm3 * (squared - dz * dz),
    ]


def body_inertial(
    readings: Sequence[Mapping[str, Any]],
    density_kg_m3: float,
    *,
    context: str,
) -> dict[str, Any]:
    """Mass, centre of mass and inertia tensor for one component's solids.

    ``readings`` is what ``cadex_assembly_worker._solid_inertia_readings``
    produces: one entry per ``TopoShapeSolid``, each carrying its volume in
    mm³, its centre of mass in the component's own frame, and its inertia
    tensor **about its own centre of mass** in mm⁵ at unit density.

    Two things are deliberate here.

    *The tensor is read about the solid's own centre of mass*, by
    translating a copy of the solid, rather than read about the origin and
    corrected afterwards. ``J_origin − V·(‖C‖²E − C·Cᵀ)`` is a difference of
    near-equal large numbers: a part modelled 500 mm from the origin has an
    origin term about 150 times the centre-of-mass term, so a 1 mm feature
    at 10⁴ mm loses roughly nine significant digits to cancellation.
    Translating first cannot cancel.

    *Multi-solid components are summed about a common point*, which is the
    combined centre of mass -- adding tensors taken about different points
    is meaningless and produces a number that still passes every sanity
    check MuJoCo applies (hazard 2).

    The result is what a MuJoCo body wants: ``mass``, ``ipos`` (the centre
    of mass **in the component frame**, because the body frame is the
    component frame -- hazard 4) and ``fullinertia`` about that centre.
    """

    density = checked_density(density_kg_m3, context=context)
    if not readings:
        raise DynamicsError(
            f"{context} has no solid to take mass properties from.",
            reason="no_solid",
            correction=(
                "A dynamics body needs a component whose shape contains at least "
                "one solid. A wire, a face or an empty compound has no mass."
            ),
            observed={"context": context},
        )
    entries: list[tuple[float, list[float], list[float]]] = []
    for index, reading in enumerate(readings):
        volume = float(reading["volume_mm3"])
        if not math.isfinite(volume) or volume <= 0.0:
            raise DynamicsError(
                f"{context} solid {index} has volume {volume:g} mm³.",
                reason="degenerate_solid",
                correction=(
                    "Every solid must enclose a positive volume. Check for an "
                    "inverted or self-intersecting solid in the source part."
                ),
                observed={"context": context, "solid_index": index, "volume_mm3": volume},
            )
        centre = _floats(
            reading["center_of_mass_mm"], count=3, context=f"{context} solid {index} COM"
        )
        tensor = _floats(
            reading["inertia_mm5_about_com"],
            count=9,
            context=f"{context} solid {index} inertia",
        )
        entries.append((volume, centre, tensor))

    total_volume = math.fsum(volume for volume, _centre, _tensor in entries)
    centre_of_mass = [
        math.fsum(volume * centre[axis] for volume, centre, _tensor in entries)
        / total_volume
        for axis in range(3)
    ]
    combined = [0.0] * 9
    for volume, centre, tensor in entries:
        offset = [centre[axis] - centre_of_mass[axis] for axis in range(3)]
        shift = _parallel_axis_mm5(volume, offset)
        for index in range(9):
            combined[index] += tensor[index] + shift[index]
    # Symmetrise: the two halves differ only by rounding, and MuJoCo reads
    # six numbers from a matrix we would otherwise be asserting nine of.
    for row, column in ((0, 1), (0, 2), (1, 2)):
        average = 0.5 * (combined[row * 3 + column] + combined[column * 3 + row])
        combined[row * 3 + column] = average
        combined[column * 3 + row] = average

    tensor_kg_m2 = inertia_kg_m2(density, combined)
    principal = _symmetric_eigenvalues(tensor_kg_m2)
    largest = max(principal)
    if principal[0] <= 0.0:
        raise DynamicsError(
            f"{context} has a non-positive principal moment of inertia "
            f"({principal[0]:.6g} kg·m²).",
            reason="degenerate_inertia",
            correction=(
                "The component's solids do not form a body with volume in three "
                "dimensions. Check for a zero-thickness or duplicated solid."
            ),
            observed={"context": context, "principal_kg_m2": principal},
        )
    # A + B >= C. MuJoCo enforces this with *no* tolerance at all -- a
    # violation of one part in 1e9 is refused -- so the check is here, where
    # the refusal can name the component. It is stated with a tolerance
    # rather than bare because a sheet-metal part sits arithmetically on the
    # boundary: in the continuum limit Ixx + Iyy = Izz exactly, and a real
    # plate clears it only by its own thickness squared (hazard 8).
    residual = principal[0] + principal[1] - principal[2]
    if residual < -1.0e-9 * largest:
        raise DynamicsError(
            f"{context} has an inertia tensor that violates the triangle "
            f"inequality by {abs(residual):.6g} kg·m² "
            f"({abs(residual) / largest:.3g} of its largest moment).",
            reason="inertia_triangle_violation",
            correction=(
                "No real rigid body has such a tensor, so the source geometry is "
                "degenerate: look for overlapping solids counted twice, or a "
                "solid with inverted orientation."
            ),
            observed={
                "context": context,
                "principal_kg_m2": principal,
                "residual_kg_m2": residual,
            },
        )
    return {
        "mass_kg": mass_kg(density, total_volume),
        "volume_mm3": total_volume,
        "density_kg_m3": density,
        "center_of_mass_mm": centre_of_mass,
        "inertia_kg_m2": tensor_kg_m2,
        "principal_inertia_kg_m2": principal,
        "solid_count": len(entries),
    }


def full_inertia_six(tensor: Sequence[float]) -> list[float]:
    """The nine-entry tensor as MuJoCo's ``fullinertia``.

    MJCF order is (Ixx, Iyy, Izz, Ixy, Ixz, Iyz) -- measured against the
    compiler rather than read off the documentation, because a transposed
    or reordered product-of-inertia term is a body that tumbles subtly
    wrong and nothing refuses it.
    """

    values = [float(item) for item in tensor]
    return [values[0], values[4], values[8], values[1], values[2], values[5]]


# ---------------------------------------------------------------------------
# Collision geometry, and the measurement that refuses it (M3 phase 1).
# ---------------------------------------------------------------------------

#: The chord tolerance a collision mesh is tessellated at when the script
#: does not say. Deliberately an **absolute length** and deliberately not
#: the display deflection: ``cadex_tessellation`` scales that one by the
#: bounding-box diagonal because it is chosen for looks, so a collision mesh
#: inheriting it would be a physics result that changes when the view does --
#: a part rendered at "draft" quality would collide differently from the same
#: part at "fine". A fixed length is only safe because the fidelity check
#: below refuses a mesh too coarse to be the part; without that check this
#: number would be a silent quality knob on the physics.
DEFAULT_COLLISION_DEFLECTION_MM = 0.25

#: How far the hull may exceed the mesh before the part is called concave.
#: Both volumes are computed from the *same vertices*, so for a genuinely
#: convex part they agree to floating-point noise and this is pure headroom
#: against Qhull merging near-coplanar facets. A real concavity -- a slot, a
#: pocket, a C-section -- is percent-scale, three or more orders of magnitude
#: above this.
COLLISION_CONVEXITY_TOLERANCE = 1.0e-4

#: How far the tessellation may fall short of the exact BREP volume. A
#: tessellated cylinder is an inscribed prism, so this is never zero for a
#: curved part, and it is the number that says whether the geom is still the
#: part: 5% of volume missing is a visibly faceted stand-in, and its contacts
#: would be wrong in a way that looks like physics.
COLLISION_TESSELLATION_TOLERANCE = 0.05

#: A bound on what one collision mesh may cost. MuJoCo hulls the mesh, and a
#: hull with a hundred thousand vertices is a collision cost nobody asked
#: for; the correction is a coarser deflection, which the refusal names.
MAXIMUM_COLLISION_VERTICES = 200_000

#: The contact spring's time constant, in seconds. It is MuJoCo's own
#: default written down rather than inherited, for the reason M3 phase 0
#: gave: a default is a promise, not a decision. Softer than this and a
#: resting part sinks visibly into what it rests on; stiffer and the
#: integrator needs a finer step to stay stable.
CONTACT_TIMECONST_S = 0.02

#: MuJoCo's own friction triple (sliding, torsional, rolling), again
#: written down. A script that gives one number replaces the sliding term
#: and keeps these two, because torsional and rolling friction are in
#: different units and guessing them from a sliding coefficient would be
#: inventing numbers.
DEFAULT_FRICTION = (1.0, 0.005, 0.0001)

#: The restitutions this translation can actually deliver, measured (M3
#: phase 2). MuJoCo has no restitution coefficient at all; bounce falls out
#: of the contact spring's damping ratio, and the map between them stops
#: being honest at both ends. Below 0.3 the discrete solver eats the bounce
#: -- a requested 0.15 measures 0.00 -- and above 0.9 the damping is so
#: light that the integrator *adds* energy, which is a ball that bounces
#: higher than it was dropped from. Both ends are refused rather than
#: quietly delivered wrong; 0 is exact and is the default.
MINIMUM_RESTITUTION = 0.3
MAXIMUM_RESTITUTION = 0.9

#: How finely the solver must step for a bouncy contact to come out at the
#: value that was asked for. Measured by round-tripping a requested
#: restitution through the damping ratio and back off a dropped ball: at
#: ten steps per time constant -- which is what 60 fps and the default
#: solver step give -- a requested 0.9 measures **3.45**, energy from
#: nowhere. At twenty the worst error over [0.3, 0.9] is 12%, and finer
#: buys almost nothing. So restitution above zero *requires* the finer
#: step, and asking for one without the other is refused.
RESTITUTION_STEPS_PER_TIMECONST = 20

#: MuJoCo's four contact dimensionalities: 1 is frictionless, 3 adds
#: sliding friction, 4 adds torsional, 6 adds rolling.
CONDIM_VALUES = (1, 3, 4, 6)

#: How many collision groups a script may name. MuJoCo's contype and
#: conaffinity are documented as 32-bit masks and are *signed* int32 in the
#: binding, measured: an all-ones 0xFFFFFFFF is refused by ``add_geom``
#: outright. So the top bit is unusable and the count is 31, not 32 -- a
#: number found by a compiler error rather than by reading, which is the
#: cheap end of the same lesson the flags taught.
CONTACT_GROUP_COUNT = 31

#: The five MuJoCo geom types this surface can produce, and how many size
#: numbers each takes. ``mesh`` and ``hull`` are the same MuJoCo type: they
#: differ only in whether a concave part is refused, which is a decision
#: this module makes before MuJoCo ever sees the geometry.
_COLLISION_GEOM_TYPES = {
    "box": "box",
    "sphere": "sphere",
    "cylinder": "cylinder",
    "capsule": "capsule",
    "mesh": "mesh",
    "hull": "mesh",
}
_COLLISION_FROM_SHAPE = ("mesh", "hull")


def _scipy_hull() -> Any:
    """The one import site for Qhull, with the payload failure named."""

    try:
        from scipy.spatial import ConvexHull  # noqa: PLC0415 - not module scope
    except ImportError as exc:  # pragma: no cover - a broken payload only
        raise DynamicsError(
            "This engine build cannot import scipy.spatial, so a collision "
            "mesh cannot be measured for convexity.",
            reason="scipy_unavailable",
            correction=(
                "scipy ships in the engine payload already (it is what the "
                "mesh domain fits surfaces with). Rebuild the payload with "
                "pixi run stage-engine."
            ),
        ) from exc
    return ConvexHull


def restitution_for_dampratio(dampratio: float) -> float:
    """The bounce a MuJoCo contact spring with this damping ratio delivers.

    MuJoCo has no restitution coefficient. A contact is a spring-damper
    whose ``solref`` is ``(timeconst, dampratio)``, so restitution is a
    *consequence* of the damping ratio and the translation between them is
    arithmetic -- which is why it lives here, in the module that does every
    unit conversion, and not at the seam where a second copy could drift.

    The textbook relation ``e = exp(−ζπ/√(1−ζ²))`` is the wrong one and was
    measured to be wrong: it assumes the mass stays in contact for a full
    half period, which a *bilateral* spring does. A contact is unilateral --
    it separates the instant the normal force would turn tensile, which is
    earlier. Solving ``kx + cẋ = 0`` for that instant gives

        ``ωd·t* = π − 2·arcsin ζ``      and      ``e = exp(−ζ(π − 2 arcsin ζ)/√(1−ζ²))``

    and the difference is not academic: at ζ = 0.5 the bilateral formula
    says 0.16 and this one says 0.29, against a measured 0.29.
    """

    ratio = float(dampratio)
    if ratio <= 0.0:
        return 1.0
    if ratio >= 1.0:
        # The formula's own limit. MuJoCo's discrete solver kills the bounce
        # entirely well before this, which is why MINIMUM_RESTITUTION exists.
        return math.exp(-2.0)
    return math.exp(
        -ratio * (math.pi - 2.0 * math.asin(ratio)) / math.sqrt(1.0 - ratio * ratio)
    )


def dampratio_for_restitution(restitution: float, *, context: str) -> float:
    """The damping ratio that delivers one restitution, by bisection.

    ``restitution_for_dampratio`` is transcendental and strictly decreasing
    on (0, 1), so the inverse is a bisection rather than a closed form.
    Fifty halvings put it well inside double precision, and the result is
    deterministic to the bit -- which matters, because it goes into a model
    whose trace digest is compared across processes.
    """

    target = float(restitution)
    if target <= 0.0:
        # Critical damping. Measured: a ball dropped on a critically damped
        # contact does not leave the surface at all.
        return 1.0
    if not MINIMUM_RESTITUTION <= target <= MAXIMUM_RESTITUTION:
        raise DynamicsError(
            f"{context} asks for a restitution of {target:g}, which this "
            "contact model cannot deliver.",
            reason="restitution_out_of_range",
            correction=(
                "MuJoCo has no restitution coefficient: bounce comes out of "
                "the contact spring's damping, and the map holds only between "
                f"{MINIMUM_RESTITUTION:g} and {MAXIMUM_RESTITUTION:g}. Below "
                "that the solver damps the bounce out entirely and above it "
                "the integrator adds energy. Use 0 for a contact that does "
                "not bounce."
            ),
            observed={"context": context, "restitution": target},
        )
    low, high = 0.0, 1.0
    for _step in range(50):
        middle = 0.5 * (low + high)
        if restitution_for_dampratio(middle) > target:
            low = middle
        else:
            high = middle
    return 0.5 * (low + high)


def contact_masks(
    group: int, collides_with: Sequence[int] | None, *, context: str
) -> tuple[int, int]:
    """One group and its partners, as MuJoCo's ``contype``/``conaffinity``.

    MuJoCo's rule is that two geoms may touch when
    ``contype₁ & conaffinity₂`` or ``contype₂ & conaffinity₁`` is non-zero,
    which is a bitmask protocol a CAD author has no reason to know. The
    script says which group a shape is in and which groups it collides
    with; the bits are made here.

    Note the ``or``: the relation MuJoCo checks is symmetric even when the
    declarations are not, so a shape in group 1 that collides with nothing
    can still be touched by a shape that collides with group 1. That is
    MuJoCo's semantics and it is recorded rather than papered over.
    """

    index = int(group)
    if not 0 <= index < CONTACT_GROUP_COUNT:
        raise DynamicsError(
            f"{context} is in collision group {index}, outside 0..{CONTACT_GROUP_COUNT - 1}.",
            reason="collision_group_out_of_range",
            observed={"context": context, "group": index},
        )
    if collides_with is None:
        affinity = (1 << CONTACT_GROUP_COUNT) - 1
    else:
        affinity = 0
        for other in collides_with:
            other_index = int(other)
            if not 0 <= other_index < CONTACT_GROUP_COUNT:
                raise DynamicsError(
                    f"{context} collides with group {other_index}, outside "
                    f"0..{CONTACT_GROUP_COUNT - 1}.",
                    reason="collision_group_out_of_range",
                    observed={"context": context, "group": other_index},
                )
            affinity |= 1 << other_index
    return 1 << index, affinity


def collision_deflection_mm(
    shapes: Sequence[Mapping[str, Any]], *, context: str
) -> float | None:
    """The chord tolerance the worker must tessellate at, or ``None``.

    The worker cannot tessellate without a number and cannot compute one
    without breaking the split rule, so the resolution happens here and the
    worker reads the answer. ``None`` means no shape needs the BREP at all,
    which is the case a body made of primitives must not pay for.
    """

    deflections = [
        shape.get("deflection_mm")
        for shape in shapes
        if str(shape.get("kind")) in _COLLISION_FROM_SHAPE
    ]
    if not deflections:
        return None
    if len(deflections) > 1:
        raise DynamicsError(
            f"{context} declares more than one mesh or hull collision shape.",
            reason="duplicate_collision_mesh",
            observed={"context": context, "count": len(deflections)},
        )
    declared = deflections[0]
    value = (
        DEFAULT_COLLISION_DEFLECTION_MM if declared is None else float(declared)
    )
    if not math.isfinite(value) or value <= 0.0:
        raise DynamicsError(
            f"{context} declares a collision deflection of {value:g} mm.",
            reason="malformed_deflection",
            observed={"context": context, "deflection_mm": declared},
        )
    return value


def mesh_volume_mm3(
    vertices_mm: Sequence[float], triangles: Sequence[int]
) -> float:
    """The volume a closed triangle mesh encloses, by the divergence theorem.

    ``V = ⅙ Σ v₀ · (v₁ × v₂)`` over outward-wound triangles.
    ``cadex_tessellation.tessellate_shape`` flips reversed faces so the
    winding is consistently outward, which is exactly the precondition this
    needs -- and a mesh that came out inside-out reports a *negative* volume,
    which is loud rather than subtly wrong.

    This is what the hull is compared against, and it is not the same
    question as comparing the hull to the exact BREP volume. A tessellated
    cylinder is an inscribed prism whose volume is short of the exact one by
    a chord-error term that has nothing to do with concavity: at the default
    deflection a 5 mm pin loses about 1.6% of its volume to faceting alone.
    Measuring hull-against-mesh isolates concavity, because both come from
    the same vertices; mesh-against-exact is a separate question with a
    separate tolerance, and conflating them would either refuse every
    cylinder or accept every shallow pocket.
    """

    total = 0.0
    terms: list[float] = []
    for index in range(0, len(triangles) - 2, 3):
        base = [3 * int(triangles[index + corner]) for corner in range(3)]
        a = [float(vertices_mm[base[0] + axis]) for axis in range(3)]
        b = [float(vertices_mm[base[1] + axis]) for axis in range(3)]
        c = [float(vertices_mm[base[2] + axis]) for axis in range(3)]
        cross = [
            b[1] * c[2] - b[2] * c[1],
            b[2] * c[0] - b[0] * c[2],
            b[0] * c[1] - b[1] * c[0],
        ]
        terms.append(sum(a[axis] * cross[axis] for axis in range(3)))
    total = math.fsum(terms)
    return total / 6.0


def convex_hull_volume_mm3(vertices_mm: Sequence[float], *, context: str) -> float:
    """The volume of the convex hull of a point set, via Qhull.

    This is the number MuJoCo's compiler will effectively use, because it
    hulls every collision mesh it is given and says nothing about it. Having
    it *here*, before the model is built, is what turns hazard 2 from a
    silent wrong answer into a refusal with a number in it.
    """

    ConvexHull = _scipy_hull()
    points = [
        [float(vertices_mm[index + axis]) for axis in range(3)]
        for index in range(0, len(vertices_mm) - 2, 3)
    ]
    if len(points) < 4:
        raise DynamicsError(
            f"{context} tessellated to {len(points)} vertices, which cannot "
            "bound a volume.",
            reason="degenerate_collision_mesh",
            correction=(
                "The component's solids did not produce a usable surface mesh. "
                "Check that the component is a solid rather than a shell."
            ),
            observed={"context": context, "vertex_count": len(points)},
        )
    try:
        hull = ConvexHull(points)
    except Exception as exc:
        raise DynamicsError(
            f"{context} has no three-dimensional convex hull: {exc}",
            reason="degenerate_collision_mesh",
            correction=(
                "Qhull refuses a point set that is flat or degenerate. A "
                "zero-thickness component cannot be a collision shape; give it "
                "an explicit primitive instead."
            ),
            observed={"context": context},
        ) from exc
    return float(hull.volume)


def collision_geoms(
    shapes: Sequence[Mapping[str, Any]],
    mesh: Mapping[str, Any] | None,
    *,
    exact_volume_mm3: float,
    context: str,
) -> list[dict[str, Any]]:
    """One body's collision shapes, in metres, measured and refused.

    Every conversion happens here and nowhere else: full extents become
    MuJoCo half-extents, millimetres become metres, and the xyzw quaternion
    the script surface speaks becomes the wxyz one MuJoCo does. The worker
    hands over millimetres and a tessellation; it computes nothing.

    Returns a list of geom records, each carrying the evidence for itself --
    for a mesh, the three volumes that decided whether it was allowed.
    """

    records: list[dict[str, Any]] = []
    for index, shape in enumerate(shapes):
        kind = str(shape.get("kind"))
        if kind not in _COLLISION_GEOM_TYPES:
            raise DynamicsError(
                f"{context} declares an unknown collision kind {kind!r}.",
                reason="unknown_collision_kind",
                observed={"context": context, "kind": kind},
            )
        offset = shape.get("offset") or {}
        position = _floats(
            offset.get("position", [0.0, 0.0, 0.0]),
            count=3,
            context=f"{context} collision {index} offset position",
        )
        rotation = _floats(
            offset.get("rotation", [0.0, 0.0, 0.0, 1.0]),
            count=4,
            context=f"{context} collision {index} offset rotation",
        )
        record: dict[str, Any] = {
            "index": index,
            "kind": kind,
            "mujoco_type": _COLLISION_GEOM_TYPES[kind],
            "pos_m": vector_m(position),
            "quat_wxyz": quaternion_normalised(
                quaternion_wxyz_from_xyzw(rotation)
            ),
            **_contact_parameters(
                shape, context=f"{context} collision {index}"
            ),
        }
        if kind == "box":
            extents = _floats(
                shape["size_mm"], count=3, context=f"{context} collision {index} size"
            )
            # MuJoCo boxes are half-extents. A script that said 20 mm and got
            # a 40 mm box would be a factor of two nobody notices until two
            # parts overlap, so the halving is here with the unit conversion
            # rather than anywhere a second copy could drift from it.
            record["size_m"] = [length_m(value) / 2.0 for value in extents]
            record["size_mm"] = extents
        elif kind == "sphere":
            radius = float(shape["radius_mm"])
            record["size_m"] = [length_m(radius)]
            record["size_mm"] = [radius]
        elif kind in {"cylinder", "capsule"}:
            radius = float(shape["radius_mm"])
            length = float(shape["length_mm"])
            # Same halving, and for a capsule the half-length is of the
            # *cylindrical section*: the two hemispherical caps sit outside
            # it, so a capsule is always ``length + 2·radius`` long overall.
            record["size_m"] = [length_m(radius), length_m(length) / 2.0]
            record["size_mm"] = [radius, length]
        else:
            if mesh is None:
                raise DynamicsError(
                    f"{context} declares a {kind} collision shape but no "
                    "tessellation was supplied for it.",
                    reason="missing_collision_mesh",
                    observed={"context": context},
                )
            record.update(
                _measured_collision_mesh(
                    mesh,
                    accept_hull=kind == "hull",
                    exact_volume_mm3=exact_volume_mm3,
                    context=context,
                )
            )
        records.append(record)
    return records


def _contact_parameters(
    shape: Mapping[str, Any], *, context: str
) -> dict[str, Any]:
    """What one collision shape does when it touches something.

    Everything MuJoCo needs, translated once: friction as a triple, bounce
    as a ``solref``, the group pair as bitmasks, margin in metres. The
    script surface speaks millimetres and coefficients; the geom speaks
    metres and packed vectors, and this is the only place the two meet.

    **What MuJoCo does with two geoms' worth of these, measured**, because
    every one of them is a property of a *pair* and none of these numbers
    is used on its own:

    * friction is the elementwise **maximum**, so the rougher surface wins;
    * ``condim`` is the maximum, so the richer contact model wins;
    * ``margin`` is the **sum**, which is not what the documentation's
      "max" led us to expect -- two geoms at 20 mm and 30 mm produce a
      50 mm margin, measured;
    * ``solref`` is the **average**, so a bouncy ball on a dead floor
      bounces half as much as it asked to. That one is worth knowing: a
      restitution declared on one side of a contact is not the restitution
      the contact has.
    """

    friction = shape.get("friction")
    if friction is None:
        triple = list(DEFAULT_FRICTION)
    elif isinstance(friction, (int, float)) and not isinstance(friction, bool):
        # One number replaces sliding friction only. Torsional and rolling
        # friction are in different units (length and length² respectively),
        # so deriving them from a sliding coefficient would be invention.
        triple = [float(friction), DEFAULT_FRICTION[1], DEFAULT_FRICTION[2]]
    else:
        triple = _floats(friction, count=3, context=f"{context} friction")
    for position, value in enumerate(triple):
        if value < 0.0:
            raise DynamicsError(
                f"{context} has a negative friction coefficient {value:g}.",
                reason="negative_friction",
                observed={"context": context, "friction": triple, "index": position},
            )

    restitution = float(shape.get("restitution") or 0.0)
    dampratio = dampratio_for_restitution(restitution, context=context)

    condim = shape.get("condim")
    condim_value = 3 if condim is None else int(condim)
    if condim_value not in CONDIM_VALUES:
        raise DynamicsError(
            f"{context} asks for condim {condim_value}, which is not one of "
            f"{list(CONDIM_VALUES)}.",
            reason="unknown_condim",
            observed={"context": context, "condim": condim_value},
        )
    if condim_value == 1 and friction is not None:
        # A condim-1 contact is frictionless by definition, so MuJoCo
        # ignores the friction vector entirely. Declaring both is a script
        # that does not do what it says, and ignoring it quietly is exactly
        # the failure this slice is organised against.
        raise DynamicsError(
            f"{context} declares friction on a frictionless contact "
            "(condim=1), where MuJoCo ignores it.",
            reason="friction_on_frictionless_contact",
            correction=(
                "Either raise condim to 3 so the friction is used, or drop "
                "the friction argument to say the contact really is "
                "frictionless."
            ),
            observed={"context": context, "condim": condim_value},
        )

    margin_mm = float(shape.get("margin_mm") or 0.0)
    if margin_mm < 0.0:
        raise DynamicsError(
            f"{context} has a negative contact margin of {margin_mm:g} mm.",
            reason="negative_margin",
            observed={"context": context, "margin_mm": margin_mm},
        )
    contype, conaffinity = contact_masks(
        int(shape.get("contact_group") or 0),
        shape.get("collides_with"),
        context=context,
    )
    return {
        "friction": triple,
        "restitution": restitution,
        "solref": [CONTACT_TIMECONST_S, dampratio],
        "dampratio": dampratio,
        "condim": condim_value,
        "margin_m": length_m(margin_mm),
        "margin_mm": margin_mm,
        "contact_group": int(shape.get("contact_group") or 0),
        "collides_with": (
            None
            if shape.get("collides_with") is None
            else [int(value) for value in shape["collides_with"]]
        ),
        "contype": contype,
        "conaffinity": conaffinity,
    }


def _measured_collision_mesh(
    mesh: Mapping[str, Any],
    *,
    accept_hull: bool,
    exact_volume_mm3: float,
    context: str,
) -> dict[str, Any]:
    """One tessellation, measured twice, and refused for either reason.

    **Concavity.** MuJoCo takes the convex hull of a collision mesh without
    complaint, so a bracket with a slot becomes a solid block and the
    resulting contacts look entirely plausible. The hull volume is computed
    here, against the mesh's own volume, and a part the hull would change is
    refused with the error in it -- the same move M2 made when it refused
    ``rack_pinion`` rather than shipping a guessed sign convention. ``hull``
    is the opt-in that turns this refusal into an accepted fact.

    **Fidelity.** The mesh is also compared against the component's exact
    ``GProp_GProps`` volume, which is the check that says whether this is
    still the part. It is not a convexity question and it is not turned off
    by the ``hull`` opt-in: an author who accepts the hull of their bracket
    has not thereby accepted a twelve-sided cylinder.
    """

    vertices = list(mesh["vertices_mm"])
    triangles = list(mesh["triangles"])
    vertex_count = len(vertices) // 3
    if vertex_count > MAXIMUM_COLLISION_VERTICES:
        raise DynamicsError(
            f"{context} tessellated to {vertex_count} collision vertices; the "
            f"accepted maximum is {MAXIMUM_COLLISION_VERTICES}.",
            reason="collision_mesh_too_large",
            correction=(
                "Raise deflection_mm on the collision shape, or replace it with "
                "explicit primitives -- a bracket's real collision behaviour is "
                "usually two boxes."
            ),
            observed={"context": context, "vertex_count": vertex_count},
        )
    volume = mesh_volume_mm3(vertices, triangles)
    if volume <= 0.0:
        raise DynamicsError(
            f"{context} tessellated to a mesh enclosing {volume:.6g} mm³.",
            reason="degenerate_collision_mesh",
            correction=(
                "A negative or zero enclosed volume means the triangle winding "
                "is inverted or the surface is not closed. Check the source "
                "solid."
            ),
            observed={"context": context, "mesh_volume_mm3": volume},
        )
    hull_volume = convex_hull_volume_mm3(vertices, context=context)
    concavity = (hull_volume - volume) / hull_volume if hull_volume > 0.0 else 0.0
    fidelity = (
        abs(exact_volume_mm3 - volume) / exact_volume_mm3
        if exact_volume_mm3 > 0.0
        else 0.0
    )
    if fidelity > COLLISION_TESSELLATION_TOLERANCE:
        raise DynamicsError(
            f"{context}'s collision mesh encloses {volume:.6g} mm³ where the "
            f"solid is {exact_volume_mm3:.6g} mm³ -- {fidelity:.2%} of the "
            "part is missing to faceting.",
            reason="collision_mesh_too_coarse",
            correction=(
                "The mesh is too coarse to be this part, so its contacts would "
                "be wrong in a way that looks like physics. Lower deflection_mm "
                f"on the collision shape (it is {float(mesh['deflection_mm']):g} "
                "mm), or declare an explicit primitive instead."
            ),
            observed={
                "context": context,
                "mesh_volume_mm3": volume,
                "solid_volume_mm3": exact_volume_mm3,
                "volume_error": fidelity,
                "deflection_mm": float(mesh["deflection_mm"]),
            },
        )
    if concavity > COLLISION_CONVEXITY_TOLERANCE and not accept_hull:
        raise DynamicsError(
            f"{context} is concave: its convex hull encloses "
            f"{hull_volume:.6g} mm³ against the part's {volume:.6g} mm³, so "
            f"{concavity:.2%} of what it would collide with is not part of it.",
            reason="collision_mesh_concave",
            correction=(
                "MuJoCo takes the convex hull of every collision mesh without "
                "saying so, so this part would touch things across its own "
                "openings. Either describe the collision behaviour with "
                "explicit primitives -- assembly.collision('box', ...) and "
                "friends, which is usually what a bracket really needs -- or "
                "declare assembly.collision('hull') to record that you have "
                "read this number and accept the solid block."
            ),
            observed={
                "context": context,
                "mesh_volume_mm3": volume,
                "hull_volume_mm3": hull_volume,
                "solid_volume_mm3": exact_volume_mm3,
                "concavity": concavity,
            },
        )
    return {
        "vertices_m": [length_m(float(value)) for value in vertices],
        "triangles": [int(value) for value in triangles],
        "vertex_count": vertex_count,
        "triangle_count": len(triangles) // 3,
        "deflection_mm": float(mesh["deflection_mm"]),
        "mesh_volume_mm3": volume,
        "hull_volume_mm3": hull_volume,
        "solid_volume_mm3": float(exact_volume_mm3),
        "concavity": concavity,
        "volume_error": fidelity,
        "accepted_hull": bool(accept_hull),
    }


# ---------------------------------------------------------------------------
# The joint table, and the spanning forest.
# ---------------------------------------------------------------------------

#: How each of FreeCAD's thirteen joint types reaches MuJoCo's four.
#:
#: ``tree`` is the MuJoCo joint chain a tree edge builds, in the order the
#: joints are added to the child body. ``closure`` is the equality
#: constraint a *non-tree* edge becomes, or ``None`` when M2 refuses to
#: close that kind. ``coupling`` marks the joints that are never tree edges
#: at all: a gear pair is a polynomial relation between two hinges that
#: other joints provide, not a body attachment.
JOINT_TABLE: dict[str, dict[str, Any]] = {
    "fixed": {"tree": (), "closure": "weld", "coupling": False},
    "revolute": {"tree": ("hinge",), "closure": "connect", "coupling": False},
    "slider": {"tree": ("slide",), "closure": None, "coupling": False},
    "ball": {"tree": ("ball",), "closure": "connect", "coupling": False},
    "cylindrical": {"tree": ("slide", "hinge"), "closure": None, "coupling": False},
    # All four coupled kinds attach nothing. FreeCAD says so itself:
    # AssemblyObject::isJointTypeConnecting returns false for exactly these
    # four, so its own solver will not use them to locate a part. A screw
    # constrains the relative twist between two components that a slider and
    # a revolute have already placed; docs/MUJOCO.md M2's "a hinge plus a
    # coupling" had it one joint too generous.
    "screw": {"tree": None, "closure": None, "coupling": True},
    "rack_pinion": {"tree": None, "closure": None, "coupling": True},
    "gears": {"tree": None, "closure": None, "coupling": True},
    "belt": {"tree": None, "closure": None, "coupling": True},
    "distance": {"tree": None, "closure": None, "coupling": False},
    "parallel": {"tree": None, "closure": None, "coupling": False},
    "perpendicular": {"tree": None, "closure": None, "coupling": False},
    "angle": {"tree": None, "closure": None, "coupling": False},
}

#: The four with no runtime meaning at all. They are *placement*
#: constraints: they told the solver where to put a part once, and a
#: dynamics model has no use for them afterwards. Refused with a sentence
#: naming the joint rather than dropped, because dropping one leaves a
#: mechanism with a degree of freedom the author does not know it has.
_PLACEMENT_ONLY = ("distance", "parallel", "perpendicular", "angle")

#: What each closure actually constrains, and what it lets go. A ``connect``
#: pins one point and nothing else, which is exactly right for a planar
#: four-bar and under-constrained for a spatial one -- so it is recorded in
#: the published evidence rather than hidden.
_CLOSURE_EVIDENCE = {
    "weld": {
        "constrained_dof": 6,
        "note": "A weld closure pins position and orientation; nothing is lost.",
    },
    "connect": {
        "constrained_dof": 3,
        "note": (
            "A connect closure pins the shared connector point only. Axis "
            "alignment is not constrained, which is exact for a planar loop "
            "and one constraint short for a spatial one."
        ),
    },
}


def _connector_frames(
    joint: Mapping[str, Any], *, index: int
) -> list[tuple[str, list[float]]]:
    connectors = list(joint.get("connectors") or [])
    name = str(joint.get("name") or f"joint {index}")
    if len(connectors) != 2:
        raise DynamicsError(
            f"Joint {name!r} does not have exactly two connectors.",
            reason="malformed_graph",
            observed={"joint": name, "connector_count": len(connectors)},
        )
    return [
        (
            str(connector.get("component") or ""),
            checked_rigid_matrix(
                connector.get("local_matrix"),
                context=f"joint {name!r} connector {position} frame",
            ),
        )
        for position, connector in enumerate(connectors, start=1)
    ]


def classify_joints(joints: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Every joint, resolved to its MuJoCo meaning, in script order.

    Classification happens before any traversal so a refusal can name the
    script rather than a half-built tree: an author who wrote
    ``api.joint('angle', ...)`` wants to be told that sentence, not told
    that component 4 is unreachable.
    """

    classified: list[dict[str, Any]] = []
    for index, joint in enumerate(joints):
        name = str(joint.get("name") or f"joint {index}")
        kind = str(joint.get("kind") or "")
        entry = JOINT_TABLE.get(kind)
        if entry is None:
            raise DynamicsError(
                f"Joint {name!r} has unknown type {kind!r}.",
                reason="unknown_joint_type",
                observed={"joint": name, "kind": kind},
            )
        suppressed = bool(joint.get("suppressed"))
        if not suppressed and kind in _PLACEMENT_ONLY:
            raise DynamicsError(
                f"Joint {name!r} is a {kind} joint, which has no dynamics "
                "meaning: it constrains where the solver puts a part, not how "
                "the mechanism moves.",
                reason="placement_only_joint",
                correction=(
                    f"Remove {name!r} from the assembly passed to "
                    "assembly.dynamics, or replace it with the joint that "
                    "describes the real connection -- a revolute, slider, ball, "
                    "cylindrical or fixed joint. Its solved placement is already "
                    "carried into the dynamics model as the starting pose."
                ),
                observed={"joint": name, "kind": kind},
            )
        connectors = _connector_frames(joint, index=index)
        if connectors[0][0] == connectors[1][0]:
            raise DynamicsError(
                f"Joint {name!r} connects component {connectors[0][0]!r} to "
                "itself.",
                reason="malformed_graph",
                observed={"joint": name, "component": connectors[0][0]},
            )
        classified.append(
            {
                "name": name,
                "index": index,
                "kind": kind,
                # A suppressed joint is not an edge at all: FreeCAD's solver
                # ignored it, so the solved pose it would have produced is
                # not the pose the model starts from.
                "suppressed": suppressed,
                "tree": entry["tree"],
                "closure": entry["closure"],
                "coupling": bool(entry["coupling"]),
                "components": [connectors[0][0], connectors[1][0]],
                "local_matrices": [connectors[0][1], connectors[1][1]],
                "parameters": dict(joint.get("parameters") or {}),
                "length_limits_mm": joint.get("length_limits_mm"),
                "angle_limits_degrees": joint.get("angle_limits_degrees"),
            }
        )
    return classified


def _closure_refusal(
    joint: Mapping[str, Any], bodies: Mapping[str, Mapping[str, Any]]
) -> DynamicsError:
    """Why this joint could not close the loop, and what would change it.

    The advice has to be specific to be worth printing, so it names the
    joints that *did* reach both of this one's components. The spanning tree
    is grown breadth-first from the grounded components, which means a joint
    becomes a tree edge when it is the shortest way to one of its
    components; two components already reached more directly leave it
    nothing to attach.
    """

    kind = str(joint["kind"])
    name = str(joint["name"])
    first, second = joint["components"]
    reached_by = {
        component: (
            repr(str(bodies[component]["joint"]))
            if bodies[component].get("joint")
            else f"its {bodies[component]['attachment']} attachment to the world"
        )
        for component in (first, second)
    }
    return DynamicsError(
        f"Joint {name!r} closes a loop and is a {kind} joint, which M2 cannot "
        "express as an equality constraint: a sliding closure needs a tendon, "
        "which is real design work and belongs to a later slice.",
        reason="unclosable_loop_joint",
        correction=(
            f"The spanning tree already reaches {first!r} through "
            f"{reached_by[first]} and {second!r} through {reached_by[second]}, "
            f"so {name!r} has no body left to attach. Make it the way one of "
            "them is reached: ground a different component, remove the more "
            "direct joint, or -- when two joints connect the same pair of "
            f"components -- list {name!r} first, because the tree takes the "
            "earlier joint and closes the later one."
        ),
        observed={
            "joint": name,
            "kind": kind,
            "components": [first, second],
            "reached_by": [
                str(bodies[first].get("joint") or ""),
                str(bodies[second].get("joint") or ""),
            ],
        },
    )


def extract_tree(
    components: Sequence[Mapping[str, Any]],
    joints: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """A MuJoCo kinematic tree plus its loop closures, from a constraint graph.

    Our assembly graph is a constraint graph and may contain loops; MuJoCo
    is a tree plus equality constraints. The spanning forest is grown
    breadth-first from the grounded components, because tree *depth* is
    what costs: it is the chain over which pose error accumulates and the
    chain the solver walks every step.

    Every ordering is total and explicit -- components in script order,
    joints in script order, the frontier keyed ``(depth, joint index,
    component index)``. ``component_outputs`` and ``joint_outputs`` upstream
    are ``id()``-keyed dicts whose keys vary per run, so nothing here may
    iterate a set or hash an object.
    """

    ordered = [str(component.get("name") or "") for component in components]
    if len(set(ordered)) != len(ordered) or not all(ordered):
        raise DynamicsError(
            "Assembly components must have unique non-empty names.",
            reason="malformed_graph",
            observed={"components": ordered},
        )
    positions = {name: index for index, name in enumerate(ordered)}
    grounded = [
        str(component["name"])
        for component in components
        if bool(component.get("grounded"))
    ]
    if not grounded:
        raise DynamicsError(
            "This assembly has no grounded component, so a dynamics model has "
            "no reference frame and every part would fall together.",
            reason="no_grounded_component",
            correction=(
                "Ground the fixed base with api.component(..., grounded=True) "
                "and reuse that variable throughout the graph."
            ),
            observed={"component_count": len(ordered)},
        )
    for component in components:
        if bool(component.get("flexible")):
            raise DynamicsError(
                f"Component {component.get('name')!r} is a flexible "
                "subassembly, and M2 builds exactly one rigid body per "
                "component.",
                reason="flexible_component",
                correction=(
                    "Set flexible=False. A flexible subassembly expands into "
                    "many bodies with internal joints, which the dynamics "
                    "translator does not walk yet."
                ),
                observed={"component": str(component.get("name") or "")},
            )

    classified = classify_joints(joints)
    for joint in classified:
        for name in joint["components"]:
            if name not in positions:
                raise DynamicsError(
                    f"Joint {joint['name']!r} references component {name!r}, "
                    "which is not part of this assembly.",
                    reason="malformed_graph",
                    observed={"joint": joint["name"], "component": name},
                )

    #: Adjacency in joint order: only joints that can attach a body.
    adjacency: dict[str, list[int]] = {name: [] for name in ordered}
    for joint in classified:
        if joint["suppressed"] or joint["tree"] is None:
            continue
        first, second = joint["components"]
        adjacency[first].append(joint["index"])
        adjacency[second].append(joint["index"])
    by_index = {joint["index"]: joint for joint in classified}

    def _other_index(joint_index: int, component: str) -> int:
        first, second = by_index[joint_index]["components"]
        return positions[second if first == component else first]

    bodies: list[dict[str, Any]] = []
    attached: dict[str, int] = {}
    used_joints: set[int] = set()

    def _attach(
        name: str,
        *,
        parent: str | None,
        joint: Mapping[str, Any] | None,
        attachment: str,
        depth: int,
    ) -> None:
        record: dict[str, Any] = {
            "name": name,
            "parent": parent,
            "depth": depth,
            "attachment": attachment,
            "joint": None if joint is None else str(joint["name"]),
            "joint_kind": None if joint is None else str(joint["kind"]),
            "mujoco_joints": (
                ["free"]
                if attachment == "free"
                else ([] if joint is None else list(joint["tree"]))
            ),
            "parent_local_matrix": None,
            "child_local_matrix": None,
        }
        if joint is not None:
            first, second = joint["components"]
            parent_side = 0 if first == parent else 1
            record["parent_local_matrix"] = joint["local_matrices"][parent_side]
            record["child_local_matrix"] = joint["local_matrices"][1 - parent_side]
        attached[name] = len(bodies)
        bodies.append(record)

    def _expand(root: str) -> None:
        # (depth, joint index, component index, parent): a total order, so
        # the same graph produces the same tree on every run, and depth
        # first so the traversal stays breadth-first.
        frontier = sorted(
            (1, joint_index, _other_index(joint_index, root), root)
            for joint_index in sorted(adjacency[root])
        )
        while frontier:
            depth, joint_index, component_index, parent = frontier.pop(0)
            child = ordered[component_index]
            if child in attached:
                continue
            used_joints.add(joint_index)
            _attach(
                child,
                parent=parent,
                joint=by_index[joint_index],
                attachment="tree",
                depth=depth,
            )
            for next_joint in sorted(adjacency[child]):
                next_component = _other_index(next_joint, child)
                if ordered[next_component] in attached:
                    continue
                frontier.append((depth + 1, next_joint, next_component, child))
            frontier.sort()

    # Every grounded component is a static root *before* any traversal
    # starts. A grounded component may not become another body's child: it
    # is fixed to the world, and hanging it off a moving parent would give
    # it degrees of freedom FreeCAD's solver says it does not have. A joint
    # between two grounded components therefore reaches neither the tree nor
    # the closures -- it is already satisfied, permanently.
    for name in ordered:
        if name in grounded:
            _attach(name, parent=None, joint=None, attachment="grounded", depth=0)
    for name in grounded:
        _expand(name)
    for name in ordered:
        if name not in attached:
            # An island the joints never reach from ground. Its first
            # component in script order gets a free joint and falls; the rest
            # of the island hangs off it as an ordinary subtree.
            _attach(name, parent=None, joint=None, attachment="free", depth=0)
            _expand(name)

    closures: list[dict[str, Any]] = []
    couplings: list[dict[str, Any]] = []
    static_joints: list[dict[str, Any]] = []
    grounded_names = frozenset(grounded)
    for joint in classified:
        if joint["suppressed"]:
            continue
        if joint["coupling"]:
            couplings.append(joint)
        if joint["tree"] is None or joint["index"] in used_joints:
            continue
        first_component, second_component = joint["components"]
        if (
            first_component in grounded_names
            and second_component in grounded_names
        ):
            static_joints.append(
                {
                    "joint": joint["name"],
                    "kind": joint["kind"],
                    "components": [first_component, second_component],
                    "note": (
                        "Both components are grounded, so this joint is "
                        "satisfied by the solved placements and needs no "
                        "constraint in the dynamics model."
                    ),
                }
            )
            continue
        closure = joint["closure"]
        if closure is None:
            raise _closure_refusal(
                joint, {body["name"]: body for body in bodies}
            )
        evidence = _CLOSURE_EVIDENCE[closure]
        first, second = joint["components"]
        closures.append(
            {
                "joint": joint["name"],
                "kind": joint["kind"],
                "closure_kind": closure,
                "constrained_dof": evidence["constrained_dof"],
                "note": evidence["note"],
                "components": [first, second],
                "local_matrices": [
                    joint["local_matrices"][0],
                    joint["local_matrices"][1],
                ],
            }
        )
    return {
        "bodies": bodies,
        "closures": closures,
        "couplings": couplings,
        "static_joints": static_joints,
        "classified_joints": classified,
        "grounded": grounded,
        "tree_joint_count": len(used_joints),
        "maximum_depth": max((body["depth"] for body in bodies), default=0),
    }


# ---------------------------------------------------------------------------
# Joint coordinates, derived from the solved placements by inversion.
# ---------------------------------------------------------------------------


def joint_transform(
    parent_world: Sequence[float],
    parent_local: Sequence[float],
    child_world: Sequence[float],
    child_local: Sequence[float],
) -> list[float]:
    """The motion one joint has undergone, in its own connector frame.

    ``inv(L_p) ∘ inv(T_wp) ∘ T_wc ∘ L_c``. Every term is either a *solved*
    component placement or a component-local connector frame -- never
    ``global_frame``, which ``setJointConnectors`` records *before*
    ``assembly.solve`` runs and which therefore depends on the order the
    joints appear in the script (hazard 1). Composing the component-local
    frame with the solved placement is rigid-body invariant and cannot
    disagree with the pose the trace starts from.
    """

    return matrix_multiply(
        matrix_inverse(parent_local),
        matrix_multiply(
            matrix_inverse(parent_world),
            matrix_multiply(child_world, child_local),
        ),
    )


def joint_coordinates(
    kind: str, transform: Sequence[float], *, context: str
) -> dict[str, Any]:
    """One joint's coordinates, plus the residual its kind cannot express.

    The residual is the cheapest possible detector for a frame-composition,
    unit or handedness error, and it needs no MuJoCo at all: a revolute
    joint's connector frames must differ by a pure rotation about their
    shared +Z, so anything else in the transform is a mistake made
    somewhere upstream. The caller decides what to do with it -- the tree
    build refuses, the closure gate reports.
    """

    rotation = matrix_rotation(transform)
    translation = matrix_translation_mm(transform)
    quaternion = quaternion_wxyz_from_matrix(transform)
    # The rotation about +Z, and how much of the rotation is not about +Z.
    about_z = math.atan2(rotation[3], rotation[0])
    residual_rotation = rotation_angle_between(
        quaternion, quaternion_from_axis_angle_wxyz((0.0, 0.0, 1.0), about_z)
    )
    off_axis_mm = math.sqrt(translation[0] ** 2 + translation[1] ** 2)
    along_axis_mm = translation[2]
    if kind in {"revolute", "screw", "rack_pinion"}:
        values = [about_z]
        residual_mm = math.sqrt(off_axis_mm**2 + along_axis_mm**2)
        residual_radians = residual_rotation
    elif kind == "slider":
        values = [length_m(along_axis_mm)]
        residual_mm = off_axis_mm
        residual_radians = rotation_angle_between(quaternion, [1.0, 0.0, 0.0, 0.0])
    elif kind == "cylindrical":
        values = [length_m(along_axis_mm), about_z]
        residual_mm = off_axis_mm
        residual_radians = residual_rotation
    elif kind == "ball":
        values = list(quaternion)
        residual_mm = math.sqrt(sum(item * item for item in translation))
        residual_radians = 0.0
    elif kind == "fixed":
        values = []
        residual_mm = math.sqrt(sum(item * item for item in translation))
        residual_radians = rotation_angle_between(quaternion, [1.0, 0.0, 0.0, 0.0])
    else:
        raise DynamicsError(
            f"{context} has no joint coordinate for kind {kind!r}.",
            reason="unknown_joint_type",
            observed={"context": context, "kind": kind},
        )
    return {
        "kind": kind,
        "values": values,
        "residual_mm": residual_mm,
        "residual_radians": residual_radians,
    }


#: How far a solved joint may sit from the pose its kind describes before
#: the model is refused. FreeCAD's own solver converges to ~1e-6 mm, and a
#: frame composed the wrong way is out by millimetres or by whole degrees --
#: there is nothing in between, so the threshold is not delicate.
CLOSURE_RESIDUAL_MM = 1.0e-4
CLOSURE_RESIDUAL_RADIANS = 1.0e-6

#: How far a loop closure may be violated at the solved pose, in metres and
#: radians -- ``efc_pos`` mixes both, and a micrometre and a microradian are
#: each far below anything a real error produces. A closure that starts
#: violated is a pre-stressed model: the solver pulls the mechanism into
#: shape on the first step and the animation opens with a snap.
CLOSURE_EQUALITY_TOLERANCE = 1.0e-6


def closure_residuals(
    components: Sequence[Mapping[str, Any]],
    joints: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Every live joint's residual against the pose its kind demands.

    Cheap, exact, and available before a single line of MuJoCo runs. If the
    solved placements and the connector frames are composed correctly, each
    joint's two JCS coincide up to that joint's own freedom; if a frame was
    inverted, a unit was missed or a handedness flipped, this is where it
    shows -- in millimetres, against the joint that caused it.
    """

    placements = {
        str(component["name"]): checked_rigid_matrix(
            component["solved_matrix"],
            context=f"component {component.get('name')!r} solved placement",
        )
        for component in components
    }
    results: list[dict[str, Any]] = []
    for joint in classify_joints(joints):
        if joint["suppressed"] or joint["kind"] in _PLACEMENT_ONLY:
            continue
        first, second = joint["components"]
        transform = joint_transform(
            placements[first],
            joint["local_matrices"][0],
            placements[second],
            joint["local_matrices"][1],
        )
        kind = joint["kind"]
        if kind in {"gears", "belt"}:
            # A gear pair constrains rates, not poses: there is no residual
            # to take, and pretending otherwise would refuse working models.
            continue
        results.append(
            {"joint": joint["name"], **joint_coordinates(kind, transform, context=f"joint {joint['name']!r}")}
        )
    return results


# ---------------------------------------------------------------------------
# The model. This is where mujoco is imported, and nowhere else.
# ---------------------------------------------------------------------------

#: Constraint impedance for every equality this module writes -- loop
#: closures and couplings alike. MuJoCo's default (0.9, 0.95) leaves a
#: constraint that yields under load, and a screw is where that shows: a
#: heavy nut on a fine thread has to be held by a shaft with almost no
#: inertia, and at the default the coupling was overwhelmed completely --
#: 610 mm of travel where the pitch allows 105, with an 893 mm residual.
#: At (0.99, 0.9999) the same run tracks its pitch to 0.8% with a 1.2 mm
#: residual, which is a real screw's elasticity rather than a broken model.
_EQUALITY_SOLIMP = (0.99, 0.9999, 0.0001, 0.5, 2.0)

#: What a one-sided limit becomes. MuJoCo's ``range`` needs both ends, so
#: the open side is pushed out to somewhere the mechanism cannot reach: a
#: hundred turns, or a kilometre. Recorded per joint in the evidence rather
#: than quietly substituted -- a limit the model never meets is still a
#: number somebody may later wonder about.
_OPEN_ANGLE_MARGIN_RADIANS = 100.0 * 2.0 * math.pi
_OPEN_LENGTH_MARGIN_M = 1000.0

#: The default solver step, and since M3 phase 3 the *default* rather than
#: the only one: ``api.dynamics`` takes ``solver_step_s``. It stays 0.002
#: because that is what every M2 measurement was made at, and because the
#: cases that need finer -- a bouncing contact, chiefly -- now say so and
#: are refused when they do not get it.
DEFAULT_TIME_STEP_S = 0.002

#: How many solver steps one trace frame may cost. The frame budget bounds
#: how many frames a run produces; this bounds what each one is worth, and
#: without it ``solver_step_s`` is an unbounded cost rather than a slow one.
#: 2000 steps at 60 fps is a 8.3 microsecond step, three orders finer than
#: anything the contact model needs.
MAXIMUM_STEPS_PER_SAMPLE = 2000

#: The whole run's solver work (M3 phase 4). **Two budgets, because there
#: are two costs and they are not proportional to each other.**
#:
#: ``api.dynamics`` caps *frames* and *component poses* -- 10 000 and
#: 100 000, sized for kinematics and kept. Those count what leaves the
#: engine: bytes in the artifact, keyframes the shell bakes, memory in
#: Blender. This one counts what the engine *does*, which since
#: ``solver_step_s`` became authorable is a completely different number:
#: the same 600-frame trace costs 4 800 steps at the default step and
#: 1 200 000 at the finest one the per-frame cap allows.
#:
#: Naming them separately is the answer to docs/MUJOCO.md §6's remaining
#: open question -- what the cap should count once an M7-scale rollout
#: exists. A policy rollout is long in *steps* and short in frames: it
#: wants to integrate for minutes and report a hundred poses. Under one
#: combined cap that trade is impossible; under two it is exactly what the
#: numbers describe. Two million steps is about forty seconds of solver
#: time on a mechanism-sized model, which is long for a script and finite,
#: and it is two orders above anything M3 itself needs.
MAXIMUM_SOLVER_STEPS = 2_000_000

#: How stiff a position actuator may be at a given solver step, as the
#: dimensionless ``ω·h`` -- the joint's natural frequency under the gain,
#: times the step. Measured (M4 phase 0), and it is exactly the textbook
#: explicit-integration limit: ``implicitfast`` integrates *damping*
#: implicitly and stiffness explicitly, so a position actuator's spring term
#: inherits ``ω·h < 2`` and an undamped one was measured to diverge at
#: 2.02 at four different steps and across a 400x range of inertia.
#:
#: It is the *undamped* boundary on purpose. Actuator damping buys real
#: headroom -- ζ = 1 survives to 5.09 -- but a model whose stability rests
#: on a damping number the author chose for how the motion looks is a model
#: that breaks when somebody smooths it, and nothing would say why. The
#: refusal names the finer step instead, which is the same shape as M3's
#: restitution refusal and for the same reason.
MAXIMUM_ACTUATOR_OMEGA_STEP = 2.0

#: How much damping one joint coordinate may carry, as damping divided by
#: that coordinate's own inertia -- a rate, in reciprocal seconds. This is
#: the *other* failure a gain can produce and it is the worse one, because
#: it is silent: past ``c / M ≈ 1.2e10`` a velocity actuator commanded to
#: 1 rad/s delivers 1e-9 instead, finite the whole way, warned about by
#: nothing. Measured (M4 phase 0) at 1.218e10 for an actuator's damping and
#: 2.89e10 for a joint's, invariant across four decades of inertia and both
#: solver steps -- so one ceiling a decade below the smaller of them covers
#: both, and the two cannot drift apart.
#:
#: Nothing real approaches it: 1e9 s⁻¹ is an actuator that settles in a
#: nanosecond. It exists so that the regime where MuJoCo stops moving a
#: joint without saying so is a refusal rather than a mystery.
MAXIMUM_DAMPING_RATE_PER_S = 1.0e9


def _limit_range(
    limits: Any, *, angular: bool, context: str
) -> tuple[list[float], dict[str, Any]] | None:
    """One FreeCAD limit pair as a MuJoCo range, in radians or metres."""

    if limits is None:
        return None
    values = list(limits)
    if len(values) != 2 or values == [None, None]:
        return None
    margin = _OPEN_ANGLE_MARGIN_RADIANS if angular else _OPEN_LENGTH_MARGIN_M

    def _convert(value: Any) -> float:
        return math.radians(float(value)) if angular else length_m(float(value))

    low = None if values[0] is None else _convert(values[0])
    high = None if values[1] is None else _convert(values[1])
    if low is None:
        low = high - margin
    if high is None:
        high = low + margin
    if not (math.isfinite(low) and math.isfinite(high)) or low >= high:
        raise DynamicsError(
            f"{context} has an empty limit range.",
            reason="malformed_limits",
            observed={"context": context, "limits": values},
        )
    return [low, high], {
        "declared": values,
        "range": [low, high],
        "unit": "radians" if angular else "metres",
        "one_sided": values[0] is None or values[1] is None,
    }


def _coupling_records(
    tree: Mapping[str, Any],
    placements: Mapping[str, Sequence[float]],
    solved_values: Mapping[str, Sequence[float]],
) -> list[dict[str, Any]]:
    """Gear, belt and screw couplings, as MuJoCo ``equality/joint`` rows.

    The laws are **measured against OndselSolver**, not guessed, because a
    wrong ratio or a wrong sign is a gear train running backwards, which
    looks exactly like a working mechanism. Driving one revolution through
    the real kinematics path gave:

    * **gears** (r1=20, r2=10): the second wheel turns −2x the first, both
      measured against their common housing. So ``a1 = −(r1/r2)``, and
      external gears counter-rotate. FreeCAD builds a belt as a gear with
      ``radiusJ`` negated (AssemblyObject.cpp), so a belt is ``+(r1/r2)``,
      and the measurement agrees.
    * **screw** (pitch 4 mm): one turn of the shaft moved the nut −4.00 mm,
      so ``pitch`` is millimetres per **revolution** and the relation is
      ``Δz = pitch·Δθ / 2π``. That is hazard 7's 2π ambiguity settled by
      experiment; OndselSolver's own ``ScrewConstraintIJ`` agrees
      (``2π·z − pitch·θz = const``).

    ``rack_pinion`` is refused. Its native constraint acts along a marker
    frame OndselSolver builds specially (``getRackPinionMarkers``), the one
    measurement run on it did not produce the clean ``x = R·θ`` the sign
    convention would need, and shipping the guess is precisely what hazard 7
    warns against.

    Every coupling also carries strict preconditions, because a coupling is
    only expressible as a scalar relation when each side *is* one scalar
    joint coordinate: both components attached by tree joints, to the same
    parent, on axes parallel to the coupling's own.
    """

    bodies = {str(body["name"]): body for body in tree["bodies"]}
    records: list[dict[str, Any]] = []
    for coupling in tree["couplings"]:
        name = str(coupling["name"])
        kind = str(coupling["kind"])
        if kind == "rack_pinion":
            raise DynamicsError(
                f"Joint {name!r} is a rack-and-pinion, which M2 does not "
                "translate.",
                reason="unmapped_coupled_joint",
                correction=(
                    "The native rack constraint acts along a marker frame "
                    "OndselSolver derives from the rack's geometry, and this "
                    "slice will not guess its sign: a rack running backwards "
                    "looks like a working mechanism. Model the pair as a "
                    "gears joint, or leave it out of the dynamics assembly."
                ),
                observed={"joint": name, "kind": kind},
            )
        first, second = coupling["components"]
        axis = _axis_normalised(
            matrix_z_axis(
                matrix_multiply(placements[first], coupling["local_matrices"][0])
            ),
            context=f"joint {name!r}",
        )
        sides: list[dict[str, Any]] = []
        for component, local in zip(
            coupling["components"], coupling["local_matrices"], strict=True
        ):
            body = bodies[component]
            # The coupling's own two connector frames must agree about the
            # axis before anything else is asked about it: FreeCAD requires
            # collinear JCS for all four of these, and a pair that disagrees
            # is a joint whose relative rotation is not a scalar at all.
            connector_axis = _axis_normalised(
                matrix_z_axis(matrix_multiply(placements[component], local)),
                context=f"joint {name!r}",
            )
            connector_alignment = sum(
                a * b for a, b in zip(connector_axis, axis, strict=True)
            )
            if abs(connector_alignment) < 1.0 - 1.0e-6:
                raise DynamicsError(
                    f"Joint {name!r} has connector frames whose +Z axes are not "
                    f"collinear (alignment {connector_alignment:.6f}).",
                    reason="coupled_axes_not_parallel",
                    correction=(
                        "A gear, belt or screw joint relates rotation about one "
                        "shared axis. Point both connector +Z axes the same way."
                    ),
                    observed={"joint": name, "component": component},
                )
            if body["attachment"] != "tree" or len(body["mujoco_joints"]) != 1:
                raise DynamicsError(
                    f"Joint {name!r} couples component {component!r}, which has "
                    "no single joint coordinate to couple: it is "
                    f"{body['attachment']} with "
                    f"{len(body['mujoco_joints'])} degree(s) of freedom.",
                    reason="uncouplable_component",
                    correction=(
                        f"A {kind} joint constrains motion that other joints "
                        "provide. Give each coupled component exactly one "
                        "revolute or slider joint to the same parent component."
                    ),
                    observed={"joint": name, "component": component},
                )
            side_axis = _axis_normalised(
                matrix_z_axis(
                    matrix_multiply(
                        placements[component], body["child_local_matrix"]
                    )
                ),
                context=f"joint {body['joint']!r}",
            )
            alignment = sum(a * b for a, b in zip(side_axis, axis, strict=True))
            if abs(alignment) < 1.0 - 1.0e-6:
                raise DynamicsError(
                    f"Joint {name!r} couples component {component!r} about an "
                    f"axis its {body['joint_kind']} joint does not share "
                    f"(alignment {alignment:.6f}).",
                    reason="coupled_axes_not_parallel",
                    correction=(
                        "Gear, belt and screw couplings relate rotation about "
                        "one shared axis. Align the coupled joint's connector "
                        "+Z with the joints that place the two components."
                    ),
                    observed={"joint": name, "component": component},
                )
            sides.append(
                {
                    "component": component,
                    "body": body,
                    "sign": 1.0 if alignment > 0.0 else -1.0,
                    "joint": str(body["joint"]),
                    "kind": str(body["joint_kind"]),
                    "value": float(solved_values[str(body["joint"])][0]),
                }
            )
        if sides[0]["body"]["parent"] != sides[1]["body"]["parent"]:
            raise DynamicsError(
                f"Joint {name!r} couples two components that hang off different "
                f"parents ({sides[0]['body']['parent']!r} and "
                f"{sides[1]['body']['parent']!r}).",
                reason="coupled_parents_differ",
                correction=(
                    "A coupling relates two joint coordinates, and coordinates "
                    "are only comparable against a common frame. Join both "
                    "coupled components to the same parent component."
                ),
                observed={"joint": name},
            )
        parameters = dict(coupling["parameters"])
        if kind in {"gears", "belt"}:
            for side in sides:
                if side["kind"] != "revolute":
                    raise DynamicsError(
                        f"Joint {name!r} is a {kind} joint, but component "
                        f"{side['component']!r} is placed by a {side['kind']} "
                        "joint rather than a revolute one.",
                        reason="coupled_joint_kind",
                        correction=(
                            "Gears and belts couple two rotations. Place both "
                            "wheels with revolute joints."
                        ),
                        observed={"joint": name, "component": side["component"]},
                    )
            ratio = float(parameters["radius1_mm"]) / float(parameters["radius2_mm"])
            slope = (-ratio if kind == "gears" else ratio) * sides[0]["sign"] * sides[1]["sign"]
            dependent, independent = sides[1], sides[0]
        else:
            sliders = [side for side in sides if side["kind"] == "slider"]
            rotators = [side for side in sides if side["kind"] == "revolute"]
            if len(sliders) != 1 or len(rotators) != 1:
                raise DynamicsError(
                    f"Joint {name!r} is a screw, which needs one component on a "
                    "slider and the other on a revolute joint; this one has "
                    f"{[side['kind'] for side in sides]}.",
                    reason="coupled_joint_kind",
                    correction=(
                        "FreeCAD's screw joint constrains a slide against a "
                        "rotation that other joints provide. Add the missing "
                        "slider or revolute joint to the same parent."
                    ),
                    observed={"joint": name},
                )
            pitch_m = length_m(float(parameters["thread_pitch_mm"]))
            slope = (
                -sliders[0]["sign"]
                * rotators[0]["sign"]
                * pitch_m
                / (2.0 * math.pi)
            )
            dependent, independent = sliders[0], rotators[0]
        # a0 carries the solved offset: the coupling holds where FreeCAD
        # solved it, not only where the model's reference configuration is.
        intercept = dependent["value"] - slope * independent["value"]
        records.append(
            {
                "joint_output": name,
                "joint_kind": kind,
                "dependent_joint": dependent["joint"],
                "independent_joint": independent["joint"],
                "slope": slope,
                "intercept": intercept,
                "parameters": parameters,
            }
        )
    return records


#: Which unit family each MuJoCo joint type's coordinate speaks. ``ball``
#: and ``free`` are absent because neither has a scalar coordinate, which is
#: why neither can be damped or driven.
_MOTION_BY_MUJOCO_TYPE = {"hinge": "angular", "slide": "linear"}


def _coordinate_table(
    tree: Mapping[str, Any], joint_records: Sequence[Mapping[str, Any]]
) -> dict[tuple[str, str], dict[str, Any]]:
    """Every joint coordinate a script may damp or drive, and why the rest not.

    Built from ``joint_records`` rather than from the tree directly, so the
    MuJoCo joint names here are the ones ``build_model`` actually wrote --
    a second copy of the ``joint`` vs ``joint/hinge`` naming rule is a bug
    waiting for a cylindrical joint.

    The second return is the *refusal* map, and it is the reason this exists
    as a table rather than a lookup: a joint that is missing from the model
    is missing for a specific reason -- it closes a loop, it is a coupling
    that attaches nothing, it is suppressed, both its components are
    grounded -- and a refusal that cannot say which is a bug report
    addressed to nobody.
    """

    table: dict[tuple[str, str], dict[str, Any]] = {}
    for record in joint_records:
        joint = record.get("joint")
        if joint is None:
            continue
        motion = _MOTION_BY_MUJOCO_TYPE.get(str(record["mujoco_type"]))
        if motion is None:
            continue
        table[(str(joint), motion)] = dict(record)
    return table


def _coordinate_refusals(tree: Mapping[str, Any]) -> dict[str, str]:
    """Why each live joint that owns no coordinate owns none."""

    reasons: dict[str, str] = {}
    for closure in tree["closures"]:
        reasons[str(closure["joint"])] = (
            "closes a loop, so the dynamics model expresses it as an equality "
            "constraint and there is no MuJoCo joint on it to drive. Drive one "
            "of the joints the spanning tree did use, or reorder the joints so "
            "that this one becomes a tree edge and another closes the loop"
        )
    for coupling in tree["couplings"]:
        reasons[str(coupling["name"])] = (
            f"is a {coupling['kind']} joint, which attaches nothing: it relates "
            "coordinates that other joints provide. Drive one of those joints "
            "instead -- the coupling will carry the motion across"
        )
    for static in tree["static_joints"]:
        reasons[str(static["joint"])] = (
            "connects two grounded components, so it is satisfied by the "
            "solved placements and has no coordinate in the dynamics model"
        )
    for joint in tree["classified_joints"]:
        if joint["suppressed"]:
            reasons[str(joint["name"])] = (
                "is suppressed, so FreeCAD's solver ignored it and the dynamics "
                "model has no joint there at all"
            )
    return reasons


def _coordinate_context(joint: str, motion: str) -> str:
    return f"joint {joint!r} ({motion})"


def _resolve_coordinate(
    entry: Mapping[str, Any],
    table: Mapping[tuple[str, str], Mapping[str, Any]],
    refusals: Mapping[str, str],
    *,
    what: str,
) -> dict[str, Any]:
    """One graph entry, against the coordinate it claims to configure."""

    joint = str(entry.get("joint") or "")
    motion = str(entry.get("motion_type") or "")
    record = table.get((joint, motion))
    if record is not None:
        return dict(record)
    reason = refusals.get(joint)
    if reason is not None:
        raise DynamicsError(
            f"{what} targets joint {joint!r}, which {reason}.",
            reason="joint_has_no_coordinate",
            observed={"joint": joint, "motion_type": motion, "what": what},
        )
    if any(name == joint for name, _motion in table):
        available = sorted(
            other for name, other in table if name == joint
        )
        raise DynamicsError(
            f"{what} targets the {motion} coordinate of joint {joint!r}, which "
            f"owns only {' and '.join(available)}.",
            reason="joint_has_no_coordinate",
            correction=(
                "A revolute joint has an angular coordinate and a slider a "
                "linear one; only a cylindrical joint has both."
            ),
            observed={"joint": joint, "motion_type": motion},
        )
    raise DynamicsError(
        f"{what} targets joint {joint!r}, which is not part of this assembly.",
        reason="joint_not_in_assembly",
        correction=(
            "Pass the same api.joint variable the assembly was built from."
        ),
        observed={"joint": joint},
    )


def joint_dynamics_records(
    entries: Sequence[Mapping[str, Any]],
    tree: Mapping[str, Any],
    joint_records: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Damping, armature and friction loss for named joint coordinates, in SI.

    Every conversion happens here and nowhere else, which is the M2 split
    rule holding through a second slice: the script surface speaks
    newton-millimetres per degree and kilogram-millimetres squared, the
    model speaks newton-metre-seconds per radian and kilogram-metres
    squared, and the worker -- which is the only place with FreeCAD in it --
    reads these numbers straight off the graph without touching them.
    """

    table = _coordinate_table(tree, joint_records)
    refusals = _coordinate_refusals(tree)
    records: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for entry in entries:
        joint = str(entry.get("joint") or "")
        motion = str(entry.get("motion_type") or "")
        what = f"joint_dynamics for {_coordinate_context(joint, motion)}"
        record = _resolve_coordinate(entry, table, refusals, what=what)
        if (joint, motion) in seen:
            raise DynamicsError(
                f"{_coordinate_context(joint, motion)} is configured twice.",
                reason="duplicate_joint_dynamics",
                observed={"joint": joint, "motion_type": motion},
            )
        seen.add((joint, motion))
        angular = motion == "angular"
        damping = float(
            (
                entry.get("damping_nmms_per_deg")
                if angular
                else entry.get("damping_ns_per_mm")
            )
            or 0.0
        )
        armature = float(
            (entry.get("armature_kgmm2") if angular else entry.get("armature_kg"))
            or 0.0
        )
        friction = float(
            (
                entry.get("friction_loss_nmm")
                if angular
                else entry.get("friction_loss_n")
            )
            or 0.0
        )
        records.append(
            {
                "joint": joint,
                "motion_type": motion,
                "mujoco_joint": str(record["mujoco_joint"]),
                "mujoco_type": str(record["mujoco_type"]),
                "joint_kind": str(record["kind"]),
                "damping_si": (
                    damping_nms_per_rad(damping) if angular else damping_ns_per_m(damping)
                ),
                "armature_si": (
                    armature_kg_m2(armature) if angular else float(armature)
                ),
                "friction_loss_si": (
                    torque_nm(friction) if angular else float(friction)
                ),
                "declared": {
                    "damping": damping,
                    "armature": armature,
                    "friction_loss": friction,
                },
            }
        )
    return records


#: Everything a control formula may name, bound once and shared by every
#: evaluation. This dict *is* the globals the expression sees: there is no
#: ``__builtins__`` in it, so a name the API's whitelist somehow let through
#: still resolves to nothing. Two independent barriers rather than one,
#: because the second costs a dictionary.
_CONTROL_GLOBALS: dict[str, Any] = {
    "__builtins__": {},
    "pi": math.pi,
    "abs": abs,
    "sin": math.sin,
    "cos": math.cos,
    "asin": math.asin,
    "arcsin": math.asin,
    "arctan": math.atan,
}


def compile_control(formula: str, *, context: str) -> Any:
    """One control formula, compiled once, for a run that will step it a lot.

    ``compile`` of an already-parsed and already-whitelisted expression --
    never ``eval`` of a string at step time. At the two-million-step ceiling
    ``MAXIMUM_SOLVER_STEPS`` allows, evaluating a compiled expression costs
    about a second per actuator, which is affordable; re-parsing the source
    every step would not be.
    """

    try:
        tree = ast.parse(str(formula), mode="eval")
    except SyntaxError as exc:
        raise DynamicsError(
            f"{context} has a control formula that is not an expression: {exc}",
            reason="malformed_control_formula",
            observed={"context": context, "formula": str(formula)},
        ) from exc
    return compile(tree, filename="<control>", mode="eval")


def evaluate_control(code: Any, time_s: float, *, context: str) -> float:
    """The formula's value at one instant, as a finite number or a refusal."""

    try:
        value = float(eval(code, _CONTROL_GLOBALS, {"time": float(time_s)}))
    except Exception as exc:
        raise DynamicsError(
            f"{context} could not be evaluated at t = {time_s:.6g} s: {exc}",
            reason="control_formula_failed",
            correction=(
                "A control formula is arithmetic on `time` in seconds. Check "
                "for a division by zero or a function outside its domain -- "
                "asin of something past 1, for instance."
            ),
            observed={"context": context, "time_s": float(time_s)},
        ) from exc
    if not math.isfinite(value):
        raise DynamicsError(
            f"{context} evaluated to {value} at t = {time_s:.6g} s.",
            reason="control_formula_failed",
            correction=(
                "A control that is not a finite number is not a command. "
                "Check the formula for a pole in the run's time range."
            ),
            observed={"context": context, "time_s": float(time_s)},
        )
    return value


#: What one evaluated control means, per kind and coordinate, in the unit
#: MuJoCo's ``ctrl`` speaks. This is the last conversion in the M4 boundary
#: and the one with the most ways to be silently wrong: the same string
#: "30" is a third of a turn, thirty millimetres or half a newton-metre
#: depending on two other words in the script.
_CONTROL_CONVERSIONS = {
    ("position", "angular"): angle_radians,
    ("position", "linear"): length_m,
    ("velocity", "angular"): angle_radians,
    ("velocity", "linear"): speed_m_s,
    ("motor", "angular"): torque_nm,
    ("motor", "linear"): float,
}


def control_si(value: float, *, kind: str, motion_type: str, context: str) -> float:
    """One evaluated control, in the unit the compiled model reads."""

    convert = _CONTROL_CONVERSIONS.get((str(kind), str(motion_type)))
    if convert is None:
        raise DynamicsError(
            f"{context} has no control unit for a {kind} actuator on a "
            f"{motion_type} coordinate.",
            reason="malformed_actuator",
            observed={"context": context, "kind": kind, "motion_type": motion_type},
        )
    return float(convert(float(value)))


def actuator_records(
    entries: Sequence[Mapping[str, Any]],
    tree: Mapping[str, Any],
    joint_records: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Every motor, resolved to a joint coordinate and converted to SI.

    Same shape as :func:`joint_dynamics_records` and the same refusals, for
    the same reason: a joint the spanning forest turned into a loop closure,
    a coupling that attaches nothing, a suppressed joint and a joint from
    some other assembly are all authoring mistakes, and only the tree can
    tell which one this is.

    The control formula travels through untouched. It is a *formula*, not a
    number, so there is nothing to convert until it has been evaluated --
    which is what makes the conversion of its result the one thing this
    module must not let escape.
    """

    table = _coordinate_table(tree, joint_records)
    refusals = _coordinate_refusals(tree)
    records: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for entry in entries:
        joint = str(entry.get("joint") or "")
        motion = str(entry.get("motion_type") or "")
        kind = str(entry.get("kind") or "")
        what = f"the {kind} actuator on {_coordinate_context(joint, motion)}"
        record = _resolve_coordinate(entry, table, refusals, what=what)
        if (joint, motion) in seen:
            raise DynamicsError(
                f"{_coordinate_context(joint, motion)} carries two actuators.",
                reason="duplicate_actuator",
                correction=(
                    "One joint coordinate has one motor. Two would sum their "
                    "efforts, which is a mechanism nobody described."
                ),
                observed={"joint": joint, "motion_type": motion},
            )
        seen.add((joint, motion))
        angular = motion == "angular"

        def _declared(angular_key: str, linear_key: str) -> float | None:
            value = entry.get(angular_key if angular else linear_key)
            return None if value is None else float(value)

        stiffness = _declared("stiffness_nmm_per_deg", "stiffness_n_per_mm")
        damping = _declared("damping_nmms_per_deg", "damping_ns_per_mm")
        effort = _declared("torque_limit_nmm", "force_limit_n")
        control = entry.get(
            {
                ("motor", True): "control_nmm",
                ("motor", False): "control_n",
                ("position", True): "control_deg",
                ("position", False): "control_mm",
                ("velocity", True): "control_deg_per_s",
                ("velocity", False): "control_mm_per_s",
            }[(kind, angular)]
        )
        if not isinstance(control, str) or not control:
            raise DynamicsError(
                f"{what} has no control formula.",
                reason="malformed_actuator",
                observed={"joint": joint, "kind": kind},
            )
        records.append(
            {
                "joint": joint,
                "motion_type": motion,
                "kind": kind,
                "mujoco_joint": str(record["mujoco_joint"]),
                "mujoco_type": str(record["mujoco_type"]),
                "mujoco_actuator": f"{record['mujoco_joint']}/{kind}",
                "joint_kind": str(record["kind"]),
                "control": control,
                # Compiled here rather than at step time: the formula is
                # evaluated once per solver step, and there are up to two
                # million of those.
                "control_code": compile_control(control, context=what),
                # Every gain in SI, converted exactly once and here. The
                # units the script wrote are kept beside them, because a
                # reader comparing two runs wants the number they typed.
                "stiffness_si": (
                    None
                    if stiffness is None
                    else (
                        stiffness_nm_per_rad(stiffness)
                        if angular
                        else stiffness_n_per_m(stiffness)
                    )
                ),
                "damping_si": (
                    None
                    if damping is None
                    else (
                        damping_nms_per_rad(damping)
                        if angular
                        else damping_ns_per_m(damping)
                    )
                ),
                "effort_limit_si": (
                    None
                    if effort is None
                    else (torque_nm(effort) if angular else float(effort))
                ),
                "declared": {
                    "control": control,
                    "stiffness": stiffness,
                    "damping": damping,
                    "effort_limit": effort,
                },
            }
        )
    return records


def _verify_gains_are_resolvable(
    mujoco: Any,
    model: Any,
    qpos: Sequence[float],
    actuators: Sequence[Mapping[str, Any]],
) -> None:
    """A position gain the solver step cannot carry is refused, not delivered.

    ``implicitfast`` integrates damping implicitly and stiffness explicitly,
    so a position actuator's spring term inherits the classical ``ω·h < 2``
    -- measured (M4 phase 0) at 2.02 on four different steps and invariant
    across a 400x range of inertia, which is what lets this be stated once,
    dimensionlessly, for every mechanism rather than as a gain for one.

    The refusal names the step it would take, exactly as M3's restitution
    refusal does, because "too stiff" without a number is advice nobody can
    act on.
    """

    if not any(record.get("stiffness_si") for record in actuators):
        return
    inertia = _dof_inertia(mujoco, model, qpos)
    for record in actuators:
        gain = record.get("stiffness_si")
        if not gain:
            continue
        joint_id = mujoco.mj_name2id(
            model, mujoco.mjtObj.mjOBJ_JOINT, str(record["mujoco_joint"])
        )
        mass = inertia[int(model.jnt_dofadr[joint_id])]
        if mass <= 0.0:
            continue
        step = float(model.opt.timestep)
        omega_step = step * math.sqrt(float(gain) / mass)
        if omega_step <= MAXIMUM_ACTUATOR_OMEGA_STEP:
            continue
        required = MAXIMUM_ACTUATOR_OMEGA_STEP / math.sqrt(float(gain) / mass)
        raise DynamicsError(
            f"The actuator on joint {record['joint']!r} has a gain of "
            f"{gain:.6g} against {mass:.6g} of inertia, which needs a solver "
            f"step of {required:.6g} s or finer; this run steps at "
            f"{step:.6g} s.",
            reason="actuator_gain_needs_a_finer_step",
            correction=(
                "MuJoCo integrates a position actuator's spring explicitly, so "
                "a spring stepped too coarsely gains energy rather than "
                "holding: past this the joint oscillates and then diverges. "
                "Pass a finer solver_step_s to assembly.dynamics, lower the "
                "gain, or raise the joint's armature with "
                "assembly.joint_dynamics -- a heavier rotor carries a stiffer "
                "gain at the same step."
            ),
            observed={
                "joint": str(record["joint"]),
                "stiffness_si": float(gain),
                "inertia": mass,
                "solver_step_s": step,
                "required_step_s": required,
                "omega_step": omega_step,
            },
        )


def _mujoco_module() -> Any:
    """The one import site, with the payload failure named if it is missing."""

    try:
        import mujoco  # noqa: PLC0415 - deliberately not module scope
    except ImportError as exc:  # pragma: no cover - a broken payload only
        raise DynamicsError(
            "This engine build cannot import mujoco, so assembly.dynamics "
            "cannot run.",
            reason="mujoco_unavailable",
            correction=(
                "The engine payload carries mujoco as a pypi wheel (ADR-061). "
                "Rebuild the payload with pixi run stage-engine."
            ),
        ) from exc
    return mujoco


def _verify_restitution_is_resolvable(
    geoms: Mapping[str, Sequence[Mapping[str, Any]]], *, time_step_s: float
) -> None:
    """A bouncy contact the solver cannot resolve is refused, not delivered.

    The measurement that made this a refusal rather than a footnote: at the
    default solver step -- ten steps per contact time constant, which is
    what 60 fps and ``DEFAULT_TIME_STEP_S`` produce -- a requested
    restitution of 0.9 comes back as **3.45**. The ball bounces higher than
    it was dropped from, forever, and every frame of it looks like physics.
    At twenty steps the worst error across the whole authorable band is
    12%, so twenty is the line.

    Nothing is refused when no shape bounces, which is the default, so this
    costs an ordinary contact model nothing.
    """

    limit = CONTACT_TIMECONST_S / RESTITUTION_STEPS_PER_TIMECONST
    if time_step_s <= limit:
        return
    bouncy = sorted(
        (name, float(record["restitution"]))
        for name, records in geoms.items()
        for record in records
        if float(record.get("restitution") or 0.0) > 0.0
    )
    if not bouncy:
        return
    component, restitution = bouncy[0]
    raise DynamicsError(
        f"Component {component!r} asks for a restitution of {restitution:g}, "
        f"but the solver step is {time_step_s:.6g} s and a bouncing contact "
        f"needs {limit:.6g} s or finer to come out at the value asked for.",
        reason="restitution_needs_a_finer_step",
        correction=(
            "MuJoCo integrates a contact as a spring, and a spring stepped "
            "too coarsely gains energy: measured, a restitution of 0.9 at "
            "the default step returns 3.45, a ball bouncing higher than it "
            "was dropped from. Pass a finer solver_step_s to "
            "assembly.dynamics, or set the restitution to 0."
        ),
        observed={
            "component": component,
            "restitution": restitution,
            "solver_step_s": time_step_s,
            "required_step_s": limit,
        },
    )


def _add_collision_geoms(
    mujoco: Any,
    spec: Any,
    native: Any,
    name: str,
    records: Sequence[Mapping[str, Any]],
) -> None:
    """Attach one body's measured collision shapes to it.

    Adding nothing when there is nothing to add is the case that matters:
    a body with no collision shape keeps ``ngeom == 0``, passes through
    everything, and behaves exactly as it did before M3 -- which is what
    lets a mechanism opt into contact one part at a time.

    A geom carries no mass here. ``inertiafromgeom`` is off and the body's
    inertia is explicit, so these shapes decide what touches what and
    nothing else; ``_verify_compiled_inertia`` re-checks that after the
    compile, which is what would catch a MuJoCo release deciding otherwise.
    """

    types = {
        "box": mujoco.mjtGeom.mjGEOM_BOX,
        "sphere": mujoco.mjtGeom.mjGEOM_SPHERE,
        "cylinder": mujoco.mjtGeom.mjGEOM_CYLINDER,
        "capsule": mujoco.mjtGeom.mjGEOM_CAPSULE,
        "mesh": mujoco.mjtGeom.mjGEOM_MESH,
    }
    for record in records:
        geom_name = f"{name}/collision{record['index']}"
        arguments: dict[str, Any] = {
            "name": geom_name,
            "type": types[str(record["mujoco_type"])],
            "pos": list(record["pos_m"]),
            "quat": list(record["quat_wxyz"]),
            "friction": list(record["friction"]),
            "solref": list(record["solref"]),
            "condim": int(record["condim"]),
            "margin": float(record["margin_m"]),
            "contype": int(record["contype"]),
            "conaffinity": int(record["conaffinity"]),
        }
        if str(record["mujoco_type"]) == "mesh":
            mesh = spec.add_mesh()
            mesh.name = geom_name + "/mesh"
            mesh.uservert = list(record["vertices_m"])
            mesh.userface = list(record["triangles"])
            arguments["meshname"] = mesh.name
        else:
            arguments["size"] = list(record["size_m"])
        native.add_geom(**arguments)


def build_model(
    components: Sequence[Mapping[str, Any]],
    joints: Sequence[Mapping[str, Any]],
    *,
    gravity_m_s2: Sequence[float] = DEFAULT_GRAVITY_M_S2,
    time_step_s: float = DEFAULT_TIME_STEP_S,
    joint_dynamics: Sequence[Mapping[str, Any]] = (),
    actuators: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    """One assembly, as a compiled MuJoCo model plus the evidence for it.

    The construction, stated once because everything downstream depends on
    it being this and not something that merely looks like it:

    * The MuJoCo body frame **is** the FreeCAD component frame, with the
      mass offset carried in ``body.ipos``. Putting the body frame at the
      centre of mass instead offsets every part inside itself, which reads
      on screen as "the mesh is wrong" (hazard 4).
    * A tree body's frame relative to its parent is ``L_p ∘ inv(L_c)`` --
      the configuration in which the two connector frames *coincide* -- and
      the joint sits at ``L_c``'s origin along ``L_c``'s +Z. That makes the
      model's reference configuration a canonical one rather than the
      solved one, so the solved pose has to be *derived* as a joint
      coordinate and can be checked against ``component_placements``.
      Building at the solved pose instead would make that check a
      tautology: it passes on a model whose joint axes are entirely wrong.
    * Grounded components are static bodies. Unreached ones get a free
      joint and fall.

    Returns the spec, the compiled model, the tree, and per-joint records
    carrying each joint's qpos address and its solved coordinate.
    """

    mujoco = _mujoco_module()
    tree = extract_tree(components, joints)
    placements = {
        str(component["name"]): checked_rigid_matrix(
            component["solved_matrix"],
            context=f"component {component.get('name')!r} solved placement",
        )
        for component in components
    }
    inertials = {
        str(component["name"]): dict(component["inertial"])
        for component in components
    }
    # Every collision shape is measured and converted before a single geom
    # is added, so a refusal names the component rather than arriving as a
    # compiler error about an element id.
    geoms = {
        str(component["name"]): collision_geoms(
            list((component.get("collision") or {}).get("shapes") or []),
            (component.get("collision") or {}).get("mesh"),
            exact_volume_mm3=float(component["inertial"]["volume_mm3"]),
            context=f"component {component.get('name')!r}",
        )
        for component in components
    }

    _verify_restitution_is_resolvable(geoms, time_step_s=float(time_step_s))

    spec = mujoco.MjSpec()
    spec.modelname = "cadex-assembly"
    # Every one of these is load-bearing and none is a default worth
    # trusting. balanceinertia rewrites an exact tensor into invented
    # numbers -- [0.001, 0.001, 1.0] compiles to [0.334, 0.334, 0.334] --
    # and exact inertia is this slice's whole differentiator. boundinertia
    # and boundmass do the same thing more quietly. inertiafromgeom would
    # infer mass from geometry we deliberately do not add.
    spec.compiler.balanceinertia = False
    spec.compiler.boundinertia = 0.0
    spec.compiler.boundmass = 0.0
    spec.compiler.inertiafromgeom = mujoco.mjtInertiaFromGeom.mjINERTIAFROMGEOM_FALSE
    # Radians everywhere. The default is degrees, and it silently turned a
    # [-1, 1] joint range into [-0.017, 0.017] the first time this was
    # measured.
    spec.compiler.degree = False
    spec.option.gravity = list(gravity_m_s2)
    spec.option.timestep = float(time_step_s)
    # Islands off, explicitly (M3 phase 0). Measured on mujoco 3.10.0:
    # ``mjDSBL_ISLAND`` is a *disable* bit and a default compile has
    # ``disableflags == 0``, so islands are **on** by default -- the
    # opposite of what "forced single-threaded" sounded like. On a jointed
    # model with no contact the flag moves nothing (measured: zero delta
    # over 300 steps of the four-bar), but once geoms exist it does: three
    # boxes settling on a plane came out 2e-14 apart in qpos after 1500
    # steps, which is small and is still enough to move a digest we assert
    # equality over. Both settings are reproducible across processes, so
    # the choice is about which one is *written down*: islands off is the
    # single monolithic constraint solve, whose row ordering does not
    # depend on how contacts happen to partition. It costs nothing here
    # because islands only buy parallelism when an ``mjData`` is handed a
    # thread pool, which this module never does.
    spec.option.disableflags = int(mujoco.mjtDisableBit.mjDSBL_ISLAND)
    # Sleep off, explicitly, for the same reason and a louder failure: a
    # body MuJoCo has put to sleep stops integrating, and a settling
    # mechanism -- M3's whole scenario -- is exactly what that freezes. It
    # is off by default in 3.10.0 (``enableflags == 0``); an assertion
    # after compile is what keeps that true.
    spec.option.enableflags = 0
    # The integrator is a decision, not a default (M3 phase 3). MuJoCo's
    # default is Euler and the measurement that ruled it out is a freely
    # tumbling asymmetric part -- the shape of anything that falls over:
    # over twenty seconds at the default step Euler *gains* 51% of its
    # kinetic energy, a part spinning faster the longer it spins, and every
    # frame of it looks like physics. implicitfast conserves angular
    # momentum and energy to the printed precision, reproduces RK4's
    # trajectory through three Dzhanibekov flips to three decimals, and
    # costs one force evaluation per step where RK4 costs four. Full
    # implicit was measured too and is worse than either: it *loses* 29%.
    spec.option.integrator = mujoco.mjtIntegrator.mjINT_IMPLICITFAST

    # ``autolimits`` defaults *on* and would turn any range this module
    # writes into a limit by inference. Off, a range without its flag is a
    # compile error instead -- which is the version worth having, and the
    # reason every ``limited`` below is stated rather than implied (M4
    # phase 0).
    spec.compiler.autolimits = False

    native_bodies: dict[str, Any] = {"": spec.worldbody}
    native_joints: dict[str, Any] = {}
    joint_records: list[dict[str, Any]] = []
    for body in tree["bodies"]:
        name = str(body["name"])
        parent_name = body["parent"]
        if parent_name is None:
            frame = placements[name]
            parent = spec.worldbody
        else:
            frame = matrix_multiply(
                body["parent_local_matrix"], matrix_inverse(body["child_local_matrix"])
            )
            parent = native_bodies[str(parent_name)]
        native = parent.add_body(
            name=name,
            pos=vector_m(matrix_translation_mm(frame)),
            quat=quaternion_wxyz_from_matrix(frame),
        )
        native_bodies[name] = native

        inertial = inertials[name]
        native.explicitinertial = True
        native.mass = float(inertial["mass_kg"])
        native.ipos = vector_m(inertial["center_of_mass_mm"])
        native.fullinertia = full_inertia_six(inertial["inertia_kg_m2"])
        _add_collision_geoms(mujoco, spec, native, name, geoms[name])

        if body["attachment"] == "free":
            native.add_freejoint(name=f"{name}/free")
            joint_records.append(
                {
                    "body": name,
                    "joint": None,
                    "kind": "free",
                    "mujoco_joint": f"{name}/free",
                    "mujoco_type": "free",
                    "limits": None,
                }
            )
            continue
        if not body["mujoco_joints"]:
            continue

        local = body["child_local_matrix"]
        anchor = vector_m(matrix_translation_mm(local))
        axis = _axis_normalised(
            matrix_z_axis(local), context=f"joint {body['joint']!r}"
        )
        classified = next(
            item
            for item in tree["classified_joints"]
            if item["name"] == body["joint"]
        )
        for mujoco_type in body["mujoco_joints"]:
            angular = mujoco_type in {"hinge", "ball"}
            limits = _limit_range(
                classified["angle_limits_degrees"]
                if angular
                else classified["length_limits_mm"],
                angular=angular,
                context=f"joint {body['joint']!r}",
            )
            joint_name = (
                str(body["joint"])
                if len(body["mujoco_joints"]) == 1
                else f"{body['joint']}/{mujoco_type}"
            )
            native_joint = native.add_joint(
                name=joint_name,
                type={
                    "hinge": mujoco.mjtJoint.mjJNT_HINGE,
                    "slide": mujoco.mjtJoint.mjJNT_SLIDE,
                    "ball": mujoco.mjtJoint.mjJNT_BALL,
                }[mujoco_type],
                pos=anchor,
                axis=axis,
            )
            if limits is not None and mujoco_type != "ball":
                native_joint.limited = mujoco.mjtLimited.mjLIMITED_TRUE
                native_joint.range = limits[0]
            else:
                native_joint.limited = mujoco.mjtLimited.mjLIMITED_FALSE
            native_joints[joint_name] = native_joint
            joint_records.append(
                {
                    "body": name,
                    "joint": str(body["joint"]),
                    "kind": str(body["joint_kind"]),
                    "mujoco_joint": joint_name,
                    "mujoco_type": mujoco_type,
                    "limits": None if limits is None else limits[1],
                }
            )

    # Damping, armature and friction loss, resolved against the tree that
    # was just built rather than against the script -- which is what lets
    # the refusal say "that joint closes a loop" instead of "no such joint".
    # MuJoCo's defaults for all three are zero, so a joint nobody configured
    # behaves exactly as it did before M4 and a mechanism that only falls
    # pays nothing for this existing.
    joint_dynamics_applied = joint_dynamics_records(
        joint_dynamics, tree, joint_records
    )
    for record in joint_dynamics_applied:
        native_joint = native_joints[str(record["mujoco_joint"])]
        # ``damping`` is a three-vector on an MjsJoint -- one entry per dof,
        # for a ball joint's three -- while ``armature`` and
        # ``frictionloss`` are scalars. Measured; assigning a float to the
        # first is a TypeError, which is at least the loud kind of wrong.
        native_joint.damping = [float(record["damping_si"]), 0.0, 0.0]
        native_joint.armature = float(record["armature_si"])
        native_joint.frictionloss = float(record["friction_loss_si"])

    # Actuators, after every joint exists and before the compile. Each is a
    # MuJoCo actuator on exactly one joint coordinate, with the gear pinned
    # at one: MuJoCo's ``gear`` rescales the *setpoint* as well as the
    # effort (measured, M4 phase 0), so a translator that wrote anything
    # else would silently mean something other than what the script said.
    actuator_applied = actuator_records(actuators, tree, joint_records)
    for record in actuator_applied:
        native_actuator = spec.add_actuator()
        native_actuator.name = str(record["mujoco_actuator"])
        native_actuator.target = str(record["mujoco_joint"])
        native_actuator.trntype = mujoco.mjtTrn.mjTRN_JOINT
        native_actuator.gear = [1.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        kind = str(record["kind"])
        if kind == "motor":
            native_actuator.set_to_motor()
        elif kind == "position":
            # gainprm = [kp], biasprm = [0, -kp, -kv]: the PD loop, in the
            # compiled model. Measured in phase 0 rather than read, because
            # a sign or a slot out of place is a servo that pushes away
            # from its setpoint and still looks like a mechanism.
            native_actuator.set_to_position(
                float(record["stiffness_si"]),
                kv=float(record["damping_si"] or 0.0),
            )
        else:
            native_actuator.set_to_velocity(float(record["damping_si"]))
        # Both flags stated, always. ``autolimits`` is off, so an unstated
        # one is a compile error rather than an inference -- and an effort
        # limit that exists is one somebody wrote down.
        native_actuator.ctrllimited = mujoco.mjtLimited.mjLIMITED_FALSE
        if record["effort_limit_si"] is None:
            native_actuator.forcelimited = mujoco.mjtLimited.mjLIMITED_FALSE
        else:
            limit = float(record["effort_limit_si"])
            native_actuator.forcelimited = mujoco.mjtLimited.mjLIMITED_TRUE
            native_actuator.forcerange = [-limit, limit]

    # Closures are written against *sites* placed at the two connector
    # frames, not against bodies. Measured, and it matters: a body-anchored
    # connect takes one anchor and derives the other by resolving it through
    # the model's **reference configuration** -- and this model's reference
    # configuration is deliberately not the solved pose (that is what makes
    # phase 5's parity check a test rather than a tautology). A four-bar
    # built with body anchors closed 16 mm away from where it should, in a
    # model whose XML looked entirely ordinary. Sites carry both frames
    # explicitly, so there is nothing left to infer: connect pins their
    # origins together, weld pins the whole frames -- which is exactly what
    # FreeCAD's revolute and fixed joints mean.
    for closure in tree["closures"]:
        first, second = closure["components"]
        sites = []
        for component, local in zip(
            closure["components"], closure["local_matrices"], strict=True
        ):
            site_name = f"{closure['joint']}/{component}"
            native_bodies[component].add_site(
                name=site_name,
                pos=vector_m(matrix_translation_mm(local)),
                quat=quaternion_wxyz_from_matrix(local),
            )
            sites.append(site_name)
        equality = spec.add_equality()
        equality.name = str(closure["joint"])
        equality.objtype = mujoco.mjtObj.mjOBJ_SITE
        equality.name1, equality.name2 = sites
        equality.type = (
            mujoco.mjtEq.mjEQ_CONNECT
            if closure["closure_kind"] == "connect"
            else mujoco.mjtEq.mjEQ_WELD
        )
        # MuJoCo's equality constraints are soft: a spring-damper with a
        # 0.02 s time constant by default, which let a driven four-bar drift
        # 3 mm open on a 200 mm mechanism -- measured. Two timesteps is the
        # stiffest setting the integrator accepts, and it brings that to
        # 0.05 mm. A loop that visibly comes apart while it runs is a wrong
        # answer that looks right, which is the class of failure this whole
        # slice is organised against.
        equality.solref = [2.0 * float(time_step_s), 1.0]
        equality.solimp = list(_EQUALITY_SOLIMP)
        if closure["closure_kind"] == "weld":
            data = [0.0] * 11
            data[10] = 1.0  # torquescale: the rotational rows are the point
            equality.data = data

    # Two components a script *joined* must not collide with each other, and
    # MuJoCo will not work that out on its own. Measured (M3 phase 2): its
    # parent/child filter excludes a body from its parent only when that
    # parent is not itself welded to the world -- so in a model built this
    # way, where every grounded component is a static world child, the very
    # first link of every mechanism collides with the base it is hinged to.
    # A four-bar's crank and ground overlap at the pin by construction, so
    # geoms would have made every M2 mechanism explode the moment they
    # existed. The exclusion is authored intent: parts connected by a joint
    # interpenetrate at the joint, and simulating that is never what the
    # script meant. Gears and belts are excluded for the same reason from
    # the other direction -- a coupling exists precisely because we are not
    # simulating tooth contact.
    excluded_pairs: list[list[str]] = []
    for classified in tree["classified_joints"]:
        if classified["suppressed"]:
            continue
        first, second = sorted(str(item) for item in classified["components"])
        if [first, second] in excluded_pairs:
            continue
        excluded_pairs.append([first, second])
        exclude = spec.add_exclude()
        exclude.name = f"{first}|{second}"
        exclude.bodyname1, exclude.bodyname2 = first, second

    solved_values = _solved_joint_values(tree, placements)
    couplings = _coupling_records(tree, placements, solved_values)
    for coupling in couplings:
        equality = spec.add_equality()
        equality.name = str(coupling["joint_output"])
        equality.type = mujoco.mjtEq.mjEQ_JOINT
        equality.objtype = mujoco.mjtObj.mjOBJ_JOINT
        # name1 is the dependent coordinate and name2 the independent one:
        # y − y0 = a0 + a1·(x − x0). Measured, because the documentation's
        # "joint1/joint2" says nothing about which side is which.
        equality.name1 = str(coupling["dependent_joint"])
        equality.name2 = str(coupling["independent_joint"])
        data = [0.0] * 11
        data[0] = float(coupling["intercept"])
        data[1] = float(coupling["slope"])
        equality.data = data
        equality.solref = [2.0 * float(time_step_s), 1.0]
        equality.solimp = list(_EQUALITY_SOLIMP)

    try:
        model = spec.compile()
    except Exception as exc:
        raise DynamicsError(
            f"MuJoCo refused the assembly's model: {exc}",
            reason="model_compile_failed",
            correction=(
                "The tree, the inertias and the joint frames all come from the "
                "solved assembly, so a refusal here means one of them is "
                "degenerate. Check the reported body."
            ),
            observed={"compiler_error": str(exc)},
        ) from exc

    _verify_compiled_inertia(mujoco, model, inertials, tree)
    _verify_solver_flags(mujoco, model)
    _verify_actuator_flags(mujoco, model, actuator_applied)
    qpos = _solved_qpos(
        mujoco, model, tree, placements, joint_records, solved_values
    )
    _verify_damping_is_resolvable(mujoco, model, qpos)
    _verify_gains_are_resolvable(mujoco, model, qpos, actuator_applied)
    closure_violation = _closure_violation(mujoco, model, qpos)
    if closure_violation > CLOSURE_EQUALITY_TOLERANCE:
        raise DynamicsError(
            "The assembly's loop closures do not hold at the solved pose: the "
            f"worst equality residual is {length_mm(closure_violation):.6g} mm.",
            reason="closure_inconsistent",
            correction=(
                "A loop closure that is violated at the starting pose is a "
                "pre-stressed model: the solver will pull the mechanism into "
                "shape on the first step and the animation will begin with a "
                "snap. Re-solve the assembly and check the closing joint's "
                "connectors."
            ),
            observed={"closure_residual_m": closure_violation},
        )
    return {
        "spec": spec,
        "model": model,
        "tree": tree,
        # Kept rather than discarded so an exporter can re-run the OCCT
        # comparison against a *reloaded* model without recomputing what
        # the numbers were meant to be (M5 phase 1).
        "inertials": inertials,
        "joint_records": joint_records,
        "couplings": couplings,
        "qpos_solved": qpos,
        "placements": placements,
        "time_step_s": float(time_step_s),
        "gravity_m_s2": list(gravity_m_s2),
        "disableflags": int(model.opt.disableflags),
        "enableflags": int(model.opt.enableflags),
        "geoms": geoms,
        "excluded_pairs": excluded_pairs,
        "joint_dynamics": joint_dynamics_applied,
        "actuators": actuator_applied,
        "mujoco_version": str(getattr(mujoco, "__version__", "unknown")),
    }


def _dof_inertia(mujoco: Any, model: Any, qpos: Sequence[float]) -> list[float]:
    """Each degree of freedom's own diagonal of the mass matrix, at one pose.

    This is the number every actuator refusal is stated against, and it is
    the reason those refusals can be dimensionless: a maximum *gain* would
    be right only for the mechanism it was measured on, while ``ω·h`` is
    right for all of them. ``qM`` is sparse and ``dof_Madr`` addresses its
    diagonal directly, so no dense copy is made -- and armature is already
    in it, which is exactly the sense in which an armature buys stability.
    """

    data = mujoco.MjData(model)
    data.qpos[:] = list(qpos)
    mujoco.mj_forward(model, data)
    return [
        float(data.qM[int(model.dof_Madr[index])]) for index in range(int(model.nv))
    ]


def _verify_damping_is_resolvable(
    mujoco: Any, model: Any, qpos: Sequence[float]
) -> None:
    """Damping so large the solver stops the joint rather than damping it.

    The failure this catches does not diverge: past ``c / M ≈ 1.2e10`` per
    second MuJoCo's own regularisation wins, and a joint commanded to a
    radian per second delivers a nanoradian instead -- finite the whole way,
    warned about by nothing (M4 phase 0). Silence is the worse of the two
    failure modes, so it is the one with a refusal in front of it.
    """

    inertia = _dof_inertia(mujoco, model, qpos)
    for index in range(int(model.nv)):
        mass = inertia[index]
        if mass <= 0.0:
            continue
        rate = float(model.dof_damping[index]) / mass
        if rate <= MAXIMUM_DAMPING_RATE_PER_S:
            continue
        joint = int(model.dof_jntid[index])
        name = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_JOINT, joint)
        raise DynamicsError(
            f"Joint {name!r} carries {model.dof_damping[index]:.6g} of damping "
            f"against {mass:.6g} of inertia, a rate of {rate:.4g} per second; "
            f"the accepted maximum is {MAXIMUM_DAMPING_RATE_PER_S:g}.",
            reason="damping_rate_too_high",
            correction=(
                "Past this the solver does not damp the joint, it stops it: "
                "measured, a joint commanded to one radian per second delivers "
                "a nanoradian instead, and nothing reports it. Lower the "
                "damping, or raise the joint's armature if the intent was a "
                "heavy rotor rather than a stiff damper."
            ),
            observed={
                "joint": name,
                "damping": float(model.dof_damping[index]),
                "inertia": mass,
                "rate_per_s": rate,
            },
        )


def _closure_violation(mujoco: Any, model: Any, qpos: Sequence[float]) -> float:
    """The worst equality-constraint residual at one configuration.

    ``efc_pos`` carries every active constraint row, so the equality ones
    are selected by type: a joint sitting exactly on its declared limit
    contributes a row too, and it is not a closure problem.
    """

    data = mujoco.MjData(model)
    data.qpos[:] = list(qpos)
    mujoco.mj_forward(model, data)
    worst = 0.0
    for row in range(int(data.nefc)):
        if int(data.efc_type[row]) == int(mujoco.mjtConstraint.mjCNSTR_EQUALITY):
            worst = max(worst, abs(float(data.efc_pos[row])))
    return worst


def simulate(
    components: Sequence[Mapping[str, Any]],
    joints: Sequence[Mapping[str, Any]],
    *,
    start_time_s: float,
    end_time_s: float,
    frames_per_second: int,
    time_step_s: float = DEFAULT_TIME_STEP_S,
    gravity_m_s2: Sequence[float] = DEFAULT_GRAVITY_M_S2,
    joint_dynamics: Sequence[Mapping[str, Any]] = (),
    actuators: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    """Run the model and return trace frames in the schema the shell plays.

    Three details of that schema are contract rather than choice, and all
    three were found by running M1's prototype against ``cadex_animate``
    rather than by reading it:

    * **There is a solved frame at ``start_time``, and it is not the input
      frame.** The first sample is taken *before* any stepping, and the
      untimed ``input`` frame sits in front of it. Stepping first puts the
      whole run one frame late and nothing errors.
    * **Positions are millimetres and rotations are xyzw.** MuJoCo
      integrates in metres and reports ``wxyz``.
    * **The sample rate is part of the contract.** A link turning more than
      half a circle between samples is aliased, and no amount of
      de-flipping recovers it.

    The solver steps far finer than the trace samples: the step is chosen so
    a whole number of them lands exactly on each sample time, because a
    sample interpolated between steps would make the trace depend on
    floating-point accumulation. That rounding means the step the solver
    actually takes is rarely exactly the one the script asked for, so the
    step that ran is reported in the evidence beside the one requested --
    a run whose bouncing contact was refused for being too coarsely stepped
    should be able to see which number the refusal was about.
    """

    mujoco = _mujoco_module()
    sample_interval = 1.0 / float(frames_per_second)
    requested_step = float(time_step_s)
    if not math.isfinite(requested_step) or requested_step <= 0.0:
        raise DynamicsError(
            f"The solver step must be a positive number of seconds, not "
            f"{requested_step:g}.",
            reason="malformed_solver_step",
            observed={"solver_step_s": requested_step},
        )
    steps_per_sample = max(1, int(round(sample_interval / requested_step)))
    if steps_per_sample > MAXIMUM_STEPS_PER_SAMPLE:
        raise DynamicsError(
            f"A solver step of {requested_step:g} s needs {steps_per_sample} "
            f"steps per frame at {frames_per_second} fps; the accepted maximum "
            f"is {MAXIMUM_STEPS_PER_SAMPLE}.",
            reason="solver_step_too_fine",
            correction=(
                "The cost of a run is frames times steps-per-frame, and this "
                "one is unbounded rather than slow. Raise solver_step_s or "
                "lower frames_per_second."
            ),
            observed={
                "solver_step_s": requested_step,
                "steps_per_sample": steps_per_sample,
                "frames_per_second": int(frames_per_second),
            },
        )
    solver_step = sample_interval / steps_per_sample
    sample_count = int(
        math.floor((float(end_time_s) - float(start_time_s)) * frames_per_second + 1e-9)
    )
    # The second budget (M3 phase 4), checked before the model is built so
    # a run that cannot be afforded is refused before it is paid for. The
    # frame cap in ``api.dynamics`` bounds the trace; this bounds the work.
    solver_steps = sample_count * steps_per_sample
    if solver_steps > MAXIMUM_SOLVER_STEPS:
        raise DynamicsError(
            f"This run needs {solver_steps} solver steps "
            f"({sample_count} frames x {steps_per_sample} steps each); the "
            f"accepted maximum is {MAXIMUM_SOLVER_STEPS}.",
            reason="solver_budget_exceeded",
            correction=(
                "Frames and solver steps are budgeted separately because they "
                "are separate costs: frames are what the trace carries and "
                "steps are what the solver does. Raise solver_step_s, shorten "
                "the time range, or lower frames_per_second."
            ),
            observed={
                "sample_count": sample_count,
                "steps_per_sample": steps_per_sample,
                "solver_steps": solver_steps,
                "maximum_solver_steps": MAXIMUM_SOLVER_STEPS,
            },
        )
    built = build_model(
        components,
        joints,
        gravity_m_s2=gravity_m_s2,
        time_step_s=solver_step,
        joint_dynamics=joint_dynamics,
        actuators=actuators,
    )
    model = built["model"]
    names = [str(component["name"]) for component in components]
    body_ids = {
        name: mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, name)
        for name in names
    }

    # Each actuator's index in ``data.ctrl``, resolved once. The order the
    # spec added them in is not promised to be the compiled order, and
    # writing a setpoint into the wrong slot is a mechanism that runs.
    actuator_slots = [
        (
            int(
                mujoco.mj_name2id(
                    model,
                    mujoco.mjtObj.mjOBJ_ACTUATOR,
                    str(record["mujoco_actuator"]),
                )
            ),
            record,
        )
        for record in built["actuators"]
    ]

    def _apply_control(step_index: int) -> None:
        """Every actuator's command at one instant, in the model's units.

        **Time is computed, not accumulated.** ``start + index · step`` from
        an integer index, and never MuJoCo's own clock -- which it maintains
        by adding the step to itself, and which is therefore a
        floating-point accumulation. ``simulate`` already lands its samples
        on exact step boundaries for the same reason; a control signal that
        drifted off them would make the trace depend on the drift, and the
        determinism gate is what would have to catch it, after the fact, on
        a digest, with nothing to point at.

        (A test greps this module for the attribute that would be the easy
        mistake, so it is deliberately not spelled anywhere here.)
        """

        control_time = float(start_time_s) + step_index * solver_step
        for slot, record in actuator_slots:
            context = (
                f"the {record['kind']} actuator on joint {record['joint']!r}"
            )
            data.ctrl[slot] = control_si(
                evaluate_control(
                    record["control_code"], control_time, context=context
                ),
                kind=str(record["kind"]),
                motion_type=str(record["motion_type"]),
                context=context,
            )

    data = mujoco.MjData(model)
    data.qpos[:] = built["qpos_solved"]
    _apply_control(0)
    mujoco.mj_forward(model, data)
    peak_effort = [0.0] * len(actuator_slots)

    def _record_effort() -> None:
        for index, (slot, _record) in enumerate(actuator_slots):
            peak_effort[index] = max(
                peak_effort[index], abs(float(data.actuator_force[slot]))
            )

    def _placements() -> dict[str, dict[str, list[float]]]:
        poses = {
            name: {
                "position_mm": vector_mm(data.xpos[body_ids[name]]),
                "rotation_xyzw": quaternion_xyzw_from_wxyz(
                    quaternion_normalised(data.xquat[body_ids[name]])
                ),
            }
            for name in names
        }
        # Hazard 5: a component missing from one frame is not an error the
        # shell reports -- cadex_animate skips it and Blender interpolates
        # the gap, so a part that stops moving looks like a physics result.
        if set(poses) != set(names):
            raise DynamicsError(
                "A trace frame is missing a component pose.",
                reason="incomplete_frame",
                observed={"expected": names, "observed": sorted(poses)},
            )
        return poses

    frames: list[dict[str, Any]] = [
        {
            "frame_index": 0,
            "frame_kind": "input",
            "nominal_time_s": None,
            "component_placements": _placements(),
        }
    ]
    worst_closure = _closure_violation(mujoco, model, built["qpos_solved"])
    _record_effort()
    for sample in range(sample_count + 1):
        if sample:
            for inner in range(steps_per_sample):
                _apply_control((sample - 1) * steps_per_sample + inner)
                mujoco.mj_step(model, data)
                _record_effort()
            worst_closure = max(worst_closure, _active_equality_residual(mujoco, data))
        frames.append(
            {
                "frame_index": len(frames),
                "frame_kind": "solver_output",
                "nominal_time_s": min(
                    float(end_time_s),
                    float(start_time_s) + sample * sample_interval,
                ),
                "component_placements": _placements(),
            }
        )
        if not all(math.isfinite(float(value)) for value in data.qpos):
            raise DynamicsError(
                f"The dynamics solver diverged at "
                f"{frames[-1]['nominal_time_s']:.6g} s.",
                reason="solver_diverged",
                correction=(
                    "A model that blows up usually has a body with almost no "
                    "inertia, a joint limit fighting a closure, or a mechanism "
                    "that is over-constrained. Check the reported masses."
                ),
                observed={"time_s": frames[-1]["nominal_time_s"]},
            )
    return {
        "frames": frames,
        "sample_interval_s": sample_interval,
        "solver_step_s": solver_step,
        "requested_step_s": requested_step,
        "steps_per_sample": steps_per_sample,
        "solver_steps": solver_steps,
        "solver_tolerance": float(model.opt.tolerance),
        "worst_closure_residual_mm": length_mm(worst_closure),
        "model": model,
        "built": built,
        "evidence": model_evidence(built, components, peak_effort=peak_effort),
    }


def _active_equality_residual(mujoco: Any, data: Any) -> float:
    return max(
        (
            abs(float(data.efc_pos[row]))
            for row in range(int(data.nefc))
            if int(data.efc_type[row]) == int(mujoco.mjtConstraint.mjCNSTR_EQUALITY)
        ),
        default=0.0,
    )


def model_evidence(
    built: Mapping[str, Any],
    components: Sequence[Mapping[str, Any]],
    *,
    peak_effort: Sequence[float] = (),
) -> dict[str, Any]:
    """What the translator decided, in the record the model can inspect.

    A ``connect`` closing a revolute constrains position and lets axis
    alignment go -- exact for a planar loop, one constraint short for a
    spatial one. That is recorded here rather than hidden, along with the
    mass and inertia of every body, because "the arm feels heavy" is a
    complaint nobody can act on without these numbers.
    """

    tree = built["tree"]
    return {
        "bodies": [
            {
                "component_output": str(body["name"]),
                "parent": body["parent"],
                "attachment": body["attachment"],
                "depth": body["depth"],
                "joint_output": body["joint"],
                "joint_kind": body["joint_kind"],
                "mujoco_joints": list(body["mujoco_joints"]),
            }
            for body in tree["bodies"]
        ],
        "inertials": [
            {
                "component_output": str(component["name"]),
                "density_kg_m3": float(component["inertial"]["density_kg_m3"]),
                "mass_kg": float(component["inertial"]["mass_kg"]),
                "center_of_mass_mm": list(
                    component["inertial"]["center_of_mass_mm"]
                ),
                "principal_inertia_kg_m2": list(
                    component["inertial"]["principal_inertia_kg_m2"]
                ),
                "solid_count": int(component["inertial"]["solid_count"]),
            }
            for component in components
        ],
        "closures": [
            {
                "joint_output": str(closure["joint"]),
                "joint_kind": str(closure["kind"]),
                "closure_kind": str(closure["closure_kind"]),
                "constrained_dof": int(closure["constrained_dof"]),
                "note": str(closure["note"]),
                "component_outputs": list(closure["components"]),
            }
            for closure in tree["closures"]
        ],
        "static_joints": list(tree["static_joints"]),
        "couplings": [
            {
                "joint_output": str(coupling["joint_output"]),
                "joint_kind": str(coupling["joint_kind"]),
                "dependent_joint": str(coupling["dependent_joint"]),
                "independent_joint": str(coupling["independent_joint"]),
                "slope": float(coupling["slope"]),
                "intercept": float(coupling["intercept"]),
            }
            for coupling in built["couplings"]
        ],
        "tree_joint_count": int(tree["tree_joint_count"]),
        "maximum_depth": int(tree["maximum_depth"]),
        "grounded_components": list(tree["grounded"]),
        "gravity_m_s2": list(built["gravity_m_s2"]),
        # Recorded, not merely asserted: the flags are what make one trace
        # digest comparable to another, so the trace says which ones it ran
        # under rather than leaving a reader to infer them from a version.
        "solver_disableflags": int(built["disableflags"]),
        "solver_enableflags": int(built["enableflags"]),
        "solver_integrator": "implicitfast",
        # Hazard 3, made legible. MuJoCo disclaims numerical reproducibility
        # across its own releases, and a trace's bytes are in no project
        # digest today -- so a version bump changes every trace and moves
        # nothing anybody would see. Until that decision is taken (ADR-064
        # routes it to main, because the digest code is shared with the
        # kinematics trace), the artifact at least says which MuJoCo wrote
        # it, and a reader comparing two traces can tell drift from a bug.
        "solver_version": str(built["mujoco_version"]),
        # What each body may touch things with, and -- for a mesh -- the
        # three volumes that decided it was allowed to. A hull an author
        # accepted is a fact about the model somebody will want to find
        # later without re-reading the script.
        "collisions": [
            {
                "component_output": name,
                "shapes": [
                    {
                        key: value
                        for key, value in record.items()
                        # The geometry itself is thousands of numbers and it
                        # is already in the model; the evidence carries what
                        # was decided, not what was tessellated.
                        if key not in {"vertices_m", "triangles"}
                    }
                    for record in records
                ],
            }
            for name, records in sorted(built["geoms"].items())
            if records
        ],
        # Which components were told not to touch each other, and why there
        # is a list at all: MuJoCo's own parent filter does not cover a body
        # hinged to a grounded one, so without these a four-bar's crank
        # collides with the ground it turns on.
        "contact_exclusions": [list(pair) for pair in built["excluded_pairs"]],
        "joints": [
            {
                "joint_output": record["joint"],
                "joint_kind": record["kind"],
                "mujoco_joint": record["mujoco_joint"],
                "mujoco_type": record["mujoco_type"],
                "limits": record["limits"],
            }
            for record in built["joint_records"]
        ],
        # What resistance each joint was given, in the script's units beside
        # the model's. MuJoCo's defaults are zero for all three, so a joint
        # absent from this list is frictionless, undamped and has no rotor --
        # which is a fact about the run somebody comparing two of them will
        # want without re-reading the script.
        # Every motor, what it was told, what it was allowed, and what it
        # actually had to do. The peak effort is the argument this block
        # exists for: "the arm sagged" is a complaint nobody can act on, and
        # "it saturated at its 8 N·m limit for 0.4 s" is the same complaint
        # with the answer in it -- the same case the inertials block makes
        # about "the arm feels heavy".
        "actuators": [
            {
                "joint_output": str(record["joint"]),
                "motion_type": str(record["motion_type"]),
                "kind": str(record["kind"]),
                "mujoco_actuator": str(record["mujoco_actuator"]),
                "control": str(record["control"]),
                "stiffness_si": record["stiffness_si"],
                "damping_si": record["damping_si"],
                "effort_limit_si": record["effort_limit_si"],
                "peak_effort_si": (
                    float(peak_effort[index]) if index < len(peak_effort) else None
                ),
                "saturated": (
                    None
                    if record["effort_limit_si"] is None
                    or index >= len(peak_effort)
                    else bool(
                        float(peak_effort[index])
                        >= float(record["effort_limit_si"]) * (1.0 - 1.0e-9)
                    )
                ),
                "declared": dict(record["declared"]),
            }
            for index, record in enumerate(built["actuators"])
        ],
        "joint_dynamics": [
            {
                "joint_output": str(record["joint"]),
                "motion_type": str(record["motion_type"]),
                "mujoco_joint": str(record["mujoco_joint"]),
                "damping_si": float(record["damping_si"]),
                "armature_si": float(record["armature_si"]),
                "friction_loss_si": float(record["friction_loss_si"]),
                "declared": dict(record["declared"]),
            }
            for record in built["joint_dynamics"]
        ],
    }


#: The exported file's own byte cap, sized from what a collision mesh costs
#: rather than copied from the trace's reasoning. Collision meshes are
#: written *inline* as ``<mesh vertex= face=>``, at about 51 bytes a vertex
#: measured, so one mesh at ``MAXIMUM_COLLISION_VERTICES`` is roughly 11 MB
#: of XML. 64 MiB admits five of those and refuses a file no mechanism a
#: person designed produces. It is the same number the trace carries, and
#: that is a coincidence of arithmetic rather than an inheritance.
MAXIMUM_MJCF_BYTES = 64 * 1024 * 1024

#: The keyframe the export writes, and the name anything reading the file
#: has to ask for. Without it a stock load opens at the configuration where
#: every joint's connector frames coincide -- 61 mm out of pose on the
#: four-bar, and it looks like a model rather than an error.
MJCF_KEYFRAME_NAME = "solved"

#: What a round trip through ``to_xml()`` is allowed to cost. Measured, not
#: guessed, and deliberately three separate numbers because the formatter
#: charges wildly different amounts for them (M5 phase 0):
#:
#: * mass is one number and survives to 1e-16 relative;
#: * an inertia triple's smallest entry is 1e-5 of its largest, so six
#:   significant figures leave 2.4e-6 of relative-to-largest error;
#: * everything else -- positions, axes, actuator gains -- lands under
#:   2e-6, and 1e-5 is the bound with headroom over all of them.
#:
#: There is no precision knob on ``MjSpec``. These are the terms on which
#: the exported file is the model, and stating them is the honest version
#: of "matches the in-engine simulation".
MJCF_MASS_TOLERANCE = 1.0e-12
MJCF_INERTIA_TOLERANCE = 1.0e-5
MJCF_FIELD_TOLERANCE = 1.0e-5

#: How far a body may sit from where the engine put it, at the solved pose,
#: in millimetres. The worst fixture measured 2.5e-4 mm; a hundredth of a
#: millimetre is two orders of headroom and is still far finer than any
#: tolerance a machined part carries.
MJCF_POSE_TOLERANCE_MM = 1.0e-2

#: Every count an exported file must reproduce exactly. A field comparison
#: over a model of a different shape is meaningless, so these are checked
#: before any of them.
_MJCF_COUNT_FIELDS = (
    "nbody", "njnt", "nq", "nv", "neq", "ngeom", "nsite", "nmesh", "nu",
    "nmeshvert", "nmeshface",
)

#: Every numeric field the reload is diffed on, written out rather than
#: derived from ``dir(model)``: a MuJoCo release adding a field should be a
#: decision to extend this tuple, never a silent widening of what "the same
#: model" means. ``test_dynamics_mjcf_measured`` carries the same list and
#: the measured drift of each entry.
_MJCF_MODEL_FIELDS = (
    "body_mass", "body_inertia", "body_ipos", "body_iquat", "body_pos",
    "body_quat", "jnt_type", "jnt_bodyid", "jnt_pos", "jnt_axis", "jnt_range",
    "jnt_limited", "jnt_qposadr", "jnt_dofadr", "eq_type", "eq_obj1id",
    "eq_obj2id", "eq_data", "eq_active0", "eq_solref", "eq_solimp",
    "geom_type", "geom_size", "geom_pos", "geom_quat", "geom_friction",
    "geom_solref", "geom_solimp", "geom_condim", "geom_margin", "geom_gap",
    "geom_contype", "geom_conaffinity", "actuator_gainprm", "actuator_biasprm",
    "actuator_ctrlrange", "actuator_forcerange", "actuator_gear",
    "actuator_trnid", "actuator_ctrllimited", "actuator_forcelimited",
    "dof_damping", "dof_armature", "dof_frictionloss", "site_pos", "site_quat",
    "mesh_vert", "mesh_face", "qpos0",
)

#: The solver settings M3 chose deliberately. A file that lost one would
#: integrate differently from the engine that wrote it while looking
#: identical in every other respect.
_MJCF_OPTION_FIELDS = (
    "timestep", "gravity", "integrator", "disableflags", "enableflags",
    "iterations", "tolerance", "solver", "impratio", "cone", "jacobian",
    "noslip_iterations", "o_margin", "o_solref", "o_solimp", "wind",
    "density", "viscosity", "ls_iterations", "ls_tolerance",
)


def _flattened(value: Any) -> list[float]:
    """One MuJoCo model field as a flat list of floats.

    ``tolist`` rather than numpy, so this module keeps importing nothing
    that ``test_engine_purity_guardrails`` would have to hear about.
    """

    listed = value.tolist() if hasattr(value, "tolist") else value
    flat: list[float] = []
    stack: list[Any] = [listed]
    while stack:
        item = stack.pop()
        if isinstance(item, (list, tuple)):
            stack.extend(reversed(item))
        else:
            flat.append(float(item))
    return flat


def _field_drift(first: Any, second: Any) -> float:
    """The worst absolute difference between two fields, over their scale.

    Relative to the field's own largest magnitude rather than element by
    element: a ``diaginertia`` whose smallest entry is 1e-5 of its largest
    would otherwise report the formatter's rounding of a near-zero number
    as total disagreement.
    """

    left = _flattened(first)
    right = _flattened(second)
    if len(left) != len(right):
        return float("inf")
    if not left:
        return 0.0
    scale = max(max(abs(value) for value in left), 1.0e-30)
    return max(abs(a - b) for a, b in zip(left, right)) / scale


def export_mjcf(
    built: Mapping[str, Any],
    *,
    observations: Sequence[Mapping[str, Any]] = (),
    context: str = "this assembly",
) -> dict[str, Any]:
    """One built model, as an MJCF file that is provably the same model.

    The engineering here is not "write an MJCF writer" -- MuJoCo has one,
    and ``MjSpec.to_xml()`` already emits a valid self-contained file with
    collision meshes inline, so there are no sidecars and no asset
    directory. The engineering is making the file *demonstrably* the model
    the engine simulated, and it is three things:

    * **The solved keyframe.** ``build_model`` deliberately builds at the
      configuration where each joint's connector frames coincide, so that
      the solved pose is derived and checkable rather than assumed
      (ADR-062). ``to_xml()`` writes no keyframe, so a stock load opens the
      mechanism folded up -- 61 mm out of pose on the four-bar, and it
      looks like a model rather than an error. This adds one, named
      ``solved``, **on a copy of the spec**: a script carrying both
      ``api.dynamics`` and ``api.mjcf`` must not have its simulation's
      numbers moved by an export, and a copy makes that structural rather
      than careful.
    * **The verification.** The file is reloaded and diffed against the
      model it came from, field by field, counts first, and refused if
      anything exceeds the tolerances phase 0 measured. The OCCT
      comparison is re-run against the *reloaded* model rather than the
      original, because the claim being sold is about the file.
    * **``explicitinertial``.** It is already set for other reasons; this
      asserts it, because the whole differentiator rides on it and its
      absence is silent. Measured: without it a body with a collision geom
      loads with inertia inferred from the geom and says nothing.

    **No arithmetic happens here.** The spec is already SI, ``to_xml()``
    converts nothing, and ``qpos_solved`` is already in MuJoCo's
    coordinates -- so there is no number for a second unit-conversion site
    to appear in, which is the structural answer to hazard 1 rather than a
    promise to be careful. The only division in this function is the one
    inside :func:`_field_drift`, which is dimensionless by construction.

    ``observations`` are :func:`observation_records`, added as MJCF
    ``<sensor>`` elements to the same copy the keyframe goes on (M6). They
    are what makes the file *readable as a task*: stock MuJoCo computes the
    observation vector and the bundle names the channels, so no Cadex code
    is on the path between the mechanism and a trainer's array.

    Adding them does not weaken anything above. M6 phase 0 measured what a
    sensor costs the simulation -- 500 steps with four of them give ``qpos``
    bit-identical to the same model without, exactly zero -- so "the
    exported file is the model the engine simulated" survives the addition
    rather than being quietly re-scoped by it. :func:`_verify_exported_sensors`
    re-takes that as a check on every export rather than trusting the
    measurement.

    Returns ``{"xml": bytes, "evidence": {...}}``.
    """

    mujoco = _mujoco_module()
    spec = built["spec"]
    model = built["model"]
    qpos = [float(value) for value in built["qpos_solved"]]

    _verify_explicit_inertia(spec, context=context)

    exported = spec.copy()
    _add_observation_sensors(mujoco, exported, observations)
    exported.add_key(name=MJCF_KEYFRAME_NAME, qpos=list(qpos))
    # The copy's own compiled model, kept: it is the only thing that has
    # both the sensors and the engine's own numbers, so it is what the
    # reload's ``sensordata`` is compared against below. Every other
    # comparison in this function stays against ``built["model"]`` -- the
    # model the engine actually simulated -- because that is the claim M5
    # sells and a re-compile would be a weaker one.
    with_sensors = exported.compile()
    xml = exported.to_xml().encode("utf-8")
    if len(xml) > MAXIMUM_MJCF_BYTES:
        raise DynamicsError(
            f"The MJCF model for {context} requires {len(xml)} bytes; the "
            f"accepted maximum is {MAXIMUM_MJCF_BYTES}.",
            reason="mjcf_too_large",
            correction=(
                "Collision meshes are written into the file itself, at about "
                "50 bytes a vertex. Raise the collision deflection, or use "
                "primitive collision shapes for the parts that do not need a "
                "mesh."
            ),
            observed={"bytes": len(xml), "maximum": MAXIMUM_MJCF_BYTES},
        )

    reloaded = mujoco.MjModel.from_xml_string(xml.decode("utf-8"))
    _verify_exported_counts(reloaded, model, context=context)
    worst_field, worst_field_name = _verify_exported_fields(
        reloaded, model, context=context
    )
    # The exactness claim, re-taken on the file rather than on the model it
    # came from: this compares the reloaded body inertias against the
    # numbers OCCT produced, not against what MuJoCo compiled a moment ago.
    worst_inertia = _verify_compiled_inertia(
        mujoco,
        reloaded,
        built["inertials"],
        built["tree"],
        mass_tolerance=MJCF_MASS_TOLERANCE,
        inertia_tolerance=MJCF_INERTIA_TOLERANCE,
        subject="The exported MJCF",
        reason="mjcf_lost_inertia",
        correction=(
            "MuJoCo's XML writer emits about six significant figures and has "
            "no precision setting. An inertia that moved by more than that "
            "means something rewrote it, not that it was rounded."
        ),
    )
    worst_mass = _field_drift(model.body_mass, reloaded.body_mass)
    worst_pose_mm = _verify_exported_pose(mujoco, reloaded, model, qpos, context=context)
    worst_sensor = _verify_exported_sensors(
        mujoco, reloaded, with_sensors, observations, context=context
    )

    tree = built["tree"]
    return {
        "xml": xml,
        "evidence": {
            "bytes": len(xml),
            "keyframe": MJCF_KEYFRAME_NAME,
            "keyframe_count": int(reloaded.nkey),
            "body_count": int(reloaded.nbody),
            "joint_count": int(reloaded.njnt),
            "geom_count": int(reloaded.ngeom),
            "mesh_count": int(reloaded.nmesh),
            "equality_count": int(reloaded.neq),
            "actuator_count": int(reloaded.nu),
            "coordinate_count": int(reloaded.nq),
            "degree_of_freedom_count": int(reloaded.nv),
            "component_outputs": [str(body["name"]) for body in tree["bodies"]],
            # The three numbers the exit criterion is stated against, and
            # the bound each was checked at. Reported rather than merely
            # asserted: "within tolerance" is not a fact anyone can act on
            # without knowing how much of it was used.
            "worst_mass_rel_error": worst_mass,
            "worst_inertia_rel_error": worst_inertia,
            "worst_field_rel_error": worst_field,
            "worst_field": worst_field_name,
            "worst_pose_error_mm": worst_pose_mm,
            # M6: how many channels the file carries and how far the worst
            # one moved through it. Zero when the export declares none, so
            # an ``api.mjcf`` with no observations reads exactly as it did.
            "sensor_count": int(reloaded.nsensor),
            "sensor_value_count": int(reloaded.nsensordata),
            "observation_channels": [
                str(name)
                for record in observations
                for name in record["channels"]
            ],
            "worst_sensor_rel_error": worst_sensor,
            "mass_tolerance": MJCF_MASS_TOLERANCE,
            "inertia_tolerance": MJCF_INERTIA_TOLERANCE,
            "field_tolerance": MJCF_FIELD_TOLERANCE,
            "pose_tolerance_mm": MJCF_POSE_TOLERANCE_MM,
            # Hazard 3, made legible exactly as the trace makes it (M3):
            # an exported file's bytes are in no project digest, so a MuJoCo
            # version bump changes every one of them silently. Until that
            # decision is taken -- ADR-064 routes it to main, because the
            # digest code is shared with the kinematics trace -- the file at
            # least says which MuJoCo wrote it.
            "mujoco_version": str(built["mujoco_version"]),
        },
    }


def _verify_explicit_inertia(spec: Any, *, context: str) -> None:
    """Every body states its own inertia, rather than letting one be guessed.

    A flag is a promise about a default, and this is the promise M5 cannot
    take on trust: with ``explicitinertial`` off, ``to_xml()`` omits the
    ``<inertial>`` element entirely. Measured on mujoco 3.10.0, a body with
    no collision geom then makes the file unloadable -- loud, and survivable
    -- while a body that has one loads with inertia inferred from the geom
    instead of from OCCT, which is the silent failure this whole slice
    exists to avoid.
    """

    for body in list(spec.bodies):
        name = str(body.name)
        if name == "world":
            continue
        if not bool(body.explicitinertial):
            raise DynamicsError(
                f"Body {name!r} in {context} does not carry an explicit "
                "inertial, so an exported MJCF would not contain its mass "
                "properties.",
                reason="mjcf_inertia_not_explicit",
                correction=(
                    "build_model sets explicitinertial on every body. Exact "
                    "OCCT inertia is what an exported model is for, and "
                    "without the flag MuJoCo omits it from the file."
                ),
                observed={"body": name},
            )


def _verify_exported_counts(reloaded: Any, model: Any, *, context: str) -> None:
    """The file describes a model of the same shape, before any number is."""

    for field in _MJCF_COUNT_FIELDS:
        here = int(getattr(model, field))
        there = int(getattr(reloaded, field))
        if here != there:
            raise DynamicsError(
                f"The MJCF exported for {context} reloads as a different "
                f"model: {field} is {there}, not {here}.",
                reason="mjcf_shape_changed",
                observed={"field": field, "expected": here, "observed": there},
            )


def _verify_exported_fields(
    reloaded: Any, model: Any, *, context: str
) -> tuple[float, str]:
    """Field by field, at the tolerance phase 0 measured.

    Returns the worst drift and the field it was on, which is the number
    the evidence reports -- an export that quietly consumed nine tenths of
    its tolerance is worth being able to see before it consumes the tenth.
    """

    worst = 0.0
    worst_field = ""
    for field in _MJCF_MODEL_FIELDS + tuple(
        f"opt.{name}" for name in _MJCF_OPTION_FIELDS
    ):
        if field.startswith("opt."):
            here = getattr(model.opt, field[4:])
            there = getattr(reloaded.opt, field[4:])
            # Solver settings are not rounded by the writer, they are
            # written or lost; anything but equality is a changed solver.
            if _flattened(here) != _flattened(there):
                raise DynamicsError(
                    f"The MJCF exported for {context} does not preserve "
                    f"{field}: the file would integrate differently from the "
                    "engine that wrote it.",
                    reason="mjcf_option_changed",
                    observed={
                        "field": field,
                        "expected": _flattened(here),
                        "observed": _flattened(there),
                    },
                )
            continue
        drift = _field_drift(getattr(model, field), getattr(reloaded, field))
        if drift > worst:
            worst, worst_field = drift, field
        if drift > MJCF_FIELD_TOLERANCE:
            raise DynamicsError(
                f"The MJCF exported for {context} changed {field} by "
                f"{drift:.6g} relative; the accepted maximum is "
                f"{MJCF_FIELD_TOLERANCE:g}.",
                reason="mjcf_field_drift",
                correction=(
                    "MuJoCo's XML writer emits about six significant figures "
                    "and has no precision setting, so a drift this large is "
                    "not rounding."
                ),
                observed={"field": field, "drift": drift},
            )
    return worst, worst_field


def _verify_exported_pose(
    mujoco: Any,
    reloaded: Any,
    model: Any,
    qpos: Sequence[float],
    *,
    context: str,
) -> float:
    """The file opens where the engine left the mechanism.

    Everything above compares numbers in a model; this compares *where the
    parts are*, which is the only form of the claim a person can check by
    looking. It resets the reloaded model to its own ``solved`` keyframe
    rather than to the qpos it was handed, so a keyframe that failed to
    survive the file is caught here rather than assumed away.
    """

    key = mujoco.mj_name2id(reloaded, mujoco.mjtObj.mjOBJ_KEY, MJCF_KEYFRAME_NAME)
    if key < 0:
        raise DynamicsError(
            f"The MJCF exported for {context} carries no {MJCF_KEYFRAME_NAME!r} "
            "keyframe, so it would open at the pose where every joint's "
            "connector frames coincide rather than at the solved one.",
            reason="mjcf_keyframe_missing",
            observed={"keyframe": MJCF_KEYFRAME_NAME},
        )
    there = mujoco.MjData(reloaded)
    mujoco.mj_resetDataKeyframe(reloaded, there, key)
    mujoco.mj_forward(reloaded, there)
    here = mujoco.MjData(model)
    here.qpos[:] = list(qpos)
    mujoco.mj_forward(model, here)
    worst_m = max(
        (
            abs(a - b)
            for a, b in zip(_flattened(here.xpos), _flattened(there.xpos))
        ),
        default=0.0,
    )
    worst_mm = length_mm(worst_m)
    if worst_mm > MJCF_POSE_TOLERANCE_MM:
        raise DynamicsError(
            f"The MJCF exported for {context} opens {worst_mm:.6g} mm away "
            f"from the solved pose; the accepted maximum is "
            f"{MJCF_POSE_TOLERANCE_MM:g} mm.",
            reason="mjcf_pose_drift",
            correction=(
                "The exported keyframe is what puts the mechanism back where "
                "the assembly solver left it. A drift this large means the "
                "keyframe is describing a different configuration."
            ),
            observed={"pose_error_mm": worst_mm},
        )
    return worst_mm


def _verify_solver_flags(mujoco: Any, model: Any) -> None:
    """The determinism flags survived the compile, and nothing else joined.

    Set on the spec above; asserted on the *compiled* model here, which is
    the assertion that survives a MuJoCo release changing what a spec field
    means -- the lesson ``balanceinertia`` charged M2 for. The equality is
    exact rather than a bit test on purpose: a flag we did not ask for
    arriving as a new default is exactly as digest-moving as one of ours
    going missing, and this is the only place that would notice.
    """

    integrator = int(model.opt.integrator)
    expected = int(mujoco.mjtIntegrator.mjINT_IMPLICITFAST)
    if integrator != expected:
        raise DynamicsError(
            f"The compiled model integrates with {integrator} where this "
            f"translator asked for implicitfast ({expected}).",
            reason="solver_flags_changed",
            correction=(
                "The integrator is a measured choice: Euler gains 51% of a "
                "tumbling part's kinetic energy over twenty seconds. Re-measure "
                "before moving it."
            ),
            observed={"integrator": integrator},
        )
    island = int(mujoco.mjtDisableBit.mjDSBL_ISLAND)
    disable = int(model.opt.disableflags)
    enable = int(model.opt.enableflags)
    if disable != island or enable != 0:
        raise DynamicsError(
            "The compiled model's solver flags are not the ones this "
            f"translator set: disableflags={disable}, enableflags={enable}, "
            f"expected {island} and 0.",
            reason="solver_flags_changed",
            correction=(
                "Islands are disabled and sleep is off so a trace digest "
                "means the same thing on every machine. A MuJoCo upgrade "
                "that changes a default lands here; re-measure both ways "
                "and record the answer before moving the flag."
            ),
            observed={"disableflags": disable, "enableflags": enable},
        )


def _verify_actuator_flags(
    mujoco: Any, model: Any, actuators: Sequence[Mapping[str, Any]]
) -> None:
    """Every actuator compiled to the thing the translator asked for.

    Set on the spec; asserted on the *compiled* model, which is the
    assertion that survives a MuJoCo release changing what a spec field
    means -- the lesson ``balanceinertia`` charged M2 for, and the same
    argument ``_verify_solver_flags`` makes about the solver's own flags.

    Three things are checked and each has a measured reason. The gear,
    because at anything but one ``ctrl`` addresses ``gear · q`` and every
    setpoint in the run means something else. ``ctrllimited``, because a
    control range nobody asked for would clamp a formula silently. And the
    gain and bias parameters, because they *are* the closed loop: a ``kp``
    in the wrong slot is a servo that does not servo.
    """

    for index, record in enumerate(actuators):
        actuator_id = mujoco.mj_name2id(
            model, mujoco.mjtObj.mjOBJ_ACTUATOR, str(record["mujoco_actuator"])
        )
        if actuator_id < 0:
            raise DynamicsError(
                f"The compiled model has no actuator named "
                f"{record['mujoco_actuator']!r}.",
                reason="actuator_flags_changed",
                observed={"actuator": str(record["mujoco_actuator"])},
            )
        gear = [float(value) for value in model.actuator_gear[actuator_id]]
        if gear != [1.0, 0.0, 0.0, 0.0, 0.0, 0.0]:
            raise DynamicsError(
                f"The compiled model gives actuator "
                f"{record['mujoco_actuator']!r} a gear of {gear}.",
                reason="actuator_flags_changed",
                correction=(
                    "The gear is pinned at one because MuJoCo's ctrl addresses "
                    "gear times the joint coordinate, so any other value "
                    "silently rescales every setpoint in the run."
                ),
                observed={"actuator": str(record["mujoco_actuator"]), "gear": gear},
            )
        if bool(model.actuator_ctrllimited[actuator_id]):
            raise DynamicsError(
                f"The compiled model clamps actuator "
                f"{record['mujoco_actuator']!r}'s control range.",
                reason="actuator_flags_changed",
                correction=(
                    "The control is the formula the script wrote; an effort "
                    "limit is what bounds what the motor can do about it."
                ),
                observed={"actuator": str(record["mujoco_actuator"])},
            )
        limited = bool(model.actuator_forcelimited[actuator_id])
        if limited != (record["effort_limit_si"] is not None):
            raise DynamicsError(
                f"Actuator {record['mujoco_actuator']!r} compiled with "
                f"forcelimited={limited}.",
                reason="actuator_flags_changed",
                observed={"actuator": str(record["mujoco_actuator"])},
            )
        if record["effort_limit_si"] is not None:
            expected = float(record["effort_limit_si"])
            compiled = [
                float(value) for value in model.actuator_forcerange[actuator_id]
            ]
            if compiled != [-expected, expected]:
                raise DynamicsError(
                    f"Actuator {record['mujoco_actuator']!r} compiled with a "
                    f"force range of {compiled}, not {[-expected, expected]}.",
                    reason="actuator_flags_changed",
                    observed={"actuator": str(record["mujoco_actuator"])},
                )
        kind = str(record["kind"])
        gain = [float(value) for value in model.actuator_gainprm[actuator_id][:3]]
        bias = [float(value) for value in model.actuator_biasprm[actuator_id][:3]]
        stiffness = float(record["stiffness_si"] or 0.0)
        damping = float(record["damping_si"] or 0.0)
        expected_gain, expected_bias = {
            "motor": ([1.0, 0.0, 0.0], [0.0, 0.0, 0.0]),
            "position": ([stiffness, 0.0, 0.0], [0.0, -stiffness, -damping]),
            "velocity": ([damping, 0.0, 0.0], [0.0, 0.0, -damping]),
        }[kind]
        if gain != expected_gain or bias != expected_bias:
            raise DynamicsError(
                f"Actuator {record['mujoco_actuator']!r} is a {kind} actuator "
                f"whose compiled gain is {gain} and bias {bias}; this "
                f"translator asked for {expected_gain} and {expected_bias}.",
                reason="actuator_flags_changed",
                correction=(
                    "A position actuator's gain and bias are the PD loop "
                    "itself. Re-measure what set_to_position writes before "
                    "moving this."
                ),
                observed={
                    "actuator": str(record["mujoco_actuator"]),
                    "index": index,
                    "gainprm": gain,
                    "biasprm": bias,
                },
            )


def _verify_compiled_inertia(
    mujoco: Any,
    model: Any,
    inertials: Mapping[str, Mapping[str, Any]],
    tree: Mapping[str, Any],
    *,
    mass_tolerance: float = 1.0e-12,
    inertia_tolerance: float = 1.0e-9,
    subject: str = "MuJoCo's compiler",
    reason: str = "compiler_rewrote_inertia",
    correction: str = (
        "balanceinertia, boundinertia and boundmass must stay off. "
        "Exact OCCT inertia is what this model is for."
    ),
) -> float:
    """The compiler may not have touched the numbers we gave it.

    ``balanceinertia`` is asserted off above; this asserts the *effect* of
    it being off, which is the assertion that survives a MuJoCo upgrade
    changing a default. It compares the compiled principal moments against
    the ones computed from OCCT, per body, and refuses a model whose inertia
    was rewritten -- silently rewritten exact inertia is the failure this
    whole slice exists to avoid.

    The tolerances are parameters because there is a second caller with a
    different one and the same question (M5 phase 1): a model reloaded from
    an exported MJCF carries the *same* OCCT inertia through a formatter
    that writes six significant figures, so it lands 2.4e-6 out rather than
    1e-9 out. Making that a second copy of this function is how the two
    would eventually stop asking the same thing. Returns the worst inertia
    drift observed, which is what the export records as evidence.
    """

    worst = 0.0
    for body in tree["bodies"]:
        name = str(body["name"])
        body_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, name)
        expected = inertials[name]
        mass = float(model.body_mass[body_id])
        if abs(mass - float(expected["mass_kg"])) > mass_tolerance * max(
            1.0, abs(float(expected["mass_kg"]))
        ):
            raise DynamicsError(
                f"{subject} changed body {name!r}'s mass from "
                f"{expected['mass_kg']:.12g} to {mass:.12g} kg.",
                reason=reason,
                observed={"body": name},
            )
        compiled = sorted(float(value) for value in model.body_inertia[body_id])
        principal = list(expected["principal_inertia_kg_m2"])
        scale = max(principal[2], 1.0e-30)
        drift = max(
            abs(compiled[index] - principal[index]) / scale for index in range(3)
        )
        worst = max(worst, drift)
        if drift > inertia_tolerance:
            raise DynamicsError(
                f"{subject} rewrote body {name!r}'s inertia: asked for "
                f"{principal}, compiled {compiled} kg·m².",
                reason=reason,
                correction=correction,
                observed={"body": name, "asked": principal, "compiled": compiled},
            )
    return worst


def _solved_joint_values(
    tree: Mapping[str, Any], placements: Mapping[str, Sequence[float]]
) -> dict[str, list[float]]:
    """Each tree joint's coordinate at the solved pose, by joint output name.

    Derived by inversion from the solved placements rather than read back
    out of the model it is about to be checked against, and computed before
    the model is compiled because the coupling equalities need it too.
    """

    values: dict[str, list[float]] = {}
    for body in tree["bodies"]:
        if body["attachment"] == "free" or not body["mujoco_joints"]:
            continue
        transform = joint_transform(
            placements[str(body["parent"])],
            body["parent_local_matrix"],
            placements[str(body["name"])],
            body["child_local_matrix"],
        )
        coordinates = joint_coordinates(
            str(body["joint_kind"]), transform, context=f"joint {body['joint']!r}"
        )
        if (
            coordinates["residual_mm"] > CLOSURE_RESIDUAL_MM
            or coordinates["residual_radians"] > CLOSURE_RESIDUAL_RADIANS
        ):
            raise DynamicsError(
                f"Joint {body['joint']!r} does not hold in the solved assembly: "
                f"its connector frames are {coordinates['residual_mm']:.6g} mm "
                f"and {coordinates['residual_radians']:.6g} rad apart in "
                f"directions a {body['joint_kind']} joint cannot move.",
                reason="joint_residual",
                correction=(
                    "The solved placements and the connector frames disagree. "
                    "Re-solve the assembly, and check that the joint's two "
                    "connectors select the geometry they were meant to."
                ),
                observed={
                    "joint": str(body["joint"]),
                    "residual_mm": coordinates["residual_mm"],
                    "residual_radians": coordinates["residual_radians"],
                },
            )
        values[str(body["joint"])] = list(coordinates["values"])
    return values


def _solved_qpos(
    mujoco: Any,
    model: Any,
    tree: Mapping[str, Any],
    placements: Mapping[str, Sequence[float]],
    joint_records: Sequence[Mapping[str, Any]],
    solved_values: Mapping[str, Sequence[float]],
) -> list[float]:
    """The configuration that reproduces FreeCAD's solved placements."""

    qpos = [float(value) for value in model.qpos0]
    addresses = {
        str(record["mujoco_joint"]): int(
            model.jnt_qposadr[
                mujoco.mj_name2id(
                    model, mujoco.mjtObj.mjOBJ_JOINT, str(record["mujoco_joint"])
                )
            ]
        )
        for record in joint_records
    }
    for body in tree["bodies"]:
        name = str(body["name"])
        if body["attachment"] == "free":
            address = addresses[f"{name}/free"]
            frame = placements[name]
            qpos[address : address + 3] = vector_m(matrix_translation_mm(frame))
            qpos[address + 3 : address + 7] = quaternion_wxyz_from_matrix(frame)
            continue
        if not body["mujoco_joints"]:
            continue
        values = list(solved_values[str(body["joint"])])
        if str(body["joint_kind"]) == "cylindrical":
            # The tree adds slide then hinge, and joint_coordinates returns
            # them in that order.
            for mujoco_type, value in zip(("slide", "hinge"), values, strict=True):
                address = addresses[f"{body['joint']}/{mujoco_type}"]
                qpos[address] = value
        elif values:
            address = addresses[str(body["joint"])]
            qpos[address : address + len(values)] = values
    return qpos


def _axis_normalised(axis: Sequence[float], *, context: str) -> list[float]:
    values = [float(item) for item in axis]
    magnitude = math.sqrt(sum(item * item for item in values))
    if magnitude <= _TINY:
        raise DynamicsError(
            f"{context} has no direction: its connector frame +Z is degenerate.",
            reason="degenerate_axis",
            correction=(
                "Select an edge, circular face or cylindrical face whose axis "
                "FreeCAD can derive, or give the connector an explicit offset."
            ),
            observed={"context": context},
        )
    return [item / magnitude for item in values]


# ---------------------------------------------------------------------------
# M6 -- a task is part of the script.
#
# A model is not a task. Training needs an observation space, an action
# space, a reward, a termination rule, an episode length and domain
# randomisation -- none of which is geometry, all of which is *data*, and the
# script is already the sole source of truth for data.
#
# Three decisions shape everything below, and each was measured in phase 0
# rather than chosen:
#
# * **MuJoCo computes the observation vector.** A channel is an MJCF
#   ``<sensor>`` element, so a trainer reads ``data.sensordata`` and no Cadex
#   code is anywhere on the path between the mechanism and the array. What
#   this module contributes is the *naming*: which channel is which slice,
#   what unit it is in, and what to multiply it by.
# * **Component channels are ``xbody`` channels.** MuJoCo's frame sensors
#   accept an ``objtype`` that a reader would take for one thing and that is
#   two: ``body`` is the frame the principal axes of inertia define, and
#   ``xbody`` is the frame the assembly solver placed. Phase 0 measured them
#   a half turn apart on a plain box.
# * **The action bound is derived or refused.** A policy needs a bounded
#   action space; the model M4 builds has none. Where the mechanism states a
#   bound -- a two-sided joint limit, an effort limit -- that bound is the
#   action range. Where it does not, this refuses, because the alternative is
#   inventing a mechanical limit and a one-sided limit's synthetic endpoint
#   is worth a hundred turns.
# ---------------------------------------------------------------------------


#: How many scalar channels one task may observe. A vector channel expands
#: to its components, so this counts what a reward formula could name rather
#: than what the script wrote. Sized for comprehensibility rather than for
#: bytes: phase 0 measured a sensor at 54 XML bytes, so even the ceiling is
#: under 4 KB of file, and a task naming more than this many quantities is
#: one nobody can read.
MAXIMUM_OBSERVATION_CHANNELS = 64

#: Reward terms, termination rules and randomisation entries. Each is a
#: whitelisted expression or a field write evaluated once per control step,
#: so the cost is real but small; these bound the *description* rather than
#: the arithmetic.
MAXIMUM_REWARD_TERMS = 16
MAXIMUM_TERMINATION_TERMS = 8
MAXIMUM_RANDOMISATION_ENTRIES = 32

#: Control steps in one episode. At the 50 Hz the surface encourages this is
#: over an hour of simulated time, which is far past any episode a person
#: designs; what it really bounds is a typo in ``episode_seconds``.
MAXIMUM_EPISODE_STEPS = 200_000

#: The bundle's own byte cap. A task is names, numbers and short
#: expressions -- no geometry -- so this is three orders of magnitude below
#: ``MAXIMUM_MJCF_BYTES`` on purpose: a task file approaching a megabyte is
#: not a task, it is a mistake with a loop in it.
MAXIMUM_TASK_BYTES = 1024 * 1024

#: The schema the bundle declares, and the version a reader checks first.
TASK_SCHEMA = "cadex-training-task-v1"

#: What the observation vector may contain, script word by script word.
#:
#: Each row maps a word a script writes to an ``mjtSensor``, the MuJoCo
#: object it attaches to, its dimension, the suffixes a vector channel
#: expands to, and the unit its value reaches the surface in. ``units`` is
#: keyed on the joint coordinate where the unit depends on one -- a joint
#: position is degrees on a hinge and millimetres on a slider -- and on
#: ``None`` where it does not.
#:
#: Deliberately small. ``touch`` and ``accelerometer`` are the obvious next
#: rows and both need a *site*, which is a placement the assembly graph does
#: not carry; they are named here as deferred rather than half-built, so a
#: reader looking for them finds the reason instead of the absence.
OBSERVATION_KINDS: dict[str, dict[str, Any]] = {
    "position": {
        "sensor": "mjSENS_JOINTPOS",
        "target": "joint",
        "objtype": "mjOBJ_JOINT",
        "dim": 1,
        "suffixes": ("",),
        "units": {"angular": ("deg", angle_degrees), "linear": ("mm", length_mm)},
    },
    "velocity": {
        "sensor": "mjSENS_JOINTVEL",
        "target": "joint",
        "objtype": "mjOBJ_JOINT",
        "dim": 1,
        "suffixes": ("",),
        "units": {
            "angular": ("deg/s", angle_degrees),
            "linear": ("mm/s", speed_mm_per_s),
        },
    },
    "actuator_force": {
        "sensor": "mjSENS_ACTUATORFRC",
        "target": "actuator",
        "objtype": "mjOBJ_ACTUATOR",
        "dim": 1,
        "suffixes": ("",),
        "units": {"angular": ("nmm", torque_nmm), "linear": ("n", float)},
    },
    # The four frame channels. ``xbody`` throughout, which is the phase 0
    # finding: ``body`` would report the inertial frame, and a reward that
    # named a position would silently be given the centre of mass.
    "component_position": {
        "sensor": "mjSENS_FRAMEPOS",
        "target": "component",
        "objtype": "mjOBJ_XBODY",
        "dim": 3,
        "suffixes": ("_x", "_y", "_z"),
        "units": {None: ("mm", length_mm)},
    },
    "component_orientation": {
        "sensor": "mjSENS_FRAMEQUAT",
        "target": "component",
        "objtype": "mjOBJ_XBODY",
        "dim": 4,
        "suffixes": ("_qw", "_qx", "_qy", "_qz"),
        # A unit quaternion is dimensionless, so the scale is exactly one --
        # stated as a row rather than special-cased, so that every channel
        # in the bundle carries a scale and a reader never has to ask
        # whether a missing one means "1" or "forgot".
        "units": {None: ("quat", float)},
    },
    "component_linear_velocity": {
        "sensor": "mjSENS_FRAMELINVEL",
        "target": "component",
        "objtype": "mjOBJ_XBODY",
        "dim": 3,
        "suffixes": ("_x", "_y", "_z"),
        "units": {None: ("mm/s", speed_mm_per_s)},
    },
    "component_angular_velocity": {
        "sensor": "mjSENS_FRAMEANGVEL",
        "target": "component",
        "objtype": "mjOBJ_XBODY",
        "dim": 3,
        "suffixes": ("_x", "_y", "_z"),
        "units": {None: ("deg/s", angle_degrees)},
    },
    # ``subtreecom`` is a mass-weighted quantity over a subtree rather than
    # a frame, so the body/xbody distinction does not arise for it and
    # ``mjOBJ_BODY`` is the only object type it takes.
    "centre_of_mass": {
        "sensor": "mjSENS_SUBTREECOM",
        "target": "component",
        "objtype": "mjOBJ_BODY",
        "dim": 3,
        "suffixes": ("_x", "_y", "_z"),
        "units": {None: ("mm", length_mm)},
    },
}

#: Observation kinds named here on purpose, with the reason they are not
#: rows above. A refusal that says "unknown kind" about something MuJoCo
#: plainly supports sends a reader looking for a typo.
DEFERRED_OBSERVATION_KINDS = {
    "touch": (
        "needs a site with a size, which is a placement the assembly graph "
        "does not carry: a touch sensor measures contact normal force inside "
        "a volume somebody has to draw"
    ),
    "accelerometer": (
        "needs a site to be mounted on, for the same reason. A component's "
        "acceleration is also not a quantity MuJoCo exposes per body"
    ),
    "contact_force": (
        "reports per-contact rather than per-body, so its dimension depends "
        "on what is touching what at the instant it is read -- which is not "
        "a fixed-width observation channel"
    ),
}

#: What a randomisation entry may vary, and every compiled-model field one
#: draw has to move.
#:
#: ``mass`` is the row that is not obvious, and phase 0 is why: MuJoCo keeps
#: ``body_mass`` and ``body_inertia`` in independent arrays and derives
#: ``body_subtreemass`` from the first at ``mj_setConst``. Scaling the mass
#: alone leaves a body whose rotational inertia no longer matches it -- not
#: a heavier part, a part whose density depends on which equation you ask.
#: One draw therefore scales both, which is exactly what changing the
#: density of a fixed shape means, and is how :func:`mass_kg` and
#: :func:`inertia_kg_m2` produced the two numbers in the first place: each
#: linear in the density.
RANDOMISATION_TARGETS: dict[str, dict[str, Any]] = {
    "mass": {"on": "component", "fields": ("body_mass", "body_inertia"), "positive": True},
    "damping": {"on": "joint", "fields": ("dof_damping",), "positive": False},
    "armature": {"on": "joint", "fields": ("dof_armature",), "positive": False},
    "friction_loss": {"on": "joint", "fields": ("dof_frictionloss",), "positive": False},
}

#: Everything a reward or termination expression may name beyond the
#: observation channels themselves. ``_CONTROL_GLOBALS`` plus the three a
#: reward actually wants: ``exp`` for a shaped bell, ``sqrt`` for a distance,
#: ``tanh`` for a bounded term.
#:
#: This is deliberately *not* the control whitelist widened. ``api.motion``
#: renders its formula back to Ondsel, which has no ``tanh``, so a shared
#: set would export an expression Ondsel cannot read; the extension point is
#: a parameter, not a bigger common set.
_REWARD_GLOBALS: dict[str, Any] = {
    **_CONTROL_GLOBALS,
    "exp": math.exp,
    "sqrt": math.sqrt,
    "tanh": math.tanh,
}

#: The sorted function names the bundle ships, so that the reference runner's
#: own evaluator can be asserted equal to this rather than kept equal to it
#: by attention. Two evaluators is a place for a whitelist to drift, and this
#: codebase keeps catching drift by writing the second copy down; here it
#: costs one array.
REWARD_FUNCTIONS = tuple(
    sorted(
        name
        for name, value in _REWARD_GLOBALS.items()
        if callable(value) and not name.startswith("__")
    )
)


def _observation_unit(kind: str, motion_type: str | None) -> tuple[str, float]:
    """One channel's surface unit and the number a trainer multiplies by.

    The scale is the conversion applied to 1.0 -- a single number computed
    here and emitted into the bundle, so the trainer multiplies rather than
    converts. That is hazard 1's answer on this boundary: a reward formula
    is evaluated outside this process, and a conversion that has to be
    *performed* over there is a conversion that can be performed wrongly.
    """

    units = OBSERVATION_KINDS[kind]["units"]
    entry = units.get(motion_type if motion_type in units else None)
    if entry is None:
        raise DynamicsError(
            f"A {kind!r} observation has no unit for a {motion_type} coordinate.",
            reason="malformed_observation",
            observed={"kind": kind, "motion_type": motion_type},
        )
    unit, convert = entry
    return str(unit), float(convert(1.0))


def observation_records(
    entries: Sequence[Mapping[str, Any]],
    tree: Mapping[str, Any],
    joint_records: Sequence[Mapping[str, Any]],
    actuators: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Every declared channel, resolved to something the model really carries.

    The same shape and the same refusals as :func:`actuator_records`, for
    the same reason: a joint the spanning forest turned into a loop closure,
    a suppressed joint and a joint from some other assembly are all
    authoring mistakes, and only the tree can say which one this is.

    Two things happen here that do not happen for an actuator. A **vector
    channel expands** to suffixed scalar names -- ``name="hand"`` on a
    position gives ``hand_x``, ``hand_y``, ``hand_z`` -- because reward
    formulas do arithmetic on scalars, and the set of names a formula may
    use has to be enumerable for every one of them to be checkable. And a
    **duplicate name is refused**, including one produced by expansion: two
    channels called the same thing make a reward that reads correctly and
    means whichever one came second.
    """

    table = _coordinate_table(tree, joint_records)
    refusals = _coordinate_refusals(tree)
    bodies = [str(body["name"]) for body in tree["bodies"]]
    by_actuator = {
        (str(record["joint"]), str(record["motion_type"]), str(record["kind"])): record
        for record in actuators
    }
    records: list[dict[str, Any]] = []
    taken: dict[str, str] = {}
    for index, entry in enumerate(entries):
        kind = str(entry.get("kind") or "")
        name = str(entry.get("name") or "")
        row = OBSERVATION_KINDS.get(kind)
        if row is None:
            deferred = DEFERRED_OBSERVATION_KINDS.get(kind)
            raise DynamicsError(
                f"Observation {name!r} asks for {kind!r}, which "
                + (
                    f"{deferred}."
                    if deferred
                    else "is not an observation kind this engine supports."
                ),
                reason="unknown_observation_kind",
                correction=(
                    "The supported kinds are "
                    f"{', '.join(sorted(OBSERVATION_KINDS))}."
                ),
                observed={"kind": kind, "observation": name},
            )
        what = f"observation {name!r}"

        motion_type: str | None = None
        if row["target"] == "joint":
            resolved = _resolve_coordinate(entry, table, refusals, what=what)
            motion_type = str(entry.get("motion_type") or "")
            object_name = str(resolved["mujoco_joint"])
            target = str(entry.get("joint") or "")
        elif row["target"] == "actuator":
            motion_type = str(entry.get("motion_type") or "")
            key = (
                str(entry.get("joint") or ""),
                motion_type,
                str(entry.get("actuator_kind") or ""),
            )
            actuator = by_actuator.get(key)
            if actuator is None:
                raise DynamicsError(
                    f"{what} reads the effort of an actuator this model does "
                    "not carry.",
                    reason="observation_actuator_missing",
                    correction=(
                        "Pass the same assembly.actuator value that was given "
                        "to the api.mjcf this task observes."
                    ),
                    observed={
                        "observation": name,
                        "joint": key[0],
                        "motion_type": key[1],
                        "actuator_kind": key[2],
                        "available": sorted(
                            str(record["mujoco_actuator"]) for record in actuators
                        ),
                    },
                )
            object_name = str(actuator["mujoco_actuator"])
            target = str(entry.get("joint") or "")
        else:
            target = str(entry.get("component") or "")
            if target not in bodies:
                raise DynamicsError(
                    f"{what} reads component {target!r}, which is not a body "
                    "in this assembly's dynamics model.",
                    reason="observation_component_missing",
                    correction=(
                        "Pass the same assembly.component value the assembly "
                        "was built from. A component with no api.body has no "
                        "mass and is not part of the model."
                    ),
                    observed={"observation": name, "component": target,
                              "available": list(bodies)},
                )
            object_name = target

        unit, scale = _observation_unit(kind, motion_type)
        channels = [f"{name}{suffix}" for suffix in row["suffixes"]]
        for channel in channels:
            if channel in taken:
                raise DynamicsError(
                    f"Two observation channels are both called {channel!r}.",
                    reason="duplicate_observation_channel",
                    correction=(
                        "A reward formula names channels, so two with one name "
                        "means whichever was declared second. Rename one. Note "
                        "that a vector channel expands: a component_position "
                        "named 'hand' occupies hand_x, hand_y and hand_z."
                    ),
                    observed={
                        "channel": channel,
                        "observation": name,
                        "conflicts_with": taken[channel],
                    },
                )
            taken[channel] = name
        records.append(
            {
                "name": name,
                "kind": kind,
                "target": target,
                "sensor": str(row["sensor"]),
                "objtype": str(row["objtype"]),
                "object_name": object_name,
                "dim": int(row["dim"]),
                "channels": channels,
                "unit": unit,
                "scale": scale,
                "motion_type": motion_type,
                # The MJCF element's own name. Positional rather than
                # derived from the script's name, because a channel name is
                # authored text and an XML name attribute is an identifier;
                # keeping them separate means a rename cannot collide with
                # anything MuJoCo already carries.
                "mujoco_sensor": f"obs/{index}",
            }
        )
    if len(taken) > MAXIMUM_OBSERVATION_CHANNELS:
        raise DynamicsError(
            f"This task observes {len(taken)} scalar channels; the accepted "
            f"maximum is {MAXIMUM_OBSERVATION_CHANNELS}.",
            reason="too_many_observation_channels",
            correction=(
                "A vector channel counts as its components: a "
                "component_position is three. Observe the quantities the "
                "reward and the policy actually use."
            ),
            observed={"channels": len(taken),
                      "maximum": MAXIMUM_OBSERVATION_CHANNELS},
        )
    return records


def _add_observation_sensors(
    mujoco: Any, spec: Any, observations: Sequence[Mapping[str, Any]]
) -> None:
    """Each channel as one MJCF ``<sensor>`` element, on the exported copy.

    On the *copy*, which is the same structural care the keyframe gets: a
    script carrying both an ``api.dynamics`` and an ``api.mjcf`` must not
    have its simulation's numbers moved by an export, and phase 0's
    inertness measurement is only worth having if nothing can reach the
    simulated spec to test it against.
    """

    for record in observations:
        sensor = spec.add_sensor()
        sensor.name = str(record["mujoco_sensor"])
        sensor.type = getattr(mujoco.mjtSensor, str(record["sensor"]))
        sensor.objtype = getattr(mujoco.mjtObj, str(record["objtype"]))
        sensor.objname = str(record["object_name"])


def _verify_exported_sensors(
    mujoco: Any,
    reloaded: Any,
    with_sensors: Any,
    observations: Sequence[Mapping[str, Any]],
    *,
    context: str,
) -> float:
    """The file's observation vector is the one the engine declared.

    Three claims, in the order that makes a failure legible: the file
    carries the channels that were asked for, each lands at the address and
    width the bundle will record, and the values agree with the engine's own
    compiled model at the tolerance M5 measured.

    The third is the one that matters and the one that is cheap to skip. A
    bundle records ``adr`` and ``dim`` per channel and a trainer slices
    ``sensordata`` with them; an off-by-one there is a policy trained on the
    wrong number, and it looks exactly like a policy that failed to learn.
    """

    expected = int(len(observations))
    if int(reloaded.nsensor) != expected:
        raise DynamicsError(
            f"The MJCF exported for {context} carries {int(reloaded.nsensor)} "
            f"observation channels, not the {expected} that were declared.",
            reason="mjcf_sensor_count",
            observed={"expected": expected, "observed": int(reloaded.nsensor)},
        )
    if not observations:
        return 0.0

    width = sum(int(record["dim"]) for record in observations)
    if int(reloaded.nsensordata) != width:
        raise DynamicsError(
            f"The MJCF exported for {context} reloads with "
            f"{int(reloaded.nsensordata)} observation values, not {width}.",
            reason="mjcf_sensor_width",
            observed={"expected": width, "observed": int(reloaded.nsensordata)},
        )
    for index, record in enumerate(observations):
        name = mujoco.mj_id2name(reloaded, mujoco.mjtObj.mjOBJ_SENSOR, index)
        if str(name) != str(record["mujoco_sensor"]):
            raise DynamicsError(
                f"The MJCF exported for {context} reordered its observation "
                f"channels: slot {index} is {name!r}, not "
                f"{record['mujoco_sensor']!r}.",
                reason="mjcf_sensor_order",
                observed={"index": index, "expected": str(record["mujoco_sensor"]),
                          "observed": str(name)},
            )
        if int(reloaded.sensor_dim[index]) != int(record["dim"]):
            raise DynamicsError(
                f"Observation {record['name']!r} in {context} reloads "
                f"{int(reloaded.sensor_dim[index])} values wide, not "
                f"{int(record['dim'])}.",
                reason="mjcf_sensor_width",
                observed={"observation": str(record["name"]),
                          "expected": int(record["dim"]),
                          "observed": int(reloaded.sensor_dim[index])},
            )

    # The values, at the solved keyframe, against the engine's own compiled
    # model rather than against the reload alone.
    here = mujoco.MjData(with_sensors)
    key_here = mujoco.mj_name2id(
        with_sensors, mujoco.mjtObj.mjOBJ_KEY, MJCF_KEYFRAME_NAME
    )
    mujoco.mj_resetDataKeyframe(with_sensors, here, key_here)
    mujoco.mj_forward(with_sensors, here)
    there = mujoco.MjData(reloaded)
    key_there = mujoco.mj_name2id(
        reloaded, mujoco.mjtObj.mjOBJ_KEY, MJCF_KEYFRAME_NAME
    )
    mujoco.mj_resetDataKeyframe(reloaded, there, key_there)
    mujoco.mj_forward(reloaded, there)
    drift = _field_drift(here.sensordata, there.sensordata)
    if drift > MJCF_FIELD_TOLERANCE:
        raise DynamicsError(
            f"The MJCF exported for {context} changed its observation values "
            f"by {drift:.6g} relative; the accepted maximum is "
            f"{MJCF_FIELD_TOLERANCE:g}.",
            reason="mjcf_sensor_drift",
            correction=(
                "A sensor reads state MuJoCo already computed, so a drift "
                "this large is the state having moved, not the reading."
            ),
            observed={"drift": drift},
        )
    return drift


# ---------------------------------------------------------------------------
# The action space, and the refusals that are the point.
# ---------------------------------------------------------------------------


#: Where an action range may come from, per actuator kind and coordinate:
#: the surface unit the bound is quoted in, the conversion that carries one
#: unit of it into what ``data.ctrl`` reads, and the name of the declaration
#: it is derived from.
#:
#: Note the direction. An observation's ``scale`` converts *out* of MuJoCo;
#: an action's converts *in*, because an action travels the other way. Both
#: are one number in the bundle and the arithmetic on both sides is a
#: multiply, which is the only shape that cannot be performed backwards.
_ACTION_SOURCES = {
    ("motor", "angular"): ("nmm", torque_nm, "torque_limit_nmm"),
    ("motor", "linear"): ("n", float, "force_limit_n"),
    ("position", "angular"): ("deg", angle_radians, "angle_limits_degrees"),
    ("position", "linear"): ("mm", length_m, "length_limits_mm"),
}


def _action_bound(
    record: Mapping[str, Any], joint_limits: Mapping[str, Any] | None, *, what: str
) -> dict[str, Any]:
    """One actuator's action range, derived from the mechanism or refused.

    The whole fork, in one function. A policy needs a bounded action space
    and the model M4 builds has none -- phase 0 measured ``ctrllimited`` as
    FALSE on every actuator -- so the bound is new, and the only defensible
    place to get it is something the mechanism already states:

    * a **motor** is bounded by its effort limit, which is the most a real
      motor can produce and is exactly the number a saturating mechanism
      already sags against;
    * a **position** servo is bounded by its joint's own limits, because a
      setpoint outside them is a command the joint cannot obey.

    Everything else is a refusal with the correction attached, and the two
    that matter are worth naming:

    * a **one-sided** limit. ``_limit_range`` fills the missing endpoint
      from ``_OPEN_ANGLE_MARGIN_RADIANS``, which phase 0 measured at a
      hundred full turns. That number is a solver convenience -- it keeps
      the joint effectively free while still being a declared range -- and
      it is not a mechanical bound. A policy handed it would spend its whole
      action budget in a region the mechanism cannot reach.
    * a **velocity** actuator. Its control is a speed, and nothing in a
      FreeCAD assembly states one: a joint carries position limits, not
      velocity limits. Deriving a speed from an angle needs a time, and
      there is no time in the model to take it from.
    """

    kind = str(record["kind"])
    motion = str(record["motion_type"])
    source = _ACTION_SOURCES.get((kind, motion))
    if source is None:
        raise DynamicsError(
            f"{what} is a {kind} actuator, and its action range cannot be "
            "derived: a velocity command is a speed, and this assembly states "
            "no speed limit anywhere.",
            reason="action_range_underivable",
            correction=(
                "A joint carries position limits, not velocity limits, so "
                "there is no number to bound a speed with and inventing one "
                "would be inventing a mechanism. Drive this coordinate with a "
                "motor actuator, whose range is its torque limit, or with a "
                "position actuator, whose range is the joint's own limits."
            ),
            observed={"actuator": str(record["mujoco_actuator"]), "kind": kind},
        )
    unit, convert, declared = source

    if kind == "motor":
        effort = record.get("effort_limit_si")
        if effort is None:
            raise DynamicsError(
                f"{what} has no effort limit, so its action range cannot be "
                "derived.",
                reason="action_range_underivable",
                correction=(
                    f"Give the actuator {declared}=... -- the most the real "
                    "motor can produce. A policy needs a bounded action space, "
                    "and an unbounded torque is not a motor anybody can build."
                ),
                observed={"actuator": str(record["mujoco_actuator"])},
            )
        # Back to the surface unit the script wrote, so the bundle quotes a
        # number the author would recognise.
        limit = float(record["declared"]["effort_limit"])
        low, high = -limit, limit
    else:
        if joint_limits is None:
            raise DynamicsError(
                f"{what} drives a joint with no limits, so its action range "
                "cannot be derived.",
                reason="action_range_underivable",
                correction=(
                    f"Give the joint {declared} in FreeCAD -- both endpoints. "
                    "A position command outside a joint's travel is not an "
                    "action, and a policy with no bound will spend most of its "
                    "exploration there."
                ),
                observed={"actuator": str(record["mujoco_actuator"])},
            )
        if bool(joint_limits.get("one_sided")):
            raise DynamicsError(
                f"{what} drives a joint whose limit states only one endpoint, "
                "so its action range cannot be derived.",
                reason="action_range_underivable",
                correction=(
                    "The missing endpoint is filled in with a margin worth a "
                    "hundred turns so the solver treats the joint as free. "
                    "That is a convenience, not a mechanical bound, and an "
                    "action range taken from it would be a limit nobody "
                    f"designed. State both endpoints of {declared}."
                ),
                observed={
                    "actuator": str(record["mujoco_actuator"]),
                    "declared": list(joint_limits.get("declared") or []),
                },
            )
        declared_pair = [float(value) for value in joint_limits["declared"]]
        low, high = declared_pair[0], declared_pair[1]

    if not (math.isfinite(low) and math.isfinite(high)) or low >= high:
        raise DynamicsError(
            f"{what} has an empty action range.",
            reason="action_range_underivable",
            observed={"low": low, "high": high},
        )
    return {
        "unit": unit,
        "low": float(low),
        "high": float(high),
        # One unit of the surface quantity, in what ``data.ctrl`` reads.
        "scale": float(convert(1.0)),
        "source": declared,
    }


# ---------------------------------------------------------------------------
# Reward and termination: expressions over the observation namespace.
# ---------------------------------------------------------------------------


def compile_reward(formula: str, *, names: Sequence[str], context: str) -> Any:
    """One reward or termination expression, checked against the channels.

    The API whitelists the expression's *syntax*; this checks its
    *vocabulary* against the channels that actually resolved, which is the
    check the API cannot make -- a vector observation expands to suffixed
    names, and whether ``hand_x`` exists depends on what the model carried.

    Compiled rather than kept as text for the same reason a control formula
    is: an episode evaluates every term at every control step.
    """

    allowed = set(names) | {
        name for name in _REWARD_GLOBALS if not name.startswith("__")
    }
    try:
        tree = ast.parse(str(formula), mode="eval")
    except SyntaxError as exc:
        raise DynamicsError(
            f"{context} is not an expression: {exc}",
            reason="malformed_reward_formula",
            observed={"context": context, "formula": str(formula)},
        ) from exc
    used = sorted(
        {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
    )
    unknown = [name for name in used if name not in allowed]
    if unknown:
        raise DynamicsError(
            f"{context} names {', '.join(repr(name) for name in unknown)}, "
            "which is not an observation channel of this task.",
            reason="reward_names_unknown_channel",
            correction=(
                "A reward may name the observation channels this task "
                "declares and the functions "
                f"{', '.join(REWARD_FUNCTIONS)}. The channels here are "
                f"{', '.join(sorted(names)) or '(none declared)'}. Note that a "
                "vector observation expands: one named 'hand' is hand_x, "
                "hand_y and hand_z rather than 'hand'."
            ),
            observed={"context": context, "unknown": unknown,
                      "channels": sorted(names)},
        )
    return compile(tree, filename="<reward>", mode="eval")


def evaluate_reward(code: Any, values: Mapping[str, float], *, context: str) -> float:
    """One compiled expression against one observation, as a finite number."""

    try:
        value = float(eval(code, _REWARD_GLOBALS, dict(values)))
    except Exception as exc:
        raise DynamicsError(
            f"{context} could not be evaluated: {exc}",
            reason="reward_formula_failed",
            correction=(
                "A reward is arithmetic on the task's observation channels. "
                "Check for a division by zero, a sqrt of a negative, or an "
                "exp that overflowed."
            ),
            observed={"context": context},
        ) from exc
    if not math.isfinite(value):
        raise DynamicsError(
            f"{context} evaluated to {value}.",
            reason="reward_formula_failed",
            correction=(
                "A reward that is not a finite number is not a reward: it "
                "makes every episode incomparable with every other."
            ),
            observed={"context": context},
        )
    return value


# ---------------------------------------------------------------------------
# The task bundle, and the episode that is run from it.
# ---------------------------------------------------------------------------


def _episode_schedule(model: Any, *, control_hz: int, episode_seconds: float,
                      context: str) -> dict[str, Any]:
    """How many solver steps one action lasts, and how many actions an episode.

    The rounding ``api.dynamics`` already does for trace frames, applied to
    control steps: a whole number of solver steps has to land exactly on
    each action boundary, or the last step of an episode integrates a
    different amount of time from the first and two runs at different
    control rates stop being comparable.

    The *actual* rate after rounding is reported rather than the one that
    was asked for, because that is the number the episode really ran at.
    """

    timestep = float(model.opt.timestep)
    interval = 1.0 / float(control_hz)
    steps = int(round(interval / timestep))
    if steps < 1:
        raise DynamicsError(
            f"{context} asks for {control_hz} control steps a second, which is "
            f"faster than the solver's own step of {timestep:g} s.",
            reason="control_rate_too_high",
            correction=(
                "An action has to last at least one solver step. Lower "
                "control_hz, or lower solver_step_s on the api.mjcf this task "
                f"reads -- at this step the ceiling is {1.0 / timestep:.0f} Hz."
            ),
            observed={"control_hz": int(control_hz), "solver_step_s": timestep},
        )
    max_steps = int(round(float(episode_seconds) * float(control_hz)))
    if max_steps < 1:
        raise DynamicsError(
            f"{context} describes an episode of no control steps.",
            reason="episode_too_short",
            observed={"episode_seconds": float(episode_seconds),
                      "control_hz": int(control_hz)},
        )
    if max_steps > MAXIMUM_EPISODE_STEPS:
        raise DynamicsError(
            f"{context} describes an episode of {max_steps} control steps; the "
            f"accepted maximum is {MAXIMUM_EPISODE_STEPS}.",
            reason="episode_too_long",
            observed={"steps": max_steps, "maximum": MAXIMUM_EPISODE_STEPS},
        )
    solver_steps = max_steps * steps
    if solver_steps > MAXIMUM_SOLVER_STEPS:
        raise DynamicsError(
            f"{context} would integrate {solver_steps} solver steps; the "
            f"accepted maximum is {MAXIMUM_SOLVER_STEPS}.",
            reason="episode_too_long",
            correction=(
                "The episode length times the control rate times the solver "
                "steps per action is the real cost. Shorten the episode or "
                "coarsen solver_step_s on the api.mjcf this task reads."
            ),
            observed={"solver_steps": solver_steps,
                      "maximum": MAXIMUM_SOLVER_STEPS},
        )
    return {
        "control_hz": int(control_hz),
        "solver_steps_per_action": steps,
        "max_steps": max_steps,
        "solver_step_s": timestep,
        "control_interval_s": steps * timestep,
        "episode_seconds": max_steps * steps * timestep,
        "reset_keyframe": MJCF_KEYFRAME_NAME,
        # Which observation a reward is computed from, stated in the file so
        # that two evaluators cannot disagree about it silently. The gym
        # convention: observe, act, integrate, and the reward is a property
        # of where the action *landed*.
        "reward_stage": "after_step",
    }


def _randomisation_records(
    mujoco: Any,
    reloaded: Any,
    entries: Sequence[Mapping[str, Any]],
    tree: Mapping[str, Any],
    joint_records: Sequence[Mapping[str, Any]],
    *,
    context: str,
) -> list[dict[str, Any]]:
    """Every randomisation entry, resolved to compiled-model field indices.

    Resolved *here*, at export time, so that the process applying a draw
    needs no name lookup and no MuJoCo introspection -- one multiply into a
    flat array. That is what lets the reference runner stay small enough to
    be obviously correct.

    One draw may move more than one field: a mass draw scales ``body_mass``
    and the body's three ``body_inertia`` entries together, because phase 0
    measured that MuJoCo keeps them independent and a body scaled in one
    alone is a body whose density depends on which equation you ask.
    """

    table = _coordinate_table(tree, joint_records)
    refusals = _coordinate_refusals(tree)
    bodies = [str(body["name"]) for body in tree["bodies"]]
    records: list[dict[str, Any]] = []
    for entry in entries:
        target = str(entry.get("target") or "")
        row = RANDOMISATION_TARGETS.get(target)
        label = str(entry.get("label") or target)
        what = f"randomisation {label!r} in {context}"
        if row is None:
            raise DynamicsError(
                f"{what} varies {target!r}, which is not a randomisable "
                "property.",
                reason="unknown_randomisation_target",
                correction=(
                    f"The supported targets are "
                    f"{', '.join(sorted(RANDOMISATION_TARGETS))}."
                ),
                observed={"target": target},
            )
        low = float(entry.get("low"))
        high = float(entry.get("high"))
        if not (math.isfinite(low) and math.isfinite(high)) or low > high:
            raise DynamicsError(
                f"{what} has an empty range.",
                reason="malformed_randomisation",
                observed={"low": low, "high": high},
            )
        if row["positive"] and low <= 0.0:
            raise DynamicsError(
                f"{what} would scale a mass by {low:g}, which is not a mass.",
                reason="malformed_randomisation",
                correction=(
                    "A scale range multiplies the value the assembly computed, "
                    "so it has to stay positive: [0.9, 1.1] is a ten per cent "
                    "spread. A body of zero or negative mass has undefined "
                    "acceleration and MuJoCo will not compile it."
                ),
                observed={"low": low, "high": high},
            )

        fields: list[dict[str, Any]] = []
        if row["on"] == "component":
            component = str(entry.get("component") or "")
            if component not in bodies:
                raise DynamicsError(
                    f"{what} varies component {component!r}, which is not a "
                    "body in this assembly's dynamics model.",
                    reason="randomisation_component_missing",
                    correction=(
                        "Pass the same assembly.component value the assembly "
                        "was built from."
                    ),
                    observed={"component": component, "available": list(bodies)},
                )
            body_id = int(mujoco.mj_name2id(reloaded, mujoco.mjtObj.mjOBJ_BODY, component))
            fields.append({"field": "body_mass", "index": body_id})
            # The three principal moments, flat: MuJoCo stores body_inertia
            # as (nbody, 3), so the row starts at 3*body_id.
            fields.extend(
                {"field": "body_inertia", "index": 3 * body_id + axis}
                for axis in range(3)
            )
            subject = component
        else:
            resolved = _resolve_coordinate(entry, table, refusals, what=what)
            joint_name = str(resolved["mujoco_joint"])
            joint_id = int(
                mujoco.mj_name2id(reloaded, mujoco.mjtObj.mjOBJ_JOINT, joint_name)
            )
            dof = int(reloaded.jnt_dofadr[joint_id])
            fields.extend(
                {"field": field, "index": dof} for field in row["fields"]
            )
            subject = joint_name
        records.append(
            {
                "label": label,
                "target": target,
                "subject": subject,
                # Multiplicative, always. An additive range would mean
                # something different for a mass than for a damping, and a
                # single scale is comparable across mechanisms.
                "mode": "scale",
                "low": low,
                "high": high,
                "fields": fields,
            }
        )
    if len(records) > MAXIMUM_RANDOMISATION_ENTRIES:
        raise DynamicsError(
            f"{context} declares {len(records)} randomisation entries; the "
            f"accepted maximum is {MAXIMUM_RANDOMISATION_ENTRIES}.",
            reason="too_many_randomisation_entries",
            observed={"entries": len(records),
                      "maximum": MAXIMUM_RANDOMISATION_ENTRIES},
        )
    return records


def task_records(
    built: Mapping[str, Any],
    reloaded: Any,
    task: Mapping[str, Any],
    *,
    observations: Sequence[Mapping[str, Any]],
    context: str = "this task",
) -> dict[str, Any]:
    """One task declaration, as the self-contained bundle a trainer reads.

    Everything is resolved against ``reloaded`` -- the model compiled from
    the **exported bytes** -- rather than against the model the engine
    simulated. That is deliberate and it is what makes the exit criterion a
    claim about the task spec rather than a second proof of M5's physics: an
    address recorded here is an address into the file somebody else will
    load, so if the file and the engine disagreed about it, this is where it
    shows.

    The bundle carries no path and no digest. Those are the worker's to add,
    because they describe where the model landed and this function has never
    seen a filesystem.
    """

    mujoco = _mujoco_module()
    tree = built["tree"]
    joint_records = built["joint_records"]
    actuators = list(built["actuators"])
    by_actuator = {
        (str(record["joint"]), str(record["motion_type"]), str(record["kind"])): record
        for record in actuators
    }
    limits_by_joint = {
        str(record["mujoco_joint"]): record.get("limits")
        for record in joint_records
    }

    # -- observations -------------------------------------------------------
    observation_rows: list[dict[str, Any]] = []
    channels: list[str] = []
    for index, record in enumerate(observations):
        adr = int(reloaded.sensor_adr[index])
        dim = int(reloaded.sensor_dim[index])
        observation_rows.append(
            {
                "name": str(record["name"]),
                "kind": str(record["kind"]),
                "target": str(record["target"]),
                "sensor": str(record["mujoco_sensor"]),
                "adr": adr,
                "dim": dim,
                "channels": [str(name) for name in record["channels"]],
                "unit": str(record["unit"]),
                "scale": float(record["scale"]),
            }
        )
        channels.extend(str(name) for name in record["channels"])

    # -- actions ------------------------------------------------------------
    action_rows: list[dict[str, Any]] = []
    seen_actions: set[str] = set()
    for entry in task.get("actions") or ():
        key = (
            str(entry.get("joint") or ""),
            str(entry.get("motion_type") or ""),
            str(entry.get("actuator_kind") or ""),
        )
        record = by_actuator.get(key)
        what = f"the action on {_coordinate_context(key[0], key[1])}"
        if record is None:
            raise DynamicsError(
                f"{what} names an actuator this model does not carry.",
                reason="action_actuator_missing",
                correction=(
                    "An action list names assembly.actuator values that were "
                    "given to the api.mjcf this task reads. An actuator the "
                    "model does not have is a coordinate nothing can drive."
                ),
                observed={
                    "joint": key[0],
                    "motion_type": key[1],
                    "actuator_kind": key[2],
                    "available": sorted(
                        str(item["mujoco_actuator"]) for item in actuators
                    ),
                },
            )
        name = str(record["mujoco_actuator"])
        if name in seen_actions:
            raise DynamicsError(
                f"{what} is listed twice.",
                reason="duplicate_action",
                correction=(
                    "One actuator is one action. Two entries would give a "
                    "policy two numbers for one motor and use whichever came "
                    "second."
                ),
                observed={"actuator": name},
            )
        seen_actions.add(name)
        index = int(mujoco.mj_name2id(reloaded, mujoco.mjtObj.mjOBJ_ACTUATOR, name))
        if index < 0:
            raise DynamicsError(
                f"{what} resolves to actuator {name!r}, which the exported "
                "model does not contain.",
                reason="action_actuator_missing",
                observed={"actuator": name},
            )
        bound = _action_bound(
            record, limits_by_joint.get(str(record["mujoco_joint"])), what=what
        )
        action_rows.append(
            {
                "actuator": name,
                "joint": str(record["joint"]),
                "motion_type": str(record["motion_type"]),
                "kind": str(record["kind"]),
                "index": index,
                # The control formula the script already had to write. It is
                # the deterministic fallback: the action taken when no policy
                # is driving, which is what lets an episode run -- and be
                # compared -- before any policy exists (M8 swaps it out).
                "fallback": str(record["control"]),
                **bound,
            }
        )
    if not action_rows:
        raise DynamicsError(
            f"{context} declares no actions, so nothing a policy does could "
            "change what happens.",
            reason="task_has_no_actions",
            correction=(
                "Give the task at least one assembly.actuator to drive."
            ),
            observed={"task": context},
        )

    # -- reward and termination --------------------------------------------
    reward_rows: list[dict[str, Any]] = []
    for entry in task.get("reward") or ():
        label = str(entry.get("label") or "reward")
        expression = str(entry.get("expression") or "")
        compile_reward(expression, names=channels, context=f"reward {label!r}")
        reward_rows.append(
            {
                "label": label,
                "weight": float(entry.get("weight", 1.0)),
                "expression": expression,
            }
        )
    if not reward_rows:
        raise DynamicsError(
            f"{context} declares no reward terms.",
            reason="task_has_no_reward",
            correction=(
                "A task without a reward is a simulation. Give it at least "
                "one assembly.reward term naming the channels it observes."
            ),
            observed={"task": context},
        )
    if len(reward_rows) > MAXIMUM_REWARD_TERMS:
        raise DynamicsError(
            f"{context} declares {len(reward_rows)} reward terms; the accepted "
            f"maximum is {MAXIMUM_REWARD_TERMS}.",
            reason="too_many_reward_terms",
            observed={"terms": len(reward_rows), "maximum": MAXIMUM_REWARD_TERMS},
        )

    termination_rows: list[dict[str, Any]] = []
    for entry in task.get("termination") or ():
        label = str(entry.get("label") or "termination")
        expression = str(entry.get("expression") or "")
        compile_reward(expression, names=channels, context=f"termination {label!r}")
        above = entry.get("above")
        below = entry.get("below")
        if above is None and below is None:
            raise DynamicsError(
                f"Termination {label!r} in {context} states no threshold.",
                reason="malformed_termination",
                correction=(
                    "A termination rule is an expression and a bound it must "
                    "not cross: give it above=... or below=..."
                ),
                observed={"termination": label},
            )
        termination_rows.append(
            {
                "label": label,
                "expression": expression,
                "above": None if above is None else float(above),
                "below": None if below is None else float(below),
            }
        )
    if len(termination_rows) > MAXIMUM_TERMINATION_TERMS:
        raise DynamicsError(
            f"{context} declares {len(termination_rows)} termination rules; "
            f"the accepted maximum is {MAXIMUM_TERMINATION_TERMS}.",
            reason="too_many_termination_terms",
            observed={"terms": len(termination_rows),
                      "maximum": MAXIMUM_TERMINATION_TERMS},
        )

    schedule = _episode_schedule(
        reloaded,
        control_hz=int(task.get("control_hz") or 0),
        episode_seconds=float(task.get("episode_seconds") or 0.0),
        context=context,
    )
    randomisation = _randomisation_records(
        mujoco,
        reloaded,
        task.get("randomisation") or (),
        tree,
        joint_records,
        context=context,
    )
    return {
        "schema": TASK_SCHEMA,
        "label": str(task.get("label") or ""),
        "observations": observation_rows,
        "actions": action_rows,
        "reward": reward_rows,
        "termination": termination_rows,
        "episode": schedule,
        "randomisation": randomisation,
        # Shipped so the reference runner's own evaluator can be asserted
        # equal to this array rather than kept equal to it by attention.
        "functions": list(REWARD_FUNCTIONS),
        "mujoco_version": str(built["mujoco_version"]),
    }


def load_model(xml: bytes) -> Any:
    """One exported file's bytes, as a compiled model.

    Here rather than in the worker because this module is the only one in
    the tree allowed to import ``mujoco`` -- ``test_engine_purity_guardrails``
    asserts that import closure exactly, and a worker that loaded a model
    itself would be the second place it entered.
    """

    mujoco = _mujoco_module()
    return mujoco.MjModel.from_xml_string(bytes(xml).decode("utf-8"))


def observation_values(
    task: Mapping[str, Any], sensordata: Sequence[float]
) -> dict[str, float]:
    """One raw ``sensordata`` array as the named, scaled channels of a task.

    Three lines of arithmetic, and every one of them is the bundle's:
    ``adr`` and ``dim`` say which slice, ``scale`` says what to multiply by,
    ``channels`` say what to call the results. Nothing is looked up in a
    model here, which is exactly why a process with no Cadex on its path can
    do the same thing from the same file.
    """

    values: dict[str, float] = {}
    for record in task["observations"]:
        adr = int(record["adr"])
        dim = int(record["dim"])
        scale = float(record["scale"])
        for offset, channel in enumerate(record["channels"][:dim]):
            values[str(channel)] = float(sensordata[adr + offset]) * scale
    return values


def apply_randomisation(
    mujoco: Any, model: Any, data: Any, task: Mapping[str, Any], *, seed: int
) -> list[dict[str, Any]]:
    """Draw one factor per entry and multiply it into the model, in place.

    ``random.Random(seed)`` drawing ``uniform(low, high)`` in bundle order:
    a stated algorithm rather than an implicit one, because the reference
    runner has to reproduce the same draws from the same seed and "whatever
    the RNG did" is not reproducible across two implementations.

    ``mj_setConst`` afterwards is not optional -- phase 0 measured that
    ``body_subtreemass`` is derived from ``body_mass`` there, so a mass draw
    that skipped it would change the mass and not what the solver does with
    it.
    """

    import random

    rng = random.Random(int(seed))
    drawn: list[dict[str, Any]] = []
    for entry in task.get("randomisation") or ():
        factor = rng.uniform(float(entry["low"]), float(entry["high"]))
        for field in entry["fields"]:
            array = getattr(model, str(field["field"]))
            array.flat[int(field["index"])] *= factor
        drawn.append({"label": str(entry["label"]), "factor": float(factor)})
    if drawn:
        mujoco.mj_setConst(model, data)
    return drawn


def evaluate_episode(
    model: Any,
    task: Mapping[str, Any],
    *,
    actions: Any = None,
    sample: Any = None,
    seed: int | None = None,
) -> dict[str, Any]:
    """One full episode, from the bundle, in the engine.

    **This is M8's rollout path**, and M8 took it: ``actions`` is a callable
    taking the step and the observation rather than a precomputed array
    precisely so that a trained policy could be dropped into it, and
    :func:`rollout_policy` is what does the dropping. ``sample`` is the other
    half of that swap and is the only thing M8 added to this loop.

    ``sample`` is a callable ``(step, data, final) -> record | None`` invoked
    once at the reset pose and once after every control step's integration,
    with ``final`` true on the last invocation whether the episode was
    terminated or truncated. Every non-``None`` return joins ``samples`` in
    order. **The caller decides what a frame is**: this loop knows control
    steps and nothing about frame rates, so a rollout that wants one frame
    per five control steps returns ``None`` on the other four. One episode
    loop stays one episode loop, which matters more here than anywhere --
    M7 already carries three evaluators of the reward whitelist, and a
    second loop would be a fourth place for the same drift.

    The bundle is the only input besides the model: no ``built``, no tree,
    no records. That is what makes the comparison against the reference
    runner meaningful -- both evaluators consume the same file, so a
    disagreement is a disagreement about the *task spec* and not about which
    side had more information.

    One control step is: observe, act, integrate
    ``solver_steps_per_action`` times, observe again, and score. The reward
    is a property of where the action landed rather than of where it started
    (``episode.reward_stage``), and the termination rules are checked on the
    same post-step observation, so a run that ends does so at the step whose
    action ended it.

    ``actions`` is a callable ``(step, observation) -> sequence`` in the
    surface units the bundle advertises; without one, each actuator's own
    control formula is evaluated at the step's time, which is the
    deterministic fallback that lets an episode run before any policy
    exists. Either way the value is clamped to the advertised range before
    it is scaled into ``data.ctrl``: the bound is what the bundle promised a
    policy, and a runner that quietly exceeded it would be running a
    different mechanism from the one it described.
    """

    mujoco = _mujoco_module()
    episode = task["episode"]
    per_action = int(episode["solver_steps_per_action"])
    max_steps = int(episode["max_steps"])
    control_interval = float(episode["control_interval_s"])

    reward_terms = [
        (
            str(term["label"]),
            float(term["weight"]),
            compile_reward(
                str(term["expression"]),
                names=_task_channels(task),
                context=f"reward {term['label']!r}",
            ),
        )
        for term in task["reward"]
    ]
    termination_terms = [
        (
            str(term["label"]),
            term.get("above"),
            term.get("below"),
            compile_reward(
                str(term["expression"]),
                names=_task_channels(task),
                context=f"termination {term['label']!r}",
            ),
        )
        for term in task["termination"]
    ]
    fallbacks = [
        compile_control(str(action["fallback"]), context=f"action {action['actuator']!r}")
        for action in task["actions"]
    ]

    data = mujoco.MjData(model)
    drawn = (
        []
        if seed is None
        else apply_randomisation(mujoco, model, data, task, seed=int(seed))
    )
    key = mujoco.mj_name2id(
        model, mujoco.mjtObj.mjOBJ_KEY, str(episode["reset_keyframe"])
    )
    if key < 0:
        raise DynamicsError(
            "The model this task reads carries no "
            f"{episode['reset_keyframe']!r} keyframe, so an episode has no "
            "starting pose.",
            reason="task_keyframe_missing",
            observed={"keyframe": str(episode["reset_keyframe"])},
        )
    mujoco.mj_resetDataKeyframe(model, data, key)
    mujoco.mj_forward(model, data)

    steps: list[dict[str, Any]] = []
    samples: list[Any] = []

    def _sampled(step: int, final: bool) -> None:
        if sample is None:
            return
        record = sample(step, data, final)
        if record is not None:
            samples.append(record)

    total = 0.0
    terminated_step: int | None = None
    termination_label = ""
    _sampled(0, max_steps < 1)
    for step in range(max_steps):
        time_s = step * control_interval
        observation = observation_values(task, data.sensordata)
        if actions is None:
            commanded = [
                evaluate_control(code, time_s, context=f"action {index}")
                for index, code in enumerate(fallbacks)
            ]
        else:
            commanded = [float(value) for value in actions(step, observation)]
        if len(commanded) != len(task["actions"]):
            raise DynamicsError(
                f"An episode of {task.get('label') or 'this task'} was given "
                f"{len(commanded)} action values for "
                f"{len(task['actions'])} actuators.",
                reason="action_shape_mismatch",
                observed={"given": len(commanded),
                          "expected": len(task["actions"])},
            )
        applied: list[float] = []
        for value, action in zip(commanded, task["actions"], strict=True):
            clamped = min(max(float(value), float(action["low"])), float(action["high"]))
            applied.append(clamped)
            data.ctrl[int(action["index"])] = clamped * float(action["scale"])
        for _ in range(per_action):
            mujoco.mj_step(model, data)

        landed = observation_values(task, data.sensordata)
        contributions = []
        reward = 0.0
        for label, weight, code in reward_terms:
            raw = evaluate_reward(code, landed, context=f"reward {label!r}")
            contributions.append({"label": label, "value": raw,
                                  "weighted": weight * raw})
            reward += weight * raw
        total += reward
        reason = ""
        for label, above, below, code in termination_terms:
            value = evaluate_reward(code, landed, context=f"termination {label!r}")
            if (above is not None and value > float(above)) or (
                below is not None and value < float(below)
            ):
                reason = label
                break
        steps.append(
            {
                "step": step,
                "time_s": time_s + control_interval,
                "action": applied,
                "observation": landed,
                "reward": reward,
                "reward_terms": contributions,
                "terminated": bool(reason),
                "termination": reason,
            }
        )
        _sampled(step + 1, bool(reason) or step == max_steps - 1)
        if reason:
            terminated_step = step
            termination_label = reason
            break
    return {
        "label": str(task.get("label") or ""),
        "steps": steps,
        # Empty unless a ``sample`` callable was given, and never inspected
        # by this loop: what a record *is* belongs to whoever asked for one.
        "samples": samples,
        "step_count": len(steps),
        "total_reward": total,
        "terminated_step": terminated_step,
        "termination": termination_label,
        # A run that used its whole budget and one that was cut short are
        # different outcomes, and a trainer has to be able to tell them
        # apart: the first is a horizon, the second is a failure.
        "truncated": terminated_step is None,
        "randomisation": drawn,
        "seed": None if seed is None else int(seed),
    }


def _task_channels(task: Mapping[str, Any]) -> list[str]:
    """Every scalar channel name the bundle declares, in slice order."""

    return [
        str(channel)
        for record in task["observations"]
        for channel in record["channels"]
    ]


# ---------------------------------------------------------------------------
# The trained policy (docs/MUJOCO.md M7, ADR-070).
#
# Training happens on a machine this engine will never see -- ADR-060 said
# offboard and M7 kept it that way -- so what comes back is a *file*, and the
# whole of this section is about that file being checkable rather than
# trusted. A policy whose weights are fine but whose architecture the engine
# reads differently is not a bad gait, it is a different network; the witness
# below is what turns that from something you notice in a viewport into a
# refusal.
#
# Nothing here imports numpy. Phase 0 measured a pure-Python forward pass at
# 219 us for the 16x64x64x2 network an arm task trains and 5.29 ms for a
# 231 000-parameter humanoid-scale one -- 4 564 Hz and 189 Hz against a
# control rate the surface encourages at 50 Hz. ``scipy.spatial`` is
# deferred-imported at line ~996 because a convex hull genuinely needs it;
# this does not, so the module stays what its docstring says it is.
# ---------------------------------------------------------------------------


#: The schema the container declares, and the version a reader checks first.
POLICY_SCHEMA = "cadex-policy-v1"

#: The container's first bytes. A magic line rather than a suffix check,
#: because the store accepts the suffix and this is what says the bytes are
#: what the name claimed.
POLICY_MAGIC = b"CXPOLICY1\n"

#: The container's own byte cap.
#:
#: Phase 0 measured what a PPO policy is actually made of, because
#: docs/MUJOCO.md 3.1 guessed "tens of megabytes" and that guess is three
#: orders of magnitude high. An MLP with its observation normaliser:
#: 4.6 KiB for a one-hinge swing-up, 21.1 KiB for a two-link arm, 20.4 KiB
#: for brax's PPO default, and 902 KiB for a 123-observation humanoid at
#: 512x256x128. Four mebibytes is headroom over the largest of those plus a
#: witness, and is still small enough that a policy approaching it is a
#: network nobody meant to train.
MAXIMUM_POLICY_BYTES = 4 * 1024 * 1024

#: Bounds on the network itself, so a malformed header is refused before a
#: length is trusted to allocate anything.
MAXIMUM_POLICY_PARAMETERS = 1_000_000
MAXIMUM_POLICY_LAYERS = 8
MAXIMUM_POLICY_WIDTH = 1024

#: How many observation/action pairs the trainer must record, and may.
#:
#: The witness is the whole safety argument, so it cannot be optional and it
#: cannot be one sample: a single vector agrees by accident far more often
#: than eight do, and eight of them across the observation range exercise
#: every layer's nonlinearity in both directions.
MINIMUM_POLICY_WITNESS_SAMPLES = 8
MAXIMUM_POLICY_WITNESS_SAMPLES = 256

#: How far the engine's forward pass may differ from the trainer's, relative
#: to each action's own advertised range.
#:
#: Measured (phase 0), not chosen, in the style of M5's inertia bound. A
#: float32 JAX network against a float64 numpy one over 64 random
#: observations: max relative error **1.46e-5**, max absolute error 2.16e-7
#: on tanh-bounded outputs. JAX's own jitted and un-jitted evaluations of the
#: same weights in the same process differ by ~1e-7, so no tolerance tighter
#: than that is meaningful about anything. This is seven times the worst
#: measurement and four orders below a difference a person would call a
#: different gait.
POLICY_WITNESS_TOLERANCE = 1.0e-4

#: What a hidden layer may do. Deliberately two rows, and named rather than
#: open: an activation the engine guesses wrong is a network that reads as
#: plausible and is not the one that trained.
POLICY_ACTIVATIONS = ("tanh", "relu")

#: What the output layer may do. One row, and it is load-bearing rather than
#: restrictive: ``network.output_scale`` and ``network.output_bias`` map a
#: bounded output onto the bundle's advertised action range, and that map is
#: only checkable because the thing it maps is known to lie in [-1, 1].
POLICY_OUTPUT_ACTIVATIONS = ("tanh",)


def _policy_error(
    message: str, *, reason: str, correction: str = "", **observed: Any
) -> DynamicsError:
    return DynamicsError(
        message, reason=reason, correction=correction, observed=dict(observed)
    )


def _float32_bytes(values: Sequence[float]) -> bytes:
    """One flat parameter vector as little-endian float32.

    ``struct`` rather than ``array`` because ``array('f')`` is
    native-endian, and a container whose bytes depend on the machine that
    wrote it is not a container a digest can identify.
    """

    import struct

    return struct.pack(f"<{len(values)}f", *[float(value) for value in values])


def _float32_values(blob: bytes) -> list[float]:
    """The inverse, as Python floats holding exactly the float32 that landed."""

    import struct

    count = len(blob) // 4
    return [float(value) for value in struct.unpack(f"<{count}f", blob)]


def _canonical_header(header: Mapping[str, Any]) -> bytes:
    """One header as the only bytes it can be.

    Sorted keys, no whitespace, ASCII, and no NaN -- so two writers with the
    same header produce the same file and the project digest is about the
    policy rather than about when it was written. Python's ``repr`` for
    floats round-trips exactly, and ``json`` uses it, so nothing is lost to
    the text form.
    """

    import json

    return json.dumps(
        dict(header),
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("ascii")


def encode_policy(header: Mapping[str, Any], weights: Sequence[float]) -> bytes:
    """One header and one parameter vector, as the bytes that are the policy.

    ``CXPOLICY1\\n | <u64 LE header length> | <canonical JSON> | <f32 LE blob>``

    Hand-rolled rather than ``np.savez``, and phase 0 is why the *stated*
    reason for that is not the one docs/MUJOCO.md's plan gave. The plan
    expected a zip container to stamp entries with an mtime and so not be
    byte-deterministic. **It is deterministic** -- numpy writes a fixed
    ``date_time``, and two processes an hour apart produced the same
    sha256 -- so that argument does not hold and is recorded as wrong rather
    than quietly dropped.

    What does hold is smaller and still decides it. The engine reads this
    file inside a ``--safe-mode`` sandbox with no numpy import in this
    module at all, and ``np.load`` on an untrusted archive is a zip parser
    plus an ``allow_pickle`` flag that has to stay false. A length-prefixed
    header and a flat float32 blob need neither, are readable by the
    fourteen lines of ``decode_policy`` below, and carry the schema, the
    task digest and the witness in one file rather than in a naming
    convention over several arrays.
    """

    payload = _canonical_header(header)
    return b"".join(
        (
            POLICY_MAGIC,
            len(payload).to_bytes(8, "little"),
            payload,
            _float32_bytes(weights),
        )
    )


def decode_policy(blob: bytes, *, context: str = "this policy") -> dict[str, Any]:
    """The inverse of :func:`encode_policy`, refusing everything malformed.

    Every length is checked against the bytes that are actually there before
    it is used, because this is the one function in the module that reads a
    file a user supplied rather than a value the engine computed.
    """

    import json

    data = bytes(blob)
    if len(data) > MAXIMUM_POLICY_BYTES:
        raise _policy_error(
            f"{context} is {len(data)} bytes; the accepted maximum is "
            f"{MAXIMUM_POLICY_BYTES} bytes.",
            reason="policy_too_large",
            correction=(
                "A trained control policy is a small multilayer perceptron: "
                "a humanoid-scale one measures under a megabyte. A file this "
                "large is a checkpoint, an optimiser state or a replay "
                "buffer rather than a policy."
            ),
            bytes=len(data),
            maximum=MAXIMUM_POLICY_BYTES,
        )
    if not data.startswith(POLICY_MAGIC):
        raise _policy_error(
            f"{context} does not begin with the {POLICY_SCHEMA} magic line.",
            reason="policy_not_a_container",
            correction=(
                "A .cxpolicy file is what training/cadex_train.py writes. "
                "An MJCF model, a task bundle or a raw checkpoint stored "
                "under that name is refused here rather than read as one."
            ),
            observed_prefix=repr(data[:16]),
        )
    start = len(POLICY_MAGIC)
    if len(data) < start + 8:
        raise _policy_error(
            f"{context} ends inside its header length.",
            reason="policy_truncated",
            correction="The file was cut short in transit; copy it again.",
            bytes=len(data),
        )
    header_bytes = int.from_bytes(data[start : start + 8], "little")
    body = start + 8
    if header_bytes > len(data) - body:
        raise _policy_error(
            f"{context} declares a {header_bytes}-byte header but carries "
            f"{len(data) - body} bytes after the length.",
            reason="policy_truncated",
            correction="The file was cut short in transit; copy it again.",
            declared=header_bytes,
            available=len(data) - body,
        )
    try:
        header = json.loads(data[body : body + header_bytes].decode("ascii"))
    except Exception as exc:
        raise _policy_error(
            f"{context} carries a header that is not the canonical JSON this "
            f"container declares: {exc}",
            reason="policy_header_malformed",
            correction=(
                "The header is written by encode_policy and is ASCII JSON. "
                "A file edited by hand, or one written by a different "
                "container version, lands here."
            ),
        ) from exc
    if not isinstance(header, dict):
        raise _policy_error(
            f"{context} carries a header that is not an object.",
            reason="policy_header_malformed",
            correction="The header is a JSON object; this file's is not.",
        )
    remainder = data[body + header_bytes :]
    if len(remainder) % 4:
        raise _policy_error(
            f"{context} carries {len(remainder)} weight bytes, which is not a "
            "whole number of float32 values.",
            reason="policy_truncated",
            correction="The file was cut short in transit; copy it again.",
            weight_bytes=len(remainder),
        )
    return {"header": header, "weights": _float32_values(remainder)}


def _policy_layers(
    header: Mapping[str, Any], *, context: str
) -> list[tuple[int, int]]:
    """The declared layer shapes, checked before any of them is trusted."""

    network = header.get("network")
    if not isinstance(network, Mapping):
        raise _policy_error(
            f"{context} declares no network.",
            reason="policy_network_malformed",
            correction="A cadex-policy-v1 header carries a 'network' object.",
        )
    if str(network.get("kind") or "") != "mlp":
        raise _policy_error(
            f"{context} declares a {network.get('kind')!r} network; this "
            "engine evaluates 'mlp'.",
            reason="policy_network_malformed",
            correction=(
                "The forward pass the engine runs is a multilayer "
                "perceptron. A recurrent or convolutional policy would need "
                "an engine that knows how to step it."
            ),
            kind=str(network.get("kind") or ""),
        )
    activation = str(network.get("activation") or "")
    if activation not in POLICY_ACTIVATIONS:
        raise _policy_error(
            f"{context} declares a {activation!r} hidden activation.",
            reason="policy_network_malformed",
            correction=(
                "The engine evaluates "
                f"{' and '.join(repr(name) for name in POLICY_ACTIVATIONS)}. "
                "An activation it guessed wrong would read as a plausible "
                "network and not be the one that trained."
            ),
            activation=activation,
        )
    output = str(network.get("output") or "")
    if output not in POLICY_OUTPUT_ACTIVATIONS:
        raise _policy_error(
            f"{context} declares a {output!r} output activation.",
            reason="policy_network_malformed",
            correction=(
                "The output activation is 'tanh'. The container maps a "
                "bounded output onto the task's action range through "
                "network.output_scale and network.output_bias, and that map "
                "is only checkable because its input is known to lie in "
                "[-1, 1]."
            ),
            output=output,
        )
    raw = network.get("layers")
    if not isinstance(raw, (list, tuple)) or not raw:
        raise _policy_error(
            f"{context} declares no layers.",
            reason="policy_network_malformed",
            correction="A network is at least one [inputs, outputs] pair.",
        )
    if len(raw) > MAXIMUM_POLICY_LAYERS:
        raise _policy_error(
            f"{context} declares {len(raw)} layers; the accepted maximum is "
            f"{MAXIMUM_POLICY_LAYERS}.",
            reason="policy_network_malformed",
            correction=(
                "A control policy for a mechanism is a few layers deep. This "
                "bounds a header that was generated by a loop."
            ),
            layers=len(raw),
        )
    shapes: list[tuple[int, int]] = []
    for index, entry in enumerate(raw):
        if (
            not isinstance(entry, (list, tuple))
            or len(entry) != 2
            or any(isinstance(value, bool) or not isinstance(value, int)
                   for value in entry)
            or any(value < 1 for value in entry)
        ):
            raise _policy_error(
                f"{context} layer {index} is not a pair of positive integers.",
                reason="policy_network_malformed",
                correction="Each layer is [inputs, outputs].",
                layer=index,
            )
        inputs, outputs = int(entry[0]), int(entry[1])
        if max(inputs, outputs) > MAXIMUM_POLICY_WIDTH:
            raise _policy_error(
                f"{context} layer {index} is {inputs}x{outputs}; the accepted "
                f"maximum width is {MAXIMUM_POLICY_WIDTH}.",
                reason="policy_network_malformed",
                correction=(
                    "A wider layer than this is not a mechanism controller, "
                    "and evaluating it at the control rate is not free."
                ),
                layer=index,
            )
        if shapes and shapes[-1][1] != inputs:
            raise _policy_error(
                f"{context} layer {index} takes {inputs} inputs where layer "
                f"{index - 1} produces {shapes[-1][1]}.",
                reason="policy_network_malformed",
                correction="The layers have to chain; these do not.",
                layer=index,
            )
        shapes.append((inputs, outputs))
    total = sum(inputs * outputs + outputs for inputs, outputs in shapes)
    if total > MAXIMUM_POLICY_PARAMETERS:
        raise _policy_error(
            f"{context} declares {total} parameters; the accepted maximum is "
            f"{MAXIMUM_POLICY_PARAMETERS}.",
            reason="policy_network_malformed",
            correction=(
                "A humanoid-scale gait policy measures 231 000 parameters. "
                "This is a network trained for something else."
            ),
            parameters=total,
        )
    return shapes


def _policy_vector(
    header: Mapping[str, Any],
    observation: Any,
    *,
    context: str,
) -> list[float]:
    """One observation as the ordered vector the network's first layer takes.

    Accepts the named mapping :func:`observation_values` produces -- which is
    what an episode holds -- or an already-ordered sequence, which is what
    the container's witness records. Either way the order is the *header's*
    channel list, so a policy trained against a different observation order
    cannot be silently fed this one.
    """

    channels = [str(name) for name in header.get("observations") or ()]
    if isinstance(observation, Mapping):
        missing = [name for name in channels if name not in observation]
        if missing:
            raise _policy_error(
                f"{context} was given an observation with no "
                f"{', '.join(repr(name) for name in missing[:4])} in it.",
                reason="policy_observation_mismatch",
                correction=(
                    "The observation a policy is evaluated on carries every "
                    "channel the policy was trained on, under the same name."
                ),
                missing=missing[:8],
            )
        return [float(observation[name]) for name in channels]
    values = [float(value) for value in observation]
    if len(values) != len(channels):
        raise _policy_error(
            f"{context} was given {len(values)} observation values for "
            f"{len(channels)} channels.",
            reason="policy_observation_mismatch",
            correction=(
                "An ordered observation is the header's 'observations' list, "
                "in that order and at that length."
            ),
            given=len(values),
            expected=len(channels),
        )
    return values


def policy_forward(
    header: Mapping[str, Any],
    weights: Sequence[float],
    observation: Any,
    *,
    context: str = "this policy",
) -> list[float]:
    """One observation through the network, as actions in the task's own units.

    **This is hazard 1's fifth payment, and it is paid structurally.** The
    number that leaves here is already in the unit the bundle advertised for
    that actuator -- newton-millimetres for a motor, degrees for a servo --
    so :func:`evaluate_episode` applies it through exactly the ``clamp then
    x scale`` it already applies to a fallback formula, and M7 adds **no**
    conversion site at all. ``test_dynamics_units`` greps for that, now
    including the trainer.

    Two arithmetic stages here are not unit conversions and are still
    arithmetic that must round-trip, so both are explicit arrays in the
    container rather than conventions:

    * the **observation normaliser**, ``(x - mean) / std``, which is what
      makes a 300 mm channel and a 0.3 rad one comparable to a network; and
    * the **output map**, ``tanh(z) * output_scale + output_bias``, whose
      two arrays :func:`verify_policy` checks against the action ranges the
      *bundle* derived -- so the numbers come from the mechanism rather than
      from the trainer's imagination.
    """

    shapes = _policy_layers(header, context=context)
    network = header["network"]
    activation = str(network.get("activation") or "")
    normaliser = header.get("normaliser")
    if not isinstance(normaliser, Mapping):
        raise _policy_error(
            f"{context} declares no observation normaliser.",
            reason="policy_normaliser_malformed",
            correction=(
                "A cadex-policy-v1 header carries 'normaliser' with a 'mean' "
                "and a 'std' the same length as its observation list. A "
                "policy trained without one records zeros and ones."
            ),
        )
    mean = [float(value) for value in normaliser.get("mean") or ()]
    std = [float(value) for value in normaliser.get("std") or ()]
    values = _policy_vector(header, observation, context=context)
    if len(mean) != len(values) or len(std) != len(values):
        raise _policy_error(
            f"{context} normalises {len(mean)} means and {len(std)} standard "
            f"deviations over {len(values)} channels.",
            reason="policy_normaliser_malformed",
            correction="The normaliser is one mean and one std per channel.",
            mean=len(mean), std=len(std), channels=len(values),
        )
    if any(value == 0.0 for value in std):
        raise _policy_error(
            f"{context} normalises a channel by a standard deviation of zero.",
            reason="policy_normaliser_malformed",
            correction=(
                "A channel that never moved during training has no scale. "
                "The trainer writes 1.0 for those rather than 0.0."
            ),
        )
    if shapes[0][0] != len(values):
        raise _policy_error(
            f"{context} takes {shapes[0][0]} inputs for {len(values)} "
            "observation channels.",
            reason="policy_network_malformed",
            correction=(
                "The first layer's input width is the number of scalar "
                "observation channels the task declares."
            ),
            inputs=shapes[0][0], channels=len(values),
        )
    expected = sum(inputs * outputs + outputs for inputs, outputs in shapes)
    if len(weights) != expected:
        raise _policy_error(
            f"{context} carries {len(weights)} parameters for a network that "
            f"needs {expected}.",
            reason="policy_weights_mismatch",
            correction=(
                "The blob is each layer's weight matrix row-major followed by "
                "its bias, in layer order. A count that disagrees with the "
                "header means the two halves of the file came from different "
                "runs."
            ),
            carried=len(weights), expected=expected,
        )

    activations = [(value - mean[index]) / std[index]
                   for index, value in enumerate(values)]
    cursor = 0
    last = len(shapes) - 1
    for index, (inputs, outputs) in enumerate(shapes):
        matrix = weights[cursor : cursor + inputs * outputs]
        cursor += inputs * outputs
        bias = weights[cursor : cursor + outputs]
        cursor += outputs
        result = [0.0] * outputs
        for column in range(outputs):
            total = bias[column]
            offset = column
            for row in range(inputs):
                total += activations[row] * matrix[offset]
                offset += outputs
            result[column] = total
        if index < last:
            if activation == "tanh":
                result = [math.tanh(value) for value in result]
            else:
                result = [value if value > 0.0 else 0.0 for value in result]
        activations = result

    squashed = [math.tanh(value) for value in activations]
    scale = [float(value) for value in network.get("output_scale") or ()]
    bias_out = [float(value) for value in network.get("output_bias") or ()]
    if len(scale) != len(squashed) or len(bias_out) != len(squashed):
        raise _policy_error(
            f"{context} maps {len(squashed)} outputs through {len(scale)} "
            f"scales and {len(bias_out)} biases.",
            reason="policy_network_malformed",
            correction=(
                "network.output_scale and network.output_bias carry one "
                "number per action, and they are what put the network's "
                "bounded output into the units the task advertised."
            ),
        )
    return [
        value * scale[index] + bias_out[index]
        for index, value in enumerate(squashed)
    ]


def _policy_action_map(task: Mapping[str, Any]) -> tuple[list[float], list[float]]:
    """The output map the bundle's own action ranges imply.

    Half-range and midpoint, per action. Computed from the task rather than
    read from the policy, so that :func:`verify_policy` compares the
    trainer's arithmetic against the *mechanism's* numbers -- the same move
    ``_action_bound`` makes when it derives a range from a joint limit
    instead of defaulting one.
    """

    scale = [
        (float(action["high"]) - float(action["low"])) / 2.0
        for action in task["actions"]
    ]
    bias = [
        (float(action["high"]) + float(action["low"])) / 2.0
        for action in task["actions"]
    ]
    return scale, bias


#: What a policy's action row must restate from the bundle, and nothing else.
#: ``source`` and ``fallback`` are deliberately absent: they describe how the
#: bundle *derived* the bound and what to do without a policy, neither of
#: which a trained network has an opinion about.
_POLICY_ACTION_FIELDS = ("actuator", "index", "unit", "low", "high", "scale")


def _same_action_field(found: Any, wanted: Any) -> bool:
    """Whether a policy's copy of one bundle field is that field.

    Exact rather than approximate, and typed by what the *bundle* holds: an
    action row is copied verbatim by the trainer, so anything but equality
    means it was copied from a different bundle. A number that arrives as a
    string, or as nothing at all, is a difference rather than an exception --
    this reads a file somebody else wrote.
    """

    if isinstance(wanted, bool) or not isinstance(wanted, (int, float)):
        return isinstance(found, str) and found == str(wanted)
    if isinstance(found, bool) or not isinstance(found, (int, float)):
        return False
    return float(found) == float(wanted)


def verify_policy(
    container: Mapping[str, Any],
    task: Mapping[str, Any],
    *,
    task_sha256: str,
    context: str = "this policy",
) -> dict[str, Any]:
    """Cross-check one decoded container against the task it claims to be for.

    Six claims, each of which is a way for a policy to be confidently wrong
    about a mechanism:

    1. it was trained on **this** task bundle, by digest;
    2. against **this** model, by the digest the bundle itself recorded;
    3. observing **these** channels, in this order;
    4. driving **these** actuators, at these indices, in these units, within
       these ranges;
    5. through an output map the bundle's own action ranges imply; and
    6. reproducing, under the engine's forward pass, the actions the
       trainer's own network produced for the observations it recorded.

    Six is M5's self-verification idea reused, and it is the one that makes
    M8 safe: a container whose weights are intact but whose layer order,
    activation or parameter layout the engine reads differently passes the
    first five and fails this one. The refusal is then about the *file*
    rather than about a gait somebody has to watch to distrust.
    """

    header = container.get("header")
    weights = container.get("weights")
    if not isinstance(header, Mapping) or not isinstance(weights, (list, tuple)):
        raise _policy_error(
            f"{context} is not a decoded policy container.",
            reason="policy_header_malformed",
            correction="Pass what decode_policy returned.",
        )
    if str(header.get("schema") or "") != POLICY_SCHEMA:
        raise _policy_error(
            f"{context} declares schema {header.get('schema')!r}; this engine "
            f"reads {POLICY_SCHEMA!r}.",
            reason="policy_schema_unknown",
            correction=(
                "The container version is written by training/cadex_train.py. "
                "Retrain, or use the trainer that matches this engine."
            ),
            schema=str(header.get("schema") or ""),
        )

    declared_task = header.get("task")
    declared_task = dict(declared_task) if isinstance(declared_task, Mapping) else {}
    if str(declared_task.get("sha256") or "") != str(task_sha256):
        raise _policy_error(
            f"{context} was trained on a task bundle whose digest is "
            f"{declared_task.get('sha256')!r}, and the task it is declared "
            f"against digests to {task_sha256!r}.",
            reason="policy_task_mismatch",
            correction=(
                "A policy is only meaningful for the exact task it was "
                "trained on: change a reward weight or an episode length and "
                "the policy is optimising something else. Retrain against "
                "the current bundle, or point the script at the task that "
                "produced this policy."
            ),
            policy_task_sha256=str(declared_task.get("sha256") or ""),
            task_sha256=str(task_sha256),
        )

    declared_model = header.get("model")
    declared_model = dict(declared_model) if isinstance(declared_model, Mapping) else {}
    model_sha256 = str((task.get("model") or {}).get("sha256") or "")
    if str(declared_model.get("sha256") or "") != model_sha256:
        raise _policy_error(
            f"{context} was trained against a model digesting to "
            f"{declared_model.get('sha256')!r}; this task's model digests to "
            f"{model_sha256!r}.",
            reason="policy_model_mismatch",
            correction=(
                "The task and the model are two artifacts that only mean "
                "anything together. A policy trained on a mechanism whose "
                "geometry has since changed is a policy for a different "
                "robot."
            ),
            policy_model_sha256=str(declared_model.get("sha256") or ""),
            model_sha256=model_sha256,
        )

    channels = _task_channels(task)
    declared_channels = [str(name) for name in header.get("observations") or ()]
    if declared_channels != channels:
        raise _policy_error(
            f"{context} observes {len(declared_channels)} channels where this "
            f"task declares {len(channels)}.",
            reason="policy_channels_mismatch",
            correction=(
                "The observation vector is positional: the policy's first "
                "input is the task's first channel. Reordering the "
                "observations in the script changes what every weight means. "
                f"The task's channels are {', '.join(channels)}; the policy's "
                f"are {', '.join(declared_channels)}."
            ),
            task_channels=channels,
            policy_channels=declared_channels,
        )

    actions = list(task["actions"])
    declared_actions = header.get("actions")
    declared_actions = (
        list(declared_actions) if isinstance(declared_actions, (list, tuple)) else []
    )
    if len(declared_actions) != len(actions):
        raise _policy_error(
            f"{context} drives {len(declared_actions)} actuators where this "
            f"task declares {len(actions)}.",
            reason="policy_actions_mismatch",
            correction=(
                "One action is one actuator, in the order the task lists "
                "them. A policy with a different width was trained elsewhere."
            ),
            policy_actions=len(declared_actions),
            task_actions=len(actions),
        )
    for index, (declared, action) in enumerate(zip(declared_actions, actions)):
        entry = dict(declared) if isinstance(declared, Mapping) else {}
        for field in _POLICY_ACTION_FIELDS:
            wanted = action[field]
            found = entry.get(field)
            if not _same_action_field(found, wanted):
                raise _policy_error(
                    f"{context} action {index} declares {field}={found!r} "
                    f"where the task declares {wanted!r}.",
                    reason="policy_actions_mismatch",
                    correction=(
                        "The action table is copied from the bundle "
                        "verbatim, so a difference means the policy was "
                        "trained against a task whose actuators, units or "
                        "derived limits are not these. Retrain."
                    ),
                    action=index, field=str(field),
                    policy_value=found, task_value=wanted,
                )

    shapes = _policy_layers(header, context=context)
    if shapes[-1][1] != len(actions):
        raise _policy_error(
            f"{context} produces {shapes[-1][1]} outputs for {len(actions)} "
            "actuators.",
            reason="policy_network_malformed",
            correction=(
                "The last layer's width is the number of actions the task "
                "declares."
            ),
            outputs=shapes[-1][1], actions=len(actions),
        )
    network = dict(header["network"])
    wanted_scale, wanted_bias = _policy_action_map(task)
    for label, found, wanted in (
        ("output_scale", network.get("output_scale"), wanted_scale),
        ("output_bias", network.get("output_bias"), wanted_bias),
    ):
        values = [float(value) for value in found or ()]
        if len(values) != len(wanted) or any(
            abs(value - target) > POLICY_WITNESS_TOLERANCE * max(abs(target), 1.0)
            for value, target in zip(values, wanted)
        ):
            raise _policy_error(
                f"{context} declares network.{label}={values} where this "
                f"task's action ranges imply {wanted}.",
                reason="policy_output_range_mismatch",
                correction=(
                    "The output map is half-range and midpoint of each "
                    "action's own advertised bound, which the bundle derived "
                    "from the mechanism. A policy that scaled its outputs "
                    "differently is driving the actuator to a limit nobody "
                    "designed."
                ),
                field=label, policy_value=values, task_value=wanted,
            )

    evaluation = header.get("evaluation")
    evaluation = dict(evaluation) if isinstance(evaluation, Mapping) else {}
    witness_observations = list(evaluation.get("observations") or ())
    witness_actions = list(evaluation.get("actions") or ())
    if len(witness_observations) < MINIMUM_POLICY_WITNESS_SAMPLES:
        raise _policy_error(
            f"{context} records {len(witness_observations)} witness samples; "
            f"at least {MINIMUM_POLICY_WITNESS_SAMPLES} are required.",
            reason="policy_witness_missing",
            correction=(
                "The witness is what makes a policy checkable rather than "
                "trusted: the trainer records observation vectors and the "
                "actions its own network produced for them, and the engine "
                "recomputes those actions. Without it, an architecture the "
                "engine reads differently is a bad gait instead of a "
                "refusal."
            ),
            samples=len(witness_observations),
            minimum=MINIMUM_POLICY_WITNESS_SAMPLES,
        )
    if len(witness_observations) > MAXIMUM_POLICY_WITNESS_SAMPLES:
        raise _policy_error(
            f"{context} records {len(witness_observations)} witness samples; "
            f"the accepted maximum is {MAXIMUM_POLICY_WITNESS_SAMPLES}.",
            reason="policy_witness_missing",
            correction=(
                "The witness proves the forward pass agrees; it is not a "
                "dataset. A few dozen samples across the observation range "
                "is what it is for."
            ),
            samples=len(witness_observations),
            maximum=MAXIMUM_POLICY_WITNESS_SAMPLES,
        )
    if len(witness_actions) != len(witness_observations):
        raise _policy_error(
            f"{context} records {len(witness_observations)} witness "
            f"observations and {len(witness_actions)} witness actions.",
            reason="policy_witness_missing",
            correction="One recorded action vector per recorded observation.",
            observations=len(witness_observations),
            actions=len(witness_actions),
        )

    worst = 0.0
    worst_sample = -1
    worst_action = -1
    ranges = [
        max(float(action["high"]) - float(action["low"]), _TINY)
        for action in actions
    ]
    for sample, (observed, recorded) in enumerate(
        zip(witness_observations, witness_actions)
    ):
        produced = policy_forward(
            header, weights, observed, context=f"{context} witness {sample}"
        )
        expected_values = [float(value) for value in recorded]
        if len(expected_values) != len(produced):
            raise _policy_error(
                f"{context} witness {sample} records {len(expected_values)} "
                f"actions for {len(produced)} actuators.",
                reason="policy_witness_disagrees",
                correction="One recorded action per actuator, in task order.",
                sample=sample,
            )
        for index, (found, target) in enumerate(zip(produced, expected_values)):
            error = abs(found - target) / ranges[index]
            if error > worst:
                worst, worst_sample, worst_action = error, sample, index
    if worst > POLICY_WITNESS_TOLERANCE:
        raise _policy_error(
            f"{context} does not reproduce its own recorded actions: witness "
            f"{worst_sample}, action {worst_action}, relative error {worst:g} "
            f"against a tolerance of {POLICY_WITNESS_TOLERANCE:g}.",
            reason="policy_witness_disagrees",
            correction=(
                "The weights survived the trip and the engine reads the "
                "network differently -- a layer order, a bias layout or an "
                "activation. This is refused rather than run, because a "
                "policy the engine evaluates differently from the trainer is "
                "a different network and would look like a badly trained one."
            ),
            witness=worst_sample, action=worst_action,
            error=float(worst), tolerance=POLICY_WITNESS_TOLERANCE,
        )

    parameters = sum(inputs * outputs + outputs for inputs, outputs in shapes)
    return {
        "schema": POLICY_SCHEMA,
        "label": str(header.get("label") or ""),
        "task_sha256": str(task_sha256),
        "model_sha256": model_sha256,
        "observation_channels": list(channels),
        "action_count": len(actions),
        "layers": [[inputs, outputs] for inputs, outputs in shapes],
        "activation": str(network.get("activation") or ""),
        "output": str(network.get("output") or ""),
        "parameters": int(parameters),
        "witness_samples": len(witness_observations),
        "witness_error": float(worst),
        "witness_tolerance": POLICY_WITNESS_TOLERANCE,
        "training": dict(header.get("training") or {}),
    }


# ---------------------------------------------------------------------------
# The rollout (docs/MUJOCO.md M8, ADR-071).
#
# The whole arc's last step, and the smallest: the policy drives the episode
# loop M6 already wrote, and what comes out is a trace in the schema the
# shell has played since ADR-050. A swap, not a discovery.
# ---------------------------------------------------------------------------

#: What a rollout may leave behind, on the same two axes ``api.dynamics``
#: bounds a trace on: frames are what the artifact carries, poses are what
#: the shell bakes into keyframes. The solver's own cost is bounded
#: separately by ``_episode_schedule`` -- an episode is budgeted before it
#: runs, and these are re-checked against the frames that really came out.
MAXIMUM_TRACE_FRAMES = 10_000
MAXIMUM_TRACE_POSES = 100_000


def rollout_policy(
    model: Any,
    task: Mapping[str, Any],
    container: Mapping[str, Any],
    *,
    components: Sequence[str],
    frames_per_second: int,
    seed: int | None = None,
    context: str = "this rollout",
) -> dict[str, Any]:
    """One trained policy, driving one episode, as trace frames.

    The end of the arc, and it adds no physics: :func:`evaluate_episode` runs
    the episode exactly as M6 wrote it, :func:`policy_forward` supplies the
    action exactly as M7 wrote it, and what is new here is only *sampling* --
    turning control steps into the frames ``cadex_animate`` has baked since
    ADR-050.

    Three details are contract rather than choice, and all three are
    ``simulate``'s rather than this function's:

    * **The frame schema is copied, not re-derived.** An untimed ``input``
      frame first, then ``solver_output`` frames carrying ``position_mm`` and
      ``rotation_xyzw`` for every component in every frame. The shell reads
      exactly this, and a rollout that wrote a fourth dialect of it would be
      a bake the viewport declines with nothing to point at.
    * **Every component is in every frame** (hazard 5). ``cadex_animate``
      skips a missing pose and Blender interpolates the gap, so a part that
      stopped moving would look like a physics result.
    * **``frames_per_second`` divides ``control_hz`` exactly**, which is the
      control-step form of ``simulate``'s rule that a whole number of solver
      steps lands on each frame. A policy picks its own control rate, so this
      cannot be defaulted away; phase 0 measured what 50 Hz played at 60 fps
      does, which is to put frames 1, 2 and 4 between two different actions.

    **Zero new conversion sites** (hazard 1's sixth payment). The action
    leaves ``policy_forward`` in the unit the bundle advertised and goes
    through the ``clamp then x scale`` the episode loop has performed since
    M6; the pose goes through :func:`vector_mm` and
    :func:`quaternion_xyzw_from_wxyz`, which are the same two calls
    ``simulate`` makes. ``test_dynamics_units`` greps this module's callers
    for a third.

    Returns the frames, the sampling schedule, and a summary of the episode
    the frames came from -- total reward, per-term totals, step count,
    whether it terminated or ran its horizon, and the seed and draws behind
    it.
    """

    mujoco = _mujoco_module()
    episode_schedule = task["episode"]
    control_hz = int(episode_schedule["control_hz"])
    control_interval = float(episode_schedule["control_interval_s"])
    max_steps = int(episode_schedule["max_steps"])

    rate = int(frames_per_second)
    if rate < 1 or control_hz % rate:
        divisors = ", ".join(
            str(value) for value in range(1, control_hz + 1) if not control_hz % value
        )
        raise DynamicsError(
            f"{context} samples at {rate} frames a second from a task that "
            f"acts at {control_hz} Hz, which is not a whole number of control "
            "steps a frame.",
            reason="frame_rate_indivisible",
            correction=(
                "A trace frame is taken at a control-step boundary, the same "
                "way a simulation's frame is taken at a solver-step boundary: "
                "a frame between two actions would depend on floating-point "
                "accumulation. This task can be played at "
                f"{divisors} frames a second."
            ),
            observed={"frames_per_second": rate, "control_hz": control_hz},
        )
    steps_per_frame = control_hz // rate

    names = [str(name) for name in components]
    body_ids: dict[str, int] = {}
    for name in names:
        found = int(mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, name))
        if found < 0:
            raise DynamicsError(
                f"{context} plays a component named {name!r}, and the model it "
                "reads carries no body of that name.",
                reason="rollout_component_missing",
                correction=(
                    "The rollout resolves poses by component name against the "
                    "exported model, so a component the export did not carry "
                    "cannot be played. Export the model from the same "
                    "assembly the rollout names."
                ),
                observed={"component": name, "components": names},
            )
        body_ids[name] = found

    # Bounded before it runs, on the two axes api.dynamics bounds a trace on.
    # The horizon is the worst case: an episode that terminates early
    # produces fewer frames, never more.
    frames_expected = max_steps // steps_per_frame + 2
    poses_expected = frames_expected * len(names)
    if frames_expected > MAXIMUM_TRACE_FRAMES or poses_expected > MAXIMUM_TRACE_POSES:
        raise DynamicsError(
            f"{context} would produce up to {frames_expected} frames and "
            f"{poses_expected} component poses; the accepted maxima are "
            f"{MAXIMUM_TRACE_FRAMES} and {MAXIMUM_TRACE_POSES}.",
            reason="rollout_budget_exceeded",
            correction=(
                "Lower frames_per_second, or shorten the task's "
                "episode_seconds. What the solver does is budgeted "
                "separately, when the task bundle is built."
            ),
            observed={
                "frames": frames_expected,
                "poses": poses_expected,
                "components": len(names),
                "maximum_frames": MAXIMUM_TRACE_FRAMES,
                "maximum_poses": MAXIMUM_TRACE_POSES,
            },
        )

    header = container["header"]
    weights = container["weights"]

    def _actions(_step: int, observation: Mapping[str, float]) -> list[float]:
        return policy_forward(header, weights, observation, context=context)

    def _placements(data: Any) -> dict[str, dict[str, list[float]]]:
        poses = {
            name: {
                "position_mm": vector_mm(data.xpos[body_ids[name]]),
                "rotation_xyzw": quaternion_xyzw_from_wxyz(
                    quaternion_normalised(data.xquat[body_ids[name]])
                ),
            }
            for name in names
        }
        # Hazard 5, copied from ``simulate`` rather than shared with it: a
        # component missing from one frame is not an error the shell reports
        # -- cadex_animate skips it and Blender interpolates the gap, so a
        # part that stops moving looks like a physics result.
        if set(poses) != set(names):
            raise DynamicsError(
                "A rollout frame is missing a component pose.",
                reason="incomplete_frame",
                observed={"expected": names, "observed": sorted(poses)},
            )
        return poses

    def _sample(step: int, data: Any, final: bool) -> dict[str, Any] | None:
        # The last state is always recorded, however the episode ended: a
        # trace that stopped at the previous frame boundary would show a
        # mechanism that had not yet fallen over.
        if step % steps_per_frame and not final:
            return None
        return {
            "frame_kind": "solver_output",
            "nominal_time_s": step * control_interval,
            "component_placements": _placements(data),
        }

    episode = evaluate_episode(
        model, task, actions=_actions, sample=_sample, seed=seed
    )
    sampled = list(episode["samples"])
    if not sampled:
        raise DynamicsError(
            f"{context} produced no frames.",
            reason="rollout_produced_no_frames",
            observed={"steps": int(episode["step_count"])},
        )

    # The input frame is the reset pose, untimed, in front of the solved
    # frame at t=0 -- ``simulate``'s first contract detail, and the one M1
    # found by running its prototype against ``cadex_animate`` rather than by
    # reading it.
    frames: list[dict[str, Any]] = [
        {
            "frame_index": 0,
            "frame_kind": "input",
            "nominal_time_s": None,
            "component_placements": sampled[0]["component_placements"],
        }
    ]
    for record in sampled:
        frames.append({"frame_index": len(frames), **record})

    totals: dict[str, float] = {}
    for step in episode["steps"]:
        for term in step["reward_terms"]:
            label = str(term["label"])
            totals[label] = totals.get(label, 0.0) + float(term["weighted"])

    return {
        "frames": frames,
        "frames_per_second": rate,
        "steps_per_frame": steps_per_frame,
        "frame_interval_s": steps_per_frame * control_interval,
        # Read off the reloaded model rather than off the bundle: these are
        # facts about the file that ran, and the file is the claim.
        "solver_step_s": float(model.opt.timestep),
        "solver_tolerance": float(model.opt.tolerance),
        "episode": {
            "label": str(episode["label"]),
            "step_count": int(episode["step_count"]),
            "episode_seconds": episode["step_count"] * control_interval,
            "control_hz": control_hz,
            "total_reward": float(episode["total_reward"]),
            "reward_totals": [
                {"label": label, "total": value} for label, value in totals.items()
            ],
            "terminated_step": episode["terminated_step"],
            "termination": str(episode["termination"]),
            "truncated": bool(episode["truncated"]),
            "seed": episode["seed"],
            "randomisation": list(episode["randomisation"]),
        },
    }
