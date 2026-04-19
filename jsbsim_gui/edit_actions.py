from enum import Enum, auto


class EditAction(Enum):
    UNDO = auto()
    REDO = auto()
    SELECT_ALL = auto()
    CUT = auto()
    COPY = auto()
    PASTE = auto()
