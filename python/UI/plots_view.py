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
from typing import Any, List, Optional, Tuple

import matplotlib as mpl
import numpy as np
from jsbsim import FGPropertyNode
from matplotlib.backend_bases import KeyEvent, LocationEvent, MouseEvent
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure


class SelectedLine:
    def __init__(self, axes: List[mpl.axes.Axes], **props):
        self.ax_id = -1
        self.line_id = -1
        self.axes = axes
        self.pick_props = props
        self.orig_props: dict[str, Any] = {}

    def select(self, ax_id: int, line_id: int) -> None:
        self.deselect()
        self.ax_id = ax_id
        self.line_id = line_id
        line = self.axes[ax_id].lines[line_id]
        for prop in self.pick_props:
            self.orig_props[prop] = mpl.artist.get(line, prop)
        line.set(**self.pick_props)

    def deselect(self) -> None:
        if self.ax_id >= 0 and self.line_id >= 0:
            self.axes[self.ax_id].lines[self.line_id].set(**self.orig_props)
        self.ax_id = -1
        self.line_id = -1

    def get_params(self) -> Optional[Tuple[int, int]]:
        if self.ax_id >= 0 and self.line_id >= 0:
            return self.ax_id, self.line_id
        return None


class PlotsView(ttk.Frame):
    def __init__(self, master: tk.Widget, dt: float, **kw):
        super().__init__(master, **kw)
        self.dt = dt
        helper_font = font.Font(slant="italic")
        self.helper_message = ttk.Label(
            self,
            text="Drop properties to plot",
            anchor=tk.CENTER,
            foreground="gray",
            font=helper_font,
        )
        self.helper_message.pack(fill=tk.BOTH, expand=True)
        self.properties: list[FGPropertyNode] = []
        self.properties_values = np.empty((0, 0))

        root = master.winfo_toplevel()
        pixels = root.winfo_screenwidth()
        width = root.winfo_screenmmwidth()
        self.dpi = 25.4 * pixels / width
        self.canvas: FigureCanvasTkAgg | None = None
        self.plots: list[int] = []
        self.bbox = None
        self.selected_line: SelectedLine | None = None

    def on_enter_figure(self, event: LocationEvent):
        canvas = event.canvas
        params = self.selected_line.get_params()
        if params:
            self.selected_line.deselect()
            canvas.draw()
        self.bbox = canvas.copy_from_bbox(canvas.figure.bbox)
        if params:
            self.selected_line.select(*params)

    def on_leave_figure(self, event: LocationEvent):
        canvas = event.canvas
        axes = canvas.figure.axes

        axes[0].texts[1].set_visible(False)
        for ax in axes:
            ax.lines[0].set_visible(False)
            ax.texts[0].set_visible(False)

        canvas.draw()
        self.bbox = None

    def on_click(self, event: MouseEvent):
        axes = self.canvas.figure.axes

        if event.inaxes:
            for ax_id, ax in enumerate(axes):
                if ax == event.inaxes:
                    for line_id, line in enumerate(ax.lines[1:]):
                        if line.contains(event)[0]:
                            self.selected_line.select(ax_id, line_id + 1)
                            self.canvas_blit()
                            return

        self.selected_line.deselect()
        self.canvas_blit()

    def on_key_press(self, event: KeyEvent):
        if event.key == "delete":
            params = self.selected_line.get_params()
            if params:
                ax_id, line_id = params
                self.plots[ax_id].pop(line_id - 1)
                if not self.plots[ax_id]:
                    self.plots.pop(ax_id)
                self.selected_line.deselect()
                self.initialize_canvas()

    def on_move(self, event: MouseEvent):
        canvas = event.canvas
        axes = canvas.figure.axes

        def text_bbox_size(
            text: mpl.text.Text, axe: mpl.axes.Axes
        ) -> Tuple[float, float]:
            bbox = text.get_window_extent()
            m = axe.transData.inverted()
            pos0 = m.transform((bbox.x0, bbox.y0))
            pos1 = m.transform((bbox.x1, bbox.y1))
            return pos1 - pos0

        if event.inaxes:
            idx = int(event.xdata / self.dt)
            x0 = idx * self.dt
            if event.xdata - x0 > self.dt / 2:
                idx += 1
                x0 += self.dt
            ax0 = axes[0]
            text = ax0.texts[1]
            text.set_text(f"t={x0:.3f}s")
            text.set_visible(True)
            w = text_bbox_size(text, ax0)[0]
            ymin, ymax = ax0.get_ybound()
            text.set_position((x0 - w / 2, ymax + 0.05 * (ymax - ymin)))

            for ax in axes:
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
                    text = ax.texts[0]
                    if np.isnan(y0):
                        text.set_visible(False)
                        continue
                    text.set_text(f" {y0:.5f} ")
                    text.set_visible(True)
                    # text.set_position((x0, y0))
                    w, h = tuple(text_bbox_size(text, ax))
                    pos0 = ax.transData.transform((x0, y0))
                    pos1 = ax.transData.transform((x0 + w, y0 + h))
                    m = ax.transData.inverted()
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
            axes[0].texts[1].set_visible(False)
            for ax in axes:
                ax.lines[0].set_visible(False)
                ax.texts[0].set_visible(False)

        self.canvas_blit()

    def canvas_blit(self):
        canvas = self.canvas
        axes = canvas.figure.axes
        if self.bbox:
            canvas.restore_region(self.bbox)
            ax0 = axes[0]
            ax0.draw_artist(ax0.texts[1])
            for ax in axes:
                ax.draw_artist(ax.texts[0])
                for line in ax.lines:
                    ax.draw_artist(line)
            canvas.blit(canvas.figure.bbox)
        else:
            canvas.draw()
            self.bbox = canvas.copy_from_bbox(canvas.figure.bbox)

    def add_properties(self, properties: List[FGPropertyNode], _: tk.Widget):
        nrows, ncol = self.properties_values.shape
        nprops = len(properties)
        new_prop_values = np.full((nprops, max(ncol, 1)), np.nan)
        new_values = 0
        for prop in properties:
            if prop not in self.properties:
                self.properties.append(prop)
                new_prop_values[new_values, -1] = prop.get_double_value()
                self.plots.append([nrows + new_values])
                new_values += 1
            else:
                prop_id = self.properties.index(prop)
                self.plots.append([prop_id])

        if ncol > 0:
            if new_values > 0:
                self.properties_values = np.vstack(
                    (self.properties_values, new_prop_values[:new_values, :])
                )
        else:
            self.run_ic()

        self.initialize_canvas()

    def initialize_canvas(self):
        if self.helper_message:
            self.helper_message.destroy()
            self.helper_message = None

        if self.canvas:
            self.selected_line.deselect()
            self.canvas.get_tk_widget().pack_forget()
            self.canvas = None

        nplots = len(self.plots)
        t = np.arange(0.0, len(self.properties_values[0, :]) * self.dt, self.dt)
        w = self.winfo_width()
        h = self.winfo_height()
        fig = Figure(figsize=(w / self.dpi, h / self.dpi), dpi=self.dpi)
        for plot_id, plots in enumerate(self.plots):
            ax = fig.add_subplot(nplots, 1, plot_id + 1)
            # Cross hair
            v0 = self.properties_values[plots[0], 0]
            ax.plot([0.0, 0.0], [v0, v0], color="red", visible=False)
            ax.text(0.0, v0, f"{v0:.2f}", color="red", visible=False, fontweight="bold")
            if plot_id == 0:
                ax.text(0.0, v0, "0.0", color="red", visible=False, fontweight="bold")
            # Plot the property history
            for idx, prop_id in enumerate(plots):
                ax.plot(t, self.properties_values[prop_id, :], color=f"C{idx%10}")
            ax.set_ylabel(self.properties[plots[0]].get_name())
            ax.grid(True)
            ax.autoscale(enable=True, axis="y", tight=False)
            if len(t) > 1:
                ax.set_xlim(t[0], t[-1])
            else:
                ax.set_xlim(0, self.dt)
            # Hide the x-axis tick labels of all but the bottom subplot
            if plot_id < nplots - 1:
                ax.tick_params(labelbottom=False)
            else:
                ax.set_xlabel("Time (s)")
        self.canvas = FigureCanvasTkAgg(fig, master=self)
        self.canvas.mpl_connect("figure_enter_event", self.on_enter_figure)
        self.canvas.mpl_connect("figure_leave_event", self.on_leave_figure)
        self.canvas.mpl_connect("motion_notify_event", self.on_move)
        self.canvas.mpl_connect("button_press_event", self.on_click)
        self.canvas.mpl_connect("key_press_event", self.on_key_press)
        self.selected_line = SelectedLine(fig.axes, linewidth=4, color="red")
        self.reset_and_redraw()
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def reset_and_redraw(self):
        self.canvas.draw()
        self.bbox = None

    def run_ic(self):
        self.properties_values = np.array(
            [[prop.get_double_value() for prop in self.properties]]
        ).T

    def update_plots(self):
        col = np.array([[prop.get_double_value() for prop in self.properties]]).T
        self.properties_values = np.hstack((self.properties_values, col))

        axes = self.canvas.figure.axes
        t = axes[0].lines[1].get_xdata()
        t = np.append(t, t[-1] + self.dt)
        # Iterate over the plots and update the data
        for axe, plots in zip(axes, self.plots):
            for line, prop_id in zip(axe.lines[1:], plots):
                line.set_xdata(t)
                line.set_ydata(self.properties_values[prop_id, :])
            axe.set_xlim(t[0], t[-1])
            axe.relim()
            axe.autoscale_view()
        self.reset_and_redraw()
