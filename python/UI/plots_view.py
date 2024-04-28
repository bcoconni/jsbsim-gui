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

import math
import tkinter as tk
from tkinter import font, ttk
from typing import Any, List, Optional, Tuple

import matplotlib as mpl
import numpy as np
from jsbsim import FGPropertyNode
from matplotlib.backend_bases import KeyEvent, LocationEvent, MouseEvent
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from .controller import Controller


class SelectedLine:
    def __init__(self, figure: Figure, **props):
        self.ax_id: int | None = None
        self.line_id: int | None = None
        self.figure = figure
        self.pick_props = props
        self.orig_props: dict[str, Any] = {}

    def select(self, ax_id: int, line_id: int) -> None:
        self.deselect()
        self.ax_id = ax_id
        self.line_id = line_id
        line = self.figure.axes[ax_id].lines[line_id]
        for prop in self.pick_props:
            self.orig_props[prop] = mpl.artist.get(line, prop)
        line.set(**self.pick_props)

    def deselect(self) -> None:
        if self.ax_id is not None and self.line_id is not None:
            self.figure.axes[self.ax_id].lines[self.line_id].set(**self.orig_props)
        self.ax_id = None
        self.line_id = None

    def get_params(self) -> Optional[Tuple[int, int]]:
        if self.ax_id is not None and self.line_id is not None:
            return self.ax_id, self.line_id
        return None


class PlotsView(ttk.Frame):
    def __init__(self, master: tk.Widget, controller: Controller, **kw):
        super().__init__(master, **kw)
        self.controller = controller
        helper_font = font.Font(slant="italic")
        self.helper_message = ttk.Label(
            self,
            text="Drop properties to plot",
            anchor=tk.CENTER,
            foreground="gray",
            font=helper_font,
        )
        self.helper_message.pack(fill=tk.BOTH, expand=True)

        root = master.winfo_toplevel()
        pixels = root.winfo_screenwidth()
        width = root.winfo_screenmmwidth()
        self.dpi = 25.4 * pixels / width
        self.canvas: FigureCanvasTkAgg | None = None
        self.plots: list[list[FGPropertyNode]] = []
        self.bbox = None
        self.selected_line: SelectedLine | None = None

    def on_leave_figure(self, event: LocationEvent):
        for ax in event.canvas.figure.axes:
            ax.lines[-1].set_visible(False)
            for text in ax.texts:
                text.set_visible(False)

        self.reset_and_redraw()

    def on_click(self, event: MouseEvent):
        if event.inaxes:
            for ax_id, ax in enumerate(self.canvas.figure.axes):
                if ax == event.inaxes:
                    for line_id, line in enumerate(ax.lines[:-1]):
                        if line.contains(event)[0]:
                            self.selected_line.select(ax_id, line_id)
                            self.reset_and_redraw()
                            return

        self.selected_line.deselect()
        self.reset_and_redraw()

    def on_key_press(self, event: KeyEvent):
        if event.key == "delete":
            params = self.selected_line.get_params()
            if params:
                ax_id, line_id = params
                self.plots[ax_id].pop(line_id)
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
            dt = self.controller.dt
            step_id = int(event.xdata / dt)
            x0 = step_id * dt
            if event.xdata - x0 > dt / 2:
                step_id += 1
                x0 += dt
            ax0 = axes[0]
            text0 = ax0.texts[-1]
            text0.set_text(f"t={x0:.3f}s")
            text0.set_visible(True)
            w = text_bbox_size(text0, ax0)[0]
            ymin, ymax = ax0.get_ybound()
            text0.set_position((x0 - w / 2, ymax + 0.05 * (ymax - ymin)))
            offset = np.array([1, 1])

            for ax in axes:
                vline = ax.lines[-1]
                vline.set_visible(True)
                xmax = ax.get_xbound()[1]
                ymin, ymax = ax.get_ybound()
                vline.set_xdata([event.xdata, event.xdata])
                vline.set_ydata([ymin, ymax])

                for line_id, line in enumerate(ax.lines[:-1]):
                    ydata = line.get_ydata()
                    if len(ydata) > 1:
                        text = ax.texts[line_id]
                        y0 = ydata[step_id]
                        if np.isnan(y0):
                            text.set_visible(False)
                            continue
                        text.set_text(f"{y0:.5f}")
                        text.set_visible(True)
                        w, h = tuple(text_bbox_size(text, ax))
                        pos0 = ax.transData.transform((x0, y0))
                        pos1 = ax.transData.transform((x0 + w, y0 + h))
                        m = ax.transData.inverted()
                        pos0 = m.transform(pos0 - offset)
                        pos1 = m.transform(pos1 - offset)
                        x0, y0 = tuple(pos0)
                        w, h = tuple(pos1 - pos0)
                        if pos1[0] > xmax:
                            x0 -= w
                        if pos1[1] > ymax:
                            y0 -= h
                        text.set_position((x0, y0))
        else:
            for ax in axes:
                ax.lines[-1].set_visible(False)
                for text in ax.texts:
                    text.set_visible(False)

        self.on_draw(event)
        canvas.blit(canvas.figure.bbox)

    def on_draw(self, event):
        canvas = event.canvas

        if self.bbox:
            canvas.restore_region(self.bbox)
        else:
            self.bbox = canvas.copy_from_bbox(canvas.figure.bbox)

        for ax in canvas.figure.axes:
            ax.draw_artist(ax.lines[-1])
            for text in ax.texts:
                ax.draw_artist(text)

    def on_scroll(self, event: MouseEvent):
        ax0 = event.inaxes

        if ax0:
            xmin, xmax = ax0.get_xbound()
            dxl = event.xdata - xmin
            dxr = xmax - event.xdata
            factor = math.pow(1.5, -event.step)
            tmax = ax0.lines[0].get_xdata()[-1]
            xl = max(event.xdata - dxl * factor, 0.0)
            xr = min(event.xdata + dxr * factor, tmax)

            for ax in event.canvas.figure.axes:
                ax.set_xlim(xl, xr)

            self.reset_and_redraw()

    def add_properties(self, properties: List[FGPropertyNode], event: tk.Event):
        # Check if the properties are dropped on a subplot
        canvas = self.canvas
        target_ax_id: int | None = None
        if canvas:
            x, y = event.widget.winfo_pointerxy()
            tk_canvas = canvas.get_tk_widget()
            x -= tk_canvas.winfo_rootx()
            # Matplotlib y-axis is inverted: (0,0) is the bottom left corner while in
            # tkinter (0,0) is the top left corner
            y = tk_canvas.winfo_height() - (y - tk_canvas.winfo_rooty())
            target_ax = canvas.inaxes((x, y))
            if target_ax:
                for ax_id, ax in enumerate(canvas.figure.axes):
                    if ax == target_ax:
                        target_ax_id = ax_id
                        break

        if target_ax_id is None:
            self.plots.append(properties)
        else:
            self.plots[target_ax_id] += properties

        self.controller.log_properties(properties)
        self.initialize_canvas()

    def initialize_canvas(self):
        if self.helper_message:
            self.helper_message.destroy()
            self.helper_message = None

        if self.canvas:
            self.selected_line.deselect()
            self.canvas.figure.clear()
        else:
            self.canvas = FigureCanvasTkAgg(Figure(dpi=self.dpi), master=self)
            self.canvas.mpl_connect("draw_event", self.on_draw)
            self.canvas.mpl_connect("figure_leave_event", self.on_leave_figure)
            self.canvas.mpl_connect("motion_notify_event", self.on_move)
            self.canvas.mpl_connect("button_press_event", self.on_click)
            self.canvas.mpl_connect("key_press_event", self.on_key_press)
            self.canvas.mpl_connect("scroll_event", self.on_scroll)
            self.selected_line = SelectedLine(
                self.canvas.figure, linewidth=4, color="red"
            )
            self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        nplots = len(self.plots)
        prop0 = self.plots[0][0]
        values = self.controller.get_property_log(prop0)
        dt = self.controller.dt
        t = np.arange(0, len(values)) * dt
        w = self.winfo_width()
        h = self.winfo_height()
        figure = self.canvas.figure
        figure.set_size_inches(w / self.dpi, h / self.dpi)
        figure.subplots(nplots, 1, sharex=True)
        for plot_id, plots in enumerate(self.plots):
            ax = figure.axes[plot_id]
            # Plot the property history
            for idx, prop in enumerate(plots):
                color = f"C{idx%10}"
                ax.plot(
                    t,
                    self.controller.get_property_log(prop),
                    label=prop.get_name(),
                    color=color,
                )
                ax.text(0.0, 0.0, "0.0", color=color, visible=False, animated=True)
            # Cross hair
            ax.plot(
                [0.0, 0.0],
                [0.0, 0.0],
                color="0.0",
                linewidth=0.5,
                visible=False,
                animated=True,
            )
            # Figure decorations
            if len(plots) > 1:
                ax.legend()
            else:
                ax.set_ylabel(plots[0].get_name())
            ax.grid(True)
            ax.autoscale(enable=True, axis="y", tight=False)
            if len(t) > 1:
                ax.set_xlim(t[0], t[-1])
            else:
                ax.set_xlim(0, dt)

            if plot_id == nplots - 1:
                ax.set_xlabel("Time (s)")
        figure.axes[0].text(0.0, 0.0, "0.0", color="0.0", visible=False, animated=True)
        self.reset_and_redraw()

    def reset_and_redraw(self):
        self.bbox = None
        self.canvas.draw_idle()

    def update_plots(self):
        prop0 = self.plots[0][0]
        values = self.controller.get_property_log(prop0)
        ncol = len(values)
        axes = self.canvas.figure.axes

        if ncol > len(axes[0].lines[0].get_xdata()):
            t = np.arange(0, ncol) * self.controller.dt

            # Iterate over the plots and update the data
            for axe, plots in zip(axes, self.plots):
                for line, prop in zip(axe.lines[:-1], plots):
                    line.set_xdata(t)
                    line.set_ydata(self.controller.get_property_log(prop))
                axe.set_xlim(t[0], t[-1])
                axe.relim(True)
                axe.autoscale_view(scalex=False, scaley=True)
            self.reset_and_redraw()
