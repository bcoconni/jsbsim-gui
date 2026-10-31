# A Graphical User Interface for JSBSim
#
# Copyright (c) 2026 Bertrand Coconnier
#
# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License, version 3 or later.

import tkinter as tk
import unittest
from tkinter import ttk
from types import SimpleNamespace
from unittest.mock import Mock, patch

from jsbsim_gui.simulation_controls import SimulationControls


class TestSimulationControls(unittest.TestCase):
    def setUp(self):
        self.root = tk.Tk()
        self.root.withdraw()
        self.controller = Mock()
        self.controller.fdm = SimpleNamespace(get_sim_time=lambda: 0.0)
        self.controller.dt = 0.1
        self.controller.run.return_value = True
        self.on_update = Mock()
        self.on_trimmed = Mock()
        self.controls = SimulationControls(
            ttk.Frame(self.root), self.controller, self.on_update, self.on_trimmed
        )

    def tearDown(self):
        self.root.destroy()

    def test_buttons_follow_simulation_state(self):
        controls = self.controls
        self.assertEqual(str(controls.init_button["state"]), "normal")
        for button in (
            controls.trim_button,
            controls.step_button,
            controls.run_pause_button,
        ):
            self.assertEqual(str(button["state"]), "disabled")

        controls.init_button.invoke()
        self.controller.run_ic.assert_called_once()
        self.on_update.assert_called_once()
        self.assertEqual(str(controls.init_button["state"]), "disabled")
        self.assertEqual(str(controls.trim_options["state"]), "readonly")
        self.assertEqual(str(controls.step_button["state"]), "normal")

        controls.step_button.invoke()
        self.controller.run.assert_called_once()
        self.assertEqual(self.on_update.call_count, 2)

        controls.run_pause_button.invoke()
        self.assertTrue(controls.is_running)
        self.assertEqual(str(controls.step_button["state"]), "disabled")
        self.assertEqual(controls.run_pause_button["text"], "Pause")
        controls.run_pause_button.invoke()
        self.assertFalse(controls.is_running)
        self.assertEqual(str(controls.step_button["state"]), "normal")
        self.assertEqual(controls.run_pause_button["text"], "Run")

    def test_trim_notifies_only_after_success(self):
        self.controls.init_button.invoke()
        self.controls.trim_options.current(1)
        self.controller.trim.return_value = True
        self.controls.trim_button.invoke()
        self.controller.trim.assert_called_once_with(2)
        self.on_trimmed.assert_called_once()

        self.controller.trim.return_value = False
        with patch("jsbsim_gui.simulation_controls.showerror") as error:
            self.controls.trim_button.invoke()
            error.assert_called_once()
        self.on_trimmed.assert_called_once()

    def test_reset_cancels_timer_and_restores_initial_state(self):
        self.controls.init_button.invoke()
        self.controls.run_pause_button.invoke()
        timer_id = self.controls.update_id
        self.controls.reset_for_reload()

        self.assertNotIn(
            timer_id, self.root.tk.splitlist(self.root.tk.call("after", "info"))
        )
        self.assertFalse(self.controls.is_running)
        self.assertEqual(str(self.controls.init_button["state"]), "normal")
        self.assertEqual(str(self.controls.step_button["state"]), "disabled")

    def test_destroy_cancels_timer(self):
        self.controls.init_button.invoke()
        self.controls.run_pause_button.invoke()
        timer_id = self.controls.update_id
        self.controls.destroy()
        self.assertNotIn(
            timer_id, self.root.tk.splitlist(self.root.tk.call("after", "info"))
        )

    def test_simulation_end_pauses_and_notifies(self):
        self.controls.init_button.invoke()
        self.controller.run.return_value = False
        with patch(
            "jsbsim_gui.simulation_controls.time.time", side_effect=[100.0, 100.3]
        ):
            self.controls.run()
            self.controls._update_simulation()
        self.assertFalse(self.controls.is_running)
        self.assertTrue(self.controls.script_end_reached)
        self.assertEqual(self.on_update.call_count, 2)
        self.assertEqual(str(self.controls.step_button["state"]), "normal")

    def test_timer_catches_up_and_schedules_next_update(self):
        self.controls.init_button.invoke()
        with patch(
            "jsbsim_gui.simulation_controls.time.time",
            side_effect=[100.0, 100.25, 100.26, 100.27],
        ):
            self.controls.run()
            assert self.controls.update_id is not None
            self.controls.after_cancel(self.controls.update_id)
            self.controls._update_simulation()
        self.assertEqual(self.controller.run.call_count, 2)
        self.assertTrue(self.controls.is_running)
        self.assertEqual(self.on_update.call_count, 2)

    def test_timer_limits_time_spent_catching_up(self):
        self.controls.init_button.invoke()
        with patch(
            "jsbsim_gui.simulation_controls.time.time",
            side_effect=[100.0, 100.25, 100.46],
        ):
            self.controls.run()
            assert self.controls.update_id is not None
            self.controls.after_cancel(self.controls.update_id)
            self.controls._update_simulation()
        self.controller.run.assert_called_once()
        self.assertTrue(self.controls.is_running)
        self.assertEqual(self.on_update.call_count, 2)


if __name__ == "__main__":
    unittest.main()
