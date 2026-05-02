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

from jsbsim_gui.controller import XMLNode


def make_node(name: str = "node") -> XMLNode:
    return XMLNode(name, {"attr": "val"}, "some/path.xml", 5, 10)


class TestXMLNodeInit(unittest.TestCase):
    def test_attributes_are_stored(self):
        node = XMLNode("tag", {"k": "v"}, "dir/file.xml", 3, 7)
        self.assertEqual(node.name, "tag")
        self.assertEqual(node.attrs, {"k": "v"})
        self.assertEqual(node.filepath, "dir/file.xml")
        self.assertEqual(node.column, 3)
        self.assertEqual(node.line, 7)

    def test_parent_is_none(self):
        node = make_node()
        self.assertIsNone(node.parent)

    def test_children_is_empty(self):
        node = make_node()
        self.assertEqual(node.children, [])

    def test_empty_attrs(self):
        node = XMLNode("tag", {}, "f.xml", 0, 1)
        self.assertEqual(node.attrs, {})


class TestXMLNodeParentSetter(unittest.TestCase):
    def test_set_parent_adds_self_to_parent_children(self):
        parent = make_node("parent")
        child = make_node("child")
        child.parent = parent
        self.assertIn(child, parent.children)
        self.assertIs(child.parent, parent)

    def test_set_parent_to_none_when_no_parent(self):
        node = make_node()
        node.parent = None
        self.assertIsNone(node.parent)

    def test_set_parent_to_none_removes_from_old_parent(self):
        parent = make_node("parent")
        child = make_node("child")
        child.parent = parent
        child.parent = None
        self.assertNotIn(child, parent.children)
        self.assertIsNone(child.parent)

    def test_reparent_removes_from_old_and_adds_to_new(self):
        parent1 = make_node("p1")
        parent2 = make_node("p2")
        child = make_node("child")
        child.parent = parent1
        child.parent = parent2
        self.assertNotIn(child, parent1.children)
        self.assertIn(child, parent2.children)
        self.assertIs(child.parent, parent2)

    def test_set_same_parent_keeps_child_in_parent(self):
        parent = make_node("parent")
        child = make_node("child")
        child.parent = parent
        child.parent = parent
        self.assertIn(child, parent.children)
        self.assertEqual(parent.children.count(child), 1)

    def test_multiple_children_order_is_preserved(self):
        parent = make_node("parent")
        child1 = make_node("c1")
        child2 = make_node("c2")
        child3 = make_node("c3")
        child1.parent = parent
        child2.parent = parent
        child3.parent = parent
        self.assertEqual(parent.children, [child1, child2, child3])

    def test_parent_getter_returns_none_by_default(self):
        node = make_node()
        self.assertIsNone(node.parent)

    def test_parent_getter_returns_set_parent(self):
        parent = make_node("parent")
        child = make_node("child")
        child.parent = parent
        self.assertIs(child.parent, parent)


class TestXMLNodePath(unittest.TestCase):
    def test_root_node_path_is_its_name(self):
        root = make_node("fdm_config")
        self.assertEqual(root.path, "fdm_config")

    def test_one_level_deep(self):
        root = make_node("root")
        child = make_node("child")
        child.parent = root
        self.assertEqual(child.path, "root/child")

    def test_two_levels_deep(self):
        root = make_node("root")
        middle = make_node("middle")
        leaf = make_node("leaf")
        middle.parent = root
        leaf.parent = middle
        self.assertEqual(leaf.path, "root/middle/leaf")

    def test_path_of_root_is_unaffected_by_children(self):
        root = make_node("root")
        child = make_node("child")
        child.parent = root
        self.assertEqual(root.path, "root")

    def test_path_updates_after_reparent(self):
        root1 = make_node("root1")
        root2 = make_node("root2")
        child = make_node("child")
        child.parent = root1
        self.assertEqual(child.path, "root1/child")
        child.parent = root2
        self.assertEqual(child.path, "root2/child")

    def test_path_updates_after_detach(self):
        root = make_node("root")
        child = make_node("child")
        child.parent = root
        child.parent = None
        self.assertEqual(child.path, "child")


class TestXMLNodeIter(unittest.TestCase):
    def test_iter_resets_children_it(self):
        parent = make_node("parent")
        child = make_node("child")
        child.parent = parent
        it = iter(parent)
        next(it)  # consume parent itself
        next(it)  # consume child
        # second iteration should start fresh
        result = list(iter(parent))
        self.assertEqual(result, [parent, child])


class TestXMLNodeIteration(unittest.TestCase):
    def test_leaf_node_yields_itself_only(self):
        leaf = make_node("leaf")
        self.assertEqual(list(iter(leaf)), [leaf])

    def test_root_with_one_child(self):
        root = make_node("root")
        child = make_node("child")
        child.parent = root
        self.assertEqual(list(iter(root)), [root, child])

    def test_root_with_two_children(self):
        root = make_node("root")
        child1 = make_node("c1")
        child2 = make_node("c2")
        child1.parent = root
        child2.parent = root
        self.assertEqual(list(iter(root)), [root, child1, child2])

    def test_root_with_three_children(self):
        root = make_node("root")
        child1 = make_node("c1")
        child2 = make_node("c2")
        child3 = make_node("c3")
        child1.parent = root
        child2.parent = root
        child3.parent = root
        self.assertEqual(list(iter(root)), [root, child1, child2, child3])

    def test_two_levels_deep(self):
        root = make_node("root")
        child = make_node("child")
        grandchild = make_node("grandchild")
        child.parent = root
        grandchild.parent = child
        self.assertEqual(list(iter(root)), [root, child, grandchild])

    def test_depth_first_pre_order(self):
        # root → [left → [left_leaf], right]
        root = make_node("root")
        left = make_node("left")
        left_leaf = make_node("left_leaf")
        right = make_node("right")
        left.parent = root
        right.parent = root
        left_leaf.parent = left
        self.assertEqual(list(iter(root)), [root, left, left_leaf, right])

    def test_wide_and_deep_tree(self):
        # root → [a → [a1, a2], b → [b1]]
        root = make_node("root")
        a = make_node("a")
        a1 = make_node("a1")
        a2 = make_node("a2")
        b = make_node("b")
        b1 = make_node("b1")
        a.parent = root
        b.parent = root
        a1.parent = a
        a2.parent = a
        b1.parent = b
        self.assertEqual(list(iter(root)), [root, a, a1, a2, b, b1])

    def test_iterating_child_directly_yields_subtree(self):
        root = make_node("root")
        child = make_node("child")
        grandchild = make_node("grandchild")
        child.parent = root
        grandchild.parent = child
        self.assertEqual(list(iter(child)), [child, grandchild])

    def test_iteration_is_repeatable(self):
        root = make_node("root")
        child1 = make_node("c1")
        child2 = make_node("c2")
        child1.parent = root
        child2.parent = root
        first = list(iter(root))
        second = list(iter(root))
        self.assertEqual(first, second)

    def test_iteration_count_matches_tree_size(self):
        root = make_node("root")
        nodes = [make_node(f"n{i}") for i in range(5)]
        for n in nodes:
            n.parent = root
        self.assertEqual(len(list(iter(root))), 6)  # root + 5 children


if __name__ == "__main__":
    unittest.main()
