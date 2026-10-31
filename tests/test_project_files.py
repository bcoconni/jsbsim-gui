# A Graphical User Interface for JSBSim
#
# Copyright (c) 2026 Bertrand Coconnier
#
# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License, version 3 or later.

import os
import tempfile
import tkinter as tk
import unittest
from tkinter import ttk
from types import SimpleNamespace
from unittest.mock import Mock, patch

from jsbsim_gui.project_files import ProjectFiles


class TestProjectFiles(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = tk.Tk()
        self.root.withdraw()
        self.paths = ["main.xml", "other.xml"]
        for path, content in zip(self.paths, ["<main/>", "<other/>"]):
            with open(
                os.path.join(self.directory.name, path), "w", encoding="utf-8"
            ) as f:
                f.write(content + "\n")
        controller = Mock()
        controller.get_root_dir.return_value = self.directory.name
        controller.filename = os.path.join(self.directory.name, "main.xml")
        controller.get_relative_path.return_value = "main.xml"
        controller.get_xml_trees.return_value = [
            [SimpleNamespace(filepath=path) for path in self.paths]
        ]
        self.editor_content = "<main/>"
        self.on_selected = Mock()
        self.on_invalid = Mock()
        self.on_dirty = Mock()
        self.on_updated = Mock()
        self.files = ProjectFiles(
            ttk.Frame(self.root),
            controller,
            self.on_selected,
            lambda: self.editor_content,
            self.on_invalid,
            self.on_dirty,
            self.on_updated,
        )

    def tearDown(self):
        self.root.destroy()
        self.directory.cleanup()

    def test_saves_modified_files_after_switching_between_them(self):
        main = self.files.current_file
        other = self.files.get_file_state("other.xml")
        assert other is not None
        self.editor_content = "<main>changed</main>"
        self.files.mark_current_modified(True)
        self.files.select_file(other)
        self.assertEqual(main.content, "<main>changed</main>")
        self.editor_content = "<other>changed</other>"
        self.files.mark_current_modified(True)

        self.assertTrue(self.files.save_all())
        self.assertFalse(self.files.has_modified_files())
        self.on_dirty.assert_called_with(False)
        self.on_updated.assert_called_once()
        for path, expected in zip(
            self.paths, ["<main>changed</main>", "<other>changed</other>"]
        ):
            with open(os.path.join(self.directory.name, path), encoding="utf-8") as f:
                self.assertEqual(f.read(), expected)

    def test_save_all_validates_every_file_before_writing(self):
        main = self.files.current_file
        other = self.files.get_file_state("other.xml")
        assert other is not None
        self.editor_content = "<main>changed</main>"
        self.files.mark_current_modified(True)
        self.files.select_file(other)
        self.editor_content = "<other>"
        self.files.mark_current_modified(True)

        with patch("jsbsim_gui.file_state.showerror") as error:
            self.assertFalse(self.files.save_all())
            error.assert_called_once()
        self.assertIs(self.on_invalid.call_args.args[0], other)
        self.assertTrue(main.is_modified)
        self.assertTrue(other.is_modified)
        self.on_updated.assert_not_called()
        with open(os.path.join(self.directory.name, "main.xml"), encoding="utf-8") as f:
            self.assertEqual(f.read(), "<main/>\n")

    def test_save_file_reads_current_editor_contents(self):
        self.editor_content = "<main>saved</main>"
        self.files.mark_current_modified(True)
        self.assertTrue(self.files.save_file())
        self.assertFalse(self.files.current_file.is_modified)
        with open(os.path.join(self.directory.name, "main.xml"), encoding="utf-8") as f:
            self.assertEqual(f.read(), self.editor_content)


if __name__ == "__main__":
    unittest.main()
