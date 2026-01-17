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

import os
import re
import tkinter as tk
from tkinter import ttk
from tkinter.constants import BROWSE, NONE, NS, NSEW
from typing import Callable, Dict, List, Literal, Optional, Tuple, Union

from .controller import Controller, XMLNode
from .file_state import FileState
from .hierarchical_tree import FileTree, HierarchicalTree, PropertyTree, SearchableTree
from .textview import XMLSourceCodeView


class LabeledWidget(ttk.Frame):
    def __init__(self, master: tk.Widget, label: str):
        super().__init__(master)
        self.widget: Optional[tk.Widget] = None
        self.header_frame = ttk.Frame(self)
        self.header_frame.grid(column=0, row=0, sticky="ew", pady=5, padx=5)
        self.label = ttk.Label(self.header_frame, text=label, anchor="center")
        self.label.grid(column=0, row=0, sticky="ew")
        self.header_frame.columnconfigure(0, weight=1)

    def set_widget(self, widget: tk.Widget) -> None:
        self.widget = widget
        self.widget.grid(column=0, row=1, sticky=NSEW)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

    def set_label(self, label: str) -> None:
        self.label.config(text=label)


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

                node_id = tree.insert(
                    parent_id,
                    tk.END,
                    text=node.name,
                    open=False,
                )
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
    property_variants: List[str], file_states: Dict[str, FileState]
) -> Dict[str, List[Tuple[int, int]]]:
    results: Dict[str, List[Tuple[int, int]]] = {}

    dummy_frame = tk.Frame()
    dummy_editor = XMLSourceCodeView(dummy_frame)

    for filepath, file_state in file_states.items():
        file_occurrences = []

        dummy_editor.new_content(file_state.content)
        data_regions = dummy_editor.extract_tagged_regions("XML_data")
        attr_regions = dummy_editor.extract_tagged_regions("XML_attr_value")
        attr_regions = [
            (line, col + 1, text.strip('"')) for line, col, text in attr_regions
        ]

        all_regions = data_regions + attr_regions

        for line, column, text in all_regions:
            for variant in property_variants:
                pattern = r"(^|[\s/])" + re.escape(variant) + r"($|[\s/\[])"
                if re.search(pattern, text):
                    file_occurrences.append((line, column))
                    break

        if file_occurrences:
            results[filepath] = sorted(file_occurrences)

    dummy_frame.destroy()
    return results


class PropertyOccurrencesTree(LabeledWidget):
    def __init__(
        self,
        master: tk.Widget,
        property_name: str,
        occurrences: Dict[str, List[Tuple[int, int, str]]],
        close_callback: Callable[[], None],
    ):
        display_property = property_name.replace("[0]", "")
        super().__init__(master, f"Occurrences of: {display_property}")

        close_button = ttk.Button(
            self.header_frame, text="✕", width=3, command=close_callback
        )
        close_button.grid(column=1, row=0)

        self.occurrence_data: Dict[str, Tuple[str, int, int]] = {}

        input_files = []
        for filepath in occurrences.keys():
            if filepath not in input_files:
                input_files.append(filepath)

        tree_widget = HierarchicalTree(self, input_files, ["line"], True)
        self.set_widget(tree_widget)

        tree_widget.tree.configure(show="tree headings", selectmode=BROWSE)
        tree_widget.tree.heading("#0", text="File")
        tree_widget.tree.heading("line", text="Line")

        for filepath, file_occurrences in occurrences.items():
            file_id = tree_widget.get_id_from_path(filepath)

            for line, column in file_occurrences:
                occurrence_id = tree_widget.tree.insert(
                    file_id,
                    tk.END,
                    text="",
                    values=(str(line),),
                )
                self.occurrence_data[occurrence_id] = (filepath, line, column)

    def bind_selection(
        self,
        func: Callable[[str, int, int], None],
        add: Union[bool, Literal["", "+"], None] = None,
    ) -> None:
        def bind_func(_: tk.Event) -> None:
            tree_widget: HierarchicalTree = self.widget
            selection = tree_widget.tree.selection()
            if selection and selection[0] in self.occurrence_data:
                filepath, line, column = self.occurrence_data[selection[0]]
                func(filepath, line, column)

        tree_widget: HierarchicalTree = self.widget
        tree_widget.tree.bind("<<TreeviewSelect>>", bind_func, add)


class SourceEditor(ttk.Frame):
    def __init__(
        self,
        master: tk.Widget,
        controller: Controller,
    ):
        super().__init__(master)
        self.root_dir = controller.get_root_dir()
        self.controller = controller
        self.file_states: Dict[str, FileState] = {}
        left_frame = ttk.Frame(self)

        xml_trees = controller.get_xml_trees()
        input_files = []
        for xml_tree in xml_trees:
            for node in xml_tree:
                if node.filepath not in input_files:
                    input_files.append(node.filepath)

        notebook = ttk.Notebook(left_frame)
        self.fileview = FileTree(notebook, input_files)
        self.fileview.bind_selection(
            lambda filepath: self.open_source_file(self.file_states[filepath])
        )
        xmlview = XMLTree(notebook, xml_trees)
        xmlview.bind_selection(
            lambda filename, column, line: self.move_to(
                self.file_states[filename], False, column, line
            )
        )
        notebook.add(self.fileview, text="Project Files")
        notebook.add(xmlview, text="XML")

        for filepath in input_files:
            with open(
                os.path.join(self.root_dir, filepath), "r", encoding="utf-8"
            ) as f:
                self.file_states[filepath] = FileState(filepath, f.read())

        file_relpath = controller.get_relative_path(controller.filename)
        self.current_file = self.file_states[file_relpath]
        self.codeview = LabeledWidget(self, file_relpath)
        editor = XMLSourceCodeView(
            self.codeview,
            self.current_file.content,
            width=80,
            height=30,
            wrap=NONE,
        )
        self.codeview.set_widget(editor)

        self.modified_event_id = editor.text.bind("<<Modified>>", self.on_text_modified)
        self.bind("<Control-s>", lambda e: self.save_file())

        self.property_view = LabeledWidget(left_frame, "Property Explorer")
        property_tree = PropertyTree(
            self.property_view,
            controller.get_property_list(),
            controller.get_property_root().get_fully_qualified_name(),
        )
        self.property_view.set_widget(property_tree)

        property_tree.tree.tree.bind(
            "<ButtonRelease-3>", self.on_property_selected, add="+"
        )

        self.occurrence_view: Optional[PropertyOccurrencesTree] = None

        # Window layout
        self.codeview.grid(column=1, row=0, sticky=NSEW)
        notebook.grid(column=0, row=0, sticky=NSEW)
        self.property_view.grid(column=0, row=1, sticky=NS)
        self.left_frame = left_frame
        left_frame.grid(column=0, row=0, sticky=NS)
        left_frame.grid_columnconfigure(0, weight=1)
        left_frame.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

    def on_property_selected(self, event: tk.Event) -> None:
        property_tree: PropertyTree = self.property_view.widget
        tree = property_tree.tree.tree
        item_id = tree.identify_row(event.y)

        # Dismiss when the table header is selected
        if not item_id:
            return

        property_node = property_tree.properties[item_id]
        property_path = property_node.get_fully_qualified_name()

        variants = self.controller.expand_property_with_children(property_path)
        if not variants:
            return

        occurrences = search_property_occurrences(variants, self.file_states)
        if not occurrences:
            return

        self.show_occurrence_panel(property_path, occurrences)

    def show_occurrence_panel(
        self, property_name: str, occurrences: Dict[str, List[Tuple[int, int, str]]]
    ) -> None:
        self.property_view.grid_remove()

        if self.occurrence_view:
            self.occurrence_view.destroy()

        self.occurrence_view = PropertyOccurrencesTree(
            self.left_frame, property_name, occurrences, self.hide_occurrence_panel
        )
        self.occurrence_view.bind_selection(
            lambda filepath, line, column: self.move_to(
                self.file_states[filepath], True, column, line
            )
        )
        self.occurrence_view.grid(column=0, row=1, sticky=NS)

    def hide_occurrence_panel(self) -> None:
        if self.occurrence_view:
            self.occurrence_view.grid_remove()
            self.occurrence_view.destroy()
            self.occurrence_view = None

        self.property_view.grid(column=0, row=1, sticky=NS)

    def open_source_file(self, file_state: FileState) -> None:
        editor: XMLSourceCodeView = self.codeview.widget
        if file_state is not self.current_file:
            self.current_file.content = editor.text.get("1.0", "end-1c")

            # Avoid calling `self.on_text_modified` as new content will be loaded in the editor.
            editor.text.unbind("<<Modified>>", self.modified_event_id)

            self.codeview.set_label(file_state.filepath)
            editor.new_content(file_state.content)

            self.modified_event_id = editor.text.bind(
                "<<Modified>>", self.on_text_modified
            )

            self.current_file = file_state
            self.update_title_bar_state()

    def move_to(
        self, file_state: FileState, focus: bool, column: int, line: int
    ) -> None:
        self.open_source_file(file_state)
        editor: XMLSourceCodeView = self.codeview.widget
        editor.text.mark_unset("insert")
        editor.text.mark_set("insert", f"{line}.{column}")
        editor.text.see("insert")
        if focus:
            editor.text.focus()

    def on_text_modified(self, _event: tk.Event) -> None:
        editor: XMLSourceCodeView = self.codeview.widget

        if editor.text.edit_modified() and not self.current_file.is_modified:
            self.current_file.is_modified = True
            self.fileview.highlight_file(self.current_file.filepath)
            self.update_title_bar_state()

    def update_title_bar_state(self) -> None:
        any_modified = self.has_modified_files()
        self.master.mark_title_modified(any_modified)

    def has_modified_files(self) -> bool:
        return any(file_state.is_modified for file_state in self.file_states.values())

    def get_modified_files(self) -> List[FileState]:
        return [
            file_state
            for file_state in self.file_states.values()
            if file_state.is_modified
        ]

    def save_file(self) -> bool:
        if not self.current_file.is_modified:
            return True

        editor: XMLSourceCodeView = self.codeview.widget
        self.current_file.content = editor.text.get("1.0", "end-1c")

        error = self.current_file.validate_xml()
        if error:
            self.move_to(self.current_file, True, *error)
            return False

        if self.current_file.write(self.root_dir):
            self.fileview.clear_highlight(self.current_file.filepath)
            self.update_title_bar_state()
            return True

        return False

    def save_all(self) -> bool:
        modified_files = self.get_modified_files()
        if not modified_files:
            return True

        if self.current_file.is_modified:
            editor: XMLSourceCodeView = self.codeview.widget
            self.current_file.content = editor.text.get("1.0", "end-1c")

        for file_state in modified_files:
            error = file_state.validate_xml()
            if error:
                self.move_to(file_state, True, *error)
                return False

        # Save AFTER all the files have been validated
        for file_state in modified_files:
            if not file_state.write(self.root_dir):
                return False
            self.fileview.clear_highlight(file_state.filepath)

        self.update_title_bar_state()
        return True
