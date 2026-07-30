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
from typing import Any, Iterable, Mapping, Sequence

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
    "rotation_angle_between",
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
    # A screw and a rack-and-pinion are a rotation plus a coupling to the
    # companion slider FreeCAD already insists exists (the worker's
    # _coupled_joint_issues refuses the graph without it), so the body
    # attachment they contribute is a plain hinge.
    "screw": {"tree": ("hinge",), "closure": "connect", "coupling": True},
    "rack_pinion": {"tree": ("hinge",), "closure": "connect", "coupling": True},
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

#: What a one-sided limit becomes. MuJoCo's ``range`` needs both ends, so
#: the open side is pushed out to somewhere the mechanism cannot reach: a
#: hundred turns, or a kilometre. Recorded per joint in the evidence rather
#: than quietly substituted -- a limit the model never meets is still a
#: number somebody may later wonder about.
_OPEN_ANGLE_MARGIN_RADIANS = 100.0 * 2.0 * math.pi
_OPEN_LENGTH_MARGIN_M = 1000.0

#: The default solver step. Deliberately not a script parameter in M2: one
#: number to be wrong about while the translator is being proved, and M3
#: splits solver step from trace step properly.
DEFAULT_TIME_STEP_S = 0.002


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
        if closure["closure_kind"] == "weld":
            data = [0.0] * 11
            data[10] = 1.0  # torquescale: the rotational rows are the point
            equality.data = data

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
    qpos = _solved_qpos(mujoco, model, tree, placements, joint_records)
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
        "qpos_solved": qpos,
        "placements": placements,
        "time_step_s": float(time_step_s),
        "gravity_m_s2": list(gravity_m_s2),
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


def _solved_qpos(
    mujoco: Any,
    model: Any,
    tree: Mapping[str, Any],
    placements: Mapping[str, Sequence[float]],
    joint_records: Sequence[Mapping[str, Any]],
) -> list[float]:
    """The configuration that reproduces FreeCAD's solved placements.

    Derived by inversion from the solved placements, joint by joint, rather
    than read back out of the model it is about to be checked against.
    """

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
        transform = joint_transform(
            placements[str(body["parent"])],
            body["parent_local_matrix"],
            placements[name],
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
        values = list(coordinates["values"])
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


def _ordered_names(values: Iterable[Any]) -> list[str]:
    """Script order, deduplicated -- never a set, never id()-keyed."""

    return list(dict.fromkeys(str(item) for item in values))
