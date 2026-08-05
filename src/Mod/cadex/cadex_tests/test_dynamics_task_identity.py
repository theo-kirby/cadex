# SPDX-License-Identifier: LGPL-2.1-or-later

"""Task identity: what makes two bundles the same task (ADR-134).

``verify_policy`` check 1 is a **whole-file hash** of the task bundle, and it
is right to be: a policy is only meaningful for the task it was trained on,
and change a reward weight or an episode length and it is optimising something
else. What the whole-file hash cannot tell apart is *"this is a different
task"* from *"this bundle was written by a different route"*, and two
corrections in this engine are exactly the second kind:

* **ADR-133** snaps inertial coordinates below a nanometre, which changes every
  model digest, which changes every bundle that embeds one. Every policy
  trained before it would be orphaned.
* **ADR-131** made a command range sayable in a script and reports its
  provenance honestly as ``command_limits_degrees``. The arm it replaces was
  produced by editing the derived bundle, which reported ``angle_limits_
  degrees`` -- the joint's limits, which are not where ±25° came from. Every
  action *number* is identical between the two.

So this file pins two things. ``task_semantic_digest`` is blind to a rename, a
key order, a float format, and a provenance string; and it is not blind to
anything that decides behaviour -- there is one test per field for that, run
one at a time, because a comparison that missed a field would be a comparison
that quietly accepted a different task.

**And ``model_differences`` is the half that keeps it honest.** Excluding
``model.sha256`` from a bundle comparison and stopping there would accept a
policy against a mechanism with the same joint names and limits and different
masses -- every number in the bundle would match and the robot would be a
different robot. So the two models are compared as models.
"""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest

import CadexDynamics as dyn

mujoco = pytest.importorskip("mujoco")

import dynamics_policy_fixtures as pf  # noqa: E402


@pytest.fixture(scope="module")
def prepared() -> dict:
    """One real bundle, from the fixture that builds one forwards."""

    return pf.swing_up_bundle()


def _mutate(bundle: dict, path: str, value: object) -> dict:
    """A deep copy of ``bundle`` with one dotted path replaced.

    ``reward[0].weight`` reads as it would be written. The copy is deep because
    a fixture shared across a module and mutated in place is a test that passes
    or fails on collection order.
    """

    changed = copy.deepcopy(bundle)
    cursor: object = changed
    parts = path.replace("[", ".").replace("]", "").split(".")
    for part in parts[:-1]:
        cursor = cursor[int(part)] if part.isdigit() else cursor[part]
    last = parts[-1]
    if last.isdigit():
        cursor[int(last)] = value
    else:
        cursor[last] = value
    return changed


# ---------------------------------------------------------------------------
# Blind to how the file was written.
# ---------------------------------------------------------------------------


def test_key_order_does_not_change_the_digest(prepared) -> None:
    bundle = prepared["bundle"]
    reversed_keys = {key: bundle[key] for key in reversed(list(bundle))}
    assert list(reversed_keys) != list(bundle)
    assert dyn.task_semantic_digest(reversed_keys) == dyn.task_semantic_digest(
        bundle
    )


def test_an_integer_and_the_same_float_agree(prepared) -> None:
    """``30`` and ``30.0`` are one action bound written two ways."""

    bundle = prepared["bundle"]
    integral = _mutate(bundle, "episode.control_hz", 50)
    floated = _mutate(bundle, "episode.control_hz", 50.0)
    assert dyn.task_semantic_digest(integral) == dyn.task_semantic_digest(floated)
    # ...and a *string* 50.0 is not the number, which is what keeps the
    # canonical text from collapsing two different bundles onto one digest.
    stringy = _mutate(bundle, "episode.control_hz", "50.0")
    assert dyn.task_semantic_digest(stringy) != dyn.task_semantic_digest(floated)


def test_negative_zero_is_zero(prepared) -> None:
    """The same normalisation ADR-133 makes at the MJCF writer."""

    bundle = prepared["bundle"]
    positive = _mutate(bundle, "actions[0].low", 0.0)
    negative = _mutate(bundle, "actions[0].low", -0.0)
    assert dyn.task_semantic_digest(positive) == dyn.task_semantic_digest(negative)


def test_the_task_label_is_provenance(prepared) -> None:
    """`stand12` by hand and `stand` from source are the same task."""

    bundle = prepared["bundle"]
    renamed = _mutate(bundle, "label", "stand12")
    assert renamed["label"] != bundle["label"]
    assert dyn.task_semantic_digest(renamed) == dyn.task_semantic_digest(bundle)
    assert dyn.task_differences(renamed, bundle) == []


def test_an_actions_source_string_is_provenance(prepared) -> None:
    """ADR-131's correction, which moved a whole-file hash and no number."""

    bundle = prepared["bundle"]
    relabelled = _mutate(bundle, "actions[0].source", "command_limits_degrees")
    assert relabelled["actions"][0]["source"] != bundle["actions"][0]["source"]
    assert dyn.task_semantic_digest(relabelled) == dyn.task_semantic_digest(bundle)


def test_an_actions_fallback_is_provenance(prepared) -> None:
    """What to write with no policy, which a trained policy never reads."""

    bundle = prepared["bundle"]
    changed = _mutate(bundle, "actions[0].fallback", "0.5")
    assert dyn.task_semantic_digest(changed) == dyn.task_semantic_digest(bundle)


def test_the_model_block_is_compared_as_a_model_not_as_a_hash(prepared) -> None:
    """ADR-133's cost, absorbed. The digest moved; the mechanism did not."""

    bundle = prepared["bundle"]
    for field, value in (
        ("model.sha256", "0" * 64),
        ("model.path", "outputs/somewhere-else-model.xml"),
        ("model.bytes", 14169),
    ):
        moved = _mutate(bundle, field, value)
        assert dyn.task_semantic_digest(moved) == dyn.task_semantic_digest(
            bundle
        ), field


# ---------------------------------------------------------------------------
# ...and not blind to anything that decides behaviour. One field at a time.
# ---------------------------------------------------------------------------


BEHAVIOUR_CHANGES = [
    ("reward[0].weight", 99.0),
    ("reward[0].expression", "1.0"),
    ("episode.max_steps", 400),
    ("episode.episode_seconds", 12.0),
    ("episode.control_hz", 100),
    ("episode.solver_step_s", 0.001),
    ("episode.reset_keyframe", "home"),
    ("termination[0].expression", "pel_z"),
    ("actions[0].low", -29.0),
    ("actions[0].high", 31.0),
    ("actions[0].scale", 1.0),
    ("actions[0].unit", "rad"),
    ("actions[0].actuator", "hinge/other"),
    ("actions[0].index", 3),
    ("actions[0].kind", "position"),
    ("actions[0].motion_type", "linear"),
    ("actions[0].joint", "elbow"),
    ("observations[0].channels", ["renamed"]),
    ("observations[0].scale", 2.0),
    ("observations[0].adr", 7),
    ("observations[0].kind", "velocity"),
    ("observations[0].target", "post"),
    ("schema", "cadex-training-task-v2"),
    ("mujoco_version", "3.11.0"),
    ("variation_algorithm", "something else entirely"),
    ("functions", ["abs"]),
]


@pytest.mark.parametrize("path,value", BEHAVIOUR_CHANGES,
                         ids=[path for path, _ in BEHAVIOUR_CHANGES])
def test_a_behaviour_field_moves_the_digest_and_is_named(
    prepared, path: str, value: object
) -> None:
    bundle = prepared["bundle"]
    if path.split(".")[0].split("[")[0] not in bundle:
        pytest.skip(f"this fixture declares no {path}")
    changed = _mutate(bundle, path, value)
    assert dyn.task_semantic_digest(changed) != dyn.task_semantic_digest(bundle)
    differences = dyn.task_differences(changed, bundle)
    assert differences, path
    # The refusal has to say *which* field, or the author is guessing between
    # a reward weight and a foot radius.
    named = path.replace("[", "[").split(".")[-1]
    assert any(named in line for line in differences), differences


def test_a_termination_threshold_moves_the_digest(prepared) -> None:
    """Called out separately because ``above``/``below`` may be null."""

    bundle = prepared["bundle"]
    entry = dict(bundle["termination"][0])
    key = "below" if entry.get("below") is not None else "above"
    changed = _mutate(bundle, f"termination[0].{key}", -12345.0)
    assert dyn.task_semantic_digest(changed) != dyn.task_semantic_digest(bundle)
    assert any(key in line for line in dyn.task_differences(changed, bundle))


def test_dropping_a_list_entry_is_a_difference(prepared) -> None:
    bundle = prepared["bundle"]
    shorter = copy.deepcopy(bundle)
    shorter["reward"] = shorter["reward"][:-1]
    assert dyn.task_semantic_digest(shorter) != dyn.task_semantic_digest(bundle)
    differences = dyn.task_differences(shorter, bundle)
    assert any("entries" in line for line in differences), differences


def test_a_digest_match_and_an_empty_diff_are_the_same_claim(prepared) -> None:
    """Two functions that could disagree would make one of them a lie."""

    bundle = prepared["bundle"]
    for path, value in BEHAVIOUR_CHANGES[:8] + [("label", "other")]:
        if path.split(".")[0].split("[")[0] not in bundle:
            continue
        changed = _mutate(bundle, path, value)
        same_digest = dyn.task_semantic_digest(changed) == dyn.task_semantic_digest(
            bundle
        )
        assert same_digest == (dyn.task_differences(changed, bundle) == []), path


def test_the_diff_is_bounded(prepared) -> None:
    """A changed mechanism would otherwise bury its first line under three
    hundred observation rows."""

    bundle = prepared["bundle"]
    wrecked = copy.deepcopy(bundle)
    for row in wrecked["observations"]:
        row["scale"] = 1234.5
    for row in wrecked["actions"]:
        row["low"] = -1.0
    differences = dyn.task_differences(wrecked, bundle)
    assert 0 < len(differences) <= dyn.MAXIMUM_REPORTED_DIFFERENCES


def test_a_non_finite_number_is_refused(prepared) -> None:
    """A bundle cannot carry one, and a digest over one would not be stable."""

    for bad in (float("nan"), float("inf"), float("-inf")):
        with pytest.raises(dyn.DynamicsError) as raised:
            dyn.task_semantic_digest(_mutate(prepared["bundle"],
                                             "reward[0].weight", bad))
        assert raised.value.reason == "task_not_finite"


def test_the_field_lists_are_declared_rather_than_derived() -> None:
    """A schema that grows a field is a decision, not a silent widening."""

    source = Path(dyn.__file__).read_text(encoding="utf-8")
    assert "TASK_SEMANTIC_FIELDS" in source
    # Every field of a real bundle is accounted for in exactly one list, so a
    # new one cannot be forgotten into neither.
    covered = set(dyn.TASK_SEMANTIC_FIELDS) | set(dyn.TASK_PROVENANCE_FIELDS)
    bundle = pf.swing_up_bundle()["bundle"]
    assert set(bundle) <= covered, set(bundle) - covered


# ---------------------------------------------------------------------------
# The models, compared as models.
# ---------------------------------------------------------------------------


_TWO_BODY_MJCF = """<mujoco model="t">
  <compiler autolimits="false"/>
  <option timestep="{timestep}"/>
  <worldbody>
    <body name="a" pos="0 0 1">
      <inertial pos="{ipos} 0 0" mass="{mass}" diaginertia="1e-4 1e-4 1e-4"/>
      <joint name="j" type="hinge" axis="0 1 0" limited="true" range="-1 1"/>
      <geom name="g" type="box" size="0.1 0.1 0.1"/>
      {extra}
    </body>
  </worldbody>
  <actuator>
    <position name="p" joint="j" ctrlrange="-1 1" ctrllimited="true"/>
  </actuator>
</mujoco>
"""


def _mjcf(*, ipos: str = "0", mass: str = "0.5", timestep: str = "0.002",
          extra: str = "") -> bytes:
    return _TWO_BODY_MJCF.format(
        ipos=ipos, mass=mass, timestep=timestep, extra=extra
    ).encode("utf-8")


def test_two_identical_models_have_no_differences() -> None:
    assert dyn.model_differences(_mjcf(), _mjcf()) == []


def test_the_adr_133_snap_is_inside_the_tolerance() -> None:
    """The case ADR-134 exists for, as the two files actually differ.

    A pre-snap MJCF says ``5.10087e-11`` where a post-snap one says ``0``. On a
    body 0.3 m tall that is fifteen orders of magnitude inside 1e-5 relative,
    and the two are the same mechanism.
    """

    before = _mjcf(ipos="5.10087e-11")
    after = _mjcf(ipos="0")
    assert before != after
    assert dyn.model_differences(before, after) == []
    # ...and so is the *other* platform's reading, which is the whole point.
    assert dyn.model_differences(_mjcf(ipos="5.10066e-11"), after) == []


def test_the_absolute_floor_is_a_nanometre_on_one_field_only() -> None:
    """Why the escape hatch is not applied everywhere.

    ``_field_drift`` divides by the field's own largest magnitude, so a
    ``body_ipos`` whose entire content is symmetry noise reads 1.0 relative
    drift against zeros -- which is what made the previous assertion fail. The
    floor fixes that field. It is *not* applied to the others because 1e-9 is
    looser than the relative bound for a sub-kilogram limb's inertia, whose
    moments are around 1e-5 kg·m²: a blanket floor would admit 1e-4 relative
    where the field bound admits 1e-5.
    """

    assert dyn.MODEL_ABSOLUTE_FLOOR_FIELDS == frozenset({"body_ipos"})
    # The arithmetic that rules a blanket floor out, stated as a number.
    limb_moment = 1.0e-5
    assert dyn.MODEL_ABSOLUTE_FLOOR_M / limb_moment > dyn.MJCF_FIELD_TOLERANCE


def test_the_floor_is_the_snap_in_metres() -> None:
    """One quantity, two units, and neither may drift from the other.

    Stated literally in each place because the division wobbles --
    ``1.0e-6 / 1000.0`` is 9.999999999999999e-10 and a bound should not carry
    that -- so this is what ties them together.
    """

    assert dyn.MODEL_ABSOLUTE_FLOOR_M == pytest.approx(
        dyn.INERTIAL_ZERO_TOLERANCE_MM / 1000.0, rel=1.0e-15
    )


def test_the_floor_does_not_admit_a_real_coordinate_change() -> None:
    """A micrometre is a thousand floors, and it is refused."""

    differences = dyn.model_differences(_mjcf(ipos="0"), _mjcf(ipos="1e-6"))
    assert differences
    assert any("body_ipos" in line for line in differences), differences
    # The refusal reports both numbers, so "which bound did I miss" is not a
    # question anyone has to ask.
    assert any("absolute" in line for line in differences), differences


def test_a_changed_mass_is_a_different_mechanism() -> None:
    differences = dyn.model_differences(_mjcf(mass="0.5"), _mjcf(mass="0.6"))
    assert differences
    assert any("body_mass" in line for line in differences), differences


def test_a_changed_solver_setting_is_refused_exactly() -> None:
    """Solver settings are written or lost, never rounded."""

    differences = dyn.model_differences(
        _mjcf(timestep="0.002"), _mjcf(timestep="0.0021")
    )
    assert any("opt.timestep" in line for line in differences), differences


def test_a_different_shape_is_reported_before_any_number() -> None:
    """A field diff over models of different shapes would report every array."""

    extra = '<body name="b" pos="0 0 0.2"><inertial pos="0 0 0" mass="0.1" ' \
            'diaginertia="1e-5 1e-5 1e-5"/><geom name="g2" type="sphere" ' \
            'size="0.05"/></body>'
    differences = dyn.model_differences(_mjcf(), _mjcf(extra=extra))
    assert differences
    assert all(
        line.split(":")[0] in dyn._MJCF_COUNT_FIELDS for line in differences
    ), differences
    assert any("nbody" in line for line in differences), differences


def test_an_unloadable_model_is_refused_rather_than_compared() -> None:
    with pytest.raises(dyn.DynamicsError) as raised:
        dyn.model_differences(_mjcf(), b"<mujoco><worldbody>")
    assert raised.value.reason == "model_not_loadable"


def test_the_real_export_is_equivalent_to_itself(prepared) -> None:
    """Through the fixture that produces a real mechanism, not a hand MJCF."""

    xml = prepared["model_xml"]
    assert dyn.model_differences(xml, xml) == []
    # And the digest of those bytes is what the bundle records, which is the
    # link the equivalence check follows to find the travelling model.
    assert hashlib.sha256(xml).hexdigest() == prepared["bundle"]["model"]["sha256"]


# ---------------------------------------------------------------------------
# The surface.
# ---------------------------------------------------------------------------


def test_the_api_validates_trained_task_like_it_validates_weights() -> None:
    from cadex_assembly_api import AssemblyDomainAPI

    text = " ".join(
        (AssemblyDomainAPI.policy.__doc__ or "").split()
    )
    assert "trained_task" in text
    assert "strictly stronger" in text
    source = Path(
        Path(dyn.__file__).parent / "cadex_assembly_api.py"
    ).read_text(encoding="utf-8")
    # The same three confinements ``weights`` gets, on the new name.
    section = source.split("operation = \"policy\"")[1].split("def rollout")[0]
    assert "trained_task" in section
    assert "1-120 characters" in section
    assert "directly inside the project assets" in section
    assert ".json" in section


def test_the_worker_names_its_new_refusal_stages() -> None:
    """Each stage is a contract with the failure envelope a driver reads."""

    source = (
        Path(dyn.__file__).parent / "cadex_assembly_worker.py"
    ).read_text(encoding="utf-8")
    for stage in ("policy_trained_task", "policy_task_equivalence",
                  "policy_model_equivalence"):
        assert f'"{stage}"' in source, stage


def test_verify_policy_was_not_weakened() -> None:
    """The point of ADR-134 is a *second* proof, not a relaxed first one.

    A policy is still bound to one exact bundle by whole-file digest. If that
    check ever became approximate, the equivalence check would be the only
    thing standing between a policy and a task it never saw.
    """

    source = Path(dyn.__file__).read_text(encoding="utf-8")
    body = source.split("def verify_policy(")[1].split("\ndef ")[0]
    assert 'reason="policy_task_mismatch"' in body
    assert "!= str(task_sha256)" in body
    assert "task_semantic_digest" not in body
