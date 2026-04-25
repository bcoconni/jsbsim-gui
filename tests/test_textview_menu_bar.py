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
import unittest
import sys
import os

import jsbsim_gui.edit_actions as edit_actions
from jsbsim_gui.menu_bar import MenuBar
from jsbsim_gui.textview import XMLSourceCodeView


class TestRoot(tk.Tk):
    def __init__(self):
        super().__init__()
        self.calls: list[str] = []

    def save_file(self) -> None:
        return None

    def save_all(self) -> None:
        return None

    def on_closing(self) -> None:
        return None

    def edit(self) -> None:
        return None

    def run(self) -> None:
        return None

    def edit_action(self, action: edit_actions.EditAction) -> None:
        self.calls.append(action.name)


class TestEditMenuCommands(unittest.TestCase):
    def setUp(self):
        self.root = TestRoot()
        self.root.withdraw()

    def tearDown(self):
        self.root.destroy()

    def test_edit_menu_commands_delegate_to_master_methods(self):
        menubar = MenuBar(self.root, ".")

        for index in [0, 1, 3, 4, 5, 6]:
            menubar.edit_menu.invoke(index)

        self.assertEqual(
            self.root.calls,
            ["UNDO", "REDO", "SELECT_ALL", "CUT", "COPY", "PASTE"],
        )


class TestXMLSourceCodeViewEditActions(unittest.TestCase):
    def setUp(self):
        self.root = tk.Tk()
        self.root.withdraw()
        self.editor = XMLSourceCodeView(self.root, "<root>value</root>")
        self.editor.grid(column=0, row=0)
        self.root.update_idletasks()

    def tearDown(self):
        self.root.destroy()

    def test_select_all_copy_cut_paste_undo_redo(self):
        if sys.platform == "darwin" and os.environ.get("GITHUB_ACTIONS") == "true":
            self.skipTest("Clipboard edit actions hang on macOS Tk in GitHub Actions")

        self.editor.focus_text()
        self.editor.apply_edit_action(edit_actions.EditAction.SELECT_ALL)
        self.editor.apply_edit_action(edit_actions.EditAction.COPY)
        self.root.update()
        self.assertEqual(self.root.clipboard_get(), "<root>value</root>")

        self.editor.apply_edit_action(edit_actions.EditAction.CUT)
        self.root.update()
        self.assertEqual(self.editor.get_content(), "")

        self.editor.apply_edit_action(edit_actions.EditAction.PASTE)
        self.root.update()
        self.assertEqual(self.editor.get_content(), "<root>value</root>")

        self.editor.apply_edit_action(edit_actions.EditAction.UNDO)
        self.root.update()
        self.assertEqual(self.editor.get_content(), "")

        self.editor.apply_edit_action(edit_actions.EditAction.REDO)
        self.root.update()
        self.assertEqual(self.editor.get_content(), "<root>value</root>")


if __name__ == "__main__":
    unittest.main()
