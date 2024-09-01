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
from typing import List, Iterable, Optional, Tuple

from jsbsim import FGPropertyNode


class PropertyList:
    def __init__(self, properties: Optional[List[FGPropertyNode]] = None):
        if properties:
            self.properties: List[FGPropertyNode] = properties.copy()
            if len(properties) > 1:
                self._update_unique_names()
            else:
                self.unique_names = [properties[0].get_name()]
        else:
            self.properties = []
            self.unique_names: List[str] = []

    def __iter__(self) -> Iterable[Tuple[str, FGPropertyNode]]:
        return zip(self.unique_names, self.properties)

    def __len__(self) -> int:
        return len(self.properties)

    def __getitem__(self, index: int) -> Tuple[str, FGPropertyNode]:
        return self.unique_names[index], self.properties[index]

    def _update_unique_names(self) -> None:
        fully_qualified_names = [p.get_fully_qualified_name() for p in self.properties]
        common_root = os.path.commonpath(fully_qualified_names)
        self.unique_names = [
            os.path.relpath(name, common_root) for name in fully_qualified_names
        ]

        if platform.system() == "Windows":
            self.unique_names = [name.replace("\\", "/") for name in self.unique_names]

    def add_properties(self, props: List[FGPropertyNode]) -> None:
        if not props:
            return

        self.properties.extend(props)
        if len(self.properties) > 1:
            self._update_unique_names()
        else:
            self.unique_names.append(props[0].get_name())

    def pop(self, index: int) -> FGPropertyNode:
        prop = self.properties.pop(index)
        if len(self.properties) > 1:
            self._update_unique_names()
        else:
            self.unique_names = [p.get_name() for p in self.properties]
        return prop
