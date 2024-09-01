# A Graphical User Interface for JSBSim
#
# Copyright (c) 2024 Bertrand Coconnier
#
# This program is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation; either version 3 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, see <http://www.gnu.org/licenses/>

import unittest

import numpy as np
from jsbsim import FGPropertyManager

from src.property_history import PropertyHistory


class TestPropertyHistory(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.pm = FGPropertyManager()
        self.properties = [
            self.pm.get_node("a", True),
            self.pm.get_node("b", True),
            self.pm.get_node("c", True),
        ]
        self.d_node = self.pm.get_node("d", True)

    def test_init(self):
        prop_hist = PropertyHistory(self.properties)
        for prop in self.properties:
            self.assertTrue(
                np.array_equal(prop_hist.get_property_history(prop), np.empty(0))
            )

    def test_unknown_property(self):
        prop_hist = PropertyHistory(self.properties)
        self.assertRaises(
            ValueError, lambda: prop_hist.get_property_history(self.d_node)
        )

    def test_record_first_entry(self):
        prop_hist = PropertyHistory(self.properties)

        for i, prop in enumerate(self.properties):
            prop.set_double_value(i)
        prop_hist.record()

        for i, prop in enumerate(self.properties):
            self.assertTrue(
                np.array_equal(
                    prop_hist.get_property_history(prop),
                    np.full(1, i, dtype=np.float64),
                )
            )

    def test_record_several_entries(self):
        prop_hist = PropertyHistory(self.properties)

        for i in range(10):
            for j, prop in enumerate(self.properties):
                prop.set_double_value(float(f"{j}.{i}"))
            prop_hist.record()

        for i, prop in enumerate(self.properties):
            self.assertTrue(
                np.array_equal(
                    prop_hist.get_property_history(prop),
                    np.array([float(f"{i}.{j}") for j in range(10)]),
                )
            )

    def test_record_many_entries(self):
        prop_hist = PropertyHistory(self.properties)

        for i in range(prop_hist.CHUNK_SIZE + 10):
            for j, prop in enumerate(self.properties):
                prop.set_double_value(float(f"{j}.{i}"))
            prop_hist.record()

        for i, prop in enumerate(self.properties):
            self.assertTrue(
                np.array_equal(
                    prop_hist.get_property_history(prop),
                    np.array(
                        [float(f"{i}.{j}") for j in range(prop_hist.CHUNK_SIZE + 10)]
                    ),
                )
            )
