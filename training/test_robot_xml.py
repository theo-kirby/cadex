# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""ADR-954: `robot_xml` drops the ground, and the ground's own contact pairs with it.

A warm start across a course change (ADR-161) compares the two models less
everything named under ``environment/``. A training cut gives feet and fall
geoms the same contact bits, so a course that must touch the feet alone names
its foot pairs; those pairs are the ground's, not the robot's.

Run: ``~/cadex-train-venv/bin/python -m pytest training/test_robot_xml.py``.
"""

from __future__ import annotations

from cadex_train import robot_xml

ROBOT = """<mujoco model="r">
  <worldbody>
    <geom name="environment/floor" type="plane" size="0 0 0.1"/>
    <body name="b"><freejoint/>
      <geom name="paw" type="sphere" size="0.015" contype="0"/>
      <geom name="trunk" type="box" size="0.1 0.05 0.03" contype="0"/>
    </body>
  </worldbody>
</mujoco>"""

COURSE = """  <worldbody>
    <geom name="environment/terrain" type="plane" size="0 0 0.1"/>
    <geom name="environment/terrain/0" type="box" size="1 1 0.01" contype="0" conaffinity="0"/>
"""


def _course(contact: str) -> bytes:
    xml = ROBOT.replace('  <worldbody>\n    <geom name="environment/floor" type="plane" size="0 0 0.1"/>\n',
                        COURSE)
    return xml.replace("</mujoco>", contact + "</mujoco>").encode()


def test_a_course_with_its_own_paw_pairs_is_the_same_robot():
    pairs = ('<contact><pair name="environment/pair/paw/0" geom1="paw" '
             'geom2="environment/terrain/0"/></contact>\n')
    assert robot_xml(_course(pairs)) == robot_xml(ROBOT.encode())


def test_a_pair_not_named_for_the_ground_still_moves_the_robot():
    pairs = '<contact><pair name="paw_course" geom1="paw" geom2="environment/terrain/0"/></contact>\n'
    assert robot_xml(_course(pairs)) != robot_xml(ROBOT.encode())


def test_the_robots_own_contact_survives_beside_the_grounds_pairs():
    own = '<contact><exclude body1="world" body2="b"/></contact>\n'
    both = ('<contact><exclude body1="world" body2="b"/>'
            '<pair name="environment/pair/paw/0" geom1="paw" geom2="environment/terrain/0"/></contact>\n')
    robot = ROBOT.replace("</mujoco>", own + "</mujoco>").encode()
    assert robot_xml(_course(both)) == robot_xml(robot)
    assert robot_xml(_course(both)) != robot_xml(ROBOT.encode())


def test_an_indented_contact_section_of_ground_pairs_leaves_no_trace():
    robot = ROBOT.replace("</mujoco>", "  <keyframe><key name=\"home\"/></keyframe>\n</mujoco>")
    course = robot.replace(
        '  <worldbody>\n    <geom name="environment/floor" type="plane" size="0 0 0.1"/>\n', COURSE)
    course = course.replace("</mujoco>", "  <contact>\n    <pair name=\"environment/pair/paw/0\" "
                            "geom1=\"paw\" geom2=\"environment/terrain/0\"/>\n  </contact>\n</mujoco>")
    assert robot_xml(course.encode()) == robot_xml(robot.encode())
