# A Graphical User Interface for JSBSim
#
# Copyright (c) 2023 Bertrand Coconnier
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

import tkinter as tk
from tkinter import ttk
from tkinter.constants import BROWSE, EW, NS, NSEW, VERTICAL
from typing import Callable

from jsbsim import FGPropertyNode


class HierarchicalTree(ttk.Frame):
    def __init__(
        self,
        master: tk.Widget,
        elements: list[str],
        columns_id: list[str],
        is_open: bool = True,
    ):
        super().__init__(master)
        self.tree = ttk.Treeview(self, columns=columns_id)
        self.tree.grid(column=0, row=0, sticky=NSEW)

        for elm in sorted(elements):
            parent_id = ""
            for name in elm.split("/"):
                for child_id in self.tree.get_children(parent_id):
                    child = self.tree.item(child_id)
                    if name == child["text"]:
                        parent_id = child_id
                        break
                else:
                    parent_id = self.tree.insert(
                        parent_id,
                        tk.END,
                        text=name,
                        values=[""] * len(columns_id),
                        open=is_open,
                    )

        # Vertical scrollbar
        ys = ttk.Scrollbar(self, orient=VERTICAL, command=self.tree.yview)
        ys.grid(column=1, row=0, sticky=NS)
        self.tree["yscrollcommand"] = ys.set

        # Widget layout
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

    def get_selected_elements(self) -> list[str]:
        selected_prop = []
        for selected_item in self.tree.selection():
            item = self.tree.item(selected_item)
            name = item["text"]

            parent = self.tree.parent(selected_item)
            while parent:
                item = self.tree.item(parent)
                name = "/".join([item["text"], name])
                parent = self.tree.parent(parent)

            if not self.tree.get_children(selected_item):
                selected_prop.append(name)

        return selected_prop

    def collapse(self, parent_id: str = ""):
        tree = self.tree
        for child_id in tree.get_children(parent_id):
            self.collapse(child_id)
            tree.item(child_id, open=False)
        tree.see(tree.get_children()[0])


class PropertyTree(ttk.Frame):
    def __init__(
        self,
        master: tk.Widget,
        properties: list[FGPropertyNode],
    ):
        super().__init__(master)
        self.hidden_items: list[tuple[str, str, int]] = []

        search_frame = ttk.Frame(self, padding=(0, 2))
        search_frame.grid(column=0, row=0, sticky=EW)
        search_label = ttk.Label(search_frame, text="Search:")
        search_label.grid(column=0, row=0, padx=10)
        self.search_string = tk.StringVar()
        search_box = ttk.Entry(search_frame, textvariable=self.search_string)
        search_box.grid(column=1, row=0, sticky=EW)

        self.proptree = HierarchicalTree(
            self, [p.get_relative_name() for p in properties], ["value", "node"], False
        )
        self.proptree.grid(column=0, row=1, sticky=NSEW)
        tree = self.proptree.tree
        tree.configure(displaycolumns=("value",))  # Hide the node columns
        tree.heading("#0", text="Property")
        tree.heading("value", text="Value")
        self.set_values(properties)

        collapse_button = ttk.Button(
            search_frame, text="Collapse", command=self.proptree.collapse
        )
        collapse_button.grid(column=2, row=0, padx=10)

        # Widget layout
        search_frame.grid_columnconfigure(1, weight=1)
        search_frame.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        search_box.bind("<KeyRelease>", self.search)

    def set_values(self, properties: list[FGPropertyNode]) -> None:
        tree = self.proptree.tree
        for node in properties:
            parent_id = ""
            pname = node.get_relative_name()
            for name in pname.split("/"):
                for child_id in tree.get_children(parent_id):
                    if name == tree.item(child_id,"text"):
                        parent_id = child_id
                        break
                else:
                    assert tree.item(child_id, "text") == name
            tree.set(parent_id, "value", node.get_double_value())
            tree.set(parent_id, "node", node)

    def search(self, _) -> None:
        tree = self.proptree.tree
        for child_id, parent_id, idx in reversed(self.hidden_items):
            tree.reattach(child_id, parent_id, idx)

        self.hidden_items = []
        pattern = self.search_string.get()
        if pattern:
            self.filter(pattern)

    def filter(self, pattern: str, parent_id: str = "") -> bool:
        tree = self.proptree.tree
        retVal = False

        for child_id in tree.get_children(parent_id):
            child = tree.item(child_id)
            if pattern in child["text"]:
                tree.see(child_id)
                retVal = True
                continue
            if not self.filter(pattern, child_id):
                idx = tree.index(child_id)
                self.hidden_items.append((child_id, parent_id, idx))
                tree.detach(child_id)
        return retVal


class FileTree(HierarchicalTree):
    def __init__(self, master: tk.Widget, elements: list[str]):
        super().__init__(master, elements, [])
        self.tree.configure(show="tree", selectmode=BROWSE)

    def bind_selection(
        self, func: Callable[[str], None], add: bool | None = None
    ) -> None:
        def bind_func(_):
            selection = self.get_selected_elements()
            if selection:
                func(selection[0])

        self.tree.bind("<<TreeviewSelect>>", bind_func, add)
