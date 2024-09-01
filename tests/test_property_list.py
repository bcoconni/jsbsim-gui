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
    def test_init_default(self):
        prop_list = PropertyList()

        for _, _ in prop_list:
            self.fail("PropertyList should be empty")

    def test_init_empty_list(self):
        prop_list = PropertyList([])

        for _, _ in prop_list:
            self.fail("PropertyList should be empty")

    def test_init_one_property(self):
        pm = FGPropertyManager()
        prop1 = pm.get_node("a/b/c", True)
        prop_list = PropertyList([prop1])
        self.assertEqual(list(prop_list)[0], ("c", prop1))

    def test_init_two_properties(self):
        pm = FGPropertyManager()
        prop1 = pm.get_node("a/b/c", True)
        prop2 = pm.get_node("a/b/d", True)
        prop_list = PropertyList([prop1, prop2])
        self.assertEqual(list(prop_list), [("c", prop1), ("d", prop2)])

    def test_init_two_properties_with_same_name(self):
        pm = FGPropertyManager()
        prop1 = pm.get_node("a/b/c", True)
        prop2 = pm.get_node("a/d/c", True)
        prop_list = PropertyList([prop1, prop2])
        self.assertEqual(list(prop_list), [("b/c", prop1), ("d/c", prop2)])

    def test_init_one_add_one_property(self):
        pm = FGPropertyManager()
        prop1 = pm.get_node("a/b/c", True)
        prop2 = pm.get_node("a/d/c", True)
        l = [prop1]
        prop_list = PropertyList(l)
        prop_list.add_properties([prop2])
        self.assertEqual(list(prop_list), [("b/c", prop1), ("d/c", prop2)])
        # Check that the original list is not modified
        self.assertEqual(l, [prop1])

    def test_add_no_property(self):
        prop_list = PropertyList()
        prop_list.add_properties([])
        self.assertEqual(list(prop_list), [])

    def test_add_one_property_list(self):
        prop_list = PropertyList()
        pm = FGPropertyManager()
        prop1 = pm.get_node("a/b/c", True)

        prop_list.add_properties([prop1])
        self.assertEqual(list(prop_list)[0], ("c", prop1))

    def test_add_two_properties_list(self):
        prop_list = PropertyList()
        pm = FGPropertyManager()
        prop1 = pm.get_node("a/b/c", True)
        prop2 = pm.get_node("a/b/d", True)

        prop_list.add_properties([prop1, prop2])
        self.assertEqual(list(prop_list), [("c", prop1), ("d", prop2)])

    def test_add_two_properties_list_with_same_name(self):
        prop_list = PropertyList()
        pm = FGPropertyManager()
        prop1 = pm.get_node("a/b/c", True)
        prop2 = pm.get_node("a/d/c", True)

        prop_list.add_properties([prop1, prop2])
        self.assertEqual(list(prop_list), [("b/c", prop1), ("d/c", prop2)])

    def test_add_two_properties_list_and_one_property_with_common_path(self):
        prop_list = PropertyList()
        pm = FGPropertyManager()
        prop1 = pm.get_node("a/b/c", True)
        prop2 = pm.get_node("a/b/d", True)
        prop3 = pm.get_node("a/e/c", True)

        prop_list.add_properties([prop1, prop2])
        self.assertEqual(list(prop_list), [("c", prop1), ("d", prop2)])

        prop_list.add_properties([prop3])
        self.assertEqual(
            list(prop_list), [("b/c", prop1), ("b/d", prop2), ("e/c", prop3)]
        )

    def test_add_two_properties_list_and_one_property_list_with_common_path(self):
        prop_list = PropertyList()
        pm = FGPropertyManager()
        prop1 = pm.get_node("a/b/c", True)
        prop2 = pm.get_node("a/b/d", True)
        prop3 = pm.get_node("a/e/c", True)

        prop_list.add_properties([prop1, prop2])
        self.assertEqual(list(prop_list), [("c", prop1), ("d", prop2)])

        prop_list.add_properties([prop3])
        self.assertEqual(
            list(prop_list), [("b/c", prop1), ("b/d", prop2), ("e/c", prop3)]
        )

    def test_pop_one_property(self):
        prop_list = PropertyList()
        pm = FGPropertyManager()
        prop1 = pm.get_node("a/b/c", True)

        prop_list.add_properties([prop1])
        prop_list.pop(0)
        self.assertEqual(list(prop_list), [])

    def test_pop_first_of_two_properties_list_with_same_name(self):
        prop_list = PropertyList()
        pm = FGPropertyManager()
        prop1 = pm.get_node("a/b/c", True)
        prop2 = pm.get_node("a/d/c", True)

        prop_list.add_properties([prop1, prop2])
        prop_list.pop(0)
        self.assertEqual(list(prop_list)[0], ("c", prop2))

    def test_pop_last_of_two_properties_list_with_same_name(self):
        prop_list = PropertyList()
        pm = FGPropertyManager()
        prop1 = pm.get_node("a/b/c", True)
        prop2 = pm.get_node("a/d/c", True)

        prop_list.add_properties([prop1, prop2])
        prop_list.pop(1)
        self.assertEqual(list(prop_list)[0], ("c", prop1))

    def test_pop_first_of_three_properties_list_with_common_path(self):
        prop_list = PropertyList()
        pm = FGPropertyManager()
        prop1 = pm.get_node("a/b/c", True)
        prop2 = pm.get_node("a/b/d", True)
        prop3 = pm.get_node("a/e/c", True)

        prop_list.add_properties([prop1, prop2, prop3])
        prop_list.pop(0)
        self.assertEqual(list(prop_list), [("b/d", prop2), ("e/c", prop3)])

    def test_pop_second_of_three_properties_list_with_common_path(self):
        prop_list = PropertyList()
        pm = FGPropertyManager()
        prop1 = pm.get_node("a/b/c", True)
        prop2 = pm.get_node("a/b/d", True)
        prop3 = pm.get_node("a/e/c", True)

        prop_list.add_properties([prop1, prop2, prop3])
        prop_list.pop(1)
        self.assertEqual(list(prop_list), [("b/c", prop1), ("e/c", prop3)])

    def test_pop_last_of_three_properties_list_with_common_path(self):
        prop_list = PropertyList()
        pm = FGPropertyManager()
        prop1 = pm.get_node("a/b/c", True)
        prop2 = pm.get_node("a/b/d", True)
        prop3 = pm.get_node("a/e/c", True)

        prop_list.add_properties([prop1, prop2, prop3])
        prop_list.pop(2)
        self.assertEqual(list(prop_list), [("c", prop1), ("d", prop2)])

    def test_getitem_one_item(self):
        prop_list = PropertyList()
        pm = FGPropertyManager()
        prop1 = pm.get_node("a/b/c", True)

        prop_list.add_properties([prop1])
        self.assertEqual(prop_list[0], ("c", prop1))

    def test_getitem_two_items(self):
        prop_list = PropertyList()
        pm = FGPropertyManager()
        prop1 = pm.get_node("a/b/c", True)
        prop2 = pm.get_node("a/b/d", True)

        prop_list.add_properties([prop1, prop2])
        self.assertEqual(prop_list[0], ("c", prop1))
        self.assertEqual(prop_list[1], ("d", prop2))
        self.assertEqual(prop_list[-1], ("d", prop2))
