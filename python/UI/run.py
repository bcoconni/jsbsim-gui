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
from tkinter import font, ttk
from tkinter.constants import EW, NS, NSEW, RAISED

from jsbsim import FGPropertyNode

from .hierarchical_tree import PropertyTree
from .source_editor import LabeledWidget


class DragNDropManager:
    def __init__(self, widget: tk.Widget):
        widget.bind("<ButtonPress-1>", self.select)
        widget.bind("<B1-Motion>", self.drag)
        widget.bind("<ButtonRelease-1>", self.drop)
        self.root = widget.winfo_toplevel()
        self.widget = widget
        self.offset_x = 0
        self.offset_y = 0
        self.snapshot: tk.Widget | None = None
        self.target: tk.Widget | None = None

    def select(self, event: tk.Event):
        root = self.root
        self.offset_x = root.winfo_rootx()
        self.offset_y = root.winfo_rooty()
        self.target = None

    def drag(self, event: tk.Event):
        if self.snapshot:
            x, y = event.widget.winfo_pointerxy()
            self.snapshot.place(x=x - self.offset_x, y=y - self.offset_y)

    def drop(self, event: tk.Event):
        if self.snapshot:
            x, y = event.widget.winfo_pointerxy()
            self.target = event.widget.winfo_containing(x, y)
            print(self.target)
            self.snapshot.destroy()
            self.snapshot = None


class DnDProperties(DragNDropManager):
    def __init__(self, widget: PropertyTree):
        super().__init__(widget.proptree.tree)
        self.property_tree = widget
        self.property_list: list[FGPropertyNode] = []

    def drag(self, event: tk.Event):
        if self.snapshot:
            super().drag(event)
        else:
            self.property_list = self.property_tree.get_selected_elements()
            if self.property_list:
                self.snapshot = tk.Frame(
                    self.root, padx=5, pady=5, borderwidth=1, relief=RAISED
                )
                for idx, prop in enumerate(self.property_list):
                    if idx < 3:
                        propname = ttk.Label(
                            self.snapshot,
                            text=prop.get_relative_name(),
                            justify=tk.LEFT,
                        )
                        propname.pack(anchor=tk.W)
                    else:
                        propname = ttk.Label(self.snapshot, text="...", justify=tk.LEFT)
                        propname.pack(anchor=tk.W)
                        break

                super().drag(event)


class Run(tk.Frame):
    def __init__(self, master: tk.Widget, width: int, height: int):
        super().__init__(master, width=width, height=height)
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

        DnDProperties(self.property_view.widget)

        # Window Layout
        plots_view.grid_columnconfigure(0, weight=1)
        plots_view.grid_rowconfigure(0, weight=1)
        plotsview_pos = plots_view.grid_info()
        self.grid_columnconfigure(plotsview_pos["column"], weight=1)
        self.grid_rowconfigure(plotsview_pos["row"], weight=1)

    def run_ic(self):
        self.master.controller.run_ic()
        self.property_view.widget.update_values()
