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

from dataclasses import asdict
import json
from pathlib import Path
import tempfile
import tkinter as tk
import unittest
from unittest.mock import patch

from jsbsim_gui.options import Options, set_options, get_options
from jsbsim_gui.textview import XMLSourceCodeView, OptionsWindow, XMLSyntaxColors


class TestOptions(Options):
    def __init__(self, file_path: Path):
        self._super_init_completed = False
        super().__init__()
        self._super_init_completed = True
        self._file_path = file_path
        try:
            self.load()
        except json.JSONDecodeError:
            pass

    def load(self):
        if self._super_init_completed:
            super().load()


class TestOptionsModel(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config_file = Path(self.temp_dir.name) / "options.json"

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_default_options(self):
        options = TestOptions(self.config_file)
        self.assertEqual(options.get("xml_syntax_colors"), {})
        default_colors = XMLSyntaxColors()
        self.assertEqual(default_colors.tag, "#ff00ff")
        self.assertEqual(default_colors.comment, "#00aaaa")
        self.assertEqual(default_colors.attribute_name, "#00aa00")
        self.assertEqual(default_colors.attribute_value, "#aaaa00")
        self.assertEqual(default_colors.data, "#000000")

    def test_save_and_load_options(self):
        options = TestOptions(self.config_file)
        custom_colors = {
            "tag": "#112233",
            "comment": "#223344",
            "attribute_name": "#334455",
            "attribute_value": "#445566",
            "data": "#556677",
        }

        options.set("xml_syntax_colors", custom_colors)
        options.save()

        self.assertTrue(self.config_file.is_file())
        with open(self.config_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(data["xml_syntax_colors"], custom_colors)

        # Create a new Options instance pointing to the same file
        loaded_options = TestOptions(self.config_file)
        self.assertEqual(loaded_options.get("xml_syntax_colors"), custom_colors)

    def test_corrupt_file_falls_back_to_defaults(self):
        with open(self.config_file, "w", encoding="utf-8") as f:
            f.write("invalid json content")

        options = TestOptions(self.config_file)
        self.assertEqual(options.get("xml_syntax_colors"), {})

    def test_subscribe_and_notify(self):
        options = TestOptions(self.config_file)
        notified = []

        def callback():
            notified.append(1)

        options.subscribe(callback)
        options.notify()
        self.assertEqual(len(notified), 1)

        options.unsubscribe(callback)
        options.notify()
        self.assertEqual(len(notified), 1)


class TestOptionsWindow(unittest.TestCase):
    def setUp(self):
        self.root = tk.Tk()
        self.root.withdraw()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config_file = Path(self.temp_dir.name) / "options.json"
        set_options(TestOptions(self.config_file))

    def tearDown(self):
        self.root.destroy()
        self.temp_dir.cleanup()

    def test_options_window_init(self):
        window = OptionsWindow(self.root)
        self.assertEqual(window.title(), "Options")
        default_colors = XMLSyntaxColors()
        for tag in asdict(default_colors):
            self.assertIn(tag, window._swatches)
            self.assertIn(tag, window._hex_labels)
            self.assertEqual(
                window._hex_labels[tag].cget("text"),
                getattr(default_colors, tag),
            )
        window.destroy()

    def test_choose_color_updates_preview(self):
        window = OptionsWindow(self.root)
        with patch(
            "tkinter.colorchooser.askcolor", return_value=((18, 52, 86), "#123456")
        ):
            window._choose_color("tag")

        self.assertEqual(window._current_colors.tag, "#123456")
        self.assertEqual(window._hex_labels["tag"].cget("text"), "#123456")
        self.assertEqual(
            window._preview._text.tag_cget("XML_tag", "foreground"), "#123456"
        )
        window.destroy()

    def test_restore_defaults(self):
        window = OptionsWindow(self.root)
        window._current_colors.tag = "#123456"
        window._restore_defaults()
        default_colors = XMLSyntaxColors()
        self.assertEqual(window._current_colors.tag, default_colors.tag)
        self.assertEqual(window._hex_labels["tag"].cget("text"), default_colors.tag)
        window.destroy()

    def test_apply_and_ok(self):
        window = OptionsWindow(self.root)
        window._current_colors.tag = "#abcdef"
        window._apply()

        options_colors = get_options().get("xml_syntax_colors")
        color = XMLSyntaxColors(**options_colors)
        self.assertEqual(color.tag, "#abcdef")
        self.assertFalse(self.config_file.is_file())

        window._ok()
        self.assertTrue(self.config_file.is_file())
        self.assertFalse(window.winfo_exists())


class TestXMLSourceCodeViewOptionsIntegration(unittest.TestCase):
    def setUp(self):
        self.root = tk.Tk()
        self.root.withdraw()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config_file = Path(self.temp_dir.name) / "options.json"
        self.options = TestOptions(self.config_file)
        set_options(self.options)

    def tearDown(self):
        set_options(None)
        self.root.destroy()
        self.temp_dir.cleanup()

    def test_xml_source_code_view_reflects_options(self):
        custom_colors = XMLSyntaxColors()
        custom_colors.tag = "#123456"
        self.options.set("xml_syntax_colors", asdict(custom_colors))

        editor = XMLSourceCodeView(self.root, "<root>text</root>")
        self.assertEqual(editor._text.tag_cget("XML_tag", "foreground"), "#123456")

        # Live update via notify
        new_colors = XMLSyntaxColors()
        new_colors.tag = "#654321"
        self.options.set("xml_syntax_colors", asdict(new_colors))
        self.options.notify()

        self.assertEqual(editor._text.tag_cget("XML_tag", "foreground"), "#654321")
        editor.destroy()


if __name__ == "__main__":
    unittest.main()
