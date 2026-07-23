# SPDX-License-Identifier: LGPL-2.1-or-later

"""Internal native geometry builders used by focused Sketcher operations."""

from __future__ import annotations

import math
from numbers import Real
from typing import Any, Callable

from .common import (
    active_response,
    get_sketch,
    no_sketch,
    run_freecad_transaction,
    vector2,
)


GEOMETRY_KINDS = ("line", "point", "arc", "circle", "ellipse", "bspline", "polyline")


def _error(message: str) -> dict[str, Any]:
    return {"ok": False, "error": message, "retry_same_call": False}


def _number_arg(name: str, value: Any) -> tuple[float | None, dict[str, Any] | None]:
    if value is None:
        return None, _error(f"{name} is required and must be an explicit number.")
    if isinstance(value, bool) or not isinstance(value, Real):
        return None, _error(f"{name} must be a number.")
    return float(value), None


def _bool_arg(name: str, value: Any) -> tuple[bool | None, dict[str, Any] | None]:
    if value is None or not isinstance(value, bool):
        return None, _error(f"{name} is required and must be true or false.")
    return value, None


def _validated_points(
    points: list[Any] | None,
    kind: str,
    minimum: int,
    exact: int | None = None,
) -> tuple[list[list[float]] | None, dict[str, Any] | None]:
    values = points or []
    if exact is not None and len(values) != exact:
        return None, _error(
            f"kind='{kind}' requires exactly {exact} point(s) in 'points'; got {len(values)}."
        )
    if len(values) < minimum:
        return None, _error(
            f"kind='{kind}' requires at least {minimum} points in 'points'; got {len(values)}."
        )
    normalized: list[list[float]] = []
    for index, raw in enumerate(values):
        if not isinstance(raw, (list, tuple)) or len(raw) != 2:
            return None, _error(
                f"kind='{kind}' point {index} must be exactly [x, y] in sketch-local mm. "
                f"Got {raw!r}. Coordinates must use the exact [x, y] form."
            )
        if isinstance(raw[0], bool) or isinstance(raw[1], bool):
            return None, _error(
                f"kind='{kind}' point {index} must contain numeric x and y coordinates."
            )
        try:
            normalized.append([float(raw[0]), float(raw[1])])
        except (TypeError, ValueError):
            return None, _error(
                f"kind='{kind}' point {index} must contain numeric x and y coordinates."
            )
    return normalized, None


def _validated_center(
    center: Any, kind: str
) -> tuple[list[float] | None, dict[str, Any] | None]:
    if not isinstance(center, (list, tuple)) or len(center) != 2:
        return None, _error(
            f"kind='{kind}' requires center=[x, y] in sketch-local mm. "
            f"Got {center!r}. Coordinates must use the exact [x, y] form."
        )
    if isinstance(center[0], bool) or isinstance(center[1], bool):
        return None, _error(
            f"kind='{kind}' center must contain numeric x and y coordinates."
        )
    try:
        return [float(center[0]), float(center[1])], None
    except (TypeError, ValueError):
        return None, _error(
            f"kind='{kind}' center must contain numeric x and y coordinates."
        )


def run(
    service: Any,
    sketch_name: str | None = None,
    kind: str = "",
    points: list[list[float]] | None = None,
    center: list[float] | None = None,
    radius: float | None = None,
    start_angle_degrees: float | None = None,
    end_angle_degrees: float | None = None,
    major_radius: float | None = None,
    minor_radius: float | None = None,
    angle_degrees: float | None = None,
    closed: bool | None = None,
    constrain_points: bool | None = None,
    interpolate: bool | None = None,
    periodic: bool | None = None,
    expose_internal_geometry: bool | None = None,
    construction: bool | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    if kwargs:
        unsupported = ", ".join(sorted(str(key) for key in kwargs))
        return _error(f"Unsupported internal geometry parameter(s): {unsupported}.")
    construction_value, error = _bool_arg("construction", construction)
    if error is not None:
        return error
    assert construction_value is not None
    kind_value = str(kind or "").strip().lower()
    if kind_value not in GEOMETRY_KINDS:
        return _error(
            f"Unknown geometry kind: {kind!r}. Expected one of: {', '.join(GEOMETRY_KINDS)}."
        )
    sketch = get_sketch(service, sketch_name)
    if sketch is None:
        return {
            **no_sketch(sketch_name),
            "error": "No Sketcher sketch is currently open for editing.",
            "retry_same_call": False,
        }

    builder: Callable[[Any], dict[str, Any]]

    if kind_value == "line":
        line_points, error = _validated_points(points, "line", 2, exact=2)
        if error is not None:
            return error
        assert line_points is not None

        def builder(target: Any) -> dict[str, Any]:
            import FreeCAD as App
            import Part

            geometry_index = target.addGeometry(
                Part.LineSegment(
                    App.Vector(line_points[0][0], line_points[0][1], 0.0),
                    App.Vector(line_points[1][0], line_points[1][1], 0.0),
                ),
                construction_value,
            )
            return {
                "geometry_index": int(geometry_index),
                "geometry_added": 1,
                "start": line_points[0],
                "end": line_points[1],
            }

    elif kind_value == "point":
        point_values, error = _validated_points(points, "point", 1, exact=1)
        if error is not None:
            return error
        assert point_values is not None

        def builder(target: Any) -> dict[str, Any]:
            import FreeCAD as App
            import Part

            geometry_index = target.addGeometry(
                Part.Point(App.Vector(point_values[0][0], point_values[0][1], 0.0)),
                construction_value,
            )
            return {
                "geometry_index": int(geometry_index),
                "geometry_added": 1,
                "point": point_values[0],
            }

    elif kind_value == "arc":
        center_value, error = _validated_center(center, "arc")
        if error is not None:
            return error
        assert center_value is not None
        radius_value, error = _number_arg("radius", radius)
        if error is not None:
            return error
        start_angle_value, error = _number_arg(
            "start_angle_degrees", start_angle_degrees
        )
        if error is not None:
            return error
        end_angle_value, error = _number_arg("end_angle_degrees", end_angle_degrees)
        if error is not None:
            return error
        assert radius_value is not None
        assert start_angle_value is not None
        assert end_angle_value is not None
        if radius_value <= 0:
            return _error("kind='arc' requires a positive 'radius'.")
        if abs(end_angle_value - start_angle_value) < 1e-9:
            return _error("Arc start and end angles must differ.")

        def builder(target: Any) -> dict[str, Any]:
            import FreeCAD as App
            import Part

            circle = Part.Circle(
                App.Vector(center_value[0], center_value[1], 0.0),
                App.Vector(0.0, 0.0, 1.0),
                radius_value,
            )
            geometry_index = target.addGeometry(
                Part.ArcOfCircle(
                    circle,
                    math.radians(start_angle_value),
                    math.radians(end_angle_value),
                ),
                construction_value,
            )
            return {
                "geometry_index": int(geometry_index),
                "geometry_added": 1,
                "center": center_value,
                "radius": radius_value,
                "start_angle_degrees": start_angle_value,
                "end_angle_degrees": end_angle_value,
            }

    elif kind_value == "circle":
        center_value, error = _validated_center(center, "circle")
        if error is not None:
            return error
        assert center_value is not None
        radius_value, error = _number_arg("radius", radius)
        if error is not None:
            return error
        assert radius_value is not None
        if radius_value <= 0:
            return _error("kind='circle' requires a positive 'radius'.")

        def builder(target: Any) -> dict[str, Any]:
            import FreeCAD as App
            import Part

            geometry_index = target.addGeometry(
                Part.Circle(
                    App.Vector(center_value[0], center_value[1], 0.0),
                    App.Vector(0.0, 0.0, 1.0),
                    radius_value,
                ),
                construction_value,
            )
            return {
                "geometry_index": int(geometry_index),
                "created_geometry_indices": [int(geometry_index)],
                "geometry_added": 1,
                "center": center_value,
                "radius": radius_value,
            }

    elif kind_value == "ellipse":
        center_value, error = _validated_center(center, "ellipse")
        if error is not None:
            return error
        assert center_value is not None
        major_value, error = _number_arg("major_radius", major_radius)
        if error is not None:
            return error
        minor_value, error = _number_arg("minor_radius", minor_radius)
        if error is not None:
            return error
        angle_value, error = _number_arg("angle_degrees", angle_degrees)
        if error is not None:
            return error
        assert major_value is not None
        assert minor_value is not None
        assert angle_value is not None
        if major_value <= 0 or minor_value <= 0:
            return _error("Ellipse radii must be positive.")
        if minor_value > major_value:
            return _error("Ellipse 'minor_radius' must not exceed 'major_radius'.")

        def builder(target: Any) -> dict[str, Any]:
            import FreeCAD as App
            import Part

            ellipse = Part.Ellipse(
                App.Vector(center_value[0], center_value[1], 0.0),
                major_value,
                minor_value,
            )
            angle = math.radians(angle_value)
            ellipse.XAxis = App.Vector(math.cos(angle), math.sin(angle), 0.0)
            geometry_index = target.addGeometry(ellipse, construction_value)
            return {
                "geometry_index": int(geometry_index),
                "geometry_added": 1,
                "center": center_value,
                "major_radius": major_value,
                "minor_radius": minor_value,
                "angle_degrees": angle_value,
            }

    elif kind_value == "bspline":
        spline_points, error = _validated_points(points, "bspline", 2)
        if error is not None:
            return error
        assert spline_points is not None
        interpolate_value, error = _bool_arg("interpolate", interpolate)
        if error is not None:
            return error
        periodic_value, error = _bool_arg("periodic", periodic)
        if error is not None:
            return error
        assert interpolate_value is not None
        assert periodic_value is not None
        expose_value = True if expose_internal_geometry is None else expose_internal_geometry
        if not isinstance(expose_value, bool):
            return _error("expose_internal_geometry must be true or false.")
        minimum_points = 5 if periodic_value else 3
        if len(spline_points) < minimum_points:
            return _error(
                f"A {'periodic' if periodic_value else 'non-periodic'} B-spline requires "
                f"at least {minimum_points} points; got {len(spline_points)}."
            )
        tolerance = 1e-9
        for index in range(1, len(spline_points)):
            previous = spline_points[index - 1]
            current = spline_points[index]
            if (
                math.hypot(current[0] - previous[0], current[1] - previous[1])
                <= tolerance
            ):
                return _error(
                    f"B-spline points {index - 1} and {index} are coincident. "
                    "Remove duplicate consecutive points."
                )
        if periodic_value:
            first = spline_points[0]
            last = spline_points[-1]
            if math.hypot(last[0] - first[0], last[1] - first[1]) <= tolerance:
                return _error(
                    "Do not repeat the first point at the end of a periodic B-spline; "
                    "FreeCAD closes periodic curves natively."
                )
        distinct_points = {
            (round(point[0], 9), round(point[1], 9)) for point in spline_points
        }
        if len(distinct_points) < minimum_points:
            return _error(
                f"B-spline requires at least {minimum_points} distinct points; "
                f"got {len(distinct_points)}."
            )

        def builder(target: Any) -> dict[str, Any]:
            import Part

            vectors = [
                vector2(raw, index, "B-spline")
                for index, raw in enumerate(spline_points)
            ]
            curve = Part.BSplineCurve()
            if interpolate_value:
                curve.interpolate(vectors, PeriodicFlag=periodic_value)
            else:
                curve.buildFromPoles(vectors, periodic_value)
            geometry_index = target.addGeometry(curve, construction_value)
            internal_result = (
                target.exposeInternalGeometry(int(geometry_index))
                if expose_value
                else {
                    "source_geometry_index": int(geometry_index),
                    "created_count": 0,
                    "created": [],
                }
            )
            if not isinstance(internal_result, dict):
                raise RuntimeError(
                    "FreeCAD exposeInternalGeometry() did not return structured geometry data."
                )
            internal = [
                dict(item)
                for item in list(internal_result.get("created") or [])
                if isinstance(item, dict)
            ]
            created_indices = [int(geometry_index)] + [
                int(item["geometry_index"]) for item in internal
            ]
            return {
                "geometry_index": int(geometry_index),
                "primary_geometry_index": int(geometry_index),
                "created_geometry_indices": created_indices,
                "primary_geometry_added": 1,
                "geometry_added": len(created_indices),
                "point_count": len(vectors),
                "interpolate": interpolate_value,
                "periodic": periodic_value,
                "internal_geometry_exposed": expose_value,
                "internal_geometry": internal,
            }

    else:  # polyline
        poly_points, error = _validated_points(points, "polyline", 2)
        if error is not None:
            return error
        assert poly_points is not None
        closed_value, error = _bool_arg("closed", closed)
        if error is not None:
            return error
        constrain_points_value, error = _bool_arg("constrain_points", constrain_points)
        if error is not None:
            return error
        assert closed_value is not None
        assert constrain_points_value is not None

        def builder(target: Any) -> dict[str, Any]:
            import Part
            import Sketcher

            before_geometry = len(getattr(target, "Geometry", []))
            before_constraints = len(getattr(target, "Constraints", []))
            vectors = [
                vector2(raw, index, "Polyline") for index, raw in enumerate(poly_points)
            ]
            segments = [
                Part.LineSegment(vectors[index], vectors[index + 1])
                for index in range(len(vectors) - 1)
            ]
            if closed_value:
                segments.append(Part.LineSegment(vectors[-1], vectors[0]))
            target.addGeometry(segments, construction_value)
            constraints = [
                Sketcher.Constraint(
                    "Coincident",
                    before_geometry + index,
                    2,
                    before_geometry + index + 1,
                    1,
                )
                for index in range(len(segments) - 1)
            ]
            if closed_value and len(segments) > 1:
                constraints.append(
                    Sketcher.Constraint(
                        "Coincident",
                        before_geometry + len(segments) - 1,
                        2,
                        before_geometry,
                        1,
                    )
                )
            dimensional_constraints = []
            point_constraint_targets = []
            if constrain_points_value:
                for point_index, vector in enumerate(vectors):
                    if point_index < len(vectors) - 1:
                        geometry_index = before_geometry + point_index
                        point_pos = 1
                    else:
                        geometry_index = before_geometry + point_index - 1
                        point_pos = 2
                    dimensional_constraints.extend(
                        [
                            Sketcher.Constraint(
                                "DistanceX", geometry_index, point_pos, float(vector.x)
                            ),
                            Sketcher.Constraint(
                                "DistanceY", geometry_index, point_pos, float(vector.y)
                            ),
                        ]
                    )
                    point_constraint_targets.append(
                        {
                            "point_index": point_index,
                            "geometry_index": geometry_index,
                            "point_position": point_pos,
                            "x": float(vector.x),
                            "y": float(vector.y),
                        }
                    )
            constraints.extend(dimensional_constraints)
            if constraints:
                target.addConstraint(constraints)
            return {
                "geometry_index": before_geometry,
                "geometry_added": len(segments),
                "constraints_added": len(constraints),
                "coincident_constraints_added": len(constraints)
                - len(dimensional_constraints),
                "point_dimension_constraints_added": len(dimensional_constraints),
                "constraint_count_before": before_constraints,
                "constraint_count": len(getattr(target, "Constraints", [])),
                "closed": closed_value,
                "constrain_points": constrain_points_value,
                "point_constraint_targets": point_constraint_targets,
            }

    def _add() -> dict[str, Any]:
        import FreeCAD as App

        target = get_sketch(service, sketch.Name)
        if target is None:
            raise RuntimeError(f"Sketch not found: {sketch.Name}")
        before_count = len(getattr(target, "Geometry", []))
        payload = builder(target)
        result: dict[str, Any] = {
            "sketch": target.Name,
            "kind": kind_value,
            "geometry_count_before": before_count,
            "geometry_count": len(getattr(target, "Geometry", [])),
            "construction": construction_value,
        }
        result.update(payload)
        return result

    return active_response(
        service,
        sketch,
        run_freecad_transaction(f"Add Sketcher {kind_value}", _add),
    )
