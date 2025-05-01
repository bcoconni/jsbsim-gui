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
        left_frame = ttk.Frame(self)

        xml_trees = controller.get_xml_trees()
        input_files = []
        for xml_tree in xml_trees:
            for node in xml_tree:
                if node.filepath not in input_files:
                    input_files.append(node.filepath)

        notebook = ttk.Notebook(left_frame)
        fileview = FileTree(notebook, input_files)
        fileview.bind_selection(self.open_source_file)
        xmlview = XMLTree(notebook, xml_trees)
        xmlview.bind_selection(self.move_to)
        notebook.add(fileview, text="Project Files")
        notebook.add(xmlview, text="XML")

        with open(controller.filename, "r", encoding="utf-8") as f:
            file_relpath = controller.get_relative_path(controller.filename)
            self.codeview = LabeledWidget(self, file_relpath)
            self.codeview.set_widget(
                XMLSourceCodeView(
                    self.codeview, f.read(), width=80, height=30, wrap=NONE
                )
            )

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

    def open_source_file(self, filename: str) -> None:
        editor = self.codeview.widget
        if editor:
            with open(os.path.join(self.root_dir, filename), "r") as f:
                self.codeview.set_label(filename)
                editor.new_content(f.read())

    def move_to(self, filename: str, column: int, line: int) -> None:
        self.open_source_file(filename)
        editor: XMLSourceCodeView = self.codeview.widget
        editor.text.see(f"{line}.{column}")
