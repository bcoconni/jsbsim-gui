# A Graphical User Interface for JSBSim
#
# Copyright (c) 2024 Bertrand Coconnier
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

import os
import platform
from dataclasses import dataclass
from typing import List, Iterable, Optional

from jsbsim import FGPropertyNode


@dataclass
class PlotInfo:
    node: FGPropertyNode
    name: str


class PlotInfoList:
    def __init__(self, properties: Optional[List[FGPropertyNode]] = None):
        if properties:
            self.plotinfos: List[PlotInfo] = [
                PlotInfo(p, p.get_name()) for p in properties
            ]
            if len(properties) > 1:
                self._update_unique_names()
        else:
            self.plotinfos = []

    def __iter__(self) -> Iterable[PlotInfo]:
        return iter(self.plotinfos)

    def __len__(self) -> int:
        return len(self.plotinfos)

    def __getitem__(self, index: int) -> PlotInfo:
        return self.plotinfos[index]

    def _update_unique_names(self) -> None:
        fully_qualified_names = [
            p.node.get_fully_qualified_name() for p in self.plotinfos
        ]
        common_root = os.path.commonpath(fully_qualified_names)

        for p in self.plotinfos:
            p.name = os.path.relpath(p.node.get_fully_qualified_name(), common_root)

            if platform.system() == "Windows":
                p.name = p.name.replace("\\", "/")

    def add_properties(self, props: List[FGPropertyNode]) -> None:
        if not props:
            return

        self.plotinfos.extend([PlotInfo(p, p.get_name()) for p in props])
        if len(self.plotinfos) > 1:
            self._update_unique_names()

    def pop(self, index: int) -> FGPropertyNode:
        prop = self.plotinfos.pop(index)
        if len(self.plotinfos) > 1:
            self._update_unique_names()
        else:
            for p in self.plotinfos:
                p.name = p.node.get_name()
        return prop.node
