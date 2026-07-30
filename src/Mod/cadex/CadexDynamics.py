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
    # the model
    "build_model",
    "simulate",
    "model_evidence",
    "DEFAULT_TIME_STEP_S",
    "CLOSURE_RESIDUAL_MM",
    "CLOSURE_RESIDUAL_RADIANS",
    "CLOSURE_EQUALITY_TOLERANCE",
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

    native_bodies: dict[str, Any] = {"": spec.worldbody}
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
    qpos = _solved_qpos(
        mujoco, model, tree, placements, joint_records, solved_values
    )
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
        "mujoco_version": str(getattr(mujoco, "__version__", "unknown")),
    }


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
    )
    model = built["model"]
    names = [str(component["name"]) for component in components]
    body_ids = {
        name: mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, name)
        for name in names
    }

    data = mujoco.MjData(model)
    data.qpos[:] = built["qpos_solved"]
    mujoco.mj_forward(model, data)

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
    for sample in range(sample_count + 1):
        if sample:
            for _step in range(steps_per_sample):
                mujoco.mj_step(model, data)
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
        "evidence": model_evidence(built, components),
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
    built: Mapping[str, Any], components: Sequence[Mapping[str, Any]]
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
    }


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


def _verify_compiled_inertia(
    mujoco: Any,
    model: Any,
    inertials: Mapping[str, Mapping[str, Any]],
    tree: Mapping[str, Any],
) -> None:
    """The compiler may not have touched the numbers we gave it.

    ``balanceinertia`` is asserted off above; this asserts the *effect* of
    it being off, which is the assertion that survives a MuJoCo upgrade
    changing a default. It compares the compiled principal moments against
    the ones computed from OCCT, per body, and refuses a model whose inertia
    was rewritten -- silently rewritten exact inertia is the failure this
    whole slice exists to avoid.
    """

    for body in tree["bodies"]:
        name = str(body["name"])
        body_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, name)
        expected = inertials[name]
        mass = float(model.body_mass[body_id])
        if abs(mass - float(expected["mass_kg"])) > 1.0e-12 * max(
            1.0, abs(float(expected["mass_kg"]))
        ):
            raise DynamicsError(
                f"MuJoCo's compiler changed body {name!r}'s mass from "
                f"{expected['mass_kg']:.12g} to {mass:.12g} kg.",
                reason="compiler_rewrote_inertia",
                observed={"body": name},
            )
        compiled = sorted(float(value) for value in model.body_inertia[body_id])
        principal = list(expected["principal_inertia_kg_m2"])
        scale = max(principal[2], 1.0e-30)
        drift = max(
            abs(compiled[index] - principal[index]) / scale for index in range(3)
        )
        if drift > 1.0e-9:
            raise DynamicsError(
                f"MuJoCo's compiler rewrote body {name!r}'s inertia: asked for "
                f"{principal}, compiled {compiled} kg·m².",
                reason="compiler_rewrote_inertia",
                correction=(
                    "balanceinertia, boundinertia and boundmass must stay off. "
                    "Exact OCCT inertia is what this model is for."
                ),
                observed={"body": name, "asked": principal, "compiled": compiled},
            )


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
