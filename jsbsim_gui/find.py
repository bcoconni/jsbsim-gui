# A Graphical User Interface for JSBSim
#
# Copyright (c) 2023-2026 Bertrand Coconnier
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
from typing import Callable, Dict, List, Literal, Optional, Tuple, Union

from .controller import Controller, XMLNode
from .file_state import FileState
from .hierarchical_tree import HierarchicalTree, SearchableTree, TextBox
from .textview import XMLSourceCodeView


class XMLTree(SearchableTree):
    def __init__(self, master: tk.Widget, xml_trees: List[XMLNode]):
        super().__init__(master, lambda parent: HierarchicalTree(parent, [], [], False))
        self.tree.tree.configure(show="tree", selectmode=BROWSE)
        self.xml_trees = xml_trees
        self.nodes: Dict[str, XMLNode] = {}
        tree = self.tree.tree

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

    def bind_selection(
        self,
        func: Callable[[str, int, int], None],
        add: Union[bool, Literal["", "+"], None] = None,
    ) -> None:
        def bind_func(_: tk.Event) -> None:
            node = self.nodes[self.tree.tree.selection()[0]]
            func(node.filepath, node.column, node.line)

        self.tree.bind("<<TreeviewSelect>>", bind_func, add)


def search_property_occurrences(
    property_variants: List[str], file_states: List[FileState]
) -> Dict[FileState, List[Tuple[int, int]]]:
    results: Dict[FileState, List[Tuple[int, int]]] = {}

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
                    file_occurrences.append((property_line, property_column))

        if file_occurrences:
            results[file_state] = sorted(file_occurrences)

    dummy_frame.destroy()
    return results


class PropertyOccurrencesTree(ttk.Frame):
    def __init__(self, master: tk.Widget):
        super().__init__(master)
        self._label = ttk.Label(self, text="", anchor="center")
        self._label.grid(column=0, row=0, sticky=EW, pady=5, padx=5)

        self._occurrence_data: Dict[str, Tuple[FileState, int, int]] = {}

        tree_widget = HierarchicalTree(self, [], ["content"], True)
        tree_widget.tree.configure(show="tree headings", selectmode=BROWSE)
        tree_widget.tree.heading("#0", text="Location")
        tree_widget.tree.heading("content", text="Content")
        tree_widget.grid(column=0, row=1, sticky=NSEW)
        self._tree = tree_widget

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

    def set_occurrences(
        self,
        property_name: str,
        occurrences: Dict[FileState, List[Tuple[int, int]]],
    ) -> None:
        self._occurrence_data = {}
        self._tree.clear()

        display_property = property_name.replace("[0]", "")
        self._label.config(
            text=f"Occurrences of {display_property}" if display_property else ""
        )

        input_files: List[str] = []
        for file_state in occurrences.keys():
            if file_state.filepath not in input_files:
                input_files.append(file_state.filepath)

        self._tree.create_tree_nodes(input_files)

        for file_state, file_occurrences in occurrences.items():
            file_id = self._tree.get_id_from_path(file_state.filepath)
            lines = file_state.content.split("\n")

            for line, column in file_occurrences:
                occurrence_id = self._tree.tree.insert(
                    file_id, tk.END, text=str(line), values=(lines[line - 1].strip(),)
                )
                self._occurrence_data[occurrence_id] = (file_state, line, column)

    def bind_selection(
        self,
        func: Callable[[FileState, int, int], None],
        add: Union[bool, Literal["", "+"], None] = None,
    ) -> None:
        def bind_func(_: tk.Event) -> None:
            selection = self._tree.tree.selection()
            if selection and selection[0] in self._occurrence_data:
                file_state, line, column = self._occurrence_data[selection[0]]
                func(file_state, line, column)

        self._tree.tree.bind("<<TreeviewSelect>>", bind_func, add)


class FindWindow(tk.Toplevel):
    def __init__(
        self,
        master: tk.Widget,
        controller: Controller,
        file_states: Dict[str, FileState],
        navigate_callback: Callable[[FileState, int, int], None],
    ):
        super().__init__(master)
        self.title("Find")
        self.controller = controller
        self.file_states = file_states
        self.navigate_callback = navigate_callback

        # Search mode selector
        mode_frame = ttk.Frame(self)
        mode_frame.grid(column=0, row=0, sticky=EW, padx=5, pady=5)
        ttk.Label(mode_frame, text="Search:").grid(column=0, row=0, padx=(0, 5))
        self._mode_combo = ttk.Combobox(
            mode_frame,
            values=["XML", "Property"],
            state="readonly",
            width=12,
        )
        self._mode_combo.current(0)
        self._mode_combo.grid(column=1, row=0)
        self._mode_combo.bind("<<ComboboxSelected>>", self._on_mode_change)

        # XML panel
        self._xml_panel = ttk.Frame(self)
        xml_trees = controller.get_xml_trees()
        self._xml_tree = XMLTree(self._xml_panel, xml_trees)
        self._xml_tree.grid(column=0, row=0, sticky=NSEW)
        self._xml_panel.grid_columnconfigure(0, weight=1)
        self._xml_panel.grid_rowconfigure(0, weight=1)
        self._xml_tree.bind_selection(self._on_xml_selected)

        # Property panel
        self._property_panel = ttk.Frame(self)
        input_frame = ttk.Frame(self._property_panel)
        input_frame.grid(column=0, row=0, sticky=EW, padx=5, pady=5)
        ttk.Label(input_frame, text="Property:").grid(column=0, row=0, padx=(0, 5))
        self._property_entry = TextBox(input_frame)
        self._property_entry.grid(column=1, row=0, sticky=EW)
        input_frame.grid_columnconfigure(1, weight=1)
        self._property_entry.bind("<Return>", self._on_property_search)

        self._occurrences_tree = PropertyOccurrencesTree(self._property_panel)
        self._occurrences_tree.grid(column=0, row=1, sticky=NSEW)
        self._occurrences_tree.bind_selection(navigate_callback)
        self._property_panel.grid_columnconfigure(0, weight=1)
        self._property_panel.grid_rowconfigure(1, weight=1)

        # Show XML panel by default, hide property panel
        self._xml_panel.grid(column=0, row=1, sticky=NSEW)
        self._property_panel.grid(column=0, row=1, sticky=NSEW)
        self._property_panel.grid_remove()

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

    def _on_mode_change(self, _: tk.Event) -> None:
        mode = self._mode_combo.get()
        if mode == "XML":
            self._property_panel.grid_remove()
            self._xml_panel.grid()
        else:
            self._xml_panel.grid_remove()
            self._property_panel.grid()

    def _on_xml_selected(self, filepath: str, column: int, line: int) -> None:
        file_state = self.file_states.get(filepath)
        if file_state is not None:
            self.navigate_callback(file_state, line, column)

    def _on_property_search(self, _: tk.Event) -> None:
        property_path = self._property_entry.get().strip()
        if not property_path:
            self._occurrences_tree.set_occurrences("", {})
            return

        variants = self.controller.expand_property_with_children(property_path)
        occurrences: Dict[FileState, List[Tuple[int, int]]] = {}
        if variants:
            occurrences = search_property_occurrences(
                variants, list(self.file_states.values())
            )

        self._occurrences_tree.set_occurrences(property_path, occurrences)
