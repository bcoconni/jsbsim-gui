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

from jsbsim_gui.consoles_panel import ConsoleLogger, LogColor, LogTags


class DummyConsole:
    def __init__(self):
        self.contents = []

    def write(self, contents: str) -> None:
        self.contents.append(contents)

    def write_formatted(self, _segments) -> None:
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
        seg_text = segments[0].text
        tags = segments[0].tags
        self.assertEqual(seg_text, "error message")
        self.assertIn(LogColor.RED, tags)

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
        tags = segments[0].tags
        self.assertIn(LogColor.RED, tags)
        self.assertNotIn(LogTags.BOLD, tags)

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
        tags = segments[0].tags
        self.assertNotIn(LogColor.BLUE, tags)
        self.assertIn(LogTags.BOLD, tags)

    def test_color_persists_across_messages_in_same_flush(self):
        console = DummyFormattedConsole()
        logger = ConsoleLogger(console, console, lambda s: s)

        logger.set_level(next(iter(jsbsim.LogLevel)))
        logger.format(jsbsim.LogFormat.GREEN)
        logger.message("part 1")
        logger.message("part 2")
        logger.flush()

        segments = console.write_formatted_calls[0]
        self.assertEqual("".join(segment.text for segment in segments), "part 1part 2")
        for segment in segments:
            self.assertIn(LogColor.GREEN, segment.tags)

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
            "".join(segment.text for segment in segments), "plain red plain again"
        )
        self.assertEqual(len(segments), 3)
        self.assertEqual(segments[0].tags, LogTags())
        self.assertIn(LogColor.RED, segments[1].tags)
        self.assertEqual(segments[2].tags, LogTags())

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
            "".join(segment.text for segment in segments),
            "cyan underlinedcyan no underline",
        )
        tags0 = segments[0].tags
        tags1 = segments[1].tags
        self.assertIn(LogColor.CYAN, tags0)
        self.assertIn(LogTags.UNDERLINE, tags0)
        self.assertIn(LogColor.CYAN, tags1)
        self.assertNotIn(LogTags.UNDERLINE, tags1)

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

    def test_file_location_produces_file_link_segment(self):
        problems_console = DummyFormattedConsole()
        output_console = DummyFormattedConsole()
        logger = ConsoleLogger(output_console, problems_console, lambda s: s)

        logger.set_level(jsbsim.LogLevel.ERROR)
        logger.file_location("aircraft/c172/c172.xml", 42)
        logger.flush()

        segments = problems_console.write_formatted_calls[0]
        link_segments = [s for s in segments if s.file_link is not None]
        self.assertEqual(len(link_segments), 1)
        self.assertEqual(link_segments[0].file_link, ("aircraft/c172/c172.xml", 42))
        self.assertIn(LogTags.UNDERLINE, link_segments[0].tags)
        self.assertIn("In aircraft/c172/c172.xml: line 42", link_segments[0].text)

    def test_file_location_does_not_merge_with_adjacent_segments(self):
        problems_console = DummyFormattedConsole()
        output_console = DummyFormattedConsole()
        logger = ConsoleLogger(output_console, problems_console, lambda s: s)

        logger.set_level(jsbsim.LogLevel.ERROR)
        logger.message("ERROR: something went wrong\n")
        logger.file_location("foo.xml", 7)
        logger.message("more context\n")
        logger.flush()

        segments = problems_console.write_formatted_calls[0]
        link_segments = [s for s in segments if s.file_link is not None]
        self.assertEqual(len(link_segments), 1)
        self.assertEqual(link_segments[0].file_link, ("foo.xml", 7))
