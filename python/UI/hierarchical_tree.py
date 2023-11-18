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
from tkinter.constants import BROWSE, NS, NSEW, VERTICAL
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


class PropertyTree(HierarchicalTree):
    def __init__(
        self,
        master: tk.Widget,
        properties: list[str],
        get_property_value: Callable[[str], float],
    ):
        super().__init__(master, properties, ("prop", "val"), False)

        self.tree.heading("prop", text="Name")
        self.tree.heading("val", text="Values")
        self.set_values("", None, get_property_value)

    def set_values(
        self,
        parent_name: str,
        parent_id: str,
        get_property_value: Callable[[str], float],
    ):
        children = self.tree.get_children(parent_id)
        for child_id in children:
            child = self.tree.item(child_id)
            child_name = str(child["values"][0]).strip()
            if parent_name:
                child_name = "/".join([parent_name, child_name])
            self.set_values(child_name, child_id, get_property_value)

        if not children:
            self.tree.set(parent_id, "val", get_property_value(parent_name))


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
