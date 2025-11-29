# A Graphical User Interface for JSBSim
#
# Copyright (c) 2023-2024 Bertrand Coconnier
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
import tkinter as tk
from tkinter import ttk
from tkinter.constants import BROWSE, NONE, NS, NSEW
from typing import Callable, Dict, List, Literal, Optional, Union

from .controller import Controller, XMLNode
from .file_state import FileState
from .hierarchical_tree import FileTree, HierarchicalTree, PropertyTree, SearchableTree
from .textview import XMLSourceCodeView


class LabeledWidget(ttk.Frame):
    def __init__(self, master: tk.Widget, label: str):
        super().__init__(master)
        self.widget: Optional[tk.Widget] = None
        self.label = ttk.Label(self, text=label)
        self.label.grid(column=0, row=0)

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


class SourceEditor(ttk.Frame):
    def __init__(
        self,
        master: tk.Widget,
        controller: Controller,
    ):
        super().__init__(master)
        self.root_dir = controller.get_root_dir()
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

        property_view = LabeledWidget(left_frame, "Property Explorer")
        property_view.set_widget(
            PropertyTree(
                property_view,
                controller.get_property_list(),
                controller.get_property_root().get_fully_qualified_name(),
            )
        )

        # Window layout
        self.codeview.grid(column=1, row=0, sticky=NSEW)
        notebook.grid(column=0, row=0, sticky=NSEW)
        property_view.grid(column=0, row=1, sticky=NS)
        left_frame.grid(column=0, row=0, sticky=NS)
        left_frame.grid_columnconfigure(0, weight=1)
        left_frame.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

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
