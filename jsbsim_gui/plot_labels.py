# A Graphical User Interface for JSBSim
#
# Copyright (c) 2026 Bertrand Coconnier
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

from typing import List, Optional, Tuple

import numpy as np
from matplotlib.axes import Axes
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.lines import Line2D
from matplotlib.transforms import Bbox, Transform


class PlotLabel:
    PADDING_PIXELS = 5

    def __init__(
        self, canvas: FigureCanvasTkAgg, ax: Axes, line: Optional[Line2D], color: str
    ):
        self._canvas = canvas
        self._ax = ax
        self._line = line
        self._text = canvas.figure.text(
            0.0, 0.0, "0.0", color=color, visible=False, animated=True
        )

        if line is not None:
            self._text.set_bbox(
                {"boxstyle": "round,pad=0.3", "ec": color, "alpha": 0.8, "fc": "white"}
            )

        self.bounding_box = self._get_current_mpl_bbox()

    # Bounding box coordinates are only updated during the drawing operation
    # WARNING: calls to `set_position` DO NOT update the bounding box position !
    def _get_current_mpl_bbox(self) -> Bbox:
        renderer = self._canvas.get_renderer()
        patch = self._text.get_bbox_patch()
        if patch is None:
            return self._text.get_window_extent(renderer)
        else:
            return patch.get_window_extent(renderer)

    # Manually update the bounding box position
    def _update_bounding_box(
        self, bbox_px: Bbox, pos0_px: np.ndarray, pos_px: Tuple[float, float]
    ) -> None:
        delta_pos_px = pos_px - pos0_px
        bbox_xy0 = [bbox_px.x0, bbox_px.y0] + delta_pos_px
        bbox_xy1 = [bbox_px.x1, bbox_px.y1] + delta_pos_px
        self.bounding_box = Bbox([list(bbox_xy0), list(bbox_xy1)])

    def update_time_position(self, t: float, m_figure: Transform) -> None:
        xdata: np.ndarray = self._ax.lines[0].get_xdata(True)
        if xdata.size > 1:
            self._text.set_text(f"t={t:.3f}s")
            self._text.set_visible(True)
            bbox_px = self._get_current_mpl_bbox()
            pos0_fig = self._text.get_position()
            pos0_px = self._canvas.figure.transFigure.transform(pos0_fig)
            bbox_width_px = bbox_px.x1 - bbox_px.x0
            _, ymax = self._ax.get_ybound()
            t_px, ymax_px = self._ax.transData.transform((t, ymax))
            pos_px = (t_px - bbox_width_px / 2, ymax_px + self.PADDING_PIXELS)
            self._update_bounding_box(bbox_px, pos0_px, pos_px)
            pos_fig = m_figure.transform(pos_px)
            self._text.set_position((pos_fig[0], pos_fig[1]))

    def update_position(self, t: float, m_figure: Transform) -> None:
        assert self._line is not None
        ydata: np.ndarray = self._line.get_ydata(True)
        if ydata.size > 1:
            xdata: np.ndarray = self._line.get_xdata(True)
            idx = min(np.searchsorted(xdata, t), ydata.size - 1)
            y0 = ydata[idx]
            if np.isnan(y0):
                self._text.set_visible(False)
                return

            self._text.set_text(f"{y0:.5f}")
            self._text.set_visible(True)
            bbox_px = self._get_current_mpl_bbox()
            pos0_fig = self._text.get_position()
            pos0_px = self._canvas.figure.transFigure.transform(pos0_fig)
            bbox_padding_px = pos0_px - (bbox_px.x0, bbox_px.y0)
            data_px = self._ax.transData.transform((t, y0))
            pos_px = tuple(data_px + bbox_padding_px + self.PADDING_PIXELS)
            self._update_bounding_box(bbox_px, pos0_px, pos_px)
            pos_fig = m_figure.transform(pos_px)
            self._text.set_position(tuple(pos_fig))

    def translate(self, delta: np.ndarray) -> None:
        pos_fig = self._text.get_position()
        self._text.set_position(tuple(delta + pos_fig))

    def hide(self) -> None:
        self._text.set_visible(False)

    def draw(self) -> None:
        self._canvas.figure.draw_artist(self._text)


class PlotLabelManager:
    PADDING_PIXELS = 3

    def __init__(self, canvas: FigureCanvasTkAgg):
        self._canvas = canvas
        self._labels: List[PlotLabel] = []

    def create_labels(self, axes: List[Axes]) -> None:
        time_label = PlotLabel(self._canvas, axes[0], None, color="0.0")
        self._labels = [time_label]

        for ax in axes:
            for idx, line in enumerate(ax.lines[:-1]):
                label = PlotLabel(self._canvas, ax, line, color=f"C{idx%10}")
                self._labels.append(label)

    def update_positions(self, t: float) -> None:
        m_figure = self._canvas.figure.transFigure.inverted()
        self._labels[0].update_time_position(t, m_figure)

        for label in self._labels[1:]:
            label.update_position(t, m_figure)

        # Prevent overlap/collision between labels
        bounding_boxes = [(label, label.bounding_box) for label in self._labels]
        sorted_boxes = sorted(bounding_boxes, key=lambda b: b[1].y1, reverse=True)

        _, prev_box = sorted_boxes[0]
        for label, box in sorted_boxes[1:]:
            prev_bottom = prev_box.y0 - self.PADDING_PIXELS
            box_top = box.y1

            if box_top > prev_bottom:
                shift_px = prev_bottom - box_top
                shift_fig = m_figure.transform((0, shift_px))
                label.translate(shift_fig)
                prev_box = Bbox(
                    [[box.x0, box.y0 + shift_px], [box.x1, box.y1 + shift_px]]
                )
            else:
                prev_box = box

    def hide_labels(self) -> None:
        for label in self._labels:
            label.hide()

    def draw_labels(self) -> None:
        for label in self._labels:
            label.draw()
