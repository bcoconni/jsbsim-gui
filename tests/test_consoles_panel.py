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

from jsbsim_gui.consoles_panel import Console, LogColor, LogSegment, LogTags


class TestConsoleFileLinkCallback(unittest.TestCase):
    def setUp(self):
        self.root = tk.Tk()
        self.root.withdraw()

    def tearDown(self):
        self.root.destroy()

    def test_file_link_click_calls_callback_with_correct_payload(self):
        clicked: list = []

        def on_click(rel_path: str, line: int) -> None:
            clicked.append((rel_path, line))

        console = Console(self.root, on_file_link_click=on_click)
        console.grid(column=0, row=0)
        segments = [
            LogSegment("ERROR: bad config\n", LogTags(color=LogColor.RED, bold=True)),
            LogSegment(
                "In aircraft/c172.xml: line 17\n",
                LogTags(underline=True),
                ("aircraft/c172.xml", 17),
            ),
        ]
        console.write_formatted(segments)

        self.root.update_idletasks()
        self.assertEqual(console._file_link_counter, 1)
        self.assertIn("_fl_0", console._text.tag_names("2.0"))
        self.assertEqual(clicked, [])

    def test_second_file_link_uses_distinct_tag(self):
        clicked: list = []

        def on_click(rel_path: str, line: int) -> None:
            clicked.append((rel_path, line))

        console = Console(self.root, on_file_link_click=on_click)
        console.grid(column=0, row=0)
        segments = [
            LogSegment(
                "In first.xml: line 1\n", LogTags(underline=True), ("first.xml", 1)
            ),
            LogSegment(
                "In second.xml: line 2\n",
                LogTags(underline=True),
                ("second.xml", 2),
            ),
        ]
        console.write_formatted(segments)

        self.root.update_idletasks()
        self.assertEqual(console._file_link_counter, 2)
        self.assertIn("_fl_0", console._text.tag_names("1.0"))
        self.assertIn("_fl_1", console._text.tag_names("2.0"))
        self.assertEqual(clicked, [])

    def test_click_outside_file_link_does_not_call_callback(self):
        clicked: list = []

        def on_click(rel_path: str, line: int) -> None:
            clicked.append((rel_path, line))

        console = Console(self.root, on_file_link_click=on_click)
        console.grid(column=0, row=0)
        segments = [
            LogSegment("ERROR: bad config\n", LogTags(color=LogColor.RED, bold=True)),
            LogSegment("In foo.xml: line 5\n", LogTags(underline=True), ("foo.xml", 5)),
        ]
        console.write_formatted(segments)

        self.root.update_idletasks()
        bbox = console._text.bbox("1.0")
        self.assertIsNotNone(bbox)
        x, y, _, _ = bbox
        console._text.event_generate("<Button-1>", x=x + 1, y=y + 1)
        self.root.update_idletasks()

        self.assertEqual(clicked, [])

    def test_plain_segment_does_not_create_file_link_payload(self):
        clicked: list = []

        def on_click(rel_path: str, line: int) -> None:
            clicked.append((rel_path, line))

        console = Console(self.root, on_file_link_click=on_click)
        console.grid(column=0, row=0)
        segments = [
            LogSegment("plain message\n", LogTags()),
            LogSegment("colored message\n", LogTags(color=LogColor.RED)),
        ]
        console.write_formatted(segments)

        self.root.update_idletasks()
        bbox1 = console._text.bbox("1.0")
        self.assertIsNotNone(bbox1)
        x1, y1, _, _ = bbox1
        console._text.event_generate("<Button-1>", x=x1 + 1, y=y1 + 1)

        bbox2 = console._text.bbox("2.0")
        self.assertIsNotNone(bbox2)
        x2, y2, _, _ = bbox2
        console._text.event_generate("<Button-1>", x=x2 + 1, y=y2 + 1)
        self.root.update_idletasks()

        self.assertEqual(clicked, [])


if __name__ == "__main__":
    unittest.main()
