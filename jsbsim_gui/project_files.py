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
from pathlib import Path
from typing import Callable

import ttkbootstrap as ttk

from .controller import Controller
from .file_state import FileState
from .hierarchical_tree import FileTree
from .widget import LabeledWidget


class ProjectFiles(LabeledWidget):
    def __init__(
        self,
        master: tk.Widget,
        controller: Controller,
        file_selected: Callable[[FileState], None],
        get_editor_content: Callable[[], str],
        invalid_file: Callable[[FileState, int, int], None],
        has_dirty_files: Callable[[bool], None],
        file_updated: Callable[[], None],
    ):
        super().__init__(master, "Project Files", True)
        self._controller = controller
        self._file_selected = file_selected
        self._get_editor_content = get_editor_content
        self._invalid_file = invalid_file
        self._has_dirty_files = has_dirty_files
        self._file_updated = file_updated
        self._file_states = self._load_file_states()
        filepath = controller.get_relative_path(controller.filename)
        self.current_file = self._file_states[filepath]
        self._fileview = FileTree(self, list(self._file_states))
        self._select_file(filepath)
        self._fileview.bind("<<TreeviewSelect>>", lambda _: self._show_file(), add="+")
        self.set_widget(self._fileview)

    def _load_file_states(self) -> dict[Path, FileState]:
        root_dir = self._controller.get_root_dir()
        file_states = {}
        for xml_tree in self._controller.get_xml_trees():
            file_states[xml_tree.filepath] = FileState(xml_tree, root_dir)
        return file_states

    def _show_file(self) -> None:
        paths = self._fileview.get_selected_items(True)
        if paths:
            file_state = self._file_states[Path(paths[0])]
            if file_state is not self.current_file:
                self.current_file.content = self._get_editor_content()
            self._file_selected(file_state)
            self.current_file = file_state

    def get_file_states(self) -> dict[Path, FileState]:
        return self._file_states

    def select_file(self, filepath: Path) -> None:
        self._select_file(filepath)
        self._show_file()

    def _select_file(self, filepath: Path) -> None:
        file_id = self._fileview.get_id_from_path(filepath)
        assert file_id is not None
        self._fileview.see(file_id)
        self._fileview.selection_set([file_id])

    def mark_current_modified(self, modified: bool) -> None:
        if modified and not self.current_file.is_modified:
            self.current_file.is_modified = True
            self._fileview.highlight_file(self.current_file.filepath)
            self._has_dirty_files(True)

    def has_modified_files(self) -> bool:
        return any(state.is_modified for state in self._file_states.values())

    def refresh_model(self) -> None:
        file_states = self._load_file_states()
        current_path = self.current_file.filepath
        if current_path not in file_states:
            current_path = self._controller.get_relative_path(self._controller.filename)
        self._file_states = file_states
        self.current_file = file_states[current_path]
        self._fileview.clear()
        self._fileview.create_tree_nodes(
            sorted(str(file_name) for file_name in file_states)
        )

    def save_file(self) -> bool:
        if not self.current_file.is_modified:
            return True

        self.current_file.content = self._get_editor_content()
        error = self.current_file.validate_xml()
        if error:
            self._invalid_file(self.current_file, *error)
            return False

        if self.current_file.write():
            self._fileview.clear_highlight(self.current_file.filepath)
            self._has_dirty_files(self.has_modified_files())
            self._file_updated()
            return True

        return False

    def save_all(self) -> bool:
        modified_files = [
            state for state in self._file_states.values() if state.is_modified
        ]
        if not modified_files:
            return True

        if self.current_file.is_modified:
            self.current_file.content = self._get_editor_content()

        for file_state in modified_files:
            error = file_state.validate_xml()
            if error:
                self._invalid_file(file_state, *error)
                return False

        for file_state in modified_files:
            if not file_state.write():
                ttk.Messagebox.show_error(
                    f'Could not save "{file_state.filepath}"', "Error"
                )
                return False
            self._fileview.clear_highlight(file_state.filepath)

        self._has_dirty_files(False)
        self._file_updated()
        return True

    def prompt_save_if_modified(self, message: str) -> bool:
        if self.has_modified_files():
            result = ttk.Messagebox.yesnocancel(message, "Unsaved Changes")
            if result is None or result == ttk.L("Cancel"):
                return False
            elif result == ttk.L("Yes"):
                if not self.save_all():
                    return False
        return True
