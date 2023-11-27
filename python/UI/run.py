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
from tkinter import ttk, font
from tkinter.constants import EW, NS, NSEW

from .hierarchical_tree import PropertyTree
from .source_editor import LabeledWidget


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
        button.grid(column=0, row=0, columnspan=3, sticky=EW, padx = 5, pady=5)
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
        plots_view.grid_columnconfigure(0, weight=1)
        plots_view.grid_rowconfigure(0, weight=1)
        plotsview_pos = plots_view.grid_info()
        self.grid_columnconfigure(plotsview_pos["column"], weight=1)
        self.grid_rowconfigure(plotsview_pos["row"], weight=1)

    def run_ic(self):
        self.master.controller.run_ic()
        self.property_view.widget.update_values()
