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

import numpy as np
from jsbsim import FGPropertyNode
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

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
        self.target.add_properties(self.property_list, target)


class PlotsView(tk.Frame):
    def __init__(self, master: tk.Widget, **kw):
        super().__init__(master, **kw)
        helper_font = font.Font(slant="italic")
        self.helper_message = ttk.Label(
            self,
            text="Drop properties to plot",
            anchor=tk.CENTER,
            foreground="gray",
            font=helper_font,
        )
        self.helper_message.grid(column=0, row=0, sticky=EW)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.properties: list[FGPropertyNode] = []
        self.properties_values = np.empty((0, 0))

        root = master.winfo_toplevel()
        pixels = root.winfo_screenwidth()
        width = root.winfo_screenmmwidth()
        self.dpi = 25.4 * pixels / width
        self.canvas: FigureCanvasTkAgg | None = None
        self.plots = []
        self.bbox = None

    def on_enter_figure(self, event):
        canvas = event.canvas
        self.bbox = canvas.copy_from_bbox(canvas.figure.bbox)

    def on_leave_figure(self, _):
        self.bbox = None

    def on_move(self, event):
        canvas = event.canvas
        figure = canvas.figure

        if event.inaxes:
            dt = self.master.master.controller.dt
            idx = int(event.xdata / dt)
            x0 = idx * dt
            if event.xdata - x0 > dt / 2:
                idx += 1
                x0 += dt
            ax = figure.axes[0]
            text = ax.texts[1]
            text.set_text(f"t={x0:.3f}s")
            text.set_visible(True)
            bbox = text.get_window_extent()
            m = ax.transData.inverted()
            pos0 = m.transform((bbox.x0, bbox.y0))
            pos1 = m.transform((bbox.x1, bbox.y1))
            w = (pos1 - pos0)[0]
            ymin, ymax = ax.get_ybound()
            text.set_position((x0 - w / 2, ymax + 0.05 * (ymax - ymin)))

            for ax in figure.axes:
                vline = ax.lines[0]
                vline.set_visible(True)
                xmax = ax.get_xbound()[1]
                ymin, ymax = ax.get_ybound()
                vline.set_xdata([event.xdata, event.xdata])
                vline.set_ydata([ymin, ymax])

                ydata = ax.lines[1].get_ydata()
                if len(ydata) > 1:
                    offset = np.array([0, 1])
                    y0 = ydata[idx]
                    if np.isnan(y0):
                        continue
                    text = ax.texts[0]
                    text.set_text(f" {y0:.5f} ")
                    text.set_visible(True)
                    text.set_position((x0, y0))
                    bbox = text.get_window_extent()
                    m = ax.transData.inverted()
                    pos0 = m.transform((bbox.x0, bbox.y0))
                    pos1 = m.transform((bbox.x1, bbox.y1))
                    w, h = tuple(pos1 - pos0)
                    pos0 = ax.transData.transform((x0, y0))
                    pos1 = ax.transData.transform((x0 + w, y0 + h))
                    pos0 = m.transform(pos0 - offset)
                    pos1 = m.transform(pos1 + offset)
                    x0, y0 = tuple(pos0)
                    w, h = tuple(pos1 - pos0)
                    if pos1[0] > xmax:
                        x0 -= w
                    if pos1[1] > ymax:
                        y0 -= h
                    text.set_position((x0, y0))
        else:
            figure.axes[0].texts[1].set_visible(False)
            for ax in figure.axes:
                ax.lines[0].set_visible(False)
                ax.texts[0].set_visible(False)

        if self.bbox:
            canvas.restore_region(self.bbox)
            ax0 = figure.axes[0]
            ax0.draw_artist(ax0.texts[1])
            for ax in figure.axes:
                ax.draw_artist(ax.texts[0])
                for line in ax.lines:
                    ax.draw_artist(line)
            canvas.blit(canvas.figure.bbox)
        else:
            canvas.draw()
            self.bbox = canvas.copy_from_bbox(canvas.figure.bbox)

    def add_properties(self, properties: list[FGPropertyNode], target: tk.Widget):
        nrows, ncol = self.properties_values.shape
        nprops = len(properties)
        rows = np.full((nprops, max(ncol, 1)), np.nan)
        for idx, prop in enumerate(properties):
            if prop not in self.properties:
                self.properties.append(prop)
                rows[idx, -1] = prop.get_double_value()
                self.plots.append(nrows + idx)

        if ncol > 0:
            self.properties_values = np.vstack((self.properties_values, rows))
        else:
            self.run_ic()

        if self.helper_message:
            self.helper_message.destroy()
            self.helper_message = None

        if self.canvas:
            self.canvas.get_tk_widget().grid_forget()
            self.canvas = None

        dt = self.master.master.controller.dt
        t = np.arange(0.0, len(self.properties_values[0, :]) * dt, dt)
        w = self.winfo_width()
        h = self.winfo_height()
        fig = Figure(figsize=(w / self.dpi, h / self.dpi), dpi=self.dpi)
        for row, idx in enumerate(self.plots):
            ax = fig.add_subplot(nprops + nrows, 1, row + 1)
            # Cross hair
            v0 = self.properties_values[idx, 0]
            ax.plot([0.0, 0.0], [v0, v0], color="red", visible=False)
            ax.text(0.0, v0, f"{v0:.2f}", color="red", visible=False, fontweight="bold")
            if idx == 0:
                ax.text(0.0, v0, "0.0", color="red", visible=False, fontweight="bold")
            # Plot the data
            ax.plot(t, self.properties_values[idx, :], color="C0")
            ax.set_ylabel(self.properties[idx].get_name())
            ax.grid(True)
            ax.autoscale(enable=True, axis="y", tight=False)
            if len(t) > 1:
                ax.set_xlim(t[0], t[-1])
            else:
                ax.set_xlim(0, dt)
            # Hide the x-axis tick labels of all but the bottom subplot
            if row < nprops + nrows - 1:
                ax.tick_params(labelbottom=False)
            else:
                ax.set_xlabel("Time (s)")
        self.canvas = FigureCanvasTkAgg(fig, master=self)
        self.canvas.mpl_connect("figure_enter_event", self.on_enter_figure)
        self.canvas.mpl_connect("figure_leave_event", self.on_leave_figure)
        self.canvas.mpl_connect("motion_notify_event", self.on_move)
        self.canvas.draw()
        self.canvas.get_tk_widget().grid(column=0, row=0, sticky=NSEW)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

    def run_ic(self):
        self.properties_values = np.array(
            [[prop.get_double_value() for prop in self.properties]]
        ).T

    def update_values(self):
        col = np.array([[prop.get_double_value() for prop in self.properties]]).T
        self.properties_values = np.hstack((self.properties_values, col))
        figure = self.canvas.figure
        t = figure.axes[0].lines[1].get_xdata()
        t = np.append(t, t[-1] + self.master.master.controller.dt)
        # Iterate over the plots and update the data
        for idx, plot in enumerate(self.plots):
            axe = figure.axes[idx]
            axe.lines[1].set_xdata(t)
            axe.lines[1].set_ydata(self.properties_values[plot, :])
            axe.set_xlim(t[0], t[-1])
            axe.relim()
            axe.autoscale_view()
        self.canvas.draw()


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
        button = ttk.Button(controls_frame, text="Step", command=self.step)
        button.grid(column=0, row=1, sticky=EW, padx=5, pady=5)
        button_pos = button.grid_info()
        controls_frame.columnconfigure(button_pos["column"], weight=1)
        button = ttk.Button(controls_frame, text="Run")
        button.grid(column=1, row=1, sticky=EW, padx=5, pady=5)
        button_pos = button.grid_info()
        controls_frame.columnconfigure(button_pos["column"], weight=1)
        button = ttk.Button(controls_frame, text="Pause")
        button.grid(column=2, row=1, sticky=EW, padx=5, pady=5)
        button_pos = button.grid_info()
        controls_frame.columnconfigure(button_pos["column"], weight=1)
        controls_frame.grid(column=0, row=1, sticky=EW)

        self.plots_view = PlotsView(self)
        self.plots_view.grid(column=1, row=0, rowspan=3, sticky=NSEW)

        DnDProperties(self.property_view.widget, self.plots_view)

        # Window Layout
        plotsview_pos = self.plots_view.grid_info()
        self.grid_columnconfigure(plotsview_pos["column"], weight=1)
        self.grid_rowconfigure(plotsview_pos["row"], weight=1)

    def run_ic(self):
        self.master.controller.run_ic()
        self.property_view.widget.update_values()
        self.plots_view.run_ic()

    def step(self):
        self.master.controller.run()
        self.property_view.widget.update_values()
        self.plots_view.update_values()
