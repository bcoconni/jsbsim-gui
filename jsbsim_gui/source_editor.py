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

import os
import tkinter as tk
from tkinter import ttk
from tkinter.constants import NONE, NS, NSEW
from typing import Dict, List, Optional

from .controller import Controller
from .edit_actions import EditableFrame, EditAction
from .file_state import FileState
from .find import FindWindow
from .hierarchical_tree import FileTree, PropertyTree
from .textview import XMLSourceCodeView


class LabeledWidget(EditableFrame):
    def __init__(self, master: tk.Widget, label: str):
        super().__init__(master)
        self.widget: Optional[EditableFrame] = None
        self.header_frame = ttk.Frame(self)
        self.header_frame.grid(column=0, row=0, sticky="ew", pady=5, padx=5)
        self.label = ttk.Label(self.header_frame, text=label, anchor="center")
        self.label.grid(column=0, row=0, sticky="ew")
        self.header_frame.columnconfigure(0, weight=1)

    def set_widget(self, widget: EditableFrame) -> None:
        self.widget = widget
        self.widget.grid(column=0, row=1, sticky=NSEW)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

    def set_label(self, label: str) -> None:
        self.label.config(text=label)

    def apply_edit_action(self, action: EditAction) -> None:
        if self.widget is not None:
            self.widget.apply_edit_action(action)


def widget_is_descendant(
    widget: Optional[tk.Misc], container: Optional[tk.Widget]
) -> bool:
    if not (widget and container):
        return False

    return str(widget).startswith(str(container))


class SourceEditor(EditableFrame):
    def __init__(self, master: tk.Widget, controller: Controller):
        super().__init__(master)
        self.root_dir = controller.get_root_dir()
        self.controller = controller
        self.file_states: Dict[str, FileState] = {}
        self._find_window: Optional[FindWindow] = None
        left_frame = ttk.Frame(self)

        xml_trees = controller.get_xml_trees()
        input_files = []
        for xml_tree in xml_trees:
            for node in xml_tree:
                if node.filepath not in input_files:
                    input_files.append(node.filepath)

        fileview = LabeledWidget(left_frame, "Project Files")
        self.fileview = FileTree(fileview, input_files)
        self.fileview.bind_selection(
            lambda filepath: self.open_source_file(self.file_states[filepath])
        )
        fileview.set_widget(self.fileview)

        for filepath in input_files:
            with open(
                os.path.join(self.root_dir, filepath), "r", encoding="utf-8"
            ) as f:
                contents = f.read()
                # Source files are having a trailing carriage return (CR) that shall not
                # be displayed.
                if contents and contents[-1] == "\n":
                    contents = contents[:-1]  # Remove the last trailing CR

                self.file_states[filepath] = FileState(filepath, contents)

        file_relpath = controller.get_relative_path(controller.filename)
        self.current_file = self.file_states[file_relpath]
        self.codeview = LabeledWidget(self, file_relpath)
        editor = XMLSourceCodeView(
            self.codeview, self.current_file.content, width=80, height=30, wrap=NONE
        )
        self.codeview.set_widget(editor)

        editor.bind_modified_text(self.on_text_modified)
        editor.bind("<Control-s>", lambda e: self._on_save_shortcut())

        self.property_view = LabeledWidget(left_frame, "Property Explorer")
        property_tree = PropertyTree(
            self.property_view,
            controller.get_property_list(),
            controller.get_property_root(),
        )
        self.property_view.set_widget(property_tree)

        # Window layout
        self.codeview.grid(column=1, row=0, sticky=NSEW)
        fileview.grid(column=0, row=0, sticky=NSEW)
        self.property_view.grid(column=0, row=1, sticky=NS)
        left_frame.grid(column=0, row=0, sticky=NS)
        left_frame.grid_columnconfigure(0, weight=1)
        left_frame.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

    def open_source_file(self, file_state: FileState) -> None:
        editor: XMLSourceCodeView = self.codeview.widget
        if file_state is not self.current_file:
            self.current_file.content = editor.get_content()
            self.codeview.set_label(file_state.filepath)
            editor.new_content(file_state.content)
            self.current_file = file_state
            self.update_title_bar_state()

    def _open_file(self, file_state: FileState) -> None:
        file_tree = self.fileview
        file_id = file_tree.get_id_from_path(file_state.filepath)
        assert file_id is not None
        file_tree.tree.see(file_id)
        file_tree.tree.selection_set([file_id])

        self.open_source_file(file_state)

    def move_to(
        self, file_state: FileState, focus: bool, column: int, line: int
    ) -> None:
        self._open_file(file_state)
        assert isinstance(self.codeview.widget, XMLSourceCodeView)
        editor: XMLSourceCodeView = self.codeview.widget
        editor.move_cursor(f"{line}.{column}", focus)

    def select_text(
        self, text: str, file_state: FileState, column: int, line: int
    ) -> None:
        self._open_file(file_state)
        assert isinstance(self.codeview.widget, XMLSourceCodeView)
        editor: XMLSourceCodeView = self.codeview.widget
        editor.select_text(text, f"{line}.{column}")

    def on_text_modified(self, modified: bool) -> None:
        if modified and not self.current_file.is_modified:
            self.current_file.is_modified = True
            self.fileview.highlight_file(self.current_file.filepath)
            self.update_title_bar_state()

    def _on_save_shortcut(self) -> str:
        self.save_file()
        return "break"

    def apply_edit_action(self, action: EditAction) -> None:
        if action == EditAction.FIND:
            self._open_find_window()
            return

        focused_widget = self.focus_get()
        if widget_is_descendant(focused_widget, self.property_view):
            self.property_view.apply_edit_action(action)
            return

        if widget_is_descendant(focused_widget, self.fileview):
            self.fileview.apply_edit_action(action)
            return

        assert isinstance(self.codeview.widget, XMLSourceCodeView)
        editor = self.codeview.widget
        editor.focus_text()
        editor.apply_edit_action(action)

    def update_title_bar_state(self) -> None:
        any_modified = self.has_modified_files()
        self.master.mark_title_modified(any_modified)

    def has_modified_files(self) -> bool:
        return any(file_state.is_modified for file_state in self.file_states.values())

    def get_modified_files(self) -> List[FileState]:
        return [
            file_state
            for file_state in self.file_states.values()
            if file_state.is_modified
        ]

    def _close_find_window(self) -> None:
        if self._find_window is not None and self._find_window.winfo_exists():
            self._find_window.destroy()
        self._find_window = None

    def _open_find_window(self) -> None:
        if self._find_window is not None and self._find_window.winfo_exists():
            self._find_window.lift()
            return

        self._find_window = FindWindow(
            self,
            self.controller,
            self.file_states,
            self.select_text,
            lambda file_state, col, line: self.move_to(file_state, True, col, line),
        )

    def save_file(self) -> bool:
        if not self.current_file.is_modified:
            return True

        editor: XMLSourceCodeView = self.codeview.widget
        self.current_file.content = editor.get_content()

        error = self.current_file.validate_xml()
        if error:
            self.move_to(self.current_file, True, *error)
            return False

        if self.current_file.write(self.root_dir):
            self.fileview.clear_highlight(self.current_file.filepath)
            self.update_title_bar_state()
            return True

        return False

    def save_all(self) -> bool:
        modified_files = self.get_modified_files()
        if not modified_files:
            return True

        if self.current_file.is_modified:
            editor: XMLSourceCodeView = self.codeview.widget
            self.current_file.content = editor.get_content()

        for file_state in modified_files:
            error = file_state.validate_xml()
            if error:
                self.move_to(file_state, True, *error)
                return False

        # Save AFTER all the files have been validated
        for file_state in modified_files:
            if not file_state.write(self.root_dir):
                return False
            self.fileview.clear_highlight(file_state.filepath)

        self.update_title_bar_state()
        return True
