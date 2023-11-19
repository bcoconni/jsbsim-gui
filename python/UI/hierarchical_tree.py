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
from typing import Callable, Optional


class HierarchicalTree(ttk.Frame):
    def __init__(
        self,
        master: tk.Widget,
        elements: list[str],
        columns_id: tuple[str],
        is_open: bool = True,
    ):
        super().__init__(master)
        self.tree = ttk.Treeview(self, columns=columns_id)
        self.tree.grid(column=0, row=0, sticky=NSEW)

        self.tree.column("#0", width=60, stretch=False)

        for elm in sorted(elements):
            parent_id = ""
            for depth, name in enumerate(elm.split("/")):
                for child_id in self.tree.get_children(parent_id):
                    child = self.tree.item(child_id)
                    child_name = str(child["values"][0]).strip()
                    if name == child_name:
                        parent_id = child_id
                        break
                else:
                    display_name = "  " * depth + name
                    parent_id = self.tree.insert(
                        parent_id, tk.END, values=(display_name, ""), open=is_open
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
            name = str(item["values"][0]).strip()

            parent = self.tree.parent(selected_item)
            while parent:
                item = self.tree.item(parent)
                name = "/".join([str(item["values"][0]).strip(), name])
                parent = self.tree.parent(parent)

            if not self.tree.get_children([selected_item]):
                selected_prop.append(name)

        return selected_prop

    def collapse(self, parent_id: str = ""):
        tree = self.tree
        for child_id in tree.get_children(parent_id):
            self.collapse(child_id)
            tree.item(child_id, open=False)


class PropertyTree(ttk.Frame):
    def __init__(
        self,
        master: tk.Widget,
        properties: list[str],
        get_property_value: Callable[[str], float],
    ):
        super().__init__(master)
        self.get_property_value = get_property_value
        self.hidden_items: list[tuple[str, str, int]] = []

        search_frame = ttk.Frame(self, padding=(0, 2))
        search_frame.grid(column=0, row=0)
        search_label = ttk.Label(search_frame, text="Search:")
        search_label.grid(column=0, row=0, padx=10)
        self.search_string = tk.StringVar()
        search_box = ttk.Entry(search_frame, textvariable=self.search_string)
        search_box.grid(column=1, row=0, sticky=EW)

        self.proptree = HierarchicalTree(self, properties, ("prop", "val"), False)
        self.proptree.grid(column=0, row=1, sticky=NSEW)
        tree = self.proptree.tree
        tree.heading("prop", text="Name")
        tree.heading("val", text="Values")
        self.set_values()

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

    def set_values(self, parent_name: str = "", parent_id: str | None = None) -> None:
        tree = self.proptree.tree
        children = tree.get_children(parent_id)
        for child_id in children:
            child = tree.item(child_id)
            child_name = str(child["values"][0]).strip()
            if parent_name:
                child_name = "/".join([parent_name, child_name])
            self.set_values(child_name, child_id)

        if not children:
            tree.set(parent_id, "val", self.get_property_value(parent_name))

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
            child_name = str(child["values"][0]).strip()
            if pattern in child_name:
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
        super().__init__(master, elements, ("name",))
        self.tree.configure(show="tree", selectmode=BROWSE)

    def bind(self, sequence: Optional[str], func, add: Optional[bool] = None) -> None:
        def bind_func(_):
            selection = self.get_selected_elements()
            if selection:
                func(selection[0])

        self.tree.bind(sequence, bind_func, add)
