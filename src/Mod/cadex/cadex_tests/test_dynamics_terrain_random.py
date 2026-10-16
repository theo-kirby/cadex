# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""A seeded random box course, re-drawn per episode in the trainer (ADR-717).

``terrain={"form": "boxes", ..., "random": {...}}`` draws its steps, slopes
and bumps from a seed instead of listing them. Course 0 is the one the model
carries; ``pool`` holds every course of the draw as features, and the model
has one box geom per box of the pool's fullest course, the rest parked under
the plane. The trainer rebuilds each pooled course's boxes (its own copy of
the engine's builder, held equal here), and on every reset places one in
each environment's terrain geoms and reads it in the height scan.
"""

from __future__ import annotations

import math

import pytest

import CadexDynamics as dyn
from test_dynamics_policy_trainer import _trainer_module

#: A 6 m course: steps, slopes and bumps, a small pool.
RANDOM_COURSE = {
    "form": "boxes",
    "x_range_mm": [-500.0, 6000.0],
    "y_range_mm": [-800.0, 800.0],
    "random": {"seed": 7, "courses": 6, "step_mm": [20.0, 80.0],
               "grade_deg": [5.0, 15.0], "bump_mm": [10.0, 40.0], "bumps": 4},
}


def _descriptor(course=RANDOM_COURSE):
    return dyn.terrain_grid(course)["descriptor"]


# -- the draw, pure ---------------------------------------------------------

def test_a_seed_draws_the_same_pool_and_course_zero_is_the_models() -> None:
    first, second = _descriptor(), _descriptor()
    assert first == second
    assert first["kind"] == "boxes" and len(first["pool"]) == 6
    assert first["pool"][0]["features"] == first["features"]
    assert first["pool"][0]["boxes"] == len(first["boxes"])
    assert first["slots"] == max(course["boxes"] for course in first["pool"])
    assert first["random"]["algorithm"] == dyn.TERRAIN_RANDOM_ALGORITHM
    assert first["scale"] == dyn.length_m(1.0)
    assert len({repr(course["features"]) for course in first["pool"]}) == 6
    other = _descriptor({**RANDOM_COURSE, "random": {**RANDOM_COURSE["random"], "seed": 8}})
    assert other["features"] != first["features"]


def test_every_pooled_course_is_a_valid_course_in_its_bounds() -> None:
    spec = RANDOM_COURSE["random"]
    descriptor = _descriptor()
    for course in descriptor["pool"]:
        features = course["features"]
        built = dyn.terrain_boxes(features, RANDOM_COURSE["x_range_mm"], RANDOM_COURSE["y_range_mm"])
        assert built["lowest_mm"] == course["lowest_mm"]
        assert built["highest_mm"] == course["highest_mm"]
        assert dyn.terrain_box_ground_mm(built, 0.0, 0.0) == 0.0
        kinds = {feature["kind"] for feature in features}
        assert kinds <= {"step", "slope", "bump"} and "bump" in kinds
        level, last_end = 0.0, dyn.TERRAIN_RANDOM_DEFAULTS["clear_mm"]
        for feature in features:
            if feature["kind"] == "step":
                assert spec["step_mm"][0] <= abs(feature["height_mm"]) <= spec["step_mm"][1]
                start, end, rise = feature["x_mm"], feature["x_mm"], feature["height_mm"]
            elif feature["kind"] == "slope":
                assert spec["grade_deg"][0] <= abs(feature["grade_deg"]) <= spec["grade_deg"][1]
                start, end = feature["from_x_mm"], feature["to_x_mm"]
                rise = (end - start) * math.tan(math.radians(feature["grade_deg"]))
            else:
                assert spec["bump_mm"][0] <= feature["height_mm"] <= spec["bump_mm"][1]
                assert feature["x_mm"] - feature["radius_mm"] / 2.0 >= 500.0
                continue
            # A flat run before each, and signed back towards z = 0.
            assert start - last_end >= dyn.TERRAIN_RANDOM_DEFAULTS["run_mm"][0]
            if abs(level) > dyn.TERRAIN_FLAT_MM:
                assert rise * level < 0.0
            level, last_end = level + rise, end
            assert end < RANDOM_COURSE["x_range_mm"][1]


@pytest.mark.parametrize(
    ("change", "reason"),
    [
        ({"form": "heightfield"}, "malformed_terrain"),
        ({"features": [{"kind": "step", "x_mm": 400.0, "height_mm": 40.0}]}, "malformed_terrain"),
        ({"random": {"seed": 1, "step_mm": [20.0, 80.0], "colour": "red"}}, "malformed_terrain"),
        ({"random": {"seed": 1}}, "malformed_terrain"),
        ({"random": {"seed": 1, "step_mm": [80.0, 20.0]}}, "malformed_terrain"),
        ({"random": {"seed": 1, "grade_deg": [5.0, 60.0]}}, "malformed_terrain"),
        ({"random": {"seed": 1, "step_mm": [20.0, 80.0], "run_mm": [10.0, 100.0]}},
         "malformed_terrain"),
        ({"random": {"seed": 1, "step_mm": [20.0, 80.0], "clear_mm": 0.0}}, "malformed_terrain"),
        ({"random": {"seed": 1, "step_mm": [20.0, 80.0], "courses": 0}}, "malformed_terrain"),
        ({"random": {"seed": 1, "step_mm": [20.0, 80.0], "courses": 65}}, "terrain_too_large"),
        ({"x_range_mm": [-500.0, 700.0], "random": {"seed": 1, "step_mm": [20.0, 80.0]}},
         "terrain_is_flat"),
    ],
)
def test_a_random_course_it_cannot_draw_is_refused_with_its_reason(change, reason) -> None:
    with pytest.raises(dyn.DynamicsError) as caught:
        dyn.terrain_grid({**RANDOM_COURSE, **change})
    assert caught.value.reason == reason
    assert caught.value.correction


def test_the_trainers_box_builder_is_the_engines_on_every_pooled_course() -> None:
    numpy = pytest.importorskip("numpy")
    module = _trainer_module()
    descriptor = _descriptor()
    for name in ("TERRAIN_BASE_MM", "TERRAIN_FLAT_MM", "TERRAIN_RAMP_HALF_THICKNESS_MM",
                 "TERRAIN_PARKED_DEPTH_MM", "TERRAIN_PARKED_HALF_MM"):
        assert getattr(module, name) == getattr(dyn, name), name
    for course in descriptor["pool"]:
        engine = dyn.terrain_boxes(course["features"], descriptor["x_range_mm"],
                                   descriptor["y_range_mm"])
        boxes = module.course_boxes(course["features"], descriptor["x_range_mm"],
                                    descriptor["y_range_mm"])
        assert boxes == engine["boxes"]
        placed = module.course_geoms(boxes, course["lowest_mm"], descriptor["slots"],
                                     descriptor["scale"])
        expected = dyn.terrain_box_geoms(engine["boxes"], course["lowest_mm"], descriptor["slots"])
        assert set(placed) == set(expected)
        for key in expected:
            assert numpy.allclose(placed[key], expected[key], rtol=0.0, atol=1e-12), key


# -- the model and the trainer's placement, stock MuJoCo ---------------------

mujoco = pytest.importorskip("mujoco")


def _built():
    from test_dynamics_terrain import _free_block

    components, joints, _ = _free_block()
    return dyn.build_model(components, joints, terrain=RANDOM_COURSE)


def test_the_model_has_a_slot_per_box_of_the_fullest_course_and_parks_the_rest() -> None:
    from test_dynamics_terrain import _ground_z_mm

    built = _built()
    model, descriptor = built["model"], built["environment"]["terrain"]
    slots = [mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_GEOM,
                               f"{dyn.ENVIRONMENT_TERRAIN_GEOM}/{index}")
             for index in range(descriptor["slots"])]
    assert min(slots) >= 0
    assert mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_GEOM,
                             f"{dyn.ENVIRONMENT_TERRAIN_GEOM}/{descriptor['slots']}") == -1
    parked = slots[len(descriptor["boxes"]):]
    assert parked, "course 0 should not be the fullest of this pool"
    for geom in parked:
        assert model.geom_pos[geom][2] * 1000.0 == pytest.approx(
            descriptor["lowest_mm"] - dyn.TERRAIN_BASE_MM - dyn.TERRAIN_PARKED_DEPTH_MM)
    for x in range(600, 5900, 175):
        for y in (-500.0, 300.0):
            assert _ground_z_mm(model, float(x), y) == pytest.approx(
                dyn.terrain_box_ground_mm(descriptor, float(x), y), abs=1e-3), (x, y)


def _geom_ids(model, slots):
    plane = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_GEOM, dyn.ENVIRONMENT_TERRAIN_GEOM)
    return plane, [mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_GEOM,
                                     f"{dyn.ENVIRONMENT_TERRAIN_GEOM}/{index}")
                   for index in range(slots)]


def test_the_trainers_placement_of_each_course_is_the_model_the_engine_compiles_for_it() -> None:
    """Course k's features declared as a listed box course compile to the
    geoms the trainer places for course k: the plane's height, then each box
    slot's position, turn, size and the bounds MuJoCo derives from it."""

    import numpy
    from test_dynamics_terrain import _free_block

    module = _trainer_module()
    descriptor = _built()["environment"]["terrain"]
    pool = module.terrain_pool(numpy, descriptor)
    assert pool["scan"].shape == (6, descriptor["slots"], 6)
    for index, course in enumerate(descriptor["pool"]):
        components, joints, _ = _free_block()
        listed = {key: RANDOM_COURSE[key] for key in ("form", "x_range_mm", "y_range_mm")}
        model = dyn.build_model(components, joints,
                                terrain={**listed, "features": course["features"]})["model"]
        plane, slots = _geom_ids(model, course["boxes"])
        assert min(slots) >= 0
        assert model.geom_pos[plane][2] == pytest.approx(pool["plane_z"][index], abs=1e-9)
        count = course["boxes"]
        for field, key in (("geom_pos", "pos"), ("geom_quat", "quat"), ("geom_size", "size"),
                           ("geom_rbound", "rbound"), ("geom_aabb", "aabb")):
            assert numpy.asarray(getattr(model, field))[slots] == pytest.approx(
                pool[key][index][:count], abs=1e-9), (index, field)


def test_the_bundle_carries_the_pool() -> None:
    from test_dynamics_height_scan import scanned

    prepared = scanned(terrain=RANDOM_COURSE)
    descriptor = prepared["built"]["environment"]["terrain"]
    assert prepared["bundle"]["terrain"]["pool"] == descriptor["pool"]
    assert prepared["bundle"]["terrain"]["slots"] == descriptor["slots"]
    assert prepared["bundle"]["terrain"]["boxes"] == descriptor["boxes"]


# -- the trainer, under MJX ---------------------------------------------------

def test_each_environment_runs_its_own_course_and_a_reset_redraws_it(tmp_path) -> None:
    """Built as the trainer builds it: 16 environments on a 6-course pool
    start on several courses, each environment's privileged scan reads its
    own course, an episode that ends draws again, and everything stays
    finite."""

    jax = pytest.importorskip("jax")
    jnp = pytest.importorskip("jax.numpy")
    mjx = pytest.importorskip("mujoco.mjx")
    import numpy
    from test_dynamics_height_scan import TASK, scanned

    module = _trainer_module()
    prepared = scanned(terrain=RANDOM_COURSE, root=tmp_path, task={**TASK, "episode_seconds": 0.1})
    bundle = prepared["bundle"]
    options = module.arguments([str(prepared["path"]), "--out", str(tmp_path / "x.cxpolicy")])
    loaded = module.load_bundle(str(prepared["path"]), module.globals_for(jnp))
    env = module.build_environment(loaded, options, count=16, seed=0,
                                   jax=jax, jnp=jnp, np=numpy, mujoco=mujoco, mjx=mjx)
    state = jax.jit(env.reset)(jax.random.PRNGKey(0))
    courses = numpy.asarray(state.info["course"])
    assert len(set(courses.tolist())) > 1
    descriptor = bundle["terrain"]
    scan_index = [env.names.index(name) for name in dyn.scan_channels(bundle)]
    data = state.pipeline_state
    for env_index in range(16):
        reading = dyn.terrain_boxes(descriptor["pool"][int(courses[env_index])]["features"],
                                    descriptor["x_range_mm"], descriptor["y_range_mm"])
        engine = dyn.height_scan_values(
            {**bundle, "terrain": {**descriptor, **reading}},
            numpy.asarray(data.xpos[env_index]), numpy.asarray(data.xmat[env_index]), None)
        assert numpy.asarray(state.obs["privileged_state"][env_index])[scan_index].tolist() == \
            pytest.approx([engine[name] for name in dyn.scan_channels(bundle)], abs=0.05)
    step = jax.jit(env.step)
    seen = {int(value) for value in courses}
    for _ in range(3 * env.horizon):
        state = step(state, jnp.zeros((16, env.action_size)))
        seen |= {int(value) for value in numpy.asarray(state.info["course"])}
    assert numpy.isfinite(numpy.asarray(state.pipeline_state.qpos)).all()
    assert numpy.isfinite(numpy.asarray(state.obs["privileged_state"])).all()
    assert seen == set(range(6))


def test_under_mjx_a_block_rests_on_the_course_its_environment_was_given() -> None:
    """``place_course`` on the MJX model: the block dropped where each course
    has its own ground comes to rest 10 mm above that course's ground, so
    the geoms MJX collides with are the course the scan reads."""

    jax = pytest.importorskip("jax")
    jnp = pytest.importorskip("jax.numpy")
    mjx = pytest.importorskip("mujoco.mjx")
    import numpy

    module = _trainer_module()
    built = _built()
    descriptor = built["environment"]["terrain"]
    model = mujoco.MjModel.from_xml_string(dyn.export_mjcf(built)["xml"].decode("utf-8"))
    plane, slots = _geom_ids(model, descriptor["slots"])
    pool = {key: jnp.asarray(value, dtype=jnp.float32)
            for key, value in module.terrain_pool(numpy, descriptor).items()}
    device = mjx.put_model(model)
    # On each course, the first place raised off z = 0 that is flat for
    # 150 mm round it: the block stands there, clear of an edge.
    grounds, places = [], []
    for course in descriptor["pool"]:
        reading = dyn.terrain_boxes(course["features"], descriptor["x_range_mm"],
                                    descriptor["y_range_mm"])
        for x_mm in range(800, 5600, 25):
            around = {round(dyn.terrain_box_ground_mm(reading, x_mm + dx, dy), 6)
                      for dx in range(-150, 175, 25) for dy in (-60.0, 0.0, 60.0)}
            if len(around) == 1 and abs(next(iter(around))) > 5.0:
                break
        else:
            pytest.fail("no flat raised place on a pooled course")
        places.append(x_mm / 1000.0)
        grounds.append(next(iter(around)))
    assert len({round(value) for value in grounds}) > 1
    start = numpy.tile(numpy.asarray(built["qpos_solved"], numpy.float32), (len(grounds), 1))
    start[:, 0] = numpy.asarray(places) + start[:, 0]
    start[:, 2] += (numpy.asarray(grounds) + 30.0) / 1000.0

    def settle(course, qpos):
        m = module.place_course(device, pool, jnp.asarray(slots), plane, course)
        data = mjx.make_data(m).replace(qpos=qpos)
        data = jax.lax.fori_loop(0, 400, lambda _, d: mjx.step(m, d), data)
        return data.qpos[2]

    rested = jax.jit(jax.vmap(settle))(jnp.arange(len(grounds)), jnp.asarray(start))
    assert (numpy.asarray(rested) * 1000.0).tolist() == pytest.approx(
        [ground + 10.0 for ground in grounds], abs=2.0)
