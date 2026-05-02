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
from tkinter.constants import BROWSE, EW, NSEW, VERTICAL
from tkinter.messagebox import showerror
from typing import Callable, Dict, List, Literal, Optional, Tuple, Union

import numpy as np
from jsbsim import FGPropertyNode
from .edit_actions import EditAction, EditableFrame


def _natural_sort_key(path: str) -> List[Tuple[str, int]]:
    result = []
    for component in path.split("/"):
        m = re.match(r"^(.*)\[(\d+)\]$", component)
        if m:
            result.append((m.group(1), int(m.group(2))))
        else:
            result.append((component, -1))
    return result


class HierarchicalTree(EditableFrame):
    def __init__(
        self,
        master: tk.Widget,
        nodes: List[str],
        columns_id: List[str],
        is_open: bool = True,
    ):
        super().__init__(master)
        self._tree = ttk.Treeview(self, columns=columns_id)
        self._tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self._hidden_items: List[Tuple[str, str, int]] = []
        self._num_columns = len(columns_id)

        self.create_tree_nodes(nodes, is_open)

        # Vertical scrollbar
        self._yscrollbar = ttk.Scrollbar(
            self, orient=VERTICAL, command=self._tree.yview
        )
        self._yscrollbar.pack(side=tk.LEFT, fill=tk.Y)
        self._tree["yscrollcommand"] = self._yscrollbar.set
        self._tree.bind("<Control-c>", self._copy_selected_items_to_clipboard)

        self.bbox = self._tree.bbox
        self.configure_tree = self._tree.configure
        self.get_children = self._tree.get_children
        self.heading = self._tree.heading
        self.identify_row = self._tree.identify_row
        self.insert = self._tree.insert
        self.item = self._tree.item
        self.see = self._tree.see
        self.selection = self._tree.selection
        self.selection_set = self._tree.selection_set
        self.set = self._tree.set
        self.yview = self._tree.yview

    def create_tree_nodes(self, nodes: List[str], is_open: bool = True) -> None:
        for node in nodes:
            parent_id = ""
            for name in node.split("/"):
                for child_id in self._tree.get_children(parent_id):
                    if name == self._tree.item(child_id, "text"):
                        parent_id = child_id
                        break
                else:
                    parent_id = self._tree.insert(
                        parent_id,
                        tk.END,
                        text=name,
                        values=[""] * self._num_columns,
                        open=is_open,
                    )

    def clear(self) -> None:
        for item in self._tree.get_children():
            self._tree.delete(item)
        self._hidden_items = []

    def move_to_top(self) -> None:
        children = self._tree.get_children()
        if children:
            self._tree.see(children[0])
            self._tree.yview_moveto(0)

    def bind(
        self,
        sequence: Optional[str],
        func: Callable[[tk.Event], None],
        add: Union[bool, Literal["", "+"], None] = None,
    ) -> None:
        self._tree.bind(sequence, func, add)

    def get_selected_items(self, leaf_only: bool) -> List[str]:
        tree = self._tree
        selected_items = []
        for item in tree.selection():
            name = tree.item(item, "text")
            parent = tree.parent(item)
            while parent:
                name = "/".join([tree.item(parent, "text"), name])
                parent = tree.parent(parent)

            if not (leaf_only and tree.get_children(item)):
                selected_items.append(name)

        return selected_items

    def filter(self, pattern: str, parent_id: str = "") -> bool:
        """
        Filters the hierarchical tree based on the given pattern.

        Args:
            pattern (str): The pattern to filter the tree with.
            parent_id (str, optional): The ID of the parent item. Defaults to "".

        Returns:
            bool: True if any item in the tree matches the pattern, False otherwise.
        """
        tree = self._tree
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
                self._tree.reattach(*child_params)

            self._hidden_items = []
            return True
        return False

    def collapse(self, parent_id: str = "") -> None:
        tree = self._tree
        for child_id in tree.get_children(parent_id):
            self.collapse(child_id)
            tree.item(child_id, open=False)
        tree.see(tree.get_children()[0])

    def get_id_from_path(self, path: str) -> Optional[str]:
        parent_id = ""
        for name in path.split("/"):
            for child_id in self._tree.get_children(parent_id):
                if name == self._tree.item(child_id, "text"):
                    parent_id = child_id
                    break
            else:
                return None

        return parent_id

    def _copy_selected_items_to_clipboard(self, _event: Optional[tk.Event]) -> str:
        self.clipboard_clear()
        for item in self.get_selected_items(False):
            self.clipboard_append(item)
        return "break"

    def apply_edit_action(self, action: EditAction) -> None:
        if action is EditAction.COPY:
            self._copy_selected_items_to_clipboard(None)


class TextBox(ttk.Entry):
    def __init__(self, master: tk.Widget, **kw):
        super().__init__(master, **kw)
        self.bind("<Control-a>", self._select_all)

    def _select_all(self, *_) -> str:
        self.selection_range(0, tk.END)
        # Return break to interrupt the default key binding.
        return "break"


class CellEntry(TextBox):
    def __init__(
        self, master: tk.Widget, content: str, update_value: Callable[[str], None], **kw
    ):
        super().__init__(master, **kw)
        self.update_value = update_value
        self.insert(0, content)
        self.config(exportselection=False)
        self._select_all()
        self.focus_force()
        self.bind("<Return>", self.set_value)
        self.bind("<KP_Enter>", self.set_value)
        self.bind("<Escape>", lambda _: self.destroy())
        self.bind("<FocusOut>", lambda _: self.destroy())

    def set_value(self, _) -> None:
        self.update_value(self.get())
        self.destroy()


class SearchableTree(EditableFrame):
    def __init__(
        self, master: tk.Widget, create_tree: Callable[[tk.Widget], HierarchicalTree]
    ):
        super().__init__(master)
        self._visible_items: List[str] = []

        search_frame = ttk.Frame(self, padding=(0, 2))
        search_frame.grid(column=0, row=0, sticky=EW)
        search_label = ttk.Label(search_frame, text="Search:")
        search_label.grid(column=0, row=0, padx=10, sticky=tk.W)
        self._search_box = TextBox(search_frame)
        self._search_box.grid(column=1, row=0, sticky=EW)
        self.tree = create_tree(self)
        self.tree.grid(column=0, row=1, columnspan=3, sticky=NSEW)

        collapse_button = ttk.Button(
            search_frame, text="Collapse", command=self.collapse
        )
        collapse_button.grid(column=2, row=0, padx=5)

        # Widget layout
        search_frame.grid_columnconfigure(1, weight=1)
        search_frame.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._search_box.bind("<KeyRelease>", self._search)
        self.tree._yscrollbar.configure(command=self._yview)

    def _yview(self, *args) -> None:
        self._update_visible_items(None)
        return self.tree.yview(*args)

    def get_search_text(self) -> str:
        return self._search_box.get()

    def set_search_text(self, text: str) -> None:
        self._search_box.selection_range(0, tk.END)
        self._search_box.select_clear()
        self._search_box.insert(0, text)
        self._search(None)

    def collapse(self, parent_id: str = "") -> None:
        self.tree.collapse(parent_id)

    def _search(self, _: Optional[tk.Event]) -> None:
        self.tree.unfilter()
        pattern = self._search_box.get()
        if pattern:
            self.tree.filter(pattern)

        self._update_visible_items(None)
        self.tree.move_to_top()

    def _update_visible_items(self, _: Optional[tk.Event]) -> None:
        self._visible_items = []
        tree = self.tree

        def enumerate_children(parent_id: str) -> None:
            children = tree.get_children(parent_id)
            if children:
                if tree.item(parent_id, "open"):
                    for child_id in children:
                        enumerate_children(child_id)
            elif tree.bbox(parent_id):
                self._visible_items.append(parent_id)

        for item in tree.get_children():
            enumerate_children(item)

    def apply_edit_action(self, action: EditAction) -> None:
        self.tree.apply_edit_action(action)


class PropertyTree(SearchableTree):
    def __init__(
        self, master: tk.Widget, properties: List[FGPropertyNode], root: FGPropertyNode
    ):
        self._property_root: str = root.get_fully_qualified_name()
        common_root, property_pairs = self.get_unified_property_names(root, properties)
        sorted_properties = [pair[0] for pair in property_pairs]
        sorted_names = [pair[1] for pair in property_pairs]
        super().__init__(
            master,
            lambda parent: HierarchicalTree(parent, sorted_names, ["value"], False),
        )
        self._properties: Dict[str, FGPropertyNode] = {}

        tree = self.tree
        tree.configure_tree(displaycolumns=("value",))  # Hide the node columns
        tree.heading("#0", text="Property")
        tree.heading("value", text="Value")
        self._initialize_values(sorted_properties, sorted_names)
        self._rename_indexed_nodes()
        self._bind_ids_to_nodes("", common_root)
        tree.bind("<Double-Button-1>", self._edit_property_value)
        self.tree.bind("<ButtonRelease-1>", self._update_visible_items, add="+")

        self.get_selected_property_names = self.tree.get_selected_items

    def _rename_indexed_nodes(self, parent_id: str = "") -> None:
        tree = self.tree
        children = tree.get_children(parent_id)
        nchildren = len(children)
        for i, child_id in enumerate(children):
            name = tree.item(child_id, "text")
            if i + 1 < nchildren and tree.item(children[i + 1], "text") == f"{name}[1]":
                tree.item(child_id, text=f"{name}[0]")
            self._rename_indexed_nodes(child_id)

    def get_unified_property_names(
        self, root: FGPropertyNode, properties: List[FGPropertyNode]
    ) -> Tuple[FGPropertyNode, List[Tuple[FGPropertyNode, str]]]:
        have_common_root = True
        raw_names = []
        for node in properties:
            name = node.get_fully_qualified_name()
            raw_names.append(name)
            if have_common_root and not name.startswith(self._property_root):
                have_common_root = False

        if have_common_root:
            # Remove the root name and its trailing slash
            offset = len(self._property_root) + 1
            common_root = root
        else:
            offset = 1  # Remove the leading slash
            common_root = root.get_node("/")
            assert common_root is not None

        stripped_names = [name[offset:] for name in raw_names]
        pairs = sorted(
            zip(properties, stripped_names),
            key=lambda pair: _natural_sort_key(pair[1]),
        )
        return common_root, list(pairs)

    def collapse(self, parent_id: str = "") -> None:
        super().collapse(parent_id)
        self._update_visible_items(None)

    def _initialize_values(
        self, properties: List[FGPropertyNode], property_names: List[str]
    ) -> None:
        tree = self.tree
        for node, pname in zip(properties, property_names):
            parent_id = self.tree.get_id_from_path(pname)
            assert parent_id is not None
            tree.set(parent_id, "value", node.get_double_value())

    def _bind_ids_to_nodes(self, parent_id: str, root: FGPropertyNode) -> None:
        tree = self.tree
        for child_id in tree.get_children(parent_id):
            name = tree.item(child_id, "text")
            node = root.get_node(name)
            assert node is not None
            self._properties[child_id] = node
            self._bind_ids_to_nodes(child_id, node)

    def _search(self, event: tk.Event) -> None:
        super()._search(event)
        self._update_visible_items(None)

    def _edit_property_value(self, event: tk.Event) -> None:
        tree = self.tree
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
            tree, content, lambda value: self._set_value(item_id, value)
        )
        cell_entry.place(x=x, y=y, width=width, height=height)

    def _set_value(self, item_id: str, value: str) -> None:
        try:
            v = float(value)
        except ValueError:
            showerror("Error", message=f"'{value}' is not a number")
            return

        self._properties[item_id].set_double_value(v)
        self.update_values()

    def update_values(self, values: Optional[np.ndarray] = None) -> None:
        tree = self.tree
        if values is None:
            for item_id in self._visible_items:
                node = self._properties[item_id]
                tree.set(item_id, "value", node.get_double_value())
        else:
            for item_id, value in zip(self._visible_items, values):
                tree.set(item_id, "value", value)

    def get_selected_properties(self) -> List[FGPropertyNode]:
        selected_prop: List[FGPropertyNode] = []
        tree = self.tree

        def enumerate_children(parent_id: str) -> None:
            children = tree.get_children(parent_id)
            if children:
                for item in children:
                    enumerate_children(item)
            else:
                selected_prop.append(self._properties[parent_id])

        for selected_item in tree.selection():
            enumerate_children(selected_item)

        return selected_prop

    def _update_visible_items(self, event: Optional[tk.Event]) -> None:
        super()._update_visible_items(event)
        self.update_values()

    def get_visible_properties(self) -> List[FGPropertyNode]:
        return [self._properties[item_id] for item_id in self._visible_items]


class FileTree(HierarchicalTree):
    def __init__(self, master: tk.Widget, elements: List[str]):
        super().__init__(master, sorted(elements), [])
        self._tree.configure(show="tree", selectmode=BROWSE)
        self._tree.tag_configure("modified", foreground="red")

    def bind_selection(
        self,
        func: Callable[[str], None],
        add: Union[bool, Literal["", "+"], None] = None,
    ) -> None:
        def bind_func(_: tk.Event) -> None:
            selection = self.get_selected_items(True)
            if selection:
                func(selection[0])

        self._tree.bind("<<TreeviewSelect>>", bind_func, add)

    def highlight_file(self, filepath: str) -> None:
        item_id = self.get_id_from_path(filepath)
        assert item_id
        self._tree.item(item_id, tags=("modified",))

    def clear_highlight(self, filepath: str) -> None:
        item_id = self.get_id_from_path(filepath)
        assert item_id
        self._tree.item(item_id, tags=())
