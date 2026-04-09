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
        console = DummyFormattedConsole()
        logger = ConsoleLogger(console, console, lambda s: s)

        logger.set_level(next(iter(jsbsim.LogLevel)))
        logger.file_location("f.xml", 42)
        logger.message("alpha")
        logger.message(" beta")
        logger.format(next(iter(jsbsim.LogFormat)))
        logger.flush()

        self.assertEqual(len(console.write_formatted_calls), 1)

    def test_flush_no_message_is_noop(self):
        console = DummyConsole()
        logger = ConsoleLogger(console, console, lambda s: s)

        logger.set_level(next(iter(jsbsim.LogLevel)))
        logger.flush()

        self.assertEqual(console.contents, [])

    def test_set_logger_and_restore_default(self):
        original_logger = jsbsim.get_logger()
        console = DummyConsole()
        logger = ConsoleLogger(console, console, lambda s: s)

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
        logger = ConsoleLogger(console, console, lambda s: s)

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
        logger = ConsoleLogger(console, console, lambda s: s)

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
        logger = ConsoleLogger(console, console, lambda s: s)

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
        logger = ConsoleLogger(console, console, lambda s: s)

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
        logger = ConsoleLogger(console, console, lambda s: s)

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
        logger = ConsoleLogger(console, console, lambda s: s)

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
        logger = ConsoleLogger(console, console, lambda s: s)

        logger.set_level(next(iter(jsbsim.LogLevel)))
        logger.format(jsbsim.LogFormat.RED)
        logger.set_level(next(iter(jsbsim.LogLevel)))
        logger.message("plain")
        logger.flush()

        self.assertEqual(console.write_calls, ["plain"])
        self.assertEqual(console.write_formatted_calls, [])

    def test_underline_on_off_independent_of_color(self):
        console = DummyFormattedConsole()
        logger = ConsoleLogger(console, console, lambda s: s)

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

    def test_ordinary_level_routes_to_output_console(self):
        output_console = DummyConsole()
        problems_console = DummyFormattedConsole()
        logger = ConsoleLogger(output_console, problems_console, lambda s: s)

        logger.set_level(jsbsim.LogLevel.INFO)
        logger.message("ordinary")
        logger.flush()

        self.assertEqual(output_console.contents, ["ordinary"])
        self.assertEqual(problems_console.write_calls, [])
        self.assertEqual(problems_console.write_formatted_calls, [])

    def test_warn_routes_to_problems_console(self):
        output_console = DummyFormattedConsole()
        problems_console = DummyFormattedConsole()
        logger = ConsoleLogger(output_console, problems_console, lambda s: s)

        logger.set_level(jsbsim.LogLevel.WARN)
        logger.message("warning")
        logger.flush()

        self.assertEqual(output_console.write_calls, [])
        self.assertEqual(output_console.write_formatted_calls, [])
        self.assertEqual(len(problems_console.write_formatted_calls), 1)
        self.assertGreater(len(problems_console.write_formatted_calls[0]), 0)

    def test_error_and_fatal_route_to_problems_console(self):
        output_console = DummyFormattedConsole()
        problems_console = DummyFormattedConsole()
        logger = ConsoleLogger(output_console, problems_console, lambda s: s)

        logger.set_level(jsbsim.LogLevel.ERROR)
        logger.message("error")
        logger.flush()

        logger.set_level(jsbsim.LogLevel.FATAL)
        logger.format(jsbsim.LogFormat.RED)
        logger.message("fatal")
        logger.flush()

        self.assertEqual(output_console.write_calls, [])
        self.assertEqual(len(problems_console.write_formatted_calls), 2)
        self.assertGreater(len(problems_console.write_formatted_calls[0]), 0)
        self.assertGreater(len(problems_console.write_formatted_calls[1]), 0)
