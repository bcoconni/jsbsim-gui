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

import time
import tkinter as tk
from abc import ABC, abstractmethod
from tkinter import ttk
from tkinter.constants import EW, NS, NSEW
from tkinter.messagebox import showerror
from typing import Optional

from jsbsim import FGPropertyNode

from .controller import Controller
from .edit_actions import EditAction, EditableFrame
from .hierarchical_tree import PropertyTree
from .plots_view import PlotsView
from .source_editor import LabeledWidget
from .widget import widget_is_descendant


class DragNDropManager(ABC):
    def __init__(self, source: tk.Widget, target: tk.Widget):
        source.bind("<ButtonPress-1>", self.select, add=True)
        source.bind("<B1-Motion>", self.drag, add=True)
        source.bind("<ButtonRelease-1>", self.drop, add=True)
        self.offset_x = 0
        self.offset_y = 0
        self.dragged_widget_preview: Optional[tk.Widget] = None
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
    def drop_on_target(self, event: tk.Event):
        pass

    def drop(self, event: tk.Event):
        if self.dragged_widget_preview:
            self.dragged_widget_preview.destroy()
            self.dragged_widget_preview = None

            x, y = event.widget.winfo_pointerxy()
            target_widget = event.widget.winfo_containing(x, y)
            # If target_widget is a child of self.target, process the dragged widget
            if str(target_widget).startswith(str(self.target)):
                self.drop_on_target(event)


class DnDProperties(DragNDropManager):
    def __init__(self, source: PropertyTree, root: FGPropertyNode, target: tk.Widget):
        super().__init__(source.tree, target)
        self.property_tree = source
        self.property_list: list[FGPropertyNode] = []
        self._property_root = root

    def create_source_widget(self, master: tk.Widget) -> Optional[tk.Widget]:
        self.property_list = self.property_tree.get_selected_properties()
        if self.property_list:
            widget_preview = ttk.Frame(master, borderwidth=1)
            _, property_names = self.property_tree.get_unified_property_names(
                self._property_root, self.property_list
            )
            for idx, name in enumerate(property_names):
                if idx < 3:
                    propname = ttk.Label(
                        widget_preview,
                        text=name[1],
                        justify=tk.LEFT,
                    )
                    propname.pack(anchor=tk.W)
                else:
                    propname = ttk.Label(widget_preview, text="...", justify=tk.LEFT)
                    propname.pack(anchor=tk.W)
                    break
            return widget_preview
        return None

    def drop_on_target(self, _):
        self.target.add_properties(self.property_list)


class Run(EditableFrame):
    REALTIME_UPDATE_INTERVAL_ms = 200
    MAX_UPDATE_TIME_s = 0.95 * REALTIME_UPDATE_INTERVAL_ms / 1000

    def __init__(
        self, master: tk.Widget, controller: Controller, status_bar: ttk.Label, **kw
    ):
        super().__init__(master, **kw)
        self.property_view = LabeledWidget(self, "Property Explorer")
        root = controller.get_property_root()
        assert root is not None
        self.property_view.set_widget(
            PropertyTree(self.property_view, controller.get_property_list(), root)
        )
        self.property_view.widget.grid(sticky=NS)
        self.property_view.grid(column=0, row=0, sticky=NS)
        self.controller = controller
        self._status_bar = status_bar
        self.update_id = None
        self.initial_seconds = 0.0
        self.script_end_reached = False

        controls_frame = ttk.Frame(self)
        self.init_button = ttk.Button(
            controls_frame, text="Initialize", command=self.run_ic
        )
        self.init_button.grid(column=0, row=0, columnspan=3, sticky=EW, padx=5, pady=5)

        # Trim button
        self._trim_button = ttk.Button(
            controls_frame, text="Trim", command=self._trim, state=tk.DISABLED
        )
        self._trim_button.grid(column=0, row=1, sticky=EW, padx=5)
        self._trim_mode = tk.StringVar()
        self._trim_options = ttk.Combobox(
            controls_frame, textvariable=self._trim_mode, state=tk.DISABLED
        )
        self._trim_options["values"] = ["Full Trim", "Ground Trim"]
        self._trim_options.current(0)
        self._trim_options.grid(column=1, row=1, sticky=EW, padx=5)
        # Step button
        self.step_button = ttk.Button(
            controls_frame, text="Step", command=self.step, state=tk.DISABLED
        )
        self.step_button.grid(column=0, row=2, sticky=EW, padx=5, pady=5)
        button_pos = self._trim_button.grid_info()
        controls_frame.columnconfigure(button_pos["column"], weight=1)

        # Run/Pause button
        self.run_pause_button = ttk.Button(
            controls_frame, text="Run", command=self.run, state=tk.DISABLED
        )
        self.run_pause_button.grid(column=1, row=2, sticky=EW, padx=5, pady=5)
        button_pos = self._trim_options.grid_info()
        controls_frame.columnconfigure(button_pos["column"], weight=1)
        controls_frame.grid(column=0, row=1, sticky=EW)

        self.plots_view = PlotsView(self, controller)
        self.plots_view.grid(column=1, row=0, rowspan=3, sticky=NSEW)
        self.plots_view.bind_motion_handler(self.update_properties)

        self.dnd_properties = DnDProperties(
            self.property_view.widget, root, self.plots_view
        )

        # Window Layout
        plotsview_pos = self.plots_view.grid_info()
        self.grid_columnconfigure(plotsview_pos["column"], weight=1)
        self.grid_rowconfigure(plotsview_pos["row"], weight=1)

    def run_ic(self):
        self.controller.run_ic()
        self.property_view.widget.update_values()
        self.init_button.config(state=tk.DISABLED)
        self._trim_button.config(state=tk.NORMAL)
        self._trim_options.config(state="readonly")
        self.step_button.config(state=tk.NORMAL)
        self.run_pause_button.config(state=tk.NORMAL)

    def step(self):
        self.controller.run()
        self.property_view.widget.update_values()
        self.plots_view.update_plots()

    def update_plots(self) -> None:
        start_time = time.time()
        actual_elapsed_time = start_time - self.initial_seconds
        sim_time = self.controller.fdm.get_sim_time()
        sim_lag_time = actual_elapsed_time - sim_time

        for _ in range(int(sim_lag_time / self.controller.dt)):
            if not self.controller.run() and not self.script_end_reached:
                self.pause()
                self.script_end_reached = True
                break
            # If the update takes too long, break the loop
            if time.time() - start_time > self.MAX_UPDATE_TIME_s:
                self.update_id = self.after(
                    self.REALTIME_UPDATE_INTERVAL_ms, self.update_plots
                )
                break
        else:
            self.update_id = self.after(
                self.REALTIME_UPDATE_INTERVAL_ms, self.update_plots
            )

        self.property_view.widget.update_values()
        self.plots_view.update_plots()
        self._status_bar.config(text=f"Simulated time: {sim_time:.3f}s")

    def pause(self) -> None:
        self.after_cancel(self.update_id)
        self.update_id = None
        self.step_button.config(state=tk.NORMAL)
        self.run_pause_button.config(command=self.run, text="Run")

    def run(self) -> None:
        self.update_id = self.after(self.REALTIME_UPDATE_INTERVAL_ms, self.update_plots)
        self.initial_seconds = time.time() - self.controller.fdm.get_sim_time()
        self.step_button.config(state=tk.DISABLED)
        self.run_pause_button.config(command=self.pause, text="Pause")

    def _trim(self) -> None:
        if not self.controller.trim(self._trim_options.current() + 1):
            showerror("Error", message="Trim failed")
        else:
            self.update_properties(None)

    def update_properties(self, _) -> None:
        sim_time = self.plots_view.t_hover
        prop_view: PropertyTree = self.property_view.widget
        if sim_time:
            props = prop_view.get_visible_properties()
            values = self.controller.get_time_snapshot(sim_time, props)
            prop_view.update_values(values)
        else:
            prop_view.update_values()
            sim_time = self.controller.fdm.get_sim_time()

        self._status_bar.config(text=f"Simulated time: {sim_time:.3f}s")

    def apply_edit_action(self, action: EditAction) -> None:
        focused_widget = self.focus_get()
        if widget_is_descendant(focused_widget, self.property_view):
            self.property_view.apply_edit_action(action)

        self.plots_view.apply_edit_action(action)
