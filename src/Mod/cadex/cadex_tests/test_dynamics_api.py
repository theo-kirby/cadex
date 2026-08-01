# SPDX-License-Identifier: LGPL-2.1-or-later

"""``assembly.body`` and ``assembly.dynamics`` (docs/MUJOCO.md M2, phase 7).

Two additions to the script surface, and one deliberate non-addition.

``body`` wraps a component with its dynamics-only data exactly as
``connector`` wraps one for ``joint``: an intermediate value, never returned
as an output, needing no native type and no publication branch.
``api.component`` is untouched, so the kinematics path cannot regress.

``dynamics`` produces ``output_type: "simulation"`` -- the *same* type
``api.simulation`` produces, not a sibling. The reason is concrete rather
than tidy: ``cadex_animate._simulation_entries`` selects on
``artifact_kind == "assembly_simulation_json"`` and, on finding two, bakes
**neither** -- it clears the scene, drops the Simulation panel and reports
into a message the UI never shows. A sibling type would let a script
declare both a kinematics and a dynamics run and silently lose the
animation it already had.
"""

from __future__ import annotations

import shutil

import pytest

from cadex_assembly_api import AssemblyDomainAPI, _PUBLISHABLE_TYPES
from CadexScriptedDomains import XSCRIPT_WORKBENCH_PACKS


def _api() -> AssemblyDomainAPI:
    pack = XSCRIPT_WORKBENCH_PACKS["AssemblyWorkbench"]
    return AssemblyDomainAPI(pack.api_exports, pack.output_types)


def _source(name: str) -> dict[str, str]:
    return {"document_uid": "doc", "object_name": name}


def _assembly(api, count: int = 2):
    components = [
        api.component(_source(f"solid{index}"), grounded=index == 0)
        for index in range(count)
    ]
    joints = [
        api.joint(
            "revolute",
            api.connector(components[index], "origin"),
            api.connector(components[index + 1], "origin"),
        )
        for index in range(count - 1)
    ]
    return api.assembly(components, joints), components


def test_the_pack_and_the_api_export_the_same_names_in_the_same_order() -> None:
    pack = XSCRIPT_WORKBENCH_PACKS["AssemblyWorkbench"]
    assert pack.api_exports == AssemblyDomainAPI.exported_names
    assert "dynamics" in pack.api_exports and "body" in pack.api_exports


def test_a_body_is_an_intermediate_and_never_an_output() -> None:
    """Like connector: no native type, no publication branch, no ADR-055 row."""

    api = _api()
    component = api.component(_source("plate"), grounded=True)
    body = api.body(component, density_kg_m3=7850)
    assert body.output_type == "body"
    assert "body" not in _PUBLISHABLE_TYPES
    pack = XSCRIPT_WORKBENCH_PACKS["AssemblyWorkbench"]
    assert "body" not in pack.output_types


def test_a_dynamics_run_is_a_simulation_and_not_a_sibling_type() -> None:
    api = _api()
    model, components = _assembly(api)
    bodies = [api.body(component, density_kg_m3=2700) for component in components]
    run = api.dynamics(model, bodies, end_time_s=2.0)
    assert run.output_type == "simulation"
    assert run.operation == "dynamics"
    assert run.properties["frames_per_second"] == 60


def test_density_is_required_and_never_defaulted() -> None:
    api = _api()
    component = api.component(_source("plate"), grounded=True)
    with pytest.raises(TypeError):
        api.body(component)


@pytest.mark.parametrize("density", [0.0, -1.0, 30000.1, float("nan"), True])
def test_an_impossible_density_is_refused(density) -> None:
    api = _api()
    component = api.component(_source("plate"), grounded=True)
    with pytest.raises(ValueError, match="density_kg_m3"):
        api.body(component, density_kg_m3=density)


def test_the_density_bounds_admit_the_materials_people_use() -> None:
    api = _api()
    component = api.component(_source("plate"), grounded=True)
    for density in (30.0, 1040.0, 2700.0, 7850.0, 19300.0):
        assert api.body(component, density_kg_m3=density).properties[
            "density_kg_m3"
        ] == pytest.approx(density)


def test_every_component_needs_exactly_one_body() -> None:
    """A massless part is not a lighter part; it is an unsolvable one."""

    api = _api()
    model, components = _assembly(api, count=3)
    bodies = [api.body(component, density_kg_m3=7850) for component in components]
    api.dynamics(model, bodies)
    with pytest.raises(ValueError, match="one api.body per component"):
        api.dynamics(model, bodies[:2])


def test_one_component_may_not_have_two_densities() -> None:
    api = _api()
    model, components = _assembly(api)
    bodies = [
        api.body(components[0], density_kg_m3=7850),
        api.body(components[0], density_kg_m3=2700),
    ]
    with pytest.raises(ValueError, match="two densities"):
        api.dynamics(model, bodies)


def test_a_body_from_another_assembly_is_refused() -> None:
    api = _api()
    model, components = _assembly(api)
    stranger = api.component(_source("elsewhere"))
    bodies = [api.body(component, density_kg_m3=7850) for component in components]
    with pytest.raises(ValueError, match="not listed in this assembly"):
        api.dynamics(model, [*bodies[1:], api.body(stranger, density_kg_m3=7850)])


def test_the_time_range_and_frame_rate_are_bounded() -> None:
    api = _api()
    model, components = _assembly(api)
    bodies = [api.body(component, density_kg_m3=7850) for component in components]
    with pytest.raises(ValueError, match="end_time_s"):
        api.dynamics(model, bodies, start_time_s=1.0, end_time_s=1.0)
    for rate in (0, 241, 1.5, True):
        with pytest.raises(ValueError, match="frames_per_second"):
            api.dynamics(model, bodies, frames_per_second=rate)
    with pytest.raises(ValueError, match="100000 component-pose samples"):
        api.dynamics(model, bodies, end_time_s=2000.0, frames_per_second=240)


def test_the_declared_frame_budget_matches_what_the_run_will_produce() -> None:
    """One sample per frame plus the input frame, and no solver slack.

    ``api.simulation`` has to over-declare because OndselSolver decides its
    own frame count; a dynamics run samples exactly where it is told to.
    """

    api = _api()
    model, components = _assembly(api)
    bodies = [api.body(component, density_kg_m3=7850) for component in components]
    run = api.dynamics(model, bodies, end_time_s=2.0, frames_per_second=60)
    assert run.properties["estimated_frame_limit"] == 122


def test_kinematics_and_dynamics_cannot_both_run_in_one_script() -> None:
    """The worker contract, because the API cannot see both values at once."""

    from cadex_assembly_worker import AssemblyCandidateError, _simulation_contract

    api = _api()
    model, components = _assembly(api)
    bodies = [api.body(component, density_kg_m3=7850) for component in components]
    joint = model.properties["joints"][0]
    motion = api.motion(joint, "2 * pi * time")
    run = api.dynamics(model, bodies)
    raw = {"asm": model, "spin": motion, "sim": run}
    with pytest.raises(AssemblyCandidateError, match="cannot be combined"):
        _simulation_contract(raw, assembly_value=model, joint_outputs={id(joint): "j"})


def test_two_simulations_of_any_kind_are_still_exactly_one_too_many() -> None:
    from cadex_assembly_worker import AssemblyCandidateError, _simulation_contract

    api = _api()
    model, components = _assembly(api)
    bodies = [api.body(component, density_kg_m3=7850) for component in components]
    joint = model.properties["joints"][0]
    raw = {
        "asm": model,
        "spin": api.motion(joint, "2 * pi * time"),
        "kin": api.simulation(model, [api.motion(joint, "time")]),
        "dyn": api.dynamics(model, bodies),
    }
    with pytest.raises(AssemblyCandidateError, match="exactly one"):
        _simulation_contract(raw, assembly_value=model, joint_outputs={id(joint): "j"})


def test_the_worker_contract_accepts_a_dynamics_run() -> None:
    from cadex_assembly_worker import _simulation_contract

    api = _api()
    model, components = _assembly(api)
    bodies = [api.body(component, density_kg_m3=7850) for component in components]
    run = api.dynamics(model, bodies)
    output, value, motions = _simulation_contract(
        {"asm": model, "dyn": run}, assembly_value=model, joint_outputs={}
    )
    assert output == "dyn"
    assert value is run
    assert motions == {}


def test_the_simulation_trace_is_part_of_the_project_digest() -> None:
    """The correction ADR-077 owed ADR-075, now finally true (ADR-068).

    ADR-075 justified MuJoCo's exact version pin with "every open_project
    asserts digest equality, so an unpinned patch bump would silently turn
    every stored simulation into a restore failure." M2 measured that and
    found it false: ``compute_project_digest`` branched on ``artifact_kind``
    for ``brep`` and ``mesh`` and fell through to the canonical *definition*
    for everything else, so a trace's bytes were in no digest. A version bump
    changed every trace and moved nothing.

    ADR-079 decided that should change and routed it to ``main``, because
    the digest code is shared with the kinematics trace. ADR-068 landed it
    there, and this is the test M3 wrote in its inverted form saying it would
    have to be rewritten. The pin's justification is now the truth rather
    than the intent.
    """

    from pathlib import Path
    import tempfile

    from cadex_project_worker import compute_project_digest

    root = Path(tempfile.mkdtemp(prefix="m5-trace-digest-"))
    try:
        artifact = root / "outputs" / "assembly-simulation-trace.json"
        artifact.parent.mkdir(parents=True)
        artifact.write_bytes(b'{"schema":"cadex-assembly-simulation-trace-v1"}')
        outputs = [
            {
                "name": "sim",
                "domain": "assembly",
                "type": "simulation",
                "artifact_kind": "assembly_simulation_json",
                "artifact_path": "outputs/assembly-simulation-trace.json",
                "definition": {"operation": "dynamics", "end_time_s": 1.0},
            }
        ]
        before = compute_project_digest(root, outputs)
        artifact.write_bytes(
            b'{"schema":"cadex-assembly-simulation-trace-v1","x":1}'
        )
        assert compute_project_digest(root, outputs) != before
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_an_exported_mjcf_model_is_part_of_the_project_digest() -> None:
    """And it got there without a line of dynamics-aware code, by design.

    ADR-068 keyed the digest's bytes clause on *having an artifact* rather
    than on a roster of known kinds, precisely so that this branch's
    ``assembly_mjcf_xml`` would be covered by the sync rather than by
    somebody remembering it. This asserts the outcome rather than trusting
    the reasoning -- hazard 3 applied to exported models, closed by
    inheritance.
    """

    from pathlib import Path
    import tempfile

    from cadex_project_worker import compute_project_digest

    root = Path(tempfile.mkdtemp(prefix="m5-mjcf-digest-"))
    try:
        artifact = root / "outputs" / "model-model.xml"
        artifact.parent.mkdir(parents=True)
        artifact.write_bytes(b'<mujoco model="cadex-assembly"/>')
        outputs = [
            {
                "name": "model",
                "domain": "assembly",
                "type": "mjcf",
                "artifact_kind": "assembly_mjcf_xml",
                "artifact_path": "outputs/model-model.xml",
                "definition": {"operation": "mjcf"},
            }
        ]
        before = compute_project_digest(root, outputs)
        artifact.write_bytes(b'<mujoco model="cadex-assembly"><!-- --></mujoco>')
        assert compute_project_digest(root, outputs) != before
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_the_worker_contract_re_checks_the_bodies_it_is_handed() -> None:
    """The worker validates the graph it gets, not the graph it hopes for."""

    from cadex_assembly_worker import AssemblyCandidateError, _simulation_contract

    api = _api()
    model, components = _assembly(api, count=3)
    bodies = [api.body(component, density_kg_m3=7850) for component in components]
    run = api.dynamics(model, bodies)
    # Forge a graph the API would have refused, as a rewritten payload could.
    object.__setattr__(
        run,
        "properties",
        {**run.properties, "bodies": tuple(bodies[:2])},
    )
    with pytest.raises(AssemblyCandidateError, match="one api.body per"):
        _simulation_contract({"asm": model, "dyn": run}, assembly_value=model, joint_outputs={})
