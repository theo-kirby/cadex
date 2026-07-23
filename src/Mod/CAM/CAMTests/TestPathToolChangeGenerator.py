# SPDX-License-Identifier: LGPL-2.1-or-later

# ***************************************************************************
# *   Copyright (c) 2021 sliptonic <shopinthewoods@gmail.com>               *
# *                                                                         *
# *   This program is free software; you can redistribute it and/or modify  *
# *   it under the terms of the GNU Lesser General Public License (LGPL)    *
# *   as published by the Free Software Foundation; either version 2 of     *
# *   the License, or (at your option) any later version.                   *
# *   for detail see the LICENCE text file.                                 *
# *                                                                         *
# *   This program is distributed in the hope that it will be useful,       *
# *   but WITHOUT ANY WARRANTY; without even the implied warranty of        *
# *   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the         *
# *   GNU Library General Public License for more details.                  *
# *                                                                         *
# *   You should have received a copy of the GNU Library General Public     *
# *   License along with this program; if not, write to the Free Software   *
# *   Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  *
# *   USA                                                                   *
# *                                                                         *
# ***************************************************************************

import Path
import Path.Base.Generator.toolchange as generator
import CAMTests.PathTestUtils as PathTestUtils

Path.Log.setLevel(Path.Log.Level.DEBUG, Path.Log.thisModule())
Path.Log.trackModule(Path.Log.thisModule())


class TestPathToolChangeGenerator(PathTestUtils.PathTestBase):
    def test00(self):
        """Test Basic Tool Change Generator Return"""

        args = {
            "toolnumber": 1,
            "toollabel": "My Label",
            "spindlespeed": 500,
            "spindledirection": generator.SpindleDirection.OFF,
        }

        results = generator.generate(**args)

        # Get a label
        self.assertTrue(len(results) == 2)
        commentcommand = results[0]
        self.assertTrue(isinstance(commentcommand, Path.Command))
        self.assertTrue(commentcommand.toGCode() == "(My Label)")

        # Get a tool command
        toolcommand = results[1]
        self.assertTrue(toolcommand.Name == "M6")

        # Turn on the spindle
        args["spindledirection"] = generator.SpindleDirection.CW
        results = generator.generate(**args)
        self.assertTrue(len(results) == 3)

        speedcommand = results[2]
        self.assertTrue(speedcommand.Name == "M3")
        self.assertTrue(speedcommand.Parameters["S"] == 500)

        # speed zero with spindle on
        args["spindlespeed"] = 0
        results = generator.generate(**args)
        self.assertTrue(len(results) == 2)
        Path.Log.track(results)

        # negative spindlespeed
        args["spindlespeed"] = -10
        self.assertRaises(ValueError, generator.generate, **args)

    def test10(self):
        """Tool length offset (G43) emission is opt-in and follows M6"""

        # Default: no G43 (backward compatibility)
        results = generator.generate(1, "My Label")
        self.assertTrue(all(cmd.Name != "G43" for cmd in results))

        # Explicit H register with output_tlo=True: G43 H5 right after M6
        results = generator.generate(
            5,
            "T5",
            12000,
            generator.SpindleDirection.CW,
            tool_length_offset=5,
            output_tlo=True,
        )
        names = [cmd.Name for cmd in results]
        self.assertIn("G43", names)
        m6_idx = names.index("M6")
        g43 = results[m6_idx + 1]
        self.assertEqual(g43.Name, "G43")
        self.assertEqual(g43.Parameters["H"], 5)
        # spindle command still emitted after the TLO
        self.assertEqual(results[-1].Name, "M3")
        self.assertEqual(results[-1].Parameters["S"], 12000)

        # tool_length_offset omitted/zero falls back to the tool number
        results = generator.generate(7, "T7", output_tlo=True)
        names = [cmd.Name for cmd in results]
        g43 = results[names.index("G43")]
        self.assertEqual(g43.Parameters["H"], 7)

        results = generator.generate(3, "T3", tool_length_offset=0, output_tlo=True)
        names = [cmd.Name for cmd in results]
        g43 = results[names.index("G43")]
        self.assertEqual(g43.Parameters["H"], 3)

        # output_tlo=False never emits G43 even with an offset supplied
        results = generator.generate(4, "T4", tool_length_offset=4, output_tlo=False)
        self.assertTrue(all(cmd.Name != "G43" for cmd in results))

        # negative offset is invalid
        self.assertRaises(
            ValueError, generator.generate, 1, "T1", tool_length_offset=-2, output_tlo=True
        )
