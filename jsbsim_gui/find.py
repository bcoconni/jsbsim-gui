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

import re
import tkinter as tk
from tkinter import ttk
from tkinter.constants import BROWSE, EW, NSEW
from typing import Callable, Dict, List, Optional, Tuple, Union

from .controller import Controller, XMLNode
from .file_state import FileState
from .hierarchical_tree import HierarchicalTree, SearchableTree
from .textview import XMLSourceCodeView


class XMLTree(SearchableTree):
    def __init__(
        self,
        master: tk.Widget,
        xml_trees: List[XMLNode],
        file_states: Dict[str, FileState],
        move_cursor: Callable[[FileState, int, int], None],
    ):
        super().__init__(master, lambda parent: HierarchicalTree(parent, [], [], False))
        self._file_states = file_states
        self._move_cursor = move_cursor
        self.nodes: Dict[str, XMLNode] = {}
        tree = self.tree
        tree.configure_tree(show="tree", selectmode=BROWSE)

        for xml_tree in xml_trees:
            node_ids = {}
            for node in xml_tree:
                if node.parent:
                    parent_id = node_ids[node.parent]
                else:
                    parent_id = ""

                node_id = tree.insert(parent_id, tk.END, text=node.name, open=False)
                self.nodes[node_id] = node
                node_ids[node] = node_id

        tree.bind("<<TreeviewSelect>>", self._on_xml_selected)

    def _on_xml_selected(self, _: tk.Event) -> None:
        node = self.nodes[self.tree.selection()[0]]
        file_state = self._file_states.get(node.filepath)
        if file_state is not None:
            self._move_cursor(file_state, node.column, node.line)


def search_property_occurrences(
    property_variants: List[str], file_states: List[FileState]
) -> Dict[FileState, List[Tuple[int, int, str]]]:
    results: Dict[FileState, List[Tuple[int, int, str]]] = {}

    dummy_frame = tk.Frame()
    dummy_editor = XMLSourceCodeView(dummy_frame)

    for file_state in file_states:
        file_occurrences = []

        dummy_editor.new_content(file_state.content)
        data_regions = dummy_editor.extract_tagged_regions("XML_data")
        attr_regions = dummy_editor.extract_tagged_regions("XML_attr_value")
        attr_regions = [
            (line, col + 1, text.strip('"')) for line, col, text in attr_regions
        ]

        all_regions = data_regions + attr_regions

        for variant in property_variants:
            # Build pattern that allows optional [0] indices in property names
            pattern_parts = []
            for part in variant.split("/"):
                escaped_part = re.escape(part)
                # If part is empty (from leading slash in absolute paths) or has a
                # non-zero index, match it exactly.
                # Otherwise allow optional [0] after the part.
                if not part or "[" in part:
                    pattern_parts.append(escaped_part)
                else:
                    pattern_parts.append(escaped_part + r"(?:\[0\])?")

            pattern = r"(?:^|[\s/])(" + "/".join(pattern_parts) + r")(?:$|[\s/\[])"

            for line, column, text in all_regions:
                property_match = re.search(pattern, text)
                if property_match:
                    property_column = property_match.start(1)
                    property_line = line
                    for l in text.split("\n"):
                        length = len(l)
                        if length < property_column:
                            property_column -= length + 1  # Including '\n
                            property_line += 1
                        else:
                            break
                    if property_line == line:
                        property_column += column
                    file_occurrences.append((property_line, property_column, variant))

        if file_occurrences:
            results[file_state] = sorted(file_occurrences)

    dummy_frame.destroy()
    return results


class PropertyOccurrencesTree(SearchableTree):
    def __init__(
        self,
        master: tk.Widget,
        controller: Controller,
        file_states: Dict[str, FileState],
        select_text: Callable[[str, FileState, int, int], None],
    ):
        super().__init__(
            master, lambda parent: HierarchicalTree(parent, [], ["content"], True)
        )
        self._occurrence_data: Dict[str, Tuple[FileState, int, int, str]] = {}
        self._controller = controller
        self._file_states = file_states
        self._select_text = select_text
        self._entries: List[str] = []
        self._num_entries = 0
        self._selected_entry = -1
        self.tree.configure_tree(show="tree headings", selectmode=BROWSE)
        self.tree.heading("#0", text="Location")
        self.tree.heading("content", text="Content")
        self.tree.grid(column=0, row=1, sticky=NSEW)
        self.tree.bind("<<TreeviewSelect>>", self._on_entry_selected)

        buttons_frame = ttk.Frame(self, padding=(0, 2))
        ttk.Button(buttons_frame, text="Previous", command=self._prev_entry).grid(
            column=0, row=0, padx=1
        )
        ttk.Button(buttons_frame, text="Next", command=self._next_entry).grid(
            column=1, row=0, padx=1
        )
        buttons_frame.grid(column=0, row=2)

    def set_occurrences(
        self, occurrences: Dict[FileState, List[Tuple[int, int, str]]]
    ) -> None:
        self._occurrence_data = {}
        self.tree.clear()

        input_files: List[str] = []
        for file_state in occurrences.keys():
            if file_state.filepath not in input_files:
                input_files.append(file_state.filepath)

        self.tree.create_tree_nodes(input_files)

        for file_state, file_occurrences in occurrences.items():
            file_id = self.tree.get_id_from_path(file_state.filepath)
            if file_id is None:
                continue

            lines = file_state.content.split("\n")

            for line, column, prop_name in file_occurrences:
                occurrence_id = self.tree.insert(
                    file_id,
                    tk.END,
                    text=f"line {line}",
                    values=(lines[line - 1].strip(),),
                )
                self._occurrence_data[occurrence_id] = (
                    file_state,
                    column,
                    line,
                    prop_name,
                )

    def search(self, _: tk.Event) -> None:
        property_path = self.search_box.get().strip()
        if not property_path or len(property_path) < 2:
            self.set_occurrences({})
            return

        variants = self._expand_property_with_children(property_path)
        occurrences: Dict[FileState, List[Tuple[int, int, str]]] = {}
        if variants:
            occurrences = search_property_occurrences(
                variants, list(self._file_states.values())
            )

        self.set_occurrences(occurrences)
        self._entries = sorted(self._occurrence_data.keys())
        self._num_entries = len(self._entries)
        self._selected_entry = -1

    def _expand_property_with_children(self, property_path: str) -> List[str]:
        property_root = self._controller.get_property_root()
        if not property_root:
            return []

        root_name = property_root.get_fully_qualified_name()
        search_path = property_path.replace("[0]", "")
        properties = self._controller.get_property_list()
        variants = set()

        for prop in properties:
            full_path = prop.get_fully_qualified_name()
            normalized_path = full_path.replace("[0]", "")

            if search_path in normalized_path:
                variants.add(normalized_path)
                # Also add the relative path
                if normalized_path.startswith(root_name + "/"):
                    variants.add(normalized_path[len(root_name) + 1 :])

        return list(variants)

    def _on_entry_selected(self, _event: Optional[tk.Event]) -> None:
        selection = self.tree.selection()
        if selection and selection[0] in self._occurrence_data:
            file_state, column, line, prop_name = self._occurrence_data[selection[0]]
            self._select_text(prop_name, file_state, column, line)

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
        master: Union[tk.Tk, tk.Toplevel],
        controller: Controller,
        file_states: Dict[str, FileState],
        select_text: Callable[[str, FileState, int, int], None],
        move_cursor: Callable[[FileState, int, int], None],
    ):
        super().__init__(master)
        self.title("Find")
        self.transient(master)

        # Search mode selector
        mode_frame = ttk.Frame(self)
        mode_frame.grid(column=0, row=0, sticky=EW, padx=5, pady=5)
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
            mode_frame, controller, file_states, select_text
        )
        self._occurrences_tree.grid(column=0, row=1, columnspan=2, sticky=NSEW)
        self._xml_tree.tkraise()

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

    def _on_mode_change(self, _: tk.Event) -> None:
        mode = self._type_combo.get()
        if mode == "XML":
            self._xml_tree.tkraise()
        else:
            self._occurrences_tree.tkraise()
