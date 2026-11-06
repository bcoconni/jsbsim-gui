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

import copy
import re
import tkinter as tk
from dataclasses import asdict
from itertools import chain
from pathlib import Path
from tkinter import ttk
from tkinter.constants import BROWSE, EW, NSEW
from typing import Callable

from .controller import Controller
from .file_state import FileState
from .hierarchical_tree import HierarchicalTree, SearchableTree
from .tree_node import TextRegion, TreeNode, TreeNodeConditionalIterator, XMLNode


class XMLTree(SearchableTree):
    def __init__(
        self,
        master: tk.Widget,
        xml_trees: list[XMLNode],
        file_states: dict[Path, FileState],
        move_cursor: Callable[[FileState, int, int], None],
    ):
        super().__init__(master, lambda parent: HierarchicalTree(parent, [], [], False))
        self._file_states = file_states
        self._move_cursor = move_cursor
        self.nodes: dict[str, XMLNode] = {}
        tree = self.tree
        tree.configure_tree(show="tree", selectmode=BROWSE)

        for xml_tree in xml_trees:
            node_ids = {}
            for node in xml_tree:
                if node.parent:
                    parent_id = node_ids[node.parent]
                else:
                    parent_id = ""

                node_id = tree.insert(parent_id, tk.END, text=f"{node}", open=False)
                self.nodes[node_id] = node
                node_ids[node] = node_id

        tree.bind("<<TreeviewSelect>>", self._on_xml_selected)

    def _on_xml_selected(self, _: tk.Event) -> None:
        node = self.nodes[self.tree.selection()[0]]
        file_state = self._file_states.get(node.filepath)
        if file_state is not None:
            self._move_cursor(file_state, node.column, node.line)


class PropertyTreeNode(TreeNode):
    def __init__(self, node_name: str):
        names = node_name.split("/", maxsplit=1)
        super().__init__(names[0])
        if len(names) == 2:
            child = PropertyTreeNode(names[1])
            child.parent = self

    def add(self, node_name: str) -> None:
        names = node_name.split("/", maxsplit=1)
        child_names = names[1].split("/", maxsplit=1)
        for child in self.children:
            assert isinstance(child, PropertyTreeNode)
            if child.name == child_names[0]:
                if len(child_names) == 2:
                    child.add(names[1])
                return
        child = PropertyTreeNode(names[1])
        child.parent = self

    def find(self, node_name: str) -> TreeNode | None:
        names = node_name.split("/", maxsplit=1)
        child_names = names[1].split("/", maxsplit=1)
        for child in self.children:
            assert isinstance(child, PropertyTreeNode)
            if child.name == child_names[0]:
                if len(child_names) == 2:
                    return child.find(names[1])
                return child
        return None


def _node_in_text(
    tree: TreeNode,
    text: str,
    relative_path: bool,
    match_start: int = -1,
    match_end: int = -1,
) -> tuple[int, int] | None:
    earliest: tuple[int, int] | None = None
    for child in tree.children:
        name = child.name if relative_path else "/" + child.name
        index_start = name.find("[")

        if index_start >= 0:
            base_name = name[:index_start]
            index = name[index_start:]
        else:
            base_name = name
            index = None

        if match_end == -1:
            column = text.find(base_name)
        else:
            column = match_end if text.startswith(base_name, match_end) else -1

        while column >= 0:
            end_column = column + len(base_name)
            valid_index = True

            if text.startswith("[#]", end_column):
                end_column += 3
            elif index is None:
                if text.startswith("[0]", end_column):
                    end_column += 3
                else:
                    valid_index = not text.startswith("[", end_column)
            elif text.startswith(index, end_column):
                end_column += len(index)
            else:
                valid_index = False

            if valid_index:
                start_column = column if match_start == -1 else match_start
                if child.children:
                    position = _node_in_text(
                        child, text, False, start_column, end_column
                    )
                else:
                    position = (start_column, end_column)
                if position is not None:
                    if earliest is None or position[0] < earliest[0]:
                        earliest = position
                    break

            if match_end != -1:
                break

            column = text.find(base_name, column + 1)

    return earliest


def _nodes_in_text(
    tree: TreeNode, text: str, relative_path: bool
) -> list[tuple[int, int]]:
    matching_positions: list[tuple[int, int]] = []
    position = _node_in_text(tree, text, relative_path)
    while position:
        matching_positions.append(position)
        end = position[1]
        if len(text) > end:
            position = _node_in_text(tree, text[end:], relative_path)
            if position is not None:
                next_start, next_end = position
                position = next_start + end, next_end + end
        else:
            position = None

    return matching_positions


def _search_node_occurrences(
    tree: TreeNode, sub_tree: TreeNode | None, xml_trees: list[XMLNode]
) -> dict[Path, list[TextRegion]]:
    occurrences: dict[Path, list[TextRegion]] = {}

    for xml_tree in xml_trees:
        for node in xml_tree:
            assert isinstance(node, XMLNode)
            for region in chain(node.attrs.values(), node.data):
                if isinstance(region, TextSubstitutionRegion):
                    text = region.substitute_text
                else:
                    text = region.text

                paths = _nodes_in_text(tree, text, False)
                if sub_tree is not None:
                    paths += _nodes_in_text(sub_tree, text, True)

                for column_start, column_end in paths:
                    property_name = region.text[column_start:column_end]
                    prefix = region.text[:column_start]
                    lines = prefix.split("\n")
                    property_line = region.line
                    if len(lines) == 1:
                        property_column = region.column + len(prefix)
                    else:
                        property_column = len(lines[-1])
                        property_line += len(lines) - 1

                    property_region = TextRegion(
                        property_name, property_column, property_line
                    )
                    if node.filepath in occurrences:
                        occurrences[node.filepath].append(property_region)
                    else:
                        occurrences[node.filepath] = [property_region]

    return {
        file_path: sorted(regions, key=lambda r: r.line)
        for file_path, regions in occurrences.items()
    }


class TextSubstitutionRegion(TextRegion):
    substitute_text: str = ""


def _compute_substitute_text(
    region: TextRegion, compute: Callable[[str], str]
) -> TextSubstitutionRegion:
    alt_region = TextSubstitutionRegion(**asdict(region))
    alt_region.substitute_text = compute(region.text)
    return alt_region


_ENGINE_SPECIAL_FUNCTION_NAMES = (
    ("turboprop_engine", "EnginePowerVC"),
    ("turbine_engine", "IdleThrust"),
    ("turbine_engine", "MilThrust"),
    ("turbine_engine", "AugThrust"),
    ("turbine_engine", "Injection"),
    ("turbine_engine", "N1SpoolUp"),
    ("turbine_engine", "N1SpoolDown"),
    ("turbine_engine", "N2SpoolUp"),
    ("turbine_engine", "N2SpoolDown"),
)


def _normalize_attribute_names(xml_trees: list[XMLNode]) -> list[XMLNode]:
    trees = copy.deepcopy(xml_trees)
    for tree in trees:
        tree_traversal = TreeNodeConditionalIterator(tree)
        for node in tree_traversal:
            assert isinstance(node, XMLNode)
            attr_name = node.attrs.get("name")
            rename: Callable[[str], str] | None = None
            p = node.parent

            if node.name == "function":
                rename = lambda s: s.replace(" ", "-")

                for child_tree in node.children:
                    assert isinstance(child_tree, XMLNode)
                    for child_node in child_tree:
                        child_name_attr = child_node.attrs.get("name")
                        if child_name_attr:
                            child_node.attrs["name"] = _compute_substitute_text(
                                child_name_attr, rename
                            )

                if p and attr_name:
                    function_name = attr_name.text
                    if (p.name, function_name) in _ENGINE_SPECIAL_FUNCTION_NAMES:
                        rename = lambda s: "propulsion/engine[#]/" + s
            else:
                if attr_name is None:
                    continue

                name = attr_name.text

                if node.name == "table":
                    table_type = node.attrs.get("type")
                    if p and p.name == "turboprop_engine" and name == "EnginePowerVC":
                        rename = lambda s: "propulsion/engine[#]/" + s
                    elif table_type is None or table_type.text != "internal":
                        rename = lambda s: s.replace(" ", "-")
                else:  # FGFCSComponents
                    if p and name and p.name == "channel" and name.find("/") == -1:
                        rename = lambda s: "fcs/" + s.replace(" ", "-").lower()

            if rename is not None:
                if attr_name is not None:
                    node.attrs["name"] = _compute_substitute_text(attr_name, rename)
                tree_traversal.skip_current_node_children()

    return trees


class PropertyOccurrencesTree(SearchableTree):
    def __init__(
        self,
        master: tk.Widget,
        controller: Controller,
        xml_trees: list[XMLNode],
        file_states: dict[Path, FileState],
        select_text: Callable[[str, FileState, int, int], None],
    ):
        super().__init__(
            master, lambda parent: HierarchicalTree(parent, [], ["content"], True)
        )
        self._occurrence_data: dict[str, tuple[FileState, TextRegion]] = {}
        self._controller = controller
        self._file_states = file_states
        self._xml_trees = _normalize_attribute_names(xml_trees)
        self._select_text = select_text
        self._entries: list[str] = []
        self._num_entries = 0
        self._selected_entry = -1
        self.tree.configure_tree(show="tree headings", selectmode=BROWSE)
        self.tree.heading("#0", text="Location")
        self.tree.heading("content", text="Content")
        self.tree.grid(column=0, row=1, sticky=NSEW)
        self.tree.bind("<<TreeviewSelect>>", self._on_entry_selected)

        self._label = ttk.Label(self)
        self._label.grid(column=0, row=2, sticky=tk.W)
        buttons_frame = ttk.Frame(self, padding=(0, 2))
        ttk.Button(buttons_frame, text="Previous", command=self._prev_entry).grid(
            column=0, row=0, padx=1
        )
        ttk.Button(buttons_frame, text="Next", command=self._next_entry).grid(
            column=1, row=0, padx=1
        )
        buttons_frame.grid(column=0, row=3)

    def set_occurrences(self, occurrences: dict[Path, list[TextRegion]]) -> None:
        self._occurrence_data = {}
        self.tree.clear()

        input_files: list[str] = []
        for file_path in occurrences.keys():
            if file_path not in input_files:
                input_files.append(str(file_path))

        self.tree.create_tree_nodes(input_files)

        for file_path, node_occurrences in occurrences.items():
            file_id = self.tree.get_id_from_path(str(file_path))
            if file_id is None:
                continue

            file_state = self._file_states[file_path]
            lines = file_state.content.split("\n")

            for occurence in node_occurrences:
                occurrence_id = self.tree.insert(
                    file_id,
                    tk.END,
                    text=f"line {occurence.line}",
                    values=(lines[occurence.line - 1].strip(),),
                )
                self._occurrence_data[occurrence_id] = (file_state, occurence)

    def _search(self) -> None:
        property_path = self.get_search_text()
        if not property_path or len(property_path) < 2:
            self.set_occurrences({})
            return

        property_tree, root = self._find_matching_properties(property_path)
        occurrences: dict[Path, list[TextRegion]] = {}
        if property_tree.children:
            occurrences = _search_node_occurrences(property_tree, root, self._xml_trees)

        self.set_occurrences(occurrences)
        self._entries = sorted(self._occurrence_data.keys())
        self._num_entries = len(self._entries)
        self._label.configure(text=f"{self._num_entries} occurence(s)")
        self._selected_entry = -1

    def _find_matching_properties(
        self, property_path: str
    ) -> tuple[TreeNode, TreeNode | None]:

        search_pattern: list[str] = []
        for item in property_path.split("/"):
            if item.endswith("[0]"):
                search_pattern.append(re.escape(item[:-3]))
            elif item.endswith("[#]"):
                search_pattern.append(re.escape(item[:-3]) + r"(\[[0-9]+\])?(?=/|$)")
            else:
                search_pattern.append(re.escape(item))

        search_path = re.compile(r"/".join(search_pattern))
        property_tree = PropertyTreeNode("")

        for prop in self._controller.get_property_list():
            full_path = prop.get_fully_qualified_name()
            normalized_path = full_path.replace("[0]", "")

            if search_path.search(normalized_path):
                property_tree.add(normalized_path)

        property_root = self._controller.get_property_root()
        if property_root is None:
            return (property_tree, None)

        root_name = property_root.get_fully_qualified_name()
        relative_property_tree = property_tree.find(root_name)
        return property_tree, relative_property_tree

    def _on_entry_selected(self, _event: tk.Event | None) -> None:
        selection = self.tree.selection()
        if selection and selection[0] in self._occurrence_data:
            self._selected_entry = self._entries.index(selection[0])
            file_state, region = self._occurrence_data[selection[0]]
            self._select_text(region.text, file_state, region.column, region.line)

    def _cycle_entries(self):
        if self._num_entries == 0:
            return
        if self._selected_entry < 0:
            self._selected_entry = self._num_entries - 1
        elif self._selected_entry >= self._num_entries:
            self._selected_entry = 0

        entry = self._entries[self._selected_entry]
        self.tree.selection_set([entry])
        self.tree.see(entry)
        self._on_entry_selected(None)

    def _next_entry(self):
        self._selected_entry += 1
        self._cycle_entries()

    def _prev_entry(self):
        self._selected_entry -= 1
        self._cycle_entries()


class FindWindow(tk.Toplevel):
    def __init__(
        self,
        master: tk.Tk | tk.Toplevel,
        controller: Controller,
        file_states: dict[Path, FileState],
        select_text: Callable[[str, FileState, int, int], None],
        move_cursor: Callable[[FileState, int, int], None],
    ):
        super().__init__(master)
        self.title("Find")
        self.transient(master)

        # Search mode selector
        mode_frame = ttk.Frame(self)
        mode_frame.grid(column=0, row=0, sticky=NSEW, padx=5, pady=5)
        ttk.Label(mode_frame, text="Type:").grid(column=0, row=0, padx=10, sticky=tk.W)
        self._type_combo = ttk.Combobox(
            mode_frame,
            values=["XML", "Property"],
            state="readonly",
            width=12,
        )
        self._type_combo.current(0)
        self._type_combo.grid(column=1, row=0, sticky=EW)
        self._type_combo.bind("<<ComboboxSelected>>", self._on_mode_change)

        # XML panel
        xml_trees = controller.get_xml_trees()
        self._xml_tree = XMLTree(mode_frame, xml_trees, file_states, move_cursor)
        self._xml_tree.grid(column=0, row=1, columnspan=2, sticky=NSEW)

        # Property panel
        self._occurrences_tree = PropertyOccurrencesTree(
            mode_frame, controller, xml_trees, file_states, select_text
        )
        self._occurrences_tree.grid(column=0, row=1, columnspan=2, sticky=NSEW)
        self._xml_tree.tkraise()
        self._xml_tree.focus_search()

        mode_frame.grid_columnconfigure(1, weight=1)
        mode_frame.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

    def find_property(self, property_name: str) -> None:
        self._type_combo.current(1)
        self._occurrences_tree.tkraise()
        self._occurrences_tree.set_search_text(property_name)
        self._occurrences_tree.focus_search()

    def _on_mode_change(self, _: tk.Event) -> None:
        mode = self._type_combo.get()
        if mode == "XML":
            self._xml_tree.tkraise()
            self._xml_tree.focus_search()
        else:
            self._occurrences_tree.tkraise()
            self._occurrences_tree.focus_search()
