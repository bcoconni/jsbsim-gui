# A Graphical User Interface for JSBSim
#
# Copyright (c) 2026 Bertrand Coconnier
# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License, version 3 or later.

import unittest

from jsbsim_gui.hierarchical_tree import HierarchicalTree


class _TreeviewStub:
    def __init__(self, paths: tuple[str, ...]) -> None:
        self._nodes: dict[str, tuple[str, str]] = {}
        self._children: dict[str, list[str]] = {"": []}
        self.seen: list[str] = []

        for path in paths:
            parent_id = ""
            for name in path.strip("/").split("/"):
                node_id = f"{parent_id}/{name}"
                if node_id not in self._nodes:
                    self._nodes[node_id] = (name, parent_id)
                    self._children.setdefault(parent_id, []).append(node_id)
                    self._children[node_id] = []
                parent_id = node_id

    def get_children(self, parent_id: str = "") -> tuple[str, ...]:
        return tuple(self._children[parent_id])

    def item(self, node_id: str, option: str) -> str:
        if option == "text":
            return self._nodes[node_id][0]
        raise ValueError(f"Unsupported item option: {option}")

    def parent(self, node_id: str) -> str:
        return self._nodes[node_id][1]

    def index(self, node_id: str) -> int:
        return self._children[self.parent(node_id)].index(node_id)

    def see(self, node_id: str) -> None:
        self.seen.append(node_id)

    def detach(self, node_id: str) -> None:
        self._children[self.parent(node_id)].remove(node_id)

    def reattach(self, node_id: str, parent_id: str, index: int) -> None:
        self._children[parent_id].insert(index, node_id)

    def visible_paths(self) -> set[str]:
        paths: set[str] = set()

        def visit(parent_id: str) -> None:
            for node_id in self.get_children(parent_id):
                paths.add(node_id)
                visit(node_id)

        visit("")
        return paths


class TestHierarchicalTreeFilter(unittest.TestCase):
    def setUp(self) -> None:
        self.tree = HierarchicalTree.__new__(HierarchicalTree)
        self.tree._tree = _TreeviewStub(
            (
                "/aircraft/engines/engine0/rpm",
                "/aircraft/engines/engine0/rpm/peak",
                "/aircraft/engines/engine0/thrust",
                "/aircraft/engines/engine1/rpm",
                "/aircraft/engines/engine1/temperature",
                "/aircraft/controls/rpm_trim",
                "/properties/engine/rpm",
                "/properties/engine/torque",
                "/propeller/rpm",
                "/propeller/pitch",
                "/other/engine/temperature",
            )
        )
        self.tree._hidden_items = []

    def test_matches_text_at_any_level_then_child_name(self) -> None:
        self.assertTrue(self.tree.filter("eng/rpm"))
        self.assertEqual(
            self.tree._tree.visible_paths(),
            {
                "/aircraft",
                "/aircraft/engines",
                "/aircraft/engines/engine0",
                "/aircraft/engines/engine0/rpm",
                "/aircraft/engines/engine0/rpm/peak",
                "/aircraft/engines/engine1",
                "/aircraft/engines/engine1/rpm",
                "/properties",
                "/properties/engine",
                "/properties/engine/rpm",
            },
        )

    def test_empty_token_skips_one_hierarchy_level(self) -> None:
        self.assertTrue(self.tree.filter("prop//rpm"))
        self.assertEqual(
            self.tree._tree.visible_paths(),
            {"/properties", "/properties/engine", "/properties/engine/rpm"},
        )

    def test_multiple_empty_tokens_allow_arbitrary_depth(self) -> None:
        self.assertTrue(self.tree.filter("air///rpm"))
        self.assertEqual(
            self.tree._tree.visible_paths(),
            {
                "/aircraft",
                "/aircraft/engines",
                "/aircraft/engines/engine0",
                "/aircraft/engines/engine0/rpm",
                "/aircraft/engines/engine0/rpm/peak",
                "/aircraft/engines/engine1",
                "/aircraft/engines/engine1/rpm",
            },
        )

    def test_no_match_hides_tree_and_unfilter_restores_it(self) -> None:
        original_paths = self.tree._tree.visible_paths()

        self.assertFalse(self.tree.filter("missing/rpm"))
        self.assertEqual(self.tree._tree.visible_paths(), set())
        self.assertTrue(self.tree.unfilter())
        self.assertEqual(self.tree._tree.visible_paths(), original_paths)
        self.assertFalse(self.tree.unfilter())
