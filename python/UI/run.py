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
from abc import ABC, abstractmethod
from tkinter import font, ttk
from tkinter.constants import EW, NS, NSEW, RAISED

from jsbsim import FGPropertyNode

from .hierarchical_tree import PropertyTree
from .source_editor import LabeledWidget


class DragNDropManager(ABC):
    def __init__(self, source: tk.Widget, target: tk.Widget):
        source.bind("<ButtonPress-1>", self.select)
        source.bind("<B1-Motion>", self.drag)
        source.bind("<ButtonRelease-1>", self.drop)
        self.offset_x = 0
        self.offset_y = 0
        self.dragged_widget_preview: tk.Widget | None = None
        self.target = target

    def select(self, event: tk.Event):
        root = event.widget.winfo_toplevel()
        self.offset_x = root.winfo_rootx()
        self.offset_y = root.winfo_rooty()

    @abstractmethod
    def create_source_widget(self, master: tk.Widget) -> tk.Widget:
        pass

    def drag(self, event: tk.Event):
        if not self.dragged_widget_preview:
            root = event.widget.winfo_toplevel()
            self.dragged_widget_preview = self.create_source_widget(root)

        if self.dragged_widget_preview:
            x, y = event.widget.winfo_pointerxy()
            self.dragged_widget_preview.place(x=x - self.offset_x, y=y - self.offset_y)

    @abstractmethod
    def drop_on_target(self, target: tk.Widget):
        pass

    def drop(self, event: tk.Event):
        if self.dragged_widget_preview:
            self.dragged_widget_preview.destroy()
            self.dragged_widget_preview = None

            x, y = event.widget.winfo_pointerxy()
            target_widget = event.widget.winfo_containing(x, y)
            # If target_widget is a child of self.target, process the dragged widget
            if str(target_widget).startswith(str(self.target)):
                self.drop_on_target(target_widget)


class DnDProperties(DragNDropManager):
    def __init__(self, source: PropertyTree, target: tk.Widget):
        super().__init__(source.proptree.tree, target)
        self.property_tree = source
        self.property_list: list[FGPropertyNode] = []

    def create_source_widget(self, master: tk.Widget) -> tk.Widget:
        self.property_list = self.property_tree.get_selected_elements()
        if self.property_list:
            widget_preview = tk.Frame(
                master, padx=5, pady=5, borderwidth=1, relief=RAISED
            )
            for idx, prop in enumerate(self.property_list):
                if idx < 3:
                    propname = ttk.Label(
                        widget_preview,
                        text=prop.get_relative_name(),
                        justify=tk.LEFT,
                    )
                    propname.pack(anchor=tk.W)
                else:
                    propname = ttk.Label(widget_preview, text="...", justify=tk.LEFT)
                    propname.pack(anchor=tk.W)
                    break
            return widget_preview
        return None

    def drop_on_target(self, target: tk.Widget):
        print(f"Dropped on {target}")


class Run(tk.Frame):
    def __init__(self, master: tk.Widget, **kw):
        super().__init__(master, **kw)
        self.property_view = LabeledWidget(self, "Property List")
        self.property_view.set_widget(
            PropertyTree(self.property_view, master.controller.get_property_list())
        )
        self.property_view.widget.grid(sticky=NS)
        self.property_view.grid(column=0, row=0, sticky=NS)

        controls_frame = tk.Frame(self)
        button = ttk.Button(controls_frame, text="Initialize", command=self.run_ic)
        button.grid(column=0, row=0, columnspan=3, sticky=EW, padx=5, pady=5)
        button = ttk.Button(controls_frame, text="Run")
        button.grid(column=0, row=1, sticky=EW, padx=5, pady=5)
        button_pos = button.grid_info()
        controls_frame.columnconfigure(button_pos["column"], weight=1)
        button = ttk.Button(controls_frame, text="Step")
        button.grid(column=1, row=1, sticky=EW, padx=5, pady=5)
        button_pos = button.grid_info()
        controls_frame.columnconfigure(button_pos["column"], weight=1)
        button = ttk.Button(controls_frame, text="Pause")
        button.grid(column=2, row=1, sticky=EW, padx=5, pady=5)
        button_pos = button.grid_info()
        controls_frame.columnconfigure(button_pos["column"], weight=1)
        controls_frame.grid(column=0, row=1, sticky=EW)

        plots_view = tk.Frame(self)
        plots_view.grid(column=1, row=0, rowspan=3, sticky=NSEW)
        helper_font = font.Font(slant="italic")
        helper_message = ttk.Label(
            plots_view,
            text="Drop properties to plot",
            anchor=tk.CENTER,
            foreground="gray",
            font=helper_font,
        )
        helper_message.grid(column=0, row=0, sticky=EW)

        DnDProperties(self.property_view.widget, plots_view)

        # Window Layout
        plots_view.grid_columnconfigure(0, weight=1)
        plots_view.grid_rowconfigure(0, weight=1)
        plotsview_pos = plots_view.grid_info()
        self.grid_columnconfigure(plotsview_pos["column"], weight=1)
        self.grid_rowconfigure(plotsview_pos["row"], weight=1)

    def run_ic(self):
        self.master.controller.run_ic()
        self.property_view.widget.update_values()
