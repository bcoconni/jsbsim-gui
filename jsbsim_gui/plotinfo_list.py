# A Graphical User Interface for JSBSim
#
# Copyright (c) 2024-2026 Bertrand Coconnier
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

import copy
import math
import os
import platform
from abc import ABC, abstractmethod
from typing import Dict, Iterator, List, Set

import numpy as np
from jsbsim import FGPropertyNode

from .controller import Controller
from .csv_tree import CsvData


class PlotInfo(ABC):
    max_points = 256
    name: str
    line_style: str
    _data = np.empty((2, 0))

    @property
    @abstractmethod
    def default_name(self) -> str: ...

    @abstractmethod
    def get_data(self, t_min: float, t_max: float) -> np.ndarray: ...

    def t_max(self) -> float:
        return self._data[0, -1] if self._data.size else 0.0

    def refresh(self) -> None:
        pass

    def _get_sample(self, min_idx: int, max_idx: int, data: np.ndarray) -> np.ndarray:
        ndata = data.shape[1]
        if ndata:
            max_idx = max(max_idx, ndata - 1)
            assert 0 <= min_idx <= max_idx
            ratio = max((max_idx - min_idx) // self.max_points, 1)
            sample_data = data[:, min_idx:max_idx:ratio]
            # Make sure the last data point is included.
            if min_idx + (sample_data.size - 1) * ratio != max_idx:
                sample_data = np.column_stack((sample_data, data[:, max_idx]))
            return sample_data
        else:
            return data


class _CsvPlotInfo(PlotInfo):
    def __init__(self, csv_data: CsvData):
        self.csv_path = csv_data.path
        self._column_name = csv_data.name
        self.name = csv_data.name
        self.line_style = "--"
        self._data = np.empty((2, csv_data.data.size))
        self._data[0, :] = csv_data.time
        self._data[1, :] = csv_data.data

    @property
    def default_name(self) -> str:
        return self._column_name

    def get_data(self, t_min: float, t_max: float) -> np.ndarray:
        if not self._data.size:
            return np.array((2, 0))
        min_idx = max(0, int(np.searchsorted(self._data[0, :], t_min)) - 1)
        max_idx = self._data.shape[1] - 1
        if math.isfinite(t_max):
            max_idx = min(
                int(np.searchsorted(self._data[0, :], t_max, side="right")), max_idx
            )

        min_idx = min(min_idx, max_idx)
        return self._get_sample(min_idx, max_idx, self._data)


class _PropertyPlotInfo(PlotInfo):
    def __init__(self, node: FGPropertyNode, controller: Controller):
        self.node = node
        self.name = node.get_name()
        self._controller = controller
        self._dt = controller.dt
        self.line_style = "-"

    def __eq__(self, other) -> bool:
        return isinstance(other, _PropertyPlotInfo) and self.node == other.node

    @property
    def default_name(self) -> str:
        return self.node.get_name()

    def refresh(self) -> None:
        data = self._controller.get_property_log(self.node)
        ndata = data.size
        self._data = np.empty((2, ndata))
        self._data[0, :] = np.arange(ndata) * self._dt
        self._data[1, :] = data

    def get_data(self, t_min: float, t_max: float) -> np.ndarray:
        ndata = self._data.shape[1]
        if not ndata:
            return np.array((0, 2))
        min_idx = max(0, math.floor(t_min / self._dt)) if self._dt > 0 else 0
        max_idx = (
            min(math.ceil(t_max / self._dt), ndata - 1)
            if math.isfinite(t_max) and self._dt > 0
            else ndata - 1
        )
        return self._get_sample(min_idx, max_idx, self._data)


class PlotInfoList:
    def __init__(self, controller: Controller):
        self._controller = controller
        self._plotinfos: List[PlotInfo] = []

    def __deepcopy__(self, memo):
        plist_copy = PlotInfoList(self._controller)
        memo[id(plist_copy)] = plist_copy
        plist_copy._plotinfos = [copy.copy(plot_info) for plot_info in self._plotinfos]
        return plist_copy

    def __iter__(self) -> Iterator[PlotInfo]:
        return iter(self._plotinfos)

    def __len__(self) -> int:
        return len(self._plotinfos)

    def __getitem__(self, index: int) -> PlotInfo:
        return self._plotinfos[index]

    def _update_property_names(self) -> None:
        prop_infos = [p for p in self._plotinfos if isinstance(p, _PropertyPlotInfo)]
        if len(prop_infos) <= 1:
            for p in prop_infos:
                p.name = p.default_name
            return

        full_names = [p.node.get_fully_qualified_name() for p in prop_infos]
        common_root = os.path.commonpath(full_names)

        for p, fullname in zip(prop_infos, full_names):
            p.name = os.path.relpath(fullname, common_root)

            if platform.system() == "Windows":
                p.name = p.name.replace("\\", "/")

    def _update_csv_names(self) -> None:
        csv_infos = [p for p in self._plotinfos if isinstance(p, _CsvPlotInfo)]
        name_to_paths: Dict[str, Set[str]] = {}

        for p in csv_infos:
            name_to_paths.setdefault(p.default_name, set()).add(p.csv_path)

        for p in csv_infos:
            if len(name_to_paths[p.default_name]) > 1:
                csv_filename = os.path.basename(p.csv_path)
                p.name = f"{p.default_name} ({csv_filename})"
            else:
                p.name = p.default_name

    def t_max(self) -> float:
        return max((p.t_max() for p in self._plotinfos), default=0.0)

    def refresh(self) -> None:
        for pinfo in self._plotinfos:
            pinfo.refresh()

    def add_properties(self, props: List[FGPropertyNode]) -> None:
        if props:
            self._plotinfos.extend(
                [_PropertyPlotInfo(p, self._controller) for p in props]
            )
            self._update_property_names()

    def add_csv_columns(self, cols_data: List[CsvData]) -> None:
        if cols_data:
            self._plotinfos.extend([_CsvPlotInfo(data) for data in cols_data])
            self._update_csv_names()

    def pop(self, index: int) -> PlotInfo:
        prop = self._plotinfos.pop(index)
        if len(self._plotinfos) > 1:
            self._update_property_names()
            self._update_csv_names()
        else:
            for p in self._plotinfos:
                p.name = p.default_name
        return prop
