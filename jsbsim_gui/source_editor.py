# A Graphical User Interface for JSBSim
#
# Copyright (c) 2023-2026 Bertrand Coconnier
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
from tkinter.constants import NONE, NSEW
from typing import Callable, Literal, Union

from .edit_actions import EditableFrame, EditAction
from .file_state import FileState
from .textview import XMLSourceCodeView
from .widget import LabeledWidget


class SourceEditor(EditableFrame):
    def __init__(
        self,
        master: tk.Widget,
        initial_file: FileState,
        file_opened: Callable[[FileState], None],
        file_modified: Callable[[bool], None],
    ):
        super().__init__(master)
        self._file_opened = file_opened
        self._current_path = initial_file.filepath
        self._codeview = LabeledWidget(self, self._current_path)
        self._editor = XMLSourceCodeView(
            self._codeview, initial_file.content, width=80, height=30, wrap=NONE
        )
        self._editor.bind_modified_text(file_modified)
        self._codeview.set_widget(self._editor)

        self._codeview.grid(column=0, row=0, sticky=NSEW)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

    def bind(
        self,
        sequence: str,
        func: Callable[[tk.Event], object],
        add: Union[bool, Literal["", "+"], None] = None,
    ) -> str:
        return self._editor.bind(sequence, func, add)

    def refresh_model(self, file_state: FileState) -> None:
        self._current_path = file_state.filepath
        self._codeview.set_label(file_state.filepath)
        assert isinstance(self._codeview.widget, XMLSourceCodeView)
        self._codeview.widget.new_content(file_state.content)

    def get_content(self) -> str:
        assert isinstance(self._codeview.widget, XMLSourceCodeView)
        return self._codeview.widget.get_content()

    def open_source_file(self, file_state: FileState) -> None:
        editor = self._codeview.widget
        assert isinstance(editor, XMLSourceCodeView)
        if file_state.filepath != self._current_path:
            self._codeview.set_label(file_state.filepath)
            editor.new_content(file_state.content)
            self._current_path = file_state.filepath

    def move_to(
        self, file_state: FileState, focus: bool, column: int, line: int
    ) -> None:
        self._file_opened(file_state)
        assert isinstance(self._codeview.widget, XMLSourceCodeView)
        editor: XMLSourceCodeView = self._codeview.widget
        editor.move_cursor(f"{line}.{column}", focus)

    def select_text(
        self, text: str, file_state: FileState, column: int, line: int
    ) -> None:
        self._file_opened(file_state)
        assert isinstance(self._codeview.widget, XMLSourceCodeView)
        editor: XMLSourceCodeView = self._codeview.widget
        editor.select_text(text, f"{line}.{column}")

    def apply_edit_action(self, action: EditAction) -> None:
        assert isinstance(self._codeview.widget, XMLSourceCodeView)
        editor = self._codeview.widget
        editor.focus_text()
        editor.apply_edit_action(action)
