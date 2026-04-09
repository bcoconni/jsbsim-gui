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

import pathlib
import unittest

import jsbsim

from jsbsim_gui.controller import ConsoleLogger


class DummyConsole:
    def __init__(self):
        self.contents = []

    def write(self, contents: str) -> None:
        self.contents.append(contents)

    def write_formatted(self, segments) -> None:
        assert False


class DummyFormattedConsole:
    def __init__(self):
        self.write_calls = []
        self.write_formatted_calls = []

    def write(self, contents: str) -> None:
        self.write_calls.append(contents)

    def write_formatted(self, segments) -> None:
        self.write_formatted_calls.append(list(segments))


class TestJSBSimConsoleLogger(unittest.TestCase):
    def test_flush_assembles_fragmented_messages(self):
        console = DummyConsole()
        logger = ConsoleLogger(console)

        logger.set_level(next(iter(jsbsim.LogLevel)))
        logger.file_location("f.xml", 42)
        logger.message("alpha")
        logger.message(" beta")
        logger.format(next(iter(jsbsim.LogFormat)))
        logger.flush()

        self.assertEqual(console.contents, ["In f.xml: line 42\nalpha beta"])

    def test_flush_no_message_is_noop(self):
        console = DummyConsole()
        logger = ConsoleLogger(console)

        logger.set_level(next(iter(jsbsim.LogLevel)))
        logger.flush()

        self.assertEqual(console.contents, [])

    def test_set_logger_and_restore_default(self):
        original_logger = jsbsim.get_logger()
        console = DummyConsole()
        logger = ConsoleLogger(console)

        try:
            jsbsim.set_logger(logger)
            self.assertIs(jsbsim.get_logger(), logger)

            jsbsim.set_logger(jsbsim.DefaultLogger())
            self.assertIsInstance(jsbsim.get_logger(), jsbsim.DefaultLogger)
        finally:
            jsbsim.set_logger(original_logger)

    def test_controller_no_longer_uses_redirect_stdout(self):
        controller_path = (
            pathlib.Path(__file__).resolve().parents[1] / "jsbsim_gui" / "controller.py"
        )
        code = controller_path.read_text(encoding="utf-8")

        self.assertNotIn("redirect_stdout", code)

    def test_color_format_routes_to_write_formatted(self):
        console = DummyFormattedConsole()
        logger = ConsoleLogger(console)

        logger.set_level(next(iter(jsbsim.LogLevel)))
        logger.format(jsbsim.LogFormat.RED)
        logger.message("error message")
        logger.flush()

        self.assertEqual(console.write_calls, [])
        self.assertEqual(len(console.write_formatted_calls), 1)
        segments = console.write_formatted_calls[0]
        self.assertEqual(len(segments), 1)
        seg_text, tags = segments[0]
        self.assertEqual(seg_text, "error message")
        self.assertIn("log_red", tags)

    def test_format_reset_produces_plain_write(self):
        console = DummyFormattedConsole()
        logger = ConsoleLogger(console)

        logger.set_level(next(iter(jsbsim.LogLevel)))
        logger.format(jsbsim.LogFormat.RED)
        logger.format(jsbsim.LogFormat.BOLD)
        logger.format(jsbsim.LogFormat.UNDERLINE_ON)
        logger.format(jsbsim.LogFormat.RESET)
        logger.message("plain message")
        logger.flush()

        self.assertEqual(console.write_calls, ["plain message"])
        self.assertEqual(console.write_formatted_calls, [])

    def test_format_normal_clears_bold_but_not_color(self):
        console = DummyFormattedConsole()
        logger = ConsoleLogger(console)

        logger.set_level(next(iter(jsbsim.LogLevel)))
        logger.format(jsbsim.LogFormat.RED)
        logger.format(jsbsim.LogFormat.BOLD)
        logger.format(jsbsim.LogFormat.NORMAL)
        logger.message("still red text")
        logger.flush()

        segments = console.write_formatted_calls[0]
        _, tags = segments[0]
        self.assertIn("log_red", tags)
        self.assertNotIn("log_bold", tags)

    def test_format_default_clears_color_but_not_bold(self):
        console = DummyFormattedConsole()
        logger = ConsoleLogger(console)

        logger.set_level(next(iter(jsbsim.LogLevel)))
        logger.format(jsbsim.LogFormat.BLUE)
        logger.format(jsbsim.LogFormat.BOLD)
        logger.format(jsbsim.LogFormat.DEFAULT)
        logger.message("bold but no color")
        logger.flush()

        segments = console.write_formatted_calls[0]
        _, tags = segments[0]
        self.assertNotIn("log_blue", tags)
        self.assertIn("log_bold", tags)

    def test_color_persists_across_messages_in_same_flush(self):
        console = DummyFormattedConsole()
        logger = ConsoleLogger(console)

        logger.set_level(next(iter(jsbsim.LogLevel)))
        logger.format(jsbsim.LogFormat.GREEN)
        logger.message("part 1")
        logger.message("part 2")
        logger.flush()

        segments = console.write_formatted_calls[0]
        self.assertEqual("".join(seg_text for seg_text, _ in segments), "part 1part 2")
        for _, tags in segments:
            self.assertIn("log_green", tags)

    def test_mixed_plain_and_colored_segments(self):
        console = DummyFormattedConsole()
        logger = ConsoleLogger(console)

        logger.set_level(next(iter(jsbsim.LogLevel)))
        logger.message("plain ")
        logger.format(jsbsim.LogFormat.RED)
        logger.message("red")
        logger.format(jsbsim.LogFormat.RESET)
        logger.message(" plain again")
        logger.flush()

        segments = console.write_formatted_calls[0]
        self.assertEqual(
            "".join(seg_text for seg_text, _ in segments), "plain red plain again"
        )
        self.assertEqual(len(segments), 3)
        _, tags0 = segments[0]
        _, tags1 = segments[1]
        _, tags2 = segments[2]
        self.assertEqual(frozenset(tags0), frozenset())
        self.assertIn("log_red", tags1)
        self.assertEqual(frozenset(tags2), frozenset())

    def test_set_level_resets_format_state(self):
        console = DummyFormattedConsole()
        logger = ConsoleLogger(console)

        logger.set_level(next(iter(jsbsim.LogLevel)))
        logger.format(jsbsim.LogFormat.RED)
        logger.set_level(next(iter(jsbsim.LogLevel)))
        logger.message("plain")
        logger.flush()

        self.assertEqual(console.write_calls, ["plain"])
        self.assertEqual(console.write_formatted_calls, [])

    def test_underline_on_off_independent_of_color(self):
        console = DummyFormattedConsole()
        logger = ConsoleLogger(console)

        logger.set_level(next(iter(jsbsim.LogLevel)))
        logger.format(jsbsim.LogFormat.CYAN)
        logger.format(jsbsim.LogFormat.UNDERLINE_ON)
        logger.message("cyan underlined")
        logger.format(jsbsim.LogFormat.UNDERLINE_OFF)
        logger.message("cyan no underline")
        logger.flush()

        segments = console.write_formatted_calls[0]
        self.assertEqual(
            "".join(seg_text for seg_text, _ in segments),
            "cyan underlinedcyan no underline",
        )
        _, tags0 = segments[0]
        _, tags1 = segments[1]
        self.assertIn("log_cyan", tags0)
        self.assertIn("log_underline", tags0)
        self.assertIn("log_cyan", tags1)
        self.assertNotIn("log_underline", tags1)
