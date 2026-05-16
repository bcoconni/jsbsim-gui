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
from typing import Iterator, List, Optional, Tuple

import numpy as np
from jsbsim import FGPropertyNode

from .controller import Controller


class PlotInfo(ABC):
    max_points: int = 256
    name: str

    @property
    @abstractmethod
    def leaf_name(self) -> str: ...

    @abstractmethod
    def unique_path(self) -> str: ...

    @abstractmethod
    def t_max(self) -> float: ...

    @abstractmethod
    def get_data(self, t_min: float, t_max: float) -> Tuple[np.ndarray, np.ndarray]: ...

    def refresh(self) -> None:
        pass

    def _get_sample(self, min_idx: int, max_idx: int, data: np.ndarray) -> np.ndarray:
        ndata = data.size
        if ndata:
            max_idx = max(max_idx, ndata - 1)
            assert 0 <= min_idx <= max_idx
            ratio = max((max_idx - min_idx) // self.max_points, 1)
            sample_data = data[min_idx:max_idx:ratio]
            # Make sure the last data point is included.
            if min_idx + (sample_data.size - 1) * ratio != max_idx:
                sample_data = np.append(sample_data, data[max_idx])
            return sample_data
        else:
            return data


class PropertyPlotInfo(PlotInfo):
    def __init__(self, node: FGPropertyNode, name: str, controller: Controller):
        self.node = node
        self.name = name
        self._controller = controller
        self._data: np.ndarray = np.array([])
        self._dt: float = controller.dt

    def __eq__(self, other) -> bool:
        return (
            isinstance(other, PropertyPlotInfo)
            and self.node == other.node
            and self.name == other.name
        )

    @property
    def leaf_name(self) -> str:
        return self.node.get_name()

    def unique_path(self) -> str:
        return self.node.get_fully_qualified_name()

    def refresh(self) -> None:
        self._data = self._controller.get_property_log(self.node)

    def t_max(self) -> float:
        return (self._data.size - 1) * self._dt if self._data.size else 0.0

    def get_data(self, t_min: float, t_max: float) -> Tuple[np.ndarray, np.ndarray]:
        ndata = self._data.size
        if not ndata:
            return np.array([]), np.array([])
        t_full = np.arange(ndata) * self._dt
        min_idx = max(0, math.floor(t_min / self._dt)) if self._dt > 0 else 0
        max_idx = (
            min(math.ceil(t_max / self._dt), ndata - 1)
            if math.isfinite(t_max) and self._dt > 0
            else ndata - 1
        )
        return (
            self._get_sample(min_idx, max_idx, t_full),
            self._get_sample(min_idx, max_idx, self._data),
        )


class PlotInfoList:
    def __init__(
        self, controller: Controller, properties: Optional[List[FGPropertyNode]] = None
    ):
        self._controller = controller
        if properties:
            self._plotinfos: List[PlotInfo] = [
                PropertyPlotInfo(p, p.get_name(), controller) for p in properties
            ]
            if len(properties) > 1:
                self._update_unique_names()
        else:
            self._plotinfos = []

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

    def _update_unique_names(self) -> None:
        fully_qualified_names = [p.unique_path() for p in self._plotinfos]
        common_root = os.path.commonpath(fully_qualified_names)

        for p, fullname in zip(self._plotinfos, fully_qualified_names):
            p.name = os.path.relpath(fullname, common_root)

            if platform.system() == "Windows":
                p.name = p.name.replace("\\", "/")

    def t_max(self) -> float:
        return max((p.t_max() for p in self._plotinfos), default=0.0)

    def refresh(self) -> None:
        for pinfo in self._plotinfos:
            pinfo.refresh()

    def add_properties(self, props: List[FGPropertyNode]) -> None:
        if not props:
            return

        self._plotinfos.extend(
            [PropertyPlotInfo(p, p.get_name(), self._controller) for p in props]
        )
        if len(self._plotinfos) > 1:
            self._update_unique_names()

    def pop(self, index: int) -> PlotInfo:
        prop = self._plotinfos.pop(index)
        if len(self._plotinfos) > 1:
            self._update_unique_names()
        else:
            for p in self._plotinfos:
                p.name = p.leaf_name
        return prop
