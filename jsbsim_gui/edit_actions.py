import tkinter as tk
from enum import Enum, auto


class EditAction(Enum):
    UNDO = auto()
    REDO = auto()
    SELECT_ALL = auto()
    CUT = auto()
    COPY = auto()
    PASTE = auto()


class EditableFrame(tk.Frame):
    def apply_edit_action(self, action: EditAction) -> None:
        pass
