# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileCopyrightText: 2025 Brad Collette
# SPDX-FileNotice: Part of the FreeCAD project.

################################################################################
#                                                                              #
#   FreeCAD is free software: you can redistribute it and/or modify            #
#   it under the terms of the GNU Lesser General Public License as             #
#   published by the Free Software Foundation, either version 2.1              #
#   of the License, or (at your option) any later version.                     #
#                                                                              #
#   FreeCAD is distributed in the hope that it will be useful,                 #
#   but WITHOUT ANY WARRANTY; without even the implied warranty                #
#   of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.                    #
#   See the GNU Lesser General Public License for more details.                #
#                                                                              #
#   You should have received a copy of the GNU Lesser General Public           #
#   License along with FreeCAD. If not, see https://www.gnu.org/licenses       #
#                                                                              #
################################################################################

import FreeCAD
import tempfile
import pathlib
import CAMTests.PathTestUtils as PathTestUtils
from Machine.models.machine import (
    Machine,
    Toolhead,
    OutputOptions,
    ProcessingOptions,
    MachineFactory,
)
from Machine.models.validation import validate_job_against_machine


class TestMachineDataclass(PathTestUtils.PathTestBase):
    """Test the unified Machine dataclass"""

    def setUp(self):
        """Set up test fixtures"""
        self.default_machine = Machine()

    def test_default_initialization(self):
        """Test that Machine initializes with sensible defaults"""
        machine = Machine()

        # Basic identification
        self.assertEqual(machine.name, "Default Machine")
        self.assertEqual(machine.manufacturer, "")
        self.assertEqual(machine.description, "")

        # Machine type is derived from axes configuration
        self.assertEqual(machine.machine_type, "custom")  # No axes configured yet

        # Add axes and verify machine type updates
        machine.add_linear_axis("X", FreeCAD.Vector(1, 0, 0))
        machine.add_linear_axis("Y", FreeCAD.Vector(0, 1, 0))
        self.assertEqual(machine.machine_type, "custom")  # Still missing Z axis

        machine.add_linear_axis("Z", FreeCAD.Vector(0, 0, 1))
        self.assertEqual(machine.machine_type, "xyz")  # Now has XYZ axes

        # Add rotary axes and verify machine type updates
        machine.add_rotary_axis("A", FreeCAD.Vector(1, 0, 0), -120, 120)
        self.assertEqual(machine.machine_type, "xyza")

        machine.add_rotary_axis("C", FreeCAD.Vector(0, 0, 1), -360, 360)
        self.assertEqual(machine.machine_type, "xyzac")

        # Units and versioning
        self.assertEqual(machine.configuration_units, "metric")
        self.assertEqual(machine.version, 1)
        self.assertIsNotNone(machine.freecad_version)

        # Post-processor defaults
        self.assertIsInstance(machine.output, OutputOptions)
        self.assertIsInstance(machine.processing, ProcessingOptions)
        self.assertEqual(machine.postprocessor_file_name, "")
        self.assertIsInstance(machine.postprocessor_properties, dict)

    def test_custom_initialization(self):
        """Test Machine initialization with custom values and verify machine_type is derived"""
        # Create a 5-axis machine (XYZAC)
        machine = Machine(
            name="Test Mill",
            manufacturer="ACME Corp",
            description="5-axis mill",
            configuration_units="imperial",
        )

        # Add axes to make it a 5-axis machine
        machine.add_linear_axis("X", FreeCAD.Vector(1, 0, 0))
        machine.add_linear_axis("Y", FreeCAD.Vector(0, 1, 0))
        machine.add_linear_axis("Z", FreeCAD.Vector(0, 0, 1))
        machine.add_rotary_axis("A", FreeCAD.Vector(1, 0, 0), -120, 120)
        machine.add_rotary_axis("C", FreeCAD.Vector(0, 0, 1), -360, 360)

        self.assertEqual(machine.name, "Test Mill")
        self.assertEqual(machine.manufacturer, "ACME Corp")
        self.assertEqual(machine.description, "5-axis mill")
        self.assertEqual(machine.machine_type, "xyzac")
        self.assertEqual(machine.configuration_units, "imperial")

    def test_configuration_units_property(self):
        """Test configuration_units property returns correct values"""
        metric_machine = Machine(configuration_units="metric")
        self.assertEqual(metric_machine.configuration_units, "metric")

        imperial_machine = Machine(configuration_units="imperial")
        self.assertEqual(imperial_machine.configuration_units, "imperial")

    def test_output_unit_properties(self):
        """Output unit properties derive from output.units (regression for API drift)"""
        from Machine.models.machine import MachineUnits, OutputUnits

        machine = Machine()
        self.assertEqual(machine.output_machine_units, MachineUnits.METRIC)
        self.assertEqual(machine.gcode_units, MachineUnits.METRIC)
        self.assertEqual(machine.output_unit_format, "mm")
        self.assertEqual(machine.output_unit_speed_format, "mm/min")

        machine.output.units = OutputUnits.IMPERIAL
        self.assertEqual(machine.output_machine_units, MachineUnits.IMPERIAL)
        self.assertEqual(machine.gcode_units, MachineUnits.IMPERIAL)
        self.assertEqual(machine.output_unit_format, "in")
        self.assertEqual(machine.output_unit_speed_format, "in/min")

    def test_add_spindle_keyword_construction(self):
        """add_spindle() must map arguments to the correct Toolhead fields.

        Regression test: a positional-argument misalignment previously caused
        toolhead_type to receive the id, shifting every other field.
        """
        from Machine.models.machine import ToolheadType

        machine = Machine(name="Spindle Test")
        machine.add_spindle(
            "Main Spindle",
            id="spindle-01",
            max_power_kw=5.5,
            max_rpm=24000,
            min_rpm=1000,
            tool_change="automatic",
        )

        self.assertEqual(len(machine.toolheads), 1)
        toolhead = machine.toolheads[0]
        self.assertEqual(toolhead.name, "Main Spindle")
        self.assertEqual(toolhead.toolhead_type, ToolheadType.ROTARY)
        self.assertEqual(toolhead.id, "spindle-01")
        self.assertEqual(toolhead.max_power_kw, 5.5)
        self.assertEqual(toolhead.max_rpm, 24000)
        self.assertEqual(toolhead.min_rpm, 1000)
        self.assertEqual(toolhead.tool_change, "automatic")

    def test_add_spindle_machine_survives_serialization(self):
        """A machine built via add_spindle() serializes without error.

        Regression test: the misaligned Toolhead previously had
        toolhead_type=None, which crashed to_dict() with AttributeError.
        """
        machine = Machine(name="Serialize Test")
        machine.add_spindle("S1", max_rpm=18000, min_rpm=500)

        data = machine.to_dict()
        self.assertIsInstance(data, dict)

        restored = Machine.from_dict(data)
        self.assertEqual(len(restored.toolheads), 1)
        self.assertEqual(restored.toolheads[0].max_rpm, 18000)
        self.assertEqual(restored.toolheads[0].min_rpm, 500)

    def test_add_axis_accepts_tuple_vectors(self):
        """add_linear_axis/add_rotary_axis accept tuple and list vectors."""
        machine = Machine()
        machine.add_linear_axis("X", (1, 0, 0))
        machine.add_linear_axis("Y", [0, 1, 0])
        machine.add_linear_axis("Z", (0, 0, 1))
        machine.add_rotary_axis("A", (1, 0, 0), -120, 120)

        self.assertEqual(machine.machine_type, "xyza")
        self.assertIsInstance(machine.linear_axes["X"].direction_vector, FreeCAD.Vector)
        self.assertIsInstance(machine.rotary_axes["A"].rotation_vector, FreeCAD.Vector)
        self.assertAlmostEqual(machine.linear_axes["Y"].direction_vector.y, 1.0)

    def test_add_axis_invalid_vector_raises_type_error(self):
        """Invalid axis vectors raise TypeError naming the axis."""
        machine = Machine()

        with self.assertRaises(TypeError) as ctx:
            machine.add_linear_axis("X", "not a vector")
        self.assertIn("X", str(ctx.exception))

        with self.assertRaises(TypeError) as ctx:
            machine.add_rotary_axis("A", (1, 0))  # wrong length
        self.assertIn("A", str(ctx.exception))

        with self.assertRaises(TypeError) as ctx:
            machine.add_linear_axis("Z", (1, 0, "z"))  # non-numeric component
        self.assertIn("Z", str(ctx.exception))


class TestOutputOptions(PathTestUtils.PathTestBase):
    """Test OutputOptions dataclass"""

    def test_default_initialization(self):
        """Test OutputOptions initialization with defaults"""
        from Machine.models.machine import OutputUnits

        opts = OutputOptions()

        # Main output options
        self.assertEqual(opts.units, OutputUnits.METRIC)
        self.assertTrue(opts.output_tool_length_offset)
        self.assertFalse(opts.remote_post)
        self.assertTrue(opts.output_header)

        # Header options (nested)
        self.assertTrue(opts.header.include_date)
        self.assertTrue(opts.header.include_description)
        self.assertTrue(opts.header.include_document_name)
        self.assertTrue(opts.header.include_machine_name)
        self.assertTrue(opts.header.include_project_file)
        self.assertTrue(opts.header.include_units)
        self.assertTrue(opts.header.include_tool_list)
        self.assertTrue(opts.header.include_fixture_list)

        # Comment options (nested)
        self.assertTrue(opts.comments.enabled)
        self.assertEqual(opts.comments.symbol, "(")
        self.assertFalse(opts.comments.include_operation_labels)
        self.assertTrue(opts.comments.include_blank_lines)
        self.assertFalse(opts.comments.output_bcnc_comments)

        # Formatting options (nested)
        self.assertFalse(opts.formatting.line_numbers)
        self.assertEqual(opts.formatting.line_number_start, 100)
        self.assertEqual(opts.formatting.line_number_prefix, "N")
        self.assertEqual(opts.formatting.line_increment, 10)
        self.assertEqual(opts.formatting.command_space, " ")
        self.assertEqual(opts.formatting.end_of_line_chars, "\n")

        # Precision options (nested)
        self.assertEqual(opts.precision.axis, 3)
        self.assertEqual(opts.precision.feed, 3)
        self.assertEqual(opts.precision.spindle, 0)

        # Duplicate options (nested)
        self.assertTrue(opts.duplicates.commands)
        self.assertTrue(opts.duplicates.parameters)

    def test_custom_initialization(self):
        """Test OutputOptions initialization with custom values"""
        from Machine.models.machine import (
            OutputUnits,
            HeaderOptions,
            CommentOptions,
            FormattingOptions,
            PrecisionOptions,
            DuplicateOptions,
        )

        opts = OutputOptions(
            units=OutputUnits.IMPERIAL,
            output_tool_length_offset=False,
            remote_post=True,
            output_header=False,
            header=HeaderOptions(
                include_date=False,
                include_description=False,
                include_document_name=False,
                include_machine_name=False,
                include_project_file=False,
                include_units=False,
                include_tool_list=False,
                include_fixture_list=False,
            ),
            comments=CommentOptions(
                enabled=False,
                symbol=";",
                include_operation_labels=True,
                include_blank_lines=False,
                output_bcnc_comments=True,
            ),
            formatting=FormattingOptions(
                line_numbers=True,
                line_number_start=10,
                line_number_prefix="L",
                line_increment=5,
                command_space="",
                end_of_line_chars="\r\n",
            ),
            precision=PrecisionOptions(axis=4, feed=2, spindle=1),
            duplicates=DuplicateOptions(commands=False, parameters=False),
        )

        # Verify custom values
        self.assertEqual(opts.units, OutputUnits.IMPERIAL)
        self.assertFalse(opts.output_tool_length_offset)
        self.assertTrue(opts.remote_post)
        self.assertFalse(opts.output_header)
        self.assertFalse(opts.header.include_date)
        self.assertFalse(opts.header.include_units)
        self.assertFalse(opts.comments.enabled)
        self.assertEqual(opts.comments.symbol, ";")
        self.assertTrue(opts.comments.include_operation_labels)
        self.assertFalse(opts.comments.include_blank_lines)
        self.assertTrue(opts.comments.output_bcnc_comments)
        self.assertTrue(opts.formatting.line_numbers)
        self.assertEqual(opts.formatting.line_number_start, 10)
        self.assertEqual(opts.formatting.line_number_prefix, "L")
        self.assertEqual(opts.formatting.line_increment, 5)
        self.assertEqual(opts.formatting.command_space, "")
        self.assertEqual(opts.formatting.end_of_line_chars, "\r\n")
        self.assertEqual(opts.precision.axis, 4)
        self.assertEqual(opts.precision.feed, 2)
        self.assertEqual(opts.precision.spindle, 1)
        self.assertFalse(opts.duplicates.commands)
        self.assertFalse(opts.duplicates.parameters)

    def test_equality(self):
        """Test OutputOptions equality comparison"""
        opts1 = OutputOptions()
        opts2 = OutputOptions()
        self.assertEqual(opts1, opts2)

        opts2.comments.enabled = False
        self.assertNotEqual(opts1, opts2)


class TestProcessingOptions(PathTestUtils.PathTestBase):
    """Test ProcessingOptions dataclass"""

    def test_default_initialization(self):
        """Test ProcessingOptions initialization with defaults"""
        opts = ProcessingOptions()

        # Default values
        self.assertFalse(opts.early_tool_prep)
        self.assertFalse(opts.filter_inefficient_moves)
        self.assertFalse(opts.split_arcs)
        self.assertTrue(opts.tool_change)
        self.assertFalse(opts.translate_rapid_moves)
        self.assertIsNone(opts.return_to)

    def test_custom_initialization(self):
        """Test ProcessingOptions initialization with custom values"""
        opts = ProcessingOptions(
            early_tool_prep=True,
            filter_inefficient_moves=True,
            split_arcs=True,
            tool_change=False,
            translate_rapid_moves=True,
            return_to=(10.0, 20.0, 30.0),
        )

        # Verify custom values
        self.assertTrue(opts.early_tool_prep)
        self.assertTrue(opts.filter_inefficient_moves)
        self.assertTrue(opts.split_arcs)
        self.assertFalse(opts.tool_change)
        self.assertTrue(opts.translate_rapid_moves)
        self.assertEqual(opts.return_to, (10.0, 20.0, 30.0))

    def test_equality(self):
        """Test ProcessingOptions equality comparison"""
        opts1 = ProcessingOptions()
        opts2 = ProcessingOptions()
        self.assertEqual(opts1, opts2)

        opts2.filter_inefficient_moves = True
        self.assertNotEqual(opts1, opts2)


class TestToolhead(PathTestUtils.PathTestBase):
    """Test Toolhead dataclass"""

    def test_toolhead_initialization(self):
        """Test Toolhead initialization with defaults"""
        toolhead = Toolhead(
            name="Main Toolhead",
            max_power_kw=5.5,
            max_rpm=24000,
            min_rpm=1000,
            tool_change="automatic",
        )

        self.assertEqual(toolhead.name, "Main Toolhead")
        self.assertEqual(toolhead.max_power_kw, 5.5)
        self.assertEqual(toolhead.max_rpm, 24000)
        self.assertEqual(toolhead.min_rpm, 1000)
        self.assertEqual(toolhead.tool_change, "automatic")
        # Default toolhead_wait should be 0.0
        self.assertEqual(toolhead.toolhead_wait, 0.0)

    def test_toolhead_serialization(self):
        """Test to_dict and from_dict"""
        toolhead = Toolhead(
            name="Test Toolhead",
            id="toolhead-001",
            max_power_kw=3.0,
            max_rpm=18000,
            min_rpm=500,
            tool_change="manual",
            toolhead_wait=1.5,
        )

        data = toolhead.to_dict()
        self.assertEqual(data["name"], "Test Toolhead")
        self.assertEqual(data["id"], "toolhead-001")
        self.assertEqual(data["max_power_kw"], 3.0)
        self.assertEqual(data["toolhead_wait"], 1.5)

        restored = Toolhead.from_dict(data)
        self.assertEqual(restored.name, toolhead.name)
        self.assertEqual(restored.id, toolhead.id)
        self.assertEqual(restored.max_power_kw, toolhead.max_power_kw)
        self.assertEqual(restored.toolhead_wait, toolhead.toolhead_wait)


class TestMachineFactory(PathTestUtils.PathTestBase):
    """Test MachineFactory class for loading/saving configurations"""

    def setUp(self):
        """Set up test fixtures with temporary directory"""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = pathlib.Path(self.temp_dir)
        MachineFactory.set_config_directory(self.temp_dir)

    def tearDown(self):
        """Clean up temporary directory"""
        import shutil

        if self.temp_path.exists():
            shutil.rmtree(self.temp_path)

    def test_set_and_get_config_directory(self):
        """Test setting and getting configuration directory"""
        test_dir = self.temp_path / "test_configs"
        MachineFactory.set_config_directory(test_dir)

        config_dir = MachineFactory.get_config_directory()
        self.assertEqual(config_dir, test_dir)
        self.assertTrue(config_dir.exists())

    def test_save_and_load_configuration(self):
        """Test saving and loading a machine configuration"""
        # Create a test machine
        machine = Machine(
            name="Test Machine",
            manufacturer="Test Corp",
            description="Test description",
            configuration_units="metric",
        )

        # Add axes to make it an XYZ machine
        machine.add_linear_axis("X", FreeCAD.Vector(1, 0, 0))
        machine.add_linear_axis("Y", FreeCAD.Vector(0, 1, 0))
        machine.add_linear_axis("Z", FreeCAD.Vector(0, 0, 1))

        # Add a toolhead
        toolhead = Toolhead(
            name="Main Toolhead",
            max_power_kw=5.5,
            max_rpm=24000,
            min_rpm=1000,
        )
        machine.toolheads.append(toolhead)

        # Save configuration
        filepath = MachineFactory.save_configuration(machine, "test_machine.fcm")
        self.assertTrue(filepath.exists())

        # Load configuration
        loaded_machine = MachineFactory.load_configuration("test_machine.fcm")

        # Verify loaded data
        self.assertEqual(loaded_machine.name, "Test Machine")
        self.assertEqual(loaded_machine.manufacturer, "Test Corp")
        self.assertEqual(loaded_machine.description, "Test description")
        self.assertEqual(loaded_machine.machine_type, "xyz")
        self.assertEqual(loaded_machine.configuration_units, "metric")
        self.assertEqual(len(loaded_machine.toolheads), 1)
        self.assertEqual(loaded_machine.toolheads[0].name, "Main Toolhead")

    def test_save_configuration_auto_filename(self):
        """Test saving with automatic filename generation"""
        machine = Machine(name="My Test Machine")

        filepath = MachineFactory.save_configuration(machine)

        # Should create file with sanitized name
        self.assertTrue(filepath.exists())
        self.assertEqual(filepath.name, "My_Test_Machine.fcm")

    def test_load_nonexistent_file(self):
        """Test loading a file that doesn't exist"""
        with self.assertRaises(FileNotFoundError):
            MachineFactory.load_configuration("nonexistent.fcm")

    def test_create_default_machine_data(self):
        """Test creating default machine data dictionary"""
        data = MachineFactory.create_default_machine_data()

        self.assertIsInstance(data, dict)
        # The data structure has nested "machine" key
        self.assertIn("machine", data)
        self.assertEqual(data["machine"]["name"], "New Machine")
        self.assertIn("toolheads", data["machine"])

    def test_list_configuration_files(self):
        """Test listing available configuration files"""
        # Create some test configurations
        machine1 = Machine(name="Machine 1")
        machine2 = Machine(name="Machine 2")

        MachineFactory.save_configuration(machine1, "machine1.fcm")
        MachineFactory.save_configuration(machine2, "machine2.fcm")

        # List configurations
        configs = MachineFactory.list_configuration_files()

        # Should include <any> plus our two machines
        self.assertGreaterEqual(len(configs), 3)
        self.assertEqual(configs[0][0], "<any>")

        # Check that our machines are in the list (by display name, not filename)
        names = [name for name, path in configs]
        self.assertIn("Machine 1", names)
        self.assertIn("Machine 2", names)

    def test_list_configurations(self):
        """Test listing configuration names"""
        machine = Machine(name="Test Machine")
        MachineFactory.save_configuration(machine, "test.fcm")

        configs = MachineFactory.list_configurations()

        self.assertIsInstance(configs, list)
        self.assertIn("<any>", configs)
        # Returns display name from JSON, not filename
        self.assertIn("Test Machine", configs)

    def test_delete_configuration(self):
        """Test deleting a configuration file"""
        machine = Machine(name="To Delete")
        filepath = MachineFactory.save_configuration(machine, "delete_me.fcm")

        self.assertTrue(filepath.exists())

        # Delete the configuration
        result = MachineFactory.delete_configuration("delete_me.fcm")
        self.assertTrue(result)
        self.assertFalse(filepath.exists())

        # Try deleting again (should return False)
        result = MachineFactory.delete_configuration("delete_me.fcm")
        self.assertFalse(result)

    def test_get_builtin_config(self):
        """Test getting built-in machine configurations"""
        # Test each built-in config type
        config_types = ["XYZ", "XYZAC", "XYZBC", "XYZA", "XYZB"]

        for config_type in config_types:
            machine = MachineFactory.get_builtin_config(config_type)
            self.assertIsInstance(machine, Machine)
            self.assertIsNotNone(machine.name)

    def test_get_builtin_config_invalid_type(self):
        """Test getting built-in config with invalid type"""
        with self.assertRaises(ValueError):
            MachineFactory.get_builtin_config("INVALID")

    def test_serialization_roundtrip(self):
        """Test full serialization roundtrip with complex machine"""
        # Create a complex machine with all components
        machine = Machine(
            name="Complex Machine",
            manufacturer="Test Mfg",
            description="Full featured machine",
            configuration_units="metric",
        )

        # Add toolhead
        machine.toolheads.append(
            Toolhead(
                name="Main",
                max_power_kw=7.5,
                max_rpm=30000,
            )
        )

        # Configure post-processor settings
        machine.output.comments.enabled = False
        machine.output.precision.axis = 4
        machine.output.formatting.line_increment = 5

        # line_increment is set to default 10 in OutputOptions

        # Save and load
        filepath = MachineFactory.save_configuration(machine, "complex.fcm")
        loaded = MachineFactory.load_configuration(filepath)

        # Verify all components
        self.assertEqual(loaded.name, machine.name)
        self.assertEqual(loaded.manufacturer, machine.manufacturer)
        self.assertEqual(len(loaded.toolheads), 1)
        self.assertFalse(loaded.output.comments.enabled)
        self.assertEqual(loaded.output.precision.axis, 4)
        self.assertEqual(loaded.output.formatting.line_increment, 5)

    def test_register_addon_machine_dir(self):
        """register_addon_machine_dir() adds path to _addon_machine_dirs without duplicates.

        Given: a temporary directory not yet registered
        When: register_addon_machine_dir() is called twice with the same path
        Then: _addon_machine_dirs contains it exactly once
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            p = pathlib.Path(tmpdir)
            before = len(MachineFactory._addon_machine_dirs)
            MachineFactory.register_addon_machine_dir(p)
            self.assertEqual(len(MachineFactory._addon_machine_dirs), before + 1)
            MachineFactory.register_addon_machine_dir(p)  # second call — no duplicate
            self.assertEqual(len(MachineFactory._addon_machine_dirs), before + 1)
            MachineFactory._addon_machine_dirs[:] = [
                (ns, d) for ns, d in MachineFactory._addon_machine_dirs if d != p
            ]

    def test_list_addon_templates(self):
        """list_addon_templates() returns machines from registered addon dirs.

        Given: a registered addon directory containing one .fcm file with name "Addon Machine"
        When: list_addon_templates() is called
        Then: "Addon Machine" appears in the returned display names
        """
        import json

        with tempfile.TemporaryDirectory() as tmpdir:
            p = pathlib.Path(tmpdir)
            fcm = {"machine": {"name": "Addon Machine", "axes": {}, "spindles": []}}
            (p / "addon_machine.fcm").write_text(json.dumps(fcm))
            MachineFactory.register_addon_machine_dir(p)
            templates = MachineFactory.list_addon_templates()
            names = [dn for _ns, dn, _path in templates]
            self.assertIn("Addon Machine", names)
            MachineFactory._addon_machine_dirs[:] = [
                (ns, d) for ns, d in MachineFactory._addon_machine_dirs if d != p
            ]

    def test_get_machine_from_addon(self):
        """get_machine() can load a machine from a registered addon directory.

        Given: a registered addon directory containing a valid .fcm file
              for "Addon Test Machine"
        When: get_machine("Addon Test Machine") is called
        Then: a Machine object with name "Addon Test Machine" is returned
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            p = pathlib.Path(tmpdir)
            machine = Machine(name="Addon Test Machine")
            import json

            (p / "addon_test.fcm").write_text(json.dumps(machine.to_dict()))
            MachineFactory.register_addon_machine_dir(p)
            loaded = MachineFactory.get_machine("Addon Test Machine")
            self.assertIsInstance(loaded, Machine)
            self.assertEqual(loaded.name, "Addon Test Machine")
            MachineFactory._addon_machine_dirs[:] = [
                (ns, d) for ns, d in MachineFactory._addon_machine_dirs if d != p
            ]

    def test_list_configurations_includes_addon(self):
        """list_configurations() includes addon machine names.

        Given: a registered addon directory with a machine named "Community Mill"
        When: list_configurations() is called
        Then: "Community Mill" appears in the returned list
        """
        import json

        with tempfile.TemporaryDirectory() as tmpdir:
            p = pathlib.Path(tmpdir)
            fcm = {"machine": {"name": "Community Mill", "axes": {}, "spindles": []}}
            (p / "community_mill.fcm").write_text(json.dumps(fcm))
            MachineFactory.register_addon_machine_dir(p)
            configs = MachineFactory.list_configurations()
            self.assertIn("Community Mill", configs)
            MachineFactory._addon_machine_dirs[:] = [
                (ns, d) for ns, d in MachineFactory._addon_machine_dirs if d != p
            ]


class TestMachineValidation(PathTestUtils.PathTestBase):
    """Test validate_job_against_machine machine-safety checks"""

    @classmethod
    def setUpClass(cls):
        import Path.Main.Job as PathJob
        import Path.Tool.Controller as PathToolController

        cls.doc = FreeCAD.newDocument("TestMachineValidation")
        box = cls.doc.addObject("Part::Box", "Box")
        box.Length = 50
        box.Width = 50
        box.Height = 10
        cls.doc.recompute()

        cls.job = PathJob.Create("ValidationJob", [box], None)
        cls.doc.recompute()

        # Replace any default tool controllers with one known controller.
        for tc in list(cls.job.Tools.Group):
            cls.doc.removeObject(tc.Name)
        cls.doc.recompute()
        cls.tc = PathToolController.Create("ValidationTC", toolNumber=1)
        cls.job.Proxy.addToolController(cls.tc)
        cls.doc.recompute()

    @classmethod
    def tearDownClass(cls):
        FreeCAD.closeDocument(cls.doc.Name)

    def setUp(self):
        self.machine = Machine(name="Validation Machine")
        self.machine.add_linear_axis("X", (1, 0, 0), min_limit=0, max_limit=500)
        self.machine.add_linear_axis("Y", (0, 1, 0), min_limit=0, max_limit=400)
        self.machine.add_linear_axis("Z", (0, 0, 1), min_limit=-100, max_limit=100)
        self.machine.add_spindle("Spindle", max_rpm=20000, min_rpm=1000)
        self.tc.SpindleSpeed = 12000.0
        self.job.Machine = ""
        self._added_ops = []

    def tearDown(self):
        for op in self._added_ops:
            self.doc.removeObject(op.Name)
        self.doc.recompute()

    def _add_op_with_commands(self, commands):
        import Path

        op = self.doc.addObject("Path::Feature", "ValidationOp")
        op.Path = Path.Path(commands)
        self.job.Proxy.addOperation(op)
        self.doc.recompute()
        self._added_ops.append(op)
        return op

    def test_no_machine_returns_warning(self):
        """A job with no resolvable machine yields a single no_machine warning"""
        violations = validate_job_against_machine(self.job)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0].code, "no_machine")
        self.assertEqual(violations[0].severity, "warning")
        self.assertFalse(violations[0].is_error)

    def test_valid_job_returns_empty(self):
        """A job within machine limits yields no violations"""
        import Path

        self._add_op_with_commands(
            [
                Path.Command("G0", {"X": 10.0, "Y": 10.0, "Z": 50.0}),
                Path.Command("G1", {"X": 100.0, "Y": 100.0, "F": 20.0}),
            ]
        )
        violations = validate_job_against_machine(self.job, self.machine)
        self.assertEqual(violations, [])

    def test_spindle_rpm_exceeded(self):
        """A tool controller above the machine's max RPM yields an error"""
        self.tc.SpindleSpeed = 99999.0
        violations = validate_job_against_machine(self.job, self.machine)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0].code, "spindle_rpm_exceeded")
        self.assertTrue(violations[0].is_error)
        self.assertEqual(violations[0].details["max_rpm"], 20000)

    def test_axis_limit_exceeded(self):
        """A command moving beyond an axis envelope yields an error"""
        import Path

        self._add_op_with_commands(
            [
                Path.Command("G0", {"X": 10.0, "Y": 10.0, "Z": 50.0}),
                Path.Command("G1", {"X": 5000.0, "Y": 10.0, "F": 20.0}),
            ]
        )
        violations = validate_job_against_machine(self.job, self.machine)
        axis = [v for v in violations if v.code == "axis_limit_exceeded"]
        self.assertEqual(len(axis), 1)
        self.assertTrue(axis[0].is_error)
        self.assertEqual(axis[0].command_index, 1)
        self.assertEqual(axis[0].details["axis"], "X")
        self.assertEqual(len(violations), 1)

    def test_path_spindle_command_exceeded(self):
        """An S word in the path above the machine's max RPM yields an error"""
        import Path

        self._add_op_with_commands([Path.Command("M3", {"S": 30000.0})])
        violations = validate_job_against_machine(self.job, self.machine)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0].code, "spindle_rpm_exceeded")
        self.assertTrue(violations[0].is_error)

    def test_violation_to_dict(self):
        """Violation.to_dict serializes all fields"""
        self.tc.SpindleSpeed = 99999.0
        violations = validate_job_against_machine(self.job, self.machine)
        d = violations[0].to_dict()
        self.assertEqual(d["code"], "spindle_rpm_exceeded")
        self.assertEqual(d["severity"], "error")
        self.assertIn("message", d)
        self.assertIn("details", d)
