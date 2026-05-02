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

import tkinter as tk
from abc import ABC, abstractmethod
from enum import Enum, auto
from typing import List


class EditAction(Enum):
    UNDO = auto()
    REDO = auto()
    SELECT_ALL = auto()
    CUT = auto()
    COPY = auto()
    PASTE = auto()
    FIND = auto()


class Command(ABC):
    @abstractmethod
    def execute(self) -> None:
        pass

    @abstractmethod
    def undo(self) -> None:
        pass


class EditableFrame(tk.Frame):
    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self._undo_stack: List[Command] = []
        self._redo_stack: List[Command] = []

    def apply_edit_action(self, action: EditAction) -> None:
        if action == EditAction.UNDO:
            self.undo()
        elif action == EditAction.REDO:
            self.redo()

    def do(self, command: Command) -> None:
        command.execute()
        self._undo_stack.append(command)
        self._redo_stack.clear()

    def undo(self) -> None:
        if self._undo_stack:
            command = self._undo_stack.pop()
            command.undo()
            self._redo_stack.append(command)

    def redo(self) -> None:
        if self._redo_stack:
            command = self._redo_stack.pop()
            command.execute()
            self._undo_stack.append(command)
