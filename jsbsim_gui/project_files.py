# A Graphical User Interface for JSBSim
#
# Copyright (c) 2023-2026 Bertrand Coconnier
#
# This program is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation; either version 3 of the License, or (at your option) any later
# version.

import os
import tkinter as tk
from tkinter.messagebox import askyesnocancel, showerror
from typing import Callable

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
        self._root_dir = controller.get_root_dir()
        self._file_selected = file_selected
        self._get_editor_content = get_editor_content
        self._invalid_file = invalid_file
        self._has_dirty_files = has_dirty_files
        self._file_updated = file_updated
        self._file_states = self._load_file_states()
        filepath = controller.get_relative_path(controller.filename)
        self.current_file = self._file_states[filepath]
        self._fileview = FileTree(self, list(self._file_states))
        self._fileview.bind_selection(self._bind_selection)
        self._fileview.bind("<ButtonRelease-1>", self._on_file_click, add="+")
        self.set_widget(self._fileview)

    def _load_file_states(self) -> dict[str, FileState]:
        file_states = {}
        for xml_tree in self._controller.get_xml_trees():
            for node in xml_tree:
                filepath = node.filepath
                if filepath not in file_states:
                    with open(
                        os.path.join(self._root_dir, filepath), encoding="utf-8"
                    ) as f:
                        contents = f.read()
                    if contents.endswith("\n"):
                        contents = contents[:-1]
                    file_states[filepath] = FileState(filepath, contents)
        return file_states

    def _bind_selection(self, filepath: str) -> None:
        file_state = self._file_states[filepath]
        self._file_selected(file_state)

    def _on_file_click(self, event: tk.Event) -> None:
        selected = self._fileview.selection()
        if selected and self._fileview.identify_row(event.y) == selected[0]:
            paths = self._fileview.get_selected_items(True)
            if paths:
                file_state = self._file_states[paths[0]]
                self._file_selected(file_state)

    def get_file_states(self) -> dict[str, FileState]:
        return self._file_states

    def get_file_state(self, filepath: str) -> FileState | None:
        return self._file_states.get(filepath)

    def select_file(self, file_state: FileState) -> None:
        if file_state is not self.current_file:
            self.current_file.content = self._get_editor_content()
            self.current_file = file_state

    def show_file(self, filepath: str) -> None:
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
        self._fileview.create_tree_nodes(sorted(file_states))

    def save_file(self) -> bool:
        if not self.current_file.is_modified:
            return True

        self.current_file.content = self._get_editor_content()
        error = self.current_file.validate_xml()
        if error:
            self._invalid_file(self.current_file, *error)
            return False

        if self.current_file.write(self._root_dir):
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
            if not file_state.write(self._root_dir):
                showerror("Error", message=f'Could not save "{file_state.filepath}"')
                return False
            self._fileview.clear_highlight(file_state.filepath)

        self._has_dirty_files(False)
        self._file_updated()
        return True

    def prompt_save_if_modified(self, message: str) -> bool:
        if self.has_modified_files():
            result = askyesnocancel("Unsaved Changes", message=message)
            if result is None:
                return False
            elif result:
                if not self.save_all():
                    return False
        return True
