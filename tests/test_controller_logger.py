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

from jsbsim_gui.controller import JSBSimConsoleLogger


class DummyConsole:
    def __init__(self):
        self.contents = []

    def write(self, contents: str) -> None:
        self.contents.append(contents)


class TestJSBSimConsoleLogger(unittest.TestCase):
    def test_flush_assembles_fragmented_messages(self):
        console = DummyConsole()
        logger = JSBSimConsoleLogger(console)

        logger.set_level(next(iter(jsbsim.LogLevel)))
        logger.message("alpha")
        logger.message(" beta")
        logger.file_location("f.xml", 42)
        logger.format(next(iter(jsbsim.LogFormat)))
        logger.flush()

        self.assertEqual(console.contents, ["alpha beta"])

    def test_flush_no_message_is_noop(self):
        console = DummyConsole()
        logger = JSBSimConsoleLogger(console)

        logger.set_level(next(iter(jsbsim.LogLevel)))
        logger.flush()

        self.assertEqual(console.contents, [])

    def test_set_logger_and_restore_default(self):
        original_logger = jsbsim.get_logger()
        console = DummyConsole()
        logger = JSBSimConsoleLogger(console)

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
