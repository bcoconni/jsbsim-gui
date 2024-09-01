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
from typing import List

from jsbsim import FGPropertyNode


class PropertyList:
    def __init__(self):
        self.properties: List[FGPropertyNode] = []
        self.unique_names: List[str] = []

    def add_property(self, prop: FGPropertyNode) -> None:
        self.properties.append(prop)

        if len(self.properties) > 1:
            fully_qualified_names = [
                p.get_fully_qualified_name() for p in self.properties
            ]
            common_root = os.path.commonpath(fully_qualified_names)
            self.unique_names = [
                os.path.relpath(name, common_root) for name in fully_qualified_names
            ]
        else:
            self.unique_names.append(prop.get_name())

    def __iter__(self):
        return zip(self.unique_names, self.properties)
