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

from jsbsim_gui.plotinfo_list import PlotInfoList, PlotInfo


class TestPlotInfoList(unittest.TestCase):
    def test_init_default(self):
        plot_info = PlotInfoList()

        for _, _ in plot_info:
            self.fail("PropertyList should be empty")

    def test_init_empty_list(self):
        plot_info = PlotInfoList([])

        for _, _ in plot_info:
            self.fail("PropertyList should be empty")

    def test_init_one_property(self):
        pm = FGPropertyManager()
        prop1 = pm.get_node("a/b/c", True)
        plot_info = PlotInfoList([prop1])
        self.assertEqual(list(plot_info)[0], PlotInfo(prop1, "c"))

    def test_init_two_properties(self):
        pm = FGPropertyManager()
        prop1 = pm.get_node("a/b/c", True)
        prop2 = pm.get_node("a/b/d", True)
        plot_info = PlotInfoList([prop1, prop2])
        self.assertEqual(list(plot_info), [PlotInfo(prop1, "c"), PlotInfo(prop2, "d")])

    def test_init_two_properties_with_same_name(self):
        pm = FGPropertyManager()
        prop1 = pm.get_node("a/b/c", True)
        prop2 = pm.get_node("a/d/c", True)
        plot_info = PlotInfoList([prop1, prop2])
        self.assertEqual(
            list(plot_info), [PlotInfo(prop1, "b/c"), PlotInfo(prop2, "d/c")]
        )

    def test_init_one_add_one_property(self):
        pm = FGPropertyManager()
        prop1 = pm.get_node("a/b/c", True)
        prop2 = pm.get_node("a/d/c", True)
        l = [prop1]
        plot_info = PlotInfoList(l)
        plot_info.add_properties([prop2])
        self.assertEqual(
            list(plot_info), [PlotInfo(prop1, "b/c"), PlotInfo(prop2, "d/c")]
        )
        # Check that the original list is not modified
        self.assertEqual(l, [prop1])

    def test_add_no_property(self):
        plot_info = PlotInfoList()
        plot_info.add_properties([])
        self.assertEqual(list(plot_info), [])

    def test_add_one_property_list(self):
        plot_info = PlotInfoList()
        pm = FGPropertyManager()
        prop1 = pm.get_node("a/b/c", True)

        plot_info.add_properties([prop1])
        self.assertEqual(list(plot_info)[0], PlotInfo(prop1, "c"))

    def test_add_two_properties_list(self):
        plot_info = PlotInfoList()
        pm = FGPropertyManager()
        prop1 = pm.get_node("a/b/c", True)
        prop2 = pm.get_node("a/b/d", True)

        plot_info.add_properties([prop1, prop2])
        self.assertEqual(list(plot_info), [PlotInfo(prop1, "c"), PlotInfo(prop2, "d")])

    def test_add_two_properties_list_with_same_name(self):
        plot_info = PlotInfoList()
        pm = FGPropertyManager()
        prop1 = pm.get_node("a/b/c", True)
        prop2 = pm.get_node("a/d/c", True)

        plot_info.add_properties([prop1, prop2])
        self.assertEqual(
            list(plot_info), [PlotInfo(prop1, "b/c"), PlotInfo(prop2, "d/c")]
        )

    def test_add_two_properties_list_and_one_property_with_common_path(self):
        plot_info = PlotInfoList()
        pm = FGPropertyManager()
        prop1 = pm.get_node("a/b/c", True)
        prop2 = pm.get_node("a/b/d", True)
        prop3 = pm.get_node("a/e/c", True)

        plot_info.add_properties([prop1, prop2])
        self.assertEqual(list(plot_info), [PlotInfo(prop1, "c"), PlotInfo(prop2, "d")])

        plot_info.add_properties([prop3])
        self.assertEqual(
            list(plot_info),
            [PlotInfo(prop1, "b/c"), PlotInfo(prop2, "b/d"), PlotInfo(prop3, "e/c")],
        )

    def test_add_two_properties_list_and_one_property_list_with_common_path(self):
        plot_info = PlotInfoList()
        pm = FGPropertyManager()
        prop1 = pm.get_node("a/b/c", True)
        prop2 = pm.get_node("a/b/d", True)
        prop3 = pm.get_node("a/e/c", True)

        plot_info.add_properties([prop1, prop2])
        self.assertEqual(list(plot_info), [PlotInfo(prop1, "c"), PlotInfo(prop2, "d")])

        plot_info.add_properties([prop3])
        self.assertEqual(
            list(plot_info),
            [PlotInfo(prop1, "b/c"), PlotInfo(prop2, "b/d"), PlotInfo(prop3, "e/c")],
        )

    def test_pop_one_property(self):
        plot_info = PlotInfoList()
        pm = FGPropertyManager()
        prop1 = pm.get_node("a/b/c", True)

        plot_info.add_properties([prop1])
        plot_info.pop(0)
        self.assertEqual(list(plot_info), [])

    def test_pop_first_of_two_properties_list_with_same_name(self):
        plot_info = PlotInfoList()
        pm = FGPropertyManager()
        prop1 = pm.get_node("a/b/c", True)
        prop2 = pm.get_node("a/d/c", True)

        plot_info.add_properties([prop1, prop2])
        plot_info.pop(0)
        self.assertEqual(list(plot_info)[0], PlotInfo(prop2, "c"))

    def test_pop_last_of_two_properties_list_with_same_name(self):
        plot_info = PlotInfoList()
        pm = FGPropertyManager()
        prop1 = pm.get_node("a/b/c", True)
        prop2 = pm.get_node("a/d/c", True)

        plot_info.add_properties([prop1, prop2])
        plot_info.pop(1)
        self.assertEqual(list(plot_info)[0], PlotInfo(prop1, "c"))

    def test_pop_first_of_three_properties_list_with_common_path(self):
        plot_info = PlotInfoList()
        pm = FGPropertyManager()
        prop1 = pm.get_node("a/b/c", True)
        prop2 = pm.get_node("a/b/d", True)
        prop3 = pm.get_node("a/e/c", True)

        plot_info.add_properties([prop1, prop2, prop3])
        plot_info.pop(0)
        self.assertEqual(
            list(plot_info), [PlotInfo(prop2, "b/d"), PlotInfo(prop3, "e/c")]
        )

    def test_pop_second_of_three_properties_list_with_common_path(self):
        plot_info = PlotInfoList()
        pm = FGPropertyManager()
        prop1 = pm.get_node("a/b/c", True)
        prop2 = pm.get_node("a/b/d", True)
        prop3 = pm.get_node("a/e/c", True)

        plot_info.add_properties([prop1, prop2, prop3])
        plot_info.pop(1)
        self.assertEqual(
            list(plot_info), [PlotInfo(prop1, "b/c"), PlotInfo(prop3, "e/c")]
        )

    def test_pop_last_of_three_properties_list_with_common_path(self):
        plot_info = PlotInfoList()
        pm = FGPropertyManager()
        prop1 = pm.get_node("a/b/c", True)
        prop2 = pm.get_node("a/b/d", True)
        prop3 = pm.get_node("a/e/c", True)

        plot_info.add_properties([prop1, prop2, prop3])
        plot_info.pop(2)
        self.assertEqual(list(plot_info), [PlotInfo(prop1, "c"), PlotInfo(prop2, "d")])

    def test_getitem_one_item(self):
        plot_info = PlotInfoList()
        pm = FGPropertyManager()
        prop1 = pm.get_node("a/b/c", True)

        plot_info.add_properties([prop1])
        self.assertEqual(plot_info[0], PlotInfo(prop1, "c"))

    def test_getitem_two_items(self):
        plot_info = PlotInfoList()
        pm = FGPropertyManager()
        prop1 = pm.get_node("a/b/c", True)
        prop2 = pm.get_node("a/b/d", True)

        plot_info.add_properties([prop1, prop2])
        self.assertEqual(plot_info[0], PlotInfo(prop1, "c"))
        self.assertEqual(plot_info[1], PlotInfo(prop2, "d"))
        self.assertEqual(plot_info[-1], PlotInfo(prop2, "d"))
