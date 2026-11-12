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
from tkinter import ttk
from unittest.mock import patch

from jsbsim_gui.options import Options, OptionsWindow, set_options, get_options
from jsbsim_gui.textview import (
    SOURCE_CODE_VIEW_OPTIONS_KEY,
    SourceCodeViewOptions,
    XMLSourceCodeView,
    XMLSyntaxColors,
    TextViewOptionsTab,
)


class TestOptions(Options):
    def __init__(self, file_path: Path):
        self._super_init_completed = False
        super().__init__()
        self._super_init_completed = True
        self._file_path = file_path
        try:
            self._load()
        except json.JSONDecodeError:
            pass

    def _load(self):
        if self._super_init_completed:
            super()._load()


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
        display_options = SourceCodeViewOptions()
        self.assertEqual(display_options.active_line_color, "#fff2cc")
        self.assertEqual(display_options.selection_color, "#c3d9ff")
        self.assertTrue(display_options.highlight_active_line)
        self.assertTrue(display_options.bold_line_number)

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
        options._save()

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

        options.subscribe("test", callback)
        options.set("test", {"a": 1})
        self.assertEqual(len(notified), 1)

        options.unsubscribe("test", callback)
        options.set("test", {})
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
        xml_tab = TextViewOptionsTab(window)
        window.add_option_tab(xml_tab, "XML Syntax")
        window.update_idletasks()
        self.assertEqual(window.title(), "Options")
        self.assertEqual(
            xml_tab._preview._line_numbers.winfo_reqheight(),
            xml_tab._preview._text.winfo_reqheight(),
        )
        syntax_chooser = xml_tab._color_choosers["tag"]
        display_chooser = xml_tab._color_choosers["active_line_color"]
        notebook = syntax_chooser.master.master
        self.assertIsInstance(notebook, ttk.Notebook)
        self.assertIs(display_chooser.master.master, notebook)
        self.assertEqual(notebook.tab(syntax_chooser.master, "text"), "XML Colors")
        self.assertEqual(notebook.tab(display_chooser.master, "text"), "Editor")
        self.assertTrue(xml_tab._highlight_active_line_var.get())
        self.assertTrue(xml_tab._bold_line_number_var.get())
        window.destroy()

    def test_choose_color_updates_preview(self):
        window = OptionsWindow(self.root)
        xml_tab = TextViewOptionsTab(window)
        window.add_option_tab(xml_tab, "XML Syntax")
        with patch(
            "tkinter.colorchooser.askcolor", return_value=((18, 52, 86), "#123456")
        ):
            xml_tab._color_choosers["tag"].choose_color()

        self.assertEqual(xml_tab._current_colors.tag, "#123456")
        self.assertEqual(
            xml_tab._color_choosers["tag"].hex_label.cget("text"), "#123456"
        )
        self.assertEqual(
            xml_tab._preview._text.tag_cget("XML_tag", "foreground"), "#123456"
        )
        window.destroy()

    def test_cancel_unregisters_preview_option_callbacks(self):
        window = OptionsWindow(self.root)
        xml_tab = TextViewOptionsTab(window)
        window.add_option_tab(xml_tab, "XML Syntax")

        with patch.object(self.root, "report_callback_exception") as report_exception:
            window._cancel()

        report_exception.assert_not_called()
        options = get_options()
        self.assertNotIn(
            xml_tab._preview._load_syntax_colors,
            options._subscribers.get("xml_syntax_colors", []),
        )
        self.assertNotIn(
            xml_tab._preview._load_display_options,
            options._subscribers.get(SOURCE_CODE_VIEW_OPTIONS_KEY, []),
        )

    def test_display_options_update_preview_and_apply(self):
        window = OptionsWindow(self.root)
        xml_tab = TextViewOptionsTab(window)
        window.add_option_tab(xml_tab, "XML Syntax")
        with patch(
            "tkinter.colorchooser.askcolor",
            side_effect=[
                ((18, 52, 86), "#123456"),
                ((101, 67, 33), "#654321"),
            ],
        ):
            xml_tab._color_choosers["active_line_color"].choose_color()
            xml_tab._color_choosers["selection_color"].choose_color()

        xml_tab._highlight_active_line_var.set(False)
        xml_tab._bold_line_number_var.set(False)
        xml_tab._update_display_options()
        xml_tab.apply()

        options = SourceCodeViewOptions(
            **get_options().get(SOURCE_CODE_VIEW_OPTIONS_KEY)
        )
        self.assertEqual(options.active_line_color, "#123456")
        self.assertEqual(options.selection_color, "#654321")
        self.assertFalse(options.highlight_active_line)
        self.assertFalse(options.bold_line_number)
        self.assertEqual(xml_tab._preview._text.cget("selectbackground"), "#654321")
        self.assertEqual(
            xml_tab._preview._text.tag_cget("active_line", "background"), ""
        )
        self.assertEqual(
            xml_tab._preview._active_line_number_font.actual("weight"), "normal"
        )
        window.destroy()

    def test_restore_defaults(self):
        window = OptionsWindow(self.root)
        xml_tab = TextViewOptionsTab(window)
        window.add_option_tab(xml_tab, "XML Syntax")
        xml_tab._current_colors.tag = "#123456"
        xml_tab.restore_defaults()
        default_colors = XMLSyntaxColors()
        self.assertEqual(xml_tab._current_colors.tag, default_colors.tag)
        window.destroy()

    def test_apply_and_ok(self):
        window = OptionsWindow(self.root)
        xml_tab = TextViewOptionsTab(window)
        window.add_option_tab(xml_tab, "XML Syntax")
        xml_tab._current_colors.tag = "#abcdef"
        xml_tab.apply()

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

        self.assertEqual(editor._text.tag_cget("XML_tag", "foreground"), "#654321")
        editor.destroy()

    def test_xml_source_code_view_reflects_display_options(self):
        editor = XMLSourceCodeView(self.root, "<root>text</root>")
        options = SourceCodeViewOptions(
            active_line_color="#123456",
            selection_color="#654321",
            highlight_active_line=True,
            bold_line_number=False,
        )
        self.options.set(SOURCE_CODE_VIEW_OPTIONS_KEY, asdict(options))

        self.assertEqual(editor._text.cget("selectbackground"), "#654321")
        self.assertEqual(editor._text.cget("inactiveselectbackground"), "#654321")
        self.assertEqual(editor._text.tag_cget("active_line", "background"), "#123456")
        self.assertEqual(editor._active_line_number_font.actual("weight"), "normal")

        options.highlight_active_line = False
        self.options.set(SOURCE_CODE_VIEW_OPTIONS_KEY, asdict(options))
        self.assertEqual(editor._text.tag_cget("active_line", "background"), "")
        editor.destroy()


if __name__ == "__main__":
    unittest.main()
