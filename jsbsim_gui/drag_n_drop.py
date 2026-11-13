# A Graphical User Interface for JSBSim
#
# Copyright (c) 2023-2026 Bertrand Coconnier
#
# This program is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation; either version 3 of the License, or (at your option) any later
# version.

import tkinter as tk
from abc import ABC, abstractmethod

import ttkbootstrap as ttk
from jsbsim import FGPropertyNode

from .csv_tree import CsvData, CsvTree
from .hierarchical_tree import PropertyTree, SearchableTree
from .plots_view import PlotsView


class DragNDropManager(ABC):
    def __init__(self, source: tk.Widget, target: tk.Widget):
        source.bind("<ButtonPress-1>", self.select, add=True)
        source.bind("<B1-Motion>", self.drag, add=True)
        source.bind("<ButtonRelease-1>", self.drop, add=True)
        self.offset_x = 0
        self.offset_y = 0
        self.dragged_widget_preview: tk.Widget | None = None
        self.target = target

    def select(self, event: tk.Event):
        root = event.widget.winfo_toplevel()
        self.offset_x = root.winfo_rootx()
        self.offset_y = root.winfo_rooty()

    @abstractmethod
    def create_source_widget(
        self, master: tk.Widget | tk.Tk | tk.Toplevel
    ) -> tk.Widget:
        pass

    def drag(self, event: tk.Event):
        if not self.dragged_widget_preview:
            root = event.widget.winfo_toplevel()
            self.dragged_widget_preview = self.create_source_widget(root)

        if self.dragged_widget_preview:
            x, y = event.widget.winfo_pointerxy()
            self.dragged_widget_preview.place(x=x - self.offset_x, y=y - self.offset_y)

    @abstractmethod
    def drop_on_target(self, event: tk.Event):
        pass

    def drop(self, event: tk.Event):
        if self.dragged_widget_preview:
            self.dragged_widget_preview.destroy()
            self.dragged_widget_preview = None

            x, y = event.widget.winfo_pointerxy()
            target_widget = event.widget.winfo_containing(x, y)
            if str(target_widget).startswith(str(self.target)):
                self.drop_on_target(event)


class DnDTreeItems(DragNDropManager):
    def __init__(self, source: SearchableTree, target: tk.Widget):
        super().__init__(source.tree, target)
        self._source_tree = source
        self._data_plots: list[FGPropertyNode] | list[CsvData] = []

    def _create_namelist_widget(self, master: tk.Widget, names: list[str]) -> tk.Widget:
        widget_preview = ttk.Frame(master, borderwidth=1)
        for idx, name in enumerate(names):
            if idx < 3:
                propname = ttk.Label(widget_preview, text=name, justify=tk.LEFT)
                propname.pack(anchor=tk.W)
            else:
                propname = ttk.Label(widget_preview, text="...", justify=tk.LEFT)
                propname.pack(anchor=tk.W)
                break
        return widget_preview

    def drop_on_target(self, _):
        assert isinstance(self.target, PlotsView)
        self.target.add_data(self._data_plots)


class DnDProperties(DnDTreeItems):
    def create_source_widget(self, master: tk.Widget) -> tk.Widget | None:
        assert isinstance(self._source_tree, PropertyTree)
        self._data_plots = self._source_tree.get_selected_properties()
        if self._data_plots:
            _, property_names = self._source_tree.get_unified_property_names(
                self._data_plots
            )
            return self._create_namelist_widget(
                master, [names[1] for names in property_names]
            )
        return None


class DnDCsvColumns(DnDTreeItems):
    def create_source_widget(self, master: tk.Widget) -> tk.Widget | None:
        assert isinstance(self._source_tree, CsvTree)
        self._data_plots = self._source_tree.get_selected_csv_columns()
        if self._data_plots:
            return self._create_namelist_widget(
                master, [col.name for col in self._data_plots]
            )
        return None
