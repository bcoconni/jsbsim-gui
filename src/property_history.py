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

from typing import List

import numpy as np
from jsbsim import FGPropertyNode


class PropertyHistory:
    CHUNK_SIZE = 100

    def __init__(self, properties: List[FGPropertyNode]):
        self.properties: List[FGPropertyNode] = properties
        self.history = [np.full((len(properties), self.CHUNK_SIZE), np.nan)]
        self.step = 0

    def record(self) -> None:
        chunk = self.history[-1]
        for i, prop in enumerate(self.properties):
            chunk[i, self.step] = prop.get_double_value()

        self.step += 1
        if self.step == self.CHUNK_SIZE:
            self.history.append(
                np.full((len(self.properties), self.CHUNK_SIZE), np.nan)
            )
            self.step = 0

    def get_property_history(self, prop: FGPropertyNode) -> np.ndarray:
        index = self.properties.index(prop)
        n_full_chunks = len(self.history) - 1
        size = n_full_chunks * self.CHUNK_SIZE + self.step
        property_history = np.empty(size)
        chunk_first_index = 0

        for chunk in self.history[:-1]:
            property_history[
                chunk_first_index : chunk_first_index + self.CHUNK_SIZE
            ] = chunk[index]
            chunk_first_index += self.CHUNK_SIZE

        property_history[chunk_first_index : chunk_first_index + self.step] = (
            self.history[-1][index, : self.step]
        )

        return property_history
