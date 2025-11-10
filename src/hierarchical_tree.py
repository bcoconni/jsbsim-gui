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

import tkinter as tk
from tkinter import ttk
from tkinter.constants import BROWSE, EW, NSEW, VERTICAL
from tkinter.messagebox import showerror
from typing import Callable, Dict, Iterator, List, Literal, Optional, Tuple, Union

from jsbsim import FGPropertyNode


class HierarchicalTree(ttk.Frame):
    def __init__(
        self,
        master: tk.Widget,
        elements: List[str],
        columns_id: List[str],
        is_open: bool = True,
    ):
        super().__init__(master)
        self.tree = ttk.Treeview(self, columns=columns_id)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self._hidden_items: List[Tuple[str, str, int]] = []

        for elm in sorted(elements):
            parent_id = ""
            for name in elm.split("/"):
                for child_id in self.tree.get_children(parent_id):
                    if name == self.tree.item(child_id, "text"):
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
        self.yscrollbar = ttk.Scrollbar(self, orient=VERTICAL, command=self.tree.yview)
        self.yscrollbar.pack(side=tk.LEFT, fill=tk.Y)
        self.tree["yscrollcommand"] = self.yscrollbar.set

    def bind(
        self,
        sequence: Optional[str],
        func: Callable[[tk.Event], None],
        add: Union[bool, Literal["", "+"], None] = None,
    ) -> None:
        self.yscrollbar.bind(sequence, func, add)
        self.tree.bind(sequence, func, add)

    def get_selected_elements(self) -> List[str]:
        selected_prop = []
        for selected_item in self.tree.selection():
            name = self.tree.item(selected_item, "text")
            parent = self.tree.parent(selected_item)
            while parent:
                name = "/".join([self.tree.item(parent, "text"), name])
                parent = self.tree.parent(parent)

            if not self.tree.get_children(selected_item):
                selected_prop.append(name)

        return selected_prop

    def filter(self, pattern: str, parent_id: str = "") -> bool:
        """
        Filters the hierarchical tree based on the given pattern.

        Args:
            pattern (str): The pattern to filter the tree with.
            parent_id (str, optional): The ID of the parent item. Defaults to "".

        Returns:
            bool: True if any item in the tree matches the pattern, False otherwise.
        """
        tree = self.tree
        success = False

        for child_id in tree.get_children(parent_id):
            if pattern in tree.item(child_id, "text"):
                tree.see(child_id)
                success = True
                continue

            if self.filter(pattern, child_id):
                success = True
            else:
                self._hidden_items.append((child_id, parent_id, tree.index(child_id)))
                tree.detach(child_id)
        return success

    def unfilter(self) -> bool:
        """
        Unfilters the hidden items in the hierarchical tree.

        Returns:
            bool: True if there were hidden items to unfilter, False otherwise.
        """
        if self._hidden_items:
            for child_params in reversed(self._hidden_items):
                self.tree.reattach(*child_params)

            self._hidden_items = []
            return True
        return False

    def collapse(self, parent_id: str = "") -> None:
        tree = self.tree
        for child_id in tree.get_children(parent_id):
            self.collapse(child_id)
            tree.item(child_id, open=False)
        tree.see(tree.get_children()[0])


class CellEntry(ttk.Entry):
    def __init__(
        self,
        master: tk.Widget,
        content: str,
        update_value: Callable[[str], None],
        **kw,
    ):
        super().__init__(master, **kw)
        self.update_value = update_value
        self.insert(0, content)
        self.config(exportselection=False)
        self.select_all()
        self.focus_force()
        self.bind("<Return>", self.set_value)
        self.bind("<KP_Enter>", self.set_value)
        self.bind("<Control-a>", self.select_all)
        self.bind("<Escape>", lambda _: self.destroy())
        self.bind("<FocusOut>", lambda _: self.destroy())

    def set_value(self, _) -> None:
        self.update_value(self.get())
        self.destroy()

    def select_all(self, *_) -> str:
        self.selection_range(0, tk.END)
        # Return break to interrupt the default key binding.
        return "break"


class SearchableTree(ttk.Frame):
    def __init__(
        self, master: tk.Widget, create_tree: Callable[[tk.Widget], HierarchicalTree]
    ):
        super().__init__(master)
        self.visible_items: List[str] = []

        search_frame = ttk.Frame(self, padding=(0, 2))
        search_frame.grid(column=0, row=0, sticky=EW)
        search_label = ttk.Label(search_frame, text="Search:")
        search_label.grid(column=0, row=0, padx=10)
        self.search_box = ttk.Entry(search_frame)
        self.search_box.grid(column=1, row=0, sticky=EW)
        self.tree = create_tree(self)
        self.tree.grid(column=0, row=1, columnspan=3, sticky=NSEW)

        collapse_button = ttk.Button(
            search_frame, text="Collapse", command=self.collapse
        )
        collapse_button.grid(column=2, row=0, padx=10)

        # Widget layout
        search_frame.grid_columnconfigure(1, weight=1)
        search_frame.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self.search_box.bind("<KeyRelease>", self.search)

    def collapse(self, parent_id: str = "") -> None:
        self.tree.collapse(parent_id)

    def search(self, _: tk.Event) -> None:
        self.tree.unfilter()
        pattern = self.search_box.get()
        if pattern:
            self.tree.filter(pattern)

        self.update_visible_properties(None)

    def update_visible_properties(self, _: tk.Event) -> None:
        self.visible_items = []
        tree = self.tree.tree

        def enumerate_children(parent_id: str) -> None:
            children = tree.get_children(parent_id)
            if children:
                if tree.item(parent_id, "open"):
                    for item in children:
                        enumerate_children(item)
            elif tree.bbox(parent_id):
                self.visible_items.append(parent_id)

        for item in tree.get_children():
            enumerate_children(item)


class PropertyTree(SearchableTree):
    def __init__(
        self, master: tk.Widget, properties: List[FGPropertyNode], property_root: str
    ):
        self.property_root: str = property_root
        super().__init__(
            master,
            lambda parent: HierarchicalTree(
                parent, self.get_unified_property_names(properties), ["value"], False
            ),
        )
        self.properties: Dict[str, FGPropertyNode] = {}

        tree = self.tree.tree
        tree.configure(displaycolumns=("value",))  # Hide the node columns
        tree.heading("#0", text="Property")
        tree.heading("value", text="Value")
        self.initialize_values(properties)
        self.tree.tree.bind("<Double-Button-1>", self.edit_property_value)
        self.tree.bind("<ButtonRelease-1>", self.update_visible_properties, add="+")

    def get_unified_property_names(
        self, properties: List[FGPropertyNode]
    ) -> Iterator[str]:
        have_common_root = True
        unified_property_names = []
        for node in properties:
            name = node.get_fully_qualified_name()
            unified_property_names.append(name)
            if have_common_root and not name.startswith(self.property_root):
                have_common_root = False

        if have_common_root:
            # Remove the root name and its trailing slash
            offset = len(self.property_root) + 1
        else:
            offset = 1  # Remove the leading slash

        return map(lambda name: name[offset:], unified_property_names)

    def collapse(self, parent_id: str = "") -> None:
        super().collapse(parent_id)
        self.update_visible_properties(None)

    def initialize_values(self, properties: List[FGPropertyNode]) -> None:
        tree = self.tree.tree
        property_names = self.get_unified_property_names(properties)
        for node, pname in zip(properties, property_names):
            parent_id = ""
            for name in pname.split("/"):
                for child_id in tree.get_children(parent_id):
                    if name == tree.item(child_id, "text"):
                        parent_id = child_id
                        break
                else:
                    assert tree.item(child_id, "text") == name
            tree.set(parent_id, "value", node.get_double_value())
            self.properties[parent_id] = node

    def search(self, event: tk.Event) -> None:
        super().search(event)
        self.update_visible_properties(None)

    def edit_property_value(self, event: tk.Event) -> None:
        tree = self.tree.tree
        item_id = tree.identify_row(event.y)

        # Dismiss when the table header is selected
        if not item_id:
            return

        content = tree.item(item_id, "values")[0]
        # Dismiss when the cell is empty
        if content == "":
            return

        # node = self.properties[item_id]
        # Dismiss when the property is readonly
        # if not node.get_attribute(Attribute.WRITE):
        #     return

        x, y, width, height = tree.bbox(item_id, "value")
        cell_entry = CellEntry(
            tree, content, lambda value: self.set_value(item_id, value)
        )
        cell_entry.place(x=x, y=y, width=width, height=height)

    def set_value(self, item_id: str, value: str) -> None:
        try:
            v = float(value)
        except ValueError:
            showerror("Error", message=f"'{value}' is not a number")
            return

        self.properties[item_id].set_double_value(v)
        self.update_values()

    def update_values(self, values: Optional[List[float]] = None) -> None:
        tree = self.tree.tree
        if values is None:
            for item_id in self.visible_items:
                node = self.properties[item_id]
                tree.set(item_id, "value", node.get_double_value())
        else:
            for item_id, value in zip(self.visible_items, values):
                tree.set(item_id, "value", value)

    def get_selected_elements(self) -> List[FGPropertyNode]:
        selected_prop: List[FGPropertyNode] = []
        tree = self.tree.tree

        def enumerate_children(parent_id: str) -> None:
            children = tree.get_children(parent_id)
            if children:
                for item in children:
                    enumerate_children(item)
            else:
                selected_prop.append(self.properties[parent_id])

        for selected_item in tree.selection():
            enumerate_children(selected_item)

        return selected_prop

    def update_visible_properties(self, event: tk.Event) -> None:
        super().update_visible_properties(event)
        self.update_values()

    def get_visible_properties(self) -> List[FGPropertyNode]:
        return [self.properties[item_id] for item_id in self.visible_items]


class FileTree(HierarchicalTree):
    def __init__(self, master: tk.Widget, elements: List[str]):
        super().__init__(master, elements, [])
        self.tree.configure(show="tree", selectmode=BROWSE)

    def bind_selection(
        self,
        func: Callable[[str], None],
        add: Union[bool, Literal["", "+"], None] = None,
    ) -> None:
        def bind_func(_: tk.Event) -> None:
            selection = self.get_selected_elements()
            if selection:
                func(selection[0])

        self.tree.bind("<<TreeviewSelect>>", bind_func, add)
