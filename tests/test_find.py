# A Graphical User Interface for JSBSim
#
# Copyright (c) 2026 Bertrand Coconnier
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
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Dict, Optional
from unittest.mock import Mock

from jsbsim_gui.find import (
    PropertyOccurrencesTree,
    TextSubstitutionRegion,
    PropertyTreeNode,
    _node_in_text,
    _nodes_in_text,
    _normalize_attribute_names,
    _search_property_occurrences,
)
from jsbsim_gui.tree_node import TextRegion, XMLNode, XMLNodeBuilder


class TestPropertySearch(unittest.TestCase):
    def test_numeric_index_wildcards_match_optional_zero_and_one_or_more_digits(
        self,
    ) -> None:
        tree = PropertyOccurrencesTree.__new__(PropertyOccurrencesTree)
        tree._controller = Mock()
        tree._controller.get_property_list.return_value = [
            Mock(get_fully_qualified_name=Mock(return_value=path))
            for path in (
                "/fdm/engine/blade",
                "/fdm/engine[0]/blade",
                "/fdm/engine[1]/blade",
                "/fdm/engine[12]/blade",
                "/fdm/engine[a]/blade",
            )
        ]
        tree._controller.get_property_root.return_value = Mock(
            get_fully_qualified_name=Mock(return_value="/fdm")
        )

        property_tree, _ = tree._find_matching_properties("engine[#]/blade")

        self.assertEqual(
            [node.path for node in property_tree],
            [
                "",
                "/fdm",
                "/fdm/engine",
                "/fdm/engine/blade",
                "/fdm/engine[1]",
                "/fdm/engine[1]/blade",
                "/fdm/engine[12]",
                "/fdm/engine[12]/blade",
            ],
        )

    def test_terminal_index_wildcard_requires_a_path_boundary(self) -> None:
        tree = PropertyOccurrencesTree.__new__(PropertyOccurrencesTree)
        tree._controller = Mock()
        tree._controller.get_property_list.return_value = [
            Mock(get_fully_qualified_name=Mock(return_value=path))
            for path in (
                "/fdm/n1",
                "/fdm/n1/gen",
                "/fdm/n1[23]/gen",
                "/fdm/n1-gen",
            )
        ]
        tree._controller.get_property_root.return_value = Mock(
            get_fully_qualified_name=Mock(return_value="/fdm")
        )

        property_tree, _ = tree._find_matching_properties("n1[#]")
        self.assertEqual(
            [node.path for node in property_tree],
            [
                "",
                "/fdm",
                "/fdm/n1",
                "/fdm/n1/gen",
                "/fdm/n1[23]",
                "/fdm/n1[23]/gen",
            ],
        )

        property_tree, _ = tree._find_matching_properties("n1[#]-gen")
        self.assertEqual([node.path for node in property_tree], [""])


class TestPropertyTreeNode(unittest.TestCase):
    def test_constructor_builds_nested_nodes_and_parent_links(self) -> None:
        tree = PropertyTreeNode("/fdm/engine[1]/rpm")
        self.assertEqual([node.name for node in tree], ["", "fdm", "engine[1]", "rpm"])
        for parent in tree:
            for child in parent.children:
                self.assertIs(child.parent, parent)
        self.assertEqual(
            tree.children[0].children[0].children[0].path, "/fdm/engine[1]/rpm"
        )

    def test_constructor_with_single_name_or_empty_name(self) -> None:
        for name in ("", "rpm"):
            with self.subTest(name=name):
                tree = PropertyTreeNode(name)
                self.assertEqual(tree.name, name)
                self.assertIsNone(tree.parent)
                self.assertEqual(tree.children, [])

    def test_add_shared_prefixes_duplicates_and_prefix_paths(self) -> None:
        tree = PropertyTreeNode("")
        for path in (
            "/fdm/engine/rpm",
            "/fdm/engine/thrust",
            "/fdm/engine/rpm",
            "/fdm/engine",
        ):
            tree.add(path)

        self.assertEqual(
            [node.path for node in tree],
            ["", "/fdm", "/fdm/engine", "/fdm/engine/rpm", "/fdm/engine/thrust"],
        )
        engine = tree.find("/fdm/engine")
        self.assertIsNotNone(engine)
        rpm = tree.find("/fdm/engine/rpm")
        self.assertIsNotNone(rpm)
        assert rpm is not None
        self.assertIs(rpm.parent, engine)

    def test_add_extends_a_leaf_and_creates_siblings(self) -> None:
        tree = PropertyTreeNode("")
        tree.add("/a")
        tree.add("/a/b")
        tree.add("/c")
        self.assertEqual([node.path for node in tree], ["", "/a", "/a/b", "/c"])

    def test_find_existing_and_missing_paths(self) -> None:
        tree = PropertyTreeNode("/a/b/c")
        tree.add("/a/d")
        self.assertIs(tree.find("/a/b/c"), tree.children[0].children[0].children[0])
        self.assertIs(tree.find("/a"), tree.children[0])
        for path in ("/missing", "/a/missing", "/a/b/c/missing", "/a/bc"):
            with self.subTest(path=path):
                self.assertIsNone(tree.find(path))


class TestPropertyTextSearch(unittest.TestCase):
    def setUp(self) -> None:
        self.tree = PropertyTreeNode("")
        for path in ("/fdm/engine/rpm", "/fdm/engine[1]/rpm", "/position/altitude"):
            self.tree.add(path)

    def test_node_in_text_absolute_and_relative_positions(self) -> None:
        cases = (
            ("prefix /fdm/engine/rpm suffix", False, (7, 22)),
            ("prefix fdm/engine/rpm suffix", True, (7, 21)),
            ("fdm/engine/rpm", False, None),
            ("", False, None),
            ("no matching property", True, None),
        )
        for text, relative, expected in cases:
            with self.subTest(text=text, relative=relative):
                self.assertEqual(_node_in_text(self.tree, text, relative), expected)

    def test_optional_zero_indices_at_each_level(self) -> None:
        cases = (
            ("/fdm/engine/rpm", (0, 15)),
            ("/fdm[0]/engine/rpm", (0, 18)),
            ("/fdm/engine[0]/rpm", (0, 18)),
            ("/fdm[0]/engine[0]/rpm[0]", (0, 24)),
            ("/fdm/engine[1]/rpm[0]", (0, 21)),
        )
        for text, expected in cases:
            with self.subTest(text=text):
                self.assertEqual(_node_in_text(self.tree, text, False), expected)

    def test_rejects_nonmatching_indices_and_incomplete_paths(self) -> None:
        for text in (
            "/fdm[1]/engine/rpm",
            "/fdm/engine[2]/rpm",
            "/fdm/engine/rpm[1]",
            "/fdm/engine",
            "/fdm/engine/rp",
        ):
            with self.subTest(text=text):
                self.assertIsNone(_node_in_text(self.tree, text, False))

    def test_retries_after_partial_or_invalid_match(self) -> None:
        text = "/fdm/engine[2]/rpm then /fdm/engine/rpm"
        self.assertEqual(_node_in_text(self.tree, text, False), (24, 39))
        text = "/fdm/not-a-property then /fdm/engine/rpm"
        self.assertEqual(_node_in_text(self.tree, text, False), (25, 40))

    def test_recursive_match_respects_start_and_end(self) -> None:
        branch = self.tree.find("/fdm")
        self.assertIsInstance(branch, PropertyTreeNode)
        assert isinstance(branch, PropertyTreeNode)
        text = "prefix /fdm/engine/rpm"
        self.assertEqual(_node_in_text(branch, text, False, 7, 11), (7, 22))
        self.assertIsNone(_node_in_text(branch, text, False, 7, 10))

    def test_empty_tree_has_no_matches(self) -> None:
        tree = PropertyTreeNode("")
        self.assertIsNone(_node_in_text(tree, "/fdm/engine/rpm", False))
        self.assertEqual(_nodes_in_text(tree, "/fdm/engine/rpm", False), [])

    def test_nodes_in_text_returns_all_positions_including_adjacent_matches(
        self,
    ) -> None:
        text = "/fdm/engine/rpm/fdm/engine/rpm + /position/altitude"
        self.assertEqual(
            _nodes_in_text(self.tree, text, False),
            [(0, 15), (15, 30), (33, 51)],
        )

    def test_nodes_in_text_with_repeated_relative_matches(self) -> None:
        text = "fdm/engine/rpm; fdm/engine/rpm; fdm/engine/rpm"
        self.assertEqual(
            _nodes_in_text(self.tree, text, True),
            [(0, 14), (16, 30), (32, 46)],
        )

    def test_nodes_in_text_finds_earlier_sibling_before_later_sibling(self) -> None:
        tree = PropertyTreeNode("")
        tree.add("/a")
        tree.add("/b")
        self.assertEqual(_nodes_in_text(tree, "/b /a", False), [(0, 2), (3, 5)])

    def test_nodes_in_text_finds_unindexed_before_later_explicit_zero(self) -> None:
        tree = PropertyTreeNode("")
        tree.add("/a")
        self.assertEqual(_nodes_in_text(tree, "/a /a[0]", False), [(0, 2), (3, 8)])

    def test_nodes_in_text_orders_deep_siblings_and_indexed_paths(self) -> None:
        tree = PropertyTreeNode("")
        for path in ("/a/first", "/a/second", "/b/leaf"):
            tree.add(path)
        text = "/b/leaf /a/second /a/first /a[0]/first"
        self.assertEqual(
            _nodes_in_text(tree, text, False),
            [(0, 7), (8, 17), (18, 26), (27, 38)],
        )

    def test_earlier_valid_path_is_not_skipped_after_invalid_candidates(self) -> None:
        tree = PropertyTreeNode("")
        tree.add("/a/leaf")
        tree.add("/b/leaf")
        text = "/a[1]/leaf /b/leaf /a/missing /a/leaf"
        self.assertEqual(_nodes_in_text(tree, text, False), [(11, 18), (30, 37)])

    def test_many_invalid_candidates_do_not_exhaust_recursion(self) -> None:
        tree = PropertyTreeNode("")
        tree.add("/a/leaf")
        text = "/a/missing " * 1500 + "/a/leaf"
        self.assertEqual(_nodes_in_text(tree, text, False), [(16500, 16507)])


class TestSearchPropertyOccurrences(unittest.TestCase):
    def setUp(self) -> None:
        self.tree = PropertyTreeNode("")
        self.tree.add("/fdm/engine/rpm")
        self.relative_root = PropertyTreeNode("")
        self.relative_root.add("/relative/value")

    def test_empty_inputs_and_no_matches(self) -> None:
        node = XMLNode("node", {"attr": TextRegion("unrelated", 4, 2)}, "a.xml", 0, 1)
        self.assertEqual(_search_property_occurrences(self.tree, None, []), {})
        self.assertEqual(_search_property_occurrences(self.tree, None, [node]), {})
        self.assertEqual(
            _search_property_occurrences(PropertyTreeNode(""), None, [node]), {}
        )

    def test_attributes_data_children_and_multiline_positions(self) -> None:
        root = XMLNode(
            "root",
            {"attr": TextRegion("x /fdm/engine/rpm y /fdm/engine[0]/rpm", 5, 10)},
            "a.xml",
            0,
            1,
        )
        root.data.append(
            TextRegion("header\n  /fdm/engine/rpm\n/fdm/engine/rpm", 9, 20)
        )
        child = XMLNode(
            "child", {"attr": TextRegion("/fdm/engine/rpm", 3, 5)}, "a.xml", 0, 2
        )
        child.parent = root
        self.assertEqual(
            _search_property_occurrences(self.tree, None, [root]),
            {
                "a.xml": [
                    TextRegion("/fdm/engine/rpm", 3, 5),
                    TextRegion("/fdm/engine/rpm", 7, 10),
                    TextRegion("/fdm/engine[0]/rpm", 25, 10),
                    TextRegion("/fdm/engine/rpm", 2, 21),
                    TextRegion("/fdm/engine/rpm", 0, 22),
                ]
            },
        )

    def test_relative_root_is_optional(self) -> None:
        node = XMLNode(
            "node", {"attr": TextRegion("relative/value", 4, 7)}, "a.xml", 0, 1
        )
        self.assertEqual(_search_property_occurrences(self.tree, None, [node]), {})
        self.assertEqual(
            _search_property_occurrences(self.tree, self.relative_root, [node]),
            {"a.xml": [TextRegion("relative/value", 4, 7)]},
        )

    def test_occurrences_preserve_text_order_across_branches(self) -> None:
        tree = PropertyTreeNode("")
        tree.add("/a")
        tree.add("/b")
        node = XMLNode("node", {"attr": TextRegion("/b /a /a[0]", 5, 3)}, "a.xml", 0, 1)
        self.assertEqual(
            _search_property_occurrences(tree, None, [node]),
            {
                "a.xml": [
                    TextRegion("/b", 5, 3),
                    TextRegion("/a", 8, 3),
                    TextRegion("/a[0]", 11, 3),
                ]
            },
        )

    def test_multiple_files_and_trees_with_the_same_filepath(self) -> None:
        later = XMLNode(
            "later", {"a": TextRegion("/fdm/engine/rpm", 0, 9)}, "a.xml", 0, 9
        )
        other = XMLNode(
            "other", {"a": TextRegion("/fdm/engine/rpm", 1, 3)}, "b.xml", 0, 3
        )
        earlier = XMLNode(
            "earlier", {"a": TextRegion("/fdm/engine/rpm", 2, 1)}, "a.xml", 0, 1
        )
        self.assertEqual(
            _search_property_occurrences(self.tree, None, [later, other, earlier]),
            {
                "a.xml": [
                    TextRegion("/fdm/engine/rpm", 2, 1),
                    TextRegion("/fdm/engine/rpm", 0, 9),
                ],
                "b.xml": [TextRegion("/fdm/engine/rpm", 1, 3)],
            },
        )

    def test_search_parsed_xml_attribute_and_element_text(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "model.xml"
            path.write_text(
                '<root attr="prefix /fdm/engine/rpm">\n'
                "  <property>\n"
                "    /fdm/engine[0]/rpm\n"
                "  </property>\n"
                "</root>\n",
                encoding="utf-8",
            )
            root = XMLNodeBuilder("model.xml", str(path)).root
            self.assertIsNotNone(root)
            assert root is not None
            self.assertEqual(
                _search_property_occurrences(self.tree, None, [root]),
                {
                    "model.xml": [
                        TextRegion("/fdm/engine/rpm", 19, 1),
                        TextRegion("/fdm/engine[0]/rpm", 4, 3),
                    ]
                },
            )


class TestNormalizeAttributeNames(unittest.TestCase):
    def make_node(
        self, name: str, attrs: Dict[str, str], parent: Optional[XMLNode] = None
    ) -> XMLNode:
        node = XMLNode(
            name,
            {key: TextRegion(value, column=4, line=7) for key, value in attrs.items()},
            "model.xml",
            0,
            1,
        )
        node.parent = parent
        return node

    def test_function_and_non_internal_table_names_replace_spaces(self) -> None:
        function = self.make_node("function", {"name": "gear position"})
        external_table = self.make_node(
            "table", {"name": "engine thrust", "type": "external"}
        )
        default_table = self.make_node("table", {"name": "engine thrust"})

        normalized = _normalize_attribute_names(
            [function, external_table, default_table]
        )

        for node, expected in zip(
            normalized, ("gear-position", "engine-thrust", "engine-thrust")
        ):
            region = node.attrs["name"]
            self.assertIsInstance(region, TextSubstitutionRegion)
            self.assertEqual(region.text, expected.replace("-", " "))
            self.assertEqual(region.substitute_text, expected)

    def test_function_renames_names_on_all_descendants(self) -> None:
        function = self.make_node("function", {"name": "gear function"})
        child = self.make_node("product", {"name": "gear position"}, function)
        nested_child = self.make_node("property", {"name": "engine speed"}, child)
        unnamed_child = self.make_node("value", {}, child)

        normalized = _normalize_attribute_names([function])[0]
        normalized_child = normalized.children[0]
        normalized_nested_child = normalized_child.children[0]
        normalized_unnamed_child = normalized_child.children[1]

        self.assertEqual(normalized.attrs["name"].substitute_text, "gear-function")
        self.assertEqual(
            normalized_child.attrs["name"].substitute_text, "gear-position"
        )
        self.assertEqual(
            normalized_nested_child.attrs["name"].substitute_text, "engine-speed"
        )
        self.assertNotIn("name", normalized_unnamed_child.attrs)
        self.assertEqual(function.attrs["name"].text, "gear function")
        self.assertEqual(child.attrs["name"].text, "gear position")
        self.assertEqual(nested_child.attrs["name"].text, "engine speed")
        self.assertEqual(unnamed_child.attrs, {})

    def test_function_renames_empty_name_attributes_on_descendants(self) -> None:
        function = self.make_node("function", {"name": "some function"})
        child = self.make_node("property", {"name": ""}, function)

        normalized = _normalize_attribute_names([function])[0]
        child_name = normalized.children[0].attrs["name"]

        self.assertIsInstance(child_name, TextSubstitutionRegion)
        self.assertEqual(child_name.text, "")
        self.assertEqual(child_name.substitute_text, "")

    def test_function_descendant_rename_precedes_channel_context(self) -> None:
        function = self.make_node("function", {"name": "some function"})
        channel = self.make_node("channel", {}, function)
        child = self.make_node("property", {"name": "Gear Up"}, channel)

        normalized = _normalize_attribute_names([function])[0]
        normalized_child = normalized.children[0].children[0]

        self.assertEqual(normalized_child.attrs["name"].substitute_text, "Gear-Up")

    def test_function_descendants_are_renamed_when_function_has_no_name(self) -> None:
        function = self.make_node("function", {})
        child = self.make_node("property", {"name": "gear position"}, function)

        normalized = _normalize_attribute_names([function])[0]

        self.assertNotIn("name", normalized.attrs)
        self.assertEqual(
            normalized.children[0].attrs["name"].substitute_text, "gear-position"
        )

    def test_internal_table_name_is_not_normalized(self) -> None:
        table = self.make_node("table", {"name": "engine thrust", "type": "internal"})

        normalized = _normalize_attribute_names([table])[0]

        self.assertNotIsInstance(normalized.attrs["name"], TextSubstitutionRegion)
        self.assertEqual(normalized.attrs["name"].text, "engine thrust")

    def test_channel_child_name_gets_fcs_prefix_and_lowercase(self) -> None:
        channel = self.make_node("channel", {})
        child = self.make_node("summer", {"name": "Gear Up"}, channel)

        (normalized_channel,) = _normalize_attribute_names([channel])
        normalized_child = normalized_channel.children[0]
        region = normalized_child.attrs["name"]

        self.assertIsInstance(region, TextSubstitutionRegion)
        self.assertEqual(region.text, "Gear Up")
        self.assertEqual(region.substitute_text, "fcs/gear-up")
        self.assertIs(normalized_child.parent, normalized_channel)

    def test_channel_child_name_with_path_is_not_rewritten(self) -> None:
        channel = self.make_node("channel", {})
        child = self.make_node("summer", {"name": "custom/Gear Up"}, channel)

        normalized = _normalize_attribute_names([channel])[0]
        region = normalized.children[0].attrs["name"]

        self.assertNotIsInstance(region, TextSubstitutionRegion)
        self.assertEqual(region.text, "custom/Gear Up")

    def test_name_is_only_normalized_in_supported_contexts(self) -> None:
        node = self.make_node("input", {"name": "Gear Up"})

        normalized = _normalize_attribute_names([node])[0]

        self.assertNotIsInstance(normalized.attrs["name"], TextSubstitutionRegion)
        self.assertEqual(normalized.attrs["name"].text, "Gear Up")

    def test_function_context_takes_precedence_over_channel_context(self) -> None:
        channel = self.make_node("channel", {})
        function = self.make_node("function", {"name": "Gear Up"}, channel)

        normalized = _normalize_attribute_names([channel])[0]
        region = normalized.children[0].attrs["name"]

        self.assertEqual(region.substitute_text, "Gear-Up")

    def test_normalization_does_not_mutate_original_xml_tree(self) -> None:
        channel = self.make_node("channel", {})
        child = self.make_node("summer", {"name": "Gear Up"}, channel)

        normalized = _normalize_attribute_names([channel])

        self.assertEqual(channel.children, [child])
        self.assertEqual(child.attrs["name"].text, "Gear Up")
        self.assertEqual(
            normalized[0].children[0].attrs["name"].substitute_text,
            "fcs/gear-up",
        )

    def test_search_reports_original_channel_name_and_source_position(self) -> None:
        channel = self.make_node("channel", {})
        channel.attrs.clear()
        child = self.make_node("summer", {"name": "Gear Up"}, channel)
        child.attrs["name"].column = 12
        child.attrs["name"].line = 9
        property_tree = PropertyTreeNode("")
        root = PropertyTreeNode("")
        root.add("/fcs/gear-up")

        occurrences = _search_property_occurrences(
            property_tree, root, _normalize_attribute_names([channel])
        )

        self.assertEqual(
            occurrences,
            {"model.xml": [TextRegion("Gear Up", column=12, line=9)]},
        )

    def test_empty_channel_child_name_is_not_given_synthetic_path(self) -> None:
        channel = self.make_node("channel", {})
        self.make_node("summer", {"name": ""}, channel)

        normalized = _normalize_attribute_names([channel])[0]

        self.assertNotIsInstance(
            normalized.children[0].attrs["name"], TextSubstitutionRegion
        )
        self.assertEqual(normalized.children[0].attrs["name"].text, "")


if __name__ == "__main__":
    unittest.main()
