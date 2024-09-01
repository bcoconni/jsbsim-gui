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

from jsbsim import FGPropertyManager

from src.property_list import PropertyList


class TestPropertyList(unittest.TestCase):
    def test_init(self):
        prop_list = PropertyList()

        for _, _ in prop_list:
            self.fail("PropertyList should be empty")

    def test_add_one_property(self):
        prop_list = PropertyList()
        pm = FGPropertyManager()
        prop1 = pm.get_node("a/b/c", True)

        prop_list.add_property(prop1)
        self.assertEqual(list(prop_list)[0], ("c", prop1))

    def test_add_two_properties(self):
        prop_list = PropertyList()
        pm = FGPropertyManager()
        prop1 = pm.get_node("a/b/c", True)
        prop2 = pm.get_node("a/b/d", True)

        prop_list.add_property(prop1)
        prop_list.add_property(prop2)
        self.assertEqual(list(prop_list), [("c", prop1), ("d", prop2)])

    def test_add_two_properties_with_same_name(self):
        prop_list = PropertyList()
        pm = FGPropertyManager()
        prop1 = pm.get_node("a/b/c", True)
        prop2 = pm.get_node("a/d/c", True)

        prop_list.add_property(prop1)
        prop_list.add_property(prop2)
        self.assertEqual(list(prop_list), [("b/c", prop1), ("d/c", prop2)])

    def test_add_three_properties_with_common_path(self):
        prop_list = PropertyList()
        pm = FGPropertyManager()
        prop1 = pm.get_node("a/b/c", True)
        prop2 = pm.get_node("a/b/d", True)
        prop3 = pm.get_node("a/e/c", True)

        prop_list.add_property(prop1)
        prop_list.add_property(prop2)
        self.assertEqual(list(prop_list), [("c", prop1), ("d", prop2)])

        prop_list.add_property(prop3)
        self.assertEqual(
            list(prop_list), [("b/c", prop1), ("b/d", prop2), ("e/c", prop3)]
        )
