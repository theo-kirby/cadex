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
